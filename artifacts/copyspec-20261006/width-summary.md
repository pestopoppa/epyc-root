# Width A/B summary (per-impl ngram draft width)

NOTE: this run overlapped a GPU VRAM-attribution job (no --gpu-quiet taken), so its speeds are paired-only (P vs P2 floor, same window); no absolute claims.

Generated 2026-10-06 06:15:37. Greedy (temp 0, top_k 1), max_tokens 512, distinct prompts, one request each per arm, server restarted between arms, cache_prompt=false, cache-ram 0.
Arm order P (production binary), W8 (experimental, ngram n-max 8), W16 (n-max 16), P2 (repeat of P, noise floor).
acceptance = sum(draft_n_accepted)/sum(draft_n) over requests (alarm if exactly 1.000).
identity = byte-equal text vs P for the same prompt id; P2 vs P is the identity noise floor.

## Acceptance and identity

| class | arm | n | draft_n | accepted | acceptance | identical vs P | first-diverge (median char) | ngram-supplied reqs | mean accepted len / ngram draft | mean gen len / ngram draft |
|---|---|---|---|---|---|---|---|---|---|---|
| debugbench | P | 40 | 14358 | 10029 | 0.698 | (ref) | - | - | - | - |
| debugbench | W8 | 40 | 15257 | 10345 | 0.678 | 40/40 | - | 40 | 6.47 | 8.00 |
| debugbench | W16 | 40 | 16427 | 10547 | 0.642 | 40/40 | - | 40 | 10.72 | 15.95 |
| debugbench | P2 | 40 | 14358 | 10029 | 0.698 | 40/40 | - | - | - | - |
| hotpotqa | P | 25 | 2060 | 1709 | 0.830 | (ref) | - | - | - | - |
| hotpotqa | W8 | 25 | 2316 | 1758 | 0.759 | 25/25 | - | 21 | 5.65 | 8.00 |
| hotpotqa | W16 | 25 | 2652 | 1789 | 0.675 | 25/25 | - | 21 | 8.88 | 16.00 |
| hotpotqa | P2 | 25 | 2060 | 1709 | 0.830 | 25/25 | - | - | - | - |
| ALL | P | 65 | 16418 | 11738 | 0.715 | (ref) | - | - | - | - |
| ALL | W8 | 65 | 17573 | 12103 | 0.689 | 65/65 | - | 61 | 6.33 | 8.00 |
| ALL | W16 | 65 | 19079 | 12336 | 0.647 | 65/65 | - | 61 | 10.38 | 15.96 |
| ALL | P2 | 65 | 16418 | 11738 | 0.715 | 65/65 | - | - | - | - |

## Speed (paired-only; GPU job overlapped): W8/W16 vs P, against the |P - P2| floor

Mean timings.predicted_per_second per class. delta = arm vs mean(P,P2). floor = |P-P2|/mean(P,P2). A delta is only a signal if |delta| > floor.

| class | P tok/s | P2 tok/s | W8 tok/s | W8 delta % | W16 tok/s | W16 delta % | floor % | verdict W8 / W16 |
|---|---|---|---|---|---|---|---|---|
| debugbench | 54.78 | 56.60 | 63.52 | +14.06 | 67.11 | +20.50 | 3.26 | faster / faster |
| hotpotqa | 57.12 | 57.13 | 58.74 | +2.83 | 58.00 | +1.53 | 0.02 | faster / faster |
| ALL | 55.68 | 56.80 | 61.68 | +9.67 | 63.61 | +13.09 | 1.99 | faster / faster |

## Arm-level ngram impl stats (last 'statistics' lines seen in each server log)

- P: {"draft-mtp": {"gen_drafts": 4110, "acc_drafts": 3643, "gen_tokens": 16418, "acc_tokens": 11738}}
- W8: {"ngram-mod": {"gen_drafts": 643, "acc_drafts": 643, "gen_tokens": 5144, "acc_tokens": 4067}, "draft-mtp": {"gen_drafts": 3113, "acc_drafts": 2673, "gen_tokens": 12429, "acc_tokens": 8036}}
- W16: {"ngram-mod": {"gen_drafts": 419, "acc_drafts": 419, "gen_tokens": 6687, "acc_tokens": 4349}, "draft-mtp": {"gen_drafts": 3104, "acc_drafts": 2660, "gen_tokens": 12392, "acc_tokens": 7987}}
- P2: {"draft-mtp": {"gen_drafts": 4110, "acc_drafts": 3643, "gen_tokens": 16418, "acc_tokens": 11738}}

Note: draft_n/draft_n_accepted are totals over ALL impls that won a round (ngram or MTP); ngram-supplied counts come from the per-impl '#gen drafts' counter in the verbosity-4 log.
