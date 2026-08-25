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
#
# CANONICAL-CHECKOUT RESOLUTION (RTG-46, 2026-08-24): regenerate in the PRIMARY
# worktree, not the checkout where the hook fired. Lane-worktree commits and the
# detached promotion merge share this repo's hooks but write their own checkout's
# `data/handoff_timeline.json` (untracked+gitignored), so the real-repo artifact
# went stale (observed: last regen 2026-08-23 15:26 despite handoff commits
# 2026-08-24 06:48/10:34). The primary is the FIRST entry of `git worktree list
# --porcelain`; regenerating there keeps the artifact the :8100 hub reads fresh.
regen_body() {
  cat <<'EOF'
  _repo="$(git rev-parse --show-toplevel 2>/dev/null)" || _repo=""
  if [ -n "$_repo" ]; then
    _primary="$(git worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p' | head -1)"
    if [ -n "$_primary" ] && [ -f "$_primary/scripts/handoffs/build_handoff_timeline.py" ]; then
      _repo="$_primary"
    fi
  fi
  if [ -n "$_repo" ] && [ -f "$_repo/scripts/handoffs/build_handoff_timeline.py" ]; then
    ( python3 "$_repo/scripts/handoffs/build_handoff_timeline.py" >/dev/null 2>&1 & ) || true
  fi
EOF
}

# ---------------------------------------------------------------------------
# BENCHMARK ARTIFACT INVENTORY (RTG-46, 2026-08-24): `data/benchmark_artifact_inventory.json`
# froze at 2026-07-29 (file mtime Aug 12) while the :8100/benchmarks page showed
# 26-day-old data with no alarm stronger than "aging". Regeneration cadence was
# unowned. This block gives it an OWNER without any host-level change: the same
# canonical-checkout resolution as the timeline, but delta-guarded on the INPUT —
# regenerate only when a research artifact is newer than the artifact itself, so
# an ordinary commit does not churn a file nobody asked to see change. The build
# is ~0.5 s (measured), pure-stdlib, and the guard makes it a no-op on the common
# path. Fires on ANY commit (artifacts arrive outside handoffs/), guarded
# internally. The timeline block keeps its own handoffs/ change-guard.
# ---------------------------------------------------------------------------
IMARKER="# >>> handoff-inventory hook >>>"
IEND_MARKER="# <<< handoff-inventory hook <<<"

inventory_body() {
  cat <<'EOF'
  _repo="$(git rev-parse --show-toplevel 2>/dev/null)" || _repo=""
  if [ -n "$_repo" ]; then
    _primary="$(git worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p' | head -1)"
    if [ -n "$_primary" ] && [ -f "$_primary/scripts/dashboard/build_benchmark_artifact_inventory.py" ]; then
      _repo="$_primary"
    fi
  fi
  if [ -n "$_repo" ] && [ -f "$_repo/scripts/dashboard/build_benchmark_artifact_inventory.py" ]; then
    _inv="$_repo/data/benchmark_artifact_inventory.json"
    _arts="${ARTIFACTS_DIR:-/mnt/raid0/llm/epyc-inference-research/artifacts}"
    if [ -d "$_arts" ]; then
      if [ ! -f "$_inv" ] || find "$_arts" -name '*.json' -newer "$_inv" -print -quit 2>/dev/null | grep -q .; then
        ( python3 "$_repo/scripts/dashboard/build_benchmark_artifact_inventory.py" >/dev/null 2>&1 & ) || true
      fi
    fi
  fi
EOF
}

# Emit the full marked block for a given hook kind on stdout.
# Each block has its OWN emitter; replace_block swaps one span, so an emitter
# must contain exactly its own markers (a combined emitter would duplicate).
timeline_block_for() {
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

inventory_block_for() {
  printf '%s\n' "$IMARKER"
  printf '%s\n' "# Regenerate the benchmark artifact inventory when a research artifact is newer (detached, delta-guarded)."
  inventory_body
  printf '%s\n' "$IEND_MARKER"
}

# Replace one marked block (start_marker .. end_marker) in a hook file with the
# freshly-emitted body, preserving everything outside it. Returns 1 if the
# markers are missing or malformed (caller decides whether that is fatal).
replace_block() {
  local hook="$1" start_marker="$2" end_marker="$3" emitter="$4"
  local marker_count end_marker_count start_line end_line tmp
  marker_count="$(awk -v marker="$start_marker" '$0 == marker { count++ } END { print count + 0 }' "$hook")"
  end_marker_count="$(awk -v marker="$end_marker" '$0 == marker { count++ } END { print count + 0 }' "$hook")"
  if [ "$marker_count" -ne 1 ] || [ "$end_marker_count" -ne 1 ]; then
    echo "[install-hook] refusing malformed marked block in $hook" >&2
    return 1
  fi
  start_line="$(awk -v marker="$start_marker" '$0 == marker { print NR }' "$hook")"
  end_line="$(awk -v marker="$end_marker" '$0 == marker { print NR }' "$hook")"
  if [ "$start_line" -ge "$end_line" ]; then
    echo "[install-hook] refusing inverted marked block in $hook" >&2
    return 1
  fi
  tmp="$hook.handoff.$$"
  {
    head -n "$((start_line - 1))" "$hook"
    "$emitter" "$kind"
    tail -n "+$((end_line + 1))" "$hook"
  } > "$tmp"
  mv "$tmp" "$hook"
  return 0
}

install_into() {
  kind="$1"
  hook="$HOOK_DIR/$kind"
  if [ -f "$hook" ] && grep -qF "$MARKER" "$hook"; then
    # This is an upgrade path, not an "already installed" no-op.  The marked
    # body is version-controlled by this installer; replacing it removes stale
    # worker-triggered actions (notably the former index_state.py regeneration)
    # while preserving unrelated chained hooks such as git-lfs.
    if ! replace_block "$hook" "$MARKER" "$END_MARKER" timeline_block_for; then
      return 1
    fi
    if grep -qF "$IMARKER" "$hook"; then
      if ! replace_block "$hook" "$IMARKER" "$IEND_MARKER" inventory_block_for; then
        return 1
      fi
      echo "[install-hook] upgraded handoff-timeline + inventory blocks in $hook"
    else
      # Hook predates the inventory block: append it after the timeline block.
      tmp="$hook.handoff.$$"
      {
        cat "$hook"
        printf '\n'
        inventory_block_for
      } > "$tmp"
      mv "$tmp" "$hook"
      echo "[install-hook] upgraded handoff-timeline block, added inventory block in $hook"
    fi
    chmod +x "$hook"
    return 0
  fi
  if [ ! -f "$hook" ]; then
    { printf '#!/bin/sh\n\n'; timeline_block_for "$kind"; inventory_block_for; } > "$hook"
    echo "[install-hook] created $hook"
  else
    # Insert our blocks right after the shebang so they run even if a chained
    # hook (e.g. git-lfs) exits non-zero before the end of the file.
    tmp="$hook.handoff.$$"
    { head -n 1 "$hook"; printf '\n'; timeline_block_for "$kind"; inventory_block_for; tail -n +2 "$hook"; } > "$tmp"
    mv "$tmp" "$hook"
    echo "[install-hook] inserted handoff-timeline + inventory blocks into existing $hook (after shebang)"
  fi
  chmod +x "$hook"
}

mkdir -p "$HOOK_DIR"
for kind in post-commit post-merge post-checkout; do
  install_into "$kind"
done

echo "[install-hook] running an initial build…"
python3 "$REPO/scripts/handoffs/build_handoff_timeline.py" --print >/dev/null || true
echo "[install-hook] done. To remove, delete the blocks between these marker pairs in each hook:"
echo "    $MARKER  /  $END_MARKER"
echo "    $IMARKER  /  $IEND_MARKER"
