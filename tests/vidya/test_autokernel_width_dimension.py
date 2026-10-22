"""AKX-ALL-27 width-dimension record -> strict reader -> shared grade. Fixture tree, no inference."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_width_dimension as reader  # noqa: E402

PARENT, KEEP = "/b/gpu-20261021-732389d6d", "/b/gpu-20261021-b0eb4fab4"


def _cells(path: Path, build: str, commit: str, rows: dict):
    lines = [json.dumps({"record": "run", "backend_bound": "ROCm0", "device_description": "MI210",
                         "ggml_commit": commit, "env": {"LD_LIBRARY_PATH": build + "/bin:/opt/rocm/lib"}})]
    for cid, (verdict, first) in rows.items():
        lines.append(json.dumps({"record": "cell", "id": cid, "sub": 0, "backend_bound": "ROCm0",
                                 "status": "OK", "verdict": verdict, "first_fail_k": first}))
    path.mkdir()
    (path / "cells.jsonl").write_text("\n".join(lines) + "\n")


@pytest.fixture
def tree(tmp_path):
    _cells(tmp_path / "parent", PARENT, "732389d6d", {"A": ("FAIL", 2), "B": ("FAIL", 3), "C": ("PASS", None)})
    _cells(tmp_path / "keep", KEEP, "b0eb4fab4", {"A": ("FAIL", 5), "B": ("FAIL", 3), "C": ("PASS", None)})
    a, _, _ = reader._table(tmp_path / "parent")
    k, _, _ = reader._table(tmp_path / "keep")
    cmp_ = reader._compare(a, k)
    (tmp_path / "DECISION.json").write_text(json.dumps({
        "counts": cmp_["counts"], "coverage_complete": True, "route": {"proven": True},
        "builds": {"parent": PARENT, "keep": KEEP}, "decided_at": "2026-10-22T12:58:39Z"}))
    rec = {"schema": reader.SCHEMA, "observe_only": True, "refuses": False, "anchor": None, "keep": None,
           "disposition": "measured", "touched": {"mmvq": ["x.cu"]}, "comparison": cmp_}
    (tmp_path / "width_dimension.json").write_text(json.dumps(rec))
    return tmp_path


def test_valid_record_projects_four_counts_and_grades_by_the_shared_ladder(tree):
    natives = reader.native_rows(tree / "width_dimension.json")
    assert [n["value"] for n in natives] == [0, 0, 1, 0]
    tuples = [reader.project(n) for n in natives]
    assert all(t.protocol_id == "" and t.reps is None for t in tuples)
    for t in tuples:
        assert len(ct.grade(t)) == 3
    assert len({t.measurement_id for t in tuples}) == 4


def test_tampered_comparison_does_not_rederive(tree):
    p = tree / "width_dimension.json"
    rec = json.loads(p.read_text())
    rec["comparison"]["counts"]["higher_first_fail_k"] = 9
    p.write_text(json.dumps(rec))
    with pytest.raises(ct.ProjectionError, match="re-derive"):
        reader.native_rows(p)


def test_unproven_route_is_refused(tree):
    d = json.loads((tree / "DECISION.json").read_text())
    d["route"]["proven"] = False
    (tree / "DECISION.json").write_text(json.dumps(d))
    with pytest.raises(ct.ProjectionError, match="route"):
        reader.native_rows(tree / "width_dimension.json")


def test_build_commit_mismatch_is_refused(tree):
    d = json.loads((tree / "DECISION.json").read_text())
    d["builds"]["keep"] = "/b/gpu-20261021-deadbeef1"
    (tree / "DECISION.json").write_text(json.dumps(d))
    with pytest.raises(ct.ProjectionError, match="header does not match"):
        reader.native_rows(tree / "width_dimension.json")


def test_foreign_schema_emits_nothing(tree):
    p = tree / "width_dimension.json"
    p.write_text(json.dumps({"schema": "other.v1"}))
    assert reader.native_rows(p) == ()
