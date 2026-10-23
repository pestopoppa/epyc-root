# HSF-4 results, source-rate sub-term and log re-run (2026-10-23, workspace-f8)

Task: `handoffs/active/heterogeneous-slot-fabric-residency.md` HSF-4 (reload-vs-re-prefill crossover per lineup model;
per-role uncached-prompt-length histogram with alpha(B) and the ceiling alpha(B)*(1 - 1/rho)). The analytic half (2026-10-20)
and the llama-server-log half (2026-10-21) are already in the handoff. This pass adds (a) the source-rate sub-term
from today's KPF-18-S1 remainder step 7 and (b) the serving_call.v1 / dispatch.v1 re-run the handoff left open.
No inference was run; step 7 is a recorded measurement from earlier today.

## Headline

- **Source rates are now measured, but only as GRAPHS-DISABLED values** (see the labelled section). For the 27B on the
  production-shaped :8083 argv at L = 8000 / 16000 / 32000 tokens: tmpfs restore 8.26 / 9.27 / 6.15 GB/s, cold-disk
  restore 4.12 / 4.10 / 3.06 GB/s, tmpfs save 3.06 / 3.09 / 2.89 GB/s, disk save 1.59 / 1.73 / 0.80 GB/s.
- **Restore versus re-prefill, 27B (copy-and-apply only):** restoring the slot file takes 52.7 / 77.1 / 206.8 ms from tmpfs
  and 105.6 / 174.2 / 416.2 ms from cold disk, against measured re-prefill of 10.9 / 23.2 / 51.6 s (n = 0 idle control,
  1.3659 / 1.4514 / 1.6132 ms/token, graphs ON). That is 207 / 301 / 250 x (tmpfs) and 103 / 133 / 124 x (cold disk).
  Crossover prefix length (restore cheaper than re-prefill above it): about 14 tokens from tmpfs, 28 from cold disk
  (fixed 150 MiB recurrent-state restore, 19 ms or 38 ms, over a re-prefill cost of about 1.36 ms/token). The analytic
  "~6 tokens" used the 28.9 GB/s H2D plateau only; the measured source path makes it 14 to 28.
- **This does not rehabilitate the 60-820x line.** The HSF-LB1 correction stands: the measured end-to-end ON-arm pre-eval
  stall is 43.5 s (median, 20-29k cached tokens, 15 turns, one rep). Step 7's largest single transfer is 1.58 s (32k-token
  disk save), 27 x smaller than that stall, so a single save or restore cannot explain it; attribution stays with
  UFH14-LB7. Step 7 prices one clean transfer, not a stall.
- **Done: NO.** Not ticked. Remaining: the rates are graphs-off (KPF-18-S1.7g is the open decision and was not touched),
  the serving_call.v1 / dispatch.v1 per-role histogram has no usable sample (below), and the placement KV-recovery term
  still needs the end-to-end restore cost from LB7. A dated note was written.

## (a) Source-rate table, GRAPHS DISABLED

LABEL: **every rate and ms value below was measured with `GGML_CUDA_DISABLE_GRAPHS=1`** (KPF-18-S1 remainder PREDECLARATION
amendment 2026-10-23T13:25Z, GPU-LEAK-1). Not the production condition. Do not quote them as the production rate.
Source: `VERDICT.json` `items.step7_hsf`, status `MEASURED` (n >= 3 valid in every mode at every L; hot disk restore n = 1).
Unit: GB/s = 1e9 bytes/s, ms medians of 3. Model: Qwen3.8-27B-Q8_0, fork build `gpu-20261020-a1f0c8cf9`, `-np 4 -b/-ub 512
--kv-unified --cache-ram 65536 --no-cache-idle-slots`, host threads 184-191.

| L (tokens) | slot-file bytes | tmpfs save ms (GB/s) | tmpfs restore ms (GB/s) | disk save ms (GB/s) | cold-disk restore ms (GB/s) | derived disk-only read (GB/s) | --cache-ram save stall ms | --cache-ram load stall ms (raw GB/s) |
|---|---|---|---|---|---|---|---|---|
| 8000 | 435,646,768 | 142.4 (3.06) | 52.7 (8.26) | 273.2 (1.59) | 105.6 (4.12) | 8.23 | 115.7 | 68.8 (15.0) |
| 16000 | 714,398,768 | 231.4 (3.09) | 77.1 (9.27) | 412.9 (1.73) | 174.2 (4.10) | 7.36 | 144.2 | 45.7 (24.4) |
| 32000 | 1,271,902,768 | 439.4 (2.89) | 206.8 (6.15) | 1580.9 (0.80) | 416.2 (3.06) | 6.07 | 205.0 | 77.3 (23.9) |

Bytes versus tokens: slope 34,844 B/token plus 156.9 MB (149.6 MiB) fixed, matching the earlier prompt_save fit
(34,840 B/token, 149.63 MiB). Cold restores had residency 0.0 (mincore), so they read from disk.

Cautions inside the data:
- `--cache-ram` rates use the stall (TTFT minus prompt_ms), not a copy timer. The L = 8000 baseline stall is 37.2 ms against
  1.26 ms at 16000 and 1.55 ms at 32000, a 26x outlier in the first length measured; the baseline-subtracted load rate at
  8000 (32.6 GB/s) exceeds the 28.9 GB/s H2D plateau and is the least reliable cell. The raw columns above are not
  baseline-subtracted. The drafter state is in the cache entry but not in the byte count, so rates are lower bounds.
- Disk-save varies 178-292 ms across 3 reps at L = 8000 (fsync 75 ms in one rep).
- HSF-5's gather rate is NOT COVERED (no code exists).
- The slot save/restore endpoints serialize the target context only (KV, recurrent state, token ids). The draft model's
  state is not restored and must be rebuilt, which is outside these rates.

### Could HIP graphs plausibly affect a save/restore rate?

Judgment from code path, not from a measurement (no graphs-on step 7 exists):
- **tmpfs/disk save and restore: unlikely.** Both are `ggml_backend_tensor_get/set` copies (hipMemcpy D2H / H2D) around file I/O.
  Graphs change how compute kernels are launched; the copies are not graph nodes. With the server idle at each request there
  is no outstanding graph work for the copy to wait on. I expect any difference to sit inside the 3-rep spread (for example
  tmpfs restore 52.0-56.6 ms at 8000, +/- 4 %), but this is an expectation.
- **`--cache-ram` save/load stalls: possible but small.** These are measured as TTFT minus prompt_ms, so they include
  the non-prompt work of the same request (slot setup, first-token decode, draft resync) which does run through graphs.
  Baseline subtraction cancels the part common to both arms, which leaves graph-dependent work only if it differs between
  the arms; no evidence either way.
- **Memory side effect:** graphs-on holds captured graph/exec memory (GPU-LEAK-1: 290 MiB per request on the E1 scratch shape,
  1.7 MiB on the production shape), which is irrelevant to a copy rate unless VRAM is tight.
- The mechanism leans toward "no meaningful effect", but a graphs-ON re-measure (KPF-18-S1.7g) is the only thing that can
  say so. That decision is open; this document does not resolve it.

## Restore-versus-re-prefill crossover, 27B (uses graphs-off rates, labelled)

| L | re-prefill s (idle, measured ms/token x L, graphs ON, 1 rep) | tmpfs restore ms | cold-disk restore ms | `--cache-ram` load stall ms (raw) | ratio re-prefill / tmpfs | / cold disk | / cache-ram |
|---|---|---|---|---|---|---|---|
| 8000 | 10.93 | 52.7 | 105.6 | 68.8 | 207 | 103 | 159 |
| 16000 | 23.22 | 77.1 | 174.2 | 45.7 | 301 | 133 | 509 |
| 32000 | 51.62 | 206.8 | 416.2 | 77.3 | 250 | 124 | 668 |

Crossover prefix tokens, linear model (restore = fixed + 34,844 B/token over the measured rate; re-prefill about 1.36
ms/token at small L): tmpfs 19.0 ms + 4.2 us/token, crossover 14 tokens; cold disk 38.1 ms + 8.5 us/token, crossover 28.
These are graphs-off copy rates against a graphs-on re-prefill rate, so the ratio mixes the two conditions; if graphs-on
copy rates are similar (the expectation above), the ratios hold to the stated precision. Recompute from the 7g re-measure.

Save-side cost per idle-slot demotion (graphs off): a 32k-token slot costs 0.44 s to tmpfs, 1.58 s to disk, 0.21 s to
`--cache-ram`. A neighbour demotion inside someone else's TTFT is therefore a sub-2-s term per slot at 32k, which is
below the 43.5 s stall by a factor of 20 or more; this constrains LB7's attribution, it does not make it.

## (b) Per-role histogram and ceilings

**Carried forward unchanged** from `hsf4_results.json` (llama-server logs 2026-09-22..10-20, 16,087 completed requests;
role = port + model era, the logs carry no role field). rho = 1.325 (log-median prefill tok/s, full 296.2 n = 369 vs
half 223.5 n = 187; not a controlled matrix value). alpha(B) = share of uncached tokens in requests below B; ceiling =
alpha(B) x (1 - 1/rho), with (1 - 1/rho) = 0.245. Mechanism labels: 1K is the prefill-compute HOL scale, 8K-16K the
KV-reservation scale, 2K-4K between the two.

| role / port / model | n | uncached tokens | p50 / p90 / p99 / max (tokens) |
|---|---|---|---|
| frontdoor :8070 + :8080/:8180, Qwen3.6-35B-A3B-MTP-Q8_0 | 5,581 | 3,254,645 | 164 / 967 / 7,761 / 64,019 |
| GPU :8083, Qwen3.8-27B-Q8_0 | 5,488 | 31,908,913 | 628 / 18,239 / 57,680 / 157,144 |
| GPU :8083, Qwen3.6-27B-MTP-Q8_0 (earlier era) | 1,810 | 1,301,151 | 226 / 2,052 / 10,637 / 29,654 |
| architect_general :8074, Qwen3.8-Flash-Next UD-IQ4_XS | 2,609 | 1,605,251 | 188 / 659 / 4,647 / 61,259 |
| :8185 / :8285, Qwen3-Next-80B-A3B Q4_K_M | 264 / 190 | 2.08M / 1.74M | 2,031 / 30,355 / 60,852 / 60,852; 2,045 / 30,356 / 60,852 / 60,852 |
| :8074 Qwen3.5-122B era; :8085 | 97; 48 | insufficient (< 100) | not reported |

Request share below B / alpha(B) / ceiling:

| B | frontdoor 35B | GPU 27B (3.8) | architect_general Flash-Next |
|---|---|---|---|
| 1K | 90.1 % / 0.309 / 0.076 | 60.4 % / 0.034 / 0.008 | 93.5 % / 0.344 / 0.084 |
| 2K | 93.3 % / 0.408 / 0.100 | 68.7 % / 0.054 / 0.013 | 97.0 % / 0.425 / 0.104 |
| 4K | 98.2 % / 0.646 / 0.159 | 77.8 % / 0.101 / 0.025 | 98.9 % / 0.506 / 0.124 |
| 8K | 99.1 % / 0.745 / 0.183 | 85.2 % / 0.174 / 0.043 | 99.2 % / 0.542 / 0.133 |
| 16K | 99.7 % / 0.860 / 0.211 | 89.4 % / 0.256 / 0.063 | 99.3 % / 0.556 / 0.136 |
| 64K | 100 % / 1.000 / 0.245 | 99.4 % / 0.899 / 0.220 | 100 % / 1.000 / 0.245 |

(The 64K row reads the ceiling off the 65,536 cut, so it is only a bound.)

**serving_call.v1 / dispatch.v1 re-run (done today, not usable as a per-role histogram).** Union of three orchestrator
roots (`epyc-orchestrator`, `worktrees/f8-turn1-grammar-lazy`, `worktrees/hil15a-fix-20261022`): 478 serving_call.v1 rows (14 with no
`result`), 481 dispatch.v1 dispatch records, 459 joined on request_id. Per role (uncached = prompt_tokens - cached_prompt_tokens):
frontdoor n = 352 (p50 1,402 / p90 2,662 / p99 2,959 / max 3,124), coder_escalation n = 60 (684 / 3,058 / 3,271 / 3,370),
architect_general n = 13, worker_summarize n = 39 (p50 139). Token-weighted hit rate 0.543 frontdoor, 0.465 coder_escalation.
Why it does not replace the log table: every joined record is `method=direct`, client class `orchestrator_internal`, 433 of 481
on scratch ports (18973 gate server), zero fleet records, no prompt over 3,370 tokens, so no B >= 4K cut can be read
(everything lies between 2K and 4K for the frontdoor). It is test and gate traffic, not the live agentic distribution.
The 2026-10-21 log table remains the best available. Re-run it when real frontdoor traffic is recorded (WP-15.3).

## Data provenance

- `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf18-s1-remainder/VERDICT.json` e9d02f3302b1cb9e59d4d677310855b171dc8bb5819726c1393b71ebbda56106
- `.../PREDECLARATION.md` fec95598f3ae418b28141a768f458c51eb1952304386646e1aac0b5176722dc8; `.../RUN_RECORD.json` dbfdda560b7aa79a958799837bea8987212cf78e7d985c68622630a2c8e3ed16; `.../out/belief_measurements.jsonl` 3fb62336c63ad51091a96d7fd8c129114db87346abe118d6dee34974f1ffeae8
- `/mnt/raid0/llm/tmp/hsf4-wp15-20261021/hsf4_results.json` 30987331ad71311872c60c31daf1e614f26d65bf17c937b9979753d8a3666349; `rows.json` 76cf16467c0c18e33d689a69144445343d116a178ed27b516e1b5a6946fbf498
- `/mnt/raid0/llm/tmp/analytics-20261020/HSF-4/REPORT.md` a4e19530f8bd0304792c4b42b4098adc80db174986287e08761555b4d4574656
- `/mnt/raid0/llm/tmp/pb-qcost-1/runs/20261021T212922Z/pb_qcost_1.jsonl` a82cdf93dc8ca304703f057822586d61f746600bc8791036a3d7023e41c2699e (n = 0 control re-prefill rates)
- serving_calls / dispatch (sha256): `epyc-orchestrator/logs/serving_calls/serving_calls.jsonl` 3281cab8006b5fb647365aae389ed4529ecad6daca85f4f1fb6a67299395b856, `logs/dispatch/dispatch.jsonl` 49f44be8272fe706697a007a2a87d1c0be2b1436e5eea2e3dbe29d37bf7b048b; f8-turn1-grammar-lazy serving_calls 34e0ad6a4d2d2b9ad7af1ef784e318101d4a1ea3c21e10b4f8b3aee734e1f142, dispatch ced65b76090b72f3c28018aaea18aadfacc89711983c3e87d2d1d81f12e635f4; hil15a-fix serving_calls f145be3138fb6934b0095a41d92b29dfe7232e625b10c89f8f88b0515468018f, dispatch 53acceb8247a8d3cf005d1e7a1bf62b9976d351a1d7fe2f207148fe3a711be29
- Scripts (scratch, not committed): `/mnt/raid0/llm/tmp/f8-prodstack-20261023/{hsf4_restore.py,join.py}` sha256 a142c766b17b6c75d849a353db9c36a0c19acbbef65d53d03f5961167e88d15d and 57e90d2dd4a8b1a64998f0e2abadc4a5516839ea238f03bcc852859fccce50cb.

## Compute proposal (NOT armed)

Graphs-ON re-measure of step 7 is KPF-18-S1.7g and is the operator's open decision; no new row is proposed here. If 7g
is taken, the launcher is the existing `kpf18-s1-remainder` job with step 7 only and `GGML_CUDA_DISABLE_GRAPHS` unset
(about 10 min after a 2-5 min load). The only new request from this analysis: fix the L = 8000 `--cache-ram` baseline
(repeat the filler-eviction baseline x3 at the start AND the end of the step, so the first-length outlier is detectable).
