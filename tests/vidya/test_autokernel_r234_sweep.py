"""R23-4 sweep adapter: synthetic producer-boundary controls plus a read-only check of the real run.

The synthetic sweep is a fixture: it proves the strict reader's positive and refusal paths, never a
measurement. Grading is only ever `claim_tuple.grade()`.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
from adapters import autokernel_r234_sweep as a  # noqa: E402
import ingest_sources  # noqa: E402
from claim_tuple import ProjectionError, grade, registered  # noqa: E402
from ledger import Ledger  # noqa: E402

REAL = Path("/mnt/raid0/llm/tmp/vb-r234-wire-20261104/runs/dc2079b32cce475a9f4e62d782cb09ca")
BROAD = sorted(a.DESIGNED_BROAD)
PINNED = sorted(a.PINNED)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _rows(producer):
    files = {}
    for name, body in (("job.py", b"job"), ("summarize.py", b"summarize")):
        (producer / name).write_bytes(body)
        files[name] = {"path": str(producer / name), "sha256": _sha(body)}
    (producer / "SOURCE.json").write_text(json.dumps({k: v["sha256"] for k, v in files.items()}))
    identity = {"schema": a.IDENTITY_SCHEMA, "source_closure": files, "root_code": {"head": "x"},
                "grant": {"raw": "regions=x", "captured_at": 1793750399.0, "allowed_cpus": BROAD,
                          "environment": {"FILLER_DEADLINE": "1793759999", "FILLER_ID": "fixture"}},
                "model": {"path": a.MODEL}, "drafter": {"path": a.DRAFT}}
    packet = dict(source_commit=a.SOURCE, model_sha256=a.MODEL_SHA, draft_sha256=a.DRAFT_SHA,
                  probe_sha256=a.PROBE_SHA, expected_hip_sha256=a.HIP_SHA, expected_hip=a.HIP,
                  server=a.SERVER, closure_manifest=a.MANIFEST)
    rows, n = [], 0
    for i in range(7):
        for p in range(3):
            for k in range(3):
                ratio, accepted = (0.6, 6) if i == 1 else (0.5, 5)
                rate = 60.0 if i == 1 else 50.0
                start = float(n * 2)
                span = 2 / rate
                line = (f"slot print_timing: id 0 | task 1 | draft acceptance = {ratio} "
                        f"({accepted} accepted / 10 generated)")
                rows.append(dict(
                    schema=a.REQUEST_SCHEMA, arm=a.ORDER[i], arm_index=i, prompt_index=p, repeat=k,
                    acceptance=dict(state="window_correlated", ratio=ratio, accepted=accepted, generated=10,
                                    slot=0, task=1, raw=line),
                    residency=dict(resident=True, own_pid=100 + i, samples=[1 << 30, 1 << 30], readable=2,
                                   sample_monotonic_s=[start + .1, start + .2]),
                    server_pid=100 + i, host_affinity=PINNED if i == 5 else BROAD, argv=a._argv(i),
                    started_monotonic_s=start, ended_monotonic_s=start + 1, started_at=1793750400.0,
                    client_stream_events_s=rate, mapped_hip=[a.HIP], input_packet=copy.deepcopy(packet),
                    run_id="same", native_identity=copy.deepcopy(identity), disposition="complete",
                    prompt="fixture prompt", response_id_attribution="UNKNOWN",
                    mapped_closure=[dict(path=a.HIP, sha256=a.HIP_SHA)],
                    stream_capture=dict(completed=True, request=dict(messages=[dict(role="user", content="fixture prompt")]),
                                        events=[dict(elapsed_s=t, raw="data: " + json.dumps(
                                            {"choices": [{"delta": {"content": "x"}}]})) for t in (0, span)]
                                        + [dict(elapsed_s=span, raw="data: [DONE]")])))
                n += 1
    return rows


def _write(tmp, rows, *, native=True):
    run = tmp / "run"
    run.mkdir(exist_ok=True)
    path = run / "results.jsonl"
    raw = b"".join(json.dumps(r).encode() + b"\n" for r in rows)
    path.write_bytes(raw)
    if native:
        result = a._summarize(rows)
        result["response_id_attribution"] = "UNKNOWN"
        sha = _sha(raw)
        (run / "native-comparisons.json").write_text(json.dumps(dict(
            schema=a.PACKET_SCHEMA, request_sha256=sha, comparison=result,
            belief_measurements=a._mappings(rows, result, sha, str(path), marked=False))))
    return run


@pytest.fixture
def sweep(tmp_path):
    producer = tmp_path / "producer"
    producer.mkdir()
    return tmp_path, _rows(producer)


def test_positive_projects_every_adjacent_comparison_through_the_shared_grade(sweep):
    tmp, rows = sweep
    run = _write(tmp, rows)
    natives = a.native_rows(run)
    assert len(natives) == 18
    assert "autokernel-r234-native-sweep" in registered()
    tuples = [a.project(n) for n in natives]
    assert all(t.protocol_id == "" and t.source_kind == a.SOURCE_KIND for t in tuples)
    assert all(Path(t.applicability["model_file"]).name == "Qwen3.8-27B-Q8_0.gguf" and t.applicability["backend"] == "gpu"
               for t in tuples)
    assert all(t.extra["response_id_attribution"] == "UNKNOWN" for t in tuples)
    context = next(t for t in tuples if t.applicability["knob_family"] == "context"
                   and t.metric == "acceptance_ratio")
    assert context.value == 0.6 and context.observation["anchor_value"] == 0.5
    assert context.extra["producer_outcome_native"] == "outside-observed-baseline"
    for t in tuples:
        assert grade(t)  # the shared ladder decides; this module carries none


def test_outcome_is_the_descriptive_bracket_position_and_never_decisive(sweep):
    tmp, rows = sweep
    tuples = [a.project(n) for n in a.native_rows(_write(tmp, rows))]
    by = {(t.applicability["knob_family"], t.metric, t.measurement_id.split(":")[3]): t for t in tuples}
    # intervention median above both adjacent baselines -> improved; the producer's word is kept verbatim
    t = by[("context", "acceptance_ratio", "0")]
    assert (t.observation["outcome"], t.extra["producer_outcome_native"]) == ("improved", "outside-observed-baseline")
    assert t.observation["decisive"] is False and "effect_rel" not in t.observation
    # operator ruling 2026-11-10: every claim is marked low-confidence descriptive evidence, in the
    # rendered field (`outcome_native` after the producer's word) and in `extra`
    for x in tuples:
        assert x.observation["outcome_native"].endswith(a.LOW_CONFIDENCE)
        assert x.observation["outcome_native"].startswith(x.extra["producer_outcome_native"])
        assert x.extra["confidence"] == a.LOW_CONFIDENCE and len(x.observation["outcome_native"]) <= 120
    base = dict(baseline_before_median=0.5, baseline_after_median=0.6, intervention_median=0.55)
    assert a._outcome(dict(base, classification="within-observed-baseline")) == "null"
    assert a._outcome(dict(base, classification="outside-observed-baseline", intervention_median=0.7)) == "improved"
    assert a._outcome(dict(base, classification="outside-observed-baseline", intervention_median=0.4)) == "regressed"


def test_explicit_results_file_is_accepted_and_window_acceptance_is_never_response_id(sweep):
    tmp, rows = sweep
    run = _write(tmp, rows)
    assert len(a.native_rows(run / "results.jsonl")) == 18
    assert "response_id" not in json.dumps([a.project(n).claim for n in a.native_rows(run)]).replace(
        "response-ID attribution UNKNOWN", "")


def _mut(fn):
    def apply(rows):
        fn(rows)
    return apply


REFUSALS = {
    "window-only acceptance unknown": lambda r: r[0].update(acceptance={"state": "unknown"}),
    "response-id overclaim": lambda r: r[0].update(response_id_attribution="proven"),
    "no stream events": lambda r: r[0]["stream_capture"].update(events=[]),
    "stream rate does not rederive": lambda r: r[0].update(client_stream_events_s=r[0]["client_stream_events_s"] * 2),
    "acceptance raw does not rederive": lambda r: r[0]["acceptance"].update(raw="no acceptance line"),
    "residency outside window": lambda r: r[0]["residency"].update(sample_monotonic_s=[-1.0, -1.0]),
    "residency below 1 GiB": lambda r: r[0]["residency"].update(samples=[0, 1 << 30]),
    "mapped DSO digest missing": lambda r: r[0].update(mapped_closure=[]),
    "pre-hook (no native identity)": lambda r: [x.pop("native_identity") for x in r],
    "failed request": lambda r: r[3].update(failure="timeout"),
    "wrong source commit": lambda r: r[0]["input_packet"].update(source_commit="0" * 40),
    "wrong server invocation": lambda r: r[1].update(argv=a._argv(3)),
    "partial sweep": lambda r: r.pop(),
    "duplicate request": lambda r: r.append(copy.deepcopy(r[0])),
    "reordered requests": lambda r: r.insert(0, r.pop(1)),
    "wrong affinity": lambda r: r[0].update(host_affinity=PINNED),
    "request before grant": lambda r: [x.update(started_at=1.0) for x in r],
    "partial disposition": lambda r: r[2].update(disposition="partial"),
}


@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_refusal_controls(sweep, name):
    tmp, rows = sweep
    REFUSALS[name](rows)
    # the producer's own comparison file is built without the strict checks so only the reader refuses
    run = tmp / "run"
    run.mkdir()
    (run / "results.jsonl").write_bytes(b"".join(json.dumps(r).encode() + b"\n" for r in rows))
    (run / "native-comparisons.json").write_text("{}")
    with pytest.raises(ProjectionError):
        a.native_rows(run)


def test_producer_comparison_tamper_is_refused(sweep):
    tmp, rows = sweep
    run = _write(tmp, rows)
    f = run / "native-comparisons.json"
    packet = json.loads(f.read_text())
    packet["belief_measurements"][0]["value"] = 99
    f.write_text(json.dumps(packet))
    with pytest.raises(ProjectionError, match="mapping mismatch"):
        a.native_rows(run)
    packet["belief_measurements"][0]["value"] = a._mappings(rows, a._summarize(rows), "", "")[0]["value"]
    packet["comparison"]["comparisons"][0]["intervention_median"] = 0.0
    f.write_text(json.dumps(packet))
    with pytest.raises(ProjectionError, match="does not rederive"):
        a.native_rows(run)


def test_missing_native_comparisons_and_source_pin_tamper_are_refused(sweep):
    tmp, rows = sweep
    run = _write(tmp, rows, native=False)
    with pytest.raises(ProjectionError, match="native comparisons"):
        a.native_rows(run)
    run = _write(tmp, rows)
    (tmp / "producer" / "job.py").write_bytes(b"changed")
    a._derive.cache_clear()
    with pytest.raises(ProjectionError, match="changed since capture"):
        a.native_rows(run)


def test_cli_ingest_end_to_end_into_a_temp_ledger(sweep):
    tmp, rows = sweep
    run = _write(tmp, rows)
    ledger = Ledger(tmp / "ledger.jsonl")
    dry = ingest_sources.ingest(ledger, "ak-r234-sweep", [run], as_of="2026-11-10T00:00:00Z", dry_run=True)
    assert (dry["units_matched"], dry["rows_projected"], len(dry["refused"])) == (1, 18, 0)
    assert not (tmp / "ledger.jsonl").exists() or (tmp / "ledger.jsonl").read_text() == ""
    report = ingest_sources.ingest(ledger, "ak-r234-sweep", [run], as_of="2026-11-10T00:00:00Z")
    assert (report["rows_projected"], len(report["refused"]), report["frames_emitted"] > 0) == (18, 0, True)


def test_cli_counts_a_refused_sweep_by_name(sweep):
    tmp, rows = sweep
    rows[0].update(response_id_attribution="proven")
    run = tmp / "run"
    run.mkdir()
    (run / "results.jsonl").write_bytes(b"".join(json.dumps(r).encode() + b"\n" for r in rows))
    (run / "native-comparisons.json").write_text("{}")
    report = ingest_sources.ingest(Ledger(tmp / "l.jsonl"), "ak-r234-sweep", [run], as_of="2026-11-10T00:00:00Z",
                                   dry_run=True)
    assert len(report["refused"]) == 1 and report["rows_projected"] == 0


@pytest.mark.skipif(not (REAL / "native-comparisons.json").is_file(), reason="real run not on this host")
def test_real_run_rederives_and_projects_18_comparisons(tmp_path):
    report = ingest_sources.ingest(Ledger(tmp_path / "l.jsonl"), "ak-r234-sweep", [REAL],
                                   as_of="2026-11-10T00:00:00Z", dry_run=True)
    assert (report["units_matched"], report["rows_projected"], len(report["refused"])) == (1, 18, 0)
