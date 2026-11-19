#!/bin/bash
set -euo pipefail
# Hook: PreToolUse -> Bash
# REG-ENF-2: refuse an agent-typed INFERENCE LAUNCH (llama-server, llama-bench, llama-cli,
# whisper-cli, ...) that does not ACQUIRE a region claim in the same command.
#
# Mirrors check_destructive_git.sh / check_process_pattern_kill.sh: tool-boundary refusal,
# scanner scoped to invocations not text (shell_scan.lex), exit 2 with a remedy on stderr.
#
# Prose rule it replaces: INVARIANTS.md #5 (claims are ACQUIRED, never observed) and #8
# (compute windows are granted per policy); OPERATING_CONSTRAINTS.md -> Inference and
# Benchmarks. Registry row: docs/reference/governance/rule_registry.json REG-ENF-2.
#
# A claim counts only when it WRAPS the launch:
#   flock [-w N] /mnt/raid0/llm/tmp/cpu_region.<role>.<qN>.lock  <launch...>
#   flock [-w N] /mnt/raid0/llm/tmp/gpu_device.mi210_0.lock -c '<launch...>'
#   bash .../filler_run*.sh ...      (the calendar engine takes its own claim)
# Observing that some lock is held is NOT accepted (invariant 5: TOCTOU, wrong holder).
# --help / --version / --list-devices are not launches. A launch hidden in a script file is
# out of scope (the hook sees command text only); that path is the engine's own claim.
#
# POSTURE
#   * Launch detected, no wrapping claim  -> FAIL CLOSED (exit 2). That is the rule.
#   * Scanner unavailable or errored      -> FAIL CLOSED only for the unambiguous form
#     (a launch binary at a command position with no region lock path anywhere in the
#     text); everything else passes. Same posture as the pkill guard.
#   * jq missing / unparsable hook input  -> FAIL OPEN (cannot read the call at all).
#   * Override: EPYC_ALLOW_UNCLAIMED_INFERENCE=1 in the HOOK environment (operator-set,
#     not settable from the command text) -> allow.
# Tests: scripts/hooks/tests/test_inference_region_claim.py

INPUT=$(cat)
[[ "${EPYC_ALLOW_UNCLAIMED_INFERENCE:-0}" == "1" ]] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
case "$TOOL" in Bash|"") ;; *) exit 0 ;; esac
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -z "$CMD" ]] && exit 0

SCAN="$(dirname "${BASH_SOURCE[0]}")/inference_claim_scan.py"
BIN_RE='(^|[;&|(]|[[:space:]]|/)(llama-(server|bench|cli|perplexity|batched-bench|speculative|mtmd-cli|sweep-bench)|whisper-(cli|server|bench))([[:space:]]|$)'
LOCK_RE='(cpu_region\.[^[:space:]]+\.lock|gpu_device\.[^[:space:]]+\.lock|gpu_quiet\.lock|filler_run[0-9]*\.sh)'

refuse() {
  echo "BLOCKED: inference launch without a region claim ($1)." >&2
  echo "Every inference launch must ACQUIRE its region (INVARIANTS.md #5, #8). Wrap it:" >&2
  echo "  flock -w 600 /mnt/raid0/llm/tmp/cpu_region.GLOBAL.q0.lock taskset -c 0-23 <launch>" >&2
  echo "  flock -w 600 /mnt/raid0/llm/tmp/gpu_device.mi210_0.lock -c '<launch>'" >&2
  echo "or run it through the calendar engine (filler_run*.sh) under a grant." >&2
  echo "Operator override: EPYC_ALLOW_UNCLAIMED_INFERENCE=1 in the session environment." >&2
  exit 2
}

fallback() {
  if [[ "$CMD" =~ $BIN_RE ]] && ! [[ "$CMD" =~ $LOCK_RE ]]; then
    refuse "scanner unavailable; unambiguous form"
  fi
  exit 0
}

if ! command -v python3 >/dev/null 2>&1 || [[ ! -f "$SCAN" ]]; then fallback; fi
VERDICT=$(printf '%s' "$CMD" | python3 -I "$SCAN" 2>/dev/null) || fallback

case "$VERDICT" in
  unclaimed-launch) refuse "no flock on cpu_region/gpu_device lock wraps the launch" ;;
  claimed-launch|clean) exit 0 ;;
  *) fallback ;;
esac
