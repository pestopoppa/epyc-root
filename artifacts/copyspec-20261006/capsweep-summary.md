# Ngram draft-cap sweep (trimmed), CPU frontdoor (35B-A3B-MTP Q8_0)

Trimmed EC window: arms P W32 W64 P2, debugbench 40 + prose 15, no hotpotqa. Full host 0-95, gpu-quiet shared, single outer hold.

Generated 2026-10-06 07:49:59. Greedy (temp 0, top_k 1), max_tokens 512, distinct prompts (debugbench 40, prose 15), one request each per arm, server restarted between arms, cache_prompt=false.
Arm order: P W32 W64 P2 (P2 = repeat of P, noise floor). Caps: {"W32": 32, "W64": 64}.
acceptance = sum(draft_n_accepted)/sum(draft_n) over requests (alarm if exactly 1.000).
identity = byte-equal text vs P for the same prompt id; P2 vs P is the identity noise floor.

## Acceptance and identity

| class | arm | n | draft_n | accepted | acceptance | identical vs P | first-diverge (median char) | ngram-supplied reqs | mean accepted len / ngram draft | mean gen len / ngram draft |
|---|---|---|---|---|---|---|---|---|---|---|
| debugbench | P | 40 | 14379 | 10021 | 0.697 | (ref) | - | - | - | - |
| debugbench | W32 | 40 | 18534 | 10639 | 0.574 | 40/40 | - | 40 | 15.74 | 31.80 |
| debugbench | W64 | 40 | 22776 | 10682 | 0.469 | 40/40 | - | 40 | 20.06 | 62.63 |
| debugbench | P2 | 40 | 14379 | 10021 | 0.697 | 40/40 | - | - | - | - |
| prose | P | 15 | 9421 | 3643 | 0.387 | (ref) | - | - | - | - |
| prose | W32 | 15 | 9465 | 3653 | 0.386 | 15/15 | - | 1 | 22.00 | 32.00 |
| prose | W64 | 15 | 9497 | 3654 | 0.385 | 15/15 | - | 1 | 33.50 | 64.00 |
| prose | P2 | 15 | 9421 | 3643 | 0.387 | 15/15 | - | - | - | - |
| ALL | P | 55 | 23800 | 13664 | 0.574 | (ref) | - | - | - | - |
| ALL | W32 | 55 | 27999 | 14292 | 0.510 | 55/55 | - | 41 | 15.82 | 31.80 |
| ALL | W64 | 55 | 32273 | 14336 | 0.444 | 55/55 | - | 41 | 20.20 | 62.64 |
| ALL | P2 | 55 | 23800 | 13664 | 0.574 | 55/55 | - | - | - | - |

## Mean accepted ngram draft length versus cap (ALL classes, then per class)

cap = --spec-ngram-mod-n-max. gen/cap = mean generated ngram draft length over the cap (1.0 = every draft saturates the cap); acc/gen = fraction of generated ngram tokens accepted. Rising mean accepted length with cap = width is being used.

| arm | cap | class | ngram drafts | mean gen len | mean accepted len | gen/cap | acc/gen |
|---|---|---|---|---|---|---|---|
| W32 | 32 | ALL | 239 | 31.80 | 15.82 | 0.99 | 0.50 |
| W32 | 32 | debugbench | 236 | 31.80 | 15.74 | 0.99 | 0.49 |
| W32 | 32 | prose | 3 | 32.00 | 22.00 | 1.00 | 0.69 |
| W64 | 64 | ALL | 189 | 62.64 | 20.20 | 0.98 | 0.32 |
| W64 | 64 | debugbench | 187 | 62.63 | 20.06 | 0.98 | 0.32 |
| W64 | 64 | prose | 2 | 64.00 | 33.50 | 1.00 | 0.52 |

## Speed (paired-only): each non-P arm vs the |P - P2| floor

Mean timings.predicted_per_second per class. delta = arm vs mean(P,P2). floor = |P-P2|/mean(P,P2). A delta is only a signal if |delta| > floor.

| class | arm | tok/s | delta % vs mean(P,P2) | floor % | verdict |
|---|---|---|---|---|---|
| debugbench | W32 | 68.18 | +20.66 | 0.11 | faster |
| debugbench | W64 | 64.45 | +14.07 | 0.11 | faster |
| prose | W32 | 36.70 | +1.73 | 0.16 | faster |
| prose | W64 | 36.78 | +1.94 | 0.16 | faster |
| ALL | W32 | 59.59 | +17.01 | 0.12 | faster |
| ALL | W64 | 56.91 | +11.73 | 0.12 | faster |

## Arm-level impl stats (last 'statistics' lines seen in each server log)

- P: {"draft-mtp": {"gen_drafts": 5960, "acc_drafts": 4877, "gen_tokens": 23800, "acc_tokens": 13664}}
- W32: {"ngram-mod": {"gen_drafts": 239, "acc_drafts": 239, "gen_tokens": 7601, "acc_tokens": 3780}, "draft-mtp": {"gen_drafts": 5110, "acc_drafts": 4034, "gen_tokens": 20398, "acc_tokens": 10512}}
- W64: {"ngram-mod": {"gen_drafts": 189, "acc_drafts": 189, "gen_tokens": 11839, "acc_tokens": 3818}, "draft-mtp": {"gen_drafts": 5119, "acc_drafts": 4043, "gen_tokens": 20434, "acc_tokens": 10518}}
- P2: {"draft-mtp": {"gen_drafts": 5960, "acc_drafts": 4877, "gen_tokens": 23800, "acc_tokens": 13664}}

Note: draft_n/draft_n_accepted are totals over ALL impls that won a round; ngram-supplied counts come from the per-impl '#gen drafts' counter in the verbosity-4 log.
