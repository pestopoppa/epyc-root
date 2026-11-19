"""Prospective KPF-26 serving records use the existing source and ladder."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
from adapters import kv_prefix_fork as adapter  # noqa: E402
from claim_tuple import ProjectionError  # noqa: E402


def row(tmp_path):
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps({"id": "t", "children": [{"status": "ok"}, {"status": "error"}]}) + "\n")
    data = {"schema": adapter.SCHEMA, "kpf_task": "KPF-26", "run_id": "r", "arm": "fork_on",
            "binary_sha256": "a" * 64, "prompt_set_sha256": "b" * 64, "window_id": "w",
            "end_utc": "2026-11-02T12:00:00Z", "host": "h", "argv": ["/server"],
            "equivalence": {"not_measured": True}, "category": "CANDIDATE", "rows": str(rows),
            "rows_sha256": hashlib.sha256(rows.read_bytes()).hexdigest(),
            "kpf26": {"tasks": 1, "children": 2, "completed": 1}}
    data["record_sha256"] = adapter._digest(data)
    return data


def test_native_row_projects_completion_not_kpf18(tmp_path):
    native = row(tmp_path)
    assert adapter.validate_row(native) == []
    claim = adapter.project({"row": native, "sidecar_path": str(tmp_path / "belief_measurements.jsonl")})
    assert claim.metric == "kpf26_completed_scouts"
    assert claim.value == 1 and claim.reps == 2
    assert claim.attestation_present is True
    assert "KPF-26" in claim.claim and "KPF-18" not in claim.claim


def test_counts_cannot_be_invented_on_read(tmp_path):
    native = row(tmp_path)
    native["kpf26"]["completed"] = 2
    native["record_sha256"] = adapter._digest({k: v for k, v in native.items() if k != "record_sha256"})
    with pytest.raises(ProjectionError, match="disagree"):
        adapter.project({"row": native, "sidecar_path": str(tmp_path / "belief_measurements.jsonl")})
