# 2026-10-05 — HS-16 session lifecycle

HS-16 source is accepted against the fifth off-host run: root commit
`565e0195b9cdd61e1dbcb84be50ec1611d1c5bbb` and orchestrator commit
`b61cdc38b2552a9882bba28e2b047edcf91795b6`. The orchestrator’s focused
`tests/unit/test_v1_subagent_link.py` suite passed 53/53 cases, and the OpenCode
plugin Node suite passed 105/105, including final-signal/no-inference, TTL,
stale-node and unknown-session coverage.

At OpenCode 1.18.31, the event hook exposes status, idle and deleted events but
no distinct end event. The plugin sends a bounded minimal final request on
`session.deleted`; ordinary idle is ignored. The API releases only a known,
unexpired session on signal, otherwise expiry follows the declared TTL, and it
records `session_end_source=signal|ttl`.

This records the accepted lifecycle source evidence. Main applies the canonical
HS-16 checkbox and index changes after source promotion. No local tests ran in
this session.
