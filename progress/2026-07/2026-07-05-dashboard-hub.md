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
