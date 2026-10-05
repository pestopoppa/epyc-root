"""Loose-end fix: ContentionDenied → HTTP 503 + Retry-After."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_contention_denied_class_is_runtime_error() -> None:
    from src.scheduling.contention_gate import ContentionDenied
    assert issubclass(ContentionDenied, RuntimeError)
    # Can be raised + caught
    with pytest.raises(ContentionDenied) as exc_info:
        raise ContentionDenied("test reason")
    assert "test reason" in str(exc_info.value)


def test_contention_denied_provenance_is_closed_json_primitive_contract() -> None:
    """Admission denials carry typed state, never text-derived evidence."""
    from src.scheduling.contention_gate import ContentionDenied

    exc = ContentionDenied(
        "placement lost its lock race",
        role="frontdoor",
        workload_class="quality_baseline",
        wait_budget_ms=300_000,
        failure_class="admission_timeout",
        code="race_lost",
    )

    provenance = exc.provenance()
    assert provenance == {
        "schema": "epyc.failure_provenance.v1",
        "class": "admission_timeout",
        "code": "race_lost",
        "phase": "admission",
        "role": "frontdoor",
        "workload_class": "quality_baseline",
        "max_queue_wait_ms": 300_000,
        "generation_started": False,
        "tokens_generated": 0,
        "partial": False,
        "degraded": False,
    }
    assert all(type(value) in {str, int, bool} for value in provenance.values())
    provenance["code"] = "mutated"
    assert exc.provenance()["code"] == "race_lost"


def test_contention_denied_rejects_non_primitive_budget() -> None:
    from src.scheduling.contention_gate import ContentionDenied

    with pytest.raises(TypeError, match="wait_budget_ms"):
        ContentionDenied("bad", wait_budget_ms=True)


def test_contention_denied_reserves_race_lost_for_admission_timeout() -> None:
    from src.scheduling.contention_gate import ContentionDenied

    with pytest.raises(ValueError, match="reserved"):
        ContentionDenied("bad", code="race_lost")
    with pytest.raises(ValueError, match="reserved"):
        ContentionDenied("bad", failure_class="admission_timeout", code="gate_timeout")


def test_app_registers_503_handler_for_contention_denied() -> None:
    """The FastAPI app must have an exception handler mapping ContentionDenied → 503."""
    import os
    os.environ["PYTEST_CURRENT_TEST"] = "1"  # disables lifespan
    from fastapi.exceptions import ResponseValidationError
    from src.api import app
    from src.scheduling.contention_gate import ContentionDenied
    # FastAPI stores handlers in app.exception_handlers keyed by exception class
    assert ContentionDenied in app.exception_handlers
    assert ResponseValidationError in app.exception_handlers
    assert Exception in app.exception_handlers


def test_503_response_carries_retry_after() -> None:
    """End-to-end via TestClient — a route that raises ContentionDenied should
    return 503 with Retry-After header + structured body."""
    import os
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    from fastapi.testclient import TestClient
    from src.api import app
    from src.scheduling.contention_gate import ContentionDenied

    # Inject a test-only route that raises
    @app.get("/__test_contention_denied")
    def _raise():
        raise ContentionDenied("test pair frontdoor+architect blocked")

    client = TestClient(app)
    resp = client.get("/__test_contention_denied")
    assert resp.status_code == 503
    assert resp.headers.get("Retry-After") == "5"
    body = resp.json()
    assert body["error"] == "contention_denied"
    assert "frontdoor" in body["detail"]
    assert body["retry_after_s"] == 5
    # The original three body fields remain intact; typed provenance is
    # additive and only emitted by this explicit exception handler.
    assert body["error_code"] == 503
    assert body["error_detail"] == body["detail"]
    provenance = body["failure_provenance"]
    assert provenance["schema"] == "epyc.failure_provenance.v1"
    assert provenance["phase"] == "admission"
    assert provenance["generation_started"] is False
    assert provenance["tokens_generated"] == 0
    assert provenance["partial"] is False
    assert provenance["degraded"] is False
    assert all(type(value) in {str, int, bool} for value in provenance.values())


def test_generic_exception_does_not_receive_admission_provenance() -> None:
    """Structured denial state is never guessed for unrelated failures."""
    import os

    os.environ["PYTEST_CURRENT_TEST"] = "1"
    from fastapi.testclient import TestClient
    from src.api import app

    @app.get("/__test_generic_error_without_provenance")
    def _raise_generic():
        raise RuntimeError("unrelated backend bug")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/__test_generic_error_without_provenance")

    assert response.status_code == 500
    body = response.json()
    assert body == {"error": "internal_server_error", "detail": "Internal server error"}


def test_503_response_logs_progress_counter() -> None:
    """ContentionDenied responses emit a durable counter event for bake gates."""
    import os
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    from fastapi.testclient import TestClient
    from src.api import app
    from src.api.state import get_state
    from src.scheduling.contention_gate import ContentionDenied

    state = get_state()
    state.progress_logger = MagicMock()

    @app.get("/__test_contention_denied_progress")
    def _raise_with_task_id():
        raise ContentionDenied("test pair frontdoor+worker blocked")

    client = TestClient(app)
    resp = client.get(
        "/__test_contention_denied_progress",
        headers={"x-task-id": "task-contention-1"},
    )

    assert resp.status_code == 503
    state.progress_logger.log.assert_called_once()
    entry = state.progress_logger.log.call_args.args[0]
    assert entry.task_id == "task-contention-1"
    assert entry.event_type.value == "routing_fallback"
    assert entry.data["kind"] == "contention_denied"
    assert entry.data["retry_after_s"] == 5
    assert "frontdoor" in entry.data["detail"]
    state.progress_logger.flush.assert_called_once()
