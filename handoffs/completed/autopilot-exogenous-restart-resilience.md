# Handoff: Autopilot resilience to exogenous service restarts + crash recovery

**Status:** ✅ COMPLETE 2026-05-24 — all phases (0, 1, 2, 3, 4, 5, 6a, 6b, 7) executed; orchestrator stack reloaded; ready for autopilot restart (operator-owned).
Phase 7 scrub was determined no-op: no quality=0 exogenous-pollution signatures
found in trustworthy entries since 2026-05-20 (autopilot was down during all
implementation-window reloads). Implementation commits in `epyc-orchestrator`:
`89ecba3` (Phase 1) · `10dd8d1` (Phase 2) · `e7c53a7` (Phase 3) · `ca527b2` (Phase 4) ·
`db068bd` (Phase 5) · `3154c48` (Phase 6a) · `8b18f35` (Phase 6b). Live verification:
`/dashboard/api/version` returns `git_sha=8b18f35`; all 20 llama-server ports
marked `source=stack_commands` via `/dashboard/api/llama_fleet_ids`.

**Historical status:** REVISED PROPOSAL r2 — external audit complete + clarifications
folded in (2026-05-23 r2). Original Phase 5/6 ordering was unsafe and has
been corrected. R1-R6 clarifications from the second-pass audit are inline.
Do not implement older copies of this handoff.
**Author:** dashboard/autopilot ops session, 2026-05-23.
**Revision history:**
  - r1 (initial): scope, taxonomy, design, phases, risks.
  - r1.5 (external audit): four correctness blockers identified
    (safety-gate ordering, Pareto pollution, seed-batch metadata gap,
    atomicity assumption) and folded into design + phases. Section 3.8
    documents them.
  - r2 (this revision): six clarifications folded in — open questions
    resolved, role→port mapping source pinned, recovery helper
    `_maybe_reimport_pareto_from_journal` fully spec'd, "fail loudly"
    semantics made concrete, concurrent constrained-creativity work
    flagged for rebase, Phase 6 split into 6a/6b.
**Scope:** `scripts/autopilot/*` + `scripts/server/*` + `src/api/routes/dashboard.py` +
`scripts/benchmark/{seeding_orchestrator,seeding_eval,seeding_injection,feature_validation_live}.py`
in the `epyc-orchestrator` repo.
**Implementation prerequisite:** autopilot must be SHUT DOWN before any work
begins (see Phase 0). Implementation finishes with a journal scrub of
already-polluted entries (Phase 7).
**Implementation status:** ZERO code written. This document is the entire
artifact of the session; no commits, no scripts run, no autopilot restart.

**Concurrent-work coexistence (read before editing shared files):** the
"constrained-creativity planner upgrade" landed in
`scripts/autopilot/experiment_journal.py` (new `falsifier`,
`rubric_scores` fields on `JournalEntry`) and `scripts/autopilot/autopilot.py`
(new constants `CREATIVITY_N`, `TAIL_WINDOW`, `TAIL_SEED_COUNT`,
`STAGNATION_HV_EPS`, `STAGNATION_STREAK`; new `### Exploration mode`
template section) on 2026-05-23 between this handoff's r1 and r2 audits.
No semantic conflict with this handoff — the proposed
`bug_corrupted_by` tagging, `eval_details["exogenous_retries"]` audit
block, and `### Journal Trustworthiness`/`### Hypotheses Under Test`
template sections are orthogonal. But implementation will edit those
same files; rebase carefully so neither initiative regresses the other.

---

## 1. TL;DR

Autopilot's experiment journal currently gets polluted three ways:

1. **Orchestrator API reloaded mid-trial** (operator runs
   `orchestrator_stack reload orchestrator`) → every /chat fails →
   `EvalResult(quality=0, reliability=0)` → journaled as "quality_floor"
   failure → planner learns wrong lesson.
2. **Llama-server reloaded mid-trial** (operator reloads `frontdoor`,
   `worker_general`, etc.) → same downstream effect.
3. **Autopilot SIGKILL'd mid-trial** at the narrow window between
   `dispatch_action()` and `journal.record()` → orphaned Pareto entry
   with no journal evidence → hypothesis chain becomes inconsistent on
   restart.

Real production crashes (4) llama-server OOM-killed, (5) network blip
during a request, etc., are NOT in this category — those are real
infrastructure signals the planner should journal and react to.

The fix uses **deterministic startup-marker files** for each piece of
infrastructure (orchestrator, each llama-server, autopilot itself), which
let any consumer compare a "fleet identity" before/after a failure to
classify it as "operator-initiated reload" vs "genuine production
incident". For operator-reloads the questions affected are **retried in
place** until the service is healthy again, so the trial completes
normally and "picks up where it left off". For genuine crashes nothing
changes — the failure flows through to the journal as before.

Per-question (not per-trial) tagging: the trial as a whole is only
marked `bug_corrupted_by` when at least one question stayed
**unrecovered** after the retry window — i.e. the orchestrator/llama
stayed down past the wait timeout. Trials that weathered a brief reload
cleanly carry only audit info in `eval_details` and are fully usable as
planner evidence.

Critical audit constraint: classification must happen **before** both
`gate.check()` and `archive.update(...)`. An unrecovered exogenous trial is
not a safety failure and must not increment `consecutive_failures`, trigger
rollback, enter the Pareto archive, or update species-effectiveness as a
real failed experiment. It is journaled only as a bug-corrupted operational
placeholder so the planner can see the interruption without learning from it.

Crash-recovery constraint: current state/archive persistence is direct
`Path.write_text(...)`, not atomic. Atomic temp-file + `os.replace()` writes
are now a prerequisite before adding an `in_flight_trial` marker; otherwise
SIGKILL during persistence can leave truncated JSON and prevent recovery
logic from loading at all.

---

## 2. Problem context

### 2.1 Cost of pollution

When autopilot records a trial with quality=0 because the orchestrator
was being reloaded, the next planner invocation sees:

- `### Pareto Archive` — gains a dominated entry at (0, 0, ?, ?).
- `### Experiment Journal (last 20 entries)` — shows the trial with
  failure_analysis text describing a fake quality regression.
- `### Hypotheses Under Test` — the operator's hypothesis ("does
  prompt_mutation X improve quality?") is recorded as REFUTED.
- `### Recent Insights (structured)` — the action_type bucket for
  this hypothesis has a +0 success / +1 failure tick.
- `### Species Effectiveness` — counts the trial as a species
  ineffectiveness signal.
- Safety gate: `consecutive_failures` counter increments; if 3 of these
  happen in a row, a real rollback fires.

The downstream cost is high relative to the cause (a 5-10s reload window
during dev work). Today the operator has to manually scrub afterward
via `scripts/autopilot/scrub_journal.py` — which itself requires
autopilot to be down.

### 2.2 Why this is fixable deterministically

Every process start gets a unique startup timestamp (or equivalent
identifier). A consumer that captures the identifier before a request
can compare it to the identifier after a failure: if it changed, the
service was restarted in between, so the failure is exogenous. If it's
the same, the failure was real. There's no statistical estimation
involved — it's a structural comparison.

The only complication is **multi-worker uvicorn**. The orchestrator
runs `--workers 6`, each with its own `_SERVER_STARTED_AT = time.time()`
set at module load. A naive comparison would false-positive when
consecutive requests hit different workers. The fix is a **fleet-level
marker file** written by whichever script launches uvicorn, BEFORE
workers fork; every worker reads the same file at import time, so
`/dashboard/api/version` returns the same `server_started_at` across
all six workers.

---

## 3. Findings from codebase investigation

### 3.1 Single funnel for /chat traffic (good)

All autopilot dispatch paths converge on
`scripts/benchmark/seeding_orchestrator.py:504-576`
(`call_orchestrator_forced`). The chain:

```
autopilot.py:704     dispatch_action(action={"type": "seed_batch", ...})
  → actions.py:81    _action_seed_batch()
  → species/seeder.py:105   Seeder.run_batch()       (sequential per question)
  → benchmark/seeding_eval.py:796  evaluate_question_per_role()
  → benchmark/seeding_eval.py:233  _eval_single_config()
  → benchmark/seeding_orchestrator.py:255  _call_orchestrator_with_slot_poll()
  → benchmark/seeding_orchestrator.py:504  call_orchestrator_forced()
  → httpx.post(f"{url}/chat", ...)
```

Current behavior at line 575-576: ALL exceptions caught and swallowed,
returns `{"answer": "", "error": str(e)}`. No retry, no exception
propagation, no distinction between transient and persistent errors.

Two other quality-extracting /chat callers (per user direction "anything
that extracts performance/quality metrics for subsequent decision
making"):

- `scripts/benchmark/feature_validation_live.py:LiveValidator._run_prompts`
  — A/B test harness; results feed structural experiments.
- `scripts/benchmark/seeding_injection.py:_inject_single_reward` and
  `_inject_per_role_rewards_http` — POSTs `/chat/reward`; reward signal
  shapes Q-learning.

GitNexus audit result: `call_orchestrator_forced` has **HIGH** upstream
blast radius (14 impacted symbols/processes across Autopilot, Benchmark,
and Pipeline Monitor). Any signature change must be backward-compatible
(`watcher=None`, optional `_meta` response field only) and existing non-
autopilot callers must continue to work without fleet markers.

### 3.2 Single funnel for llama-server launches (good)

All llama-server starts flow through
`scripts/server/orchestrator_stack.py:start_server()` at lines 603-849.
Four paths (vision / embedding / worker_pool / standard) all converge on
`subprocess.Popen + wait_for_health(port, timeout)`. No external
auto-restart (no systemd / supervisor / monit found). Operator-only
restarts.

### 3.3 Reactive PID-drift detection exists but unused for autopilot

`scripts/server/stack_commands.py:841-850` already has:
```python
if not alive and is_port_in_use(info.port):
    # PID drift can happen if the original launcher PID exits while
    # a listener remains healthy on the same port.
    replacement_pids = _pids_on_port(info.port)
    ...
```

But this is reactive (status() inspection) and only updates the
dashboard's state. It doesn't notify autopilot.

### 3.4 Autopilot SIGKILL corruption window

Trace of `autopilot.py` main loop (lines 704-930):

| Line | Action |
|---|---|
| 704 | `eval_result, species_name = dispatch_action(...)` |
| 713 | If eval_result is None: bump trial_counter, save_state, continue |
| 759-770 | `archive.update(ParetoEntry(...))` ← **archive mutated in-memory** |
| 772-782 | Strategy-store write (if frontier improvement) |
| 837-879 | `journal.record(JournalEntry(...))` ← **journal write** |
| 926-927 | `trial_counter += 1; state["trial_counter"] = ...` |
| 929 | `archive.save(state)` ← Pareto persisted to disk |
| 930 | `save_state(state)` ← state persisted to disk |

**Corruption window analysis:**

| Window | What's on disk if SIGKILL fires here | Verdict |
|---|---|---|
| 704-758 | trial_counter=N, pareto=old, journal=old | CLEAN — trial cleanly forgotten |
| 759-836 | trial_counter=N, pareto=old (in-memory only), journal=old | CLEAN — `archive.save()` not yet hit |
| **837-928** | **trial_counter=N (stale), pareto=old, journal=NEW (durable append)** | **CORRUPT — journal has trial N+1 but pareto and counter unaware** |
| 929 | trial_counter=N (stale), pareto=NEW, journal=NEW | INCONSISTENT — trial_counter behind journal/pareto |
| 930 | trial_counter=N+1, pareto=NEW, journal=NEW | CLEAN — fully consistent |

The Pareto-archive integrity check at `pareto_archive.py:90-99` only
catches complete frontier loss, not single-entry gaps, so this
corruption is currently invisible to startup-time integrity validation.

**Both windows are narrow (microseconds in normal flow) but real.** A
SIGKILL during normal operation is unlikely to land here; a SIGKILL
delivered during a slow disk write is more plausible. Worth handling
because the corruption is silent.

### 3.5 .autopilot.lock has no stale-detection

`orchestration/.autopilot.lock` is held by fcntl. SIGKILL releases the
lock via kernel cleanup, but the FILE remains (empty, 0-byte). Restart
acquires the lock cleanly. There's no "previous instance died unclean"
detection signal — the next instance just resumes.

### 3.6 Llama-server has no PID-aware request retry

`src/backends/llama_server.py:184-190` configures
`httpx.HTTPTransport(retries=3)` at the transport layer. Retries are
transparent (operator can't observe). If a llama-server restarts during
a request, httpx retries 3 times and reconnects to the new PID without
notifying the application. From the LLM's perspective the request just
hangs longer.

### 3.7 Existing infrastructure to reuse (don't reinvent)

| Utility | File | Use for |
|---|---|---|
| `wait_for_health(port, timeout)` | `scripts/server/stack_health.py:8-29` | Polling /health for orchestrator + llama recovery |
| `classify_exception(e)` | `src/observability.py:10-46` | Categorizing httpx errors into stable codes (connect_error, read_timeout, …) |
| `BackendHealthTracker` circuit breaker | `src/api/health_tracker.py:1-232` | Available for richer per-backend tracking later (v2) |
| `bug_corrupted_by` + `bug_corrupted_reason` JournalEntry fields | `scripts/autopilot/experiment_journal.py:93-94` | Auto-tagging trials with unrecovered exogenous failures |
| `DeficiencyCategory` enum | `scripts/autopilot/experiment_journal.py:19-33` | Adding new category for exogenous reload |
| Planner trustworthiness gate (excludes bug_corrupted entries) | `scripts/autopilot/experiment_journal.py:trustworthiness_score()` + `autopilot.py:CONTROLLER_PROMPT_TEMPLATE` | Reuse for hypothesis-chain filtering; verify all other learning surfaces also exclude corrupted placeholders |
| `scripts/autopilot/scrub_journal.py` CLI | Post-implementation cleanup of legacy pollution |
| Reactive PID-drift detect | `scripts/server/stack_commands.py:841-850` | Logic reusable for the llama-server watcher |

### 3.8 External audit blockers integrated into this revision

The external audit found four correctness blockers in the original plan:

1. **Safety-gate ordering bug:** original Phase 5 tagged the `JournalEntry`
   after `gate.check(eval_result)`. That still increments
   `consecutive_failures` and can trigger rollback before the entry is
   marked corrupted. Revised design classifies exogenous status before
   safety-gate evaluation.
2. **Pareto pollution bug:** original Phase 5 tagged the journal after
   `archive.update(...)`. That still admits corrupted exogenous trials into
   the archive. Revised design skips archive insertion entirely for
   unrecovered exogenous trials.
3. **Seed-batch metadata gap:** original propagation covered
   `EvalTower._eval_question()` but ignored `Seeder.run_batch()`, even
   though `seed_batch` first mutates Q-learning via per-role seeding and
   reward injection, then separately runs `tower.hybrid_eval()`. Revised
   design propagates exogenous metadata through `RoleResult`,
   `SeederBatchResult`, and `_action_seed_batch`.
4. **Atomicity assumption bug:** original risk register claimed
   `save_state()` used atomic rename. It currently writes directly. Revised
   Phase 6 starts with atomic persistence before any in-flight marker work.

Additional audit result: `EvalTower._aggregate` has **HIGH** upstream blast
radius (18 impacted symbols across Autopilot, Species, Benchmark), and
`_call_orchestrator_with_slot_poll` has **HIGH** blast radius (6 impacted
symbols/processes). Propagation changes must be minimal additive fields with
defaults and tests for all existing action families that consume EvalResult.

---

## 4. Failure-source taxonomy

| # | Source | Detection signal | Treatment |
|---|---|---|---|
| 1 | Orchestrator API reloaded by operator | Fleet marker `/mnt/raid0/llm/tmp/orchestrator_fleet_started_at` changes | Retry affected questions. If all recovered: normal trial + audit metadata only. If any unrecovered: journal bug-corrupted placeholder, skip safety gate, skip rollback, skip Pareto/archive/species learning. |
| 2 | Llama-server reloaded by operator | Per-port fleet marker `/mnt/raid0/llm/tmp/llama_<port>_started_at` changes AND the change came from the orchestrator_stack launch path | Same as #1. Requires reliable role→port hint or backend identity; without a port hint, only orchestrator-level reloads can be deterministic. |
| 3 | Llama-server crashed (production incident) | Health check fails AND no recent marker-file update (because nothing restarted it via stack_commands) | Real failure: do NOT auto-retry, do NOT tag as corrupted. The planner SHOULD see this and react. (Existing httpx transport retry of 3 still applies for transient blips.) |
| 4 | Autopilot SIGKILL'd at lines 837-929 (between journal.record and final state save) | New on-restart check: scan journal for entries with `trial_id > state["trial_counter"]` (journal advanced past last saved counter), after JSON state/archive files are readable via atomic persistence | Re-sync: bump state.trial_counter to match journal max + re-import any eligible trusted orphan into Pareto from journal eval_details |
| 5 | Autopilot SIGKILL'd at lines 704-836 (before journal.record) | New on-startup `in_flight_trial` marker in autopilot_state.json: written with atomic state save before dispatch_action, cleared only after final atomic save | If marker is present on startup, mark a "lost trial" placeholder JournalEntry with `bug_corrupted_by="autopilot_killed_mid_trial"`; skip gate and archive |

---

## 5. Design

### 5.1 Layer A — fleet markers for orchestrator + each llama-server

**Orchestrator:**
- New file: `/mnt/raid0/llm/tmp/orchestrator_fleet_started_at`
  - Contents: single line `<float_epoch_seconds>`
- Modify `scripts/server/orchestrator_stack.py:start_orchestrator()`:
  write the file atomically BEFORE invoking uvicorn. `stack_commands.py`
  only proxies to this function during start/reload; do not put the
  canonical marker write in the proxy.
- Modify `src/api/routes/dashboard.py:602`: replace
  `_SERVER_STARTED_AT = time.time()` with a read-on-import block that
  falls back to `time.time()` when the file is missing. (~12 lines.)
- `/dashboard/api/version` now returns the same `server_started_at`
  across all six workers. No new endpoint needed.

**Llama-server (per port):**
- New file pattern: `/mnt/raid0/llm/tmp/llama_<port>_started_at`
  - Contents: three lines —
      1. `<float_epoch_seconds>`
      2. `<launch_source>` ∈ {`stack_commands`, `external`}
      3. `<role>` (canonical role name; comma-separated when one
         process serves multiple roles, as worker_pool can — e.g.
         `worker_general,worker_summarize`)
    The launch_source `external` tag is for future-proofing — if
    anything other than stack_commands ever starts a llama-server, it
    should mark itself as external so the watcher can decide whether
    to treat it as benign or as a crash-recover event. The `<role>`
    line is the canonical role→port source of truth; consumers should
    NOT duplicate the mapping from `_PORT_HINTS` or `_SLOT_QUERY_PORTS`
    (both of which exist in the codebase and could drift).
- Modify `scripts/server/orchestrator_stack.py:start_server()`: write
  this file atomically (temp + `os.replace`) in ALL four launch paths
  (vision / embedding / worker_pool / standard) right before
  `subprocess.Popen`. (~20 lines, one shared helper that takes
  `(port, roles)`.)
- New endpoint `/dashboard/api/llama_fleet_ids` returns
  `{port: {started_at: float, source: str, roles: list[str]}}` for
  every llama-server marker found. Read-only; the watcher polls this
  and builds its role→port lookup from the response.

### 5.2 Layer B — `OrchestratorWatcher` utility

**New file:** `scripts/autopilot/orchestrator_watch.py`

```
class OrchestratorWatcher:
    __init__(api_url="http://localhost:8000", health_timeout_s=120,
             cache_ttl_s=2.0)
    current_orchestrator_id() -> float | None
        # GET /dashboard/api/version; cached for cache_ttl_s
    current_llama_id(port: int) -> tuple[float, str] | None
        # GET /dashboard/api/llama_fleet_ids; cached; (started_at, source)
    reference_for_role(role: str) -> dict[str, float]
        # Returns orchestrator marker plus llama_<port> when role→port is known.
        # If role is unknown/empty, returns orchestrator only.
        #
        # Role→port mapping source (canonical): the watcher reads
        # /dashboard/api/llama_fleet_ids and scans each entry's `roles`
        # field for the requested role. First match wins (a given role
        # currently maps to one process). Cached for cache_ttl_s so the
        # role→port lookup is cheap. The watcher MUST NOT consult
        # src/api/routes/dashboard_topology._PORT_HINTS or
        # scripts/autopilot/autopilot._SLOT_QUERY_PORTS — both are
        # process-local mappings that could drift from the actual marker
        # files. When role is given but no marker matches, return
        # orchestrator-only with a one-time log warning (rate-limited
        # to once per role per process).
    was_restarted_since(reference_ids: dict) -> dict[str, str]
        # reference_ids = {"orchestrator": float, "llama_8070": float, ...}
        # Returns dict of changed identifiers with classification:
        #   "operator_reload" — id changed + source field still 'stack_commands'
        #   "external_restart" — id changed + source != 'stack_commands'
        #   "unreachable" — current id is None / fleet endpoint failed
    wait_for_orchestrator() -> bool
        # wraps wait_for_health(8000)
    wait_for_llama(port: int) -> bool
        # wraps wait_for_health(port)
```

**Crash-vs-reload classification logic:**

When a `/chat` call fails AND a llama-server marker exists, the watcher
checks the `source` field. If `stack_commands` (operator-initiated), the
failure is exogenous + recoverable. If `external` (started by something
else — a watchdog, a manual `llama-server …` invocation), classify as
external_restart, which is HALFWAY between exogenous and real. The
plan's v1 behavior: treat external_restart as recoverable (retry once)
but DO journal as a real failure if retry doesn't succeed (no
bug_corrupted tag). This preserves the planner's ability to react to
unexpected llama-server restarts as genuine signals.

For real production crashes (no marker file update, llama-server PID
died and stayed dead): /health stays 503, wait_for_llama returns False,
retry fails → real failure path → normal journaling.

Port-hint rule: llama-server classification is deterministic only when the
call path can supply a target port. `seeding_eval._eval_single_config()`
has `role` and can derive `ROLE_PORT[role]`; `EvalTower._eval_question()`
uses natural routing (`force_role=""`) and should be treated as
orchestrator-only unless the orchestrator response/failure path exposes the
backend port. Do not infer a llama restart from "some marker changed" when
the request might have used a different backend.

### 5.3 Layer C — `resilient_post` shared utility

**New file:** `scripts/autopilot/resilient_http.py`

```
def resilient_post(client, url, json, timeout, watcher, llama_port=None,
                   max_retries=1) -> (response_dict, meta_dict):
    """
    POST to url with watcher-aware retry on exogenous reload.

    Arguments:
        client          httpx.Client | None  (creates one if None)
        url             full URL including endpoint path
        json            request body
        timeout         per-request timeout (seconds)
        watcher         OrchestratorWatcher instance
        llama_port      Optional port hint. When set, the watcher will
                        ALSO check that llama-server's marker for restart
                        signals. When None, only the orchestrator marker
                        is checked.
        max_retries     Default 1. Retry budget for exogenous failures only.

    Returns (response_dict, meta_dict) where meta_dict carries:
        clean             True when no exception, no retry, no marker change
        exogenous_recovered  Retry succeeded after operator reload detected
        exogenous_unrecovered  Retry exhausted or wait_for_availability failed
        external_restart   Detected a llama-server with source != stack_commands
        real_failure       Failure with no marker change, no service unreachable
        retry_count        N
        wait_s             N.NN
        marker_changes     {"orchestrator": "operator_reload", "llama_8070": ...}
    """
```

Adopted by three call sites:
- `scripts/benchmark/seeding_orchestrator.py:call_orchestrator_forced`
- `scripts/benchmark/feature_validation_live.py:LiveValidator._run_prompts`
- `scripts/benchmark/seeding_injection.py:_inject_single_reward`

Compatibility rule: `call_orchestrator_forced` accepts optional
`watcher=None` and optional `llama_port=None`; existing callers see the
same response dict except for an optional `_meta` key. No exceptions that
were previously swallowed may newly escape from this high-blast-radius
function.

### 5.4 Layer D — propagation through eval and seeding results

`scripts/autopilot/eval_tower.py` and `scripts/autopilot/safety_gate.py`
types:

```
@dataclass
class QuestionResult:
    ... existing fields ...
    exogenous_recovered: bool = False
    exogenous_unrecovered: bool = False
    external_restart: bool = False
    retry_count: int = 0

@dataclass
class EvalResult:
    ... existing fields ...
    n_exogenous_recovered: int = 0
    n_exogenous_unrecovered: int = 0
    n_external_restart: int = 0
    exogenous_question_ids: list[str] = field(default_factory=list)
    exogenous_marker_log: list[dict] = field(default_factory=list)
```

- `_eval_question` (eval_tower.py:162-236): reads `meta` from
  `resilient_post`'s return value and sets the QuestionResult fields.
- `_aggregate` (eval_tower.py:240-350): accumulates counts from
  QuestionResult list.

Seeding path types must also propagate the same class of metadata:

```
RoleResult:
    exogenous_recovered: bool = False
    exogenous_unrecovered: bool = False
    external_restart: bool = False
    retry_count: int = 0
    resilient_meta: dict[str, Any] = field(default_factory=dict)

SeederBatchResult:
    n_exogenous_recovered: int = 0
    n_exogenous_unrecovered: int = 0
    n_external_restart: int = 0
    exogenous_question_ids: list[str] = field(default_factory=list)
    exogenous_marker_log: list[dict] = field(default_factory=list)
```

- `seeding_eval._eval_single_config()` passes `llama_port=ROLE_PORT[role]`
  into `call_orchestrator_forced()` and copies `_meta` into `RoleResult`.
- `evaluate_question_per_role()` aggregates role-level metadata into its
  returned `metadata` dict.
- `Seeder.run_batch()` aggregates per-question metadata into
  `SeederBatchResult`.
- `_action_seed_batch()` must preserve the returned `SeederBatchResult` and
  merge its exogenous counters into the final trial `EvalResult` produced by
  `tower.hybrid_eval()`. Without this, the Q-learning/reward-injection phase
  can be polluted while the final eval looks clean.

### 5.5 Layer E — pre-gate trial classification + selective recording

`autopilot.py` must classify trial cleanliness before `gate.check()` and
before `archive.update(...)`.

Required ordering:

1. `dispatch_action(...)` returns `eval_result, species_name`.
2. Compute:
   - `has_exogenous_unrecovered = eval_result.n_exogenous_unrecovered > 0`
   - `has_exogenous_recovered = eval_result.n_exogenous_recovered > 0`
3. If unrecovered:
   - do **not** call `gate.check(eval_result)`
   - do **not** increment `consecutive_failures`
   - do **not** call `archive.update(...)`
   - do **not** auto-rollback or blacklist the action
   - build a `JournalEntry` with `pareto_status="dominated"` for
     backward compatibility with existing journal consumers
   - set `bug_corrupted_by="exogenous_operator_reload"`
   - set `deficiency_category=DeficiencyCategory.EXOGENOUS_RELOAD.value`
   - include all marker observations and affected question ids in
     `eval_details["exogenous_retries"]`
4. If recovered-only or clean:
   - run `gate.check(eval_result)` normally
   - call `archive.update(...)` normally
   - if recovered-only, add audit metadata to `eval_details` but leave
     `bug_corrupted_by` empty.

Pseudocode sketch:

```
has_exo_unrecovered = eval_result.n_exogenous_unrecovered > 0
has_exo_recovered = eval_result.n_exogenous_recovered > 0

if has_exo_unrecovered:
    verdict = SafetyVerdict(passed=True, warnings=["exogenous reload unrecovered"])
    failure_analysis = "Excluded: unrecovered operator/service reload during trial"
    pareto_status = "dominated"
else:
    verdict = gate.check(eval_result)
    failure_analysis = gate.analyze_failure(eval_result, verdict)
    pareto_status = archive.update(ParetoEntry(...))

entry = JournalEntry(...)

if has_exo_unrecovered:
    entry.bug_corrupted_by = "exogenous_operator_reload"
    entry.bug_corrupted_reason = (
        f"{eval_result.n_exogenous_unrecovered}/{total} questions remained "
        f"unrecovered after detected service reload (ids: "
        f"{eval_result.exogenous_question_ids[:10]}...)"
    )
    entry.deficiency_category = DeficiencyCategory.EXOGENOUS_RELOAD.value
elif has_exo_recovered:
    # Trial is sound. Surface audit only in eval_details so operator can see.
    entry.eval_details = dict(entry.eval_details or {})
    entry.eval_details["exogenous_retries"] = {
        "n_recovered": eval_result.n_exogenous_recovered,
        "question_ids": eval_result.exogenous_question_ids,
        "marker_observations": eval_result.exogenous_marker_log,
    }
```

Add `EXOGENOUS_RELOAD = "exogenous_reload"` to DeficiencyCategory enum.

The central invariant: unrecovered exogenous trials are visible in the
journal but invisible to optimizer learning surfaces (`SafetyGate`,
`ParetoArchive`, species effectiveness, hypotheses under test, recent
structured insights).

### 5.6 Layer F0 — atomic persistence prerequisite

Before adding `in_flight_trial`, change persistence helpers to atomic
write-then-rename:

- `scripts/autopilot/state_store.py:save_state`
- `scripts/autopilot/pareto_archive.py:save`
- any journal scrub/rewrite path touched by this work

Implementation shape:

```
tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
with open(tmp, "w") as f:
    f.write(json.dumps(...))
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, path)
```

Also add defensive load handling. "Fail loudly" is concrete:

- **Exit code**: 70 (`EX_SOFTWARE` per `sysexits.h`). Distinguishes
  configuration/state failure from normal-exit (0) or signal-exit (>=128).
- **stderr message** (verbatim format so log scrapers can match):
  ```
  FATAL: orchestration/autopilot_state.json is corrupt
    error: <json.JSONDecodeError message + line/col>
    path:  <absolute path>
    size:  <bytes>
  Recovery options:
    1. cp /tmp/autopilot_state.baseline-*.json orchestration/autopilot_state.json
       (latest baseline from Phase 0 snapshot)
    2. cp orchestration/autopilot_checkpoints/<timestamp>/autopilot_state.json
       orchestration/autopilot_state.json
       (most recent autopilot-managed checkpoint)
  Autopilot refuses to start with reset state.
  ```
- **Do NOT** write a fresh empty state file (would overwrite any
  partial-recovery files the operator was about to use).
- **Do NOT** touch journal files (autopilot_journal.jsonl / .tsv).
- **Do NOT** acquire the .autopilot.lock (a corrupt-state failure is
  pre-lock-acquisition; another autopilot instance may legitimately be
  trying to start after the operator restores).
- Tests must simulate a truncated state file and verify all of the
  above (rc=70, exact stderr format, no file mutations).

### 5.7 Layer F — autopilot self-crash recovery

**Two new state markers in `autopilot_state.json`:**

```
{
  ...existing fields...
  "in_flight_trial": {
    "trial_id": N,
    "action": {...action dict...},
    "started_at": float,
    "host_pid": int,
    "host_started_at": float,        # autopilot.py process startup time
  } | null,
  "autopilot_fleet_started_at": float,  # bumped on every autopilot start
}
```

**Write `in_flight_trial`** in autopilot.py at the start of every trial,
using the new atomic state save:
- After action is selected (line ~700)
- Before `dispatch_action(...)` (line 704)
- `save_state()` immediately so it's durable

**Clear `in_flight_trial`** at line 930 (after final atomic save).
Specifically: set to None and atomic `save_state()` as the last operation.

**On autopilot startup** (in cmd_start before the main loop):

```
state = load_state()
prior_in_flight = state.get("in_flight_trial")
if prior_in_flight is not None:
    # Autopilot died mid-trial. Distinguish two sub-cases:
    journal_max = journal.next_trial_id() - 1
    if journal_max >= prior_in_flight["trial_id"]:
        # The trial DID get recorded; we died between line 837 and line 930.
        # Just re-sync: bump trial_counter, save_state, clear marker.
        state["trial_counter"] = max(state.get("trial_counter", 0),
                                     journal_max + 1)
        # If Pareto archive lacks the trial, re-import from JournalEntry.
        # Specification (see _maybe_reimport_pareto_from_journal below).
        _maybe_reimport_pareto_from_journal(archive, journal, prior_in_flight["trial_id"])
    else:
        # Died before journal.record. Write a placeholder JournalEntry
        # tagged bug_corrupted_by="autopilot_killed_mid_trial" so the
        # planner can see the gap and exclude it from hypothesis chains.
        placeholder = JournalEntry(
            trial_id=prior_in_flight["trial_id"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            species="(killed)",
            action_type=prior_in_flight["action"].get("type", "unknown"),
            tier=0, quality=0.0, speed=0.0, cost=0.0, reliability=0.0,
            pareto_status="dominated",
            failure_analysis=(
                f"Autopilot process killed before journal.record() "
                f"(prior host_pid={prior_in_flight['host_pid']}, "
                f"prior host_started_at={prior_in_flight['host_started_at']}, "
                f"died at trial_id={prior_in_flight['trial_id']})."
            ),
            bug_corrupted_by="autopilot_killed_mid_trial",
            bug_corrupted_reason="incomplete trial; no eval evidence available",
            deficiency_category=DeficiencyCategory.AUTOPILOT_KILLED.value,
        )
        journal.record(placeholder)
        state["trial_counter"] = prior_in_flight["trial_id"] + 1
    state["in_flight_trial"] = None
    save_state(state)
```

**Add to DeficiencyCategory enum:**
- `AUTOPILOT_KILLED = "autopilot_killed_mid_trial"`
- `EXOGENOUS_RELOAD = "exogenous_reload"`

**`_maybe_reimport_pareto_from_journal` specification:**

```
def _maybe_reimport_pareto_from_journal(
    archive: ParetoArchive, journal: ExperimentJournal, trial_id: int
) -> bool:
    """
    Re-add a single journal entry to the Pareto archive if it landed in
    the journal but never made it into the archive (corruption window
    837 → 929 in autopilot.py).

    Returns True if the entry was re-imported, False otherwise.
    """
    # 1. Locate the JournalEntry for trial_id.
    entry = next((e for e in journal.all_entries() if e.trial_id == trial_id), None)
    if entry is None:
        return False

    # 2. SKIP corrupted entries. Bug-tagged or placeholder trials must
    #    never enter the Pareto archive. This includes both
    #    "autopilot_killed_mid_trial" placeholders and
    #    "exogenous_operator_reload" tags.
    if entry.bug_corrupted_by:
        log.info("skip re-import: trial %d is bug_corrupted_by=%s",
                 trial_id, entry.bug_corrupted_by)
        return False

    # 3. SKIP entries the archive already has.
    if any(e.trial_id == trial_id for e in archive.all_entries()):
        return False

    # 4. Construct ParetoEntry from JournalEntry fields. Note we use
    #    -cost as the third objective per the ParetoArchive convention
    #    (higher is better on all four axes). Do NOT preserve the
    #    JournalEntry's recorded `pareto_status` — that was decided
    #    when the archive was in a different state. Let
    #    archive.update() re-run the dominance check.
    p_entry = ParetoEntry(
        trial_id=entry.trial_id,
        objectives=(entry.quality, entry.speed, -entry.cost, entry.reliability),
        config_snapshot=entry.config_snapshot,
        git_tag=entry.git_tag,
        species=entry.species,
        timestamp=entry.timestamp,
        reasoning=(entry.reasoning or "")[:200],
        # parent_trial, memory_count, active_flags from the journal entry
        parent_trial=entry.parent_trial,
        memory_count=entry.memory_count,
        active_flags=list(entry.active_flags or []),
    )
    new_status = archive.update(p_entry)
    log.info("re-imported trial %d into Pareto archive (status=%s)",
             trial_id, new_status)
    return True
```

Edge cases the spec deliberately handles:
- Bug-corrupted entries (any tag) are excluded — including placeholders
  written by THIS recovery path for the prior crash. Never compounds.
- Stale `pareto_status` from the JournalEntry is discarded; the archive
  re-classifies via its own dominance check.
- Idempotent: safe to call multiple times on the same trial_id.

### 5.8 Out of scope (deferred to v2 if needed)

- Graceful drain on orchestrator reload (uvicorn config change).
- `force_action_next` to re-enqueue the exact prior action — superseded
  by the inline retry mechanism (recovered trials complete normally; if
  the orchestrator stays down past 120s the trial is journaled corrupt,
  trustworthiness gate excludes it, planner picks fresh).
- Retry-budget tracking across trials (a "stop retrying if 5 retries
  failed in 10min" governor).
- Auto-restart watchdog for llama-server crashes.
- BackendHealthTracker circuit-breaker integration (already exists for
  internal backend; v2 could route external traffic through it too).

---

## 6. Implementation phases

Strict ordering. Each phase has a verification gate. The plan does NOT
proceed to the next phase until the gate passes.

### Phase 0 — Stop autopilot + capture baseline (REQUIRED PREREQUISITE)

```bash
# Verify autopilot is not running
pgrep -af "autopilot.py start"

# If running, stop cleanly
kill -TERM $(pgrep -f "autopilot.py start")
sleep 5
# If still alive, escalate
kill -KILL $(pgrep -f "autopilot.py start") 2>/dev/null
sleep 1
# Verify dead
pgrep -af "autopilot.py start" && echo "FATAL: autopilot still alive" && exit 1

# Remove the .autopilot.lock (if dangling)
rm -f /mnt/raid0/llm/epyc-orchestrator/orchestration/.autopilot.lock

# Snapshot the journal + state for rollback baseline
cd /mnt/raid0/llm/epyc-orchestrator
cp orchestration/autopilot_state.json /tmp/autopilot_state.baseline-$(date +%s).json
cp orchestration/autopilot_journal.jsonl /tmp/autopilot_journal.baseline-$(date +%s).jsonl
cp orchestration/autopilot_journal.tsv /tmp/autopilot_journal.baseline-$(date +%s).tsv

# Baseline counts for verification
python3 -c "
import sys; sys.path.insert(0, 'scripts/autopilot')
from experiment_journal import ExperimentJournal
j = ExperimentJournal()
print('baseline trial_counter:', j.next_trial_id())
print('baseline trustworthy:', j.trustworthiness_score())
"
```

**Gate:** autopilot is confirmed not running, baseline files exist in
`/tmp`, state checksums recorded.

### Phase 1 — Fleet markers + Watcher utility (no behavior change)

Add the marker-writing logic to `orchestrator_stack.py`.
Modify `dashboard.py` to read the orchestrator marker. Build the
`OrchestratorWatcher` class with full unit-test coverage.

**Critical files:**
- `scripts/server/orchestrator_stack.py:start_orchestrator` (orchestrator marker)
- `scripts/server/orchestrator_stack.py:start_server` (llama-server markers)
- `src/api/routes/dashboard.py:602` (read orchestrator marker)
- `src/api/routes/dashboard.py` (new `/llama_fleet_ids` endpoint)
- `scripts/autopilot/orchestrator_watch.py` (NEW)
- `tests/unit/test_orchestrator_watcher.py` (NEW)

**Verification gate:**
- Restart orchestrator via `orchestrator_stack reload orchestrator`,
  observe marker file mtime + content changes; observe all six workers
  return the same value via curl `/dashboard/api/version`.
- Restart one llama-server via `orchestrator_stack reload frontdoor`,
  observe per-port marker file changes; observe `/llama_fleet_ids` shows
  the bump.
- Unit tests pass.

### Phase 2 — `resilient_post` utility + unit tests

Build the shared retry helper. Pure code addition; no call sites
adopt it yet, so behaviour is unchanged.

**Critical files:**
- `scripts/autopilot/resilient_http.py` (NEW)
- `tests/unit/test_resilient_http.py` (NEW, mocks watcher + httpx)

**Verification gate:** Three test scenarios pass:
- Clean success path (no exception, no retry, meta=clean)
- Exogenous recovered (mock httpx raises once → watcher reports restart
  → wait + retry succeeds → meta carries `exogenous_recovered=True`)
- Exogenous unrecovered (mock httpx raises persistently → watcher
  reports restart → wait succeeds → retry still raises → meta carries
  `exogenous_unrecovered=True`)
- External restart (marker `source=external`) classified separately

### Phase 3 — Call-site adoption (3 files)

Wire `resilient_post` into:
- `scripts/benchmark/seeding_orchestrator.py:call_orchestrator_forced`
  — accept `watcher` kwarg, default None (preserves existing call
  signature for any non-autopilot callers), plus optional `llama_port`
- `scripts/benchmark/feature_validation_live.py:LiveValidator._run_prompts`
- `scripts/benchmark/seeding_injection.py:_inject_single_reward`

The response shape from `call_orchestrator_forced` gains an optional
`_meta` field carrying the meta dict; downstream consumers ignore it
unless interested.

**Critical files:**
- `scripts/benchmark/seeding_orchestrator.py:504-576` (~15 lines)
- `scripts/benchmark/seeding_eval.py:_eval_single_config` (derive/pass `llama_port`)
- `scripts/benchmark/feature_validation_live.py:LiveValidator._run_prompts` (~10 lines)
- `scripts/benchmark/seeding_injection.py:_inject_single_reward` (~10 lines)
- `tests/unit/test_seeding_orchestrator_resilient.py` (extend)

**Verification gate:** All existing tests still pass + new tests for
the meta-propagation path. Include a backward-compatibility test where
`call_orchestrator_forced(..., watcher=None)` swallows exceptions exactly as
today and returns `{"answer": "", "error": ...}`.

### Phase 4 — Eval/seeding propagation + audit fields

Add fields to `QuestionResult`, `RoleResult`, `SeederBatchResult`, and
`EvalResult`. Pipe the meta dict through `_eval_question`, `_aggregate`,
`_eval_single_config`, `evaluate_question_per_role`, `Seeder.run_batch`,
and `_action_seed_batch`.

**Critical files:**
- `scripts/autopilot/eval_tower.py:162-236` (`_eval_question`)
- `scripts/autopilot/eval_tower.py:240-350` (`_aggregate`)
- `scripts/autopilot/safety_gate.py:44-75` (`EvalResult`)
- `scripts/autopilot/species/seeder.py` (`SeederBatchResult`, `run_batch`)
- `scripts/benchmark/seeding_types.py` or current `RoleResult` definition
- `scripts/benchmark/seeding_eval.py` (`_eval_single_config`, metadata aggregation)
- `scripts/autopilot/actions.py:_action_seed_batch` (merge seeding metadata)
- `tests/unit/test_eval_tower.py` (extend)
- `tests/unit/test_seeder_exogenous_metadata.py` (NEW)

**Verification gate:** Test that synthesizes a fake batch where one
question carries `exogenous_recovered=True`; assert
`EvalResult.n_exogenous_recovered=1`, `n_exogenous_unrecovered=0`,
`exogenous_question_ids` correctly populated. Add a seed_batch test where
the seeding pass observes an unrecovered reload but the later
`tower.hybrid_eval()` is clean; assert the final `EvalResult` still carries
the unrecovered exogenous counters.

### Phase 5 — Pre-gate trial classification + DeficiencyCategory

Add the EXOGENOUS_RELOAD + AUTOPILOT_KILLED enum values. Wire the
conditional `bug_corrupted_by` + `bug_corrupted_reason` assignment before
SafetyGate and Pareto side effects.

**Critical files:**
- `scripts/autopilot/experiment_journal.py:19-33` (DeficiencyCategory)
- `scripts/autopilot/autopilot.py:719-879` (classification before gate/archive)
- `scripts/autopilot/actions.py` (wire watcher into ActionContext)
- `tests/unit/test_autopilot_trial_tagging.py` (NEW)

**Verification gate:** Synthesize three trial outcomes (clean, recovered,
unrecovered); assert the JournalEntry's `bug_corrupted_by` /
`bug_corrupted_reason` / `deficiency_category` are correct for each.
For unrecovered exogenous trials, assert all of the following:
`gate.check()` was not called, `consecutive_failures` did not increment,
rollback/blacklist was not triggered, and `archive.update()` was not called.

### Phase 6a — Atomic persistence prerequisite

Convert state and archive persistence to atomic temp+rename. Safe
independent of all the resilience work — this just makes existing writes
crash-safe.

**Critical files:**
- `scripts/autopilot/state_store.py` (atomic `save_state`)
- `scripts/autopilot/pareto_archive.py` (atomic `save`)
- `tests/unit/test_atomic_state_persistence.py` (NEW)

**Verification gate:**
- Existing autopilot tests still pass (atomic writes are transparent to
  consumers).
- New corrupt-state test: write deliberately-truncated JSON to
  `autopilot_state.json`, invoke load_state. Assert all of: exit code
  70, exact stderr format from section 5.6, no journal-file mutations,
  no lock acquisition, no fresh empty state written.
- New crash-during-write test: monkeypatch `os.replace` to raise after
  the temp file is written; assert the original state file is untouched
  and a `.tmp.<pid>` file exists for forensics.

This phase can land independently of 6b — the in_flight_trial logic
isn't needed yet, but the atomic writes are independently safer.

### Phase 6b — In-flight trial marker + crash recovery

Add the `in_flight_trial` marker write/clear + the startup recovery
block. Add the placeholder JournalEntry generation for the
"died-before-record" case. Depends on Phase 6a (atomic writes).

**Critical files:**
- `scripts/autopilot/state_store.py` (in_flight_trial field handling)
- `scripts/autopilot/autopilot.py` (~30 lines: marker write at trial
  start using atomic save, clear at end using atomic save, recovery
  block in cmd_start with `_maybe_reimport_pareto_from_journal`)
- `tests/unit/test_autopilot_recovery.py` (NEW)

**Verification gate:** Simulated tests:
- Set `in_flight_trial = {trial_id: N+1}`, journal max = N, start
  autopilot → assert placeholder JournalEntry created with
  `bug_corrupted_by=autopilot_killed_mid_trial`; assert
  `state.trial_counter = N+1`; assert `in_flight_trial` cleared; assert
  archive.update() was NOT called for the placeholder.
- Set `in_flight_trial = {trial_id: N+1}`, journal max = N+1, start
  autopilot → assert NO placeholder; assert `state.trial_counter = N+2`;
  assert `in_flight_trial` cleared; assert
  `_maybe_reimport_pareto_from_journal` was called (and either re-added
  trial N+1 OR skipped if it was already in archive — both are valid).
- Set `in_flight_trial = {trial_id: N+1}`, journal max = N+1 AND the
  journal entry has `bug_corrupted_by = "exogenous_operator_reload"`,
  start autopilot → assert `_maybe_reimport_pareto_from_journal` SKIPS
  the import (corrupted entries never enter archive on recovery either).
- Set `in_flight_trial = {trial_id: N+1}` AND set a `host_started_at`
  matching a still-alive PID, start autopilot → recovery proceeds
  normally (we can't distinguish "prior instance still alive" from
  "this instance lying"; the lock acquisition in cmd_start protects
  against the live-instance case).

### Phase 7 — Scrub legacy pollution + restart autopilot

After all phases are merged and tests pass:

```bash
# Confirm autopilot is still NOT running
pgrep -af "autopilot.py start"

# Run scrub for known-pollution windows.
# Operator reviews the dry-run output first.
python3 scripts/autopilot/scrub_journal.py \
    --commit-sha pre-resilience-cleanup \
    --reason "pre-resilience cleanup: removing trials corrupted by orchestrator/llama reloads under the old behavior" \
    --since 2026-05-20 --until 2026-05-23T<APPLY_DATE> \
    --dry-run

# Operator decides which trials to actually scrub by tightening
# the --since / --until window. The dry-run reports affected ids.

# Apply once approved:
python3 scripts/autopilot/scrub_journal.py \
    --commit-sha pre-resilience-cleanup \
    --reason "pre-resilience cleanup" \
    --since <chosen_since> --until <chosen_until>

# Verify trustworthiness post-scrub
python3 -c "
import sys; sys.path.insert(0, 'scripts/autopilot')
from experiment_journal import ExperimentJournal
j = ExperimentJournal()
print('post-scrub:', j.trustworthiness_score())
"

# Restart autopilot
cd /mnt/raid0/llm/epyc-orchestrator
python3 scripts/autopilot/autopilot.py start
```

**Verification gate:**
- Trustworthiness score reports the expected new ratio
- First post-restart planner-prompt includes `### Journal Trustworthiness`
  showing the new `corrupted_by` breakdown
- Hypothesis-chain section shows only trusted entries
- No safety-gate `consecutive_failures` fires

---

## 7. Critical files summary

| File | Phase | Lines (approx) | Purpose |
|---|---|---|---|
| `scripts/server/orchestrator_stack.py` | 1 | +40 | Write orchestrator marker before uvicorn and per-llama-port marker (with role list) before each `subprocess.Popen` |
| `src/api/routes/dashboard.py` | 1 | +35 | Read marker on import; new `/llama_fleet_ids` endpoint returning `{port: {started_at, source, roles}}` |
| `scripts/autopilot/orchestrator_watch.py` | 1 | NEW ~125 | Watcher class; role→port lookup via /llama_fleet_ids |
| `scripts/autopilot/resilient_http.py` | 2 | NEW ~100 | Shared `resilient_post` |
| `scripts/benchmark/seeding_orchestrator.py` | 3 | ~20 | Adopt `resilient_post` |
| `scripts/benchmark/seeding_eval.py` | 3+4 | ~30 | Pass role-name (not port — watcher resolves) for the watcher to look up the right marker; propagate role-level retry metadata |
| `scripts/benchmark/feature_validation_live.py` | 3 | ~15 | Adopt `resilient_post` |
| `scripts/benchmark/seeding_injection.py` | 3 | ~15 | Adopt `resilient_post` |
| `scripts/autopilot/eval_tower.py` | 4 | ~30 | `QuestionResult` fields + eval meta propagation |
| `scripts/autopilot/safety_gate.py` | 4 | ~10 | Add `EvalResult` exogenous counters with defaults |
| `scripts/autopilot/species/seeder.py` | 4 | ~35 | Carry seeding-phase exogenous metadata into final trial result |
| `scripts/autopilot/experiment_journal.py` | 5 | ~5 | Two new `DeficiencyCategory` values (note: file recently gained `falsifier`/`rubric_scores` fields per coexistence note; rebase carefully) |
| `scripts/autopilot/autopilot.py` | 5+6b | ~90 | Pre-gate classification, selective recording, self-crash recovery (note: file recently gained CREATIVITY_N et al. constants + `### Exploration mode` template section; rebase carefully) |
| `scripts/autopilot/actions.py` | 4+5 | ~20 | Wire watcher into `ActionContext`; merge seed_batch metadata |
| `scripts/autopilot/state_store.py` | 6a+6b | ~30 | Atomic `save_state` with verbose fatal-on-corrupt loader; `in_flight_trial` field handling |
| `scripts/autopilot/pareto_archive.py` | 6a | ~20 | Atomic archive save |
| New tests across phases | 1-6b | NEW ~600 | Unit + integration |

Total: ~1,100 LoC (~360 production, ~600 tests, ~140 documentation).

---

## 8. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Marker file deleted by `/tmp` cleanup | M | Use `/mnt/raid0/llm/tmp` (RAID0, no system-wide cleanup); document the path; consider `/mnt/raid0/llm/epyc-orchestrator/orchestration/` instead if `/tmp` turns out to be cleaned |
| Workers ALL die simultaneously without marker file update (extreme edge case) | L | Fallback in dashboard.py: when marker is missing or younger than this worker's import time, use module-load timestamp. Per-worker false-positives possible but rare and self-healing |
| External script starts llama-server bypassing `stack_commands` | M | The `source=external` field in the marker handles this — if anything ever writes a marker with `source=external`, the watcher classifies as `external_restart` (real failure path, not auto-recovered). If a future script forgets to write the marker entirely, requests during that startup look like a real crash and journal accordingly — safe fail-closed default |
| `resilient_post` retries hide a real persistent connection failure | L | `max_retries=1` by default; `wait_for_availability` has 120s ceiling; after ~120s the failure flows to real-failure path |
| Safety gate runs before exogenous classification | H | Phase 5 explicitly classifies before `gate.check()`. Test must assert unrecovered exogenous trials do not increment `consecutive_failures` or trigger rollback. |
| Corrupted exogenous trial enters Pareto archive | H | Phase 5 skips `archive.update()` for unrecovered exogenous trials. Test must assert `archive.update()` not called. |
| Seed-batch reward/Q-learning pollution not propagated to trial result | H | Phase 4 propagates metadata through `RoleResult` → `SeederBatchResult` → `_action_seed_batch` → `EvalResult`. Test seed phase dirty/final eval clean. |
| `in_flight_trial` marker corruption or truncated state file | H | Phase 6 first converts state/archive writes to atomic temp-file + `os.replace()` and tests truncated JSON startup behavior. |
| Pareto archive divergence from journal (existing gap, not introduced) | M | New `_maybe_reimport_pareto_from_journal` helper reconciles trusted recorded trials on startup; never imports bug-corrupted placeholder entries. |
| Race between marker file write and worker fork | L | Order of operations: write marker BEFORE Popen. uvicorn workers fork only after Popen returns. Workers' module import runs after fork → reads the freshly-written marker |
| Scrub script accidentally tags too many trials during Phase 7 | L | `--dry-run` mandatory first; operator reviews; `--since`/`--until` bounds; backup files always created |
| Adding new fields to `JournalEntry` breaks `_load_existing` for old JSONL | L | Already proven safe — `bug_corrupted_by`/`_reason` were added previously; `data.get(..., default)` pattern handles missing keys |

---

## 9. Test plan

Test pyramid (build bottom-up):

**Unit tests (Phase 1-6):**
- `test_orchestrator_watcher.py` — mock httpx; verify all classification paths
- `test_resilient_http.py` — mock httpx + watcher; verify retry semantics
- `test_eval_tower.py` (extended) — verify meta propagation
- `test_seeder_exogenous_metadata.py` — verify per-role metadata survives
  seed_batch and reward injection paths
- `test_autopilot_trial_tagging.py` — verify conditional `bug_corrupted_by`
  and, critically, no safety-gate/Pareto side effects for unrecovered
  exogenous trials
- `test_autopilot_recovery.py` — verify `in_flight_trial` recovery sequences
- `test_atomic_state_persistence.py` — verify atomic write behavior and
  invalid JSON startup refusal

**Required code-test commands (run from `/mnt/raid0/llm/epyc-orchestrator`):**

Run the new focused tests first:

```bash
python3 -m pytest -q \
  tests/unit/test_orchestrator_watcher.py \
  tests/unit/test_resilient_http.py \
  tests/unit/test_seeding_orchestrator_resilient.py \
  tests/unit/test_eval_tower.py \
  tests/unit/test_seeder_exogenous_metadata.py \
  tests/unit/test_autopilot_trial_tagging.py \
  tests/unit/test_autopilot_recovery.py \
  tests/unit/test_atomic_state_persistence.py
```

Then run existing regression tests for every touched production surface:

```bash
python3 -m pytest -q \
  tests/unit/test_seeding_orchestrator.py \
  tests/unit/test_seeding_eval.py \
  tests/unit/test_seeding_injection.py \
  tests/unit/test_seeding_injection_additional.py \
  tests/unit/test_seeding_rewards.py \
  tests/unit/test_seeding_types_state.py \
  tests/unit/test_seeding_consumers.py \
  tests/unit/test_seeding_infra.py \
  tests/unit/test_seeding_infra_additional.py \
  tests/unit/test_autopilot_actions.py \
  tests/unit/test_autopilot_state_store.py \
  tests/unit/test_safety_gate_diversity.py \
  tests/unit/test_stack_state.py \
  tests/unit/test_server_lifecycle.py \
  tests/unit/test_build_server_command_helpers.py \
  tests/unit/test_dashboard_helpers.py \
  tests/unit/test_dashboard_route_html.py \
  tests/unit/test_llama_server.py
```

Run a broader smoke pass before any live restart/scrub:

```bash
python3 -m pytest -q tests/unit
```

If the full unit suite is too slow for an intermediate phase, the phase is
not complete until the focused tests plus the existing regression group
above pass. Any skipped test must be recorded in this handoff with the exact
reason and the next command to run.

**Integration tests (after Phase 4):**
- `test_end_to_end_seed_batch_with_reload.py` — Patches httpx-on-orchestrator
  to fail once and `OrchestratorWatcher.current_orchestrator_id` to differ
  before/after. Verifies the seed_batch trial completes with all
  questions present, `n_exogenous_recovered=N`, no `bug_corrupted_by` tag.
- `test_unrecovered_exogenous_does_not_learn.py` — Patches the retry path
  to remain failed after a detected operator reload. Verifies the trial is
  journaled with `bug_corrupted_by`, `consecutive_failures` is unchanged,
  rollback/blacklist is not invoked, and no Pareto entry is added.
- `test_seed_phase_reload_propagates_to_trial.py` — Simulates reload during
  `Seeder.run_batch()` and a clean later `tower.hybrid_eval()`. Verifies the
  final trial still carries seeding-phase exogenous counters and is excluded
  when unrecovered.

Run these integration tests before Phase 7:

```bash
python3 -m pytest -q \
  tests/integration/test_end_to_end_seed_batch_with_reload.py \
  tests/integration/test_unrecovered_exogenous_does_not_learn.py \
  tests/integration/test_seed_phase_reload_propagates_to_trial.py
```

**Manual / live tests (during Phase 7):**
- Start a test trial. While it's mid-flight, run
  `orchestrator_stack reload orchestrator`. Wait. Observe in the
  journal that the trial completed; verify no `bug_corrupted_by` tag;
  verify `eval_details.exogenous_retries` records what happened.
- Repeat with `orchestrator_stack reload frontdoor` (llama-server case).
- Stress test: trigger five reloads back-to-back during a 50-question
  seed_batch. Verify the trial still completes with no tag if all
  recovered, or with tag if at least one stayed unrecovered.

---

## 10. Rollback plan

Each phase is independently revertable:

- Phase 1: remove marker-writing lines (dashboard falls back to
  `time.time()` at import); no behavior change for autopilot.
- Phase 2-3: revert `resilient_post` calls back to direct `httpx.post`.
  `call_orchestrator_forced` still returns the same response shape.
- Phase 4: drop the new fields from `QuestionResult`, `RoleResult`,
  `SeederBatchResult`, and `EvalResult`; they default to safe values so
  removal is fast.
- Phase 5-6: remove the pre-gate classification block and in-flight
  recovery block; trials go back to the old behavior (corrupting the
  journal). Atomic persistence can remain because it is independently safer
  than the old direct-write behavior.

**Hard-rollback option:** at any phase, restore the baseline files
saved in Phase 0:

```bash
cp /tmp/autopilot_state.baseline-*.json orchestration/autopilot_state.json
cp /tmp/autopilot_journal.baseline-*.jsonl orchestration/autopilot_journal.jsonl
cp /tmp/autopilot_journal.baseline-*.tsv orchestration/autopilot_journal.tsv
git revert <hash>...<hash>
```

The journal and state files predate the changes and will resume the
prior behavior.

---

## 11. Open questions (for external review)

1. **Resolved (r2):** Marker file location is `/mnt/raid0/llm/tmp/`
   (matches existing tap-file convention; RAID0 is not subject to
   system tmpfs cleanup).

2. **Scrub window for Phase 7:** how far back to tag? Recommendation:
   tag the window since the last clean restart, plus any windows the
   operator manually identifies as having reloaded mid-trial. Operator
   to specify exact dates at Phase 7 execution time.

3. **Llama-server `source` field handling:** if `source=external`, do we
   suppress journaling (treat as benign) or NOT suppress (treat as real
   for planner reactivity)? Current plan: do NOT suppress — external
   restarts are real signals.

4. **Resolved (r2 — correction after live verification at Phase 1 start):**
   Multi-worker uvicorn marker propagation. Live measurement at Phase 1
   start (2026-05-23) showed that `uvicorn --workers 6` does NOT
   share `_SERVER_STARTED_AT` across workers via fork: consecutive
   `/dashboard/api/version` requests returned **different** timestamps
   (1779561504.5081568 vs 1779561504.5233972, ~15ms apart). This means
   uvicorn forks BEFORE importing the app — each worker imports
   `dashboard.py` independently and gets its own `time.time()`. The
   original audit's caution was correct.

   The fix still works because: each worker reads the marker file at
   module-import time, and as long as the marker is atomically written
   (`os.replace`) before `Popen` is invoked, every worker reads the
   same on-disk content. The previous claim ("workers inherit value
   via fork") was wrong; the actual mechanism is "every worker reads
   the same atomically-written file." Functionally equivalent for the
   plan's purposes, but the explanation matters for future readers.

   No per-worker retry needed inside `dashboard.py` — atomic-write
   semantics guarantee that any worker reading the marker sees either
   the pre-restart content (impossible if `Popen` happens AFTER the
   `os.replace`) or the post-restart content (correct).

5. **Resolved by audit: `AUTOPILOT_KILLED` placeholder JournalEntry must not
   count toward the safety gate's `consecutive_failures`.** It is written as
   `pareto_status="dominated"` with `bug_corrupted_by` set, and the recovery
   path explicitly skips `gate.check()` and `archive.update()`.

6. **`WatcherDisabled` mode** for unit tests / dev environments without
   the fleet markers. Confirmed: the watcher constructor accepts
   `disabled=True` and all methods no-op (returning `None` for ids,
   `True` for wait-for-availability, empty dict for was_restarted_since).
   Call sites pass `OrchestratorWatcher(disabled=os.environ.get(
   "AUTOPILOT_WATCHER_DISABLED", "") == "1")` so unit tests and dev
   stacks without marker files opt out cleanly without branching on
   `watcher is None` everywhere.

7. **Pre-Phase-1 sanity checks** (no semantic decision needed; just
   verify before starting):
   - Confirm `uvicorn --workers 6` master-imports-then-forks behavior
     (item 4 above).
   - Confirm `tower.hybrid_eval()` returns a NEW `EvalResult` (not
     mutating in place). If new, the seed-batch metadata merge in
     5.4 happens in `_action_seed_batch` AFTER the call; if mutated,
     can be done inline. Both work; spec just needs to know which.

---

## 12. Definitions

- **Exogenous failure:** a /chat or /chat/reward POST that failed
  because the orchestrator/llama-server was reloaded (operator
  initiated) and is detected as such by comparing fleet markers.
- **Recovered:** an exogenous failure where the `wait_for_availability` +
  retry succeeded → the question has a real response.
- **Unrecovered:** an exogenous failure where the wait or retry did
  not produce a response (service stayed down past 120s).
- **External restart:** a service restart NOT initiated by
  `stack_commands` (marker `source=external` or marker missing entirely).
- **Real failure:** a failure with no marker change AND the service
  is reachable → genuinely something is wrong with the request.
- **Fleet marker:** small flat file at a well-known path containing a
  single timestamp + source tag, written by the launch script before
  the service process starts. Consumers read it to detect
  identity changes.
- **In-flight trial marker:** a field in `autopilot_state.json` that's
  set immediately before `dispatch_action` runs and cleared only after
  atomic `save_state` completes. Acts as a write-ahead-log marker for
  crash recovery.
- **Learning surfaces:** every mechanism the planner or optimizer learns
  from: SafetyGate counters, rollback/blacklist logic, Pareto archive,
  species effectiveness, hypothesis chains, structured insights, and
  reward/Q-value injection metadata.
- **Trustworthy entry:** a JournalEntry whose `bug_corrupted_by` field
  is empty. The planner's hypothesis-chain reasoning uses only
  trustworthy entries.
- **Trustworthiness score:** ratio of trustworthy entries to total
  entries. Surfaced in the planner prompt's `### Journal
  Trustworthiness` section.

---

## 13. References

- Commit `74c32aa` (epyc-orchestrator) — original journal scrubbing
  infrastructure (`bug_corrupted_by` field, `scrub_journal.py`,
  `trustworthiness_score`).
- `scripts/autopilot/program.md` — operator-editable strategy doc the
  planner reads.
- `src/observability.py:classify_exception` — error code standard.
- `scripts/server/stack_health.wait_for_health` — health polling.
- Memory: `feedback_handoff_driven_tracking` — all multi-phase work
  persisted to a handoff with progress/log updates after every phase.
- Memory: `project_orchestrator_stack_freeze` — orchestrator stack
  registry is FROZEN; this work is additive (marker files +
  endpoint), no registry changes.
