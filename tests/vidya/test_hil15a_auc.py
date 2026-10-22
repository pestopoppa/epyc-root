"""VB-HIL15A-WRITE: writer + strict reader; fixture grades; mock/insufficient refused."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import hil15a_auc as m  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
TABLE = {"n_runs": 24, "n_tasks": 6, "n_failed": 9,
         "auc_out_of_fold": {"size": 0.61, "size+composition": 0.70,
                             "size+composition+observed_dependency": 0.78,
                             "size+composition+degree_matched_counterfeit": 0.71},
         "deltas": {"observed_dependency_minus_composition": {"delta_auc": 0.08, "ci95_task_resampled": [-0.02, 0.17]},
                    "observed_dependency_minus_size": {"delta_auc": 0.17, "ci95_task_resampled": [0.05, 0.3]},
                    "counterfeit_minus_composition": {"delta_auc": 0.01, "ci95_task_resampled": None}},
         "edge_definition": "observed (intervention-validated needs HIL-16 replay)"}
MANIFEST = {"schema": "hil15a_flagon_run/v1", "mock": False, "hashseed": "pinned", "flags": ["A"],
            "label_classes": ["False", "True"]}


def write(tmp_path, table=TABLE, manifest=MANIFEST):
    p = tmp_path / "auc_table.json"
    p.write_text(json.dumps(table))
    return m.write_belief_measurements(tmp_path, run_id="hil15a-1", producer="t", auc_table_path=p,
                                       manifest=manifest, emitted_at=WHEN)


def test_round_trip_grades(tmp_path):
    nat = m.native_rows(write(tmp_path))
    assert len(nat) == 7
    for n in nat:
        assert ct.grade(m.project(n)) == ("Witnessed", "Attested", [])
    by = {n["row"]["extra"]["name"]: n["row"] for n in nat}
    d = by["observed_dependency_minus_composition"]
    assert d["reps"] == 24 and d["extra"]["n_tasks"] == 6 and d["extra"]["n_failed"] == 9
    assert d["extra"]["ci95_task_resampled"] == [-0.02, 0.17] and d["extra"]["edge_grade"] == "observed"
    assert by["size"]["extra"]["ci95_task_resampled"] is None and by["size"]["category"] == "BASELINE"
    assert len(m.frames_for_sidecar(tmp_path / m.SIDECAR_NAME, as_of="2026-10-22T11:00:00Z")) >= 7


@pytest.mark.parametrize("manifest", [{**MANIFEST, "mock": True},
                                      {k: v for k, v in MANIFEST.items() if k != "mock"}])
def test_mock_or_unmarked_manifest_refused(tmp_path, manifest):
    with pytest.raises(m.CaptureError):
        write(tmp_path, manifest=manifest)
    assert not (tmp_path / m.SIDECAR_NAME).exists()


def test_insufficient_refused_and_no_sidecar_zero_rows(tmp_path):
    with pytest.raises(m.CaptureError):
        write(tmp_path, table={"status": "insufficient", "n_runs": 3, "n_tasks": 2})
    assert m.rows_for_run(tmp_path) == ()


def test_tamper_voids_and_mutation_grades_down(tmp_path):
    sc = write(tmp_path)
    lines = sc.read_text().splitlines()
    row = json.loads(lines[0]); row["value"] = 0.99; lines[0] = json.dumps(row, sort_keys=True)
    sc.write_text("\n".join(lines) + "\n")
    assert m.native_rows(sc) == ()
    sc = write(tmp_path)
    Path(json.loads(sc.read_text().splitlines()[0])["results_path"]).write_text("{}")
    assert ct.grade(m.project(m.native_rows(sc)[0]))[:2] != ("Witnessed", "Attested")


def test_delta_must_rederive_and_bad_ci_refused(tmp_path):
    row = next(n["row"] for n in m.native_rows(write(tmp_path)) if n["row"]["extra"]["kind"] == "delta")
    bad = json.loads(json.dumps(row)); bad["value"] = 0.5
    assert any("re-derive" in p for p in m.validate_row(m.ns.seal(bad)))
    bad = json.loads(json.dumps(row)); bad["extra"]["ci95_task_resampled"] = [0.3, 0.1]
    assert any("ci95" in p for p in m.validate_row(m.ns.seal(bad)))


def test_foreign_row_refused():
    with pytest.raises(ct.ProjectionError):
        m.project({"row": {"schema": "other"}})
