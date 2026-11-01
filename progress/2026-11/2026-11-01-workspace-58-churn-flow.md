# 2026-11-01 — ws58: backlog churn flow installed (operator: "churn through the backlog should just work")

- Canonical flow: `docs/guides/agent-workflows/backlog-churn-flow.md`; wired into `inference-backlog-scheduling`, `coordinator-agent` (+ compute-owner-takeover.md), `compute-fillers.md`.
- Generator `scripts/coordination/backlog_gen.py` (+ `tests/coordination/test_backlog_gen.py`, 3 tests) → `compute-flags/BACKLOG-{ni,refactor,codex3}.md` every 10 min via `compute-flags/ws58-backlog-gen-v1.sh` (pid 2599082, 13:15:50Z). Replaces the one-shot `ws58-blocked-inference-feeder.sh` (no process was running).
- Metrics `scripts/coordination/flow_scoreboard.py` → `compute-flags/FLOW-SCOREBOARD.md` via `ws58-flow-scoreboard-v1.sh` (pid 2599083). `ws58-code-scoreboard.sh` pid 319739 stopped at its `sleep 3600` boundary (verified with ps); 50-tick quota retired. Science scoreboard v4 (pid 1366332) untouched.
- `compute-flags/GOAL-<worker>.md` (38 lines each) replace `OWNER-ORDER-20261029.md`, `LOOP-CONTRACT.md`, `CODEX-GOAL-20261028.md` (moved to `compute-flags/retired/` with a header). Codex `/goal` objectives replaced per pane.
- sha256: ws58-backlog-gen-v1.sh b79a8fcc…, ws58-flow-scoreboard-v1.sh 1ab7cb0c…, bin/backlog_gen.py c3b98e23…, bin/flow_scoreboard.py 6d082c65…, GOAL-ni b81ed61e…, GOAL-refactor 194ee841…, GOAL-codex3 4ffa0638…, retired ws58-code-scoreboard.sh 09dc0e75….
