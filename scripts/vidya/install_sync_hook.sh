#!/bin/bash
# Idempotently add the vidya-sync block to the shared post-commit and post-merge hooks.
# Usage: bash scripts/vidya/install_sync_hook.sh [GIT_DIR_HOOKS_PATH]   (default: git rev-parse --git-path hooks)
# The block resolves the PRIMARY worktree at run time (hooks are shared by all worktrees) and
# is a no-op until scripts/vidya/hook_sync.sh exists there.
set -euo pipefail
hooks="${1:-$(git rev-parse --git-path hooks)}"
BEGIN="# >>> vidya-sync hook >>>"
END="# <<< vidya-sync hook <<<"
for ev in post-commit post-merge; do
  f="$hooks/$ev"
  [ -f "$f" ] || { printf '#!/bin/sh\n' > "$f"; chmod +x "$f"; }
  grep -qF "$BEGIN" "$f" && continue
  block="$BEGIN
_p=\"\$(git worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p' | head -1)\"
[ -n \"\$_p\" ] && [ -f \"\$_p/scripts/vidya/hook_sync.sh\" ] && ( cd \"\$_p\" && bash scripts/vidya/hook_sync.sh $ev ) >/dev/null 2>&1 || true
$END"
  # insert after the shebang so a trailing `exit`/lfs line cannot skip it
  { head -1 "$f"; printf '%s\n' "$block"; tail -n +2 "$f"; } > "$f.tmp.$$" && chmod --reference="$f" "$f.tmp.$$" && mv "$f.tmp.$$" "$f"
  echo "installed vidya-sync block in $f"
done
