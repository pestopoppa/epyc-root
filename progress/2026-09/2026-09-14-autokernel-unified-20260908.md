# AutoKernel unified — 2026-09-14

## GLM-5.3-Flash continuous 50-loop acceptance

Completed the operator-requested health proof for the existing GLM-5.3-Flash CPU AutoKernel.
The acceptance required an observed CPU profile, a real measured candidate path, continuous
automatic operation, and 50 monitored terminal loops with halt/fix/relaunch on genuine faults.

### Result

- Terminal continuations: **50/50**, composed from retained continuous states v2/v3/v4/v7 as
  `2 + 20 + 3 + 25`. Aggregate outcomes are `42 measured_null` and `8 kept`.
- Ordered continuation-digest-list SHA-256:
  `b89c41aa4b2d68be096671d6962f37a200f7990bf193c6dd292005398b7e7ff6`.
- Final loop: v7 `batch-000024`, terminal `complete`, one `kept` outcome. Continuation SHA-256:
  `41da2b2c8c493ebed97844e3840793067d0d233fac835e95683d6f06531d0c7e`.
- Final mechanism: `akm-q4k-pairrow-zmm-accumulate`, marginal matched A/B `+0.182%` over five
  pairs. Clean-built anchor `dc3798db10a6654721f2a1fa6a162be2e5fdf95f` passed its five-pair
  A/A guard at `+0.0773869451%` drift.
- Accumulator: 23 keeps, tip `dc3798db10a6`, direct current-snapshot effect
  **+0.8303809823155373%** versus champion-of-record `c463f601bd39`. Accumulator bundle SHA-256:
  `e3df3b43bad0afdc75aad5cd3ad9d09d64e12985671c11e90c649c99c23445b5`.
- Final post-keep original-request CPU profile completed with the actual serving process and
  simultaneous `perf` capture. Receipt SHA-256:
  `b67e9b4a254eb8ac00decd8ea3d2bf0867f286f61c1423dbbf9c5f96ade9b950`.
- Loop 49's cadence gate directly measured the prior 22-keep stack at `+0.5400504842%` on the
  bench comparison and `+0.3349231781%` on the serving surface. The serving effect was not
  decisive, so it was retained as a surface divergence rather than promoted.

### Runtime disposition

The continuous supervisor automatically launched v7 batch 25 after the 50th completion,
demonstrating boundary-to-boundary continuation. The exact supervisor and post-boundary child
PIDs were stopped at the requested monitoring boundary; the supervisor wrote its `STOP` sentinel
and `stop_requested: true`. Batch 25 has no terminal continuation and is excluded from the
50-loop result. No broad PID matching was used. No production kernel was modified or promoted.

### Authoritative paths

- Store: `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-store`
- Supervisor: `/mnt/raid0/llm/tmp/aku-glm53-continuous-20260912-v7`
- Final continuation:
  `/mnt/raid0/llm/tmp/aku-glm53-continuous-20260912-v7/batches/batch-000024/loop-continuation.json`
- Experimental source: `/mnt/raid0/llm/tmp/glm53-recovered-accumulator-20260912`
- Published experimental branch: `pestopoppa/llama.cpp` branch
  `ak/glm53-recovered-accumulator-20260912`, tip `dc3798db10a6654721f2a1fa6a162be2e5fdf95f`

## Production-anchored dashboard trajectory

Corrected the new AutoKernel trajectory headline so its primary axis is the champion's directly
measured gain against frozen production, not campaign-local CoR accumulation. Commit `262b22d3`
adds an exact bounded join across producer raw receipts, full champion identities in kept rows,
and `champion_vs_production` ledger rows. Curves are grouped by recorded model and surface;
unlabelled or unjoinable evidence remains explicit, and unrelated marginal effects are never
composed. The prior CoR plot remains available only as a secondary drill-down.

Live `/mnt/raid0/llm/autokernel/loop-memory` projection resolves production-v9
`0db32c06e3e5`, explicit Qwen3.8 `tg128` (`bff30cebee0d`, `+5.633302%`) and `dec-b4`
(`b0eb4fab4729`, `+22.442869%`) curves, two model-unrecorded legacy surface curves, and two
unjoinable gaps. The GLM store has no production-anchored checkpoint, so its 23-keep
`+0.830381%` bench comparison and two inconclusive serving checks remain CoR-only. Validation:
79 focused tests plus 5 executable browser subtests passed; focused Ruff, Python compilation,
and diff checks passed. GitNexus reports LOW upstream risk. No process reload, runtime state,
registry, production kernel, or supervisor file changed.

### Trajectory correction: normalized history, live promotion chain, and baseline epochs

The first production-only projection was incomplete: legacy GPU receipts lacked model identity,
CPU whole-candidate checkpoints lived outside the loop store, the current global accumulator hid
the active GLM campaign, and a single production axis could imply continuity across incompatible
recipes or future production releases. RESEARCH `323bcf2c` plus exact-effect follow-up `3a4be85d`
adds the bounded normalizer `historical_trajectory.py`; it fails closed when its exact receipt/doc literals change and emits
source hashes, model/surface/recipe/era identities, baseline identities, conflict states, and the
active campaign locator. ROOT `ebb98492` consumes that bootstrap together with current producer
receipts and the retained accumulator promotion chain.

The live v3 payload now contains 12 isolated curves: DeepSeek-R1-Distill-Qwen-1.5B `tg128` and
`dec-b4` (including `a2728701` `+12.618%`), Qwen3.8-27B `dec-b4` `-1.414%` / `+22.443%` and
`tg128` `+5.633%`, Gemma `+7.206%`, six Flash-Next CPU plain/MTP recipe-era curves against
pristine `c51e4dabf`, and the active GLM-5.3 23-keep `+0.830381%` provisional chain against its
CoR. It explicitly marks the overwritten/conflicting Qwen `+27.363%` record and missing current
`ef81196d` production A/B. Production-v9 is a dated vertical zero-percent release epoch; synthetic
v10 tests prove the old segment is preserved, a new segment starts, and a model first covered in
v10 is not backfilled onto v9. A simulated retained-bundle promotion test proves a new tip appears
without editing static history or dashboard code.

Verification: research normalizer 2/2 tests; dashboard loop surface 81 passed, 33 skipped, and 5
browser subtests passed. Live `http://127.0.0.1:8100/api/loop` serves schema
`epyc.dashboard.autokernel_improvement_trajectory.v3`, one v9 release marker, two explicit
exceptions, GLM campaign `aku12a-glm53-five-loop`, 23 keeps, and `+0.8303809823155373%`.
The hub process was already refreshed by its supervisor. `/api/health` remains degraded because
of unrelated stale/absent producers; no runtime campaign state, production kernel, registry,
supervisor PID, or supervisor log was changed.

## Unified headline layout, epoch grammar, and experiment overlay

ROOT `a3cf6d0a` makes the champion trajectory the first Kernel R&D surface. It absorbs champion
identity and direct comparison, active/iteration tiles, production-baseline epochs, and the
experiment-event layer. The old standalone Champion and Progress sections are absent. A responsive
two-column row immediately below retains Champion Capabilities and the Accumulator, including
retained keeps, cumulative-estimate validity, serving-gate cadence/status, and the producer's
noise-floor wording and identity. The full knowledge ledger is a default-collapsed accordion;
controls remain in their operational sections.

The v3 SVG adopts the Autopilot instrument-era grammar without coupling the dashboards: low-opacity
epoch bands, dashed colored release boundaries, concise labels, full title metadata, and explicit
instrument discontinuities. ROOT `ab1a34c5` replaces the initial multi-recipe scatter with exactly
one headline trajectory per model. Each model selects its longest exact surface history (plain wins
ties); secondary surfaces remain selectable and their percentages are never blended. Recipe,
harness, backend, metric and baseline identities are checkpoint/epoch metadata rather than legend
categories. Singleton models are labelled milestones, not curves.

Only retained/promoted checkpoints render as dots. Nulls, regressions, formation refusals,
invalid/setup outcomes and other attempts remain in the default-collapsed knowledge ledger and do
not appear in the SVG. Each keyboard-selectable keep shows mechanism, marginal and cumulative
effects, floor/confidence, commit, timestamp and instrument epoch on hover, then opens a persistent
side panel with recorded hypothesis/profile, patch/commit, comparison, critic, applicability,
identifiers and evidence fields; absent producer fields render explicit unknowns.

The trajectory mounts first through an isolated error boundary; sibling renderer failures cannot
prevent its SVG from appearing. Focused validation passed 15/15, Python compilation and diff checks.
The final broader loop selection passed 85 tests, 33 skips and 5 browser subtests. Live `:8100`
proof showed transport health OK, schema v3, five unique model IDs and five headline trajectories.
The default is Flash-Next plain with exact geometry x=`64 → 443.565 → 956` across commits
`6f032c48 → 9c4f73e2 → ef81196d`; the MTP selector shows the same commit/date order. The DOM has
one SVG, two dashed instrument connectors, three keep-only dots, zero non-keep dots, no filters or
recipe legend, a persistent evidence side panel, and no render exceptions.
GitNexus reports LOW upstream risk (three dependants) for `improvement_trajectory`; the inline JS
renderer is not indexed. No campaign state, registry, supervisor files, or production kernels changed.

## Keep-history and browser-interaction correction

The preceding DOM-only verification was insufficient: real Chromium reproduced the detail panel
opening and then disappearing at the next 20-second refresh. The renderer now preserves its DOM
when its trajectory data is unchanged, restores the selected keep when data changes, and provides
an immediate visible hover card. Close/Escape and keyboard activation restore focus correctly.

The prior dots represented A/B checkpoints, not all keeps. A dedicated keep query now selects
kept rows before applying a bound and merges active retained-bundle membership. Actual keeps drive
markers; measurement checkpoints alone do not assert a keep. A keep without a cumulative checkpoint
uses a timestamped keep rail; a retained member without its original timestamp is explicitly undated.
Disposition counts are inside the default-collapsed knowledge accordion.

`tests/js/trajectory_browser_check.cjs` exercises the served page in Chromium: select GLM, verify
23 keep markers and zero non-keep markers, hover, click, refresh, wait through a natural poll,
verify panel persistence, close with Escape, and reopen with Enter. The live check passed with zero
page errors; screenshot: `/mnt/raid0/llm/tmp/autokernel-keep-panel.png`. Existing static-JS and loop
surface tests passed (75 plus five subtests). Browser dependencies were extracted into the research
cache without installing system packages. GitNexus was attempted; index recovery failed, and the
inline renderer is unindexed. Direct caller inspection and the real browser check cover this edit.

Operator follow-ups clarified that markers below 0% looked like losses and that the old +5.6%
summary still occupied the first card. The keep timeline is now outside the percentage axis,
and the old champion summary/Progress tiles and their unused renderers were removed entirely.
The champion renderer retains only the capabilities card. Historical A/B evidence remains in the
trajectory; the current task does not reclassify any measurement or modify the running campaign.

Final all-model recovery (`a0f3daee`, `154bfee6`) exposes 73/73 retained changes without truncation:
DeepSeek screen 28, Qwen3.8-27B 4, Flash-Next CPU 18, GLM 23; none are unassigned. Manual records
carry fold-inventory provenance and recovered GLM entries carry bundle provenance. Sixteen original
timestamps, two commits, fourteen hypotheses, thirty-two marginal effects, and forty-one
floor/comparison records remain unavailable; the UI does not create values for them.
The real Chromium check now compares every model's rendered marker count with the dedicated
history feed and exercises hover/click for every nonempty model, then GLM refresh persistence and
keyboard interaction. It passed with counts 28/4/18/23 and zero page errors. The Gemma curve has a
direct measurement but no independently recorded retained change, so no keep marker is invented.
The final trajectory/static-JS suite passed 21 tests; the retired-summary test migration passed
32 tests plus five subtests. Prior DOM-only completion claims are superseded by this browser check.

## GLM planner/critic formation-payoff deadlock

The continuous GLM campaign remained alive but stopped producing useful experiments: batches 27–34
made 24 first-pass critic calls and reached zero authoring, builds or measurements. The sampled CPU
profile supplied source-route attribution, while proposals named exact eligible-call census,
request-wall exposure and isolated local-speedup checks as falsifiers. The critic incorrectly made
those ordinary post-authoring payoff checks mandatory formation evidence. The planner could only
return another hypothesis, not collect the requested trace, so three revisions exhausted every
batch. Historical Qwen GPU work suffered formation refusals too, but exact device-kernel timing and
larger remaining headroom masked the control-contract defect.

Research commit `5ac7b7e4` makes the narrow correction in `loop/actors.py`: the planner must not
promise unsupported prerequisite traces, and the CPU critic must allow a bounded, source-consistent
candidate to reach the existing correctness and matched A/B pipeline when only its payoff is
unknown. Review remains strict for already measured/present mechanisms, wrong or incomplete source
routes, invented evidence, absent falsifiers and correctness/safety risks the existing gates cannot
contain. Two focused contract regressions were added; planner/critic plus loop validation passed
**74 tests**.

The retained store also contained an inbox directive that demanded the unavailable wall-time and
local-speedup proof before authoring. It was corrected operationally in place while preserving its
diminishing-returns and abstraction-escape guidance. No experiment row, retained bundle member or
one of the 23 accumulated GLM keeps was removed or rewritten. Batch 41 had imported the old Python
module before publication and completed under the superseded contract. Continuous batch 42 started
afterward and its process command proves the corrected planner text is loaded. The campaign remains
continuous; this checkpoint makes no claim about batch 42's still-pending scientific disposition.
No separate typed diagnostic-action framework was filed: it is unnecessary to clear this observed
defect, and adding it now would reintroduce speculative control-plane friction rather than improve
the working source-author/build/measure loop.
