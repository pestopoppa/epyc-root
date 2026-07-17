# GLM-MoE-DSA Evaluation — GLM-5.2 primary (GLM-5.1-REAP = fallback datapoint)

**Status**: ACTIVE — **GLM-5.2 UD-IQ2_M download COMPLETE + size-manifest verified + short CPU load/coherence smoke PASSED + 4K/8K DSA trace shakedown PASSED + true >64K CPU probe COMPLETED + current-source GLM DSA cache/runtime wiring CLOSED + runtime sparse-vs-dense classified `DSA-DENSE-MASK` (2026-07-17)**. The old "WAIT-DSA / PR #21149" gate is superseded because generic DeepSeek32 DSA landed via upstream #23346. The 2026-07-17 source audit found GLM-specific wiring missing; experimental-v7 commit `3dee86a5a` then wired `LLM_ARCH_GLM_DSA` to `llama_kv_cache_dsa`, moved GLM to the DeepSeek32 DSA graph, required live indexer tensors, and force-built the GLM indexer Hadamard rotation tensors. Validation passed `test-llama-archs --arch glm-dsa`, `--arch deepseek32`, ASAN `glm-dsa`, and a current-source exact `READY` smoke (`/mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344/`) whose log shows main + indexer DSA caches and `Lightning Indexer enabled`. Current-source fixed-`indexer_top_k=32` KV-scaling logs (`/mnt/raid0/llm/tmp/glm52-current-source-kv-scaling-20260717T130222Z/runtime_summary.md`) show Lightning/indexer caches engage but prompt throughput still declines with KV length (`23.81 -> 21.04 -> 17.28 t/s` at 2.9K/5.9K/11.9K prompt tokens), so final attention is dense-mask, not proven sparse compute. Next real action = sparse final-attention implementation/profiling, plus current-source long-context needle/coherence and quality. Inference operator-gated (`feedback_no_concurrent_inference`).
**Created**: 2026-04-22 (via research-intake deep-dive of intake-427, as GLM-5.1-REAP)
**Updated**: 2026-07-17 (current-source GLM DSA cache/runtime wiring fix + exact READY smoke + runtime DSA-DENSE-MASK classification recorded; sparse final-attention implementation and quality gates still open)
**Categories**: moe_optimization, local_inference, model_evaluation, kv_cache
**Priority**: MEDIUM-HIGH (primary GLM-MoE-DSA target; storage-unblocked; GLM DSA cache/runtime wiring closed; runtime evidence says final attention is dense-mask, so sparse final-attention implementation and quality gates remain open)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) (DSA infra — **note: its PR #21149 tracking is likely superseded by upstream #23346, see Audit below**), [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md) (GLM-5.2 GPU endgame = expert-offload; never fits 64 GB HBM), [`tree-draft-forward-port-plan.md`](tree-draft-forward-port-plan.md) (native GLM MTP head), [`reap-moe-expert-pruning.md`](../completed/reap-moe-expert-pruning.md) (REAP background, GLM-5.1 fallback)

> Filename retained (`glm51-reap-…`) for cross-reference stability (~19 inbound links); the live subject is **GLM-5.2**.

## 2026-07-16 Audit Reset — Executor Start Here

The 2026-05-28 "WAIT-DSA, no autonomous download" framing is **superseded**. Two premises that gated this handoff have changed:

**1. Storage gate — CLEARED.** GLM-5.2 UD-IQ2_M (~239 GB) fits the current raid0 (~569 GB free and being managed). Operator explicitly authorized the download 2026-07-16.

**2. DSA-runtime gate — CACHE/RUNTIME WIRING CLEARED, SPARSE-COMPUTE STILL OPEN.** The handoff long claimed `LLM_ARCH_GLM_DSA` "loads indexer tensors but the forward pass is not implemented -> dense-MLA fallback; gated on PR #21149." **Re-audit changed the premise, then the current-source GLM cache/runtime gap was fixed:**
- Upstream **PR #23346** landed generic DeepSeek Sparse Attention for `LLM_ARCH_DEEPSEEK32`; the old #21149 tracking path is superseded.
- Pre-fix audit found `src/models/glm-dsa.cpp` loaded lightning-indexer tensors but aliased the DeepSeek2 graph, while `src/llama-model.cpp` created `llama_kv_cache_dsa` only for `LLM_ARCH_DEEPSEEK32`.
- Experimental-v7 commit `3dee86a5a` closes that cache/runtime gap: `LLM_ARCH_GLM_DSA` now constructs `llama_kv_cache_dsa`, aliases the DeepSeek32 DSA graph, requires live GLM indexer tensors, and force-builds the indexer Hadamard rotation tensors.
- Validation: `test-llama-archs --arch glm-dsa`, `test-llama-archs --arch deepseek32`, ASAN `glm-dsa`, short runner DSA-cache smoke (`/mnt/raid0/llm/tmp/glm52-current-source-short-smoke-20260717T092045/`), and exact `READY` smoke (`/mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344/`) passed.
- Older GLM-5.2 >64K probe artifacts were generated with a stale experimental `build-hip` binary that self-reported `9d70bae4b`; they prove that binary's load/runnability/scaling behavior only.
- **Caveat:** `Lightning Indexer enabled` in logs is a backend capability/resolution signal, not proof that GLM final attention uses sparse selected KV rows.

### Decision state (2026-07-16)

| Question | Answer | Action |
|---|---|---|
| Is the model downloaded? | **Yes** — `unsloth/GLM-5.2-GGUF` UD-IQ2_M six public shards, total `238,577,580,768` bytes, size-verified against HF tree `abc55e72527792c6e77069c99b4cb7de16fa9f23`. | Closed; proceed to DSA verification. |
| Is llama.cpp DSA ready? | **Generic DeepSeek32 path yes; GLM-DSA cache/runtime wiring yes on experimental v7 `3dee86a5a`; sparse-compute status now classified `DSA-DENSE-MASK`.** GLM uses the DSA cache and DeepSeek32 DSA graph, and current-source smokes show main + indexer DSA caches. The runtime fixed-`indexer_top_k=32` scaling run shows Lightning/indexer caches engage, but prompt throughput declines as KV grows. | Do not claim 1M sparse-compute value until final attention gathers only selected KV rows or backend-level profiling proves masked rows are skipped. |
| Next useful action | Sparse final-attention implementation/profiling and current-source long-context quality/needle, not more load-smoke or DSA activation checks. | Phase 2/4 below. |

### Phase 0 — no-inference readiness (updated 2026-07-16)
- [x] Storage gate reconciled — CLEARED; operator authorized UD-IQ2_M download. ✅ 2026-07-16
- [x] DSA implementation status re-audited — generic DSA landed via upstream #23346; pre-fix source audit found GLM cache/runtime wiring open, and experimental-v7 `3dee86a5a` subsequently wired `LLM_ARCH_GLM_DSA` to `llama_kv_cache_dsa` + DeepSeek32 DSA graph. ✅ 2026-07-17
- [x] D2 current-source GLM cache/runtime wiring closeout: patched experimental v7 (`3dee86a5a`), rebuilt CPU/HIP targets, passed `test-llama-archs --arch glm-dsa`, `--arch deepseek32`, ASAN `glm-dsa`, and exact `READY` smoke with main + indexer DSA caches. ✅ 2026-07-17
- [x] Download completes + shard integrity verified (`models/GLM-5.2-UD-IQ2_M/`, 6 shards, `238,577,580,768` bytes). ✅ 2026-07-16
- [x] Reconcile [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md): D1/#21149 path marked superseded, D2/D3 re-anchored to landed #23346 code, and remaining work split into fresh profiling gates. ✅ 2026-07-16

## Objective

Evaluate **GLM-5.2** (`zai-org/GLM-5.2`, 754B GLM-MoE-DSA) as a large-MoE architect/long-context candidate on the EPYC stack, starting from the storage-viable **unsloth UD-IQ2_M (~239 GB)** GGUF. Primary questions: (a) now that experimental-v7 `3dee86a5a` wires `LLM_ARCH_GLM_DSA` into the generic DSA cache/runtime, does the sparse-attention (Lightning Indexer / IndexShare) path actually engage at long context, or silently behave like dense MLA with a mask; (b) does long-context quality/needle behavior remain coherent; (c) CPU throughput + quality vs current architects. GLM-5.1-REAP is retained below as a **fallback comparison datapoint only**.

## GLM-5.2 — Model Specifications (PRIMARY)

| Property | Value |
|---|---|
| **Repo (base)** | `zai-org/GLM-5.2` (BF16 safetensors, ~1.5 TB, MIT) |
| **GGUF (download target)** | `unsloth/GLM-5.2-GGUF` → **UD-IQ2_M ~239 GB** (~6 shards) |
| **UD quant ladder** | UD-IQ2_XXS/UD-IQ2_M ~238 GB · UD-Q2_K_XL ~254 GB · Q4_K_M ~466 GB (Q4 near-fills disk — avoid) |
| **Architecture** | `glm_moe_dsa` → llama.cpp `LLM_ARCH_GLM_DSA` ("glm-dsa"); DSA (Lightning Indexer) + MLA + MoE |
| **Total params** | 754B GLM-MoE-DSA |
| **Context** | 1M (vendor); real long-ctx value gated on the DSA indexer path actually engaging |
| **Notable** | IndexShare indexer-reuse (arXiv 2603.12201); ships an **MTP/NextN head** (inert stub on our fork — native-GLM-MTP port ~90% scaffolded per `tree-draft-forward-port-plan.md`) |
| **DSA status (v7 source, 2026-07-17)** | Experimental-v7 `3dee86a5a` wires `LLM_ARCH_GLM_DSA` to `llama_kv_cache_dsa`, aliases the DeepSeek32 DSA graph, requires live GLM indexer tensors, and force-builds indexer Hadamard rotation tensors. Current-source exact `READY` smoke logs main + indexer DSA caches and `Lightning Indexer enabled`. Current-source KV scaling with fixed `indexer_top_k=32` classified runtime behavior as **DSA-DENSE-MASK**: indexer engages, but final attention still scales with KV length. |
| **Runtime flags (expected)** | `--jinja`, deepseek-style reasoning; confirm from the unsloth card at run time |

*Vendor benchmarks (AIME 99.2, SWE-bench Pro 62.1, etc.) are self-reported OBSERVATIONS per `MEASUREMENT.md` — hypotheses only, never gate keep/deploy.*

## Evaluation Plan (GLM-5.2, DSA-gated fork)

### Phase 1 — Load + short-context smoke (GATE: abort on repetition loops)
- [x] Short CPU load/coherence smoke: experimental v7 `b10077-da1bf5e2f`, `llama-server`, `--device none -ngl 0 --jinja --reasoning off --reasoning-budget 0`, returned exact `READY`. Evidence: `/mnt/raid0/llm/tmp/glm52-short-smoke-20260716T2308-reasoning-off/`. ✅ 2026-07-16
- [ ] Full five-prompt short-context smoke set (greeting, code, reasoning, structured, tool-call); the first exact-output smoke is positive but not a quality gate.
- [ ] 5 basic prompts (greeting, code, reasoning, structured, tool-call); check for the repetition-loop failure mode that killed GLM-4.7 (43%, severe loops).
- [ ] **GATE:** repetition loops → abort, document.

### Phase 2 — DSA-path verification (the load-bearing question)
- [x] Investigate short-smoke unused-tensor warning before/with the long-context probe: `blk.78.*` tensors are the expected skipped physical NextN tail block (`n_layer=78`, `n_layer_all=79`, `nextn_predict_layers=1`), not an unreconciled live trunk layer. ✅ 2026-07-16
- [x] Run instrumented 4K/8K DSA trace shakedown: `/mnt/raid0/llm/tmp/glm52-dsa-long-probe-20260716T2340/plan.json` and `/mnt/raid0/llm/tmp/glm52-dsa-kv-scaling-20260716T2350/plan.json`; logs show metadata override `glm-dsa.attention.indexer.top_k=int:32` and `Lightning Indexer enabled`. ✅ 2026-07-16
- [ ] Long-context probe (>64K, ideally toward 131K+): does the Lightning-Indexer/top-k path engage coherently on current-source GLM beyond short cache/runtime smoke? Instrument via logs / KV-cache-dsa creation / a needle-in-haystack at long ctx.
  - 2026-07-17 timeout observation: `/mnt/raid0/llm/tmp/glm52-dsa-64k-probe-20260716T235329Z/` used `--long-context 65536`, but the old prompt heuristic produced `task.n_tokens = 48009`, not >64K actual tokens. The CPU-only run logged `Lightning Indexer enabled` and processed through `45056 / 48009` prompt tokens before the `5400s` HTTP timeout canceled the task; prefill tapered from `25.29 t/s` at 2K to `8.71 t/s` at 45K. Treat this as scaling/timeout evidence only. Next retry must use the live-tokenizer floor guard (`--min-prompt-tokens 65536`) and a larger timeout.
  - 2026-07-17 true >64K runnability observation: `/mnt/raid0/llm/tmp/glm52-dsa-true64k-probe-20260717T0125/` used `--long-context 90000 --min-prompt-tokens 65536 --request-timeout 21600` and completed. The runner counted `65957` prompt tokens; llama-server processed `65969` prompt tokens and decoded 16 tokens. Logs show `general.architecture=glm-dsa`, `indexer.top_k` overridden from `2048` to `32`, expected `blk.78.*` NextN-tail skipping, and `Lightning Indexer enabled`. Prompt eval was `6.76 t/s` overall; the 65K checkpoint was `6.81 t/s` cumulative and the final 2K interval was `3.93 t/s`. Decode was `1.20 t/s`; response was length-capped with reasoning-only preview. This closes stale-binary true >64K GLM runnability, but not current-source >64K behavior, sparse-compute scaling, or quality.
- [x] D2 static prompt/decode path audit: pre-fix source loaded GLM DSA hparams/tensors but did not instantiate `llama_kv_cache_dsa` for GLM; experimental-v7 `3dee86a5a` closes that cache/runtime gap. In the generic DSA path, each layer computes `indexer_score`, `ggml_top_k`, and passes `top_k` to `llm_graph_context::build_attn(llm_graph_input_attn_k_dsa*, ...)`, but that helper constructs `kq_mask_top_k` over the full KV length and then calls `build_attn_mha()` with full cached `k`/`v`. Backend flash-attention kernels iterate full `ne11` and consume the mask; no sparse gather/top-k-limited final-attention path was found. Disposition: **GLM cache/runtime wired; generic DSA-DENSE-MASK-LIKELY**, not DSA-REAL-SPARSE. ✅ 2026-07-17
- [x] D2 current-source GLM wiring closeout: rebuilt experimental source later committed as `3dee86a5a`; `LLM_ARCH_GLM_DSA` now constructs `llama_kv_cache_dsa`, uses DeepSeek32 DSA graph, and passes short exact `READY` smoke with main + indexer DSA caches. Evidence: `/mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344/`. ✅ 2026-07-17
- [x] D2 runtime closeout: current-source fixed-`indexer_top_k=32` KV-scaling run completed 4K/8K/16K arms (`/mnt/raid0/llm/tmp/glm52-current-source-kv-scaling-20260717T130222Z/runtime_summary.md`). Lightning/indexer caches engaged at each completed context, but prompt throughput declined `23.81 -> 21.04 -> 17.28 t/s` as prompt tokens grew `2900 -> 5906 -> 11921`; single-token decode was requested (`max_tokens=1`). Classification: **DSA-DENSE-MASK**. ✅ 2026-07-17
- [x] GLM long-output evidence hygiene: abort and record the attempted current-source 96K probe (`/mnt/raid0/llm/tmp/glm52-current-source-96k-quality-20260717T144022Z/plan.json`) as **non-evidence** because it used `--log-disable`, no metrics endpoint, a non-streaming busy request, and only `max_tokens=32`. The runner now has a guarded `--long-output` path that enables metrics, samples `/metrics`, and requires a minimum completion-token floor before throughput evidence is accepted. ✅ 2026-07-17
- [ ] D2 sparse-attention implementation/profiling gate: either implement a final-attention path that gathers only the selected top-k KV rows before MLA attention, or capture backend-level evidence proving masked rows are skipped. The existing fixed-`indexer_top_k=32` 4K/8K/65K stale-binary timings plus source audit should be treated as dense-mask/wiring evidence, not a reason to run more load smokes.
- [x] Record disposition: **DSA-DENSE-MASK** — top-k/indexer engages but attention still scales with full KV. Do not treat GLM's 1M-context claim as locally sparse-compute-active until a real sparse final-attention path lands and passes profiling. ✅ 2026-07-17

### Phase 3 — Throughput benchmark (CPU; GATE ~ architect baseline)
- [ ] Single-instance 192t (`numactl --interleave=all`) + NUMA 2×96t; record prefill/gen t/s, TTFT. Note: 754B at IQ2 is far larger active/total than the 122B architect; expect low CPU t/s (BW-bound). Compare vs corrected architect baseline (~18–21 t/s CPU-Q4+MTP, per `mi210-speed-campaign-summary.md`), not the stale 4.3.
  - 2026-07-17 current-source 16K long-output controls: baseline/no-spec (`/mnt/raid0/llm/tmp/glm52-current-source-16k-streaming-20260717Tpostfix/`) processed `11952` server-side prompt tokens at `18.50 t/s` and decoded `512` tokens at `2.53 t/s`; `ngram-mod` (`/mnt/raid0/llm/tmp/glm52-current-source-16k-ngram-20260717Trealistic/`) processed the same server-side prompt length at `18.75 t/s` and decoded `512` tokens at `2.54 t/s`. The `ngram-mod` server initialized but generated/accepted zero draft tokens, so this flag is not a useful GLM acceleration lane for this prompt/output shape. This is a 96-thread current-source control, not the full 192t/NUMA throughput gate.
- [ ] GPU note: GLM-5.2 **never fits the MI210 64 GB HBM** even at IQ2 (~239 GB) → the only GPU path is **expert-offload** (`--n-cpu-moe`/`-ot`), gated on the expert-routing-skew profile — see [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md).
  - 2026-07-17 GLM imatrix expert-count attempt: rebuilt stale experimental-v7 `llama-imatrix`, calibrated `/mnt/raid0/llm/tmp/expert-routing-skew-glm52-20260717T0520Z-rebuilt/expert-routing-skew.imatrix.gguf`, captured `/mnt/raid0/llm/tmp/expert-routing-skew-glm52-20260717T0520Z-rebuilt/expert-routing-skew.imatrix.stats.txt`, then extracted persisted per-expert `.counts` with `scripts/benchmark/extract_imatrix_expert_counts.py` to `/mnt/raid0/llm/tmp/expert-routing-skew-glm52-20260717T0520Z-rebuilt/expert-routing-skew.counts.{json,md}`. Preliminary signal: global aggregate near-uniform (`top_32=17.1%`, normalized entropy `0.996`), but layer-local routing has moderate hot sets (median layer `top_32=55.6%`, max `70.5%`). This is hypothesis-only because the calibration corpus is tiny/repetitive; do not unblock offload/REAP until a representative workload-profile repeat lands.

### Phase 4 — Quality eval (if smoke + throughput pass)
- [ ] Run the standard suites vs architect_general (Qwen3.5-122B) and architect_coding baselines; apply the eval-tower + MEASUREMENT protocol (not vendor numbers).

### Phase 5 — Disposition
- [ ] Record GO (candidate) / WAIT (DSA-fallback → re-open indexer gate) / KILL (quality/throughput fail), update `inference-acceleration-index.md` + master index. Do NOT add a `model_registry.yaml` role without operator approval.

## Open Questions
- [x] Does the v6/v7 `glm-dsa` graph run GLM-5.2 UD-IQ2_M coherently on load (short ctx)? Yes: initial exact `READY` short CPU smoke passed on experimental v7, and current-source GLM DSA cache/runtime smoke passed after `3dee86a5a`. ✅ 2026-07-17
- [x] Does the DSA indexer path actually engage at long context, and does attention compute scale with `indexer_top_k` rather than full KV? **Indexer engages, but final attention scales with full KV; disposition `DSA-DENSE-MASK`.** ✅ 2026-07-17
- [ ] Does GLM-5.2 expert routing have a Zipfian hot set that makes hot-expert GPU residency or REAP viable? The 2026-07-17 imatrix count extraction gives a preliminary near-uniform-global / moderate-layer-local signal, but it is not decision-grade without representative workload prompts.
- [ ] MTP: the GLM-5.2 MTP head is an inert stub on our fork — is the native-GLM-MTP forward-graph port worth finishing for spec-dec once GLM-5.2 runs? The 2026-07-17 `ngram-mod` arm generated zero drafts on the long-output probe, so n-gram is not a substitute for native GLM-MTP on this lane. (`tree-draft-forward-port-plan.md`)
- [x] Is `llama-cpp-dsa-contribution.md`'s PR-#21149 tracking now moot given #23346 landed? Yes — reconciled; remaining D2/D3 work is landed-code profiling only. ✅ 2026-07-16

## Key Files
| Repo | Path | Purpose |
|---|---|---|
| epyc-llama | `src/models/glm-dsa.cpp` | GLM-DSA model class + graph (indexer tensors, MLA-required) |
| epyc-llama | `src/llama-kv-cache-dsa.cpp` / `.h` | Lightning-indexer KV cache |
| epyc-llama | `src/llama-model.cpp` | Model-memory cache selection; experimental-v7 `3dee86a5a` creates `llama_kv_cache_dsa` for DeepSeek32 and GLM-DSA |
| epyc-llama | `src/llama-arch.cpp` (`LLM_ARCH_GLM_DSA` = "glm-dsa") | arch registration |
| models | `/mnt/raid0/llm/models/GLM-5.2-UD-IQ2_M/` | complete six-shard UD-IQ2_M artifact |

## Reporting Instructions
- After sparse final-attention behavior is profiled or implemented, record the DSA-REAL vs DSA-DENSE-MASK vs DSA-FALLBACK disposition here + in `inference-acceleration-index.md`.
- Any future GLM long-output, throughput, or reviewer-quality probe must use the instrumented runner contract: streaming progress, retained trace logs, server-log timing extraction, and a minimum completion-token floor. `/metrics` samples are useful when available, but the server may reject auxiliary endpoints while a long GLM task is busy; runs without streaming/log telemetry are process observations only, not model/kernel evidence.
- Any `GGML`/DSA correctness finding → also update `llama-cpp-dsa-contribution.md` and the landed-code D2/D3 profiling gates.
- Keep the GLM-5.1-REAP fallback section below intact (append-only) — it is retained comparison history, not deleted.

---

## HISTORICAL / FALLBACK — GLM-5.1-555B-A14B-REAP (demoted 2026-06-20; retained datapoint)

*Superseded as primary by GLM-5.2 (2026-06-20, intake-699). Kept as a fallback comparison model; NOT downloaded; its 2-for-1 DSA-leverage rationale now realized via the landed generic-DSA #23346.*

**Objective (historical):** evaluate GLM-5.1-555B-A14B-REAP Q4_K_M (325 GB, `0xSero/GLM-5.1-555B-A14B-REAP-GGUF`) as a single-model replacement for architect_general (Qwen3.5-122B, 69 GB) + architect_coding (REAP-246B, 139 GB). `GlmMoeDsaForCausalLM`, 555B total / ~14B active (top-8 of 192 experts, REAP-pruned 25% from 256), 78 layers, 131K ctx. **⚠ 444B/154-expert variant is BROKEN (29% degeneration) — never use it.**

**Published benchmarks (0xSero, Q4_K_M — vendor OBSERVATIONS):** Terminal-Bench 44/50 (88%), SWE-bench Pro 33/50 (66%), GSM8K 30/50 (60%), HLE 9/50 (18%), degeneration-fuzz 4/45 borderline / 0 hard failures. Comparison targets: architect_general 2.57/3 @4.3 t/s (baseline now corrected to ~18–21 t/s) / 69 GB; architect_coding 82% @8.0 t/s / 139 GB.

**Fallback plan (only if GLM-5.2 fails and 5.1-REAP is revisited):** pre-download storage audit → download `0xSero/GLM-5.1-555B-A14B-REAP-GGUF` (confirm 555B, not 444B) → smoke-test (abort on repetition loops) → CPU throughput (192t + NUMA 2×96t) → quality vs both architects → swap or document-failure. The GLM-5.1-REAP risk table (GLM-4.7 quality precedent; DSA-indexer-for-long-ctx; NUMA split of a 325 GB model; 444B trap) still applies if revisited.

## Research Intake Update — 2026-04-29

### New Related Research
- **[intake-506] "DeepSeek-V3.2" (arxiv:2512.02556, Dec 2025)** — canonical DSA (DeepSeek Sparse Attention) reference. Lightning Indexer (FP8, head-weighted, block-64 quantized key cache, separate from MLA KV) → top-k=2048 token selection → MLA on selected tokens. GLM-MoE-DSA is intended to reuse the same mechanism; generic #23346 provided the base infrastructure and experimental-v7 `3dee86a5a` wired GLM into the DSA cache/runtime path. V3.2 671B-class (~380 GB Q4) vs GLM-5.1 555B (~325 GB Q4). Verdict: worth_investigating (DSA remains high leverage, but sparse final-attention behavior and quality gates remain open).

## Research Intake Update — 2026-06-20

### GLM-5.2 becomes PRIMARY (intake-699, supersedes GLM-5.1)
- Per user direction 2026-06-20, **GLM-5.2 is the PRIMARY GLM-MoE-DSA target** (intake-699: `GLM-5.2-GGUF`, unsloth dynamic quants of `zai-org/GLM-5.2`, 754B, MIT, 1M ctx, IndexShare arXiv 2603.12201). GLM-5.1 demoted to fallback (history retained above). Gating event = DSA forward pass in our fork; storage escapable via UD-IQ2 (~238 GB) vs Q4_K_M (466 GB). **[2026-07-16 update: DSA appears landed via #23346; storage cleared; UD-IQ2_M download authorized + in progress — see the 2026-07-16 Audit Reset at top.]**
- GLM-5.2 vendor benchmarks (AIME 99.2, SWE-bench Pro 62.1) are self-reported OBSERVATIONS — hypotheses only.

## Research Intake Update — 2026-07-16 (Reviewer control plane: GLM-5.2 is the heavyweight-reviewer target)

The Architect→Reviewer control-plane series (see [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)) locked GLM-5.2 UD-IQ2_M as the cross-family heavyweight REVIEWER target (operator, 2026-07-16). This handoff's existing gates (download+integrity -> load smoke -> coherence -> CPU bench -> DSA disposition) are consumed downstream by [`glm52-reviewer-capability-gates.md`](glm52-reviewer-capability-gates.md) (typed-emission/rubric-authoring/why-diagnosis probes) and the H5 ablation arm A4 — no new infra tasks here, your scope is unchanged. Two notes from the planning session's v7 source review: (a) **K23** in [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md) now has its cache/runtime reconciliation leg closed by experimental-v7 `3dee86a5a`, but sparse final-attention profiling and current-source long-context quality/needle remain prerequisites before the reviewer lane can treat GLM's 1M-context value as real; (b) the RAM-residency posture for a 239GB reviewer (co-resident vs swap-on-demand vs review-windows) is an operator decision queued in master-index §A00 (GC-4).
