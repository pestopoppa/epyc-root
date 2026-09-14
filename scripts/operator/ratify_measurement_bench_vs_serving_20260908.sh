#!/bin/bash
# ratify_measurement_bench_vs_serving_20260908.sh — three measurement amendments from the
# 2026-09-08 champion / R23-58 / INF-70 campaign, on the human-only measurement paths.
#
#   Review:  bash scripts/operator/ratify_measurement_bench_vs_serving_20260908.sh --show
#   Apply:   bash scripts/operator/ratify_measurement_bench_vs_serving_20260908.sh --apply
#   Commit:  printed by --apply
#
# WHY THIS EXISTS. Three rules were paid for in our own measurements on one day, against one
# champion (`ef81196d5`, Qwen3.8-27B-Q8_0, MI210). They are ONE decision because they are one
# failure shape: a number quoted without the field that decides whether it means anything.
#
# THE THREE AMENDMENTS
#
#   MEASUREMENT.md → new appendix block INSTRUMENT-CLASS-1, plus a required §3 declaration
#
#   1. A BENCH-SURFACE NUMBER IS NEVER A SERVING NUMBER. Asked for the champion's decode
#      rate, this session quoted `llama-bench` tg128 at 31.0 tok/s. The production-recipe
#      answer, same build and same day, is 79.25 tok/s — a 2.5x UNDERSTATEMENT OF OUR OWN
#      SYSTEM, given confidently. The cause is structural, not a tuning gap: `llama-bench`
#      cannot do speculative decoding at all, so on a served path with a drafter in it tg128
#      was never measuring the served configuration. Nor is the gap a constant one could
#      correct for — the same day, the serving gate's first firing had the tg128 proxy at
#      +5.958% over six keeps while the serving instrument returned "cannot tell, probably
#      slightly negative" (-2.18%, n=10): 11 points apart, and the wrong sign. So: an
#      ABSOLUTE number may be quoted only from the serving class; a bench number is a valid
#      build-vs-build A/B on its own surface and is inadmissible as a headline; and a
#      cross-class comparison is REFUSED, not caveated.
#
#   MEASUREMENT.md → new appendix block FLOOR-UNIT-1, plus three rows in the §4 noise table
#
#   2. A FLOOR MUST CARRY ITS UNIT, AND n=10 ON A TAIL STATISTIC CANNOT GATE. Within-session
#      (arm) sd is 0.501%; between-session (process launch) sd is 2.793% — a process-scoped
#      knob faces a floor ~13x coarser. Substituting one for the other sized a test at 4
#      sessions/side when the correct answer was 4,780: a 1200-FOLD error that would have
#      been spent as real host hours before the design failed to converge. Separately, the
#      standing serving floor is 4.581% from n=10; the same configuration over n=24 measures
#      6.596%, and of 20,000 bootstrap draws of n=10 from those 24, only 9.0% land at or
#      below the standing value. p95 is an extreme order statistic — an unstable estimator,
#      not a tight condition.
#
#   MEASUREMENT.md → new appendix block BOUNDED-NULL-1, plus a required §3 declaration
#
#   3. A NULL NEEDS ITS POWER AND ITS FIRED-KNOB CONTROL. R23-58 returned null on both
#      claims over 48 launches, 24 per arm. It is a FINDING rather than an absence for two
#      reasons: it states what its power excludes (~0.97 against a 3x dispersion ratio,
#      ~0.69 against 2x), and all 48 positive-control readbacks fired in BOTH directions —
#      AnonHugePages ~53% of RSS in the control arm against 0.0% in the treatment arm, with
#      the kernel THP_enabled flag correct every time. The mechanism demonstrably ran and
#      produced nothing. The counter-example is from the same campaign: INF-70's SYNC-18 was
#      untestable precisely because "no effect" and "the knob never fired" were
#      indistinguishable in its result table — and they are indistinguishable in EVERY
#      result table. Only the control separates them.
#
#   agents/shared/MEASUREMENT_POLICY.md → one digest section pointing at the three blocks,
#   plus one sentence in "The claim rule". The digest does not restate the constitution.
#
# EVIDENCE, all committed, none in scratch (per the §5 durability clause):
#   epyc-inference-research  data/ak-r2358-shim-serving-2026-09-08/   (research main 7020bb94)
#   epyc-inference-research  data/ak-champion-maxperf-2026-09-08/     (research main 7020bb94)
#   epyc-inference-research  data/inf70-retest1-2026-09-08/           (commit 1780fa7b)
#   epyc-root                docs/design/champion-max-performance-20260908.md
#
# WHY IT NEEDS YOU. Both targets sit on the measurement trust boundary, which is
# human-amendment-only: MEASUREMENT.md, its protocols/ annexes and this digest are read-only
# for every autonomous process, precisely so that the agents being judged cannot edit the
# instrument that judges them. No agent may apply this, and no amount of evidence changes
# that — the boundary is about WHO writes, not about how good the argument is.
#
# IF YOU DECLINE. Nothing breaks and no number changes. The three rules stay where they are
# today: in the wiki compile, in the campaign handoffs, and in this session's progress log —
# which is to say campaign-local, so the next campaign re-derives them from its own mistakes.
# That is not hypothetical. The bench-vs-serving rule was ALREADY implied by the standing
# "headlines come from the production recipe" clause, and this campaign violated it anyway at
# 2.5x. A rule that is true but unenforceable at claim-writing time gets rediscovered, and
# the rediscovery is the expensive part.
#
# WHAT THIS DOES NOT DO. It changes no code, no threshold, no gate behaviour, and no existing
# ratified block. It adds two required declarations to the §3 claim grammar, three measured
# rows to the §4 noise table, one CHANGELOG line, three appendix blocks, and one digest
# section. It supersedes nothing: INSTRUMENT-CLASS-1 EXTENDS the §5 promotion clause (an
# instrument that cannot run the production recipe already could not block promotion; now it
# cannot headline either), and the six pre-2026-09-08 rows of the noise table are retained
# exactly as written rather than retro-labelled with a unit nobody verified. It re-verdicts
# nothing already decided; floors already in force become measurement debt, not invalid.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PATCH="${REPO_ROOT}/artifacts/operator/measurement-bench-vs-serving-20260908.patch"
TARGETS=(
    "MEASUREMENT.md"
    "agents/shared/MEASUREMENT_POLICY.md"
)
# Present in the amendment and nowhere in the pre-amendment text — the idempotency sentinel.
SENTINEL="INSTRUMENT-CLASS-1"

usage() { echo "usage: $0 [--show|--apply [--allow-dirty]]" >&2; exit 2; }
[[ $# -ge 1 && $# -le 2 ]] || usage

# Targets carrying unstaged edits that are NOT ours. Printed by the preflight so the operator
# sees exactly whose work sits alongside the amendment.
dirty_targets() {
    local t out=()
    for t in "${TARGETS[@]}"; do
        if ! git -C "${REPO_ROOT}" diff --quiet -- "${t}"; then out+=("${t}"); fi
    done
    printf '%s\n' "${out[@]:-}"
}

case "$1" in
    --show)
        echo "Targets (both HUMAN-AMENDMENT-ONLY):"
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

        # Idempotency. Applying twice would duplicate three appendix blocks in the
        # constitution, which is worse than not applying at all: a reader cannot tell which
        # copy is authoritative.
        if grep -q "${SENTINEL}" "${REPO_ROOT}/MEASUREMENT.md"; then
            echo "REFUSED: '${SENTINEL}' is already present in MEASUREMENT.md — this amendment" >&2
            echo "  has been applied (or landed by another route). Nothing to do." >&2
            echo "  Inspect: git -C ${REPO_ROOT} log --oneline -5 -- ${TARGETS[*]}" >&2
            exit 1
        fi

        mapfile -t DIRTY < <(dirty_targets)
        if [[ ${#DIRTY[@]} -gt 0 && -n "${DIRTY[0]}" && ${allow_dirty} -eq 0 ]]; then
            echo "REFUSED: a target carries UNSTAGED changes that are not part of this amendment:" >&2
            for t in "${DIRTY[@]}"; do
                echo "    ${t}  ($(git -C "${REPO_ROOT}" diff --numstat -- "${t}" | awk '{print $1" added, "$2" deleted"}'))" >&2
            done
            echo >&2
            echo "  These are trust-boundary files, so an unexplained edit on one is worth" >&2
            echo "  reading before anything is layered on top of it. This is also a SHARED" >&2
            echo "  CLONE: applying is safe, COMMITTING is not — a 'git commit -- <file>'" >&2
            echo "  bypasses the index and would sweep the above into this amendment." >&2
            echo >&2
            echo "  Inspect first:  git -C ${REPO_ROOT} diff -- ${DIRTY[*]}" >&2
            echo "  Then either resolve that change with its owner, or re-run:" >&2
            echo "      $0 --apply --allow-dirty" >&2
            echo "  and stage HUNK-SELECTIVELY as instructed below." >&2
            exit 1
        fi

        # Preflight before touching anything: the patch is generated against origin/main
        # content of both files, so a refusal here means a target has moved and the
        # amendment must be regenerated rather than forced.
        git -C "${REPO_ROOT}" apply --check "${PATCH}" \
            || { echo "REFUSED: the amendment does not apply cleanly." >&2
                 echo "  A target has moved since the patch was generated. Regenerate it against" >&2
                 echo "  current content; do NOT apply with fuzz to a trust-boundary file." >&2
                 echo "  Inspect: git -C ${REPO_ROOT} status --porcelain -- ${TARGETS[*]}" >&2
                 echo "           git -C ${REPO_ROOT} log --oneline -5 -- ${TARGETS[*]}" >&2
                 exit 1; }

        # Worktree only — never --index. Staging is yours to do, after you have read the diff.
        git -C "${REPO_ROOT}" apply "${PATCH}"
        echo "Applied to the working tree. NOTHING IS STAGED."
        echo
        if [[ ${#DIRTY[@]} -gt 0 && -n "${DIRTY[0]}" ]]; then
            echo "!! These targets also carry someone else's unstaged work:"
            for t in "${DIRTY[@]}"; do echo "     ${t}"; done
            echo
            echo "   Stage ONLY the amendment, by replaying this patch into the INDEX. The"
            echo "   index still holds the peer's lines, so applying there adds our hunks and"
            echo "   leaves their change unstaged, in the worktree, untouched:"
            echo "       git -C ${REPO_ROOT} apply --cached ${PATCH}"
            echo
            echo "   Do NOT use 'git add -p' here: interactive git is unavailable in this"
            echo "   environment, and a bare 'git add -p' walks the WHOLE dirty tree."
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
        echo "Commit:  git -C ${REPO_ROOT} commit -m 'RATIFIED: INSTRUMENT-CLASS-1, FLOOR-UNIT-1 and BOUNDED-NULL-1 — a bench number is not a serving number, a floor carries its unit, a null carries its power and its fired-knob control (2026-09-08)'"
        echo
        echo "Commit from the INDEX (no pathspec): a 'commit -- <path>' re-reads the working"
        echo "tree and would undo the hunk selection you just made."
        echo
        echo "Then close the prepared task in handoffs/active/autokernel-rebuild-program.md"
        echo "(search: RATIFY-MEAS-1)."
        ;;
    *) usage ;;
esac
