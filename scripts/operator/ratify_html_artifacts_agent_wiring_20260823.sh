#!/bin/bash
# Ratify HTML-artifacts index/runbook wiring into CLAUDE.md and OPERATING_CONSTRAINTS.md.
#
# Both files are on the human-only write list (coordination/session-bus/human_only_paths.yaml),
# so an agent cannot apply this directly (scripts/hooks/check_trust_boundary_edit.sh refuses the
# Write/Edit). This is the pre-validated command the hook asks for: the operator runs it, reviews
# the diff, and commits.
#
# Adds one short section/bullet to each file, pointing every agent at the new
# docs/reference/html-artifacts-index.md (catalog of the project's 5 standalone HTML artifacts)
# and docs/guides/agent-workflows/html-artifacts-runbook.md (placement/naming/registration
# contract for new ones).
#
# SHARED-CLONE SAFETY: at authoring time, CLAUDE.md carries an UNRELATED, UNSTAGED, uncommitted
# diff from another session (a "Working-tree identity" / lane-worktree section). A blanket
# `git add -- CLAUDE.md` would sweep that unrelated work into this commit -- the "shared-file
# commit sweep" hazard CLAUDE.md's own Working-tree identity section warns about. This script
# therefore stages ONLY the hunk it authors, via `git apply --cached` on an isolated
# before/after patch, never a whole-file `git add`, and refuses to commit if the shared index
# holds anything beyond the files this script itself modified.
#
# Usage:
#   bash scripts/operator/ratify_html_artifacts_agent_wiring_20260823.sh --dry-run   # diff only
#   bash scripts/operator/ratify_html_artifacts_agent_wiring_20260823.sh             # apply (no commit)
#   bash scripts/operator/ratify_html_artifacts_agent_wiring_20260823.sh --apply --commit
#
# Idempotent per file: re-running after a successful apply changes nothing for a file whose
# marker is already present.
set -euo pipefail

REPO="${REPO:-/workspace}"

DRY_RUN=0
DO_COMMIT=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --apply)   DRY_RUN=0 ;;
    --commit)  DO_COMMIT=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done

MODIFIED_FILES=()

CLAUDE_MD_SECTION=$(cat <<'EOF'
## HTML Artifacts

Standalone HTML reports/design-docs/flow-maps the project authored (not `dashboard/static/` app
UI — see Dashboards above). Catalog:
[`docs/reference/html-artifacts-index.md`](docs/reference/html-artifacts-index.md). Adding or
updating one: follow
[`docs/guides/agent-workflows/html-artifacts-runbook.md`](docs/guides/agent-workflows/html-artifacts-runbook.md)
(placement rule, naming, self-containment), register it in the index in the same change, and run
`scripts/docs/check_html_artifact_index.py --check` before committing.
EOF
)

OC_SECTION=$(cat <<'EOF'
**Looking for or adding a standalone HTML artifact** (design doc, flow map, deep-dive write-up,
operator report — not `dashboard/static/` app UI, not `tmp/` scratch)? Discovery:
[`docs/reference/html-artifacts-index.md`](../../docs/reference/html-artifacts-index.md) catalogs
every one. Adding or editing one: follow
[`docs/guides/agent-workflows/html-artifacts-runbook.md`](../../docs/guides/agent-workflows/html-artifacts-runbook.md)
(placement rule, naming, self-containment) and register it in the same change — run
`python3 scripts/docs/check_html_artifact_index.py --check` before committing.
EOF
)

# ratify_one RELPATH MARKER ANCHOR CONTENT_VARNAME
ratify_one() {
  local relpath="$1" marker="$2" anchor="$3" content_var="$4"
  local target="$REPO/$relpath"
  local content="${!content_var}"

  [ -f "$target" ] || { echo "REFUSING: $target not found (set REPO=)." >&2; exit 66; }

  if grep -qF "$marker" "$target"; then
    echo "already ratified: '$marker' present in $relpath -- skipping."
    return 0
  fi

  local count
  count=$(grep -cF "$anchor" "$target" || true)
  if [ "$count" -ne 1 ]; then
    echo "REFUSING: anchor found $count time(s) in $relpath, expected exactly 1." >&2
    echo "  anchor: $anchor" >&2
    echo "  $relpath has drifted; re-derive the insertion point before applying." >&2
    exit 65
  fi

  local before tmp
  before="$(mktemp)"
  tmp="$(mktemp)"
  cp "$target" "$before"

  # The explicit `print ""` guarantees one blank line between the inserted section and the
  # anchor regardless of trailing-newline stripping in the $(...) capture above.
  awk -v policy="$content" -v anchor="$anchor" '
    index($0, anchor) && !done { print policy; print ""; done=1 }
    { print }
  ' "$target" > "$tmp"

  if ! grep -qF "$marker" "$tmp"; then
    echo "REFUSING: transform did not insert '$marker' into $relpath; file untouched." >&2
    rm -f "$before" "$tmp"; exit 70
  fi
  local added
  added=$(( $(wc -l < "$tmp") - $(wc -l < "$before") ))
  if [ "$added" -le 0 ]; then
    echo "REFUSING: transform removed or kept lines (delta $added) in $relpath; file untouched." >&2
    rm -f "$before" "$tmp"; exit 70
  fi
  if [ "$(grep -cF "$anchor" "$tmp")" -ne 1 ]; then
    echo "REFUSING: anchor no longer unique after transform in $relpath; file untouched." >&2
    rm -f "$before" "$tmp"; exit 70
  fi

  echo "--- $relpath diff (${added} lines added) ---"
  diff -u "$target" "$tmp" || true
  echo "--- end diff ---"

  if [ "$DRY_RUN" -eq 1 ]; then
    rm -f "$before" "$tmp"
    return 0
  fi

  cp "$target" "$target.bak-$(date +%Y%m%d%H%M%S)"
  cat "$tmp" > "$target"
  echo "APPLIED to $relpath (backup alongside it)."

  local patch
  patch="$(mktemp)"
  # `before` already reflects any OTHER session's pending unstaged edits to this file; it is
  # identical to `tmp` except for this insertion, so this patch captures nothing but the
  # insertion and applies cleanly against the index -- the anchor's surrounding context is
  # untouched by whatever else is pending elsewhere in the file.
  diff -u --label "a/$relpath" --label "b/$relpath" "$before" "$tmp" > "$patch" || true
  if ! git -C "$REPO" apply --cached "$patch"; then
    echo "REFUSING: could not stage the isolated hunk for $relpath (see error above)." >&2
    echo "  Working tree WAS updated; index was not. Inspect and stage manually:" >&2
    echo "    git -C $REPO diff -- $relpath" >&2
    rm -f "$before" "$tmp" "$patch"
    exit 71
  fi
  rm -f "$before" "$tmp" "$patch"
  MODIFIED_FILES+=("$relpath")
}

ratify_one "CLAUDE.md" "## HTML Artifacts" "## Progress Tracking" CLAUDE_MD_SECTION
ratify_one "agents/shared/OPERATING_CONSTRAINTS.md" \
  "Looking for or adding a standalone HTML artifact" "## Test Safety" OC_SECTION

if [ "$DRY_RUN" -eq 1 ]; then
  echo
  echo "DRY RUN -- nothing written. Re-run without --dry-run to apply."
  exit 0
fi

if [ "${#MODIFIED_FILES[@]}" -eq 0 ]; then
  echo "Nothing to do -- both files already ratified."
  exit 0
fi

if [ "$DO_COMMIT" -eq 1 ]; then
  staged=$(git -C "$REPO" diff --cached --name-only)
  unexpected=""
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    match=0
    for m in "${MODIFIED_FILES[@]}"; do [ "$f" = "$m" ] && match=1; done
    [ "$match" -eq 0 ] && unexpected="$unexpected $f"
  done <<< "$staged"
  if [ -n "$unexpected" ]; then
    echo "REFUSING to commit: the shared index has unexpected staged file(s):$unexpected" >&2
    echo "  That is not this script's doing -- another session likely staged them." >&2
    echo "  Resolve that separately, then commit ${MODIFIED_FILES[*]} by hand:" >&2
    echo "    git -C $REPO diff --cached -- ${MODIFIED_FILES[*]}" >&2
    echo "    git -C $REPO commit -m '...'" >&2
    exit 72
  fi

  git -C "$REPO" commit -m "$(cat <<COMMIT_EOF
agents: wire HTML-artifacts index + runbook into CLAUDE.md and OPERATING_CONSTRAINTS.md

Operator-ratified. Points every agent at docs/reference/html-artifacts-index.md (catalog
of the project's 5 standalone HTML artifacts) and
docs/guides/agent-workflows/html-artifacts-runbook.md (placement/naming/registration
contract for new ones), from the two highest-traffic agent-facing docs.
COMMIT_EOF
)"
  echo "committed: ${MODIFIED_FILES[*]}"
else
  echo
  echo "NOT committed. Staged: ${MODIFIED_FILES[*]}"
  echo "Review with:  git -C $REPO diff --cached -- ${MODIFIED_FILES[*]}"
  echo "Then:         git -C $REPO commit"
fi
