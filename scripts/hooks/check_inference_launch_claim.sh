#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Bash   (REG-ENF-2)
# Denies an inference launch (llama-server/-bench/-cli/..., whisper-*) that holds no live
# region claim. Posture and the definition of "claim" are in inference_launch_claim_scan.py:
#   non-launch command -> fail-open; launch + no claim -> deny;
#   launch + unreadable claim state -> fail-closed; scanner crash -> deny only if a coarse
#   regex still sees an inference binary at a command position.
# Override (operator only): EPYC_ALLOW_UNCLAIMED_LAUNCH=1.

[[ "${EPYC_ALLOW_UNCLAIMED_LAUNCH:-0}" == "1" ]] && exit 0
INPUT=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -z "$CMD" ]] && exit 0

SCAN="$(dirname "${BASH_SOURCE[0]}")/inference_launch_claim_scan.py"
COARSE='(^|[;&|]|[[:space:]])(llama-(server|bench|cli|completion|speculative|batched-bench|perplexity)|whisper-(cli|server))([[:space:]]|$)'

VERDICT=SCANNER-FAILED
if command -v python3 >/dev/null 2>&1 && [[ -f "$SCAN" ]]; then
  VERDICT=$(printf '%s' "$CMD" | python3 "$SCAN" 2>/dev/null) || VERDICT=SCANNER-FAILED
fi

case "$VERDICT" in
  clean|wrapped|launch:covered) exit 0 ;;
  launch:uncovered|launch:unreadable)
    echo "BLOCKED: inference launch with no live region claim ($VERDICT)." >&2
    echo "Take the claim by wrapping the launch: epyc-orchestrator/scripts/region-lock run --regions <qN> -- <cmd>" >&2
    if [[ "$VERDICT" == "launch:unreadable" ]]; then
      echo "The claim registry (cpu_region.occupancy.json) is unreadable; failing closed." >&2
    fi
    echo "Shared host: an unclaimed launch corrupts other sessions' measurements. Origin: REG-ENF-2." >&2
    exit 2 ;;
  *)
    if printf '%s' "$CMD" | grep -E "$COARSE" >/dev/null; then
      echo "BLOCKED: the launch scanner failed and this command looks like an inference launch. Failing closed." >&2
      exit 2
    fi
    exit 0 ;;
esac
