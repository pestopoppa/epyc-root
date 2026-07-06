# Kernel Reconciliation Audit — GPU-opts line vs prod/bench line (pre-v7)

**Date:** 2026-07-06
**Scope:** READ-ONLY audit of optimization divergence in the shared `llama.cpp` repo (common git dir `/mnt/raid0/llm/llama.cpp/.git`), so nothing valid is stranded before the eventual **production-consolidated-v7** reconciliation.
**Method:** `git -C <worktree> …` only. No commits, merges, branch switches, builds, or inference. All queries run against worktree `/mnt/raid0/llm/llama.cpp-experimental` (sees all branches).
**Concurrency note:** a subagent is editing `feature/tree-draft-v6` and a GPU bench may be running — this audit touched no state.

---

## 0. TL;DR

- **Fork point confirmed:** `f8cc15f163e784c58fe13aee58ebc03055bb0c40` (2026-06-22, "[SYCL] support bf16 on bin_bcast…") is the exact merge-base of the experimental line and BOTH prod-line tips.
- **Nothing valid is at risk of being LOST.** Every landed optimization on both lines is committed on a real branch. The only "saved-not-committed" patch referenced in the campaign notes is the **fused-prefetch extension, which is a FALSIFIED regression** (−1.8%/−13%) — no `*.patch` file exists for it and nothing of value is stranded.
- **Experimental kernel is missing exactly one optimization family from prod: the iqk AVX-512 CPU GEMM subsystem (7 commits, 40,541 insertions), plus one server feature (Expected-Attention KV compaction) and two small CPU/server fixes.** All are **CPU-only / server-side — ZERO are GPU-relevant.**
- **The two lines are cleanly separable.** Experimental = `ggml-cuda/*` (GPU). Prod = `ggml-cpu/iqk/*` + `tools/server/*` + `src/llama-kv-*` (CPU/server). The **only** file touched by both is `ggml/src/ggml-cuda/vendors/hip.h`, and that change is **byte-identical on both lines** (fp8 ROCm≥6.3 guard) → a no-op conflict.

---

## 1. Branch inventory

Fork point (merge-base) verified three ways:
- `merge-base 496e2f098 0ebf1b4d7` = `f8cc15f16` ✓
- `merge-base 496e2f098 a30214db1` = `f8cc15f16` ✓
- `f8cc15f16` is-ancestor of both experimental and mi210 ✓

| Branch / worktree | Tip hash | `rev-list --count f8cc15f16..tip` | One-line purpose |
|---|---|---|---|
| `production-consolidated-v6` (prod) | `a30214db1` | **19** | Production kernel: v6 forward-ports + iqk subsystem + fp8 guard |
| `mi210-hip-enable` (bench build) | `0ebf1b4d7` | **19** | =v6 with its own fp8-guard tip commit; MI210/ROCm6.2 build line |
| `upstream-mtp-verify` (GPU-opts base) | `496e2f098` | **4** | Experimental GPU-opts base |
| `feature/tree-draft-v6` (this session) | `496e2f098` | **4** | **Identical hash to upstream-mtp-verify** — subagent has no committed divergence yet |
| `iqk-port` (worktree v6-iqk) | `91745611f` | (ancestor of v6/mi210) | iqk Stage-2 tip; fully contained in prod line, no unique work |
| `f1-paged-attn` (worktree v6-f1) | `112022a0b` | — | Paged-attn line (paged-attn was reverted on v6; separate experiment) |
| `feature/dflash-speculation` (worktree dflash) | `1ba2140c5` | — | DFlash speculation (HELD); see §3 for uncommitted change |

**mi210-hip-enable vs production-consolidated-v6:** they diverge by exactly **1 commit each way** (merge-base `4412872cac`). Both unique commits are the *same* fp8-guard change with **identical subject** ("hip: guard OCP fp8 typedefs behind ROCm>=6.3") but different hashes (`0ebf1b4d7` on mi210, `a30214db1` on v6) — the guard was committed twice on divergent parents. Harmless duplicate; for v7 pick one. Otherwise mi210 ≡ v6 for reconciliation purposes.

---

## 2. Optimization gap-list (BOTH directions)

### 2A. On experimental (`496e2f098`) but NOT on mi210/v6 — 4 commits, ALL net-live

All four are **GPU kernel/perf optimizations**, all in `ggml-cuda`, all runtime-gated + operator-gated for prod, all "numerically-valid-not-bit-exact" (two are byte-identical/near-zero-drift):

| Commit | Class | Perf (from commit body) | Files | Gate flag |
|---|---|---|---|---|
| `de447119f` | kernel/perf | **+17.4%** single-stream MTP (MMVQ→MMQ route for Q8_0 verify batches ne11≤1) | `mmvq.cu`, `hip.h` | (dispatch heuristic) + fp8 guard |
| `5dc116130` | kernel/perf | **+4.6%** batch-1 Q8_0 GEMV (nwarps 2→4, CDNA2) | `mmvq.cu` | (compile heuristic) |
| `7c28056b7` | kernel/perf | **+3.3%** async weight-prefetch / LDS double-buffer; output **byte-identical** | `mmvq.cu` (+207/-0) | `GGML_CUDA_Q8_PREFETCH` (default off) |
| `496e2f098` | kernel/perf | **+21.5% aggregate @B=32** bf16 GDN recurrent-state; drift PPL +0.0035% | `gated_delta_net.cu`, `ggml.h`, `ggml.c`, `llama-graph.cpp`, `llama-model.cpp`, `models/qwen35*.cpp`, `models/qwen3next.cpp`, `models/delta-net-base.cpp` | `GGML_CUDA_GDN_STATE_BF16` (default off) |

These 4 are the GPU-opts the prod/bench line lacks. Confirmed present on the experimental line via `git cat-file`.

### 2B. On mi210/v6 but NOT on experimental (`496e2f098`) — 19 commits

Classification (net effect after in-line reverts):

**NET-LIVE optimizations / features the experimental kernel is missing:**

| Commit(s) | Class | Significance | Subsystem |
|---|---|---|---|
| `fec061dea`, `060977240`, `2fdb4f97d`, `715383cde`, `c9bf4dad4`, `170f57af9`, `91745611f` | **kernel/perf — WHOLE SUBSYSTEM** | **iqk AVX-512 CPU GEMM port** (ik_llama Q4_K/Q8_0/K-quant/legacy-quant GEMM). **40,541 insertions across 30 files** in `ggml/src/ggml-cpu/iqk/*`. Includes crash fix (`715383cde` type_traits OOB), prefill-starvation fix (`c9bf4dad4` stop CPU_REPACK starving the hook), and MoE `mul_mat_id` hook + legacy-Q8_0 coverage for the Qwen frontdoor. Flag-gated `GGML_IQK`. Historical perf: +18–30% CPU quantized decode. | `ggml-cpu` (CPU) |
| `3f9df4bd3` | feature/perf | **Expected-Attention KV compaction** forward-port (624 insertions). New `src/llama-kv-compress.{cpp,h}` (417-line impl) + `tools/server/*` wiring. | server / `src/llama-kv-*` (CPU) |
| `00fe78602` | correctness | Relax IMROPE seq_add/seq_div/K-shift guards for qwen35 hybrids (9 lines) | `src/llama-kv-cache.cpp` (CPU/model) |
| `60c270203` | bugfix | Force-release processing slot on erase + notify HTTP handler (13 lines) | `tools/server/server-context.cpp` |
| `0ebf1b4d7` | build fix | fp8 ROCm≥6.3 guard (`hip.h`) — **but experimental ALREADY carries the identical guard folded into `de447119f`** → duplicate, not truly missing | `hip.h` |

**DOC (not optimizations):** `4412872ca`, `cc29b7a6a` (readiness-index docs; also touch `handoffs/active/master-handoff-index.md`, `docs/epyc-llama-readiness-index.md`).

**REVERTS — attempted-then-reverted CPU forward-ports (NET-ABSENT on prod too; recoverable from history, NOT stranded):**

| Added | Reverted by | What |
|---|---|---|
| `814e81782` (v6 Stage 1a) | `358f0c748` | CPU2 AVX-512BW repack kernels |
| `c159997e0` (v6 Stage 1b) | `7c88df85a` | CPU1/CPU4 CCD threadpool (3-way merged, EP excised) |
| `0e485a91b` (v6 F1) | `a4e2b4f86` | CPU paged-attention forward-port |

These three CPU optimizations were forward-ported onto the v6 framework then deliberately reverted — they are **net-absent from prod as well**, so the experimental line "missing" them is moot. For a v7 that wants them, they live in history (`git show <hash>`), but they were reverted for a reason (integration issues) — treat as re-port candidates, not drop-in.

**Bottom line for 2B:** the experimental kernel is missing **~4 optimization/feature items** — dominated by the **iqk CPU GEMM subsystem** — and **every one is CPU-only or server-side. None are GPU-relevant.** The GPU-opts and prod-CPU-opts are on opposite sides of the tree.

---

## 3. Uncommitted / stranded-work sweep (every worktree)

`git status --porcelain` + `git stash list` run on all 8 worktrees.

**Stashes:** the stash list is shared across all worktrees (shared object store) — 11 entries, ALL old/unrelated WIP (kv-cache f32 cast, hadamard-kv, Phase-8 replay, ttt, paged-attention, lookahead, mtp-branch, parallel-repack, layer-skip, eagle). **None correspond to the current GPU/iqk campaign.** No stash holds a stranded kernel optimization.

**Modified tracked files:**
- `/mnt/raid0/llm/llama.cpp-dflash` (`feature/dflash-speculation`): **` M common/speculative.cpp` (+130/-1 lines)** — genuinely uncommitted tracked work. This is **DFlash speculation, which the campaign explicitly marks HELD/deferred** (CPU-only, block-mode τ≈0, taps never wired into qwen35.cpp). Out of scope for the v7 *kernel* reconciliation, but flagged as the **one real piece of uncommitted tracked code** on disk. If DFlash is ever revived, this diff must be committed or it will be lost on a worktree cleanup.
- All other worktrees: only untracked scratch (`v5_bolt*.sh`, `v5_pgo_profile.sh`, `.gitnexusignore`, `tools/math-tools/`) — junk per the ignore rules.
- **`feature/tree-draft-v6` (the actively-edited worktree): NO modified tracked files** — only untracked `v5_bolt*.sh` scratch. The subagent's tip equals `upstream-mtp-verify` (`496e2f098`); its in-progress work is either already committed at the tip or not yet written to tracked files.

**Saved patch/diff files:** `find … -name '*.patch' -o -name '*.diff'` across all worktree roots (maxdepth 3, build dirs excluded) and `git ls-files '*.patch' '*.diff'` → **ZERO files.** The campaign's referenced "fused-prefetch patch saved, not committed" and "compact-LDS patch":
- The **compact-LDS / async-prefetch work IS committed** as `7c28056b7` (`GGML_CUDA_Q8_PREFETCH`).
- The **fused-path *extension* is a FALSIFIED negative result** (−1.8% @ full occupancy / −13% naive — the large FFN GEMVs are already wave-pipelined). No file exists for it; **nothing of value is stranded** even though the notes say "patch saved, not committed."

---

## 4. Cross-check vs claimed optimizations

Sources skimmed: `handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md` and `progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md`. Every hash-like token extracted and run through `git cat-file -t` across all repos.

| Cited token | Resolves? | Where | Claim | Verdict |
|---|---|---|---|---|
| `de447119f` | ✓ commit | llama.cpp (exp) | MMVQ→MMQ +17.4% LANDED | **VERIFIED** |
| `5dc116130` | ✓ commit | llama.cpp (exp) | nwarps=4 +4.6% committed | **VERIFIED** |
| `7c28056b7` | ✓ commit | llama.cpp (exp) | async-prefetch +3.3% LANDED | **VERIFIED** |
| `496e2f098` | ✓ commit | llama.cpp (exp tip) | bf16 GDN-state +21.5% BUILT+GO | **VERIFIED** |
| `0ebf1b4d7` | ✓ commit | llama.cpp (mi210 tip) | mi210 build tip | **VERIFIED** |
| `5879129b` | ✓ commit | **epyc-root** (not llama.cpp) | "drop -md double-load" production CPU fix "briefed" | **VERIFIED** — it is a *briefing-doc* commit in the governance repo, not a kernel change. Correctly described as "briefed," not "landed in llama.cpp." No lost work. |
| `a8afd338` | ✗ **NOT A COMMIT IN ANY REPO** (llama.cpp, orchestrator, research, root, workspace) | — | Used as "the Q8-dequant/MFMA kernel thread"/"reconciliation"/"when a8afd338 frees the GPU" | **FLAG (benign).** This is used as a **session / GPU-lease / thread marker, not a landed-commit claim.** The optimizations attributed to that thread all resolve to real commits (`de447119f`, `5dc116130`, `7c28056b7`, `496e2f098`), so **no optimization is lost** — but the token itself dereferences to nothing. If any process treats it as a git ref it will fail. |

**No claimed-landed optimization is missing from git.** The only non-resolving token (`a8afd338`) is a thread label whose underlying commits all exist.

---

## 5. Reconciliation summary (for a v7 that must contain "everything")

| What | From branch | Commits | Subsystem | Conflict risk |
|---|---|---|---|---|
| iqk AVX-512 CPU GEMM subsystem | `mi210-hip-enable` / `production-consolidated-v6` | 7 (`fec061dea`…`91745611f`) | `ggml-cpu/iqk/*`, `ggml-cpu.c`, `ggml-common.h`, `ggml-cpu-impl.h`, `ggml-cpu/CMakeLists.txt`, `repack.cpp` | **None vs GPU line** |
| Expected-Attention KV compaction | v6/mi210 | 1 (`3f9df4bd3`) | `src/llama-kv-compress.*`, `src/CMakeLists.txt`, `tools/server/*` | **None vs GPU line** |
| IMROPE guard relax + slot force-release | v6/mi210 | 2 (`00fe78602`, `60c270203`) | `src/llama-kv-cache.cpp`, `tools/server/server-context.cpp` | **None vs GPU line** |
| 4 gfx90a GPU opts | `feature/tree-draft-v6` / `upstream-mtp-verify` | 4 (`de447119f`, `5dc116130`, `7c28056b7`, `496e2f098`) | `ggml-cuda/mmvq.cu`, `ggml-cuda/gated_delta_net.cu`, `ggml.h`, `ggml.c`, `src/llama-graph.cpp`, `src/llama-model.cpp`, `src/models/qwen3*` | **None vs CPU line** |
| fp8 ROCm≥6.3 guard | either (identical on both) | 1 | `ggml-cuda/vendors/hip.h` | **only overlap; byte-identical → auto-resolves** |

**Overlap analysis** (`git diff --name-only f8cc15f16 <exp> ∩ <prod>`): the intersection of the two lines' net file-sets is exactly **`{ggml/src/ggml-cuda/vendors/hip.h}`**, and the diff on that file is **identical** (blob `a6115cd80` → `6d6eb2ee6` on both sides). Even the CMake surfaces don't collide (prod touches `ggml-cpu/CMakeLists.txt` + `src/CMakeLists.txt`; experimental touches neither). `src/` overlaps are also disjoint (experimental: `llama-graph.cpp`, `llama-model.cpp`, `models/*`; prod: `llama-kv-cache.cpp`, `llama-kv-compress.*`).

**Hardest expected conflict surface:** there is **no structural textual conflict** — the GPU (`ggml-cuda`) and CPU (`ggml-cpu/iqk` + server) subsystems are disjoint. The single shared file (`hip.h`) is a no-op. The real v7 integration risk is therefore **not merge conflict** but (a) the fp8-guard being committed 3× (once on experimental folded into `de447119f`, once each on mi210/v6) — dedupe on merge; and (b) **runtime/build interaction of the combined flag set** (`GGML_IQK` + `GGML_CUDA_Q8_PREFETCH` + `GGML_CUDA_GDN_STATE_BF16` coexisting) — a build+test concern outside this read-only audit's scope.

**Reverted CPU work** (CPU2 AVX-512BW repack, CPU1/CPU4 CCD threadpool, CPU paged-attention) is net-absent from prod and was deliberately reverted; if v7 wants it, re-port from history (`814e81782`, `c159997e0`, `0e485a91b`) — do not treat as drop-in.

---

## Appendix — commands used (all read-only)

- `git -C … worktree list`, `branch -a --format`, `merge-base [--is-ancestor]`, `rev-list --count`, `log --oneline --no-merges A..B`, `show --stat`, `diff --name-only`, `diff --stat`, `status --porcelain`, `stash list`, `cat-file -t`, `ls-files`.
- No `checkout`, `commit`, `merge`, `stash push/pop`, build, or inference issued.
