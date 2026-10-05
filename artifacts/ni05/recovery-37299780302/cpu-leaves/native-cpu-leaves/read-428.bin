"""Tests for the ingest-triviality routing guard.

The guard demotes trivially-easy short prompts off ``ingest_long_context``
(Qwen3-Next-80B accuracy/long-context specialist) onto ``worker_general``,
without touching long-context payloads or short-but-hard reasoning. It is
opt-in behind the ``ingest_triviality_guard`` feature flag.
"""

from unittest.mock import patch

from src.api.models import ChatRequest
from src.api.routes.chat_pipeline.routing_decision import (
    apply_ingest_triviality_guard,
)
from src.roles import Role

INGEST = str(Role.INGEST_LONG_CONTEXT)
WORKER = str(Role.WORKER_GENERAL)
FRONTDOOR = str(Role.FRONTDOOR)

_GUARD_FEATURES = "src.api.routes.chat_pipeline.routing_decision.features"


def _guard(request, decision, strategy, band, *, flag=True):
    with patch(_GUARD_FEATURES) as mock_features:
        mock_features.return_value.ingest_triviality_guard = flag
        return apply_ingest_triviality_guard(
            request, decision, strategy, band, "task-test"
        )


def _req(prompt="gcd(6432, 132)?", context=""):
    return ChatRequest(prompt=prompt, context=context, real_mode=True)


class TestIngestTrivialityGuard:
    def test_flag_off_is_noop(self):
        decision, strategy = _guard(
            _req(), [INGEST], "classified", "easy", flag=False
        )
        assert decision == [INGEST]
        assert strategy == "classified"

    def test_easy_short_ingest_is_demoted(self):
        decision, strategy = _guard(_req(), [INGEST], "classified", "easy")
        assert decision == [WORKER]
        assert strategy == "classified:ingest_triviality_guard"

    def test_hard_band_is_preserved(self):
        # short-but-hard reasoning is exactly what ingest legitimately wins
        decision, _ = _guard(_req(), [INGEST], "classified", "hard")
        assert decision == [INGEST]

    def test_medium_band_is_preserved(self):
        decision, _ = _guard(_req(), [INGEST], "classified", "medium")
        assert decision == [INGEST]

    def test_long_context_is_preserved_even_when_easy(self):
        decision, _ = _guard(
            _req(context="x" * 5000), [INGEST], "classified", "easy"
        )
        assert decision == [INGEST]

    def test_long_prompt_is_preserved_even_when_easy(self):
        decision, _ = _guard(
            _req(prompt="y" * 5000), [INGEST], "classified", "easy"
        )
        assert decision == [INGEST]

    def test_unknown_band_demotes_only_very_short(self):
        # difficulty signal off/unavailable -> strict 400-char ceiling
        short = _guard(_req(prompt="z" * 200), [INGEST], "classified", "")
        assert short[0] == [WORKER]
        mid = _guard(_req(prompt="z" * 1000), [INGEST], "classified", "")
        assert mid[0] == [INGEST]

    def test_non_ingest_role_is_untouched(self):
        decision, strategy = _guard(_req(), [FRONTDOOR], "classified", "easy")
        assert decision == [FRONTDOOR]
        assert strategy == "classified"

    def test_empty_decision_is_noop(self):
        decision, strategy = _guard(_req(), [], "classified", "easy")
        assert decision == []
        assert strategy == "classified"
