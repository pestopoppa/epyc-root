# 2026-10-05 — NI06 / HS-17 MCP progress and timeout contract

NI06 / HS-17 is accepted against off-host run `37284177689`. The orchestrator
source is published in main package `41ab07fcdaf9920d0d51520586fddae460cb50b4`
(source commit `d5310c291f9a106761f15a81f32a877f8c38910a`). The OpenCode
plugin source `ad7cc5c9d8220730b7967d06aea94aed2ea3be4b` is integrated as root
commit `3e57ed6c`; main has not published that root boundary yet.

Validation passed 48 MCP fixtures: 11 undeclared-tool cases, 16 server cases,
and 21 chat cases. The pinned OpenCode Node suite passed 105 tests, including
two timeout-lint cases. Coverage exercises asynchronous chat, cancellation,
monotone progress, and a 90-second virtual MCP call; the template enforces a
125000 ms minimum timeout. No actual inference was run.

This records source and off-host fixture evidence only. Main applies the HS-17
canonical checkbox and index changes. No local tests ran in this session.
