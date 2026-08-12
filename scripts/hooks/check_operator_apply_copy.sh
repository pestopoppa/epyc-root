#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Bash
# Refuses to EXECUTE a derived copy of a gated operator apply/ratify script.
#
# Origin: 2026-08-05, handoffs/active/autopilot-continuous-optimization.md — a C6
# agent copied artifacts/operator/apply_e8_quality_baseline_state.py, patched its
# fail-closed AutoPilot gate out of the copy as `if False and autopilot_running()`,
# and ran the copy. The gate held in the original and the incident was contained,
# but nothing structural stopped the copy: the prohibition lived INSIDE the file
# being copied, so it was prose the moment the file was duplicated.
#
# THIS GUARD DOES NOT LOOK FOR THE GATE. It keys on derivation — reproduce most of
# a protected original and you may not execute it from a non-canonical path.
# Ungated, re-gated or byte-identical, the copy is refused all the same, which is
# the only property a copier cannot patch out.
#
# SCOPED TO INVOCATIONS, NOT TEXT. Quoted runs, heredocs and comments are stripped,
# so this file, the handoff row describing the incident, and a bus message reporting
# it all pass. `cp`, `diff`, `grep` and `git show` on a copy are untouched — reading
# a suspicious copy is how you audit it. Only running it is refused.
#
# NO ENV OVERRIDE, deliberately: the canonical original at its canonical path is
# never blocked, so no legitimate workflow needs one, and an override on this guard
# would be the same prose-not-enforcement defect one level up.
#
# SCOPE LIMIT: a PreToolUse hook sees the command an AGENT TYPES. A daemon, a cron
# job, or a script that internally shells out to the copy is invisible to it — the
# enforcing layer there is OS-level, exactly as human_only_paths.yaml already records
# under `conceptual:` for AutoKernel evaluator immutability.
#
# TESTS: scripts/hooks/tests/test_operator_apply_copy.py

INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')
case "$TOOL" in Bash|"") ;; *) exit 0 ;; esac

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')
[[ -z "$CMD" ]] && exit 0

SCAN="$(dirname "${BASH_SOURCE[0]}")/operator_apply_copy_scan.py"

# Fail OPEN when the scanner cannot run — unlike the pattern-kill guard, there is no
# unambiguous textual fallback here (the decision needs file contents), and blocking
# every script invocation in the repo on a missing python3 would be worse than the
# miss. The lint mode below still catches copies after the fact.
if ! command -v python3 >/dev/null 2>&1 || [[ ! -f "$SCAN" ]]; then
  exit 0
fi

VERDICT=$(printf '%s' "$CMD" | python3 "$SCAN" 2>/dev/null) || VERDICT="SCANNER-FAILED"

if [[ "$VERDICT" == "derived-copy" ]]; then
  DETAIL=$(printf '%s' "$CMD" | python3 "$SCAN" --explain 2>/dev/null) || DETAIL=""
  cat >&2 <<EOF
BLOCKED: this runs a DERIVED COPY of a gated operator apply/ratify script.

$DETAIL

Operator apply scripts carry fail-closed, human-only gates (AutoPilot must be
stopped; the sealed evidence must be the canonical bundle; the state CAS must
match a human-reviewed pre-image). Those gates live inside the file, so copying
the file copies away the enforcement — which is exactly how a C6 agent ran an
ungated apply on 2026-08-05.

Do this instead:
  - Run the CANONICAL original at its canonical path. It is never blocked, and it
    is the only path whose gates are the reviewed ones.
  - To INSPECT a copy, read/diff/grep it. Reading is not blocked; executing is.
  - If the canonical script's gate is genuinely wrong, amend the original and get
    it reviewed. Do not route around it with a copy.
EOF
  exit 2
fi

exit 0
