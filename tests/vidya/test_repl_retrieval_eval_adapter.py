"""VB-UFH12-RETR / VB-UFH12-EMBSPEED: producer-written sidecars, whole-file refusal, ingest.

Rows are written by the orchestrator's own capture module (pinned by sha256), never hand-built.
Until the orchestrator lane lands on main, point ``EPYC_REPLRET_CAPTURE`` at the lane's
``scripts/benchmark/repl_retrieval_capture.py``; the sha256 pin still applies, and a present-but-
different file FAILS (it never skips), so a stale pin cannot hide behind a skipped suite.
"""

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
#: the ledger refuses future-stamped frames, so ingest at the wall clock
from datetime import UTC, datetime

import claim_tuple as ct
from adapters import repl_retrieval_eval as reader
from ingest_sources import SOURCES, ingest
from ledger import Ledger

AS_OF = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
T_START = "2026-10-20T10:00:00+00:00"
T_END = "2026-10-20T10:30:00+00:00"


@pytest.fixture()
def producer(monkeypatch):
    override = os.environ.get("EPYC_REPLRET_CAPTURE")
    if override:
        monkeypatch.setattr(reader, "PRODUCER_PATH", Path(override))
    if not reader.PRODUCER_PATH.is_file():
        pytest.skip(
            f"retrieval-eval capture module not landed here: {reader.PRODUCER_PATH}"
        )
    return (
        reader._producer()
    )  # a sha mismatch raises ProjectionError: the suite fails, not skips


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def clock():
    stamps = [T_START, T_END]
    return lambda: stamps.pop(0) if len(stamps) > 1 else stamps[0]


def dense_arm(arm_id="bge-large", role="CANDIDATE"):
    return {"arm_id": arm_id, "model": "BAAI/bge-large-en-v1.5", "revision": "d4aa6901",
            "dim": 1024, "dtype_or_quant": "f16", "runtime": "llama.cpp/b10303",
            "prompt_hash": sha("p"), "index_identity_digest": sha(f"i-{arm_id}"), "role": role}  # fmt: skip


def lexical_arm():
    return {"arm_id": "bm25", "model": None, "revision": None, "dim": None, "dtype_or_quant": None,
            "runtime": "context_search.py/rank_bm25", "prompt_hash": None,
            "index_identity_digest": sha("i-bm25"), "role": "BASELINE"}  # fmt: skip


def host():
    return {"hostname": "epyc-test", "cpu_list": "24-71", "cpus_allowed_observed": "24-71",
            "region_lock_claim": "q1+q2:build:sess-1",
            "loadavg": {"start": [1.0, 1.2, 1.5], "end": [1.1, 1.2, 1.5]},
            "frequency": {"governor": "performance", "mhz_min": 3500.0, "mhz_max": 4200.0,
                          "throttled": False}}  # fmt: skip


CFG = {"chunk_chars": 800}
DIGESTS = {"c": sha("c")}


def write_retrieval(tmp_path, producer, run_id="run-1"):
    run = producer.RetrievalRun(tmp_path, run_id, producer.registered_rule(), DIGESTS,
                                {"all": sha("q")}, {"g": sha("g")}, sha("m"), host(), clock=clock())  # fmt: skip
    run.add_recall(
        lexical_arm(), "all", "lexical", 5, "recall", 0.5, 120, 60, [0.4, 0.6], CFG
    )
    run.add_recall(
        dense_arm(), "all", "hybrid", 5, "recall", 0.7, 120, 84, [0.6, 0.8], CFG
    )
    run.add_paired_diff(dense_arm(), lexical_arm(), "all", 5, 0.2, [0.1, 0.3], 120, 10000, 7,
                        mode_a="hybrid", mode_b="lexical")  # fmt: skip
    run.add_cost(dense_arm(), 0.4, 55.0, 80.0, 310.0, 120, mode="hybrid")
    sidecar = run.finalize()
    return (
        sidecar,
        [json.loads(x) for x in sidecar.read_text().splitlines()],
        run.record_path,
    )


def write_speed(tmp_path, producer, run_id="run-1"):
    run = producer.SpeedRun(
        tmp_path, run_id, DIGESTS, {"q200": sha("q")}, sha("m"), host(), clock=clock()
    )
    arm = dense_arm("bge-st-fp32", role="BASELINE")
    cfg = {"threads": 4, "batch": 32}
    run.add_speed(arm, "chunks_per_s", 12.5, "chunks/s", 3, 0.4, "chunks/s", cfg)
    run.add_speed(arm, "query_p50_ms", 65.0, "ms", 600, 3.0, "ms", cfg)
    run.add_noise_floor(
        arm, "chunks_per_s", 0.3, "chunks/s", replication_unit="arm", n=3
    )
    run.add_noise_floor(arm, "query_p50_ms", 2.0, "ms", replication_unit="session", n=3)
    sidecar = run.finalize()
    return (
        sidecar,
        [json.loads(x) for x in sidecar.read_text().splitlines()],
        run.record_path,
    )


def rewrite(sidecar, rows):
    sidecar.write_text("".join(json.dumps(r) + "\n" for r in rows))


def rehash(producer, row):
    row["row_sha256"] = producer.row_digest(row)
    return row


# ------------------------------------------------------------------ the pin


def test_the_pin_matches_the_landed_producer(monkeypatch):
    override = os.environ.get("EPYC_REPLRET_CAPTURE")
    path = Path(override) if override else reader.PRODUCER_PATH
    if not path.is_file():
        pytest.skip("capture module not landed here")
    assert reader._sha256(path) == reader.PRODUCER_SHA256


# ------------------------------------------------------------------ projection and grading


def test_recall_rows_project_and_grade_through_the_shared_ladder(tmp_path, producer):
    sidecar, rows, record = write_retrieval(tmp_path, producer)
    natives = reader.native_rows(sidecar)
    assert len(natives) == len(rows) == 2 + 1 + 4
    tuples = [reader.project(n) for n in natives]
    assert {t.source_kind for t in tuples} == {"repl-retrieval-eval"}
    hybrid = next(
        t for t in tuples if t.metric == "recall_at_5" and t.extra["mode"] == "hybrid"
    )
    assert hybrid.attestation_verified is True and hybrid.protocol_id == ""
    assert hybrid.category == "CANDIDATE" and hybrid.metric_direction == "higher_better"
    assert hybrid.reps == 120 and hybrid.reps_basis == "queries scored"
    assert hybrid.extra["instrument"] == "offline_recall"
    assert hybrid.extra["rule"]["k"] == 5 and hybrid.extra["rule"]["M"] == 0.10
    assert hybrid.extra["rule_amended"] is False
    assert hybrid.extra["digests"]["arm_manifest_sha256"] == sha("m")
    assert (
        hybrid.extra["arm"]["revision"] == "d4aa6901"
        and hybrid.extra["query_category"] == "all"
    )
    assert "spill_pointer_follows" in hybrid.claim
    assert ct.grade(hybrid)[:2] == (
        "Judged",
        "Located",
    )  # an observation, graded by the shared ladder
    diff = next(t for t in tuples if t.metric.endswith("paired_diff"))
    assert (
        diff.extra["against"]["arm_id"] == "bm25"
        and diff.extra["samples"]["resamples"] == 10000
    )
    cost = next(t for t in tuples if t.metric == "cpu_s_per_query")
    assert (
        cost.metric_direction == "lower_better"
        and cost.extra["host_context"]["cpu_list"] == "24-71"
    )
    assert len({t.measurement_id for t in tuples}) == len(tuples)
    record.write_text("changed")
    assert reader.project(natives[0]).attestation_verified is None


def test_speed_rows_project_with_their_context_and_floor(tmp_path, producer):
    sidecar, rows, _ = write_speed(tmp_path, producer)
    tuples = [reader.project_speed(n) for n in reader.speed_native_rows(sidecar)]
    assert len(tuples) == len(rows) == 2
    chunks = next(t for t in tuples if t.metric == "chunks_per_s")
    assert (
        chunks.source_kind == "repl-embedder-speed"
        and chunks.extra["instrument"] == "offline_speed"
    )
    assert chunks.attestation_verified is True and chunks.category == "BASELINE"
    assert chunks.extra["noise_floor"]["unit"] == "chunks/s"
    assert chunks.extra["noise_floor"]["replication_unit"] == "arm"
    ctx = chunks.extra["host_context"]
    assert (
        ctx["region_lock_claim"]
        and ctx["loadavg"]["end"]
        and ctx["frequency"]["throttled"] is False
    )
    assert ct.grade(chunks)[:2] == ("Judged", "Located")


def test_one_ladder_two_registrations():
    assert ct.registered()["repl-retrieval-eval"] is reader.project
    assert ct.registered()["repl-embedder-speed"] is reader.project_speed
    assert ct.source_classes()["repl-retrieval-eval"] == "measurement"
    assert ct.source_classes()["repl-embedder-speed"] == "measurement"
    assert [c for c in ct.ladders() if c == "measurement"] == ["measurement"]


# ------------------------------------------------------------------ refusals


@pytest.mark.parametrize(
    "mutation",
    [
        "value",
        "rehashed_value",
        "duplicate",
        "mixed_run",
        "renamed",
        "bad_json",
        "drop_recall",
        "arm_identity_split",
    ],
)
def test_any_bad_row_voids_the_whole_recall_sidecar(tmp_path, producer, mutation):
    sidecar, rows, _ = write_retrieval(tmp_path, producer)
    if mutation == "value":
        rows[1]["value"] += 0.01
    elif mutation == "rehashed_value":
        rows[1]["value"] += 0.01
        rehash(producer, rows[1])
    elif mutation == "duplicate":
        rows[2] = rows[1]
    elif mutation == "mixed_run":
        _, other_rows, _ = write_retrieval(tmp_path, producer, run_id="run-2")
        rows[0] = other_rows[0]
    elif mutation == "renamed":
        sidecar = sidecar.rename(tmp_path / "other.belief_measurements.jsonl")
    elif mutation == "drop_recall":
        rows = [r for r in rows if r["kind"] != "recall"]
    elif mutation == "arm_identity_split":
        # an arm whose identity differs between rows of one run (provenance re-sealed)
        rows[1]["extra"]["arm"]["revision"] = "ffffffff"
        rehash(producer, rows[1])
    if mutation == "bad_json":
        sidecar.write_text("{not json\n")
    else:
        rewrite(sidecar, rows)
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(sidecar)


def test_instruments_never_pool(tmp_path, producer):
    r_sidecar, r_rows, _ = write_retrieval(tmp_path, producer)
    s_dir = tmp_path / "speed"
    s_dir.mkdir()
    s_sidecar, s_rows, _ = write_speed(s_dir, producer)
    with pytest.raises(ct.ProjectionError, match="never pool"):
        reader.native_rows(s_sidecar)  # speed sidecar offered to the recall source
    with pytest.raises(ct.ProjectionError, match="never pool"):
        reader.speed_native_rows(r_sidecar)  # and the other way round
    mixed = tmp_path / "mixed.belief_measurements.jsonl"
    rewrite(mixed, [r_rows[0], s_rows[0]])
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(mixed)
    with pytest.raises(ct.ProjectionError):
        reader.speed_native_rows(mixed)
    online = copy.deepcopy(r_rows)
    for row in online:
        row["instrument"] = "online_spill_pointer_follows"
        rehash(producer, row)
    rewrite(r_sidecar, online)
    with pytest.raises(ct.ProjectionError, match="not one of"):
        reader.native_rows(r_sidecar)


def test_a_changed_rule_is_refused(tmp_path, producer):
    sidecar, rows, _ = write_retrieval(tmp_path, producer)
    for row in rows:
        row["extra"]["provenance"]["rule"]["n_min"] = 40
        row["extra"]["provenance_sha256"] = producer.content_hash(
            row["extra"]["provenance"]
        )
        rehash(producer, row)
    rewrite(sidecar, rows)
    with pytest.raises(ct.ProjectionError, match="no dated amendment"):
        reader.native_rows(sidecar)


def test_a_missing_claim_tuple_element_is_refused(tmp_path, producer):
    sidecar, rows, _ = write_retrieval(tmp_path, producer)
    del rows[0]["reps"]
    rewrite(sidecar, rows)
    with pytest.raises(ct.ProjectionError, match="claim tuple incomplete"):
        reader.native_rows(sidecar)


def test_a_speed_row_without_its_noise_floor_or_context_is_refused(tmp_path, producer):
    sidecar, rows, _ = write_speed(tmp_path, producer)
    good = copy.deepcopy(rows)
    rows[0]["samples"]["noise_floor"] = None
    rehash(producer, rows[0])
    rewrite(sidecar, rows)
    with pytest.raises(ct.ProjectionError, match="noise floor"):
        reader.speed_native_rows(sidecar)
    rows = copy.deepcopy(good)
    for row in rows:
        del row["extra"]["provenance"]["host_context"]["loadavg"]
        row["extra"]["provenance_sha256"] = producer.content_hash(
            row["extra"]["provenance"]
        )
        rehash(producer, row)
    rewrite(sidecar, rows)
    with pytest.raises(ct.ProjectionError, match="loadavg"):
        reader.speed_native_rows(sidecar)


def test_non_finite_n_and_ci_are_refused(tmp_path, producer):
    sidecar, rows, _ = write_retrieval(tmp_path, producer)
    good = copy.deepcopy(rows)
    rows[0]["value"] = float("nan")
    sidecar.write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )  # NaN literal survives json
    with pytest.raises(ct.ProjectionError, match="not a finite number"):
        reader.native_rows(sidecar)
    rows = copy.deepcopy(good)
    rows[0]["reps"] = 0
    rows[0]["samples"]["n"] = 0
    rewrite(sidecar, [rehash(producer, r) for r in rows])
    with pytest.raises(ct.ProjectionError, match="reps must be a positive int"):
        reader.native_rows(sidecar)
    rows = copy.deepcopy(good)
    diff = next(r for r in rows if r["kind"] == "paired_diff")
    diff["samples"]["ci95"] = [0.5, 0.1]
    rewrite(sidecar, [rehash(producer, r) for r in rows])
    with pytest.raises(ct.ProjectionError, match="ci95"):
        reader.native_rows(sidecar)


# ------------------------------------------------------------------ ingest


def test_ingest_wires_both_sources_and_keeps_them_apart(tmp_path, producer):
    assert SOURCES["repl-retrieval-eval"].task == "VB-UFH12-RETR"
    assert SOURCES["repl-embedder-speed"].task == "VB-UFH12-EMBSPEED"
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    _, r_rows, _ = write_retrieval(run_dir, producer, run_id="launch-1")
    _, s_rows, _ = write_speed(run_dir, producer, run_id="launch-1")
    assert (run_dir / "launch-1.belief_measurements.jsonl").is_file()
    assert (run_dir / "launch-1.speed.belief_measurements.jsonl").is_file()
    recall = ingest(
        Ledger(tmp_path / "ledger.jsonl"),
        "repl-retrieval-eval",
        [tmp_path],
        as_of=AS_OF,
    )
    assert recall["rows_projected"] == len(r_rows) and recall["units_matched"] == 1
    assert not recall["refused"] and not recall["declined"]
    speed = ingest(
        Ledger(tmp_path / "ledger2.jsonl"),
        "repl-embedder-speed",
        [tmp_path],
        as_of=AS_OF,
    )
    assert speed["rows_projected"] == len(s_rows) and speed["units_matched"] == 1
    assert not speed["refused"] and not speed["declined"]
    # an explicit wrong-instrument file is refused by name, never silently pooled
    wrong = ingest(Ledger(tmp_path / "ledger3.jsonl"), "repl-retrieval-eval",
                   [run_dir / "launch-1.speed.belief_measurements.jsonl"], as_of=AS_OF, dry_run=True)  # fmt: skip
    assert (
        wrong["rows_projected"] == 0 and "never pool" in wrong["refused"][0]["reason"]
    )


def test_retrospective_files_without_sidecars_yield_nothing(tmp_path, producer):
    """The 2026-10-20 pilot results.jsonl and the arm manifest carry no sidecar: zero claims."""
    (tmp_path / "results.jsonl").write_text(
        '{"metric": "chunks_per_s", "value": 13.0}\n'
    )
    (tmp_path / "arm_manifest.json").write_text('{"schema": "repl-emb-arm-manifest/1"}')
    for name in ("repl-retrieval-eval", "repl-embedder-speed"):
        report = ingest(
            Ledger(tmp_path / f"{name}.jsonl"),
            name,
            [tmp_path],
            as_of=AS_OF,
            dry_run=True,
        )
        assert report["rows_projected"] == 0 and report["units_matched"] == 0
