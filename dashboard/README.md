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
| `dashboard/static/handoffs.html` | kanban UI + modal + hand-rolled SVG charts (no framework, no CDN) |
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
- `GET /api/kernel/health` — Kernel-R&D producer/data health only; HTTP 200 when
  fully reported and current, HTTP 503 with `absent`/`degraded` detail otherwise
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

Discovery/progression is a second, additive contract:
`scripts/benchmark/autokernel_progression.py` projects immutable CPU/GPU screen
and strict campaign receipts into
`/mnt/raid0/llm/autokernel/surface/kernel_progression.json`. The hub exposes it
as `_progression`; it never overwrites terminal `sections`, never mints a
champion, and requires `promotion_claim: false`. Its top layer is the operator's
ten-second scan (production anchor, CPU/GPU leaders, direction-correct effect,
workload, evidence tier, current gate, next action and candidate → strict keep →
champion → promotable counts). Strategy and unexplored hypotheses form the
second layer; all former detailed cards remain under **Evidence & diagnostics**.
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
