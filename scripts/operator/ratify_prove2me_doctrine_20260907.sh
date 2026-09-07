#!/bin/bash
# ratify_prove2me_doctrine_20260907.sh — four measurement/fan-out amendments from the
# 2026-09-07 Prove2Me intake wave, on human-only paths.
#
#   Review:  bash scripts/operator/ratify_prove2me_doctrine_20260907.sh --show
#   Apply:   bash scripts/operator/ratify_prove2me_doctrine_20260907.sh --apply
#   Commit:  printed by --apply
#
# WHY THIS EXISTS. The operator submitted Anthropic's Prove2Me / Fermat's-Last-Theorem
# material to test three hypotheses about the coordination harness. All three were
# overturned or dissolved by the dives (recorded on intake-1297..1310). What survived is
# four measurement lessons, each with a worked counterexample supplied by the producers'
# own artifacts — which is what makes them worth enshrining rather than remembering.
#
# THE FOUR AMENDMENTS
#
#   MEASUREMENT_POLICY.md → new section "Naming the unit, the instrument, and the caveat"
#
#   1. A speed claim MUST name its unit of work. Anthropic's post says Prove2Me sped up
#      compilation; Kevin Buzzard says the artifact compiles ~20x slower than Mathlib.
#      BOTH ARE TRUE. The speed-up is per-card (each unit compiles against only its
#      children's statements); the 20x is whole-artifact — and Anthropic's own published
#      build times make the real ratio ~25x, so Buzzard was charitable. The two are
#      causally linked: per-card isolation is what requires the generated preambles that
#      are 31% of the artifact's bytes. An optimization can speed the inner loop and slow
#      the artifact, through the same mechanism.
#
#   2. An instrument modified by the party making the claim requires a control run.
#      The "independent second kernel" check was run ONLY on a build the producer had
#      patched in four places, one of which memoizes negative definitional-equality
#      results — a genuine change to the decision procedure. Its soundness is asserted in
#      one sentence with no argument, no differential test and no unpatched control; and
#      the README concedes stock nanoda would take "many hours each" on some declarations,
#      so the control run was never possible as configured. We patch llama.cpp and then
#      measure with it. This is our failure mode, found in someone else's artifact.
#
#   3. Caveat placement must not be inversely correlated with caveat severity. The
#      sharpest limitations of that artifact live in generated HTML inside a 390 MB folder
#      while the README carries the headline — and the producers' own limitations.md was
#      written, fed to the doc generator, and withheld from publication (the repo has no
#      docs/ directory; the generator's README names the file as an input).
#
#   OPERATING_CONSTRAINTS.md → *Parallel Subagent Fan-Out*
#
#   4. "A fan-out's cost is its discarded work, not its width." WIDTH 3-5 IS UNCHANGED and
#      this clause proposes no change to it — the evidence in fact defends it: 3-5 workers
#      beat 1 worker on both wall-clock and token cost at matched completion, and the
#      central coordination tier was ~11% of compute. What the clause adds is a diagnosis
#      order, because the measured cost driver was elsewhere: 80% of tokens went to runs
#      producing no merged output, 52% to runs aborted outright. Our own instance is
#      fleet-fanout-measurement.md FM-5, which measures exactly that share for our fleet.
#
# WHAT THIS SCRIPT DOES NOT DO. It does not touch MEASUREMENT.md, instrument_eras.yaml, or
# any other trust-boundary file; the two targets below are the whole scope. It never runs a
# blanket `git add`, and it never stages a target on your behalf.
#
# WHY THIS DOES NOT USE `git apply --index` (unlike its sibling ratify scripts). That form
# stages and applies together and refuses when the two disagree, which is the right default
# for a CLEAN target. On 2026-09-07 it refused outright here:
#
#     error: agents/shared/MEASUREMENT_POLICY.md: does not match index
#
# because that file carries an unstaged peer edit — a 17-line DELETION of the ratified
# "Artifact and delta are separate axes" block and its INF-68 evidence. `--index` cannot
# apply to a file whose worktree and index differ, and that refusal is correct.
#
# The deeper hazard is the one the preflight below exists for: this patch was generated
# against the WORKTREE, so a `git commit -- <file>` after applying would sweep the peer's
# deletion into the same commit as our amendment. In a shared clone a pathspec commit
# bypasses the index and takes whatever is in the file. So: apply to the worktree only,
# refuse when a target is dirty unless the operator opts in, and stage HUNK-SELECTIVELY.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PATCH="${REPO_ROOT}/artifacts/operator/prove2me-doctrine-20260907.patch"
TARGETS=(
    "agents/shared/MEASUREMENT_POLICY.md"
    "agents/shared/OPERATING_CONSTRAINTS.md"
)

usage() { echo "usage: $0 [--show|--apply [--allow-dirty]]" >&2; exit 2; }
[[ $# -ge 1 && $# -le 2 ]] || usage

# Targets carrying unstaged edits that are NOT ours. Printed by the preflight so the
# operator sees exactly whose work sits alongside the amendment.
dirty_targets() {
    local t out=()
    for t in "${TARGETS[@]}"; do
        if ! git -C "${REPO_ROOT}" diff --quiet -- "${t}"; then out+=("${t}"); fi
    done
    printf '%s\n' "${out[@]:-}"
}

case "$1" in
    --show)
        echo "Targets:"
        for t in "${TARGETS[@]}"; do echo "  ${REPO_ROOT}/${t}"; done
        echo "Amendment: ${PATCH}"
        echo
        cat "${PATCH}"
        ;;
    --apply)
        [[ -f "${PATCH}" ]] || { echo "REFUSED: no patch at ${PATCH}" >&2; exit 1; }
        allow_dirty=0
        [[ "${2:-}" == "--allow-dirty" ]] && allow_dirty=1
        [[ $# -eq 2 && ${allow_dirty} -eq 0 ]] && usage

        mapfile -t DIRTY < <(dirty_targets)
        if [[ ${#DIRTY[@]} -gt 0 && -n "${DIRTY[0]}" && ${allow_dirty} -eq 0 ]]; then
            echo "REFUSED: a target carries UNSTAGED changes that are not part of this amendment:" >&2
            for t in "${DIRTY[@]}"; do
                echo "    ${t}  ($(git -C "${REPO_ROOT}" diff --numstat -- "${t}" | awk '{print $1" added, "$2" deleted"}'))" >&2
            done
            echo >&2
            echo "  This is a SHARED CLONE. Applying is safe; COMMITTING is not — a" >&2
            echo "  'git commit -- <file>' bypasses the index and would sweep the above" >&2
            echo "  into the same commit as this amendment." >&2
            echo >&2
            echo "  Inspect first:  git -C ${REPO_ROOT} diff -- ${DIRTY[*]}" >&2
            echo "  Then either resolve that change with its owner, or re-run:" >&2
            echo "      $0 --apply --allow-dirty" >&2
            echo "  and stage HUNK-SELECTIVELY as instructed below." >&2
            exit 1
        fi

        # Worktree only — never --index. See the header for why.
        git -C "${REPO_ROOT}" apply "${PATCH}"
        echo "Applied to the working tree. NOTHING IS STAGED."
        echo
        if [[ ${#DIRTY[@]} -gt 0 && -n "${DIRTY[0]}" ]]; then
            echo "!! These targets also carry someone else's unstaged work:"
            for t in "${DIRTY[@]}"; do echo "     ${t}"; done
            echo
            echo "   Stage ONLY the amendment, by replaying this patch into the INDEX."
            echo "   The index still holds the peer's lines, so applying there adds our"
            echo "   hunks and leaves their change unstaged, in the worktree, untouched:"
            echo "       git -C ${REPO_ROOT} apply --cached ${PATCH}"
            echo
            echo "   Do NOT use 'git add -p' here: interactive git is unavailable in this"
            echo "   environment, and a bare 'git add -p' walks the WHOLE dirty tree —"
            echo "   96+ files in this clone, including other sessions' work."
            echo "   Do NOT 'git add' these files whole either; that takes the peer's edit."
            echo
            echo "   Verify — MUST show additions only, and zero deletions:"
            echo "       git -C ${REPO_ROOT} diff --cached --numstat -- ${TARGETS[*]}"
            echo "       git -C ${REPO_ROOT} diff --cached -- ${TARGETS[*]} | grep -c '^-[^-]'   # expect 0"
        else
            echo "Stage:   git -C ${REPO_ROOT} add -- ${TARGETS[*]}"
            echo "Verify:  git -C ${REPO_ROOT} diff --cached -- ${TARGETS[*]}"
        fi
        echo
        echo "Commit:  git -C ${REPO_ROOT} commit -m 'RATIFIED: unit-of-work speed claims, patched-instrument control runs, caveat placement, and the fan-out discarded-work clause (Prove2Me intake wave 2026-09-07)'"
        echo
        echo "Commit from the INDEX (no pathspec): a 'commit -- <path>' would re-read the"
        echo "working tree and undo the hunk selection you just made."
        ;;
    *) usage ;;
esac
