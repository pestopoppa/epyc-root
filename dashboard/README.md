# EPYC Project Dashboard Hub

A tiny, dependency-free web server (Python **stdlib only**) owned by the
governance repo (`epyc-root`). It is the project's **view plane**: every
dashboard page, the shared nav, and the machine-readable dashboard directory
live here. Its first view was the **handoff progress board** — a kanban of
`handoffs/{active,blocked,completed,archived}` plus a git-derived
progress-over-time chart; it now also serves the machine monitor and the
autopilot page.

## The ownership boundary (plane rule — RTG-47, ratified 2026-08-10)

> **Data plane** — JSON/SSE endpoints and exported file contracts — lives
> **with the subsystem it observes** (orchestrator `:8000/dashboard/api|events/*`,
> AutoKernel's exported contract, …). That repo owns the schema.
> **View plane** — every page, `static/nav.js`, `dashboard/registry.json`, the
> freshness grammar — lives on **this hub** (`:8100`).
> A page served here fetches another process's data directly from the browser
> (the orchestrator allows the hub origin via a path-scoped CORS layer,
> `epyc-orchestrator/src/api/dashboard_cors.py`); nothing is proxied, the hub
> stays stdlib, and a dead producer renders as an honestly-dead panel rather
> than a dead page.

History: the boundary used to be a *transport* rule ("needs live in-process
state → orchestrator serves the page"), which is how the 7.6k-line combined
page on `:8000/dashboard` accreted. That page is **legacy, pending Phase-1b
deprecation** (`handoffs/active/dashboard-architecture-restructure.md`) — its
data routes stay; its page is superseded by `/machine` + `/autopilot` here.
**Adding a dashboard = three things, not one.** All three are load-bearing and all
three are checkable:

1. **A registry entry** in `dashboard/registry.json` — the shared nav and the
   directory strip render from it. Hand-adding cross-dashboard links to a page is
   the drift this registry exists to end.
2. **A health probe** — the `health_path` field on that entry. All 7 current
   entries declare one, and a surface with no probe cannot be told *down* from
   *slow*. **But know what it answers.** Every entry points at `/health`, which is
   the **TRANSPORT** probe: it says *this process is serving* and nothing more, so
   it stays green while the producer behind a panel is dead. The honest question —
   *is what this page shows still true?* — is `/api/health`, the three-valued fold
   over `dashboard/panels.py` (`ok` / `absent` / stale). A registry entry buys you
   liveness of the SERVER, not freshness of the DATA; an automated consumer that
   treats `health_path: /health` as "the dashboard is fine" is reading a narrower
   claim than it thinks. (Raised by `mainC` 2026-08-12 against the first version of
   this list, which said "health probe" without saying which one — the same
   true-about-a-smaller-set shape this repo has hit four times in a day.)
3. **A freshness envelope** for every panel — a producer, a timestamp field, a
   staleness bound and an `absence_means` string (`dashboard/panels.py`). Absence
   must say what absence MEANS, or a panel that renders nothing is
   indistinguishable from a panel whose producer died.

**No unregistered pages.** A page reachable but absent from the registry is
invisible to the nav, has no probe, and no one learns it exists — which is how the
7.6k-line `:8000/dashboard` page accreted in the first place.

## Running

```bash
# from the repo root
python3 -m dashboard.server --port 8100
# or
python3 dashboard/server.py --port 8100
```

Then open <http://localhost:8100/>. Under normal operation the hub is started as
a managed service by `epyc-orchestrator/scripts/server/orchestrator_stack.py`
(one more service with a `/health` probe), so it comes up and down with the rest
of the stack. No third-party dependencies — it runs under any `python3` (≥3.9);
the orchestrator's venv is **not** required.

## Layout

| File | Role |
|------|------|
| `dashboard/server.py` | stdlib `http.server` app: page + JSON endpoints + `/health` |
| `dashboard/panels.py` | **SSOT panel→producer registry**, per-panel freshness envelope, transport watchdog, `/api/health` fold |
| `dashboard/arena_attempt_dispositions.json` | Exact-attempt, one-way Arena integrity retractions for the Kernel-R&D view |
| `dashboard/handoff_parser.py` | pure parser: cards, tasks, status-derived Blocked column |
| `dashboard/freshness.py` | the one age→`fresh/aging/stale/missing` classifier (+ a legacy mtime badge) |
| `dashboard/loop_status.py` | read side of the **rebuilt AutoKernel loop's** `loop-status.json` contract: four-valued freshness + derived folds |
| `dashboard/static/handoffs.html` | kanban UI + modal + hand-rolled SVG charts (no framework, no CDN) |
| `dashboard/static/loop.html` | the AK Loop page: state, freshness banner, dispositions incl. negatives, GPU held-vs-busy |
| `scripts/handoffs/build_handoff_timeline.py` | git-history → `data/handoff_timeline.json` |
| `scripts/handoffs/install_timeline_hook.sh` | post-commit hook that regenerates the artifact |
| `tests/test_handoff_parser.py`, `tests/test_handoff_timeline.py` | `unittest` suites |

### Endpoints

- `GET /` — the board page
- `GET /health` — `{"status":"ok","probe":"transport"}` — **transport liveness only**
- `GET /api/handoff_board` — compact cards for all four columns (live scan, 30 s cache)
- `GET /api/handoff_detail?id=<state>/<stem>` — full card + scrubbed markdown body (path-traversal guarded)
- `GET /api/handoff_timeline` — the git-derived timeline artifact + freshness
- `GET /api/kernel` — the AutoKernel `/kernel` contract (v2, v1 still readable) + freshness
- `GET /api/kernel/live` — active discovery lock/state plus bounded, secret-free
  AutoKernel and planner lifecycle tails from the deployment-owned live contract
- `GET /api/kernel/health` — Kernel-R&D producer/data health only; HTTP 200 when
  fully reported and current, HTTP 503 with `absent`/`degraded` detail otherwise
- `GET /loop` — the **rebuilt AutoKernel loop** page (separate surface, separate
  producer; see below)
- `GET /api/loop` — that loop's `epyc.autokernel.loop_status.v1` report + its panel
  envelope. `loop` is `null`, never `{}`, when nothing readable was found
- `GET /api/loop/health` — the loop's producer/data health; HTTP 200 only for `ok`,
  HTTP 503 with `absent`/`degraded` otherwise
- `GET /api/bus`, `GET /api/queue`, `GET /api/outcome`, `GET /api/benchmark_artifacts`
- `GET /api/health` — **the fold**: every registered panel's envelope + one verdict

Routes are **tables** (`HTML_ROUTES`, `API_ROUTES`, `API_ROUTES_WITH_STATUS`,
`PROBE_ROUTES`), not an `if/elif` chain, so the surface is enumerable and
`panels.registry_gaps(server)` can fail when a panel has no registered producer.

## Panel → producer registry, freshness envelope, watchdog (AK6)

`dashboard/panels.py` exists because of one scar: the `/kernel` page was
**absence-tolerant over a missing directory** — it rendered clean when its
producer was dead, the same shape as AutoPilot dying at trial 1302 and staying
dead ~23 h with every dashboard green. A panel that cannot distinguish *"nothing
is wrong"* from *"nobody is reporting"* is worse than no panel, because it is
trusted.

* **Registry** — every panel declares its producer, repo, evidence artifact,
  semantic timestamp field, thresholds, and **what its absence means** (mandatory,
  enforced in `PanelSource.__post_init__`). The registry is checked against the
  *code*, both directions, by `registry_gaps()`; a panel that loses its entry makes
  the hub refuse to import rather than serve an unsourced card.
* **Envelope** — `staleness_class` (`fresh`/`aging`/`stale`/`missing`) **plus**
  three orthogonal fields that keep absence from looking like emptiness:
  `artifact_present`, `reporting` (`observed`/`silent`/`absent`), `content`
  (`populated`/`empty`/`unknown`). Dated by **producer-written timestamps**, never
  by mtime.
* **Watchdog** — two arms. *Age*: the newest semantic timestamp stopped advancing
  past `silent_after_s` → `stopped_reporting` (the trial-1302 detector, stateless,
  survives a hub restart). *Watermark*: timestamps advance but the producer's
  progress identity does not → `not_advancing`. A producer that **declares** it is
  stopped reads `idle`, not dead.
* **Fold** — `/api/health` is three-valued (`ok` / `absent` / `degraded`), is
  **total over the registry** (a registered panel with no envelope is `degraded`
  and named — `fold({})` is not `ok`), and carries two names: `worst` (worst by
  severity score) and **`status_set_by`** (the panel that actually produced
  `status`). They are frequently different — live, the fold is `absent` because
  of `kernel` while `worst` is `bus` — and pairing one's colour with the other's
  sentence points at the wrong repository.
* **`gates_health` governs noise, not death.** A **watchdog alarm always gates**,
  on every panel: `status: ok` beside `worst.watchdog: stopped_reporting` was the
  trial-1302 dashboard rebuilt with better words. Staleness and benign absence
  are still gated by `gates_health` / `absence_is_anomalous`. A producer whose
  silence is genuinely normal declares `watched=False` (`bus`, `queue`); a
  producer that has stopped **declares** it (`sections.campaign.stopped`,
  `outcome_progress.paused`) and reads `idle`. The hub never infers idleness.
* **A timestamp in the future is a defect, not freshness.** `age` is clamped at
  zero, so a skewed producer clock would otherwise buy a permanently `fresh`
  panel; past `FUTURE_SKEW_TOLERANCE_S` the report is treated as undated
  (`watchdog: future_timestamp`).
* **Broken ≠ never exported.** `artifact_present` answers "does a file exist",
  not "could it be parsed"; an unreadable export carries `_reader_error`, dates
  nothing, and is never labelled a readable legacy contract.
* `/health` stays transport-only because
  `scripts/dashboard/hub_supervisor.sh` restarts the hub on a non-ok body, and
  restarting the dashboard cannot revive a producer in another repository.
* `/api/kernel/health` is the non-recursive Kernel-R&D data probe used by the
  dashboard registry. It reads and folds only the `kernel` envelope; it never
  calls the global `/api/health` fold. This lets registry consumers see a live hub
  and an absent/partial AutoKernel producer as two different facts.

Producer side (contract v2): `epyc-inference-research` →
`scripts/kernel_rnd/autokernel/dashboard.py`. The campaign driver exports only
after its terminal `STOP_STATE` is fsynced, to the durable
`/mnt/raid0/llm/autokernel/surface/kernel_dashboard.json`
(`KERNEL_DASHBOARD_JSON` still overrides the reader for tests). The terminal
journal timestamp, not export time, drives freshness.

Live discovery visibility is a separate producer contract:
`operations/live/{autokernel,planner}.jsonl`, schema
`epyc.autokernel.discovery_live_event.v2` (consumer also accepts the exact
historical `v1` field set), frozen at producer commit
`76301d6647586a25f2d56de1b93f1da9ac11a3fa`. v2 binds every row to a
64-hex operation key and content-derived `ake-<sha256>` event identity. Planner
rows are mirrored byte-identically into both physical streams; the hub
deduplicates matching identities, degrades health on a missing mirror, and drops
same-identity payload, timestamp, duplicate, or sequence-order corruption.
The hub opens and takes shared locks on both streams in the producer's
global-then-planner order and holds them through one bounded snapshot and
reconciliation. Directory/file descriptors are no-follow, owner-bound,
single-link, and checked against their current path identities both before and
after each read; size/mtime/ctime drift also invalidates the attempt. A final
all-stream identity/content-epoch barrier runs after strict reconciliation and
immediately before return, catching mutations to the first stream during the
second stream's read. The hub
therefore cannot mistake the transaction's global-first
midpoint for a missing mirror. A writer that outlasts the bounded snapshot wait
is shown as `producer_write_in_progress` without gating health; an unlocked,
actually missing mirror remains degraded and health-gating.
Append-only `visibility_degraded` state markers remain visibly auditable as
historical incidents but do not keep current health red after exact mirror
equality is restored. The actor seam writes only an
allowlisted lifecycle vocabulary, provider/model identities, return codes,
decisions and transcript hashes. Prompts, model text, commands, environment and
credentials are structurally excluded. `/api/kernel/live` also observes the
deployment's controller lock, so a long first planner call is visible before its
first durable state checkpoint; that lock observation never exposes or scrapes
the ephemeral actor container. When several sealed deployments coexist, the
activity hero selects a held controller first, then the terminal deployment with
the newest producer-authored progress timestamp. A newer config-file mtime never
turns a real failed run into “idle.” The newest bundle with no controller state,
checkpoint, or lifecycle event is exposed separately as
`newest_unlaunched_deployment` (`launch_state: not_launched`); it is availability
context and does not affect liveness or freshness. That field is populated only
when the unlaunched bundle is newer in seal/progress order than the selected
meaningful campaign; once v7 is active, an older unlaunched v6 is superseded
history rather than an “available next” deployment.

The live fold also distinguishes actor completion from controller completion. If
the planner reports `planner_completed`, the controller lock then disappears,
and no critic event, state, checkpoint, or operation follows, the page reports a
terminal `planner_validation` interruption—not “idle / awaiting launch.” It says
that the exact exception was not persisted, marks resume unsafe, and records that
GPU screening was never reached. Explicit future
`planner_validation_failed`/`planner_validation_refused` lifecycle events map to
the same stage without relying on that inference.

Pending-state phases retain their controller ordering. A durable
`pending.phase: critic_pending` plus `critic_started` is rendered as active
critic review, with planner validation complete and authorization/resource
admission not reached. `critic_complete` advances to authorization; resource
admission is shown only after the pending record carries a persisted
authorization. This prevents a live critic actor from being mislabeled as an
idle GPU wait.

Post-build proof is likewise identity-bound before it reaches the page. The hub
accepts a completed correctness execution only when the inflight operation key
and manifest match the operation intent and evidence policy, the native backend
summary is present, and the same operation carries its released GPU proof claim.
This lets a terminal producer-parser failure report `correctness_validation`
after a completed GPU run (including duration and passed/total), rather than
falling backward to `evidence_binding` or claiming that GPU screening never ran.
Dispatch attribution, profiling, and benchmarking remain `not_reached` unless
their own evidence exists.

The cross-strategy lifecycle is projected from the inflight operation's native,
self-hashed receipts, never from process names or an output-directory mtime:
`proof/correctness/receipt.json`,
`proof/attribution-{candidate,anchor}/receipt.json`,
`proof/attribution-pair.json`, `proof/proof-bundle.json`, and
`runner/sN/{measurement-graphs-off,target-runtime-graphs-on}/result.json`.
Those receipts expose correctness execution/validation, both attribution arms,
the graphs-off measurement screen, the separate graphs-on target-runtime
screen, decision, S1/S2, the counterbalanced attribution order, and the exact
first incomplete resume stage. A stopped controller keeps completed receipts
complete and names the one stage a restart will execute; it does not fall back
to a generic failed screen. The operation-owned device-claim journal supplies
expected/held/released state, with a held claim requiring the captured PID and
start tick to remain live. A durable screened checkpoint is rendered as the
automatic transition to the next portfolio hypothesis, whether the controller
is still running or waiting for restart.

Governed terminal rows are also headline state. `source_apply` and `compile`
map to `authoring_refused`; correctness maps to `correctness_falsified`; and
dispatch attribution maps to `attribution_route_falsified`. The dashboard
follows the row's declared `stage_receipt_path`, verifies
`stage_receipt_sha256` against the exact file bytes, and then projects the
typed class, stage, disposition, and `scientific_budget_spent` value. This
includes both per-arm attribution refusals and the cross-arm
`proof/attribution-pair-refusal.json` invariant terminal. Planner provider
interruptions remain `planner_transient` on the same turn and expose
the durable `provider_attempt`; a critic interruption resumes only from
`pending.phase=critic_pending`. Neither is displayed as a scientific refusal.
A measurement invocation is additionally resumable at its exact arm boundary
under the contract frozen at producer commit
`eb689b0d3239f7af538015a7ccb098fe8169f9e6`. The hub validates the canonical
`preflight.json` content hash and each private
`process-{anchor,candidate}/receipt.json`
(`epyc.autokernel.gpu_discovery_process_receipt.v1`) before it calls an arm
complete or reusable. A process checkpoint names the completed arms, the next
arm, graph mode, and first incomplete screen without exposing the mode-0600
stdout/stderr bytes. A terminal sibling `process-<arm>-refusal.json`
(`epyc.autokernel.gpu_discovery_output_refusal.v1`) is rendered as
`measurement_output_refused`: its exact arm, timing-validation reason code,
bounded native/rederived timing carriers, and reusable earlier arms remain
visible, while the raw controller reason and captured process output never
cross the dashboard API. The matching
`portfolio_measurement_output_failures`/`portfolio_skips` state is projected as
either a distinct-candidate retry or the bounded non-scientific skip, including
the exact attempt count and next recovery boundary.
A nonpositive exact-attribution result is instead measured evidence from
`runner/sN/exact-attribution-outcome.json`: both runtime screens show as
governed skips, the graphs-on call is explicitly unexecuted, and the loop moves
through decision to the next hypothesis. Completed iteration rows retain both
exact-attribution and target-runtime effects plus their S1/S2 repetition.

An explicitly sealed `campaign_kind: experimental_runtime` uses an isolated
dashboard adapter rather than the kernel-source pipeline. Its deployment
descriptor has schema `epyc.autokernel.experimental_runtime_dashboard.v1`, a
bundle-contained runtime root, the fixed DFlash2 sibling stage order
`experimental_build → cpu_gpu_regression → matched_np1 → concurrency_grid →
greedy_parity → decision`, and a bounded silence budget for every stage. Each
completed stage is proven by a private, self-hashed
`epyc.autokernel.experimental_runtime_stage_receipt.v1` receipt chained to the
exact preceding receipt file hash. The first missing or invalid receipt is the
only resumable boundary. The live API exposes compact np=1, np=8, parity, and
decision headlines and marks the sibling excluded from the kernel-source
champion frontier; it never feeds these results to discovery progression.
Deployments without `campaign_kind` retain the existing kernel-source behavior.

Discovery/progression is a second, additive contract:
`scripts/benchmark/autokernel_progression.py` projects immutable CPU/GPU screen
and strict campaign receipts into
`/mnt/raid0/llm/autokernel/surface/kernel_progression.json`. The hub exposes it
as `_progression`; it never overwrites terminal `sections`, never mints a
champion, and requires `promotion_claim: false`. Its top layer is the operator's
ten-second scan (production anchor, CPU/GPU leaders, direction-correct effect,
workload and candidate → strict keep → champion → promotable counts). Candidate
cards keep only resource, lever, verdict, effect, and phase/workload exposed;
regime, gate/next prose, evidence paths/hashes, vectors, and spread live in
closed per-item disclosures. Pursued and abandoned/retest rows use the same
compact contract, and historical rows remain closed by default. The current
phase hero, last producer transition, and short timestamped AutoKernel plus
planner/critic tails remain visible; full streams, pipeline, checkpoint, full
timeline, and implementation/readiness diagnostics are closed by default. Poll
time is labelled as dashboard refresh, never producer progress, while each live
tail shows the last producer timestamp and age. Strategy and unexplored
hypotheses form the second layer; all former detailed cards remain under
**Evidence & diagnostics**. The whole progression surface is itself closed by
default behind a one-line CPU leader, GPU leader, and funnel headline. The two
short log tails are never inside a disclosure: they are the loop's operational
pulse, not optional evidence detail.
When progression is populated but strict champion/headroom/release owners are
unreported, panel and global health say `degraded`, never `ok` and no longer the
false `absent`/“nobody is reporting” state.

The hub also adds `_activity`: committed AutoKernel history, durable
`data/autokernel_*` bundles, in-progress timestamp markers, a bounded journal
inventory, and an evidence-backed `current_state` snapshot. The snapshot keeps
the operator-ratified production freeze separate from the latest fixed-panel
audit, available-source diagnostic, and empirical-smoke receipts under
`/mnt/raid0/llm/autokernel/probes`. It always carries `promotion_claim: false`:
audit readiness and a diagnostic smoke cannot promote or freeze a kernel. All of
this is presentation context only. It is structurally excluded from `_freshness`
and `/api/health`, so a commit, audit, or A/A artifact cannot make an absent or
dead campaign look alive.

`current_state.arena_campaign_progress` discovers v1/v2 Arena attempts under the
AutoKernel campaign root and selects a PID-identity-proven live attempt before
the newest semantic `ended_at` of a hash-verified completed checkpoint, never by
directory mtime or worker-request markers. Live means a controller sandbox's
captured PID still has the captured `/proc` start tick; a dead/reused PID reads
`stale_or_terminal_unreported`, not stopped. It verifies the manifest/audit
identity, checkpoint and cell self-hashes, and v2 measurement-window
claim/release and sampler evidence. The view exposes attempt receipt identities,
output roots, completed checkpoint/cell counts, the current live cell, the last
completed empirical checkpoint, and individual observations. An incomplete
matrix has no aggregate and remains explicitly non-rankable. Preflight-only
refusals are listed separately because they launched neither a controller nor a
GPU command. These fields are evidence inventory and not part of Kernel-R&D
health.

Cross-artifact integrity retractions live in the hub-owned, versioned
`dashboard/arena_attempt_dispositions.json`. Rows bind both the producer's exact
manifest self-hash and run directory. This overlay is deliberately one-way: it
may reduce a hash-valid attempt to stopped diagnostic history, forbid resume and
withhold ranking/release authority, but it cannot admit evidence or make a
producer healthy. The r4 INF-03 attempt is retracted here because its
KernelFoundry controller made 64 intermediate evaluator calls outside the two
durable GPU claim windows; the page keeps the partial checkpoint inventory
visible while labelling the campaign evidence invalid.

The seven-arm inventory also carries exact-manifest terminal dispositions. R14
and R15 are one-way retractions: source-identity drift and structured-output
exhaustion respectively made them invalid diagnostic history. R16 is a terminal
preflight refusal with no controller/GPU execution. R17 is shown as live only
while an exact sandbox PID/start-tick identity remains resident; otherwise its
state becomes stale/unreported rather than being guessed terminal. The separate
implementation-readiness card projects four reviewed research-main anchors
(retry hardening, SC33 v2 writes, C3/C5 capture/mapping, and AK-DEL-2 catalogue
expansion) while keeping their outstanding empirical or acceptance work visible.
Mainline code readiness never closes those evidence gates.

The available-source readiness card prefers the v2 `receipt.json` contract, which
admits exact-source EvoEngineer and reports the current **7/7** diagnostic panel;
the former v1 `available-source-six-arm.json` lookup remains a historical fallback.
The v2 static audit remains readiness evidence only: controller/GPU execution is
false and ARGUS remains excluded from the separate 8/8 panel. The separate r15
pilot below now satisfies the isolated one-task gate for starting a fresh 7/7 campaign.

The governed one-task/K-Search pilot ladder (`r1` through `r15`, 2026-08-12) now
has one terminal compatibility receipt. R13 and r14 remain invalid validator
failures; r15 completed one task and one round with six `gpt-5.6-sol:high` calls,
one brokered intermediate evaluation, and a final centralized evaluation. The
`epyc.autokernel.arena_diagnostic_pilot.v1` card verifies the receipt self-hash
and explicit no-authority constraints before rendering producer `PASS`, final
compile/correctness, sampler-window releases, controller device blindness, and
cgroup teardown. Its loud `NO CAMPAIGN AUTHORITY` boundary is load-bearing:
the pilot does not imply a matched campaign, rank a controller, update belief,
or authorize promotion/release. The separate 7/7 panel remains the next campaign.

`current_state.hip_decision_grade` is a curated projection of the terminal
`hip-silu-decision-grade-20260812-r6/receipt.json`. The hub verifies the receipt's
self-hash, exact producer/schema/task, complete 24-case correctness vector,
block-9 e-process crossing, all 40 per-arm duration admissions, and the physical
file digest before rendering it. The card is deliberately separate from the
champion/release plane: it says `NOT A CHAMPION`, preserves
`task_local_rank_no_release_or_promotion_authority`, and names experimental
llama integration as a prerequisite. Like the other `_activity.current_state`
cards, it cannot make Kernel-R&D healthy or fresh.

`current_state.hip_decision_grade` is a curated projection of the terminal
`hip-silu-decision-grade-20260812-r6/receipt.json`. The hub verifies the receipt's
self-hash, exact producer/schema/task, complete 24-case correctness vector,
block-9 e-process crossing, all 40 per-arm duration admissions, and the physical
file digest before rendering it. The card is deliberately separate from the
champion/release plane: it says `NOT A CHAMPION`, preserves
`task_local_rank_no_release_or_promotion_authority`, and names experimental
llama integration as a prerequisite. Like the other `_activity.current_state`
cards, it cannot make Kernel-R&D healthy or fresh.

The Kernel-R&D page executes its current-state renderer in the static-JavaScript
suite, not just a syntax parser. This matters because the complete-kernel-set card
once referenced a free identifier: the script parsed, the API remained complete,
but rendering stopped before controls, empirical gates, activity, or the seven
contract sections. Producer-authored blocking-condition details are rendered in
full, so a generic `PREFLIGHT_REFUSED` label cannot hide the actionable gate. The
production-set card also labels tree identity, observed versus attested ggml
generation, non-executing `readelf` linkage, and dashboard-process ambient
`LD_LIBRARY_PATH` as distinct claims rather than folding them into one green mark.

### The seam: what the hub owns of the producer's document

The hub is stdlib-only and **never imports the producer's package** — a consumer
that needs its producer's code installed goes dark when the producer's repo
moves. That means the schema strings, the section status and the export path are
literals here, and literals drift. Two rules keep them honest:

* **Hub-derived fields are underscored.** `/api/kernel` serves the producer's
  document *plus* `_contract_version`, `_freshness`, `_render` and the separate
  `_progression` projection. It used to
  overwrite `contract_version` — a key the producer owns and writes as the
  integer `2` — with the string `"v2"`, so the body the hub served no longer
  validated under `schemas.validate_kernel_dashboard_v2`. The seam suite now
  asserts every producer key survives byte-identical and that what is served
  still validates as a contract.
* **The empty-state sentence is derived on the wire** (`server._kernel_render`),
  not written into `static/kernel.html`. v2 carries seven owner sections and *no
  run log*, so the page's hardcoded *"no runs recorded yet — the kernel-R&D loop
  has not exported any results"* was printed over a **fully reported** contract:
  the same scar, in the render layer, pointing the other way. The page now draws
  the section table from `d.sections`, shows the reporting banner
  (`reporting`/`content`/`watchdog`/`absence_means`) above the fold, and prints
  `_render.note` where it has nothing of its own to draw.
* **`evidence` names the file that was actually read.** The registry declares the
  default; the two env-overridable readers (`KERNEL_DASHBOARD_JSON`,
  `AUTOPILOT_OUTCOME_JSON`) put the resolved path in the envelope and keep the
  declared one under `declared_evidence`. A card that names a path the hub is not
  reading sends an investigation to a file nobody wrote.

The producer is tested in
`epyc-inference-research/scripts/kernel_rnd/autokernel/test_dashboard.py`; the
consumer and cross-document seam are tested in `tests/test_dashboard_panels.py`.
The latter carries the **restart chaos test**: producer alive and reporting →
producer dies → time passes → the
board goes from green to naming it, and keeps naming it across a hub restart
(the age arm is stateless by design). Death is simulated by not exporting and by
injecting the clock — **nothing is started, signalled or killed**, and the suite
audits its own source to keep it that way.

### Known open items on this surface

* **`AUTOPILOT_OUTCOME_JSON` defaults to `/mnt/raid0/llm/tmp/autopilot/…`** — the
  ephemeral sweep root the kernel export was moved *off*. No exporter writes it
  yet and the path belongs to epyc-orchestrator, so it is flagged here rather
  than changed. The `outcome` panel is watched regardless: it is the panel the
  trial-1302 outage happened on, and its 6 h budget is what turns "dead for 23 h"
  into a named verdict.
* **Nothing schedules the kernel export**, so `/api/health` reads `absent` on
  this host today — correctly, and loudly, which is the point.
* **`queue_payload` / `bus_payload` bodies still emit `count: 0`, `agents: []`,
  `tokens: {…: 0}` over absent files.** Only their `_freshness` envelopes
  distinguish absent from empty; changing the bodies would break consumers for no
  gain.
* **`do_GET` still has a hardcoded `elif route == TRANSPORT_PROBE_ROUTE`** ahead
  of the tables, so a *second* `PROBE_ROUTES` entry would be registered and
  enumerable but not served.
* **`registry_gaps` does not include `HTML_ROUTES`** in its route universe.
* **Nor `ASSET_ROUTES`** (RTG-47 Phase 0, `/nav.js`), and for the same reason:
  pages and generated assets are not panels over a producer's evidence, so they
  are deliberately outside the panel-registry universe. The nav asset's *content*
  is `dashboard/registry.json`, whose reporting **is** a registered panel
  (`dashboards` → `/api/dashboards`); registering the asset as well would give one
  fact two registry entries. The asset builders are therefore named **without** the
  `_payload` suffix so `discover_payload_functions` does not count them — which
  means the exemption rests on a naming convention, and this bullet is where it is
  declared rather than assumed.
* **A `refused` section reads as `not_reported`.** The producer distinguishes a
  refusal (e.g. a champion record that failed validation) from silence; the hub
  folds both into `unreported` and its verdict sentence says "has no producer".
* **`/api/health` calls `board_payload()`**, so a cold fold can trigger the
  14-day `git log -p` (≤30 s, TTL-cached 30 s). Nothing automated polls it;
  `/health` is untouched and answers with every producer dead or broken.
* **The running hub on :8100 holds pre-change code in memory.** Reloading it
  belongs to whoever owns that service; nothing here restarts it.

## The rebuilt AutoKernel loop (`/loop`) — a second, separate AK surface

The operator had **zero visibility** into the rebuilt loop. The dashboard showed
only the superseded deployment `gpu-discovery-champion-v37` as STOPPED — true,
and about a *different process* — while the new loop ran as something nothing
observed. A loop nobody can see is a loop nobody can trust.

**It is a separate surface on purpose, not a section of `/kernel`.** The
Kernel-R&D surface pins 29 cross-repo source paths and 47 SHA-256 digests of
another repository's modules and is slated for wholesale rewrite; growing it
would re-arm that landmine and make one contract's rewrite a second contract's
outage. Two producers, two panels, two probes, no shared blast radius.

* **Contract** — `epyc.autokernel.loop_status.v1`, written atomically by
  `scripts/kernel_rnd/autokernel/loop/status.py` in **epyc-inference-research**
  into the loop's store root (default
  `/mnt/raid0/llm/autokernel/loop-memory/loop-status.json`, overridable with
  `AUTOKERNEL_LOOP_STORE_ROOT`, resolved **per request**). The plane rule holds:
  the producer owns the schema, this hub owns the page, the nav row and the probe.
  The hub **never imports** that package and pins no path or digest of it.
* **Four-valued freshness** — `absent` / `malformed` / `stale` / `fresh`, each
  with its own loud banner and its own probe verdict. `absent` is not `stale`
  (a producer that never ran and a producer that stopped are different facts
  about different subsystems); `malformed` is not `absent` (**broken ≠ never
  exported** — one points at the writer, the other at whether the loop exists).
  `payload["loop"]` is `null`, never `{}`, when nothing readable was found — the
  same `[]`-vs-`null` rule `_read_kernel_contract` records.
* **The envelope is the PRODUCER'S** — the body's own `stale_after_s` is handed
  to `panels.envelope` as an `Observation.silence_budget_s`, clamped to
  `[60 s, MAX_STALE_S]`, so the hub does not hold a second, drifting opinion
  about when this loop is late. A loop that declares a longer cadence does not
  read stale.
* **The negatives are on the page.** Every disposition, not just the keeps —
  a board that shows only wins is how 0 promotions looked like progress for a
  month. Each row is tagged `kept` / `measured, not kept` / `never measured`.
* **GPU held-vs-busy, or an honest silence.** The loop ran 95.4% idle on a held
  device for a month and no surface said so. But an *empty* `gpu` map renders
  "not reported" — never a fabricated `0 s busy / 100% idle`, which would be the
  same failure with a number on it.
* **`/api/loop/health` is the `/api/health` KIND of probe**, not the `/health`
  kind: it answers *is what this page shows still true?*. It folds ONE envelope
  and never recurses through the global fold. Two rulings live in it rather than
  in freshness alone: a loop that DECLARED `state=failed` is `degraded` even
  while perfectly fresh (a loop that crashed a minute ago is fresh *and* dead),
  and a loop that DECLARED `state=complete` is allowed to be silent (the same
  compliant path `kernel` and `outcome` already obey — the hub never *infers*
  idleness).
* **Cold start does not cry wolf.** The panel declares
  `absence_is_anomalous=False`, so a host where no campaign has run does not
  redden the global `/api/health`. It is still always listed under `absent`,
  named in `attention`, and `/api/loop/health` answers `absent` with HTTP 503 —
  nothing is hidden, it just is not an outage.

Tests: `tests/test_dashboard_loop_surface.py` (mutation-checked: collapsing
`absent` into `stale`, an always-200 probe, a deleted registry row, a fabricated
GPU reading, a keeps-only disposition list, and a laundered `failed` state are
each caught).

## Data model

* **State = parent directory** (authoritative). The one exception is the
  **Blocked** column, which is *status-derived*: an `active/` handoff whose
  `Status` begins with `BLOCKED`, plus rows in
  [`handoffs/blocked/BLOCKED.md`](../handoffs/blocked/BLOCKED.md).
* **Task progress** = GitHub checkboxes (`- [ ]` / `- [x]`). Files with none fall
  back to a `✅`-marker count (shown as a marker chip, no ratio); files with
  neither show no bar.
* The **board is a live per-request scan** — uncommitted handoff edits show
  immediately.

## Timeline & historical seeding

`build_handoff_timeline.py` reconstructs progress over time from
`git log -M -p` over `handoffs/` (one pass, ~1 s; **full rebuild every run**).

This repo's `handoffs/` git history begins at the **2026-02-25 monorepo split**,
which bulk-imported dozens of already-complete handoffs and hundreds of
already-`[x]` tasks in a single commit. To avoid piling all of that onto one week
and truncating the chart at the split, the generator prefers **self-reported
dates** over the git-commit date:

1. a **task completion** is dated by the `✅ YYYY-MM-DD` (or any ISO date) on the
   checkbox line;
2. else, for a file first imported already-checked, by the file's
   `**Updated**` / `**Created**`;
3. else by the commit that first shows the task checked.

Handoff **creation** uses `**Created**` (else git first-seen); a bulk-imported
terminal handoff's completion uses `**Updated**`/`**Created**`. The cumulative
`series` is rebuilt from each handoff's *(created → terminal)* interval, so it
extends back to true project origin (**2026-01-05**), not the split.

**Honest caveat:** completed work imported at the split that carried **no date
anywhere** (no inline `✅`, no `**Created**`/`**Updated**`) has no recoverable
completion date, so it is attributed to the import week (2026-W09). Everything
that carries a date is placed accurately.

### Keeping it fresh

```bash
bash scripts/handoffs/install_timeline_hook.sh
```

Installs a detached, best-effort `post-commit` hook (chained onto any existing
one) that regenerates `data/handoff_timeline.json` whenever a commit touches
`handoffs/`. The artifact is **git-ignored** (derived data). If the hook ever
stops running, the timeline's freshness badge turns `stale`.

## Tests

```bash
python3 tests/test_handoff_parser.py
python3 tests/test_handoff_timeline.py
python3 -m pytest tests/test_dashboard_panels.py \
                  tests/test_dashboard_panels_redteam.py \
                  tests/test_dashboard_activity.py
```

Stdlib `unittest` (pytest also discovers them). The timeline suite builds a
throwaway git repo and asserts the create → flip → move lifecycle, including that
inline `✅` dates override commit dates.

The AK6 suites are the registry, envelope, watchdog and fold; the **cross-repo
seam and the restart chaos test live in the producer's repo** (see above), because
only there can a real contract be assembled from the modules that own its facts.

**Run the panel suites under more than one interpreter.**
`discover_payload_functions` used `inspect.isroutine` to decide whether a
callable could be attributed to another module — and `isroutine(functools.partial(…))`
is `False` on Python 3.13 and `True` on 3.14. The 3.14 answer silently reopened
the evasion the predicate exists to close (`ghost_payload = partial(kernel_payload)`
became invisible to the totality test) on the interpreter `uv run` actually uses.
It is now `isfunction`/`isclass`, which are true only of Python-level `def`s and
classes; anything else is *counted*, so the registry has to account for it.
