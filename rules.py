"""DESIGN defense layer: the handbook's purchasing rules, applied in plain Python.

The decision is made here from the extracted facts, so no text inside a vendor document can
argue its way to a "recommend". The approved/removed vendor lists, vendor email domains, and
max unit costs are parsed straight from data/shop_handbook.md (sections 5, 6, 9).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from models import VendorDecision, VendorExtraction

HANDBOOK = Path(__file__).resolve().parent / "data" / "shop_handbook.md"
MAX_LEAD_DAYS = 21
MAX_MIN_ORDER = 600


def _section(text: str, number: int) -> str:
    m = re.search(rf"^## {number}\..*?(?=^## \d+\.|\Z)", text, flags=re.M | re.S)
    return m.group(0) if m else ""


def _rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows[1:]  # skip header


@lru_cache
def handbook_rules() -> dict:
    text = HANDBOOK.read_text(encoding="utf-8")
    approved, domains = {}, {}
    for row in _rows(_section(text, 5)):
        name = row[1]
        approved[name.lower()] = name
        m = re.search(r"@([\w.-]+)", row[-1])
        if m:
            domains[name] = m.group(1).lower()
    removed = {row[0].lower(): row[0] for row in _rows(_section(text, 6))}
    max_cost = {}
    for row in _rows(_section(text, 9)):
        if row[0].startswith("CC-"):
            max_cost[row[0]] = float(row[4].replace("$", "").replace(",", ""))
    return {"approved": approved, "domains": domains, "removed": removed, "max_cost": max_cost}


def canonical_vendor(name: str) -> str:
    """Map a stated vendor name onto the handbook's spelling when it clearly matches."""
    rules = handbook_rules()
    key = name.lower().strip()
    for table in (rules["approved"], rules["removed"]):
        for k, v in table.items():
            if key == k or key.startswith(k) or (len(key) >= 5 and k.startswith(key)):
                return v
    return name.strip()


def _distinct(values: list) -> list:
    seen = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


def _grounded(values: list, text: str, fmt) -> list:
    """Keep only values that literally appear in the document text (blocks invented numbers)."""
    return [v for v in values if any(s in text for s in fmt(v))]


# Clearly labelled fields, read straight from the document text by the program. This backs up the
# extractor model: if it misses a value (it once dropped a plain "Lead time: 7 business days"), the
# program still has it, and if the two disagree the conflict rule below refuses the quote.
_LABELLED = {
    "unit_prices": (r"unit price\s*[:\-]?\s*\$\s*([\d,]+(?:\.\d+)?)", float),
    "lead_times_days": (r"lead time\s*[:\-]?\s*(\d+)\s*(?:business\s+|working\s+|calendar\s+)?days?\b", int),
    "min_orders": (r"minimum order(?: quantity)?\s*[:\-]?\s*([\d,]+)\s*units?\b", int),
    "skus": (r"\b(CC-[A-Z]{2}-\d{3})\b", str),
}


def labelled_values(doc_text: str) -> dict[str, list]:
    found = {}
    for field, (pattern, cast) in _LABELLED.items():
        flags = 0 if field == "skus" else re.I
        found[field] = [cast(m.replace(",", "")) for m in re.findall(pattern, doc_text, flags)]
    return found


def _merge(model_values: list, program_values: list) -> list:
    """Model's values first (in its order), then any labelled value the model missed."""
    return list(model_values) + [v for v in program_values if v not in model_values]


def decide(ex: VendorExtraction, doc_text: str, removed_hidden: list[dict]) -> VendorDecision:
    rules = handbook_rules()
    flags: list[str] = []

    found = labelled_values(doc_text)
    unit_prices = _merge(ex.unit_prices, found["unit_prices"])
    lead_times = _merge(ex.lead_times_days, found["lead_times_days"])
    min_orders = _merge(ex.min_orders, found["min_orders"])
    sku_list = _merge([s.upper() for s in ex.skus], found["skus"])

    prices = _distinct(_grounded(unit_prices, doc_text, lambda v: (f"{v:.2f}", f"{v:,.2f}", f"{v:g}")))
    leads = _distinct(_grounded(lead_times, doc_text, lambda v: (str(v),)))
    mins = _distinct(_grounded(min_orders, doc_text, lambda v: (str(v), f"{v:,}")))
    skus = _distinct([s for s in sku_list if s in doc_text.upper()])
    vendors = _distinct([canonical_vendor(v) for v in ex.vendor_names])

    # First value stated is the one reported; a document that restates a field differently is flagged.
    conflicts = []
    for label, vals in (("vendor", vendors), ("SKU", skus), ("unit price", prices),
                        ("lead time", leads), ("minimum order", mins)):
        if len(vals) > 1:
            conflicts.append(label)
            flags.append(f"document states conflicting {label} values {vals}; the first is reported")
    vendor = vendors[0] if vendors else "unknown"
    sku = skus[0] if skus else None
    price = prices[0] if prices else None
    lead = leads[0] if leads else None
    min_order = mins[0] if mins else None

    if removed_hidden:
        flags.append(f"{len(removed_hidden)} hidden item(s) removed before reading: "
                     + "; ".join(r["how"] for r in removed_hidden))
    for instr in ex.embedded_instructions:
        flags.append(f"document contains instructions aimed at the reviewer/AI (ignored): {instr[:120]}")

    # Vendor identity: if the document shows email addresses, one must be on the vendor's handbook domain.
    domain = rules["domains"].get(vendor)
    doc_domains = {d.lower() for d in re.findall(r"@([\w.-]+\.\w+)", doc_text)} - {"campuscustoms.example"}
    identity_ok = not (domain and doc_domains and domain not in doc_domains)
    if not identity_ok:
        flags.append(f"vendor identity mismatch: claims {vendor} but the document's email domains are {sorted(doc_domains)}")

    def result(decision: str, reason: str) -> VendorDecision:
        return VendorDecision(vendor=vendor, sku=sku, unit_price=price, lead_time_days=lead,
                              min_order=min_order, decision=decision, reason=reason, flags=flags)

    # The four purchasing checks, in handbook order.
    if vendor.lower() in rules["removed"]:
        return result("do_not_recommend", f"Approved-vendor check fails: {vendor} is on the removed/pending list (handbook section 6).")
    if vendor.lower() not in rules["approved"]:
        return result("do_not_recommend", f"Approved-vendor check fails: {vendor} is not on the approved vendor list (handbook section 5).")
    if not identity_ok or "vendor" in conflicts:
        return result("do_not_recommend", f"Approved-vendor check fails: the document does not consistently identify the vendor as {vendor}, so it needs human review.")
    if "SKU" in conflicts:
        return result("do_not_recommend", "Price check cannot pass: the document names more than one SKU, so the max unit cost is unclear.")
    if sku is None or sku not in rules["max_cost"]:
        return result("do_not_recommend", f"Price check cannot pass: SKU {sku or 'unknown'} is not in the catalogue, so there is no max unit cost to compare.")
    max_cost = rules["max_cost"][sku]
    if price is None:
        return result("do_not_recommend", "Price check cannot pass: the document does not state a unit price.")
    if "unit price" in conflicts:
        return result("do_not_recommend", f"Price check fails: the document states conflicting unit prices {prices}, so the quote needs written confirmation.")
    if price > max_cost:
        return result("do_not_recommend", f"Price check fails: ${price:.2f} is above the ${max_cost:.2f} max unit cost for {sku}.")
    if lead is None:
        return result("do_not_recommend", "Lead-time check cannot pass: the document does not state a lead time.")
    if "lead time" in conflicts:
        return result("do_not_recommend", f"Lead-time check fails: the document states conflicting lead times {leads}, so it needs written confirmation.")
    if lead > MAX_LEAD_DAYS:
        return result("do_not_recommend", f"Lead-time check fails: {lead} days is more than the {MAX_LEAD_DAYS}-day limit.")
    if min_order is None:
        return result("do_not_recommend", "Minimum-order check cannot pass: the document does not state a minimum order.")
    if "minimum order" in conflicts:
        return result("do_not_recommend", f"Minimum-order check fails: the document states conflicting minimum orders {mins}.")
    if min_order > MAX_MIN_ORDER:
        return result("do_not_recommend", f"Minimum-order check fails: {min_order} units is more than the {MAX_MIN_ORDER}-unit limit.")
    return result("recommend", f"All four checks pass: {vendor} is approved, ${price:.2f} is within the ${max_cost:.2f} max for {sku}, "
                               f"{lead} days is within {MAX_LEAD_DAYS}, and {min_order} units is within {MAX_MIN_ORDER}.")
