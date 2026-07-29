# Gemma 4 MTP Drafter — Deep Dive

**Created**: 2026-05-06
**Source intake**: intake-527
**Companion handoff**: `handoffs/active/gemma4-mtp-drafter-evaluation.md`
**Status**: Initial deep dive — gates G0a/G0b/G0c not yet executed

## Context

Google announced (2026-05-05) Multi-Token Prediction drafters for Gemma 4 with "up to 3×" inference speedups. Apache 2.0, multi-framework support claimed. Companion to existing intake-251 / intake-252 / intake-256.

Our prior MTP work (`completed/mtp-speculative-decoding.md`) closed MTP-1 as NOT VIABLE on hybrid Qwen3.5 (0.56× — Delta-Net layers force O(N) recurrent verify). Gemma 4 26B-A4B / 31B / E-series are **non-hybrid**, so the recurrent-verify wall does not apply. This deep dive replaces the closed handoff's "MTP-class techniques are unviable" framing with a per-variant analysis.

## Variant matrix (as of 2026-05-06)

| Variant | Type | Active params | HF (PyTorch) | Drafter (PyTorch) | GGUF (drafter) | GGUF caveat |
|---------|------|---------------|--------------|-------------------|----------------|-------------|
| Gemma 4 31B | Dense | 31B | `google/gemma-4-31B-it` | `google/gemma-4-31B-it-assistant` (Gemma4Assistant: 4 layers, 1024 hidden, 32/16 heads, ~500M total) | `Radamanthys11/Gemma-4-31B-it-assistant-GGUF` (Q8_0 515 MB, F16 955 MB) | **ik_llama.cpp only**, custom `--spec-type mtp` flag, README explicit "Do not use with llama.cpp" |
| Gemma 4 26B-A4B | MoE (~4B active) | ~4B | `google/gemma-4-26B-A4B-it` | `google/gemma-4-26B-A4B-it-assistant` (Gemma4Assistant: 4 layers, 1024 hidden, 16/8 heads — same class as 31B, half the heads) | none yet | drafter is itself dense (`enable_moe_block: false`); conversion would re-use the 31B GGUF infrastructure |
| Gemma 4 E4B | Edge multimodal | 4B | `google/gemma-4-E4B-it` | `google/gemma-4-E4B-it-assistant` (78M, 4-layer Gemma4Assistant, 256 hidden) — official BF16 on HF; LiteRT-extracted PyTorch at `SeatownSin/gemma-4-E4B-mtp-drafter` | none direct | The official BF16 weights are on HF (not stripped — the SeatownSin extraction predates the assistant release). Community extraction is INT4-dequantized → 35% top-1 acceptance ceiling |
| Gemma 4 E2B | Edge multimodal | 2B | not yet checked | not yet checked | none observed | likely same Gemma4Assistant family, narrower still |

### Key architectural finding (G0.2 RESOLVED 2026-05-06): one drafter class across all Gemma 4 variants

After fetching `config.json` for `google/gemma-4-31B-it-assistant` and `google/gemma-4-26B-A4B-it-assistant`, **all three drafters share the `Gemma4AssistantForCausalLM` architecture class** with `model_type: gemma4_assistant`. The earlier "31B has a conventional 0.5B small-LM drafter" framing was wrong — it's the same Gemma4Assistant class as E4B, just wider.

| Variant | n_layers | hidden_size | n_heads / n_kv_heads | head_dim | layer_types | num_kv_shared_layers | enable_moe_block | backbone_hidden | num_centroids |
|---------|----------|-------------|----------------------|----------|-------------|----------------------|-------------------|-----------------|---------------|
| Gemma 4 31B Dense + assistant | 4 | 1024 | 32 / 16 | 256 | [sliding, sliding, sliding, full] | 4 | false | 5376 | 2048 |
| Gemma 4 26B-A4B MoE + assistant | 4 | 1024 | 16 / 8 | 256 | [sliding, sliding, sliding, full] | 4 | false | 2816 | 2048 |
| Gemma 4 E4B + assistant (per SeatownSin extraction; official HF config not yet inspected) | 4 | 256 | 4 / 2 | 256 (sliding) / 512 (full) | [sliding, sliding, sliding, full] | 4 (effective: Q-only over base KV) | false | 2560 | 2048 (from card) |

**Critical implications:**

1. **One llama.cpp port covers all three Gemma 4 variants** — they share the architecture; only width parameters differ. The earlier framing of "the E-series Q-only-shared-KV mechanism is far from llama.cpp's draft-model assumptions; the 31B conventional drafter is closer" is **REVISED**: all three are the Q-only-shared-KV mechanism (`num_kv_shared_layers=4` means all 4 drafter layers pull KV from the base model rather than maintaining their own). The differences are width and aspect ratio, not mechanism.
2. **The drafter is itself dense** (`enable_moe_block: false`, `num_experts: null`) — even when paired with the 26B-A4B MoE base. So drafter forward-pass cost is predictable and small (4 layers × 1024 hidden × 8192 intermediate ≈ ~120M core transformer params; total ~500M after centroid system + tied LM head → matches the 515 MB Q8_0 file size in `Radamanthys11/Gemma-4-31B-it-assistant-GGUF`).
3. **Embedder clustering** (`num_centroids: 2048`, `centroid_intermediate_top_k: 32`) is consistent across all three — Google's "efficient embedder clustering" applies universally, not just to E2B/E4B.
4. **`attention_k_eq_v: true`** — drafter ties K and V projections. With `num_kv_shared_layers=4` it actually pulls K and V from the base model instead.
5. **BFloat16 native** — confirmed across all three configs (no FP16 → degeneration risk).

## Performance claims and contradictions

| Source | Claim |
|--------|-------|
| Google blog | "up to 3× tokens-per-second"; "no quality degradation" |
| Google blog | ~2.2× on Apple Silicon, batch 4-8 |
| Google blog | Half wait time on RTX PRO 6000 |
| `google/gemma-4-31B-it-assistant` model card | "up to 2×" decoding speedup |
| `lilting.ch` (independent) | 26B-A4B at batch=1 sees limited gains; per-draft-candidate expert routing triggers extra weight loads that cancel drafter speedup |
| FlowHunt write-up | Initial Gemma 4 release was without MTP data; this is a follow-on release |
| Documented case (search hit) | base FP8 41.25 t/s → 25.37 t/s WITH MTP = **−38% slowdown** when drafter quant mismatches target |
| `SeatownSin/gemma-4-E4B-mtp-drafter` README | LiteRT-extracted INT4/INT8-dequantized: 35% top-1 / 80% top-5 acceptance (BF16); Python-loop standalone is 0.7× (slower than autoregressive); only useful inside vLLM/SGLang's integrated speculative decode pipeline |
| `SeatownSin/...` README | BF16 required; FP16 causes output degeneration after ~50 tokens (unscaled attention overflow); steps 1+ use stale KV caches |

**Read**: the headline 3× number applies to specific (drafter ↔ target ↔ batch ↔ framework) combinations and is far from automatic. Quant mismatch can invert the speedup. MoE batch=1 (our default) sees the smallest gain. The LiteRT-extracted E4B drafter's 35% acceptance is quantization-limited and is not what the BF16 official weights would deliver.

## Framework support claims

| Framework | Listed on blog | In `google/gemma-4-31B-it-assistant` card | Real-world evidence |
|-----------|----------------|-------------------------------------------|----------------------|
| HuggingFace Transformers | ✓ | ✓ (primary, with `assistant_model=` API) | works |
| vLLM | ✓ | — | listed |
| SGLang | ✓ | — | listed |
| MLX | ✓ | — | community Apple-Silicon collection exists (`mlx-community/gemma-4-assistant-mtp`) |
| Ollama | ✓ | — | listed |
| LiteRT-LM | ✓ | — | this is where the E-series drafter weights live natively |
| Google AI Edge Gallery (Android/iOS) | ✓ | — | listed |
| **llama.cpp (upstream)** | ✗ NOT LISTED | — | `Radamanthys11` GGUF README: "Do not use with llama.cpp as they do not offer support" |
| **ik_llama.cpp** (Kawrakow fork) | ✗ NOT LISTED by Google | — | `Radamanthys11` GGUF requires it (custom `--spec-type mtp` flag) |

llama.cpp upstream support for MTP-drafter wiring of Gemma 4 is **not announced**. ik_llama.cpp is a separate fork with substantial divergence from upstream — adopting it wholesale would conflict with our own `llama.cpp-experimental` fork, and porting forward means landing the MTP-drafter path in our fork.

## EPYC-specific implications

**Framing — CPU is the primary deployment target, not a fallback.** The 2-3× headline speedup is a framework-and-batch-dependent claim, not an architecture-bound one. There is no a-priori reason the same algorithmic gain cannot be reproduced (or approximated) on EPYC at canonical settings. The rate-limiters are not silicon-bound; they are: (1) the ik_llama.cpp port effort (G0.1), (2) per-variant drafter architecture compatibility with our llama.cpp fork (G0.2), and (3) measurement at canonical EPYC settings (G1/G2). GPU acceleration via `gpu-acceleration-path.md` is reserved for the case where G0.3 = (b) or (c) — it is NOT a parallel deployment plan.

1. **DRAM-bandwidth contention**: Drafter weights are tiny (78 MB E4B BF16, ~500 MB 31B Q8_0) compared to target (~17 GB Q4_K_M for 26B-A4B) — drafter is well under 5% of target weight footprint. At first order, the drafter is not bandwidth-significant. But during decode, drafter forward passes interleave with target verification — both pull from the same 460 GB/s aggregate BW pool. The relevant question is fraction-of-decode-budget the drafter consumes per accepted token. We have no measurement; first-order analysis says it should be well under 10% of decode time per accepted token at production acceptance rates.

2. **MoE-spec-budgeted-expert composition**: Our `moe-spec-cpu-spec-dec-integration.md` mechanism (Phase 1 PASSED: Coder +7.3%, REAP +15.2%) selects a budgeted expert shortlist on the verifier side. MTP drafter is upstream of this — it produces draft tokens that the verifier accepts/rejects under whichever expert-selection regime is active. **The mechanisms are orthogonal in principle**, but: (a) the budget mechanism mutates expert selection per token, which may break the drafter's KV-cache-sharing assumption if the drafter assumes the target's KV is consistent across speculative steps; (b) the lilting.ch finding that batch=1 MoE drafter sees per-candidate expert-load cancellation is exactly the regime we run in — if the budget mechanism reduces the number of distinct experts loaded, it might also restore some of the drafter's gain. Worth measuring; do NOT assume.

3. **Shape match to existing roles**: Coder-30B-A3B Q4_K_M (49.1 t/s on 96t-single-NUMA-node baseline) is the closest existing role to Gemma 4 26B-A4B. If the 26B-A4B + drafter delivers ≥ +20% on canonical EPYC, it becomes a credible coder swap candidate (subject to quality benchmarking). The dense Gemma 4 31B + 0.5B drafter is in the architect-tier weight class.

4. **TTFT / decode-only**: MTP gives no TTFT improvement. Our autopilot / long-context workloads are decode-dominated, so this is favourable. Short agentic-loop turns (few hundred tokens) would see negligible gain.

5. **Drafter quant decisions**: The −38% FP8 mismatch case is a warning. We canonically run Q4_K_M target. The drafter Q8_0 (515 MB for 31B) is well within budget; F16 (955 MB) is also fine. Q4_K_M target + Q8_0 drafter is the safest first benchmark.

## Per-variant gate sequencing

### G0a — Gemma 4 31B Dense + 0.5B drafter

| Sub-gate | Status | Notes |
|---------|--------|-------|
| HF model card available | ✓ | `google/gemma-4-31B-it-assistant` |
| GGUF drafter exists | ✓ | `Radamanthys11/Gemma-4-31B-it-assistant-GGUF` (Q8_0, F16) |
| Standard llama.cpp loadable | ✗ | requires ik_llama.cpp |
| Our `llama.cpp-experimental` fork loadable | unknown | depends on whether MTP draft-input plumbing is patchable from ik_llama.cpp; estimated 1-3 weeks of fork work |
| Decision | **HOLD pending fork-port effort estimate** | next step: read ik_llama.cpp's MTP commit history, estimate diff size, then decide port vs wait-for-upstream |

### G0b — Gemma 4 26B-A4B MoE + drafter

| Sub-gate | Status | Notes |
|---------|--------|-------|
| HF model card available | ✓ | `google/gemma-4-26B-A4B-it-assistant` |
| GGUF drafter exists | ✗ | no community conversion observed yet |
| Drafter architecture documented | ✗ | model card silent on shape; need to inspect `config.json` + `model.safetensors.index.json` |
| Decision | **WAIT for community GGUF or do the conversion ourselves** | Q4_K_M target already on hand for the 26B-A4B base if we use existing intake-251 references; would need to convert the assistant model |

### G0c — Gemma 4 E4B + 78M Q-only-attention drafter

| Sub-gate | Status | Notes |
|---------|--------|-------|
| Official drafter weights on HF | ✓ | `google/gemma-4-E4B-it-assistant` (BF16) |
| LiteRT-extracted variant | ✓ | `SeatownSin/gemma-4-E4B-mtp-drafter` (78M, INT4-dequant ceiling) |
| GGUF | ✗ | none |
| llama.cpp shape support | ✗ | Q-only attention with no owned K/V is not a standard llama.cpp draft-model shape; would require custom op or graph-level integration |
| Decision | **DEFER** | only relevant if the multimodal-pipeline E-series unification path becomes live; the drafter shape is far from llama.cpp's draft-model assumptions |

## Tier 2b synthesis (contradicting evidence)

Recorded under intake-527 `contradicting_evidence` field. Highlights:
- 26B MoE batch=1 cancellation (lilting.ch)
- FP8 quant-mismatch −38% slowdown documented case
- Memory overhead — drafter loads alongside target (less critical for EPYC, more for 24GB GPUs)
- No TTFT improvement — short outputs see negligible gain
- Internal counterpoint: hybrid MTP-1 0.56× does NOT generalize — different architecture class
- LiteRT-extracted E4B at 35% top-1 acceptance is quantization-limited, not the BF16 ceiling
- "Python loop standalone = 0.7× (slower than autoregressive)" — speedup is engine-integration-dependent, not algorithmic

## G0.1 — ik_llama.cpp MTP-implementation surface (RESOLVED 2026-05-06)

ik_llama.cpp has been actively developing MTP since **2026-02-22** — predates Gemma 4 by 3 months. The implementation is **architecture-general**, not Gemma-specific.

| PR | Date | Title | Files | +/− |
|----|------|-------|-------|-----|
| [#1270](https://github.com/ikawrakow/ik_llama.cpp/pull/1270) | 2026-02-22 | Add MTP decoding support for GLM-4.x MoE (foundational) | 16 | +813 / −199 |
| [#1499](https://github.com/ikawrakow/ik_llama.cpp/pull/1499) | 2026-03-25 | Improve MTP acceptance rate | — | — |
| [#1516](https://github.com/ikawrakow/ik_llama.cpp/pull/1516) | 2026-03-26 | Ignore MTP layer(s) when computing required memory | — | — |
| [#1530](https://github.com/ikawrakow/ik_llama.cpp/pull/1530) | 2026-03-28 | graph: Remove duplicate functions in MTP | — | — |
| [#1601](https://github.com/ikawrakow/ik_llama.cpp/pull/1601) | 2026-04-09 | Add llama_context to MTP | — | — |
| [#1637](https://github.com/ikawrakow/ik_llama.cpp/pull/1637) | 2026-04-16 | Add support for parallel graphs to GLM MTP | — | — |
| [#1698](https://github.com/ikawrakow/ik_llama.cpp/pull/1698) | 2026-04-28 | Support for Qwen 3.5 MTP (**dense models only**) | 10 | +398 / −128 |
| [#1713](https://github.com/ikawrakow/ik_llama.cpp/pull/1713) | 2026-05-03 | MTP: better graph reuse | — | — |
| [#1718](https://github.com/ikawrakow/ik_llama.cpp/pull/1718) | 2026-05-02 | speculative: keep MTP draft hidden state alive across steps | 1 | +8 / −2 |
| [#1724](https://github.com/ikawrakow/ik_llama.cpp/pull/1724) | 2026-05-03 | speculative: enable MTP per-step checkpoints with CPU recurrent layers | 4 | +40 / −22 |
| [#1728](https://github.com/ikawrakow/ik_llama.cpp/pull/1728) | 2026-05-03 | Fix graph reuse regression with MTP checkpoints | — | — |
| [#1736](https://github.com/ikawrakow/ik_llama.cpp/pull/1736) | 2026-05-05 | MTP improvements (Gemma 4 burst) | 3 | +62 / −20 |
| [#1741](https://github.com/ikawrakow/ik_llama.cpp/pull/1741) | 2026-05-06 | MTP tweaks | 4 | +68 / −17 |

### Foundational PR (#1270) file map

```
src/llama-build-context.cpp        +271 / −101
src/llama.cpp                      +190 / −81
common/speculative.cpp             +174 / −0
examples/server/server-context.cpp  +86 / −11
include/llama.h                    +20 / −0
common/speculative.h               +19 / −0
common/common.cpp                  +13 / −0
src/llama-load-tensors.cpp         +8 / −4
src/llama-hparams.cpp              +6 / −0
src/llama-context.h                +6 / −1
... (6 more, all small)
```

### Key conclusions

1. **MTP is multi-architecture in ik_llama.cpp** — already supports GLM-4.x MoE (foundational), Qwen 3.5 dense, and Gemma 4 (recent burst). One port amortizes across at least these three model families. Our intake also has DeepSeek-V3 + GLM-5 MTP entries; if those land in ik_llama.cpp later, the port amortizes further.
2. **Qwen 3.5 hybrid MTP is NOT supported in ik_llama.cpp** — PR #1698 title is explicit: "dense models only". This is **independent third-party confirmation** of our `completed/mtp-speculative-decoding.md` 0.56× hybrid finding. Kawrakow hit the same wall.
3. **PR #1724 (May 3, 2026)** — "MTP per-step checkpoints with CPU recurrent layers" — is small (+40 / −22, 4 files) but architecturally significant. It MAY relax the recurrent-verify wall that closed our Qwen3.5-A3B hybrid work. **Worth a focused diff read** as a potential reopener for `completed/mtp-speculative-decoding.md`.
4. **Conflict surface against our `llama.cpp-experimental` fork**: PR #1270 touches `src/llama.cpp`, `src/llama-build-context.cpp`, `common/speculative.cpp`, `src/llama-load-tensors.cpp`, `src/llama-hparams.cpp`, `examples/server/server-context.cpp` — all files with our own NUMA / CPU-EP divergence. Diff is +813 / −199. Realistic port estimate: **2-4 days of focused merge work** for the foundational MTP path, plus per-architecture additions (Gemma 4, GLM-4.x, Qwen 3.5 dense). Add another ~1-2 days for May-2026 follow-up PRs (#1499, #1516, #1530, #1601, #1637, #1713, #1718, #1724, #1728, #1736, #1741).
5. **`--spec-type mtp` is a runtime flag, not a build-time switch** — default off, no impact on non-MTP code paths once landed.

### G0.3 — port-vs-wait decision (preliminary)

| Option | Cost | Payoff | Risk |
|--------|------|--------|------|
| (a) Port ik_llama.cpp MTP path into our fork | 2-4 days port + ongoing rebase tax | Covers Gemma 4 (3 variants) + Qwen 3.5 dense + GLM-4.x MoE + future MTP targets ik adds | Maintenance debt against ik_llama.cpp's continued evolution; conflicts with our NUMA / CPU-EP divergence |
| (b) Wait for upstream llama.cpp | 0 short-term cost | Lower long-term maintenance once landed | Unbounded wait — upstream MTP support not announced |
| (c) Skip MTP entirely | 0 cost | None | Forfeits 2-3× decode speedup on viable targets |
| (d) Build ik_llama.cpp standalone for one-off measurement, treat as non-production | 1 day build + bench | Quick directional answer on whether the speedup materializes on EPYC at canonical settings | Still requires production port for actual deployment; ik_llama.cpp may not have our NUMA optimizations |

**Recommendation**: **option (d) first** — build ik_llama.cpp standalone on EPYC, run a directional G1 measurement (Gemma 4 31B Dense + Q8_0 drafter, canonical bench protocol). If G1 ≥ +20% over architect-tier baseline AND quality benchmark holds, escalate to option (a). If G1 fails on EPYC, defer to option (b) and re-evaluate when upstream support lands. **Do NOT proceed to option (a) without a positive G1 measurement.**

## Recommended next steps

1. **G0.1 + G0.2 RESOLVED** (this deep dive). G0.3 preliminary recommendation = option (d): standalone ik_llama.cpp build for a directional G1 measurement.
2. **Investigate PR #1724 separately** — "MTP per-step checkpoints with CPU recurrent layers" may unblock the closed `mtp-speculative-decoding.md` Qwen 3.5 hybrid work. Read the PR diff in detail before any reopener proposal.
3. **DO NOT BENCH YET** — per `feedback_no_concurrent_inference.md`, no llama-bench launches without explicit user approval. The G1 measurement is a separate proposal that needs sign-off.
4. Hold off on registry slot proposal until G1 + quality benchmark both pass.

## G0.4 — directional measurement attempted 2026-05-06 (BLOCKED)

After user approval, executed the standalone ik_llama.cpp directional path:

- **Build**: ik_llama.cpp main HEAD `b937219` builds clean at -j96 with znver5 native + OpenMP, no CUDA. Binaries land at `/mnt/raid0/llm/ik_llama.cpp/build/bin/`. Note: `LD_LIBRARY_PATH` must point at `build/src:build/ggml/src:build/examples/mtmd` because the system has another `/mnt/raid0/llm/llama.cpp/build/bin/libllama.so` on the default search path which has incompatible symbols.
- **Main HEAD does not load the drafter** — fails with `unknown model architecture: 'gemma4_mtp'`. The drafter GGUF (`Radamanthys11/Gemma-4-31B-it-assistant-GGUF`) declares `general.architecture = gemma4_mtp`, which is added by the open draft PR #1744 but not yet in main.
- **PR #1744 branch fetched** (`refs/pull/1744/head` → `pr-1744`, SHA `0f728f380d`), incremental rebuild ~2 min.
- **Baseline (no MTP) on EPYC canonical**: `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active numactl --interleave=all taskset -c 0-95 llama-server -m gemma-4-31B-it-Q4_K_M.gguf -t 96 -fa 1 --no-mmap --no-warmup -c 4096 -b 2048 -ub 512` → single `/completion` request with deterministic temp=0 seed=42, n_predict=128. **7.05 t/s**. Matches prior measurement of **6.85 t/s** at `data/cpu_optimization/2026-05-04-q6k-default-on-validation/a2-gemma4_31b_q4km-q6kavx0.json` within 3% noise. Confirms dense 31B Q4_K_M is BW-bound at ~25% of 460 GB/s aggregate (consistent with `feedback_cpu_decode_bw_bound.md`). The "idle CPU resources" the user observed during the bench is the expected DRAM-stall behaviour for BW-bound dense decode.
- **MTP attempt under PR #1744**: `-mtp -md drafter --draft-max 3 --draft-p-min 0.0` → drafter partially loads (gemma4_mtp arch parsed, 48 tensors loaded), then:
  1. `Oops: tensor with strange name mtp_post_proj.weight` and `Oops: tensor with strange name mtp_pre_proj.weight` — tensor mapping incomplete in PR #1744 (`gguf-py/gguf/tensor_mapping.py` and/or `src/llama-load-tensors.cpp` doesn't recognize these post/pre projection tensors).
  2. `srv init: MTP enabled via flag, but model has 0 NextN layers. Disabling speculative.` — the gate at `examples/server/server-context.cpp:282` checks `llama_model_n_nextn_layer(target) > 0` on the TARGET (which is the regular Gemma 4 base, no NextN). PR #1744 added the new `gemma4_mtp` arch class for the drafter but did not update this gate. The check should branch on whether the DRAFTER is `gemma4_mtp`, not whether the TARGET has NextN.
  3. `slot init: id 0 | task -1 | speculative decoding context initialized` — contradicts (2). The slot init re-enables speculative based on the drafter loaded, but the disabled-state from (2) is inconsistent.
  4. **Segmentation fault (core dumped) on first `/completion` request** — the inconsistent state from (2)+(3) leads to a NULL deref or similar.
  - Core dump was 27 GB; deleted to recover space. Per `feedback_no_core_dumps.md` set `ulimit -c 0` for any future shell launching ik_llama.cpp binaries.
- **First MTP attempt**: segfault. Root cause located in `examples/server/server-context.cpp:35-39` — `params_use_gemma4_external_mtp` had a chicken-and-egg precondition (`params.speculative.type == COMMON_SPECULATIVE_TYPE_MTP`) that is itself a CONSEQUENCE of the helper returning true. Helper always returned false → gate at line 356 fell through to the "Disabling speculative" branch → downstream NULL deref.

- **Patch (1 line)**: removed the type==MTP precondition. `has_mtp` flag + drafter arch `gemma4_mtp` is sufficient.

```diff
 static bool params_use_gemma4_external_mtp(const gpt_params & params_base) {
+    // Note: previously checked params_base.speculative.type == COMMON_SPECULATIVE_TYPE_MTP,
+    // but that field is set as a consequence of this helper returning true (slot init).
+    // The has_mtp flag plus a gemma4_mtp drafter arch is sufficient evidence of intent.
     return params_base.has_mtp &&
-        params_base.speculative.type == COMMON_SPECULATIVE_TYPE_MTP &&
         model_has_arch(params_base.speculative.model_dft, "gemma4_mtp");
 }
```

- **G0.4 SUCCESS** with the patch:

| Config | Throughput | Acceptance | Speedup |
|--------|------------|------------|---------|
| **Baseline (no MTP)** | 7.05 t/s | — | 1.0× |
| **Patched MTP, draft-max=3** | **21.02 t/s** | 84.3% per-token (91/108) | **2.98×** |
| (PR #1744 mixed-CPU/GPU bench) | 21.1 → 48.6 | 74% | 2.3× |

**Pure-CPU EPYC exceeds the PR's mixed-CPU/GPU speedup ratio.** The small 500 MB drafter amortizes well against the slow dense 31B target on CPU; MTP is relatively more impactful when the target is BW-bound. The "Oops: strange tensor name mtp_post_proj.weight / mtp_pre_proj.weight" warnings remain but are cosmetic (size-accounting iteration at `src/llama.cpp:2509` doesn't recognize non-`blk.*` tensors; loading is unaffected via `create_gemma4_mtp_tensors`).

### G0.4-26B — 26B-A4B MoE result (in-house GGUF + bench, 2026-05-06)

Converted `google/gemma-4-26B-A4B-it-assistant` HF safetensors (840 MB BF16, single file, 48 tensors) to Q8_0 GGUF (441 MB) using PR #1744's `convert_hf_to_gguf.py` Gemma4Assistant class + `llama-quantize` Q8_0. No conversion errors. Output drafter is structurally identical to the 31B drafter (same Gemma4Assistant arch, same 4-layer transformer with sliding+full attention pattern), differing only in width (16/8 heads vs 32/16, backbone_hidden 2816 vs 5376).

| Run | Throughput | Acceptance | Speedup |
|-----|-----------|------------|---------|
| 26B-A4B baseline (no MTP) | **41.49 t/s** | — | 1.0× |
| 26B-A4B + MTP draft-max=3 | **44.12 t/s** | **58.7% per-token** (81/138), 73.9% per-batch (34/46) | **1.06×** |
| (vs 31B Dense + MTP for context) | 7.05 → 21.02 | 84.3% | 2.98× |

**Empirical confirmation of the lilting.ch contradicting-evidence finding** (intake-527 `contradicting_evidence`): MoE batch=1 sees marginal MTP gains because per-draft-candidate expert routing triggers extra weight loads that erode the bandwidth savings. Two compounding effects:

1. **Drafter undersized for MoE prediction**: 16/8 heads at 1024 hidden cannot reliably predict an MoE target whose 80-expert routing is more discontinuous than dense FFN behavior. Acceptance dropped from 84.3% (31B Dense) to 58.7% (26B-A4B).
2. **Verifier expert-load cancellation**: each accepted draft token requires distinct expert weight loads on the verifier; on dense the verifier amortizes K accepted tokens against the same FFN weights, on MoE the K tokens may pull from up to K×8 distinct experts, eroding the bandwidth saving that makes MTP win.

**Critical implication for deployment**: 26B-A4B + MTP at 44.12 t/s is **slower than the existing Coder-30B-A3B Q4_K_M baseline of 49.1 t/s** (project_96t_single_node_operating_point.md). The MTP gain does not compensate enough to displace the existing coder role. **Tier X (eval-only, not deployable).**

This result narrows the Gemma 4 MTP deployment surface to **31B Dense + MTP at architect tier (21 t/s)** as the only viable Gemma 4 candidate on EPYC. The dense-vs-MoE asymmetry of MTP gains is now a documented quantitative finding, not just a third-party warning.

### G0.4 follow-up

| Option | Status |
|--------|--------|
| (i) Watch PR + retry | superseded |
| **(ii) Patch PR ourselves** | **✓ DONE** — 1-line fix; pure-CPU number obtained |
| (iia) Push the fix upstream | OPEN — small, isolated change with measurable benefit; worth contributing |
| (iii)/(iv) | superseded |

The result clears the conceptual blocker. Open follow-ups now belong on the production / registry path, not on the directional-bench path: full quality benchmark on standard suite, comparison against Coder-30B-A3B Q4_K_M baseline (49.1 t/s) for the architect-vs-coder role decision, and composition test with `--moe-spec-budget` (only relevant on the 26B-A4B variant which is not yet measured because community GGUF for the assistant model doesn't exist).

## Cross-references

| Type | File | Why |
|------|------|-----|
| Closed handoff | `handoffs/completed/mtp-speculative-decoding.md` | Prior MTP-1 work on Qwen3.5 hybrid; explains the recurrent-verify wall that does NOT apply here |
| Active handoff | `handoffs/active/inference-acceleration-index.md` | Listed as MTP-class reopener; this is a separate track (different architecture class) |
| Active handoff | `handoffs/active/multimodal-pipeline.md` | Gemma 4 E-series candidates; G0c relevant if multimodal unification proceeds |
| Active handoff | `handoffs/active/moe-spec-cpu-spec-dec-integration.md` | Verifier-side budgeted-expert; potential composition with drafter-side MTP, untested |
| Active handoff | `handoffs/active/gpu-acceleration-path.md` | Architect-tier 31B Dense candidate path if CPU stalls |
| Intake | intake-527 (this entry's seed) | Google blog announcement |
| Intake | intake-251, intake-252, intake-256 | Gemma 4 base family |
| Wiki memory | `project_96t_single_node_operating_point.md` | Coder-30B-A3B 49.1 t/s baseline for G1 comparison |
| Wiki memory | `feedback_speed_verify_via_llama_bench.md` | One-shot bench protocol if G1 ever runs |

## Open questions outside the gate sequence

- Is there a public Google paper on the MTP drafter architecture per variant, or only the blog post?
- Has anyone outside Google measured 26B-A4B + drafter on EPYC-class CPU (96+ cores, 1TB+ DDR5)?
- What's the relationship between Google's MTP heads and the DeepSeek-V3 / GLM-5 MTP we already track? Architecture-class shared, or independent re-derivation?
- Does ik_llama.cpp's `--spec-type mtp` flag generalize to non-Gemma MTP heads (e.g., DeepSeek-V3, GLM-5), or is it Gemma-specific? If general, the fork-port investment amortizes across multiple targets.
