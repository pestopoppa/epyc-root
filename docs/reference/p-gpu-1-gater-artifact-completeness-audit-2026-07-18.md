# P-GPU-1 / Gate-R Artifact Completeness Audit - 2026-07-18

**Scope:** artifact-only audit. No inference, benchmark, build, or server command was run.
This memo audits whether the existing Gate-R / K35 artifacts can be retro-certified under
the proposed `P-GPU-1` field list in
`docs/reference/p-gpu-1-ratification-package-2026-07-18.md`.

**2026-07-19 machine-check addendum:** this prose verdict is now reproducible with the
artifact-only helper in inference-research:
`scripts/benchmark/pgpu1_artifact_completeness_audit.py`. The generated reports are
`/mnt/raid0/llm/epyc-inference-research/docs/data/pgpu1_artifact_completeness_audit_20260719.json`
and `.md`. They audit the Gate-R candidate, context-edge/supporting K35 rows, and AXA-2
supporting rows without running inference, servers, benchmarks, builds, or ROCm commands.

## Verdict

**Rerun required** for any decision-grade `P-GPU-1` / Gate-R throughput claim if the
operator ratifies the proposed mandatory field list unchanged.

The primary Gate-R candidate is strong observation-grade evidence and is close enough to
inform operator ratification of the protocol shape, but it is not complete enough to
retro-certify as decision-grade. The blocking gap is not the throughput result grammar; it
is missing mandatory hardware-state telemetry and explicit policy fields in the artifact
record.

## Audited Inputs

- `/mnt/raid0/llm/epyc-root/docs/reference/p-gpu-1-ratification-package-2026-07-18.md`
- `/mnt/raid0/llm/epyc-root/handoffs/active/v7-promotion.md`
- `/mnt/raid0/llm/epyc-inference-research/data/k35_stack_context_matrix/frontdoor_pgpu1_candidate_20260718Tquiet/`
- `/mnt/raid0/llm/epyc-inference-research/data/k35_stack_context_matrix/frontdoor_context_edges_20260718Tcodex/`
- `/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z/`
- `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/`
- `/mnt/raid0/llm/tmp/k35-frontdoor-operational-1024-20260717T201842Z/`

## Primary Candidate Status

`/mnt/raid0/llm/epyc-inference-research/data/k35_stack_context_matrix/frontdoor_pgpu1_candidate_20260718Tquiet/`
contains the strongest Gate-R candidate:

- `guard_state.json` records device listing, `llama-server --version`, experimental git
  head `d1e5a20eb`, clean experimental status, memory/NUMA snapshot, and no process
  blockers.
- `commands.sh` and `plan.json` record exact server command lines, including
  `LD_LIBRARY_PATH`, `GGML_IQK=1`, `ROCR_VISIBLE_DEVICES=0`, `HIP_VISIBLE_DEVICES=0`,
  model path, context, KV quant, device, and spec-dec mode.
- `summary.json` records `n=5` fresh-server reps for CPU no-spec, MI210 no-spec, and
  MI210 native MTP at nominal 8K; median/MAD throughput; prompt/decode split; generated
  token counts; draft generated/accepted counters; PID/RSS/smaps samples; ROCm PID/VRAM
  utilization snapshots; and per-rep cleanup proof.
- `frontdoor_pgpu1_candidate_report.md` summarizes the same-window result:
  CPU no-spec `17.10 t/s`, MI210 no-spec `95.39 t/s`, MI210 native MTP `119.69 t/s`,
  and native MTP `3835/3835` accepted drafts.

This is enough to preserve as an observation and to justify the proposed protocol shape.
It is not enough to close Gate-R as decision-grade under the proposed `P-GPU-1` fields.

## Missing Fields That Force Rerun

These fields are missing from the primary candidate artifact:

- `rocm-smi` clocks before and after each run/window.
  The recorded sampler is only `rocm-smi --showpidgpus --showmemuse --showuse` in
  `summary.json` per-run `memory_samples[].rocm.argv`; no `--showclocks` or equivalent
  clock output exists in the audited artifacts.

- `rocm-smi` power before and after each run/window.
  No `--showpower`, socket power, board power, or equivalent power field was found in:
  `frontdoor_pgpu1_candidate_20260718Tquiet/`, `frontdoor_context_edges_20260718Tcodex/`,
  `k35-memory-backfill-20260717T1400Z/`, `k35-minicpm-service-matrix-20260717T2045Z/`,
  or `k35-frontdoor-operational-1024-20260717T201842Z/`.

- `rocm-smi` temperature before and after each run/window.
  No `--showtemp`, temperature, or equivalent thermal output was found in the same artifact
  set.

- Explicit warm-up policy.
  The primary candidate records fresh-server reps and no discarded rows, but it does not
  declare a warm-up policy such as "no warm-up", "one warm-up discarded", or graph recapture
  discard handling in the artifact itself.

- Explicit CPU stack interference disposition.
  `guard_state.json` records `process_blockers: []`, and `summary.json` records
  `cleanup_process_blockers: []`, but the artifact does not explicitly state whether the
  CPU-only production stack was quiesced, stopped, hidden from ROCm, or intentionally
  co-resident.

- Explicit post-cleanup VRAM state for the primary candidate.
  Per-rep samples cover `after_health`, `after_request`, and `before_cleanup`; cleanup proves
  the server PID is dead. The artifact does not include a distinct post-cleanup `rocm-smi`
  VRAM sample for the primary candidate run.

## Supporting Artifact Notes

- `frontdoor_context_edges_20260718Tcodex/summary.json` is useful context-edge observation
  evidence, but it has only one rep per scenario/context cell. It also uses the same reduced
  ROCm sampler and therefore cannot supply the missing clock/power/temp fields.

- `/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z/summary.json` supports residency
  and cleanup claims, but it does not add clock/power/temp evidence.

- `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/summary.json` supports
  service co-residency / active-overlap tax. Its compact summary reports active overlap
  passed, with frontdoor active-overlap mean `94.77 t/s` versus frontdoor-alone mean
  `96.33 t/s`, but it is not a frontdoor speed-certification run and also lacks
  clock/power/temp telemetry.

- `/mnt/raid0/llm/tmp/k35-frontdoor-operational-1024-20260717T201842Z/summary.json` is an
  operational support row with cleanup proof and residency samples, but it has no scenario
  summary, no repeated canonical decision rows, and no clock/power/temp telemetry.

## Ratification Implication

If the operator wants these existing artifacts to become decision-grade without rerun, the
operator amendment would need to relax or waive the missing fields above. If the proposed
fields stay mandatory, rerun Gate-R with the following additions:

- Capture `rocm-smi` clocks, power, temperature, utilization, VRAM, and PID mapping before
  and after each run/window.
- Record an explicit warm-up/discard policy.
- Record the CPU stack interference policy in the artifact, not only absence of process
  blockers.
- Record before-load, after-health, after-request, before-cleanup, and after-cleanup VRAM
  state for the GPU device.
- Keep the existing strengths: same-window CPU re-anchor, MI210 no-spec and native-MTP arms,
  fresh-server reps, `n>=5`, exact commands, git/binary/model identity, draft counters,
  median/MAD, prompt/decode split, and cleanup proof.

Machine-audit output on 2026-07-19 agrees: overall status `incomplete`, recommendation
`rerun_required_for_incomplete_artifacts`. The primary Gate-R candidate specifically lacks
`rocm_clocks_before_after`, `rocm_power_before_after`, `rocm_temp_before_after`,
`warmup_discard_policy`, `cpu_interference_policy`, and `post_cleanup_vram_sample`.
