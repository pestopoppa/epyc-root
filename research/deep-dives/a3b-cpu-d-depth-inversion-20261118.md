# A3B CPU 48t MTP depth inversion (D=2 vs D=4, 4k vs 32k) — offline analysis, 2026-11-18

Source: `/mnt/raid0/llm/tmp/rka-verify-tile-a3b48-e2e-20261117/out/results.jsonl` (rounds 1-3 full, r4 D3/D4 only; 4 prompts per depth per cell; same prompts every cell), `/mnt/raid0/llm/tmp/rka-verify-tile-cpu-20261117/out/results.jsonl` (isolated verify cost). Offline only; no runs.

## Answer in one paragraph

The headline "D=2 is 2x faster than D=4 at 4k" is not a depth-dependent verify cost. It is a measurement-quality artifact: the same (D, depth, prompt) cell varies by up to 2x across rounds, in a bimodal way (about 24 ms/token fast mode, about 50 ms/token slow mode). Round 1 is flat at 4k (D2 22-25, D3 23-27, D4 25-29 ms/token). The slow mode hits D3/D4 4k in rounds 2-4 and D2 32k in rounds 2-3, while D2 4k stayed fast in every round. The only real structural effect is the verify-cost step at n 3->4 at 32k, which explains why D3 is the worst arm at 32k. On the least-contaminated view (best round per prompt), D=2 beats D=4 by about 14% at 4k and about 10% at 32k. The row's verdict (NO_RECOMMENDATION) is right under its rule, but the evidence neither supports depth-adaptive D nor shows D=4 is better anywhere.

## (1) Decomposition

Steps = draft_n / D (one draft call set per verify step); tokens per step = 256 / steps; ms/step = ms/token x tokens/step. Mean over the 4 prompts, taking each prompt's best round (the least contended observation):

| D | depth | ms/token | tok/step | ms/step | isolated verify n=D+1 (tile-cpu, a3b48) | residual (draft + sampling + overhead) |
|---|---|---|---|---|---|---|
| 2 | 4k | 23.4 | 2.37 | 55.5 | 49.5 | ~6 |
| 3 | 4k | 25.6 | 2.75 | 70.2 | 56.5 | ~14 |
| 4 | 4k | 27.2 | 3.00 | 81.3 | 64.4 | ~17 |
| 2 | 32k | 42.1 | 2.38 | 99.8 | 91.0 | ~9 |
| 3 | 32k | 54.9 | 2.79 | 152.7 | 147.9 | ~5 |
| 4 | 32k | 46.6 | 3.01 | 139.9 | 148.8 | about 0 (within noise) |

Isolated a3b48 verify cost (median ms, depth 4096): n=1..5 = 35.7, 41.9, 49.5, 56.5, 64.4 (smooth, about +7 ms/token, no step). Depth 32768: n=1..7 = 88.4, 88.7, 91.0, **147.9**, 148.8, 155.3, 192.0 (step +63% at n 3->4, another +24% at n 6->7).

- Draft cost: residual grows about 3 ms per extra drafted token at 4k (6, 14, 17), so drafting is cheap and roughly linear. At 32k the residual is within noise of zero; do not read a draft cost off it.
- Verify cost: smooth at 4k, step at n 3->4 at 32k. Acceptance per drafted token is 0.68 / 0.58 / 0.50 for D2/D3/D4 (identical at both depths, per-prompt values repeat exactly across rounds, so acceptance is deterministic and not the cause).
- Clean-mode ms/token ranking: 4k D2 < D3 < D4 (gaps 9% and 6%); 32k D2 < D4 < D3. D3 pays the full n=4 step (148 ms) but gets only 2.79 tok/step, D4 pays the same step and gets 3.01. D2 sits below the step (n=3). That is the 32k ordering, and it is consistent with the verify-tile step being real.

Per-round spread (ms/token, 4 prompts each):

- Round 1 (clean): 4k D2 22.3-27.0, D3 22.7-27.4, D4 25.4-28.8; 32k D2 39-47, D3 51-60, D4 43-52.
- Round 2: D2 4k 23.5-24.4 (fast); D4 4k 46-54 and D3 4k 25.8, 51, 47, 52 (slow, bimodal inside one cell: first prompt fast, rest slow); D2 32k 44.9, 44.3, **75, 73**; D4 32k 49 / 74 / 92 / 53.
- Round 3: D4 4k 46-54, D2 4k 23-26, D3 4k 26.8 then 44-51; D2 32k 61-78, D3 32k 68-90.
- Round 4: D4 4k 40-58, D3 4k 44-51; 32k 57-91.
- The slow cells are about 2x. A 2x jump that appears mid-cell, hits some arms and not others at the same depth, and is absent in round 1 is not what a deterministic kernel step looks like (that would reproduce in every round and for every prompt). 4k is not special; it is where the contaminated cells happened to land on D3/D4 while D2 4k was spared. At 32k D2 was contaminated in r2-r3, which is why the median says "D2 slower at 32k by 17-23% in every round" while best-round says D2 faster by 10%.
- Mechanism for the 2x: not proven here. A host with the other half active (shared-box rows, 48t barrier-synchronised ggml threads) loses a whole step when one thread is preempted or a foreign job shares an L3/memory node. I did not sample foreign load during the runs (no per-cell loadavg was recorded), so contention is the leading explanation, not a measured one.

## (2) Earlier rows

- `rka-verify-tile-cpu-20261117` explains the 32k side only: the +63% step at n 3->4 (91 -> 148 ms) is real and reproduced by the e2e D3 ms/step (152.7 vs 148). It predicted D2 about 39% cheaper per step at 32k; end to end, with D2's lower acceptance (2.38 vs 3.01 tok/step), the gain is about 10%, not 39%, in the clean view. It shows no step at 4k, so it cannot explain a 2x at 4k.
- `/mnt/raid0/llm/tmp/*/spec.json` with a3b: the A3B rows found are DF2/INF-85/AGG/GPU rows (`rka-verify-tile-a3b-gpu-e2e-20261118`, `rka-a3b-gpu-d-np-sweep-20261118`, `rka-a3b-n4-step-gpu-20261118`); none measures CPU 48t MTP depth. The GPU e2e (D2 9.89 / D4 11.87 ms/token at 32k, D2 9.36 / D4 11.86 at 4k, three rounds, no invalid cells) shows D2 about 17-21% faster at both depths, matching the sign and rough size of the clean CPU view (10-14%), and shows no 4k-vs-32k inversion. The GPU n 3->4 step (RKA-A3B-N4-STEP) is the same shape of effect as the CPU 32k step but is a different kernel mechanism.

## (3) Production implications

- Production frontdoor A3B: `draft_max: 4`, `n_ctx: 262144`, `--ctx-checkpoints 32` (`/workspace/repos/epyc-orchestrator/orchestration/model_registry.yaml`, frontdoor block); one 96t full instance plus two 48t halves; halves serve concurrent traffic. A typical prompt-size distribution for the CPU frontdoor was not findable in the orchestrator configs (only `stage1_context_limit: 20000` and the 8192 default `context_length`; long-context ingest moved to the GPU 27B). So I cannot weight 4k vs 32k traffic. Interactive frontdoor chat is most likely short (4k and under), which is the regime where the clean data favours D=2.
- The 96t instance is a different curve (a3b96 step at n 6->7, D=4 aligned); nothing here applies to it.
- Depth-adaptive D is not justified: the clean data say D2 wins at both depths, so adaptivity would only be a hedge against the contaminated 32k median (D2 +17-23% there). Estimated gain if D=2 holds at both depths: about 10-14% ms/token on the halves, versus a risk of -17..-23% at 32k if the slow-mode data were the truth. That spread is too large to act on with this data.

## Recommendation

**Targeted re-measure, not a recipe change, no depth-adaptive D yet.** Keep D=4 (operator-owned recipe) until a contention-controlled row answers whether D=2 wins at both depths. Draft (NOT PUBLISHED): `/mnt/raid0/llm/tmp/a3b-cpu-d-depth-followup-20261118/spec.draft.json`. Design: D in {2,4} only (D3 is dominated at both depths in the clean view), depths 4k/16k/32k, ABBA, fresh server per cell, plus foreign-CPU busy% and loadavg sampled during decode so a slow-mode cell is labelled rather than averaged in; cells with p95 foreign busy >= 25% are excluded; RECOMMEND_D2 needs >= 5% gain at both 4k and 32k with CI lower bound > 0 in every valid round. Estimate ~9000 s on the CPU half. If it confirms, the operator-level change is D=2 uniformly (as already done for the GPU tenant), and the depth-adaptive variant is only worth building if 32k comes out D4-favoured.

Caveat on this analysis: best-of-rounds is optimistic by construction (it picks the minimum of noisy cells for every arm, which favours arms with more rounds; D4 r4 is missing, D3 has 3 rounds, D2 has 3). It is a bound on what clean conditions look like, not a measurement of them.
