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
TARGET="agents/shared/OPERATING_CONSTRAINTS.md"
MERGED="${REPO_ROOT}/artifacts/operator/OPERATING_CONSTRAINTS.merged-20260828.md"

# The two sides of the divergence, and the intended result. Installing the full
# merged FILE rather than applying a context patch is deliberate: this script must
# be correct whichever side the tree it runs in happens to hold, and a patch built
# against one side silently misapplies against the other.
SHA_ORIGIN=7202449e22ed6ff59db820b4c9831409cc53deb9b67d87ac5fdfef8198df4b9b
SHA_SHARED=95c5ff5fba8b6c5856ffd6c9a593c9ab1e8cadca4e5637b206181235cc64a014
SHA_MERGED=01ef1a8a9aa9ad358aa44177c761723f3536083d7f9dc7dc47a8fe2445e33ab5

usage() {
    echo "usage: $(basename "$0") --show | --apply" >&2
    exit 64
}

[[ $# -eq 1 ]] || usage
[[ -f "${MERGED}" ]] || { echo "REFUSED: no merged file at ${MERGED}" >&2; exit 1; }

got="$(sha256sum "${MERGED}" | cut -d' ' -f1)"
[[ "${got}" == "${SHA_MERGED}" ]] || {
    echo "REFUSED: ${MERGED} is not the reviewed content" >&2
    echo "  expected ${SHA_MERGED}" >&2
    echo "  got      ${got}" >&2
    exit 1
}

case "$1" in
    --show)
        diff -u "${REPO_ROOT}/${TARGET}" "${MERGED}" \
            --label "current  (${TARGET})" --label "merged" || true
        ;;
    --apply)
        current="$(sha256sum "${REPO_ROOT}/${TARGET}" | cut -d' ' -f1)"
        case "${current}" in
            "${SHA_MERGED}")
                echo "Already merged; nothing to do."; exit 0 ;;
            "${SHA_ORIGIN}"|"${SHA_SHARED}")
                ;;                       # a known side of the divergence
            *)
                echo "REFUSED: ${TARGET} is in an unrecognised state (${current})." >&2
                echo "Someone has edited it since this script was prepared. Re-derive" >&2
                echo "the merge rather than overwriting an unreviewed change." >&2
                exit 1 ;;
        esac
        cp "${MERGED}" "${REPO_ROOT}/${TARGET}"
        # Isolated staging: never a blanket `git add`. A human-only path must not
        # ride into a commit alongside anything else -- five sessions share this
        # index.
        git -C "${REPO_ROOT}" add -- "${TARGET}"
        echo "Installed and staged: ${TARGET}"
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
