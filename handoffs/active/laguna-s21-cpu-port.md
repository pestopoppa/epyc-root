# Laguna S 2.1 CPU Port — Experimental Branch

**Status**: IN PROGRESS on `experimental-v8-refresh-20260724` — base arch + DFlash landed as `afa770382` (+`6c44557bf` thread-safety); GPU IQ2 smoke GREEN post-repair, CPU q8 lane blocked on a real model arithmetic miss + a harness attribution defect. See 2026-07-25 audit section. (Was: stub, created via /research-intake Stage-2, operator-approved 2026-07-22)
**Created**: 2026-07-22
**Priority**: P2
**Effort**: Low-Medium (base arch ~350 LOC; DFlash spec path is a separate larger port)
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

- [x] Forward-port base Laguna arch (merged PR #25165 commits, ~350 LOC: `src/models/laguna.cpp` +332, `models.h`, 1-3-line touches to `llama-arch`/`llama-model`/`llama-vocab`, `conversion/laguna.py` +207) onto a FRESH-pulled `llama.cpp-experimental` off `production-consolidated-v7`; validate S-2.1 Q4_K_M loads + coherence/garbage smoke ✅ 2026-07-25 — landed as `afa770382` on `experimental-v8-refresh-20260724` (superset: includes the DFlash spec path NOT in the PR); Q4 CPU + IQ2 GPU gates green in `/mnt/raid0/llm/tmp/v8-gates-20260724/{laguna-q4-cpu,laguna-iq2-gpu,laguna-dflash-contract}` (exit 0), `test-llama-archs`/`test-chat-auto-parser` pass in ctest; 2026-07-25 audit verified graph idioms match sibling archs (NEOX rope group, Qwen3-style QK-RMSNorm, per-layer YaRN/plain-RoPE split sound, softplus gate width-checked on both target and drafter sides)
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
q8_0 model arithmetic error. Open items:

- [ ] **L-1 (silent-wrong risk) — make the SWA contract explicit in conversion.**
  `conversion/laguna.py` never writes `SLIDING_WINDOW_PATTERN` (only `add_sliding_window`,
  `laguna.py:86-89`) — the 4-dense-first layer pattern is an implicit code-side default
  (`laguna.cpp:39-41`); and `rope_freq_base_train_swa` silently defaults to the full-attn
  YaRN base (500000) when `ROPE_FREQ_BASE_SWA` is absent (`laguna.cpp:47-49`) though SWA
  layers intend θ=10000. Write both keys at conversion + make the C++ fallback loud
  (warn or abort). Any future Laguna variant converts silently-wrong today.
- [ ] **L-2 (integration gap) — validate encoder input width explicitly.** DFlash encoder
  assumes draft `n_embd` == target hidden size (`dflash.cpp:15` vs `speculative.cpp:1325`);
  `LLM_KV_TARGET_HIDDEN_SIZE` exists in `llama-arch.h` but is never read; no divisibility
  assert on `n_feat = n_embd_inp_enc()/n_aux` (`dflash.cpp:128`). Mismatch currently fails
  only indirectly via `fc` shape at load. Read the key and check explicitly.
- [ ] **L-3 (masking risk) — bound the non-finite feature sanitize.** `speculative.cpp`
  (+1471-1490) unconditionally clamps target features to ±65504/NaN→0 on ALL backends
  (comment blames Metal f16), warning once per process — after the first warning it silently
  masks real target-model numerical bugs. Gate it per-backend or export a per-batch bad-count
  telemetry counter.
- [ ] **L-4 (harness defect, root cause still open) — fix `summarize()` attribution
  ordering.** The 23:47Z "warmup" failure was a MISATTRIBUTION: all 20 cells' warmups passed;
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
- [ ] **L-6 (gate design) — add an acceptance/net-speed floor before any production DFlash
  enablement.** Measured: GPU IQ2 acceptance 21.6% pooled — dflash is +35% on primes but
  **−28%/−37% on the other two prompts**; CPU acceptance 17.2% (q4) / 19.0% (q8). This is
  consistent with the March block-diffusion NO-GO (27% accept) and the target-side quant-noise
  mechanism — the BF16 drafter does not fix it. No gate anywhere enforces acceptance or
  speedup; median-of-medians summaries can mask per-prompt net-negative. Add: per-prompt net
  decode ratio surfaced + a floor gate (e.g. pooled acceptance ≥ X AND no prompt-class
  net-negative) as a precondition for enabling `--spec-type draft-dflash` in any lineup.
  Q8_0-target CPU (+11.9% aggregate at q4 — sole positive lane) is the only arm near the
  reopen condition; IQ2-target GPU currently reads as a NO by the March precedent's own logic.
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

All Laguna quality/speed numbers to date are poolside self-reported OBSERVATIONS per MEASUREMENT.md — none gate a decision. The iqk (Laguna UD-IQ2_M beneficiary), DFlash (accept-rate bench + draft-dflash port), and architect-bench rows live in the linked handoffs and are cross-indexed under the "Laguna S 2.1 experimental-kernel cluster" in [`inference-acceleration-index.md`](inference-acceleration-index.md) so the whole cluster can be tackled in one session.
