# 2026-07-05 — Project Dashboard Hub (handoff progress + backlog + kernel-R&D Phase 3)

**Session type:** feature build (operator-directed), with two adversarial-review passes.

## Context / problem

Operator wanted a visual way to track long-horizon agent progress without asking for specifics — a graphical view of handoff work over time (add/complete/archive, task-level granularity). Follow-on asks in-session: (a) surface the **outstanding backlog** ("how far from completing everything outstanding"), and (b) build the **kernel-R&D loop Phase 3 dashboard** specced in `mi210-kernel-rnd-loop-proposal.md` as a new hub page, with the loop itself owned by `epyc-inference-research`.

## Key architecture decision

epyc-root now owns a **project dashboard hub** — a dependency-free stdlib web server (no FastAPI; runs under any `python3`) on **port 8100**, run as a managed service via `orchestrator_stack.py`. Boundary: *needs live orchestrator in-process state / SSE → orchestrator serves it (:8000); artifact/file-backed & project-wide → epyc-root hub (:8100)*. The hub is **multi-page** (handoffs + kernel-R&D, more to come). The autopilot dashboard is untouched except a reciprocal nav link.

## What was built

**Handoff kanban board** (`/`): four columns (Active/Blocked/Completed/Archived) from `handoffs/` state = parent dir; compact cards (title, priority, `done/total` bar) → click for a modal with the full checklist + rendered markdown. Blocked column is **status-derived** (`Status: BLOCKED` + `BLOCKED.md` rows). Board is a live per-request scan.

**Progress-over-time** (git-history generator): `build_handoff_timeline.py` reconstructs the timeline from `git log -M -p` over `handoffs/`. **Historical seeding**: prefers in-file self-reported dates (inline `✅ YYYY-MM-DD`, `**Created**`, `**Updated**`) over commit dates, so the charts go back to true origin (**2026-01-05**) instead of bunching at the 2026-02-25 monorepo-split import. Refresh via an epyc-root `post-commit` hook. Artifact `data/handoff_timeline.json` is git-ignored (derived).

**Outstanding-backlog view**: board payload now carries a `backlog` snapshot — **132 handoffs outstanding · 488 open tasks · 53.9% of all tracked tasks done · 61 without a checklist**. Timeline gained an **opened-vs-completed-per-week flow** chart.

**Kernel-R&D Phase 3 page** (`/kernel`): renders the MI210 kernel-R&D loop's results with the **OBSERVATION discipline** front and centre (never decision-gating; operator-only authorizes prod push), Pareto **correct-only**, best-per-model, run log with MemUnitStalled/Busy mechanism deltas, freshness badge, graceful empty-state. Ownership split honoured: the loop (`epyc-inference-research/scripts/kernel_rnd/`) owns a new `kernel_store.py export` JSON contract (wired into `kernel_sweep.sh`); the hub only reads it. Seeded with the real `prefetch-validate` Phase-0 row (Δ+2.11%, MemUnitStalled −55%, byte-identical) so it previews now.

## Changes (file / repo)

| Repo | File | Change |
|------|------|--------|
| epyc-root | `dashboard/handoff_parser.py` | backlog snapshot; priority/metadata/date/sort fixes (review) |
| epyc-root | `dashboard/server.py` | `/kernel` + `/api/kernel`; null-byte + non-dict guards (review) |
| epyc-root | `dashboard/static/handoffs.html` | backlog banner + opened/completed chart; md-render + XSS fixes (review) |
| epyc-root | `dashboard/static/kernel.html` | **new** — kernel-R&D page |
| epyc-root | `scripts/handoffs/build_handoff_timeline.py` | in-file-date seeding; opened-task flow; full-path keying; delete-interval; `seen_opened` migration (review) |
| epyc-root | `tests/test_handoff_{parser,timeline}.py` | 32 stdlib-unittest tests incl. all review regressions |
| epyc-orchestrator | `scripts/server/orchestrator_stack.py`, `stack_commands.py` | `start_handoff_dashboard()` managed service + start/reload wiring *(committed by operator)* |
| epyc-orchestrator | `src/api/routes/dashboard.html` | reciprocal "handoffs ↗" nav link *(committed by operator)* |
| epyc-inference-research | `scripts/kernel_rnd/kernel_store.py` | `export` subcommand → JSON dashboard contract; `_connect` relative-path fix (review) |
| epyc-inference-research | `scripts/kernel_rnd/kernel_sweep.sh` | export hook after ingest |
| epyc-inference-research | `scripts/kernel_rnd/samples/prefetch-validate.jsonl` | **new** — real Phase-0 validation row (preview seed) |

## Results

- **32 unit tests pass** (23 parser + 9 timeline).
- Two adversarial-review workflows (18 + 9 agents): **12 + 3 confirmed defects, all fixed and re-verified** (priority mis-parse, dropped YAML/bulleted metadata, date-synonyms, broken descending sort, timeline basename-collision, delete-erasure, md inline-code corruption, double-escaped links, null-byte 500, non-dict 500; then `seen_opened` migration, kernel-page `num()` XSS, `_connect` relative-path crash).
- All endpoints 200 (`/`, `/kernel`, `/api/handoff_board`, `/api/kernel`, `/api/health`). Operator reloaded the stack mid-session and it came up as the managed service on :8100 — **integration confirmed working**.

## Deferred / next

- **Managed service runs pre-phase-2 code** — operator runs `orchestrator_stack.py reload handoff_dashboard` to pick up the backlog + kernel page (my reload wiring handles it).
- **Kernel Pareto frontier** is empty until the loop runs a real sweep with absolute throughput (the seed row records Δ%/mechanism only — Phase-0 didn't record absolute t/s, not fabricated).
- Honest caveat: timeline "opened" total (3842) exceeds "completed" (1875) because completed/archived handoffs contain many checkboxes never individually ticked — the **exact** current backlog (488 open tasks) is the reliable headline; the per-week flow is a rough intake view.
- Wiki `total_new=39` (unrelated accumulated research-intake sources) not compiled here — separate research-wiki pass.

## Follow-up session (same day, evening) — "53.9% stuck all day" diagnosis + checkbox discipline + today-activity signal

**Problem**: operator reported the backlog % frozen at 53.9% all day despite heavy work across 5+ agent sessions — second "board feels stale" report against a board that was again NOT stale.

**Root cause (verified, not assumed)**: `/api/handoff_board` was live (`generated_at` current, 30s TTL). The % (`pct_all_done` = 1557/2888) counts **checkbox state only**. Diffing checkbox lines in `handoffs/` between the morning commit (`516c9776`) and HEAD: **1557 done / 2906 total at both ends — zero flips, zero adds** — while 90+ handoff commits landed. All sessions recorded progress as narrative prose ("Record X checkpoint", status paragraphs), which the metric cannot see. Aggravating: 2888-task denominator → one flip ≈ 0.035pp, below the 0.1 display rounding.

**Fixes (epyc-root `ea561387`)**:

| Change | File(s) |
|--------|---------|
| Checklist-sync gate in wrap-up Step 2: flip `[x]` + inline `✅ date`, add checkboxes for mid-flight tasks, verify staged flip count via `git diff HEAD -- handoffs/ \| grep -cE '^\+\s*[-*] \[[xX]\]'` before commit | `.claude/commands/wrap-up.md` |
| Same gate mirrored into Codex's skill (workflow step 3 + bundled reference) | `~/.codex/skills/wrap-up/SKILL.md`, `references/wrap-up-command.md` (outside repo) |
| Always-loaded checkbox-discipline rule — binds **autonomous checkpoint commits**, which are forbidden from running /wrap-up and were the actual authors of today's prose-only updates | `CLAUDE.md` (Handoff Workflow) |
| `activity_today` in board payload: commits / handoffs touched / boxes checked / boxes added since local midnight (`git log --since=midnight -p -- handoffs/`, best-effort zeros on git failure, cached with 30s board TTL) | `dashboard/server.py` |
| Backlog banner renders the activity line; when commits>0 and boxes_checked==0 it states "prose-only updates; no checkboxes flipped, so the % above cannot move" | `dashboard/static/handoffs.html` |
| Unit tests for the diff parser (flip/add counting, prose-only day, live-shape smoke) | `tests/test_dashboard_activity.py` |

**Validation**: full dashboard suite 54/54 pass; service reloaded via `orchestrator_stack.py reload handoff_dashboard`; live payload cross-checked against raw git — exact match (94 commits, 28 handoffs touched, 6 boxes checked, 8 added since midnight).

**Caveat**: `boxes_checked` counts *added* `[x]` lines, so moved/compacted already-checked lines count too — it is an activity signal, not a ledger; the parser's live scan stays authoritative.

**Deferred (recorded as checkboxes in `loops-and-dashboards-audit-2026-07-05.md` P5)**: priority-bucketed backlog, probably-dead lane (>30/90d untouched), promoting `pct_open_done` to the headline.

---

## Session: handoff dashboard down — restart (evening)

**Problem**: operator reported the handoff dashboard (:8100) no longer serving. `curl localhost:8100` → connection refused; `logs/dashboard_hub.log` had been truncated to 0 bytes ~20 min prior, so nothing was listening and no crash trace survived. No supervisor auto-restarts it.

**Fix**: restarted through the stack manager (the dashboard is a first-class `handoff_dashboard` service per `feedback_stack_managed_services`, launched by `start_handoff_dashboard()` in `epyc-orchestrator/scripts/server/orchestrator_stack.py:1825`). Correct invocation is `reload`, not `start --only` (avoids stack-state clobber):

```
python3 scripts/server/orchestrator_stack.py reload handoff_dashboard
```

An initial ad-hoc `nohup python3 -m dashboard.server` start was used to restore service immediately, then killed and replaced with the stack-managed launch so the process is tracked (writes `logs/handoff_dashboard.log`, health-gated on `/health`).

**Result**: PID 2917777, `status` reports `handoff_dashboard 8100 healthy`. `/` → 200, `/api/health` board=fresh (live-scan), timeline+kernel fresh.

**Deferred**: no watchdog exists for this hub — the same silent death can recur. Adding a supervised restart (or verifying the stack's health loop covers it) is open follow-up.
