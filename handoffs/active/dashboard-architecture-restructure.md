# Dashboard Architecture Restructure — audit + action plan

**Status**: active — audit complete 2026-08-10; **decisions ratified 2026-08-10 (see below); Phase 0 + Phase 1a buildout in progress**
**Created**: 2026-08-10
**Priority**: LOW-MEDIUM — operator-framed as debt prevention, "doesn't block any work"; do at seams, never ahead of campaign work
**Owner**: unclaimed
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Related**: [autopilot-dashboard-fidelity-audit-2026-07-22.md](autopilot-dashboard-fidelity-audit-2026-07-22.md) (RTG-03 — data-truth defects; this handoff is information-architecture, NOT a substitute for its C1/H1/H2 fixes) · [loops-and-dashboards-audit-2026-07-05.md](loops-and-dashboards-audit-2026-07-05.md) (RTG-16) · [benchmark-results-dashboard.md](benchmark-results-dashboard.md) (EVL-06 — the working precedent for the contract pattern) · OP-9 (hub supervisor restart, master index)

## Commission (operator, 2026-08-10, paraphrased)

1. The autopilot dashboard (:8000/dashboard) is **two distinct things** glued together: a global
   live view of hardware usage + active inference on the machine (regardless of what drives it),
   and the autopilot loop's planning/governance/optimization results. Split them.
2. Inter-dashboard links are inconsistent/invisible — reaching AutoKernel often requires routing
   through the handoff board. Fix the navigation debt.
3. Answer the ownership question: should individual repos own dashboards? Should epyc-root own
   all of them? Only the server? What are best practices?

---

## Part 1 — Audit

### 1.1 Inventory (every dashboard surface, 2026-08-10)

| Surface | URL | Page code owner | Server process | Data source |
|---|---|---|---|---|
| Handoff kanban | `:8100/` | epyc-root `dashboard/static/handoffs.html` | stdlib hub (`dashboard/server.py`) | live `handoffs/` scan + git-derived `data/handoff_timeline.json` |
| AutoKernel (Kernel-R&D) | `:8100/kernel` | epyc-root (page) | stdlib hub | producer contract: epyc-inference-research → `/mnt/raid0/llm/autokernel/surface/kernel_dashboard.json` |
| Session bus | `:8100/bus` | epyc-root | stdlib hub | `coordination/session-bus/` files |
| Benchmark artifacts | `:8100/benchmarks` | epyc-root (page + offline builders) | stdlib hub | `data/benchmark_artifact_inventory.json` (built from research `artifacts/`) |
| Orchestrator dashboard (monolith) | `:8000/dashboard` | epyc-orchestrator `src/api/routes/dashboard.html` | FastAPI, uvicorn ×6 workers | mixed: `/proc`+`ps` scans, tap event files, autopilot journal/state files, per-worker in-process state |
| Health folds | `:8100/api/health`, `:8000/dashboard/api/health` | each server | — | panel registries (see 1.4) |

Not in scope: x-scheduler `:8300` (personal app, not project), `:11235` gunicorn (containerized
service, no project dashboard), mkdocs `site/` (static docs, not a dashboard).

Sizes: orchestrator `dashboard.py` **7,855 lines** + `dashboard.html` **7,649 lines** (one page);
hub: `server.py` 1,640 + `panels.py` 1,054 + four pages totalling ~1,824 lines.

### 1.2 Finding — the :8000 monolith mixes THREE concerns, not two

Panel census of `dashboard.html` + its 38 `/dashboard/*` routes:

**(a) Machine / live-inference monitor — global, driver-agnostic** (the operator's "global
monitoring engine"): topology + NUMA badge + topology strip/flow, region locks + device
occupancy, contention gate, live inference tap (+ raw/structured tap streams), process status,
node detail (`/api/node/{port}`), `llama_fleet_ids`. Routes: `topology`, `topology_activity`,
`region_locks`, `contention`, `inference_tap`, `process_status`, `node/{port}`,
`llama_fleet_ids`, `snapshot`, `events/{raw,structured,inference}_tap`, `events/multiplex`,
`events/stream`.

**(b) Autopilot loop — process-specific planning/governance/optimization**: phase banner +
**pause/resume control buttons**, autopilot log tail, trial progress bar, GEPA + Pareto frontier +
hypervolume, insight graph, optimization brief, outcome KPIs, planner tap. Routes:
`autopilot_control`, `autopilot_progress`, `autopilot_snapshot`, `pareto`, `gepa`,
`insight_graph`, `optimization_brief`, `events/autopilot_log`, `events/planner_tap`.

**(c) Orchestrator serving telemetry**: routing decisions (last-200 distribution), recent
outcomes / completed tasks, repo readiness queue, task detail routes.

The operator's split instinct is confirmed; (c) is the refinement — serving telemetry is "active
inference on the machine" in the operator's own framing, so it travels with (a), except
repo-readiness which is an autopilot advisory queue and travels with (b).

### 1.3 Finding — navigation is per-page hand-rolled and has drifted

Link matrix (✓ = link present in the page header):

| From \ To | handoffs | kernel | bus | benchmarks | :8000 dashboard |
|---|---|---|---|---|---|
| `:8100/` (handoffs) | — | ✓ | ✓ | ✓ | ✓ |
| `:8100/kernel` | ✓ | — | ✗ | ✗ | ✓ |
| `:8100/bus` | ✓ | ✓ | — | ✗ | ✗ |
| `:8100/benchmarks` | ✓ | ✓ | ✗ | — | ✗ |
| `:8000/dashboard` | ✓ (11px header link) | ✗ | ✗ | ✗ | — |

- Only the handoff board has a complete nav — hence "you must route through the handoff
  dashboard to reach Autokernel". From :8000, kernel is a two-hop trip.
- **Root cause: there is no shared nav component or machine-readable directory of dashboards.**
  Every page hand-copies a `<nav>`; they were written at different times and drifted.
- Defect: `:8000` `dashboard.html:941` ships `href="/"` for the handoffs link and JS-rewrites it
  to `:8100` (`:943`); with JS disabled/failed the link silently points at the orchestrator's own
  root. Cross-server URLs are re-derived ad hoc in at least 3 places
  (`dashboard.html:943`, `static/handoffs.html:281→744`, `static/kernel.html:117`).

### 1.4 Finding — the documented ownership boundary is a *transport* rule, and its premise has eroded

The rule on record (`dashboard/README.md`, memory 2026-07-04): *"needs the orchestrator's live
in-process state or SSE inference taps → orchestrator serves it; artifact/file-backed &
project-wide → hub."* Two problems:

1. **It governs which process serves bytes, not what shares a page.** Anything needing any
   orchestrator state landed on the single :8000 page — that is exactly how the monolith accreted.
2. **The premise is now largely false.** Per the 2026-07-22 fidelity audit: `/topology` and
   `/region_locks` builders are **`/proc`/`ps` scans, verified network-free**; the taps tail
   **rotating event files**; autopilot panels read **journal/state files**. What is genuinely
   in-process (per-worker contention counters, breaker state) is per-worker-fragmented — i.e.
   the fidelity audit's own finding is that the genuinely-in-process data is the part that
   should not be trusted as served today. The transport rule no longer explains where things are.

Corollary worth naming: under AutoPilot, the API restarts every ~20–25 min per trial — the
machine monitor's delivery path blinks precisely when the machine is busiest (the
`snapshotTransportWatchdog` exists to paper over this). A *global* monitor whose data plane
lives inside the most-restarted process on the host is an architecture smell, not just an IA one.

### 1.5 Finding — duplicated view-plane infrastructure (two registries, two freshness grammars)

Both servers independently grew an AK6-style panel→producer registry + freshness envelope:
hub `dashboard/panels.py` (11 panels; `fresh/aging/stale/missing` + `reporting`/`content`/
watchdog/`absence_means`) vs orchestrator `dashboard_panels.py` + `dashboard_freshness.py`
(14 panels; `fresh/aging/stale/dead`, gating-vs-informational). Same idea, divergent
vocabularies and semantics. Both are tested; premature code-merge is not proposed — but every
new dashboard today must choose one of two grammars, and the two health folds cannot be read
uniformly.

### 1.6 Finding — lifecycle inversion (context for the ownership answer)

The hub's code is epyc-root's, but its lifecycle is managed from the orchestrator repo
(`orchestrator_stack.py start_handoff_dashboard()`), with epyc-root's `hub_supervisor.sh` as a
second, independent watchdog (OP-9: nothing restarts the supervisor itself). Two supervisors in
two repos for one service. Works, but is exactly the kind of cross-repo debt this plan should
rationalize, not multiply.

---

## Part 2 — The ownership question (decision D1 input)

Best-practice frame (the Grafana/exporter pattern, which this project already independently
reinvented with AutoKernel): separate three planes —

- **Data plane** — producers/exporters publishing *versioned contracts* (JSON files, HTTP APIs,
  SSE). Lives **with the subsystem it observes** — that repo is authoritative for what the
  numbers mean, and the exporter versions with the code it measures.
- **View plane** — pages that render contracts. Cross-cutting by nature (shared nav, one look,
  one freshness grammar, one directory) → belongs to the **governance repo (epyc-root hub)**.
- **Directory/nav plane** — a machine-readable registry of what dashboards exist. One owner:
  the hub.

Answers to the operator's questions, directly:

- **Should individual repos own dashboards?** They should own **data contracts, not pages.**
  The AutoKernel split is the proof it works here: producer (research repo) exports a schema'd
  JSON after fsync; hub renders it; the seam is tested; the hub never imports producer code.
  The counter-proof is also on record: the one repo that owns a full page (orchestrator) grew a
  7.6k-line HTML monolith with a hand-rolled one-link nav.
- **Should epyc-root own all of them?** epyc-root should own the **view plane** (pages, nav
  registry, freshness grammar, hub process) — not the data plane. Absorbing producers into
  epyc-root would put schema authority in the wrong repo and re-create the coupling in reverse.
- **"Maybe only the server is owned by epyc-root?"** Close — the precise cut is: **epyc-root
  owns the server *and every page and the registry*; each repo owns its data endpoints and
  export contracts.** A page served from :8100 fetches :8000 JSON/SSE directly from the browser
  (CORS allowlist on the orchestrator API — one middleware line). No proxying, hub stays
  stdlib, processes stay independent; if :8000 is down its panels go honestly dead under the
  AK6 grammar instead of the page vanishing.
- **Known cost, stated honestly**: page (epyc-root) and API (orchestrator) can skew across
  deploys. Mitigations already exist and become policy: the seam discipline from
  `dashboard/README.md` (never import producer code; hub-derived fields underscored; seam
  tests), `/dashboard/api/version`, additive-only API evolution.

## Part 3 — Decision package — **RATIFIED 2026-08-10 (operator, in-session)**

> **Ratified decisions**:
> - **D1 = C2** (full view-plane consolidation). Operator first picked C1, then upgraded to C2 when
>   the parallel-buildout constraint (below) made it strictly cleaner: C1's "slim the monolith in
>   place" step would surgically edit the live page, while C2 never touches it — both new pages
>   (`/machine` + `/autopilot`) are built fresh on the hub and the old page is deleted wholesale at
>   deprecation. Operator: *"goal set: refactor the entire dashboard serving architecture."*
> - **D2 as recommended**: routing decisions + recent outcomes → `/machine`; repo-readiness →
>   autopilot page.
> - **D3 deferred**: `/machine` rides :8000 APIs; standalone machine exporter only if blink-out
>   evidence accumulates post-C2.
> - **Parallel-buildout constraint (operator, verbatim intent)**: the operator currently depends on
>   :8000/dashboard for live views. Build new pages IN PARALLEL; the old page stays fully intact
>   and live until the operator declares deprecation, then it is removed wholesale.
> - **Restart policy**: API reloads allowed freely when quiet — verify nothing is in flight first
>   (inference tap + bus + `ps` for the codex instrumentation-baseline session, 2026-08-10) and use
>   `orchestrator_stack.py reload orchestrator` (API-only, never the stack).
> - **New-page discipline**: hub pages stay stdlib/no-CDN (the old page's jsdelivr KaTeX/marked/
>   highlight.js dependencies are NOT carried over; the new pages hand-render like the hub does).

### D1 — target ownership/topology (pick one)

| Option | Shape | Gains | Costs / risks |
|---|---|---|---|
| A. Status-quo + nav fix only | Shared nav registry on all 5 pages; no split | Kills the navigation debt in ~1 session | Monolith and mixed concerns remain |
| B. Split in place | A + orchestrator serves two pages (`/dashboard/machine`, `/dashboard/autopilot`) | Concept split lands cheaply; no CORS, no cross-repo page moves | Two view planes stay in two repos; nav/grammar drift risk persists; global monitor still dies with the API |
| **C1. Hub owns the global page; process pages stay put (RECOMMENDED)** | A + **new hub page `:8100/machine`** renders concern (a)+(c) from existing :8000 APIs (CORS); **:8000/dashboard slims to concern (b) only** | Lands the operator's split exactly on the global-vs-process line; global monitor owned by the neutral repo; no porting of the SSE-heavy autopilot panels; monolith shrinks materially | CORS + cross-origin EventSource (low, LAN HTTP); page/API skew (mitigated §Part 2); ~7.6k-line HTML still hosts the autopilot page until/unless C2 |
| C2. Full hub view plane | C1 + autopilot page also moves to hub; :8000 serves data only | One view plane, one owner, maximal | Large migration of pareto/insight-graph/SSE panels for mostly-aesthetic gain; not justified today |

**Recommendation: C1**, explicitly leaving C2 as a later option. Rationale: a *process-specific*
page owned by the process's repo is defensible under the plane model; a *global* page owned by
one client process is not — C1 fixes only what is actually wrong.

### D2 — where does serving telemetry (concern (c)) live?

Recommendation: routing decisions + recent outcomes + task detail → `/machine` ("active
inference on the machine" per the operator's own definition); repo-readiness → autopilot page
(it is an autopilot advisory queue). Alternative: a third `/serving` page — rejected as page
proliferation without an audience.

### D3 — machine-monitor data-plane independence (Phase 2, defer-able)

The `/machine` page initially rides :8000 APIs. Later options: (i) accept the coupling;
(ii) small standalone machine-state exporter (or hub-side `/proc` reader — the builders are
already network-free) so machine visibility survives the ~20-25 min per-trial API restarts;
taps stay :8000-owned (they observe the orchestrator's own traffic and *should* die with it,
honestly labeled). Recommendation: **defer decision until C1 has run for a while**; revisit with
observed blink-out evidence. Do not build ahead of evidence.

## Part 4 — Action plan

### Phase 0 — nav + directory (no restructuring; independent of D1) — **COMPLETE 2026-08-10**

- [x] `dashboard/registry.json` (moved out of `static/` — it is read+embedded, not served as-is)
      — SSOT list of dashboard surfaces: `id`, `title`, `port`, `path`, `owner_repo`,
      `health_path`, `blurb`; 7 entries. Served as `/api/dashboards` by the hub with per-unique-
      `(port, health_path)` loopback transport probes (ThreadPoolExecutor, 1.5s timeout, 15s TTL
      cache), `PanelSource("dashboards")` registered, probes deliberately NOT folded into
      `/api/health` (a down :8000 must not restart-loop the hub). ✅ 2026-08-10
- [x] Shared nav include (`dashboard/static/nav.js` + generated `/nav.js` asset with the registry
      inlined — served via a new `ASSET_ROUTES` table, outside the panel-registry universe like
      `HTML_ROUTES`, noted in README): adopted by all four hub pages **and** `:8000/dashboard`
      (cross-origin `<script>` bootstrap — script tags are CORS-exempt, so the nav needed no CORS).
      ✅ 2026-08-10
- [x] `:8000` `dashboard.html` hub link replaced by the shared-nav bootstrap with an onerror
      fallback that recreates the plain handoffs link — the page never loses its one exit if the
      hub is down; per-page `:8000`/`:8100` URL derivation deleted from kernel/handoffs pages.
      ✅ 2026-08-10
- [x] Hub root directory strip (`#dash-directory`): every registered dashboard + probe badge
      (green/red dot, latency tooltip), 30s refresh, explicit error row on fetch failure.
      ✅ 2026-08-10
- [x] Drift guard `tests/test_dashboard_nav.py` (277 lines): registry schema, bidirectional
      HTML_ROUTES↔registry check, every page carries `#epyc-nav` + `/nav.js`, retired
      `autopilot-link` pattern banned, `/nav.js` asset carries the registry. Full hub suite green
      under system python3.13 AND uv/3.14: **175 passed + 91 subtests**. ✅ 2026-08-10

### Phase 1a — parallel buildout on the hub (ratified shape: C2; old page untouched) — **DEPLOYED 2026-08-10**

- [x] New hub page `:8100/machine` (1,018 lines) — topology (ROGUE/expected derivation, NUMA
      provenance-disagreement banner, "slots ? = unknown-not-zero" honesty), region
      locks/occupancy (lease-held-not-decoding chips), contention, live inference tap (SSE +
      dedup + poll fallback), process status, routing decisions (per D2), recent outcomes.
      Primary feed = `/dashboard/events/stream` snapshot frames w/ poll fallback; stale
      thresholds adapt to OBSERVED frame cadence (flat 12s would flap against the ~10s
      /slots-bound frames); snapshot fetch budget 15s (measured 9.8s). Harness-tested against
      live payloads + ~20 degraded variants; EventSources self-heal onto CORS activation
      without a refresh. ✅ 2026-08-10
- [x] Orchestrator: `src/api/dashboard_cors.py` — pure-ASGI, path-scoped
      (`/dashboard/api/`+`/dashboard/events/` only), hub-origin regex `:8100`, GET+POST+preflight,
      credentials NEVER (strips the global CORSMiddleware's unconditional
      `allow-credentials: true`, which paired with our ACAO would have made a credentialed
      grant), outermost so the inner global CORS can't 400 the hub preflight. 29 tests + 93
      adjacent green; **activated by API reload 2026-08-10 and wire-verified** (preflight 204,
      ACAO on GET+SSE, non-dashboard paths + foreign origins closed). ✅ 2026-08-10
- [x] New hub page `:8100/autopilot` (1,541 lines) — phase/control (5-state loop posture;
      "stopped (declared)" renders stale-heartbeat blockers dim-not-alarmed), log + planner-tap
      SSE, trial progress, Pareto (4-D objective axes from payload, quality × task-rate scatter,
      trial-indexed hypervolume), GEPA, outcome KPIs (BOTH all-time and 120-trial-window scopes
      — they disagree sharply and rendering one would mislead), optimization brief, simplified
      insight graph (labeled v1), repo readiness. Endpoint shapes all verified live. ✅ 2026-08-10
- [x] Registry + nav entries for both new pages; hub `/api/health` unchanged (probes stay out
      of the fold; verified live post-deploy: fold still `absent`-by-kernel as before).
      ✅ 2026-08-10
- [x] The OLD `:8000/dashboard` page: untouched except the additive shared-nav include
      (verified serving, 394KB, after the reload). ✅ 2026-08-10

**Deploy record (2026-08-10)**: hub reloaded via `orchestrator_stack.py reload handoff_dashboard`
(PID 962033); orchestrator API reloaded via `reload orchestrator` (PID 964903) after quiet checks
(no bench processes, 0 active tap requests, 0 established :8000 connections, 0 in-flight tasks;
the one busy `ingest_long_context` slot was direct-to-llama traffic, unaffected). All 7 registry
probes green. **Operator eyeball pass DONE 2026-08-10** — three fixes landed + redeployed same
day: (1) stale greying removed on both pages (readable content + bold amber/red "no data" pill
instead), (2) machine topology regrouped substrate (CPU/GPU) → role-family cards, model named
once, partition instances labeled with REAL shapes (full/half0/half1 from `by_role` — role
suffixes still say `.qN` while instances are halves), embedder clones collapsed, (3) region-locks
table re-axised to instance shapes with quarters demoted to tooltips (`spanLabel()`), raw region
axis kept as fallback only. Verified: node --check, machine render harness 25/25, nav suite
18+51 subtests, both pages 200.

**Eyeball round 2 — DONE 2026-08-10** (progress/2026-08/2026-08-10.md has the detail): topology
nodes now carry **`substrate: gpu|cpu`** derived from process evidence (llama binary path; services
via /proc argv0 + HIP-runtime maps + model-label hint; never role lists — architect_general is a
GPU role and nothing in its name says so). Machine page: GPU cards purple (#a855f7) with GPU chips,
GPU-occupancy section in the locks panel, device occupancy aggregated to instance shapes, inference
tap rebuilt as legacy-style structured request cards (raw tail → collapsed details), task cards
click-through to a detail modal (`/dashboard/api/task/{id}` + live task SSE; 200-with-empty renders
"task no longer retained"). sd-server verified genuinely CPU-built (no HIP libs mapped, no
/dev/kfd) — unmarked is correct. Harness extended 25→48 checks, all green.
**Eyeball rounds 3–4 — DONE 2026-08-10** (fix 6–9 + data plane; detail in
progress/2026-08/2026-08-10.md): tap cards = the outcomes `.ocard` component with the legacy
state ladder ported branch-for-branch (verbatim strings incl. "streaming"/"prefill/decode
pending"; precedence + 20s lock-frame freshness gate pinned by tests); completed requests leave
the tap and MERGE into Recent outcomes (task_id+role identity: sub-rows on matching cards,
standalone tap-chipped cards otherwise, both windows deduped); **`slot_progress` added to the tap
data plane** (llama /slots `n_prompt_tokens[_processed]`/`n_decoded`, fresh-sample-only,
complete-requests-never-attach — first live check caught a same-port completed request wearing
the running request's counters — shared-port ⇒ `ambiguous`), rendered as Claude-Code-style
`↑ 48.4k/48.7k tok` / `↓ 334 tok · 40.0 tps` counters (tilde + "(port)" when ambiguous, chars
fallback); locks-table "holding" column → **slots used/total** (join role+shape→node→port→
`display_activity`; `?`-contribution and `≥` aggregates, lock truth demoted to cells/tooltips);
GPU occupancy slots-primary; panel order tap → decisions/outcomes/process → topology →
locks/contention; topology compacted; standing per-instance `tps` field (trailing avg, labeled).
Machine harness 25→48→59→81 checks, 0 fail (independently rerun); 4 quiet API reloads total.
- [x] Tap SSE stream bypassed the slot_progress funnel — operator caught a 32,851-token prefill
      rendering no ↑ counter: the stream ran its own parse+enrich while only the (unwatched) poll
      endpoint attached progress. Stream now uses `_structured_tap_requests_for_dashboard` (one
      assembly path, also gaining offwindow-holder recovery). ✅ 2026-08-10
- [x] Page retention overlay (fix 10): live-observed slot_progress retained per request
      (max-merge, sticky ambiguity, direction-dependent ↓ source — slot mid-run, final timings at
      completion), so completed cards show `↑ N tok` and a fresh-gap frame cannot wipe a shown
      counter; SSE gained server-epoch `now`. Harness 81→88, 0 fail. ✅ 2026-08-10
- [ ] Re-eyeball the tap's ACTIVE/streaming card path + live ↑/↓ counters once inference actually
      runs (`slot_progress` verified attaching live on poll + now on SSE; full live render still
      unobserved by a human).
- [ ] Data plane (small): tap writer records terminal `n_prompt_tokens` per request so completed
      requests carry TRUE prompt tokens even when never observed mid-run (today: chars fallback).
- [ ] Data plane (small): manifest-declared substrate for non-running `expected-stack-server`
      nodes (no process evidence exists for them; today they fall to the page heuristic).

### Phase 2 additions from buildout findings (rows, not yet started)

- [ ] **Trimmed machine-frame endpoint**: the snapshot document is ~3.9 MB/frame
      (`live_frame.lifecycle` ≈ 2 MB, duplicated under `region_locks.live_frame`) — ~8 MB/s per
      open tab at nominal 2 Hz. A slim frame for `/machine` is a data-plane change (belongs with
      the D3 revisit).
- [ ] **/slots fan-out answered 0/19 during buildout** — machine-state truth issue (RTG-03
      territory), surfaced loudly by the new page rather than rendered as zeros; confirm against
      RTG-03's manifest/realized work before treating as a page-side bug.

### Phase 1b — deprecation (operator-triggered, after new-page parity is confirmed)

- [ ] Operator runs old + new in parallel and confirms `/machine` + `/autopilot` cover the
      live-view usage.
- [ ] `:8000/dashboard` becomes a redirect to `:8100/autopilot`; `dashboard.html` (7,649 lines)
      deleted wholesale. **All `/dashboard/api/*` + `/dashboard/events/*` data routes stay** —
      :8000 becomes data-plane-only.
- [ ] Registry entry for the legacy page removed; `dashboard/README.md` ownership boundary
      rewritten to the plane rule (with Phase 3's codification).
- [ ] Orchestrator `dashboard_panels.py` survives as the DATA-plane registry (it guards
      endpoints/producers, not page rendering) — nothing drops out of the fold.

### Phase 2 — hardening (per D3; do only with evidence)

- [ ] Machine-truth derivation: realized-state (manifest/`/proc`)-first for `stack_numa_mode` /
      `expected` flags — **owned by RTG-03 C1 fix**; this plan only inherits it onto the right
      page. No duplicate work here.
- [ ] (If D3 = exporter) standalone machine-state exporter or hub-side reader; taps remain :8000.
- [ ] Freshness-grammar harmonization at the seam: one envelope vocabulary
      (hub's four-state + `reporting`/`content`) adopted by both registries' *wire format*;
      internal code stays separate.

### Phase 3 — codify governance

- [ ] Write the plane rule into `dashboard/README.md` (+ one-line CLAUDE.md pointer):
      *data contracts live with their subsystem; pages/nav/registry live with the hub; every new
      dashboard = registry entry + health probe + freshness envelope; no unregistered pages.*
- [ ] Rationalize supervision with OP-9's resolution: one documented lifecycle story for the hub
      (managed service + watchdog roles stated once, in one repo's docs).
- [ ] H1/H2 blind-spot panels (owned by RTG-03) get homes assigned post-split: breaker/fallback →
      `/machine`; REL-1 eval error-rate → autopilot page.

## Non-goals

- **Not a data-fidelity fix.** The per-worker env fragmentation, inverted-topology defect, and
  H1/H2 blind spots stay owned by [autopilot-dashboard-fidelity-audit-2026-07-22.md](autopilot-dashboard-fidelity-audit-2026-07-22.md).
- **No merge of the two panel-registry codebases** (both tested; harmonize the wire vocabulary only).
- **No new inference, no benchmark reruns, no stack restarts** — pure view-plane work; deploys at
  operator-approved boundaries (`orchestrator_stack.py reload` for the hub; API restart for CORS).

## Reporting

Flip checkboxes with inline `✅ YYYY-MM-DD` as phases land; record routes/registry schema in
`progress/`. Delete the index row on completion.
