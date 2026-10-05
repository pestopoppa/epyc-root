from __future__ import annotations

from pathlib import Path
import json

import pytest

from scripts.analysis import ri10_canary_dispatch_requests as dispatch


def _payload(request_id: str = "ri10-frontdoor-enforce-001-00001") -> dict:
    return {
        "request_id": request_id,
        "force_role": "frontdoor",
        "timeout_s": 1,
        "prompt": "answer a factual question",
    }


def test_dispatch_payloads_writes_scorer_compatible_success_rows() -> None:
    def fake_post(url: str, payload: dict, timeout_s: float) -> tuple[int, dict, str]:
        assert url == "http://api/chat"
        assert timeout_s == 31.0
        return 200, {"answer": "Safari", "routed_to": "frontdoor", "mode": "direct"}, "{}"

    successes, failures, summary = dispatch.dispatch_payloads(
        [_payload()],
        api_url="http://api/chat",
        post_json=fake_post,
    )

    assert failures == []
    assert summary["status"] == "ready"
    assert successes == [
        {
            "request_id": "ri10-frontdoor-enforce-001-00001",
            "role": "frontdoor",
            "response": "Safari",
            "status_code": 200,
            "elapsed_s": pytest.approx(successes[0]["elapsed_s"]),
            "routed_to": "frontdoor",
            "mode": "direct",
            "tokens_used": None,
            "tokens_generated": None,
            "predicted_tps": None,
            "factual_risk_band": None,
            "factual_risk_score": None,
            "xmas_meta": None,
        }
    ]


def test_dispatch_payloads_keeps_error_rows_out_of_scorer_responses() -> None:
    def fake_post(url: str, payload: dict, timeout_s: float) -> tuple[int, dict, str]:
        return 503, {"error_code": 503, "error_detail": "busy"}, '{"error_code":503}'

    successes, failures, summary = dispatch.dispatch_payloads(
        [_payload()],
        post_json=fake_post,
    )

    assert successes == []
    assert summary["status"] == "failures"
    assert failures[0]["request_id"] == "ri10-frontdoor-enforce-001-00001"
    assert failures[0]["status_code"] == 503
    assert failures[0]["response_error_code"] == 503


def test_load_jsonl_rejects_empty_files(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="no rows"):
        dispatch.load_jsonl(path)


def test_write_jsonl_round_trips_rows(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    dispatch.write_jsonl([{"b": 2, "a": 1}], path)

    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [
        {"a": 1, "b": 2}
    ]
