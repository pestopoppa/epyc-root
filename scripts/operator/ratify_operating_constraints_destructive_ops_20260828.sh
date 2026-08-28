#!/bin/bash
# Operator ratification — recover the destructive-operations doctrine.
#
# THIS SCRIPT IS NOT RUN BY AN AGENT. agents/shared/*.md sits inside the
# human-amendment-only trust boundary (invariant 15), and agent writes there are
# hook-blocked. It is staged here so the operator can read the amendment, decide,
# and apply it in one command.
#
#   Review:  bash scripts/operator/ratify_operating_constraints_destructive_ops_20260828.sh --show
#   Apply:   bash scripts/operator/ratify_operating_constraints_destructive_ops_20260828.sh --apply
#
# ---------------------------------------------------------------------------
# WHY THIS EXISTS
#
# The shared clone (/mnt/raid0/llm/epyc-root) and origin/main had DIVERGED on
# agents/shared/OPERATING_CONSTRAINTS.md, each holding doctrine the other lacked:
#
#   * origin/main has "The state file is not the phenomenon" and "A probe reports
#     the absence of what it never looked at" (INC-20260812-post-exit-vram-sample).
#   * The shared clone's WORKING COPY has a section origin/main has never seen --
#     "Destructive operations — mandatory pre-flight and the trash-first rule",
#     origin INC-20260828-glm53-model-deleted, where a "duplicate cleanup" deleted
#     the only copy of a 200 GB model because two aliases of ONE physical tree were
#     read as two copies.
#
# `git log --all -S INC-20260828-glm53-model-deleted` returns nothing: that section
# exists ONLY in that working copy. It is unpublished, it is load-bearing safety
# doctrine, and the three scripts it references already exist on disk
# (scripts/safety/{path_identity,guarded_rm,trash-sweep}.sh, written 2026-08-28
# 20:00Z). Any peer's whole-file operation in the shared clone would erase it with
# no reflog -- which is precisely the hazard class it was written to prevent.
#
# So this patch is a PURE ADDITION onto origin/main's copy: 24 lines added, zero
# removed. It takes neither side wholesale, because each side holds doctrine the
# other lacks. It was NOT authored by an agent -- it is recovered verbatim from
# that working copy.
#
# The blast radius is bookkeeping, not content: until this lands, the shared clone
# cannot fast-forward (it is 56 commits behind), because this file is dirty AND in
# the incoming set. After it lands, resetting the shared clone's copy is lossless.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
PATCH="${REPO_ROOT}/artifacts/operator/operating-constraints-destructive-ops-20260828.patch"
TARGET="agents/shared/OPERATING_CONSTRAINTS.md"

usage() {
    echo "usage: $(basename "$0") --show | --apply" >&2
    exit 64
}

[[ $# -eq 1 ]] || usage

case "$1" in
    --show)
        [[ -f "${PATCH}" ]] || { echo "REFUSED: no patch at ${PATCH}" >&2; exit 1; }
        cat "${PATCH}"
        ;;
    --apply)
        [[ -f "${PATCH}" ]] || { echo "REFUSED: no patch at ${PATCH}" >&2; exit 1; }
        # --index, not --cached: --cached stages WITHOUT touching the working tree,
        # so the file on disk would still lack the amendment after you commit it,
        # and the next edit to that path would silently revert it. --index applies
        # to both and refuses if they disagree.
        #
        # Isolated staging: never a blanket `git add`. A human-only path must not
        # ride into a commit alongside anything else -- five sessions share this
        # index.
        git -C "${REPO_ROOT}" apply --index "${PATCH}"
        echo "Applied and staged: ${TARGET}"
        echo
        echo "Review:  git -C ${REPO_ROOT} diff --cached -- ${TARGET}"
        echo "Commit:  git -C ${REPO_ROOT} commit -m 'doctrine: recover the destructive-operations trash-first rule (INC-20260828-glm53-model-deleted)'"
        echo
        echo "Commit that path ALONE -- a bare 'git commit' here would sweep whatever"
        echo "else five sessions have left in the shared index."
        ;;
    *)
        usage
        ;;
esac
