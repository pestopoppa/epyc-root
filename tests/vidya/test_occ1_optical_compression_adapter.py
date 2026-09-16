"""SC85: the OCC-1 optical-compression write-side hook and its strict reader.

These tests pin the following:

* A pre-hook run (``summary.json`` with no producer sidecar) emits ZERO rows, and so does a VOID
  run, because the writer refuses it.
* The ladder is not reimplemented. The grade asserted here is whatever ``claim_tuple.grade()``
  returns. With no codified OCC protocol that grade is ``Judged/Located``, an OBSERVATION.
* Identity is unique per (run, arm, metric). The LOCATOR names the run, never a question.
* Values are copied from ``summary.json`` and never recomputed. The serving identity and the suite
  fingerprint are required.
* A tampered or malformed sidecar is inadmissible as a whole. A decayed attestation grades DOWN.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct
from adapters import occ1_optical_compression as reader
from adapters import occ1_optical_compression_capture as capture

SUITE = "261d8ac1eaed" + "0" * 52
EMITTED = "2026-09-16T15:00:00Z"
PREREG = {"max_token_ratio": 0.5, "ni_margin_f1": 0.05}

SUMMARY = {
    "overall": "POSITIVE",
    "void_reasons": [],
    "suite_fingerprint": SUITE,
    "prereg": PREREG,
    "server_identity": {
        "build_info": "b10301-ef81196d5",
        "model_path": "/mnt/raid0/llm/models/lmstudio-community/Qwen3-VL-30B-A3B-Instruct-GGUF/"
                      "Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf",
        "n_ctx": 16384, "modalities": {"vision": True}, "total_slots": 1,
        "url": "http://127.0.0.1:18431", "problems": [],
    },
    "rows": [
        {"arm": "text", "requests": 39, "n": 1165, "em": 0.78, "f1": 0.861, "f1_se": 0.009,
         "unreadable": 0, "missing": 1, "truncated": 0, "prompt_tokens_mean": 8900.0},
        {"arm": "img-6x10-bw", "requests": 39, "n": 1165, "em": 0.74, "f1": 0.83, "f1_se": 0.01,
         "unreadable": 4, "missing": 0, "truncated": 0, "prompt_tokens_mean": 2600.0,
         "n_paired": 1165, "f1_delta": -0.031, "f1_delta_ci95": [-0.045, -0.018],
         "em_discordant_arm_only": 20, "em_discordant_text_only": 67, "em_mcnemar_p": 0.0001,
         "token_ratio_vs_text": 0.292, "verdict": "POSITIVE"},
        {"arm": "img-12x12u-bw", "requests": 39, "n": 1165, "em": 0.77, "f1": 0.85,
         "f1_se": 0.01, "unreadable": 0, "missing": 0, "truncated": 0,
         "prompt_tokens_mean": 6100.0, "n_paired": 1165, "f1_delta": -0.011,
         "f1_delta_ci95": [-0.02, -0.002], "em_discordant_arm_only": 10,
         "em_discordant_text_only": 22, "em_mcnemar_p": 0.05,
         "token_ratio_vs_text": 0.685, "verdict": "NEGATIVE_COST"},
    ],
}
# text: 2 rows; each image arm: 4 rows
N_ROWS = 2 + 4 + 4


def make_run(root: Path, *, name: str = "occ1-run-20260916", summary: dict | None = None) -> Path:
    run = root / name
    run.mkdir(parents=True)
    (run / "records.jsonl").write_text(json.dumps({"key": "text|c000", "items": []}) + "\n")
    (run / "summary.json").write_text(json.dumps(summary or SUMMARY))
    return run


def write_sidecar(run: Path, **kw) -> Path:
    return capture.write_belief_measurements(
        run, run_id=kw.pop("run_id", "occ1-20260916"), producer="run_occ1.py report",
        emitted_at=EMITTED, **kw)


def _rows(sidecar: Path) -> list[dict]:
    return [json.loads(x) for x in sidecar.read_text().splitlines() if x.strip()]


def _rewrite(sidecar: Path, rows: list[dict]) -> None:
    sidecar.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def _by(tuples, arm, metric):
    return next(t for t in tuples if t.extra["arm"] == arm and t.metric == metric)


def _tuples(run: Path):
    return [reader.project(n) for n in reader.rows_for_run(run)]


def test_well_formed_sidecar_projects_every_arm_metric(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    tuples = _tuples(run)
    assert len(tuples) == N_ROWS
    assert {t.metric for t in tuples if t.extra["arm"] == "text"} == {
        capture.METRIC_F1, capture.METRIC_EM}
    ratio = _by(tuples, "img-6x10-bw", capture.METRIC_TOKEN_RATIO)
    assert ratio.value == 0.292 and ratio.metric_direction == "lower_better"
    assert ratio.reps == 39 and ratio.reps_basis == "scored:chunk_requests"
    delta = _by(tuples, "img-6x10-bw", capture.METRIC_F1_DELTA)
    assert delta.value == -0.031 and delta.reps == 1165
    assert delta.extra["f1_delta_ci95"] == [-0.045, -0.018]
    assert delta.extra["verdict"] == "POSITIVE"
    assert "[95% CI -0.0450, -0.0180]" in delta.claim


def test_no_codified_protocol_grades_as_observation_via_the_shared_ladder(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    for tup in _tuples(run):
        assert tup.protocol_id == ""
        assert ct.grade(tup) == ct.grade(tup)  # pure
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Judged", "Located")
        assert any("no protocol citation" in r for r in reasons)


def test_a_cited_protocol_reaches_witnessed_attested(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run, protocol_id="measurement/protocols/occ1-optical-compression.md")
    tup = _tuples(run)[0]
    q, t, _ = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested")


def test_tuple_carries_serving_identity_suite_and_categories(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    tuples = _tuples(run)
    for tup in tuples:
        assert tup.extra["suite_fingerprint"] == SUITE
        assert tup.extra["serving"]["build_info"] == "b10301-ef81196d5"
        assert tup.extra["serving"]["url"] == "http://127.0.0.1:18431"
        assert tup.extra["overall_verdict"] == "POSITIVE"
        assert tup.extra["prereg_sha256"] == capture.content_hash(PREREG)
        assert tup.category == ("BASELINE" if tup.extra["arm"] == "text" else "CANDIDATE")


def test_locator_names_the_run_and_is_shared(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    locators = {t.attestation_locator for t in _tuples(run)}
    assert len(locators) == 1
    (loc,) = locators
    assert loc.startswith(f"occ1:occ1-20260916:suite{SUITE}:")
    assert loc.endswith("records.jsonl")


def test_identity_is_unique_and_stable(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    first = [t.measurement_id for t in _tuples(run)]
    assert len(set(first)) == N_ROWS
    write_sidecar(run)
    assert [t.measurement_id for t in _tuples(run)] == first


def test_distinct_runs_are_distinct_claims(tmp_path):
    a, b = make_run(tmp_path, name="a"), make_run(tmp_path, name="b")
    write_sidecar(a, run_id="occ1-a")
    write_sidecar(b, run_id="occ1-b")
    ids_a = {t.measurement_id for t in _tuples(a)}
    ids_b = {t.measurement_id for t in _tuples(b)}
    assert not ids_a & ids_b


def test_pre_hook_run_emits_zero_rows(tmp_path):
    run = make_run(tmp_path)
    assert (run / "summary.json").is_file()
    assert reader.rows_for_run(run) == ()


def test_missing_and_empty_sidecars_emit_zero_rows(tmp_path):
    assert reader.native_rows(tmp_path / "nope.jsonl") == ()
    empty = tmp_path / capture.SIDECAR_NAME
    empty.write_text("")
    assert reader.native_rows(empty) == ()


@pytest.mark.parametrize("mutate,match", [
    (lambda s: s.update(overall="VOID", void_reasons=["text-arm F1 0.41 < 0.60"]), "VOID"),
    (lambda s: s.update(void_reasons=["incomplete: 200/234 requests"]), "VOID"),
    (lambda s: s.update(server_identity=None), "server_identity"),
    (lambda s: s["server_identity"].update(problems=["model_path mismatch"]), "identity problems"),
    (lambda s: s["server_identity"].update(build_info=None), "build_info"),
    (lambda s: s.update(suite_fingerprint="short"), "suite_fingerprint"),
    (lambda s: s.update(prereg={}), "pre-registration"),
    (lambda s: s.update(rows=[r for r in s["rows"] if r["arm"] != "text"]), "baseline"),
    (lambda s: s["rows"][1].update(f1_delta_ci95=None), "f1_delta_ci95"),
    (lambda s: s["rows"][1].update(f1_delta=0.5), "inside its own CI"),
    (lambda s: s["rows"][1].update(verdict="NO_PAIRS"), "verdict"),
    (lambda s: s["rows"][1].pop("token_ratio_vs_text"), "token_ratio_vs_text"),
    (lambda s: s["rows"][1].update(arm="image-6x10"), "extra.arm"),
])
def test_writer_refuses_and_writes_nothing(tmp_path, mutate, match):
    summary = copy.deepcopy(SUMMARY)
    mutate(summary)
    run = make_run(tmp_path, summary=summary)
    with pytest.raises(capture.CaptureError, match=match):
        write_sidecar(run)
    assert not (run / capture.SIDECAR_NAME).exists()
    assert reader.rows_for_run(run) == ()


def test_writer_refuses_without_records(tmp_path):
    run = make_run(tmp_path)
    (run / "records.jsonl").unlink()
    with pytest.raises(capture.CaptureError, match="records missing"):
        write_sidecar(run)


def test_writer_copies_values_never_recomputes(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    tup = _by(_tuples(run), "text", capture.METRIC_F1)
    assert tup.value == 0.861


@pytest.mark.parametrize("tamper", [
    lambda r: r.update(value=0.99),
    lambda r: r.update(measurement_id="occ1_" + "0" * 24),
    lambda r: r["extra"].update(arm="img-8x8u-bw"),
    lambda r: r.update(metric_direction="higher_better") if r["metric"] ==
    capture.METRIC_TOKEN_RATIO else r.update(unit="bogus"),
    lambda r: r.update(schema="other"),
])
def test_any_malformed_row_voids_the_whole_sidecar(tmp_path, tamper):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    rows = _rows(sidecar)
    tamper(rows[-1])
    _rewrite(sidecar, rows)
    assert reader.rows_for_run(run) == ()


def test_non_json_line_voids_the_sidecar(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    sidecar.write_text(sidecar.read_text() + "not json\n")
    assert reader.rows_for_run(run) == ()


def test_rows_from_two_runs_in_one_sidecar_void_it(tmp_path):
    a, b = make_run(tmp_path, name="a"), make_run(tmp_path, name="b")
    rows = _rows(write_sidecar(a, run_id="occ1-a")) + _rows(write_sidecar(b, run_id="occ1-b"))
    _rewrite(a / capture.SIDECAR_NAME, rows)
    assert reader.rows_for_run(a) == ()


def test_project_rejects_a_bare_or_mutated_native(tmp_path):
    with pytest.raises(ct.ProjectionError):
        reader.project({"not": "a row"})
    run = make_run(tmp_path)
    write_sidecar(run)
    native = copy.deepcopy(reader.rows_for_run(run)[0])
    native["row"]["value"] = 42.0
    with pytest.raises(ct.ProjectionError):
        reader.project(native)


def test_decayed_attestation_grades_down_not_away(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run, protocol_id="measurement/protocols/occ1-optical-compression.md")
    (run / "records.jsonl").write_text("mutated\n")
    tuples = _tuples(run)
    assert len(tuples) == N_ROWS
    q, t, reasons = ct.grade(tuples[0])
    assert (q, t) == ("Witnessed", "Anchored")
    assert tuples[0].attestation_present is False
    assert any("not on disk" in r for r in reasons)


def test_projection_is_registered_under_the_shared_registry():
    assert reader.SOURCE_KIND in ct.registered()


def test_adapter_registers_no_ladder_of_its_own():
    owners = {module for module, _fn in ct.ladders().values()}
    assert reader.__name__ not in owners
    assert capture.__name__ not in owners


def test_frames_go_through_the_shared_emitter(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    frames = reader.frames_for_sidecar(sidecar, as_of="2026-09-16T16:00:00Z")
    assert len(frames) == 3 * N_ROWS
    support = [f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1")]
    assert {f["assertion"]["grade"]["Q"] for f in support} == {"Judged"}
