"""Offline candidate tests; all persistence targets pytest's temporary directory."""

import importlib
import sqlite3
import time
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
from src.api.routes.chat_pipeline import stages
from src.trace import approval_live as live


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    path = tmp_path / "events.sqlite"
    monkeypatch.setattr(live, "DEFAULT_DB_PATH", path)
    monkeypatch.setattr(stages, "features", lambda: NS(generation_monitor=True))
    monkeypatch.setattr(stages, "_detect_output_quality_issue", lambda _: "repetition")
    return path


def records(path):
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return list(conn.execute("SELECT * FROM approval_record ORDER BY id"))


def fake_primitives():
    p = NS(
        llm_call=MagicMock(return_value="better answer"),
        registry=NS(get_role=lambda role: NS(model=NS(name="model-" + role))),
        total_tokens_generated=10,
        total_prompt_eval_ms=1.0,
        total_generation_ms=1.0,
        total_http_overhead_ms=0.0,
        _last_predicted_tps=10.0,
        _backends={},
        get_last_inference_meta=dict,
    )
    return p


def quality(p, **kwargs):
    return stages._quality_escalate(
        "poor answer", "private prompt", p, "frontdoor", request_id="req-ure2", **kwargs
    )


def test_exactly_one_linked_record_per_quality_escalation(isolated_store):
    p = fake_primitives()
    assert quality(p)[0] == "better answer"
    (row,) = records(isolated_store)
    assert row["request_id"] == "req-ure2"
    assert row["selected_role"] == "coder_escalation"
    assert row["selected_model"] == "model-coder_escalation"
    assert row["quality_score"] is None and row["uncertainty_score"] is None
    assert row["actor"] == "system" and row["downstream_outcome"] == "returned"
    assert (
        row["approval_boundary"] == "re-answer this request once with the selected role"
    )
    with sqlite3.connect(isolated_store) as conn:
        (signature,) = conn.execute(
            "SELECT signature_confidence FROM behavior_signature WHERE id=?",
            (row["behavior_signature_id"],),
        ).fetchone()
        assert signature == "partial"
    assert "private prompt" not in isolated_store.read_bytes().decode(errors="ignore")
    # Repeated decisions must not collapse just because request/target match.
    quality(p)
    assert len(records(isolated_store)) == 2


@pytest.mark.parametrize(
    "result,outcome", [("", "empty"), ("[ERROR: unavailable]", "in_band_error")]
)
def test_non_answers_are_retained(isolated_store, result, outcome):
    p = fake_primitives()
    p.llm_call.return_value = result
    quality(p)
    (row,) = records(isolated_store)
    assert row["downstream_outcome"] == outcome


def test_exception_recorded_and_existing_fallback_preserved(isolated_store):
    p = fake_primitives()
    p.llm_call.side_effect = TimeoutError("offline failure")
    assert quality(p) == ("poor answer", "frontdoor")
    (row,) = records(isolated_store)
    assert row["downstream_outcome"] == "raised:TimeoutError"
    with pytest.raises(TimeoutError):
        quality(p, force=True)
    assert len(records(isolated_store)) == 2


def test_disabled_or_untriggered_paths_do_not_write(isolated_store, monkeypatch):
    p = fake_primitives()
    quality(p, allow_escalation=False)
    monkeypatch.setattr(stages, "_detect_output_quality_issue", lambda _: None)
    quality(p)
    p.llm_call.assert_not_called()
    assert records(isolated_store) == []


def test_pair_rolls_back_when_approval_insert_fails(isolated_store, monkeypatch):
    def fail(*args):
        raise sqlite3.OperationalError("injected failure")

    monkeypatch.setattr(live, "insert_approval_record", fail)
    assert quality(fake_primitives())[0] == "better answer"
    with sqlite3.connect(isolated_store) as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM behavior_signature").fetchone()[0] == 0
        )
        assert conn.execute("SELECT COUNT(*) FROM approval_record").fetchone()[0] == 0


def test_unwritable_store_does_not_change_answer(isolated_store, monkeypatch):
    monkeypatch.setattr(live, "DEFAULT_DB_PATH", isolated_store.parent)
    assert quality(fake_primitives())[0] == "better answer"


def test_graph_transition_writes_without_progress_logger(isolated_store):
    from src.graph.observability import _log_escalation

    ctx = NS(
        state=NS(task_id="graph-1", prompt="private task"),
        deps=NS(progress_logger=None, primitives=fake_primitives()),
    )
    _log_escalation(ctx, "frontdoor", "coder_escalation", "retry limit")
    (row,) = records(isolated_store)
    assert row["downstream_outcome"] == "selected_pending_execution"
    assert row["trigger_reason"] == "retry limit"


def test_v1_hook_and_receipt_do_not_duplicate_the_shared_write(isolated_store):
    from src.api.routes import v1_escalation as v1

    p = fake_primitives()
    p.total_calls = 0

    def answer(*args, **kwargs):
        p.total_calls += 1
        return "better answer"

    p.llm_call.side_effect = answer
    plan = v1.plan_v1_escalation(
        flag_on=True,
        requested="auto",
        role="frontdoor",
        role_override=False,
        image_input=False,
    )
    assert (
        v1.escalate_answer(
            plan,
            stage="direct",
            answer="poor answer",
            question="task",
            direct_prompt="task",
            primitives=p,
            state=NS(),
            chat_id="v1-approval-1",
        )
        == "better answer"
    )
    for _ in range(2):
        v1.record_escalation(
            plan, chat_id="v1-approval-1", request_keys={}, primitives=p
        )
    (row,) = records(isolated_store)
    assert row["request_id"] == "v1-approval-1"


def test_parked_targets_retain_each_attempt(isolated_store, monkeypatch):
    from src.exceptions import RoleParkedError
    from src.roles import Role

    p = fake_primitives()
    monkeypatch.setattr(
        stages,
        "get_escalation_chain",
        lambda _: [Role.CODER_ESCALATION, Role.ARCHITECT_GENERAL],
    )
    p.llm_call.side_effect = [
        RoleParkedError(
            role="coder_escalation", port=8081, holder="test", retry_after_s=1
        ),
        "better answer",
    ]
    assert quality(p)[0] == "better answer"
    rows = records(isolated_store)
    assert [r["downstream_outcome"] for r in rows] == [
        "raised:RoleParkedError",
        "returned",
    ]
    assert [r["selected_role"] for r in rows] == [
        "coder_escalation",
        "architect_general",
    ]


def test_stubbed_chat_turn_records_once(isolated_store, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api import app
    from src.api.routes.chat_pipeline import direct_stage
    from src.api.routes.chat_utils import RoutingResult
    from src.api.state import get_state

    chat = importlib.import_module("src.api.routes.chat")
    p = fake_primitives()
    p.llm_call.side_effect = ["poor answer", "better answer"]
    state = MagicMock()
    state.progress_logger = None
    routing = RoutingResult(
        task_id="chat-1",
        task_ir={},
        use_mock=False,
        routing_decision=["frontdoor"],
        routing_strategy="test",
    )
    monkeypatch.setattr(
        direct_stage, "_truncate_looped_answer", lambda answer, _: answer
    )
    monkeypatch.setattr(direct_stage, "_should_formalize", lambda _: (False, None))

    async def direct_handler(request, state, **kwargs):
        return direct_stage._execute_direct(
            request, routing, p, state, time.perf_counter(), "frontdoor"
        )

    monkeypatch.setattr(chat, "_handle_chat", direct_handler)
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_state] = lambda: state
    try:
        response = TestClient(app).post(
            "/chat",
            json={
                "prompt": "offline test",
                "real_mode": True,
                "request_id": "chat-approval-1",
            },
        )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
    assert response.status_code == 200, response.text
    assert response.json()["answer"] == "better answer"
    assert p.llm_call.call_count == 2
    (row,) = records(isolated_store)
    assert row["request_id"] == "chat-approval-1"
    assert row["behavior_signature_id"] is not None
