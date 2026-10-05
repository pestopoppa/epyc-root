"""API-handler lifecycle coverage for the live telemetry drain certificate."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.api.models import ChatRequest, ChatResponse
from src.api.routes.chat import chat
from src.runtime.live_telemetry import (
    live_batch_activity_summary,
    reset_live_telemetry_for_tests,
)


@pytest.mark.asyncio
async def test_chat_batch_activity_stays_unresolved_until_handler_exit() -> None:
    reset_live_telemetry_for_tests()
    entered = asyncio.Event()
    release = asyncio.Event()
    state = MagicMock()

    class _FakeRequest:
        async def is_disconnected(self) -> bool:
            return False

    async def fake_handle_chat(*_args, **_kwargs):
        entered.set()
        await release.wait()
        return ChatResponse(answer="ok", turns=1, elapsed_seconds=0.01, mock_mode=True)

    request = ChatRequest(
        prompt="test",
        request_id="api-req-1",
        batch_id="batch-drain",
        workload_class="eval_batch",
    )
    with patch("src.api.routes.chat._handle_chat", new=fake_handle_chat):
        running = asyncio.create_task(chat(request, _FakeRequest(), state))
        await entered.wait()
        active = live_batch_activity_summary()
        assert active["certificate_valid"] is True
        assert active["batches"]["batch-drain"]["active_unresolved"] == 1
        assert active["batches"]["batch-drain"]["queued_unresolved"] == 1
        release.set()
        await running

    drained = live_batch_activity_summary()
    assert "batch-drain" in drained["batches"]
    assert drained["batches"]["batch-drain"]["active_unresolved"] == 0
