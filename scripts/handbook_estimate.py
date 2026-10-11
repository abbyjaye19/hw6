"""Problem 2: count handbook tokens and estimate what the handbook alone costs per call."""

import json
from pathlib import Path

import tiktoken

HW_ROOT = Path(__file__).resolve().parent.parent
HANDBOOK = HW_ROOT / "data" / "shop_handbook.md"
PRICES = HW_ROOT / "data" / "prices.json"

text = HANDBOOK.read_text(encoding="utf-8")
prices = json.loads(PRICES.read_text(encoding="utf-8"))["gpt-6-luna"]

# o200k_base is the tokenizer used by OpenAI's current GPT models.
tokens = len(tiktoken.get_encoding("o200k_base").encode(text))
print(f"characters: {len(text):,}  words: {len(text.split()):,}  tokens (o200k_base): {tokens:,}")

per_m = 1_000_000
uncached = tokens * prices["input_per_1m"] / per_m
write = tokens * prices["cache_write_per_1m"] / per_m
read = tokens * prices["cached_input_per_1m"] / per_m

print(f"1 call, no cache:          ${uncached:.7f}")
print(f"1 call, cache write:       ${write:.7f}")
print(f"1 call, cache hit:         ${read:.7f}")
print(f"1000 calls, no cache:      ${uncached * 1000:.4f}")
print(f"1000 calls, cached (1w+999r): ${write + 999 * read:.4f}")
