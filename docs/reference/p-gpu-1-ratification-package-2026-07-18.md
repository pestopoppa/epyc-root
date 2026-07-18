# P-GPU-1 Ratification Package - 2026-07-18

**Status**: prepare-only package for a human MEASUREMENT amendment. This document does not
ratify `P-GPU-1` and does not make any GPU number decision-grade.

## Current Authority

`/workspace/MEASUREMENT.md` still says:

- `P-GPU-1` is deferred.
- Required fields when ratified: `rocm-smi` clocks/power/temp before+after, warm-up policy,
  per-GCD memory residency check, host-side interference policy, reps as `P-BENCH-1`, and
  local-reproduction-only vendor-number rule.

`agents/shared/MEASUREMENT_POLICY.md` keeps MEASUREMENT edits inside the human/PR-reviewed
trust boundary. So the operator action is to amend MEASUREMENT; agents may only prepare this
package and map existing artifacts.

## Proposed Amendment Content

Protocol name: `P-GPU-1 — MI210 GPU canonical throughput`.

Required evidence fields:

1. **Hardware state**
   - GPU model, gfx target, ROCm runtime/driver, visible device id, and `llama-server --version`.
   - llama.cpp worktree clean/dirty state plus exact git commit.
   - `rocm-smi` clocks, power, temp, utilization, VRAM, and PID mapping before and after each run/window.
   - VRAM used before, during/after health, after request, and after cleanup.
2. **Host interference**
   - Explicit CPU stack state: quiesced, or declared non-quiesced with reason.
   - Active `llama-server`/AutoPilot/KFD PID checks before and after.
   - Whether CPU-only production stack is stopped, hidden from ROCm, or intentionally co-resident.
3. **Binary/model identity**
   - Exact llama.cpp worktree, branch, commit, binary path, `LD_LIBRARY_PATH`, and backend list.
   - Exact model path, mmproj path if relevant, quant, context, KV quant, reasoning/sampling flags,
     and spec-dec mode.
4. **Run recipe**
   - Warm-up policy.
   - Fresh server per rep unless the protocol explicitly declares resident-server mode.
   - Discard rules for warm-up reps and shape-change graph recapture.
   - Reps: same rule as `P-BENCH-1` (`n>=5` for >=5% claims, `n>=10` for <=2% claims).
   - Fixed prompt/task set, prompt tokens, generated-token floor, seed/sampling policy.
5. **Result grammar**
   - Report median and MAD for throughput plus prompt/decode split when available.
   - For spec-dec, report draft generated/accepted counters and acceptance rate.
   - For service/residency claims, report active-overlap tax and cleanup proof.
   - Vendor/web numbers may appear only as background narrative, never in a decision row.
6. **Decision boundary**
   - Until MEASUREMENT is amended, all MI210 numbers remain observations.
   - Retro-certification, if allowed by the operator amendment, must verify every required field
     exists in the artifact before changing claim status.

## Candidate Artifacts To Review For Retro-Certification

| Artifact | Current status | Notes |
|---|---|---|
| `data/k35_stack_context_matrix/frontdoor_pgpu1_candidate_20260718Tquiet/` | observation-grade candidate | Same-window CPU no-spec, MI210 no-spec, MI210 native-MTP, `n=5`, fresh-server reps, cleanup proof; frontdoor MI210 native MTP median `119.69 t/s` and `3835/3835` accepted drafts. |
| `data/k35_stack_context_matrix/frontdoor_context_edges_20260718Tcodex/summary.json` | observation-grade candidate | 2K/32K context-edge extension; MI210 native MTP `123.55/105.17 t/s`, no-spec `101.52/78.14 t/s`, CPU no-spec `21.63/10.15 t/s`. |
| `/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z/summary.json` | supporting memory artifact | Records non-vision memory sampler rows, including frontdoor MI210 VRAM and cleanup state. Useful for residency field validation. |
| `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/summary.json` | service-concurrency observation | Vision/frontdoor co-residency matrix; useful for active-overlap tax, not a frontdoor speed claim. |
| `/mnt/raid0/llm/tmp/k35-frontdoor-operational-1024-20260717T201842Z/summary.json` | supporting operational row | Optimized frontdoor MI210 operational row across 2K/8K/32K, cleanup proof. |

## Operator Decision Needed

1. Ratify `P-GPU-1` in `/workspace/MEASUREMENT.md` using the fields above, or edit the field
   list before ratification.
2. Decide whether existing complete artifacts may be retro-certified, or whether every
   decision-grade GPU claim must be rerun after the amendment.
3. If retro-certification is allowed, audit each artifact field-by-field before upgrading it
   from observation to claim.

Known retro-certification risk: the current Gate-R candidate artifact includes utilization,
VRAM, PID/memory samples, guard state, commands, plan, report, and cleanup proof, but it may
not contain a complete clocks/power/temp before+after record. If the ratified protocol keeps
those fields mandatory, the Gate-R candidate should rerun rather than be auto-upgraded.

Canonical-tree note: the current Gate-R candidate was run on experimental v7
`d1e5a20ebebe567f0da6bc64ca7ea7ecd521fc24`. The operator amendment should state whether
experimental-candidate measurements are acceptable for v7 promotion evidence, or whether
`P-GPU-1` requires a production-named kernel after promotion.
