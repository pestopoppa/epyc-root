"""Learning-exclusion policy shared by autopilot runtime and reports."""

from __future__ import annotations

from typing import Any

BENIGN_LEARNING_EXCLUSIONS = frozenset(
    {"reproduction_confirmed", "mad_noise", "seq_accumulating", "seq_stale_reference"}
)
NON_CORRUPT_LEARNING_EXCLUSIONS = frozenset({"seq_refuted"})
WITHIN_NOISE_EXCLUSIONS = BENIGN_LEARNING_EXCLUSIONS


def classify_learning_exclusion(verdict: Any, eval_result: Any) -> tuple[str, str, str]:
    """Decide whether a trial should be excluded from strategy learning.

    Returns ``(learning_excluded_by, learning_excluded_reason,
    deficiency_category_override)``. An empty first value means "include
    normally."
    """
    bug_corrupted_by = str(getattr(eval_result, "bug_corrupted_by", "") or "").strip()
    if bug_corrupted_by:
        reason = str(getattr(eval_result, "bug_corrupted_reason", "") or "").strip()
        if not reason:
            reason = f"eval result marked bug-corrupted by {bug_corrupted_by}"
        return bug_corrupted_by, reason, bug_corrupted_by

    has_exo_unrecovered = getattr(eval_result, "n_exogenous_unrecovered", 0) > 0
    if has_exo_unrecovered:
        preview_ids = list(getattr(eval_result, "exogenous_question_ids", []))[:10]
        n_q = getattr(eval_result, "n_questions", 0) or len(
            getattr(eval_result, "exogenous_question_ids", []) or []
        )
        reason = (
            f"{eval_result.n_exogenous_unrecovered}/{n_q} questions "
            f"remained unrecovered after detected service reload "
            f"(sample ids: {preview_ids})"
        )
        return "exogenous_operator_reload", reason, "exogenous_reload"

    details = getattr(eval_result, "details", {}) or {}
    if isinstance(details, dict) and details.get("eval_contaminated_by_abandoned_requests"):
        try:
            orphan_count = int(details.get("eval_orphan_contamination_count") or 0)
        except (TypeError, ValueError):
            orphan_count = 0
        n_q = getattr(eval_result, "n_questions", 0) or orphan_count
        reason = (
            f"{orphan_count}/{n_q} eval request(s) may still have been decoding "
            "server-side after the eval-batch watchdog fired"
        )
        return "eval_abandoned_requests", reason, "eval_abandoned_requests"

    categories = getattr(verdict, "categories", None) or []
    # The MAD test is QUALITY-ONLY. A within-noise quality reading must not launder
    # a FAILED safety verdict (per-suite regression, quality floor, throughput, …)
    # into a "trusted within-noise representative" — that path admits the trial to
    # the Pareto frontier (autopilot.py upsert_representative) and suppresses its
    # deficiency. 2026-06-06: trial 707 failed three per-suite regression checks yet
    # was admitted as mad_noise. Only treat the within-noise tags as benign when the
    # verdict OTHERWISE PASSED; otherwise fall through to the normal failed-trial
    # path (deficiency from verdict.categories), which skips archive admission
    # without mislabelling the trial as corrupted data.
    verdict_passed = bool(getattr(verdict, "passed", True))
    if "mad_noise" in categories and verdict_passed:
        if "reproduction_confirmed" in categories:
            return (
                "reproduction_confirmed",
                "within-noise reproduction of an already-established above-"
                "baseline config: convergence/confirmation of an existing gain, "
                "not a new improvement and not corrupted data",
                "reproduction_confirmed",
            )
        return (
            "mad_noise",
            "quality improvement was within MAD noise band per safety_gate "
            "rolling-history significance test",
            "mad_noise",
        )

    # LEDGER-W4 (01c §3): the sequential e-process verdict, produced only when the
    # default-off AUTOPILOT_SEQ_VERDICT path runs in safety_gate. Three states:
    #   seq_accumulating — E below both confirm/refute thresholds: not-yet-decided,
    #     within-noise → exclude from learning (benign, like mad_noise) until a
    #     verdict resolves. Only honored when the verdict OTHERWISE PASSED, mirroring
    #     the mad_noise guard above (a within-noise reading must not launder a failed
    #     safety verdict into a trusted representative).
    #   seq_confirmed — a confirmed improvement (E_quality>=20 AND E_rate_noninf>=20):
    #     include normally (falls through to the empty include path below).
    #   seq_refuted — e-process evidence refuted the claimed improvement. If the
    #     broader safety verdict otherwise passed, treat it as valid negative
    #     evidence: exclude it from promotion and positive strategy distillation,
    #     but do not mark it as measurement corruption. If a real safety failure
    #     also fired, let the normal failed-trial path preserve the primary
    #     deficiency instead of relabelling it as a seq artifact.
    if "seq_stale_reference" in categories and verdict_passed:
        return (
            "seq_stale_reference",
            "sequential e-process reference profile is stale; excluded from learning "
            "until a baseline-reference draw refreshes the profile (LEDGER-W4)",
            "seq_stale_reference",
        )
    if "seq_accumulating" in categories and verdict_passed:
        return (
            "seq_accumulating",
            "sequential e-process still accumulating evidence (wealth below the "
            "confirm/refute thresholds); within-noise, excluded from learning "
            "until the e-process resolves (LEDGER-W4, AUTOPILOT_SEQ_VERDICT)",
            "seq_accumulating",
        )
    if "seq_refuted" in categories and verdict_passed:
        return (
            "seq_refuted",
            "sequential e-process refuted the candidate improvement; excluded "
            "from promotion and positive strategy distillation so the refuted "
            "hypothesis cannot be re-injected as a winning pattern (LEDGER-W4, "
            "AUTOPILOT_SEQ_VERDICT)",
            "seq_refuted",
        )

    return "", "", ""


# ── Clean-trial representatives (operator decision (c), 2026-09-16) ─────────────
#
# A clean trial (SafetyGate passed, no learning exclusion) used to enter the archive as a
# raw per-trial point, and it was journaled only AFTER the baseline-promotion decision, so
# it could never be the "same-tier frontier representative" a promotion requires. New clean
# rows are stamped ``eval_details.frontier_admission = "representative"`` and cluster by
# config fingerprint exactly like trusted within-noise rows. Rows written before the stamp
# existed keep their per-trial semantics — nothing is back-filled.
FRONTIER_ADMISSION_KEY = "frontier_admission"
FRONTIER_ADMISSION_REPRESENTATIVE = "representative"


def row_is_representative_member(row: Any) -> bool:
    """True when a journal row joins its (tier, config fingerprint) representative cluster.

    The single predicate for runtime replay, snapshot tail folding and live-reproduction
    counting: a trusted within-noise row (``mad_noise`` tag or a benign learning exclusion),
    or a clean row stamped as a frontier representative.
    """
    if not isinstance(row, dict):
        return False
    bug = str(row.get("bug_corrupted_by") or "")
    eval_details = row.get("eval_details")
    if not isinstance(eval_details, dict):
        eval_details = {}
    exclusion = eval_details.get("learning_exclusion")
    excluded_by = str(exclusion.get("by") or "") if isinstance(exclusion, dict) else ""
    if bug == "mad_noise" or excluded_by in WITHIN_NOISE_EXCLUSIONS:
        return True
    return (
        not bug
        and not excluded_by
        and eval_details.get(FRONTIER_ADMISSION_KEY) == FRONTIER_ADMISSION_REPRESENTATIVE
    )
