from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from fastapi.responses import JSONResponse

from src.api.routes import dashboard
from src.runtime.live_telemetry import LiveTelemetryReducer, _merge_worker_frames
import src.runtime.live_telemetry as live_telemetry_module
from src.runtime.live_telemetry import (
    emit_lifecycle_transition,
    lifecycle_context,
    live_telemetry_frame,
    reset_live_telemetry_for_tests,
)
from src.runtime.cpu_region_lock import cpu_region_lock
from orchestration.repl_memory.progress_logger import ProgressLogger


def test_reducer_orders_handoff_and_preserves_identity() -> None:
    reducer = LiveTelemetryReducer(queue_capacity=16, history_capacity=16)
    identity = {
        "request_id": "req-1",
        "task_id": "chat-1",
        "batch_id": "batch-1",
    }
    reducer.emit("queued", role="frontdoor", **identity)
    reducer.emit("route_selected", role="frontdoor", **identity)
    reducer.emit(
        "placement_lease_acquired",
        role="frontdoor",
        lease_token="lease-fd",
        **identity,
    )
    reducer.emit("backend_dispatched", role="frontdoor", port=8070, **identity)
    reducer.emit("first_output", role="frontdoor", port=8070, **identity)
    reducer.emit(
        "placement_lease_released",
        role="frontdoor",
        lease_token="lease-fd",
        **identity,
    )
    reducer.emit(
        "rerouted",
        role="architect_general",
        details={"from_role": "frontdoor", "to_role": "architect_general"},
        **identity,
    )
    reducer.emit("escalated", role="architect_general", port=8083, **identity)

    frame = reducer.frame()

    assert [event["sequence"] for event in frame["transitions"]] == list(range(1, 9))
    assert [event["transition"] for event in frame["transitions"]][-2:] == [
        "rerouted",
        "escalated",
    ]
    request = frame["requests"][0]
    assert request["request_id"] == "req-1"
    assert request["task_id"] == "chat-1"
    assert request["batch_id"] == "batch-1"
    assert request["role"] == "architect_general"
    assert frame["active_leases"] == []


def test_overflow_is_degraded_but_terminal_and_ownership_state_survive() -> None:
    reducer = LiveTelemetryReducer(queue_capacity=2, history_capacity=3)
    reducer.emit(
        "placement_lease_acquired",
        request_id="req-1",
        role="worker_general",
        lease_token="lease-1",
    )
    for _ in range(5):
        reducer.emit("route_selected", request_id="req-1", role="worker_general")
    reducer.emit("completed", request_id="req-1", role="worker_general")

    frame = reducer.frame()

    assert frame["degraded"] is True
    assert frame["overflow"]["total"] > 0
    assert frame["overflow"]["history_evictions"] > 0
    assert frame["batch_activity"]["certificate_valid"] is False
    assert frame["requests"][0]["terminal"] is True
    assert frame["requests"][0]["outcome"] == "completed"
    assert frame["active_leases"][0]["lease_token"] == "lease-1"


def test_batch_activity_tracks_api_entry_until_true_handler_exit() -> None:
    reducer = LiveTelemetryReducer()
    identity = {"request_id": "req-1", "task_id": "chat-1", "batch_id": "batch-1"}
    reducer.emit("queued", **identity)
    reducer.emit("api_request_started", **identity)

    queued = reducer.batch_activity()
    assert queued["event_sequence"] == 2
    assert queued["batches"]["batch-1"]["active_unresolved"] == 1
    assert queued["batches"]["batch-1"]["queued_unresolved"] == 1

    reducer.emit("backend_dispatched", role="frontdoor", port=8070, **identity)
    dispatched = reducer.batch_activity()
    assert dispatched["batches"]["batch-1"]["queued_unresolved"] == 0
    assert dispatched["batches"]["batch-1"]["backend_dispatched_unresolved"] == 1

    # A task terminal signal does not falsely certify handler drain.
    reducer.emit("completed", **identity)
    assert reducer.batch_activity()["batches"]["batch-1"]["active_unresolved"] == 1

    reducer.emit("api_request_finished", details={"outcome": "completed"}, **identity)
    drained = reducer.batch_activity()
    assert drained["batches"]["batch-1"]["active_unresolved"] == 0


def test_cpu_lease_emits_acquire_and_release_with_same_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_REGION_MUTEX", "0")
    reset_live_telemetry_for_tests()

    with lifecycle_context(
        request_id="req-lock",
        task_id="chat-lock",
        batch_id="batch-lock",
        role="frontdoor",
        port=8070,
    ):
        with cpu_region_lock("frontdoor", {"q0"}, request_tag="chat-lock"):
            held = live_telemetry_frame()
            assert len(held["active_leases"]) == 1
            lease_token = held["active_leases"][0]["lease_token"]
            assert held["transitions"][-1]["transition"] == "placement_lease_acquired"

    released = live_telemetry_frame()
    assert released["active_leases"] == []
    assert released["transitions"][-1]["transition"] == "placement_lease_released"
    assert released["transitions"][-1]["lease_token"] == lease_token


def test_progress_logger_preserves_eval_workload_in_lifecycle(tmp_path) -> None:
    reset_live_telemetry_for_tests()
    logger = ProgressLogger(log_dir=tmp_path, buffer_size=100)
    logger.log_task_started(
        task_id="chat-eval",
        task_ir={"task_type": "chat", "objective": "x", "priority": "interactive"},
        routing_decision=["frontdoor"],
        routing_strategy="learned",
        routing_meta={
            "request_id": "api-eval",
            "batch_id": "batch-eval",
            "workload_class": "eval_batch",
            "request_priority": "background",
        },
    )

    frame = live_telemetry_frame()

    assert [event["transition"] for event in frame["transitions"]] == [
        "queued",
        "route_selected",
    ]
    assert frame["transitions"][0]["details"]["workload_class"] == "eval_batch"
    assert frame["transitions"][0]["batch_id"] == "batch-eval"


def test_live_activity_endpoint_is_read_only_and_fail_closed() -> None:
    reset_live_telemetry_for_tests()
    emit_lifecycle_transition(
        "api_request_started",
        request_id="req-endpoint",
        batch_id="batch-endpoint",
    )

    first = json.loads(asyncio.run(dashboard.live_activity()).body)
    second = json.loads(asyncio.run(dashboard.live_activity()).body)

    assert first["certificate_valid"] is True
    assert first["event_sequence"] == second["event_sequence"] == 1
    assert first["batches"]["batch-endpoint"]["active_unresolved"] == 1


def test_snapshot_sse_is_transition_driven_and_frame_coupled(monkeypatch) -> None:
    sequences = iter(((("101", 0), ("102", 0)), (("101", 0), ("102", 1))))
    monotonic = iter((3.0, 3.1, 3.7, 3.8))
    calls = 0

    async def fake_snapshot() -> JSONResponse:
        nonlocal calls
        calls += 1
        return JSONResponse(
            {
                "frame_id": f"frame-{calls}",
                "live_frame": {
                    "frame_id": f"frame-{calls}",
                    "frame_sequence": calls,
                    "event_sequence": calls - 1,
                    "lifecycle": {
                        "source_sequences": {"101": 0, "102": calls - 1},
                    },
                },
                "region_locks": {"frame_id": f"frame-{calls}"},
            }
        )

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(dashboard, "snapshot", fake_snapshot)
    monkeypatch.setattr(dashboard, "live_telemetry_sequence", lambda: next(sequences))
    monkeypatch.setattr(
        dashboard,
        "time",
        SimpleNamespace(monotonic=lambda: next(monotonic)),
    )
    monkeypatch.setattr(dashboard.asyncio, "sleep", no_sleep)

    async def collect() -> list[dict]:
        stream = dashboard._snapshot_payloads()
        return [json.loads(await anext(stream)), json.loads(await anext(stream))]

    frames = asyncio.run(collect())

    assert calls == 2
    assert [frame["frame_id"] for frame in frames] == ["frame-1", "frame-2"]
    assert all(frame["frame_id"] == frame["live_frame"]["frame_id"] for frame in frames)


def _region_with_lease() -> dict:
    return {
        "by_role": {"frontdoor": {}},
        "occupancy": {
            "entries": [
                {
                    "token": "lease-1",
                    "role": "frontdoor",
                    "instance_idx": 0,
                    "capacity": 4,
                    "shared": True,
                }
            ]
        },
        "display_matrix": {
            "rows": [
                {
                    "role": "frontdoor",
                    "cells": [
                        {
                            "state": "active",
                            "shape": "full",
                            "active": 1,
                            "capacity": 4,
                        }
                    ],
                }
            ]
        },
    }


def _watchdog_sample() -> dict:
    return {
        "attempt": 1,
        "max_attempts": 2,
        "frame_started_at": 100.0,
        "placement_before_at": 100.0,
        "slots_started_at": 101.0,
        "slots_completed_at": 102.0,
        "placement_after_at": 103.0,
        "placement_stable": True,
        "slots_poll_meta": {
            "ports": 1,
            "answered": 1,
            "timed_out": 0,
            "unanswered_ports": [],
        },
    }


def test_reconciliation_surfaces_drift_then_recovery_without_overwriting_history() -> None:
    reducer = LiveTelemetryReducer()
    reducer.emit(
        "api_request_started",
        request_id="req-1",
        task_id="chat-1",
        batch_id="batch-1",
        role="frontdoor",
        source_ts=99.0,
    )
    reducer.emit(
        "backend_dispatched",
        request_id="req-1",
        task_id="chat-1",
        batch_id="batch-1",
        role="frontdoor",
        port=8070,
        source_ts=103.5,
    )
    event_frame = reducer.frame()
    original_history = list(event_frame["transitions"])

    drift = dashboard._annotate_live_observability_frame(
        region_locks=_region_with_lease(),
        activity={8070: {"n_total": 4, "n_active": 0, "active_slots": []}},
        port_roles={8070: "frontdoor"},
        structured_requests=[],
        placement_telemetry={"conflict": False, "capacity_conflicts": []},
        sample=_watchdog_sample(),
        tap_observed_at=104.0,
        event_frame=event_frame,
    )
    recovered = dashboard._annotate_live_observability_frame(
        region_locks=_region_with_lease(),
        activity={
            8070: {
                "n_total": 4,
                "n_active": 1,
                "active_slots": [{"task_id": 7}],
            }
        },
        port_roles={8070: "frontdoor"},
        structured_requests=[],
        placement_telemetry={"conflict": False, "capacity_conflicts": []},
        sample=_watchdog_sample(),
        tap_observed_at=104.0,
        event_frame=event_frame,
    )

    assert drift["reconciliation"]["status"] == "drift"
    assert recovered["reconciliation"]["status"] == "agreement"
    assert recovered["reconciliation"]["history_overwritten"] is False
    assert event_frame["transitions"] == original_history
    assert recovered["lifecycle"]["event_sequence"] == 2


def _worker_frame(
    pid: int,
    reducer: LiveTelemetryReducer,
    *,
    source_ts: float = 100.0,
) -> dict:
    frame = reducer.publication_frame()
    frame["process_id"] = pid
    frame["process_start_id"] = f"start-{pid}"
    frame["source_ts"] = source_ts
    frame["source_sequences"] = {str(pid): frame["event_sequence"]}
    frame["batch_activity"]["process_id"] = pid
    for event in frame["transitions"] + frame["pending_transitions"]:
        event["process_id"] = pid
    return frame


def test_host_reducer_aggregates_split_batch_and_vector_sequences() -> None:
    active = LiveTelemetryReducer()
    active.emit("api_request_started", request_id="req-active", batch_id="batch-host")
    drained = LiveTelemetryReducer()
    drained.emit("api_request_started", request_id="req-drained", batch_id="batch-host")
    drained.emit("api_request_finished", request_id="req-drained", batch_id="batch-host")

    merged = _merge_worker_frames(
        {101: _worker_frame(101, active), 102: _worker_frame(102, drained)},
        expected_pids=[101, 102],
        now=101.0,
        stale_after_s=3.0,
    )

    assert merged["source_sequences"] == {"101": 1, "102": 2}
    assert merged["worker_coverage"]["complete"] is True
    assert merged["batch_activity"]["certificate_valid"] is True
    batch = merged["batch_activity"]["batches"]["batch-host"]
    assert batch["active_unresolved"] == 1
    assert batch["worker_pids"] == [101, 102]

    # Any uvicorn worker can serve the dashboard. Merge order/local worker must
    # not change the host certificate or lifecycle watermark.
    alternate = _merge_worker_frames(
        {102: _worker_frame(102, drained), 101: _worker_frame(101, active)},
        expected_pids=[101, 102],
        now=101.0,
        stale_after_s=3.0,
    )
    assert alternate["source_sequences"] == merged["source_sequences"]
    assert alternate["batch_activity"] == merged["batch_activity"]


def test_host_reducer_scales_protected_history_bound_across_workers() -> None:
    pids = list(range(101, 107))
    frames = {}
    for pid in pids:
        reducer = LiveTelemetryReducer()
        for sequence in range(100):
            reducer.emit(
                "api_request_started",
                request_id=f"req-{pid}-{sequence}",
            )
        frame = _worker_frame(pid, reducer)
        assert frame["degraded"] is False
        assert frame["overflow"]["history_critical_evictions"] == 0
        frames[pid] = frame

    merged = _merge_worker_frames(
        frames,
        expected_pids=pids,
        expected_worker_count=6,
        now=101.0,
        stale_after_s=3.0,
    )

    assert len(merged["transitions"]) == 600  # Greater than one worker's 512 bound.
    expected_limits = {
        "worker_count": 6,
        "history_per_worker": 512,
        "history_fleet": 3072,
        "pending_per_worker": 1024,
        "pending_fleet": 6144,
    }
    assert merged["aggregation_limits"] == expected_limits
    assert merged["batch_activity"]["aggregation_limits"] == expected_limits
    assert merged["overflow"]["history_evictions"] == 0
    assert merged["overflow"]["history_critical_evictions"] == 0
    assert merged["degraded"] is False
    assert merged["batch_activity"]["certificate_valid"] is True


def test_host_reducer_fails_closed_for_missing_stale_or_degraded_worker() -> None:
    healthy = LiveTelemetryReducer()
    healthy.emit("api_request_started", request_id="req", batch_id="batch-host")
    stale = _worker_frame(102, LiveTelemetryReducer(), source_ts=90.0)

    incomplete = _merge_worker_frames(
        {101: _worker_frame(101, healthy), 102: stale},
        expected_pids=[101, 102, 103],
        now=101.0,
        stale_after_s=3.0,
    )

    assert incomplete["degraded"] is True
    assert incomplete["batch_activity"]["certificate_valid"] is False
    assert incomplete["worker_coverage"]["missing_pids"] == [103]
    assert incomplete["worker_coverage"]["stale_pids"] == [102]

    incomplete_roster = _merge_worker_frames(
        {101: _worker_frame(101, healthy), 102: _worker_frame(102, LiveTelemetryReducer())},
        expected_pids=[101, 102],
        expected_worker_count=3,
        now=101.0,
        stale_after_s=3.0,
    )
    assert incomplete_roster["worker_coverage"]["roster_incomplete"] is True
    assert incomplete_roster["batch_activity"]["certificate_valid"] is False

    overflowed = LiveTelemetryReducer(queue_capacity=1)
    overflowed.emit("route_selected", request_id="overflow")
    overflowed.emit("route_selected", request_id="overflow")
    overflowed_frame = _worker_frame(102, overflowed)
    assert overflowed_frame["degraded"] is True
    degraded = _merge_worker_frames(
        {101: _worker_frame(101, healthy), 102: overflowed_frame},
        expected_pids=[101, 102],
        now=101.0,
        stale_after_s=3.0,
    )
    assert degraded["batch_activity"]["certificate_valid"] is False
    assert degraded["overflow"]["total"] == 1


def test_configured_worker_count_reads_uvicorn_parent(monkeypatch) -> None:
    monkeypatch.setattr(live_telemetry_module.os, "getppid", lambda: 77)
    monkeypatch.setattr(
        live_telemetry_module,
        "_process_cmdline",
        lambda pid: "python -m uvicorn src.main:app --workers 6" if pid == 77 else "",
    )

    assert live_telemetry_module._configured_api_worker_count() == 6


def test_worker_publication_rejects_pid_reuse(tmp_path, monkeypatch) -> None:
    frame = _worker_frame(4242, LiveTelemetryReducer())
    frame["process_start_id"] = "boot-a"
    monkeypatch.setattr(live_telemetry_module, "_process_start_id", lambda _pid: "boot-a")

    live_telemetry_module._write_worker_state(frame, root=tmp_path)
    assert live_telemetry_module._read_worker_frame(4242, root=tmp_path) == frame

    monkeypatch.setattr(live_telemetry_module, "_process_start_id", lambda _pid: "boot-b")
    assert live_telemetry_module._read_worker_frame(4242, root=tmp_path) is None


def test_worker_publisher_acknowledges_queue_without_losing_history() -> None:
    reducer = LiveTelemetryReducer(queue_capacity=2, history_capacity=4)
    reducer.emit("queued", request_id="req-publish")

    published = reducer.publisher_frame()
    heartbeat = reducer.publisher_frame()

    assert [event["transition"] for event in published["pending_transitions"]] == ["queued"]
    assert heartbeat["pending_transitions"] == []
    assert [event["transition"] for event in heartbeat["transitions"]] == ["queued"]
    assert heartbeat["degraded"] is False
