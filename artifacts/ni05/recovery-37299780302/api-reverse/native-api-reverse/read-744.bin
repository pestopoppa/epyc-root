"""Unit coverage for scripts.lib.output_parser shared parser helper."""

from __future__ import annotations

from scripts.lib.output_parser import (
    parse_acceptance_rate,
    parse_output,
    parse_response,
    parse_timing,
    parse_token_counts,
)


def test_parse_response_filters_logs_and_eof_markers():
    raw = """
build: 123
llama_model_loader: loaded

Hello from model
> EOF marker
common_perf_print: eval time = 1 ms / 1 runs (1.0 tokens per second)
"""
    assert parse_response(raw) == "Hello from model"


def test_parse_timing_speculative_path_uses_n_predict_and_target_total_time():
    raw = """
n_predict = 120
draft:
  total time = 20.00 ms
target:
  prompt eval time = 33.5 ms
  total time = 2000.00 ms / 120 tokens
"""
    parsed = parse_timing(raw)
    assert parsed["total_time_ms"] == 2000.0
    assert parsed["prompt_eval_time_ms"] == 33.5
    assert parsed["tokens_per_second"] == 60.0


def test_parse_timing_standard_eval_and_prompt_eval_paths():
    raw = """
common_perf_print: prompt eval time = 100.00 ms / 10 tokens
common_perf_print: eval time = 4000.00 ms / 200 runs (20.0 ms per token, 50.00 tokens per second)
"""
    parsed = parse_timing(raw)
    assert parsed["prompt_eval_time_ms"] == 100.0
    assert parsed["total_time_ms"] == 4000.0
    assert parsed["tokens_per_second"] == 50.0


def test_parse_timing_falls_back_to_speed_line():
    raw = "decoded 100 tokens in 5.0 seconds, speed: 21.25 t/s"
    parsed = parse_timing(raw)
    assert parsed["tokens_per_second"] == 21.25
    assert parsed["total_time_ms"] is None


def test_parse_timing_last_resort_eval_line_tokens_per_second():
    raw = "eval time = 10.00 ms / 5 runs (2.00 ms per token, 500.0 tokens per second)"
    parsed = parse_timing(raw)
    assert parsed["tokens_per_second"] == 500.0
    assert parsed["total_time_ms"] == 10.0


def test_parse_timing_final_fallback_handles_nonstandard_eval_line():
    raw = "eval time: decoder summary, observed 321.5 tokens per second"
    parsed = parse_timing(raw)
    assert parsed["tokens_per_second"] == 321.5
    assert parsed["total_time_ms"] is None


def test_parse_token_counts_extracts_prompt_and_completion_tokens():
    raw = """
prompt eval time = 123.00 ms / 42 tokens
eval time = 500.00 ms / 17 runs (29.41 ms per token, 34.00 tokens per second)
"""
    parsed = parse_token_counts(raw)
    assert parsed["prompt_tokens"] == 42
    assert parsed["completion_tokens"] == 17


def test_parse_acceptance_rate_percent_and_normalization():
    assert parse_acceptance_rate("accept = 75.0%") == 0.75
    assert parse_acceptance_rate("draft acceptance rate: 0.62") == 0.62
    assert parse_acceptance_rate("acceptance: 87.5") == 0.875
    assert parse_acceptance_rate("no acceptance markers") is None


def test_parse_output_builds_structured_result():
    raw = """
build: 123
Hi there
prompt eval time = 50.00 ms / 5 tokens
eval time = 200.00 ms / 10 runs (20.0 ms per token, 50.00 tokens per second)
accept = 40.0%
    """
    parsed = parse_output(raw)
    assert parsed.response.startswith("Hi there")
    assert "accept = 40.0%" in parsed.response
    assert parsed.prompt_tokens == 5
    assert parsed.completion_tokens == 10
    assert parsed.prompt_eval_time_ms == 50.0
    assert parsed.total_time_ms == 200.0
    assert parsed.tokens_per_second == 50.0
    assert parsed.acceptance_rate == 0.4
