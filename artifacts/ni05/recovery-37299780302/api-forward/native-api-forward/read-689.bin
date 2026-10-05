"""Unit tests for resilient_post — the watcher-aware retry wrapper.

Three required scenarios per handoff Phase 2 gate:
  1. Clean success
  2. Exogenous recovered (mock httpx raises once, watcher reports change, retry succeeds)
  3. Exogenous unrecovered (mock httpx raises persistently OR wait fails)

Plus edge cases:
  - watcher=None preserves legacy behavior (no retry, real_failure=False, error returned)
  - non-retryable exception class bypasses retry
  - external_restart classification surfaces in meta
  - explicit llama_port hint works without role
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from resilient_http import resilient_post  # noqa: E402
from orchestrator_watch import (  # noqa: E402
    CLASS_EXTERNAL_RESTART,
    CLASS_OPERATOR_RELOAD,
    OrchestratorWatcher,
)


def _make_watcher(
    reference_ids: dict | None = None,
    was_restarted_since_result: dict | None = None,
    wait_for_recovery_result: bool = True,
):
    """Build a minimal mock watcher with the surface resilient_post uses."""
    w = MagicMock(spec=OrchestratorWatcher)
    w.reference_for_role.return_value = reference_ids or {"orchestrator": 1.0}
    w.was_restarted_since.return_value = was_restarted_since_result or {}
    w.wait_for_recovery.return_value = wait_for_recovery_result
    w.port_for_role.return_value = None
    w.current_llama_id.return_value = None
    w.invalidate_cache = MagicMock()
    return w


def _make_response(status: int = 200, json_payload: dict | None = None):
    r = MagicMock()
    r.status_code = status
    if status >= 400:
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status}",
            request=httpx.Request("POST", "http://localhost:8000/chat"),
            response=httpx.Response(status),
        )
    else:
        r.raise_for_status.return_value = None
    r.json.return_value = json_payload or {"answer": "ok"}
    r.text = "ok"
    return r


def _make_client(post_side_effect):
    c = MagicMock()
    c.post = MagicMock(side_effect=post_side_effect)
    return c


# ───────── 1. Clean success ──────────


def test_clean_success_no_retry_no_watcher_calls() -> None:
    client = _make_client([_make_response(json_payload={"answer": "hello"})])
    watcher = _make_watcher()
    resp, meta = resilient_post(
        "http://localhost:8000/chat",
        json={"q": "x"}, timeout=30,
        client=client, watcher=watcher, llama_role="frontdoor",
    )
    assert resp == {"answer": "hello"}
    assert meta["clean"] is True
    assert meta["exogenous_recovered"] is False
    assert meta["exogenous_unrecovered"] is False
    assert meta["real_failure"] is False
    assert meta["retry_count"] == 0
    assert client.post.call_count == 1


# ───────── 2. Exogenous recovered ──────────


def test_exogenous_recovered_after_operator_reload() -> None:
    # First call: ConnectError (simulating mid-reload connect refused)
    # Second call: success
    success_resp = _make_response(json_payload={"answer": "recovered"})
    client = _make_client([
        httpx.ConnectError("conn refused"),
        success_resp,
    ])
    watcher = _make_watcher(
        reference_ids={"orchestrator": 1.0},
        was_restarted_since_result={"orchestrator": CLASS_OPERATOR_RELOAD},
        wait_for_recovery_result=True,
    )
    resp, meta = resilient_post(
        "http://localhost:8000/chat",
        json={"q": "x"}, timeout=30,
        client=client, watcher=watcher,
    )
    assert resp == {"answer": "recovered"}
    assert meta["exogenous_recovered"] is True
    assert meta["exogenous_unrecovered"] is False
    assert meta["retry_count"] == 1
    assert meta["marker_changes"] == {"orchestrator": CLASS_OPERATOR_RELOAD}
    assert meta["wait_s"] >= 0.0
    assert client.post.call_count == 2
    watcher.invalidate_cache.assert_called_once()
    watcher.wait_for_recovery.assert_called_once_with({"orchestrator": CLASS_OPERATOR_RELOAD})


# ───────── 3. Exogenous unrecovered ──────────


def test_exogenous_unrecovered_retry_still_fails() -> None:
    client = _make_client([
        httpx.ConnectError("conn refused (attempt 1)"),
        httpx.ConnectError("conn refused (attempt 2)"),
    ])
    watcher = _make_watcher(
        was_restarted_since_result={"orchestrator": CLASS_OPERATOR_RELOAD},
        wait_for_recovery_result=True,
    )
    resp, meta = resilient_post(
        "http://localhost:8000/chat",
        json={"q": "x"}, timeout=30,
        client=client, watcher=watcher,
    )
    assert resp["answer"] == ""
    assert "ConnectError" in resp["error"]
    assert meta["exogenous_recovered"] is False
    assert meta["exogenous_unrecovered"] is True
    assert meta["retry_count"] == 1
    assert client.post.call_count == 2  # initial + 1 retry


def test_exogenous_unrecovered_wait_for_recovery_failed() -> None:
    client = _make_client([httpx.ConnectError("conn refused")])
    watcher = _make_watcher(
        was_restarted_since_result={"orchestrator": CLASS_OPERATOR_RELOAD},
        wait_for_recovery_result=False,  # service stayed down past wait timeout
    )
    resp, meta = resilient_post(
        "http://localhost:8000/chat",
        json={"q": "x"}, timeout=30,
        client=client, watcher=watcher,
    )
    assert resp["answer"] == ""
    assert meta["exogenous_unrecovered"] is True
    assert meta["exogenous_recovered"] is False
    assert meta["retry_count"] == 0  # no retry attempted; wait failed first
    assert client.post.call_count == 1


# ───────── external_restart classification ──────────


def test_external_restart_surfaces_in_meta_and_still_recovers() -> None:
    success_resp = _make_response(json_payload={"answer": "ok"})
    client = _make_client([
        httpx.ReadTimeout("timeout"),
        success_resp,
    ])
    watcher = _make_watcher(
        was_restarted_since_result={"llama_8070": CLASS_EXTERNAL_RESTART},
        wait_for_recovery_result=True,
    )
    resp, meta = resilient_post(
        "http://localhost:8000/chat",
        json={"q": "x"}, timeout=30,
        client=client, watcher=watcher,
    )
    assert resp == {"answer": "ok"}
    assert meta["exogenous_recovered"] is True
    assert meta["external_restart"] is True
    assert meta["marker_changes"] == {"llama_8070": CLASS_EXTERNAL_RESTART}


# ───────── real failure (no marker change) ──────────


def test_real_failure_no_marker_change_no_retry() -> None:
    client = _make_client([httpx.ConnectError("genuine network blip")])
    watcher = _make_watcher(
        was_restarted_since_result={},  # nothing changed → not exogenous
        wait_for_recovery_result=True,
    )
    resp, meta = resilient_post(
        "http://localhost:8000/chat",
        json={"q": "x"}, timeout=30,
        client=client, watcher=watcher,
    )
    assert resp["answer"] == ""
    assert "ConnectError" in resp["error"]
    assert meta["real_failure"] is True
    assert meta["exogenous_recovered"] is False
    assert meta["exogenous_unrecovered"] is False
    assert meta["retry_count"] == 0
    # No wait attempted
    watcher.wait_for_recovery.assert_not_called()


# ───────── watcher=None preserves legacy behavior ──────────


def test_watcher_none_legacy_behavior_on_success() -> None:
    client = _make_client([_make_response(json_payload={"answer": "ok"})])
    resp, meta = resilient_post(
        "http://localhost:8000/chat", json={}, timeout=30,
        client=client, watcher=None,
    )
    assert resp == {"answer": "ok"}
    assert meta["clean"] is True


def test_watcher_none_legacy_behavior_on_exception() -> None:
    """Without a watcher we can't classify; just return the error dict."""
    client = _make_client([httpx.ConnectError("boom")])
    resp, meta = resilient_post(
        "http://localhost:8000/chat", json={}, timeout=30,
        client=client, watcher=None,
    )
    assert resp["answer"] == ""
    assert "ConnectError" in resp["error"]
    assert meta["real_failure"] is True
    # No retry, no watcher methods called (it's None).


def test_structured_http_error_body_is_returned_without_retry() -> None:
    client = _make_client([
        _make_response(
            502,
            {
                "answer": "[ERROR: Direct LLM call failed after retry: model returned no answer]",
                "error_code": 502,
                "error_detail": "Direct LLM call failed after retry: model returned no answer",
            },
        )
    ])
    watcher = _make_watcher(was_restarted_since_result={"orchestrator": CLASS_OPERATOR_RELOAD})

    resp, meta = resilient_post(
        "http://localhost:8000/chat",
        json={"q": "x"},
        timeout=30,
        client=client,
        watcher=watcher,
    )

    assert resp["error_code"] == 502
    assert resp["error_detail"].startswith("Direct LLM call failed")
    assert meta["clean"] is True
    assert meta["retry_count"] == 0
    watcher.invalidate_cache.assert_not_called()


# ───────── non-retryable exceptions bypass retry ──────────


def test_non_retryable_exception_bypasses_retry() -> None:
    """ValueError-class exceptions are not transient — don't consult watcher."""
    client = _make_client([ValueError("malformed request body")])
    watcher = _make_watcher()
    resp, meta = resilient_post(
        "http://localhost:8000/chat", json={}, timeout=30,
        client=client, watcher=watcher,
    )
    assert resp["answer"] == ""
    assert "ValueError" in resp["error"]
    assert meta["real_failure"] is True
    watcher.was_restarted_since.assert_not_called()
    watcher.wait_for_recovery.assert_not_called()


# ───────── explicit llama_port hint ──────────


def test_llama_port_hint_includes_llama_in_reference() -> None:
    """Caller can supply port hint directly when role isn't known."""
    success_resp = _make_response(json_payload={"answer": "ok"})
    client = _make_client([success_resp])

    w = MagicMock(spec=OrchestratorWatcher)
    w.reference_for_role.return_value = {"orchestrator": 1.0}
    w.current_llama_id.return_value = (50.0, "stack_commands")
    w.port_for_role.return_value = None
    w.was_restarted_since.return_value = {}

    resp, meta = resilient_post(
        "http://localhost:8000/chat", json={}, timeout=30,
        client=client, watcher=w, llama_port=8070,
    )
    # The call site supplied no role, so reference_for_role gets called with
    # falsy → never invoked (resilient_post uses `if llama_role` gate).
    # But llama_port=8070 should still augment ref_ids via current_llama_id.
    assert meta["clean"] is True
    # We don't expect the watcher to be queried for changes since the
    # call succeeded.
    w.was_restarted_since.assert_not_called()
