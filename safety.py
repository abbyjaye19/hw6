"""CODE defense layer: turn a vendor document into only the text a person would actually see.

Runs before any model sees the document. Each reader returns (visible_text, removed), where
`removed` lists every piece of hidden content that was dropped and how it was hidden.

Hidden content we drop:
  HTML   comments, <script>/<style>/<head>, <noscript>/<template>, the `hidden` attribute, and any element whose inline
         style or <style>-block rule hides it: display:none, visibility:hidden, opacity:0,
         font-size under 4px, text the same color as its background, zero-size boxes, and
         off-screen positioning or text-indent.
  PDF    text in a font under 4 pt, text filled in white or near-white, text drawn outside
         the page, and text in an invisible render mode (3 Tr, as in OCR layers; added after
         the Problem 7 red team).
  Email  only the body a mail app displays (the HTML part if there is one, otherwise plain
         text), cleaned like HTML above. Other alternative parts are dropped.
  All    invisible Unicode characters (zero-width spaces, bidi controls) are stripped.
"""

from __future__ import annotations

import email
import re
import unicodedata
from email import policy
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from pypdf import PdfReader

MIN_FONT_PX = 4.0  # anything smaller is unreadable on screen
MIN_FONT_PT = 4.0
WHITE = {"#fff", "#ffffff", "white", "rgb(255,255,255)", "rgba(255,255,255,1)"}


def _short(text: str, n: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + "..."


def strip_invisible_chars(text: str) -> tuple[str, int]:
    """Remove zero-width and other format characters (Unicode category Cf) and normalize."""
    text = unicodedata.normalize("NFKC", text)
    cleaned = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return cleaned, len(text) - len(cleaned)


# ---------------------------------------------------------------- HTML

def _parse_style(style: str) -> dict[str, str]:
    props = {}
    for decl in style.split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            props[k.strip().lower()] = v.strip().lower()
    return props


def _size_px(value: str) -> float | None:
    m = re.match(r"^(-?[\d.]+)\s*(px|pt|em|rem|%)?", value)
    if not m:
        return None
    num, unit = float(m.group(1)), m.group(2) or "px"
    return {"px": num, "pt": num * 4 / 3, "em": num * 16, "rem": num * 16, "%": num * 0.16}[unit]


def _norm_color(value: str) -> str:
    return value.replace(" ", "").split("!")[0]


def _hidden_reason(props: dict[str, str], background: str) -> str | None:
    """Why a CSS declaration block makes its text invisible, or None if it is visible."""
    if props.get("display") == "none":
        return "display:none"
    if props.get("visibility") in ("hidden", "collapse"):
        return "visibility:hidden"
    if "opacity" in props and (_size_px(props["opacity"]) or 0) <= 0.05:
        return f"opacity:{props['opacity']}"
    if "font-size" in props:
        size = _size_px(props["font-size"])
        if size is not None and size < MIN_FONT_PX:
            return f"font-size:{props['font-size']}"
    color = _norm_color(props.get("color", ""))
    if color:
        if color in ("transparent",) or re.match(r"rgba\(.*,0(\.0+)?\)$", color):
            return f"color:{color}"
        if color == background or (color in WHITE and background in WHITE):
            return f"color:{color} on background {background}"
    for dim in ("height", "width", "max-height", "max-width"):
        if dim in props and (_size_px(props[dim]) == 0) and props.get("overflow") == "hidden":
            return f"{dim}:0 with overflow:hidden"
    if props.get("position") in ("absolute", "fixed"):
        for side in ("left", "top", "right"):
            v = _size_px(props.get(side, "0")) or 0
            if v <= -500:
                return f"off-screen {side}:{props[side]}"
    indent = _size_px(props.get("text-indent", "0")) or 0
    if indent <= -500:
        return f"text-indent:{props['text-indent']}"
    if "clip" in props and "rect(0" in props["clip"].replace(" ", ""):
        return "clip:rect(0...)"
    if "transform" in props and re.search(r"scale\(0(\.0+)?\)", props["transform"]):
        return "transform:scale(0)"
    return None


def _style_block_rules(soup: BeautifulSoup) -> list[tuple[str, dict[str, str]]]:
    """Simple selectors (tag, .class, #id, tag.class) from <style> blocks with their declarations."""
    rules = []
    for tag in soup.find_all("style"):
        css = re.sub(r"/\*.*?\*/", "", tag.get_text(), flags=re.S)
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            props = _parse_style(body)
            for sel in selectors.split(","):
                rules.append((sel.strip(), props))
    return rules


def _matches(el, selector: str) -> bool:
    m = re.fullmatch(r"([a-zA-Z][\w-]*)?((?:[.#][\w-]+)*)", selector)
    if not m or not selector:
        return False
    tag, rest = m.group(1), m.group(2)
    if tag and el.name != tag.lower():
        return False
    for kind, name in re.findall(r"([.#])([\w-]+)", rest):
        if kind == "." and name not in (el.get("class") or []):
            return False
        if kind == "#" and el.get("id") != name:
            return False
    return bool(tag or rest)


def sanitize_html(html: str) -> tuple[str, list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    removed: list[dict] = []

    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        if c.strip():
            removed.append({"how": "HTML comment", "text": _short(c)})
        c.extract()

    rules = _style_block_rules(soup)
    body_bg = "#ffffff"
    for sel, props in rules:
        if sel in ("body", "html"):
            body_bg = _norm_color(props.get("background-color") or props.get("background", body_bg).split()[0])

    for tag in soup(["noscript", "template"]):
        text = tag.get_text(" ", strip=True)
        if text:
            removed.append({"how": f"HTML <{tag.name}> (not shown in a normal browser)", "text": _short(text)})
        tag.decompose()
    for tag in soup(["script", "style", "head", "meta", "link"]):
        tag.decompose()

    def element_props(el) -> dict[str, str]:
        props = {}
        for sel, p in rules:
            if _matches(el, sel):
                props.update(p)
        props.update(_parse_style(el.get("style", "")))
        return props

    def background_of(el) -> str:
        node = el
        while node is not None and getattr(node, "name", None):
            p = element_props(node)
            bg = p.get("background-color") or (p.get("background", "").split() or [None])[0]
            if bg:
                return _norm_color(bg)
            node = node.parent
        return body_bg

    for el in list(soup.find_all(True)):
        if el.decomposed if hasattr(el, "decomposed") else False:
            continue
        if el.has_attr("hidden"):
            reason = "hidden attribute"
        else:
            reason = _hidden_reason(element_props(el), background_of(el.parent) if el.parent else body_bg)
        if reason:
            text = el.get_text(" ", strip=True)
            if text:
                removed.append({"how": f"HTML <{el.name}> {reason}", "text": _short(text)})
            el.decompose()

    text = soup.get_text("\n", strip=True)
    return text, removed


# ---------------------------------------------------------------- PDF

def _mult(a: list[float], b: list[float]) -> list[float]:
    return [
        a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
        a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
        a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5],
    ]


def _is_whiteish(color: tuple[str, list[float]]) -> bool:
    space, vals = color
    if space == "gray":
        return vals[0] >= 0.95
    if space == "rgb":
        return all(v >= 0.95 for v in vals)
    if space == "cmyk":
        return all(v <= 0.05 for v in vals)
    return False


def sanitize_pdf(path: Path) -> tuple[str, list[dict]]:
    reader = PdfReader(str(path))
    lines: list[str] = []
    removed: list[dict] = []
    for page in reader.pages:
        box = [float(v) for v in page.mediabox]
        state = {"fill": ("gray", [0.0]), "render": 0}
        kept: list[str] = []

        def before(op, args, cm, tm):
            name = op.decode() if isinstance(op, bytes) else op
            if name == "Tr" and args:
                state["render"] = int(float(args[0]))
                return
            if name == "BT":
                return
            try:
                vals = [float(a) for a in args]
            except (TypeError, ValueError):
                return
            if name == "g":
                state["fill"] = ("gray", vals)
            elif name == "rg":
                state["fill"] = ("rgb", vals)
            elif name == "k":
                state["fill"] = ("cmyk", vals)
            elif name in ("sc", "scn") and len(vals) in (1, 3, 4):
                state["fill"] = ({1: "gray", 3: "rgb", 4: "cmyk"}[len(vals)], vals)

        def visit(text, cm, tm, font_dict, font_size):
            if not text.strip():
                if text and kept and not kept[-1].endswith("\n"):
                    kept.append("\n")
                return
            m = _mult(list(tm), list(cm))
            scale = (m[2] ** 2 + m[3] ** 2) ** 0.5 or 1.0
            size = (font_size or 0) * scale
            x, y = m[4], m[5]
            reason = None
            if state["render"] in (3, 7):  # 3 = invisible text (OCR layers), 7 = clip only
                reason = f"PDF text in invisible render mode {state['render']} Tr"
            elif size < MIN_FONT_PT:
                reason = f"PDF text in {size:.1f}-pt font"
            elif _is_whiteish(state["fill"]):
                reason = f"PDF text filled white ({state['fill'][0]} {state['fill'][1]})"
            elif not (box[0] - 1 <= x <= box[2] + 1 and box[1] - 1 <= y <= box[3] + 1):
                reason = f"PDF text drawn off the page at ({x:.0f}, {y:.0f})"
            if reason:
                removed.append({"how": reason, "text": _short(text)})
            else:
                kept.append(text if text.endswith("\n") else text + "\n")

        page.extract_text(visitor_operand_before=before, visitor_text=visit)
        lines.append("".join(kept))
    text = re.sub(r"\n{2,}", "\n", "\n".join(lines)).strip()
    return text, removed


# ---------------------------------------------------------------- Email

def sanitize_eml(path: Path) -> tuple[str, list[dict]]:
    msg = email.message_from_bytes(path.read_bytes(), policy=policy.default)
    removed: list[dict] = []
    header = [f"{h}: {msg[h]}" for h in ("From", "To", "Subject", "Date") if msg[h]]

    body = msg.get_body(preferencelist=("html", "plain"))
    parts_text = []
    if body is not None:
        if body.get_content_type() == "text/html":
            text, rem = sanitize_html(body.get_content())
            removed += rem
        else:
            text = body.get_content()
        parts_text.append(text)
        # The alternative versions a mail app does NOT show are dropped. They are only reported
        # when they state different numbers than the displayed body (a normal email repeats itself).
        shown_numbers = set(re.findall(r"\d+(?:\.\d+)?", text))
        for part in msg.walk():
            if part is body or part.is_multipart() or part.get_content_maintype() != "text":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            alt = part.get_content()
            if part.get_content_type() == "text/html":
                alt = BeautifulSoup(alt, "html.parser").get_text(" ")
            extra = set(re.findall(r"\d+(?:\.\d+)?", alt)) - shown_numbers
            if extra:
                removed.append({"how": f"email {part.get_content_type()} alternative part (not displayed) "
                                       f"with different numbers {sorted(extra)}", "text": _short(alt)})

    for att in msg.iter_attachments():
        name = att.get_filename() or "attachment"
        suffix = Path(name).suffix.lower()
        data = att.get_payload(decode=True) or b""
        if suffix == ".pdf":
            tmp = path.with_name(f".{path.stem}_{name}")
            tmp.write_bytes(data)
            try:
                text, rem = sanitize_pdf(tmp)
            finally:
                tmp.unlink(missing_ok=True)
        elif suffix in (".html", ".htm"):
            text, rem = sanitize_html(data.decode("utf-8", "replace"))
        elif att.get_content_maintype() == "text":
            text, rem = data.decode("utf-8", "replace"), []
        else:
            continue
        removed += rem
        parts_text.append(f"[Attachment {name}]\n{text}")

    return "\n".join(header + parts_text).strip(), removed


# ---------------------------------------------------------------- entry point

def visible_text(path: Path) -> tuple[str, list[dict]]:
    """What a person would see when opening the document, plus everything that was dropped."""
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm"):
        text, removed = sanitize_html(path.read_text(encoding="utf-8", errors="replace"))
    elif suffix == ".pdf":
        text, removed = sanitize_pdf(path)
    elif suffix == ".eml":
        text, removed = sanitize_eml(path)
    else:
        text, removed = path.read_text(encoding="utf-8", errors="replace"), []
    text, n_invisible = strip_invisible_chars(text)
    if n_invisible:
        removed.append({"how": "invisible Unicode characters (zero-width / format)", "text": f"{n_invisible} characters"})
    return text, removed
