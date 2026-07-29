# EPYC Project Dashboard Hub

A tiny, dependency-free web server (Python **stdlib only**) owned by the
governance repo (`epyc-root`). It surfaces **project-wide, file/artifact-backed
progress**. Its first view is the **handoff progress board** — a kanban of
`handoffs/{active,blocked,completed,archived}` plus a git-derived
progress-over-time chart.

## The ownership boundary

> **Needs the orchestrator's live in-process state or SSE inference taps →**
> the **orchestrator** serves it (`:8000/dashboard`).
> **Artifact/file-backed & project-wide →** this **hub** serves it (`:8100`).

The autopilot dashboard stays on the orchestrator (it reads live fleet state and
streams running inference — those only exist inside that process). This hub is
where non-autopilot, cross-repo progress views live and grow. The two link to
each other; neither depends on the other's process.

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
| `dashboard/handoff_parser.py` | pure parser: cards, tasks, status-derived Blocked column |
| `dashboard/freshness.py` | mtime → fresh/aging/stale/missing for the timeline artifact |
| `dashboard/static/handoffs.html` | kanban UI + modal + hand-rolled SVG charts (no framework, no CDN) |
| `scripts/handoffs/build_handoff_timeline.py` | git-history → `data/handoff_timeline.json` |
| `scripts/handoffs/install_timeline_hook.sh` | post-commit hook that regenerates the artifact |
| `tests/test_handoff_parser.py`, `tests/test_handoff_timeline.py` | `unittest` suites |

### Endpoints

- `GET /` — the board page
- `GET /health` — `{"status":"ok"}` (stack health probe)
- `GET /api/handoff_board` — compact cards for all four columns (live scan, 30 s cache)
- `GET /api/handoff_detail?id=<state>/<stem>` — full card + scrubbed markdown body (path-traversal guarded)
- `GET /api/handoff_timeline` — the git-derived timeline artifact + freshness
- `GET /api/health` — board (live) + timeline staleness

## Data model

* **State = parent directory** (authoritative). The one exception is the
  **Blocked** column, which is *status-derived*: an `active/` handoff whose
  `Status` begins with `BLOCKED`, plus rows in `blocked/BLOCKED.md`.
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
```

Stdlib `unittest` (pytest also discovers them). The timeline suite builds a
throwaway git repo and asserts the create → flip → move lifecycle, including that
inline `✅` dates override commit dates.
