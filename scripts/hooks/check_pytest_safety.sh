#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Bash
# Blocks pytest -n auto or -n N where N > 16 (192-thread machine safety)
#
# C21 (2026-07-29): the match is SCOPED to the pytest invocation. It used to be
# `pytest.*-n\s*[0-9]+` against the whole command string, where `.*` crosses shell
# separators and quotes, so it fired on:
#   * an unrelated flag in a later pipeline stage — a pytest run piped into a
#     `sed` line-range was blocked as if the line range were a worker count;
#   * the mere mention of the pattern inside a quoted argument — it blocked the bus
#     message REPORTING this bug, because the payload quoted the example.
# A guard that fires on its own bug report is the guard-must-not-forbid-its-own-idiom
# shape: it was matching text, not invocations.
#
# The safety property is unchanged and deliberately generous: any segment whose
# UNQUOTED text contains the word `pytest` is scanned, so `xargs pytest -n 64` and
# `timeout 900 python -m pytest -n 32` are still caught. Only the SCOPE narrowed —
# a separator ends a segment, and quoted text is data rather than a command.

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [[ -z "$CMD" ]]; then
  exit 0
fi

# Fail CLOSED if the precise checker cannot run: fall back to the original broad
# match rather than letting an unchecked command through. A false block costs a
# rephrase; a missed `-n auto` costs the machine.
if ! command -v python3 >/dev/null 2>&1; then
  if echo "$CMD" | grep -qP 'pytest.*-n\s*(auto|[0-9]+)'; then
    echo "BLOCKED: python3 is unavailable for precise pytest-worker checking and this command" >&2
    echo "matches the broad pattern. Refusing rather than guessing. Use -n 8 (default)." >&2
    exit 2
  fi
  exit 0
fi

VERDICT=$(printf '%s' "$CMD" | python3 "$(dirname "${BASH_SOURCE[0]}")/pytest_worker_scan.py" 2>/dev/null) \
  || VERDICT="SCANNER-FAILED"

case "$VERDICT" in
  auto)
    echo "BLOCKED: pytest -n auto would spawn ~192 workers and crash this machine. Use -n 8 (default) or -n 4." >&2
    exit 2
    ;;
  SCANNER-FAILED)
    # Same fail-closed posture as a missing python3.
    if echo "$CMD" | grep -qP 'pytest.*-n\s*(auto|[0-9]+)'; then
      echo "BLOCKED: the pytest-worker scanner failed and this command matches the broad" >&2
      echo "pattern. Refusing rather than guessing. Use -n 8 (default)." >&2
      exit 2
    fi
    ;;
  "")
    ;;
  *)
    echo "BLOCKED: pytest -n $VERDICT is too many workers for this 192-thread machine. Use -n 8 (default)." >&2
    exit 2
    ;;
esac

exit 0
