"""Offline regression tests for the real REPL-to-HTTP dispatch path."""
import asyncio
import json

import fixture
import pytest
from src.graph.compaction_semantic import canonical, digest

UNITS = {unit["id"]: unit for unit in fixture.config()["units"]}


def judgment(case, *, verdict="entailed", false_governance=False):
    text = case["observed_messages"][0]["content"]
    judgments = {}
    for field, value in case["reference"].items():
        label, quote = "entailed", value
        if field == "pinned_governance":
            label = verdict
            if verdict == "contradicted":
                quote = fixture.CONFLICT
            elif false_governance:
                quote = case["reference"]["verbatim_task"]
        evidence = [] if label == "unknown" else [{"message": 0, "quote": quote}]
        assert all(span["quote"] in text for span in evidence)
        judgments[field] = {"verdict": label, "rationale": "Offline test double.", "evidence": evidence}
    return canonical({"request_id": case["request_id"], "judgments": judgments})


@pytest.mark.parametrize("chat,batch", [(True, False), (True, True), (False, False), (False, True)])
def test_exact_http_payload_across_transport_variants(chat, batch, tmp_path):
    async def evaluator(case):
        raw = judgment(case)
        # Mutation of the callback input must not leak into the verified body or audit.
        case["observed_messages"][0]["content"] = "altered by evaluator"
        return raw

    outcome = asyncio.run(fixture.capture(UNITS["preserved"], tmp_path, evaluator, "offline", 1,
                                          chat=chat, batch=batch))
    audit, = outcome["audit"]
    dispatch, = outcome["worker_dispatches"]
    assert outcome["graph_boundaries"] == [fixture.BOUNDARY_TURN] and outcome["graph_result"] == ("C3-104", None, True)
    assert outcome["prior_output_pruned"]
    assert audit["blocked"] is False
    assert (tmp_path / "synthetic-worker-response-1.json").is_file()
    assert b"C3-104" in (tmp_path / "synthetic-worker-response-1.body").read_bytes()
    assert dispatch == audit["final_request"] and bool(dispatch["payload"].get("stream")) is not batch
    assert digest(canonical(dispatch)) == audit["case"]["custody"]["final_request_sha256"]
    assert json.loads((tmp_path / "worker-body-1.json").read_bytes()) == dispatch["payload"]
    expected = dispatch["payload"]["messages"] if chat else [
        {"role": "prompt", "content": dispatch["payload"]["prompt"]}]
    assert audit["case"]["observed_messages"] == expected


@pytest.mark.parametrize("name,label,reason", [
    ("late-conflict", "contradicted", "contradicted"),
    ("late-missing-governance", "unknown", "literal_contract"),
    ("late-missing-governance", "entailed", "literal_contract"),
])
def test_late_controls_remain_blocked_on_retry(name, label, reason, tmp_path):
    async def evaluator(case):
        return judgment(case, verdict=label, false_governance=(name.endswith("governance") and label == "entailed"))

    outcome = asyncio.run(fixture.capture(UNITS[name], tmp_path, evaluator, "offline", 1, retry_blocked=True))
    assert not outcome["worker_dispatches"]
    assert outcome["graph_error"] == outcome["retry_error"] == reason
    audit, = outcome["audit"]
    assert audit["semantic_verdict"] == label
    assert audit["case"]["literal_delivered"] is UNITS[name]["expected_literal"]


def test_repl_retry_rechecks_new_final_request(tmp_path):
    async def evaluator(case):
        verdict = "contradicted" if fixture.CONFLICT in case["observed_messages"][0]["content"] else "entailed"
        return judgment(case, verdict=verdict)

    outcome = asyncio.run(fixture.capture(UNITS["late-conflict"], tmp_path, evaluator, "offline", 1,
                                          retry_after_primary=True))
    primary, retry = outcome["audit"]
    assert primary["case"]["request_id"] != retry["case"]["request_id"]
    assert [primary["blocked"], retry["blocked"]] == [False, True]
    assert retry["block_reason"] == "contradicted"
    assert outcome["worker_dispatches"] == [primary["final_request"]]
    assert outcome["graph_result"] is None


@pytest.mark.parametrize("failure,reason", [
    ("missing", "missing_evaluator"),
    ("malformed", "invalid_evaluator_response"),
    ("stale", "invalid_evaluator_response"),
    ("timeout", "timeout"),
    ("unknown", "unknown"),
])
def test_missing_invalid_and_slow_judge_fail_closed(failure, reason, tmp_path):
    async def evaluator(case):
        if failure == "malformed":
            return b'{"request_id":'
        if failure == "stale":
            case["request_id"] = "different request"
        if failure == "timeout":
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                return judgment(case)
        return judgment(case, verdict="unknown" if failure == "unknown" else "entailed")

    outcome = asyncio.run(fixture.capture(UNITS["preserved"], tmp_path,
        None if failure == "missing" else evaluator, "offline", .05 if failure == "timeout" else 1,
        retry_blocked=True))
    assert outcome["worker_dispatches"] == []
    assert outcome["graph_error"] == outcome["retry_error"] == reason
    audit, = outcome["audit"]
    assert audit["blocked"] is True and audit["semantic_verdict"] == "unknown"


def test_feature_defaults_off(tmp_path):
    from src.features import Features

    assert Features().context_compaction_final_request is False
    result = asyncio.run(fixture.capture(UNITS["late-conflict"], tmp_path, None, "", 1, enabled=False))
    assert not result["audit"] and len(result["worker_dispatches"]) == 1
    assert result["graph_result"] == ("C3-104", None, True)
