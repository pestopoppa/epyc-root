# P-GPU-1 Ratification Package - 2026-07-18

**Status**: historical ratification package and current certification map. `P-GPU-1` was
ratified by human amendment in `/workspace/MEASUREMENT.md` on 2026-07-19. This package
does not itself make any GPU number decision-grade; MEASUREMENT is the authority.

## Current Authority

`/workspace/MEASUREMENT.md` now says:

- `P-GPU-1` is ratified as `P-GPU-1 — MI210 GPU canonical throughput`.
- Decision-grade `P-GPU-1` claims may only be produced on a production-named kernel
  (`production-consolidated-vN`).
- Experimental/candidate/fork kernel rows, including `llama.cpp-experimental` and
  `experimental-v7-*`, are observation-only and must not gate promote/revert/deploy decisions.
- Required fields include GPU/ROCm/binary/model identity, `rocm-smi` clocks/power/temp/util/VRAM/PID
  before and after, CPU stack interference policy, warm-up/discard policy, reps as `P-BENCH-1`,
  prompt/decode/draft stats, cleanup proof, and attestation.

`agents/shared/MEASUREMENT_POLICY.md` keeps MEASUREMENT edits inside the human/PR-reviewed
trust boundary. So the operator action is to amend MEASUREMENT; agents may only prepare this
package and map existing artifacts.

Prepared amendment text lives at
`docs/reference/p-gpu-1-amendment-draft-2026-07-19.md`. That file is historical draft
material; `/workspace/MEASUREMENT.md` is the only ratification source.

## Ratified Protocol Summary

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
   - Experimental/candidate/fork kernel numbers remain observations.
   - Retro-certification is allowed only for artifacts produced on production-named kernels with
     every mandatory field present.
   - Existing experimental-v7 Gate-R/K35/AXA rows cannot be upgraded to decision-grade
     `P-GPU-1` claims because the ratified kernel-provenance rule excludes them.

## Candidate Artifacts To Review For Retro-Certification

| Artifact | Current status | Notes |
|---|---|---|
| `data/k35_stack_context_matrix/frontdoor_pgpu1_candidate_20260718Tquiet/` | observation-grade candidate | Same-window CPU no-spec, MI210 no-spec, MI210 native-MTP, `n=5`, fresh-server reps, cleanup proof; frontdoor MI210 native MTP median `119.69 t/s` and `3835/3835` accepted drafts. |
| `data/k35_stack_context_matrix/frontdoor_context_edges_20260718Tcodex/summary.json` | observation-grade candidate | 2K/32K context-edge extension; MI210 native MTP `123.55/105.17 t/s`, no-spec `101.52/78.14 t/s`, CPU no-spec `21.63/10.15 t/s`. |
| `/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z/summary.json` | supporting memory artifact | Records non-vision memory sampler rows, including frontdoor MI210 VRAM and cleanup state. Useful for residency field validation. |
| `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/summary.json` | service-concurrency observation | Vision/frontdoor co-residency matrix; useful for active-overlap tax, not a frontdoor speed claim. |
| `/mnt/raid0/llm/tmp/k35-frontdoor-operational-1024-20260717T201842Z/summary.json` | supporting operational row | Optimized frontdoor MI210 operational row across 2K/8K/32K, cleanup proof. |

## 2026-07-19 Supporting Artifacts

These are supporting observation-grade artifacts only. They do not ratify `P-GPU-1`
and do not upgrade AXA/Gate-R numbers to decision-grade.

| Artifact | Current status | Notes |
|---|---|---|
| `data/gpu-mi210/axa2-qwen35-122b-iq2m-prefill-sizing-20260719T060039Z/summary.json` | observation-grade supporting cost-model row | 122B UD-IQ2_M MI210 q4_0/f16 KV prefill rows: `pp2048 342.06 t/s`, `pp8192 135.56 t/s`, `pp16384 76.52 t/s`; no 32K row before SIGTERM. |
| `data/gpu-mi210/axa2-qwen35-122b-iq2m-prefill32k-t32-20260719T062410Z/summary.json` | negative/diagnostic observation | Direct q4_0/f16 32K t32 run held MI210 but emitted no usable row before bounded manual stop. |
| `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_q4k_f16v_b1024_ub256_20260719T064333Z/summary.json` | negative/diagnostic observation | q4_0/f16 b1024/ub256 32K repeat stopped after GPU activity dropped to zero with no stdout row. |
| `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_f16kv_b1024_ub256_20260719T065143Z/summary.json` | observation-grade supporting control | f16/f16 KV b1024/ub256 32K control completed at `489.31 t/s` with clean post-run process/KFD checks. This does not certify the q4_0/f16 32K cost. |
| `data/gpu-mi210/axa2_qwen35_122b_hot_load_lease_smoke_20260719T065557Z/summary.json` | observation-grade supporting control | Hot page-cache 122B IQ2_M MI210 server reached health in `7052 ms`, returned exact `READY`, and cleaned up. Not a cold-load measurement. |
| `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_f16k_q4v_b1024_ub256_rerun_20260719T070336Z/summary.json` | negative/diagnostic observation | f16/q4_0 b1024/ub256 32K rerun held VRAM but stayed at `0%` GPU through warmup until watchdog stop; no row. |
| `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_q4kv_b1024_ub256_20260719T071051Z/summary.json` | observation-grade supporting control | q4_0/q4_0 b1024/ub256 32K control completed at `487.87 t/s` with clean independent cleanup. This narrows the blocker to mixed KV. |
| `data/gpu-mi210/axa2_24k_prefill_qwen35_122b_v1_q4k_f16v_b1024_ub256_20260719T072203Z/summary.json` | diagnostic observation | Current default HIP build completed q4_0/f16 `pp24576` at `144.07 t/s`, proving mixed KV is not globally broken but is slow on this unsupported path. |
| `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_q4k_f16v_no_warmup_b1024_ub256_20260719T072934Z/summary.json` | negative/diagnostic observation | Current default HIP build q4_0/f16 `pp32768` no-warmup held 60% VRAM, emitted no row, used 0% GPU, and was manually stopped as CPU fallback. |
| `data/gpu-mi210/axa2_mixed_kv_fa_matrix_current_build_20260719T073441Z/summary.json` | diagnostic observation | Current default HIP build q4_0/f16 `pp4096` completed at `372.70 t/s` forced-FA, `564.27 t/s` auto, and `567.23 t/s` FA-off; f16/q4_0 `pp512` forced-FA completed at `454.67 t/s`, while f16/q4_0 auto failed context creation. |
| `data/gpu-mi210/axa2_fa_all_quants_mixed_kv_validation_20260719T073906Z/summary.json` | observation-grade supporting control | Separate experimental HIP build with `GGML_CUDA_FA_ALL_QUANTS=ON` completed q4_0/f16 `pp32768` at `415.31 t/s` with real MI210 activity and clean KFD cleanup. This is not the current default build and does not ratify `P-GPU-1`. |
| `data/gpu-mi210/axa2_fa_all_quants_regression_controls_20260719T074221Z/summary.json` | diagnostic observation | Same all-quants build measured homogeneous f16/f16 `pp32768 416.55 t/s` and q4_0/q4_0 `pp32768 414.60 t/s`; this shows the mixed-KV workaround should not be treated as a blanket v7 default. |
| `data/gpu-mi210/axa2_current_build_no_warmup_homogeneous_controls_20260719T074757Z/summary.json` | diagnostic observation | Current default build no-warmup homogeneous controls measured f16/f16 `pp32768 489.82 t/s` and q4_0/q4_0 `pp32768 489.07 t/s`, confirming the all-quants homogeneous drop is a build-choice effect rather than a warmup artifact. |

Retro-cert audit checklist for any future operator-approved upgrade:

| Required field | Gate-R candidate | AXA-2 prefill artifacts | Notes |
|---|---|---|---|
| ROCm clocks/power/temp before+after | Unknown until field audit | Unknown until field audit | Mandatory under the ratified amendment. |
| VRAM residency / KFD PID checks | Present in several artifacts | Present post-run; per-run detail varies | Must be checked artifact-by-artifact. |
| Binary/model identity | Present | Present | Confirm exact v7 commit and `LD_LIBRARY_PATH`. |
| Warm-up policy / rep count | Present for K35 candidates | Single-rep observation for AXA-2 | AXA-2 is cost-model support, not a promotion speed claim. |
| Cleanup proof | Present | Present | Process and KFD cleanup are required for any retro-cert path. |
| Cold-load policy | Not applicable | Missing for AXA-2 load-cost branch | Hot page-cache ready time cannot substitute for cold-load evidence. |

## Decision Recorded

1. `P-GPU-1` is ratified in `/workspace/MEASUREMENT.md` as of 2026-07-19.
2. The ratified kernel-provenance rule is **production-named-only**: experimental-v7 and other
   candidate/fork rows stay observation-grade.
3. Retro-certification is allowed only when the artifact was produced on a production-named
   kernel and every mandatory field is present.
4. Existing Gate-R/K35/AXA experimental-v7 rows therefore remain observation-grade regardless
   of field completeness. Gate-R certification happens via a post-promotion rerun on
   `production-consolidated-v7`.

Promotion-gate implication: `P-GPU-1` ratification is closed, but it does not turn existing
experimental-v7 Gate-R rows into decision-grade promotion evidence. It prepares the
post-promotion certification lane.

## Ratification Gate Checklist

Use this as the execution checklist for the operator decision. Agents may prepare or audit
the listed artifacts, but must not author, sign, or merge the MEASUREMENT amendment.

- [x] Human/operator amendment to `/workspace/MEASUREMENT.md` is signed or merged. ✅ 2026-07-19
- [x] Amendment states only a production-named kernel may produce `P-GPU-1` claims. ✅ 2026-07-19
- [x] Amendment states retro-certification is allowed only for production-named-kernel artifacts
  with every mandatory field present. ✅ 2026-07-19
- [ ] If retro-certification is considered for a production-named-kernel artifact, it passes the mandatory-field
  audit: clocks/power/temp before+after, VRAM residency and KFD PID checks, binary/model
  identity, warm-up/discard policy, rep count, CPU-stack interference policy, result
  grammar, and cleanup proof.
- [x] Existing experimental-v7 Gate-R/K35/AXA artifacts remain observation-grade; Gate-R
  must rerun under the ratified protocol on `production-consolidated-v7`. ✅ 2026-07-19
- [ ] No vendor/web number appears in a decision row.
- [ ] No production-v6 edit, build, or promotion is performed as part of ratification.

Known certification risk: the current Gate-R candidate artifact includes utilization,
VRAM, PID/memory samples, guard state, commands, plan, report, and cleanup proof, but it may
not contain a complete clocks/power/temp before+after record and was produced on an experimental
kernel. It must not be auto-upgraded.

2026-07-19 machine audit: inference-research now has an artifact-only checker at
`scripts/benchmark/pgpu1_artifact_completeness_audit.py` and report outputs at
`/mnt/raid0/llm/epyc-inference-research/docs/data/pgpu1_artifact_completeness_audit_20260719.json`
and `.md`. The audit ran over the Gate-R candidate, context-edge/supporting K35 rows, and
AXA-2 supporting rows without launching inference. Result: `rerun_required_for_incomplete_artifacts`.
The primary Gate-R row is incomplete on `rocm_clocks_before_after`, `rocm_power_before_after`,
`rocm_temp_before_after`, `production_named_kernel_identity`, `warmup_discard_policy`,
`cpu_interference_policy`, and `post_cleanup_vram_sample`. This confirms the prose audit: if
these fields remain mandatory, current artifacts remain observation-grade and Gate-R reruns
under the ratified protocol. Experimental-v7 evidence is now classified as a near miss for the
production-named-kernel field.

2026-07-19 runner-prep update: inference-research `scripts/benchmark/k35_stack_context_matrix_runner.py`
now records the missing P-GPU fields by construction for future K35/Gate-R reruns:
`collect_rocm_snapshot()` keeps the old PID/VRAM/utilization fields and adds clocks, power, and
temperature snapshots; every executed cell adds a `memory_samples` `phase=before_launch` ROCm
sample before server start plus an `after_cleanup` ROCm sample after termination; and each executed
cell writes `prompt.txt`, `prompt_sha256.txt`, `request.json`, `response.json`, and `result.json`.
Guard state now records the git root/head/status for the binary being executed and whether its
branch is production-named. Dry-run plans also emit `operator_run.sh` with the exact `--execute`
invocation. The tracked dry-run directory is not the execution artifact root: unless the operator
overrides `K35_EXEC_OUTPUT_DIR`, the generated script creates a fresh timestamped run under
`/mnt/raid0/llm/epyc-inference-research/data/k35_stack_context_matrix/`. For the next Gate-R
candidate rerun, pass operator-specific policy text with
`--warmup-discard-policy` and `--cpu-interference-policy` rather than leaving those fields implicit.
Current no-inference dry-run artifact:
`/mnt/raid0/llm/epyc-inference-research/docs/data/pgpu1_k35_runner_dryrun_20260719/`.

Canonical-tree note: the current Gate-R candidate was run on experimental v7
`d1e5a20ebebe567f0da6bc64ca7ea7ecd521fc24`. The signed amendment requires a
production-named kernel, so this artifact remains observation-only.
