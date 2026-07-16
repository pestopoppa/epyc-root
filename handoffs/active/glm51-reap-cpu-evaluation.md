# GLM-MoE-DSA Evaluation — GLM-5.2 primary (GLM-5.1-REAP = fallback datapoint)

**Status**: ACTIVE — **GLM-5.2 UD-IQ2_M download COMPLETE + size-manifest verified + short CPU load/coherence smoke PASSED (2026-07-16)**; DSA forward-pass premise **RE-AUDITED 2026-07-16 → likely LANDED in v6** (was "WAIT-DSA / PR #21149"). Next real action = long-context DSA/indexer verification and KV-length scaling. Inference operator-gated (`feedback_no_concurrent_inference`).
**Created**: 2026-04-22 (via research-intake deep-dive of intake-427, as GLM-5.1-REAP)
**Updated**: 2026-07-16 (re-scoped to GLM-5.2 primary; DSA-landed audit; download authorized)
**Categories**: moe_optimization, local_inference, model_evaluation, kv_cache
**Priority**: MEDIUM-HIGH (primary GLM-MoE-DSA target; now storage-unblocked + DSA likely unblocked)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) (DSA infra — **note: its PR #21149 tracking is likely superseded by upstream #23346, see Audit below**), [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md) (GLM-5.2 GPU endgame = expert-offload; never fits 64 GB HBM), [`tree-draft-forward-port-plan.md`](tree-draft-forward-port-plan.md) (native GLM MTP head), [`reap-moe-expert-pruning.md`](../completed/reap-moe-expert-pruning.md) (REAP background, GLM-5.1 fallback)

> Filename retained (`glm51-reap-…`) for cross-reference stability (~19 inbound links); the live subject is **GLM-5.2**.

## 2026-07-16 Audit Reset — Executor Start Here

The 2026-05-28 "WAIT-DSA, no autonomous download" framing is **superseded**. Two premises that gated this handoff have changed:

**1. Storage gate — CLEARED.** GLM-5.2 UD-IQ2_M (~239 GB) fits the current raid0 (~569 GB free and being managed). Operator explicitly authorized the download 2026-07-16.

**2. DSA-runtime gate — LIKELY CLEARED (verify by smoke-test).** The handoff long claimed `LLM_ARCH_GLM_DSA` "loads indexer tensors but the forward pass is not implemented → dense-MLA fallback; gated on PR #21149." **Re-audit of the v6 fork (2026-07-16) contradicts this:**
- `src/models/glm-dsa.cpp` is a **dedicated `llama_model_glm_dsa` model class** with `build_arch_graph`, loading the lightning-indexer tensors (`indexer_proj`, `indexer_attn_k`, `indexer_attn_q_b`, `indexer_k_norm`) and `indexer_top_k`; it **requires MLA**.
- `src/llama-kv-cache-dsa.cpp` (a real `.cpp`, not just the `.h`) **creates the indexer KV cache** (MQA single-key-head).
- Landed via upstream **PR #23346** — "generic DeepSeek Sparse Attention (DSA) implementation" (for DeepseekV32; GLM-DSA reuses the same generic DSA), **not** the tracked #21149 (fairydreaming). So the gating event effectively happened through a different PR.
- **Caveat:** presence of the code ≠ confirmed-correct for GLM-5.2 at long context. Treat "DSA works" as a hypothesis to be settled by an actual load + a long-context probe, not asserted.

### Decision state (2026-07-16)

| Question | Answer | Action |
|---|---|---|
| Is the model downloaded? | **Yes** — `unsloth/GLM-5.2-GGUF` UD-IQ2_M six public shards, total `238,577,580,768` bytes, size-verified against HF tree `abc55e72527792c6e77069c99b4cb7de16fa9f23`. | Closed; proceed to DSA verification. |
| Is llama.cpp DSA ready? | **Apparently yes in v6** (glm-dsa model + DSA KV cache via #23346) — was recorded as "no". Static audit says top-k selection exists in both prompt and decode, but final attention still looks dense/mask-based. | Confirm empirically: load + short-ctx smoke + a long-ctx (>64K) probe; then profile whether attention scales with full KV length or near `indexer_top_k`. |
| Next useful action | Smoke-test on load (operator-gated), not more paper analysis. | Phase 1 below. |

### Phase 0 — no-inference readiness (updated 2026-07-16)
- [x] Storage gate reconciled — CLEARED; operator authorized UD-IQ2_M download. ✅ 2026-07-16
- [x] DSA implementation status re-audited — `llama_model_glm_dsa` + `llama-kv-cache-dsa.cpp` present in v6 via upstream #23346; "no forward pass" premise is STALE. ✅ 2026-07-16
- [x] Download completes + shard integrity verified (`models/GLM-5.2-UD-IQ2_M/`, 6 shards, `238,577,580,768` bytes). ✅ 2026-07-16
- [x] Reconcile [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md): D1/#21149 path marked superseded, D2/D3 re-anchored to landed #23346 code, and remaining work split into fresh profiling gates. ✅ 2026-07-16

## Objective

Evaluate **GLM-5.2** (`zai-org/GLM-5.2`, 754B GLM-MoE-DSA) as a large-MoE architect/long-context candidate on the EPYC stack, starting from the storage-viable **unsloth UD-IQ2_M (~239 GB)** GGUF. Primary questions: (a) does the v6 DSA forward pass load and run GLM-5.2 coherently; (b) does the sparse-attention (Lightning Indexer / IndexShare) path actually engage at long context, or silently fall back to dense MLA; (c) CPU throughput + quality vs current architects. GLM-5.1-REAP is retained below as a **fallback comparison datapoint only**.

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
| **DSA status (v6, 2026-07-16)** | `src/models/glm-dsa.cpp` + `src/llama-kv-cache-dsa.cpp` present via upstream **#23346** (generic DSA). Load-path exists; long-ctx engagement UNVERIFIED. |
| **Runtime flags (expected)** | `--jinja`, deepseek-style reasoning; confirm from the unsloth card at run time |

*Vendor benchmarks (AIME 99.2, SWE-bench Pro 62.1, etc.) are self-reported OBSERVATIONS per `MEASUREMENT.md` — hypotheses only, never gate keep/deploy.*

## Evaluation Plan (GLM-5.2, DSA-gated fork)

### Phase 1 — Load + short-context smoke (GATE: abort on repetition loops)
- [x] Short CPU load/coherence smoke: experimental v7 `b10077-da1bf5e2f`, `llama-server`, `--device none -ngl 0 --jinja --reasoning off --reasoning-budget 0`, returned exact `READY`. Evidence: `/mnt/raid0/llm/tmp/glm52-short-smoke-20260716T2308-reasoning-off/`. ✅ 2026-07-16
- [ ] Full five-prompt short-context smoke set (greeting, code, reasoning, structured, tool-call); the first exact-output smoke is positive but not a quality gate.
- [ ] 5 basic prompts (greeting, code, reasoning, structured, tool-call); check for the repetition-loop failure mode that killed GLM-4.7 (43%, severe loops).
- [ ] **GATE:** repetition loops → abort, document.

### Phase 2 — DSA-path verification (the load-bearing question)
- [ ] Investigate short-smoke unused-tensor warning before/with the long-context probe: `blk.78.*` tensors were ignored on load, including indexer and `nextn` tensors. This may be expected tail-layer/NextN behavior or may indicate incomplete GLM-5.2 tensor mapping; do not call DSA or native-GLM-MTP live until resolved.
- [ ] Long-context probe (>64K, ideally toward 131K+): does the Lightning-Indexer/top-k path engage coherently? Instrument via logs / KV-cache-dsa creation / a needle-in-haystack at long ctx.
- [ ] D2 runtime closeout: run one prefill batch (`n_tokens > 1`) and one single-token decode; capture graph/op traces proving `top_k` or `ggml_lightning_indexer` appears in both phases.
- [ ] D2 scaling check: vary KV length while keeping `indexer_top_k` fixed and profile the actual attention op (`FLASH_ATTN_EXT` or dense `MUL_MAT` path). Full-KV scaling means dense-mask compute; near-top-k scaling means real sparse execution.
- [ ] Record disposition: **DSA-REAL-SPARSE** (sparse compute engages → 1M-ctx value live), **DSA-DENSE-MASK** (top-k engages but attention still scales with full KV), or **DSA-FALLBACK** (indexer/top-k path fails or is bypassed).

### Phase 3 — Throughput benchmark (CPU; GATE ~ architect baseline)
- [ ] Single-instance 192t (`numactl --interleave=all`) + NUMA 2×96t; record prefill/gen t/s, TTFT. Note: 754B at IQ2 is far larger active/total than the 122B architect; expect low CPU t/s (BW-bound). Compare vs corrected architect baseline (~18–21 t/s CPU-Q4+MTP, per `mi210-speed-campaign-summary.md`), not the stale 4.3.
- [ ] GPU note: GLM-5.2 **never fits the MI210 64 GB HBM** even at IQ2 (~239 GB) → the only GPU path is **expert-offload** (`--n-cpu-moe`/`-ot`), gated on the expert-routing-skew profile — see [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md).

### Phase 4 — Quality eval (if smoke + throughput pass)
- [ ] Run the standard suites vs architect_general (Qwen3.5-122B) and architect_coding baselines; apply the eval-tower + MEASUREMENT protocol (not vendor numbers).

### Phase 5 — Disposition
- [ ] Record GO (candidate) / WAIT (DSA-fallback → re-open indexer gate) / KILL (quality/throughput fail), update `inference-acceleration-index.md` + master index. Do NOT add a `model_registry.yaml` role without operator approval.

## Open Questions
- [ ] Does the v6 `glm-dsa` graph run GLM-5.2 UD-IQ2_M coherently on load (short ctx)?
- [ ] Does the DSA indexer path actually engage at long context, and does attention compute scale with `indexer_top_k` rather than full KV? (Phase 2 — the whole 1M-ctx thesis rides on this.)
- [ ] MTP: the GLM-5.2 MTP head is an inert stub on our fork — is the native-GLM-MTP forward-graph port worth finishing for spec-dec once GLM-5.2 runs? (`tree-draft-forward-port-plan.md`)
- [x] Is `llama-cpp-dsa-contribution.md`'s PR-#21149 tracking now moot given #23346 landed? Yes — reconciled; remaining D2/D3 work is landed-code profiling only. ✅ 2026-07-16

## Key Files
| Repo | Path | Purpose |
|---|---|---|
| epyc-llama | `src/models/glm-dsa.cpp` | GLM-DSA model class + graph (indexer tensors, MLA-required) |
| epyc-llama | `src/llama-kv-cache-dsa.cpp` / `.h` | Lightning-indexer KV cache |
| epyc-llama | `src/llama-arch.cpp` (`LLM_ARCH_GLM_DSA` = "glm-dsa") | arch registration |
| models | `/mnt/raid0/llm/models/GLM-5.2-UD-IQ2_M/` | download target (in progress) |

## Reporting Instructions
- After the load/smoke, record the DSA-REAL vs DSA-FALLBACK disposition here + in `inference-acceleration-index.md`.
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
- **[intake-506] "DeepSeek-V3.2" (arxiv:2512.02556, Dec 2025)** — canonical DSA (DeepSeek Sparse Attention) reference. Lightning Indexer (FP8, head-weighted, block-64 quantized key cache, separate from MLA KV) → top-k=2048 token selection → MLA on selected tokens. GLM-MoE-DSA reuses the same mechanism, so one llama.cpp DSA implementation unlocked both — **now realized via the landed generic-DSA #23346** (this was the predicted "2-models-for-1" event). V3.2 671B-class (~380 GB Q4) vs GLM-5.1 555B (~325 GB Q4). Verdict: worth_investigating (DSA was the highest-leverage external event — it has since landed).

## Research Intake Update — 2026-06-20

### GLM-5.2 becomes PRIMARY (intake-699, supersedes GLM-5.1)
- Per user direction 2026-06-20, **GLM-5.2 is the PRIMARY GLM-MoE-DSA target** (intake-699: `GLM-5.2-GGUF`, unsloth dynamic quants of `zai-org/GLM-5.2`, 754B, MIT, 1M ctx, IndexShare arXiv 2603.12201). GLM-5.1 demoted to fallback (history retained above). Gating event = DSA forward pass in our fork; storage escapable via UD-IQ2 (~238 GB) vs Q4_K_M (466 GB). **[2026-07-16 update: DSA appears landed via #23346; storage cleared; UD-IQ2_M download authorized + in progress — see the 2026-07-16 Audit Reset at top.]**
- GLM-5.2 vendor benchmarks (AIME 99.2, SWE-bench Pro 62.1) are self-reported OBSERVATIONS — hypotheses only.

## Research Intake Update — 2026-07-16 (Reviewer control plane: GLM-5.2 is the heavyweight-reviewer target)

The Architect→Reviewer control-plane series (see [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)) locked GLM-5.2 UD-IQ2_M as the cross-family heavyweight REVIEWER target (operator, 2026-07-16). This handoff's existing gates (download+integrity → load smoke → coherence → CPU bench → DSA disposition) are consumed downstream by [`glm52-reviewer-capability-gates.md`](glm52-reviewer-capability-gates.md) (typed-emission/rubric-authoring/why-diagnosis probes) and the H5 ablation arm A4 — no new infra tasks here, your scope is unchanged. Two notes from the planning session's v7 source review: (a) the experimental tree has `LLM_ARCH_GLM_DSA` ("glm-dsa") wired (`llama-arch.cpp:84`, `llama-kv-cache-dsa.cpp`), but the unsloth GGUF's arch-string/tensor mapping is unreconciled — that reconciliation is tracked as **K23** in [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md) and is a prerequisite of your load-smoke line on the v7 lane; (b) the RAM-residency posture for a 239GB reviewer (co-resident vs swap-on-demand vs review-windows) is an operator decision queued in master-index §A00 (GC-4).
