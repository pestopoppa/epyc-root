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
         "complete": True, "valid": True, "predeclared": "PREDECLARED.md",
         "roles": ["worker_general"], "renderings": ["current", "bounded_k3", "half_first25"],
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
        q, t, _r = ct.grade(m.project(n))
        assert (q, t) == ("Judged", "Located") and m.project(n).protocol_id == ""  # OBSERVATION
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


@pytest.mark.parametrize("validity", [False, None, 1])
def test_invalid_or_missing_validity_refused(tmp_path, validity):
    res = result(valid=validity)
    if validity is None:
        del res["valid"]
    with pytest.raises(m.CaptureError, match="valid"):
        write(tmp_path, res=res)
    assert m.rows_for_run(tmp_path) == ()


def test_no_answer_boundary_and_spoofed_validity(tmp_path):
    boundary = result()
    boundary["counts"]["worker_general|current"] = cell(24, none=6)
    assert len(m.native_rows(write(tmp_path, res=boundary))) == 3

    # A valid-looking earlier cell must not be emitted if a later cell is bad.
    (tmp_path / m.SIDECAR_NAME).unlink()
    bad = result(valid=True)
    bad["counts"]["worker_general|bounded_k3"] = cell(23, none=7)
    with pytest.raises(m.CaptureError, match="exceeds 20%"):
        write(tmp_path, res=bad)
    assert m.rows_for_run(tmp_path) == ()

    old = result(valid=True)
    old["counts"] = {k: cell(0, none=30) for k in old["counts"]}
    with pytest.raises(m.CaptureError, match="exceeds 20%"):
        write(tmp_path, res=old)
    assert m.rows_for_run(tmp_path) == ()


@pytest.mark.parametrize("field,values", [
    ("roles", []), ("roles", ["worker_general", "worker_general"]),
    ("roles", [" "]), ("roles", ["worker|general"]), ("roles", None),
    ("renderings", []), ("renderings", ["current", "current"]),
    ("renderings", ["current", 1]),
])
def test_invalid_declared_dimensions_refused(tmp_path, field, values):
    res = result()
    res[field] = values
    with pytest.raises(m.CaptureError, match=field):
        write(tmp_path, res=res)
    assert m.rows_for_run(tmp_path) == ()


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_declared_cells_must_match_exactly(tmp_path, change):
    res = result()
    if change == "missing":
        del res["counts"]["worker_general|current"]
    else:
        res["counts"]["worker_general|unrequested"] = cell(30)
    with pytest.raises(m.CaptureError, match="exactly"):
        write(tmp_path, res=res)
    assert m.rows_for_run(tmp_path) == ()

@pytest.mark.parametrize("bad_counts", [
    {"n": 30, "correct": 30, "blind_rule_fit": 0, "retyping_loss": 0, "other": 0, "no_answer": True},
    {"n": 30, "correct": 30, "blind_rule_fit": 0, "retyping_loss": 0, "other": 0, "no_answer": 1},
    None,
])
def test_malformed_counts_refused_before_emission(tmp_path, bad_counts):
    res = result()
    res["counts"]["worker_general|half_first25"] = bad_counts
    with pytest.raises(m.CaptureError, match="malformed"):
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
