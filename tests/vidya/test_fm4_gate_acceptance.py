"""Synthetic FM-4 controls for native receipt validation and planning context."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from adapters import fm4_gate_acceptance as adapter
from claim_tuple import ProjectionError, grade
import loop_beliefs

ROOT = Path(__file__).resolve().parents[2]
RUN_GATE = ROOT / "scripts/experiments/fm4/run_gate.py"
CLI = ROOT / "scripts/vidya/cli.py"
IDENTITIES = {
    "parent_session_id": "synthetic-parent",
    "dispatch_tool_use_id": "synthetic-dispatch",
    "child_agent_id": "synthetic-child",
    "task_id": "FM4-SYNTHETIC-CANARY",
}
GATE = "import sys; sys.stdout.buffer.write(b'private-marker\\x00\\xff'); sys.exit(int(sys.argv[1]))"


def _capture(root, code=0):
    path = root / "acceptance.json"
    argv = [sys.executable, "-c", GATE, str(code), "", "literal ; argument"]
    flags = [part for k, v in IDENTITIES.items() for part in ("--" + k.replace("_", "-"), v)]
    done = subprocess.run(
        [sys.executable, str(RUN_GATE), "--out", str(path), "--cwd", str(root),
         "--timeout-s", "5", *flags, "--", *argv],
        capture_output=True, text=True, check=True,
    )
    return path, json.loads(done.stdout), argv


def _sidecar(path):
    return path.with_name(f"{path.name}.execution.json")


def _read(path):
    return json.loads(path.read_bytes())


def _rewrite(path, raw):
    path.chmod(0o644)
    path.write_bytes(raw)
    path.chmod(0o444)


def _reseal(path, raw):
    """Preserve digest agreement so each control reaches semantic validation."""
    acceptance = _read(path)
    digest = hashlib.sha256(raw).hexdigest()
    snapshot = path.parent / "evidence" / f"{digest}.bin"
    snapshot.write_bytes(raw)
    snapshot.chmod(0o444)
    _sidecar(path).write_bytes(raw)
    acceptance["evidence"] = {"path": str(snapshot), "sha256": digest}
    _rewrite(path, json.dumps(acceptance).encode())


@pytest.mark.parametrize(("code", "result", "value"), [(0, "pass", 1), (7, "fail", 0)])
def test_native_bundle_uses_shared_observation_grade(tmp_path, code, result, value):
    path, acceptance, argv = _capture(tmp_path, code)
    (native,) = adapter.native_rows(path)
    claim = adapter.project(native)
    assert native["acceptance"] == acceptance
    execution = claim.extra["execution"]
    assert {name: execution[name] for name in IDENTITIES} == IDENTITIES
    assert execution["argv"] == argv and execution["cwd"] == str(tmp_path)
    assert execution["returncode"] == code
    assert execution["started_at"] <= execution["ended_at"] <= acceptance["timestamp"]
    assert native["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "stdout_base64" not in execution and "stderr_base64" not in execution
    assert grade(claim)[:2] == ("Judged", "Located")
    assert claim.observation["outcome_native"] == result
    assert (claim.value, claim.protocol_id, claim.reps, claim.category) == (value, "", 1, "CANDIDATE")
    assert "Task accuracy and historical verdicts are outside" in claim.claim
    assert claim.attestation_present and claim.attestation_verified


@pytest.mark.parametrize(("field", "value", "match"), [
    *((key, "different-id", key) for key in IDENTITIES),
    ("argv", [], "argv"),
    ("argv", [""], "argv"),
    ("argv", ["gate", 1], "argv"),
    ("argv", ["gate", "bad\x00argument"], "argv"),
    ("cwd", "relative/path", "cwd"),
    ("cwd", "/absolute/../wrong", "cwd"),
    ("timeout_s", -1, "timeout"),
    ("timeout_s", True, "timeout"),
    ("timeout_s", float("inf"), "nonfinite"),
    ("schema", "other", "fm4.gate_execution.v1"),
    ("returncode", -15, "normal exit status"),
    ("returncode", False, "normal exit status"),
    ("returncode", 256, "normal exit status"),
    ("returncode", 3, "does not match gate result"),
    ("timed_out", True, "normal exit status"),
    ("timed_out", 0, "normal exit status"),
    ("launch_error", "missing executable", "normal exit status"),
    ("started_at", "2040-01-01T00:00:00.000000Z", "out of order"),
    ("ended_at", "2040-01-01T00:00:00.000000Z", "out of order"),
    ("ended_at", "2026-02-31T00:00:00.000000Z", "day is out of range"),
    ("started_at", "2026-11-01T00:00:00Z", "UTC with microseconds"),
    ("stderr_base64", "AB==", "stderr_base64"),
])
def test_resealed_malformed_or_mismatched_execution_refuses(tmp_path, field, value, match):
    path, _, _ = _capture(tmp_path)
    execution = _read(_sidecar(path))
    execution[field] = value
    _reseal(path, json.dumps(execution).encode())
    with pytest.raises(ProjectionError, match=match):
        adapter.native_rows(path)


def test_duplicate_fields_refuse_in_both_records(tmp_path):
    path, _, _ = _capture(tmp_path)
    execution = _sidecar(path).read_bytes()
    _reseal(path, b'{"returncode": 0, ' + execution[1:])
    with pytest.raises(ProjectionError, match="duplicate JSON field: returncode"):
        adapter.native_rows(path)
    _rewrite(path, b'{"timestamp": "duplicate", ' + path.read_bytes()[1:])
    with pytest.raises(ProjectionError, match="duplicate JSON field: timestamp"):
        adapter.native_rows(path)


def test_receipts_and_native_rows_are_rechecked_at_projection(tmp_path):
    path, _, _ = _capture(tmp_path)
    (native,) = adapter.native_rows(path)
    changed = {**native, "execution": {**native["execution"], "argv": ["unrelated-gate"]}}
    with pytest.raises(ProjectionError, match="does not rederive"):
        adapter.project(changed)
    _rewrite(path, path.read_bytes() + b"\n")
    with pytest.raises(ProjectionError, match="does not rederive"):
        adapter.project(native)


@pytest.mark.parametrize("mutation", ["snapshot", "sidecar-argv", "sidecar-cwd", "missing-sidecar", "symlink"])
def test_evidence_mutation_or_missing_custody_refuses(tmp_path, mutation):
    path, acceptance, _ = _capture(tmp_path)
    (native,) = adapter.native_rows(path)
    sidecar = _sidecar(path)
    snapshot = Path(acceptance["evidence"]["path"])
    if mutation == "snapshot":
        _rewrite(snapshot, b"changed snapshot")
    elif mutation == "missing-sidecar":
        sidecar.unlink()
    elif mutation == "symlink":
        sidecar.unlink()
        sidecar.symlink_to(snapshot)
    else:
        execution = _read(sidecar)
        field = mutation.split("-")[1]
        execution[field] = ["different-gate"] if field == "argv" else "/other/cwd"
        sidecar.write_text(json.dumps(execution))
    with pytest.raises(ProjectionError):
        adapter.project(native)


class _FreshIndex:
    def status(self, *args, **kwargs):
        return {"fresh": True, "lag_entries": 0, "index_max_id": 1, "synced_max_id": 1,
                "last_sync": datetime.now(timezone.utc).isoformat()}

    def sync(self, *args, **kwargs):
        raise AssertionError("synthetic index must stay isolated")


def test_synthetic_cli_to_planning_context_canary(tmp_path):
    path, _, _ = _capture(tmp_path)
    as_of = (datetime.now(timezone.utc) + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ledger = tmp_path / "ledger.jsonl"
    command = [sys.executable, str(CLI), "--ledger", str(ledger), "--json", "ingest",
               adapter.SOURCE_KIND, "--path", str(path), "--as-of", as_of, "--only-new"]
    report = json.loads(subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    assert report["refused"] == [] and report["rows_projected"] == 1 and report["frames_emitted"] == 3
    before = ledger.read_bytes()
    assert b"private-marker" not in before

    index = tmp_path / "index.yaml"
    index.write_text("[]\n")
    config = tmp_path / "alarm.yaml"
    config.write_text(f"backend: file\nfile:\n  path: {tmp_path / 'alarm.jsonl'}\n")
    target = {"model_file": "synthetic.gguf", "quant": "Q4", "backend": "cpu", "device": "cpu"}

    def ask(consumer):
        answer = loop_beliefs.prepare(
            consumer, target, ledger=ledger, index_path=index, as_of=as_of, sync_module=_FreshIndex(),
            known_good=tmp_path / "kg.json", alarm_state=tmp_path / "state.json",
            alarm_config=config, read_log=tmp_path / "reads.jsonl",
        )
        assert answer["status"] == "ready", answer
        return answer["evidence"]

    evidence = ask(adapter.PLANNER_CONSUMER)
    (claim,) = [c for c in evidence["claims"] if c.get("source_kind") == adapter.SOURCE_KIND]
    assert claim["tier"] == "harness" and claim["not_evidence"]
    assert (claim["grade"], claim["value"], claim["unit"]) == ("Judged/Located", 1, "gate_pass_indicator")
    assert "selected gate reported pass" in evidence["section"]
    assert "Task accuracy and historical verdicts are outside" in evidence["section"]
    assert claim["claim_id"] not in evidence["claim_ids"]
    assert not [c for c in ask("autokernel.planner")["claims"] if c.get("source_kind") == adapter.SOURCE_KIND]

    _sidecar(path).write_text("{}")
    refused = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    report = json.loads(refused.stdout)
    assert report["rows_projected"] == report["frames_emitted"] == 0
    assert "disagrees" in report["refused"][0]["reason"]
    assert ledger.read_bytes() == before
