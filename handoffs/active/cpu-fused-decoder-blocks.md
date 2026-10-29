# CPU Fused Decoder Blocks (batch-1 decode megakernel)

**Status**: **A-GATE FAILED 2026-09-02 — the plan below is the historical design record, not a live plan.** ~~**PLAN APPROVED by operator 2026-08-30** — bit-exactness prioritized (NMSE ≤1e-4 acceptable fallback); qwen4exp-first with the GDN family in mind; op-based execution model (direct fast-path acceptable if diligent); decode prioritized, pp desirable; plan persisted before work begins.~~ The approval stands as a historical fact; what it authorised did not pass its own gate — see *Viability gate result 2026-09-02* below (fused 961 ms/token vs graph 196.9 ms in the same process and window). The 2026-09-01 control arm reproduced the same direction (graph-1T 350 ms vs fused-1T 1350 ms): **the megakernel does not currently deliver, and the scratch churn is the liability.**
**Created**: 2026-08-30
**Priority**: ~~HIGH — the last identified path to 20-60 t/s batch-1 CPU decode~~ **STALE 2026-09-08 (INF-70 audit)** — the "last identified path to 20-60 t/s" framing predates A-GATE. Re-ranking this handoff's priority is an operator/owning-session decision and is deliberately NOT made here; note only that the operator directive of 2026-09-07 stops lever research until a fully consolidated champion exists.
**Categories**: hardware_optimization, inference_serving, local_inference, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-67; the kernel-tree commit tags historically said INF-64)
**Related**:
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) (INF-10) — the direct predecessor: same diagnosis (barrier/op-count-bound, not BW), 4 fusion arms REFUTED, the +2.6% DeltaNet-native-fused-wqkv precedent this project scales up
- [`batched-decode-measurement.md`](batched-decode-measurement.md) — the NUMA×placement canonical recipe (interleave+no-mmap), the same family's reference numbers
- [`autokernel-research-loop.md`](autokernel-research-loop.md) — the GPU megakernel/persistent-kernel literature (L4 lever) this project is the CPU analogue of
- `handoffs/active/master-handoff-index.md` — the router

**Framing superseded 2026-09-02 (INF-70 audit)**: this file remains the fused decoder's design record
and phase checklist. The live viability task list (A1–A4, A-GATE), the corrected measurement ledger and
the program this work now belongs to are in [`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md)
(INF-70). The section below is the historical design premise: the 74 ms anchor does not reproduce
(INF-68 measured ~110 ms UD / ~95 ms uniform on a clean build), the 28/46 ms split and the 65 µs/9.4 ms
constants are in no committed profiler record, and the measured node count is 7,906 pre-fusion /
~6,890 on the baseline build, not ~5,850. Do not quote this section's numbers; quote INF-70's ledger.

**Viability gate result 2026-09-02 (INF-70 Axis A, branch `inf70/fused`)**: with the batched `mul_mat`
substitution (A1) and the scratch arena (A2) both in, a clean Release build at `-t 1` measures fused
961 ms/token vs graph 196.9 ms in the same process and window — gemv column 810 ms, other column 150.6 ms;
logit gate max_abs 1.311 / NMSE 6.07e-2. **A-GATE FAIL.** Three fused-path correctness bugs the campaign did
not have were found and fixed on the way (GDN state byte/float offset, repacked IQ4_NL hc loras read as
plain rows, F16 `ple_conv1d` read as F32), and the pre-A1 per-row path aborts with heap corruption on the
pristine tree in Release. Details: `/mnt/raid0/llm/tmp/inf70/agents/fused/REPORT.md` and INF-70 Axis A.

## The measured problem (2026-08-29/30, qwen4exp IQ4_XS UD, interleave baseline)

Batch-1 decode = ~74 ms/token (~13.5 t/s, t48; t64 sweet spot ~14). Breakdown, all in situ:
- ~28 ms real gemv work (expert mul_mat_id ~9.4 ms at ~65 μs/call median; dense ~18 ms) — at the machine's real memory rate (~100-180 GB/s in situ)
- ~46 ms of non-gemv dispatch: ~5,850 nodes × ~5-8 μs each (barrier + dispatch + tiny elementwise compute)
- Four clean-room kernel experiments (fused hc_mix op, elementwise chain fusion ×3, gemv software pipelining) all measured NEUTRAL or NEGATIVE in situ despite clean-room wins up to +55%. The per-node machinery cost is irreducible per-node; the only way down is fewer, fatter nodes.

## The idea

Collapse the ~6,800-node decode graph to ~100 nodes: **one fused op per layer** (GGML_OP_GATED_DELTA_NET_FUSED_LAYER ×36 + GGML_OP_FULL_ATTN_FUSED_LAYER ×12 + PLE/head tail). The layer's math runs as one sequential kernel — data flows in registers/L2, no graph barriers between the layer's micro-ops. The per-node machinery runs once per layer instead of once per micro-op.

**Target**: ~28 ms gemv + ~96×15 μs fused overhead (~1.5 ms) + state/attention (~5 ms) ≈ 35-45 ms → **22-28 t/s**, with gemv micro-tuning inside the fused kernels (where dispatch can no longer eat it) reaching 30-40.

## Operator decisions (locked 2026-08-30)

1. **Numerics contract**: bit-exactness PRIORITIZED (mirror the decomposed op order internally); NMSE ≤1e-4 acceptable where bit-exactness costs too much freedom. The arch test's CPU-vs-GPU NMSE bar applies as the floor.
2. **Scope**: qwen4exp-first; the GDN family (qwen3.5/qwen3next/qwen35moe) served by the same fused ops if it isn't disproportionate — the layer structure is shared via `llm_build_delta_net_base`.
3. **Execution model**: op-based (new GGML ops, ~100-node graph, fits the scheduler/backends). A direct decode fast-path outside the graph is permitted if it becomes clearly better — diligence required (the blast radius is real).
4. **Priority**: decode first; pp acceleration via the same ops (batched) is desirable but secondary.

## Phases

| Phase | Deliverable | Milestone / gate |
|---|---|---|
| **0** | Measurement infra: fix the logit-dump tool (was crashing), standard A/B harness at the interleave baseline, in-situ profiler runs (all present from prior rounds) | reproducible fused-vs-decomposed logit diff ≤1e-4 |
| **1** | Fused GDN-layer function (36 layers): hc_mix + qkvz + conv + GDN scan (the ggml_gated_delta_net kernel) + output proj + MoE (router/top-k/topk-norm weights/expert dots/shexp) + hc_combine; recurrent + conv state in/out | decode 74 → ~45 ms; logit diff + greedy generation + arch test |
| **2** | Fused full-attn layer function (12 layers): QSA indexer (top-k blocks) + attention + gate + MoE; KV cache + indexer cache interfaces | decode → ~38 ms |
| **3** | PLE + head + tail; the process_ubatch hook; full fused decode | full fused decode + logit-diff validation |
| **4** | Thread-pool integration + gemv/activation micro-opt INSIDE the fused kernels (safe now — no dispatch to lose it) | 30-40 t/s |

Checklist (the dashboard gate — flipped as the phases land):
- [x] Phase 0: logit-dump tool fixed and verified; A/B harness + in-situ profiler established
- [x] Phase 1: fused GDN-layer function committed (`e57e1d542`) — compiles clean, single-threaded
- [x] ~~Phase 1 gate: logit diff ≤1e-4 + greedy generation + arch test (needs the hook)~~ (closed 2026-10-29 audit: SUPERSEDED → handoff header line 3: A-GATE FAILED 2026-09-02, plan is "historical design record, not a live plan"; fused path retired to opt-in in champion C5 (c72ec82f5))
- [x] Phase 3 partial: fused_head + fused_decode_token skeleton committed (`2d699f02c`)
- [x] Phase 2: full-attn layer function committed (`95902fefa`) — QSA indexer + flash-kernel attention; rotations + long-context indexer rope marked for the validation pass
- [x] Phase 3 partial: fused_ple committed (`8fd4c7f15`); head + decode-loop skeleton already in; the process_ubatch hook committed (`99a1c111e`)
- [x] ~~Phase 1 gate: logit diff ≤1e-4 + greedy generation + arch test (needs the MoE fix)~~ (closed 2026-10-29 audit: SUPERSEDED → handoff header line 3: A-GATE FAILED 2026-09-02, plan is "historical design record, not a live plan"; fused path retired to opt-in in champion C5 (c72ec82f5))
- [x] ~~Phase 4: thread-pool integration + fused-kernel micro-opt~~ (closed 2026-10-29 audit: SUPERSEDED → handoff header line 3: A-GATE FAILED 2026-09-02, plan is "historical design record, not a live plan"; fused path retired to opt-in in champion C5 (c72ec82f5))
- [ ] **FD-OFF-PROD — declare `GGML_FUSED_DECODE_OFF=1` for production `architect_general` (:8074) so serving matches every measured Q38FN number (filed 2026-10-24, 3c4ca599).** Every Q38FN speed/correctness result (research recipe, AK q38fn campaigns, `optimal_cpu_serving` 43.28 t/s) used OFF=1, but the production launcher does not set it, so :8074 runs the default-ON fused path, which carries the open FD-DIV-1b defect (synthetic weight scales; the real UD model was byte-identical in FD-DIV-1a) and the CH-24 `/tmp` debug writes. A ratification package (one operator command, env-diff proof, no reload; the owning session reloads `architect_general` afterwards) is being prepared at `/mnt/raid0/llm/tmp/ratify-fused-off-20261024/PACKAGE.md`. Blocker after the package exists: operator signature. Follow-up once FD-DIV-1b is fixed: measure fused ON vs OFF on Q38FN and decide whether serving should re-enable it.
  - *(2026-10-24 (3c4ca599) operator direction: fix in the champion, not production. Resolved in champion fold C5 (`experimental/champion-c5-20261024` @ `c72ec82f5`: fused decode default-OFF in code, opt-in GGML_FUSED_DECODE_ON=1; plus 14c57cbe9/CH-24 gating); reaches production at the next kernel promotion. RATIFY-FUSED-OFF-ARCHGEN-20261024 is parked (not to be run). workspace-58's v10 test: production :8074 as launched is coherent with zero fused calls (MTP verify batches skip the single-token fused path), so the defect was latent there.)*
  - *(2026-10-25, workspace-58 CAS subagent.)* **Resolved in champion C5**: the champion ref `ak/champion/llama-cpp-ffc1bac82eec` is now `c72ec82f5` (CH-31 CAS 2026-10-25T08:24:10Z, fork pushed), carrying `4976a189f` (fused decode default-OFF, manifest V11-106) and `c72ec82f5` (layout contract, V11-107). Not ticked: production is still v10 (default-ON) until the next kernel promotion; the box closes when the promoted v11 candidate carries V11-106. [no-belief: champion CAS is a ref operation; gate evidence is in c4/c5-fold-prep]
- [ ] **FD-DIV-1 — the Flash-Next (`qwen4exp`) fused decode diverges from the graph at non-production weight scales,
  and double-frees at w=1.0.** (filed 2026-10-04, workspace-ec; **owner TBD, the Flash-Next owner**)
  - The repro is committed as `45d8f2937` on `experimental/fused-yarn-20261004`: `QFR_*` knobs, with the log at
    `artifacts/dca-yarn-kernel-20261004/fused-divergence-repro.log`.
  - Default synthetic weights: OK (logits 1.7e-11).
  - `w=0.05, norm N(1,0.1)`: logits nmse 1.84, K 1.08, indexer 1.06 on all three rope configs.
  - `w=1.0`: abort, "double free or corruption (out)".
  - The divergence starts before attention, in layer 0 (GDN + MoE + hyper-connections).
  - **Keep `GGML_FUSED_DECODE_OFF=1` in production** until this is root-caused.
  - Done when the divergence and the double free are root-caused and fixed (fused ≡ graph within tolerance at
    w ∈ {0.05, 0.3, 1.0}), or the fused path is retired.
  - *(2026-10-23: FD-DIV-1a PASS. The real-model double free is fixed by `14c57cbe9` (GSQ falls through to the graph; UD fused path unchanged). **Still open:** the synthetic-weight divergence at w=0.05 and the w=1.0 abort of the repro, now FD-DIV-1b; plus the fold of `14c57cbe9` via the champion route.)*
  - *(2026-10-22, workspace-58 subagent, from NEW-10's smoke abort; box stays open.)* **Double free
    root-caused on a real model.** The GSQ-RCO Q38FN IQ3_XXS GGUF aborted the production CPU `llama-completion`
    (fused path ON, i.e. without `GGML_FUSED_DECODE_OFF=1`) on the first decode token with the same "double free or
    corruption (out)". Chain:
    1. GSQ stores `blk.*.ffn_down_shexp` as IQ4_NL (40 layers incl. layer 0; UD-IQ4_XS stores Q8_0). IQ4_NL is not on
       the `GGML_IQK=1` repack exclusion list (`repack.cpp`), so CPU_REPACK interleaves it (`iq4_nl_8x8`). Fused
       `lora_mm`/FusedMM does a plain per-row `vec_dot` at `data + row*nb[1]`, reading interleaved bytes as block
       scales, so the shared-expert down goes NaN at layer 0.
    2. Layer 1's `fused_moe` gets all-NaN router logits; no prob beats -INF, `best` stays -1, and
       `probs[-1] = -INFINITY` overwrites the malloc chunk size (0xff800000); the vector's `free()` then aborts "(out)".
    3. Second, latent bug: GSQ's `blk.1.ple_conv1d` is F16 and `fused_ple` read it through a `float*` (twice the
       tensor's bytes, garbage values). The graph already casts it to F32 (`build_ple`).
    - Patch `14c57cbe9` on llama.cpp `experimental/new10-ple-type-fix-20261022` (worktree
      `/mnt/raid0/llm/worktrees/llama-new10-ple-fix-20261022`, `src/models/qwen4exp-fused.cpp` +101/-7, UNBUILT):
      `fused_weights_supported()` refuses the fused path (one `LLAMA_LOG_WARN`, falls through to the graph) if any
      row-gathered weight is repacked, except `fused_moe`'s IQ4_NL `ffn_down_exps` which has a repack-aware mirror, or
      any raw-`float*` tensor is not F32; `fused_ple` widens `ple_conv1d` to F32 via `to_float` (tap stride uses
      `kern`); `best < 0` now `GGML_ABORT`s with a diagnostic; the bring-up prints and per-token `/tmp/qwen4exp-builds`
      dumps are gated on `GGML_FUSED_DECODE_TRACE`. Graph path untouched; production keeps `GGML_FUSED_DECODE_OFF=1`.
    - Whether the synthetic-weight divergence at w=0.05 has the same cause is not yet shown (the repro's synthetic
      weights are not repacked IQ4_NL); the ASAN repro below answers it.
  - [x] **FD-DIV-1a — build `14c57cbe9` and run three smokes (correctness, one build-role grant).** (1) GSQ IQ3_XXS
    with the fused path ON under the patch is byte-identical to the same model with `GGML_FUSED_DECODE_OFF=1`
    (the refusal falls through to the graph); (2) UD-IQ4_XS, patched build vs the production v10 store build,
    byte-identical greedy output; (3) optional: the FD-DIV-1 repro (`45d8f2937` `QFR_*` knobs) under ASAN at
    w ∈ {0.05, 0.3, 1.0}. Experimental branch only; v10 stays frozen; a fold goes through the champion route with a
    v11 manifest row. (filed 2026-10-22, workspace-58)
    - *(2026-10-23 15:3xZ, workspace-58 wrap-up; box stays open.)* IN PROGRESS: a workspace-58 subagent is preparing the job (launcher and FILLERS row). The slot is booked on q2 tonight after s5-cs8l4ab, and it runs if armed (calendar REVISION 15:2xZ). Not landed at this checkpoint.
    - *(2026-10-23 16:43Z, workspace-58 wrap-up; **FD-DIV-1a PASS**, pass rule PREDECLARED.json sha256 `02251f47...`.)* Verdict `/mnt/raid0/llm/tmp/fd-div-1a-20261023/out/VERDICT.md`, receipt `/mnt/raid0/llm/tmp/fd-div-1a-20261023/out/fd_div_1a_receipt.json` (`epyc.fd_div_1a.smoke_receipt.v1`). Smoke 1 (GSQ IQ3_XXS, patched `14c57cbe9`, fused ON vs v10 `GGML_FUSED_DECODE_OFF=1`): byte-identical on 4 prompts; unpatched v10 fused ON still aborts (rc 134), defect reproduced. Smoke 2 (UD-IQ4_XS, patched vs v10): byte-identical. Smoke 3 (ASAN repro) SKIPPED: `tests/test-qwen4exp-fused-rope.cpp` exists only on `experimental/fused-yarn-20261004`; filed as FD-DIV-1b. Production keeps `GGML_FUSED_DECODE_OFF=1`; folding `14c57cbe9` goes through the champion route with a v11 manifest row.
    - *Observation, no speed claim:* on UD-IQ4_XS, v10 fused-ON decode is ~1500-2000 ms/token vs ~70-87 ms/token on the graph (fused-off) path (descriptive, single runs); warrants a look.
  - [x] **FD-DIV-1b — port the FD-DIV-1 repro and run it under ASAN (filed 2026-10-23, workspace-58 wrap-up from FD-DIV-1a smoke 3).** `tests/test-qwen4exp-fused-rope.cpp` (`QFR_*` knobs) lives only on `experimental/fused-yarn-20261004` (`5bfdcd18c`, `6c126e975`, `45d8f2937` on top of five commits not in v10); `6c126e975` gates the same per-token trace output `14c57cbe9` gates, so the port is a merge with a known textual overlap, plus a second (ASAN) build. Run at w in (0.05, 0.3, 1.0). Done when it answers whether the synthetic-weight divergence has the repacked-IQ4_NL cause or another. Experimental branch only; own build-role grant. ✅ 2026-10-24 — **ANOTHER_CAUSE** (ASAN build of 14c57cbe9 + test port `2a2a79bb6`, q1 08:20-08:22Z; PREDECLARED sha256 `293c89a2…`): ctl CLEAN; w=0.05 DIVERGE (logits nmse 1.84), w=0.3 DIVERGE (3.49), w=1.0 ABORT "fused_moe: non-finite router logits"; ASAN reported no memory error. The F32/F16 fixture excludes the repack chain, so a second fused-MoE defect exists. Verdict `/mnt/raid0/llm/tmp/fd-div-1b-20261024/out/VERDICT.md`.
  - [ ] **FD-DIV-2 — the fused qwen4exp decode is WRONG on the real served model (v10 production and C3), and ~20x slower; fix it or make it default-OFF in code (filed 2026-10-24, workspace-58).** Evidence: (1) FD-DIV-1a Informational, `/mnt/raid0/llm/tmp/fd-div-1a-20261023/out/VERDICT.md:22`: UD fused (v10) vs graph (v10) `fused_equals_graph=false` on all 4 prompts (first_diff_byte 2-7), decode 1485-2004 vs 69-87 ms/token; (2) q38fn-armP v1 coherence on C3 without `GGML_FUSED_DECODE_OFF=1`: UD greedy output garbage, coherent with the knob (`/mnt/raid0/llm/tmp/ws58-q38fn-armP-20261024/void-run1-20261024/`); (3) FD-DIV-1b ANOTHER_CAUSE above. Production architect_general (:8074) sets no OFF knob, so it serves wrong output whenever up (down since 10-11). UPDATE 2026-10-24 ~10:1xZ: the v10 production check (`/mnt/raid0/llm/tmp/ws58-v10-fused-coh-20261024/VERDICT.md`) reads NO-DEFECT AS LAUNCHED: with the exact production argv/env (MTP draft, fused nominally ON) both arms are coherent and 0 fused-path lines appear, because MTP verify batches never take the single-token fused path. The defect is LATENT for production. Per the operator rule (fix in the champion, not v10/production), RATIFY-FUSED-OFF-ARCHGEN-20261024 stays parked and :8074 is NOT held; the fix is the C5 fold (3c4ca599: fused decode default-OFF in code, opt-in GGML_FUSED_DECODE_ON=1, plus 14c57cbe9 + CH-24 gating). Done when the fused path matches the graph byte-for-byte on the UD Paris/short/long prompts at production flags, or the knob defaults OFF in a promoted kernel.
  - [x] **FD-DIV-1a decision-line CORRECTION (workspace-58, 2026-10-24).** ✅ 2026-10-24 — the 1a verdict line "production keeps GGML_FUSED_DECODE_OFF=1" was FALSE for the production launcher, and smoke-2 PASS compared patched-fused vs v10-fused (equally wrong), so it never tested correctness against the graph. The Informational fused-vs-graph result above (false on all prompts) was the real signal and was missed.
  - *(2026-10-24.)* The fold of `14c57cbe9` via the champion route is C5 (`c72ec82f5`, V11-107, CH-31). FD-DIV-1b stays open (INF-67); the fused path is opt-in from C5.
  - *(2026-10-28, workspace-58; **FD-DIV-1b re-run on C5: PERSISTS_ON_C5**.)* Champion C5 `c72ec82f5`, ASAN build 115 s on CPUs 78-95, actual rc0 at 02:24:41Z. Cells: ctl CLEAN, w=0.05 DIVERGE, w=0.3 DIVERGE, w=1.0 ABORT (nonfinite router guard); no AddressSanitizer ERROR in those four cells. Source seal `c58d6d80588287a384e05b08ed20b794ce4912d6f7ea4d338cfefce441d3d5fa`, declaration `a90f03cbee1c99884752b623dd37231032c075d2d349a6fea5e52cc35f5617ad`, audit `/mnt/raid0/llm/tmp/codex-ni-20261028-fddiv1b-audit/audit.log`, packet `/mnt/raid0/llm/tmp/codex-ni-20261028-fddiv1b-t1`. Scope: synthetic correctness finding only; not a global memory-safety proof, does not identify the fix site, says nothing about production. The parent fused-decode fix (FD-DIV-2) stays OPEN. [belief: cc]

## Validation strategy (learned the hard way — the arch test is self-consistent and cannot see graph-math errors)

1. **Logit comparison** (the dump tool, fixed in Phase 0): fused vs decomposed per-token, ≤1e-4, per layer type, before any perf claim.
2. **Greedy generation test** (Paris-style) — the real gate; every change.
3. **test-llama-archs** — necessary, insufficient.
4. **In-situ profiler** (`GGML_CPU_PROF` + `[mm_prof]/[mmid_prof]`) — the ONLY trustworthy perf instrument; clean-room numbers have lied 4/4 times.

## Risks

- **Numerics**: the fused op's internal order must mirror the decomposed (bit-exact) or stay within the NMSE — the hc_mix revert (the 2·sigmoid fold bug) is the standing warning: graph-math errors pass the arch test and show as garbage generation.
- **State machinery**: the recurrent/conv state + QSA indexer + PLE interfaces are the hardest correctness surface — Phase 1 deliberately picks the uniform layer type first.
- **The MoE routing** (dynamic expert selection) inside a fused kernel.
- Effort: 4-8 focused sessions; the branch `exp/cpu-fusion-qwen4exp-20260829` and the worktree `/mnt/raid0/llm/llama.cpp-cpu-fusion-20260829` are the workspace (champion `270b48ed6` + 4 qwen4exp backports + confirmed fusion ops mean_d1/moe_topk_norm + profiling tooling).

## Phase 0 DONE (2026-08-30) — tooling + fast-path hook design

- Logit-dump tool fixed and verified: `/tmp/qwen4exp-builds/dump_logits2` — the `-1` text_len convention is gone in this API (caused `std::length_error` in `llama_vocab::tokenize`); the two-pass tokenize returns the negative buffer size; the tool now writes the full 248,320 logits to a file for the fused-vs-decomposed diff.
- A/B harness: `numactl --interleave=all` + `-mmp 0`, t48/t64, IQK=1, the in-situ profiler (`GGML_CPU_PROF` + `[mm_prof]/[mmid_prof]`) — all established from the prior rounds.
- **Fast-path hook design**: `llama_context::process_ubatch` (src/llama-context.cpp:1320) is the single hook point — after the mctx apply, a branch: `model.supports_fused_decode() && gtype == LLM_GRAPH_TYPE_DEFAULT && batch-1 decode && CPU backend` → the fused decode writes the logits into the `llm_graph_result` and returns; the graph machinery untouched otherwise. State access via the memory context (the hybrid-idx cast, like the graph does); weights via the model's layers. The user permitted the direct fast-path blast radius.

## Phase 1 progress (2026-08-30) — foundation committed

- `src/models/qwen4exp-fused.cpp` committed (`6321806b3`): the kernel-mirror helpers (FusedMM, lora_mm, hc_rms_norm_gamma, hc_stream_mean, hc_mix) — each mirrors the graph's exact function/order for bit-exactness. Single-threaded for now (correctness first).
- `e57e1d542` committed the FULL fused GDN-layer function: hc_mix + qkvz + conv state + 4-tap causal conv + l2 norms + the ggml_gated_delta_net kernel (scratch ctx + 1-thread pool) + z-gated rms + ssm_out + fused_moe (softmax router, argsort top-k, topk-norm weights, expert dots, shared expert) + hc_combine x2. Every op mirrors the graph's function/order for bit-exactness. Single-threaded (correctness first). Compiles clean, tree green.
- Next: thread-pool integration (the mms + the GDN kernel at nth>1), then the full-attn layers + PLE + head, then the process_ubatch hook + logit-diff validation.

## Current tree state (starting point)

- Branch `exp/cpu-fusion-qwen4exp-20260829` @ `7cdd7c97b` — clean, arch suite 0 FAILs, "Paris" verified.
- The measurement recipe: `numactl --interleave=all` + `-mmp 0`, t48/t64, IQK=1, the in-situ profiler.
- Decode baseline: ~12.4-14.9 t/s depending on the box state.

## Validation round 1 (2026-08-31) — the hook is wired; five correctness fixes landed; MoE NaN open

- The `process_ubatch` fast-path hook (committed `99a1c111e`, env-gated `GGML_FUSED_DECODE_OFF`
  for A/B): single-token decode on a CPU-resident qwen4exp runs `fused_decode`; any failure or
  unsupported cache type falls through to the graph.
- **A/B harness** (`validation/dump_logits_seq`): one model, two contexts; both decode the prompt
  batch through the graph (sanity: bit-identical, and bit-reproduces the Aug-30 `logits-ref.bin`),
  then 8 single-token steps — the graph ctx (env OFF) drives the greedy token stream, the fused
  ctx runs the fast path; per-step max-abs-diff + NMSE. Graph-only control: clean (0.0 diffs).
- **Five fixes** (commit `9a915a823`, ASAN-verified, `build-asan`):
  1. GDN kernel `wdata` null → segfault; sized scratch `S_v + 16` floats.
  2. `qkv` span: `ssm_d_inner` (6144) is the v-span; `wqkv` writes 10240 → 16 KB heap overflow.
  3. Conv-state staging `rl->ne[0]*4` → the row is `(d_conv-1)*conv_channels == rl->ne[0]`; 4×
     copy-back overrun.
  4. z-gate one scalar per head vs the graph's elementwise `sigmoid(z)`.
  5. `ssm_norm` OOB: `znorm[h*S_v+i]` on a `{head_v_dim}` tensor → garbage → NaN `final_in` →
     NaN router logits → `fused_moe` wrote `probs[-1]`.
- **Full-attn wiring rewrite**: KV/indexer writes were going to local copies at `pos` (OOB and
  lost). The caller now derives the used/visible cells from the cells API (`get_cells` passthrough
  on `llama_kv_cache_context`); the layer writes into the cache views at the current cell
  (n_used-1) and masks the current cell out of the attention; the QSA block path scores the
  visible cells only.
- **FIXED — the MoE NaN (commit `2fcfc5bc1`)**: the IQ4_NL down-expert tensors live in the
  **CPU_REPACK** buffer (8x8-interleaved rows on AVX2; the repack compute handles that layout,
  the plain vec_dot cannot). The fused MoE detects `tensor->extra` and mirrors
  `ggml_gemv_iq4_nl_8x8_q8_0_generic`. Also fixed in the same pass: the conv kernels read
  transposed (tap-fast per `c[i0 + i1*nc]`), the GDN state copy-back froze the recurrence
  (must copy tgd's state region, not ts), the F16 attention/indexer caches (staged F32 view +
  cast-back writes), the IMROPE 4-position format, the rope/flash kernel wdata + threadpool,
  and the meta-only result ctx (logits into the previous graph's sched-known t_logits).
- ~~flash_attn_ext is NaN on this model's real activations~~ — **RETRACTED (2026-08-31
  external audit)**: the NaN was the repro's own staging bug — it staged Q as F16 while the
  CPU kernel reads Q as `const float*` unconditionally (4096 NaNs = 16 overflowed heads × 256).
  The graph never uses flash (flash_attn=false → manual MHA), but the flash staging with F32 Q
  was the better path and will be retried in the ATTN rewrite. The manual `fused_attn_qsa`
  used meanwhile is itself broken (see the rewrite section).
- **Current**: the complete fused decode runs all 8 validation steps without crashing or NaN;
  the per-step logit diff vs the graph is O(10). The same-position layer comparison
  (env-gated dumps) shows layer 0 differs by ~5.8 with identical inputs. The op-id mapping is
  corrected (aae8cae1d): the graph's layer-0 hc_mix runs the MANUAL build_hc_mix (no DSV4
  machinery — no hc_fn tensor), but its rms_norm passes the input through (norm ~1) and the
  gate is effectively 1 — the mixed = the input — while the fused's manual hc_mix (per-stream
  rms → lo/gate → mean) differs. **The first divergence is the hc_mix's rms_norm/gate
  behavior.**
- **The graph's step-1 rms_norm is identity-like** (b0edc7177): the batch decode's rms_norm
  output is properly normalized (-0.0309...), but the step-1's output equals the input exactly
  (norm ~1) — the fused's per-stream rms gives [0.965, 1.81, 1.54, 1.36]. The fused's hc_mix
  diverges at the very first rms_norm.
- **ROOT CAUSE found** (580e0e5ed): the graph's step-1 `hc_init` has DIFFERENT per-stream
  values (rms [0.451, 0.479, 0.153, 0.284]) — the graph's layer-0 input is NOT the embedding
  repeated 4× — while the fused path builds res_hc as 4 identical copies. The graph's rms_norm
  is identity on its input (gamma ≈ 1.05). The stream-dependent input is the root divergence.
- ~~ROOT CAUSE confirmed~~ (f36ea436c / 3fccd0ddf / ac4532bab / 2794abc7f) — **RETRACTED as a
  correctness bug by the 2026-08-31 external audit**: the gallocr mechanism is real (zero-size
  requests alias live free blocks without consuming them; input tensors are freed after last
  use; the gate scalar really overwrites the token's bytes — and the pre-fix allocator is
  byte-identical to upstream), but the graph's only consumer of inp_tokens is node 0 and the
  overwrite happens at node 144+ — nothing ever reads the corrupted bytes. The graph greedy was
  13 hours before the fix and 13 after; the fused path was the diverging side all along. The
  "evidence" was post-compute dumps of memory-reusing buffers (the instrumentation class the
  session had already declared unreliable). The patch changed the debugger's view, not the
  computation: NOT a correctness bug, do NOT upstream it as one; the graph-path validation
  stands. (The fused PLE n-gram predecessor-order fix in 2794abc7f was a genuine fused-side bug.)
- PLE component verification (a56a79cc0): token embed, rows, key, key_n, value are ALL
  graph==fused EXACT (verified via pre-compute eval-callback dumps; post-compute dumps
  read freed memory and were the source of the earlier phantom divergences).
- BREAKTHROUGH (e3ddf1583): the "query weight differs" theory (78922ed81) was IMPOSSIBLE and
  is RETRACTED — both paths dereference the same tensor object; the GGUF ground truth says
  blk.1.ple_norm_query.weight[0] = 0.8261719 (the fused value); the harness's "1.02417" was
  blk.0.hc_ffn_norm.weight[0] picked up by the pattern-matching eval callback latching onto the
  wrong MUL node. The fix in e3ddf1583 was right; the theory on the record was wrong. The
  real bugs — all fixed:
  1) conv windows (GDN ssm_conv + PLE dilated conv) are channel-major (tap k, channel i at
     i*ncs + k); the fused built them column-major (transposed state, wrong tap/channel pairing).
  2) the GDN q/k l2_norm normalizes per ne[0] column (per head); the fused normalized flat once.
  3) the PLE layer is ALSO recr: the graph runs the full GDN+ffn block after build_ple; the
     fused's else-if skipped it.
  Layers 0-2 now bit-exact (l_last 1.3e-7); greedy g=13 f=13 (was 89). Logit diff 7.2 starts
  at layer 3 = the first full-ATTN layer.
- ATTN REWRITE DONE (470730838): the ≥6 audit defects fixed — fused_rope now stages the
  graph's [n_embd_head, n_head] tensor (heads 6-23 were never roped); the q/k/v/wo lora
  scales restored (the pre-rope Q/K divergence); the attention replaced by the graph's OWN
  flash kernel staged with F32 Q (the earlier F16-Q staging was the NaN source — the audit
  was right; flash_attn defaults to AUTO in this tree, so the graph IS the flash path); the
  k/v stage builds AFTER the current-cell write (the pre-write stage read the stale cell —
  the actual source of the 1.2 attention diff); the current cell is attended; the indexer
  uses ratio[il] + the pooled/query ropes.
  Validation: attn_pregate/Qcur/Kcur/Vcur/gate/gated/wo EXACT (max_abs=0) at layers 3+7;
  layers 0-6 bit-exact (l_last 1.3e-7); greedy 13=13; logit diff 7.19 -> 0.684 (nmse 1.7e-2).
- Repack guard INVESTIGATED (79fceb05d): the expert types are all handled (up/gate IQ3_S
  plain, down IQ4_NL repacked-with-mirror or Q8_0 plain; verified via per-call dumps). The
  ~1.6e-4 routed diff at layer 7 traced to the layer-7 ffn-side hc_mixed (2.6e-4) — the
  input to moe2 — while the ffn-side xn is 6.7e-6 (the layer-7 res after the attn-combine;
  the inject/attn_out/res_in all exact). The amplification (6.7e-6 xn -> 2.6e-4 mixed -> 
  1.6e-4 routed -> 1.6e-4 l_last) is the remaining divergence chain — bisection continues
  (the res's 6.7e-6 source is the open question).
- CRASH FIXED (5c575e211): the deterministic crash was the "hc_mix w:" debug print (added
  during the repack investigation) — it evaluated ggml_type_name(w_inject->type)
  unconditionally, and the head's hc_mix is called with w_inject=nullptr — a NULL deref in
  the print, not in the compute. Isolated via the instrumentation-strip test (per the
  2026-08-31 audit follow-up): the gates→0 build passed, the bisect named the print. The
  user's ASAN-vacuity point is confirmed (GGML_SANITIZE_ADDRESS=OFF for libggml-cpu; both
  scratch overflows lived in that blind spot) — a sanitized ggml rebuild is queued before
  the next corruption hunt. Two genuine overflows were also fixed along the way: the flash
  staging's wdata (16 floats short of the kernel's 6976 need) and the GDN kernel's 3.2 MB
  state write past the ne-sized 24 KB scratch tensor. Current state: full-instrumentation
  runs exit 0, logit diff 0.684, greedy 13=13, layers 0-6 bit-exact, layer 7 at 1.6e-4.
- THE SEED FIXED (2c09c1e9e): the IQ4_NL repacked mirror must round PER-K, not per-block —
  the graph's ggml_gemv_iq4_nl_8x8_q8_0_generic accumulates sumf[j] += sumi_k * d * a per k;
  the mirror accumulated the whole sumi and did ONE product per block (~1e-8 rounding).
  With the per-k products: layers 0-11 are now EXACT (layer 7: 1.553e-4 -> 1.341e-7).
- Layer-12 bisection (b494e1599): the GDN body is exact; the ffn diverges via the same
  chain: the ffn-side xn 6.7e-6 (the norm's ~56x of the ~1.2e-7 res) -> the hc_mixed
  4.05e-4 (~60x) -> the up/gate dots 1.3e-3 -> the ffn_out 1.25e-4.
- Silu sites on the graph's SIMD kernels: the PLE conv silu (8f7bc6974 — logit 0.947 ->
  0.6335) and the GDN conv silu (96ec5827a, neutral) use ggml_vec_silu_f32 (the graph's
  ggml_v_silu/ggml_v_expf, 1.45-ulp). The ffn glu's SIMD-silu was NEGATIVE (reverted); the
  PLE gate's SIMD sigmoid was NEGATIVE (c9b0cc488, reverted).
- The ~1.2e-7 seed is still open — the PLE chain: the layer-0's l_last 1.49e-8 (the GDN)
  -> the PLE query_n 4.8e-7 (the norm ~32x) -> the gate dot 8.2e-8 -> the norm_conv 1.9e-6
  -> the padded 4.8e-6 -> the conv_out 1.34e-7 (unchanged by the SIMD silu) -> the l_last
  1.27e-7. Current: logit 0.660, greedy 13=13, layers 0-6 exact; the remaining candidates:
  the gate's dot (the key_n*query_n FMA vs the graph's mul+sum_rows), the query_n's norm,
  or the layer-0's GDN.
- Sequence: logit gate ≤1e-4 → Paris → arch suite stays; no perf claims before it passes.
  Then the honest baseline (uniform IQ4_XS requant control, ~12 min) + one symbol profile of
  the 46 ms non-gemv composition before Phase 4.
- SESSION-OWNED operational note (2026-09-01, operator-ruled, owned by this session):
  ~/.local/share/opencode/opencode.db is ~210 GB (the host's largest file, ~44% of the free
  space after yesterday's 435 GB reclaim; churning tens of GB, not a steady trend — three
  samples 186/224.9/210.3 GB). The plan, owned here: LEAVE ALONE while this session is live
  (held open by pid 433986, actively written). At a natural boundary — the INF-67 ≤1e-4
  gate or a /clear+close — run a maintenance window with the process stopped: back the DB
  up, then VACUUM (needs ~2× transient, only with the free space confirmed), and prune
  sessions only after the campaign's findings are committed, never mid-effort. The
  mechanism hypothesis (tool outputs stored verbatim per message — this campaign moved
  genuinely large artifacts) is worth knowing independently: every large tool output is
  paid for twice. No action taken; not deferred — operator-ruled, tracked here.
- **CLOSED 2026-09-02 — the premise no longer holds; no maintenance needed.** Ownership passed to
  the adhoc-audit session after the INF-67 session was closed. Measured on the live host:
  `/mnt/raid0/users/daniele/.local/share/opencode/opencode.db` is **315 MB**, not ~210 GB; the whole
  opencode tree is **403 MB** (`log` 73 MB, `snapshot` 5.8 MB, everything else under 1 MB). It is the
  ONLY `opencode.db` on the host, and no `.db` anywhere under `/mnt/raid0` exceeds 1 GB.
  - **A VACUUM would reclaim ~0.** `freelist_count = 0` and `auto_vacuum = 0` — the file is fully
    packed live data, no free pages. Occupancy: `event` 260 MB (82%), `part` 27 MB, `message` 21 MB.
  - **Therefore the shrink was not an in-place delete.** With `auto_vacuum` off, deleting rows leaves
    free pages behind; a zero freelist means the file was replaced or vacuumed, not merely pruned.
    Which of the two is NOT determined here — do not record a mechanism that was not observed.
  - **History survived**: 228 sessions spanning 2026-04-28 → 2026-09-02. The campaign-window days
    (08-29 → 08-31) hold no sessions, consistent with that data being what went; 09-01 (83) and
    09-02 (110) are present. The campaign's substance is in git regardless.
  - **Not acted on, deliberately**: a live `opencode` (pid 500205, a DIFFERENT devcontainer — the path
    resolves only via its mount namespace) holds the db/wal/shm open read-write. Nothing was killed,
    stopped or written; the DB was inspected via a throwaway copy. The operator's "no opencode
    sessions open" is true of THIS devcontainer, not of the host.
  - **Policy note for any future attempt**: that path is outside `/mnt/raid0/llm/`, so the filesystem
    containment guard blocks writes to it — real maintenance would need an explicit operator
    `EPYC_FS_ACK`, on top of stopping the holder.
  - **Residual risk: a watch item, not a task.** ~193 of the 228 sessions are from the last two days
    and the `event` table carries 82% of the bytes, so ordinary growth is ~100s of MB/day — immaterial
    against 736 GB free. The original 210 GB was real (three samples) and its mechanism was never
    confirmed, so if a single artifact ever again approaches tens of GB, re-measure before assuming
    the old hypothesis. Do not pre-build maintenance for it.
- SAFETY contract (audit item 3, before any serving exposure): the hook must become OPT-IN
  (today `GGML_FUSED_DECODE_OFF` is an opt-out with `supports_fused_decode()` unconditionally
  true and zero residency checks); all persistent state (PLE history, conv/ssm, KV cells)
  must commit atomically at end-of-token; the t_logits write relies on allocation-ordering
  luck; repack guards on tensor->extra + type; the debug I/O must be stripped before any
  perf measurement.

