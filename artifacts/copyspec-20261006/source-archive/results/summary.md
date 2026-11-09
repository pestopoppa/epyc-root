# Phase-1 copy-speculation eval summary (full-host window)

Generated 2026-10-06 05:18:30. Greedy (temp 0, top_k 1), max_tokens 512, distinct prompts, one request each per arm, server restarted between arms, cache_prompt=false, cache-ram 0.
Arm order P, NM, NO, P2. P2 = repeat of P (noise floor). NO (ngram-mod alone) is a draft-only CONTROL, not a candidate.
acceptance = sum(draft_n_accepted)/sum(draft_n) over requests (alarm if exactly 1.000).
identity = byte-equal text vs P for the same prompt id; P2 vs P is the identity noise floor.

## Acceptance and identity

| class | arm | n | draft_n | accepted | acceptance | identical vs P | first-diverge (median char) | ngram-supplied reqs |
|---|---|---|---|---|---|---|---|---|
| debugbench | P | 40 | 14366 | 10027 | 0.698 | (ref) | - | - |
| debugbench | NM | 40 | 14581 | 9972 | 0.684 | 40/40 | - | 40 |
| debugbench | NO | 40 | 3731 | 3417 | 0.916 | 16/40 | 252 | 39 |
| debugbench | P2 | 40 | 14366 | 10027 | 0.698 | 40/40 | - | - |
| hotpotqa | P | 25 | 2060 | 1709 | 0.830 | (ref) | - | - |
| hotpotqa | NM | 25 | 2136 | 1687 | 0.790 | 25/25 | - | 21 |
| hotpotqa | NO | 25 | 804 | 717 | 0.892 | 17/25 | 100 | 21 |
| hotpotqa | P2 | 25 | 2060 | 1709 | 0.830 | 25/25 | - | - |
| general | P | 20 | 80 | 80 | 1.000 ALARM | (ref) | - | - |
| general | NM | 20 | 80 | 80 | 1.000 ALARM | 20/20 | - | 0 |
| general | NO | 20 | 0 | 0 | n/a | 20/20 | - | 0 |
| general | P2 | 20 | 80 | 80 | 1.000 ALARM | 20/20 | - | - |
| ALL | P | 85 | 16506 | 11816 | 0.716 | (ref) | - | - |
| ALL | NM | 85 | 16797 | 11739 | 0.699 | 85/85 | - | 61 |
| ALL | NO | 85 | 4535 | 4134 | 0.912 | 53/85 | 219 | 60 |
| ALL | P2 | 85 | 16506 | 11816 | 0.716 | 85/85 | - | - |

## Speed (full host, 96 threads): P vs NM only, against the |P - P2| floor

Mean timings.predicted_per_second per class. delta = NM vs mean(P,P2). floor = |P-P2|/mean(P,P2). A delta is only a signal if |delta| > floor; arm NO is excluded from speed (control).

| class | P tok/s | P2 tok/s | NM tok/s | floor % | NM delta % | verdict |
|---|---|---|---|---|---|---|
| debugbench | 56.72 | 56.50 | 59.58 | 0.40 | +5.25 | NM faster |
| hotpotqa | 57.86 | 57.60 | 58.22 | 0.46 | +0.84 | NM faster |
| general | 27.51 | 27.81 | 27.97 | 1.11 | +1.11 | NM faster |
| ALL | 50.18 | 50.07 | 51.74 | 0.22 | +3.22 | NM faster |

## Arm-level ngram impl stats (last 'statistics' lines seen in each server log)

- P: {"draft-mtp": {"gen_drafts": 4132, "acc_drafts": 3664, "gen_tokens": 16506, "acc_tokens": 11816}}
- NM: {"ngram-mod": {"gen_drafts": 1037, "acc_drafts": 955, "gen_tokens": 4148, "acc_tokens": 3553}, "draft-mtp": {"gen_drafts": 3168, "acc_drafts": 2709, "gen_tokens": 12649, "acc_tokens": 8186}}
- NO: {"ngram-mod": {"gen_drafts": 1135, "acc_drafts": 1135, "gen_tokens": 4535, "acc_tokens": 4134}}
- P2: {"draft-mtp": {"gen_drafts": 4132, "acc_drafts": 3664, "gen_tokens": 16506, "acc_tokens": 11816}}

Note: draft_n/draft_n_accepted are totals over ALL impls that won a round (ngram or MTP); ngram-supplied counts come from the per-impl '#gen drafts' counter in the verbosity-4 log.
