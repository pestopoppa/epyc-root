#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Bash
# Refuses an UNBOUNDED `llama-cli` invocation. llama-cli does not exit when its
# generation finishes: it re-enters the prompt loop, and with stdin closed or
# redirected it spins printing "> " forever.
#
# Origin: 2026-09-01, self-inflicted. A one-shot "Paris" sanity check ran for
# 11h15m, wrote 322 GB (array 480 G → 191 G free, silently undoing an approved
# reclaim), and held a CPU region lock (q0-q3) the entire time. `-no-cnv` does
# not prevent it and `< /dev/null` makes it faster. The footgun was already
# documented on 2026-08-28 and hit anyway — enforcement belongs here, not in a
# memory. Root cause and the binary-level fix: llama-cli-eof-fix-20260901
# (read_input() discards console::readline()'s EOF signal); it cannot be applied
# to the FROZEN production kernel, so unpatched binaries persist on this host.
#
# SCOPED TO INVOCATIONS, NOT TEXT. The scanner strips quoted strings and
# heredocs, so this file, the progress record, a bus message about the incident,
# `ls build/bin/llama-cli` and `grep llama-cli` all pass.
#
# The compliant idiom is `timeout <secs> llama-cli ...` and it is NOT blocked —
# a guard that forbade its own remedy would be the C21 failure again.

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[[ -z "$CMD" ]] && exit 0
[[ "$CMD" != *llama-cli* ]] && exit 0

SCAN="$(dirname "${BASH_SOURCE[0]}")/llama_cli_guard_scan.py"

# Fail OPEN if the scanner is missing: this guard prevents a self-inflicted
# resource burn, not a correctness or safety violation, and blocking every
# command that merely mentions llama-cli would be worse than the bug.
if ! command -v python3 >/dev/null 2>&1 || [[ ! -f "$SCAN" ]]; then
  exit 0
fi

VERDICT=$(printf '%s' "$CMD" | python3 "$SCAN" 2>/dev/null) || exit 0

if [[ "$VERDICT" == "unbounded-invocation" ]]; then
  echo "BLOCKED: unbounded llama-cli invocation." >&2
  echo "" >&2
  echo "llama-cli does NOT exit when generation finishes — it re-enters its prompt loop," >&2
  echo "and with stdin closed or redirected every read returns instantly, so it spins" >&2
  echo "writing \"> \" at full speed. '-no-cnv' does not stop it; '< /dev/null' speeds it up." >&2
  echo "On 2026-09-01 one such process ran 11h15m, wrote 322 GB, and held a CPU region lock." >&2
  echo "" >&2
  echo "Use instead:  timeout <secs> llama-cli ..." >&2
  echo "Better:       llama-bench (for numbers) or llama-server + a client (for generation)." >&2
  echo "Deliberate long run: prefix EPYC_LLAMA_CLI_ACK=\"why\" and kill+verify it yourself." >&2
  exit 2
fi

exit 0
