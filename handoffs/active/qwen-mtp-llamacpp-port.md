# Qwen MTP llama.cpp Port (PR #22673 + #22400)

**Status**: active / WIP (created 2026-06-22). #22400 ported; #22673 reconciliation remaining.
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

## Constraints
- **Experimental repo only.** `verify_llama_cpp.sh` enforces production stays on `production-consolidated-v5`. Promotion to v5 is gated on a positive operator bench + (for MoE) clearing the MoE-on-CPU skepticism.
- The fork's untracked noise (`_libomp_src/`, `merged.profdata`, `*.sh`) is pre-existing — do NOT `git add -A` (it bloats commits; learned this session — staged 940 files by accident, fixed). Stage explicit paths.
- All bench numbers are observations until measured via the canonical recipe with operator approval on a quiesced host.

## Reference commits / PRs
- #22400 dependency: `4e732e0a6` (ported → `b139eba138`)
- #22673 MTP: `255582687` (remaining)
- #23398 gemma-4 MTP (mainline; our gemma4 path is the ik_llama #1744 lineage — alternative, not needed for Qwen)
- #18039 EAGLE-3 (deferred to MI210 / July per operator; our fork has the stub)

## Key files
- Branch: `/mnt/raid0/llm/llama.cpp-experimental` `feature/mtp-qwen36-port` (`git log` → `b139eba138`)
- Build: `cmake -B build && cmake --build build -j$(nproc)` (add `-DGGML_CUDA=OFF` for CPU-only)
- Upstream PR diffs: `git show 255582687` / `git show 4e732e0a6` (origin = ggml-org)
- Verify: `/workspace/scripts/session/verify_llama_cpp.sh`
