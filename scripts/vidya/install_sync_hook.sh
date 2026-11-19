#!/bin/bash
# Idempotently add the vidya-sync block to the shared Git hooks.
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

# A push updates origin/main only after post-commit has already fired. Git's
# reference-transaction hook observes that published remote-tracking update.
# Buffer and restore stdin for any pre-existing reference-transaction hook.
f="$hooks/reference-transaction"
[ -f "$f" ] || { printf '#!/bin/sh\n' > "$f"; chmod +x "$f"; }
if ! grep -qF "$BEGIN" "$f"; then
  block='$BEGIN_PLACEHOLDER
if _vidya_input="$(mktemp "${TMPDIR:-/tmp}/vidya-ref-hook.XXXXXXXX")"; then
 if cat > "$_vidya_input"; then
  if [ "${1:-}" = committed ] && awk '\''$3 == "refs/remotes/origin/main" && $2 !~ /^0+$/ {found=1} END {exit !found}'\'' "$_vidya_input"; then
    _vidya_primary="$(git worktree list --porcelain 2>/dev/null | sed -n '\''s/^worktree //p'\'' | head -1)"
    if [ -n "$_vidya_primary" ] && [ -f "$_vidya_primary/scripts/vidya/hook_sync.sh" ]; then
      ( cd "$_vidya_primary" && env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE bash scripts/vidya/hook_sync.sh reference-transaction ) >/dev/null 2>&1 || true
    fi
  fi
   exec < "$_vidya_input"
 fi
 rm -f "$_vidya_input"
fi
$END_PLACEHOLDER'
  block="${block/\$BEGIN_PLACEHOLDER/$BEGIN}"
  block="${block/\$END_PLACEHOLDER/$END}"
  { head -1 "$f"; printf '%s\n' "$block"; tail -n +2 "$f"; } > "$f.tmp.$$" && chmod --reference="$f" "$f.tmp.$$" && mv "$f.tmp.$$" "$f"
  echo "installed vidya-sync block in $f"
fi
