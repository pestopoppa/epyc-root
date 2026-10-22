# 2026-10-22 HS-PROF-1 Claude-as-judge backend

- Operator correction: NOT the Anthropic API; judge = claude_cli cloud judge (subscription), `--judge-backend cloud --cloud-judge sonnet-low`.
- epyc-inference-research branch `hsprof1-claude-judge` @ 02084e30c: `judge_beam_run.py --judge-backend cloud --cloud-judge --workers` reuses orchestrator `cloud_judges.py` (claude_cli); envelope usage/cost/model recorded; one-call preflight, rc 5 BLOCKED if claude missing/unauthenticated; no API key anywhere.
- `run_hs_prof1_beam_arm.sh PHASE=judge JUDGE_BACKEND=cloud`: no port/pid proof, smoke-5 first.
- Filler job `s5-hsprof1-beam_job.sh`: phase 2 is a cloud-judge call, no GPU; `HSPROF1_PHASES=reader` runs reader-only.
- Tests: 24 passed (file-scoped). Not merged; main reviews.
