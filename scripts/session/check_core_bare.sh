#!/bin/bash
set -euo pipefail
# Zero-token check: core.bare=true in a clone that has a working tree is the signature of the
# 2026-11-06 `git worktree repair` incident (breaks git status + serialized_push).
# Raises/clears a per-repo alarm through scripts/coordination/alarm_channel.py (emit-on-change).
# Usage: check_core_bare.sh [repo...]   (default: the three shared clones)
# Env: ALARM_CHANNEL_CMD overrides the alarm command (tests). Exit 1 if any clone is bad.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ALARM="${ALARM_CHANNEL_CMD:-python3 $ROOT/scripts/coordination/alarm_channel.py}"
REPOS=("$@")
[[ ${#REPOS[@]} -eq 0 ]] && REPOS=(/workspace /mnt/raid0/llm/epyc-inference-research /mnt/raid0/llm/epyc-orchestrator)
rc=0
for r in "${REPOS[@]}"; do
  [[ -e "$r/.git" ]] || continue
  name=$(basename "$r")
  bare=$(git -C "$r" config --get core.bare 2>/dev/null || echo "")
  # a working tree exists if the checkout has a .git entry and is not a *.git bare dir
  if [[ "$bare" == "true" && ( -f "$r/.git" || -d "$r/.git" ) ]]; then
    echo "ALARM: core.bare=true in $r (has working tree)"; rc=1
    $ALARM raise --severity critical --key "core-bare-$name" \
      --message "core.bare=true in $r while it has a working tree (git worktree repair?). Fix: git -C $r config core.bare false" \
      --evidence "{\"repo\":\"$r\"}" >/dev/null 2>&1 || echo "WARN: alarm delivery failed" >&2
  else
    $ALARM clear --key "core-bare-$name" >/dev/null 2>&1 || true
  fi
done
exit $rc
