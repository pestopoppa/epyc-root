"""Tests for the shared structured-output repair helper (TD-21).

Covers: `fish_json` extraction edge cases, the `parse_with_repair` state
machine (parsed / declined / repaired / failed paths, TD-21.30(b) partial
objects, never-fabricates-a-value), the `http_chat_completer` wire payload
shape, the (site, status) telemetry counter, and (TD-21.35) the wire-schema
`required`-relaxation that stops the extraction grammar from FORCING a value
for a field the raw reply never stated.
"""

from __future__ import annotations

import copy
import json
from unittest.mock import MagicMock, patch

import pytest

from src.structured_output.repair import (
    STRUCTURED_OUTPUT_REPAIR_COUNTS,
    RepairResult,
    _relax_required_for_wire,
    fish_json,
    http_chat_completer,
    parse_with_repair,
    parse_with_repair_async,
    primitives_completer,
    reset_counts_for_tests,
)


@pytest.fixture(autouse=True)
def _clear_counts():
    reset_counts_for_tests()
    yield
    reset_counts_for_tests()


# --------------------------------------------------------------------------- fish_json


class TestFishJson:
    def test_fenced_json_block(self):
        text = 'Here you go:\n```json\n{"a": 1, "b": 2}\n```\nThanks.'
        assert fish_json(text) == {"a": 1, "b": 2}

    def test_bare_fence_no_language_tag(self):
        text = 'Result:\n```\n{"a": 1}\n```'
        assert fish_json(text) == {"a": 1}

    def test_prose_around_json_no_fence(self):
        text = "The answer, after some thought, is {\"x\": 1} and that's final."
        assert fish_json(text) == {"x": 1}

    def test_nested_braces_in_strings_do_not_break_depth(self):
        text = '{"a": "value with } a brace and { another", "b": 2}'
        assert fish_json(text) == {"a": "value with } a brace and { another", "b": 2}

    def test_escaped_quote_inside_string_does_not_end_string_early(self):
        text = r'{"a": "she said \"hi\" to } me", "b": 3}'
        value = fish_json(text)
        assert value == {"a": 'she said "hi" to } me', "b": 3}

    def test_last_object_wins(self):
        text = '{"a": 1} some text in between {"a": 2}'
        assert fish_json(text) == {"a": 2}

    def test_array_kind(self):
        text = 'Items: [1, 2, 3] done.'
        assert fish_json(text, kind="array") == [1, 2, 3]

    def test_array_kind_rejects_object(self):
        text = '{"a": 1}'
        assert fish_json(text, kind="array") is None

    def test_object_kind_rejects_array(self):
        text = "[1, 2, 3]"
        assert fish_json(text, kind="object") is None

    def test_any_kind_accepts_either(self):
        assert fish_json("[1, 2]", kind="any") == [1, 2]
        assert fish_json('{"a": 1}', kind="any") == {"a": 1}

    def test_garbage_returns_none(self):
        assert fish_json("this is not json at all, sorry") is None

    def test_empty_string_returns_none(self):
        assert fish_json("") is None

    def test_never_raises_on_malformed_input(self):
        # unterminated string, dangling braces, mixed junk
        assert fish_json('{"a": "unterminated, {[[[') is None

    def test_truncated_fenced_block_repaired_via_existing_repair_idiom(self):
        # A fenced block is handed to `_repair_json_text` even when its own
        # brackets are not balanced (the fence delimiters, not brace-matching,
        # define its span) -- this is exactly the truncated-generation shape
        # `_repair_json_text`'s trailing-comma + missing-closer path targets.
        text = 'Here:\n```json\n{"a": 1, "b": 2,\n```\nend'
        assert fish_json(text) == {"a": 1, "b": 2}

    def test_fence_preferred_over_looser_balanced_match_elsewhere(self):
        text = (
            'noise {"stale": true} more noise\n'
            '```json\n{"fresh": true}\n```\n'
            'trailing {"also_stale": true}'
        )
        # fenced block wins even though it isn't the textually-last balanced span
        assert fish_json(text) == {"fresh": True}

    def test_nested_object_inside_top_level_array(self):
        text = '[{"a": 1}, {"b": 2}]'
        assert fish_json(text, kind="array") == [{"a": 1}, {"b": 2}]


# --------------------------------------------------------------------------- parse_with_repair: parsed path


SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
    "required": ["name", "count"],
}


class TestParsedPath:
    def test_clean_json_parses_with_zero_calls(self):
        complete = MagicMock(side_effect=AssertionError("must not be called"))
        result = parse_with_repair(
            'Reply: {"name": "widget", "count": 3}',
            schema=SIMPLE_SCHEMA,
            complete=complete,
            site="test.parsed",
        )
        assert result.status == "parsed"
        assert result.value == {"name": "widget", "count": 3}
        assert result.repair_calls == 0
        assert result.reason == ""
        complete.assert_not_called()
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[("test.parsed", "parsed")] == 1

    def test_additional_properties_defaulted_closed_rejects_extra_key(self):
        # No additionalProperties on SIMPLE_SCHEMA; TD-21.30(d) closes it, so
        # an extra key on the fished object should NOT be accepted as "parsed"
        # (falls through to repair, which then fails with no completer help).
        def complete(messages, schema):
            raise RuntimeError("no local server in this test")

        result = parse_with_repair(
            'Reply: {"name": "widget", "count": 3, "extra": "nope"}',
            schema=SIMPLE_SCHEMA,
            complete=complete,
            site="test.closed",
        )
        assert result.status == "failed"
        assert result.value is None


# --------------------------------------------------------------------------- TD-21.30(b): partial/wrong-type objects


class TestPartialObjectGoesToRepair:
    def test_wrong_type_required_field_is_not_accepted_as_parsed(self):
        # `count` is present (so a naive "required keys covered" check would
        # accept this) but has the WRONG TYPE -- TD-21.30(b) requires full
        # schema validation, so this must NOT short-circuit as "parsed".
        raw = 'Reply: {"name": "widget", "count": "three"}'

        def complete(messages, schema):
            return json.dumps({"name": "widget", "count": 3})

        result = parse_with_repair(raw, schema=SIMPLE_SCHEMA, complete=complete, site="test.b")
        assert result.status == "repaired"
        assert result.value == {"name": "widget", "count": 3}
        assert result.repair_calls == 1

    def test_missing_required_field_goes_to_repair(self):
        raw = 'Reply: {"name": "widget"}'

        def complete(messages, schema):
            return json.dumps({"name": "widget", "count": 7})

        result = parse_with_repair(raw, schema=SIMPLE_SCHEMA, complete=complete, site="test.b2")
        assert result.status == "repaired"
        assert result.value == {"name": "widget", "count": 7}


# --------------------------------------------------------------------------- decline path


DECLINE_SCHEMA = {
    "type": "object",
    "properties": {"mechanism_id": {"type": "string"}},
    "required": ["mechanism_id"],
    "additionalProperties": False,
}


class TestDeclinePath:
    def test_explicit_decline_returns_declined_and_never_extracts(self):
        raw = "I looked into this but found nothing worth proposing; I decline to submit a hypothesis."
        calls = []

        def complete(messages, schema):
            calls.append(schema)
            # First call is the decline probe; must never be asked twice for
            # extraction after an explicit decline.
            return json.dumps({"explicitly_declines": True, "reason": "found nothing"})

        result = parse_with_repair(
            raw,
            schema=DECLINE_SCHEMA,
            complete=complete,
            decline_question="Does the report explicitly decline to propose anything?",
            site="test.decline",
        )
        assert result.status == "declined"
        assert result.value is None
        assert result.reason == "found nothing"
        assert result.repair_calls == 1
        assert len(calls) == 1  # extraction never invoked

    def test_non_decline_falls_through_to_extraction(self):
        raw = "I propose renaming the buffer to widen alignment."

        def complete(messages, schema):
            if schema.get("properties", {}).get("explicitly_declines"):
                return json.dumps({"explicitly_declines": False, "reason": ""})
            return json.dumps({"mechanism_id": "widen-alignment"})

        result = parse_with_repair(
            raw,
            schema=DECLINE_SCHEMA,
            complete=complete,
            decline_question="Does the report explicitly decline to propose anything?",
            site="test.decline2",
        )
        assert result.status == "repaired"
        assert result.value == {"mechanism_id": "widen-alignment"}
        assert result.repair_calls == 2


# --------------------------------------------------------------------------- failure paths


class TestFailurePaths:
    def test_bad_json_from_extraction_turn_fails_without_fabricating(self):
        def complete(messages, schema):
            return "not json at all"

        result = parse_with_repair("garbage garbage", schema=SIMPLE_SCHEMA, complete=complete, site="test.f1")
        assert result.status == "failed"
        assert result.value is None
        assert "no parseable JSON" in result.reason

    def test_schema_invalid_extraction_result_fails(self):
        def complete(messages, schema):
            return json.dumps({"name": "widget"})  # missing required `count`

        result = parse_with_repair("garbage garbage", schema=SIMPLE_SCHEMA, complete=complete, site="test.f2")
        assert result.status == "failed"
        assert result.value is None

    def test_transport_exception_is_caught_and_typed_as_failed(self):
        def complete(messages, schema):
            raise ConnectionError("server unreachable")

        result = parse_with_repair("garbage garbage", schema=SIMPLE_SCHEMA, complete=complete, site="test.f3")
        assert result.status == "failed"
        assert result.value is None
        assert "transport_error" in result.reason
        assert "ConnectionError" in result.reason

    def test_never_returns_fabricated_default_value(self):
        def complete(messages, schema):
            raise TimeoutError("timed out")

        result = parse_with_repair("garbage", schema=SIMPLE_SCHEMA, complete=complete, site="test.f4")
        assert result.value is None  # never {} or a partial guess


# --------------------------------------------------------------------------- counters


class TestCounters:
    def test_counters_increment_per_site_and_status(self):
        def ok_complete(messages, schema):
            return json.dumps({"name": "w", "count": 1})

        parse_with_repair('{"name": "w", "count": 1}', schema=SIMPLE_SCHEMA, complete=ok_complete, site="site.a")
        parse_with_repair("garbage", schema=SIMPLE_SCHEMA, complete=ok_complete, site="site.a")
        parse_with_repair("garbage", schema=SIMPLE_SCHEMA, complete=ok_complete, site="site.b")

        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[("site.a", "parsed")] == 1
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[("site.a", "repaired")] == 1
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[("site.b", "repaired")] == 1


# --------------------------------------------------------------------------- http_chat_completer wire shape


class TestHttpChatCompleter:
    def test_payload_shape(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(
                    {"choices": [{"message": {"content": '{"ok": true}'}}]}
                ).encode("utf-8")

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with patch("src.structured_output.repair.urllib.request.urlopen", side_effect=fake_urlopen):
            complete = http_chat_completer("http://127.0.0.1:8083/v1", model="qwen3.8-27b", timeout_s=42)
            content = complete(
                [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}],
                SIMPLE_SCHEMA,
            )

        assert content == '{"ok": true}'
        assert captured["url"] == "http://127.0.0.1:8083/v1/chat/completions"
        assert captured["timeout"] == 42
        body = captured["body"]
        assert body["temperature"] == 0
        assert body["chat_template_kwargs"] == {"enable_thinking": False}
        assert body["model"] == "qwen3.8-27b"
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["schema"] == SIMPLE_SCHEMA
        assert body["messages"][0]["content"] == "sys"
        assert body["messages"][1]["content"] == "usr"

    def test_model_omitted_when_not_given(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(
                    {"choices": [{"message": {"content": "{}"}}]}
                ).encode("utf-8")

        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with patch("src.structured_output.repair.urllib.request.urlopen", side_effect=fake_urlopen):
            complete = http_chat_completer("http://127.0.0.1:8083")
            complete([{"role": "user", "content": "hi"}], SIMPLE_SCHEMA)

        assert "model" not in captured["body"]

    def test_transport_error_propagates_to_caller(self):
        import urllib.error

        def fake_urlopen(request, timeout=None):
            raise urllib.error.URLError("connection refused")

        with patch("src.structured_output.repair.urllib.request.urlopen", side_effect=fake_urlopen):
            complete = http_chat_completer("http://127.0.0.1:8083")
            with pytest.raises(urllib.error.URLError):
                complete([{"role": "user", "content": "hi"}], SIMPLE_SCHEMA)


# --------------------------------------------------------------------------- primitives_completer


class TestPrimitivesCompleter:
    def test_renders_messages_into_a_single_prompt_and_forwards_kwargs(self):
        primitives = MagicMock()
        primitives.llm_call.return_value = '{"ok": true}'

        complete = primitives_completer(primitives, role="worker")
        content = complete(
            [{"role": "system", "content": "sys line"}, {"role": "user", "content": "usr line"}],
            SIMPLE_SCHEMA,
        )

        assert content == '{"ok": true}'
        primitives.llm_call.assert_called_once()
        args, kwargs = primitives.llm_call.call_args
        prompt = args[0]
        assert "sys line" in prompt
        assert "usr line" in prompt
        assert kwargs["role"] == "worker"
        assert kwargs["json_schema"] == SIMPLE_SCHEMA
        assert kwargs["temperature"] == 0.0
        assert kwargs["skip_suffix"] is True

    def test_transport_exception_from_llm_call_propagates(self):
        primitives = MagicMock()
        primitives.llm_call.side_effect = RuntimeError("backend down")

        complete = primitives_completer(primitives, role="worker")
        with pytest.raises(RuntimeError):
            complete([{"role": "user", "content": "hi"}], SIMPLE_SCHEMA)


# --------------------------------------------------------------------------- integration: parse_with_repair + primitives_completer


class TestParseWithRepairUsesInjectedCompleter:
    def test_full_pipeline_with_primitives_completer(self):
        primitives = MagicMock()
        primitives.llm_call.return_value = json.dumps({"name": "widget", "count": 5})

        complete = primitives_completer(primitives, role="worker")
        result = parse_with_repair(
            "some unparseable prose about a widget",
            schema=SIMPLE_SCHEMA,
            complete=complete,
            site="test.integration",
        )
        assert result.status == "repaired"
        assert result.value == {"name": "widget", "count": 5}


# --------------------------------------------------------------------------- require_evidence
#
# 2026-09-24 live-smoke finding: a grammar that forces a required field
# forces the model to fill it even when the raw reply never states one -- a
# `deep_eval` draft with no stated tier repaired to a fabricated `tier=2`
# that would have driven a real autopilot action. `require_evidence` closes
# that gap for a REPAIRED (never a cleanly fished) value.


ACTION_LIKE_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"const": "deep_eval"},
                "tier": {"enum": [0, 1, 2, 3]},
            },
            "required": ["type"],
            "additionalProperties": False,
        }
    ],
}


class TestRequireEvidence:
    def test_invented_number_fails_even_though_schema_valid(self):
        def complete(messages, schema):
            return json.dumps({"type": "deep_eval", "tier": 2})

        result = parse_with_repair(
            "The architect's quality has plateaued; time for another evaluation round.",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.evidence.invented",
            require_evidence=True,
        )
        assert result.status == "failed"
        assert result.value is None  # never a fabricated tier
        assert "tier" in result.reason

    def test_value_present_in_text_is_repaired(self):
        def complete(messages, schema):
            return json.dumps({"type": "deep_eval", "tier": 1})

        result = parse_with_repair(
            "The architect's quality has plateaued; run a deep_eval at tier 1.",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.evidence.present",
            require_evidence=True,
        )
        assert result.status == "repaired"
        assert result.value == {"type": "deep_eval", "tier": 1}

    def test_const_discriminator_is_exempt_from_evidence(self):
        # "deep_eval" never appears verbatim in the raw text -- only its
        # const-pinned schema position (the `type` field) exempts it.
        def complete(messages, schema):
            return json.dumps({"type": "deep_eval", "tier": 1})

        result = parse_with_repair(
            "run another eval round at tier 1, quality has plateaued",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.evidence.const",
            require_evidence=True,
        )
        assert result.status == "repaired"
        assert result.value == {"type": "deep_eval", "tier": 1}

    def test_long_string_is_exempt_from_evidence(self):
        schema = {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        }
        long_value = "a paraphrased summary well over forty characters long"
        assert len(long_value) > 40

        def complete(messages, schema):
            return json.dumps({"summary": long_value})

        result = parse_with_repair(
            "totally unrelated raw text carrying none of that wording",
            schema=schema,
            complete=complete,
            site="test.evidence.longstring",
            require_evidence=True,
        )
        assert result.status == "repaired"
        assert result.value == {"summary": long_value}

    def test_boolean_is_exempt_from_evidence(self):
        schema = {
            "type": "object",
            "properties": {"flagged": {"type": "boolean"}},
            "required": ["flagged"],
        }

        def complete(messages, schema):
            return json.dumps({"flagged": True})

        result = parse_with_repair(
            "no boolean mentioned anywhere in this text at all",
            schema=schema,
            complete=complete,
            site="test.evidence.bool",
            require_evidence=True,
        )
        assert result.status == "repaired"
        assert result.value == {"flagged": True}

    def test_short_string_without_evidence_fails(self):
        schema = {
            "type": "object",
            "properties": {"surface": {"type": "string"}},
            "required": ["surface"],
        }

        def complete(messages, schema):
            return json.dumps({"surface": "memrl_retrieval"})

        result = parse_with_repair(
            "run a numeric trial next on some surface",
            schema=schema,
            complete=complete,
            site="test.evidence.shortstring",
            require_evidence=True,
        )
        assert result.status == "failed"
        assert result.value is None
        assert "surface" in result.reason

    def test_default_false_keeps_prior_behavior_byte_identical(self):
        def complete(messages, schema):
            return json.dumps({"type": "deep_eval", "tier": 2})

        result = parse_with_repair(
            "The architect's quality has plateaued; time for another evaluation round.",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.evidence.default_off",
        )
        assert result.status == "repaired"
        assert result.value == {"type": "deep_eval", "tier": 2}


# --------------------------------------------------------------------------- evidence_exempt
#
# TD-21.34: a mixed schema pairs literal facts the model must copy (an
# invented one is the exact fabrication `require_evidence` targets) with
# CLASSIFICATION leaves the model legitimately maps prose onto (an `enum`
# the raw text rarely spells verbatim -- unlike `const`, `enum` is NOT
# auto-exempt). `evidence_exempt` lets a site turn `require_evidence` on for
# the whole schema while still naming the classification keys out.

MIXED_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {"type": "string", "enum": ["direct", "investigate"]},
        "brief": {"type": "string"},
    },
    "required": ["mode", "brief"],
    "additionalProperties": False,
}


class TestEvidenceExempt:
    def test_exempt_key_skips_evidence_even_when_absent_from_reply(self):
        # "investigate" never appears in the raw text -- only `evidence_exempt`
        # keeps the classification leaf from failing the check.
        def complete(messages, schema):
            return json.dumps({"mode": "investigate", "brief": "check the disk usage report"})

        result = parse_with_repair(
            "please check the disk usage report",
            schema=MIXED_DECISION_SCHEMA,
            complete=complete,
            site="test.evidence_exempt.mode",
            require_evidence=True,
            evidence_exempt={"mode"},
        )
        assert result.status == "repaired"
        assert result.value == {"mode": "investigate", "brief": "check the disk usage report"}

    def test_non_exempt_sibling_still_evidence_checked(self):
        # `mode` is exempt but `brief` is invented wholesale -- the guard must
        # still catch the non-exempt leaf.
        def complete(messages, schema):
            return json.dumps({"mode": "investigate", "brief": "a wholly invented brief"})

        result = parse_with_repair(
            "please check the disk usage report",
            schema=MIXED_DECISION_SCHEMA,
            complete=complete,
            site="test.evidence_exempt.sibling",
            require_evidence=True,
            evidence_exempt={"mode"},
        )
        assert result.status == "failed"
        assert result.value is None
        assert "brief" in result.reason

    def test_dotted_path_exempts_only_that_position(self):
        schema = {
            "type": "object",
            "properties": {
                "verifier": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "reference": {"type": "string"},
                    },
                },
            },
            "required": ["verifier"],
        }

        def complete(messages, schema):
            return json.dumps({"verifier": {"type": "exact_match", "reference": "42"}})

        # "exact_match" is nowhere in the raw text but "verifier.type" is
        # exempt; "42" (the reference) IS in the raw text so the sibling
        # leaf is evidenced.
        result = parse_with_repair(
            "the tool should return 42",
            schema=schema,
            complete=complete,
            site="test.evidence_exempt.dotted",
            require_evidence=True,
            evidence_exempt={"verifier.type"},
        )
        assert result.status == "repaired"
        assert result.value == {"verifier": {"type": "exact_match", "reference": "42"}}


# --------------------------------------------------------------------------- require_evidence (async)
#
# TD-21.34: `parse_with_repair_async` originally had no `require_evidence`/
# `evidence_exempt` parameters at all -- an async call site (env_synth's
# `etd_agent.py` / `task_synthesizer.py`) could not get the evidence guard.
# Mirrors `TestRequireEvidence` exactly, over the async twin.


class TestRequireEvidenceAsync:
    async def test_invented_number_fails_even_though_schema_valid(self):
        async def complete(messages, schema):
            return json.dumps({"type": "deep_eval", "tier": 2})

        result = await parse_with_repair_async(
            "The architect's quality has plateaued; time for another evaluation round.",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.evidence.async.invented",
            require_evidence=True,
        )
        assert result.status == "failed"
        assert result.value is None
        assert "tier" in result.reason

    async def test_value_present_in_text_is_repaired(self):
        async def complete(messages, schema):
            return json.dumps({"type": "deep_eval", "tier": 1})

        result = await parse_with_repair_async(
            "The architect's quality has plateaued; run a deep_eval at tier 1.",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.evidence.async.present",
            require_evidence=True,
        )
        assert result.status == "repaired"
        assert result.value == {"type": "deep_eval", "tier": 1}

    async def test_evidence_exempt_key_honoured_async(self):
        async def complete(messages, schema):
            return json.dumps({"mode": "investigate", "brief": "check the disk usage report"})

        result = await parse_with_repair_async(
            "please check the disk usage report",
            schema=MIXED_DECISION_SCHEMA,
            complete=complete,
            site="test.evidence.async.exempt",
            require_evidence=True,
            evidence_exempt={"mode"},
        )
        assert result.status == "repaired"
        assert result.value == {"mode": "investigate", "brief": "check the disk usage report"}

    async def test_default_false_keeps_prior_behavior_byte_identical_async(self):
        async def complete(messages, schema):
            return json.dumps({"type": "deep_eval", "tier": 2})

        result = await parse_with_repair_async(
            "The architect's quality has plateaued; time for another evaluation round.",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.evidence.async.default_off",
        )
        assert result.status == "repaired"


# --------------------------------------------------------------------------- TD-21.35: relax_required wire schema
#
# 2026-09-24 live-smoke finding (see the module-level TD-21.35 comment above
# `_relax_required_for_wire`): a `required` field FORCES the grammar to fill
# a value even when the raw reply never states one -- a `deep_eval` draft
# with no stated tier repaired to a fabricated `tier=2`. This stops the
# invention at the grammar instead of only catching it after the fact
# (`require_evidence`, above). `required` is dropped at every object level
# for the WIRE schema (what `complete()` receives), except for a key pinned
# by `const`/single-value `enum` (an `oneOf`/`anyOf` discriminator) -- the
# RESULT is still validated against the original, unrelaxed schema.

NESTED_UNION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "outer": {
            "type": "object",
            "properties": {
                "kind": {"const": "widget"},
                "size": {"type": "integer"},
            },
            "required": ["kind", "size"],
            "additionalProperties": False,
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "score": {"type": "number"}},
                "required": ["id", "score"],
                "additionalProperties": False,
            },
        },
        "choice": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {"type": {"const": "a"}, "value": {"type": "string"}},
                    "required": ["type", "value"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {"type": {"enum": ["b"]}, "count": {"type": "integer"}},
                    "required": ["type", "count"],
                    "additionalProperties": False,
                },
            ]
        },
    },
    "required": ["outer", "items"],
}


class TestRelaxRequiredForWireUnit:
    """Direct unit coverage of `_relax_required_for_wire` -- nested objects,
    array `items`, and `oneOf` branches, with `const`/single-`enum`
    discriminators kept and every other key dropped."""

    def test_top_level_required_dropped(self):
        relaxed = _relax_required_for_wire(NESTED_UNION_SCHEMA)
        assert "required" not in relaxed

    def test_nested_object_required_dropped_but_const_kept(self):
        relaxed = _relax_required_for_wire(NESTED_UNION_SCHEMA)
        outer = relaxed["properties"]["outer"]
        assert outer["required"] == ["kind"]  # `size` dropped, `kind` (const) kept

    def test_array_items_required_dropped(self):
        relaxed = _relax_required_for_wire(NESTED_UNION_SCHEMA)
        item_schema = relaxed["properties"]["items"]["items"]
        assert "required" not in item_schema

    def test_oneof_branches_keep_only_their_discriminator(self):
        relaxed = _relax_required_for_wire(NESTED_UNION_SCHEMA)
        branch_a, branch_b = relaxed["properties"]["choice"]["oneOf"]
        assert branch_a["required"] == ["type"]  # `value` dropped
        assert branch_b["required"] == ["type"]  # single-enum discriminator kept, `count` dropped

    def test_non_required_content_untouched(self):
        relaxed = _relax_required_for_wire(NESTED_UNION_SCHEMA)
        assert relaxed["properties"]["outer"]["properties"]["size"] == {"type": "integer"}
        assert relaxed["additionalProperties"] is False
        assert relaxed["properties"]["choice"]["oneOf"][1]["properties"]["type"] == {"enum": ["b"]}

    def test_does_not_mutate_input(self):
        original = copy.deepcopy(NESTED_UNION_SCHEMA)
        _relax_required_for_wire(NESTED_UNION_SCHEMA)
        assert NESTED_UNION_SCHEMA == original

    def test_all_non_discriminator_required_schema_loses_required_entirely(self):
        relaxed = _relax_required_for_wire(SIMPLE_SCHEMA)
        assert "required" not in relaxed

    def test_action_like_schema_keeps_type_const_required(self):
        relaxed = _relax_required_for_wire(ACTION_LIKE_SCHEMA)
        assert relaxed["oneOf"][0]["required"] == ["type"]

    def test_required_with_no_sibling_properties_is_dropped(self):
        relaxed = _relax_required_for_wire({"type": "object", "required": ["x"]})
        assert "required" not in relaxed

    def test_non_mapping_and_scalar_schemas_pass_through(self):
        assert _relax_required_for_wire(True) is True
        assert _relax_required_for_wire({"type": "string"}) == {"type": "string"}


class TestRelaxRequiredIntegration:
    """`parse_with_repair` end to end: the schema handed to `complete()` is
    relaxed (const discriminators survive); the RESULT is still validated
    against the ORIGINAL schema, so an omitted required field fails honestly
    instead of being invented."""

    def test_wire_schema_seen_by_complete_has_no_required_except_discriminator(self):
        captured = {}

        def complete(messages, schema):
            captured["schema"] = schema
            return json.dumps({"type": "deep_eval"})

        parse_with_repair(
            "run a deep_eval",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.relax.wire_shape",
        )
        wire_branch = captured["schema"]["oneOf"][0]
        assert wire_branch["required"] == ["type"]

    def test_omitted_required_field_fails_instead_of_being_invented(self):
        # SIMPLE_SCHEMA requires both `name` and `count`, neither a
        # discriminator -- the wire schema forces neither, so a model that
        # only supplies `name` produces a value invalid against the
        # ORIGINAL schema: `"failed"`, never an invented `count`.
        def complete(messages, schema):
            assert "required" not in schema  # both were relaxed away on the wire
            return json.dumps({"name": "widget"})

        result = parse_with_repair(
            "widget, no count given anywhere in the text",
            schema=SIMPLE_SCHEMA,
            complete=complete,
            site="test.relax.omitted",
        )
        assert result.status == "failed"
        assert result.value is None
        assert "count" in result.reason  # names the missing field, not a fabricated value

    def test_supplied_required_field_still_repairs(self):
        def complete(messages, schema):
            return json.dumps({"name": "widget", "count": 3})

        result = parse_with_repair(
            "widget, count three",
            schema=SIMPLE_SCHEMA,
            complete=complete,
            site="test.relax.supplied",
        )
        assert result.status == "repaired"
        assert result.value == {"name": "widget", "count": 3}

    def test_relax_required_false_keeps_required_on_the_wire(self):
        captured = {}

        def complete(messages, schema):
            captured["schema"] = schema
            return json.dumps({"name": "widget", "count": 1})

        parse_with_repair(
            "widget",
            schema=SIMPLE_SCHEMA,
            complete=complete,
            site="test.relax.opt_out",
            relax_required=False,
        )
        # `relax_required=False` -- unlike the default -- sends `required`
        # on the wire exactly as the caller declared it (`_closed_schema`
        # still copies the dict for TD-21.30(d), but strips nothing else).
        assert captured["schema"]["required"] == ["name", "count"]

    def test_decline_probe_schema_is_never_relaxed(self):
        # `relax_required` only ever touches the EXTRACTION turn's schema;
        # the decline probe's own fixed schema (`explicitly_declines`,
        # `reason`) must stay exactly as `parse_with_repair` always sends it.
        schemas_seen = []

        def complete(messages, schema):
            schemas_seen.append(schema)
            if schema.get("properties", {}).get("explicitly_declines"):
                return json.dumps({"explicitly_declines": False, "reason": ""})
            return json.dumps({"mechanism_id": "widen-alignment"})

        parse_with_repair(
            "I propose renaming the buffer to widen alignment.",
            schema=DECLINE_SCHEMA,
            complete=complete,
            decline_question="Does the report explicitly decline to propose anything?",
            site="test.relax.decline_untouched",
        )
        decline_schema_sent = schemas_seen[0]
        assert decline_schema_sent["required"] == ["explicitly_declines", "reason"]


class TestRelaxRequiredAsyncIntegration:
    """Async twin of `TestRelaxRequiredIntegration` -- same wire relaxation,
    same original-schema validation, over `parse_with_repair_async`."""

    async def test_wire_schema_has_no_required_except_discriminator_async(self):
        captured = {}

        async def complete(messages, schema):
            captured["schema"] = schema
            return json.dumps({"type": "deep_eval"})

        await parse_with_repair_async(
            "run a deep_eval",
            schema=ACTION_LIKE_SCHEMA,
            complete=complete,
            site="test.relax.wire_shape.async",
        )
        wire_branch = captured["schema"]["oneOf"][0]
        assert wire_branch["required"] == ["type"]

    async def test_omitted_required_field_fails_instead_of_being_invented_async(self):
        async def complete(messages, schema):
            return json.dumps({"name": "widget"})

        result = await parse_with_repair_async(
            "widget, no count given anywhere in the text",
            schema=SIMPLE_SCHEMA,
            complete=complete,
            site="test.relax.omitted.async",
        )
        assert result.status == "failed"
        assert result.value is None
        assert "count" in result.reason

    async def test_supplied_required_field_still_repairs_async(self):
        async def complete(messages, schema):
            return json.dumps({"name": "widget", "count": 3})

        result = await parse_with_repair_async(
            "widget, count three",
            schema=SIMPLE_SCHEMA,
            complete=complete,
            site="test.relax.supplied.async",
        )
        assert result.status == "repaired"
        assert result.value == {"name": "widget", "count": 3}
