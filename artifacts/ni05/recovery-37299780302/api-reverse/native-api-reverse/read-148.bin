"""Role fields on ChatRequest must not accept free text.

`role` and `force_role` were bare `str` fields. A rescore of 117,074 historical
completions (2026-07-21) found client-supplied values reaching telemetry as
`producer_role`, including uppercase seeding labels (SELF, WORKER) and one row
containing a prompt fragment. Because `compute_reward` looks the role up in
`baseline_tps_by_role`, an unresolvable value skips every cost dimension and
scores the full base reward — so unvalidated input could suppress the cost
penalty entirely.
"""

from __future__ import annotations

from src.api.models.requests import ChatRequest


def _req(**kw) -> ChatRequest:
    return ChatRequest(prompt="hi", **kw)


def test_canonical_role_passes_through():
    assert _req(role="frontdoor").role == "frontdoor"


def test_empty_role_is_preserved_as_auto_route():
    assert _req().role == ""
    assert _req(role="").role == ""


def test_uppercase_seeding_labels_are_normalized_or_rejected():
    """SELF/WORKER came from 3-way seeding and are not canonical roles."""
    assert _req(role="WORKER").role != "WORKER"
    assert _req(role="SELF").role != "SELF"


def test_case_insensitive_match_is_normalized():
    assert _req(role="FrontDoor").role == "frontdoor"


def test_prompt_fragment_is_rejected_to_auto_route():
    """The exact shape observed in production telemetry."""
    leaked = "Provide full Python snippet with variable name."
    assert _req(role=leaked).role == ""


def test_force_role_is_validated_too():
    assert _req(force_role="Provide full Python snippet.").force_role == ""
    assert _req(force_role="architect_general").force_role == "architect_general"


def test_non_role_pipeline_sentinels_pass_through():
    """'mock' is a real wire value for the mock pipeline; do not rewrite it."""
    assert _req(role="mock").role == "mock"


def test_every_role_value_used_by_production_harnesses_survives():
    """Blast-radius guard: real force_role values from live harnesses.

    Enumerated from reviewer_corpus_ledger_run.py, reviewer_policy_arm_ab.py,
    validate_compaction_live.py, calibrate_timeouts.py and the
    memory_viability_runner. Includes the legacy aliases (reviewer,
    reviewer_agent, architect_coding) that Role._missing_ resolves. If this
    fails, the validator is too strict and will break live tooling.
    """
    for value in (
        "frontdoor",
        "architect_general",
        "worker_general",
        "coder_escalation",
        "ingest_long_context",
        "worker_vision",
        "reviewer",
        "reviewer_agent",
        "architect_coding",
        "mock",
    ):
        assert _req(role=value).role == value, value
        assert _req(force_role=value).force_role == value, value


def test_invalid_force_role_no_longer_suppresses_background_scoring():
    """Documented behaviour change found via call-site analysis.

    src/api/services/memrl.py:221 skips background scoring when
    `bool(force_role) and bool(real_mode)`. Rewriting an invalid force_role to
    "" flips it truthy -> falsy, so a bogus value no longer suppresses scoring.
    That is the correct outcome — the request auto-routes, so it should be
    scored like any other — but it IS a change, and this test pins it.
    """
    from src.api.services.memrl import should_skip_background_scoring

    bogus = _req(force_role="Provide full Python snippet.").force_role
    assert bogus == ""
    assert should_skip_background_scoring(force_role=bogus, real_mode=True) is False

    valid = _req(force_role="frontdoor").force_role
    assert should_skip_background_scoring(force_role=valid, real_mode=True) is True
