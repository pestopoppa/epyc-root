# 2026-10-05 — HS-OD-6 tools with the REPL disabled

HS-OD-6 source commit `3b84e6eb23682a5889868a4212404641d0833ea1` is included in
the published orchestrator main package at `41ab07fcdaf9920d0d51520586fddae460cb50b4`
and passed the sixth off-host validation run. The three original golden
requests that combine `x_disable_repl=true` with tools are retained and now
assert the declared HTTP 422 JSON response with zero model calls. The unrelated
golden requests remain unchanged, and the route-level refusal cases pass.

The aggregate run also had three unrelated runtime-flags expiry failures owned
by a separate repair. They do not overlap the HS-OD-6 route, golden cases, or
tool-mode contract. No local tests ran in this session. Main owns the canonical
checkbox and index.
