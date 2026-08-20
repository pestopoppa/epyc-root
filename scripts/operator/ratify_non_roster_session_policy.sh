#!/bin/bash
# Ratify the NON-ROSTER SESSION POLICY into CLAUDE.md.
#
# CLAUDE.md is on the human-only write list (coordination/session-bus/human_only_paths.yaml),
# so an agent cannot apply this. That is the point: the rule an agent must follow is not a
# rule an agent may write. This script is the pre-validated command the trust-boundary hook
# asks for -- the operator runs it, reviews the diff, and commits.
#
# Usage:
#   bash scripts/operator/ratify_non_roster_session_policy.sh --dry-run   # show the diff only
#   bash scripts/operator/ratify_non_roster_session_policy.sh             # apply
#   bash scripts/operator/ratify_non_roster_session_policy.sh --apply --commit
#
# Idempotent: re-running after a successful apply exits 0 and changes nothing.
set -euo pipefail

REPO="${REPO:-/workspace}"
TARGET="$REPO/CLAUDE.md"
MARKER="### Non-roster sessions"
ANCHOR='**Single source of truth**: `/workspace/repos/<name>`'

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

[ -f "$TARGET" ] || { echo "REFUSING: $TARGET not found (set REPO=)" >&2; exit 66; }

# Idempotency BEFORE anchor checks: a second run is a no-op, not an error.
if grep -qF "$MARKER" "$TARGET"; then
  echo "already ratified: '$MARKER' is present in $TARGET -- nothing to do."
  exit 0
fi

# The anchor must appear exactly once, or the insertion point is ambiguous.
count=$(grep -cF "$ANCHOR" "$TARGET" || true)
if [ "$count" -ne 1 ]; then
  echo "REFUSING: anchor found $count time(s) in $TARGET, expected exactly 1." >&2
  echo "  anchor: $ANCHOR" >&2
  echo "  CLAUDE.md has drifted; re-derive the insertion point before applying." >&2
  exit 65
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

POLICY=$(cat <<'POLICY_EOF'
### Non-roster sessions

Not every session is a roster main. Operator-spawned and ad-hoc sessions are legitimate and
**keep the shared clone** — there is no lane to send them to and inventing one would mean
addressing a retired id, which is how C24 and C28 happened. They accept a harder gate instead.

If `check_lane_worktree.py --strict` returns 3 and you have no lane:

1. **Declare a session id.** Use it for every lease and lock (`--agent <id>`). Make it
   self-describing and time-stamped, e.g. `operator-wrapup-20260820`. **Never borrow a roster
   id** — a main and its subagents already share one, and a third claimant makes the holder of
   a lease unknowable.
2. **Stage hunk-selectively, then commit the INDEX.** `git add -p <path>`, or
   `git apply --cached mine.patch`, then `git commit -m "..."` with **no pathspec**.
3. **`git diff -- <file>` before every commit AND every revert.** In a shared tree the hunks
   next to yours may be someone else's, and nothing in git will tell you at commit time.
4. **Say so in your wrap-up** — that you ran without a lane, and that staging was hunk-selective.
   The checkbox flip-count gate is NOT trustworthy from the shared clone; scope it to your own
   files and say that you did.

Three git shapes are **refused outright** in the shared repos by
`scripts/hooks/check_commit_hygiene.py`, for roster and non-roster sessions alike, because they
are wrong for anyone: `git commit -- <pathspec>` (bypasses the index and publishes a peer's
working-tree hunks under your name — proven, `dada0bbc`); `git checkout/restore -- <path>` over
a **dirty** path (no conflict, **no reflog**); and `git stash` push/save (captures untracked
runtime files that reappear before the pop). `git restore --staged <path>` stays allowed — it
touches the index only and is the recommended repair. Override, attributably, with
`EPYC_ALLOW_COMMIT_HYGIENE_BYPASS=1` once you have confirmed the loss is yours to take.

POLICY_EOF
)

awk -v policy="$POLICY" -v anchor="$ANCHOR" '
  index($0, anchor) && !done { print policy; done=1 }
  { print }
' "$TARGET" > "$TMP"

# Verify the transform did exactly what it claimed before anything is moved.
if ! grep -qF "$MARKER" "$TMP"; then
  echo "REFUSING: transform did not insert the policy; $TARGET untouched." >&2
  exit 70
fi
added=$(( $(wc -l < "$TMP") - $(wc -l < "$TARGET") ))
if [ "$added" -le 0 ]; then
  echo "REFUSING: transform removed or kept lines (delta $added); $TARGET untouched." >&2
  exit 70
fi
if [ "$(grep -cF "$ANCHOR" "$TMP")" -ne 1 ]; then
  echo "REFUSING: anchor no longer unique after transform; $TARGET untouched." >&2
  exit 70
fi

echo "--- diff (${added} lines added) ---"
diff -u "$TARGET" "$TMP" || true
echo "--- end diff ---"

if [ "$DRY_RUN" -eq 1 ]; then
  echo
  echo "DRY RUN - nothing written. Re-run without --dry-run to apply."
  exit 0
fi

cp "$TARGET" "$TARGET.bak-$(date +%Y%m%d%H%M%S)"
cat "$TMP" > "$TARGET"
echo "APPLIED to $TARGET (backup alongside it)."

if [ "$DO_COMMIT" -eq 1 ]; then
  git -C "$REPO" fetch --quiet || true
  git -C "$REPO" add -- CLAUDE.md
  git -C "$REPO" commit -m "CLAUDE.md: non-roster session policy (accept shared, gate hard)

Operator-ratified. Non-roster sessions keep the shared clone and accept a harder
gate: a declared session id, hunk-selective staging, an index commit with no
pathspec, and \`git diff -- <file>\` before every commit and every revert.

Pairs with scripts/hooks/check_commit_hygiene.py, which refuses the three shapes
that are destructive in a shared tree for anyone."
  echo "committed."
else
  echo "NOT committed. Review, then:  git -C $REPO add -- CLAUDE.md && git -C $REPO commit"
fi
