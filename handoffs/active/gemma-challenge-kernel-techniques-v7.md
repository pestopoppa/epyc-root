# Gemma-Challenge Kernel Techniques → v7-Experimental Candidates

**Status**: active — onegraph structural check ✅ (re-audited) + HIP graph infra verified ✅ + **K2 MI210 smoke-test/bench ✅ (2026-07-11)**. K2: per-decode HIP graph capture engages on MI210 and is net-positive on Q8 (A4B MoE decode +4.3% / **spec-dec +25%**; dense-31B +6.1% / +3.4%) — but A4B **Q4** spec-dec regresses ~−5%. **K7 root-caused it: the thrash is VERIFY-side** (target verify batch = n_drafted+1 varies with acceptance → warmup resets), NOT the draft loop (which is already shape-stable and replays). The candidate fix **Lever A — a shape-aware graph cache key** was implemented (env-gated) but a clean quiet-host re-eval measured it **NEUTRAL** (Q8 spec-dec −2% with byte-identical output → correctness-safe, no speedup; Q4 +6% noisy) → **NOT landed**, source reverted, preserved as `llama.cpp-experimental/lever-a-shape-key.patch`. The **onegraph single-graph fold is DEFERRED** (very-high effort, lower-EV — it fuses the already-optimal draft decodes, not the verify thrash). GRAPH_OPT=1 and Q8_PREFETCH levers both tested → net-negative, rejected. Also validated graphs generalize beyond gemma4 (Qwen dense/MoE base decode +7–14%; native-MTP spec-dec only +2%, so the +25% is gemma4-external-head-specific). **2026-07-16 v7 cleanup:** K14 HIP backend-ops blocker is resolved in the `experimental-v7-candidate` worktree with flash-attn selector/device-guard fixes; full `test-backend-ops` now passes on MI210. `ngram-mod` retest shows workload-dependent speed upside but is not quality-cleared. **2026-07-16 v7 perf/server A/B:** refreshed candidate `8e5c555ab` passed the backend gate earlier, the direct base-decode report and server artifacts now capture production-shaped perf, and the launcher guard landed in orchestrator so stack-launched llama-server commands always pin `--device none` and speculative launches also pin `--device-draft none`. **2026-07-16 v7 K5/readiness checkpoint:** the fixed chat-endpoint harness under `epyc-inference-research` reran K5 successfully, the invalid old `/mnt/raid0/llm/tmp/v7-quality-20260716/` raw `/v1/completions` attempt was discarded as a protocol error, the valid chat artifacts are stored under `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/`, and the no-inference stack-change promotion gate passed after refreshing generated artifacts. Scope: lossless only. Remaining hard blockers are the open promotion decision and any future promotion evidence; the K5 quality baseline and readiness/server smokes for this checkpoint are now closed.
**Categories**: speculative_decoding, hardware_optimization, quantization, local_inference
**Source**: intake-798 — "The Gemma Challenge and the Case for Agent Collabs" (HF + Google DeepMind)
**Related**: [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) (onegraph deep-dive lives here), [`gpu-drafter-mi200-investigation.md`](gpu-drafter-mi200-investigation.md) (GPU-graph home), [`v6-iqk-promotion.md`](v6-iqk-promotion.md) / [`kernel-reconciliation-audit.md`](../completed/kernel-reconciliation-audit.md) (the v7 workflow), [`gemma4-mtp-drafter-evaluation.md`](../completed/gemma4-mtp-drafter-evaluation.md)

## Objective

The Gemma Challenge (100+ agents, 6 days) drove `google/gemma-4-E4B-it` inference 5× — the **same MTP-drafter family and model family as our production `worker_general`** (gemma-4-26B-A4B, Google official assistant head). **v7 was never promoted to production**, so the `llama.cpp-experimental` line is a clean slot to fold the *validated, quality-preserving* subset of these techniques into a v7 candidate — via the mandated four-step experimental workflow (fresh-pull production → build → validate-no-regression → promote), never touching frozen production kernels.

## Governance rails (non-negotiable, per CLAUDE.md)

- **Production kernels are FROZEN.** All work on `llama.cpp-experimental` (fresh-pulled from current production tip first, so the iqk AVX-512 GEMM + CPU forward-ports are already present — do not repeat the 2026-06-22 GPU-opts fork that silently lacked the entire iqk subsystem).
- **Quality gate is the gate, not TPS.** The challenge's own lesson: a **PPL-only** gate was gamed (top lossy submission held PPL but lost **15 GPQA-Diamond / 40 MMLU-Pro** points). Any v7 candidate must pass downstream evals (MMLU-Pro + GPQA-Diamond), production sampling (seed 42), per [`MEASUREMENT.md`](../../MEASUREMENT.md) + eval-tower — **not** PPL alone. This is a hard prerequisite, especially for the lossy techniques below.
- **Inference is operator-gated** (`feedback_no_concurrent_inference`); bench only via codified recipes with approval.

## Technique candidates (from intake-798 submissions)

| Technique | Lossy? | Our-regime fit | v7 workflow slot | Open question |
|---|---|---|---|---|
| **`onegraph`** — drafter is Q-only, KV-shared, no cross-position deps ⇒ multi-position warm-up is redundant; fold warm-up into the 7-step drafting loop, record as ONE GPU graph, single-launch replay | **Lossless** (no output change) — fastest lossless: 315 TPS | GPU-drafter path (MI210/HIP graphs) directly; **structural insight may port to CPU** MTP drafter loop | GPU-graph capture → `gpu-drafter-mi200-investigation.md`; CPU-warm-up-redundancy → `speculative-decoding-mtp-refresh.md` | **✅ STRUCTURAL + HIP INFRA ✅ (2026-07-11)**: P1-P3 satisfied. HIP graph capture already implemented (vendor-agnostic, `GGML_HIP_GRAPHS=ON` default, CDNA2 >> AMPERE arch gate). Draft loop at `speculative.cpp:1663-1667` is structurally uniform — graph-capturable. **Remaining: smoke-test + benchmark on MI210.** |
| **Task-targeted fine-tuned drafter** — drafter fine-tuned on the eval's math/science prompt distribution to raise acceptance rate α | Lossy **as executed** (overfit to eval set); the *method* (raise α on our real workload) can be lossless | CPU + GPU spec-dec; raises α for both | Drafter-training track (new); gate via rescue-rate on real task corpus | Can we lift α on our real frontdoor/worker workload without overfitting? (`feedback_measure_alpha_before_specdec_investment` — measure α first; `frontier-f1-real-task-corpus.md` for the distribution) |
| **CUDA-graph capture throughout decode** — capture the decode routine as a replayable graph to cut per-step launch/bookkeeping overhead | Lossless (kernel-level) | GPU only (HIP graph equivalent on MI210) | `gpu-drafter-mi200-investigation.md` / `gpu-acceleration-path.md` | **✅ HIP GRAPH INFRA PRESENT (2026-07-11)**: vendor-agnostic, complete API mapping. Overlaps with `onegraph` — same infrastructure. **Remaining: benchmark decode + MTP paths on MI210.** |
| **Vocabulary pruning** — drop rarely-used vocab rows to shrink the output projection / embedding | **Lossy** (contributed to the 15/40-pt degradation) | Applies to any regime, but degrades downstream | Explore-only, hard-gated on MMLU-Pro/GPQA | Is there a *lossless* vocab-prune band (truly-dead tokens only) that survives the downstream gate? High risk. |
| **Layer removal / depth pruning** | **Lossy** (part of the 491.8-TPS lossy stack) | Any regime, degrades quality | Explore-only, hard-gated; likely reject | Almost certainly fails our quality gate; document as a cautionary boundary, low priority. |

## Prioritization (proposed, operator to confirm)

**Scope: lossless only.** Numerical-exactness is acceptable where bit-exactness is not achievable (per past-session precedent). Lossy techniques (vocab prune, layer removal) are OUT OF SCOPE.

1. **`onegraph` GPU-graph capture** (lossless, highest value): **structural check ✅ + HIP infrastructure ✅ (2026-07-11)**. All 3 preconditions satisfied. HIP graph capture is already implemented (vendor-agnostic, `GGML_HIP_GRAPHS=ON` default, MI210 arch gate passes). **Next: smoke-test + benchmark on MI210** — verify graph capture works with MTP draft loop, measure per-token graph launch latency vs. direct dispatch. Coordinate with `gpu-drafter-mi200-investigation.md`.
2. **Drafter-α uplift** (potentially lossless): measure current α on the real task corpus before any fine-tuning investment; only pursue if α headroom is real and generalizes beyond the eval set.

## Tasks

- [x] **K1 — `onegraph` precondition check**: verify the Q-only / KV-shared / no-cross-position preconditions hold for our gemma-4-26B-A4B assistant-head drafter ✅ 2026-07-11 — all 3 satisfied
- [x] **K2 — HIP graph smoke-test + benchmark on MI210 ✅ 2026-07-11**: verified on the existing `build-hip` (`46f876c12`, `GGML_HIP_GRAPHS=ON`, ROCm 6.2 — **no rebuild needed**). HIP graph capture engages on MI210 gfx90a; gemma-4-26B-A4B MoE + gemma-4-31B dense both run correctly on HIP under MTP (~83–88% draft accept, output byte-identical graphs on/off). Graph A/B (`GGML_CUDA_DISABLE_GRAPHS`): **Q8 A4B decode +4.3% / spec-dec +25%**; dense-31B Q8 +6.1% / +3.4%; A4B **Q4 spec-dec −5% (graphs hurt — re-capture thrash)**. See "K2 Empirical Results" below. Per-decode capture only — the onegraph single-graph fold is still unimplemented.
- [x] **K3 — CPU warm-up-redundancy test ✅ 2026-07-11 (answered by the K1 audit — no action available)**: the onegraph insight is "the multi-position drafter warm-up is redundant." Our audit (Warm-up vs Draft Loop Equivalence, above) found that for the gemma4 `is_mem_shared` drafter the warm-up is **already zero-drafter-compute** (the catch-up decode block at `speculative.cpp:~1465` is entirely elided; only hidden-state copies remain). So there is **no redundant drafter warm-up to remove** on the CPU worker — it is already optimal. No CPU win available from this lever.
- [ ] **K4 — drafter-α baseline**: measure current acceptance α on the real task corpus ([`frontier-f1-real-task-corpus.md`](frontier-f1-real-task-corpus.md)) BEFORE any fine-tuned-drafter investment (`feedback_measure_alpha_before_specdec_investment`)
- [x] **K5 — quality-gate wiring ✅ 2026-07-16**: implemented `MMLUProAdapter` (TIGER-Lab/MMLU-Pro, 12K questions, 10-choice A-J) + `v7_quality_gate_runner.py` (eval runner) + `v7_quality_gate_compare.py` (regression comparator). The fixed chat-endpoint harness under `epyc-inference-research` reran the gate successfully; the earlier raw `/v1/completions` attempt in `/mnt/raid0/llm/tmp/v7-quality-20260716/` was aborted as a Content-only protocol error and is not evidence. Valid artifacts: `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/v6-production-worker-general.json`, `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/v7-candidate-worker-general.json`, and `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/v7_quality_gate_report.md`. Result: endpoint=`chat`, errors=`0`; v6 MMLU-Pro `73/200=36.5%`, GPQA `50/195=25.6%`; v7 candidate `8e5c555ab` MMLU-Pro `73/200=36.5%`, GPQA `50/195=25.6%`; comparator `PASS`, deltas `+0.0%` on both suites versus the `-5pp` threshold.
- [x] **K6 — `GGML_CUDA_GRAPH_OPT=1` lever ✅ 2026-07-11**: benchmarked on MI210 → **REJECTED** (net-negative: Q8 base −16%, spec −11%). Leave off (default).
- [x] **K7 — onegraph/shape-cache investigation + Lever A ✅ 2026-07-11**: Lever A (shape-aware graph key) implemented env-gated → **NEUTRAL** (Q8 −2% byte-identical output, Q4 +6% noisy); not landed, reverted to `llama.cpp-experimental/lever-a-shape-key.patch`. Onegraph (Lever B) **DEFERRED** — verify-side reframe + depth sweep confirm low EV; full impl plan persisted. Retracted the noisy "n_max 2→4 +20%" (clean data: n2≈n4). See "Kernel-Optimization Levers".
- [x] **K9 — non-gemma4 graph generalization ✅ 2026-07-11**: Qwen3.6-27B (dense hybrid) + Qwen3.6-35B-A3B (MoE), native MTP. Base decode **+7–14%** (generalizes); native-MTP spec-dec only **+1.8–2.5%** (the +25% is gemma4-external-head-specific); Qwen native-MTP deterministic under load. See "Non-gemma4 generalization".
- [ ] **K10 — (follow-up) Lever A quiet-host re-eval**: on a quiesced host (fresh-server/run, `fprintf(stderr)` keylog to confirm the `nodes[0]` collision first), decide land/drop. Only pursue if verify re-capture proves a *measured* bottleneck.
- [ ] **K11 — (follow-up) root-cause the gemma4 external-head MTP non-determinism under load**: intermittent run-to-run output drift at temp0/seed42 (async D2H-copy race); Qwen native-MTP is unaffected. Low-grade correctness/repro flag.
- [x] **K12 — `GGML_CUDA_Q8_PREFETCH` 0/1/2 benchmark ✅ 2026-07-11**: net-negative on all 4 Q8 models → keep OFF (default). Dense hurt most (Qwen-27B −12/−18%, gemma4-31B −6/−7.5%); MoE marginal/noisy (gemma4-A4B −3.5/−0.3%, Qwen-35B-A3B +4.2/+3.1%). qwen-27b server relaunched graphs-ON + prefetch-off + MTP (draft-mtp n-max 3, ~91% accept). See "Kernel-Optimization Levers → Q8_PREFETCH".
- [x] **K14 — v7 HIP backend-ops failure triage ✅ 2026-07-16**: resolved the MI210 `test-backend-ops` abort in `experimental-v7-candidate` with scoped flash-attn selector/device-guard fixes in `fattn.cu`, `fattn-tile.cuh`, and `fattn-mma-f16.cuh`. Focused validation passed for the 192/128, 256/256 short-KV, 320/256, and BF16 hsk64 families; full HIP validation passed with candidate `LD_LIBRARY_PATH`: `ctest --test-dir build-hip/tests -R '^test-backend-ops$' --output-on-failure` → `100% tests passed, 0 tests failed out of 1`, `722.34 sec`. A transient `SOLVE_TRI` tolerance miss was isolated to HIP `hipblasStrsmBatched` randomness; the exact case passed 20/20 repeats and the full rerun passed, with no `SOLVE_TRI` code/test tolerance change.
- [x] **K15 — ngram-mod retest on MI210 ✅ 2026-07-16**: quiet-card retest on `4e9287eb3` shows workload-dependent speed upside. Qwen2.5-Coder-0.5B repetitive JSON edit: `292.5 -> 347.7 t/s` (+18.9%). Gemma-4-26B-A4B Q4 with default reasoning: `85.4 -> 85.8 t/s` (flat, because output was reasoning text). Gemma-4-26B-A4B Q4 with `--reasoning off`: `85.7 -> 129.1 t/s` (+50.6%). **Caveat:** outputs were not token-identical and both Gemma arms had JSON/key errors, so this is speed evidence only; do not enable by default without task-level quality/acceptance checks.
- [x] **K16 — orchestrator worker combined ngram→MTP launch ✅ 2026-07-16**: deployed the conservative single-server policy instead of redundant lanes. `worker_general` / `worker_math` / `toolrunner` now launch one combined speculative stack, `--spec-type ngram-mod,draft-mtp`, on ports `8072`, `8082`, `8182`, `8282`, and `8382`; live cmdlines verified at PIDs `1053926`, `1054354`, `1054723`, `1055049`, and `1055416`. Source of truth is the research master registry plus regenerated lean registry, descriptors, stack priors, and operator summary. AutoPilot remains stopped. This is not a planner tunable yet; task-level quality/acceptance monitoring decides whether the combined default stays.

## GPU Graph Capture Feasibility (2026-07-11)

**Verdict (refined 2026-07-11 after K2 measurement): per-decode HIP graph capture is ALREADY SUPPORTED (no port) and empirically net-positive on the MI210; the onegraph *single-graph fold* is a separate optimization that is NOT yet implemented.** The `experimental-v7-candidate` branch has a complete, vendor-agnostic graph capture infrastructure that maps 1:1 from CUDA to HIP. **Important distinction:** this infra captures each `llama_decode` call independently (cache key = `cgraph->nodes[0]`), so the draft loop's N single-token decodes are captured/replayed *per step* (after a 2-call warmup). The onegraph technique — fold the warm-up + the whole N-step draft routine into ONE captured-once, single-launch graph — is a *speculative-aware* capture feature that this infra does NOT provide; K1 confirms the draft loop is structurally uniform (single sequence), so building it is feasible but is real work, not just a flag flip.

### Existing Infrastructure

| Component | Location | Status |
|---|---|---|
| HIP graph API mappings | `ggml/src/ggml-cuda/vendors/hip.h:124-145` | Complete — 1:1 `#define` aliases, ~20 CUDA graph APIs mapped |
| USE_CUDA_GRAPH gate + graph struct | `ggml/src/ggml-cuda/common.cuh:1203-1238` | `#if defined(GGML_HIP_GRAPHS) → #define USE_CUDA_GRAPH` (1203-1205); `ggml_cuda_graph` struct (1207-1238) with `warmup_complete`, UID, node-property comparison, `is_enabled()` |
| Capture + replay flow | `ggml/src/ggml-cuda/ggml-cuda.cu:4468+` | `ggml_backend_cuda_graph_compute`: capture → instantiate → launch → `GraphExecUpdate` fast path |
| CMake enable | `ggml/CMakeLists.txt:216` + `ggml-hip/CMakeLists.txt:109-110` | `GGML_HIP_GRAPHS=ON` by default → `add_compile_definitions(GGML_HIP_GRAPHS)` |
| MI210 arch gate | `ggml-cuda.cu:4456` | gate is `cc < GGML_CUDA_CC_AMPERE(800)`; MI210 `cc = 0x1000000+0x90a = 0x100090a` (CDNA2) ≫ 800 ⇒ arch disabler **cannot** trip. **Verified live: graphs engage (+4.3% Q8 decode / +25% Q8 spec-dec).** |

### Speculative Decoding Integration

Graph capture operates transparently at the backend level (`llama_decode` → `encode` → `graph_compute` → `ggml_backend_cuda_graph_compute`). No speculative-specific graph logic exists — the graph captures whatever `ggml_cgraph` is submitted. **This is the onegraph opportunity**: the `is_mem_shared` draft loop's uniform body means the same graph shape across iterations, maximizing cache hits.

### Known Limitations / disabling conditions (independently audited + corrected 2026-07-11)

- **Split buffers** disable graphs entirely (multi-GPU layer splitting) — N/A on a single MI210.
- **`MUL_MAT_ID`** disables graphs **only** if experts are non-quantized **or** `ne[2] > mmvq_mmid_max`. `ne[2]` = n_tokens in the (u)batch (`ggml.c:3305`); `mmvq_mmid_max` = **8** for Q4_K/Q6_K/Q8_0 on CDNA2 (4–5 for IQ2\*/IQ3\*). ⇒ **single-token draft/decode (`ne[2]=1`) with quantized experts does NOT trip this** — the quantized gemma4 **MoE keeps graphs during decode** (confirmed empirically: +9.4% Q4 / +4.3% Q8). Only large target-verify batches (>8 tok, or >4–5 for IQ2/IQ3) or F16 experts disable it. *(The prior "MUL_MAT_ID disables graphs" wording was too broad — it does not apply to the decode path we care about.)*
- ~~Requires ROCm 5.7+~~ — **NOT code-backed** (audit): no ROCm/HIP version guard exists on graph enabling; graphs are gated solely by the build flag `GGML_HIP_GRAPHS` (default ON). Host runs ROCm 6.2.0 regardless.
- Two disablers the prior list omitted: `GGML_CUDA_DISABLE_GRAPHS` env (`common.cuh:1234` — this is the A/B toggle we used) and the `cc < AMPERE` arch gate (`ggml-cuda.cu:4456`, cannot trip on MI210 — favorable).
- **Warm-up transient (the key runtime caveat):** a graph needs **2 stable calls** to finish warm-up, and any shape/property change resets it (`ggml-cuda.cu:4488+`). The cache key is the `nodes[0]` pointer, but shape changes are detected by per-node `memcmp` and force a re-capture (no wrong-shape replay). So mixed-batch workloads pay repeated re-capture cost — which is exactly what the onegraph single-graph fold would eliminate.

### Effort (validation-only, not port)

Smoke-test on MI210: ~1 day. Validate + benchmark with MTP: 2-3 days.

## Onegraph Structural Verification (2026-07-11)

**Verdict: ALL THREE preconditions SATISFIED.** The gemma4 assistant drafter on our fork (`experimental-v7-candidate`) is structurally eligible for the onegraph optimization.

> **Independent re-audit (2026-07-11):** all three preconditions were adversarially re-verified against source (6-agent audit); P1/P2/warm-up-equivalence CONFIRMED, P3 CONFIRMED-but-regime-scoped (see below). Minor citation drift to fix in reading the code: P1 projections are at `gemma4-assistant.cpp:62-63` (line 61 is `attn_norm`); P2's KV-view block spans `llama-kv-cache.cpp:190-206` (not `-198`). Substance unaffected.

### P1: Q-only — SATISFIED

`src/models/gemma4-assistant.cpp:61-63`: only `wq` and `wo` tensors per layer (no `wk`/`wv`). Forward pass at `:143-154` calls `build_attn` with `nullptr` for K and V. `llama-graph.cpp:2596-2606` skips KV store when `k_cur`/`v_cur` are null — reads K/V from shared cache only.

### P2: KV-shared — SATISFIED

`src/llama-model.cpp:2169-2197`: `GEMMA4_ASSISTANT` creates `llama_kv_cache_iswa` with `mem_other` = target model's memory and a `share` callback mapping assistant layers to target layers. `src/llama-kv-cache.cpp:190-198`: when `share` is set and `other` is non-null, K/V tensors are direct views into the source cache. `speculative.cpp:1370`: `is_mem_shared = llama_get_ctx_other(ctx_dft) == ctx_tgt` evaluates true.

### P3: No cross-position dependencies — SATISFIED (scoped to the `is_mem_shared`/gemma4 branch)

`speculative.cpp:1663-1667`: every draft token decodes at the **same position** `dp.n_past`. No `seq_rm`, no KV rebuild, no batch prefix — just a single-token decode at the fixed position with the h-row carryover. Each step consumes `(token, h_row)` and produces `(token, h_row)` where `h_row` comes from `llama_get_embeddings_nextn_ith`.

> **Scope correction (audit 2026-07-11):** this property holds **only** for the `is_mem_shared` (gemma4 assistant) branch — which *is* the drafter we use. The same `draft()` function has two other branches that are NOT position-static: the growing-KV `else` branch (`:1669`) advances `dp.n_past + i + 1` per iteration, and the `chain_heads` branch (qwen35 multi-MTP-head) does `seq_rm` (`:1593`) + a full-prefix batch rebuild every iteration. So "no cross-position deps in the draft loop" is a **regime-specific** statement, not a universal one — correct for gemma4, false for the qwen MTP regimes. (Also note: even the gemma4 branch has non-*position* cross-iteration state — sampler-accept state, `i_last`, and repeated overwrite of the same shared KV cell — which is fine for onegraph but means "each step is fully independent" is an over-simplification.)

### Warm-up vs Draft Loop Equivalence

- **Warm-up (`process()`, `:1430-1546`)**: for `is_mem_shared`, the catch-up decode block (`:1465`) is **entirely skipped** — only copies hidden states from the target (`:1527-1543`). **Zero drafter compute.**
- **Draft loop (`draft()`, `:1548-1697`)**: uniform single-token decode at `dp.n_past` per iteration (`:1663-1667`). Batch is cleared and rebuilt each iteration. **No structural difference between first and subsequent iterations** — every step runs the identical graph with only data values changing.

**Implication for GPU-graph capture**: the draft loop's uniform body is exactly what the onegraph optimization requires. A HIP graph captured for one iteration is replayable for all iterations — the only state that changes is the input token + h-row, which are external to the graph (batch embeddings). The CPU path is already optimal (minimal decode at fixed position, no warm-up overhead).

## v7 Kernel-Optimization Performance Tables (consolidated, 2026-07-11)

**All observation-grade** (MI210 gfx90a, ROCm 6.2, `build-hip`; temp0/seed42, decode t/s; %Δ vs graphs-OFF baseline). Levers: OFF=`GGML_CUDA_DISABLE_GRAPHS=1` · ON=default · OPT=`GGML_CUDA_GRAPH_OPT=1` · KEY=`GGML_CUDA_GRAPH_SHAPE_KEY=1` (Lever A, env-gated experimental edit).

**Base decode** (llama-bench, -p128 -n256 -r3):

| model | quant | OFF | ON (default) | OPT=1 | KEY=1 (Lever A) |
|---|---|---|---|---|---|
| A4B MoE | Q8 | 79.05 | **82.45 (+4.3%)** | 68.81 (−16%) | n/t (Lever A targets spec-dec) |
| A4B MoE | Q4 | 80.8 | 88.3 (+9.4%) | — | — |
| dense-31B (gemma) | Q8 | 23.42 | 24.84 (+6.1%) | — | — |
| **Qwen3.6-27B** (dense hybrid SSM, native MTP) | Q8 | 28.24 | 30.27 (**+7.2%**) | — | — |
| **Qwen3.6-35B-A3B** (MoE, native MTP) | Q8 | 85.20 | 97.08 (**+13.9%**) | — | — |

**MTP spec-dec** (llama-server, chat temp0, 3 reps):

| model | quant | OFF | ON (default) | OPT=1 | KEY=1 (Lever A) |
|---|---|---|---|---|---|
| A4B MoE | **Q8** | ~86.5 | **~108 (+25%)** | ~96 (−11%) | 107.2 (−2%, output-identical†) |
| A4B MoE | Q4 | ~112 | ~104 (**−5%**) | ~115 | ~116 (+6%†, noisy) |
| dense-31B (gemma) | Q8 | ~35.2 | ~36.4 (+3.4%) | — | — |
| **Qwen3.6-27B** (dense, **native** MTP) | Q8 | 47.0 | 47.9 (**+1.8%**) | — | — |
| **Qwen3.6-35B-A3B** (MoE, **native** MTP) | Q8 | 103.4 | 105.9 (**+2.5%**) | — | — |

Takeaways: graphs (default ON) are the win on Q8 — biggest on the fast A4B MoE spec-dec (+25%, = production worker regime); GRAPH_OPT is net-negative (rejected); the A4B Q4 spec-dec −5% is the verify-side re-capture thrash that Lever A targets (see "Kernel-Optimization Levers").

**†** Lever A (KEY=1) clean re-eval (quiet card, strictly sequential, fresh-server/run): Q8 = −2% with **byte-identical output** (correctness-safe, no speedup); Q4 = +6% but noisy (2 output variants). **Neutral → not landed**; source reverted, preserved as a patch. See the Lever A result below.

**Non-gemma4 generalization (2026-07-11):** graphs-ON benefits **non-gemma4 models too**, but the magnitude splits by *what* is being accelerated:
- **Base decode: helps every model tested** — +7.2% (Qwen3.6-27B dense hybrid), +13.9% (Qwen3.6-35B-A3B MoE), alongside gemma's +4–9%. Generalizes cleanly; magnitude scales with launch-overhead-fraction (fast/MoE > slow/dense).
- **Spec-dec: the big win is drafter-architecture-specific.** gemma4's **external assistant-head** drafter gets **+25%** (a separate tiny-model decode per draft step → launch overhead dominates → graphs amortize hugely). Qwen's **native NEXTN-MTP** head gets only **+1.8–2.5%** (draft folded into the main forward → little separable launch overhead to amortize). So "graphs give +25% on spec-dec" is a **gemma4-external-head property, not a universal MTP one**.
- **Determinism:** the Qwen **native-MTP** path is fully deterministic (ON==OFF byte-identical, even at load 164); the **load-sensitive non-determinism is specific to gemma4's external-head + shared-KV path**. Useful diagnostic narrowing of the race.

## K2 Empirical Results — MI210 HIP graph A/B (2026-07-11)

**Setup**: existing `llama.cpp-experimental/build-hip` (HEAD `46f876c12`, `GGML_HIP_GRAPHS=ON`, Release) — **no rebuild needed**. MI210 gfx90a (`cc 0x100090a`), ROCm 6.2.0, sole ROCm device, otherwise idle. Toggle: default (graphs ON) vs `GGML_CUDA_DISABLE_GRAPHS=1` (direct dispatch). Base decode via `llama-bench -ngl 99 -dev ROCm0 -fa on -p128 -n256 -r3`; MTP spec-dec via `llama-server` (`--spec-type draft-mtp --spec-draft-n-max 2`, target+assistant-v6 head both `-ngl 99` on ROCm0) driven by chat-templated `/v1/chat/completions`, temp0/seed42 (deterministic → **both arms emit byte-identical, coherent output** — graphs are numerically transparent), 3 reps. **All numbers are OBSERVATION-grade** (single-config, small-n, MEASUREMENT.md) — they characterize the graph subsystem; they do NOT gate a promote decision (that is a later v6→v7 session).

| model | quant | workload | graphs ON | graphs OFF | Δ from graphs | reliability |
|---|---|---|---|---|---|---|
| gemma-4-26B-A4B (MoE) | Q8_0 | base decode | 82.45 t/s | 79.05 t/s | **+4.3%** | tight (±<1) |
| gemma-4-26B-A4B (MoE) | **Q8_0** | **MTP spec-dec** | **~108 t/s** | **~86.5 t/s** | **+25%** | tight, reliable |
| gemma-4-26B-A4B (MoE) | Q4_K_M | base decode | 88.3 t/s | 80.8 t/s | +9.4% | tight |
| gemma-4-26B-A4B (MoE) | Q4_K_M | MTP spec-dec | ~104 t/s | ~112 t/s | **−5%** (graphs *hurt*) | noisier (±~7%), direction reproduced n=1 + n=3 |
| gemma-4-31B (DENSE) | Q8_0 | base decode | 24.84 t/s | 23.42 t/s | +6.1% | tight |
| gemma-4-31B (DENSE) | Q8_0 | MTP spec-dec | ~36.4 t/s | ~35.2 t/s | +3.4% | near noise floor |

**Findings**
1. **HIP graph capture works and engages on the MI210** (gfx90a) — the non-zero, output-transparent A/B delta proves it (if graphs were silently gated out, ON==OFF). gemma-4-26B-A4B MoE **and** gemma-4-31B dense both run correctly on the HIP path (coherent output; MTP ~83–88% draft accept), so gemma4 on HIP is validated, not just Qwen native-MTP.
2. **Q8 (the MI210 focus quant) is net-positive everywhere**, and the win is **largest on the fast A4B MoE spec-dec path (+25%)** — exactly our production `worker_general` regime. Interpretation: graph benefit ≈ launch-overhead ÷ per-token time. The A4B MoE decodes fast (~3.8B active params → short kernels) so fixed launch overhead is a large fraction → big win; spec-dec adds many small draft/verify kernels → amplifies it.
3. **Dense models benefit too, but far less** (31B: +6.1% decode / +3.4% spec-dec). The 31B reads all 31B params/token → BW-bound, long kernels → launch overhead is a tiny fraction → small graph win. So the graph/onegraph lever matters *most* for the fast MoE worker and *least* for heavy dense models.
4. **The benefit is NOT universal — it is workload×quant dependent.** A4B **Q4** spec-dec is a small **regression** (graphs ~−5%), while A4B **Q8** spec-dec is +25%. The most likely mechanism: the pointer-keyed, non-shape-aware cache re-captures on every draft↔verify batch-shape switch (warm-up-transient reset); when per-kernel compute is cheap (Q4), that re-capture cost outweighs the launch savings. This is precisely the thrash the onegraph single-graph fold removes — and the concrete evidence that "just enable graphs on the spec-dec path" is the wrong move.

**Bottom line for the handoff's earlier verdict**: "HIP graph capture ALREADY SUPPORTED, no port" is confirmed for *per-decode* capture and is a real, free win on the MI210 Q8 MoE spec-dec path (+25%). The Q4 spec-dec regression and the remaining lever are analyzed in "Kernel-Optimization Levers" below — the on-target fix is a **shape-aware cache key** (Lever A), NOT the onegraph fold (Lever B), which a deeper analysis showed targets the already-optimal draft loop rather than the verify-side thrash.

**Harness lesson (recorded so it isn't rediscovered)**: an early spec-dec run produced garbage output and misleading t/s — root cause was the **test harness**, not the code: raw `/completion` prompts (no chat template) on a gemma4 *reasoning/instruct* model + a warm-up request polluting the slot. Correct method: chat-templated `/v1/chat/completions`, no warm-up, fresh slot. Speed was paired with a correctness check throughout ([[feedback_verify_test_method_before_calling_it_a_bug]], [[feedback_pair_speed_with_correctness_check]]).

**Next graph levers (not yet tested)**: (a) `GGML_CUDA_GRAPH_OPT=1` — the fork's extra fan-out/stream-reorder pass (off by default, `ggml-cuda.cu:4564`); (b) the onegraph single-graph capture feature itself; (c) whether the Q4 spec-dec regression closes under either.

## Kernel-Optimization Levers (K6/K7 investigation, 2026-07-11)

Three levers were scoped to improve on the raw K2 per-decode graph capture. Key reframing from the K7 code audit: **the A4B Q4 spec-dec regression is VERIFY-side, not the draft loop.** For single-seq gemma4/`is_mem_shared`, every *draft* decode is `n_tokens=1` at a fixed position → shape-stable → the per-decode graph already warms up and replays across draft steps (draft loop is already graph-optimal). The thrash is the *target verify* decode: `n_tokens = n_drafted+1` varies with acceptance each spec-dec step → the single shared cache slot's `warmup_complete` keeps resetting (`ggml-cuda.cu:4499-4502`) → verify runs eager. This reframes lever EV.

### Lever: `GGML_CUDA_Q8_PREFETCH` (fork CDNA2 dense-Q8_0-GEMV async weight-prefetch, `mmvq.cu:502`) — REJECTED (2026-07-11)
Compiled-in (`Q8_LDS_PREFETCH_COMPILED`), lossless/byte-identical, runtime `0`=off (default) / `1`=cached-DMA / `2`=SLC-streaming. Benchmarked 0/1/2 on all 4 Q8 models (MI210, llama-bench base decode, r5, graphs-ON): **net-negative — leave OFF.** Ironically it *hurts the dense models most* despite targeting dense GEMV: Qwen3.6-27B dense −12%/−18%, gemma4-31B dense −6%/−7.5%; MoE marginal/noisy (gemma4-A4B −3.5%/−0.3%, Qwen3.6-35B-A3B +4.2%/+3.1% — the two MoE disagree in sign → near noise). No consistent win; the experimental prefetch/LDS-double-buffer overhead outweighs the DMA-latency hiding on gfx90a for these shapes.

### Lever: `GGML_CUDA_GRAPH_OPT=1` (fork fan-out/stream-reorder pass) — REJECTED
Env-only, `ggml-cuda.cu:4564`. Measured net-negative on MI210: A4B **Q8 base decode −16%** (68.8 vs 82.5 t/s), **Q8 spec-dec ~−11%** (~96 vs 108); Q4 spec-dec noisy/neutral (~115 vs 104 on / 112 off). Leave OFF (the default).

### Lever A: shape-aware graph cache key — IMPLEMENTED (env-gated), NEUTRAL on Q8 (clean re-eval) → not landed, patch preserved
The graph cache is a multi-entry map (`common.cuh:1404`) but keyed by `cgraph->nodes[0]` **pointer only** (`ggml-cuda.cu:3297`, shape-blind — the key exists to separate CPU/GPU split sub-graphs, not batch shapes). Draft (1-tok) and each verify (n_drafted+1) forward share the same reused `nodes[0]` buffer → collide on ONE slot → per-switch warmup reset = the −5% regression. **Fix (implemented as env-gated `GGML_CUDA_GRAPH_SHAPE_KEY=1`, default off = upstream behavior):** mix an FNV-1a shape signature (per-node `op`+`ne[]`, EXCLUDING data ptrs/nb) into the key so draft and each distinct verify batch-size get their own persistent, warm slot. `update_required()` still validates node_props + refreshes pointers every launch, so **correctness is unchanged — the key only selects the slot**. Change is one function (`ggml_cuda_graph_get_key`) + an env-gated `[SHAPE_KEY]` keylog diagnostic.

**Result (2026-07-11): NEUTRAL — NOT landed.** Built the env-gated change (compiles clean) and benchmarked twice. A first pass under host load ~95–102 (3 req/server) was confounded by load + a non-deterministic baseline → discarded. **Clean re-eval (operator-directed: quiet card, strictly sequential, fresh server per run, single request):** most configs became deterministic (3/3 reps byte-identical). **Q8 spec-dec: KEY=1 = 107.2 vs default 109.5 t/s (−2%), output byte-IDENTICAL to default** → the shape-key is **correctness-safe (numerically transparent) but gives no speedup** (slight regression, within noise). **Q4 spec-dec: KEY=1 = 115.8 vs 109.2 (+6%)** but Q4 stayed noisy (2 output variants) → not conclusive. Net: the verify-side thrash hypothesis does **not** produce a clear measurable Lever-A win; on the Q8 focus quant it's neutral-to-slightly-negative. The `[SHAPE_KEY]` keylog never fired (backend `GGML_LOG_INFO` filtered during decode) so the `nodes[0]` collision is **unconfirmed** — but KEY=1's identical output proves the change is at least safe. **Action: source reverted (v7-candidate pristine); preserved as `/mnt/raid0/llm/llama.cpp-experimental/lever-a-shape-key.patch`. Not worth landing on current evidence**; only revisit if a future profile shows verify re-capture is a *measured* bottleneck (fix the keylog to `fprintf(stderr,…)` first to confirm the collision).

### Draft-depth sweep + spec-dec non-determinism (2026-07-11, CORRECTED with clean data)

Swept `--spec-draft-n-max ∈ {2,4,6}` on A4B Q8 spec-dec to size onegraph EV. A first pass (loaded host, 3-req/server) suggested deeper=faster (n2→n4→n6 = 93→112→116 t/s) — but the **clean sequential re-eval REFUTED it as a load/non-determinism artifact:**

| n_max | decode t/s (loaded, discarded) | decode t/s (clean, median) |
|---|---|---|
| 2 | ~93 | **108.4** |
| 4 | ~112 | **104.1** (slightly slower) |

**Deeper drafts do NOT help on this workload** (the per-position accept-rate drop cancels the longer accept-length; n_max=2 is already near the ceiling). **RETRACTED: the earlier "raise n_max 2→4 for +20%" recommendation — it does not reproduce.** Still supports deferring onegraph — no draft-depth throughput headroom to capture, and the draft loop is already near its ceiling here.

**Spec-dec non-determinism (refined):** the gemma4 MTP HIP spec-dec path is **intermittently** non-deterministic at temp0/seed42 — it drifts every run under concurrent host load, but **mostly resolves when run strictly sequentially on a quiet card** (3/3 identical for Q8 in the clean re-eval; occasional single-flip for Q4). Consistent with a **load-sensitive race** in the async D2H-copy / backend-sampling path — NOT the Lever-A edit (inert when its env is unset), and NOT same-server slot carryover (fresh servers also flipped under load). Implication: every spec-dec A/B must run on a quiesced host, strictly sequential, fresh-server-per-run; the residual race is a low-grade correctness/repro flag worth a dedicated look ([[feedback_pair_speed_with_correctness_check]]).

### Lever B: onegraph — fuse the whole N-step draft routine into ONE replayable graph — DEFERRED (very-high effort, high risk, lower-EV than first framed)
**Why deferred (not just hard — lower value):** onegraph fuses the *draft* decodes, which are already shape-stable and replay via per-decode capture; it does **not** touch the verify-side variability that actually caused the K2 thrash. So Lever A is the on-target fix; onegraph's marginal EV is the N draft-step launch/sync overhead only.

**Why hard — the draft loop is host-in-the-loop** (`common/speculative.cpp:1582-1681`). Each iteration: `llama_decode` → `common_sampler_sample` opens with `llama_synchronize` (a hard full GPU→host block every iteration, `sampling.cpp:541`) → host reads sampled token (`get_sampled_token_ith`, `llama-context.cpp:961`) → host `p_min` early-exit + `n_max` break (data-dependent control flow, `speculative.cpp:1632/1646`) → host reads h_row (`get_embeddings_nextn_ith`) → host rebuilds batch + `memcpy` of h_row into `batch.embd` (`speculative.cpp:1666-1667`) → next `llama_decode` re-uploads H2D. `backend_sampling=1` removes the CPU softmax/argmax but NOT the host round-trip or the host control-flow.

**What a real implementation requires** (a speculative+backend co-design, NOT a local edit): (a) keep the sampled token on-device, wired directly into the next sub-step's input tensor (no D2H / `get_sampled_token_ith`); (b) keep h_row on-device, fed GPU→GPU into the next embd input (no `embd_nextn` D2H / CPU memcpy); (c) drop the data-dependent `p_min`/`n_max` early-exit → **fixed-N unroll**, pruning the over-drafted tail on host AFTER the single graph (**ROCm 6.2 on MI210 lacks CUDA-style conditional graph nodes, so variable-length drafting cannot live in-graph — fixed-N is forced**); (d) identical batch shape across all N sub-steps. Change sites: `speculative.cpp:1582-1681`, `llama-context.cpp:1316-1533/1580-1660` (new on-device output→input feedback path), `sampling.cpp:540-541/130-162` (bypass the per-iteration sync barrier), `ggml-cuda.cu:3297-3341/4468-4522` (capture the one large N-step cgraph).

**Correctness risks that make it high-risk:** (1) on-device token/h_row feedback bypasses the `get_sampled_token_ith`/`get_embeddings_nextn_ith` host contracts — and tensor *content* is NOT part of graph `node_props` (`ggml-cuda.cu:3322-3338`), so a wrong-but-same-shape buffer silently feeds stale state and is NOT caught by re-capture. (2) fixed-N changes draft-length semantics (always draft N then prune) — must exactly reproduce the old `p_min` draft set or the acceptance/output distribution shifts. (3) `chain_heads` MTP path (>1 mtp layer) grows the batch each iteration → inherently variable-shape → not an onegraph candidate; only the single-mtp-layer gemma4 `is_mem_shared` path qualifies. **Revisit only if Lever A does not close the thrash AND draft-launch overhead is then measurably the residual bottleneck.**

## V7 Quality Gate (K5, 2026-07-14)

**Motivation**: the Gemma Challenge's PPL-only quality gate was gamed — a lossy submission held PPL at ≤2.42 while losing **15 GPQA-Diamond / 40 MMLU-Pro points** relative to base. Any v7+ kernel candidate must pass multi-suite downstream evals before promotion, not PPL alone.

### Scripts

| Script | Path | Purpose |
|---|---|---|
| `v7_quality_gate_runner.py` | `epyc-inference-research/scripts/benchmark/` | Evaluates MMLU-Pro + GPQA-Diamond on a running llama-server, outputs per-suite accuracy JSON |
| `v7_quality_gate_compare.py` | `epyc-inference-research/scripts/benchmark/` | Compares candidate vs baseline JSON, applies regression threshold, outputs PASS/FAIL report |

### Usage

```bash
# 1. Measure v6 baseline (run once, reuse)
v7_quality_gate_runner.py --port 18072 --output v6_baseline.json \
    --suites mmlu_pro gpqa --n 200 --seed 42 --kernel v6-production

# 2. Measure v7 candidate
v7_quality_gate_runner.py --port 18073 --output v7_candidate.json \
    --suites mmlu_pro gpqa --n 200 --seed 42 --kernel v7-experimental

# 3. Compare (exit 0 = PASS, 1 = FAIL)
v7_quality_gate_compare.py --baseline v6_baseline.json \
    --candidate v7_candidate.json --output report.md \
    --regression-threshold 0.05
```

### Gate Criteria (default)

- **Per-suite**: candidate accuracy ≥ baseline accuracy - regression_threshold
- **Default threshold**: -5 percentage points (0.05)
- **Both suites must pass** (mmlu_pro AND gpqa)
- **Minimum sample**: 50 questions per suite (advisory warning below this)

### ⚠ Blocking: Operator Decisions Required

1. **v6 baseline measurement**: run `v7_quality_gate_runner.py` on the production v6 kernel with the models used in production. Store the output as the canonical baseline (e.g., `data/baselines/v6_quality_gate.json`).
2. **Threshold confirmation**: confirm or adjust the -5pp regression threshold. The challenge's gamed submission lost 15/40 points — -5pp catches moderate regression while allowing kernel noise. Tighter threshold (e.g., -3pp) is available but risks false positives on small samples.
3. **Sample size**: 200 questions per suite (seed 42) is the default. The eval tower's promotion mode uses N=200-500. Increase if statistical confidence is a concern.

### MMLU-Pro Adapter

- **Dataset**: `TIGER-Lab/MMLU-Pro` (test split, 12,032 questions)
- **Format**: 10-choice multiple-choice (A-J), harder than standard MMLU (4-choice)
- **Categories**: math, physics, chemistry, computer science, engineering, biology, health, economics, psychology, philosophy, history, law, business, other
- **Tiers**: T3 (STEM/professional), T2 (social sciences/humanities), T1 (business/other)
- **Registration**: `mmlu_pro` in `ADAPTER_SUITES` (research + orchestrator repos)

## Notes

- The challenge ran on A10G/GPU with E4B (small Gemma); our production worker is **CPU MTP on a 26B-A4B** with the MI210 as the GPU path — so GPU-graph techniques land on the MI210 drafter track, while the drafter-α and warm-up-redundancy *insights* are the CPU-transferable ones.
- All intake-798 numbers (315 / 491.8 TPS, ±15/40 eval deltas, PPL ≤ 2.42) are OBSERVATION-grade (challenge-internal, single-config, self-reported) — hypotheses only, re-measure on our stack before any keep/promote per MEASUREMENT.md.
- Submission-level detail (per-result `method` fields, taskforce notes) is available on the challenge leaderboard/bucket for a deeper follow-up if a technique graduates past the structural check.

## Research Intake Update — 2026-07-16 (Bonsai-27B / upstream Q2_0 gap)

From the 2026-07-16 research-intake deep-dive (intake-820/821/822, PrismML Bonsai-27B; details in [`tq3-quantization-evaluation.md`](tq3-quantization-evaluation.md) + `research/intake_index.yaml`):

**Finding — v7-candidate is MISSING upstream `Q2_0`.** llama.cpp added two sub-2-bit weight types, both authored by PrismML (`khosravipasha`) to run Bonsai: **`Q1_0`** (1-bit, PR #21273, merged **2026-04-06**) and **`Q2_0`** (ternary group-64, PR #24448 CPU merged **2026-07-07**, #25419 Metal; CUDA #25707 open). Verified enum state 2026-07-16: both `production-consolidated-v6` and **`experimental-v7-candidate`** have `GGML_TYPE_Q1_0` (=41) but **NOT `GGML_TYPE_Q2_0`**. Q2_0 merged **11 days after** the v6 cutover (2026-06-26), so v7-candidate — forked from that pre-Q2_0 tip — never inherited it. Same *stale-fork* class the governance rails warn about (the 2026-06-22 iqk near-miss).

**Recommendation — do NOT hot-cherry-pick Q2_0.**
- Do NOT patch Q2_0 into frozen v6, and do NOT hot-cherry-pick it into v7-candidate — that violates the "full build, validated together, not reconciled at promotion" rule.
- Correct path: the **next v7 experimental refresh must fresh-pull from a post-2026-07-07 upstream+production tip**, which brings Q2_0 (and any other post-cutover upstream work) in *automatically*, validated alongside iqk/CPU forward-ports. Treat "v7-candidate lacks Q2_0" as a **freshness-audit hit** — re-pull before any promotion regardless of Bonsai.
- Do NOT refresh *solely* for Q2_0: its only near-term use is Ternary-Bonsai-27B, and there is no ROCm/HIP Q2_0 path (CUDA PR still open) so on our MI210 it would be CPU-only anyway. Gate it on the Bonsai Q1_0 smoke-test (below).

**De-risked opportunity — Bonsai-27B `Q1_0` smoke-test.** Bonsai = quantized **Qwen3.6-27B**, whose hybrid Gated-DeltaNet arch is **already supported + exercised on this branch** (K9 ran Qwen3.6-27B native-MTP; `src/models/delta-net-base.cpp` present) and `Q1_0` is already in the tree — so a **`Bonsai-27B-Q1_0.gguf`** (~3.8 GB, staged 2026-07-16 at `models/bonsai-27b/`) is a cheap load/decode test on stock kernels. Open questions: (i) does PrismML's Q1_0 packing load without their custom fused hybrid-attention kernels, and (ii) quality (self-reported 76.1 avg, **independently contested** — HF gibberish/hallucination/load-failure reports; no third-party reproduction). Footprint/density experiment, hard-gated on the K5 MMLU-Pro/GPQA quality gate — NOT a quality win.

## V7 Refresh Checkpoint — 2026-07-16

- `experimental-v7-refresh-20260716` committed at `8e5c555ab` (`Refresh v7 candidate onto upstream master`).
- The refresh merged `origin/master` at `a8dc0e326` and restored upstream freshness, including `Q2_0` support.
- Previous K14 fix remains at `99f3fffd6` (`fix hip flash-attn backend-op coverage`).
- Build validation passed: `cmake --build build-hip --target ggml-hip`; `cmake --build build-hip --target llama-server llama-bench`.
- Focused validation passed: `LD_LIBRARY_PATH=build-hip/bin build-hip/bin/test-backend-ops -o EXPM1 -b ROCm0 -p type=f32` => `2/2`.
- Full validation passed: `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin ctest --test-dir build-hip/tests -R '^test-backend-ops$' --output-on-failure` => `Passed 734.97 sec, 100% tests passed`.
- Important fix details: kept all speculative enum cases (`ngram` + `DFLASH` + `draft-tree`), restored content-scoped slot media guard for Expected Attention compaction, added Q8 prefetch fusion predicate after the upstream refactor, and patched ROCm `EXPM1` positive overflow to return `+inf`.
- AutoPilot remains intentionally stopped; production kernel was not modified or promoted.

- [x] **K13 refresh checkpoint ✅ 2026-07-16**: upstream freshness was restored by `experimental-v7-refresh-20260716` (`8e5c555ab`) merged with `origin/master` `a8dc0e326`; `Q2_0` is now present again on the refreshed v7 candidate, with the K14 backend-ops fix retained at `99f3fffd6` and validation passing on the candidate `build-hip`. The Bonsai smoke-test remains open below.
- [ ] **K13 — Bonsai-27B Q1_0 smoke-test** (operator-gated, no concurrent inference): (a) load/decode `models/bonsai-27b/Bonsai-27B-Q1_0.gguf` on `experimental-v7-refresh-20260716` — does it run on stock kernels or need the PrismML `prism`-branch fused kernels? (b) if it loads, run the K5 quality gate before any verdict (expect contested quality). Ternary Q2_0/Q2_g64 GGUFs remain staged at `models/ternary-bonsai-27b/` for a future refresh that can validate them on a post-2026-07-07 tip.
- [x] **K17 — v7 perf/server A/B + launcher guard ✅ 2026-07-16**: production-shaped measurements on the refreshed v7 candidate `8e5c555ab` are recorded in `/mnt/raid0/llm/tmp/v7-perf-20260716/v7_perf_ab_20260716.md` and the server JSON artifacts under `/mnt/raid0/llm/tmp/v7-perf-20260716/`. Direct base-decode results: worker Gemma CPU prod `12.5634 t/s` vs v7 `12.2010` (`-2.88%`); frontdoor Qwen3.6 CPU prod `8.8559` vs v7 `8.2757` (`-6.55%`); v7 worker GPU standalone `86.7806 t/s`. Fresh-server `worker_general` ngram+MTP A/Bs: production default-temp `65.6846` / `69.5352 t/s`; v7 hidden-ROCm/default `67.9978` / `68.2169 t/s`; identical output hashes and draft counters (`500` accepted / `1172` generated on measured reps). HIP-visible v7 default on CPU role regressed to roughly `34-39 t/s` and touched ROCm despite `-ngl 0`; device-hidden/default restored parity. The earlier resident production `~127 t/s` was not reproduced on a fresh production server and is treated as a resident-state outlier, not the baseline. Launcher validation in `epyc-orchestrator/scripts/server/orchestrator_stack.py` passed with `107` tests and `3` warnings.
- [x] **K18 — K5 quality + readiness checkpoint ✅ 2026-07-16**: fixed-chat K5 rerun passed with comparator `PASS` and zero errors; the invalid raw-completions attempt is discarded. Promotion-gate no-inference checks also passed after refreshing generated stack artifacts (`summary: ok`, promotion gate `181` passed, acceptance no-inference checks passed). The corrected MI210 sidecar showed the earlier no-device result was a wrong-library false negative: with `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin`, v7 `llama-bench` sees `ROCm0`, reports `backends="ROCm"` / `gpu_info="AMD Instinct MI210"`, and measured Gemma3 1B Q8 generation at `197.773 tok/s` with sampled GPU use `99%`. CPU-only temp servers and sidecar bench processes were stopped after the run; `pgrep` for `18072`, `18073`, `v7_quality_gate`, `llama-bench`, and `llama-cli` found no live process beyond the shell, and `rocm-smi` showed `0%` / no KFD PIDs. This closes the checkpoint readiness evidence for v7; no additional long inference remains queued from this checkpoint.
- [x] **K19 — v7 all-family server-smoke checkpoint ✅ 2026-07-16**: recorded the completed smoke run from `/mnt/raid0/llm/tmp/v7-server-smoke-20260716T153522Z/summary.json`. Rebuilt v7 HIP binary reports `version: 10075 (8e5c555ab)`; `LD_LIBRARY_PATH` was pinned to `build-hip/bin` so shared libraries resolved from `/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin` instead of production. All six production families passed: frontdoor `Qwen3.6`, worker_general `Gemma4+assistant draft` with `ngram-mod,draft-mtp`, architect `Qwen3.5-122B`, ingest_long_context `Qwen3-Next`, worker_vision `Qwen2.5-VL+mmproj`, and vision_escalation `Qwen3-VL+mmproj`. Structured-output schema passed for all six. Vision image smoke passed for both vision roles. Frontdoor and architect required production-style `chat_template_kwargs` `enable_thinking=false` reruns so output landed in `message.content`; direct raw chat without kwargs emitted `reasoning_content` only. All temp server PIDs were verified dead after stop.
- [x] **K20 — v7 production-path speed A/B clarification ✅ 2026-07-16**: separated base-decode guards from production server/speculative path evidence. Baseline `llama-bench` guard artifacts live in `/mnt/raid0/llm/tmp/v7-perf-20260716-postsmoke/`: architect base decode prod `5.848182 t/s` vs v7 `5.307566` (`-9.24%`), ingest base decode prod `13.886879` vs v7 `14.016139` (`+0.93%`). These are non-spec guard cells, not MTP/NEXTN coverage. Production server-path artifacts live in `/mnt/raid0/llm/tmp/v7-spec-server-ab-20260716T155208Z/summary.json` and `/mnt/raid0/llm/tmp/v7-ingest-server-ab-20260716T155557Z/summary.json`: frontdoor `draft-mtp` prod `34.599352 t/s` vs v7 `33.866551` (`-2.12%`) with matched measured draft acceptance (`219/319`); architect `draft-mtp` prod `19.343445` vs v7 `19.295712` (`-0.25%`) with matched measured draft acceptance (`194-195/240`); ingest_long_context production Qwen3-Next server path prod `23.521174` vs v7 `23.272615` (`-1.06%`) with the stack launch's `qwen3next.expert_used_count=int:4` override. All sidecar server PIDs were verified dead after stop. Interpretation: v7's production server/speculative paths are near parity, while architect's non-spec base-decode regression remains a guardrail risk to track rather than the production-path result.
- [x] **K21 — v7 performance-feature inventory and measured-runtime-scope audit ✅ 2026-07-16**: v7 does carry performance-oriented codepaths, but this is not promotion approval and the evidence is narrower than "v7 is faster everywhere." Present/retained features: per-decode HIP graph capture on MI210 (`GGML_HIP_GRAPHS=ON`), refreshed upstream speculative/MTP/NEXTN machinery with combined `ngram-mod,draft-mtp`, restored upstream freshness including `Q2_0`, and the K14 flash-attn backend-op fix that lets the HIP backend validation complete. Rejected or not landed as wins: `GGML_CUDA_GRAPH_OPT=1`, Q8 prefetch, the shape-aware graph key, and the onegraph single-graph fold. Quality coverage now includes the production CPU worker's combined `ngram-mod,draft-mtp` path: the K5 chat gate passed v6 and v7 with identical MMLU-Pro/GPQA scores and zero errors. Performance evidence says CPU-pinned production server/speculative paths are near parity, not a broad speedup; MI210 exact production-vs-v7 A/B is not available under the frozen production-kernel rule because the current production comparator is CPU-only, but v7 MI210 functionality and standalone speed sanity were captured under K18. Gemma4 external-head MTP on GPU remains a future GPU-worker-lane gate, not a blocker for the currently measured CPU-pinned runtime scope.
