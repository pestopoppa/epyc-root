"""Tests for TD-21.4/TD-21.5: architect delegation decision repair.

TD-21.4 (`resolve_architect_decision`, `_parse_architect_decision(strict=True)`)
closes the worst silent default on a serving path: unparsed architect prose
used to be wrapped as `D|<prose>` and served to the user with no failure mode,
and an unrecognized `delegate_to`/`delegate_mode` was silently clamped to a
default. TD-21.5 converts the MCQ-misroute re-prompt's letter recovery
(`_apply_decision_guards`) from a raw regex with no failure mode into the same
fish-then-repair shape, enum-constrained to A-D.

Covers: happy path is byte-identical and costs zero extra calls; unparsable
prose is repaired instead of leaked; a schema-invalid role/mode from the
repair turn is never silently clamped; repair failure surfaces a typed
failure via the existing `[ERROR: ...]` sentinel (long prose) or a verbatim
short answer (short prose); the TD-21.5 MCQ letter repair and its safe
keep-prior-decision fallback; the (site, status) counters.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.api.routes.chat_delegation_decision import (
    _apply_decision_guards,
    _parse_architect_decision,
    resolve_architect_decision,
)
from src.structured_output.repair import (
    STRUCTURED_OUTPUT_REPAIR_COUNTS,
    reset_counts_for_tests,
)


@pytest.fixture(autouse=True)
def _clear_counts():
    reset_counts_for_tests()
    yield
    reset_counts_for_tests()


def _primitives(*llm_call_results):
    """A MagicMock LLMPrimitives whose llm_call returns/raises in sequence."""
    primitives = MagicMock()
    primitives.llm_call = MagicMock(side_effect=list(llm_call_results))
    return primitives


# --------------------------------------------------------------------------- strict parse (TD-21.4 core)


class TestParseArchitectDecisionStrict:
    """`_parse_architect_decision(strict=True)` refuses to guess; `strict=False`
    (the default, every pre-existing call site) is completely unaffected."""

    def test_strict_clean_toon_direct_matches_non_strict(self):
        loose = _parse_architect_decision("D|The answer is 42")
        strict = _parse_architect_decision("D|The answer is 42", strict=True)
        assert strict == loose

    def test_strict_clean_toon_investigate_matches_non_strict(self):
        text = "I|brief:Check src/api.py|to:coder_escalation|mode:repl"
        assert _parse_architect_decision(text, strict=True) == _parse_architect_decision(text)

    def test_strict_long_unrescuable_d_answer_returns_none(self):
        # >50 chars, no MCQ-rescue pattern anywhere in it.
        long_text = "D|" + ("this is long reasoning prose with no clear letter " * 3)
        assert _parse_architect_decision(long_text, strict=True) is None
        # Non-strict callers keep today's best-effort behaviour unchanged.
        loose = _parse_architect_decision(long_text)
        assert loose["mode"] == "direct"
        assert loose["answer"] == long_text[2:].strip()

    def test_strict_invalid_role_returns_none_not_clamped(self):
        text = "I|brief:Check something|to:totally_made_up_role"
        assert _parse_architect_decision(text, strict=True) is None
        # Non-strict still clamps (unchanged legacy behaviour).
        loose = _parse_architect_decision(text)
        assert loose["delegate_to"] == "coder_escalation"

    def test_strict_invalid_mode_returns_none_not_clamped(self):
        text = "I|brief:Check something|to:coder_escalation|mode:bogus"
        assert _parse_architect_decision(text, strict=True) is None
        loose = _parse_architect_decision(text)
        assert loose["delegate_mode"] == "react"

    def test_strict_invalid_role_in_json_returns_none(self):
        payload = json.dumps({"mode": "investigate", "brief": "x", "delegate_to": "nope"})
        assert _parse_architect_decision(payload, strict=True) is None

    def test_strict_bare_prose_returns_none(self):
        assert _parse_architect_decision("Just a plain text answer with no format", strict=True) is None
        # Non-strict keeps the legacy bare-text fallback (used by other,
        # out-of-scope call sites that still call `_parse_architect_decision`
        # directly, e.g. the MCQ misroute guard's own forced-decision parse).
        loose = _parse_architect_decision("Just a plain text answer with no format")
        assert loose == {
            "mode": "direct",
            "answer": "Just a plain text answer with no format",
            "brief": "",
            "delegate_to": "",
            "delegate_mode": "react",
        }


# --------------------------------------------------------------------------- resolve_architect_decision


class TestResolveArchitectDecisionHappyPath:
    """Clean parses cost zero repair calls and return exactly what
    `_parse_architect_decision` always returned."""

    def test_clean_direct_no_llm_call(self):
        primitives = _primitives()
        decision = resolve_architect_decision(
            "D|B", primitives=primitives, architect_role="architect_general",
        )
        assert decision == _parse_architect_decision("D|B")
        primitives.llm_call.assert_not_called()

    def test_clean_investigate_no_llm_call(self):
        primitives = _primitives()
        text = "I|brief:Check src/api.py for error handling|to:coder_escalation"
        decision = resolve_architect_decision(
            text, primitives=primitives, architect_role="architect_general",
        )
        assert decision == _parse_architect_decision(text)
        primitives.llm_call.assert_not_called()


class TestResolveArchitectDecisionRepairsUnparsablePose:
    """The core TD-21.4 fix: prose that used to be silently wrapped as
    `D|<prose>` now gets ONE repair turn instead."""

    def test_unparsable_prose_is_repaired_not_leaked_verbatim(self):
        prose = (
            "Well, thinking about this carefully, I believe the best course "
            "of action here is to look deeper into the codebase before "
            "committing to any particular answer, since the situation is "
            "genuinely ambiguous and warrants further investigation."
        )
        repaired_json = json.dumps(
            {
                "mode": "investigate",
                "answer": "",
                "brief": "Look deeper into the codebase",
                "delegate_to": "worker_general",
                "delegate_mode": "react",
            }
        )
        primitives = _primitives(repaired_json)
        decision = resolve_architect_decision(
            prose, primitives=primitives, architect_role="architect_general",
        )
        assert decision["mode"] == "investigate"
        assert decision["delegate_to"] == "worker_general"
        assert decision["brief"] == "Look deeper into the codebase"
        # The old bug: the decision's answer/brief must never just BE the raw prose.
        assert decision.get("answer") != prose
        assert decision.get("brief") != prose
        primitives.llm_call.assert_called_once()
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[
            ("chat_delegation.architect_decision", "repaired")
        ] == 1

    def test_repaired_direct_answer_extracted_from_prose(self):
        prose = (
            "After much deliberation and careful cross-checking of the "
            "relevant facts, I am confident the correct value here is 42, "
            "which follows directly from the computation above."
        )
        repaired_json = json.dumps(
            {"mode": "direct", "answer": "42", "brief": "", "delegate_to": "", "delegate_mode": "react"}
        )
        primitives = _primitives(repaired_json)
        decision = resolve_architect_decision(
            prose, primitives=primitives, architect_role="architect_general",
        )
        assert decision == {
            "mode": "direct", "answer": "42", "brief": "", "delegate_to": "", "delegate_mode": "react",
        }


class TestResolveArchitectDecisionNeverClampsInvalidRole:
    """A repair turn that comes back with an off-allowlist role/mode is a
    schema-validation FAILURE, never a value that gets silently clamped."""

    def test_invalid_role_from_repair_turn_is_not_clamped(self):
        prose = "x" * 80  # long enough to bypass the short-answer fallback
        bad_json = json.dumps(
            {
                "mode": "investigate",
                "answer": "",
                "brief": "do something",
                "delegate_to": "made_up_role_not_in_allowlist",
                "delegate_mode": "react",
            }
        )
        primitives = _primitives(bad_json)
        decision = resolve_architect_decision(
            prose, primitives=primitives, architect_role="architect_general",
        )
        # Must NOT be a silently-clamped investigate decision at all --
        # schema `enum` rejected the value, so this is a "failed" repair.
        assert decision["delegate_to"] != "made_up_role_not_in_allowlist"
        assert decision["mode"] == "direct"
        assert decision["answer"].startswith("[ERROR:")
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[
            ("chat_delegation.architect_decision", "failed")
        ] == 1

    def test_invalid_delegate_mode_from_repair_turn_is_not_clamped(self):
        prose = "y" * 80
        bad_json = json.dumps(
            {
                "mode": "investigate",
                "answer": "",
                "brief": "do something",
                "delegate_to": "coder_escalation",
                "delegate_mode": "not_a_real_mode",
            }
        )
        primitives = _primitives(bad_json)
        decision = resolve_architect_decision(
            prose, primitives=primitives, architect_role="architect_general",
        )
        assert decision["answer"].startswith("[ERROR:")


class TestResolveArchitectDecisionFailurePath:
    """Repair failure (transport error or unrecoverable extraction) is a
    TYPED failure the caller must handle explicitly -- never a silent
    default, and never the raw prose re-served as the answer."""

    def test_long_prose_transport_failure_surfaces_typed_error(self):
        long_prose = "z " * 60  # >50 chars once stripped
        primitives = _primitives(RuntimeError("connection refused"))
        decision = resolve_architect_decision(
            long_prose, primitives=primitives, architect_role="architect_general",
        )
        assert decision["mode"] == "direct"
        assert decision["answer"].startswith("[ERROR:")
        # The old bug is specifically this: raw prose must never be served
        # verbatim as the answer on a failure path.
        assert decision["answer"] != long_prose.strip()
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[
            ("chat_delegation.architect_decision", "failed")
        ] == 1

    def test_short_prose_failure_is_treated_as_plausible_direct_answer(self):
        # <=50 chars: same threshold `_parse_architect_decision` already
        # uses to decide a D| answer is NOT "suspiciously long" reasoning.
        short = "42"
        primitives = _primitives(RuntimeError("connection refused"))
        decision = resolve_architect_decision(
            short, primitives=primitives, architect_role="architect_general",
        )
        assert decision == {
            "mode": "direct", "answer": "42", "brief": "", "delegate_to": "", "delegate_mode": "react",
        }

    def test_extraction_turn_returning_garbage_is_a_typed_failure(self):
        long_prose = "not json at all, just more reasoning " * 3
        primitives = _primitives("still not json, sorry")
        decision = resolve_architect_decision(
            long_prose, primitives=primitives, architect_role="architect_general",
        )
        assert decision["answer"].startswith("[ERROR:")


# --------------------------------------------------------------------------- TD-21.5: MCQ letter re-prompt


class TestMcqMisrouteLetterRepair:
    MCQ_QUESTION = (
        "What is the capital of France?\n"
        "A) London\nB) Paris\nC) Berlin\nD) Madrid\n"
    )

    def _investigate_decision(self):
        return {
            "mode": "investigate",
            "answer": "",
            "brief": "look up the capital",
            "delegate_to": "worker_general",
            "delegate_mode": "react",
        }

    def test_fish_still_wins_when_clean(self):
        """Cheap regex/TOON fish unchanged: a clean forced D|<letter> never
        spends a repair call."""
        primitives = _primitives("D|B")
        decision = _apply_decision_guards(
            self._investigate_decision(), self.MCQ_QUESTION, 0, primitives, "architect_general",
        )
        assert decision["mode"] == "direct"
        assert decision["answer"] == "B"
        primitives.llm_call.assert_called_once()  # only the force_prompt call

    def test_regex_fish_wins_over_repair(self):
        """A bare letter in the reply is caught by the existing cheap regex
        without spending the repair turn."""
        primitives = _primitives("The answer is B, I'm confident.")
        decision = _apply_decision_guards(
            self._investigate_decision(), self.MCQ_QUESTION, 0, primitives, "architect_general",
        )
        assert decision["answer"] == "B"
        primitives.llm_call.assert_called_once()

    def test_repair_recovers_when_fish_misses(self):
        """No D| and no bare A-D letter anywhere -- native-enum repair turn
        recovers it."""
        forced_reply = (
            "I believe the correct option here is the one referring to the "
            "city on the Seine, which most people would recognize easily."
        )
        primitives = _primitives(forced_reply, json.dumps({"letter": "B"}))
        decision = _apply_decision_guards(
            self._investigate_decision(), self.MCQ_QUESTION, 0, primitives, "architect_general",
        )
        assert decision["mode"] == "direct"
        assert decision["answer"] == "B"
        assert primitives.llm_call.call_count == 2
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[
            ("chat_delegation_decision.mcq_misroute_letter", "repaired")
        ] == 1

    def test_repair_failure_keeps_prior_decision_safely(self):
        """When even the repair turn can't recover a letter, the guard keeps
        the previously-parsed (schema-valid) decision rather than fabricate
        a value -- documented, safe fallback, unlike TD-21.4's prose leak."""
        forced_reply = "I cannot determine a single letter from this."
        prior = self._investigate_decision()
        primitives = _primitives(forced_reply, RuntimeError("connection refused"))
        decision = _apply_decision_guards(
            prior, self.MCQ_QUESTION, 0, primitives, "architect_general",
        )
        assert decision == prior
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[
            ("chat_delegation_decision.mcq_misroute_letter", "failed")
        ] == 1
