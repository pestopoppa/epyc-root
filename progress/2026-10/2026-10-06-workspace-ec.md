# 2026-10-06 Wrap-up — workspace-ec

## Summary

Clerical wrap-up: added four groups of operator-approved tasks (10 total) to active handoffs, covering YaRN inertness research, copy-spec evaluation, belief-substrate adapters, and GPU serving backlog. Applied index state validation (`--check` exit 0). Ratified token-efficiency rules (e17a0cbdc) and FIFO region-lock review (d48b6b79 CHANGES-REQUESTED → APPROVED).

## Tasks added

1. **yarn-context-extension-research.md** (3 tasks):
   - YARN-INERT-PRIORART: prior-art audit to confirm YaRN SOTA and how other stacks avoid native-window regression
   - YARN-MSCALE-AB: 3-arm greedy A/B on mscale-neutral YaRN (no-YaRN / static / attn-factor-cancelled) on `llama.cpp-experimental/yarn-mscale-20261006`
   - YARN-OPTION-D-DECISION: decide between length-routed second server (D) and in-process per-request YaRN (A) after audit and mscale A/B

2. **speculative-decoding-mtp-refresh.md** (4 tasks):
   - COPYSPEC-P1: copy/prompt-lookup speculation re-evaluation, phase 1+2 full-host window
   - COPYSPEC-WIDTH: per-impl n_max change for v11 champion (never production)
   - COPYSPEC-27B: GPU 27B leg (ngram + DFlash2) after AK GPU run 2 frees MI210
   - COPYSPEC-RECIPE: on v11 promotion, update canonical :8070/:8083 recipes

3. **vidya-belief-substrate-program.md** (1 task):
   - VB-COPYSPEC: adapter for copy-spec results; re-grade 2026-07-30 ngram retraction scope (measured non-copy prompts only)

4. **gpu-serving-tie-in-program.md** (2 tasks):
   - KVU-16g: first-prompt TTFT cost attribution on GPU slot
   - YARN-E1-MEM: attribute +15 GiB KFD overshoot from long-prefill E1 arms

## Key artifacts and status notes

- **FIFO region-lock review (d48b6b79)**: CHANGES-REQUESTED → APPROVED. Default-off, deterministic control required before default-on.
- **YaRN inert design study** (OPTIONS.md in `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/`): root cause is mscale 1.0693 → 1.143× logit sharpening at all positions; cparams bug.
- **Copy-spec survey and plan**: phase 1 arms P / ngram-mod(n-min 4)+MTP / ngram-only / P2 on production-shaped prompt set.
- **GPU run-2 parking protocol** with workspace-89: `AK_GPU_RUN2_READY` / `AK_GPU_RUN2_PARKED` flags coordinate MI210 availability.
- **Token rules ratified (e17a0cbdc)**: codified recipes + canonical baseline protocol.

## Index validation

✅ `python3 scripts/handoffs/index_state.py --check` exit 0



## 2026-10-06 later

Results of the copy-spec, YaRN-inertness and K-shift/Jet-Long work. Evidence files were copied into `artifacts/` so the citations are durable.

### Files and repos

| Item | Repo / branch / commit | Evidence (durable copy) |
|---|---|---|
| COPYSPEC-P1 | llama.cpp tree, canonical :8070 | `artifacts/copyspec-20261006/p1-summary.md` |
| COPYSPEC-WIDTH | `llama.cpp-experimental-specwidth-20261006`, patch `defa269af`; champion candidate `bb5d98239` (champion `4348de400` + patch) | `artifacts/copyspec-20261006/width-summary.md`, `FOLD.md` |
| YARN-MSCALE-AB | `llama.cpp-experimental-yarn-mscale-20261006`, `720a98e2a` | `artifacts/yarn-ctx-20261006/yarn-mscale-ab-summary.md` |
| CTX-KSHIFT | `llama.cpp-experimental-kshift-probe-20261006`, tip `f9cb7cd32` | `artifacts/yarn-ctx-20261006/CTX2_KSHIFT.md` |
| CTX-JETLONG-COST | microbench, no kernel change | `artifacts/yarn-ctx-20261006/ctx3a/COST.md`, `results_20261006T054613Z.csv` |
| CTX-JETLONG-PROTO | `llama.cpp-experimental-jetlong-proto-20261006`, tip `b216a5deb` (impl `a2e129fcc`) | `artifacts/yarn-ctx-20261006/jetlong/{DESIGN,TESTS,LONGCTX_PLAN}.md` |
| Prior-art audit | n/a | `artifacts/yarn-ctx-20261006/OPTIONS.md` |
| KVU-16g plan | `experimental/prefill-budget-on-fold-20261004` @ `65d48a7a0` | `artifacts/yarn-ctx-20261006/PLAN_kvu16g.md` |
| Research intake (ctxext) | Stage 1 `7f4b5127f`; Stage 2 `71de724d1`, full-read redo `1c5183df9` (103 anchors); ledger `eac86a5f9`; Stage 4 `818841b22`; intake skill read-depth fix `4563f8d8e`; re-verification handoff EVL-51 `5ff7fdc55` | audit: 352 of 889 past dives at risk |

### COPYSPEC-P1 (CPU frontdoor Qwen3.6-35B-A3B-MTP Q8_0, canonical :8070, full host)

ngram-mod (n-min 4, cap 4) + MTP vs production:

| Set | Delta | Note |
|---|---|---|
| code edits | +5.25% | noise floor 0.40% |
| RAG | +0.84% | |
| all | +3.22% | |
| identity | 85/85 | ngram+MTP arm |

The ngram-only control diverged from production greedy output on 32/85 prompts (flag, filed as COPYSPEC-NO-DIVERGENCE). The "general" set was MCQ, so the prose control is invalid (COPYSPEC-SWEEP).

### COPYSPEC-WIDTH (per-impl ngram cap, patch `defa269af`)

| Set | cap 8 | cap 16 | Note |
|---|---|---|---|
| code edits | +14.06% | +20.50% | floor 3.26%; a failed GPU job overlapped the start |
| all 65 | | +13.09% | identity 65/65 |

Mean accepted ngram draft at cap 16 is about 16 on code edits, so the cap is saturating. Champion candidate `bb5d98239` builds on CPU and HIP (10341), linkage PASS. FOLD.md handed to workspace-89 for the regression gates.

### YARN-MSCALE-AB (CTX-1) — gate FAILS

Cancel factor 0.935190 (fix `720a98e2a`). Greedy identity vs no-YaRN: N 20/20, Y 13/20, YM 13/20. MTP acceptance at 34k: N 0.514, Y 0.490, YM 0.468. Drift comes from frequency interpolation, not mscale.

### CTX-KSHIFT (CTX-2) — H1, H2, H3 CONFIRMED at `ffc1bac82`

| Hypothesis | Site | Measure |
|---|---|---|
| H1 K-shift re-applies YaRN mscale | `llama-kv-cache.cpp:1992` | ratio 1.0693^n |
| H2 `pos_div` sign error | `llama-kv-cells.h:478` | err 4.711 vs 1.7e-6 |
| H3 q8_0 Hadamard nrot from full head dim | `llama-kv-cache.cpp:1454-1461` | 84.7x / 120.8x round-trip error; CPU quantized shift also aborts (`ggml-cpu/ops.cpp:323`) |

Fixes (tip `f9cb7cd32`) are unit-verified only; the H3 fix is marginal at 2.08x. Production is NOT exposed: v10 defaults ctx_shift=false and n_cache_reuse=0, and no production argv sets them. Gate G2 fails: K-shift is not usable as a re-rope primitive at v10.

### CTX-JETLONG-COST (CTX-3a) — PASS, measured

| Context | Uncached | Cached |
|---|---|---|
| 262K | +13.5 ms/step | +2.4 ms/step |
| 1M | +46 ms/step | +9.4 ms/step |

10 layers. About 9% uncached and 2% cached, but against EXTRAPOLATED baselines (143 ms at 262K, 500 ms at 1M), so the percentages are estimates.

### CTX-JETLONG-PROTO

T1 in-window max-abs exactly 0 (np 1, mixed np 4, co-batched with an above-native sequence; q8_0+Hadamard and f16). T2: f32 1.3e-6, f16 <=7.5e-5, q8_0 1.55e-3 (gated at 2x stock's own error). T3: cached == uncached exactly across 4 epoch changes. Limits: end-to-end wiring not run; above native needs `-ub 32` (1M prefill takes hours); f32 side cache about 5 GiB at 1M.

### YARN-E1-MEM — two attempts failed harmlessly (rc 3)

1. Parked under our own gpu-quiet exclusive hold, so the executor refuses to stop the server.
2. `gpu_window park` only writes the window file and never stops :8083. The correct path is `gpu_window_executor open`, which needs a `schedule.json` entry and a compute grant (60 min cap).

Static analysis predicts the +15 GiB is runtime growth, not YaRN (YaRN share about 0.7 GiB). Scripts in `/mnt/raid0/llm/tmp/gpu-backlog-20261006/`. KVU-16g is already built as a decode-aware prefill budget (`65d48a7a0`); the plan has an `-ub 1024` trade-off.

### Process incidents

- Two subagents ran read-only `pgrep` by name pattern (CLAUDE.md violation; nothing was killed).
- One subagent claimed a "REVISION 2" section it did not write.

### Handoff updates

Ticked: YARN-INERT-PRIORART, YARN-MSCALE-AB (FAIL verdict), CTX-KSHIFT, CTX-JETLONG-COST, COPYSPEC-P1, plus two sub-items (CTX-JETLONG-PROTO synthetic part, COPYSPEC-WIDTH implemented+measured). New tasks: YARN-ATTN-FACTOR-CARRY, KSHIFT-FIX-MODEL-TEST, JETLONG-LONGCTX-RUN, JETLONG-HARDEN, COPYSPEC-SWEEP, COPYSPEC-NO-DIVERGENCE, GPU-WINDOW-PARK-DOC, E1-MEM-RERUN-EXECUTOR (sub-task), VB-YARN-KSHIFT-AB, plus a champion-fold sub-task under COPYSPEC-WIDTH (owner workspace-89).
