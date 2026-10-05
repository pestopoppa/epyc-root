"""EVL-42 1c-fix (b): reviewer must not judge a candidate on a silent 500-char prefix.

``ArchitectReviewService.review()`` used to do ``output[:500] + "..."`` before
prompting the architect, so a long-but-correct specialist answer whose
conclusion sat past char 500 was judged on an unfinished fragment. That
verdict feeds ``all_approved`` -> memrl reward (a latent verbose bias). The
fix condenses head+tail with an explicit elision marker under a configurable
budget (``DelegationConfig.review_output_max_chars``).

Offline: StubPrimitives records the prompt; no model is called.
"""

from __future__ import annotations

import pytest

from src.config.models import DelegationConfig
from src.proactive_delegation.review_service import ArchitectReviewService

HEAD_SENTINEL = "HEAD-SENTINEL-7f3a"
TAIL_SENTINEL = "FINAL ANSWER: 42 TAIL-SENTINEL-9c1d"


class StubPrimitives:
    def __init__(self, response: str = '{"d":"approve","s":0.9,"f":"ok"}'):
        self.response = response
        self.calls: list[dict] = []

    def llm_call(self, prompt, role=None, n_tokens=None, **kwargs):
        self.calls.append({"prompt": prompt, "role": role, "n_tokens": n_tokens})
        return self.response


def _service() -> tuple[ArchitectReviewService, StubPrimitives]:
    prims = StubPrimitives()
    svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
    return svc, prims


def _long_output(total: int) -> str:
    filler = "x" * (total - len(HEAD_SENTINEL) - len(TAIL_SENTINEL) - 2)
    return f"{HEAD_SENTINEL} {filler} {TAIL_SENTINEL}"


def _prompt(prims: StubPrimitives) -> str:
    assert len(prims.calls) == 1
    return prims.calls[0]["prompt"]


def test_delegation_config_carries_review_output_budget():
    assert DelegationConfig().review_output_max_chars == 4000


def test_output_within_budget_is_passed_verbatim():
    """1500 chars used to be cut at 500; now the whole candidate reaches the reviewer."""
    svc, prims = _service()
    output = _long_output(1500)
    svc.review({"objective": "o"}, {"id": "s1", "action": "a"}, output)
    assert output in _prompt(prims)


def test_over_budget_output_keeps_tail_and_marks_elision():
    svc, prims = _service()
    output = _long_output(9000)
    svc.review({"objective": "o"}, {"id": "s1", "action": "a"}, output)
    prompt = _prompt(prims)
    assert HEAD_SENTINEL in prompt
    assert TAIL_SENTINEL in prompt, "conclusion past the budget must still reach the reviewer"
    assert "chars elided by reviewer budget" in prompt
    assert "9000 total" in prompt
    assert output not in prompt


def test_budget_is_configurable_per_service():
    svc, prims = _service()
    svc.review_output_max_chars = 300
    output = _long_output(1000)
    svc.review({"objective": "o"}, {"id": "s1", "action": "a"}, output)
    prompt = _prompt(prims)
    assert HEAD_SENTINEL in prompt and TAIL_SENTINEL in prompt
    assert "700 chars elided" in prompt  # 1000 - 180 head - 120 tail


def test_quick_mode_preview_also_keeps_tail():
    svc, prims = _service()
    output = _long_output(1000)
    svc.review({"objective": "o"}, {"id": "s1", "action": "a"}, output, quick_mode=True)
    prompt = _prompt(prims)
    assert TAIL_SENTINEL in prompt
    assert "chars elided by reviewer budget" in prompt


@pytest.mark.parametrize("max_chars", [0, -1])
def test_non_positive_budget_disables_condensation(max_chars):
    output = _long_output(5000)
    assert ArchitectReviewService.condense_output(output, max_chars) == output


def test_condense_output_short_input_is_identity():
    assert ArchitectReviewService.condense_output("short", 500) == "short"
