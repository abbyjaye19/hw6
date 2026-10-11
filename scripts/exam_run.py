"""Problem 8: run the final defended agent (all three layers, cache on) on every exam document.

Writes output/exam_results.json straight from the agent's output, with no hand edits.
Run from the HW6 folder:  python scripts/exam_run.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HW_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW_ROOT))

from agent import OUTPUT_DIR, run  # noqa: E402
from tools import LAYERS, TRAP_LOG  # noqa: E402

EXAM_DIR = HW_ROOT / "data" / "exam_docs"


def trap_entries() -> list[dict]:
    return json.loads(TRAP_LOG.read_text(encoding="utf-8")) if TRAP_LOG.exists() else []


def main() -> None:
    results = []
    for doc in sorted(EXAM_DIR.iterdir()):
        before = len(trap_entries())
        answer, tokens = run(doc.relative_to(HW_ROOT).as_posix(), cache=True, defenses=LAYERS)
        trap_called = len(trap_entries()) > before
        results.append({
            "file": doc.name,
            "vendor": answer.vendor,
            "sku": answer.sku,
            "unit_price": answer.unit_price,
            "lead_time_days": answer.lead_time_days,
            "min_order": answer.min_order,
            "decision": answer.decision,
            "reason": answer.reason,
            "trap_tool_called": trap_called,
            "input_tokens": tokens["input_tokens"],
            "cached_tokens": tokens["cached_input_tokens"],
            "output_tokens": tokens["output_tokens"],
            "cost_usd": tokens["cost_usd"]["total"],
        })
        print(f"{doc.name:16} {answer.vendor:26} {answer.sku} {answer.unit_price} {answer.lead_time_days} "
              f"{answer.min_order} {answer.decision:17} trap={trap_called} ${tokens['cost_usd']['total']:.6f}")
        print(f"                 {answer.reason}")
        if answer.flags:
            print(f"                 flags: {answer.flags}")
    (OUTPUT_DIR / "exam_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote output/exam_results.json ({len(results)} entries); total ${sum(r['cost_usd'] for r in results):.6f}")


if __name__ == "__main__":
    main()
