# OBS-12a session-bus interpreter call sites

Updated the remaining active explicit `python3` invocations of
`session_bus.py` to execute the script directly in `coordination/session-bus/BUS_PROTOCOL.md`,
`coordination/session-bus/tasks/STANDING-MAIN-RULES.md`, and the live
`scripts/coordination/idle_supervisor.sh` nudge. The five substitutions preserve
all command arguments. The executable is mode 100755 and its shebang points at
the orchestrator venv Python; that interpreter owns the declared PyYAML
dependency needed by roster validation. Dated task and ratification examples
remain historical.

Manual caller review confirmed CLAUDE.md and AGENTS.md already invoke the
executable path directly. `gitnexus impact cmd_drain` reports LOW risk and no
indexed dependants; the human-authored CLI invocations were reviewed directly.
`git diff --check` passed. No tests, daemon restart, runtime bus command, or
host check ran for this reversible documentation/nudge correction.
