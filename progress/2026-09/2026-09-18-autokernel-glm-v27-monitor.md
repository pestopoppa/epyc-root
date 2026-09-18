# AutoKernel GLM v27 monitor — 2026-09-18

The operator requested a 20-iteration semantic health watch using the autonomous
Qwen3.8-27B run and manually steered Next-Flash work as patterns for useful
research: falsifiable bottleneck hypotheses, source-specific critic decisions,
independent correctness, matched measurements, and escape after measured nulls.
This is **not** a keep quota. The watch is still open.

GLM v27 started 2026-09-17 23:48 UTC in
`/mnt/raid0/llm/tmp/aku-glm53-continuous-20260917-v27`, retaining the
28-keep store `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-store`. Its one-time
distinct held-out request calibration finished at 2026-09-18 03:34 UTC:
matched_process_v2, 24 pairs, 48 process launches, 3.113% request-bound floor,
recipe hash `97223a7d...`, request digest `a2a0eab1...`. That is not a research
iteration or a performance gain.

The first post-calibration planner call abstained at 03:38 UTC. Its source
inspection found 53.03% sampled synchronization attribution without an editable
causal change and 18.62% sampled fused Q4_K/Q5_K computation. It correctly
identified that the material dot template lives in `iqk_gemm_kquants.cpp`,
outside the previously admitted `iqk_moe_fused_up_gate` body-only route. This
is a concrete scope/oracle gap, not evidence that the model lacks headroom.

The completed batch was charged 13,839.817 seconds, exceeding the scheduler's
12,600-second stage-plus-teardown forecast. The supervisor then refused its
successor and exited, while the outer loop-status incorrectly remained
`running`. The first batch is durably journaled as `abstained`; the 28 keeps and
held-out floor are retained. No v27 candidate has yet been measured or kept.

Research-lane fixes landed: `9a711722` permits a settled abstention to exceed
the forecast while still charging actual time and recovers only the proven
abstention-overrun fence; `e2984f51` publishes terminal `failed` on supervisor
exceptions. `5ccdaf3f`, `4c089bf1`, and `55e0c380` add the Q4_K/Q5_K-only dot
edit route, original/candidate hunk confinement, exact candidate-DSO
specialization hits, independent scalar cases across widths 1–8, and live
runner/prompt wiring. The 72 focused tests and 50 subtests pass. A CPU-only
oracle smoke on active-tip `anchor-gen-014` passed 32 plain/expert scalar cases
and 16 fused scalar/GDB specialization-hit cases; no performance measurement
was run in that smoke.

The supervisor was restarted at 03:58 UTC against the **same** v27 serial state
and store. It recovered the D fence and launched retained batch 1 (child PID
2186174), so the prior settled abstention remained charged. Batch 1 then
selected the full CPU recipe, whereas the 3.113% held-out floor belongs to a
different half-partition recipe. The full recipe legitimately needs its own
held-out calibration. I mistook this for a duplicate and interrupted the child
at 04:03 UTC. The process and its server are verified dead; no batch-1 result
or performance claim exists. This interruption left a failed-target marker and
an issued scheduler selection without a released-claim receipt. Recovery must
preserve that fail-closed evidence, not fabricate a settled measurement. The
20-loop semantic watch remains open; v27 is stopped and retained as evidence.

Recovery: `8ca6f796` adds a new-state-only `--initial-continuation` input,
validated against the exact target, stable argv and completed child hash. v28
started at 04:12 UTC in
`/mnt/raid0/llm/tmp/aku-glm53-continuous-20260918-v28`, with its first child
resuming the validated v27 batch-0 continuation. Its scheduler epoch starts
empty; it does **not** import the interrupted v27 selection. The same store,
worktree, 28 retained keeps and historical evidence remain in use. v28 uses
v27's exact target root to preserve stable continuation binding and disables
retired-build pruning during this recovery. The full-recipe held-out floor is
absent and its distinct calibration must finish before research authoring.
