# Unadmitted direct focused-test run — excluded from acceptance

This note records the actual tool output and its evidence limits. It is not a run receipt and does not reconstruct runtime facts that were not captured.

- Command: `.venv/bin/python -m pytest tests/unit/test_step_events.py tests/integration/test_execute_turn.py -q`
- Working directory: `/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator`
- Observed output: `42 passed in 4.22s` (pytest summary also reported 42 collected).
- UTC invocation timestamp: not captured in the tool output available to this session.
- Output log/artifact: not captured; this is a record from the live tool response only.
- PID, process birth, affinity, grant admission, RSS sampling and drain receipt: not captured.
- Relationship to the R6 window: the final R6 admission refusal was timestamped `2026-11-01T05:51:14.284173Z`; the local test invocation's precise timestamp was not captured. Main has excluded this direct run from acceptance because it was not launched through the admitted R6 process/resource guard.
- Code closure at invocation: not captured. A later source comment clarified that `output_sha256` hashes `_text_of(payload)`'s UTF-8 projection; no behavior changed. Current file hashes are recorded separately in `finalwrap-draft.md` and must not be attributed to this test invocation.
- Result disposition: correctness signal only; excluded from acceptance, not an R6 result, not a native/model outcome, and not grounds to tick the ROOT handoff.
