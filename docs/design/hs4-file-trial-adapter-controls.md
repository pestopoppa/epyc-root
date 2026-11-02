# HS-4 shared file-task adapter controls

`hs4_file_trials.py` prepares fresh public task workspaces. `hs4_file_adapters.py`
contains an in-memory `/chat` request/response control and an offline OpenCode
session parser. These controls launch nothing. They do not implement the P0.4
live shell runner, enforce grader secrecy, produce trial verdicts, or write an
SC86 measurement. OpenCode tool parts and full exported sessions/events are
retained; incomplete step usage stays null, and complete cost still requires
session-wide tap parity. `/chat` returns tool timing metadata but does not
promise complete tool arguments and outputs; that field remains unknown.

`hs4_file_transport.py` prepares the corresponding HTTP and OpenCode subprocess
paths, but **always refuses before I/O** because no accepted live isolation
verifier has been wired. Its mock controls exercise request/response and process
identity capture only. On timeout it freezes and records the direct child and
observed descendants by PID and birth time, sends TERM then KILL to those exact
identities, and reports survivors. A captured-child test passed, but ancestry
does not find descendants that escaped before capture; before enabling live
trials the owner must prove containment and complete descendant drainage.

The existing P0.4 scorer is the fixture-specific `check_fixture` running
`test_calc.sh` after a code edit, not a final-answer scorer for the three new
file-task families. A nearby APP scorer at orchestrator `868275acb64ef3d490ecac6952518ae187fe74d3`,
`scripts/benchmark/debug_scorer.py:score_answer` (Git blob
`269a8669d5f261b7355e8bb11774a1410d0efbca`) has an `exact_match` mode, but
extracts tagged/boxed answers or the last line, normalizes case and punctuation,
accepts numeric tolerance/word forms, and has quote/colon fallbacks. It is not
an appropriate whole-answer scorer for file lookup, inventory aggregation and
reconciliation without an additional format gate.
On 2026-11-02, a direct no-inference invocation of that exact Git blob returned
`True` for both `alpha.csv` and `other.csv\nalpha.csv` against `alpha.csv`, and
for `other: 2` against `2`. Thus its normal extraction does not enforce an exact
whole-answer contract; using it without a separately declared answer format
would accept additional wrong lines. A `2, 3` self-match passed, but does not
establish order, completeness or independent correctness of structured results.

`hs4_file_scoring.py` supplies a narrow precondition: require one compact,
canonical JSON object in the declared lookup, inventory or reconciliation schema,
then call the unchanged native scorer with `exact_match` and `normalize=False`.
`score_pinned` loads only regular non-symlink source bytes with SHA-256
`01cf5a675a1f107120ae6b69c1b9f9ee22783052d15239925d86d0d013755fce`;
the digest does not attest the interpreter or its imports.
An actual invocation of APP blob `269a8669d5f261b7355e8bb11774a1410d0efbca`
passed positive, wrong-answer and extra-line controls for each of the three
families. This establishes those controls, not full evaluator validation.
`hs4_file_suite.py` prepares six development and twelve acceptance synthetic
inputs with separate host-only oracle files. `seal_suite` binds their bytes,
prompts, oracle digests and scorer pin, sets trees read-only and returns a seal
digest that must be held independently and supplied to `verify_seal` before
each use. `chmod` is reversible by the owner: this is tamper-evident custody
and accidental-write protection, not immutable storage or an isolation proof.
The acceptance split must be protected from the agent and tuning before use.
No model or live trial was run.

The APP request schema at that source uses `/chat` with `prompt`, `force_mode`,
`force_role`, `allow_delegation`, `session_id` and `task_root`; `task_root` is
restricted below the llm root or `/tmp` and scopes file tools, not the server's
OS identity or hidden grader access. Default `edit_mode=none` prohibits writes;
the three planned tasks are read-only. A distinct `session_id` avoids explicit
cross-request REPL-global restoration but does not itself prove memory or
escalation are disabled: those conditions still need deployment-bound proof.

Before real execution, integrate the existing P0.4 OpenCode config/version and
SC86 capture, qualify the `/chat` transport and complete session evidence,
predeclare and validate the task-specific scorer controls, and prove a real
OS-level agent/grader boundary with the owner of scoring 2a-iv. Mock transports,
separate directories and task_root alone are not that proof. Coordinate the
inference window and resource claim with its owner before any live run.
