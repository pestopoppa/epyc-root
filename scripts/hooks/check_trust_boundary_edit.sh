#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Write | Edit
#
# Rider R7 (handoffs/active/session-bus-thin-dispatcher.md §Rider) — authority
# containment for the trust boundary.
#
# TWO LAYERS, deliberately different in strictness:
#
#   Layer 1 (unconditional) — refuse Write/Edit to the gate list itself,
#   coordination/session-bus/human_only_paths.yaml, and to its .sha256 pin. The
#   gate list defines what needs an operator signature, so an agent able to edit
#   it could widen its own authority. This layer needs no parsing and therefore
#   never degrades.
#
#   Layer 2 (best-effort) — refuse Write/Edit to the paths the gate list names
#   (MEASUREMENT.md, instrument_eras.yaml, …). This needs the list parsed. If it
#   cannot be parsed the hook ALLOWS and warns, because failing closed on an
#   unreadable config would block every edit in the repo — a far worse outcome
#   than a missed guard that `session_bus.py validate` and the coordinator-daemon
#   audit will still catch after the fact.
#
# WHY THIS DOES NOT BLOCK THE OPERATOR: the ratify scripts amend MEASUREMENT.md
# and friends through bash/python, not the Write/Edit tools, so the human path is
# untouched. An agent that finds itself needing one of these edits should raise a
# token-request rather than reach for the override.
#
# Override: EPYC_ALLOW_TRUST_BOUNDARY_EDIT=1 (deliberate, operator-scoped).
# TESTS: scripts/hooks/tests/test_trust_boundary_edit.py

INPUT=$(cat)

[[ "${EPYC_ALLOW_TRUST_BOUNDARY_EDIT:-0}" == "1" ]] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')
case "$TOOL" in Write|Edit) ;; *) exit 0 ;; esac

FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')
[[ -z "$FILE" ]] && exit 0

REPO_ROOT="${CLAUDE_PROJECT_DIR:-/workspace}"
GATE_LIST="coordination/session-bus/human_only_paths.yaml"
GATE_PIN="coordination/session-bus/human_only_paths.sha256"

TARGET=$(realpath -m "$FILE" 2>/dev/null || printf '%s' "$FILE")

# ---- layer 1: the gate list and its pin -------------------------------------

for protected in "$GATE_LIST" "$GATE_PIN"; do
  abs=$(realpath -m "${REPO_ROOT}/${protected}" 2>/dev/null || printf '%s' "${REPO_ROOT}/${protected}")
  if [[ "$TARGET" == "$abs" ]]; then
    cat >&2 <<EOF
BLOCKED: $protected is human-amendment-only.

This file defines which paths require an operator signature. An agent able to
edit it could widen its own authority, so it is off-limits to Write/Edit by
construction — not as a policy you can argue with, as a containment boundary.

If the trust boundary genuinely needs to change, raise a token-request and let
the operator amend the file and rewrite the pin together.
EOF
    exit 2
  fi
done

# ---- layer 2: the paths the gate list names ---------------------------------

globs=""
if [[ -r "${REPO_ROOT}/${GATE_LIST}" ]]; then
  # Targeted parse of a format we own: `glob: "..."` under paths:.
  globs=$(grep -oE '^[[:space:]]*glob:[[:space:]]*"[^"]+"' "${REPO_ROOT}/${GATE_LIST}" 2>/dev/null \
          | sed -E 's/.*"([^"]+)".*/\1/' || true)
fi

if [[ -z "$globs" ]]; then
  printf 'WARNING: trust-boundary guard could not read %s — layer 2 skipped. `session_bus.py validate` still checks the pin.\n' \
    "$GATE_LIST" >&2
  exit 0
fi

# Repo roots the globs are relative to. Branch-scoped rules are not path
# matchable and are deliberately not enforced here.
declare -a ROOTS=("$REPO_ROOT" "/mnt/raid0/llm/epyc-orchestrator" "/mnt/raid0/llm/epyc-inference-research")

while IFS= read -r glob; do
  [[ -z "$glob" ]] && continue
  for root in "${ROOTS[@]}"; do
    candidate=$(realpath -m "${root}/${glob}" 2>/dev/null || printf '%s' "${root}/${glob}")
    # The RHS is deliberately UNQUOTED so bash treats it as a glob pattern.
    # Quoting it forces a literal string comparison, which silently disables
    # every wildcard entry in the gate list: `measurement/protocols/*.md` then
    # compares against the literal path `.../protocols/*.md`, which no real file
    # ever equals. That left Annex B, Q and G — which MEASUREMENT.md:17-19 says
    # carry the SAME trust boundary as the constitution — agent-writable, with
    # the guard reporting success. Do not re-add the quotes; run
    # test_check_trust_boundary_edit.sh after touching this comparison.
    if [[ "$TARGET" == $candidate ]]; then
      cat >&2 <<EOF
BLOCKED: $FILE is on the human-only write list.

Reason recorded in $GATE_LIST. Writes here need a granted operator token, not an
agent edit — this is one of the enumerated trust boundaries (era registry rows,
MEASUREMENT.md, AutoPilot baseline applies, production freezes, host reboots).

Raise a token-request with a pre-validated command and let the operator apply it.
The ratify-script path (bash/python) is how these edits are meant to land.
EOF
      exit 2
    fi
  done
done <<< "$globs"

exit 0
