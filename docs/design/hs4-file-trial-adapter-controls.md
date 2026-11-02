# HS-4 shared file-task adapter controls

`hs4_file_trials.py` prepares fresh public task workspaces. `hs4_file_adapters.py`
contains an in-memory `/chat` request/response control and an offline OpenCode
session parser. These controls launch nothing. They do not implement the P0.4
live shell runner, enforce grader secrecy, produce trial verdicts, or write an
SC86 measurement. OpenCode tool parts and full exported sessions/events are
retained; incomplete step usage stays null, and complete cost still requires
session-wide tap parity. `/chat` returns tool timing metadata but does not
promise complete tool arguments and outputs; that field remains unknown.

The existing P0.4 scorer is the fixture-specific `check_fixture` running
`test_calc.sh` after a code edit, not a final-answer scorer for the three new
file-task families. A nearby APP scorer at orchestrator `868275acb64ef3d490ecac6952518ae187fe74d3`,
`scripts/benchmark/debug_scorer.py:score_answer` (Git blob
`269a8669d5f261b7355e8bb11774a1410d0efbca`) has an `exact_match` mode, but
extracts tagged/boxed answers or the last line, normalizes case and punctuation,
accepts numeric tolerance/word forms, and has quote/colon fallbacks. It is not
yet demonstrated to implement the intended whole-answer semantics for file
lookup, inventory aggregation and reconciliation; no scorer is selected here.

Before real execution, integrate the existing P0.4 OpenCode config/version and
SC86 capture, implement a `/chat` transport and complete session evidence,
predeclare and validate the task-specific unchanged scorer, and prove a real
OS-level agent/grader boundary with the owner of scoring 2a-iv. Mock transports,
separate directories and task_root alone are not that proof. Coordinate the
inference window and resource claim with its owner before any live run.
