# HSF-4 results, source-rate sub-term and log re-run (2026-10-23, workspace-f8; source rates re-quoted graphs ON 2026-10-24)

Task: `handoffs/active/heterogeneous-slot-fabric-residency.md` HSF-4 (reload-vs-re-prefill crossover per lineup model;
per-role uncached-prompt-length histogram with alpha(B) and the ceiling alpha(B)*(1 - 1/rho)). The analytic half (2026-10-20)
and the llama-server-log half (2026-10-21) are already in the handoff. This pass adds (a) the source-rate sub-term
from KPF-18-S1 step 7 and (b) the serving_call.v1 / dispatch.v1 re-run the handoff left open.
No inference was run for this document; step 7 (graphs disabled, 2026-10-23T14:18Z) and its graphs-ON re-measure
KPF-18-S1.7g (2026-10-23T18:47-18:49Z) are recorded measurements.

**2026-10-24 revision (HSF-4.G).** KPF-18-S1.7g came out `graphs-sensitive` (4 of 21 (L, mode) cells), so by its
predeclared rule HSF-4/5 use the **graphs-ON numbers, all of them, from that run**. The source rates, the ratios, the
crossover and the transfer-versus-stall comparison below are recomputed from the ON medians. The graphs-disabled
table is kept, labelled, for the record. The code-path judgement that the copies would sit inside the 3-rep spread is
retired (section "Retired"). Attribution of every ON-versus-OFF difference: **graphs ON plus the
`HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` knob plus the fresh load / step-7-only history, jointly; NOT HIP graphs alone.**
The host KV mirror costing that consumes these rates is `docs/design/hsf-5-host-kv-mirror-costing-20261024.md`.

## Headline

- **Source rates (graphs ON, the HSF-4/5 rates).** 27B on the production-shaped :8083 argv, L = 8000 / 16000 / 32000
  tokens: tmpfs restore 8.58 / 8.50 / 7.29 GB/s (50.8 / 84.1 / 174.6 ms), cold-disk restore 3.92 / 3.94 / 3.79 GB/s
  (111.0 / 181.3 / 335.6 ms), tmpfs save 3.21 / 3.19 / 3.17 GB/s (135.9 / 223.9 / 400.7 ms), disk save 1.70 / 1.69 /
  1.68 GB/s (255.7 / 422.2 / 758.5 ms), `--cache-ram` save stall 111.0 / 160.5 / 189.2 ms, load stall 77.9 / 55.1 / 83.2 ms.
- **Restore versus re-prefill, 27B (copy-and-apply only):** against measured idle re-prefill of 10.93 / 23.22 / 51.62 s
  (n = 0 control, 1.3659 / 1.4514 / 1.6132 ms/token, graphs ON) the restore is 215 / 276 / 296 x cheaper from tmpfs,
  98 / 128 / 154 x from cold disk, 140 / 421 / 620 x from `--cache-ram` (raw load stall). Crossover prefix length
  (restore cheaper above it): about **13 tokens from tmpfs, 30 from cold disk** (graphs-OFF figures were 14 and 28).
- **This does not rehabilitate the 60-820x line.** The HSF-LB1 correction stands: the measured end-to-end ON-arm pre-eval
  stall is 43.5 s (median, 20-29k cached tokens, 15 turns, one rep). The largest single transfer in the graphs-ON run is
  the 32k-token disk save, 758.5 ms median (768.1 ms worst rep), **57 x smaller than that stall** (graphs-OFF said 27 x,
  from a 1580.9 ms median that the ON run did not reproduce). A single save or restore cannot explain the stall;
  attribution stays with UFH14-LB7.
- **Done: NO for HSF-4 as a whole.** The source-rate sub-term is now closed on graphs-ON numbers (HSF-4.G). Still open:
  the serving_call.v1 / dispatch.v1 per-role histogram has no usable sample (below), and the placement KV-recovery term
  still needs the end-to-end restore cost from LB7.

## (a) Source-rate table, GRAPHS ON (the HSF-4/5 source rates)

LABEL: **graphs ON** (no `GGML_CUDA_DISABLE_GRAPHS` in the server's `/proc/<pid>/environ`, `out/graphs_proof.json`;
`HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` also set; fresh load, step 7 only). Source: KPF-18-S1.7g
`/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf18-s1-step7-graphs-on/VERDICT.json` -> `step7_graphs_on_result`, verdict
`MEASURED` (n = 3 valid in every timed mode at every L; hot disk restore n = 1). Rule sha256
`79350337f0342562830a728bf8ca0448c9ae292d75cd7b12a612aa20221684d2` (= sha256 of that run's `PREDECLARATION.md` and the
`predeclaration_sha256` field of the VERDICT; `excluded_predeclaration_mismatch` is empty). Unit: GB/s = 1e9 bytes/s,
ms medians of 3. Model: Qwen3.8-27B-Q8_0 + DFlash2 drafter, fork build `gpu-20261020-a1f0c8cf9` (binary sha256
`2be7a16e…`, not the v10 production binary), `-np 4 -c 393216 -b/-ub 512 --kv-unified --cache-ram 65536
--no-cache-idle-slots`, host threads 184-191, numactl --membind=3. Peak own-pid VRAM 49,726 MiB.

| L (tokens) | slot-file bytes | tmpfs save ms (GB/s) | tmpfs restore ms (GB/s) | disk save ms (GB/s) | cold-disk restore ms (GB/s) | hot-disk restore ms (GB/s), n = 1 | derived disk-only read (GB/s) |
|---|---|---|---|---|---|---|---|
| 8000 | 435,646,768 | 135.9 (3.21) | 50.8 (8.58) | 255.7 (1.70) | 111.0 (3.92) | 44.9 (9.70) | 7.23 |
| 16000 | 714,398,768 | 223.9 (3.19) | 84.1 (8.50) | 422.2 (1.69) | 181.3 (3.94) | 77.7 (9.19) | 7.35 |
| 32000 | 1,271,902,768 | 400.7 (3.17) | 174.6 (7.29) | 758.5 (1.68) | 335.6 (3.79) | 153.4 (8.29) | 7.90 |

`--cache-ram` (stall = TTFT minus prompt_ms; bytes = slot-file bytes at L plus the evicted slot's checkpoint, drafter state
NOT counted, so every rate is a lower bound):

| L | save stall ms | load stall ms (raw GB/s) | filler-eviction baseline stall ms | baseline-subtracted save GB/s | baseline-subtracted load GB/s | entry bytes |
|---|---|---|---|---|---|---|
| 8000 | 111.0 | 77.9 (13.12) | 49.4 | 14.18 | 36.18 | 1,032,233,140 |
| 16000 | 160.5 | 55.1 (23.77) | 1.62 | 7.25 | 24.49 | 1,310,985,140 |
| 32000 | 189.2 | 83.2 (21.57) | 1.45 | 9.11 | 22.84 | 1,868,489,140 |

Cautions inside the data:
- The L = 8000 baseline stall is again an outlier (49.4 ms against 1.62 and 1.45 ms); graphs-OFF had 37.2 ms there. It
  reproduced on a fresh step-7-only load, so it is a first-measured-length effect, not load history. The baseline-subtracted
  L = 8000 load rate (36.18 GB/s) exceeds the 28.89 GB/s H2D plateau and is physically not a copy rate: do not use the
  L = 8000 derived `--cache-ram` rates. Use the raw stalls.
- The disk-save spread is wide (172-272 ms at 8000, 459-768 ms at 32000), fsync medians 0.9-2.7 ms.
- Bytes versus tokens: 34,844 B/token plus 156.9 MB (149.6 MiB) fixed (same bytes in both runs).
- Cold restores had residency 0.0 (mincore), so they read from disk.
- The slot endpoints serialize the target context only (KV, recurrent state, token ids). The draft model's state is not
  restored and must be rebuilt, which is outside these rates.
- HSF-5's gather rate is NOT COVERED (no mapped-host UMBP gather code exists).

### Which cells were graphs-sensitive (KPF-18-S1.7g, `compare.py`)

Rule (predeclared): per (L, mode), sensitive iff |median_ON - median_OFF| > max(range_ON, range_OFF), range = ms_max - ms_min,
n = 3 on both sides. Four of 21 cells are sensitive:

| L | mode | median OFF ms | median ON ms | delta ms | max range ms |
|---|---|---|---|---|---|
| 8000 | cache_baseline | 37.215 | 49.401 | +12.186 | 11.822 |
| 16000 | cache_baseline | 1.263 | 1.620 | +0.357 | 0.186 |
| 32000 | disk_restore_cold | 416.198 | 335.568 | -80.630 | 25.053 |
| 32000 | cache_load | 77.270 | 83.245 | +5.975 | 5.375 |

Derived rates inherit sensitivity from any component: both `--cache-ram` rates at 8000 and 16000, the load rate at 32000 and
the 32000 derived disk-only read are sensitive. Note that the 32000 disk save moved from 1580.9 to 758.5 ms yet is labelled
insensitive, because the OFF run's own range was 1641 ms. The overall label is `graphs-sensitive`, so all HSF-4/5 numbers
come from the ON run. Attribution, again: graphs ON + the knob + fresh load / step-7-only history jointly, not graphs alone.

## (a-off) Source-rate table, GRAPHS DISABLED (kept for the record; NOT the HSF-4/5 rates)

LABEL: **every rate and ms value in this subsection was measured with `GGML_CUDA_DISABLE_GRAPHS=1`** (KPF-18-S1 remainder
PREDECLARATION amendment 2026-10-23T13:25Z, GPU-LEAK-1), after ~20 minutes of earlier steps on the same load. Not the production
condition and superseded for HSF-4/5 by the graphs-ON table above. Source: `kpf18-s1-remainder/VERDICT.json` `items.step7_hsf`,
copied verbatim as `kpf18-s1-step7-graphs-on/base_VERDICT_graphsoff.json` (sha256 e9d02f33…).

| L (tokens) | slot-file bytes | tmpfs save ms (GB/s) | tmpfs restore ms (GB/s) | disk save ms (GB/s) | cold-disk restore ms (GB/s) | derived disk-only read (GB/s) | --cache-ram save stall ms | --cache-ram load stall ms (raw GB/s) |
|---|---|---|---|---|---|---|---|---|
| 8000 | 435,646,768 | 142.4 (3.06) | 52.7 (8.26) | 273.2 (1.59) | 105.6 (4.12) | 8.23 | 115.7 | 68.8 (15.0) |
| 16000 | 714,398,768 | 231.4 (3.09) | 77.1 (9.27) | 412.9 (1.73) | 174.2 (4.10) | 7.36 | 144.2 | 45.7 (24.4) |
| 32000 | 1,271,902,768 | 439.4 (2.89) | 206.8 (6.15) | 1580.9 (0.80) | 416.2 (3.06) | 6.07 | 205.0 | 77.3 (23.9) |

## Retired: the code-path judgement on HIP graphs

The 2026-10-23 version of this document judged from the code path, before any graphs-ON measurement, that save/restore are
hipMemcpy plus file I/O outside graph nodes, so "any difference [would] sit inside the 3-rep spread". **That judgement is
retired.** The measurement contradicts it for 32000 cold-disk restore (-80.6 ms against a 25.1 ms spread) and 32000
`--cache-ram` load (+6.0 ms against 5.4 ms), and for both baseline cells. The 17 insensitive cells do not rescue it: the
predeclared rule is per-cell and the overall label decides. No mechanism is claimed for the four cells either, because the
run cannot separate graphs from the knob and the load history. The memory note is unchanged: graphs-on holds captured
graph/exec memory (GPU-LEAK-1d: ~1.7 MiB per request on the production shape), irrelevant to a copy rate unless VRAM is tight.

## Restore-versus-re-prefill crossover, 27B (graphs ON)

| L | re-prefill s (idle, measured ms/token x L, graphs ON, 1 rep) | tmpfs restore ms | cold-disk restore ms | `--cache-ram` load stall ms (raw) | ratio re-prefill / tmpfs | / cold disk | / cache-ram |
|---|---|---|---|---|---|---|---|
| 8000 | 10.93 | 50.8 | 111.0 | 77.9 | 215 | 98 | 140 |
| 16000 | 23.22 | 84.1 | 181.3 | 55.1 | 276 | 128 | 421 |
| 32000 | 51.62 | 174.6 | 335.6 | 83.2 | 296 | 154 | 620 |

Crossover prefix tokens, linear model (restore = 156.9 MB fixed + 34,844 B/token over the L = 8000 measured rate, the
lowest length measured; re-prefill 1.3659 ms/token): tmpfs 18.3 ms + 4.06 us/token, crossover **13 tokens**; cold disk
40.0 ms + 8.88 us/token, crossover **30 tokens**. Both copy rates and the re-prefill rate are now graphs ON, so the
ratio no longer mixes conditions. (Graphs-OFF figures: 14 and 28 tokens; 207 / 301 / 250 x and 103 / 133 / 124 x.)

Save-side cost per idle-slot demotion (graphs ON): a 32k-token slot costs 0.40 s to tmpfs, 0.76 s to disk, 0.19 s to
`--cache-ram`. A neighbour demotion inside someone else's TTFT is therefore a sub-1-s term per slot at 32k, below the
43.5 s stall by a factor of 57 or more; this constrains LB7's attribution, it does not make it.

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

**serving_call.v1 / dispatch.v1 re-run (done 2026-10-23, not usable as a per-role histogram).** Union of three orchestrator
roots (`epyc-orchestrator`, `worktrees/f8-turn1-grammar-lazy`, `worktrees/hil15a-fix-20261022`): 478 serving_call.v1 rows (14 with no
`result`), 481 dispatch.v1 dispatch records, 459 joined on request_id. Per role (uncached = prompt_tokens - cached_prompt_tokens):
frontdoor n = 352 (p50 1,402 / p90 2,662 / p99 2,959 / max 3,124), coder_escalation n = 60 (684 / 3,058 / 3,271 / 3,370),
architect_general n = 13, worker_summarize n = 39 (p50 139). Token-weighted hit rate 0.543 frontdoor, 0.465 coder_escalation.
Why it does not replace the log table: every joined record is `method=direct`, client class `orchestrator_internal`, 433 of 481
on scratch ports (18973 gate server), zero fleet records, no prompt over 3,370 tokens, so no B >= 4K cut can be read
(everything lies between 2K and 4K for the frontdoor). It is test and gate traffic, not the live agentic distribution.
The 2026-10-21 log table remains the best available. Re-run it when real frontdoor traffic is recorded (WP-15.3).

## Data provenance

- Graphs ON (the HSF-4/5 source rates): `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf18-s1-step7-graphs-on/VERDICT.json`
  9868e8bc4219e61f3045687bebd857b8ee65b1fda60772a02ff77927c515956d; `PREDECLARATION.md`
  79350337f0342562830a728bf8ca0448c9ae292d75cd7b12a612aa20221684d2; `RUN_RECORD.json`
  9ddcc5e2722611216d4b1b395480f688bbce873988bea2b01cb8b413364555de; `compare.py`
  73412452e5076412fea0ac2d25343b9a016bac8c6fe295fadc56b4a18852d4d1; `out/graphs_proof.json`
  0fee50687294c42ca601f1f23e83624fa4722f0b3abebef9e04c8d5fad4537d9; `out/belief_measurements.jsonl`
  2d074994edfb673ad47c7ead765bbffc9678f37ef8bf2384c56bad45c917c318; records `out/records/kpf18-20261023T184732Z-1.json`
  343c8541…, `-184749Z-2.json` 3ed1e16c…, `-184819Z-3.json` fd062761…; window id `kpf18-s1-step7-graphs-on-20261023T1847Z`.
- Graphs disabled: `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf18-s1-remainder/VERDICT.json` e9d02f3302b1cb9e59d4d677310855b171dc8bb5819726c1393b71ebbda56106
  (identical bytes as `kpf18-s1-step7-graphs-on/base_VERDICT_graphsoff.json`)
- `.../kpf18-s1-remainder/PREDECLARATION.md` fec95598f3ae418b28141a768f458c51eb1952304386646e1aac0b5176722dc8; `.../RUN_RECORD.json` dbfdda560b7aa79a958799837bea8987212cf78e7d985c68622630a2c8e3ed16; `.../out/belief_measurements.jsonl` 3fb62336c63ad51091a96d7fd8c129114db87346abe118d6dee34974f1ffeae8
- `/mnt/raid0/llm/tmp/hsf4-wp15-20261021/hsf4_results.json` 30987331ad71311872c60c31daf1e614f26d65bf17c937b9979753d8a3666349; `rows.json` 76cf16467c0c18e33d689a69144445343d116a178ed27b516e1b5a6946fbf498
- `/mnt/raid0/llm/tmp/analytics-20261020/HSF-4/REPORT.md` a4e19530f8bd0304792c4b42b4098adc80db174986287e08761555b4d4574656
- `/mnt/raid0/llm/tmp/pb-qcost-1/runs/20261021T212922Z/pb_qcost_1.jsonl` a82cdf93dc8ca304703f057822586d61f746600bc8791036a3d7023e41c2699e (n = 0 control re-prefill rates)
- serving_calls / dispatch (sha256): `epyc-orchestrator/logs/serving_calls/serving_calls.jsonl` 3281cab8006b5fb647365aae389ed4529ecad6daca85f4f1fb6a67299395b856, `logs/dispatch/dispatch.jsonl` 49f44be8272fe706697a007a2a87d1c0be2b1436e5eea2e3dbe29d37bf7b048b; f8-turn1-grammar-lazy serving_calls 34e0ad6a4d2d2b9ad7af1ef784e318101d4a1ea3c21e10b4f8b3aee734e1f142, dispatch ced65b76090b72f3c28018aaea18aadfacc89711983c3e87d2d1d81f12e635f4; hil15a-fix serving_calls f145be3138fb6934b0095a41d92b29dfe7232e625b10c89f8f88b0515468018f, dispatch 53acceb8247a8d3cf005d1e7a1bf62b9976d351a1d7fe2f207148fe3a711be29
- Scripts (scratch, not committed): `/mnt/raid0/llm/tmp/f8-prodstack-20261023/{hsf4_restore.py,join.py}` sha256 a142c766b17b6c75d849a353db9c36a0c19acbbef65d53d03f5961167e88d15d and 57e90d2dd4a8b1a64998f0e2abadc4a5516839ea238f03bcc852859fccce50cb.

## Compute

KPF-18-S1.7g is done (2026-10-23T18:47-18:49Z, PASSED). No new compute row is proposed. The remaining instrument fix
stands: the L = 8000 `--cache-ram` baseline outlier reproduced in both runs, so a future step-7 run should repeat the
filler-eviction baseline x3 at the start AND the end of the step, so a first-length effect is detectable and the
L = 8000 derived `--cache-ram` rates become usable.
