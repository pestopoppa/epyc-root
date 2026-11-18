import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/experiments/fm4"))
import task_acceptance as acceptance


def inputs(tmp_path):
    evidence = tmp_path / "gate.txt"
    # Completion and exit code are deliberately irrelevant to the explicit gate.
    evidence.write_text("completed; exit_code=0; acceptance gate failed\n")
    return dict(parent_session_id="sid-1", dispatch_tool_use_id="toolu_123",
                child_agent_id="agent-a", task_id="FM4-CAPTURE",
                gate_result="fail", evidence_path=evidence,
                evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest())


def capture(tmp_path, **changes):
    args = inputs(tmp_path)
    args.update(changes)
    return acceptance.write_record(tmp_path / "record.json", **args)


@pytest.mark.parametrize("outcome", ["pass", "fail"])
def test_prospective_record_is_explicit_and_digest_bound(tmp_path, outcome):
    before = datetime.now(timezone.utc)
    record = capture(tmp_path, gate_result=outcome)
    after = datetime.now(timezone.utc)
    assert record["gate_result"] == outcome
    assert before <= datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")) <= after
    assert acceptance.validate_record(record) == json.loads((tmp_path / "record.json").read_text())
    assert all(record[key] == inputs(tmp_path)[key] for key in acceptance.IDENTITIES)
    assert Path(record["evidence"]["path"]).read_bytes() == (tmp_path / "gate.txt").read_bytes()
    (tmp_path / "gate.txt").write_text("source changed")
    assert acceptance.validate_record(record) == record


@pytest.mark.parametrize("name", acceptance.IDENTITIES)
@pytest.mark.parametrize("value", ["", "a b", "a\nb", "../child", ["a", "b"], None])
def test_malformed_identity_creates_no_record_or_snapshot(tmp_path, name, value):
    with pytest.raises(ValueError, match="invalid " + name):
        capture(tmp_path, **{name: value})
    assert not (tmp_path / "record.json").exists()
    assert not (tmp_path / "evidence").exists()


@pytest.mark.parametrize("outcome", ["completed", "success", "failure", "pass,fail", ["pass", "fail"], True, 0, None])
def test_no_inference_or_ambiguous_outcomes(tmp_path, outcome):
    with pytest.raises(ValueError, match="gate_result"):
        capture(tmp_path, gate_result=outcome)
    assert not (tmp_path / "record.json").exists()


@pytest.mark.parametrize("case", ["missing", "directory", "symlink", "wrong_digest", "invalid_digest"])
def test_writer_rejects_unverified_evidence(tmp_path, case):
    args = inputs(tmp_path)
    if case == "missing":
        args["evidence_path"] = tmp_path / "absent"
    elif case == "directory":
        args["evidence_path"] = tmp_path
    elif case == "symlink":
        link = tmp_path / "link"
        link.symlink_to(args["evidence_path"])
        args["evidence_path"] = link
    else:
        args["evidence_sha256"] = "0" * 64 if case == "wrong_digest" else "ABC"
    with pytest.raises(ValueError):
        acceptance.write_record(tmp_path / "record.json", **args)
    assert not (tmp_path / "record.json").exists()


@pytest.mark.parametrize("mutation", ["version", "extra", "missing", "timestamp", "outcome", "evidence_extra", "relative_path", "sha256"])
def test_validator_rejects_malformed_records(tmp_path, mutation):
    record = copy.deepcopy(capture(tmp_path))
    if mutation == "version":
        record["schema"] = "fm4.task_acceptance.v2"
    elif mutation == "extra":
        record["exit_code"] = 0
    elif mutation == "missing":
        del record["task_id"]
    elif mutation == "timestamp":
        record["timestamp"] = "2026-02-31T12:00:00.000000Z"
    elif mutation == "outcome":
        record["gate_result"] = ["pass", "fail"]
    elif mutation == "evidence_extra":
        record["evidence"]["status"] = "completed"
    elif mutation == "relative_path":
        record["evidence"]["path"] = "gate.txt"
    else:
        record["evidence"]["sha256"] = "bad"
    with pytest.raises(ValueError):
        acceptance.validate_record(record)


@pytest.mark.parametrize("mutation", ["missing", "writable", "tampered", "symlink"])
def test_validator_rechecks_snapshot(tmp_path, mutation):
    record = capture(tmp_path)
    snapshot = Path(record["evidence"]["path"])
    if mutation in ("missing", "symlink"):
        snapshot.unlink()
        if mutation == "symlink":
            snapshot.symlink_to(tmp_path / "gate.txt")
    else:
        snapshot.chmod(0o644)
        if mutation == "tampered":
            snapshot.write_text("changed")
            snapshot.chmod(0o444)
    with pytest.raises(ValueError):
        acceptance.validate_record(record)


def test_records_never_overwrite_and_shared_snapshot_is_verified(tmp_path):
    args = inputs(tmp_path)
    first = acceptance.write_record(tmp_path / "record.json", **args)
    original_bytes = (tmp_path / "record.json").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        acceptance.write_record(tmp_path / "record.json", **args)
    assert (tmp_path / "record.json").read_bytes() == original_bytes
    second = acceptance.write_record(tmp_path / "second.json", **args)
    assert first["evidence"] == second["evidence"]
    snapshot = Path(first["evidence"]["path"])
    snapshot.chmod(0o644)
    snapshot.write_text("tampered")
    snapshot.chmod(0o444)
    with pytest.raises(ValueError, match="digest mismatch"):
        acceptance.write_record(tmp_path / "third.json", **args)
    assert not (tmp_path / "third.json").exists()


def test_cli_write_validate_and_failure_are_json_only_on_success(tmp_path, capsys):
    args = inputs(tmp_path)
    argv = ["write", "--out", str(tmp_path / "record.json")]
    for key, value in args.items():
        argv.extend(["--" + key.replace("_", "-"), str(value)])
    assert acceptance.main(argv) == 0
    output = capsys.readouterr()
    record = json.loads(output.out)
    assert not output.err
    assert acceptance.main(["validate", str(tmp_path / "record.json")]) == 0
    assert json.loads(capsys.readouterr().out) == record
    Path(record["evidence"]["path"]).unlink()
    assert acceptance.main(["validate", str(tmp_path / "record.json")]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert output.err


def test_cli_duplicate_result_fields_are_ambiguous(tmp_path, capsys):
    path = tmp_path / "ambiguous.json"
    path.write_text('{"gate_result":"pass","gate_result":"fail"}')
    assert acceptance.main(["validate", str(path)]) == 1
    assert "duplicate JSON field" in capsys.readouterr().err
