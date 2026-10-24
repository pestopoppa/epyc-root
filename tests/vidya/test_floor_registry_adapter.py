"""Floor-registry master entries -> BASELINE ClaimTuples (VB-FLOOR-REGISTRY-WIRE). Read-only.

Synthetic masters are written under tmp_path; the real master / sealed record are only read.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import floor_registry as reader  # noqa: E402

yaml = pytest.importorskip("yaml")
REAL_MASTER = Path("/workspace/repos/epyc-inference-research/orchestration/model_registry.yaml")
H = lambda c: c * 64  # noqa: E731


def _entry(record: Path, raw: bytes, schema=reader.V2_SCHEMA, **over) -> dict:
    e = {"id": "abcd1234abcd1234", "recipe": "r-t48", "recipe_hash": H("1"), "frame_digest": H("2"),
         "request_digest": H("3"), "model_sha": H("4"), "equivalence_key": H("5"),
         "numerics_epoch": "pre-W5.1a", "champion_tree_hash": H("6"),
         "build": {"commit": "dd3d9721ca37321ad9159520bbd9616e3d0d6228"}, "schema": schema,
         "floor_pct": 2.5, "unit": "process", "n": 24, "k": 5,
         "interval": {"level": 0.95, "low_pct": 1.9, "high_pct": 5.0},
         "grade": {"claim_class": "decision", "co_tenancy": "quiet", "threads": 48},
         "measured_at": "2026-10-22T08:36:13Z", "record": str(record),
         "record_sha256": hashlib.sha256(raw).hexdigest(), "content_sha256": H("7"),
         "annotation": ""}
    e.update(over)
    return e


def _master(tmp_path: Path, entries: dict) -> Path:
    m = tmp_path / "orchestration" / "model_registry.yaml"
    m.parent.mkdir(parents=True)
    m.write_text("roles:\n  x: 1\n\nserving_floors:\n"
                 + "".join("  " + ln + "\n" for ln in
                           yaml.safe_dump(entries, sort_keys=True).splitlines()) + "\nother: 2\n")
    return m


def _v2(tmp_path, **over):
    rec = tmp_path / "rec.json"
    raw = b'{"schema":"epyc.autokernel.serving_floor.v2"}\n'
    rec.write_bytes(raw)
    return _master(tmp_path, {"role-a": [_entry(rec, raw, **over)]}), rec


def test_v2_entry_projects_floor_pct_with_key_and_grades_judged(tmp_path):
    m, rec = _v2(tmp_path)
    (row,) = reader.native_rows(m)
    t = reader.project(row)
    assert (t.metric, t.value, t.reps, t.unit, t.category) == ("serving_floor_pct", 2.5, 24, "%", "BASELINE")
    assert t.metric_direction == "lower_better" and "process" in t.reps_basis
    assert t.observation == {"outcome": "floor", "noise_floor_rel": 0.025}
    key = t.extra["floor_key"]
    assert key["equivalence_key"] == H("5") and key["claim_class"] == "decision"
    assert key["threads"] == 48 and key["co_tenancy"] == "quiet" and key["numerics_epoch"] == "pre-W5.1a"
    assert t.applicability["recipe"] == "r-t48" and t.applicability["model_sha256"] == H("4")
    for k, v in t.applicability.items():  # whatever the closed set admits is carried verbatim
        if k in key:
            assert v == key[k]
    assert t.attestation_verified is True and t.attestation_present is True
    assert ct.grade(t)[:2] == ("Judged", "Located")


def test_indicative_entry_is_refused_as_decision_gating(tmp_path):
    g = {"claim_class": "indicative", "co_tenancy": "co-tenant", "threads": 24}
    m, _ = _v2(tmp_path, grade=g)
    assert reader.native_rows(m) == ()
    (r,) = reader.refusals(m)
    assert "indicative" in r["reason"] and r["role"] == "role-a"
    assert reader.frames_for_path(m, as_of="2026-10-24T00:00:00Z") == []
    with pytest.raises(ct.ProjectionError, match="indicative"):
        reader.project({"entry": _entry(Path("x"), b"", grade=g), "role": "r", "master": "m",
                        "record_path": "x", "record_sha256": H("0")})


def test_decision_with_co_tenant_is_refused(tmp_path):
    m, _ = _v2(tmp_path, grade={"claim_class": "decision", "co_tenancy": "co-tenant", "threads": 48})
    assert reader.native_rows(m) == () and "co-tenant" in reader.refusals(m)[0]["reason"]


def test_record_sha_mismatch_refuses(tmp_path):
    m, rec = _v2(tmp_path)
    rec.write_bytes(b"tampered")
    with pytest.raises(ct.ProjectionError, match="record_sha256"):
        reader.native_rows(m)


def test_unreadable_record_v2_projects_unattested(tmp_path):
    m, rec = _v2(tmp_path)
    rec.unlink()
    t = reader.project(reader.native_rows(m)[0])
    assert t.attestation_present is False and t.attestation_verified is None
    assert ct.grade(t)[0] != "Attested"


def test_v1_entry_reuses_the_v1_floor_projection(tmp_path):
    runs = [100.0, 102.0, 98.0]
    doc = {"schema": reader.V1_SCHEMA, "metric": "agg_tok_s", "recipe": "r-t48", "median_tok_s": 100.0,
           "floor_pct": 2.5, "n": 3, "runs": runs, "spread": {"p95_dev_pct": 2.5}, "unit": "process",
           "residency": {"backend": "cpu", "window_end": 1_790_000_000.0}}
    rec = tmp_path / "f1.json"
    raw = json.dumps(doc).encode()
    rec.write_bytes(raw)
    m = _master(tmp_path, {"role-a": [_entry(rec, raw, schema=reader.V1_SCHEMA, n=3)]})
    t = reader.project(reader.native_rows(m)[0])
    assert (t.metric, t.value, t.reps, t.unit) == ("agg_tok_s", 100.0, 3, "t/s")
    assert t.measurement_id.startswith("floor-registry:role-a:") and t.source_kind == "floor-registry"
    assert t.applicability["recipe"] == "r-t48" and t.applicability["backend"] == "cpu"
    assert t.extra["floor_key"]["equivalence_key"] == H("5") and t.observation["noise_floor_rel"] == 0.025
    assert ct.grade(t)[:2] == ("Judged", "Located")


def test_v1_entry_needs_its_record_and_agreeing_floor(tmp_path):
    m, rec = _v2(tmp_path, schema=reader.V1_SCHEMA)
    rec.unlink()
    with pytest.raises(ct.ProjectionError, match="no median"):
        reader.native_rows(m)


def test_malformed_entry_is_refused_not_repaired(tmp_path):
    m, _ = _v2(tmp_path, equivalence_key="")
    assert reader.native_rows(m) == () and "equivalence_key" in reader.refusals(m)[0]["reason"]


def test_units_and_frames(tmp_path):
    m, _ = _v2(tmp_path)
    assert reader.units(tmp_path) == [m] and reader.units(m) == [m]
    frames = reader.frames_for_path(m, as_of="2026-10-24T00:00:00Z")
    assert frames and any("noise_floor_rel" in json.dumps(f) for f in frames)


def test_no_section_yields_nothing(tmp_path):
    m = tmp_path / "orchestration" / "model_registry.yaml"
    m.parent.mkdir(parents=True)
    m.write_text("roles: {}\n")
    assert reader.native_rows(m) == ()


@pytest.mark.skipif(not REAL_MASTER.is_file(), reason="research master registry not present")
def test_real_master_entries_project_or_are_refused():
    rows, refused = reader._scan(REAL_MASTER)
    assert rows or refused
    for row in rows:
        t = reader.project(row)
        assert t.category == "BASELINE" and t.observation["noise_floor_rel"] >= 0
        assert t.extra["floor_key"]["claim_class"] == "decision"
        assert ct.grade(t)[0] in {"Judged", "Attested", "Witnessed", "Anchored"}
    for r in refused:
        assert r["reason"]
