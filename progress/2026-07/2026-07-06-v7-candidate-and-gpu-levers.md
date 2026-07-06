# 2026-07-06 — v7-candidate kernel reconciliation + GPU speed levers (MTP-fp16, tree-draft Phase 1a)

Self-contained session log. All GPU/kernel work happened in the shared `llama.cpp`
worktrees (`/mnt/raid0/llm/llama.cpp*`); the branch built this session lives in
`llama.cpp-experimental` and is **NOT** touched by these commits — the commits below
are epyc-root governance/handoff/progress only. Autopilot ran concurrently (its own
progress files are separate). Two benches (aggregate throughput sweep + a GLM-5.2
investigation) are still in flight at wrap-up time.

## Headline — production-consolidated-**v7 candidate** built + validated

Created branch **`experimental-v7-candidate`** in `/mnt/raid0/llm/llama.cpp-experimental`
(built commit **`46f876c12`**, in the shared llama.cpp repo — NOT epyc-root). It is a
clean reconciliation of the two divergent optimization lines that had silently drifted
apart:

- **Base:** fresh production `production-consolidated-v6` = upstream framework + native
  MTP/NEXTN + our forward-ported CPU kernels + **iqk AVX-512 GEMM** (`GGML_IQK`) + Stage-2.
- **+ 4 gfx90a GPU opts** (from `upstream-mtp-verify` / `feature/tree-draft-v6`):
  `de447119f` MMVQ→MMQ Q8_0 verify-dispatch (+17.4% single-stream MTP),
  `5dc116130` nwarps 2→4 CDNA2 batch-1 Q8_0 GEMV (+4.6%),
  `7c28056b7` async weight-prefetch / LDS double-buffer, output byte-identical
  (`GGML_CUDA_Q8_PREFETCH`, default off, +3.3%),
  `496e2f098` bf16 GDN recurrent-state (`GGML_CUDA_GDN_STATE_BF16`, default off,
  +21.5% aggregate @B=32, PPL drift +0.0035%).
- **+ tree-draft** (DySpec `--spec-type draft-tree`, Phase 1a).

**Applied with ZERO merge conflicts**, then built + validated on HIP: iqk + all 4 GPU
opts + tree-draft all compile/link clean. This closed a **stale-fork bug**: the
experimental GPU-opts branch forked at `f8cc15f16` (2026-06-22), *before* iqk landed on
prod (2026-06-25), so it had silently been missing the entire iqk CPU GEMM subsystem.

### Why the two lines are cleanly separable (read-only audit)

Full audit: `handoffs/active/kernel-reconciliation-audit.md` (READ-ONLY, `git -C … ` only —
no commits/merges/builds/inference in that audit). Key findings:

- **Fork point** confirmed three ways: `f8cc15f16` is the exact merge-base of the
  experimental line and both prod-line tips (`a30214db1` v6, `0ebf1b4d7` mi210-hip).
- **Experimental was missing ~4 optimization/feature items from prod, ALL CPU-only /
  server-side, ZERO GPU-relevant:** dominated by the **iqk AVX-512 CPU GEMM subsystem**
  (7 commits, 40,541 insertions in `ggml-cpu/iqk/*`), plus Expected-Attention KV
  compaction (`3f9df4bd3`), an IMROPE guard relax (`00fe78602`), and a slot force-release
  fix (`60c270203`).
- **The GPU line (`ggml-cuda/*`) and the CPU line (`ggml-cpu/iqk/*` + `tools/server/*` +
  `src/llama-kv-*`) are disjoint.** The ONLY file touched by both is
  `ggml-cuda/vendors/hip.h` (fp8 ROCm≥6.3 guard), and it is **byte-identical on both
  sides** → a no-op conflict. Real v7 integration risk is therefore not merge conflict
  but the combined flag-set build/runtime interaction (`GGML_IQK` +
  `GGML_CUDA_Q8_PREFETCH` + `GGML_CUDA_GDN_STATE_BF16`).
- **Nothing valid is stranded.** Every landed optimization is committed on a real branch;
  the one uncommitted tracked diff on disk is DFlash (`llama.cpp-dflash`,
  `common/speculative.cpp` +130/−1), which is HELD/deferred and out of scope. The only
  non-resolving cited token (`a8afd338`) is a thread/session marker, not a git ref — its
  underlying optimizations all resolve to real commits.
- Reverted CPU work (CPU2 AVX-512BW repack, CPU1/CPU4 CCD threadpool, CPU paged-attention)
  is net-absent from prod too and was deliberately reverted; re-port from history for v7,
  not drop-in.

## Governance — experimental-kernel workflow + production-kernel immutability

Committed `a37fc7f5` (epyc-root). Added to `CLAUDE.md` a new **"Experimental Kernel
Workflow & Production-Kernel Immutability"** section + an `ENGINEERING_STANDARDS.md`
pointer, codifying: the 4-step kernel workflow, that `production-consolidated-v6` is
immutable (kernel R&D happens only in `llama.cpp-experimental`), and that a full build
must pass before any promotion. This is the policy the v7-candidate reconciliation
followed and validated in practice.

## Lever 2 — MTP on fp16 (Q8→F16 dequant proxy)

Committed `62081fd5` (matrix L8 D-16). Measured on Qwen3.6-27B (dense), MI210, using a
Q8→F16 dequant as an fp16 proxy:

| precision | MTP speedup | α | MTP abs t/s |
|---|---|---|---|
| **F16 (proxy)** | **+60.2%** | 66.9% (≈Q8) | 31.0 |
| Q8 (MMQ) | +15.6% | ~Q8 | **40.4** |

- **BW-bound hypothesis CONFIRMED:** MTP's speedup is ~4× larger on F16 than Q8 because
  F16 decode is far more bandwidth-bound (α essentially unchanged ⇒ the extra gain is pure
  BW-headroom, not better acceptance).
- **But F16 is a precision choice, not a throughput one:** F16-MTP absolute 31.0 < Q8-MTP-MMQ
  40.4. Q8 is quality-lossless here, so the **fp16 download is DEFERRED** — no throughput
  reason to hold fp16 weights.

## Tree-draft port — Phase 1a VALIDATED; lever uncompetitive vs embedded MTP

Committed `1d85e8f3`; full plan/result in `handoffs/active/tree-draft-forward-port-plan.md`.
Built the DySpec tree-draft engine into the v7-candidate (`46f876c12`) and A/B'd on
Qwen 27B dense Q8 (external 0.8B qwen35 drafter, temp 0.2 / seed 42,
`GGML_CUDA_Q8_PREFETCH=1`):

| arm | t/s | draft_n | accepted | α |
|---|---|---|---|---|
| plain | 31.17 | 0 | — | — |
| draft-simple (0.8B ext) | 18.60 | 235 | 176 | 0.749 |
| draft-TREE (greedy) | 17.42 | 235 | 176 | 0.749 |
| **MTP-incumbent (embedded)** | **41.89** | 252 | 170 | 0.675 |

- **Engine CORRECT:** draft-tree == draft-simple bit-for-bit (draft_n/accepted/α/output);
  the Phase-1a greedy-path collapse works exactly as designed. `--spec-type draft-tree`
  accepted, coherent output. Phase 1a milestone ACHIEVED.
- **NEGATIVE for MTP-equipped targets:** external-drafter spec-dec (simple AND tree) is
  net-negative vs plain (18 < 31) — the 0.8B drafter overhead isn't repaid on fast Q8
  decode. **Embedded MTP dominates** (41.9, +34% vs plain) because its head is near-free.
  Phase-1b's +15.8%-over-linear ⇒ ~21.5 t/s, still < plain and ≪ MTP.
- **Implication:** tree-draft can't beat MTP on our MTP-equipped production targets. Its
  only niche = non-MTP targets or f16 (more BW-bound decode). **Phase 1b decision
  REOPENED** (pending a GLM-5.2 MTP-head check) — not a hard close; f16 + a cheaper
  drafter remain untested.

## L22 baseline note + IN-FLIGHT aggregate re-bench (do not treat gemma numbers as final)

- `44ba27f3` clarified the L22 note: dense-27B ~29 t/s is the plain FA-isolation baseline,
  not achieved throughput.
- gemma Q8/Q4 aggregate was measured (gemma Q8 SS 25.29 / agg B32 246.86; Q4 SS 31.93 /
  agg 272.07) **on the OLD opt-less bench binary**. These are **NOT final** — the parent
  session is **re-benching all Q8 + F16 models on the v7-candidate right now** and will
  fold the corrected top-spec aggregate numbers into `fable5-window2-findings-05c-mi210-lever-category-matrix.md`.
  Do not persist the old gemma aggregate numbers as the matrix's final values.

## Deferred / in flight at wrap-up
- Aggregate throughput re-bench of all Q8+F16 models on the v7-candidate — **in flight**.
- GLM-5.2 MTP-head investigation — **in flight**; gates the tree-draft Phase-1b reopen.
- fp16 weight download — DEFERRED (Q8 quality-lossless).
- v7 promotion (build+test of the combined flag set on the immutable prod tree) — future,
  operator-gated; the candidate is validated but NOT promoted.

## Commits (epyc-root, this arc; most pre-committed before wrap-up)
| Commit | What |
|---|---|
| `46f876c12` | (in llama.cpp-experimental, NOT epyc-root) v7-candidate build: v6+iqk + 4 GPU opts + tree-draft |
| `a37fc7f5` | Governance: experimental-kernel workflow + production-kernel immutability |
| `62081fd5` | L8 D-16: MTP on F16 +60.2% (BW-bound confirmed); fp16 deferred |
| `1d85e8f3` | Tree-draft Phase 1a validated (engine correct); uncompetitive vs MTP |
| `44ba27f3` | Clarify L22 plain-FA-isolation baseline note |
