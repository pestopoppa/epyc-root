# 2026-11-01 — research intake: dsh-superagent-prototype (intake-2603)

- Source: https://github.com/deepseek-ai/dsh-superagent-prototype @ 6337fc8. Not a duplicate; it is a companion of intake-1186 (deepseek-harness).
- Stages 1-2: 1 entry, 1 dive (PARTIAL read from disk, 8 claim anchors), 1 Stage-2 wave, 0 Stage-2b waves. No expansion entries:
  the cited article "Exploring Super-agent Design" could not be located, so it is declined and recorded in dive_corrections. No compute was used.
- Verdict for the backlog churn pipeline: adopt_patterns, not adopt_component. The dive found a lost run-end event:
  `handoff_sessions.py:711` clears pending_event at every turn end, and `backlog_gen.py:220` counts `.ended` as done.
- Stage 3: tasks DSH-1..4 are prepared for `handoffs/active/session-bus-thin-dispatcher.md` (RTG-34) and AWAIT operator approval.
  No handoff was edited. Plan and exact task lines: `research/deep-dives/intake-2603-dsh-superagent-prototype.md`.
- Wiki: section added to `wiki/agent-architecture.md`; manifest touched for the dive and digest. [no-belief: intake record; no measurement]
