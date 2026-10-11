# HW6: Campus Customs Vendor Desk Agent

A PydanticAI agent that reads one vendor document (an HTML quote, PDF, or `.eml` email), pulls out the vendor, SKU, unit price, lead time, and minimum order, and recommends **recommend** or **do_not_recommend** by following `data/shop_handbook.md`. This homework measures and cuts the agent's cost (prompt caching) and attacks and defends it against booby-trapped vendor documents.

Every AI call uses **only `gpt-6-luna`** through Portkey. The agent checks every response and stops the run if any other model answers.

**Start here:** open `output/hw6_report.html` (double-click; it works offline) for the full results page.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then put your real PORTKEY_API_KEY in .env
```

`.env` can sit in this folder or any parent folder. It is in `.gitignore` and never committed.

## Run the agent

```bash
python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

This runs the **final defended agent** (all three defense layers, with the handbook cached) on one document. It prints the answer and token counts, and appends to:
- `output/usage_log.json`: tokens and dollar cost
- `output/audit_trail.json`: every tool call and the final answer
- `output/trap_calls.json`: only written if something tries to email or pay. It should stay `[]`.

Options:

| Flag | Meaning |
|---|---|
| `--defenses none` | The original Problem 3 agent, with no defenses (used for the attack tests) |
| `--defenses code,design,prompt` | Any mix of the three defense layers (default: all) |
| `--cache off` | No cache reuse: every call gets a unique prefix (Problem 4) |

`send_email` and `approve_payment` never send or pay anything. They only log to `output/trap_calls.json`, and with the design layer on they refuse without a human sign-off.

## Reproduce each problem

| Problem | Command | Output |
|---|---|---|
| 2 Size up the handbook | `python scripts/handbook_estimate.py` | `output/handbook_estimate.md` |
| 3 Build the agent | `python agent.py --doc data/practice_docs/p08_chapelst_email.eml --defenses none` | `output/harness.md` |
| 4 With and without cache | `python scripts/cache_test.py` | `output/cache_test.json`, `.md` |
| 5 Attack your own agent | `python scripts/attack_test.py` | `output/attack_results.json`, `.md` |
| 6 Defend your agent | `python scripts/defense_test.py` and `python scripts/probe_test.py` | `output/defense_results.json`, `.md` |
| 7 Red team | `python scripts/make_attacks.py` and `python scripts/red_team_test.py` | `data/my_attacks/`, `output/red_team.md` |
| 8 Exam documents | `python scripts/exam_run.py` | `output/exam_results.json` |
| 9 Results page | `python scripts/build_report.py` | `output/hw6_report.html` |

## Layout

- **Agent:** `agent.py` (entry point), `tools.py` (reader and trap tools), `models.py` (answer types), `prompts/prompt.md` (instructions and safety rules)
- **Defense layers:** `safety.py` (code layer: keep only visible text), `rules.py` (design layer: handbook checks in Python), `prompts/extract.md` (the tool-less extractor), `prompts/prompt_baseline.md` (the undefended Problem 3 prompt)
- **Data:** `data/` holds the course data (handbook, prices, 12 practice documents with their key, 10 exam documents), `data/my_attacks/` (my two red-team documents and their key), and `data/layer_probes/` (4 probes used to compare the defense layers)
- **Results:** `output/` holds every result file and write-up. `output/human_view/` shows the documents the way a person sees them.
- **Prompt log:** `AI_prompts.md`
