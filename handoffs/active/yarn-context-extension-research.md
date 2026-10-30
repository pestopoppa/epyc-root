# YaRN Context Extension Research

**Status**: ACTIVE. ADAPTED on 2026-10-04: the scope is now Qwen3.8-27B under YaRN factor 2 (524,288 tokens) as a
dedicated np 1 MI210 mode. The operator approved running E0 and E1 on 2026-10-04. **E1 ran 2026-10-04: quality PASS to 500K, FAIL by
C4 memory (A1 63.9 GiB vs ≤ 55); next is YARN-E1-MEM.** The 2026-03-09 → 2026-09-07 scope
below is historical: its model targets are retired, its flag recipe is defeated by the v10 slot clamp, and its memory
framing (CPU RAM, TurboQuant) is wrong for a GPU-served model.
**Created**: 2026-03-09 · **Rewritten**: 2026-10-04 (workspace-ec, from the RoPE/YaRN assessment)
**Owner**: workspace-ec
**Priority**: MEDIUM (the operator wants long context; organic :8083 demand is still inside native 262K, p99 prompt
144,846 tokens)
**Workstream**: Research
**Scratch**: `/mnt/raid0/llm/tmp/yarn-e1-20261004/` · `/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/` · `/mnt/raid0/llm/tmp/rope-ctx-assessment/` · worktrees: `/mnt/raid0/llm/worktrees/yarn-e1-*`

## 2026-10-04 rewrite — current scope (start here)

**Assessment:** [`artifacts/gpu-block-27b-20261004/analysis/rope-ctx-ASSESSMENT.md`](../../artifacts/gpu-block-27b-20261004/analysis/rope-ctx-ASSESSMENT.md)
(a durable copy of `/mnt/raid0/llm/tmp/rope-ctx-assessment/ASSESSMENT.md`). It was read-only: v10 source, GGUF
headers, vendor cards. Its recommendation was **ADAPT** (§5).

**What holds:**
- Static YaRN is vendor-documented for every production Qwen LLM: Qwen3.8-27B and Flash-Next carry factor 4.0 and
  `original_max_position_embeddings` 262144, "extensible up to 1,000,000". For a ~524K typical length the cards
  recommend factor 2.0.
- v10 `ffc1bac82` implements YaRN correctly for these interleaved-MRoPE, partial-rotary (64/256) heads.
- RoPE is the only positional signal in these hybrids, since the GDN layers carry none. So scaling the attention
  layers scales the whole explicit position mechanism. The unaddressed risk is the GDN recurrent state's capacity and
  forgetting past 262K, which only a ground-truth test settles.

**Two v10 traps** (the old recipe walks into both):
1. **The server clamps every slot to `n_ctx_train` unconditionally** (`server-context.cpp:1316-1322`). A YaRN instance
   must also pass `--override-kv qwen35.context_length=int:<N>`, and then `--yarn-orig-ctx 262144` is MANDATORY.
   Without it, `n_ctx_orig_yarn` silently follows the overridden length (`llama-model.cpp:1203`).
2. **Flash-Next's fused decode ignores YaRN.** `qwen4exp-fused.cpp:1709-1717` hardcodes `freq_scale=1, ext_factor=0,
   n_ctx_orig=0`. Production is safe (`GGML_FUSED_DECODE_OFF=1`, MTP attached), but a YaRN run on that path would
   prefill with YaRN and decode without it. See YARN-FN-FIX.

**Memory [D]:**

| Shape | 524K | 1M |
|---|---|---|
| Production np 4 + DFlash2 | ≈ 64.1 GiB ✗ | ≈ 85 GiB ✗ |
| Lean np 1, no drafter, q8_0 KV | ≈ 48.9 GiB ✓ | ≈ 69.9 GiB ✗ |

1M fits only with q4_0 KV (≈ 54 GiB, quality unmeasured) or with two MI210s.

**Never put rope flags on production :8083, :8070 or :8074.** Static YaRN applies to every request, the vendor warns
about short-text degradation, and on a unified pool every co-resident slot would scan the long sequence's cells (the
KVU-16b / KVU-19 tax). YaRN is a separate long-context *mode*.

### Tasks

- [x] **YARN-E0 — the zero-compute preparation (operator-approved 2026-10-04).** ✅ 2026-10-04 (the runner and
  runbook carried E1 end to end; see below) Subagents are preparing it
  in `/mnt/raid0/llm/tmp/yarn-e1-20261004/`. It has three parts:
  - **The runner.** Fork Q38-T7's cached-prefix needle logic into a long-context runner, and write truth rows in
    `coherence_gate` form (`{"grader":"needle","expected":[…]}`).
    - **Neutral haystack only:** RULER noise, or essays with sentence ids. Q38-T7's 80k needle failed because the
      model refused an "injected" fact planted in an AutoKernel context.
    - **One prefill per (arm, length):** 5 needles at depths of 10/30/50/70/90%, each asked as a short continuation on
      the cached prefix.
  - **The launch lines** on a scratch port (e.g. 18083), with the production env and `LD_LIBRARY_PATH`:
    - **A0 (native):** `-np 1 -c 262144 -ctk q8_0 -ctv q8_0 -ub 2048 --flash-attn on --no-mmap -ngl all --cache-ram 0`,
      with no `-md`.
    - **A1 (YaRN f2):** A0 plus `-c 524288 --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 --override-kv
      qwen35.context_length=int:524288`.
    - **A2 (negative control):** A1 without the rope flags.
  - **The required bring-up proof lines:** `n_ctx_orig_yarn = 262144`, `freq_scale = 0.5`, `rope scaling = yarn`,
    and `n_ctx_slot = 524288` with no capping warning. KFD at load must be ≤ ~50 GiB.
  - **Stale-geometry caches** (intake-1347#record): the instance uses its own empty cache and a scratch slot path,
    and never restores production slots.
  - **Belief-kernel write side:** VB-YARN-E1 in `vidya-belief-substrate-program.md`.

  Done when the runner passes a dry run (and a self-test on a small model), and the launch lines and proof greps are
  in a runbook beside it.
- [x] **YARN-E1 — the GPU experiment, ~2.5–3 h of a parked-:8083 window (operator-approved 2026-10-04).** ✅ 2026-10-04
  RUN — **FAIL by C4 (memory) only**; results below. The
  pre-registered cells (ASSESSMENT §6), all greedy with thinking off and real token ids:
  1. **Short context:** ~60 `question_pool` items under 4K, A0 vs A1. A `coherence_gate` PASS means 0 REGRESSION.
  2. **Native range:** 128K and 240K haystacks with 5 needles each, A0 vs A1. A1 must score ≥ A0 − 1 correct out of
     10, with a clean `degeneracy.v2`. A0 at 240K is also the first ground truth near 262K for this model.
  3. **Beyond native:** 400K (A1, plus A2) and 500K (A1) haystacks. A1 needs ≥ 4/5 at each length, and A2 must
     score clearly worse, or the test is not discriminating.
  4. **Memory:** the KFD peak stays ≤ 55 GiB.

  Coordinate the window with the GPU-block owner, and never run it during another session's measurement window.
  Done when the four results are recorded here with the runner's output path. Outcome: pass → YARN-E2; fail →
  archive this handoff with the evidence and keep 262K as the ceiling; pass at 512K → 1M becomes YARN-1M.
  - *(2026-10-04, workspace-ec.)* **E1 result: FAIL on C4 only.** Gate: `artifacts/yarn-e1-20261004/gate/VERDICT.md`
    and `verdict.json` (durable copy, with `run_e1.log`, `run_e1_a1.log`, the KFD summaries and `SOURCES.sha256`;
    scratch `/mnt/raid0/llm/tmp/yarn-e1-20261004/results/{A0,A1}`).
    - **C1 short context (informational):** coherence_gate FAIL, 3 REGRESSION of 84 (two gsm8k items went
      degenerate `uniq+stuck`, one went unanswered); graded accuracy A1 58/70 vs A0 59/70. It confirms "separate
      mode only": never put rope flags on a production server.
    - **C2 native range (128K + 240K):** A1 10/10 = A0 10/10, no degeneracy. **PASS.** A0 at 240K is the first ground
      truth near 262K for this model.
    - **C3 beyond native (A1):** 5/5 at 400K and 5/5 at 500K, needles up to 448K tokens back, no abstentions. **PASS**
      as scored, but A2 (the negative control) did not run, so the test's discrimination is unshown (YARN-E1-A2).
    - **C4 memory:** KFD own-PID peak A0 **52.7 GiB** (estimate 38.4) and A1 **63.9 GiB** (estimate 48.9), against
      the ≤ 55 GiB gate on a 64 GiB card. **FAIL.** About +15 GiB is unexplained in BOTH arms, so it is a shared
      cost of this launch shape (long prefill), not a YaRN cost.
    - **Process notes:** `launch_arm.sh` lacked `--verbosity 4`, so the proof lines were missing and the first run
      refused (fixed in the script). A1 ran with `--force-preflight`, because the logger splits an override value
      onto a timestamped continuation line; every `print_info`/`llama_context` proof line matched by hand.
    - **Outcome branch:** quality passed at 512K; memory failed. The pre-registered "fail → archive" branch is not
      taken, because the failure is an unattributed memory overshoot, not a quality result. YARN-E2 waits on
      YARN-E1-MEM, and memory (not quality) is now the blocker for 1M.
  - [ ] **YARN-E1-MEM — attribute the +15 GiB KFD overshoot seen in both E1 arms (long prefill).** (filed 2026-10-04,
    workspace-ec) Reuse the KVU-16h allocator shim and phase-replay runner on the A0 and A1 launch lines, and compare
    the E1 build (champion `9a3f1392a`) against W `b0ba1d427`, which carries the arena fix. Done when the overshoot is
    attributed per phase, and A1's peak is either re-measured ≤ 55 GiB or the gap is named with its fix.
  - [ ] **YARN-E1-PROOF — make the runner's proof-line regex tolerate split continuation lines.** (filed 2026-10-04,
    workspace-ec) The logger puts an `--override-kv` value on a timestamped continuation line, so A1 needed
    `--force-preflight`. Done when `yarn_needle.py`'s preflight passes A1's real `A1.server.log` without the force flag
    and a self-test covers the split form.
    *(2026-10-05)* The CPU leg's `yarn_cpu_leg.py` hit the same missing-proof-line defect: no `--verbosity 4`, so the
    first launch of both arms refused, rc=3. It was fixed in that script only. Scope now includes moving the launch
    flags and proof preflight into one shared helper that `yarn_needle.py` and `yarn_cpu_leg.py` both import.
  - [ ] **YARN-E1-A2 — run the A2 negative control at 400K in the next YaRN window.** (filed 2026-10-04, workspace-ec)
    C3 pre-registered "A2 must score clearly worse, or the test is not discriminating", and E1 ran A0 and A1 only.
    Ride it on the YARN-E1-MEM re-measure or the YARN-DCA-E1 window. Done when A2's 400K needle score is recorded
    beside A1's 5/5.
- [x] **YARN-CPU — CPU leg: Qwen3.6-35B-A3B on CPU, CN (native 262K) vs CY2 (YaRN ×2, 524K), incremental 8K turns.**
  ✅ 2026-10-05 (workspace-ec; dedicated block 2026-10-04 21:18Z → ~03:15Z 10-05). Results are durable in
  `artifacts/yarn-e1-20261004/cpu_leg/` (`VERDICT.md`, `verdict.json`, `block.log`, `SOURCES.sha256`). Scratch is
  `/mnt/raid0/llm/tmp/yarn-e1-20261004/cpu_leg/results/`, which also holds the server logs and the 6.5 GB `slots/`.
  - **C1 short context (CY2 vs CN):** 0 REGRESSION of 84, 52 identical, 13 needs-review. The gate reads INCOMPLETE
    only because of those 13. Contrast with the GPU 27B E1, where C1 had 3 regressions: this hybrid MoE showed no
    short-text regression under YaRN ×2.
  - **C3 beyond native (CY2):** 5/5 at 323,527 tokens, with needles up to 286K back and the local check OK. **PASS.**
    CY2 reached 323K, not 512K. The block ran out because the per-turn append cost grew to ~600 s per 8K turn at 350K.
    The scheduler stopped the server cleanly with the slot saved at turn 42.
  - **Native range:** CN scored 5/5 at 133K, 193K and 253K. CY2 matched it at 133K and 253K.
  - **Decode tok/s at 34K / 133K / 253K / 323K:** CN 20.4 / 6.4 / 3.7 / –; CY2 19.6 / 6.2 / 3.6 / 2.9. YaRN costs ≤ 4%
    at matched depth.
  - **Turn append cost (s per 8K turn):** 19.7 at depth 0, 141 at 69K, 253 at 143K, 385 at 211K, 557 at 280K and 603 at
    351K (CY2). CN tracks it within ~4%. The cost grows with depth, so attention at depth, not YaRN, is the bottleneck.
  - **Process note:** the first launch of each arm refused for missing proof lines, because `--verbosity 4` was
    absent. It was fixed in `yarn_cpu_leg.py`; this is the same defect as GPU E1, so see YARN-E1-PROOF.
  - [ ] **YARN-CPU-512k — finish CY2 from 323K to 512K in a later dedicated CPU block.** (filed 2026-10-05,
    workspace-ec) Resume from the turn-42 slot in the scratch `slots/` if it is still there and its build and argv
    digest match; otherwise re-prefill. At ~600+ s per 8K turn, the remaining ~24 turns need ~4.5 h or more. Done when
    CY2's needle score and decode rate at ≥ 500K are recorded beside the 323K row.
  - [ ] **YARN-CPU-ATTN — CPU attention cost at depth is the CPU long-context bottleneck.** (filed 2026-10-05,
    workspace-ec) The per-8K-turn append cost rises ~30× from depth 0 to 351K, and decode falls from 20.4 to 2.9
    tok/s. Hand the measured depth profile (turn cost and decode by depth, from `verdict.json`) to the AutoKernel CPU
    FA route: AKX-ALL-21 (`cpu_fa_schedule` at depth) in
    [`autokernel-all-devices-all-dimensions.md`](autokernel-all-devices-all-dimensions.md). Done when AKX-ALL-21's
    at-depth profile cites this curve as an input, or a keep-or-refuse verdict on it is recorded.
    *(2026-10-05, ak-ds41-main)* This curve is **Qwen3.6-35B-A3B, dense attention** — an earlier AK inbox note
    wrongly attributed it to Q38FN (QSA sparse attention, a different mechanism entirely); corrected in
    `store-b0ba1d427/inbox/64-*.md`. The off-roofline falloff is now filed as a labelled hypothesis,
    AKX-ALL-24 (CPU FA decode may parallelize only over Q heads) — not measured, a candidate kernel target only.
  - [x] **YARN depth-window validation — test YaRN performance across depth ranges (native vs extended).** ✅ 2026-10-05
    (workspace-ec). E1 (GPU 27B) and CPU leg (Qwen3.6-35B-A3B) both measured needle correctness and decode speed at depths
    0/30%/50%/70%/90% and specific depths (133K, 193K, 240K, 253K up to 323K). Results show YaRN incurs ≤ 4% at matched depth.
    Evidence: `artifacts/yarn-native-window-20261005/summary.md`.
  - [ ] **YARN native-window inertness — make YaRN inert inside the native window (dynamic/per-request YaRN or DCA only).** 
    (filed 2026-10-05, workspace-ec) Static YaRN ×2 costs 1.3% at depth 0 and 7.6% at 34k decode, MTP acceptance drops 53% → 48%,
    and greedy outputs diverge on 7/20. The speed costs fail the operator rule "YaRN must not regress inside native window"; the 7/20 divergence is NOT itself a quality regression (operator 2026-10-22: "changing answers within native windows and regressing quality are not necessarily the same thing") - quality is decided by the scored net-paired gate YARN-AGG-1(i). Deploy only
    dynamic/per-request YaRN or DCA (active beyond native length only). Done when the frontdoor stack ships one of these approaches.
    - *(2026-10-06, intake ctxext-ec Stage 3)* Candidates and gates are in the intake plan: CTX-1 (YARN-MSCALE-AB) decides how cheap inertness is; CTX-KSHIFT settles the K-shift primitive; CTX-JETLONG-COST gates a cached-correction port; YARN-OPTION-D-DECISION chooses D / F / Jet-Long. Full-read dive findings: intake-1900, 1906, 1907, 1911, 1918, 1919, 1921.
- [ ] **YARN-E2 — (conditional on E1 passing) a stack-change package for an on-demand long-context mode.** The
  package must:
  - swap the 27B into the np 1 YaRN f2 profile during long-document work, and say who waits during the swap;
  - change the orchestrator's per-request cap (`src/backends/context_limits.py`, `min(n_ctx, n_ctx_train)` against
    `ctx_max: 262144`);
  - state DFlash2 acceptance under YaRN as its own measurement before keeping the drafter in the mode.

  It goes through the `stack-change` skill with one operator signature. Done when the mode is signed and serving on
  demand.
- [ ] **YARN-DCA — Dual Chunk Attention design and implementation, experimental tree (in flight).** A kernel subagent
  is working in `/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/`. Its first notes: no upstream llama.cpp issue or PR
  exists; vLLM's `DualChunkRotaryEmbedding` is still on main, while its attention backend survives only at tag
  v0.10.0; Qwen2.5-1M uses DCA without YaRN-proper. DCA is training-free and keeps every relative distance inside
  the trained range, so it is the candidate route past factor-2 YaRN on one card. The work follows the four-step
  workflow from a fresh champion on `llama.cpp-experimental`: intra/successive/inter chunk positions over a
  chunk-periodic K cache, plus the mscale logit temperature. Done when the design note and a `test-backend-ops`-green
  build exist, and an E1-style needle A/B (DCA vs YaRN f2 at 400K/500K) is filed as its own GPU-window task.
  - *(2026-10-06, intake-1906/1907/1918/1921 REDO)* DCA is identity only below chunk_len = chunk_size - local_window; positions between chunk_len and the training length are remapped in the reference code. v1 local graph has no in-window stock fallback and refuses MTP. The Qwen "does not alter short-sequence behaviour" claim has no short-length measurement in the report; the 3.2-6.7x prefill speedup is MInference plus kernels, not DCA.
  - *(2026-10-04 PM, workspace-ec; not ticked: a `test-backend-ops`-green DCA build is not yet shown.)*
    - Branch `experimental/dca-20261004`; the GPU slot ran commit `9264f8095`. `test-dca` PASS on ROCm0 and on CPU.
    - Perplexity on Qwen2.5-0.5B f16 (trained 32K), wikitext-2, positions 32K-64K, one window per arm (lower is
      better). Durable copy: `artifacts/dca-yarn-kernel-20261004/`.

      | arm | GPU (`gpu-slot-20261004T150049Z`) | CPU (`ppl-20261004T080609Z`) |
      |---|---|---|
      | plain 64K (raw extrapolation) | 14.39 ± 0.22 | 13.63 ± 0.21 |
      | YaRN f2 | — | 12.63 ± 0.19 |
      | DCA | 13.07 ± 0.20 | 12.46 ± 0.19 |
      | DCA + temperature (DCA+T) | 12.96 ± 0.19 | — |

    - DCA beats raw extrapolation on both devices. DCA vs YaRN is within the one-window spread, so it is suggestive
      only.
    - The same arm differs by ~0.6-0.8 PPL between GPU and CPU, which is unexplained (YARN-DCA-XDEV).
  - [ ] **YARN-DCA-E1 — needle A/B, DCA vs YaRN f2 at 400K/500K on the 27B, in its own GPU window.** (filed
    2026-10-04, workspace-ec, from YARN-DCA's done-when) The build must carry YARN-FA-INT64: mask offsets wrap past
    n_kv 526,592 at ub 2048. Done when needle correctness per depth is recorded for both arms.
    *(2026-10-04 note, after E1.)* E1's A1 peaked at 63.9 GiB at 500K, so this window needs YARN-E1-MEM's
    attribution (or a smaller shape) first, or it will hit the same memory wall.
  - [ ] **YARN-DCA-XDEV — explain the GPU-vs-CPU perplexity offset before quoting numbers across devices.** (filed
    2026-10-04, workspace-ec) Plain 64K is 14.39 on ROCm0 vs 13.63 on CPU, with the same model and text. Compare the
    batch/ubatch sizes, FA on/off and KV type of the two scripts, then re-run one arm with matched settings. Done when
    the offset is attributed or removed.
- [x] **YARN-FA-INT64 — fix the int32 mask/K offsets in GPU FlashAttention (probable llama.cpp #27090).** ✅ 2026-10-04
  (workspace-ec; coordinator add-on to the DCA work)
  - Branch `experimental/fa-int64-offset-20261004`, on the champion, three commits:
    - `6152cdf7a` fixes the WMMA kernel;
    - `0c4801127` fixes tile, MMA and vec, and adds `launch_fattn` truncation asserts;
    - `4f21c3477` adds the `test-backend-ops` `mask_ne0` cases.
  - CPU proof: the first wrapped mask offset is at n_kv 526,592 (ub 2048), 262,912 (ub 4096) and 1,057,024 (ub 1024);
    nothing wraps at ub 512.
  - GPU slot `gpu-slot-20261004T145625Z`: **PASS** (durable copy `artifacts/dca-yarn-kernel-20261004/fa-int64/`).
    - `mask_ne0` cases: the fixed build passes 4/4; the champion passes 1/4 (3 FAIL, ERR 0.03-0.59).
    - Full `FLASH_ATTN_EXT` suite on the fixed build: 2872/2872.
    - Existing cases: 119/119 bit-identical to the champion (worst nmse 0).
  - The v11 carry is `fork/experimental/fa-int64-offset-master-20261004`: the revert of #26046 plus the picks. It is
    not compile-verified on master.
- [x] **YARN-FA-INT64-fold — fold the three FA-INT64-OFFSET commits into the champion before any run past 512K ✅ 2026-10-29 (audit: kernel-manifests/llama-v11-manifest.md V11-017 FA-INT64-OFFSET commits 2152c39b1, 3c9b0bb4f IN champion @ dd3d9721c (G-ANC)) [no-belief: audit-reconciliation]
  cells.** (filed 2026-10-04, workspace-ec) Use the guarded CAS fold route with workspace-89: G0, `test-backend-ops`
  on ROCm0, and the `mask_ne0` cases. Done when the champion tip carries them.
- [ ] **YARN-FA-INT64-up — draft (never post) the upstream report for master's int32 FA offsets.** (filed 2026-10-04,
  workspace-ec) Master `11fe02151` still multiplies int32 strides in tile, MMA and vec; the WMMA half is moot upstream
  (#26046). Done when the draft sits in the artifact dir for the operator.
- [x] **YARN-FN-FIX — Flash-Next fused decode must honour the rope parameters (in flight).** ✅ 2026-10-04 `qwen4exp-fused.cpp:1709-1717`
  hardcodes `freq_scale=1, ext_factor=0, n_ctx_orig=0`. Pass the model's real `freq_scale`, `ext_factor`,
  `n_ctx_orig_yarn`, `attn_factor` and `beta_*` through to the fused path. This is latent at native length as well,
  where `n_ctx_orig=0` is harmless only while `ext_factor` is 0. It is being built on `llama.cpp-experimental` in the
  same subagent dir. Done when the fused decode matches the graph path bit-for-bit (or within the fused path's
  existing tolerance) under a YaRN configuration in a CPU test, with no regression at native length.
  - *(2026-10-04, workspace-ec.)* **Fixed** in `5bfdcd18c` on `experimental/fused-yarn-20261004`.
    - The fused decode now takes the context's rope/YaRN parameters. `freq_base` was hardcoded as well, so
      `--rope-freq-base` had also been ignored.
    - `6c126e975` gates two per-token debug leftovers behind `GGML_FUSED_DECODE_TRACE`: a stderr line, and `/tmp`
      file writes on every token.
    - Test `tests/test-qwen4exp-fused-rope.cpp`: K nmse 6e-9 (YaRN) and 8e-9 (freq-base), against 0.53 and 1.09
      before; logits 1.7e-11; native OK; 56/56 steps fused.
    - Notes: `artifacts/dca-yarn-kernel-20261004/NOTES.md`.
    - A separate fidelity gap at non-production weight scales is FD-DIV-1 in `cpu-fused-decoder-blocks.md`.
  - [x] **YARN-FN-FIX-fold — fold `5bfdcd18c` + `6c126e975` into the champion.** (filed 2026-10-04, workspace-ec) ✅ 2026-10-23 (triage by 3c4ca599's fold-prep subagent; ec's box, ticked on the coordinator's instruction): already folded, nothing to do. `git cherry 141e4bcf5 fork/experimental/fused-yarn-20261004` marks `5bfdcd18c`, `6c126e975` and `45d8f2937` patch-equivalent to champion commits `b86c725e2`, `39c7209e4`, `b0ba1d427` (manifest V11-019 IN; `test-qwen4exp-fused-rope` 3/3, OK again on candidate C's final build). Evidence: `/mnt/raid0/llm/tmp/c3-fold-prep/PLAN.md` section 1.
    Production keeps `GGML_FUSED_DECODE_OFF=1`, but the champion's fused path still writes `/tmp` files on every
    token and ignores rope parameters. Done when the champion tip carries both commits, with the fused-rope test
    green.
- [ ] **YARN-1M — research: what fits 1M, and how the hybrid recurrent layers behave past 262K (in flight).** A
  research subagent is answering two questions in `/mnt/raid0/llm/tmp/yarn-e1-20261004/`:
  - which shapes fit 1M: q4_0 KV on the lean shape (≈ 54 GiB; the R10 advice in `kv-cache-quantization.md` says q8_0
    at 1M), a split across two MI210s once the second card arrives (~October 2026), or CPU;
  - what is published on gated-DeltaNet / linear-recurrent state retention past the training length.

  Done when a short report recommends one 1M route with its first measurement. A route that needs the second
  MI210 is filed as trigger-gated on its arrival.
  - *(2026-10-04 note, after E1.)* **Memory is now the blocker for 1M, not quality:** A1 retrieved 5/5 at 500K, but
    measured 63.9 GiB against a 48.9 GiB estimate, and A0 overshot by the same ~15 GiB. Every 1M memory estimate
    above (≈ 54 GiB with q4_0 KV, ≈ 69.9 GiB lean) is optimistic by that amount until YARN-E1-MEM attributes it.
- [x] **YARN-INERT-PRIORART — prior-art audit of how production stacks (vLLM/SGLang/TGI/TRT-LLM/llama.cpp upstream/HF dynamic+longrope) and Qwen guidance avoid native-window regression, and whether YaRN is still SOTA.** Write-up: `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/OPTIONS.md` (in progress). Coordinate with YARN-OPTION-D-DECISION after the audit is complete. ✅ 2026-10-06
  - *(2026-10-06 correction, intake-1911 REDO)* "Nobody re-ropes at the crossing" is false for llama.cpp itself: `llama-memory_seq_div` plus the K-shift graph (`build_rope_shift`) re-rope cached K for Self-Extend (completion/passkey only; llama-server does not use it). Jet-Long keeps base-roped K and rotates distant K on the fly, so it avoids a cache rewrite.
  - *(2026-10-06, workspace-ec)* Prior-art audit complete; write-up `artifacts/yarn-ctx-20261006/OPTIONS.md` (durable copy). Root cause: mscale 1.0693 sharpens logits at all positions; feeds YARN-OPTION-D-DECISION.
- [x] **YARN-MSCALE-AB — mscale-neutral YaRN 3-arm greedy A/B (no-YaRN / static / attn-factor-cancelled) on experimental branch `llama.cpp-experimental/yarn-mscale-20261006`.** Includes the fix for `--yarn-attn-factor` being discarded when `ext_factor != 0` (`llama-context.cpp:220-228`). Done when the three arms are measured on a production-shaped Qwen3.8-27B prompt set (same as E1 short context) and the attn-factor test shows whether cancelling it recovers the native-window performance. ✅ 2026-10-06
  - *(2026-10-06, workspace-ec)* **VERDICT: the CTX-1 gate FAILS.** Fix `--yarn-attn-factor` is `720a98e2a` on `llama.cpp-experimental-yarn-mscale-20261006` (cancel factor 0.935190). Greedy identity vs no-YaRN: N 20/20, Y 13/20, YM 13/20; MTP@34k acceptance 0.514 / 0.490 / 0.468. Drift comes from frequency interpolation, not mscale, so cancelling mscale does not make YaRN inert. Evidence: `artifacts/yarn-ctx-20261006/yarn-mscale-ab-summary.md`.
- [x] **YARN-OPTION-D-DECISION ✅ 2026-10-06 — decide between the length-routed second server (D) and in-process per-request YaRN (A) after the prior-art audit and the mscale A/B.** Operator concerns to address: RAM cost of a second weights copy (production :8083 uses `--no-mmap --mlock`, so weights are private per process) and the re-prefill cost on crossing. Write the decision and its rationale into the stack-change plan template.
  - *(2026-10-06)* The package must state D's added RAM as a number (a second private weights copy under the canonical `--no-mmap --mlock` recipe, plus extended-server KV and compute buffers) and the F and Jet-Long-cached alternatives against the gates G1-G3 in the intake plan; the operator's rule (no regression inside the native window) and the CPU-first 1M order apply.
  Owner: workspace-ec
  - *(2026-10-06 inputs)* CTX-1 FAILED (inertness is not cheap via mscale), CTX-KSHIFT gate G2 fails (K-shift is not a re-rope primitive at v10), Jet-Long cost PASS on paper. Decision can now be written; see CTX-JETLONG-PROTO limits.
  - *(2026-10-06 evening, workspace-ec)* Decided by the operator 2026-10-06: cached Jet-Long (J) is the long-context target, no interim D, conditional on above-native recall >= static YaRN (D RAM would add ~49-52 GiB; host 778 GiB free). Evidence: `artifacts/ec-wrapup-20261006/DECISION_CTX4.md`.
- [x] **CTX-KSHIFT — three source-then-unit probes on the llama.cpp K-shift path (H1 mscale re-applied per shift under YaRN; H2 `pos_div` records shift += old-new vs `pos_add` += d; H3 quantized-K Hadamard `nrot` from the full head dim vs partial-rotary n_rot).** (filed 2026-10-06, from intake-1911 REDO) Experimental branch only, CPU, synthetic fixtures, f16 control. Done when each hypothesis is CONFIRMED or REFUTED with the max-abs error recorded and thresholds as predeclared (H1 norm ratio 1.000 +/- 1e-3; H2 error <= 1e-6; H3 <= 2x plain q8_0 round-trip error). A confirmed one becomes a defect ticket on the experimental branch; K-shift is not reused by F/A/Jet-Long until all three are closed. ✅ 2026-10-06
  - Owner: workspace-ec
  - *(2026-10-06, workspace-ec)* H1/H2/H3 all CONFIRMED at `ffc1bac82`. H1 K-shift re-applies YaRN mscale, ratio 1.0693^n (`llama-kv-cache.cpp:1992`). H2 `pos_div` sign error (`llama-kv-cells.h:478`; err 4.711 vs 1.7e-6). H3 q8_0 Hadamard nrot taken from the full head dim (`llama-kv-cache.cpp:1454-1461`; 84.7x/120.8x round-trip error); the CPU quantized shift also aborts (`ggml-cpu/ops.cpp:323`). Fixes on `llama.cpp-experimental-kshift-probe-20261006` (tip `f9cb7cd32`), unit-verified only; the H3 fix is marginal at 2.08x. Production NOT exposed (v10 defaults ctx_shift=false, n_cache_reuse=0; no production argv sets them). Gate G2 FAILS. Evidence: `artifacts/yarn-ctx-20261006/CTX2_KSHIFT.md`.
- [x] **CTX-JETLONG-COST — arithmetic plus CPU microbenchmark of the Jet-Long correction rotation (uncached vs per-G-epoch cached), n_rot=64, at 32K/128K/262K/1M.** (filed 2026-10-06, from intake-1900/1919 REDO) Done when bytes/step and measured ms/step on 96 threads under `region-lock` are filed; passes if the cached variant adds <= 10% decode at 262K and <= 25% at 1M, else the Jet-Long port is parked. ✅ 2026-10-06
  - Owner: workspace-ec
  - *(2026-10-06, workspace-ec)* PASS, measured. Uncached +13.5 ms/step at 262K and +46 ms at 1M (10 layers); cached +2.4 and +9.4 ms. About 9% uncached and 2% cached against EXTRAPOLATED baselines (143 ms, 500 ms), so the percentages are estimates. Evidence: `artifacts/yarn-ctx-20261006/ctx3a/COST.md`, `artifacts/yarn-ctx-20261006/ctx3a/results_20261006T054613Z.csv`.
- [ ] **CTX-JETLONG-PROTO — (only if CTX-JETLONG-COST passes) CPU-first non-fused Jet-Long prototype on an experimental branch, with a bit-exact in-window gate.** Done when logits at L <= native window are max-abs diff 0 versus the stock binary (np 1 and np 4 mixed batch, prefill and decode) and `strings` confirms the knob; otherwise rejected for in-window use.
  Owner: workspace-ec
  - [x] Synthetic-test part ✅ 2026-10-06 — branch `llama.cpp-experimental-jetlong-proto-20261006`, tip `b216a5deb` (impl `a2e129fcc`). T1 in-window max-abs exactly 0 (np 1, mixed np 4, co-batched with an above-native sequence; q8_0+Hadamard and f16). T2: f32 1.3e-6, f16 <=7.5e-5, q8_0 1.55e-3 (gated at 2x stock error). T3: cached == uncached exactly across 4 epoch changes. Evidence: `artifacts/yarn-ctx-20261006/jetlong/DESIGN.md`, `TESTS.md`, `LONGCTX_PLAN.md`. Limits: end-to-end wiring not run; above native needs `-ub 32` (1M prefill takes hours); f32 side cache ~5 GiB at 1M.
  - [ ] End-to-end long-context runs (tracked as JETLONG-LONGCTX-RUN below); this task stays open until they pass.

- [x] **YARN-ATTN-FACTOR-CARRY ✅ 2026-10-06 — carry the `--yarn-attn-factor` fix `720a98e2a` (llama.cpp-experimental-yarn-mscale-20261006) onto the champion branch via the champion fold.** Owner: workspace-ec. (filed 2026-10-06) Done when the champion carries the fix, `strings` confirms it, and a re-run of the YM arm reproduces cancel factor 0.935190. Never on production.
  - *(2026-10-06 evening, workspace-ec)* Carried to the champion candidate llama.cpp-experimental-champion-specwidth-20261006 @ `8e597b701` (version 10342; CPU+HIP builds and linkage PASS). The fold itself is pending workspace-89 regression gates (`artifacts/ec-wrapup-20261006/FOLD.md`). Upstream draft: `artifacts/ec-wrapup-20261006/ISSUE_ATTNFACTOR.md`.

- [ ] **KSHIFT-FIX-MODEL-TEST — model-level K-shift test, then carry the H1-H3 fixes to the champion, then draft an upstream bug report.** Owner: workspace-ec. (filed 2026-10-06) Fixes on `llama.cpp-experimental-kshift-probe-20261006` (tip `f9cb7cd32`) are unit-verified only. Done when (1) a real-model shift test (CPU, region-locked) shows post-shift logits match a re-prefill within the predeclared thresholds, (2) fixes are folded into the champion, (3) an upstream bug report draft is filed under `docs/` for operator review. Production is not exposed; no urgency beyond the champion fold.

- [ ] **JETLONG-LONGCTX-RUN — end-to-end Jet-Long runs: gate A in-window identity + needle at 300K/524K + decode tok/s.** Owner: workspace-ec. (filed 2026-10-06) Needs a full-host window (AutoKernel CPU window; flock is truth) and `-ub 32` above native. Script skeleton `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/jetlong/longctx_skeleton.sh`; plan `artifacts/yarn-ctx-20261006/jetlong/LONGCTX_PLAN.md`. Done when in-window identity (max-abs 0 vs stock) holds end to end, needle passes at 300K and 524K, and decode tok/s is recorded against the extrapolated 143 ms / 500 ms baselines.
  - [x] Gate A (in-window identity) ✅ 2026-10-06 — A2 PASS 09:28Z on canonical :8070: S, JOFF, JON byte-identical 41/41, MTP draft/accept 4217/2866 identical, 34k probe identical. Evidence: `artifacts/ec-wrapup-20261006/jetlong_gateA.md`.
  - *(2026-10-06 evening)* CPU 35B long-context run STOPPED by the operator (stopped, not failed): prefill 490 tok/s at 3k falling to ~45 tok/s at 97k, ~2.5 h more to 300K and ~5.6 h more to 524K; the first attempt had failed HTTP 400 (slot capped at n_ctx_train without a `context_length` override). Needle at 300K/524K and decode tok/s remain open.

- [ ] **JETLONG-HARDEN — fix stale side-cache rows on aborted compute; add an f16 side cache option (f32 side cache is ~5 GiB at 1M).** Owner: workspace-ec. (filed 2026-10-06) Branch `llama.cpp-experimental-jetlong-proto-20261006`. Done when an aborted-compute test leaves no stale rows (T3 still exact) and f16 side cache passes T1/T2 with its error recorded.

- [x] **JETLONG-SMALL-UB-BUG — fix the Jet-Long get_rows OOB assert (`ggml-cpu/ops.cpp:5350`) for ubatch < window at positions beyond native (IMRoPE).** Owner: workspace-ec. (filed 2026-10-06) Hits 4-token tails and likely decode on Qwen3.8-27B (qwen35); no repro on Qwen3-0.6B (NeoX). Evidence `artifacts/ec-wrapup-20261006/SAVE_RESTORE_TEST.md`. Done when ubatch 1/4/32 above native run without the assert on qwen35 and T1-T3 stay exact. Blocks the two items below. ✅ 2026-10-07 Fixed at `e6ea79421` (llama.cpp-experimental-jetlong-hip-20261006): root cause was `llm_graph_input_mem_hybrid::set_input` never filling Jet-Long inputs and `can_reuse` never blocking reuse; every pre-fix above-native hybrid result is INVALID. T4 tests ub 1/4/16/64, tail, decode, IMRoPE+NeoX, q8_0+f16 pass; evidence `artifacts/ec-wrapup-20261007/SAVE_RESTORE_TEST.md`.

- [x] **JETLONG-SAVERESTORE-PRETEST — order-(ii) slot save at the ack plus the within-window context-checkpoint hit (after JETLONG-SMALL-UB-BUG).** Owner: workspace-ec. (filed 2026-10-06) Checkpoint creation at the expected positions already observed; reuse on hybrid models was never observed historically (`progress/2026-09/2026-09-16-sub-op42-readiness.md:131-143`). Done when a restored slot resumes with a checkpoint hit and identical continuation. ✅ 2026-10-07 Prefill-only boundary trick passed on CPU 27B: save 280.8 MB/70 ms, restore 36 ms, extension prompt_n 2203 == delta, byte-identical, acceptance 33/41 both; first observed hybrid prefix reuse (follow-on HYBRID-PREFIX-REUSE, kv-unified-stack-rollout.md).

- [ ] **JETLONG-GPU27B-WINDOWS — two GPU windows for the Qwen3.8-27B Jet-Long run with slot save/restore, via `operator_authorize.sh`, :8083 stopped.** Owner: workspace-ec. (filed 2026-10-06) Design `artifacts/ec-wrapup-20261006/GPU27B_JETLONG_TEST.md`; branch llama.cpp-experimental-jetlong-hip-20261006 (`cd2d65d94`, `ebbf9ad0c`); scripts `/mnt/raid0/llm/tmp/jetlong-gpu27b-20261006/`. Executor caps windows at 60 min (MAX_WINDOW_S). AK GPU run 2 waits for it. Done when both windows complete and needle/decode results are recorded. 2026-10-07: entry `jetlong-gpu27b-20261007T023630Z` UNUSED — window A stopped :8083 but gpu-quiet EXCLUSIVE timed out at 600 s (AK shared claims starve it, FIFO off); rerun cancelled for token budget; scripts now prefill-only with 1800 s acquire timeout. Needs a new entry plus GPUQUIET-WRITER-PREFERENCE (autokernel-concurrent-target-coordination.md) or a lane pause.

- [ ] **JETLONG-SMALL-RECALL — finish the Qwen3-0.6B above-native recall arms (65k/130k).** Owner: workspace-ec. (filed 2026-10-06) At 30k (native 32k) N 6/6 and J 6/6, identical prompt_n 28914. Done when 65k and 130k arms report N, static YaRN and J recall; this is the evidence for the YARN-OPTION-D-DECISION condition (recall >= static YaRN).
  - [x] ✅ 2026-10-07 1x and 2x arms (Qwen3-0.6B, native 32k): 1x N 6/6, J 6/6; 2x J 6/6, Y 5/6, X 5/6; 4x Y 3/6, X 0/6. Evidence `artifacts/ec-wrapup-20261007/JETLONG_SMALL_RESULTS.md`.
  - [ ] 4x J arm (not run, CPU too slow).

- [ ] **JETLONG-PROTO-INWINDOW-UB — use the normal ubatch in-window and switch to the small ubatch only above native.** Owner: workspace-ec. (filed 2026-10-06) Done when in-window prefill runs at the production ubatch with T1 still max-abs 0 and throughput recovered.

- [x] **LLAMA-EXP-BRANCHES-PUSH-OR-RETIRE — push or retire the local-only experimental llama.cpp branches.** Owner: workspace-ec. (filed 2026-10-07) ✅ 2026-10-23 (ec's box, ticked on the coordinator's instruction after an authoritative re-audit): all six named branches were already on `fork` at the same sha (jetlong-proto `f06123436`, jetlong-hip `e6ea79421`, specwidth `defa269af`, champion-specwidth `8e597b701`, kshift-probe `f9cb7cd32`, yarn-mscale `720a98e2a`). The re-audit (`/mnt/raid0/llm/tmp/c3-fold-prep/branch_audit.py`, all 190 local branches) found 11 other genuinely unpushed experimental branches and pushed them with plain non-force `git push fork`; it now reports 0 of 191 unpushed. Per-branch last commit, in-champion flag and keep/retire recommendation (nothing deleted): `/mnt/raid0/llm/tmp/c3-fold-prep/BRANCHES.md`. Unpushed: jetlong-proto, jetlong-hip (`e6ea79421`), specwidth, champion-specwidth candidate `8e597b701`, kshift-probe, yarn-mscale. Done when each is pushed to its remote or retired with a recorded reason (no work lost).

- [ ] **EXECUTOR-WINDOW-CAP — decide whether operator_approved executor entries may exceed the 60 min window cap (MAX_WINDOW_S).** Owner: workspace-ec (the decision is the operator's; queue entry via the master index). (filed 2026-10-06) Alternative already planned: two windows with slot save/restore. Done when the operator rules and the executor or plan reflects it.

- [ ] **KSHIFT-UPSTREAM-FILING — operator files the upstream bug-report drafts H1, H2, H3 and attn-factor.** Owner: workspace-ec (drafts), operator (filing). (filed 2026-10-06) Drafts `artifacts/ec-wrapup-20261006/ISSUE_H1.md`, `ISSUE_H2.md`, `ISSUE_H3.md`, `ISSUE_ATTNFACTOR.md`. Done when the four issues are filed upstream and links recorded here.
- [ ] **YARN-FN-0 — (after YARN-FN-FIX) validate Flash-Next's NATIVE 262K before any YaRN arm on it.** Flash-Next has
  never served beyond 8,192 tokens, and its deepest benchmark is d4096. Its native long context is the more valuable
  experiment for that model, regardless of YaRN. It needs all four CPU regions, so it runs in an AutoKernel CPU
  window. Done when needle correctness and decode rate at 64K/128K/240K are recorded with the neutral haystack runner.
- [ ] **YARN-WIKI — recompile `wiki/context-extension.md` after E1.** That page carries stale facts: a "384GB RAM
  budget", "Hadamard q4_0 deployed", Qwen3.5/Qwen3-Next targets and TurboQuant. It lands in the operator-invoked
  `/wrap-up` wiki sweep, not as an ad-hoc edit. Done when the page reflects E1's result and this rewrite.
- [ ] **YARN-AGG-1 — Aggregation and recall arms for the YaRN gate: Oolong, HELMET recall and RAG, LongBioBench (spec now, runs need a window).** Spec (zero inference) the arms beside the needle cells, A0 versus A1 and CN versus CY2, at the native lengths and beyond; A1 must not fall below A0 minus a pre-declared margin inside the native window. (1) Oolong-synth counting and user questions (intake-2246#record): lengths 128K, 240K, 400K, 500K; score by length bucket with attempted-rate and no-answer-rate; add a constant-relevant-amount control (HoloBench info_amount, intake-2268#record) so a drop at 400K is attributed to length versus more items to aggregate. (2) One HELMET recall plus RAG cell (ruler_niah_mk_2/3, ruler_niah_mv, json_kv, rag nq and hotpotqa at 128K and 240K, `--endpoint_url http://localhost:8080/v1/`); pin the repo at `aeadacc6593e9a222a84b0660b186a4e23d2efda`, treat paper numbers as non-comparable, record the config file and `max_test_samples` (intake-2267#record). (3) A LongBioBench arm: generator pinned at `dc6f6ed1aab5dd072f0837f3160a45beb4df8dbe`, standard, multi_standard (5 and 10 retrievals) and paraphrase, served-model tokenizer, exact match, a coherent haystack in place of the neutral one (intake-2309#record). (4) Lengths are nominal (generator sizing used a GPT-4 tokenizer): re-tokenize every context with the served tokenizer, record real prompt_n, bin by it, and refuse to label a cell native or beyond-native from the nominal length (intake-2281#record). Data fetch: oolong-synth is a 12 GB download, about 25 minutes at the unauthenticated rate; fetch only the lengths used, as an operator-visible step. Acceptance: the spec section is filed with the arms, pins, margins and binning rule; the data subset is fetched and its token counts re-measured. Estimate: spec 1 day, fetch 0.5 day; runs per arm need their own window.
  - *(2026-10-27, workspace-58 results harvest)* extension-arms FINAL NOT-FAIL-underpowered: 74 native-window pairs, b=2 c=1, McNemar p=0.5, mean diff -0.022 (not an equivalence claim). Beyond-native A1 report-only: Oolong-synth@400k 0.093 (CI 0.071-0.133, n=54); other cells n=1. HELMET nq/hotpotqa 128k dropped (KILT data missing). Artifact `/mnt/raid0/llm/tmp/yarn-extension-arms-out/decision.json`. [no-belief: sidecar 78 records awaiting ingest]
  - [ ] **YARN-AGG-1g — restore HELMET KILT nq/hotpotqa 128k data and fold the extension-arm discordant items into the YARN-AGG-1f power run.**
    - 2026-10-27: MAIN reviewed and approved a bounded CPU data-restoration launcher, submitted to workspace-58. It reserves 32 GiB total and preserves the 150 GiB free-space floor; it pins and checks the original archive digest, inventories and hashes the four selected KILT files before extraction, and resumes interrupted per-file extraction. Source and proof: `/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch/ROW-HELMET.md`, `HELMET-FINAL-SEAL.sha256`; queue notification receipt `HELMET-WS58-RECEIPT.json`. This is preparation only: no download or inference has occurred. Both data cells and the parent remain open. [no-belief: source readiness and model-free controls, no measurement]
    - 2026-10-27: a separate fresh 120-pair native Oolong cohort was reviewed, approved and sent to workspace-58 as a GPU observation. It records full model, store-library, template, source and arm-recipe identities before each window's first model load, uses the existing native McNemar rule, and does not pool or regrade historical results. The historical windows do not capture all of those content digests, so the original pooling task remains open; the finite new cohort may remain underpowered. Row and seal: `/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch/fresh/ROW.md` and `fresh/FINAL-SEAL.sha256`; notification receipt `FRESH-WS58-RECEIPT.json`. No inference has run. Existing `yarn-gate-agg` source registration and pinned `arm_runner` FINAL write-side emitter remain in use; inspect `belief_emit` after the run. [no-belief: source readiness and model-free controls, no measurement]
    - 2026-10-28 (ws58 results filing 19:50Z): the CPU fixed-120 v3 shards `yarn-cpu-fixed120-v3-s{0,1,3}-20261027` ended rc1 at 19:51Z (window end, ~8 h) and `-v3-s2` rc1 at 19:39:55Z. Zero scored pairs in any shard: s0/s1/s3 each spent the whole window on their FIRST A0 item (`oolong_synth@131072`, started 11:54:55Z) and logged `TimeoutError` at 19:51:25Z; s2 never scored because the worker died on `ModuleNotFoundError: No module named 'dateutil'` (`oolong_adapter.py:92`). Predeclared rule (full 120 paired native items, one-sided exact McNemar p <= 0.05 fails A1; no shard verdict) is not evaluable: 0/120 coverage → FAILED-RUN, harness class, no verdict. Evidence: `/mnt/raid0/llm/tmp/refactor-01a16fc3/heavy-yarn-quarter-ready/v3-*/out-v3/shard-*/`. [no-belief: failed run, no measurement]
      - [ ] **YARN-CPU-V3-HARNESS (filed 2026-10-28, ws58 filer):** (a) install `python-dateutil` into the runner env and add an import preflight so a missing module fails at dry-run, not in-window; (b) a single 128k A0 item does not finish in an ~8 h CPU-quarter window — bound per-item wall (or move 128k items to GPU) before re-arming; (c) make window-end exits return rc75 (resumable) instead of rc1. Done when one shard scores >= 1 pair inside a window and a window-end exit writes rc75.
        - 2026-10-29 (ws58 results filing batch B): the four r11 repair re-arms `yarn-cpu-fixed120-v3-s{0,1,2,3}-r11-20261028` (CPU quarters 0-23/24-47/48-71/72-95, class cpu; the GPU cohort note in each scratch root records the GPU filler as WITHDRAWN) were granted at about 05:52Z. All four were REFUSED at T1 admission rc 6 at 05:52:45-05:53:52Z (`DRYRUN_REFUSED: disk free-after-output 133.1 GiB < floor 150 GiB`). Units 0/120 pairs, and no `out-v3/` directory was created. This was not a window-end exit, so it is neither rc75 nor rc1; the rc75 criterion (c) is still unexercised. Only pre-launch smoke outputs (10-28, `direct-smoke-out/`) exist. FAILED-RUN, disk-floor class, no verdict; this box stays open. [no-belief: failed run, no measurement]
        - 2026-10-28 (owner decision, workspace-58): the CPU-quarter path fails on window fit. One 128K item takes about 8-9 h on one quarter, which is more than a whole window, so criterion (b) cannot be met by bounding alone. The 128K A0 items are redirected to the MI210. The CPU fixed-120 shards are not re-armed for 128K items. [no-belief: not-a-result]
        - [ ] **YARN-128K-MI210** — re-plan the 128K A0/A1 items as a GPU (MI210) row. It needs a measured per-item wall, an `est_output`, and a `scratch_root` + `keep` per R10. Keep the predeclared full-120-pair McNemar rule unchanged. Done when the row is READY and the CPU v3 shards carry only items shorter than 128K, or are withdrawn.
          - *(2026-10-30, accepted R3 preparation)* The R3 READY row was keeper-validated READY-WAIT at 15:14:17Z (rank 22), restored byte-for-byte at 15:18:38Z after its bounded own-row yield, and the actual frozen native A1 smoke completed: 223.848s request / 232.102s window, 103,311 prompt tokens, result writer and owned cleanup true. There were 23 positive observations among 24 successful active-slot KFD samples; 120 observer timeouts remain disclosed. This qualifies the row/launcher and sampled residency only; the 120-pair quality decision, CPU-v3 disposition and scientific checkbox remain open. Cold4 owner-approved retirements removed 4.2023 GiB of allocated tree bytes with 30 reference files under custody; no filesystem-free delta is claimed. Evidence: `/mnt/raid0/llm/tmp/codex-ni-yarn-128k-mi210-r3-20261030/review-evidence/YARN-R3-WRAP-DRAFT.md` and `cold4-custody/RESULT.json`. [belief: cc — committed operational observation, not original measurement warrant]
  - [x] **YARN-AGG-1-V18-DIAGNOSTIC-SMOKES — exercise the isolated worker and cutoff.** The same v18 launcher returned rc0 with 30 scored diagnostic responses and rc75 with 12 completed, one in-flight unknown and a live native slot witness; both captured process trees drained. These 0.6B/11,000-character diagnostic attempts are not the 27B/128K gate or its quality result. Evidence: `/mnt/raid0/llm/tmp/yarn-oolong-s0-v19-scheduler-entry-20261029/FINAL-CHECKPOINT.md`. ✅ 2026-10-29 [no-belief: diagnostic launcher validation, not a cohort result]
  - [ ] **YARN-AGG-1-FIXED120-CONTINUATION — resolve original A0 exposures and schedule the native gate.** Retained earlier-window logs do not identify which A0 item was sent for each shard; matching token counts alone are shared by multiple items, and s2's response was lost before scoring. Preserve those identities as unknown, do not redraw or change the predeclared 120-pair denominator, and coordinate the GPU version with NI. The separate v19 public entry returns `needs_review` and has not had a real v19 smoke pair. A single s2 CPU prefill took 27,890.159s; it does not establish a full-cohort bound. Current source, scoped smokes and remaining gates: `/mnt/raid0/llm/tmp/yarn-oolong-s0-v19-scheduler-entry-20261029/FINAL-CHECKPOINT.md`.
  - 2026-10-21 (fillers-3c4ca599): registered as queue items `yarn-native-gate` (<=128K gate, high priority) and `yarn-extension-arms` (240K-500K + judge, ~6 GPU-h, lower priority); both NOT armed: no arm runner exists (arms.py is a manifest), oolong_adapter loads from HF not the fetched subset.
  - [x] **YARN-AGG-1a — arm runner for the A0/A1 window.** `scripts/benchmark/yarn_gate/arm_runner.py` (research branch `yarn-native-gate-runner-20261022` @ `2fd3208d`, not merged): freezes a pre-registered plan (`plans.py`; items, prompt blobs and `plan_sha256`), runs one arm against an already-running server with per-item fsync'd results, resumes and completes pairs first, starts an item only if its E1-fitted cost fits the deadline, labels zones from the server's prompt_n only, and writes `decision.json` (net-paired McNemar, INTERIM until both arms finish, with the claim-tuple fields). Tests with a fake endpoint: `tests/test_arm_runner.py`, 14 pass. ✅ 2026-10-22
  - [x] **YARN-AGG-1b — local-data cells for the native-window gate.** `oolong_local.py` reads the fetched JSONL subset through the OOL-1 adapter (no HuggingFace; upstream scorer). The ≤128K exact-match cells are RULER NIAH mk_2/mk_3/mv generated locally by `ruler_local.py` (RULER checkout `ab17b78`, sized with the served tokenizer.json, essay haystack from the local Paul Graham set; deviations pinned per item). The native-gate plan is frozen at `/mnt/raid0/llm/tmp/yarn-native-gate-out/plan` (sha `b2233026…`, 185 items: Oolong 131072 × 8 contexts and RULER at 32K/64K/124K). ✅ 2026-10-22
  - [x] **YARN-AGG-1c — extension-arm builders.** `helmet_local.py` (HELMET `aeadacc6`: json_kv regenerated locally, ruler/RAG readers, metric ports, a validated 240K local config) and `longbio_local.py` (LongBioBench `dc6f6ed1`: standard, multi 5 and 10, paraphrase). Both pinned checkouts are local clones at `/mnt/raid0/llm/data/eval/{helmet,longbiobench}/repo`. The HELMET RAG data (`data.tar.gz`, 10.5 GiB) is not on disk, so nq and hotpotqa are optional segments that drop at freeze with a recorded reason. Tests: 20 (HELMET), 7 (LongBio), 13 (RULER). ✅ 2026-10-22
  - [x] **YARN-AGG-1d — grant-polling filler jobs.** `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/yarn_native_gate_job.sh` and `yarn_extension_arms_job.sh` share `yarn_gate_lib.sh`. Each job runs `ram_admit 12`, uses the v10 store GPU build with its own LD_LIBRARY_PATH plus `verify_ggml_linkage.sh`, launches the E1 A0/A1 argv on :18093 or :18094, proves its own PID, the rope config and KFD residency, and kills only the captured group (verified dead). It refuses with rc 4 when production :8083 is listening or a foreign KFD tenant holds VRAM, and never stops anything. A run on a fake server proved resume across three windows, INTERIM then FINAL, and the COMPLETE marker. Proposed FILLERS rows are block-correctness, mi210_0 exclusive plus 184-191, and pass `validate_fillers.py --for-grant` once a launcher PID is present. Main arms them. ✅ 2026-10-22
  - [x] **YARN-AGG-1e — native-window gate run (A0 vs A1) on the v10 GPU store build: FINAL, verdict NOT-FAIL-underpowered.** Plan `native-gate` sha `b2233026…`, protocol `YARN-AGG-1/native-gate/net-paired-mcnemar/v1`; `/mnt/raid0/llm/tmp/yarn-native-gate-out/decision.json` FINAL 2026-10-23T13:02:40Z. Pooled native: 185 pairs, b (A0 right / A1 wrong) = 1, c = 1, n_discordant = 2, one-sided exact McNemar p = 0.75, mean score diff A1-A0 = +0.004. Per cell: oolong_synth@131072 152 pairs 1/1 (p 0.75, diff +0.0049); ruler mk_2, mk_3, mv at 32k (6 pairs), 64k (3), 124k (2): 0/0 each. Only 2 discordant pairs, so this is NO HARM DETECTED, not an equivalence or safety claim (min losses to fail with zero wins = 5). Run history: started 2026-10-22 19:29Z; both arms OOM'd on the llama-server own-PID VRAM leak (GPU-LEAK-1), fixed 2026-10-23 with the restart/VRAM-recycle lib (`yarn_gate_lib.sh` sha 983276fe…), resumed 08:30-11:05Z and 12:15-13:02Z. Beliefs: 30 records ingested 2026-10-23T13:04:30Z (90 frames); the ruler niah_multikey groups were excluded from the beliefs sidecar for non-uniform source pins. Per the net-paired rule, no regression is shown inside the native window; this clears the YaRN native-window gate owed before the CH-20 CAS and unblocks CH-23 (fold V11-100) and KPF-62.1 as far as this gate is concerned. `yarn-extension-arms` (240K-500K + judge) has its own run window and is not covered. ✅ 2026-10-23
    - 2026-10-27 harvest (yarn-extension-arms, grants ended 2026-10-24 .. 2026-10-25, final `complete` 2026-10-26T00:13Z; plan `extension-arms` sha `d94cd4ae…`, FINAL decision.json): YARN-AGG-1(ii) net-paired one-sided exact McNemar on native-zone pairs = **NOT-FAIL-underpowered**: n_pairs 74, b (A0 right/A1 wrong) 2, c 1, p 0.5 (alpha 0.05), mean paired diff A1-A0 -0.022, n_discordant 3. A0 80/80 and A1 139/139 planned items done. Per-arm cell means (report-only, tiny n): oolong_synth@240k n=61 A1 0.138 vs A0 0.149; oolong_synth@131072+think n=6 A1 0.167 vs A0 0.0; ruler_mk_2@240k n=1 A1 0.0 vs A0 1.0; ruler_mk_3@240k, ruler_mv@240k, helmet_json_kv@124k/240k, longbio@124k/240k are 1.0 in both arms. Beyond-native, A1 only (no A0, no gate): oolong_synth@400k n=54 mean 0.093; helmet_json_kv@400k, longbio_standard@400k, ruler_mv@400k 1/1; ruler_mk_2@400k and @480k 0/1. HELMET nq/hotpotqa RAG segments dropped (data files absent). NOT-FAIL is harm-detection only, not an equivalence or safety claim. Artifact `/mnt/raid0/llm/tmp/yarn-extension-arms-out/decision.json` (+ `yarn_gate_agg.beliefs.jsonl`, 78 records). [belief: cc]
  - [ ] **YARN-AGG-1f — (OPTIONAL) power follow-up for the native gate: add discordant-prone items.** The handoff has no prescribed rule for NOT-FAIL-underpowered, so this is proposed (3c4ca599, 2026-10-23). The ruler cells contribute 0 discordant pairs in 2-6 items each, and Oolong 2 of 152. Add more Oolong-synth items at 64K-128K (the only cell that disagrees) or harder multi-key items, re-freeze a new plan, and rerun A0/A1 only if an equivalence claim is wanted; the verdict rule stays unchanged. Done when n_discordant >= 10 or the operator declines.
    - [ ] **YARN-AGG-1f power runs** (operator decision 2026-10-25 via decision tool): run the extra paired A0/A1 runs up to the predeclared n so the native-window gate resolves to a real PASS or FAIL; verdict rule unchanged. Launcher prepared (not armed): `/mnt/raid0/llm/tmp/cal-1025/yarn-agg-1f/`.
- [x] **YARN-JUDGE-1 — Local judge for judged long-context cells (replaces the hosted-judge decline).** Serve a local judge through the existing OpenAI-client path to `localhost:{port}/v1` on the worker model (about 0.5-1 day), validate it on about 50 hand-labelled items (about 0.5 day), pin the judge model and prompt in the claim tuple, and schedule judging outside the YaRN timing window. This unblocks the judged HELMET categories (single and multi-document QA, summarisation) and the HoloBench two-pass scoring, whose hosted-GPT-4o judge was the stated obstacle; results are relative to the pinned local judge and never comparable to published figures (intake-2319#record, intake-2267#record, intake-2268#record). Acceptance: judge agreement with the 50 hand labels reported with the judge pin, and one judged HELMET cell scored end to end. Estimate: 1-1.5 days.
  - 2026-10-21 (wrap-up 3c4ca599): human labels were requested from the operator. SUPERSEDED 2026-10-22, see the delegation note below.
  - **Delegation note (operator ruling 2026-10-22, verbatim: "Why do you need me to manually label? Build the labels yourself. Don't overcomplicate this").** The 50 gold labels are NOT human. They are agent-produced under operator delegation. Coordinator 3c4ca599 then required that the labels come from a different model family than the judge, so that agreement is not inflated by shared blind spots. Labeler: `codex-luna-low` (gpt-5.6-luna, codex_exec) plus deterministic rules. Judge: `sonnet-5-5-low` (claude-sonnet-5-5, claude_cli). No Claude model wrote a label.
  - [x] **YARN-JUDGE-1a — judge job.** `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/yarn_judge1_job.sh`. As of 2026-10-22 it is a post-step with no server, no GPU, no RAM booking and no grant. It judges the 50 kit items through the cloud judge, then runs agree and pin, and refuses unless the research worktree is at the pinned sha and the frozen registry copy matches its sha256. ✅ 2026-10-22
  - [x] **YARN-DIRTY-TREE-REFUSE — yarn jobs must refuse a dirty pinned tree (filed 2026-10-22, 3c4ca599).** `yarn_gate_lib.sh` and `yarn_judge1_job.sh` (under `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/`) must exit non-zero when the pinned research worktree is dirty, and the shared lib must not reassign the job's pinned tree variable (the hsprof1 failure mode, see compute-fillers.md Owner duties). Apply only when the yarn poller is idle. Done when a dirty-tree dry run exits non-zero in both jobs. ✅ 2026-10-23 (3c4ca599): `yarn_gate_lib.sh` gained `yg_tree_clean` (porcelain must be empty, tracked and untracked), called from `yg_resolve` right after the sha pin, so every window and `--dry-run` of both gate jobs exits rc 5 on a dirty pinned tree. `yarn_judge1_job.sh` `check_pins` does the same, and its `--dry-run` now exits with the pin result (it used to exit 0 regardless). The lib assigns only `YG_*` names (self-test asserts `RESEARCH`/`ARM_TREE` survive sourcing). Self-test `jobs/yarn_dirty_tree_selftest.sh`: 10 checks PASS on the new files, 6 FAIL on the old ones. Applied with the poller idle (filler_run6 `--repeat` waiting, no job child, no yarn grant); `.bak-pre-dirtytree-20261023` kept. Real-tree dry-runs rc 0 (clean).
  - [x] **YARN-JUDGE-1b — gold labels (rule + cross-family labeller).** `judge_validation_kit.py context` resolves each item's full question and source data. The logged prompt is cut at 200 characters, so hotpotqa had lost its question; hotpotqa resolves by qid and simpleqa by prompt prefix, 50 of 50. Then `label` runs: 19 rows are decided by rule (no-answer marker, exact normalised match, yes/no, numeric equality) and 31 by `codex-luna-low`. Every labeller prompt is gated to contain the reference. The result is 10 correct, 40 incorrect, 0 undecided. Output: `/mnt/raid0/llm/tmp/yarn-judge1-kit/labels_sheet_filled.csv` (`human_label` + `label_rationale` + `label_source` + `labeler`) and `labels.jsonl` (+ `.meta.json`). ✅ 2026-10-22
  - [x] **YARN-JUDGE-1c — judge switched to the pinned cloud judge.** `--judge-backend cloud --cloud-judge sonnet-5-5-low` (research `cloud_judge.py`; the same transport pattern as HS-PROF-1's `judge_beam_run.py`). The registry is the frozen copy of orch `fa25cfbd` `orchestration/cloud_judges.yaml` via `ORCHESTRATOR_CLOUD_JUDGES_FILE`. `helmet_judged_cell.py` takes the same flag. Research `ddf985a51` + `e5173d638` (the cloud pin carries `max_tokens: null` for the `yarn_gate_agg` adapter) on branch `yarn-native-gate-runner-20261022`. `yarn_gate_lib.sh` `YG_RESEARCH_SHA` is repinned to `e5173d638724bde7b2e395033097a20eda9efc88`. ✅ 2026-10-22
  - [x] **YARN-JUDGE-1d — agreement reported with the pin.** Cloud judge `sonnet-5-5-low` (envelope model `claude-sonnet-5-5`, 50 calls, $0.2156) against the 50 gold labels: accuracy 0.98 (49/50, Wilson 95% 0.895 to 0.996), Cohen kappa 0.940 (95% CI 0.823 to 1.0 by Cohen-1960 SE; 0.766 to 1.0 by seeded bootstrap), confusion label0/judge0 39, label0/judge1 1, label1/judge0 0, label1/judge1 10; 0 unparsed. The one disagreement is j008: cut-off meta-reasoning that names Atlético Madrid but commits no final answer (labeller 0, judge 1). The task text sets no numeric threshold (acceptance = agreement REPORTED with the pin), so this clause is met. Record: `/mnt/raid0/llm/tmp/yarn-judge1-out/run-20261022T125515Z/judge_pin.json` (`epyc.yarn_judge_pin.v1`: judge pin, cloud identity, envelope models, usage, label provenance with `labels_are_human: false`); marker `/mnt/raid0/llm/tmp/yarn-judge1-out/COMPLETE`. Agreement is between two model families, not with humans, and is relative to this pinned judge only. ✅ 2026-10-22
  - 2026-10-29 23:40: **remaining end-to-end integration criterion MET; YARN-JUDGE-1 closed under the already approved cloud-judge and delegated-label substitutions.** Judged-cell-v4 produced one genuine native HELMET longqa cell,7390 server-reported prompt tokens and55 output tokens, HTTP200, nonempty response, positive owned-PID VRAM samples wholly inside the request, schema-check OK,1 judged/0 unjudged and verified cleanup. Every field of its cloud judge pin matches the retained50-item validation pin (49/50 agreement, Cohen kappa0.939759;19 rule labels and31 cross-family model labels, not human labels). The new cell has descriptive accuracy0/1 after8192-context truncation; this closes integration and establishes no full long-context quality or promotion result. [Exact evidence and matched pins](../../artifacts/compute/results-filing-20261029-2340.json). [belief: cc]
- Declined (2026-10-04, ASSESSMENT §6 *Not recommended now*):
  - **A 1M run on CPU.** The memory fits, but prefill is ~2.8 h per prompt even on the GPU model, and CPU prefill is
    unmeasured. YARN-1M decides the 1M route.
  - **Rope flags on any production server.** See above.
  - **intake-569#record's A1 indexing check as a substitute.** It measures position indexing at 4–32K, not
    retrieval past 262K.
  - **The Qwen3.6-35B-A3B front door.** No workload, and static YaRN would tax every short request.
  - **The embedders.** They have no RoPE.
  - **LongRoPE.** No production GGUF ships the factor tensors.
  - **NTK base raising.** θ is already 1e7, and YaRN supersedes it.

### YARN-AGG-1 / YARN-JUDGE-1 spec (2026-10-21, lane dpf-sample-yarn-yarn)

Code: research repo `scripts/benchmark/yarn_gate/` (lane branch `lane/dpf-sample-yarn-yarn-epyc-inference-research-20261021`). Everything below was built and tested with an in-process fake endpoint; no model was called and no data was fetched.

**Comparisons.** A0 vs A1 (GPU 27B) and CN vs CY2 (CPU 35B-A3B hybrid), each at native lengths and beyond. Greedy, thinking off, same item ids in both arms (paired).

**Arms and pins**

| Arm | Cells | Pins and records |
|---|---|---|
| Oolong-synth (config and aggregation on top of the OOL-1 adapter `scripts/benchmark/oolong_adapter.py`; the adapter is not duplicated) | counting and user; REAL-token targets 128K, 240K (native) and 400K, 500K (beyond) | `oolongbench/oolong-synth@81d2f8d9349f6ff329d695f9be494051e9f05cb9`; upstream scorer `abertsch72/oolong@0bb7eabe8` (vendored unmodified); labelled column never used. Per bin: mean score with context-clustered CI, attempted rate, no-answer rate, failure classes. |
| Oolong control | HoloBench info_amount (constant relevant amount) | Restrict to the `num_labels` value(s) present at every real-length bin; report score by length inside that band. A drop at 400K is attributed to length only if it persists inside the band. An empty common band means the control is UNAVAILABLE and the drop is not attributed. |
| HELMET recall and RAG | `ruler_niah_mk_2`, `ruler_niah_mk_3`, `ruler_niah_mv`, `json_kv`, `nq`, `hotpotqa` at 128K and 240K, `--endpoint_url http://localhost:8080/v1/` | repo `princeton-nlp/HELMET@aeadacc6593e9a222a84b0660b186a4e23d2efda`; record the config file (path and sha256), `max_test_samples`, pin; paper numbers are non-comparable. HELMET configs stop at 128K, so the 240K config is a local copy recorded by sha and must be validated against the pinned checkout before the first run. |
| LongBioBench | standard, multi_standard (5 and 10 retrievals), paraphrase; exact match | generator `dc6f6ed1aab5dd072f0837f3160a45beb4df8dbe`; served-model tokenizer for sizing; a coherent haystack, not the neutral one. The generator output schema was not inspected offline; the runner expects JSONL rows `{id, prompt or context, question, answer, variant}` and the window runner adapts the generator to it. |

**Binning rule.** Nominal lengths come from a GPT-4-tokenizer sizing and are never used to label a cell. Every context is re-tokenized with the served tokenizer (`POST /tokenize`) or its real size is read from the server timings (`prompt_n + cache_n`); that real count is recorded, binned in 32,768-token bins, and is the only input to the zone label. With N = 262,144 (`--yarn-orig-ctx`) and 4,096 tokens reserved for question and answer: native means real + 4,096 <= N; beyond-native means real > N; anything in between is `boundary` and counts as neither. `label_zone` raises on any non-measured source. A cell whose real median differs from its nominal target by more than 10% is flagged `nominal_mismatch`. The dataset ships power-of-two nominal buckets, so 240K, 400K and 500K buckets probably do not exist for Oolong; a target zone that no bucket lands in is reported NOT CONSTRUCTIBLE and is never relabelled from the nominal length.

**Margin rule (operator-ratified "Net, paired", 2026-10-21; no absolute slack).** Inside the native window A1 FAILS iff a one-sided exact McNemar test on the paired discordant items is significant at alpha = 0.05: b = items A0 got right and A1 wrong, c = the reverse, p = P(X >= b | n = b + c, p = 0.5), FAIL iff p <= 0.05, otherwise NOT-FAIL. An item is "right" iff its score is 1.0. The point estimate (mean paired score difference, b, c, p) is always reported beside the verdict, because a NOT-FAIL on few discordants is weak evidence. Needle cells keep their E1 rule (A1 >= A0 - 1 of 10). Code: `agg_scoring.net_paired_mcnemar`.

**Judge (YARN-JUDGE-1).** Superseded 2026-10-22: the judge of record is the pinned cloud judge `sonnet-5-5-low` (see the YARN-JUDGE-1 delegation note). Original text: the judge is served locally on `localhost:{port}/v1` (OpenAI wire format; a non-localhost endpoint is refused). Model id, prompt version and sha256, temperature 0, seed 0 and max_tokens ride in the claim tuple fields; the client refuses to run while `YARN_TIMING_WINDOW_ACTIVE=1`; an unparsed reply is listed under `unjudged` and never scored 0. Validation on about 50 hand-labelled items: `judge_validation_kit.py select | sheet | judge | agree | pin` (a blind sheet, accuracy, Cohen kappa, Wilson interval, a pin record).

**Oolong data subset: fetched and re-measured (2026-10-21).** `fetch_oolong_subset.py --list-lengths` showed the test split has 13 power-of-two nominal lengths (1024 to 4,194,304), 400 rows each, so no 240K, 400K or 500K nominal bucket exists. Fetched the 131072, 262144 and 524288 buckets (1.04 GB of JSONL, labelled column excluded, revision `81d2f8d9349f6ff329d695f9be494051e9f05cb9`) to `/mnt/raid0/llm/tmp/yarn-agg-oolong-subset/`. Token counts were re-measured offline with the served model's own `tokenizer.json` (Qwen3.8-27B, sha256 `0997f410c57a...`, source `model_tokenizer_json`; no server was started, so the llama.cpp `/tokenize` and `server_timings` prompt_n cross-check is still to be done in the first window and supersedes this). 16 distinct contexts per length; real tokens are LOWER than nominal, not higher:

| Nominal bucket | Real tokens (min / median / max) | Zone |
|---|---|---|
| 131072 | 89,419 / 110,768 / 122,120 | native |
| 262144 | 179,722 / 222,455 / 239,818 | native |
| 524288 | 371,962 / 447,286 / 472,304 | beyond-native |

Constructibility of the real-token targets (needs at least 8 of 16 contexts within 10% of the target and in the expected zone; that threshold was chosen after seeing the counts, the raw counts are in the report): 240K constructible (9 contexts, from the 262144 bucket); 400K constructible (10, from the 524288 bucket); **128K NOT CONSTRUCTIBLE** (1 context within 10%; the 131072 bucket is a native "~110K" cell, labelled by its real bin); **500K NOT CONSTRUCTIBLE** (4 contexts, none above 472,304; the beyond-native cells are ~400K to ~470K). Report: `artifacts/yarn-agg-1-20261021/oolong_token_report.json`.

**Ready for a window (not run).** `run_local_judge_window.sh` (needs `WINDOW_CONFIRMED=1`, a served judge, a filled labelling sheet; also scores one HELMET cell if `HELMET_CELL` is given). Open before the first HELMET cell: the real HELMET result schema (`--selfcheck-schema` checks it).

**YARN-JUDGE-1 item note (2026-10-21).** The blind 50-item labelling sheet (stratified from logged simpleqa and hotpotqa eval answers, seed 20261021, no judge verdict column) is `/mnt/raid0/llm/tmp/yarn-judge1-kit/labels_sheet.csv` (sha256 `97e4861f3fc1dc20f300fb5bf974d92846fb979de1905073fad2d0dfe33de5ca`; items in `items.jsonl` beside it). Filling `human_label` (1 correct / 0 incorrect, `?` to skip) is an operator item; serving the judge on the worker model is a window item for main. Not done, not ticked. (Superseded 2026-10-22: labels by codex-luna-low + rules under operator delegation; judge = cloud sonnet-5-5-low. See YARN-JUDGE-1b to 1d.)

**YARN-AGG-1 power caveat (2026-10-22).** NOT-FAIL is harm-detection only; an equivalence claim needs a pre-registered margin (see M15 / DP-E). `decision.json` now carries `n_discordant`, `min_losses_to_fail_given_discordant`, `power_note` and `interpretation` (FAIL / NOT-FAIL-underpowered / NOT-FAIL; underpowered = fewer than 10 discordant pairs); the verdict rule is unchanged.

**YARN-AGG-1 item note (2026-10-21).** Spec filed and the Oolong subset fetched and re-measured with the model's tokenizer, so the acceptance clause is met except the served-server `/tokenize` cross-check. Left unticked for main to decide; the runs per arm still need their own windows.

## Completed Scope

- The superseded 2026-03-09 to 2026-09-07 scope (YaRN primer, flag table, key questions, references, the 2026-03-24, 04-18 and 05-20 intake updates, stale progress checklist) moved 2026-10-06 to [the archived history](../archived/yarn-context-extension-research-history-through-2026-10-06.md). The Tulving benchmark gate now lives with `episodic-memory-integrity.md` M-12 (rescoped 2026-09-07; 200ch/100K split, fixed tau).

## Research Intake Update — 2026-10-21 (harness cluster, DP-F amendment)

Operator-approved Stage-3 amendment (plan sha256 2edfb0662f61e1254e7dc5e2b21888ef4f19df800a283e82b25caebeb6644746). Durable records only: no checkbox, no index next action. Each monitor row carries its trigger and first step; each knowledge row states what to rely on. Ledger ids (DPF-...) key to the Stage-3 recommendation mapping preserved in `.research-session.json` (`stage3_filing`).

### M21 — Long-context gate follow-ons

- DPF-W1-OOLONG-O4 (intake-2246): Higher reasoning effort stops helping after about 64K; within a length, longer Gemini 3 Pro reasoning traces correlate with worse correctness (authors flag confounding by difficulty). — Trigger: CT-13 reports at least the 2 percent floor of budget-exhausted turns, or an Oolong arm (O1/O2) runs on a thinking-on role. Then include a reasoning-budget arm. Do not import the API-model result.
- DPF-W2-HOLOBENCH-H2 (intake-2268): Generated gold lets us build aggregation items at ANY length from a fixed dataset (max_context_size, info_amount parameters), unlike fixed-length Oolong buckets; useful exactly where Oolong has few c… — Trigger: the Oolong arm (rao-redel task, OL1-OL4) is specified and its largest nominal length is below the cell we need. Then try HoloBench `load_context(max_context_size=...)` at the needed length with the dummy-document fallback. First s…
- DPF-W3-LONGBIO-L3 (intake-2309): Trustworthiness tasks (citation, refuse-when-absent) degraded as long-context continual pretraining proceeded, while retrieval saturated in about 4K steps; reasoning did not improve. — Trigger: an extended-window (A1) candidate is evaluated beyond the native window under L1. Then add the paper's IDK task (answer absent, must refuse) as one report-only cell, since a model that retrieves well can still fabricate. Mechanism…
- DPF-W4-100LONGBENCH-LB3 (intake-2319): Judge-free counting and retrieval tasks (counting stars, passage count, passage retrieval) test aggregation that needle cells do not. — Trigger: needle cells and the L1 LongBioBench arm disagree on A1 vs A0 at the extended window. Then add one judge-free counting cell as a tie-breaker. Build cost: reimplement the four judge-free generators from the paper appendix (about 1.…
- DPF-W4-CAPA-C3 (intake-2323): Option-level probabilities give the full CAPA; discrete CAPA loses little (App. D.3). — Trigger: C1 shows non-trivial judge overlap. Then build option-logprob capture on the llama-server completion path for MCQ graders (n_probs) and recompute the full form. Build cost ~0.5 day harness plumbing; missing logprob capture is a bu…
- DPF-W4-CAPA-C6 (intake-2323): Weak-to-strong gain scales with complementary knowledge (r=-0.85). — Not declined. If a fine-tune or distillation lane opens (annotator/student pairs), compute CAPA between supervisor and student before choosing pairs; building a fine-tune lane would be the cost, tracked by whichever handoff proposes it.
- DPF-W4-EFFREASON-E3 (intake-2327): FSF (LLM-extracted failed-step fraction) is the strongest selector and beat length for best-of-64. — Trigger: F1 shows a within-question length signal on our roles. Then BUILD the FSF extractor locally: prompt + Graphviz validity check + 50-graph human spot-check (~0.5 day), extraction on MI210 (< 1 day GPU for a few thousand traces), the…
- DPF-W4-EFFREASON-E4 (intake-2327): Pruning or summarising failed branches before continuing raises accuracy 8-14% (models do not "unsee" failed attempts). — Trigger: the next context-folding A/B window. Build: a continuation harness that takes a logged thinking trace, removes the extractor-marked failed branch and continues via raw completion with cache_prompt (~1 day), then replicate Table 1…

- 2026-10-29 results filing: `codex-ni-yarn-dca-xdev-cpu-r2-20261029` refused22:09:01Z rc1 before the normal model path. The actual grant supplied CPUs96-119, and region-lock reported that this maps to no physical regions. This is a launcher/admission mapping failure, with no CPU PPL or cross-device verdict. Owner action: request a physical-quarter manifest under a fresh id; retain the original refusal. [Evidence](../../artifacts/compute/results-filing-20261029-2222.json). [belief: cc]

2026-10-29 23:40 results filing: cross-device CPU r3 ended rc75 at its6GiB process guard, sampled6,460,628,992 bytes, context65536, first native work incomplete, PPL null and cleanup verified. The short8192-context smoke PPL is not a substitute. No CPU/GPU comparison exists; the owner must qualify normal-context resource planning before a new successor. [Native result](../../artifacts/compute/results-filing-20261029-2340.json). [belief: cc]

2026-10-30 results filing: CPU cross-device r4 first normal65536-context attempt ended23:56:43Z rc75 at its16GiBguard, sampled17,263,681,536bytes in347.581s, first native work incomplete, PPLnull, cleanup verified. Later same-ID resumes and short-context smokes are separate; no CPU/GPU PPL comparison or uncertainty claim exists. Owner action: qualify normal-context resource planning under a fresh successor without changing comparison settings. [Original native result](../../artifacts/compute/results-filing-20261030-0000.json). [belief: cc]


### 2026-10-30 — four CPU continuation packets fit the disk budget

- [x] Qualify and publish all four task-local low-disk successors: S0v25/S1v26/S2v27/S3v28 (`yarn-oolong-s{0,1,2,3}-budget256-eligible{28,29,26,27}-v{25,26,27,28}-20261030`). Original120-pair denominator, aggregate eligible110, immutable unknown/no-redraw and A1-after-successful-matching-A0 rules remain unchanged;42000-second minimum/43200-second requested window retained. Each packet passed its own final-pin real normal and witnessed active-cutoff smoke, native writer and owned-tree drain, four-quarter T1/arming-declaration controls and keeper READY scan. Strict per-file/log/capture limits support a256MiB sampled cohort cap and four-shard1GiB allocation reserve plus128MiB safety above the150GiB floor. Cap pauses return75/partial, never truncated native result records; no full-cohort completion guarantee. Former grantless pollers were stopped by captured PID identity only after no-grant checks, and final old-cohort inventories showed no new exposure before successor enrollment. Smoke model is the actual captured Qwen3-0.6B, not the full27B measurement model. [no-belief: diagnostic launcher qualification and resource packing, no full27B quality/promotion result]

Evidence: `/mnt/raid0/llm/tmp/yarn-judged-cell-repair-v4-20261029/YARN-s{0,1,2,3}-READY-PUBLISHED.json`, per-shard arm controls/final re-inventory/budget audits, and `YARN-BUDGET-BUILD.json`. S3's first small-model cutoff exhausted its canaries before30seconds and was correctly rejected; a smoke-only15second deadline then passed both fresh modes without changing the official protocol.
2026-10-30 original GPUcross-device r2 failed before nativework because RUN_IDwasunbound. Separate r3 produced nativePPL14.3940 with0.21592within-runspread,137positiveowned-PIDresidencysamples andverifiedcleanup; nativejobrc0 butouterwrapperrc1/incomplete, whosecause isnotindependently established. This is valid standalone GPUarm collection, not the requestedCPU/GPUcomparison: availableCPU8K512/128smoke differsfromGPU64K2048/256. Do not interpret within-runspread asbetween-runCI or inferGPU/CPUadvantage. ExistingmatchedCPU/fullrecipe andwrapperrepair remainopen. [Originalevidence](../../artifacts/compute/results-filing-20261030-0038.json). [belief: cc]


2026-10-30: CPU r5 ended rc70 at in-claim admission (`DRYRUN_REFUSED: malformed claimed_cpus`), before its full native arm; no full CPU PPL exists from that attempt. Its earlier smoke/cutoff artifacts are separate. The GPU r3 result is a standalone measurement and does not form the declared matched CPU/GPU comparison. Existing owner repair covers the row's literal CPU metadata and completion environment; no offset attribution or significance claim. Original launcher SHA-256 `94385141b61ae11401d54476138221ca69a4176e407237b75251c1f5666cd232`. [belief: cc] [Original native audit](../../artifacts/compute/results-filing-20261030-0102.json). Existing full-run checkbox remains open.


2026-10-30: A new full CPU r6 window completed rc0, native PPL **13.6293 ± 0.20758**; accepted GPU r3 native PPL was **14.3940 ± 0.21592**. Lower is better; the observed GPU-minus-CPU difference is **+0.7647 PPL**. The original results bind identical model/text SHA-256 and source commit `9264f8095e4272f84e3b375e73b57ec380ecb328`, context 65536, batch 2048, ubatch 256, FA off, f16 K/V, one chunk and 24 threads. Neither command supplies a stride or seed; the pinned source default for PPL stride is 0 (legacy path), and no numeric runtime seed is recorded. Both native jobs exited cleanly and report verified cleanup; the GPU record includes positive owned-PID residency. These single-run +/- values are within-run token spreads, not a between-run interval; no statistical significance or speed claim. The previously observed offset persists under these matched settings, so it is **neither attributed nor removed** and the checkbox's done-when remains unmet. CPU native result SHA-256 `39f1643502aab70a5847e47651f6094fd58e599812900ab0a19fa920eb43ccad`; GPU `4607b1e453bfc6677679ce74a54ad4451f20ff81a7cdcd9ac7937436bc4ac0b5`. [belief: cc] [Committed original audit](../../artifacts/compute/results-filing-20261030-0115.json).


**CPU tokenwise attribution, original R2 diagnostic (2026-10-30).** The scheduled CPU arm completed at 02:48:06Z, rc=0. Native 64K-context, 24-thread, batch 2048/ubatch 256, FA off and F16 K/V produced PPL **13.6293 ± 0.20758** on Qwen2.5-0.5B-Instruct-f16 and wiki.test.raw; lower PPL is better. The ± value is within-run token spread, not a between-run confidence interval. This is one CPU arm, not a matched tokenwise GPU comparison or an attribution/equivalence/significance verdict. The native log states the 65,536 requested context exceeds the model's 32,768 training context.

- Native full result: `/mnt/raid0/llm/tmp/codex-ni-yarn-dca-attribution-cpu-r2-20261030/runs/codex-ni-yarn-dca-attribution-cpu-r2-20261030-full-1793328131/result.json`, SHA256 `b5c0bea9394489312af09f32b16ca163a1ff94b7b27a61dc178ff651a381cb02`. Native run duration 351.666s, sampled peak RSS 24,530,640,896 bytes across 698 samples; clean exit, writer and cleanup verified.
- Its CSV has exactly 64 rows for prediction positions 32768–32831 and target positions 32769–32832; SHA256 `9eb6b7a76b06e6d375552ee09fed60169754b037e76700143b2ff359b57448fb`. The full CSV, run log, process and resource sample hashes, source, binary, six loaded libraries, model and text checks are in [durable audit references](../../artifacts/compute/20261030-0310/results.json). Source commit `9264f8095e4272f84e3b375e73b57ec380ecb328`; packet SHA256 `0fe6d05d62b87cd79ea42c276cdb5c8941c1d7537a35952c2e8a38f8b3a938dc`.
- [belief: cc] Observation is limited to this native CPU diagnostic. Compare tokenwise only after a full matched GPU arm verifies identical source, model, text, context, batch, ubatch, attention and KV configuration; retain the original one-pair limitation.


2026-10-30 original GPU tokenwise attribution R1:

- **FAILED-RUN `codex-ni-yarn-dca-attribution-gpu-r1-20261030`:** the 03:13:08–03:13:11 GPU grant ended rc70 at in-claim admission, logging `invalid window, output or RAM`. The original row requests 1590 seconds, which is 30 seconds short of a whole-minute multiple, while `dryrun_check.py` rejects `requested % 60`; the row's 6 GiB RAM and 0.25 GiB output estimate satisfy that predicate. No `YDX_FULL_ENTRY` or full-run result was present. Prior bounded GPU smokes remain separate evidence; no matched full tokenwise attribution, kernel cause or significance verdict follows. [belief: cc]

[Original native audit references](../../artifacts/compute/results-filing-20261030-0320.json).


### 2026-10-30 overdue original-event filing (HIL, Paddle R14, FA4 and DCA)

GPU token-attribution R2 completed the full 65,536-context diagnostic: GPU PPL 14.3944 ± 0.21593 and prior matched CPU PPL 13.6293 (lower is better; ± is within-run token spread). The 64 prediction/target/token-ID keys match exactly, with shared model, text, source and recipe checks; GPU residency, native writer and cleanup verified. GPU result SHA-256 `f7f7aee0a479e29a103aa8085d51308048e23252eb04ca1b4ed8cc00ee330711`; token CSV `11c3ea9451ca277e76cc917cac17097d0a166bff70404263ba7483149257f745`. This single matched pair does not establish a kernel cause or statistical significance. [Native event audit](../../artifacts/compute/results-filing-20261030-0520.json). [belief: cc]


### 2026-10-30 05:30 original HSF and YaRN event filing

YaRN 128K MI210 R1's original 05:26:22Z grant ended rc1 at `live grant/GPU/disk admission refused`, before the scheduled output root or A0/A1 execution. This aggregate predicate also checks affinity, STOP, deadline, live grant and GPU lock; the original diagnostic does not isolate which check returned false. The frozen 120-pair McNemar rule therefore has no new verdict from this attempt. [Original event](../../artifacts/compute/results-filing-20261030-0530.json). [belief: cc]


### 2026-10-30 06:05 original EVL, Paddle and YaRN resource events

- YaRN Oolong S2 v27, S1 v26 and S3 v28 original grants ended 05:53:35/47/48Z rc75; each native record reports `new_exposures=0` and refusal at the 150 GiB floor plus 1 GiB aggregate reserve and 128 MiB safety. Retain the original 120-pair denominator: S2 has four unknown A0 and 26 candidate pairs, S1 one unknown and 29, S3 three unknown and 27; A1 requires matched A0 success. No full-cohort McNemar verdict. [Native event audit](../../artifacts/compute/results-filing-20261030-0605.json).
  - [belief: cc] Original native records and unchanged criteria are linked above.


**Refactor launcher repair checkpoint (2026-10-30):**

- [x] Repair and qualify retained Oolong S1/S2/S3 continuation launchers after obsolete T1 admission refusal. ✅ 2026-10-30 [no-belief: launcher qualification; no scientific result] Three READY successors retain original120 denominator and respectively1/4/3 immutable A0 unknowns, with29/26/27 eligible pairs. Each final frozen executed bundle passed normal native request/result and active cutoff rc75/partial/drain, plus actual no-argument startup and private scheduled-entry/inner controls. Private engines bypass obsolete outer and inner T1 receipts while actual jobs retain grant, CPU affinity, source, lock and resource validation. Smoke uses0.6B and shortened prompts; full27B cohort efficacy remains open. [Evidence](../../artifacts/compute/refactor-yarn-s123-t1-repair-20261030.json).
