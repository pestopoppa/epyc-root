# scripts/coordination/churn — the backlog-churn pipeline's installed set

Git is the source; `/mnt/raid0/llm/tmp/compute-flags/` (`F`) holds installed copies plus state. `churn_up.sh` installs,
cleans reboot residue, starts what is down, and `--status` proves installed sha == git sha for every file. Runbook:
`docs/guides/agent-workflows/backlog-churn-runbook.md`.

| installed at (`F/…`) | git source | runs as |
|---|---|---|
| `ws58-calendar-keeper-v13.sh` (+ `ws58-calendar-keeper.current`) | `../rowflow/ws58-calendar-keeper-v13.sh` | started by the watchdog; pid in `ws58-calendar-keeper.pid`; runs `rowflow.py allocate` each tick (wakes within 5 s on a grants/ or ready/ change, 120 s fallback) |
| `ws58-keeper-watchdog.sh` | `ws58-keeper-watchdog.sh` | loop; `ws58-keeper-watchdog.pid` (written by churn_up) |
| `ws58-backlog-gen-v1.sh` → `bin/backlog_gen.py` | `ws58-backlog-gen-v1.sh`, `../backlog_gen.py` | loop (10 min); `ws58-backlog-gen.pid` |
| `ws58-flow-scoreboard-v1.sh` → `bin/flow_scoreboard.py` | `ws58-flow-scoreboard-v1.sh`, `../flow_scoreboard.py` | loop (10 min); `ws58-flow-scoreboard.pid` |
| `bin/handoff_sessions.py dispatch --loop` | `../handoff_sessions.py` | loop (60 s); `handoff-sessions.dispatcher.pid` |
| `ws58-disk-trend.sh` | `ws58-disk-trend.sh` | loop (10 min) → `disk-trend.tsv`; `ws58-disk-trend.pid` |
| (runs from the repo) `scripts/coordination/filing_watch.sh` + `filing_takeover_alarm.py` | `../filing_watch.sh`, `../filing_takeover_alarm.py` | loop (60 s); `ws58-filing-watch.pid` |
| `bin/rowflow/*` | `../rowflow/*` | keeper v11 (`allocate`), engine, publish |
| `GOAL-codex-gen.md` | `GOAL-codex-gen.md` | read by the codex-gen session |

The single `grant_ok_launcher.py` copy is `scripts/coordination/rowflow/grant_ok_launcher.py`. It must accept every flag
`filler_run15.sh` accepts: `scripts/coordination/tests/test_grant_ok_launcher_flags.py` (origin: 2026-11-01 21:11Z,
`--qual-interpreter` unknown to the gate → every GPU grant skipped as "launcher dead/reused/unrecognised").
