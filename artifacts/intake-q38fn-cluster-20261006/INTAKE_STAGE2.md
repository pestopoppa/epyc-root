## Research Intake Report — Stage 2 close-out — 2026-10-06 (session intake-q38fn-cluster-ec-20261006)

Waves used: 4 of 4 (wave 4 = full GB10 byte ledger, intake-1951 deep read, run on the coordinator's all-recommended instruction; the earlier stop-early note is superseded). Wave 1 = 10 dives (1937-1945, 1948); wave 2 = 10 sources (1946, 1947 existing Stage-1 entries + 8 new 1949-1956); wave 3 = 3 new (1957-1959). 23 entries total (12 from Stage 1 + 11 Stage-2b), all `dive-verified`, 209 claim_anchors (every quote mechanically re-found on disk; semantic per-claim second reader NOT run — only the mechanical re-find; disagreements none surfaced). No handoff/stub/index-row writes; only research/intake_index.yaml and .research-session.json. Dive scratch: /mnt/raid0/llm/tmp/intake-q38fn-cluster/ (artifact audit: clean).

Deviation note: 1946 (b12x) was dived concurrently with wave 1 and is accounted to wave 2 so that wave 1 stays at the 10-dive cap.

### Headline findings per source (author-reported unless marked; setup in brackets)
| ID | Source | Headline | Setup / caveat |
|---|---|---|---|
| 1937 | myllmbox 2-Spark kit v5.2 @d2721ec | 93.2 tok/s avg, 176.8 peak (c=1); 1,008 tok/s @64 streams; prefill 3,939 tok/s @128k | 5-of-512-expert healed INT4 checkpoint, MTP K<=7 (~3.9 accepted/step thinking-on), TP2/EP over RoCE; peak = best 10 s window; 1,008 = best prompt class (code 1,007.5; mixed 968.4); hibrid48 (10 experts) ~120 tok/s c=1 |
| 1948/1949 | NVIDIA forum + tonyd2wild repo (independent of the kit author) | official 10-expert NVFP4: 1 Spark median 32.5 -> 43.9; 2 Sparks TP2 median 53.7 (peak 63.7); 4 Sparks 40.5 | thinking off, 40 prompts, MTP3/4; MTP-off floor 15.4 (1 Spark); >70 tok/s only as x6 aggregate or count-to-100 peaks |
| 1950 | MiaAI dual-Spark | MTP off 24.5 -> MTP3 52.1; 47k reduced draft vocab +9.6% mean | TP2+EP, acceptance 72.8% (89/74.5/60% by position); analytical 9.9 GB/step per GPU (assumed 235-245 GB/s) |
| 1958 | ai-muninn two-Spark post | 51.9 -> 72.0 tok/s (median of 3, c=1) | NVFP4 TP2+EP, five bundled changes, code-heavy mix (83-87 code, 45-49 prose); 185 Gb/s measured link; kernels at 80-87% of 273 GB/s; ~51 ms/step |
| 1940/1939 | azampatti kit + card | one Spark 70-75 (yaml up to 79.2); two-node single-stream 96.8-112.7 | 5-of-10 experts, draft head at top-10, K=5; scaling 1->2 nodes only 1.45x |
| 1951 | jschmied speed-of-light | GB10 attainable ~220 GB/s of 273 (80%); K=5 code 68.1-68.4 tok/s vs floor ~80-82 | measured per-kernel GB/s (224 "DRAM floor"); GDN verify kernel 145-148 GB/s latency-bound |
| 1952 | ai-muninn single-Spark | MTP-off 16.6-17.0 tok/s at 9.27 GiB/token (~154-158 GiB/s, ~60% of 273) ; MTP 2.93 tok/step -> 41.7-43.9 | official NVFP4 |
| 1946/1947 | b12x, eugr | 4-node all-reduce 48 KB: NCCL 65.5 us vs RoCEnante 23.6 us; ib_write_lat 1.47 us typical | no 2-node numbers; ~3-4 ms/step saved; eugr publishes no Q38FN tok/s |
| 1943 | NVIDIA spec | 273 GB/s per node; 200 Gb/s per QSFP; two PCIe Gen5 x4 NIC links | theoretical only; no latency published |
| 1945 | Qwen card + safetensors headers | 125.7B main-text params, 6.04B active (6.67B with head), 10 of 512 experts, PLE table 51.2B | bytes/step computed; reproduces our 1.296 GB expert figure |
| 1955/1956/1959 | FR-Spec, MiaAI single, TensorFold | reduced-vocab draft head: +13% mean, code x1 +21.5% (measured, 1956); FR-Spec LM head = 49% of EAGLE-2 draft time at 128k vocab | 1959's 63.6/96.9 headline contradicted by its own docs (52.0/63.7) |

### Physics comparison
Denominators: Spark 273 GB/s peak per node (NVIDIA spec, intake-1943); measured attainable ~220-224 GB/s per kernel (jschmied, intake-1951; 80-87% of spec per 1958); two nodes 546 GB/s peak (NOT pooled: per-layer all-reduce over a ~25 GB/s port / ~31 GB/s of PCIe, latency ~17-65 us per collective). EPYC 9655: 12ch DDR5-5600 = 537.6 GB/s theoretical, 446.8 GB/s measured read-sum (post-BIOS 2026-09-21; re-read 449.4 under load; wiki/hardware-optimization.md, cpu-decode-roofline-program.md). MI210: 1.6 TB/s HBM2e spec (1638), 1433 GB/s achievable (87.5%), 64 GiB.

Bytes (computed from config + safetensors headers, intake-1945, unless marked): plain (R=1) decode bytes/token: official NVFP4 9.95 GB (dense stays bf16 7.35); INT4+fp8 5-expert kit ~4.2 GB (intake-1939 computed); our IQ4_XS-uniform GGUF 4.16 GB (measured tensor table). Per speculative step (verify R rows) routed experts grow with the expert union: k=10: R=4 5.0 GB, R=6 7.4 GB; k=5: R=6 3.8 GB (independent-routing assumption; real routing correlated, so true union is lower, and jschmied measured 26.6 vs 38.8 distinct experts at R=4).

| Platform (model variant, quant) | Bandwidth peak / measured | Bytes/token plain; bytes/step (spec) | Roofline tok/s plain; spec-aware | Reported or measured tok/s | Efficiency |
|---|---|---|---|---|---|
| EPYC 9655 CPU, Q38FN 10 experts, IQ4_XS-uniform, MTP d4 (alpha 0.82) | 537.6 / 446.8 | 4.16 GB; ~9.1 GB (R=5 verify only) to ~11.6 GB (adds ~4 draft passes incl. 0.52 GB head each) [assumed] | 107 (129 at peak); 172 at 9.1 GB, 3.5 tok/step [derived] | **52.66 measured** (champion MTP, post-BIOS, ef81196d5; v10 planner 50). Plain post-BIOS ~33.9 [derived from 43.28/27.89 ratio] | 49% of plain roofline (spec-inflated); **31-39% of measured read-sum** (137-174 GB/s effective) |
| MI210, Q38FN | 1638 / 1433 | same bytes | 344 plain at 1433 | **not measured; does not fit** (routed experts alone ~64 GB at 4.25 bpw vs 68.7 GB, no room for KV) | reference only: dense Q8 decode measured at 50.2% of achievable -> ~170 tok/s hypothetical, unmeasured |
| 1x Spark, official NVFP4 (10 exp) | 273 / ~220 | 9.95 GB; ~17-20 GB/step | 27.4 plain | MTP off 15.4-17.0; MTP3/4 median 43.9 (peak 209.9 count-to-100) | 56-62% of plain roofline MTP-off (16.6 t/s = 62%) |
| 2x Spark TP2, official NVFP4 (10 exp) | 546 / ~440 | 9.95 GB | 54.9 plain | MTP off 24.5; MTP3 median 53.7, best run 72.0 (code-heavy) | 45% of plain roofline MTP-off |
| 1x Spark, INT4+fp8 5-expert, K=5 | 273 / ~220 | ~4.2 GB; ~9.7 GB/step [computed] | 65 plain; ~93 spec-aware (3.29 tok/step) | 70-79 (author); jschmied K=5 code 68 | ~80% of spec-aware roofline; ~83% of 1951's own floor |
| 2x Spark TP2/EP, INT4+fp8 5-expert (kit) | 546 / ~440 | ~4.2 GB; ~9.7 GB/step | 130 plain; ~220 spec-aware (3.9 tok/step) | **93.2 avg / 176.8 peak window** (kit); 96.8-112.7 (author yaml) | 42% (avg), 80% (peak window) of spec-aware; scaling 1->2 nodes 1.3-1.45x |

### Verdict
**Physics does not contradict the Spark headline, and it does not make our CPU number unreachable either.** Two-Spark aggregate bandwidth (546 GB/s) is within 2% of our theoretical (537.6) and above our measured (446.8), so the operator's premise holds; but the headline 93/177 tok/s is NOT a like-for-like Q38FN number:
1. Different model: the kit's default routes 5 of 512 experts (healed, ~2.5 capability points lower per its own card; credibility 3) vs the 10 we serve; plus dense layers at fp8/int4 (3.7 GB) vs bf16 in the official quant (7.35 GB). Fewer bytes per step by ~25-45%.
2. Speculation: ~3.9 accepted tokens/step (code 5.1) with K up to 7; every Spark number is a spec-decode number. MTP-off floors are 15-17 (1 Spark) and 24.5 (2 Sparks).
3. Aggregation/peaks: 177 is the best 10 s window; 1,008 is the best prompt class at 64 streams; independent medians for the 10-expert model on two Sparks are 53.7 (72.0 best bundled run on a code-heavy mix).
**Like-for-like, we are at parity** (our CPU 52.7 vs 53.7 TP2 official NVFP4).
**Where the gap really is: software efficiency.** The Sparks stream at ~80-85% of attainable bandwidth on one node (jschmied) and ~42% on two; our decode streams ~137-174 GB/s = 31-39% of our measured 446.8 read-sum (an identical ~31% on the plain path). At 60% of read-sum (268 GB/s) the same step bytes give roughly **80-100 tok/s** (23-29 steps/s x ~3.5 tokens/step) [derived estimate, assumes our MTP step bytes and tokens/step above].
Top levers (all operator-review candidates, none authorised): (1) raise effective streaming from ~140 toward 270+ GB/s (dispatch/barrier floor, ~7.9k graph nodes/token; existing INF-70 / AK-Q38FN lanes); (2) draft-head vocab trim: RETRACTED AS A LEVER on our CPU. Spark gains (+9.6% mean / +21.5% code x1, intake-1950/1956) do not transfer: our own B10 (cpu-decode-roofline-program.md, 2026-09-05) measured the head at ~4-5% of the token (L3-resident, derived 260 GB/s), 64k slice ceiling +3.0-3.9%, break-even on alpha, upstream #25187 +1.4%; only the no-code IQ4_XS head requant (+1.4-1.8% expected) remains. My earlier '~20% of step bytes' was wrong; (3) adaptive/deeper K with cheap GDN rollback (ours is O(1) rs_idx rollback already; their dynamic K<=7); (4) cap verify rows R (routed bytes are the main step term). Wave-4 ledger: the measured verify-window expert union is only 0.69/0.63/0.60 of independent routing at 4/8/16 rows (jschmied, author-measured, one traffic mix), so my independence-based 9.1-11.6 GB step estimate is an UPPER bound; a measured union could put our R=5 verify nearer ~3.4 GB of experts (total step ~7-8 GB) and raise the 80-100 tok/s estimate; (5) the 5-of-10 expert cut is a model change = operator decision package, not a lever to pull. Interconnect cost (17-65 us per all-reduce, ~106 collectives/step) is irrelevant to us.
Not established: our actual MTP step bytes and tokens/step (assumed from alpha and R); real routing correlation; no Q38FN run on MI210.

### ROCm 10.1 (operator addition; intake-1938 blog superseded by intake-1944 docs)
- ALREADY-HAVE: gfx90a MFMA int8/fp16/bf16, HIP graphs, rocWMMA FA are in production on 6.2; 10.1 adds no new CDNA2 capability. No gfx90a deprecation wording found; MI210/MI250/MI250X (gfx90a) listed in the 10.1.0 compatibility matrix.
- REBUILD: LLVM 23->24 (clang_major 24; our 6.2 is ~LLVM 18-era [knowledge]), `/opt/rocm/core-10.1` layout, amdrocm-* packages (hipcc into amdrocm-llvm, rocBLAS+hipBLASLt merged, rocWMMA into ccl-dev), rocm-smi removed (amd-smi), newer amdgpu driver/kernel (host reboot = operator), `HSA_NO_SCRATCH_RECLAIM=1` known issue on gfx90a with >=7.14 (RCCL). Tarball install allows side-by-side non-root.
- AK-HYPOTHESIS (unmeasured): LLVM 24 codegen on MMQ_MFMA/rocWMMA/graph launch is a toolchain axis, not a bandwidth lever; rocprofv3 `--hip-graph-trace` per-graph-node attribution (10.0).
- KNOWLEDGE: no FP8/FP4 on CDNA2; rocWMMA 2.2.1 / hipBLASLt 1.4.1 unchanged; CK changes target gfx11/12/950; vLLM 0.29 / SGLang 0.5.18 gfx lists exclude gfx90a; graph-safe table marks rocWMMA/CK not graph-safe (docs label, contradicts our working use); no 10.1 system-requirements page resolved.
- Bearing on the Q38FN physics / MI210 decode efficiency: **nothing**.

### Derived-actionables ledger (proposed dispositions; nothing filed)
| # | Item | Proposed disposition |
|---|---|---|
| A1 | Physics-normalised comparison row (model variant, K, concurrency, bytes/step) for external Q38FN numbers | draft task, cpu-decode-roofline-program.md |
| A2 | Measure our MTP step bytes and tokens/step (write-side evidence first) to replace the assumed 9.1-11.6 GB / 3.5 | draft task, AK-Q38FN / roofline program |
| A3 | Reduced-draft-vocab probe on the llama.cpp MTP head (profile draft-step byte share first) | draft task, existing #25187 owner |
| A4 | Adaptive/deeper MTP depth with R-capped verify; GDN state-write cost arithmetic (state bytes x layers x K) | AK hypothesis |
| A5 | 5-of-10 expert cut as quality/speed trade | operator decision package only |
| A6 | ROCm 10.x side-by-side experimental build probe (MMQ_MFMA/rocWMMA/graphs) | monitor; trigger = operator scopes a v11 build |
| A7 | Add bandwidth back-calculation and saturation diagnostics to our measurement practice | knowledge/measurement handoff (draft) |
| A8 | Check Q38FN draft-vocab coverage vs our traffic mix; hybrid-GDN prefix-cache chunk alignment | draft task |

### Stage-2 close-out: dive-surfaced sources not dived (operator selects; recommendation each)
Decline unless stated: ai-muninn Part 46 baseline post (setup already in 1958); MiaAI PR #45 / draft-vocab tool (README-level evidence in 1950/1956); ashhart/TensorFold upstream (no byte-floor docs expected); llama-benchy (tool, no data); jschmied the-field.md and unread remainder of speed-of-light.md L310-630/L745+ (INGEST-AND-DIVE recommended only if the operator wants the full GB10 byte ledger); hibrid48 HF card (claim already in 1937); Intel W4A16-AutoRound card; TheRock supported-GPUs page (long-term MI210 horizon; optional); NVIDIA forum thread 382522 (aggregator). Declines are recorded in the bearing entries' dive_corrections. Stage 3 does not begin until the operator closes this gate.

### Steering ledger
3 rows retained verbatim (dive policy; physics requirement; ROCm 10.1 addition), dispositions context-only / planned / planned, plan_ref null until Stage 3.
