"""VB-CJ7A-INVERSE-MUTATION-WRITE: strict verifier-class projection of CJ-7a native outcome records.

Synthetic fixtures follow the producer's declared record shape (scorer.score() + control_proof).
Pinned: decided_proposition is re-derived, never composed; undecided records yield no tuple; a record
without a native control kind (a model evaluation) is refused; tampered hashes/verdicts/doc bytes refuse.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import cj7a_inverse_mutation as adapter  # noqa: E402

H = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
FMT = {"version": "ruff 0.16.3", "configuration": "isolated; line-length=100", "executable_sha256": "88" * 32}
INSTR = "Restore the original arithmetic operator."
REAL = Path("/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/inverse_mutation_v1/fixtures/native_control_proof.json")


def record(kind="correct-inverse-control", equal=True):
    exp, cand = H("expected"), (H("expected") if equal else H("mutated"))
    rec = {"recorded_at_utc": "2026-11-01T04:15:57.040615+00:00", "fixture_id": "cj7a-operator-swap-001",
           "instruction": INSTR, "instruction_sha256": H(INSTR), "source_sha256": H("src"),
           "source_provenance": {"repository": "r", "commit": "c" * 40, "path": "p.py",
                                 "license": "MIT", "source_sha256": H("src"), "scope": "mechanical"},
           "mutation": "operator-swap", "candidate_raw_sha256": H("raw-" + kind),
           "candidate_normalized_sha256": cand, "expected_normalized_sha256": exp, "formatter": dict(FMT),
           "verdict": "pass" if equal else "fail", "control_kind": kind}
    rec["decided_proposition"] = adapter._proposition(rec)
    return rec


def write(tmp_path, records, name="native_control_proof.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"schema": adapter.DOC_SCHEMA, "records": records}))
    return p


def fixture(tmp_path):  # used by test_ingest_sources BUILDERS
    return write(tmp_path, [record(), record("mutated-source-negative-control", equal=False)])


def test_valid_records_project_verifier_observations(tmp_path):
    natives = adapter.native_rows(fixture(tmp_path))
    tuples = [adapter.project(n) for n in natives]
    assert [t.value for t in tuples] == [1, 0]
    for t in tuples:
        assert t.source_class == "verifier" and t.protocol_id == "" and t.binding_kind == ""
        assert t.decided_proposition == natives[0]["record"]["decided_proposition"] or t.value == 0
        q, _, _ = ct.grade(t)
        assert q != "Witnessed"
    assert len({t.measurement_id for t in tuples}) == 2


def test_registered_as_verifier_class():
    assert ct.source_classes()["cj7a_inverse_mutation"] == "verifier"


@pytest.mark.parametrize("mutate,match", [
    (lambda r: r.update(verdict="out-of-coverage", cause="unsupported"), "undecided"),
    (lambda r: r.update(candidate_normalized_sha256=None), "missing"),
    (lambda r: r.update(verdict="fail"), "disagrees"),
    (lambda r: r.update(decided_proposition="pass"), "re-derive"),
    (lambda r: r.update(decided_proposition=r["decided_proposition"] + " (and it is correct)"), "re-derive"),
    (lambda r: r.update(control_kind="model-eval"), "model evaluation"),
    (lambda r: r.update(mutation="rename"), "unknown mutation"),
    (lambda r: r["formatter"].update(executable_sha256=""), "formatter identity"),
    (lambda r: r.update(instruction="tampered"), "instruction_sha256"),
    (lambda r: r["source_provenance"].update(source_sha256=H("other")), "provenance"),
    (lambda r: r.update(recorded_at_utc="2026-11-01T04:15:57"), "UTC"),
])
def test_tampered_partial_or_undecided_records_are_refused(tmp_path, mutate, match):
    rec = copy.deepcopy(record())
    mutate(rec)
    (native,) = adapter.native_rows(write(tmp_path, [rec]))
    with pytest.raises(ct.ProjectionError, match=match):
        adapter.project(native)


def test_document_bytes_changed_after_read_are_refused(tmp_path):
    path = fixture(tmp_path)
    native = adapter.native_rows(path)[0]
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ct.ProjectionError, match="hashed bytes"):
        adapter.project(native)


def test_foreign_document_and_missing_path(tmp_path):
    bad = tmp_path / "x.json"
    bad.write_text(json.dumps({"schema": "other", "records": []}))
    with pytest.raises(ct.ProjectionError):
        adapter.native_rows(bad)
    assert adapter.native_rows(tmp_path / "absent.json") == ()


@pytest.mark.skipif(not REAL.is_file(), reason="research checkout absent")
def test_real_native_control_proof_projects_all_eight():
    tuples = [adapter.project(n) for n in adapter.native_rows(REAL)]
    assert len(tuples) == 8 and all(t.extra["control_behaved"] for t in tuples)
