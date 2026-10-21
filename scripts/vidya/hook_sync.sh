#!/bin/bash
# OPTIONAL, non-blocking safety net (rarely fires: most commits land on lane branches and are
# pushed HEAD:main; `cli.py sync` itself reads fetched origin/main, so it is cwd-independent): after a commit/merge ON MAIN that touched research/intake_index.yaml,
# fold the index into the canonical vidya ledger. Never blocks or fails a git operation.
# Usage (from a git hook):  hook_sync.sh <post-commit|post-merge>
# Detached by design; output goes to <state>/sync-hook.log. Idempotent: `cli.py sync` skips
# an already-folded index and takes the host-wide ledger write lock.
set -u
event="${1:-post-commit}"
top="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" || exit 0
[ "$branch" = "main" ] || exit 0
if [ "$event" = "post-merge" ]; then
  changed="$(git diff --name-only 'HEAD@{1}' HEAD 2>/dev/null)"
else
  changed="$(git diff-tree --root --no-commit-id --name-only -r HEAD 2>/dev/null)"
fi
printf '%s\n' "$changed" | grep -qx 'research/intake_index.yaml' || exit 0
cli="$top/scripts/vidya/cli.py"
[ -f "$cli" ] || exit 0
state="${VIDYA_STATE_DIR:-/mnt/raid0/llm/state/vidya}"
mkdir -p "$state" 2>/dev/null || exit 0
( nohup python3 "$cli" sync --quiet >>"$state/sync-hook.log" 2>&1 </dev/null & ) >/dev/null 2>&1 || true
exit 0
