# Autopilot / Orchestrator Dashboard Fidelity Audit — 2026-07-22

**Commission**: Operator, 2026-07-22. Read-only audit. Hypothesis under test (operator, verbatim):
the dashboard must be "properly wired to capture and faithfully display the fixes we've been
implementing" and "since it was built on top of flawed infra, it is probably flawed itself."

**Scope**: `src/api/routes/dashboard*.py` + the single static frontend `dashboard.html`
(served by `GET /dashboard`). No scripts/ dashboard server exists (only stack-management tools).
The epyc-root handoff-kanban hub on :8100 is out of scope (confirmed a distinct `service` node).

**Method / constraints honored**: read-only. 5 GET requests issued to `localhost:8000` dashboard
endpoints (topology×2, region_locks, contention; one snapshot attempt refused during a stack
handover). NO llama-server traffic (the `/topology` and `/region_locks` builders are `/proc`-scan
only — verified network-free; `/snapshot` and `/health` fan out to llama `/slots`/probes and were
deliberately NOT driven). No inference, no POSTs, no edits. EV-11c left undisturbed.
Mid-edit files (`scripts/server/*`, `src/config/models.py`, `src/registry/stack_priors.py`)
read from committed HEAD.

---

## Executive summary

**The hypothesis is confirmed.** The dashboard inherits the data plane's central defect: it does
not read a single realized source of truth for fleet state. Its correctness is *coincidental* —
it depends on a launch-time environment variable (`ORCHESTRATOR_STACK_NUMA_MODE`) happening to
match the realized fleet.

The capstone proof, captured live on the same quarters-only fleet:

- **GET #1 `/dashboard/api/topology`** (routed to a uvicorn worker whose env was `full`) rendered
  `stack_numa_mode="full"`, flagged **all 12 live quarter servers `expected=False`** (i.e. rogue),
  and flagged **the 3 dead full ports (8070/8072/8085) as `expected-stack-server, running=False,
  expected=True`** (i.e. missing/down). This is a **fully inverted fleet-health picture**: the
  correct fleet reads as broken, and the intentionally-absent full servers read as expected.
- **GET #5 `/dashboard/api/topology`** minutes later (after a stack relaunch to an env=`quarter`
  master) rendered `stack_numa_mode="quarter"`, `0` rogue quarters, `0` missing fulls — **correct**.

Same realized fleet both times (12 quarters live, 3 fulls dead, verified by `ps`). The only thing
that changed was which launch env the serving worker inherited. The dashboard already computes the
realized fleet (`_discover_llama_ports()` — a `ps`/`/proc` scan) and uses it for the node list, but
it does **not** use it to derive `stack_numa_mode` or the `expected` flags. Those come from the env.

**Root cause (cross-cutting, defect-signature "duplicated state without a single SoT")**: the API
runs `uvicorn --workers 6`, and during the audit **three concurrent/successive worker pools carried
divergent env** — `ORCHESTRATOR_STACK_NUMA_MODE=full` (master 1778291), `=quarter` (master
1851981), and `UNSET` (worker 1854520). `active_stack_numa_mode()` therefore returns **full /
quarter / both** depending on which worker the load balancer picks. Two dashboard panels sampled
seconds apart genuinely disagreed: `/topology`→`full`, `/region_locks`→`quarter`. The
"coherent-snapshot" fix guarantees coherence *within* a worker; it provides none *across* the pool.

Every field sourced from per-process state inherits this fragmentation: contention-gate counters,
per-role scheduling, migration counters, and circuit-breaker state are all per-worker singletons and
show a 1-of-6 fragment (or empty) with no worker provenance. Fields sourced from the shared
filesystem/`/proc` (region-lock held-state, the rotating journal, the topology node list) are NOT
fragmented — which is exactly why those panels are the trustworthy ones.

Three fixes are faithfully wired (journal rotation, era-labeling, region-precise held-state).
Three states the recent fixes made honest are **blind spots** the dashboard never surfaces at all:
REL-1 eval error-rate, calibration/confidence provenance, and circuit-breaker/forced-role-fallback
events — the last being precisely the EV-11c incident class.

---

## Fix-inventory fidelity table

| # | Fixed data-plane state | Dashboard verdict | Read path (file:line) | Proof |
|---|---|---|---|---|
| 1 | Topology / NUMA mode (env-first vs realized fleet) | **READS LYING SOURCE** (env-first; correctness coincidental) | `dashboard_topology.py:140` (env short-circuits before the hardened manifest reader `:150`); mode consumed at `dashboard.py:4839`, `:4636` (`expected_stack_services(mode)`), `:5131` | GET#1 env=full → inverted; GET#5 env=quarter → correct; same fleet |
| 2 | Placement / holder truth (`held_regions_by_role` exact sets) | **READS CORRECTED SOURCE** for held-state; **duplicated + partial** | region grid re-derives from `/proc/locks` via `_current_lock_owner_pids` inline `dashboard.py:998-1029`; never calls `cpu_region_lock.held_regions_by_role()` (`:419`) | GET#2 region-precise; `launch_selected` inherits Fix-1 inversion; eval lane (18072) bypasses locks |
| 3 | Error honesty REL-1 (excluded-error vs scored-wrong) | **BLIND SPOT** | REL-1 lives in `scripts/autopilot/eval_tower.py`; **no** dashboard route reads eval-tower/eval-batch reports | grep: no `eval_tower`/`excluded_error`/error-rate read in any route |
| 4 | Era awareness (E7 priors) | **READS CORRECTED SOURCE** | `_autopilot_era_regions()` `dashboard.py:2317`, applied in pareto `:4011`; KPIs `current_run_only=True` `:3393` | pareto "all_eras" era-labeled + speed-deinflated; default = current era |
| 5 | Calibration provenance (`confidence_is_real`) | **BLIND SPOT** | `confidence_is_real` only in `src/autopilot_core/rlvr_tiers.py`, `scripts/autopilot/eval_tower.py`; **no** route/HTML reference | grep: 0 hits for calibration/ECE/`confidence_is_real` in routes or `dashboard.html` |
| 6 | Circuit breakers / forced-role fallback | **BLIND SPOT** (+ fragmented where it exists) | breaker state only at `src/api/routes/health.py:224` (per-process `health_tracker`); `dashboard.html` never fetches `/health`; `forced_role_fallback` unsurfaced | grep of `dashboard.html` fetch list: no `/health`, no breaker/fallback panel |
| 7 | Journal rotation (numbered shards) | **READS CORRECTED SOURCE** | `_autopilot_journal_shards()` `dashboard.py:2390` + `_read_autopilot_journal_rows()` `:2425` read base + all `_<n>.jsonl` | rotated `autopilot_journal_1.jsonl` present on disk and included |
| 8 | Freshness contract (envelope + coherent snapshot) | **IMPLEMENTED but INSUFFICIENT** | `dashboard_freshness.py` classify/envelope/stamp; `value_consistency` used only at `dashboard.py:4324` | age-only; no value-consistency reconciles declared-mode vs realized fleet; coherence is intra-worker only |

---

## Findings by severity

### CRITICAL

**C1 — NUMA-mode / fleet-health inversion driven by launch env, non-deterministic across the
worker pool.** `active_stack_numa_mode()` (`dashboard_topology.py:122`) returns the value of
`ORCHESTRATOR_STACK_NUMA_MODE` *first* (line 140), before the hardened fail-closed manifest reader
(line 150, commit 22e32ec2) it was supposed to gate on. The live fleet is quarters-only (12 quarter
llama-servers; full ports 8070/8072/8085 dead — `worker_general` is even `placement_policy:
full_disabled`). When a serving worker's env is `full`, `expected_stack_services("full")` keeps only
the full instances (`stack_manifest._filter_by_numa_mode`), so in `_build_topology_nodes`
(`dashboard.py:4636`) the **live quarters get `expected=False` and the dead fulls become
`expected-stack-server` down rows** — the operator sees the healthy fleet as rogue and the absent
fulls as missing. Proven live: GET#1 (env=full) inverted; GET#5 (env=quarter) correct.

Two compounding causes make this un-self-correcting:
1. **Worker-pool env divergence.** `ps` + `/proc/<pid>/environ` showed concurrent masters/workers
   with `full`, `quarter`, and `UNSET`. `--workers 6` means a given poll hits a random worker, so
   `stack_numa_mode` can read `full` on one 5 s poll and `quarter` on the next.
2. **The intended fix is itself unusable.** The runtime-facts manifest
   (`/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json`, written 09:08:44Z) carries the correct
   `runtime_stack.stack_numa_mode="quarter"` but `selected_servers=[]` / `selected_ports=[]`. The
   fail-closed guard (`_fail_closed_runtime_stack_numa_mode`, requires a non-empty lineup) correctly
   rejects it → returns `None` → falls to the env/`both` default. So even removing the env would
   yield `both`, not `quarter`. The launcher wrote the mode but not the lineup — an
   *intent-not-realized writer*.

The single authoritative source — the realized fleet from `_discover_llama_ports()` — is already
computed for the node list but is not used to derive the mode or the `expected` flags.

### HIGH

**H1 — Circuit-breaker and forced-role-fallback state is a dashboard blind spot (EV-11c incident
class).** The EV-11c incident was *caused* by breakers tripping (deadline-starved 1 s calls) and the
orchestrator silently role-falling-back worker_math→worker_general 90×. Breaker state exists only at
`GET /health` (`routes/health.py:224`, per-process `health_tracker`, and it actively probes
llama-servers). `dashboard.html` never fetches `/health`; no panel surfaces breaker state or
`forced_role_fallback` churn. During exactly the incident the fixes were built for, the dashboard is
dark.

**H2 — REL-1 eval error-rate / reliability is a blind spot.** The REL-1 honesty guards (in-band
`[ERROR:` detection, forced-role integrity, error-row exclusion) live in the eval harness
(`scripts/autopilot/eval_tower.py`, `seeding_*.py`) and are written into eval reports. No dashboard
route reads eval-tower/eval-batch reports; nothing surfaces excluded-error rows vs wrong answers or
an error/reliability rate. The pareto/optimization "reliability" objective is autopilot
*trial-outcome* reliability, not eval error classification — the two must not be conflated by a
reader.

**H3 — Contention / scheduling panel shows a per-worker fragment as fleet truth.**
`contention.metrics_snapshot()` returns in-process `ContentionGate` singleton counters
(`contention_gate.py:439`, singleton `:461`). With `--workers 6`, `active_decodes_by_role`,
`contention_admitted_count`, blocked/wait counts reflect only the answering worker.
`per_role_scheduling` reads the per-process `_real_primitives._backends` and came back **empty** at
GET#3. Migration counters are likewise per-worker. No worker provenance is attached, and the
endpoint docstring mislabels the source as "from region-lock holders" (it is not — it is an
in-process counter). Numbers displayed without provenance; systematic undercount.

**H4 — Cross-worker snapshot incoherence.** The freshness/coherent-snapshot machinery guarantees one
`generated_at` *within* a worker's build, but different workers (divergent env, divergent in-process
counters) produce mutually inconsistent frames. `/topology`=`full` beside `/region_locks`=`quarter`
was observed. The "one coherent snapshot" contract does not hold across the 6-worker pool.

### MEDIUM

**M1 — region_locks re-implements the held-set SoT instead of calling it.** The grid re-derives
holders from `/proc/locks` inline (`dashboard.py:998-1029`) rather than calling
`cpu_region_lock.held_regions_by_role()` (`:419`). Functionally region-precise today (same
`_current_lock_owner_pids` primitive, so it is NOT the over-reporting `active_region_holders` view —
good), but it is duplicated logic that can drift from the placement plane's SoT.

**M2 — `launch_selected` grid annotation inherits the Fix-1 inversion.** When env=`full`, the
region-lock display marks the dead full instance `launch_selected=True` and the live quarters
`launch_selected=False` (with a "not selected by stack_numa_mode=full" tooltip), i.e. the same
inverted selection story as C1. Held-state cells remain correct; the selection overlay is wrong.

**M3 — The active eval-batch serving lane is unattributed and lock-invisible.** EV-11c serves on
port 18072 (3 procs, `-np 14`), which renders as `extern_18072 / external-llama-server /
expected=False` and takes no interactive CPU region lock — so a live 4-wide eval shows `0` held
regions and `active_decodes_by_role: {}`. Faithful *for the interactive lane*, but the operator
watching a running eval sees no activity attributable to it.

**M4 — Calibration provenance has no plumbing.** `confidence_is_real` never reaches a dashboard
surface. Today that is a pure blind spot (calibration/ECE simply isn't shown); it becomes a
misdisplay risk the moment any panel starts showing confidence without carrying the flag.

### LOW

**L1 — Journal concatenation is not era-sliced.** `_read_autopilot_journal_rows()` concatenates all
shards (Jun-27 base run + Jul-16 `_1` run) with no era filter. Quality-gating views are era-aware
(pareto era-labeling; KPIs `current_run_only`), but a current run that *straddles* the E7 boundary
(run start Jul-16 vs E7 ~Jul-18/20) could blend pre/post-E7 quality inside a single "current"
window. Low impact because the era-labeled pareto is the decision surface.

**L2 — Warm-only servers marked `expected` in `full` mode.** `worker_fast` (8102) and
`eval_batch_frontdoor` (18070) show `expected-stack-server / expected=True / running=False`; they are
warm/explicit-only and not normally launched, so "expected down" slightly overstates a problem.

### No finding

**Fix 7 (journal rotation)** — clean. All shards read, freshness keyed to newest shard by mtime.

---

## Prioritized fix list (file:line targets)

1. **[C1] Derive NUMA mode and `expected` from the realized fleet, not the env.** In
   `dashboard_topology.py:active_stack_numa_mode()` (122) and `expected_stack_services()` (461),
   demote `ORCHESTRATOR_STACK_NUMA_MODE` below a realized-fleet check built on the port set already
   returned by `_discover_llama_ports()` (347). A port that is live is `expected`; a configured-but-
   dead full is `absent-by-policy`, not `missing`. Treat the env as a spawn-time hint only.
2. **[C1] Repair the manifest writer's intent-not-realized gap.** The launcher must write
   `runtime_stack.selected_servers` / `selected_ports` alongside `stack_numa_mode`, so the hardened
   reader (`_fail_closed_runtime_stack_numa_mode`, `:150`) has a lineup to accept. (Writer lives in
   `scripts/server/runtime_facts_manifest.py`.)
3. **[C1/H4] Give the worker pool one env / one SoT.** Ensure all `uvicorn --workers 6` workers
   inherit an identical `ORCHESTRATOR_STACK_NUMA_MODE` (or, preferably per #1, none — read the
   realized fleet). Add a value-consistency check (reuse `dashboard_freshness.value_consistency`)
   that reconciles declared mode vs realized fleet and badges the topology panel when they diverge.
4. **[H1] Add a breaker/fallback panel.** Surface `health_tracker.get_status()` per endpoint URL and
   a `forced_role_fallback` event feed on the dashboard; key it to the realized fleet, not a role's
   private URL copy. Make it multi-worker-aware (aggregate or label the worker).
5. **[H2] Surface REL-1 eval error-rate.** Add a reader for the latest eval-tower/eval-batch report
   that displays excluded-error rows distinctly from wrong answers, plus an error/reliability rate.
6. **[H3] Fix contention-panel provenance.** Either aggregate the per-worker gate counters into a
   shared store, or label each reading with its worker PID and stop presenting it as fleet-wide;
   correct the endpoint docstring (`dashboard.py:635`) that claims "from region-lock holders".
7. **[M1] Replace the inline held-set derivation** (`dashboard.py:998-1029`) with a call to
   `cpu_region_lock.held_regions_by_role()` so the panel and the placement plane share one SoT.
8. **[M2] Recompute `launch_selected`** from the realized fleet once #1 lands (falls out for free).
9. **[M3] Attribute the eval-batch lane** (18072) to its role in `_discover_llama_ports`/port hints.
10. **[L1] Era-slice the KPI window**, not just the run window, when a run straddles an era boundary.

---

## Evidence appendix (live captures)

- Realized fleet (`ps`, quarters-only): live `8080/8180/8280/8380` (frontdoor q0-3),
  `8082/8182/8282/8382` (worker_general q0-3), `8185/8285/8385/8485` (ingest q0-3), `8083`
  (architect), `8086/8087` (vision), `8090-8095` (embedders); **dead**: `8070`, `8072`, `8085`.
- Worker env divergence: PID 1778291=`full`, PID 1851981=`quarter`, PID 1854520=`UNSET`.
- Manifest `/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json` @09:08:44Z:
  `runtime_stack.stack_numa_mode="quarter"`, `selected_servers=[]`, `selected_ports=[]`.
- GET#1 `/topology` (env=full worker): `stack_numa_mode=full`; frontdoor.q0-3 / worker_general.q0-3
  / ingest.q0-3 all `expected=False`; 8070/8072/8085 `expected-stack-server, running=False`.
- GET#5 `/topology` (env=quarter worker): `stack_numa_mode=quarter`; 0 rogue quarters, 0 missing
  fulls.
- GET#2 `/region_locks`: `stack_numa_mode=quarter`, quarters `launch_selected=True`, full
  `launch_selected=False`; 0 regions held (interactive lane idle; EV-11c on the 18072 eval lane).
- GET#3 `/contention`: `active_decodes_by_role={}`, `contention_admitted_count=0`,
  `per_role_scheduling=[]` (per-worker fragment).

---

## Implementation record

**2026-07-22 — C1 + M2 landed** (`epyc-orchestrator@e97d4ed9`, branch
`spec-dec-mtp-refresh-2026-06-22`; owned dashboard route/template files + tests only).

- [x] **[C1] Realized-fleet-first NUMA-mode resolution** ✅ 2026-07-22 —
  `dashboard_topology.active_stack_numa_mode()` reworked to resolve
  **realized live fleet (bare-TCP probe via `scripts.server.realized_fleet.derive_realized_numa_mode`) > hardened runtime-facts manifest > `ORCHESTRATOR_STACK_NUMA_MODE` env hint > `both` default**. The env is
  demoted to a last-resort spawn-time hint, so a worker that inherited `full`
  can no longer invert a quarters-only fleet. New `active_stack_numa_mode_resolution()`
  returns provenance (`mode`/`source`/`realized`/`manifest`/`env`/`disagreements`).
- [x] **[C1] Realized probe runs in-process at request time, TTL-cached** ✅ 2026-07-22 —
  `_probe_realized_numa_mode()` (isolated seam) + `_cached_realized_numa_mode()` with
  a ~5s TTL so 2 Hz × 6-worker polling collapses to one probe. Fully fail-safe
  (any error → `None` → falls through to manifest/env/default).
- [x] **[C1/H4] Visible provenance annotation** ✅ 2026-07-22 — `stack_numa_mode_provenance`
  added to the `/topology`, `/region_locks`, and coherent `snapshot` payloads;
  `dashboard.html` renders a topology mode badge that goes amber and shows
  "env disagrees: full" when a lower-precedence source contradicts the realized fleet.
- [x] **[M2] `expected`/rogue + `launch_selected` inversion fixed** ✅ 2026-07-22 —
  both derive from the realized-first mode (fell out of C1): live quarters read
  `expected=True`, dead fulls are absent-by-policy, never surfaced as
  `expected-stack-server` down rows. Guarded by a 12-quarter + env=full inversion
  regression test.
- [x] **Tests** ✅ 2026-07-22 — realized-over-env, inversion regression,
  manifest-beats-env, manifest-rejected fallback ordering, TTL-cache probe-storm
  collapse, provenance badge (route-HTML). Existing dashboard suites kept green
  (realized probe neutralized in their fixtures). Two `test_dashboard_helpers`
  failures remain (`test_port_hints_follow_current_full_mode_priors`,
  `test_topology_activity_initializes_expected_embedder_bucket`) — **pre-existing
  and environmental** (they read the live host's empty `selected_servers` manifest;
  both fail identically on clean HEAD, unrelated to this change).

**Not done (deferred, still open):**

- [ ] **[C1 fix #2] Manifest writer intent-not-realized gap** — writer lives in
  `scripts/server/runtime_facts_manifest.py` (other-agent ownership); ESC-8 fixes
  already rewrote the writer to derive `selected_servers` from realized state, but
  the live manifest still shows an empty lineup — verify separately.
- [ ] **[C1 fix #3] One env / one SoT across the `--workers 6` pool** — process/launch
  concern (`scripts/server/*`), out of dashboard-file ownership.
- [x] **[E8-PANELS] Era-honest pareto/GEPA plots for E8** ✅ 2026-07-27 — implemented in
  orchestrator `64c05ca7` (7 files, +828/−48, 285 focused tests green), converging with
  Codex's independent region-lock membership fix (22:17 same night). Delivered: (A) E8 era
  pickup pinned by test against the live registry; (B) per-point `historical_instrument`
  labeling, faded historical series, E8 boundary annotation (label-never-rescale); (C) GEPA
  no-op provenance window 2026-06-04→`ed6288ea` hatched + caveat badge; (D) ALL live
  instances render in the region-lock panel with "n/a (no lock domain)"; (E — scope-extended)
  authority banner reads live holds ("quality: HELD pending E8 baseline; speed: pending E8
  numeric rerun N/16"); `decision_grade_possible=False` while any hold is open. Python-side
  takes effect at the deferred API reload (reseed trial boundary); HTML live on refresh.
  - [ ] **[E8-PANELS-a] Reconcile the rerun counter fields**: banner shows the gate marker's
    `frontier_rerun_required` count (0/16) while `frontier_rerun_pending_clear` carries the
    live 15/16 — unify which field the gate updates mid-run (cosmetic, confusing).
  - [ ] **[E8-PANELS-b] Commit the ratified era-registry row**: an uncommitted `eval_quality`
    E8 row sits in `orchestration/instrument_eras.yaml` (output of the operator's quality-fence
    transaction; human-amendment provenance) — commit it with its receipt reference.
  - [ ] **[E8-PANELS-c] Hub pct presentation**: `pct_all_done` reads intake sweeps as decline
    (denominator inflation, see 2026-07-27 forensics) — surface absolute `all_tasks_done` +
    a newly-filed-tasks series on the :8100 hub (owner may also be
    loops-and-dashboards-audit-2026-07-05.md).
- [x] **[E8-TRIALS-COLD] Validate restart-surface trial speed samples for cold-start
  contamination** ✅ 2026-07-27. Retrospective row-level audit cleared the sealed E8
  frontier: restart attempts 1442/1455 were tier-0 skips because AP-3 restart was disabled,
  so neither relaunched a role; trials 1443/1445/1453 each recorded all 65
  `cache_warm_state=warm` covariates. Only warm trial 1445 entered the sealed frontier
  (`[1445, 1446, 1450]`) and supplied its speed maximum. The terminalizer itself did not
  enforce or attest this predicate. Original concern: `spec_decode_role_restart` trials
  relaunch servers and may sample speed un-prewarmed (guardrail: cold-start collapses to
  24-35 t/s vs 55-70 warm; live tap showed worker at 18.3 t/s ~1 min post-restart; trials
  1443/1445/1453 logged s=8.4/9.7/4.4). Owner overlap: autopilot-decision-plane-audit §E8
  RE-ARM; filed here because the evidence surfaced via the dashboard tap. The E8 reseed's honest-instrument trials (q≈1.71–1.77) plot
  against pre-E8 points measured on the laxer instrument (q≈1.85–2.04 plateau), inviting a
  false regression read. The pareto panel's era machinery exists (`_autopilot_era_regions()`
  `dashboard.py:2317`, applied `:4011`, default=current era) but was certified for E7 — verify
  and fix three things: (a) era regions derive from the LIVE sources (`instrument_eras.yaml`
  E8 rows appended 2026-07-26 + `pareto_epoch_ts=1785004723` = the E8 fence), not hardcoded
  E7 boundaries — E8 trials must render as the current-era series with the boundary line
  annotated at 2026-07-25T18:38:43Z; (b) the QUALITY axis gets era labeling too — C1 showed
  only speed was era-fenced/de-inflated; pre-E7/E7/E8 quality points are different-instrument
  numbers (41-suite pool + B7 scorer + extractor fixes ≈ −0.1..−0.3 q systematic) and must be
  rendered as greyed "historical prior (era, instrument)" series, never one undifferentiated
  scatter. Never rescale values — label eras (append-only constitution). (c) GEPA/optimizer
  panel: hatch or grey the 2026-06-04→07-25 reflective-mutation NO-OP window (every reflection
  raised pre-LM-call; optimizer provenance broken) or suppress the panel until ≥1 post-fix
  GEPA trial exists; tooltip carries the provenance caveat. Panels stamp era + generated_at
  per the freshness contract.
- [ ] **[E8-TRIALS-COLD-GUARD] Enforce restart/cold eligibility in future frontier
  terminalizers**: reject or quarantine restart-surface evidence until an affirmative
  prewarm/cache-warm predicate is present, and persist the predicate in the terminalization
  receipt. The 2026-07-27 retrospective clears E8 factually; it does not establish this
  forward instrument control.
- [ ] **[H1] Circuit-breaker / forced-role-fallback panel** — deferred (stretch).
- [ ] **[H2] REL-1 eval error-rate surface** — deferred (stretch).
- [ ] **[H3] Contention-panel per-worker provenance**, **[M1] region_locks held-set
  SoT reuse**, **[M3] eval-batch lane attribution**, **[M4] calibration provenance**,
  **[L1] era-sliced KPI window** — untouched.
