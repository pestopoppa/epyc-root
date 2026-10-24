"""DS41-1017 validation capture: producer rows project through the shared ladder; tampering refuses."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
import claim_tuple as ct  # noqa: E402
import loop_beliefs as lb  # noqa: E402
from adapters import ds41_1017_validation as reader  # noqa: E402

import os  # noqa: E402

_RESEARCH = Path(os.environ.get("DS41_TEST_RESEARCH_ROOT", str(reader.RESEARCH_ROOT)))
reader.RESEARCH_ROOT = _RESEARCH
PRODUCER = _RESEARCH / reader.PRODUCER_REL


def _rows(tmp_path, arm="1017"):
    producer = reader._producer()
    root = tmp_path / "research"
    run = root / "data" / "run-x"
    run.mkdir(parents=True)
    scored = run / "raw.txt"
    scored.write_text("Final estimate: PPL = 5.0\n")
    sha = producer.sha256_file(scored)
    if arm == "1017":
        artifact = {"arm": arm,
                    "path": str(Path(producer.MODEL_DIR) / producer.SHARDS_1017[0][0]),
                    "split_count": 9,
                    "shards": [{"name": n, "bytes": b, "sha256": h}
                               for n, b, h in producer.SHARDS_1017]}
    else:
        artifact = {"arm": arm,
                    "path": str(Path(producer.MODEL_DIR) / producer.SEPT_Q4["name"]),
                    "split_count": 1, **producer.SEPT_Q4}
    row = {"schema": producer.SCHEMA, "producer": producer.PRODUCER, "source_kind": producer.SOURCE_KIND,
           "run_id": "run-x", "gate": "ppl", "arm": arm, "metric": "ppl", "value": 5.0, "unit": "ppl",
           "category": producer.ARMS[arm], "metric_direction": "lower_better", "claim": "ppl 5.0",
           "protocol_id": "", "reps": 1, "reps_basis": "chunks", "date": "2026-10-21",
           "emitted_at": "2026-10-21T00:00:00+00:00", "scored_path": "data/run-x/raw.txt",
           "scored_sha256": sha,
           "artifact": artifact,
           "drafter": {"sha256": None, "reason": producer.NO_DRAFTER_REASON},
           "binary": {"head": "abc", "binary_sha256": "0" * 64},
           "recipe": {"argv": ["x"], "env": {}}, "region": {"role": "build", "cpu_list": "0-95"},
           "extra": {}}
    row["measurement_id"] = producer.measurement_identity(run_id="run-x", gate="ppl", arm=arm,
                                                          metric="ppl", scored_sha256=sha)
    row["row_sha256"] = producer._row_hash(row)
    side = run / "belief_measurements.jsonl"
    side.write_text(json.dumps(row) + "\n")
    return root, side, row, producer


@pytest.mark.skipif(not PRODUCER.is_file(), reason="research producer not checked out")
def test_row_projects_and_grades(tmp_path, monkeypatch):
    root, side, row, producer = _rows(tmp_path)
    natives = reader.native_rows(side, root=root)
    tup = reader.project(natives[0])
    assert tup.attestation_verified is True
    assert len(tup.extra["shard_sha256"]) == 9
    assert tup.applicability["model_file"].endswith(producer.SHARDS_1017[0][0])
    assert "quant" not in tup.applicability
    q, t, _ = ct.grade(tup)
    assert q == "Judged"  # no protocol citation: an OBSERVATION, honestly graded


@pytest.mark.skipif(not PRODUCER.is_file(), reason="research producer not checked out")
@pytest.mark.parametrize("arm", ["1017", "sept-q4"])
def test_projection_scopes_each_arm_to_its_exact_artifact_without_guessing_quant(tmp_path, arm):
    root, side, _, _ = _rows(tmp_path, arm=arm)
    tup = reader.project(reader.native_rows(side, root=root)[0])
    expected_name = (reader._producer().SHARDS_1017[0][0] if arm == "1017"
                     else reader._producer().SEPT_Q4["name"])
    assert tup.applicability["model_file"].endswith(expected_name)
    assert tup.applicability["backend"] == "cpu"
    assert "quant" not in tup.applicability


@pytest.mark.skipif(not PRODUCER.is_file(), reason="research producer not checked out")
@pytest.mark.parametrize("arm", ["1017", "sept-q4"])
def test_projector_refuses_artifact_path_alias_even_with_valid_row_hash(tmp_path, arm):
    root, side, row, producer = _rows(tmp_path, arm=arm)
    row["artifact"]["path"] = "/mnt/other/DeepSeek-V4.1-Flash-Q4.gguf"
    row["row_sha256"] = producer._row_hash(row)
    side.write_text(json.dumps(row) + "\n")
    with pytest.raises(ct.ProjectionError, match="artifact path"):
        reader.native_rows(side, root=root)


@pytest.mark.skipif(not PRODUCER.is_file(), reason="research producer not checked out")
@pytest.mark.parametrize(("arm", "quant"), [("1017", "Q8_0"), ("sept-q4", "Q8_0")])
def test_projected_artifact_matches_only_its_cpu_target(tmp_path, arm, quant):
    root, side, _, _ = _rows(tmp_path, arm=arm)
    tup = reader.project(reader.native_rows(side, root=root)[0])
    frames = ct.to_frames(tup, as_of="2026-10-24T12:00:00Z", adapter_id=reader.ADAPTER_ID)
    model_path = tup.applicability["model_file"]
    target = lb.Target.from_mapping({"model_path": model_path, "quant": quant, "backend": "cpu"})
    matching = lb.evaluate_frames(frames, [target], as_of="2026-10-24T12:00:00Z")
    claim_id = f"clm_{tup.measurement_id}"
    assert claim_id in matching["claim_ids"]
    assert next(c for c in matching["claims"] if c["claim_id"] == claim_id)["tier"] == "target"

    for mismatch in (
            {"model_path": "/mnt/raid0/llm/models/Other.gguf", "quant": quant, "backend": "cpu"},
            {"model_path": model_path, "quant": quant, "backend": "gpu"},
    ):
        refused = lb.evaluate_frames(
            frames, [lb.Target.from_mapping(mismatch)], as_of="2026-10-24T12:00:00Z")
        assert refused["tiers"]["target"] == 0

    # The reader still rejects a quant mismatch when a source explicitly declares one.
    wrong_quant = ct.ClaimTuple(**{**tup.__dict__,
                                   "applicability": {**tup.applicability, "quant": "MXFP4"}})
    wrong_frames = ct.to_frames(wrong_quant, as_of="2026-10-24T12:00:00Z",
                                adapter_id=reader.ADAPTER_ID)
    refused = lb.evaluate_frames(wrong_frames, [target], as_of="2026-10-24T12:00:00Z")
    assert refused["tiers"]["target"] == 0


@pytest.mark.skipif(not PRODUCER.is_file(), reason="research producer not checked out")
@pytest.mark.parametrize("field,value", [("value", 4.0), ("artifact", {"arm": "1017", "shards": []}),
                                         ("drafter", {"sha256": None})])
def test_tampered_row_refuses(tmp_path, field, value):
    root, side, row, _ = _rows(tmp_path)
    row[field] = value
    side.write_text(json.dumps(row) + "\n")
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(side, root=root)
