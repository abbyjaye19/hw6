# Handbook Token & Cost Estimate (Problem 2)

## 1. Token count: **10,058 tokens**

**How I got it:**

1. I read `data/shop_handbook.md` as UTF-8 text: 28,903 characters and 6,127 words.
2. I tokenized it with OpenAI's `tiktoken` library using the **`o200k_base`** encoding. That is the tokenizer used by OpenAI's current GPT model family, which gpt-6-luna belongs to. Result: **10,058 tokens**.
3. Sanity checks:
   - The older `cl100k_base` encoding gives 10,184 tokens, about 1% more.
   - The "about 4 characters per token" rule of thumb gives 28,903 / 4 ≈ 7,226 tokens. That undercounts because the handbook is full of tables, SKUs and numbers, which split into more tokens than plain prose.
   - The assignment says the handbook is "about 10,000 tokens". That matches.

Reproduce with `python scripts/handbook_estimate.py`.

> Caveat: gpt-6-luna's exact tokenizer isn't published, so 10,058 is an estimate. Problem 4 checks it against the `input_tokens` that the API actually reports. Real calls will also show a few extra tokens for message formatting, plus whatever system instructions and vendor document sit next to the handbook.

## 2. Prices used (`data/prices.json`, gpt-6-luna, $ per 1M tokens)

| Token type | Price per 1M | Price per token |
|---|---|---|
| Input (uncached) | $0.10 | $0.0000001 |
| Cached input (cache hit) | $0.01 | $0.00000001 |
| Cache write | $0.125 | $0.000000125 |
| Output | $0.50 | *(not relevant: the handbook is input only)* |

## 3. What the handbook alone costs

### Without caching

Every call pays the full input price for all 10,058 tokens.

- **One call:** 10,058 × $0.10 / 1,000,000 = **$0.0010058** (about 0.1¢)
- **1,000 calls:** 1,000 × $0.0010058 = **$1.0058** (about $1.01)

### With caching

The first call writes the handbook into the cache at the cache-write price. Each later call that reuses the same handbook prefix is a cache hit and pays the cached-input price.

- **One call, first time (cache write):** 10,058 × $0.125 / 1,000,000 = **$0.0012573**. This is about 25% *more* than uncached, because writing the cache costs extra.
- **One call, already cached (cache hit):** 10,058 × $0.01 / 1,000,000 = **$0.0001006**. That's 10× cheaper than uncached.
- **1,000 calls (1 write + 999 hits):**
  - Write: 1 × $0.0012573 = $0.0012573
  - Hits: 999 × $0.0001006 (exactly $0.00010058) = $0.1004794
  - **Total = $0.1017** (about 10¢)

### Summary

| Scenario | 1 call | 1,000 calls |
|---|---|---|
| No caching | $0.0010058 | **$1.0058** |
| With caching | $0.0012573 (first call, write) / $0.0001006 (hit) | **$0.1017** |
| **Savings from caching** | n/a | **$0.904 (≈ 89.9% cheaper)** |

## 4. Assumptions that Problem 4 will test

- **The handbook has to be an identical prefix.** Caching only works if the handbook comes first in every request and doesn't change. The vendor document has to go *after* it. If anything that varies sits before the handbook, every call is a cache miss.
- **The cache has to stay warm.** Cached prefixes expire after a few minutes of no use. If calls are spread out, some calls become fresh writes again, so the real 1,000-call cost lands somewhere between $0.10 and $1.01.
- **The cache may be all-or-nothing.** If the provider only caches part of the prefix (for example, in fixed-size blocks), a few handbook tokens may still be billed at the full price on a hit.
- **This counts the handbook only.** The vendor document, the instructions and the output tokens (at $0.50/1M, 5× the input price) are extra. Problem 4 measures the full bill.
