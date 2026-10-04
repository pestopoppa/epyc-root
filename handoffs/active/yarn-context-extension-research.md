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
  - [ ] **YARN-E1-A2 — run the A2 negative control at 400K in the next YaRN window.** (filed 2026-10-04, workspace-ec)
    C3 pre-registered "A2 must score clearly worse, or the test is not discriminating", and E1 ran A0 and A1 only.
    Ride it on the YARN-E1-MEM re-measure or the YARN-DCA-E1 window. Done when A2's 400K needle score is recorded
    beside A1's 5/5.
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
- [ ] **YARN-FA-INT64-fold — fold the three FA-INT64-OFFSET commits into the champion before any run past 512K
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
  - [ ] **YARN-FN-FIX-fold — fold `5bfdcd18c` + `6c126e975` into the champion.** (filed 2026-10-04, workspace-ec)
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
- [ ] **YARN-FN-0 — (after YARN-FN-FIX) validate Flash-Next's NATIVE 262K before any YaRN arm on it.** Flash-Next has
  never served beyond 8,192 tokens, and its deepest benchmark is d4096. Its native long context is the more valuable
  experiment for that model, regardless of YaRN. It needs all four CPU regions, so it runs in an AutoKernel CPU
  window. Done when needle correctness and decode rate at 64K/128K/240K are recorded with the neutral haystack runner.
- [ ] **YARN-WIKI — recompile `wiki/context-extension.md` after E1.** That page carries stale facts: a "384GB RAM
  budget", "Hadamard q4_0 deployed", Qwen3.5/Qwen3-Next targets and TurboQuant. It lands in the operator-invoked
  `/wrap-up` wiki sweep, not as an ad-hoc edit. Done when the page reflects E1's result and this rewrite.
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

## Historical scope (2026-03-09 → 2026-09-07; superseded by the rewrite above)

**Status then**: QUEUED — blocker P3 long-context eval datasets resolved (2026-04-05). New quality gate added: Tulving 200ch episodic memory benchmark (P3b in research-evaluation-index). **Gate to reactivate**: context_extension becomes a concrete workload requirement AND the workload tolerates degraded position-discrimination above 32K (per intake-569 Theorem 3+4 trade-off table — raising the RoPE base helps token-distinguishing but provably hurts position-distinguishing; see `research/deep-dives/2026-05-20-rope-long-context-bounds.md`).
**Priority then**: LOW

## What is YaRN?

YaRN (Yet another RoPE extensioN) is a compute-efficient method to extend LLM context windows beyond their training length by modifying Rotary Position Embeddings (RoPE). It divides RoPE dimensions into groups and applies different linear scaling factors to each.

Two modes:
- **Fine-tuned**: Extends context ~2x with minimal training (0.1% of pre-training data)
- **Dynamic**: Extends >2x at inference time with zero fine-tuning

Zero overhead during inference — RoPE embeddings are pre-computed.

## Relevance to Our Stack

Qwen3.5 models have 256K native context, extensible to 1M with YaRN. Qwen3-Next-80B also supports 256K native + YaRN to 1M. Our ingest role (Qwen3-Next-80B) currently runs at default context. If we need >256K context for long document processing, YaRN is the path.

## llama.cpp Support

Fully supported with dedicated CLI flags:

```bash
# Extend a 256K model to 1M context
llama-server -m model.gguf -c 1048576 \
  --rope-scaling yarn \
  --rope-scale 4 \
  --yarn-orig-ctx 262144
```

| Flag | Purpose |
|------|---------|
| `--rope-scaling yarn` | Enable YaRN scaling |
| `--rope-scale N` | Context scaling factor (e.g., 4 for 4x extension) |
| `--yarn-orig-ctx N` | Original model context size |
| `--yarn-ext-factor N` | Extrapolation mix factor (0.0 = full interpolation) |
| `--yarn-attn-factor N` | Attention magnitude scaling |
| `--yarn-beta-slow N` | High correction dimension parameter |
| `--yarn-beta-fast N` | Low correction dimension parameter |

## Key Questions to Research

1. **Quality degradation curve**: How does RULER accuracy degrade from 256K → 512K → 1M with YaRN on our hardware?
2. **Memory impact**: KV cache for 1M context at Q4 — how much RAM does this consume?
3. **Speed impact**: Does YaRN affect generation speed or just prompt processing?
4. **Qwen3.5 vs Qwen3-Next**: Which model retains quality better under YaRN extension?
5. **GGUF metadata**: Do Unsloth GGUFs include YaRN parameters in metadata, or must we specify manually?

## References

- **Original Paper**: [YaRN: Efficient Context Window Extension of Large Language Models](https://arxiv.org/abs/2309.00071) (ICLR 2024)
- **GitHub**: [jquesnelle/yarn](https://github.com/jquesnelle/yarn)
- **llama.cpp PR**: [#2268 — YaRN RoPE scaling implementation](https://github.com/ggerganov/llama.cpp/pull/2268)
- **EleutherAI Analysis**: [YaRN paper summary](https://www.eleuther.ai/papers-blog/yarn-efficient-context-window-extension-of-large-language-models)
- **Tutorial**: [Understanding YaRN (Medium)](https://medium.com/@rcrajatchawla/understanding-yarn-extending-context-window-of-llms-3f21e3522465)
- **Qwen3-Next-80B**: [HuggingFace model card](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct) — RULER 91.8% avg across 4K-1M
- **Qwen3.5-27B**: [HuggingFace model card](https://huggingface.co/Qwen/Qwen3.5-27B) — 256K native, 1M with YaRN

## Research Intake Update — 2026-04-18

### Tulving Episodic Memory Benchmark as YaRN Quality Gate (intake-408/409 deep-dive)

The Tulving Episodic Memory Benchmark (arXiv 2501.13121, ICLR 2025) tests entity tracking and temporal ordering across extended narratives. The 200ch variant (100K tokens, 686 QA pairs) is now proposed as a quality gate for YaRN extension, complementing RULER/NIAH.

**Why this benchmark matters for YaRN**: RULER and NIAH test retrieval ("find the needle"). Tulving tests episodic memory ("track this entity across 200 chapters and order events chronologically"). YaRN quality degradation at extended contexts may manifest differently across these axes — a model could pass NIAH at 512K but fail temporal ordering.

**Scaling data from the benchmark** (across 21 models at 100K tokens):
- Sharp performance cliff between 10K and 100K for most models. Only Gemini-2.5 survives with <2% recall loss.
- Chronological awareness degrades faster than simple recall at every scale transition
- At 1M tokens (Gemini-2.5-Pro only): recall 0.968→0.654, chronological 0.796→0.320
- **Prediction for YaRN**: Expect steeper degradation on chronological awareness than on RULER/NIAH at equivalent context lengths. If YaRN-extended Qwen3.5 passes RULER at 512K but fails Tulving chronological awareness, it signals attention distribution problems that YaRN's RoPE scaling doesn't fully compensate.

**Integration**: The 200ch dataset (Figshare download, MIT license) is queued as P3b in [research-evaluation-index.md](research-evaluation-index.md). Add to P4 YaRN eval alongside RULER quality degradation curve.

**Rescoped 2026-09-07 (intake-408#record, dive-verified).** The Tulving-as-YaRN-gate hypothesis is
retained and is sound in principle — a YaRN-extended model that passes NIAH but fails Tulving
temporal ordering signals an attention-distribution problem RoPE scaling does not compensate — but
it is now **downstream of M-12, not a competitor for the same inference window**, and it must use
the **200ch/100K** split and the **fixed tau** (M-12e). "24 models" corrected to 21. The archived
"P3b" pointer above is historical: P3b is retired to
`../archived/research-evaluation-index-history-through-2026-06-19.md:114`; the live owner is
[episodic-memory-integrity.md](episodic-memory-integrity.md) M-12.

**EM-LLM alternative (intake-409)**: EM-LLM (arXiv 2407.09450) extends context to 10M tokens via episodic memory retrieval with no fine-tuning. Outperforms InfLLM +4.3% on LongBench. Complementary to YaRN (YaRN extends native window; EM-LLM retrieves beyond it). However, full integration requires deep llama.cpp modifications (per-layer KV access, unified softmax) — estimated 4-8 weeks. **Not viable for our stack without major surgery.** YaRN remains the preferred context extension path.

## Research Intake Update — 2026-03-24

### New Related Research
- **[intake-191] "TurboQuant: Redefining AI efficiency with extreme compression"** (arxiv:2504.19874)
  - Relevance: Directly addresses question 2 (KV cache memory at 1M context). 6x+ KV cache memory reduction via 3-4 bit quantization without training.
  - Key technique: TurboQuant combines PolarQuant (polar coordinate compression) and QJL (1-bit Johnson-Lindenstrauss transform) for data-oblivious KV cache quantization.
  - Reported results: 6x+ memory reduction, 8x attention speedup on H100, perfect accuracy on needle-in-haystack.
  - Delta from current approach: We have no KV cache quantization. At 1M context, KV cache dominates RAM — 6x reduction would make extended context practical on our EPYC stack.
- **[intake-192] "PolarQuant: Quantizing KV Caches with Polar Transformation"** (arxiv:2502.02617)
  - Relevance: Component technique of TurboQuant. 4.2x KV cache compression via polar coordinate transformation. Eliminates normalization overhead.
- **[intake-193] "QJL: 1-Bit Quantized JL Transform for KV Cache Quantization with Zero Overhead"** (arxiv:2406.03482)
  - Relevance: Component technique of TurboQuant. 5x KV cache reduction to 3 bits. Has GitHub implementation (github.com/amirzandieh/QJL). Published at AAAI 2025.

## Research Intake Update — 2026-05-20

### New Related Research
- **[intake-569] "RoPE Distinguishes Neither Positions Nor Tokens in Long Contexts, Provably"** (arxiv:2605.15514)
  - Relevance: Bounds the cost of YaRN's central trick. YaRN extends context by **raising the RoPE base hyperparameter** — this paper proves (Theorems 3+4) that raising the base trades off position-distinguishing for token-distinguishing, and the trade-off is irreducible: a single base cannot preserve both. **YaRN does not contradict this; it accepts the trade-off implicitly.** The paper turns the trade-off explicit and quantifies where it bites.
  - Key technique: closed-form statistical model (RoPE Product ~ Normal RV) + 4-way failure taxonomy {position inversion, position aliasing, token inversion, token aliasing}. Proves position inversion → 1/2 (chance) as `log M log B → ∞`; position aliasing converges to 1 exponentially with M.
  - Reported results: empirically 7B–405B models (Llama 3.1, Mistral, Qwen3, DeepSeek-v3, Kimi k2.5, GPT-OSS) all collapse to ~0.25 (random) on a position-indexing task by 4K–8K tokens. At 8K BF16: 75K position-aliasing pairs + 1,491 attention-invariance cases. Token inversion → 1/2 once `m ≥ 20K`.
  - Delta from current approach: Strengthens the **"YaRN is gated to a concrete workload need, NOT a default"** posture this handoff already takes (Status line: "Gate to reactivate: context_extension becomes a concrete workload requirement"). Cite this paper as theoretical justification for the gate; do not change the gate criteria.
  - Caveat (Tier 2b): paper is 2026-05-15 (5 days old at intake); the most dramatic chance-floor claims kick in at 128K+ where EPYC operates rarely (we cap at 32K–64K in practice). Use as informing-evidence, not blocking-evidence.

## Progress checklist

- [x] QUEUED (LOW): reactivate when context_extension is a concrete workload requirement tolerating >32K position-discrimination loss ✅ 2026-10-04 — reactivated by the ADAPT rewrite. The operator wants long context and approved E0+E1, and the ">32K tolerance" clause is replaced by YARN-E1's pre-registered gate. The live tasks are in *2026-10-04 rewrite → Tasks* at the top of this file.
