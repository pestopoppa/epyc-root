"""The output_schema preamble and the schema-retry failure message must reach the MODEL.

Found while building INF-78 OAB-7 (2026-09-25): the REPL loop rebuilds each turn's
root prompt from ``TaskState.prompt`` (``graph/helpers._execute_turn`` ->
``PromptBuilder.build_root_lm_prompt(original_prompt=state.prompt)``). The
``final_schema_validation`` path wrote the schema preamble -- and, on a schema failure,
the retry-with-error message -- into ``TaskState.context`` instead, which no turn prompt
reads (only compaction measures it). The model therefore never saw the schema it was
validated against, and the "retry with the error" re-ran blind.

Offline, inference-free: a recording double stands in for the models.

Run: taskset -c 72-79 .venv/bin/python -m pytest tests/unit/test_repl_schema_reaches_root_prompt.py -q
"""
from __future__ import annotations

import dataclasses
import json

import pytest

from src.api.models import ChatRequest
from src.features import features, reset_features, set_features
from tests.unit.test_oab7_context_bundle import _RecordingPrimitives, _run

SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


@pytest.fixture
def schema_validation_on():
    set_features(dataclasses.replace(features(), final_schema_validation=True))
    yield
    reset_features()


def _root(prims):
    return prims.root_prompts()


@pytest.mark.asyncio
async def test_schema_preamble_is_in_the_first_root_prompt(schema_validation_on):
    prims = _RecordingPrimitives(["```python\nFINAL('{\"answer\": \"yes\"}')\n```"])
    request = ChatRequest(prompt="Answer yes.", real_mode=True, mock_mode=False,
                          force_mode="repl", max_turns=3, output_schema=SCHEMA)
    resp = await _run(request, prims)
    assert json.loads(resp.answer) == {"answer": "yes"}
    first = _root(prims)[0]
    assert '"additionalProperties": false' in first or "additionalProperties" in first
    assert "FINAL(" in first and '"required"' in first


@pytest.mark.asyncio
async def test_schema_retry_shows_the_model_why(schema_validation_on):
    prims = _RecordingPrimitives([
        "```python\nFINAL('{\"wrong\": 1}')\n```",          # fails the schema; repair
                                                               # (worker) cannot fix it
        "```python\nFINAL('{\"answer\": \"fixed\"}')\n```",   # the retry, informed
    ])
    request = ChatRequest(prompt="Answer.", real_mode=True, mock_mode=False,
                          force_mode="repl", max_turns=6, output_schema=SCHEMA)
    resp = await _run(request, prims)
    assert json.loads(resp.answer) == {"answer": "fixed"}
    roots = _root(prims)
    assert len(roots) == 2
    assert "wrong" not in roots[0]
    # the retry's root prompt carries the validation failure and the rejected value
    assert "FINAL value failed schema validation." not in roots[0]
    assert "FINAL value failed schema validation." in roots[1]
    assert 'Rejected value: {"wrong": 1}' in roots[1]


@pytest.mark.asyncio
async def test_no_schema_prompt_unchanged():
    prims = _RecordingPrimitives(["```python\nFINAL('{\"answer\": \"x\"}')\n```"])
    request = ChatRequest(prompt="Plain.", real_mode=True, mock_mode=False,
                          force_mode="repl", max_turns=3)
    await _run(request, prims)
    assert '"required"' not in _root(prims)[0]
