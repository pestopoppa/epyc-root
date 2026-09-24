#!/bin/bash
# ratify_rtg09_duration_reward_20260924.sh — flip compute_reward's wall-clock
# duration speed axis from DEFAULT-OFF to live, as ONE operator-ratified
# routing_reward instrument-era boundary.
#
#   Review:  bash scripts/operator/ratify_rtg09_duration_reward_20260924.sh --show
#   Apply:   bash scripts/operator/ratify_rtg09_duration_reward_20260924.sh --apply
#   Commit:  printed by --apply (orchestrator repo)
#
# WHY THIS NEEDS RATIFICATION (not just a code merge)
#
#   RTG-09 (handoffs/active/decision-aware-routing.md, DAR-5 precondition) adds a graded
#   wall-clock task-duration speed dimension to `compute_reward`
#   (epyc-orchestrator orchestration/repl_memory/q_reward.py), because tokens/sec alone is
#   gameable through tool calls and blind to orchestration/tool overhead (DAR handoff:
#   median wall/model-compute overhead 1.60x, p90 9.09x over 19,433 tasks).
#
#   A change to compute_reward's OUTPUT DISTRIBUTION is a routing_reward instrument-era
#   change (see E9-routing-reward in orchestration/instrument_eras.yaml — the 2026-07-21
#   role-key fix that last changed this same function's output distribution, replayed at
#   0.0000 -> 2.4580 bits of reward entropy). That registry is human-amendment-only, and
#   rewards feed Q-updates CONTINUOUSLY (every scored task nudges a stored Q-value), so the
#   behaviour flip and the era boundary must happen at the SAME moment, by ratification —
#   never as a silent default change in a merged commit.
#
#   The RTG-09 code therefore landed with `cost_lambda_duration` DEFAULT-OFF (0.0) and
#   `cost_penalty_lambda` (tokens/sec) unchanged (0.15): with those defaults,
#   `compute_reward` is byte-identical to pre-RTG-09 for every input (proved by
#   tests/unit/test_q_reward_duration.py::test_default_config_reward_is_byte_identical_with_and_without_duration).
#   Everything else RTG-09 added — the derivation script, the checked-in per-role p50/p90
#   baselines JSON, the loader, and the task_duration_s wiring at all three call sites — is
#   inert data/plumbing until this script's --apply flips the two floats.
#
# WHAT --apply DOES
#
#   1. Refuses unless $ORCH_ROOT's checked-out HEAD contains BOTH RTG-09 commits (below) —
#      i.e. refuses until noninf/rtg09-duration has actually been reviewed and merged into
#      whatever branch that clone runs. Refuses if AutoPilot is running (read-only /proc
#      scan, never a name-pattern kill).
#   2. Flips, in $ORCH_ROOT/orchestration/repl_memory/q_scorer.py:
#        cost_lambda_duration: float = 0.0   -> 0.20   (becomes the PRIMARY speed axis)
#        cost_penalty_lambda:  float = 0.15  -> 0.05   (tokens/sec demoted to SECONDARY)
#      via an anchor-based single-occurrence text replace (refuses if the sentinel is not
#      found exactly once, so it can never silently touch the wrong line or a stale file).
#   3. Appends an era row to $ORCH_ROOT/orchestration/instrument_eras.yaml, scope
#      routing_reward, id E18-routing-reward-duration-axis (next free E-number after E17;
#      E9-routing-reward is the prior era in this same scope), with a RECONCILIATION note
#      mirroring E9's: pre-boundary reward/Q-value rows are demote-to-prior for any
#      pre/post reward comparison or policy training spanning this boundary.
#   4. Stamps the boundary at APPLY time (not at code-review time), matching E9/E17's own
#      convention — the boundary is when the flip takes effect, not when it was written.
#   5. Runs the q_reward/q_scorer test suite against the now-flipped tree and refuses
#      (before printing commit instructions) if it fails.
#   6. Prints, but does NOT run, the commit command for the orchestrator repo. NOTHING IS
#      STAGED OR COMMITTED by this script.
#
# WHAT --apply DOES NOT DO
#
#   Does not commit, does not push, does not reload or restart anything. The orchestrator
#   API/autopilot process must be reloaded separately for the flip to take effect once
#   committed — this script prints that requirement and stops; per
#   agents/shared/OPERATING_CONSTRAINTS.md ("Reload ownership"), the session that owns
#   inference executes that reload at its own boundary, never this script.
#
# IDEMPOTENCY. Sentinel-checked: a second --apply refuses immediately (old value already
# flipped, or the era id is already present), rather than double-applying or corrupting the
# file on a re-run.
#
# IF YOU DECLINE. Nothing breaks. RTG-09's code stays on main (once merged) fully inert —
# cost_lambda_duration stays 0.0 and compute_reward keeps its pre-RTG-09 output for every
# input. DAR-5 remains gated on this ratification, not on anything else.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ORCH_ROOT="${ORCH_ROOT:-/mnt/raid0/llm/epyc-orchestrator}"
QSCORER="${ORCH_ROOT}/orchestration/repl_memory/q_scorer.py"
ERAS="${ORCH_ROOT}/orchestration/instrument_eras.yaml"
ERA_ID="E18-routing-reward-duration-axis"
# The RTG-09 commits on epyc-orchestrator main (landed 2026-09-24): b8035db9 adds
# the duration dimension + derivation artifact, 88e24ef0 lands it DEFAULT-OFF per
# this ratification's own precondition.
RTG09_COMMITS=(b8035db9 88e24ef0)
SENTINEL_OLD_DURATION='cost_lambda_duration: float = 0.0'
SENTINEL_NEW_DURATION='cost_lambda_duration: float = 0.20'
SENTINEL_OLD_TPS='cost_penalty_lambda: float = 0.15'
SENTINEL_NEW_TPS='cost_penalty_lambda: float = 0.05'

usage() { echo "usage: $0 [--show|--apply]" >&2; exit 2; }
[[ $# -eq 1 ]] || usage

era_row() {  # $1 = boundary timestamp
    cat <<EOF
  - id: ${ERA_ID}
    from: "$1"
    scope: routing_reward
    note: >
      RTG-09 duration-axis boundary (operator ratification 2026-09-24; DAR-5 precondition,
      handoffs/active/decision-aware-routing.md). compute_reward
      (orchestration/repl_memory/q_reward.py) gained a graded wall-clock task-duration
      speed dimension (Dimension 0), landed DEFAULT-OFF (cost_lambda_duration=0.0) pending
      this ratification, because rewards feed Q-updates continuously and a change to
      compute_reward's output distribution is its own instrument-era boundary, independent
      of E9-routing-reward's role-key fix above. This boundary flips cost_lambda_duration
      0.0 -> 0.20 (primary speed axis, graded 0..weight between each role's measured p50/p90
      wall-clock duration) and demotes cost_penalty_lambda (tokens/sec) 0.15 -> 0.05
      (secondary) in the SAME commit as this era row. Implementation: epyc-orchestrator
      ${RTG09_COMMITS[0]} + ${RTG09_COMMITS[1]}. Per-role p50/p90 duration baselines:
      orchestration/derived/duration_baselines_by_role.json (protocol id
      RTG09-DURATION-BASELINE-v1, 137,256 task_started/task_completed pairs, 117 progress-log
      files 2026-02-27..2026-09-23). RECONCILIATION: pre-boundary reward and q_value rows
      reflect tokens/sec-only speed pricing; they are demote-to-prior for any pre/post reward
      comparison or policy training that spans this boundary — re-derive under the
      duration-aware scorer, or replay via scripts/analysis/rescore_rewards_from_progress.py.

EOF
}

# Read-only /proc scan for a running AutoPilot (never a name-pattern tool; nothing is signalled).
autopilot_pids() {
    local d cmd
    for d in /proc/[0-9]*; do
        cmd="$(tr '\0' ' ' < "${d}/cmdline" 2>/dev/null || true)"
        [[ "$cmd" == *"autopilot.py"*" start"* ]] && printf '%s ' "${d#/proc/}"
    done
    return 0
}

case "$1" in
    --show)
        echo "Targets (routing_reward instrument-era boundary, human-amendment-only):"
        echo "  ${QSCORER}"
        echo "  ${ERAS}"
        echo
        echo "== q_scorer.py ScoringConfig default flip =="
        echo "  ${SENTINEL_OLD_DURATION}"
        echo "    -> ${SENTINEL_NEW_DURATION}"
        echo "  ${SENTINEL_OLD_TPS}"
        echo "    -> ${SENTINEL_NEW_TPS}"
        echo
        echo "== era row appended to the eras: list (boundary = apply time) =="
        era_row "<apply-time UTC>"
        echo "== required RTG-09 commits in \${ORCH_ROOT} HEAD =="
        printf '  %s\n' "${RTG09_COMMITS[@]}"
        echo
        echo "After --apply: commit the orchestrator repo (printed then), and reload the"
        echo "orchestrator API/autopilot separately for the flip to take effect (not done here)."
        ;;
    --apply)
        [[ -f "${QSCORER}" ]] || { echo "REFUSED: no file at ${QSCORER}" >&2; exit 1; }
        [[ -f "${ERAS}" ]] || { echo "REFUSED: no file at ${ERAS}" >&2; exit 1; }

        old_d_count="$(grep -oF "${SENTINEL_OLD_DURATION}" "${QSCORER}" | wc -l | tr -d ' ')"
        new_d_count="$(grep -oF "${SENTINEL_NEW_DURATION}" "${QSCORER}" | wc -l | tr -d ' ')"
        if [[ "${old_d_count}" -eq 0 ]]; then
            if [[ "${new_d_count}" -gt 0 ]]; then
                echo "REFUSED: ${QSCORER} already carries '${SENTINEL_NEW_DURATION}' — already applied." >&2
                exit 1
            fi
            echo "REFUSED: sentinel not found in ${QSCORER}: ${SENTINEL_OLD_DURATION}" >&2
            exit 1
        fi
        if [[ "${old_d_count}" -ne 1 ]]; then
            echo "REFUSED: expected exactly one occurrence of '${SENTINEL_OLD_DURATION}' in ${QSCORER}, found ${old_d_count}." >&2
            exit 1
        fi
        old_t_count="$(grep -oF "${SENTINEL_OLD_TPS}" "${QSCORER}" | wc -l | tr -d ' ')"
        if [[ "${old_t_count}" -ne 1 ]]; then
            echo "REFUSED: expected exactly one occurrence of '${SENTINEL_OLD_TPS}' in ${QSCORER}, found ${old_t_count}." >&2
            exit 1
        fi
        if grep -q "id: ${ERA_ID}" "${ERAS}"; then
            echo "REFUSED: ${ERA_ID} already present in ${ERAS}." >&2
            exit 1
        fi

        for c in "${RTG09_COMMITS[@]}"; do
            git -C "${ORCH_ROOT}" merge-base --is-ancestor "$c" HEAD 2>/dev/null || {
                echo "REFUSED: ${ORCH_ROOT} HEAD does not contain RTG-09 commit $c." >&2
                echo "  Merge/fast-forward noninf/rtg09-duration into that clone's checked-out branch first," >&2
                echo "  or update RTG09_COMMITS in this script if the branch was squash-merged under a new SHA." >&2
                exit 1; }
        done

        live="$(autopilot_pids)"
        if [[ -n "${live// /}" ]]; then
            echo "REFUSED: AutoPilot is running (pid ${live}) on code that may predate this boundary." >&2
            echo "  Stop it first (full-stack rule: stop autopilot before the stack), then re-run." >&2
            exit 1
        fi

        git -C "${ORCH_ROOT}" diff --quiet -- orchestration/repl_memory/q_scorer.py || {
            echo "REFUSED: ${QSCORER} carries unstaged changes that are not this ratification:" >&2
            echo "  git -C ${ORCH_ROOT} diff -- orchestration/repl_memory/q_scorer.py" >&2
            exit 1; }
        git -C "${ORCH_ROOT}" diff --quiet -- orchestration/instrument_eras.yaml || {
            echo "REFUSED: ${ERAS} carries unstaged changes; inspect them first." >&2
            exit 1; }

        boundary="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

        python3 - "${QSCORER}" "${SENTINEL_OLD_DURATION}" "${SENTINEL_NEW_DURATION}" \
                              "${SENTINEL_OLD_TPS}" "${SENTINEL_NEW_TPS}" <<'PY'
import sys
path, old_d, new_d, old_t, new_t = sys.argv[1:6]
text = open(path, encoding="utf-8").read()
if text.count(old_d) != 1:
    sys.exit(f"REFUSED: expected exactly one occurrence of {old_d!r} in {path}, found {text.count(old_d)}")
if text.count(old_t) != 1:
    sys.exit(f"REFUSED: expected exactly one occurrence of {old_t!r} in {path}, found {text.count(old_t)}")
text = text.replace(old_d, new_d, 1).replace(old_t, new_t, 1)
open(path, "w", encoding="utf-8").write(text)
PY

        python3 - "${ERAS}" "$(era_row "${boundary}")" <<'PY'
import sys
path, row = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
anchor = "\nknown_dead_instrument_items:"
if text.count(anchor) != 1:
    sys.exit(f"REFUSED: expected exactly one '{anchor.strip()}' anchor in {path}")
text = text.replace(anchor, "\n" + row.rstrip("\n") + "\n" + anchor, 1)
open(path, "w", encoding="utf-8").write(text)
PY
        python3 -c "import sys,yaml; d=yaml.safe_load(open(sys.argv[1])); assert any(e.get('id')==sys.argv[2] for e in d['eras'])" "${ERAS}" "${ERA_ID}" \
            || { echo "ERROR: era file failed to parse after the append — inspect ${ERAS}" >&2; exit 1; }

        echo "Applied to ${ORCH_ROOT} (boundary ${boundary}). NOTHING IS STAGED."
        echo
        echo "Running q_reward/q_scorer tests against the flipped tree..."
        VENVPY="${ORCH_ROOT}/.venv/bin/python3"
        [[ -x "${VENVPY}" ]] || VENVPY="python3"
        "${VENVPY}" -m pytest \
            "${ORCH_ROOT}/tests/unit/test_q_reward_duration.py" \
            "${ORCH_ROOT}/tests/unit/test_q_reward_role_key.py" \
            "${ORCH_ROOT}/tests/unit/test_q_scorer.py" -q || {
            echo "REFUSED (post-flip check): tests failed — inspect before committing anything." >&2
            exit 1
        }

        echo
        echo "Review, then commit the orchestrator repo from its own tree, pathspec-limited:"
        echo "  git -C ${ORCH_ROOT} diff -- orchestration/repl_memory/q_scorer.py orchestration/instrument_eras.yaml"
        echo "  git -C ${ORCH_ROOT} commit -m 'RATIFIED: RTG-09 duration reward axis live; era ${ERA_ID} (2026-09-24)' -- orchestration/repl_memory/q_scorer.py orchestration/instrument_eras.yaml"
        echo
        echo "REQUIRED, NOT DONE HERE: the orchestrator API/autopilot process must be reloaded"
        echo "for this flip to take effect (uvicorn :8000 reload / stack reload). Reload"
        echo "ownership: the session that owns inference executes it at its own boundary"
        echo "(agents/shared/OPERATING_CONSTRAINTS.md -> Inference and Benchmarks)."
        ;;
    *) usage ;;
esac
