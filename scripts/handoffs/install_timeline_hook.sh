#!/bin/bash
# Install (idempotently) a git post-commit hook that regenerates the handoff
# dashboard timeline artifact whenever a commit touches handoffs/.
#
# The hook is detached and best-effort: it never blocks or fails a commit. The
# generator is pure-stdlib, so it runs under the base python3. Safe to re-run.
set -euo pipefail

REPO="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
HOOK_DIR="$(git -C "$REPO" rev-parse --git-path hooks)"
# rev-parse --git-path may return a path relative to the repo root.
case "$HOOK_DIR" in
  /*) : ;;
  *)  HOOK_DIR="$REPO/$HOOK_DIR" ;;
esac
HOOK="$HOOK_DIR/post-commit"
MARKER="# >>> handoff-timeline hook >>>"
END_MARKER="# <<< handoff-timeline hook <<<"

read -r -d '' BLOCK <<'EOF' || true
# >>> handoff-timeline hook >>>
# Regenerate the dashboard timeline artifact when handoffs/ changes (detached).
if git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | grep -q '^handoffs/'; then
  _repo="$(git rev-parse --show-toplevel 2>/dev/null)" || _repo=""
  if [ -n "$_repo" ] && [ -f "$_repo/scripts/handoffs/build_handoff_timeline.py" ]; then
    ( python3 "$_repo/scripts/handoffs/build_handoff_timeline.py" >/dev/null 2>&1 & ) || true
  fi
fi
# <<< handoff-timeline hook <<<
EOF

mkdir -p "$HOOK_DIR"

if [ -f "$HOOK" ] && grep -qF "$MARKER" "$HOOK"; then
  echo "[install-hook] already installed in $HOOK"
  exit 0
fi

if [ ! -f "$HOOK" ]; then
  printf '#!/bin/sh\n\n%s\n' "$BLOCK" > "$HOOK"
  echo "[install-hook] created $HOOK"
else
  # Insert our block right after the shebang so it runs even if a chained hook
  # (e.g. git-lfs) exits non-zero before the end of the file.
  tmp="$HOOK.handoff.$$"
  {
    head -n 1 "$HOOK"
    printf '\n%s\n' "$BLOCK"
    tail -n +2 "$HOOK"
  } > "$tmp"
  mv "$tmp" "$HOOK"
  echo "[install-hook] inserted handoff-timeline block into existing $HOOK (after shebang)"
fi
chmod +x "$HOOK"

echo "[install-hook] running an initial build…"
python3 "$REPO/scripts/handoffs/build_handoff_timeline.py" --print || true
echo "[install-hook] done. To remove: delete the block between:"
echo "    $MARKER"
echo "    $END_MARKER"
