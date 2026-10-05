"""Shared REL-1 measurement guards for role-attributed scoring.

Both the eval tower (`scripts/autopilot/eval_tower.py`) and the seeding path
(`scripts/benchmark/seeding_scoring.py`) must answer the same two questions
before a response is allowed to count as a measurement of a role:

  1. Is this "answer" actually an in-band orchestrator ERROR string?
  2. Was the request served by a DIFFERENT role than the one it pinned?

Until now each side carried its own copy. The copies were deliberate — eval_tower
was read-only to the session that wrote the seeding guards — and the audit that
created them filed their unification as a residual (`scorer-fork-drift-audit-
2026-07-22.md`). This module is that unification.

Why it matters that there is exactly one copy: these are not helpers, they are
the predicates that decide whether a number is admissible evidence. Two copies of
an admissibility rule drift silently, and the drift only shows up as a scorer
disagreement between two paths that are supposed to be measuring the same thing —
which is precisely the defect class the fork-drift audit exists to close.

Verified byte-equivalent in behaviour at unification time: both prior copies
parsed to identical ASTs once docstrings were stripped, so this move changes no
outcome on either path.
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = [
    "DISPOSITION_INFRA_FAILED",
    "DISPOSITION_SCORED",
    "DISPOSITION_SCORING_FAILED",
    "DISPOSITION_TASK_FAILED",
    "FAILURE_DISPOSITION_KEY",
    "FAILURE_REASON_KEY",
    "INBAND_ERROR_PREFIX",
    "INFRA_ERROR_PATTERNS",
    "INFRA_FAILURE_REASONS",
    "INFRA_PROVENANCE_CLASSES",
    "NON_QUALITY_DISPOSITIONS",
    "forced_role_serving_mismatch",
    "inband_error_text",
    "infra_failure_reason",
    "is_quality_admissible",
    "legacy_error_type",
    "measurement_disposition",
]


# The orchestrator emits in-band failures as `[ERROR: ...]` at start-of-answer:
# `src/llm_primitives/inference.py` returns `f"[ERROR: {e}]"`, and the
# circuit-open detail reads `Backend unavailable (circuit open): <url>`. When the
# breaker opens and the /chat body is NOT run through server-side
# `_annotate_error`, the client receives `answer="[ERROR: Backend unavailable
# (circuit open): ...]"` with `error=None` — i.e. a failure wearing a success's
# clothes.
#
# Anchor to this REAL start-of-answer prefix, never a loose substring: a model
# legitimately discussing "[ERROR:" mid-answer must not be discarded as infra.
INBAND_ERROR_PREFIX = "[ERROR:"


def inband_error_text(answer: Any) -> str | None:
    """Return the in-band orchestrator error string when ``answer`` IS one.

    Anchored to the emitted ``[ERROR: ...]`` prefix at start-of-answer (after
    stripping leading whitespace), matching the primitives/inference emitters
    and the server-side ``_annotate_error`` convention. Returns ``None`` for a
    normal answer.
    """
    if not isinstance(answer, str):
        return None
    stripped = answer.lstrip()
    if stripped.startswith(INBAND_ERROR_PREFIX):
        return stripped
    return None


def forced_role_serving_mismatch(
    force_role: Any, resp: Mapping[str, Any]
) -> str | None:
    """Return the serving role when it differs from the forced role, else None.

    REL-1 Guard 2: when a config pins ``force_role`` for a role-attributed
    measurement *with delegation disabled* and the orchestrator silently serves
    it from a DIFFERENT role (the 2026-07-21 circuit_open fallback
    ``worker_math → worker_general``), the number is not a measurement of the
    forced role. Compare ``force_role`` against the response's ``routed_to``
    (the primary role that handled the request), falling back to the terminal
    ``role_history`` entry when ``routed_to`` is absent. Returns ``None`` when
    ``force_role`` is empty or the serving role cannot be determined — avoiding
    false positives on partial/legacy responses.

    NOTE: callers MUST gate this on ``allow_delegation is False``. On the
    seeding path the ARCHITECT config runs with delegation ENABLED, where
    ``routed_to != force_role`` is the expected, correct behavior (the architect
    delegates to workers); applying this guard there would wrongly exclude every
    delegated result.
    """
    forced = str(force_role or "").strip()
    if not forced:
        return None
    serving = str(resp.get("routed_to") or "").strip()
    if not serving:
        history = resp.get("role_history")
        if isinstance(history, (list, tuple)) and history:
            serving = str(history[-1] or "").strip()
    if not serving or serving == forced:
        return None
    return serving


# ── Measurement disposition (INFRA-FAILED vs WRONG) ──────────────────
#
# 2026-08-03 incident: a T1 calibration reported `0% correct` over 70 questions
# purely because the orchestrator API was down. A score of 0.0 for an
# unreachable endpoint is a measurement that was NEVER MADE, reported as a
# measurement that was made and failed — the fail-open family
# (`feedback_fail_open_defaults_conceal_their_own_corruption`).
#
# The pre-existing classifier was a SUBSTRING match over the exception's
# `str()` (`INFRA_ERROR_PATTERNS` below). That is fail-open by construction:
# it must recognise a failure to exclude it, so every message it does not
# recognise silently becomes a wrong answer. Measured on the real code paths
# before this module existed:
#
#   HTTP 400  →  "Client error '400 Bad Request' for url ..."  → no pattern
#                matches ("server error" does, "client error" does not) →
#                scored WRONG.
#   ReadTimeout with an EMPTY message → `str(exc) == ""` → the error field is
#                falsy → the empty answer was scored against `expected` → WRONG.
#   Empty JSON body → "Expecting value: line 1 column 1" → no match → WRONG.
#
# The fix is to classify STRUCTURALLY — from the transport facts the caller
# already recorded (`failure_reason`, `failure_provenance.class`,
# `_meta.reason`, the HTTP status) — and to keep the substring list only as a
# last-resort fallback for legacy responses that carry none of them.

DISPOSITION_SCORED = "scored"
DISPOSITION_INFRA_FAILED = "infra_failed"
DISPOSITION_SCORING_FAILED = "scoring_failed"
DISPOSITION_TASK_FAILED = "task_failed"

# Dispositions that carry NO quality information about the role that served the
# request. They must be excluded from every quality denominator AND must never
# reach a reward writer: counting them as a failure is the fail-open this
# taxonomy exists to prevent.
NON_QUALITY_DISPOSITIONS = frozenset(
    {DISPOSITION_INFRA_FAILED, DISPOSITION_SCORING_FAILED}
)


def is_quality_admissible(disposition: Any) -> bool:
    """True iff a row carrying this disposition may enter a quality statistic.

    ONE predicate, because there were four coercers reading `correct` and none
    reading `disposition` — every one of them a place where an `infra_failed`
    row entered a paired test or an e-process as a WRONG ANSWER. Four literal
    membership tests would be four places to forget.

    An ABSENT / empty disposition is admissible: rows written before the
    taxonomy existed are `scored` by default, and flipping that default would
    silently empty every historical denominator.
    """
    text = "" if disposition is None else str(disposition).strip()
    return text not in NON_QUALITY_DISPOSITIONS

# The wire names under which the live-serving pipeline stamps a disposition onto
# a TASK_FAILED progress entry's `completion_meta`, so the asynchronous reward
# writer (`QScorer._score_task`, which sees only the progress trajectory) can
# refuse it. Defined HERE so the producer (src.api.services.memrl) and the
# consumer (orchestration.repl_memory.q_scorer) share one spelling — a literal
# duplicated across a process boundary is a silent-drift defect waiting to
# happen, and a guard that reads the wrong key passes vacuously.
FAILURE_DISPOSITION_KEY = "failure_disposition"
FAILURE_REASON_KEY = "failure_reason"

# Structural failure reasons that mean "no measurement was produced". The
# transport-level names are the vocabulary of `src.observability
# .classify_exception`; the rest are stamped by the eval/seeding callers.
INFRA_FAILURE_REASONS = frozenset(
    {
        # src.observability.classify_exception
        "connect_error",
        "connect_timeout",
        "read_timeout",
        "write_timeout",
        "pool_timeout",
        "socket_timeout",
        "timeout",
        "request_error",
        "http_status",
        "invalid_json",
        # stamped by seeding_orchestrator / eval_tower
        "api_unreachable_after_backoff",
        "deadline_starved",
        "forced_role_fallback",
        "inband_error",
        "empty_response",
        # ETR-3: text present, decode counter at zero — the answer did not come
        # from a generation, so there is nothing about the model to score.
        "answer_without_generation",
    }
)

# `failure_provenance["class"]` values (schema `epyc.failure_provenance.v1`)
# that mean the request never produced a scoreable answer.
INFRA_PROVENANCE_CLASSES = frozenset(
    {
        "client_transport_timeout",
        "admission_timeout",
        "admission_denied",
        "placement_timeout",
        "backend_request_rejected",
        "backend_timeout",
        "backend_failure",
        "circuit_open",
        "inband_error",
        "slot_erase_timeout",
    }
)

# Legacy substring fallback. Kept ONLY for responses that carry no structural
# signal at all (old journal rows, third-party callers). Never the primary
# test — see the module comment above for why a substring list fails open.
INFRA_ERROR_PATTERNS = (
    "timed out",
    "timeout",
    "connection",
    "refused",
    "unreachable",
    "502",
    "503",
    "504",
    "connecterror",
    "readtimeout",
    "backend down",
    "server error",
    "server disconnected without sending a response",
    "remoteprotocolerror",
    "connection reset",
    "broken pipe",
    "temporarily unavailable",
    "name or service not known",
    "circuit open",
    "backend unavailable",
    "deadline_starved",
    "forced_role_fallback",
)

_LEGACY_ERROR_TYPE = {
    DISPOSITION_SCORED: "none",
    DISPOSITION_INFRA_FAILED: "infrastructure",
    # A scorer that cannot produce a trustworthy verdict is an instrument
    # failure, not a model failure. The seeding path has always excluded it
    # under the "infrastructure" label; keep that mapping so its callers and
    # journals are unchanged while the finer disposition stays available.
    DISPOSITION_SCORING_FAILED: "infrastructure",
    DISPOSITION_TASK_FAILED: "task_failure",
}


def legacy_error_type(disposition: str) -> str:
    """Map a disposition onto the seeding path's legacy ``error_type`` string."""
    return _LEGACY_ERROR_TYPE.get(disposition, "task_failure")


def _http_status_of(resp: Mapping[str, Any]) -> int | None:
    """Best-effort HTTP status recorded on a response dict."""
    for key in ("http_status", "status_code", "error_code"):
        raw = resp.get(key)
        if raw is None or isinstance(raw, bool):
            continue
        try:
            code = int(raw)
        except (TypeError, ValueError):
            continue
        # `error_code` is sometimes an application code rather than an HTTP
        # status; only treat plausible HTTP statuses as such.
        if 100 <= code <= 599:
            return code
    return None


def infra_failure_reason(
    resp: Mapping[str, Any] | None = None,
    *,
    error: Any = None,
    require_generation_evidence: bool = False,
) -> str | None:
    """Return a structural reason this response is an INFRA FAILURE, else None.

    An infra failure means *the endpoint did not produce an answer to score* —
    it is the absence of a measurement, never a wrong one. Signals, in
    precedence order:

    1. ``failure_reason`` stamped by the caller (``api_unreachable_after_backoff``,
       ``deadline_starved``, ``inband_error``, a transport reason, …).
    2. ``failure_provenance["class"]`` (schema ``epyc.failure_provenance.v1``).
    3. ``_meta["reason"]`` from ``resilient_http.resilient_post``.
    4. A recorded HTTP status >= 400 — the server REFUSED the request. A per-slot
       context overflow returns 400; that is a capacity fact, not a quality one.
    5. An in-band ``[ERROR: ...]`` banner in the error text or the answer.
    6. ``empty_response``: a non-error reply with a blank answer AND zero
       generated tokens. Nothing was produced, so there is nothing to score.
    6b. ``answer_without_generation`` — ETR-3, only when
       ``require_generation_evidence`` is set: a NON-BLANK answer whose response
       reports a token counter of zero. The text did not come out of a decode, so
       it is the absence of a measurement (see the leg's comment below).
    7. Last resort only: the legacy substring heuristic over the error text.

    ``resp`` may be omitted to classify a bare error string (the legacy
    seeding call shape).

    ``require_generation_evidence`` is opt-in and OFF by default: MEASUREMENT
    callers (eval tower, seeding calibration) set it, because a row that cannot be
    attributed to a generation must leave the quality denominator. The live-serving
    reward path deliberately does NOT, so a genuine wrong answer keeps earning its
    negative reward even on a path that reports no fresh decode.
    """
    resp = resp if isinstance(resp, Mapping) else {}

    reason = str(resp.get("failure_reason") or "").strip().lower()
    if reason in INFRA_FAILURE_REASONS:
        return reason

    provenance = resp.get("failure_provenance")
    if isinstance(provenance, Mapping):
        klass = str(provenance.get("class") or "").strip().lower()
        if klass in INFRA_PROVENANCE_CLASSES:
            return klass

    meta = resp.get("_meta")
    if isinstance(meta, Mapping):
        meta_reason = str(meta.get("reason") or "").strip().lower()
        if meta_reason in INFRA_FAILURE_REASONS and not meta.get("clean"):
            return meta_reason

    status = _http_status_of(resp)
    if status is not None and status >= 400:
        return "http_status"

    error_text = "" if error is None else str(error)
    if inband_error_text(error_text) is not None:
        return "inband_error"
    if inband_error_text(resp.get("answer")) is not None:
        return "inband_error"

    if not error_text.strip():
        answer = resp.get("answer")
        answer_text = answer if isinstance(answer, str) else ""
        if "answer" in resp:
            try:
                tokens = int(resp.get("tokens_generated") or 0)
            except (TypeError, ValueError):
                tokens = 0
            if not answer_text.strip():
                if tokens <= 0:
                    # A blank answer with zero generated tokens is a non-event: the
                    # endpoint returned nothing at all. Scoring it against `expected`
                    # manufactures a WRONG verdict out of an absent measurement.
                    return "empty_response"
            elif (
                require_generation_evidence
                and "tokens_generated" in resp
                and tokens <= 0
                and not resp.get("mock_mode")
            ):
                # ETR-3 (2026-07-20 audit): the narrow silent-scoring hole. A
                # NON-BLANK answer with no error field and no other structural signal
                # used to return None and be scored as an ordinary wrong answer. The
                # structural fact available here is decisive: the response reports ZERO
                # generated tokens, so whatever text it carries did not come out of a
                # decode (a templated/echoed/stub body). That is the absence of a
                # measurement, not a wrong answer — the same class as `empty_response`,
                # whose blank-answer requirement is exactly why this shape slipped past.
                #
                # Deliberately narrow, and the residue is named: a non-blank answer WITH
                # a real token count is a genuine generation, so garbage there is the
                # model's own failure and stays scored WRONG. Mock-mode replies are
                # excluded because they legitimately report no decode.
                return "answer_without_generation"
        return None

    lowered = error_text.lower()
    # Several callers prefix the error with the reason itself
    # (`forced_role_fallback: ...`, `deadline_starved: ...`,
    # `api_unreachable_after_backoff: ...`, `infra_failed: ...`). Recover the
    # exact token so the aggregate's reason histogram stays specific instead of
    # collapsing every self-labelled failure into one bucket.
    head = lowered.split(":", 1)[0].strip()
    if head in INFRA_FAILURE_REASONS:
        return head
    if head == "infra_failed":
        tail = lowered.split(":", 1)[1].strip() if ":" in lowered else ""
        return tail.split()[0] if tail else "infra_failed"

    if any(pattern in lowered for pattern in INFRA_ERROR_PATTERNS):
        return "legacy_error_text_match"
    return None


def measurement_disposition(
    resp: Mapping[str, Any] | None = None,
    *,
    error: Any = None,
    scoring_failed: bool = False,
    require_generation_evidence: bool = False,
) -> str:
    """Classify one response into a measurement disposition.

    Returns one of ``scored`` / ``infra_failed`` / ``scoring_failed`` /
    ``task_failed``. ``infra_failed`` and ``scoring_failed`` rows carry NO
    quality information and must be excluded from every quality denominator —
    counting them as 0.0 is the fail-open this taxonomy exists to prevent.

    ``require_generation_evidence`` (ETR-3) is forwarded to
    ``infra_failure_reason``: set it on MEASUREMENT paths so a non-blank answer
    with a zero token counter is excluded instead of scored as a wrong answer.
    """
    # `scoring_failed` is a STRUCTURAL fact the caller already established (the
    # scorer raised ScoringUnavailableError / ValueError), so it is tested
    # first: routing it through the error-text heuristic would let a scorer
    # message that happens to contain "unreachable" be relabelled a transport
    # failure, losing the distinction between a broken instrument and a broken
    # endpoint.
    if scoring_failed:
        return DISPOSITION_SCORING_FAILED
    if (
        infra_failure_reason(
            resp, error=error, require_generation_evidence=require_generation_evidence
        )
        is not None
    ):
        return DISPOSITION_INFRA_FAILED
    if error is not None and str(error).strip():
        return DISPOSITION_TASK_FAILED
    return DISPOSITION_SCORED
