"""RTG-51 rollout gates: shadow records and does not reject; enforce refuses.

The rollout contract (handoffs/active/wrap-up-division-of-labor-policy.md,
"Rollout and rollback"): start off, then shadow, then enforce. Shadow mode
records and validates the new receipts while legacy behavior remains
available; it NEVER rejects legacy behavior, and every validation result is
written as a finding-shaped observation. Enforcement is fleet-wide only after
the protected policy package lands.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.coordination import rtg51_rollout as r  # noqa: E402

YAML = """\
# RTG-51 rollout gates
schema_version: rtg51_rollout.v1
worker_checkpoint_receipts: {wcp}
auditor_full_wrap: {afw}
compute_window_plan: {cwp}
"""


def valid_receipt() -> dict:
    return {
        "schema_version": "session_bus.msg.v1",
        "id": "msg-20260823T120000Z-1-mainA",
        "ts": "2026-08-23T12:00:00Z",
        "from": "mainA",
        "to": "coordinator-agent",
        "kind": "task-checkpoint",
        "task_id": "RTG-51-x",
        "payload": {
            "boundary_id": "wcp-abc",
            "outcome": "completed",
            "boundary_reason": "task-boundary",
            "task_id": "RTG-51-x",
            "task_text": "run x",
            "spec_ref": "handoffs/active/x.md",
            "agent": "mainA",
            "branch": "lane/mainA",
            "commit_sha": "a" * 40,
            "pushed_ref": "refs/remotes/origin/lane/mainA",
            "progress_path": "progress/2026-08/2026-08-23-mainA.md",
            "handoff_paths": ["handoffs/active/x.md"],
            "validation": [{"command": ["pytest"], "exit_code": 0, "evidence_ref": "e"}],
            "next_context": "related",
            "major_checkpoint": False,
            "completed_at": "2026-08-23T12:00:00Z",
        },
    }


def invalid_receipt() -> dict:
    row = valid_receipt()
    row["payload"] = dict(row["payload"])
    row["payload"]["commit_sha"] = "not-a-sha"
    row["payload"]["branch"] = "main"
    return row


def window() -> dict:
    return {
        "schema_version": "session_bus.msg.v1",
        "id": "msg-20260823T115900Z-1-inference",
        "ts": "2026-08-23T11:59:00Z",
        "from": "inference",
        "to": "coordinator-agent",
        "kind": "compute-window",
        "payload": {
            "window_id": "W-1",
            "grade": "full-idle",
            "eligible_devices": ["gpu0"],
            "cpu_bandwidth_class": "idle",
            "gpu_vram_available": {"bytes": 100, "observation_refs": ["vram:1"]},
            "resident_model": None,
            "load_allowed": True,
            "starts_at": "2026-08-23T12:00:00Z",
            "expires_at": "2026-08-23T14:00:00Z",
            "time_budget_seconds": 100,
            "safe_drain_at": "window expiry",
            "observation_refs": ["sample:1"],
            "eligible_model_ids": ["m"],
            "max_model_bytes": 100,
        },
    }


@pytest.fixture
def bus_root(tmp_path: Path) -> Path:
    bus = tmp_path / "session-bus"
    bus.mkdir()
    shutil.copy2(ROOT / "coordination/session-bus/session_bus.schema.json", bus)
    (bus / "config.yaml").write_text(
        "roster:\n  - id: auditor\n  - id: coordinator-agent\n  - id: inference\n",
        encoding="utf-8",
    )
    return bus


def write_yaml(bus_root: Path, *, wcp="off", afw="off", cwp="off") -> None:
    (bus_root / "rtg51_rollout.yaml").write_text(
        YAML.format(wcp=wcp, afw=afw, cwp=cwp), encoding="utf-8")


def test_defaults_are_off_and_missing_file_reads_off(tmp_path: Path) -> None:
    assert r.load_rollout(tmp_path) == {
        "worker_checkpoint_receipts": "off",
        "auditor_full_wrap": "off",
        "compute_window_plan": "off",
    }


def test_env_override_forces_shadow_grade(tmp_path: Path) -> None:
    gates = r.load_rollout(tmp_path, env={"RTG51_SHADOW_MODE": "1"})
    assert gates["worker_checkpoint_receipts"] == "shadow"
    assert gates["auditor_full_wrap"] == "shadow"
    assert gates["compute_window_plan"] == "observe"


def test_malformed_or_unknown_config_refuses(tmp_path: Path) -> None:
    bad = tmp_path / "rtg51_rollout.yaml"
    bad.write_text("schema_version: rtg51_rollout.v1\nworker_checkpoint_receipts: sidegrade\n",
                   encoding="utf-8")
    with pytest.raises(r.RolloutError, match="invalid mode"):
        r.load_rollout(tmp_path)
    bad.write_text("schema_version: wrong.v1\n", encoding="utf-8")
    with pytest.raises(r.RolloutError, match="schema_version"):
        r.load_rollout(tmp_path)
    bad.write_text("schema_version: rtg51_rollout.v1\nmystery_gate: on\n", encoding="utf-8")
    with pytest.raises(r.RolloutError, match="unknown gate"):
        r.load_rollout(tmp_path)


def test_off_mode_records_and_validates_nothing(bus_root: Path) -> None:
    write_yaml(bus_root, wcp="off")
    gates = r.load_rollout(bus_root)
    assert r.validate_event(invalid_receipt(), surface="task-checkpoint",
                            gates=gates, bus_root=bus_root, emit_agent="auditor") == []
    outbox = bus_root / "outbox" / "auditor.jsonl"
    assert not outbox.exists()


def test_shadow_records_findings_and_never_rejects(bus_root: Path) -> None:
    write_yaml(bus_root, wcp="shadow")
    gates = r.load_rollout(bus_root)
    findings = r.validate_event(invalid_receipt(), surface="task-checkpoint",
                                gates=gates, bus_root=bus_root, emit_agent="auditor")
    assert len(findings) == 1
    assert findings[0].result == "defect"
    assert any("commit_sha" in reason for reason in findings[0].reasons)
    outbox = bus_root / "outbox" / "auditor.jsonl"
    rows = [json.loads(line) for line in outbox.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["kind"] == "finding"
    assert rows[0]["from"] == "auditor"
    assert rows[0]["payload"]["rtg51_validation"]["result"] == "defect"
    assert rows[0]["payload"]["rtg51_validation"]["mode"] == "shadow"
    assert rows[0]["payload"]["source"] == "rtg51-shadow"


def test_shadow_records_valid_result_too(bus_root: Path) -> None:
    write_yaml(bus_root, wcp="shadow")
    gates = r.load_rollout(bus_root)
    findings = r.validate_event(valid_receipt(), surface="task-checkpoint",
                                gates=gates, bus_root=bus_root, emit_agent="auditor")
    assert findings[0].result == "valid"
    rows = [json.loads(line) for line in
            (bus_root / "outbox" / "auditor.jsonl").read_text().splitlines()]
    assert rows[0]["payload"]["rtg51_validation"]["result"] == "valid"


def test_enforce_refuses_defects_and_accepts_valid(bus_root: Path) -> None:
    write_yaml(bus_root, wcp="enforce")
    gates = r.load_rollout(bus_root)
    with pytest.raises(r.ReceiptRefusal, match="commit_sha"):
        r.validate_event(invalid_receipt(), surface="task-checkpoint", gates=gates,
                         bus_root=bus_root, emit_agent="auditor")
    findings = r.validate_event(valid_receipt(), surface="task-checkpoint", gates=gates,
                                bus_root=bus_root, emit_agent="auditor")
    assert findings[0].result == "valid"


def test_compute_window_surface_follows_compute_gate(bus_root: Path) -> None:
    write_yaml(bus_root, cwp="enforce")
    gates = r.load_rollout(bus_root)
    bad = window()
    bad["payload"] = dict(bad["payload"])
    bad["payload"]["grade"] = "mystery-grade"
    with pytest.raises(r.ReceiptRefusal, match="grade"):
        r.validate_event(bad, surface="compute-window", gates=gates,
                         bus_root=bus_root, emit_agent="auditor")
    assert r.validate_event(window(), surface="compute-window", gates=gates,
                            bus_root=bus_root, emit_agent="auditor")[0].result == "valid"


def test_shadow_mode_canary_via_env_without_config_file(bus_root: Path) -> None:
    gates = r.load_rollout(bus_root, env={"RTG51_SHADOW_MODE": "1"})
    findings = r.validate_event(invalid_receipt(), surface="task-checkpoint", gates=gates,
                                bus_root=bus_root, emit_agent="auditor")
    assert findings[0].mode == "shadow"
    assert findings[0].result == "defect"
