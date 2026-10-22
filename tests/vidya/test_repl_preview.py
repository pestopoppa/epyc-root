"""VB-DRIPREVIEW-WRITE: writer + strict reader; fixture grades; mock/partial refused."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import repl_preview as m  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
FX = "a" * 64
PINS = {"worker_general": {"gguf_path": "/m/Qwen3.6-35B-A3B-MTP-Q8_0.gguf"}}


def cell(correct, n=30, blind=0, retype=0, other=0, none=0):
    assert correct + blind + retype + other + none == n
    return {"n": n, "correct": correct, "blind_rule_fit": blind, "retyping_loss": retype,
            "other": other, "no_answer": none, "correct_rate": round(correct / n, 4)}


def result(**kw):
    r = {"schema": "epyc.repl_preview_result.v1", "mock": False, "n_per_cell": 30, "temperature": 0.7,
         "complete": True, "predeclared": "PREDECLARED.md",
         "counts": {"worker_general|current": cell(10, retype=20), "worker_general|bounded_k3": cell(28, other=2),
                    "worker_general|half_first25": cell(5, blind=25)}}
    r.update(kw)
    return r


def write(tmp_path, res=None, **kw):
    p = tmp_path / "result.json"
    p.write_text(json.dumps(res or result()))
    args = dict(run_id="dripreview1", producer="t", result_path=p, role_pins=PINS, fixture_sha256=FX,
                emitted_at=WHEN)
    args.update(kw)
    return m.write_belief_measurements(tmp_path, **args)


def test_round_trip_grades(tmp_path):
    nat = m.native_rows(write(tmp_path))
    assert len(nat) == 3
    for n in nat:
        assert ct.grade(m.project(n)) == ("Witnessed", "Attested", [])
    by = {n["row"]["extra"]["rendering"]: n["row"] for n in nat}
    assert by["bounded_k3"]["value"] == pytest.approx(28 / 30) and by["bounded_k3"]["reps"] == 30
    assert by["current"]["category"] == "BASELINE" and by["current"]["extra"]["counts"]["retyping_loss"] == 20
    assert FX in m.project(nat[0]).attestation_locator
    assert "Qwen3.6" in m.project(nat[0]).attestation_locator
    assert len(m.frames_for_sidecar(tmp_path / m.SIDECAR_NAME, as_of="2026-10-22T11:00:00Z")) >= 3


@pytest.mark.parametrize("res", [result(mock=True), result(complete=False), {**result(), "mock": None}])
def test_mock_and_partial_refused(tmp_path, res):
    with pytest.raises(m.CaptureError):
        write(tmp_path, res=res)
    assert m.rows_for_run(tmp_path) == ()


def test_short_cell_and_missing_gguf_and_bad_fixture_refused(tmp_path):
    short = result(); short["counts"]["worker_general|current"] = cell(5, n=20, other=15)
    with pytest.raises(m.CaptureError):
        write(tmp_path, res=short)
    with pytest.raises(m.CaptureError):
        write(tmp_path, role_pins={})
    with pytest.raises(m.CaptureError):
        write(tmp_path, fixture_sha256="nope")


def test_tamper_and_value_rederive(tmp_path):
    sc = write(tmp_path)
    row = json.loads(sc.read_text().splitlines()[0])
    row["value"] = 0.99
    assert any("re-derive" in p for p in m.validate_row(m.ns.seal(row)))
    Path(row["results_path"]).write_text("{}")
    assert ct.grade(m.project(m.native_rows(sc)[0]))[:2] != ("Witnessed", "Attested")


def test_fixture_digest_is_stable():
    assert m.fixture_sha256({"b": 1, "a": 2}) == m.fixture_sha256({"a": 2, "b": 1})


def test_foreign_row_refused():
    with pytest.raises(ct.ProjectionError):
        m.project({"row": {"schema": "other"}})
