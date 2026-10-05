"""Tests for passive task_record.v1 capture in progress logs."""

from __future__ import annotations

import json

from orchestration.repl_memory.progress_logger import ProgressLogger


def _read_events(log_dir):
    paths = sorted(log_dir.glob("*.jsonl"))
    assert len(paths) == 1
    return [json.loads(line) for line in paths[0].read_text().splitlines()]


def test_task_completion_embeds_task_record_v1(tmp_path):
    logger = ProgressLogger(log_dir=tmp_path, buffer_size=100)

    logger.log_task_started(
        task_id="chat-abc12345",
        task_ir={
            "task_type": "code",
            "workload_class": "campaign",
            "objective": "Implement a safe parser",
            "priority": "interactive",
        },
        routing_decision=["coder_escalation", "worker_general"],
        routing_strategy="learned",
    )
    logger.log_task_completed(
        "chat-abc12345",
        success=True,
        details="done",
        completion_meta={
            "producer_role": "coder_escalation",
            "tokens_generated": 42,
        },
    )
    logger.flush()

    events = _read_events(tmp_path)
    assert [event["event_type"] for event in events] == [
        "task_started",
        "routing_decision",
        "task_completed",
    ]
    assert events[0]["data"]["workload_class"] == "campaign"
    record = events[-1]["data"]["task_record_v1"]
    assert record["schema_version"] == "task_record.v1"
    assert record["task_id"] == "chat-abc12345"
    assert record["class"] == "code"
    assert record["workload_class"] == "campaign"
    assert record["prompt_ref"].startswith("progress-text-sha256:")
    assert record["prompt_ref"] != "Implement a safe parser"
    assert record["prompt_chars"] == len("Implement a safe parser")
    assert record["route_taken"] == ["coder_escalation", "worker_general"]
    assert record["routing_strategy"] == "learned"
    assert record["tokens"] == 42
    assert record["outcome"] == "success"
    assert record["wall_s"] >= 0
    assert "completed_ts_utc" in record
    assert "outcome_details_ref" in record


def test_task_completion_without_start_omits_task_record(tmp_path):
    logger = ProgressLogger(log_dir=tmp_path, buffer_size=100)

    logger.log_task_completed(
        "chat-missing",
        success=False,
        details="failed before routing",
        completion_meta={"producer_role": "frontdoor"},
    )
    logger.flush()

    events = _read_events(tmp_path)
    assert events[0]["event_type"] == "task_failed"
    assert "task_record_v1" not in events[0]["data"]


def test_task_record_sums_prompt_and_completion_tokens(tmp_path):
    logger = ProgressLogger(log_dir=tmp_path, buffer_size=100)

    logger.log_task_started(
        task_id="chat-tokened",
        task_ir={"task_type": "chat", "objective": "Count tokens"},
        routing_decision=["frontdoor"],
        routing_strategy="rules",
    )
    logger.log_task_completed(
        "chat-tokened",
        success=True,
        details=None,
        completion_meta={
            "prompt_tokens": 10,
            "completion_tokens": 5,
        },
    )
    logger.flush()

    record = _read_events(tmp_path)[-1]["data"]["task_record_v1"]
    assert record["workload_class"] == "interactive"
    assert record["tokens"] == 15


def test_task_completion_embeds_operator_verdict_refs(tmp_path):
    logger = ProgressLogger(log_dir=tmp_path, buffer_size=100)

    logger.log_task_started(
        task_id="chat-verdict",
        task_ir={"task_type": "review", "objective": "Review a stack-change patch"},
        routing_decision=["architect_general"],
        routing_strategy="operator",
    )
    logger.log_task_completed(
        "chat-verdict",
        success=True,
        completion_meta={"operator_verdict_details": "contains private note"},
        operator_verdict="Accepted",
    )
    logger.flush()

    terminal_event = _read_events(tmp_path)[-1]
    payload = json.dumps(terminal_event)
    assert "contains private note" not in payload
    assert terminal_event["data"]["operator_verdict"] == "accepted"
    assert "operator_verdict_details_ref" in terminal_event["data"]
    record = terminal_event["data"]["task_record_v1"]
    assert record["operator_verdict"] == "accepted"
    assert record["operator_verdict_source"] == "explicit_operator"
    assert record["workload_class"] == "interactive"
    assert "operator_verdict_details_ref" in record
