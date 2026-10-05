"""Additional tests for seeding_injection reward and embedder edge paths."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_injection_additional", _ROOT / "seeding_injection.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_injection_additional"] = _MOD
_SPEC.loader.exec_module(_MOD)


def test_get_reward_executor_reuses_singleton():
    # Reset local singleton for deterministic behavior.
    if _MOD._reward_executor is not None:
        _MOD._reward_executor.shutdown(wait=False, cancel_futures=True)
    _MOD._reward_executor = None
    try:
        ex1 = _MOD._get_reward_executor()
        ex2 = _MOD._get_reward_executor()
    finally:
        if _MOD._reward_executor is not None:
            _MOD._reward_executor.shutdown(wait=False, cancel_futures=True)
        _MOD._reward_executor = None
    assert ex1 is ex2


def test_precompute_embedding_supports_multiple_response_shapes():
    client = Mock()
    client.post.side_effect = [
        SimpleNamespace(status_code=500, json=lambda: {}),
        SimpleNamespace(status_code=200, json=lambda: {"embedding": [[0.1, 0.2]]}),
    ]
    emb = _MOD._precompute_embedding("task", client)
    assert emb == [0.1, 0.2]

    client2 = Mock()
    client2.post.return_value = SimpleNamespace(
        status_code=200,
        json=lambda: {"data": [{"embedding": [0.3, 0.4]}]},
    )
    emb2 = _MOD._precompute_embedding("task", client2)
    assert emb2 == [0.3, 0.4]


def test_precompute_embedding_supports_flat_embedding_list():
    client = Mock()
    client.post.return_value = SimpleNamespace(
        status_code=200,
        json=lambda: {"embedding": [0.7, 0.8, 0.9]},
    )
    emb = _MOD._precompute_embedding("task", client)
    assert emb == [0.7, 0.8, 0.9]


def test_precompute_embedding_returns_none_when_all_ports_fail():
    client = Mock()
    client.post.side_effect = RuntimeError("embedder unavailable")
    assert _MOD._precompute_embedding("task", client) is None


def test_inject_single_reward_success_http_failure_and_exception():
    ok_client = MagicMock()
    ok_client.post.return_value = SimpleNamespace(status_code=200)
    with patch("httpx.Client") as factory:
        factory.return_value.__enter__.return_value = ok_client
        ok, reason = _MOD._inject_single_reward("http://localhost:8000", {"x": 1}, "SELF")
    assert (ok, reason) == (True, "")

    bad_client = MagicMock()
    bad_client.post.return_value = SimpleNamespace(status_code=503)
    with patch("httpx.Client") as factory:
        factory.return_value.__enter__.return_value = bad_client
        ok2, reason2 = _MOD._inject_single_reward("http://localhost:8000", {"x": 1}, "ARCH")
    assert ok2 is False
    assert reason2 == "http_503"

    err_client = MagicMock()
    err_client.post.side_effect = RuntimeError("boom")
    with patch("httpx.Client") as factory:
        factory.return_value.__enter__.return_value = err_client
        ok3, reason3 = _MOD._inject_single_reward("http://localhost:8000", {"x": 1}, "WORKER")
    assert ok3 is False
    assert "RuntimeError" in reason3


class _Future:
    def __init__(self, result=None, exc: Exception | None = None):
        self._result = result
        self._exc = exc
        self.cancel_called = False

    def result(self):
        if self._exc is not None:
            raise self._exc
        return self._result

    def cancel(self):
        self.cancel_called = True
        return True


class _Executor:
    def __init__(self, futures_by_action: dict[str, _Future], payload_sink: list[dict]):
        self._futures = futures_by_action
        self._payload_sink = payload_sink

    def submit(self, fn, url, payload, action_key):
        self._payload_sink.append({"action": action_key, "payload": payload})
        return self._futures[action_key]


def test_inject_3way_rewards_http_empty_rewards_returns_zero_summary():
    summary = _MOD._inject_3way_rewards_http(
        prompt="hello",
        suite="general",
        question_id="q1",
        rewards={},
        metadata={},
        url="http://localhost:8000",
        client=Mock(),
    )
    assert summary == {
        "submitted": 0,
        "acknowledged": 0,
        "failed": 0,
        "skipped": 0,
        "failure_reasons": {},
    }


def test_inject_3way_rewards_http_tracks_done_exceptions_and_timeout():
    rewards = {"SELF:direct": 1.0, "ARCHITECT": 0.0, "WORKER": 0.5}
    done_ok = _Future(result=(True, ""))
    done_exc = _Future(exc=RuntimeError("delivery failed"))
    not_done = _Future(result=(False, "late"))
    payloads: list[dict] = []
    futures = {
        "SELF:direct": done_ok,
        "ARCHITECT": done_exc,
        "WORKER": not_done,
    }
    _by_future = {
        done_ok: "SELF:direct",
        done_exc: "ARCHITECT",
        not_done: "WORKER",
    }

    def _wait(keys, timeout):  # noqa: ANN001
        return {done_ok, done_exc}, {not_done}

    metadata = {
        "cost_metrics": {
            "SELF:direct": {"tokens_generated": 10, "elapsed_seconds": 1.2},
            "ARCHITECT": {"tokens_generated_estimate": 11, "elapsed_seconds": 2.4},
            "WORKER": {"tokens_generated": 9, "elapsed_seconds": 3.6},
        },
        "web_research_rewards": {"SELF:direct": {"wr_bonus": 1.0}},
        "scratchpad_rewards": {"ARCHITECT": {"sp_bonus": 2.0}},
        "tools_helped": True,
        "tool_advantage": 1,
    }

    with (
        patch("seeding_injection_additional._precompute_embedding", return_value=[0.9, 0.8]),
        patch(
            "seeding_injection_additional._get_reward_executor",
            return_value=_Executor(futures, payloads),
        ),
        patch("seeding_injection_additional.concurrent.futures.wait", side_effect=_wait),
    ):
        summary = _MOD._inject_3way_rewards_http(
            prompt="hello world",
            suite="general",
            question_id="q42",
            rewards=rewards,
            metadata=metadata,
            url="http://localhost:8000",
            client=Mock(),
        )

    assert summary["submitted"] == 3
    assert summary["acknowledged"] == 1
    assert summary["failed"] == 2
    assert summary["failure_reasons"]["WORKER"] == "wait_timeout"
    assert "RuntimeError" in summary["failure_reasons"]["ARCHITECT"]

    # Verify context shaping and embedding propagation.
    self_payload = next(x["payload"] for x in payloads if x["action"] == "SELF:direct")
    arch_payload = next(x["payload"] for x in payloads if x["action"] == "ARCHITECT")
    assert self_payload["embedding"] == [0.9, 0.8]
    assert self_payload["context"]["tokens_generated_effective"] == 10
    assert self_payload["context"]["wr_bonus"] == 1.0
    assert arch_payload["context"]["tokens_generated_effective"] == 11
    assert arch_payload["context"]["sp_bonus"] == 2.0


def test_inject_per_role_rewards_http_empty_rewards():
    summary = _MOD._inject_per_role_rewards_http(
        prompt="hello",
        suite="general",
        question_id="q1",
        rewards={},
        metadata={},
        url="http://localhost:8000",
        client=Mock(),
    )
    assert summary["submitted"] == 0
    assert summary["acknowledged"] == 0
    assert summary["failed"] == 0


def test_inject_per_role_rewards_http_tracks_delivery():
    rewards = {"frontdoor": 1.0, "architect_general": 0.0}
    done_ok = _Future(result=(True, ""))
    done_fail = _Future(result=(False, "http_503"))
    payloads: list[dict] = []
    futures = {
        "frontdoor": done_ok,
        "architect_general": done_fail,
    }

    def _wait(keys, timeout):  # noqa: ANN001
        return {done_ok, done_fail}, set()

    metadata = {
        "cost_metrics": {
            "frontdoor": {
                "tokens_generated": 42,
                "elapsed_seconds": 1.5,
                "predicted_tps": 12.7,
                "prompt_eval_ms": 100.0,
                "generation_ms": 300.0,
                "tools_used": 2,
            },
            "architect_general": {
                "tokens_generated": 100,
                "elapsed_seconds": 5.0,
            },
        },
    }

    with (
        patch("seeding_injection_additional._precompute_embedding", return_value=[0.5, 0.6]),
        patch(
            "seeding_injection_additional._get_reward_executor",
            return_value=_Executor(futures, payloads),
        ),
        patch("seeding_injection_additional.concurrent.futures.wait", side_effect=_wait),
    ):
        summary = _MOD._inject_per_role_rewards_http(
            prompt="test prompt",
            suite="coder",
            question_id="q99",
            rewards=rewards,
            metadata=metadata,
            url="http://localhost:8000",
            client=Mock(),
        )

    assert summary["submitted"] == 2
    assert summary["acknowledged"] == 1
    assert summary["failed"] == 1
    assert summary["failure_reasons"]["architect_general"] == "http_503"

    # Verify per-role context shaping
    fd_payload = next(x["payload"] for x in payloads if x["action"] == "frontdoor")
    assert fd_payload["context"]["source"] == "per_role_eval"
    assert fd_payload["context"]["tokens_generated"] == 42
    assert fd_payload["context"]["predicted_tps"] == 12.7
    assert fd_payload["embedding"] == [0.5, 0.6]


def test_inject_per_role_rewards_http_timeout_handling():
    rewards = {"worker_explore": 0.5}
    not_done = _Future(result=(False, "late"))
    payloads: list[dict] = []
    futures = {"worker_explore": not_done}

    def _wait(keys, timeout):  # noqa: ANN001
        return set(), {not_done}

    with (
        patch("seeding_injection_additional._precompute_embedding", return_value=None),
        patch(
            "seeding_injection_additional._get_reward_executor",
            return_value=_Executor(futures, payloads),
        ),
        patch("seeding_injection_additional.concurrent.futures.wait", side_effect=_wait),
    ):
        summary = _MOD._inject_per_role_rewards_http(
            prompt="test",
            suite="general",
            question_id="q1",
            rewards=rewards,
            metadata={},
            url="http://localhost:8000",
            client=Mock(),
        )

    assert summary["submitted"] == 1
    assert summary["failed"] == 1
    assert summary["failure_reasons"]["worker_explore"] == "wait_timeout"
    # Verify no embedding when precompute returns None
    payload = payloads[0]["payload"]
    assert "embedding" not in payload
