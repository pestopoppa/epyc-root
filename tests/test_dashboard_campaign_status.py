from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from dashboard import campaign_status as C
from dashboard import loop_status, server

H = "a" * 64


def stamp(age: float = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat().replace(
        "+00:00", "Z")


def body(**changes):
    row = {
        "schema": C.SNAPSHOT_SCHEMA,
        "producer_build": {
            "schema": "epyc.autokernel.loaded_producer_build.v1",
            "scope": "campaign_control_callable_bytecode_and_selected_constants",
            "module": "autokernel.loop.campaign_control",
            "identity_basis": "loaded_callable_bytecode_and_constants_sha256",
            "included_symbols": ["method:CampaignController.snapshot"],
            "excluded_scope": ["campaign_service_transport"],
            "sha256": H,
        },
        "producer_schema": C.SNAPSHOT_SCHEMA,
        "campaign_id": "campaign-1", "config_generation": 1,
        "config_digest": H, "requested_manifest_digest": "b" * 64,
        "supervisor_incarnation": 1, "stream_epoch": 1, "sequence": 1,
        "journal_cursor": 1, "control_revision": 0,
        "generated_at": stamp(), "desired_state": "paused",
        "observed_state": "paused", "command_results": [],
        "active_worker": None, "producer_heartbeat_at": stamp(),
        "last_scientific_result_at": None, "worker_activity_at": None,
        "execution_authorized": False,
        "prerequisite_reason": "explicit resume required",
    }
    row.update(changes)
    return row


def result_v2(operation="pause", *, request_id="request-v2", completed=False,
              control_revision=1, accepted_at=None, **changes):
    accepted_at = accepted_at or stamp()
    desired = "paused" if operation == "pause" else (
        "drained" if operation == "drain" else "running")
    observed = desired if completed else (
        "pausing" if operation == "pause" else
        "draining" if operation == "drain" else "waiting_prerequisite")
    reason = ("already quiescent" if completed else None)
    prerequisite = ("authority unavailable" if operation == "resume" else None)
    if operation == "resume":
        completed = True
        observed = "waiting_prerequisite"
        reason = "waiting on named prerequisite"
    row = {
        "schema": "epyc.autokernel.campaign_command_result.v2",
        "request_id": request_id, "operation": operation, "payload_digest": H,
        "accepted": True, "accepted_at": accepted_at, "completed": completed,
        "completed_at": accepted_at if completed else None,
        "completion_reason": reason if completed else None,
        "control_revision": control_revision, "desired_state": desired,
        "observed_state": observed, "prerequisite_reason": prerequisite,
    }
    row.update(changes)
    return row


def active_worker_v2(**changes):
    row = {
        "worker_id": "worker-v2", "worker_generation": 1,
        "request_id": "worker-request-v2", "plan_digest": "1" * 64,
        "lineage_id": "lineage-v2", "stage_id": "stage-v2",
        "state": "executing", "grant_id": "grant-v2", "grant_generation": 1,
        "container_id": "container-v2", "provider_deadline": 12345.0,
        "deadline_clock_domain": "linux-monotonic:fixture", "control_revision": 1,
        "started_at": stamp(), "activity_at": stamp(),
        "termination_deadline": None, "unresolved_reason": None,
    }
    row.update(changes)
    return row


def body_v2(**changes):
    generated = stamp()
    row = body(schema=C.SNAPSHOT_SCHEMA_V2, producer_schema=C.SNAPSHOT_SCHEMA_V2,
               journal_cursor=0, generated_at=generated,
               producer_heartbeat_at=generated)
    row.update({"execution_capability_available": True,
                "worker_lifecycle_revision": 0})
    row.update(changes)
    return row


def active_body_v2(**changes):
    worker = active_worker_v2()
    row = body_v2(desired_state="running", observed_state="running",
                  prerequisite_reason=None, control_revision=1,
                  worker_lifecycle_revision=1, active_worker=worker,
                  worker_activity_at=worker["activity_at"])
    row.update(changes)
    return row


def body_v3(**changes):
    accounting_body = {
        "schema": "epyc.autokernel.accounting_view.v1", "receipt_count": 0,
        "held_seconds": 0.0, "physical_region_seconds": 0.0,
        "gpu_device_seconds": {}, "memory_byte_seconds": 0.0,
        "beneficiary_seconds": {},
    }
    accounting = accounting_body | {"view_digest": hashlib.sha256(json.dumps(
        accounting_body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    unified = {
        "schema": C.UNIFIED_PROJECTION_SCHEMA,
        "scheduler": {
            "schema": "epyc.autokernel.unified_scheduler_projection.v1",
            "projection_digest": "1" * 64, "config_digest": "2" * 64,
            "policy_digest": "3" * 64, "round_number": 0, "accounting_epoch": 1,
            "capacity": {"schema": "epyc.autokernel.resource_vector.v1",
                         "physical_region_fraction": 0.5, "gpu_devices": ["gpu0"],
                         "memory_reservation_bytes": 1024},
            "pending_selection_digest": None, "status": "available",
            "reason": "controller-owned scheduler projection", "campaign_attempts": 0,
            "campaign_charged_seconds": 0.0, "accounting": accounting,
            "coverage_debt_count": 0,
        },
        "resources": {"schema": "epyc.autokernel.unified_resource_status.v1",
                      "status": "not_connected", "reason": "resource telemetry not connected",
                      "requested": None, "granted": None, "held": None, "used": None},
        "actors": {"schema": "epyc.autokernel.unified_actor_status.v1",
                   "status": "not_connected", "reason": "actor result cache not connected",
                   "clock_semantics": "UTC wall-clock projection; runtime fences remain monotonic",
                   "items": []},
        "evidence": {"schema": "epyc.autokernel.unified_evidence_status.v1",
                     "status": "not_connected", "reason": "evidence frontier not connected",
                     "frontier_digest": None, "lag_seconds": None},
        "candidate": {"schema": "epyc.autokernel.unified_candidate_status.v1",
                      "status": "not_connected", "reason": "candidate projection not connected",
                      "accumulated_identity": None, "validated_identity": None,
                      "frozen_production_identity": None, "validation_debt": None},
        "targets": {"schema": "epyc.autokernel.unified_target_status.v1",
                    "status": "available", "reason": "resolved campaign enrollment",
                    "total": 2, "ready": 1, "prerequisite": 1,
                    "production_enrolled": 1, "seed_enrolled": 1, "items_page_ref": None},
    }
    row = body_v2(schema=C.SNAPSHOT_SCHEMA_V3, producer_schema=C.SNAPSHOT_SCHEMA_V3,
                  unified=unified)
    row.update(changes)
    return row


def health(snapshot=None, **changes):
    source = snapshot or body()
    row = {"schema": C.HEALTH_SCHEMA, "ok": True,
           "transport": "campaign-control-http", "producer": "running",
           "service_build": {
               "schema": "epyc.autokernel.loaded_producer_build.v1",
               "scope": "campaign_service_loaded_transport_bytecode_and_constants",
               "module": "autokernel.loop.campaign_service",
               "identity_basis": "loaded_callable_bytecode_and_constants_sha256",
               "included_symbols": ["make_handler"],
               "excluded_scope": ["campaign_controller"], "sha256": "c" * 64,
           },
           "campaign_id": source["campaign_id"],
           "config_generation": source["config_generation"],
           "config_digest": source["config_digest"],
           "supervisor_incarnation": source["supervisor_incarnation"],
           "stream_epoch": source["stream_epoch"],
           "allowed_origin": "http://127.0.0.1:8100", "error": None}
    row.update(changes)
    return row


class Response:
    def __init__(self, value, *, url=None):
        self.value = value
        self.url = url
        self.closed = False

    def read(self, amount=-1):
        return json.dumps(self.value).encode()[:amount]

    def close(self):
        self.closed = True

    def geturl(self):
        return self.url or "http://127.0.0.1:9999/health"


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.setenv(C.STORE_ROOT_ENV, str(tmp_path))
    monkeypatch.setenv(C.CAMPAIGN_ID_ENV, "campaign-1")
    monkeypatch.setenv(C.CONFIG_GENERATION_ENV, "1")
    monkeypatch.setenv(C.CONFIG_DIGEST_ENV, H)
    return tmp_path


def write(root: Path, value) -> None:
    (root / C.SNAPSHOT_FILENAME).write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture(scope="module")
def research_v2_contract(tmp_path_factory):
    """Snapshots/results emitted by the real research controller, not mirror JSON."""
    configured_research = os.environ.get("EPYC_INFERENCE_RESEARCH_ROOT")
    candidates = ([Path(configured_research)] if configured_research else []) + [
        Path("/workspace/repos/epyc-inference-research"),
    ]
    source_root = next((path for path in candidates if (
        path / "scripts/kernel_rnd/autokernel/loop/campaign_control.py").is_file()), None)
    if source_root is None:
        pytest.skip("optional matching epyc-inference-research producer checkout is unavailable")
    research = source_root / "scripts" / "kernel_rnd"
    sys.path.insert(0, str(research))
    try:
        from autokernel.loop import campaign_control as producer
        from autokernel.loop.test_campaign_control import _command, _resolved
        from autokernel.loop.test_campaign_worker_lifecycle import _request
        from autokernel.loop.test_worker_lifecycle import MockProvider
        if hasattr(producer, "validate_snapshot_v3"):
            from autokernel.loop import scheduling as producer_scheduling
            from autokernel.loop.test_scheduling import config as _scheduler_config
        else:
            producer_scheduling = None
            _scheduler_config = None
    finally:
        sys.path.remove(str(research))

    def _run_captured(controller, request, outcomes, failures):
        try:
            outcomes.append(controller.run_worker_stage(request))
        except BaseException as exc:  # noqa: BLE001 - never lose a thread failure
            failures.append(exc)

    def _install_stage_barrier(controller):
        entered, release = threading.Event(), threading.Event()

        def barrier(phase):
            if phase == "WORKER_STAGE":
                entered.set()
                if not release.wait(2):
                    raise AssertionError("root producer fixture stage barrier timed out")

        controller._worker_lifecycle.fault_hook = barrier
        return entered, release

    root = tmp_path_factory.mktemp("research-v2-producer")
    containers = root / "containers"
    containers.mkdir(mode=0o700)
    resolved = _resolved("root-dashboard-real-v2")
    store = root / "store"
    provider = MockProvider(containers)
    controller = producer.CampaignController(
        resolved, store, snapshot_version=2, lifecycle_provider=provider,
        readiness_check=lambda: (True, None))
    controller.__enter__()
    try:
        initial = controller.publish_snapshot()
        controller.apply_command(_command(resolved, "resume", "resume", 0))
        outcomes, failures = [], []
        stage_entered, stage_release = _install_stage_barrier(controller)
        thread = threading.Thread(target=_run_captured, args=(
            controller, _request(root, 1, "import time; time.sleep(0.15)"),
            outcomes, failures))
        thread.start()
        try:
            assert stage_entered.wait(2)
            active = controller.snapshot()
            assert active["active_worker"]["state"] == "executing"
            pause_ack = controller.apply_command(
                _command(resolved, "pause", "pause", 1))
            settling = controller.publish_snapshot()
        finally:
            stage_release.set()
            thread.join(2)
        assert not thread.is_alive() and not failures and outcomes[0].accepted
        paused = controller.publish_snapshot()
    finally:
        controller.close()
    with producer.CampaignController(
            resolved, store, snapshot_version=2, lifecycle_provider=provider,
            readiness_check=lambda: (True, None)) as restarted:
        restart_paused = restarted.publish_snapshot()
        duplicate_pause = dict(_command(resolved, "pause", "pause", 1),
                               expected_control_revision=999)
        pause_duplicate = restarted.apply_command(duplicate_pause)
        drain_ack = restarted.apply_command(_command(resolved, "drain", "drain", 2))
        drained = restarted.publish_snapshot()
    escalation_containers = root / "escalation-containers"
    escalation_containers.mkdir(mode=0o700)
    escalation_provider = MockProvider(escalation_containers)
    escalation_resolved = _resolved("root-dashboard-real-v2-escalation")
    escalation_controller = producer.CampaignController(
        escalation_resolved, root / "escalation-store", snapshot_version=2,
        lifecycle_provider=escalation_provider, readiness_check=lambda: (True, None))
    escalation_controller.__enter__()
    escalation_outcomes, escalation_failures = [], []
    try:
        escalation_controller.apply_command(
            _command(escalation_resolved, "escalation-resume", "resume", 0))
        escalation_entered, escalation_release = _install_stage_barrier(
            escalation_controller)
        escalation_thread = threading.Thread(target=_run_captured, args=(
            escalation_controller,
            _request(root, 1, "import time; time.sleep(0.15)"),
            escalation_outcomes, escalation_failures))
        escalation_thread.start()
        try:
            assert escalation_entered.wait(2)
            escalation_active = escalation_controller.snapshot()
            assert escalation_active["active_worker"]["state"] == "executing"
            escalation_pause_ack = escalation_controller.apply_command(
                _command(escalation_resolved, "escalation-pause", "pause", 1))
            escalation_pause_snapshot = escalation_controller.publish_snapshot()
            escalation_drain_ack = escalation_controller.apply_command(
                _command(escalation_resolved, "escalation-drain", "drain", 2))
            escalation_draining = escalation_controller.publish_snapshot()
        finally:
            escalation_release.set()
            escalation_thread.join(2)
        assert (not escalation_thread.is_alive() and not escalation_failures
                and escalation_outcomes[0].accepted)
        escalation_drained = escalation_controller.publish_snapshot()
    finally:
        escalation_controller.close()
    pending_containers = root / "pending-containers"
    pending_containers.mkdir(mode=0o700)
    pending_provider = MockProvider(pending_containers)
    acquisition_entered, acquisition_finish = threading.Event(), threading.Event()

    def ambiguous_authorize(_request_value, _container_id, _deadline):
        acquisition_entered.set()
        assert acquisition_finish.wait(1)
        raise TimeoutError("root fixture ambiguous acquisition")

    pending_provider.authorize = ambiguous_authorize
    pending_resolved = _resolved("root-dashboard-real-v2-pending")
    pending_controller = producer.CampaignController(
        pending_resolved, root / "pending-store", snapshot_version=2,
        lifecycle_provider=pending_provider, readiness_check=lambda: (True, None))
    pending_controller.__enter__()
    pending_controller.apply_command(
        _command(pending_resolved, "pending-resume", "resume", 0))
    pending_failures = []

    def attempt_pending():
        try:
            pending_controller.run_worker_stage(_request(root, 1, "pass"))
        except producer.worker_lifecycle_module.ContainmentFailure as exc:
            pending_failures.append(exc)

    pending_thread = threading.Thread(target=attempt_pending)
    pending_thread.start()
    assert acquisition_entered.wait(1)
    pending_acquisition = pending_controller.publish_snapshot()
    acquisition_finish.set()
    pending_thread.join(2)
    assert not pending_thread.is_alive() and pending_failures
    pending_controller.reconcile_workers()
    pending_controller.close()
    v3 = None
    if hasattr(producer, "validate_snapshot_v3"):
        assert producer_scheduling is not None and _scheduler_config is not None
        v3_resolved = _resolved("root-dashboard-real-v3")
        scheduler_config = producer_scheduling.SchedulerConfig.from_dict(
            _scheduler_config() | {"config_id": v3_resolved.campaign_id})
        scheduler_engine = producer_scheduling.SchedulerEngine(
            scheduler_config,
            producer_scheduling.initial_state(scheduler_config, v3_resolved.campaign_id))
        v3_store = root / "v3-store"
        with producer.CampaignController(
                v3_resolved, v3_store, snapshot_version=3,
                scheduler_engine=scheduler_engine) as v3_controller:
            v3 = v3_controller.publish_snapshot()
            producer.validate_snapshot_v3(v3)
    return {"initial": initial, "active": active, "pause_ack": pause_ack,
            "settling": settling, "paused": paused, "restart_paused": restart_paused,
            "pause_duplicate": pause_duplicate, "drain_ack": drain_ack,
            "drained": drained, "pending_acquisition": pending_acquisition,
            "escalation_active": escalation_active,
            "escalation_pause_ack": escalation_pause_ack,
            "escalation_pause_snapshot": escalation_pause_snapshot,
            "escalation_drain_ack": escalation_drain_ack,
            "escalation_draining": escalation_draining,
            "escalation_drained": escalation_drained, "v3": v3,
            "v3_fields": sorted(getattr(producer, "SNAPSHOT_V3_FIELDS", ())),
            "v3_schema": getattr(producer, "SNAPSHOT_SCHEMA_V3", None),
            "v3_source": Path(producer.__file__).read_bytes()}


def test_checked_producer_v1_fixture_contract_digest():
    fixture = body(generated_at="2026-09-09T00:00:00Z",
                   producer_heartbeat_at="2026-09-09T00:00:00Z")
    digest = hashlib.sha256(json.dumps(
        fixture, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == "bdfa1d9b472ef649ca64b690da5ce1bf02146d6370dcd5a8628beb1f598555db"
    assert C.validate_snapshot(fixture) == fixture


def test_real_research_v2_producer_round_trips_through_independent_reader(
        research_v2_contract):
    rows = research_v2_contract
    for name in ("initial", "active", "settling", "paused", "restart_paused", "drained"):
        assert C.validate_snapshot(rows[name]) == rows[name], name
    assert rows["active"]["active_worker"]["state"] in {
        "intent", "container_created", "child_captured", "exec_release_intent", "executing"}
    assert rows["active"]["execution_capability_available"] is True
    assert rows["active"]["execution_authorized"] is False
    assert rows["pause_ack"]["accepted"] is True
    assert rows["pause_ack"]["completed"] is False
    assert rows["paused"]["command_results"][-1]["request_id"] == \
        rows["pause_ack"]["request_id"]
    assert rows["paused"]["command_results"][-1]["completed"] is True
    assert rows["pause_duplicate"] == rows["paused"]["command_results"][-1]
    assert rows["drained"]["active_worker"] is None
    assert rows["drained"]["observed_state"] == "drained"
    for name in ("escalation_active", "escalation_pause_snapshot",
                 "escalation_draining", "escalation_drained"):
        assert C.validate_snapshot(rows[name]) == rows[name], name
    superseded = next(result for result in rows["escalation_draining"]["command_results"]
                      if result["request_id"] == rows["escalation_pause_ack"]["request_id"])
    assert superseded["completed"] is True
    assert superseded["desired_state"] == "drained"
    assert superseded["observed_state"] == "draining"
    assert superseded["completion_reason"] == "superseded by a later accepted drain"


def test_real_research_v3_producer_round_trips_through_independent_reader(
        research_v2_contract):
    row = research_v2_contract["v3"]
    if row is None:
        pytest.skip("selected optional research checkout has no snapshot v3 producer")
    assert row["schema"] == research_v2_contract["v3_schema"] == C.SNAPSHOT_SCHEMA_V3
    assert sorted(row) == research_v2_contract["v3_fields"]
    assert C.validate_snapshot(row) == row
    assert row["unified"]["scheduler"]["status"] == "available"
    assert row["unified"]["resources"]["requested"] is None
    assert row["unified"]["targets"]["items_page_ref"] is None
    assert hashlib.sha256(research_v2_contract["v3_source"]).hexdigest()


def test_portable_v3_fixture_retains_v2_commands_and_three_valued_projection():
    result = result_v2("pause")
    row = body_v3(control_revision=1, desired_state="paused", observed_state="pausing",
                  command_results=[result])
    row["unified"]["scheduler"].update(
        status="unknown", reason="projection refresh outcome unknown")
    row["unified"]["targets"].update(
        status="not_connected", reason="target projection not connected")
    validated = C.validate_snapshot(row)
    assert validated["command_results"] == [result]
    assert validated["unified"]["scheduler"]["status"] == "unknown"
    assert validated["unified"]["targets"]["status"] == "not_connected"
    assert validated["unified"]["resources"]["requested"] is None


@pytest.mark.parametrize("mutation", [
    lambda row: row["unified"].update({"invented": {}}),
    lambda row: row["unified"]["resources"].update({"requested": {}}),
    lambda row: row["unified"]["resources"].update({"status": "unknown"}),
    lambda row: row["unified"]["actors"]["items"].append({}),
    lambda row: row["unified"]["evidence"].update({"lag_seconds": 0}),
    lambda row: row["unified"]["candidate"].update({"validated_identity": "label"}),
    lambda row: row["unified"]["targets"].update({"ready": True}),
    lambda row: row["unified"]["targets"].update({"ready": 2}),
    lambda row: row["unified"]["scheduler"].update({"pending_selection_digest": "bad"}),
    lambda row: row["unified"]["scheduler"]["capacity"].update({"grant": True}),
    lambda row: row["unified"]["scheduler"]["accounting"].update({"held_seconds": 1}),
])
def test_v3_nested_projection_mutations_fail_closed(mutation):
    row = body_v3()
    mutation(row)
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(row)


def test_v3_is_a_durable_same_campaign_downgrade_fence():
    v1 = body(campaign_id="migration", sequence=1)
    v2 = body_v2(campaign_id="migration", sequence=2, journal_cursor=2)
    v3 = body_v3(campaign_id="migration", sequence=3, journal_cursor=3)
    assert C.advance_snapshot(v1, v2)["status"] == "accepted"
    assert C.advance_snapshot(v2, v3)["status"] == "accepted"
    downgrade = body_v2(campaign_id="migration", stream_epoch=2, sequence=1,
                        journal_cursor=4, supervisor_incarnation=2)
    with pytest.raises(C.CampaignStatusError, match="downgrade"):
        C.advance_snapshot(v3, downgrade)


@pytest.mark.parametrize("result", [
    result_v2("pause"),
    result_v2("pause", completed=True),
    result_v2("pause", completed=True, desired_state="drained",
              observed_state="draining",
              completion_reason="superseded by a later accepted drain"),
    result_v2("drain"),
    result_v2("drain", completed=True),
    result_v2("resume"),
    result_v2("resume", observed_state="running", prerequisite_reason=None,
              completion_reason="running"),
])
def test_v2_command_semantic_combinations_are_closed(result):
    snapshot = body_v2(control_revision=result["control_revision"],
                       command_results=[result])
    assert C.validate_snapshot(snapshot)["command_results"] == [result]


@pytest.mark.parametrize("changes", [
    {"desired_state": "running", "observed_state": "running", "completed": True,
     "completed_at": stamp(), "completion_reason": "running"},
    {"completed": True, "completed_at": stamp(),
     "completion_reason": "operator says it is probably done", "observed_state": "paused"},
    {"completed": False, "completed_at": None, "completion_reason": None,
     "observed_state": "paused"},
    {"operation": "resume", "desired_state": "running", "observed_state": "running",
     "completed": False, "completed_at": None, "completion_reason": None},
])
def test_v2_command_semantic_mutations_cannot_invent_completion(changes):
    result = result_v2("pause")
    result.update(changes)
    with pytest.raises(C.CampaignStatusError, match="semantics|settling|contradictory"):
        C.validate_snapshot(body_v2(control_revision=1, command_results=[result]))


@pytest.mark.parametrize("snapshot", [
    active_body_v2(desired_state="paused", observed_state="paused"),
    body_v2(desired_state="paused", observed_state="pausing"),
    active_body_v2(observed_state="running"),
])
def test_v2_snapshot_rejects_impossible_worker_quiescence(snapshot):
    if snapshot["active_worker"] is not None and snapshot["observed_state"] == "running":
        snapshot["active_worker"].update(
            state="unresolved", unresolved_reason="cleanup uncertain")
    with pytest.raises(C.CampaignStatusError, match="active worker|settling|unresolved"):
        C.validate_snapshot(snapshot)


@pytest.mark.parametrize("operation,desired,observed", [
    ("pause", "paused", "pausing"),
    ("drain", "drained", "draining"),
])
def test_v2_null_worker_settling_requires_matching_incomplete_result_basis(
        operation, desired, observed):
    result = result_v2(operation)
    snapshot = body_v2(desired_state=desired, observed_state=observed,
                       prerequisite_reason=None, control_revision=1,
                       command_results=[result])
    assert C.validate_snapshot(snapshot) == snapshot
    snapshot["command_results"] = []
    with pytest.raises(C.CampaignStatusError, match="accepted command basis"):
        C.validate_snapshot(snapshot)


def test_v2_null_worker_pending_acquisition_is_the_only_unresolved_null_basis():
    snapshot = body_v2(desired_state="running", observed_state="ownership_unresolved",
                       prerequisite_reason="worker_acquisition_pending:request-v2")
    assert C.validate_snapshot(snapshot) == snapshot
    for malformed in ("worker_acquisition_pending:", "worker_acquisition_pending:   "):
        snapshot["prerequisite_reason"] = malformed
        with pytest.raises(C.CampaignStatusError, match="acquisition-pending"):
            C.validate_snapshot(snapshot)


def test_real_v2_restart_and_late_worker_snapshot_do_not_roll_back(
        research_v2_contract):
    paused = research_v2_contract["paused"]
    restarted = research_v2_contract["restart_paused"]
    advanced = C.advance_snapshot(paused, restarted)
    assert advanced["status"] == "accepted"
    assert restarted["stream_epoch"] > paused["stream_epoch"]
    late = C.advance_snapshot(restarted, research_v2_contract["active"])
    assert late["status"] == "older" and late["snapshot"] == C.validate_snapshot(restarted)
    rollback = json.loads(json.dumps(restarted))
    rollback["sequence"] += 1
    rollback["worker_lifecycle_revision"] -= 1
    with pytest.raises(C.CampaignStatusError, match="worker lifecycle"):
        C.advance_snapshot(restarted, rollback)


def test_unknown_snapshot_version_is_not_an_open_union():
    row = active_body_v2()
    row["schema"] = row["producer_schema"] = "epyc.autokernel.campaign_snapshot.v4"
    with pytest.raises(C.CampaignStatusError, match="unsupported"):
        C.validate_snapshot(row)


@pytest.mark.parametrize("mutation,match", [
    (lambda row: row.update({"execution_capability_available": "yes"}), "capability"),
    (lambda row: row.update({"worker_lifecycle_revision": -1}), "lifecycle"),
    (lambda row: row["active_worker"].update({"state": "future-worker-v3"}), "state"),
    (lambda row: row["active_worker"].update({"provider_deadline": float("inf")}), "finite"),
    (lambda row: row["active_worker"].update({"deadline_clock_domain": ""}), "clock_domain"),
])
def test_v2_worker_mutations_fail_closed(mutation, match):
    row = active_body_v2()
    mutation(row)
    with pytest.raises(C.CampaignStatusError, match=match):
        C.validate_snapshot(row)


def test_v2_preacquisition_pending_intent_is_degraded_not_quiescent(
        research_v2_contract, configured, monkeypatch):
    row = research_v2_contract["pending_acquisition"]
    write(configured, row)
    monkeypatch.setenv(C.CAMPAIGN_ID_ENV, row["campaign_id"])
    monkeypatch.setenv(C.CONFIG_DIGEST_ENV, row["config_digest"])
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    monkeypatch.setenv(C.HUB_ORIGIN_ENV, "http://127.0.0.1:8100")
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(health(row)))
    assert result["state"] == "degraded"
    assert result["controls"]["available"] is False
    assert result["campaign"]["active_worker"] is None


@pytest.mark.parametrize("name", ["active", "paused", "drained"])
def test_real_v2_active_and_intentional_quiescence_are_live_with_live_producer(
        name, research_v2_contract, configured, monkeypatch):
    row = research_v2_contract[name]
    write(configured, row)
    monkeypatch.setenv(C.CAMPAIGN_ID_ENV, row["campaign_id"])
    monkeypatch.setenv(C.CONFIG_DIGEST_ENV, row["config_digest"])
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    monkeypatch.setenv(C.HUB_ORIGIN_ENV, "http://127.0.0.1:8100")
    monkeypatch.setattr(C, "observe_health", lambda *_args, **_kwargs: {
        "state": "live", "matched": True, "reason": "producer fixture",
        "identity": {"allowed_origin": "http://127.0.0.1:8100"}})
    result = C.snapshot()
    assert result["state"] == "live"
    assert result["controls"]["available"] is True
    assert (result["campaign"]["active_worker"] is None) == (name != "active")


def test_v3_disconnected_dependencies_degrade_health_without_disabling_controls(
        configured, monkeypatch):
    row = body_v3()
    write(configured, row)
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    monkeypatch.setenv(C.HUB_ORIGIN_ENV, "http://127.0.0.1:8100")
    monkeypatch.setattr(C, "observe_health", lambda *_args, **_kwargs: {
        "state": "live", "matched": True, "reason": "producer fixture",
        "identity": {"allowed_origin": "http://127.0.0.1:8100"}})
    result = C.snapshot()
    assert result["state"] == "degraded"
    assert result["controls"]["available"] is True
    assert result["campaign"]["unified"]["actors"]["status"] == "not_connected"


def test_v3_disconnected_dependencies_stay_history_when_drained_producer_unknown(
        configured):
    row = body_v3(desired_state="drained", observed_state="drained",
                  prerequisite_reason=None)
    write(configured, row)
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
        OSError("historical producer is unreachable")))
    assert result["health"]["state"] == "unknown"
    assert result["state"] == "history"
    assert result["controls"]["available"] is False
    assert result["campaign"]["unified"]["actors"]["status"] == "not_connected"


def test_v2_null_worker_unresolved_requires_exact_pending_identity():
    row = body_v2()
    row.update({"observed_state": "ownership_unresolved",
                "prerequisite_reason": "looks quiet"})
    with pytest.raises(C.CampaignStatusError, match="acquisition-pending"):
        C.validate_snapshot(row)


def test_unconfigured_is_legacy_and_configured_absence_is_not_legacy(monkeypatch, configured):
    monkeypatch.delenv(C.STORE_ROOT_ENV)
    assert C.snapshot()["state"] == "legacy"
    monkeypatch.setenv(C.STORE_ROOT_ENV, str(configured))
    result = C.snapshot()
    assert result["state"] == "absent" and result["campaign"] is None


def test_malformed_or_wrong_identity_never_falls_back(configured):
    write(configured, {"schema": C.SNAPSHOT_SCHEMA})
    assert C.snapshot()["state"] == "malformed"
    write(configured, body(campaign_id="other"))
    result = C.snapshot()
    assert result["state"] == "malformed"
    assert "identity differs" in result["error"]


@pytest.mark.parametrize("field,value", [
    ("sequence", True), ("stream_epoch", 0), ("config_generation", False),
    ("generated_at", "undated"), ("execution_authorized", True),
    ("active_worker", {}),
])
def test_strict_snapshot_rejects_malformed_authority_fields(field, value):
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(body(**{field: value}))


@pytest.mark.parametrize("mutation", [
    lambda row: row.update({"desired_state": []}),
    lambda row: row.update({"observed_state": {}}),
    lambda row: row["command_results"].append({
        "request_id": "x", "operation": [], "payload_digest": H,
        "accepted": True, "completed": True, "control_revision": 1,
        "desired_state": "paused", "observed_state": "paused",
        "prerequisite_reason": None}),
    lambda row: row["producer_build"].update({1: "mixed key"}),
])
def test_nested_shape_mutations_are_typed_refusals(mutation):
    row = body(control_revision=1)
    mutation(row)
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(row)


def test_validated_snapshot_is_detached_from_mutable_input():
    source = body()
    validated = C.validate_snapshot(source)
    source["producer_build"]["included_symbols"].append("actor mutation")
    source["command_results"].append({})
    assert validated["producer_build"]["included_symbols"] == [
        "method:CampaignController.snapshot"]
    assert validated["command_results"] == []


def test_invalid_utf8_is_malformed_not_legacy(configured):
    (configured / C.SNAPSHOT_FILENAME).write_bytes(b"\xff\xfe")
    result = C.snapshot()
    assert result["configured"] is True and result["state"] == "malformed"


def test_matching_health_makes_paused_or_drained_healthy_without_worker(
        configured, monkeypatch):
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    monkeypatch.setenv(C.HUB_ORIGIN_ENV, "http://127.0.0.1:8100")
    for observed in ("paused", "drained"):
        snapshot = body(desired_state=observed, observed_state=observed,
                        prerequisite_reason=None)
        write(configured, snapshot)
        result = C.snapshot(
            health_opener=lambda *_args, snapshot=snapshot, **_kwargs: Response(
                health(snapshot)))
        assert result["state"] == "live"
        assert result["controls"]["available"] is True
        assert result["campaign"]["active_worker"] is None


@pytest.mark.parametrize("changes", [
    {"transport": "other"}, {"producer": "starting"}, {"producer": []},
    {"ok": False, "producer": "running", "error": "failed"},
    {"ok": True, "producer": "running", "error": "unexpected"},
])
def test_transport_health_contract_is_strict(changes):
    with pytest.raises(C.CampaignStatusError):
        C.validate_health(health(**changes))


def _probe_until_settled(report, opener, cache):
    deadline = time.monotonic() + 1
    while True:
        result = C.observe_health(report, opener=opener, cache=cache)
        if "pending" not in result["reason"]:
            return result
        assert time.monotonic() < deadline
        time.sleep(0.005)


def test_health_probe_is_async_bounded_and_single_owner_under_trickle():
    entered, release = threading.Event(), threading.Event()

    class TrickleResponse(Response):
        def read(self, _amount=-1):
            entered.set()
            release.wait(1)
            raise TimeoutError("trickled response exceeded its read timeout")

    response = TrickleResponse(health())

    def trickle(_request, timeout):
        assert timeout == C.HEALTH_TIMEOUT_S
        return response

    cache = C._HealthProbeCache()
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}
    started = time.monotonic()
    result = C.observe_health(report, opener=trickle, cache=cache)
    elapsed = time.monotonic() - started
    assert result["state"] == "unknown" and elapsed < 0.15
    assert entered.wait(0.2)
    assert cache._thread.is_alive()
    release.set()
    cache.close()
    assert response.closed is True


def test_health_probe_bounds_body_closes_response_and_refuses_redirect():
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}

    class RawResponse(Response):
        def __init__(self, raw, *, url=None):
            super().__init__({}, url=url)
            self.raw = raw

        def read(self, amount=-1):
            return self.raw[:amount]

    oversized = RawResponse(b"x" * (C.MAX_HEALTH_BODY + 1))
    cache = C._HealthProbeCache()
    result = _probe_until_settled(report, lambda *_args, **_kwargs: oversized, cache)
    cache.close()
    assert result["state"] == "unknown" and "too large" in result["reason"]
    assert oversized.closed is True

    redirected = Response(health(), url="http://unrelated.test/health")
    cache = C._HealthProbeCache()
    result = _probe_until_settled(report, lambda *_args, **_kwargs: redirected, cache)
    cache.close()
    assert result["state"] == "unknown" and "redirect" in result["reason"]
    assert redirected.closed is True


def test_health_probe_timeout_is_unknown_without_trusting_old_response():
    cache = C._HealthProbeCache()
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}
    result = _probe_until_settled(
        report, lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("slow")),
        cache)
    cache.close()
    assert result["state"] == "unknown" and "slow" in result["reason"]


def test_expired_health_cache_is_unknown_while_single_owner_refreshes():
    cache = C._HealthProbeCache()
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}
    release = threading.Event()
    blocked = False

    def opener(*_args, **_kwargs):
        if blocked:
            release.wait(1)
            raise TimeoutError("late refresh")
        return Response(health())

    initial = _probe_until_settled(report, opener, cache)
    assert initial["state"] == "live"
    with cache._condition:
        key, _recorded, result = cache._result
        cache._result = (key, time.monotonic() - C.HEALTH_CACHE_TTL_S - 1, result)
    blocked = True
    expired = C.observe_health(report, opener=opener, cache=cache)
    assert expired["state"] == "unknown"
    release.set()
    cache.close()


def test_health_cache_dates_completion_interval_and_has_bounded_idempotent_close():
    class Clock:
        value = 10.0

        def __call__(self):
            return self.value

    clock = Clock()
    cache = C._HealthProbeCache(clock=clock)
    assert cache._thread is None
    report = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}

    def late_response(*_args, **_kwargs):
        clock.value += C.HEALTH_TIMEOUT_S + 1
        return Response(health())

    result = _probe_until_settled(report, late_response, cache)
    assert result["state"] == "unknown" and "too late" in result["reason"]
    for invalid_timeout in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(C.CampaignStatusError, match="finite"):
            C._HealthProbeCache().close(timeout=invalid_timeout)
    assert cache.close() is True and cache.close() is True
    assert C.observe_health(report, opener=late_response, cache=cache)["state"] == "unknown"

    entered, release = threading.Event(), threading.Event()
    blocked_cache = C._HealthProbeCache()

    class BlockedResponse(Response):
        def read(self, _amount=-1):
            entered.set()
            release.wait(1)
            return super().read(_amount)

    C.observe_health(report, opener=lambda *_args, **_kwargs: BlockedResponse(health()),
                     cache=blocked_cache)
    assert entered.wait(0.2)
    assert blocked_cache.close(timeout=0) is False
    assert blocked_cache.close_incomplete is True
    refused = C.observe_health(report, opener=None, cache=blocked_cache)
    assert refused["state"] == "unknown" and "close is incomplete" in refused["reason"]
    release.set()
    assert blocked_cache.close(timeout=1) is True


def test_health_cache_campaign_switch_never_reuses_prior_identity():
    cache = C._HealthProbeCache()
    old = {"snapshot": body(), "gateway_url": "http://127.0.0.1:9999"}
    new_snapshot = body(campaign_id="campaign-2")
    new = {"snapshot": new_snapshot, "gateway_url": "http://127.0.0.1:9999"}
    old_opener = lambda *_args, **_kwargs: Response(health(old["snapshot"]))
    assert _probe_until_settled(old, old_opener, cache)["identity"]["campaign_id"] == "campaign-1"
    new_opener = lambda *_args, **_kwargs: Response(health(new_snapshot))
    switched = _probe_until_settled(new, new_opener, cache)
    cache.close()
    assert switched["identity"]["campaign_id"] == "campaign-2"


def test_fresh_snapshot_without_live_identity_is_history_not_live(configured):
    write(configured, body())
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
        OSError("no service")))
    assert result["state"] == "history"
    assert result["controls"]["available"] is False


def test_new_server_identity_cannot_freshen_old_snapshot(configured, monkeypatch):
    snapshot = body()
    write(configured, snapshot)
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(
        health(snapshot, supervisor_incarnation=2, stream_epoch=2)))
    assert result["state"] == "degraded"
    assert result["health"]["state"] == "mismatch"


def test_stale_heartbeat_and_explicit_transport_failure_are_degraded(
        configured, monkeypatch):
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    stale = body(producer_heartbeat_at=stamp(C.HEARTBEAT_STALE_AFTER_S + 10))
    write(configured, stale)
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(health(stale)))
    assert result["state"] == "degraded"

    drained = body(desired_state="drained", observed_state="drained",
                   prerequisite_reason=None)
    write(configured, drained)
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(
        health(drained, ok=False, producer="failed", error="publisher failed")))
    assert result["state"] == "degraded"
    assert result["health"]["state"] == "failed"


def test_future_clocks_and_nonfinite_now_never_freshen_campaign(configured, monkeypatch):
    future = stamp(-60)
    snapshot = body(generated_at=future, producer_heartbeat_at=future,
                    worker_activity_at=stamp(100), last_scientific_result_at=stamp(10000))
    write(configured, snapshot)
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(health(snapshot)))
    assert result["state"] == "degraded"
    assert result["clocks"]["producer_heartbeat_at"]["state"] == "future"
    assert result["clocks"]["worker_activity_at"]["state"] == "known"
    assert result["clocks"]["last_scientific_result_at"]["state"] == "known"
    for invalid in (True, float("nan"), float("inf"), "now"):
        with pytest.raises(C.CampaignStatusError, match="finite"):
            C.snapshot(now=invalid)


def test_heartbeat_stage_and_scientific_clocks_are_not_collapsed(configured, monkeypatch):
    snapshot = body(producer_heartbeat_at=stamp(5), worker_activity_at=stamp(90),
                    last_scientific_result_at=stamp(7200))
    write(configured, snapshot)
    monkeypatch.setenv(C.GATEWAY_URL_ENV, "http://127.0.0.1:9999")
    result = C.snapshot(health_opener=lambda *_args, **_kwargs: Response(health(snapshot)))
    assert result["state"] == "live"
    clocks = result["clocks"]
    assert clocks["producer_heartbeat_at"]["age_s"] < 30
    assert clocks["worker_activity_at"]["age_s"] > 60
    assert clocks["last_scientific_result_at"]["age_s"] > 7000


def test_snapshot_ordering_duplicate_conflict_rollback_and_explicit_switch():
    first = body(sequence=2, journal_cursor=2)
    assert C.advance_snapshot(first, dict(first))["status"] == "duplicate"
    conflict = dict(first, prerequisite_reason="different historical reason")
    with pytest.raises(C.CampaignStatusError, match="same stream key"):
        C.advance_snapshot(first, conflict)
    assert C.advance_snapshot(first, body(sequence=1))["status"] == "older"
    rollback = body(sequence=3, journal_cursor=1)
    with pytest.raises(C.CampaignStatusError, match="rolls back"):
        C.advance_snapshot(first, rollback)
    switched = body(campaign_id="campaign-2")
    with pytest.raises(C.CampaignStatusError, match="explicit"):
        C.advance_snapshot(first, switched)
    assert C.advance_snapshot(first, switched, allow_campaign_switch=True)["status"] == "switched"


def test_epoch_change_consumes_full_snapshot_and_preserves_revisions():
    first = body(sequence=9, journal_cursor=4, control_revision=2)
    changed = body(stream_epoch=2, sequence=1, supervisor_incarnation=2,
                   journal_cursor=5, control_revision=2)
    result = C.advance_snapshot(first, changed)
    assert result == {"status": "accepted", "snapshot": C.validate_snapshot(changed)}
    with pytest.raises(C.CampaignStatusError, match="incarnation"):
        C.advance_snapshot(first, dict(changed, supervisor_incarnation=1))


def test_same_campaign_protocol_cannot_downgrade_but_v1_can_migrate_to_v2():
    active = active_body_v2()
    downgrade_same_epoch = body(
        campaign_id=active["campaign_id"], config_digest=active["config_digest"],
        requested_manifest_digest=active["requested_manifest_digest"], sequence=2,
        journal_cursor=1, control_revision=1, prerequisite_reason=None)
    downgrade_new_epoch = dict(
        downgrade_same_epoch, stream_epoch=2, sequence=1, supervisor_incarnation=2)
    for candidate in (downgrade_same_epoch, downgrade_new_epoch):
        with pytest.raises(C.CampaignStatusError, match="downgrade"):
            C.advance_snapshot(active, candidate)
    legacy = body()
    migrated = body_v2(sequence=2, journal_cursor=1)
    assert C.advance_snapshot(legacy, migrated)["status"] == "accepted"


def test_command_results_preserve_accepted_separate_from_completed():
    result = {"request_id": "resume-1", "operation": "resume",
              "payload_digest": H, "accepted": True, "completed": False,
              "control_revision": 1, "desired_state": "running",
              "observed_state": "waiting_prerequisite",
              "prerequisite_reason": "authority absent"}
    snapshot = C.validate_snapshot(body(control_revision=1, command_results=[result]))
    assert snapshot["command_results"][0]["accepted"] is True
    assert snapshot["command_results"][0]["completed"] is False


@pytest.mark.parametrize("changes", [
    {"accepted": False}, {"completed": True},
    {"observed_state": "running"}, {"prerequisite_reason": None},
    {"desired_state": "paused"},
])
def test_command_result_contract_refuses_management_contradictions(changes):
    result = {"request_id": "resume-1", "operation": "resume",
              "payload_digest": H, "accepted": True, "completed": False,
              "control_revision": 1, "desired_state": "running",
              "observed_state": "waiting_prerequisite",
              "prerequisite_reason": "authority absent"}
    result.update(changes)
    with pytest.raises(C.CampaignStatusError):
        C.validate_snapshot(body(control_revision=1, command_results=[result]))


def test_configured_malformed_campaign_cannot_hide_behind_fresh_legacy_loop(
        configured, monkeypatch):
    loop_root = configured / "legacy"
    loop_root.mkdir()
    monkeypatch.setenv(loop_status.STORE_ROOT_ENV, str(loop_root))
    (loop_root / loop_status.STATUS_FILENAME).write_text(json.dumps({
        "schema": loop_status.STATUS_SCHEMA, "generated_at": stamp(),
        "stale_after_s": 1800, "state": "running", "iterations_done": 1,
        "measurements_reached": 0, "champion_head": "c" * 40,
    }), encoding="utf-8")
    write(configured, {"schema": C.SNAPSHOT_SCHEMA})
    with server._watchdog_lock:
        server._watchdog_state.clear()
    payload = server.loop_payload()
    assert payload["freshness_state"] == "fresh"
    assert payload["campaign"]["state"] == "malformed"
    code, health_result = server.loop_data_health()
    assert code == 503 and health_result["status"] == "degraded"
    assert "campaign" in health_result["campaign_attention"]
    envelope = server.panel_envelopes()["autokernel_loop"]
    assert envelope["watchdog"]["state"] == "no_timestamp"


def test_selected_live_campaign_replaces_failed_legacy_health_fields(
        configured, monkeypatch):
    loop_root = configured / "failed-legacy"
    loop_root.mkdir()
    monkeypatch.setenv(loop_status.STORE_ROOT_ENV, str(loop_root))
    (loop_root / loop_status.STATUS_FILENAME).write_text(json.dumps({
        "schema": loop_status.STATUS_SCHEMA, "generated_at": stamp(),
        "stale_after_s": 1800, "state": "failed", "iterations_done": 1,
        "measurements_reached": 0, "champion_head": "c" * 40,
    }), encoding="utf-8")
    campaign = body()
    live = {"configured": True, "state": "live", "campaign": campaign,
            "health": {"state": "live", "matched": True, "reason": "fixture"},
            "clocks": {"producer_heartbeat_at": {"age_s": 1}},
            "evidence": "/selected/campaign-snapshot.json"}
    monkeypatch.setattr(C, "snapshot", lambda **_kwargs: live)
    with server._watchdog_lock:
        server._watchdog_state.clear()
    code, result = server.loop_data_health()
    assert code == 200 and result["status"] == "ok"
    assert result["selected_producer"] == "campaign"
    assert result["freshness_state"] == "live" and result["loop_state"] == "paused"
    assert result["evidence"] == "/selected/campaign-snapshot.json"
    assert result["declared_failure"] is None
    assert result["legacy_history"]["state"] == "failed"


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_command_lost_ack_retries_exact_request_and_stale_refresh_cannot_roll_back(
        tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    scripts = re.findall(r"<script[^>]*>(.*?)</script>",
                         page.read_text(encoding="utf-8"), re.DOTALL)
    source = "\n".join(scripts).replace(
        "tick();\nsetInterval(tick, 20000);", "")
    initial = body(sequence=1, journal_cursor=1)
    fresh = body(sequence=2, journal_cursor=1)
    after = body(sequence=3, journal_cursor=2, control_revision=1)
    view = {"configured": True, "state": "live", "campaign": initial,
            "clocks": {}, "controls": {"available": True,
                "gateway_url": "https://gateway.test", "hub_origin": "https://hub.test",
                "reason": None}}
    script = r'''
const fs=require("fs"), {webcrypto}=require("crypto");
global.crypto=webcrypto; global.TextEncoder=TextEncoder;
const made={}; function el(id){return made[id]||(made[id]={id,style:{},classList:{add(){},remove(){},toggle(){}},
  _html:"",set innerHTML(v){this._html=String(v)},get innerHTML(){return this._html},
  set textContent(v){this._text=String(v)},get textContent(){return this._text||""},
  addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el(id+">q")},querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],createElement:()=>el("new"),
  createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};
global.setInterval=()=>0; global.setTimeout=()=>0;
const page=fs.readFileSync(process.argv[2],"utf8"), fixture=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
let snapshots=[fixture.fresh,fixture.after,fixture.fresh], posts=[], commandCalls=0;
global.fetch=async(url,options={})=>{
  if(url.endsWith("/snapshot")){const value=snapshots.shift();return{ok:true,status:200,json:async()=>value};}
  const posted=JSON.parse(options.body);posts.push(posted);commandCalls++;
  if(commandCalls===1)throw new Error("lost ack");
  return{ok:true,status:200,json:async()=>({request_id:posted.request_id,operation:posted.operation,
    payload_digest:posted.payload_digest,accepted:true,completed:true,control_revision:1,
    desired_state:"paused",observed_state:"paused",prerequisite_reason:null})};
};
eval(page+`;globalThis.hooks={renderCampaign,campaignSend,campaignRefreshAuthenticated,
  campaignAcceptSnapshot,renderFetchFailure,setToken:v=>campaignToken=v,pending:()=>campaignPending,
  accepted:()=>campaignAccepted,streamError:()=>campaignStreamError};`);
(async()=>{hooks.renderCampaign({campaign:fixture.view});hooks.setToken("memory-secret");
  await hooks.campaignSend("pause",fixture.view);const first=hooks.pending();
  hooks.renderFetchFailure("hub down");const afterHubFailure=hooks.pending();
  await hooks.campaignSend("drain",fixture.view);const afterDrain=hooks.pending();
  await hooks.campaignSend("pause",fixture.view,true);const afterRetry=hooks.pending();
  let staleError="";try{await hooks.campaignRefreshAuthenticated(fixture.view)}catch(e){staleError=e.message}
  const retained=hooks.accepted();
  let conflictError="";try{hooks.campaignAcceptSnapshot({...retained,requested_manifest_digest:"d".repeat(64)})}
    catch(e){conflictError=e.message}
  let malformedError="";try{hooks.campaignAcceptSnapshot({...retained,sequence:[]})}
    catch(e){malformedError=e.message}
  const malformedStream=hooks.streamError();
  hooks.renderCampaign({campaign:{...fixture.view,state:"live",campaign:fixture.fresh}});
  const staleRender={html:made.campaign._html,badge:made["campaign-badgetxt"]._text,
    drainDisabled:made["campaign-drain"].disabled};
  console.log(JSON.stringify({posts,first,afterHubFailure,afterDrain,afterRetry,retained,staleError,
    conflictError,malformedError,malformedStream,staleRender,
    streamError:hooks.streamError(),status:made["campaign-command-status"]._text||""}));
})().catch(e=>{console.error(e);process.exit(2)});
'''
    page_js = tmp_path / "page.js"
    runner = tmp_path / "runner.js"
    fixture = tmp_path / "fixture.json"
    page_js.write_text(source, encoding="utf-8")
    runner.write_text(script, encoding="utf-8")
    fixture.write_text(json.dumps({"view": view, "fresh": fresh, "after": after}),
                       encoding="utf-8")
    run = subprocess.run(["node", str(runner), str(page_js), str(fixture)],
                         capture_output=True, text=True, timeout=10, check=True)
    result = json.loads(run.stdout)
    assert len(result["posts"]) == 2
    assert result["posts"][0] == result["posts"][1]
    assert result["posts"][0]["operation"] == "pause"
    expected = hashlib.sha256(json.dumps({
        "config_generation": 1, "campaign_id": "campaign-1",
        "operation": "pause", "payload": {}},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert result["posts"][0]["payload_digest"] == expected
    assert result["first"]["request_id"] == result["posts"][0]["request_id"]
    assert result["afterHubFailure"] == result["first"]
    assert result["afterDrain"] == result["first"]
    assert result["afterRetry"] is None
    assert result["retained"]["sequence"] == 3
    assert "older" in result["staleError"]
    assert "same campaign stream key" in result["conflictError"]
    assert "sequence is malformed" in result["malformedError"]
    assert "sequence is malformed" in result["malformedStream"]
    assert "older" in result["streamError"]
    assert "1:3" in result["staleRender"]["html"]
    assert result["staleRender"]["badge"] == "UNKNOWN / HISTORY"
    assert result["staleRender"]["drainDisabled"] is True
    assert "accepted revision 1; completed" in result["status"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_v2_incomplete_ack_settles_only_from_same_request_revision_and_old_ack_loses(
        tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(
        r"<script[^>]*>(.*?)</script>", page.read_text(encoding="utf-8"), re.DOTALL
    )).replace("tick();\nsetInterval(tick, 20000);", "")
    fixture_path = tmp_path / "fixture.json"
    active = active_body_v2()
    paused = body_v2(sequence=2, journal_cursor=1, control_revision=2,
                     worker_lifecycle_revision=2, prerequisite_reason=None)
    drained = body_v2(sequence=3, journal_cursor=2, control_revision=3,
                      worker_lifecycle_revision=2, desired_state="drained",
                      observed_state="drained", prerequisite_reason=None)
    fixture_path.write_text(json.dumps({
        "active": active, "paused": paused, "drained": drained,
    }), encoding="utf-8")
    page_js, runner = tmp_path / "page.js", tmp_path / "runner.js"
    page_js.write_text(source, encoding="utf-8")
    runner.write_text(r'''
const fs=require("fs"),{webcrypto}=require("crypto");global.crypto=webcrypto;
global.TextEncoder=TextEncoder;const made={};function el(id){return made[id]||(made[id]={id,
 style:{},classList:{add(){},remove(){},toggle(){}},_html:"",set innerHTML(v){this._html=String(v)},
 get innerHTML(){return this._html},set textContent(v){this._text=String(v)},get textContent(){return this._text||""},
 addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el(id+">q")},querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],createElement:()=>el("new"),
 createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};
global.setInterval=()=>0;global.setTimeout=()=>0;
const page=fs.readFileSync(process.argv[2],"utf8"),f=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
let current=f.active,posted=[],delayDrain=null,releaseDrain=null;
function resultFor(request,completed){return {schema:"epyc.autokernel.campaign_command_result.v2",
 request_id:request.request_id,operation:request.operation,payload_digest:request.payload_digest,
 accepted:true,accepted_at:current.generated_at,completed,
 completed_at:completed?current.generated_at:null,
 completion_reason:completed?"owned workers quiesced and claims released":null,
 control_revision:request.expected_control_revision+1,
 desired_state:request.operation==="drain"?"drained":"paused",
 observed_state:completed?(request.operation==="drain"?"drained":"paused"):
   (request.operation==="drain"?"draining":"pausing"),prerequisite_reason:null};}
global.fetch=async(url,options={})=>{if(url.endsWith("/snapshot"))return{ok:true,status:200,json:async()=>current};
 const request=JSON.parse(options.body);posted.push(request);const ack=resultFor(request,false);
 if(request.operation==="drain")await new Promise(r=>{releaseDrain=r;delayDrain=ack});
 return{ok:true,status:200,json:async()=>ack};};
eval(page+`;globalThis.h={renderCampaign,campaignSend,setToken:v=>campaignToken=v,
 pending:()=>campaignPending};`);
const envelope=s=>({configured:true,state:"live",campaign:s,clocks:{},controls:{available:true,
 gateway_url:"https://gateway.test",hub_origin:"https://hub.test",reason:null}});
(async()=>{h.renderCampaign({campaign:envelope(current)});const activeHtml=made.campaign._html;
 h.setToken("tab-secret");
 await h.campaignSend("pause",envelope(current));const incomplete={pending:h.pending(),
  status:made["campaign-command-status"]._text};
 const pauseRequest=posted[0],pauseDone=resultFor(pauseRequest,true);
 current={...f.paused,command_results:[...f.active.command_results,pauseDone],control_revision:2};
 h.renderCampaign({campaign:envelope(current)});const settled={pending:h.pending(),
  status:made["campaign-command-status"]._text};
 const delayed=h.campaignSend("drain",envelope(current));
 while(!releaseDrain)await new Promise(r=>setImmediate(r));
 const drainRequest=posted[1],drainDone=resultFor(drainRequest,true);
 current={...f.drained,command_results:[...current.command_results,drainDone],control_revision:3};
 h.renderCampaign({campaign:envelope(current)});releaseDrain();await delayed;
 console.log(JSON.stringify({incomplete,settled,afterDelayed:{pending:h.pending(),
  status:made["campaign-command-status"]._text},posted,delayDrain,activeHtml}));
})().catch(e=>{console.error(e);process.exit(2)});
''', encoding="utf-8")
    result = json.loads(subprocess.run(
        ["node", str(runner), str(page_js), str(fixture_path)], capture_output=True,
        text=True, timeout=10, check=True).stdout)
    assert result["incomplete"]["pending"]["request_id"] == result["posted"][0]["request_id"]
    assert "not completed" in result["incomplete"]["status"]
    assert result["settled"]["pending"] is None
    assert "completed" in result["settled"]["status"]
    assert result["delayDrain"]["completed"] is False
    assert result["afterDelayed"]["pending"] is None
    assert "completed" in result["afterDelayed"]["status"]
    assert "execution capability / current authority" in result["activeHtml"]
    worker = active["active_worker"]
    assert worker["worker_id"] not in result["activeHtml"]
    assert worker["grant_id"] not in result["activeHtml"]
    assert worker["container_id"] not in result["activeHtml"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_real_producer_pause_escalates_to_distinct_drain_atomically(
        research_v2_contract, tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(
        r"<script[^>]*>(.*?)</script>", page.read_text(encoding="utf-8"), re.DOTALL
    )).replace("tick();\nsetInterval(tick, 20000);", "")
    fixtures = {name: research_v2_contract[name] for name in (
        "escalation_active", "escalation_pause_ack", "escalation_pause_snapshot",
        "escalation_drain_ack", "escalation_draining", "escalation_drained")}
    active = fixtures["escalation_active"]
    fixtures["downgrade_same"] = body(
        campaign_id=active["campaign_id"], config_digest=active["config_digest"],
        requested_manifest_digest=active["requested_manifest_digest"],
        sequence=active["sequence"] + 10, journal_cursor=active["journal_cursor"] + 10,
        control_revision=3, prerequisite_reason=None)
    fixtures["downgrade_epoch"] = dict(
        fixtures["downgrade_same"], stream_epoch=active["stream_epoch"] + 1,
        sequence=1, supervisor_incarnation=active["supervisor_incarnation"] + 1)
    fixtures["migration_v1"] = body(campaign_id="protocol-migration")
    fixtures["migration_v2"] = body_v2(
        campaign_id="protocol-migration", sequence=2, journal_cursor=1)
    page_js, runner, fixture = (
        tmp_path / "page.js", tmp_path / "runner.js", tmp_path / "fixture.json")
    page_js.write_text(source, encoding="utf-8")
    fixture.write_text(json.dumps(fixtures), encoding="utf-8")
    runner.write_text(r'''
const fs=require("fs"),{webcrypto}=require("crypto");
const f=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const ids=[f.escalation_pause_ack.request_id,f.escalation_drain_ack.request_id];
Object.defineProperty(global,"crypto",{value:{subtle:webcrypto.subtle,randomUUID:()=>ids.shift()}});
global.TextEncoder=TextEncoder;
const made={};function el(id){return made[id]||(made[id]={id,disabled:false,style:{},
 classList:{add(){},remove(){},toggle(){}},_html:"",set innerHTML(v){this._html=String(v)},
 get innerHTML(){return this._html},set textContent(v){this._text=String(v)},
 get textContent(){return this._text||""},addEventListener(){},setAttribute(){},
 removeAttribute(){},querySelector(){return el(id+">q")},querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],
 createElement:()=>el("new"),createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};
global.setInterval=()=>0;global.setTimeout=()=>0;
const page=fs.readFileSync(process.argv[2],"utf8");let current=f.escalation_active;
let posts=[],releaseDrain=null;
global.fetch=async(url,options={})=>{
 if(url.endsWith("/snapshot"))return{ok:true,status:200,json:async()=>current};
 const request=JSON.parse(options.body);posts.push(request);
 const ack=request.operation==="pause"?f.escalation_pause_ack:f.escalation_drain_ack;
 if(request.operation==="drain")await new Promise(resolve=>releaseDrain=resolve);
 return{ok:true,status:200,json:async()=>ack};
};
eval(page+`;globalThis.h={renderCampaign,campaignSend,setToken:v=>campaignToken=v,
 pending:()=>campaignPending,pendingAck:()=>campaignPendingAck,
 escalated:()=>campaignEscalatedPause,validateAck:campaignValidateAck,
 validateSnapshot:campaignValidateSnapshot,
 acceptSnapshot:campaignAcceptSnapshot,
 failDigestOnce:()=>{const saved=campaignDigest;campaignDigest=async()=>{
   campaignDigest=saved;throw new Error("synthetic digest failure")}}};`);
const envelope=s=>({configured:true,state:"live",campaign:s,clocks:{},controls:{available:true,
 gateway_url:"https://gateway.test",hub_origin:"https://hub.test",reason:null}});
const buttons=()=>({pause:made["campaign-pause"].disabled,resume:made["campaign-resume"].disabled,
 drain:made["campaign-drain"].disabled,retry:made["campaign-retry"].disabled});
(async()=>{
 h.renderCampaign({campaign:envelope(current)});h.setToken("tab-secret");
 await h.campaignSend("pause",envelope(current));
 const afterPause={pending:h.pending(),ack:h.pendingAck(),buttons:buttons()};
 current=f.escalation_pause_snapshot;h.failDigestOnce();
 await h.campaignSend("drain",envelope(current));
 const afterDigestFailure={pending:h.pending(),ack:h.pendingAck(),buttons:buttons(),
   status:made["campaign-command-status"]._text,postCount:posts.length};
 const drainingRequest=h.campaignSend("drain",envelope(current));
 while(!releaseDrain)await new Promise(resolve=>setImmediate(resolve));
 const duringPost={pending:h.pending(),ack:h.pendingAck(),escalated:h.escalated(),buttons:buttons()};
 current=f.escalation_draining;h.renderCampaign({campaign:envelope(current)});
 const newerSnapshot={pending:h.pending(),ack:h.pendingAck(),escalated:h.escalated(),buttons:buttons()};
 releaseDrain();await drainingRequest;
 const afterLateAck={pending:h.pending(),ack:h.pendingAck(),escalated:h.escalated(),buttons:buttons()};
 current=f.escalation_drained;h.renderCampaign({campaign:envelope(current)});
 const completed={pending:h.pending(),ack:h.pendingAck(),escalated:h.escalated(),buttons:buttons()};
 let semanticError="";const invented={...f.escalation_pause_ack,completed:true,
   completed_at:f.escalation_pause_ack.accepted_at,observed_state:"paused",
   completion_reason:"operator says it is probably done"};
 try{h.validateAck(invented)}catch(err){semanticError=err.message}
 let settlingError="";const nullSettling={...f.escalation_pause_snapshot,
   active_worker:null,worker_activity_at:null};h.validateSnapshot(nullSettling);
 try{h.validateSnapshot({...nullSettling,command_results:nullSettling.command_results.filter(
   row=>row.request_id!==f.escalation_pause_ack.request_id)})}
 catch(err){settlingError=err.message}
 let pendingIdentityError="";try{h.validateSnapshot({...nullSettling,
   observed_state:"ownership_unresolved",prerequisite_reason:"worker_acquisition_pending:   "})}
 catch(err){pendingIdentityError=err.message}
 const a=f.escalation_pause_ack;const legacyAck={request_id:a.request_id,
   operation:a.operation,payload_digest:a.payload_digest,accepted:true,completed:true,
   control_revision:a.control_revision,desired_state:"paused",observed_state:"paused",
   prerequisite_reason:null};
 let v1InV2="",v2InV1="",directProtocol="",sameDowngrade="",epochDowngrade="";
 try{h.validateSnapshot({...f.escalation_active,command_results:[legacyAck]})}
 catch(err){v1InV2=err.message}
 try{h.validateSnapshot({...f.downgrade_same,command_results:[a],control_revision:a.control_revision})}
 catch(err){v2InV1=err.message}
 try{h.validateAck(legacyAck,posts[0],true)}catch(err){directProtocol=err.message}
 try{h.acceptSnapshot(f.downgrade_same)}catch(err){sameDowngrade=err.message}
 try{h.acceptSnapshot(f.downgrade_epoch)}catch(err){epochDowngrade=err.message}
 const switched=h.acceptSnapshot(f.migration_v1,true);
 const migrated=h.acceptSnapshot(f.migration_v2);
 console.log(JSON.stringify({posts,afterPause,afterDigestFailure,duringPost,newerSnapshot,
   afterLateAck,completed,semanticError,settlingError,pendingIdentityError,v1InV2,v2InV1,
   directProtocol,sameDowngrade,epochDowngrade,switched,migrated}));
})().catch(err=>{console.error(err);process.exit(2)});
''', encoding="utf-8")
    result = json.loads(subprocess.run(
        ["node", str(runner), str(page_js), str(fixture)], capture_output=True,
        text=True, timeout=10, check=True).stdout)
    assert result["afterPause"]["pending"]["operation"] == "pause"
    assert result["afterPause"]["ack"]["completed"] is False
    assert result["afterPause"]["buttons"] == {
        "pause": True, "resume": True, "drain": False, "retry": True}
    assert result["afterDigestFailure"]["postCount"] == 1
    assert result["afterDigestFailure"]["pending"] == result["afterPause"]["pending"]
    assert result["afterDigestFailure"]["ack"] == result["afterPause"]["ack"]
    assert "synthetic digest failure" in result["afterDigestFailure"]["status"]
    assert result["afterDigestFailure"]["buttons"] == result["afterPause"]["buttons"]
    assert [request["operation"] for request in result["posts"]] == ["pause", "drain"]
    assert result["posts"][0]["request_id"] != result["posts"][1]["request_id"]
    assert [request["expected_control_revision"] for request in result["posts"]] == [1, 2]
    assert result["duringPost"]["pending"]["operation"] == "drain"
    assert result["duringPost"]["escalated"]["request"] == result["posts"][0]
    assert result["newerSnapshot"]["escalated"] is None
    assert result["newerSnapshot"]["ack"]["completed"] is False
    assert result["newerSnapshot"]["buttons"]["resume"] is True
    assert result["afterLateAck"]["pending"]["operation"] == "drain"
    assert result["completed"]["pending"] is None
    assert result["completed"]["ack"] is None
    assert "semantics are contradictory" in result["semanticError"]
    assert "accepted command basis" in result["settlingError"]
    assert "pending acquisition identity" in result["pendingIdentityError"]
    assert "result protocol" in result["v1InV2"]
    assert "result protocol" in result["v2InV1"]
    assert "acknowledgment protocol" in result["directProtocol"]
    assert "downgrade" in result["sameDowngrade"]
    assert "downgrade" in result["epochDowngrade"]
    assert result["switched"] is True and result["migrated"] is True


def test_page_keeps_token_memory_only_and_has_no_hub_control_proxy():
    page = (Path(__file__).resolve().parents[1] / "dashboard/static/loop.html").read_text(
        encoding="utf-8")
    assert "localStorage" not in page and "sessionStorage" not in page
    assert "Bearer ${campaignToken}" in page
    assert "/api/campaign" not in page
    assert "secure browser context" in page
    assert "campaign-retry" in page
    assert "AbortController" in page


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_executes_real_v3_projection_and_preserves_downgrade_fence(
        research_v2_contract, tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(
        r"<script[^>]*>(.*?)</script>", page.read_text(encoding="utf-8"), re.DOTALL
    )).replace("tick();\nsetInterval(tick, 20000);", "")
    v3 = research_v2_contract["v3"]
    if v3 is None:
        pytest.skip("selected optional research checkout has no snapshot v3 producer")
    v2 = {key: value for key, value in v3.items() if key != "unified"}
    v2.update(schema=C.SNAPSHOT_SCHEMA_V2, producer_schema=C.SNAPSHOT_SCHEMA_V2,
              stream_epoch=v3["stream_epoch"] + 1, sequence=1,
              supervisor_incarnation=v3["supervisor_incarnation"] + 1)
    settling = body_v3(control_revision=1, desired_state="paused", observed_state="pausing",
                       command_results=[result_v2("pause")])
    page_js, runner, fixture = tmp_path / "page.js", tmp_path / "runner.js", tmp_path / "v3.json"
    page_js.write_text(source, encoding="utf-8")
    fixture.write_text(json.dumps({"v3": v3, "v2": v2, "settling": settling}),
                       encoding="utf-8")
    runner.write_text(r'''
const fs=require("fs"),{webcrypto}=require("crypto");global.crypto=webcrypto;
global.TextEncoder=TextEncoder;const made={};function el(id){return made[id]||(made[id]={id,
 disabled:false,style:{},classList:{add(){},remove(){},toggle(){}},_html:"",
 set innerHTML(v){this._html=String(v)},get innerHTML(){return this._html},
 set textContent(v){this._text=String(v)},get textContent(){return this._text||""},
 addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el(id+">q")},
 querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],
 createElement:()=>el("new"),createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};
global.setInterval=()=>0;global.setTimeout=()=>0;
const page=fs.readFileSync(process.argv[2],"utf8"),f=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
eval(page+`;globalThis.h={validate:campaignValidateSnapshot,accept:campaignAcceptSnapshot,
 render:renderCampaign,send:campaignSend,token:value=>campaignToken=value,
 pending:()=>campaignPending};`);
(async()=>{h.validate(f.v3);h.validate(f.settling);let posted=null;
 let unknownField="",disconnectedNonNull="";
 const unknown=JSON.parse(JSON.stringify(f.v3));unknown.unified.scheduler.invented={};
 try{h.validate(unknown)}catch(err){unknownField=err.message}
 const nonNull=JSON.parse(JSON.stringify(f.v3));nonNull.unified.resources.requested={cpu:"claimed"};
 try{h.validate(nonNull)}catch(err){disconnectedNonNull=err.message}
 const view={configured:true,state:"degraded",campaign:f.v3,clocks:{},controls:{available:true,
   gateway_url:"https://gateway.test",reason:null}};
 global.fetch=async(url,options={})=>{if(url.endsWith("/snapshot"))
   return{ok:true,status:200,json:async()=>f.v3};posted=JSON.parse(options.body);
   return{ok:true,status:200,json:async()=>({schema:"epyc.autokernel.campaign_command_result.v2",
     request_id:posted.request_id,operation:posted.operation,payload_digest:posted.payload_digest,
     accepted:true,accepted_at:f.v3.generated_at,completed:true,completed_at:f.v3.generated_at,
     completion_reason:"already quiescent",control_revision:posted.expected_control_revision+1,
     desired_state:"paused",observed_state:"paused",prerequisite_reason:null})};};
 h.render({campaign:view});h.token("fixture-token");await h.send("pause",view);
 let downgrade="";try{h.accept(f.v2)}catch(err){downgrade=err.message}
 console.log(JSON.stringify({html:made.campaign._html,downgrade,unknownField,disconnectedNonNull,
   posted,pending:h.pending(),
   command:made["campaign-command-status"]._text,badge:made["campaign-badgetxt"]._text}));
})().catch(err=>{console.error(err);process.exit(2)});
''', encoding="utf-8")
    result = json.loads(subprocess.run(
        ["node", str(runner), str(page_js), str(fixture)], capture_output=True,
        text=True, timeout=10, check=True).stdout)
    assert result["badge"] == "DEGRADED"
    assert "declared scheduling capacity (not a grant)" in result["html"]
    assert "resources · not_connected" in result["html"]
    assert "unknown / not connected" in result["html"]
    assert "none promised" in result["html"]
    assert "downgrade" in result["downgrade"]
    assert "unsupported fields" in result["unknownField"]
    assert "must remain null/empty" in result["disconnectedNonNull"]
    assert result["posted"]["operation"] == "pause"
    assert result["pending"] is None
    assert "completed" in result["command"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_total_body_deadline_size_and_parse_fail_closed(tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(
        r"<script[^>]*>(.*?)</script>", page.read_text(encoding="utf-8"), re.DOTALL
    )).replace("tick();\nsetInterval(tick, 20000);", "")
    initial, fresh = body(), body(sequence=2)
    view = {"configured": True, "state": "live", "campaign": initial,
            "clocks": {}, "controls": {"available": True,
                "gateway_url": "https://gateway.test", "reason": None}}
    script = r'''
const fs=require("fs"),{webcrypto}=require("crypto");global.crypto=webcrypto;
global.TextEncoder=TextEncoder;const made={};function el(id){return made[id]||(made[id]={id,
 style:{},classList:{add(){},remove(){},toggle(){}},_html:"",set innerHTML(v){this._html=String(v)},
 get innerHTML(){return this._html},set textContent(v){this._text=String(v)},get textContent(){return this._text||""},
 addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el(id+">q")},querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],createElement:()=>el("new"),
 createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};global.setInterval=()=>0;
let timers=[];global.setTimeout=fn=>{const row={fn,active:true};timers.push(row);return row};
global.clearTimeout=row=>{if(row)row.active=false};const fire=()=>{const row=[...timers].reverse().find(x=>x.active);row.fn()};
const page=fs.readFileSync(process.argv[2],"utf8"),f=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
eval(page+`;globalThis.h={campaignFetch,renderCampaign,campaignSend,
 validateAck:campaignValidateAck,validateSnapshot:campaignValidateSnapshot,
 setToken:v=>campaignToken=v,pending:()=>campaignPending,inflight:()=>campaignInFlight};`);
function stalled(signal,mark){let started=false,cancelled=false,aborted=false;
 signal.addEventListener("abort",()=>aborted=true);const reader={read(){started=true;return new Promise(()=>{})},
 cancel(){cancelled=true;return Promise.resolve()}};mark(()=>({started,cancelled,aborted}));
 return{ok:true,status:200,body:{getReader:()=>reader}}}
(async()=>{
 let inspect,readState,snapshotError="";global.fetch=async(_url,o)=>stalled(o.signal,x=>{inspect=x});
 const snapshot=h.campaignFetch("https://gateway.test/snapshot",{},100).catch(e=>snapshotError=e.message);
 while(!inspect||!inspect().started)await new Promise(r=>setImmediate(r));fire();await snapshot;readState=inspect();
 let oversized="";global.fetch=async()=>({ok:true,status:200,text:async()=>"x".repeat(101)});
 await h.campaignFetch("x",{},100).catch(e=>oversized=e.message);
 let malformed="";global.fetch=async()=>({ok:true,status:200,text:async()=>"{"});
 await h.campaignFetch("x",{},100).catch(e=>malformed=e.message);
 let revisionError="";try{h.validateAck({request_id:"r",operation:"pause",payload_digest:"a".repeat(64),
  accepted:true,completed:true,control_revision:2,desired_state:"paused",observed_state:"paused",
  prerequisite_reason:null},{request_id:"r",operation:"pause",payload_digest:"a".repeat(64),
  expected_control_revision:0})}catch(e){revisionError=e.message}
 let clockError="";try{h.validateSnapshot({...f.fresh,producer_heartbeat_at:
  new Date(Date.parse(f.fresh.generated_at)+6000).toISOString()})}catch(e){clockError=e.message}
 h.renderCampaign({campaign:f.view});h.setToken("secret");let calls=0,ackInspect;
 global.fetch=async(_url,o)=>{calls++;if(calls===1)return{ok:true,status:200,json:async()=>f.fresh};
  return stalled(o.signal,x=>{ackInspect=x})};
 const command=h.campaignSend("pause",f.view);
 while(!ackInspect||!ackInspect().started)await new Promise(r=>setImmediate(r));fire();await command;
 console.log(JSON.stringify({snapshotError,readState,oversized,malformed,revisionError,clockError,ack:ackInspect(),
  pending:h.pending(),inflight:h.inflight(),status:made["campaign-command-status"]._text}));
})().catch(e=>{console.error(e);process.exit(2)});
'''
    page_js, runner, fixture = tmp_path / "page.js", tmp_path / "runner.js", tmp_path / "f.json"
    page_js.write_text(source, encoding="utf-8")
    runner.write_text(script, encoding="utf-8")
    fixture.write_text(json.dumps({"view": view, "fresh": fresh}), encoding="utf-8")
    result = json.loads(subprocess.run(
        ["node", str(runner), str(page_js), str(fixture)], capture_output=True,
        text=True, timeout=10, check=True).stdout)
    assert "timed out" in result["snapshotError"]
    assert result["readState"] == {"started": True, "cancelled": True, "aborted": True}
    assert "oversized" in result["oversized"]
    assert "malformed JSON" in result["malformed"]
    assert "does not match" in result["revisionError"]
    assert "observation window" in result["clockError"]
    assert result["ack"] == {"started": True, "cancelled": True, "aborted": True}
    assert result["pending"]["operation"] == "pause"
    assert result["inflight"] is False
    assert "Retry keeps the same request ID" in result["status"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_serializes_double_click_and_retains_malformed_ack_for_retry(tmp_path):
    page = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"
    source = "\n".join(re.findall(
        r"<script[^>]*>(.*?)</script>", page.read_text(encoding="utf-8"), re.DOTALL
    )).replace("tick();\nsetInterval(tick, 20000);", "")
    initial = body()
    fresh = body(sequence=2)
    later = body(sequence=3, control_revision=1)
    script = r'''
const fs=require("fs"),{webcrypto}=require("crypto");global.crypto=webcrypto;
global.TextEncoder=TextEncoder;const made={};function el(id){return made[id]||(made[id]={id,
 style:{},classList:{add(){},remove(){},toggle(){}},_html:"",set innerHTML(v){this._html=String(v)},
 get innerHTML(){return this._html},set textContent(v){this._text=String(v)},get textContent(){return this._text||""},
 addEventListener(){},setAttribute(){},removeAttribute(){},querySelector(){return el(id+">q")},querySelectorAll(){return[]}})}
global.document={getElementById:el,querySelector:el,querySelectorAll:()=>[],createElement:()=>el("new"),
 createElementNS:()=>el("newns"),addEventListener(){},body:el("body")};
global.window={isSecureContext:true,addEventListener(){},location:{href:""}};
global.setInterval=()=>0;global.setTimeout=()=>0;
const page=fs.readFileSync(process.argv[2],"utf8"),f=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
let snapshots=[f.fresh,f.later],posts=[],release;
global.fetch=async(url,options={})=>{if(url.endsWith("/snapshot"))return{ok:true,status:200,json:async()=>snapshots.shift()};
 const posted=JSON.parse(options.body);posts.push(posted);if(posts.length===1)await new Promise(r=>release=r);
 const valid={request_id:posted.request_id,operation:posted.operation,payload_digest:posted.payload_digest,
  accepted:true,completed:true,control_revision:posted.expected_control_revision+1,
  desired_state:posted.operation==="resume"?"running":posted.operation+"d",
  observed_state:posted.operation==="resume"?"running":posted.operation+"d",prerequisite_reason:null};
 if(posts.length===2)valid.observed_state="waiting_prerequisite";return{ok:true,status:200,json:async()=>valid};};
eval(page+`;globalThis.h={renderCampaign,campaignSend,setToken:v=>campaignToken=v,
 pending:()=>campaignPending};`);
(async()=>{h.renderCampaign({campaign:f.view});h.setToken("secret");
 const first=h.campaignSend("resume",f.view);await Promise.resolve();
 await h.campaignSend("drain",f.view);while(!release)await new Promise(r=>setImmediate(r));release();await first;
 const afterFirst=h.pending();await h.campaignSend("pause",f.view);const retained=h.pending();
 console.log(JSON.stringify({posts,afterFirst,retained,status:made["campaign-command-status"]._text}));
})().catch(e=>{console.error(e);process.exit(2)});
'''
    page_js, runner, fixture = tmp_path / "page.js", tmp_path / "runner.js", tmp_path / "f.json"
    page_js.write_text(source, encoding="utf-8")
    runner.write_text(script, encoding="utf-8")
    fixture.write_text(json.dumps({"view": {"configured": True, "state": "live",
        "campaign": initial, "clocks": {}, "controls": {"available": True,
        "gateway_url": "https://gateway.test", "reason": None}},
        "fresh": fresh, "later": later}), encoding="utf-8")
    result = json.loads(subprocess.run(
        ["node", str(runner), str(page_js), str(fixture)], capture_output=True,
        text=True, timeout=10, check=True).stdout)
    assert [row["operation"] for row in result["posts"]] == ["resume", "pause"]
    assert result["afterFirst"] is None
    assert result["retained"] == result["posts"][1]
    assert "contradictory" in result["status"]
