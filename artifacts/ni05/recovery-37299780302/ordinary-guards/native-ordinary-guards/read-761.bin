"""Tests for reward delivery accounting in seeding injection."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_injection", _ROOT / "seeding_injection.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_injection"] = _MOD
_SPEC.loader.exec_module(_MOD)

_inject_3way_rewards_http = _MOD._inject_3way_rewards_http


class _ImmediateFuture:
    def __init__(self, value):
        self._value = value

    def result(self):
        return self._value

    def cancel(self):
        return False


class _ImmediateExecutor:
    def __init__(self, mapping):
        self.mapping = mapping

    def submit(self, fn, url, payload, action_key):
        return _ImmediateFuture(self.mapping[action_key])


def test_inject_3way_rewards_http_tracks_acknowledged_and_failed():
    client = Mock()
    rewards = {"SELF:direct": 1.0, "ARCHITECT": 0.0}
    mapping = {
        "SELF:direct": (True, ""),
        "ARCHITECT": (False, "http_503"),
    }

    def _fake_wait(futures, timeout):
        return set(futures), set()

    with patch("seeding_injection._precompute_embedding", return_value=None):
        with patch("seeding_injection._get_reward_executor", return_value=_ImmediateExecutor(mapping)):
            with patch("seeding_injection.concurrent.futures.wait", side_effect=_fake_wait):
                summary = _inject_3way_rewards_http(
                    prompt="hello",
                    suite="general",
                    question_id="q1",
                    rewards=rewards,
                    metadata={},
                    url="http://localhost:8000",
                    client=client,
                )

    assert summary["submitted"] == 2
    assert summary["acknowledged"] == 1
    assert summary["failed"] == 1
    assert summary["failure_reasons"]["ARCHITECT"] == "http_503"
