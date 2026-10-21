"""DS41-1017 validation capture: producer rows project through the shared ladder; tampering refuses."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import ds41_1017_validation as reader  # noqa: E402

import os  # noqa: E402

_RESEARCH = Path(os.environ.get("DS41_TEST_RESEARCH_ROOT", str(reader.RESEARCH_ROOT)))
reader.RESEARCH_ROOT = _RESEARCH
PRODUCER = _RESEARCH / reader.PRODUCER_REL


def _rows(tmp_path):
    producer = reader._producer()
    root = tmp_path / "research"
    run = root / "data" / "run-x"
    run.mkdir(parents=True)
    scored = run / "raw.txt"
    scored.write_text("Final estimate: PPL = 5.0\n")
    sha = producer.sha256_file(scored)
    row = {"schema": producer.SCHEMA, "producer": producer.PRODUCER, "source_kind": producer.SOURCE_KIND,
           "run_id": "run-x", "gate": "ppl", "arm": "1017", "metric": "ppl", "value": 5.0, "unit": "ppl",
           "category": "CANDIDATE", "metric_direction": "lower_better", "claim": "ppl 5.0",
           "protocol_id": "", "reps": 1, "reps_basis": "chunks", "date": "2026-10-21",
           "emitted_at": "2026-10-21T00:00:00+00:00", "scored_path": "data/run-x/raw.txt",
           "scored_sha256": sha,
           "artifact": {"arm": "1017", "path": "/m/shard1.gguf", "split_count": 9,
                        "shards": [{"name": n, "bytes": b, "sha256": h} for n, b, h in producer.SHARDS_1017]},
           "drafter": {"sha256": None, "reason": producer.NO_DRAFTER_REASON},
           "binary": {"head": "abc", "binary_sha256": "0" * 64},
           "recipe": {"argv": ["x"], "env": {}}, "region": {"role": "build", "cpu_list": "0-95"},
           "extra": {}}
    row["measurement_id"] = producer.measurement_identity(run_id="run-x", gate="ppl", arm="1017",
                                                          metric="ppl", scored_sha256=sha)
    row["row_sha256"] = producer._row_hash(row)
    side = run / "belief_measurements.jsonl"
    side.write_text(json.dumps(row) + "\n")
    return root, side, row, producer


@pytest.mark.skipif(not PRODUCER.is_file(), reason="research producer not checked out")
def test_row_projects_and_grades(tmp_path, monkeypatch):
    root, side, row, _ = _rows(tmp_path)
    natives = reader.native_rows(side, root=root)
    tup = reader.project(natives[0])
    assert tup.attestation_verified is True
    assert len(tup.extra["shard_sha256"]) == 9
    q, t, _ = ct.grade(tup)
    assert q == "Judged"  # no protocol citation: an OBSERVATION, honestly graded


@pytest.mark.skipif(not PRODUCER.is_file(), reason="research producer not checked out")
@pytest.mark.parametrize("field,value", [("value", 4.0), ("artifact", {"arm": "1017", "shards": []}),
                                         ("drafter", {"sha256": None})])
def test_tampered_row_refuses(tmp_path, field, value):
    root, side, row, _ = _rows(tmp_path)
    row[field] = value
    side.write_text(json.dumps(row) + "\n")
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(side, root=root)
