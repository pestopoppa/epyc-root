"""Tests for reasoning length alarm (short-m@k Action 9)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.features import Features, set_features, reset_features
from src.graph.helpers import _check_reasoning_length_alarm


@pytest.fixture(autouse=True)
def _reset():
    yield
    reset_features()


def _make_think_output(length: int) -> str:
    """Build a raw output string with a <think> block of given char length."""
    body = "x" * length
    return f"<think>{body}</think>\nFINAL(42)"


class TestCheckReasoningLengthAlarm:
    """Unit tests for _check_reasoning_length_alarm."""

    def test_no_band_returns_false(self):
        set_features(Features(reasoning_length_alarm=True))
        assert _check_reasoning_length_alarm("<think>long</think>", "", 9999) is False

    def test_feature_flag_off_returns_false(self):
        set_features(Features(reasoning_length_alarm=False))
        # Feature flag off → returns False before even checking mode
        assert _check_reasoning_length_alarm(
            _make_think_output(50000), "easy", 9999
        ) is False

    @patch("src.classifiers.difficulty_signal.get_mode", return_value="shadow")
    def test_mode_not_enforce_returns_false(self, mock_mode):
        set_features(Features(reasoning_length_alarm=True))
        assert _check_reasoning_length_alarm(
            _make_think_output(50000), "easy", 9999
        ) is False

    @patch("src.classifiers.difficulty_signal.get_mode", return_value="enforce")
    def test_no_think_block_returns_false(self, mock_mode):
        set_features(Features(reasoning_length_alarm=True))
        assert _check_reasoning_length_alarm(
            "Just a plain answer", "easy", 9999
        ) is False

    @patch("src.classifiers.difficulty_signal.get_mode", return_value="enforce")
    def test_under_threshold_returns_false(self, mock_mode):
        set_features(Features(reasoning_length_alarm=True))
        # easy budget = 1500, threshold = 2250
        assert _check_reasoning_length_alarm(
            _make_think_output(100), "easy", 1000
        ) is False

    @patch("src.classifiers.difficulty_signal.get_mode", return_value="enforce")
    def test_over_threshold_returns_true(self, mock_mode):
        set_features(Features(reasoning_length_alarm=True))
        # easy budget = 1500, threshold = 2250
        assert _check_reasoning_length_alarm(
            _make_think_output(100), "easy", 3000
        ) is True

    @patch("src.classifiers.difficulty_signal.get_mode", return_value="enforce")
    def test_fallback_to_char_count_when_tokens_zero(self, mock_mode):
        set_features(Features(reasoning_length_alarm=True))
        # easy budget = 1500, threshold = 2250
        # 10000 chars // 4 = 2500 tokens > 2250
        assert _check_reasoning_length_alarm(
            _make_think_output(10000), "easy", 0
        ) is True

    @patch("src.classifiers.difficulty_signal.get_mode", return_value="enforce")
    def test_fallback_under_threshold_when_tokens_zero(self, mock_mode):
        set_features(Features(reasoning_length_alarm=True))
        # easy budget = 1500, threshold = 2250
        # 4000 chars // 4 = 1000 tokens < 2250
        assert _check_reasoning_length_alarm(
            _make_think_output(4000), "easy", 0
        ) is False

    @patch("src.classifiers.difficulty_signal.get_mode", return_value="enforce")
    def test_hard_band_higher_threshold(self, mock_mode):
        set_features(Features(reasoning_length_alarm=True))
        # hard budget = 7000, threshold = 10500
        assert _check_reasoning_length_alarm(
            _make_think_output(100), "hard", 8000
        ) is False
        assert _check_reasoning_length_alarm(
            _make_think_output(100), "hard", 11000
        ) is True
