# Devcontainer Autopilot Restart Handoff — 2026-07-09

> **Archived 2026-07-14** (backlog ROI audit, [backlog-roi-audit-2026-07-14.md](../active/backlog-roi-audit-2026-07-14.md)): superseded by the healthy 2026-07-14 restart; unresolved Jul-8 silent-death root-cause folded into active/autopilot-continuous-optimization.md (AP-RC-1).

## Context
Autopilot died at trial 1302, ~21:33 UTC Jul 8, with no crash/shutdown message in the log. Process vanished — no lock file, no PID. This handoff was generated from a host-side session that cannot access the devcontainer filesystem.

## What Was Investigated (Host Side)
- **Broken `.venv` on host**: The `.venv/bin/python` symlink points to `/home/node/.local/share/uv/python/...` which only exists inside the devcontainer. This is expected — autopilot runs inside container, not on host.
- **Log tail analysis**: Trial 1301 completed normally (q=1.909, dominated). Planner was invoked for trial 1302 with `local_ingest` (spend breaker active, projected $542/mo > $250 threshold). Then silence — last log line is `Planner spend breaker active` at 21:33:11 UTC.
- **Repeated prior failures Jul 7-8**: The process experienced multiple cycles of `orchestrator_stack.py reload` failures and "4 consecutive non-executing actions" auto-pauses before being manually restarted. By 21:00 it was running normally again.

## Unknowns (To Investigate Inside Container)
- Did the planner call hang and timeout, causing the process to die without logging?
- Was the process externally killed (OOM, operator, devcontainer stop/restart)?
- Check `dmesg` inside container for OOM kills
- Check if there's a newer log file or journal entries after 21:33
- Verify orchestrator health before restarting

## Restart Instructions
1. Verify `.venv/bin/python` resolves: `ls -la /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python && /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python --version`
2. Verify orchestrator health: `curl -s http://localhost:8072/health` (or whatever port)
3. Clear stale lock if present: `rm -f /mnt/raid0/llm/epyc-orchestrator/.autopilot.lock`
4. Restart: `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python scripts/autopilot/autopilot.py start --max-trials 3000`
5. Verify PID is running: `ps aux | grep autopilot | grep -v grep`
6. Monitor log tail: `tail -f /mnt/raid0/llm/epyc-orchestrator/logs/autopilot.log`

## Prior Config
- `AUTOPILOT_PLANNER_PRIMARY=local_ingest`
- `AUTOPILOT_PLANNER_CRITIC=local_frontdoor`
- `stack_mode=both`
- `AUTOPILOT_TOOL_SENTINELS=1`
- `AUTOPILOT_PLANNER_TIMEOUT=600`

## State at Death
- `trial_counter: 1302`
- `paused: False`
- `halt_reason: None`
- `in_flight: null`
- `consecutive_failures: 2`
