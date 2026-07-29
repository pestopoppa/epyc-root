# Quant-Asymmetric Self-Spec Serving Design

Date: 2026-07-20
Status: DR-2 design checkpoint, not a serving rollout
Evidence: `/mnt/raid0/llm/epyc-inference-research/data/dr0_quant_asym_self_spec/dr0_quant_asym_self_spec_20260720T060423Z_dr0e2_full_k_sweep_final/summary.json`

## Scope

This design translates the DR-0e.2 observation into the next serving/routing
work item for the Qwen3.5-122B quant-asymmetric self-spec lane:

- Target/verifier: Qwen3.5-122B-A10B `UD-Q4_K_M`, CPU-only.
- Drafter: same-family Qwen3.5-122B-A10B `UD-IQ2_M`, MI210-resident.
- Serving mechanism: one `llama-server` process with CPU target and GPU draft model,
  `--spec-type draft-mtp`, `--spec-draft-device ROCm0`.
- Activation state: default-off research lane. Do not expose to AutoPilot or
  NumericSwarm until broader admission and production-named `P-GPU-1` certification pass.

This is not a replacement for native MTP on roles that already have a fast, quality-clean
native path. It is a candidate for cases where the full-quality CPU verifier must remain
authoritative and the MI210 can be leased as a draft accelerator.

## Evidence Summary

DR-0e.2 passed all bounded safety checks:

| Arm | Decode t/s | Speedup vs CPU | Alpha | F(K) | H(K) |
|---|---:|---:|---:|---:|---:|
| CPU Q4 target baseline | 7.083 | 1.000x | n/a | n/a | n/a |
| CPU Q4 + MI210 IQ2 K1 | 9.888 | 1.396x | 0.945 | 39.040s | 0.545s |
| CPU Q4 + MI210 IQ2 K2 | 11.407 | 1.610x | 0.900 | 33.667s | 0.657s |
| CPU Q4 + MI210 IQ2 K4 | 11.847 | 1.672x | 0.787 | 32.280s | 0.781s |

Quality and output-stability gate:

- `28/28` task-quality rows passed.
- Combined K1/K2/K4 outputs matched the CPU verifier baseline hashes for all four
  DR-0 task classes.
- Cleanup passed with no llama process leak and no KFD PID leak.

The result is observation-grade only. It proves the control design is viable enough
to keep, not that it is ready to serve production traffic.

## K Selection

Use **K2** for the first default-off serving design.

Reasons:

- K2 captures most of the measured gain: `1.610x` vs baseline.
- K4 adds only `3.85%` throughput over K2 (`11.407 -> 11.847 t/s`).
- K4 alpha falls from `0.900` to `0.787`, which increases exposure to draft mismatch
  and coordination overhead on broader prompts.
- K2 has lower H(K) and a better safety margin for first admission.

K4 remains a later optimization candidate after K2 passes broader task admission.
K1 is useful as a fallback diagnostic if K2 regresses under longer or noisier prompts.

## Routing Policy

Initial lane name in documentation: `qwen35_122b_q4_cpu_iq2_mi210_draft_k2`.

Default-off policy:

- Requires an explicit operator/runtime flag before routing any live traffic.
- Requires a MI210 lease before launch; if unavailable, use the CPU verifier baseline.
- Does not co-reside with the MI210 frontdoor by default. The IQ2 drafter is about
  37.6 GiB and can crowd out the production frontdoor residency lane.
- Does not accept planner/autopilot numeric mutation yet. K is fixed at `2` until
  broader admission closes.
- Does not change the accepted-token quality source: accepted tokens are verified by
  the CPU Q4 target.

Candidate routing classes:

- Structured or repetitive output where draft acceptance is naturally high.
- Bounded architect/reviewer-style JSON decisions where the CPU target remains the
  authority.
- Long CPU-target completions where expected remaining output is high enough to repay
  GPU lease/load overhead.

Avoid:

- Short requests where CPU baseline latency dominates less than lease/load overhead.
- General frontdoor requests that can use the already-fast MI210 native-MTP frontdoor.
- Any production reviewer route until reviewer admission is separately solved.
- Mid-stream quant-changing teleport claims; AXA-2 already owns that policy boundary.

## Admission Gates

Before a serving rollout:

1. **Broader task-class admission**
   - Run K2 against a wider task slice than DR-0: structured JSON, strict formatting,
     code-review controls, architect planning/rubric rows, and long-output rows.
   - Require CPU-target equivalence by exact hash where deterministic and by a
     documented content-equivalence scorer where exact hash would overconstrain.
   - Require no quality regression relative to CPU target baseline.

2. **Context and token-length coverage**
   - Cover at least 8K and 16K context bands before live routing.
   - Add 32K only if the target production use case needs it.
   - Use generated-token counts large enough to measure decode, not 1-3 token smokes.

3. **Resource and lease behavior**
   - Prove no KFD PID leak and no residual llama PIDs after every row.
   - Measure frontdoor opportunity cost: resident frontdoor alone, frontdoor after
     eviction/reload, and DR-2 lane active.
   - Keep one MI210 owner unless a co-residency test proves otherwise.

4. **Production-named GPU certification**
   - Any decision-grade GPU performance claim must run after operator promotion under
     a production-named v7 kernel and the ratified `P-GPU-1` fields.
   - Current experimental-v7 rows remain observation-grade.

## Implementation Package

The first code package should be dry-run-first and config-gated:

- Add a named stack/model-registry candidate in inference research, not the production
  orchestrator registry.
- Add a runner that emits `operator_run.sh`, exact server args, ROCm pre/post samples,
  process cleanup proof, response artifacts, and CPU-baseline comparison.
- Add a narrow orchestrator capability proposal only after the research runner passes:
  route label, lease requirement, fallback target, and an explicit default-off flag.
- Do not add a NumericSwarm tunable for K until K2 admission passes. If exposed later,
  valid values should be the measured set `{1, 2, 4}` with K2 as default.

## DR-3b Live Runner Checkpoint

Follow-up evidence closed the runner implementation step:

- Runner: `epyc-inference-research/scripts/benchmark/dr3_quant_asym_k2_admission_runner.py`.
- Passing artifact:
  `epyc-inference-research/data/dr3_quant_asym_k2_admission/dr3_quant_asym_k2_admission_20260720T071200Z_live_smoke_ctx8192_r1_v2/`.
- Result: quality `12/12`, output stability pass, cleanup pass,
  `observation_grade=true`, `decision_grade=false`.
- Speed: CPU baseline `7.185 t/s`; combined K2 `11.104 t/s`; ratio `1.545x`;
  alpha `0.876`.

This proves the live runner and an 8K observation slice. It does not admit a
serving route.

## DR-3c Default Admission Checkpoint

Follow-up evidence closed the default 8K+16K admission-package execution step:

- Passing artifact:
  `epyc-inference-research/data/dr3_quant_asym_k2_admission/dr3_quant_asym_k2_admission_20260720T071816Z_dr3c_default_ctx8192_16384_r1/`.
- Result: quality `24/24`, output stability pass, context coverage pass for
  `8192` and `16384`, cleanup pass, `observation_grade=true`,
  `decision_grade=false`.
- Speed:

| Context | CPU baseline decode t/s | Combined K2 decode t/s | Ratio | Alpha | Draft accepted/generated |
|---:|---:|---:|---:|---:|---:|
| 8192 | 6.980 | 10.535 | 1.509x | 0.876 | 408/466 |
| 16384 | 6.979 | 10.429 | 1.494x | 0.879 | 420/478 |

This proves the default admission package on experimental v7. It does not admit
a serving route because the frontdoor opportunity-cost gate and production-named
`P-GPU-1` rerun path were still open at this checkpoint.

## DR-3d Frontdoor Opportunity-Cost Checkpoint

The frontdoor opportunity-cost gate was implemented and run live against the
experimental v7 binary:

- Runner: `epyc-inference-research/scripts/benchmark/dr3_frontdoor_opportunity_cost_gate.py`.
- Dry-run artifact:
  `epyc-inference-research/data/dr3_frontdoor_opportunity_cost/dr3_frontdoor_opportunity_cost_20260720T075235Z_dryrun_v2/`.
- Passing live artifact:
  `epyc-inference-research/data/dr3_frontdoor_opportunity_cost/dr3_frontdoor_opportunity_cost_20260720T074853Z_live_ctx8192_r1/`.
- Result: `frontdoor_opportunity_cost_gate.status=pass`,
  `cleanup_proof.status=pass`, `observation_grade=true`,
  `decision_grade=false`, `serving_route_allowed=false`,
  `numeric_swarm_surface_allowed=false`.

| Measurement | Value |
|---|---:|
| Frontdoor before lease decode | `93.690 t/s` |
| Frontdoor before lease load wall | `7.439 s` |
| Frontdoor after eviction/reload decode | `94.157 t/s` |
| Frontdoor after eviction/reload load wall | `7.461 s` |
| After/before decode ratio | `1.005x` |
| DR-3 K2 active decode | `11.701 t/s` |
| DR-3 K2 active alpha | `1.000` |
| DR-3 K2 draft accepted/generated | `128/128` |

This closes the experimental opportunity-cost blocker: temporarily leasing the
MI210 to the K2 lane did not show a frontdoor reload/decode regression in this
single-run observation. It still does not admit a serving route because the
result was not run under a production-named kernel/protocol.

## Current Verdict

Keep the lane as a serious candidate. Do not serve it yet.

Next executable step: repeat required GPU claims under `production-consolidated-v7`
for `P-GPU-1` if the operator promotes the frozen v7 candidate.
