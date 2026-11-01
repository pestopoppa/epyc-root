# scripts/coordination/churn — the backlog-churn pipeline's installed set

Git is the source; `/mnt/raid0/llm/tmp/compute-flags/` (`F`) holds installed copies plus state. `churn_up.sh` installs,
cleans reboot residue, starts what is down, and `--status` proves installed sha == git sha for every file. Runbook:
`docs/guides/agent-workflows/backlog-churn-flow.md` → *Reboot / cold start*.

| installed at (`F/…`) | git source | runs as |
|---|---|---|
| `ws58-calendar-keeper-v10.sh` (+ `ws58-calendar-keeper.current`) | `../rowflow/ws58-calendar-keeper-v10.sh` | started by the watchdog; pid in `ws58-calendar-keeper.pid` |
| `ws58-keeper-watchdog.sh` | `ws58-keeper-watchdog.sh` | loop; `ws58-keeper-watchdog.pid` (written by churn_up) |
| `ws58-backlog-gen-v1.sh` → `bin/backlog_gen.py` | `ws58-backlog-gen-v1.sh`, `../backlog_gen.py` | loop (10 min); `ws58-backlog-gen.pid` |
| `ws58-flow-scoreboard-v1.sh` → `bin/flow_scoreboard.py` | `ws58-flow-scoreboard-v1.sh`, `../flow_scoreboard.py` | loop (10 min); `ws58-flow-scoreboard.pid` |
| `bin/handoff_sessions.py dispatch --loop` | `../handoff_sessions.py` | loop (60 s); `handoff-sessions.dispatcher.pid` |
| `ws58-disk-trend.sh` | `ws58-disk-trend.sh` | loop (10 min) → `disk-trend.tsv`; `ws58-disk-trend.pid` |
| (runs from the repo) `scripts/coordination/filing_watch.sh` + `filing_takeover_alarm.py` | `../filing_watch.sh`, `../filing_takeover_alarm.py` | loop (60 s); `ws58-filing-watch.pid` |
| `grant-ws58-quarters-<day>.sh` | template `grant-ws58-quarters-20261101.sh` (today's file is derived by sed: keeper step 3 / churn_up) | one per day, `.pid` |
| `grant-gpu-<MMDD>-v<n>.sh` | template `grant-gpu-1101-v20.sh` (successor derived by sed) | one live at a time, `.pid` |
| `grant_ok.sh`, `grant_ok_v4.sh`, `bin/rowflow/grant_ok_v4.sh` | `../rowflow/grant_ok_v4.sh` | called by the writers |
| `grant_ok_launcher.py` (legacy, imports `validate_fillers.py`; the GPU writer's `claim_regex` imports it from `F`) | `legacy/grant_ok_launcher.py`, `../validate_fillers.py` | library |
| `bin/rowflow/*` | `../rowflow/*` | keeper step 5, engine, publish |
| `ram_admit.sh` | `ram_admit.sh` | called by grant_ok |
| `GOAL-codex-gen.md` | `GOAL-codex-gen.md` | read by the codex-gen session |

Both `grant_ok_launcher.py` copies must accept every flag `filler_run15.sh` accepts:
`scripts/coordination/tests/test_grant_ok_launcher_flags.py` (origin: 2026-11-01 21:11Z, `--qual-interpreter` unknown to the
gate → every GPU grant skipped as "launcher dead/reused/unrecognised").
