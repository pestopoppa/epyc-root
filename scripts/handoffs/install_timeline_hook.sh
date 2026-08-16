#!/bin/bash
# Install (idempotently) git hooks that regenerate only the handoff dashboard
# timeline artifact whenever handoffs/ changes — on local commits AND on pulled/
# merged/checked-out commits.  Wrap-up-owned index state is deliberately excluded.
#
# Three hooks are wired, each with a change-guard appropriate to its arguments:
#   post-commit    — the just-made commit touched handoffs/ (git diff-tree HEAD)
#   post-merge     — a merge/pull changed handoffs/ (git diff HEAD@{1} HEAD)
#   post-checkout  — a branch switch changed handoffs/ (git diff $1 $2, flag $3=1)
#
# Every block is detached and best-effort: it never blocks or fails the git op.
# The generator is pure-stdlib, so it runs under the base python3. Safe to re-run.
#
# NOTE: .git/hooks is NOT version-controlled. Fresh clones must run this script
# (wire it into clone-repos.sh / session init) or the dashboard timeline will only
# refresh on the next local handoffs commit.
set -euo pipefail

REPO="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
HOOK_DIR="$(git -C "$REPO" rev-parse --git-path hooks)"
# rev-parse --git-path may return a path relative to the repo root.
case "$HOOK_DIR" in
  /*) : ;;
  *)  HOOK_DIR="$REPO/$HOOK_DIR" ;;
esac
MARKER="# >>> handoff-timeline hook >>>"
END_MARKER="# <<< handoff-timeline hook <<<"

# The detached regen body, shared by all three hooks. Kept identical so the block
# is easy to find/remove; only the enclosing change-guard differs per hook.
regen_body() {
  cat <<'EOF'
  _repo="$(git rev-parse --show-toplevel 2>/dev/null)" || _repo=""
  if [ -n "$_repo" ] && [ -f "$_repo/scripts/handoffs/build_handoff_timeline.py" ]; then
    ( python3 "$_repo/scripts/handoffs/build_handoff_timeline.py" >/dev/null 2>&1 & ) || true
  fi
EOF
}

# Emit the full marked block for a given hook kind on stdout.
block_for() {
  case "$1" in
    post-commit)
      printf '%s\n' "$MARKER"
      printf '%s\n' "# Regenerate the dashboard timeline artifact when this commit changed handoffs/ (detached)."
      printf '%s\n' "if git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | grep -q '^handoffs/'; then"
      regen_body
      printf '%s\n' "fi"
      printf '%s\n' "$END_MARKER"
      ;;
    post-merge)
      printf '%s\n' "$MARKER"
      printf '%s\n' "# Regenerate when a merge/pull changed handoffs/ (detached)."
      printf '%s\n' "if git diff --name-only 'HEAD@{1}' HEAD 2>/dev/null | grep -q '^handoffs/'; then"
      regen_body
      printf '%s\n' "fi"
      printf '%s\n' "$END_MARKER"
      ;;
    post-checkout)
      printf '%s\n' "$MARKER"
      printf '%s\n' "# Regenerate on a branch checkout (flag \$3=1) that changed handoffs/ (detached)."
      printf '%s\n' 'if [ "${3:-0}" = "1" ] && git diff --name-only "$1" "$2" 2>/dev/null | grep -q '"'"'^handoffs/'"'"'; then'
      regen_body
      printf '%s\n' "fi"
      printf '%s\n' "$END_MARKER"
      ;;
  esac
}

install_into() {
  kind="$1"
  hook="$HOOK_DIR/$kind"
  if [ -f "$hook" ] && grep -qF "$MARKER" "$hook"; then
    # This is an upgrade path, not an "already installed" no-op.  The marked
    # body is version-controlled by this installer; replacing it removes stale
    # worker-triggered actions (notably the former index_state.py regeneration)
    # while preserving unrelated chained hooks such as git-lfs.
    marker_count="$(awk -v marker="$MARKER" '$0 == marker { count++ } END { print count + 0 }' "$hook")"
    end_marker_count="$(awk -v marker="$END_MARKER" '$0 == marker { count++ } END { print count + 0 }' "$hook")"
    if [ "$marker_count" -ne 1 ] || [ "$end_marker_count" -ne 1 ]; then
      echo "[install-hook] refusing malformed marked block in $hook" >&2
      return 1
    fi
    start_line="$(awk -v marker="$MARKER" '$0 == marker { print NR }' "$hook")"
    end_line="$(awk -v marker="$END_MARKER" '$0 == marker { print NR }' "$hook")"
    if [ "$start_line" -ge "$end_line" ]; then
      echo "[install-hook] refusing inverted marked block in $hook" >&2
      return 1
    fi
    tmp="$hook.handoff.$$"
    {
      head -n "$((start_line - 1))" "$hook"
      block_for "$kind"
      tail -n "+$((end_line + 1))" "$hook"
    } > "$tmp"
    mv "$tmp" "$hook"
    chmod +x "$hook"
    echo "[install-hook] upgraded handoff-timeline block in $hook"
    return 0
  fi
  if [ ! -f "$hook" ]; then
    { printf '#!/bin/sh\n\n'; block_for "$kind"; } > "$hook"
    echo "[install-hook] created $hook"
  else
    # Insert our block right after the shebang so it runs even if a chained hook
    # (e.g. git-lfs) exits non-zero before the end of the file.
    tmp="$hook.handoff.$$"
    { head -n 1 "$hook"; printf '\n'; block_for "$kind"; tail -n +2 "$hook"; } > "$tmp"
    mv "$tmp" "$hook"
    echo "[install-hook] inserted handoff-timeline block into existing $hook (after shebang)"
  fi
  chmod +x "$hook"
}

mkdir -p "$HOOK_DIR"
for kind in post-commit post-merge post-checkout; do
  install_into "$kind"
done

echo "[install-hook] running an initial build…"
python3 "$REPO/scripts/handoffs/build_handoff_timeline.py" --print >/dev/null || true
echo "[install-hook] done. To remove, delete the block between these markers in each hook:"
echo "    $MARKER"
echo "    $END_MARKER"
