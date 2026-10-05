"""Deterministic scoring, error classification, and timeout logic.

Pure functions — no network I/O or mutable state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from seeding_types import DEFAULT_TIMEOUT

__all__ = [
    "INFRA_PATTERNS",
    "_adaptive_timeout_s",
    "_bump_timeout_from_observed",
    "_classify_error",
    "_forced_role_serving_mismatch",
    "_inband_error_text",
    "_is_coding_task",
    "infra_failure_reason",
    "measurement_disposition",
    "score_answer_deterministic",
    "score_answer_or_error",
]


# ── Scoring ──────────────────────────────────────────────────────────


_ORCH_SCORER_KEY = "epyc_orch_debug_scorer"


def _load_orchestrator_debug_scorer():
    """Load THIS repo's ``debug_scorer.py`` by path, under a private key.

    seeding_scoring lives beside the orchestrator copy of ``debug_scorer.py``,
    but the research repo ships a diverged copy of the *same* filename. A bare
    ``from debug_scorer import score_answer`` binds whichever copy won the
    ``sys.path`` insertion race, so scorer identity became import-order
    dependent (and could silently pick up the research copy's scoring rules).

    Load the sibling file explicitly via ``importlib`` under a private
    ``epyc_orch_debug_scorer`` ``sys.modules`` key so we always resolve the
    orchestrator copy regardless of import history — and without mutating
    ``sys.path`` or touching the research repo. Cached after first load.
    """
    import importlib.util
    import sys

    cached = sys.modules.get(_ORCH_SCORER_KEY)
    if cached is not None:
        return cached

    scorer_path = Path(__file__).resolve().parent / "debug_scorer.py"
    spec = importlib.util.spec_from_file_location(_ORCH_SCORER_KEY, scorer_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load debug_scorer from {scorer_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_ORCH_SCORER_KEY] = module
    spec.loader.exec_module(module)
    return module


def score_answer_deterministic(
    answer: str,
    expected: str,
    scoring_method: str = "exact_match",
    scoring_config: dict[str, Any] | None = None,
) -> bool:
    """Score an answer deterministically."""
    score_answer = _load_orchestrator_debug_scorer().score_answer

    return score_answer(answer, expected, scoring_method, scoring_config or {})


def score_answer_or_error(
    answer: str,
    expected: str,
    scoring_method: str = "exact_match",
    scoring_config: dict[str, Any] | None = None,
) -> tuple[bool | None, str | None]:
    """Score, converting scorer-unavailability into an EXCLUDED row.

    The B7-hardened orchestrator scorer *raises* when it cannot produce a
    trustworthy verdict rather than silently mis-scoring:
    ``ScoringUnavailableError`` for entry_point-without-oracle, math_verify
    unavailable / bad gold, or an unreachable llm_judge (SCORE-04/05); and
    ``ValueError`` for an unknown scoring method or verifier (SCORE-25).

    The seeding call sites historically invoked ``score_answer_deterministic``
    with no ``try/except`` (seeding_eval.py ``_build_role_result``): a raise
    therefore CRASHED the entire seed run on the main 3-way path and was
    silently swallowed — the question vanishing with no row and no tally — on
    the debugger-retry path. Mirror the eval tower's per-question guard
    (eval_tower.py:2575-2591 → excluded from the denominator at :2991) by
    returning ``(None, reason)`` so the caller can stamp an EXCLUDED
    infrastructure row instead of crashing or dropping. A normal verdict
    returns ``(bool, None)``.
    """
    scorer = _load_orchestrator_debug_scorer()
    # ScoringUnavailableError lives in the dynamically-loaded scorer module.
    # Fall back to an empty tuple (a never-matching except target) if a future
    # scorer build lacks it, so this wrapper never raises on the guard itself.
    scoring_unavailable = getattr(scorer, "ScoringUnavailableError", ())
    try:
        return bool(
            score_answer_deterministic(answer, expected, scoring_method, scoring_config or {})
        ), None
    except scoring_unavailable as exc:  # type: ignore[misc]
        return None, f"scoring_unavailable: {exc}"
    except ValueError as exc:
        return None, f"scoring_error: {exc}"


# ── Error classification ─────────────────────────────────────────────


# REL-1 in-band error prefix (2026-07-21 EV-11c circuit-open incident).
# The orchestrator's llm primitives emit failures AS the answer string of the
# form ``[ERROR: <detail>]`` (src/llm_primitives/primitives.py::_call →
# REL-1 measurement guards — UNIFIED 2026-08-11 into
# `src.autopilot_core.measurement_guards`, closing the residual filed by
# scorer-fork-drift-audit-2026-07-22.md. These were local copies of the
# eval_tower implementations, deliberate at the time because eval_tower was
# read-only to the session that wrote them.
#
# They are re-exported under their original private names so every existing
# caller and test keeps working unchanged; the names remain in __all__.
# Two copies of an ADMISSIBILITY rule drift silently, and the drift only ever
# surfaces as two paths disagreeing about the same measurement.
from src.autopilot_core.measurement_guards import (
    INFRA_ERROR_PATTERNS as _INFRA_ERROR_PATTERNS,
    forced_role_serving_mismatch as _forced_role_serving_mismatch,
    inband_error_text as _inband_error_text,
    infra_failure_reason,
    legacy_error_type as _legacy_error_type,
    measurement_disposition,
)


# The substring list is now owned by `measurement_guards` (one copy of an
# admissibility rule, per this module's own unification note). Re-exported
# under its historical name for the callers and tests that import it.
INFRA_PATTERNS = list(_INFRA_ERROR_PATTERNS)


def _classify_error(
    error_str: str | None,
    resp: Mapping[str, Any] | None = None,
) -> str:
    """Classify an error as ``infrastructure`` / ``task_failure`` / ``none``.

    STRUCTURAL first, substring last. The historical implementation was a
    substring match over ``error_str`` alone, which fails open by construction:
    it must RECOGNISE a failure in order to exclude it, so every message it did
    not recognise became a wrong answer. Measured against the real transport:

    * ``HTTP 400`` → ``"Client error '400 Bad Request' for url ..."`` matches no
      pattern (``server error`` does, ``client error`` does not) → ``task_failure``
      → scored WRONG. A per-slot context overflow returns 400, so a *capacity*
      problem was being reported as a permanent quality regression.
    * ``httpx.ReadTimeout("")`` → ``error_str`` is ``""`` → callers' ``if not
      error`` guard treats the call as a SUCCESS and scores its empty answer.
    * an empty/garbage HTTP body → ``"Expecting value: line 1 column 1"`` →
      ``task_failure`` → scored WRONG.

    Passing ``resp`` lets the shared classifier read the transport facts the
    caller already recorded (``failure_reason``, ``failure_provenance.class``,
    ``_meta.reason``, the HTTP status, an empty non-error reply). The
    single-argument form is preserved for legacy callers.
    """
    if error_str is None and resp is None:
        return "none"
    return _legacy_error_type(
        # ETR-3: the seeding/calibration path is a MEASUREMENT path — a non-blank
        # answer with a zero token counter did not come from a generation, so it
        # must leave the quality denominator instead of scoring as a wrong answer.
        measurement_disposition(resp, error=error_str, require_generation_evidence=True)
    )


# ── Coding-task heuristic ────────────────────────────────────────────


def _is_coding_task(prompt: str) -> bool:
    """Heuristic to determine if a task is coding-related.

    Used to choose between live architect-like roles when multiple exist.
    """
    coding_indicators = [
        "code", "function", "implement", "debug", "refactor",
        "class", "method", "algorithm", "bug", "error",
        "syntax", "compile", "runtime", "test", "unittest",
        "python", "javascript", "typescript", "rust", "go",
        "def ", "async ", "import ", "return ", "class ",
    ]
    prompt_lower = prompt.lower()
    return any(ind in prompt_lower for ind in coding_indicators)


# ── Timeout logic ────────────────────────────────────────────────────


def _adaptive_timeout_s(
    *,
    role: str,
    mode: str,
    prompt: str,
    is_vl: bool,
    hard_timeout_s: int,
) -> int:
    """Return a generous per-call timeout.

    Previous per-role caps (frontdoor=180, vision=240, etc.) caused premature
    INFRA classifications when the server was still generating.  The llama.cpp
    server keeps generating after client disconnect, so tight timeouts only
    waste the work.  Use a flat 600s ceiling; optimize later once we have
    solid per-role telemetry.
    """
    return max(60, int(hard_timeout_s or DEFAULT_TIMEOUT))


def _bump_timeout_from_observed(
    *,
    current_s: int,
    observed_s: float,
    factor: float,
    slack_s: int,
    hard_timeout_s: int,
    role_cap_s: int,
) -> int:
    """Increase timeout based on observed earlier stage runtime for this question.

    With the flat 600s ceiling from _adaptive_timeout_s, this function now
    only raises current_s if the observed time suggests it's too low.
    """
    if observed_s <= 0:
        return current_s
    observed_budget = int(observed_s * factor + slack_s)
    return max(current_s, min(observed_budget, max(60, int(hard_timeout_s or DEFAULT_TIMEOUT))))
