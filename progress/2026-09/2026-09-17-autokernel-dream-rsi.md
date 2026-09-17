# AutoKernel Dream-RSI handoff implementation checkpoint — 2026-09-17

Reviewed the new Dream-RSI rows in `autokernel-research-loop.md`, RB-lineage
telemetry in `autokernel-rebuild-program.md`, and AR-RPUCG/AR-ROCm-eval in
`agentic-rocm-kernel-authoring.md` before assigning code. These rows are
offline/observe-only except for later, explicitly gated measurements; no live
search-policy or promotion gate was changed at this checkpoint.

## GLM CPU recipe diagnosis

At retained experimental tip `614ff2ba02e095b3ed11d7ed5e85ca3b1e2efeb3`,
the same frozen GLM-5.3-Flash request and CPU-only build were measured under
held q0–q3 CPU and MI210-exclusion claims. Five alternating 24-vs-48 thread
pairs produced a median 24-thread effect of **−6.391%** versus 48; the
48-thread median was 8.835 tok/s. A clean 48/32/48 rescreen, after the
initial 32-thread arm overlapped indexing, found 8.714 tok/s at 32 versus
8.957 tok/s for the two bracketing 48-thread arms (−2.713%). The original
96-thread screen overlapped a brief worktree checkout and is not promoted to
clean evidence. This is a runtime-recipe diagnostic, not a matched-process
champion gate; lifecycle telemetry reports placement/foreign-load validity
as `unproven`. No source keep, recipe change, or champion advancement follows
from these numbers. Evidence:
`/mnt/raid0/llm/tmp/aku-glm53-thread-sweep-20260917/summary.json` and
`clean32-summary.json` beside it.

## Reviewed task outcomes

- Added prospective Vidya source rows/tasks SC87 and VB-AK-LINEAGE before any
  real lineage diagnostic run. The offline line-level detector was integrated
  on an isolated root lane and its six fixture tests pass. The prospective
  source-capture producer and journal/outcome join remain separate; no
  historical overwritten patch is used to claim a cycling rate.
- Audited AK-WM-3, adaptive policy, plateau, and cost-credit prerequisites.
  The AK-WM-2a real archive is not materialized: the inspected r49 IQK
  intervention ends in `state:error` and its control journal is empty. The
  strict builder exists, but even a future matched archive would not contain
  prefix-visible choice/cost state needed for honest counterfactual replay.
  No policy uplift was computed.
- Audited AR-RPUCG and SimpleTES ROCm evaluation. No same-task evaluated DAG
  plus incumbent selector trace was identified for the selection A/B; the
  pinned SimpleTES path uses `rocprofv3` pftrace/CSV while this host's governed
  profiler seam is ROCm 6.2.0 v1/v2. No GPU evaluation or executable adapter
  was registered.
- Audited existing C6 integrity and promotion controls. GPU hardened input
  rotation and prebuild static scanning already run; their residual is the
  absence of an independent reference check for each new timed content vector.
  Exact author prompts are not retained, so historical keeps cannot be
  represented as same-prompt replay results. N=10 and BO remain future
  metered, report-only controls, not promotion conditions.

## Live-loop repair in progress

The GLM v20 serial child reprofiled the unchanged anchor on each one-batch
startup and carried no profile into continuation. Its preplanner defaulted to
HALF scope before seeing the observed synchronization-heavy profile; runtime
arms were also blocked by four campaign-ID-prefix checks. Isolated workers
are implementing exact-identity profile reuse/full-scope routing and
prospective lineage/correctness receipts. No relaunch or new measured
candidate is claimed at this checkpoint. The 28 retained keeps remain intact.
