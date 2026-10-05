"""ETR-6: the two "no decode" responses carry ``tokens_generated`` the same way.

Mock mode used to leave ``tokens_generated`` unset while the vision-unavailable
response set it to 0. With the model default both dump as 0, but any serializer
using ``exclude_unset`` (and any structural check on field presence, such as
ETR-3's ``"tokens_generated" in resp``) saw two different wire contracts.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from src.api.models import ChatRequest
from src.api.routes.chat_pipeline.stages import _execute_mock
from src.api.routes.chat_pipeline.vision_stage import _vision_unavailable_response
from src.api.routes.chat_utils import RoutingResult


def _routing() -> RoutingResult:
    return RoutingResult(
        task_id="etr6",
        task_ir={},
        use_mock=True,
        routing_decision=["frontdoor"],
        routing_strategy="mock",
    )


def _mock_dump() -> dict:
    state = MagicMock()
    state.progress_logger = None
    resp = _execute_mock(ChatRequest(prompt="p", real_mode=False), _routing(), state, time.perf_counter())
    return resp.model_dump(exclude_unset=True)


def _vision_dump() -> dict:
    resp = _vision_unavailable_response(
        ChatRequest(prompt="p", real_mode=True),
        _routing(),
        "worker_vision",
        "vision",
        time.perf_counter(),
        "RuntimeError: down",
    )
    return resp.model_dump(exclude_unset=True)


def test_mock_response_sets_tokens_generated_explicitly():
    dumped = _mock_dump()
    assert "tokens_generated" in dumped
    assert dumped["tokens_generated"] == 0


def test_both_no_decode_shapes_agree_on_tokens_generated():
    mock, vision = _mock_dump(), _vision_dump()
    assert ("tokens_generated" in mock) == ("tokens_generated" in vision)
    assert mock["tokens_generated"] == vision["tokens_generated"] == 0
