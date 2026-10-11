"""Problem 4: run all 12 practice documents with cache off, then with cache on.

Saves every model call to output/cache_test.json and prints a summary.
Run from the HW6 folder:  python scripts/cache_test.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HW_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW_ROOT))

from agent import OUTPUT_DIR, parse_defenses, run  # noqa: E402

DOCS = sorted((HW_ROOT / "data" / "practice_docs").iterdir())
KEY = {k["file"]: k for k in json.loads((HW_ROOT / "data" / "practice_key.json").read_text(encoding="utf-8"))}
FIELDS = ["vendor", "sku", "unit_price", "lead_time_days", "min_order", "decision"]
OUT = OUTPUT_DIR / "cache_test.json"


def main() -> None:
    calls: list[dict] = []
    # Cache off first, so the "off" runs cannot benefit from anything the "on" runs wrote.
    for setup, cache in (("without_cache", False), ("with_cache", True)):
        for doc in DOCS:
            rel = doc.relative_to(HW_ROOT).as_posix()
            answer, tokens = run(rel, cache=cache, defenses=parse_defenses("none"))  # the Problem 3 agent
            key = KEY[doc.name]
            correct = {f: getattr(answer, f) == key[f] for f in FIELDS}
            for c in tokens["calls"]:
                calls.append({"setup": setup, "document": doc.name, **c,
                              "answer_fields_correct": sum(correct.values()) if c is tokens["calls"][-1] else None})
            run_cost = sum(c["cost_usd"]["total"] for c in tokens["calls"])
            print(f"{setup:14} {doc.name:30} in={tokens['input_tokens']:6} cached={tokens['cached_input_tokens']:6} "
                  f"write={tokens['cache_write_tokens']:6} out={tokens['output_tokens']:4} "
                  f"${run_cost:.6f}  correct {sum(correct.values())}/6  {answer.decision}")
            OUT.write_text(json.dumps(calls, indent=2), encoding="utf-8")  # save as we go

    # Hard check: a without-cache run that shows cached tokens does not count.
    leaked = [c for c in calls if c["setup"] == "without_cache" and c["cached_input_tokens"]]
    print("\nwithout_cache calls with cached tokens:", len(leaked))


if __name__ == "__main__":
    main()
