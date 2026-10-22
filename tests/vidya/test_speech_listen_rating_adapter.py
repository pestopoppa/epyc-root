"""VB-SPEECH-LISTEN-1: the real CS-8.L aggregate projects as observations; bad records are refused."""
import copy
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import speech_listen_rating as reader  # noqa: E402
from ingest_sources import SOURCES, ingest  # noqa: E402
from ledger import Ledger  # noqa: E402

REAL = ROOT / "artifacts/stt-cs8/cs8l-italian-listen-20261022.json"
AS_OF = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tuples(path):
    return [reader.project(n) for n in reader.native_rows(path)]


def test_real_artifact_projects_and_grades():
    tups = _tuples(REAL)
    metrics = {t.metric: t for t in tups}
    assert len(tups) == 7 and len({t.measurement_id for t in tups}) == 7
    assert metrics["listen_naturalness_mean"].value == 4.62
    assert metrics["listen_intelligibility_rate"].value == 1.0
    assert metrics["listen_error_count_numbers_and_units"].metric_direction == "lower_better"
    for t in tups:
        assert t.extra["rating_docs_sha256"].startswith("db10caef")
        assert "single labelled rater" in t.extra["rater"]
        assert t.attestation_verified is True
        assert ct.grade(t)[0]  # the shared ladder decides


def test_protocol_id_is_empty():
    assert all(t.protocol_id == "" for t in _tuples(REAL))


def test_malformed_or_mock_records_refused(tmp_path):
    d = json.loads(REAL.read_text())
    cases = {}
    for name, mut in {
        "mean": lambda x: x.update(naturalness_mean=3.0),
        "protocol": lambda x: x.update(protocol_id="P-1"),
        "schema": lambda x: x.update(schema="mock"),
        "count": lambda x: x["error_categories"]["lexical_stress"].update(count=9),
        "n": lambda x: x["clips"].pop(),
    }.items():
        m = copy.deepcopy(d)
        mut(m)
        p = tmp_path / f"{name}-listen-x.json"
        p.write_text(json.dumps(m))
        cases[name] = p
    for p in cases.values():
        with pytest.raises(ct.ProjectionError, match="refused"):
            reader.native_rows(p)
    junk = tmp_path / "junk-listen-x.json"
    junk.write_text("{not json")
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(junk)
    with pytest.raises(ct.ProjectionError):
        reader.project({"record": {"schema": "mock"}, "metric": "naturalness_mean"})


def test_ingest_wires_the_source(tmp_path):
    assert "speech-listen-rating" in SOURCES
    report = ingest(Ledger(tmp_path / "ledger.jsonl"), "speech-listen-rating", [REAL], as_of=AS_OF)
    assert report["rows_projected"] == 7 and not report["refused"]
