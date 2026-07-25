# Laguna S 2.1 CPU Port — Experimental Branch

**Status**: IN PROGRESS on `experimental-v8-refresh-20260724` — base arch + DFlash landed as `afa770382` (+`6c44557bf` thread-safety); the required GPU IQ2 and CPU Q4 lanes are complete. CPU Q8 characterization retains a real arithmetic miss but is not a promotion lane under operator scope. DFlash enablement is a gate FAIL/no-go. See 2026-07-25 audit section. (Was: stub, created via /research-intake Stage-2, operator-approved 2026-07-22)
**Created**: 2026-07-22
**Priority**: P2
**Effort**: Low-Medium (base arch ~350 LOC; DFlash spec path is included in the v8 carrying work, with enablement separately gated)
**Categories**: local_inference, moe_optimization, speculative_decoding, quantization, hardware_optimization
**Source**: intake-879 (poolside launch blog) + intake-880 (GGUF model card) + Stage-2 deep-dive 2026-07-22
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`iqk-iquant-enablement.md`](iqk-iquant-enablement.md) — Laguna UD-IQ2_M IQ-quant acceleration (already-coded branch; add Laguna as 5th beneficiary)
- [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) — the DFlash draft-dflash spec path + accept-rate bench
- [`deepseek-v4-flash-cpu-port.md`](deepseek-v4-flash-cpu-port.md) — the reusable experimental-branch new-arch CPU-port precedent (pattern, not coupling)
- [`architect-model-selection-bench.md`](architect-model-selection-bench.md) — Laguna as a candidate once served

---

## Objective

Port the **Laguna** architecture (poolside/Laguna-S-2.1: 118B-total / 8B-active MoE — 256 routed experts top-10 + 1 shared; 48 layers mixed 12 full-attention + 36 sliding-window(512); **sigmoid**-routed MoE with score-correction bias; **softplus attention-output gate**; QK-norm; per-layer-type RoPE — YaRN on full layers, plain RoPE on SWA layers) onto an experimental llama.cpp branch on the EPYC 9655 CPU stack, validate quality + throughput vs the production kernel, and merge into a new production version **only** after both gates pass. **NEVER modify frozen `production-consolidated-v7`** — all work on `llama.cpp-experimental` off a fresh production pull, per the four-step workflow.

## Why now

`/research-intake` ingested Laguna 2026-07-22; the operator is downloading Q4_K_M (poolside, 75GB) + UD-IQ2_M (unsloth, 37GB) + the DFlash-BF16 drafter (2.2GB). Laguna is a weight-class-leading agentic coding model whose 8B-active MoE shape is favorable for bandwidth-bound CPU decode, and it lands directly on the active spec-dec-mtp-refresh line. **Base arch support is already MERGED upstream** (ggml-org/llama.cpp PR #25165, 2026-07-22T01:54Z, approved), so the forward-port can pull from upstream rather than only poolside's fork.

## Key facts (Stage-2 deep-dive, 2026-07-22)

- **PR #25165 is MERGED** (22 files, +1091/−1): base arch only in `src/models/laguna.cpp` (+332) + `conversion/laguna.py` (+207). The `conversion/` package is **already present** in the v7 tree → the converter applies clean. **DFlash spec path is NOT in the PR** — it lives only in poolside's fork branch `laguna` (`--spec-type draft-dflash`).
- **DFlash = z-lab block-diffusion** (arXiv:2602.06036, intake-158), SAME codebase (GGUF `dflash.target_layers` = HF `target_layer_ids` +1, matching z-lab `offset=1`). No timestep/denoise tensors → single-pass conditioned block drafter, not iterative diffusion. Draft cost is cheap; the open question is acceptance.
- **DFlash-on-CPU is still likely NO-GO for quantized targets.** The March NO-GO (`../completed/dflash-block-diffusion-speculation.md`, 27% accept, AR drafter won 36.5 vs 13.0 t/s) roots in TARGET-side quant noise in the conditioning hidden states — which poolside's BF16 drafter does NOT fix. Only a near-lossless target (Q8_0 / F16) plausibly reopens it. See `speculative-decoding-mtp-refresh.md`.
- **UD-IQ2_M iqk coverage**: 92.2% of bytes are IQ-quant (IQ2_XXS 51% + IQ3_XXS 37% + IQ2_S 1.4% + IQ4_XS 2.3%), stubbed on frozen v7; the code-complete `iqk-iquant-enablement` branch already covers 97.6% of the IQ bulk (all but the 2 IQ4_XS tensors). No new kernel needed — see that handoff.

## Tasks

- [x] Forward-port base Laguna arch (merged PR #25165 commits, ~350 LOC: `src/models/laguna.cpp` +332, `models.h`, 1-3-line touches to `llama-arch`/`llama-model`/`llama-vocab`, `conversion/laguna.py` +207) onto a FRESH-pulled `llama.cpp-experimental` off `production-consolidated-v7`; validate S-2.1 Q4_K_M loads + coherence/garbage smoke ✅ 2026-07-25 — landed as `afa770382` on `experimental-v8-refresh-20260724` (superset: includes the DFlash spec path NOT in the PR). Required CPU Q4 evidence is at `epyc-inference-research/data/kernel-v8-candidate/laguna-cpu-dflash-exact-tip/run-20260725T112845Z-67a433bf4-noswap/` (nested `run-20260725T113030Z`): base median `7.078103` t/s, DFlash median `8.028143` t/s, but acceptance `17.2267%` fails the lineup floor. Final hardened GPU IQ2 artifact `epyc-inference-research/data/gpu-mi210/laguna-iq2-kv-sweep-exact-tip/run-20260725T125201Z` is post-identity, `15/15`, and observation-only: A q8/FA-on `33.992845`, B f16/FA-on `35.490117`, C f16/FA-off `33.782293`; B/A `+4.404668%`. `test-llama-archs`/`test-chat-auto-parser` pass in ctest; 2026-07-25 audit verified graph idioms match sibling archs (NEOX rope group, Qwen3-style QK-RMSNorm, per-layer YaRN/plain-RoPE split sound, softplus gate width-checked on both target and drafter sides)
- [ ] Confirm the PR-author-flagged "GQA head-ratio backend dispatch" bug does not hit the CPU build (PR touches no `ggml/` files; per-layer `n_head` handled at graph level → likely CUDA-only)

---

## 2026-07-25 v8 audit (Claude session, operator-requested) — findings + new tasks

Deep review of `afa770382`/`6c44557bf` + the certification harness
(`laguna_pgpu1_dflash_runner.py`, `laguna_cpu_dflash_observation_runner.py`). Kernel-side
code is clean (conversion surface complete 1:1 vs `load_arch_tensors`; templates match
`test-chat-auto-parser` expectations; the thread-safety fix is a textbook atomic-exchange).
The harness relaxations were audited commit-by-commit and are **NOT vacuous**: RESULT_JSON
exact numeric equality, `finish_reason=stop`, completion floors, anti-garbage, and
`draft_n>0` all still hard-gate — and post-relaxation the harness caught a REAL deterministic
q8_0 model arithmetic error. Remaining items:

- [x] **L-1 (silent-wrong risk) — make the SWA contract explicit in conversion.** ✅ 2026-07-25 — landed in `89d55f161`.
  Before the fix, `conversion/laguna.py` never wrote `SLIDING_WINDOW_PATTERN` (only `add_sliding_window`,
  `laguna.py:86-89`) — the 4-dense-first layer pattern is an implicit code-side default
  (`laguna.cpp:39-41`); and `rope_freq_base_train_swa` silently defaults to the full-attn
  YaRN base (500000) when `ROPE_FREQ_BASE_SWA` is absent (`laguna.cpp:47-49`) though SWA
  layers intend θ=10000. The landed conversion writes both keys and makes the C++ fallback loud.
- [x] **L-2 (integration gap) — validate encoder input width explicitly.** ✅ 2026-07-25 — landed in `89d55f161`. DFlash encoder
  previously assumed draft `n_embd` == target hidden size (`dflash.cpp:15` vs `speculative.cpp:1325`);
  `LLM_KV_TARGET_HIDDEN_SIZE` existed in `llama-arch.h` but was never read; there was no
  divisibility assert on `n_feat = n_embd_inp_enc()/n_aux` (`dflash.cpp:128`). Mismatch
  previously failed only indirectly via `fc` shape at load. The landed change reads the key
  and checks explicitly.
- [x] **L-3 (masking risk) — bound the non-finite feature sanitize.** ✅ 2026-07-25 — landed in `89d55f161`. `speculative.cpp`
  (+1471-1490) previously unconditionally clamped target features to ±65504/NaN→0 on ALL backends
  (comment blames Metal f16), warning once per process — after the first warning it silently
  masks real target-model numerical bugs. The landed change bounds that sanitize behavior.
- [x] **L-4 (harness defect) — fix `summarize()` attribution
  ordering.** ✅ 2026-07-25 — landed in `978ca540`; the exact CPU final reports semantic failure status before schema completeness. The 23:47Z "warmup" failure was a MISATTRIBUTION: all 20 cells' warmups passed;
  the real failure was 5/5 `q8_0_base` cells with `incorrect prime sum: 361` (vs 311),
  deterministic at temp0/seed 424242. Mechanism: error-path result rows lack the `"warmup"`
  key and `summarize()` checks `row["warmup"]` before ever surfacing `primary_error`. The
  `dc61034a` partial-summary patch preserves evidence but the strict path STILL dies on the
  next field check (`non-numeric replicate prompt_tps`) instead of reporting the semantic
  error. Make summarize() status-first: surface `primary_error` before schema-completeness
  checks.
- [ ] **L-5 (model finding, investigate before more prompt surgery) — the q8_0 base
  deterministic arithmetic miss.** Sum 361≠311 with the correct prime list, plausibly induced
  by the `e2ea1df7` prompt constraints (≤2-sentence rationale, no enumeration → no shown
  arithmetic). Decide: relax the no-enumeration cap for the CPU lane, or accept and rerun with
  a different seed sweep — but do NOT paper over it with a validator relaxation; it is exactly
  the class of failure the harness exists to catch.
- [x] **L-6 (gate design) — add an acceptance/net-speed floor before any production DFlash
  enablement.** ✅ 2026-07-25 — gate implemented in `733c2cee`/`2bbd4109`; current DFlash result is FAIL/no-go, not an enablement. Measured: GPU IQ2 acceptance 21.6% pooled — dflash is +35% on primes but
  **−28%/−37% on the other two prompts**; CPU acceptance 17.2% (q4) / 19.0% (q8). This is
  consistent with the March block-diffusion NO-GO (27% accept) and the target-side quant-noise
  mechanism — the BF16 drafter does not fix it. The landed runner now surfaces per-prompt net
  decode ratios and fails closed unless pooled acceptance is at least 60% with no prompt-class
  net-negative. Q4 CPU improved aggregate decode by 13.42% but its 17.23% acceptance still
  fails; IQ2-target GPU remains a NO by the March precedent's own logic.
- [ ] **L-7 (minor) — tighten the normalize prompt.** `bed4a1d4` states "JSON `sum` … must be
  1.0" in the prompt, so the validator's `sum==1.0` check no longer tests computation (the
  normalized values 0/0.2/0.3/0.5 are still computed+checked). Reword so the gated value is
  not disclosed, or drop that sub-check from the gate accounting.
- [ ] **L-8 (hygiene) — promote the ad-hoc GPU smoke artifact to a script.** The
  `epyc.laguna_iq2_dflash_candidate_smoke.final_postrepair.v1` summary schema is written by
  no script under `scripts/` — bespoke one-off, honestly labeled non-gating, but
  unreproducible. Fold it into `laguna_pgpu1_dflash_runner.py` or delete after the formal
  P-GPU-1 run supersedes it.

## Notes

Laguna evidence includes both poolside self-reported observations and the local exact-tip GPU KV artifact above; neither is decision-grade or a production-enable gate under MEASUREMENT.md. The iqk (Laguna UD-IQ2_M beneficiary), DFlash (accept-rate bench + draft-dflash port), and architect-bench rows live in the linked handoffs and are cross-indexed under the "Laguna S 2.1 experimental-kernel cluster" in [`inference-acceleration-index.md`](inference-acceleration-index.md) so the whole cluster can be tackled in one session.
