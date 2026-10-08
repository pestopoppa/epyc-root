# D9 acknowledgement: RTG48 historical-cadence comments

Context: two checked-in comments describe C49 restart attempts as recurring every ten seconds. The reviewed original evidence supports two cited reports 42 seconds apart within a 74-second window. A ten-second heartbeat age does not establish recurrence cadence. The proposed patch corrects the supervisor comment and test docstrings/comments. It changes no executable shell line, Python AST body, assertion, timing, or configuration.

Exact proposal: [lossless two-file patch payload](proposed-patch.json), SHA-256 `9c191746a397e3bd2bbbc47f37adf6cd661390836fce56ff6847527bd86e345f`, against ROOT `11f38bd0`. Files: `scripts/coordination/bus_supervisor.sh` and `scripts/coordination/tests/test_bus_supervisor.py`. MAIN independently compared preimages/postimages and executable structure. It is applied only in our isolated ownership worktree, remains unpublished, and will be rechecked before integration.

| Option | Effect | Tradeoff |
|---|---|---|
| A — acknowledge this exact proposal (recommended) | Publish both factual comment corrections. | A protected-path merge; executable behavior and runtime remain unchanged. |
| B — retain current comments | Keep the audit findings published without changing protected source comments. | Leaves an unsupported historical cadence description in source; its correction remains open. |

Recommendation: A. D9 in `handoffs/active/loop-owned-fleet-implementation.md:39` explicitly says “merging any change under scripts/coordination/** requires operator ack.” The acknowledgement covers only this exact patch, not runtime activation, reloads, tests, other protected proposals, policy amendment, or inference. MAIN caught this gate before any commit or push; the previous private application is preserved as proposed work rather than presented as operator approval.

The JSON payload preserves every original patch byte, including diff context-line spaces. Decode `payload_b64` and verify the declared SHA-256 before applying; the immutable plain patch remains retained in MAIN private custody.
