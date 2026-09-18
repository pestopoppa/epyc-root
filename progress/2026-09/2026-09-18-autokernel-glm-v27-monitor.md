# AutoKernel GLM v27 monitor — 2026-09-18

The operator requested a 20-iteration semantic health watch using the autonomous
Qwen3.8-27B run and manually steered Next-Flash work as patterns for useful
research: falsifiable bottleneck hypotheses, source-specific critic decisions,
independent correctness, matched measurements, and escape after measured nulls.
This was **not** a keep quota. The operator ended the watch on 2026-09-18;
AutoKernel is stopped and must not be relaunched by this session.

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

10:39–11:07 UTC status: v28 has now completed **36** serial batches, all
`abstained` in their sealed continuations, with zero measured source candidates
and no new keep. The active batch 36 is in a matched CPU serving A/B, with
fresh dashboard heartbeats and repeated `llama-server` launches using roughly
34 CPU-core equivalents during requests. The apparent host idleness between
launches is not a stopped process. The 36 abstentions do **not** satisfy the
operator's semantic 20-loop health watch. Their repeated reason is that dense
Q8 work lacks an admitted independent path while 25–53% sampled barrier/wait
time has no node-local causal attribution; the Q4_K/Q5_K route is admitted but
prior mechanisms are exhausted. A SIGTERM to the captured supervisor PID
2212445 set its STOP marker; it is expected to exit after batch 36 settles.
At 11:09:46 UTC the supervisor honored the STOP marker after batch 36
settled. Its continuation is `terminal=stopped`, `iterations_completed=1`,
`outcome_counts={"runtime_observed":1}` for
`akm-threads44-balanced-numa`. This is an observation-only runtime arm,
not a source candidate, keep, or champion promotion. The serial state now
has `next_batch=37`, `active=null`, and no failed target; the outer status
declares `complete`. Exact captured supervisor PID 2212445 and child PID
2806534 were absent when checked, and no AutoKernel process remained. No
signal was needed because the queued stop completed before termination.

The operator then explicitly ended this campaign and requested session
wrap-up. The semantic 20-loop acceptance condition was **not met**: 36
abstentions followed by one observation-only runtime arm produced zero new
source-candidate measurements or keeps. The retained 28-keep store and
experimental source remain intact. The causal per-thread profile described
below was not run; it is a possible diagnostic only if the operator later
authorizes another campaign, not a pending action for this session.

Read-only audit identified a nonduplicative next diagnostic: compile the
retained 614ff2ba experimental tree with existing `GGML_CPU_PROF` support,
verify profiler markers in its CPU DSO, then profile the exact GLM request
with `GGML_CPU_PROF_THREADS=1` and separate draft/trunk graph-shape filters.
Older c463 per-node captures exist but their per-thread columns are all zero,
so they cannot distinguish barrier overhead from straggler work. Hold the
shared CPU-region claim through the replay. A Q8_0_1 exact-path oracle is
technically possible, but the audit found no distinct evidence-backed Q8
optimization to justify opening that gate yet. Wait for a causal source or
assembly finding rather than invite more variations of exhausted mechanisms.
