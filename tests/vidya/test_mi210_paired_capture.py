import json
from pathlib import Path

import pytest

from scripts.vidya.producers import mi210_paired_capture as capture


def declaration(mode="measurement"):
    return {"source": "Q38P-3a", "mode": mode, "model": None, "builds": None,
            "recipe": {"speculation": "off"}, "order": [["p1", "C"], ["p1", "B"]],
            "grant": None, "native_producer": {"path": __file__, "sha256": capture.carrier.file_sha256(Path(__file__))}}


def native(arm="C", state="complete"):
    return {"pair": "p1", "arm": arm, "state": state, "requests": [],
            "actual_placement": None, "residency_linkage": None, "grant": None,
            "stop": None, "errors": None, "release": None}


def test_complete_raw_is_not_measurement_attestation(tmp_path):
    capture.begin(tmp_path, declaration())
    capture.record(tmp_path, native())
    capture.record(tmp_path, native("B"))
    capture.finish(tmp_path, "complete")
    row = capture.read(tmp_path)
    assert row["state"] == "complete"
    assert row["intent"]["declaration"]["model"] is None
    assert row["attempts"][0]["native"]["residency_linkage"] is None
    assert "grade" not in row


def test_smoke_scope_and_failed_attempt_preserved(tmp_path):
    capture.begin(tmp_path, declaration("smoke"))
    n = native(state="failed")
    n["errors"] = ["health timeout"]
    capture.record(tmp_path, n)
    capture.finish(tmp_path, "partial", errors=n["errors"])
    row = capture.read(tmp_path)
    assert row["state"] == "partial"
    assert row["intent"]["declaration"]["mode"] == "smoke"
    assert row["attempts"][0]["native"]["errors"] == ["health timeout"]


def test_interruption_has_no_invented_terminal(tmp_path):
    capture.begin(tmp_path, declaration())
    capture.record(tmp_path, native())
    assert capture.read(tmp_path)["state"] == "interrupted"
    with pytest.raises(ValueError, match="every declared"):
        capture.finish(tmp_path, "complete")


def test_order_is_declared_before_launch(tmp_path):
    capture.begin(tmp_path, declaration())
    with pytest.raises(ValueError, match="order"):
        capture.record(tmp_path, native("B"))
    assert not list(tmp_path.glob("attempt-*.json"))


def test_no_historical_adoption_or_redeclaration(tmp_path):
    (tmp_path / "results.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="historical"):
        capture.begin(tmp_path, declaration())


def test_failure_cannot_be_completed(tmp_path):
    capture.begin(tmp_path, declaration())
    capture.record(tmp_path, native(state="stopped"))
    capture.record(tmp_path, native("B"))
    with pytest.raises(ValueError, match="every declared"):
        capture.finish(tmp_path, "complete")


def test_tampered_native_rejected(tmp_path):
    capture.begin(tmp_path, declaration())
    capture.record(tmp_path, native())
    p = tmp_path / "attempt-00.json"
    row = json.loads(p.read_text())
    row["native"]["actual_placement"] = [184, 185]
    p.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="digest"):
        capture.read(tmp_path)


def test_terminal_blocks_more_writes_and_append_custody(tmp_path):
    capture.begin(tmp_path, declaration())
    capture.record(tmp_path, native())
    capture.finish(tmp_path, "stopped", stop="operator")
    with pytest.raises(ValueError, match="terminal"):
        capture.record(tmp_path, native("B"))
    with pytest.raises(FileExistsError):
        capture.finish(tmp_path, "partial")


def test_symlink_and_nan_rejected(tmp_path):
    d = tmp_path / "run"
    d.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(d, target_is_directory=True)
    with pytest.raises(ValueError, match="nonsymlink"):
        capture.begin(link, declaration())
    capture.begin(d, declaration())
    n = native()
    n["requests"] = [{"predicted_per_second": float("nan")}]
    with pytest.raises(ValueError, match="non-finite"):
        capture.record(d, n)
    assert not list(d.glob("attempt-*.json"))


def test_removed_attempt_breaks_terminal_chain(tmp_path):
    capture.begin(tmp_path, declaration())
    capture.record(tmp_path, native())
    capture.record(tmp_path, native("B"))
    capture.finish(tmp_path, "complete")
    (tmp_path / "attempt-01.json").unlink()
    with pytest.raises(ValueError, match="custody|every declared"):
        capture.read(tmp_path)


@pytest.mark.parametrize("change", ["source", "mode", "order", "native_producer"])
def test_resealed_bad_declaration_is_rejected(tmp_path, change):
    capture.begin(tmp_path, declaration())
    p = tmp_path / "declaration.json"
    row = json.loads(p.read_text())
    row["declaration"][change] = None
    row["row_sha256"] = capture.carrier.row_digest(row)
    p.write_text(json.dumps(row))
    with pytest.raises((ValueError, TypeError)):
        capture.read(tmp_path)


@pytest.mark.parametrize("state", ["complete", "invented"])
def test_resealed_terminal_semantics_rejected(tmp_path, state):
    capture.begin(tmp_path, declaration())
    capture.record(tmp_path, native(state="failed"))
    capture.finish(tmp_path, "failed")
    p = tmp_path / "terminal.json"
    row = json.loads(p.read_text())
    row["state"] = state
    row["row_sha256"] = capture.carrier.row_digest(row)
    p.write_text(json.dumps(row))
    with pytest.raises(ValueError):
        capture.read(tmp_path)


def test_original_native_source_must_match_before_begin(tmp_path):
    d = declaration()
    d['native_producer']['sha256'] = 'a' * 64
    with pytest.raises(ValueError, match='producer bytes'):
        capture.begin(tmp_path, d)
    assert not list(tmp_path.iterdir())
