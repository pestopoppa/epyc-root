"""Tests for the DeepConf live-generation runner + OpenAI-style logprob adapter (P21.A2/A3).

No server: the HTTP POST is injected. Covers the OpenAI-style `top_logprobs[].logprob`
shape (the real format the production Qwen3.6 build returns), legacy-shape back-compat,
garbage tolerance, trace generation, post-failure handling, and the end-to-end vote.
"""

from __future__ import annotations

import math

import pytest

from src.test_time.deepconf import DeepConfConfig, trace_from_completion_probabilities
from src.test_time.deepconf_runner import generate_traces, run_deepconf


def _openai_cp(probs_per_token: list[list[float]]) -> list[dict]:
    """Fabricate OpenAI-style completion_probabilities from linear top-k probs."""
    return [
        {
            "token": "x",
            "logprob": math.log(p[0]),
            "top_logprobs": [{"token": str(i), "logprob": math.log(pp)} for i, pp in enumerate(p)],
        }
        for p in probs_per_token
    ]


def _fake_post(responses: list[dict]):
    state = {"n": 0}

    def post(url: str, body: dict, timeout: float) -> dict:
        r = responses[state["n"] % len(responses)]
        state["n"] += 1
        return r

    return post


class TestOpenAIAdapter:
    def test_openai_logprob_shape(self):
        tr = trace_from_completion_probabilities("ans", _openai_cp([[0.9, 0.1], [0.8, 0.2]]))
        assert len(tr.token_top_probs) == 2
        assert tr.token_top_probs[0][0] == pytest.approx(0.9)
        assert tr.token_top_probs[1][1] == pytest.approx(0.2)

    def test_legacy_shape_still_works(self):
        cp = [{"content": "4", "probs": [{"tok_str": "4", "prob": 0.7}, {"tok_str": "5", "prob": 0.3}]}]
        tr = trace_from_completion_probabilities("4", cp)
        assert tr.token_top_probs[0] == pytest.approx([0.7, 0.3])

    def test_garbage_entries_tolerated(self):
        cp = ["not a dict", {"token": "x"}, {"top_logprobs": [{"logprob": math.log(0.5)}]}]
        tr = trace_from_completion_probabilities("x", cp)
        assert tr.token_top_probs[0] == []   # non-dict -> empty row
        assert tr.token_top_probs[1] == []   # no candidates
        assert tr.token_top_probs[2][0] == pytest.approx(0.5)


class TestGenerateTraces:
    def test_builds_n_traces(self):
        peaked = {"content": "43", "completion_probabilities": _openai_cp([[0.98, 0.02]] * 3)}
        traces = generate_traces("p", "http://x/completion", 4, post_fn=_fake_post([peaked]))
        assert len(traces) == 4
        assert all(t.text == "43" for t in traces)
        assert all(len(t.token_top_probs) == 3 for t in traces)

    def test_post_failure_yields_empty_trace(self):
        def boom(url, body, timeout):
            raise RuntimeError("server down")

        traces = generate_traces("p", "u", 2, post_fn=boom)
        assert len(traces) == 2
        assert all(t.token_top_probs == [] and t.text == "" for t in traces)

    def test_n_probs_passed_through(self):
        seen: dict = {}

        def post(url, body, timeout):
            seen.update(body)
            return {"content": "x", "completion_probabilities": []}

        generate_traces("p", "u", 1, n_probs=7, post_fn=post)
        assert seen["n_probs"] == 7
        assert seen["prompt"] == "p"


class TestRunDeepconf:
    def test_end_to_end_confident_trace_wins(self):
        flat = {"content": "wrong", "completion_probabilities": _openai_cp([[0.34, 0.33, 0.33]] * 10)}
        peaked = {"content": "right", "completion_probabilities": _openai_cp([[0.98, 0.01, 0.01]] * 10)}
        # n_traces=3 -> calls cycle flat, flat, peaked; keep top 40% -> 1 (the peaked "right").
        res = run_deepconf(
            "p", "u",
            DeepConfConfig(n_traces=3, keep_percent=40.0, window=4),
            answer_extractor=lambda t: t,
            post_fn=_fake_post([flat, flat, peaked]),
        )
        assert res.answer == "right"
        assert res.kept_indices == [2]
