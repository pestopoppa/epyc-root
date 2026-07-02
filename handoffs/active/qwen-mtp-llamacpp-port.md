# Qwen MTP llama.cpp Port (PR #22673 + #22400)

**Status**: cherry-pick BLOCKED, but the **fresh-upstream-build path is VERIFIED WORKING (2026-06-22)** — Qwen dense MTP runs on CPU at ~2× via a fresh `origin/master` build (see ✅ section below). #22400 ported (b139eba138). **#22673 cherry-pick is INFEASIBLE** — model-framework generation gap (see finding below). The cheap-port path is dead; landing Qwen MTP in *our fork* needs reimplementation, but standing up Qwen MTP at all is now a solved, proven operation via a fresh upstream build.

## ✅ Upgrade verified (2026-06-22) — fresh upstream build runs Qwen dense MTP on CPU

Per operator directive ("we're on llama.cpp-experimental for a reason — perform the upgrade and verify it works"), built a **fresh `origin/master`** (f8cc15f16, the new `llama_model_base` framework + #22673 MTP + EAGLE3) into `/mnt/raid0/llm/llama.cpp-experimental/build-upstream/` (branch `upstream-mtp-verify`) and ran a functional + speed verify on **dense Qwen3.5-9B-Q4_K_M** (in-GGUF NEXTN head, `qwen35.nextn_predict_layers` present):

| config | t/s | draft accept | output |
|---|---|---|---|
| baseline (no spec) | 14.90 | n/a | correct (25 primes listed + correct partial sums) |
| **`--spec-type draft-mtp --spec-draft-n-max 3`** | **29.30** | **184/211 = 87%** | correct, sensible |

- **`--spec-type draft-mtp` loads and is active**; 87% draft acceptance confirms the in-GGUF MTP head is healthy and well-matched. **1.97× speedup** on a dense 9B on CPU.
- Output **distribution-lossless, not byte-exact** (the two completions diverged at a temp-0 formatting near-tie — same property observed for gemma-4-31B MTP; expected from batched-verify FP rounding).
- **Caveat (the real decision input)**: this build is **upstream-master kernels — it does NOT carry our fork's NUMA/CPU optimizations**, so the absolute baseline (14.90 t/s) is *not* comparable to production throughput. The verified quantity is the **MTP multiplier (~2×) and that the path runs end-to-end**, not the absolute t/s. Whether to *deploy* via fresh-upstream (loses our kernels) vs reimplement in our fork (option 2) is now a real, data-backed fork — see options below.
- Reproduce: `build-upstream/bin/llama-server -m /mnt/raid0/llm/models/Qwen3.5-9B-MTP-GGUF/Qwen3.5-9B-Q4_K_M.gguf --port 8099 -t 96 -fa on -c 8192 [--spec-type draft-mtp --spec-draft-n-max 3]`, `taskset -c 0-95 numactl --interleave=all`, `LD_LIBRARY_PATH=/usr/lib/llvm-20/lib:$B/bin:$B/src:$B/ggml/src`. Script: `/mnt/raid0/llm/tmp/verify_qwen_mtp.sh`.

## ⛔ Port feasibility finding (2026-06-22) — cherry-pick is NOT viable

Attempted the full #22673 cherry-pick + resolved all 25 conflicts (spec subsystem adopted upstream cleanly: enum rename `DRAFT→DRAFT_SIMPLE` / `EAGLE3→DRAFT_EAGLE3` / `PART_BOUNDED→RS`, added `DRAFT_MTP`; dropped our experimental `tree`-spec — not production-critical). **The build then failed on a STRUCTURAL wall**, not enum/glue:

- **Our fork**: models use the old `struct llm_build_<arch> : public llm_graph_context` graph-builder pattern.
- **Upstream #22673**: models are `struct llama_model_<arch> : public llama_model_base` classes (`load_arch_hparams`/`build_arch_graph`/nested `graph`). This is a **major model-architecture refactor** that happened somewhere in the **~901 commits our fork is behind**; #22673's Qwen MTP graph is written against it.
- Result: `models.h:140 error: expected class-name before '{'` + every model class "does not have field `llama_model_base`" / "marked override but does not override" — the MTP graph code cannot be lifted into our `llm_build_*` framework. Confirmed: ours `struct llm_build_llama : public llm_graph_context` vs upstream `struct llama_model_llama : public llama_model_base`.

**Conclusion**: Qwen MTP (#22673) is **not portable to production-consolidated-v5 by cherry-pick.** The broken resolution was reverted; branch is back at the clean #22400 checkpoint.

### Realistic options (pick when there's a deployable Qwen MTP need — currently none, see refresh handoff)
1. **Use a FRESH upstream-master llama.cpp build** for any Qwen-MTP need (it already has the new model framework + MTP + EAGLE3). **✅ DONE + VERIFIED this session** (`build-upstream/`, branch `upstream-mtp-verify`): Qwen3.5-9B dense MTP runs at 87% accept / ~2×, correct output — see the ✅ section above. Cost: loses our fork's CPU/NUMA kernel optimizations → **not apples-to-apples for throughput** (the verified 14.9→29.3 t/s is on un-optimized upstream kernels), but trivial to stand up and now a proven path. **Recommended** for the low-ROI infra case / any one-off Qwen-MTP need.
2. **Reimplement the Qwen MTP graph in our `llm_build_qwen35*` idiom** (framework-aware translation of just the MTP nextn layer + the spec-dec driver). Moderate, focused — but only worth it if a Qwen MTP model becomes deployable (none is: gemma-4-31B/Qwen3.5-9B are Pareto-dominated; Qwen3.6-MoE-MTP is dead on CPU).
3. **Rebase/catch-up the fork ~901 commits to adopt upstream's model framework** — large, separate effort; out of scope for MTP alone.

**#22400 (GDN seq_rm) note**: its commit was resolved forward-compat toward #22673 so it does NOT build standalone (references `DRAFT_MTP`). Since #22673 is shelved, if the GDN backend is ever wanted standalone, re-cherry-pick #22400 resolving its 2 conflicts to the OURS side (drop the MTP-context glue). No current consumer.
**Categories**: speculative_decoding, hardware_optimization, local_inference
**Parent**: [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) · [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Work location**: `/mnt/raid0/llm/llama.cpp-experimental`, branch `feature/mtp-qwen36-port` (NEVER production `/mnt/raid0/llm/llama.cpp`).

## Objective

Land mainline llama.cpp Qwen MTP self-speculation (`--spec-type draft-mtp` / `--spec-draft-n-max`) in our fork so we can run the native NEXTN/MTP heads for **Qwen3.6-35B-A3B** (frontdoor/coder) and dense **Qwen3.5-9B** on CPU. Our `production-consolidated-v5` has no Qwen MTP path (`--spec-type` = ngram-only; EAGLE3 is an inert `// TODO PR-18039` stub).

> **GATING**: do NOT invest the full #22673 reconciliation until the **gemma-4-31B dense gate-bench (T1 in the parent handoff)** shows CPU MTP actually delivers on a dense model. Qwen3.6 is pure-MoE-A3B (worst CPU-MTP case; 26B-A4B measured only 1.06×). The dense bench is the cheap proof-point that justifies this port. This handoff is the "how", staged behind that "whether".

## Current state (verified 2026-06-22)

- Branch `feature/mtp-qwen36-port` created from a **fresh `production-consolidated-v5`** (a6c793fc66, = production HEAD), per operator instruction (keeps our CPU/NUMA optimizations apples-to-apples for the eventual bench).
- **PR #22400 (`4e732e0a6`, GDN partial seq_rm — the dependency): PORTED.** Commit `b139eba138`. 26/28 files auto-merged; 2 conflicts (`tools/server/server-context.cpp`, `tests/test-backend-ops.cpp`) resolved to the upstream side (new GDN 3-D delta-net state + MTP-aware draft-context path). **Does NOT build standalone** — server-context.cpp now references the newer speculative API (`COMMON_SPECULATIVE_TYPE_DRAFT_MTP`, `LLAMA_CONTEXT_TYPE_MTP`) that #22673 provides.
- **PR #22673 (`255582687`, MTP support): NOT yet applied.** Cherry-pick measured **25 conflicted files** (19 auto-merge clean). Aborted rather than commit a broken half-merge.
- Production fork untouched (`verify_llama_cpp.sh` PASSED).

## Root cause of the conflicts (read before resuming)

Our fork's speculative subsystem is an **older API generation** than PR #22673's base. Our fork carries: an EAGLE3 scaffold (`COMMON_SPECULATIVE_TYPE_EAGLE3` + state struct, gated off by `has_draft_eagle3=false // TODO PR-18039`), tree/DySpec speculation, the ngram family, and the gemma4 external-MTP tooling (`tools/mtp-speculation/`, `tools/mtp-acceptance/`). Upstream #22673 introduces the `DRAFT_MTP` speculative type + `LLAMA_CONTEXT_TYPE_MTP` + `--spec-type draft-mtp` + per-model MTP graph/loader on a **refactored** `common/speculative.{cpp,h}`. So the merge isn't textual — it's reconciling two speculative-API designs **without breaking our existing EAGLE3/tree/ngram/gemma4 paths**. That is the real work; it is a focused multi-session hand-merge + compile-iterate, **not** a 5-minute cherry-pick and **not** "2-4 weeks of catastrophe."

## #22673 conflict map (25 files)

**Core spec-dec subsystem (the hard part — hand-merge, preserve our paths):**
`common/speculative.cpp` (+1980 lines upstream), `common/speculative.h`, `common/arg.cpp` (the `--spec-type` enum + `--spec-draft-n-max`), `common/common.cpp`, `common/common.h`, `include/llama.h` (MTP APIs: `llama_decode_mtp`, `llama_get_logits_mtp`, `LLM_GRAPH_TYPE_*_MTP`), `src/llama-context.cpp`, `src/llama-cparams.h`, `src/llama-ext.h`.

**Model + arch (MTP graph/loader for Qwen):**
`src/models/qwen35.cpp`, `src/models/qwen35moe.cpp`, `src/models/delta-net-base.cpp`, `src/models/models.h`, `src/llama-arch.cpp`, `src/llama-arch.h`, `src/llama-memory-recurrent.cpp`.

**Backend / conversion / docs:**
`ggml/include/ggml.h`, `ggml/src/ggml-backend-meta.cpp`, `ggml/src/ggml-cuda/gated_delta_net.cu` (CUDA — N/A for our CPU build but resolve to compile), `conversion/base.py`, `conversion/qwen.py` (MTP metadata: `nextn_predict_layers`), `tools/cli/README.md`, `tools/completion/README.md`, `tools/server/README.md`, `tools/server/server-context.cpp`.

## Remaining tasks

- [ ] **P1** Reconcile `common/speculative.{cpp,h}`: merge upstream's `DRAFT_MTP` state machine INTO our version, keeping our EAGLE3 scaffold + tree/DySpec + ngram + suffix paths intact. This is the keystone — most other files follow once the type/enum + state class exist.
- [ ] **P2** `common/arg.cpp`: extend `--spec-type` enum to include `draft-mtp` (alongside our existing `none|mtp|ngram-*|suffix`); add `--spec-draft-n-max`. Note our fork already has a `mtp` spec-type (gemma4 external) — disambiguate `mtp` (gemma4 external assistant head) vs `draft-mtp` (in-GGUF NEXTN self-draft) or unify.
- [ ] **P3** `include/llama.h` + `src/llama-context.cpp` + `src/llama-cparams.h`: add the MTP context type + decode/logits MTP APIs; reconcile with our context lifecycle.
- [ ] **P4** `src/models/qwen35.cpp` / `qwen35moe.cpp` + `src/llama-arch.*` + `conversion/qwen.py`: the Qwen MTP graph (nextn layer) + metadata loader.
- [ ] **P5** Resolve the remaining backend/test/doc files to compile; `cmake -B build && cmake --build build -j$(nproc)` (CPU: `-DGGML_CUDA=OFF`).
- [ ] **P6** Verify: `llama-server --help` / `llama-speculative --help` show `--spec-type draft-mtp` + `--spec-draft-n-max`; load a `unsloth/Qwen3.6-35B-A3B-MTP-GGUF` (operator-gated load). Then the gate-benches (parent T3/T4).
- [ ] **P7 (optional, post-#22673): FR-Spec draft LM-head vocab-trim** (intake-740). Restrict the native-MTP draft LM-head projection to a frequency-ranked top-32,768 subset of the 248,320 vocab (target verifies full vocab) → **lossless (byte-identical at temp=0)**, cutting the draft-head `mul_mat_vec_q` kernel ~85%. Verified upstream on `qwen35.cpp` (this port's P4 target); ~30 lines reusing `eagle3.cpp` d2t + `ggml_set_rows`. CAVEATS: (a) our fork's EAGLE3 is an **inert stub** (`// TODO PR-18039`), so the d2t machinery may not exist in-fork — this likely **rides the #22673 reconciliation, not free**; (b) build an **EPYC-workload-matched frequency map** from our own coder/prose traffic (the author's code-tuned map regressed prose); (c) expect only **+1-3% end-to-end** on BW-bound decode despite the −85% kernel cut → measure end-to-end before adopting.

## Constraints
- **Experimental repo only.** `verify_llama_cpp.sh` enforces production stays on `production-consolidated-v5`. Promotion to v5 is gated on a positive operator bench + (for MoE) clearing the MoE-on-CPU skepticism.
- The fork's untracked noise (`_libomp_src/`, `merged.profdata`, `*.sh`) is pre-existing — do NOT `git add -A` (it bloats commits; learned this session — staged 940 files by accident, fixed). Stage explicit paths.
- All bench numbers are observations until measured via the canonical recipe with operator approval on a quiesced host.

## Reference commits / PRs
- #22400 dependency: `4e732e0a6` (ported → `b139eba138`)
- #22673 MTP: `255582687` (remaining)
- #23398 gemma-4 MTP (mainline; our gemma4 path is the ik_llama #1744 lineage — alternative, not needed for Qwen)
- #18039 EAGLE-3 (deferred to MI210 / July per operator; our fork has the stub)
- FR-Spec-for-MTP (intake-740): llama.cpp **issue #25187**; author branch `avifenesh/llama.cpp` commit `047bfa508`; underlying FR-Spec = **arXiv 2502.14856** (ACL 2025, thunlp)

## Key files
- Branch: `/mnt/raid0/llm/llama.cpp-experimental` `feature/mtp-qwen36-port` (`git log` → `b139eba138`)
- Build: `cmake -B build && cmake --build build -j$(nproc)` (add `-DGGML_CUDA=OFF` for CPU-only)
- Upstream PR diffs: `git show 255582687` / `git show 4e732e0a6` (origin = ggml-org)
- Verify: `/workspace/scripts/session/verify_llama_cpp.sh`
