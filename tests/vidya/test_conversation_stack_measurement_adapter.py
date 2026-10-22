"""VB-SPEECH-CONV-1 (+1B..1E): one fixture per record kind, every named refusal, and the round trip
through the one shared ladder (`claim_tuple.grade()`), never a grade computed by the adapter."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import conversation_stack_measurement as csm  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
H = {c: c * 64 for c in "abcdef"}  # distinct 64-hex digests
MANIFEST = "1" * 64


def harness(**kw):
    base = {"model": "whisper-large-v3-turbo", "quant": "f16",
            "runtime": {"kind": "port", "binary_sha256": H["a"]},
            "device": "cpu", "host_lane": "q0:cpus 0-47",
            "co_tenant": {"present": False, "sampled_during_row": True}, "llm_judged": False}
    base.update(kw)
    return base


def stt_fields(**kw):
    f = {"runner_id": "transcribe.cpp", "runner_commit": "abc1234", "ggml_version": "0.18.0",
         "quant": "f16", "backend": "cpu", "device": "cpu", "residency_proof": "ldd+linkage ok",
         "weights_sha256": H["b"], "decode_options": {"greedy": True, "temperature": 0},
         "kv_dtype": "f16", "language": "en", "language_mode": "forced",
         "normaliser_id": "stt_norm/v1", "normaliser_sha256": H["c"],
         "reference_set_id": "fleurs-test", "reference_set_track": "en", "scorer_sha256": "d" * 40,
         "manifest_sha256": MANIFEST, "n": 350, "unk_count": 0, "unk_ban": True,
         "segmentation_mode": "utterance", "stratum": "public-anchor",
         "corpus_id": "fleurs-en@" + MANIFEST[:12], "confirmation_reuse_n": 0,
         "column": "v1", "candidate": False, "streaming": False, "arm_id": "whisper-turbo",
         "whisper_parity_gate_ref": "CS-8.STT3:transcribe.cpp@abc1234:pass"}
    f.update(kw)
    return f


def records():
    """One record per measured kind (the lexicon trial is one record per lexicon metric) plus one
    literature reference row."""
    stt = {"record_kind": "stt_arm_wer", "subject": "whisper-turbo:en", "metric": "stt_corpus_wer",
           "value": 4.76, "unit": "wer_pct", "metric_direction": "lower", "category": "BASELINE",
           "protocol_id": "P-STT-1", "harness": harness(), "fields": stt_fields()}
    fit = {"record_kind": "stt_fitting_screen", "subject": "whisper-turbo:voxpopuli-en",
           "metric": "stt_fitting_accept_ref", "value": 0.04, "unit": "fraction",
           "metric_direction": "fitting indicator: higher accept-ref = more fitting; reports, never gates",
           "harness": harness(),
           "fields": {"arm": "whisper-turbo", "model_revision": "r1", "probe": "ref_disagreement",
                      "accept_ref": 0.04, "accept_ref_ci": [0.02, 0.07], "n_eligible": 200,
                      "panel": "p3", "predictions_sha256": H["d"], "language": "en",
                      "stratum": "public-anchor", "gates": False,
                      "paired_wer_measurement_id": "@0"}}
    lex_vals = {"term_recall": 0.9, "term_precision": 0.8, "insertions_per_hour": 1.5,
                "non_list_word_wer": 5.1}
    lex = [{"record_kind": "stt_lexicon_trial", "subject": "whisper-turbo:lex", "metric": m,
            "value": lex_vals[src], "unit": "as_named", "metric_direction":
                csm.METRIC_DIRECTIONS[m].split("_")[0], "harness": harness(),
            "fields": stt_fields(lexicon_sha256=H["e"], boost_alpha=1.5, list_scope="domain",
                                 case_policy="insensitive", **lex_vals)}
           for m, src in csm.LEXICON_METRIC_FIELD.items()]
    vad = {"record_kind": "vad_arm", "subject": "silero-v5:it", "metric": "false_cut_rate",
           "value": 0.03, "unit": "fraction", "metric_direction": "lower",
           "harness": harness(model="silero-vad-v5", quant="f32"),
           "fields": {"vad_model": "silero-vad-v5", "weights_sha256": H["f"], "runtime": "onnx",
                      "hop_ms": 32, "params": {"threshold": 0.5, "smoothing": 0.1, "padding": 30,
                                               "min_speech": 250, "min_silence": 100},
                      "language": "it", "dataset_revision": "cs45-v2@cb6b08fea",
                      "corpus_manifest_sha256": MANIFEST, "confidence_mask": "speech>=0.5",
                      "n": 278}}
    eot = {"record_kind": "end_of_turn", "subject": "text-llm:cs45", "metric": "eot_fpr",
           "value": 0.12, "unit": "fraction", "metric_direction": "lower",
           "harness": harness(model="qwen3-1.7b", quant="Q8_0"),
           "fields": {"turn_arm": "text_llm_prompt", "interim_source": "nemotron-3.5@6",
                      "prompt_sha256": H["a"], "n": 112}}
    ttf = {"record_kind": "time_to_final", "subject": "nemotron:clip7",
           "metric": "time_to_final_after_vad_end_s", "value": 0.42, "unit": "s",
           "metric_direction": "lower", "harness": harness(model="nemotron-3.5", quant="Q8_0"),
           "fields": {"method_protocol": "aa-forced-endpoint-v1", "chunk_ms": 80,
                      "silero_pin_sha256": H["f"], "stt_arm": "nemotron-3.5",
                      "att_context_right": 6, "device": "cpu",
                      "clip_id": "clip7@" + MANIFEST[:12], "language": "en", "n": 20}}
    intr = {"record_kind": "interruption", "subject": "barge-in:set5",
            "metric": "t_stop_backchannel_s", "value": 2.5, "unit": "s",
            "metric_direction": "higher_is_correct", "harness": harness(),
            "fields": {"record_set": "CS-4.set5", "gate_under_test": "silero-vad-v5@0.5",
                       "timing_oracle": {"kind": "asr_word_times", "id": "whisper-large-v3@dtw",
                                         "merge_params": {"gap_ms": 120}},
                       "event_class": "backchannel", "n": 40}}
    deg = {"record_kind": "coresidency_degraded", "subject": "parakeet-1t:corun",
           "metric": "stt_rtf_corun", "value": 0.31, "unit": "rtf", "metric_direction": "lower",
           "harness": harness(model="parakeet-tdt-v3", quant="Q8_0",
                              co_tenant={"present": True, "sampled_during_row": True,
                                         "llm": "qwen3-1.7b-Q8_0 llama-bench", "device": "cpu",
                                         "np": 1, "generating": True}),
           "fields": {"record_set": "CS-26.F1", "legs": [
               {"leg": "A", "arm_id": "neighbour-solo", "neighbour_tok_s": 40.0},
               {"leg": "B", "arm_id": "neighbour+parakeet-1t", "neighbour_tok_s": 37.5},
               {"leg": "A", "arm_id": "neighbour-solo", "neighbour_tok_s": 39.6}],
               "region_lock_claim_id": "claim-q1-20261022", "cpu_list": "96-143",
               "thread_counts": {"speech": 1, "neighbour": 8},
               "neighbour": {"identity": "Qwen3-1.7B Q8_0 llama-bench " + H["c"][:12]},
               "speech_cpu_time_per_thread_s": [3.1], "n": 22}}
    gen = {"record_kind": "generic", "subject": "lid:fleurs-1s", "metric": "lid_accuracy",
           "value": 0.93, "unit": "fraction", "metric_direction": "higher_better",
           "harness": harness(runtime={"kind": "reference", "upstream_digest": "hf:abc"}),
           "fields": {"router": "whisper-lid", "n": 400}}
    lit = {"record_kind": "literature_reference", "subject": "parakeet-tdt-v3:open-asr",
           "metric": "wer_pct", "value": 6.3, "unit": "wer_pct", "metric_direction": "lower",
           "fields": {"source_kind": "leaderboard", "source_name": "Open ASR leaderboard",
                      "source_url": "https://huggingface.co/spaces/hf-audio/open_asr_leaderboard",
                      "published_date": "2026-10-01", "set_list": ["librispeech", "voxpopuli"],
                      "normaliser": "open_asr_leaderboard EnglishTextNormalizer"}}
    return [stt, fit, *lex, vad, eot, ttf, intr, deg, gen, lit]


def rec_of(kind):
    return next(r for r in records() if r["record_kind"] == kind)


def write_fixture(tmp: Path, recs=None) -> Path:
    res = tmp / "cs_results.json"
    res.write_text("{}")
    return csm.write_belief_measurements(tmp, run_id="cs-run-1", producer="cs-harness",
                                         results_path=res, records=recs or records(),
                                         emitted_at=WHEN)


def _first_row(tmp, kind):
    sc = write_fixture(tmp)
    return next(n["row"] for n in csm.native_rows(sc) if n["row"]["record_kind"] == kind)


def _mutate(row, fn):
    row = copy.deepcopy(row)
    fn(row)
    row["measurement_id"] = csm._identity(row)
    return csm.ns.seal(row)


# --- one fixture per kind, graded by the shared ladder -----------------------------------------

def test_every_kind_projects_and_is_graded_only_by_claim_tuple_grade(tmp_path, monkeypatch):
    natives = csm.native_rows(write_fixture(tmp_path))
    kinds = {n["row"]["record_kind"] for n in natives}
    assert kinds == csm.RECORD_KINDS - {csm.LITERATURE_KIND}
    calls = []
    real = ct.grade
    monkeypatch.setattr(ct, "grade", lambda t: calls.append(t) or real(t))
    for nat in natives:
        tup = csm.project(nat)
        assert isinstance(tup, ct.ClaimTuple) and tup.source_class == "measurement"
        q, t, reasons = ct.grade(tup)
        # P-STT-1 WER is "not a claim without its owning release protocol" (MEASUREMENT.md), and
        # nothing else is admissible until the CS-2 Annex S amendment: every kind is an OBSERVATION.
        assert tup.protocol_id == "" and q == "Judged" and t == "Located"
    assert len(calls) == len(natives)
    # the adapter module never calls grade itself
    assert "grade(" not in Path(csm.__file__).read_text().replace("claim_tuple.grade()", "")


def test_registered_projection_is_the_module_project():
    assert ct.registered()[csm.SOURCE_KIND].__module__ == csm.project.__module__
    assert ct.source_classes()[csm.SOURCE_KIND] == "measurement"


def test_frames_emit_for_every_measured_row(tmp_path):
    sc = write_fixture(tmp_path)
    assert len(csm.frames_for_sidecar(sc, as_of="2026-10-22T11:00:00Z")) == 3 * len(
        csm.native_rows(sc))


def test_directions_are_per_metric_and_mapped_from_native_words(tmp_path):
    rows = {(n["row"]["record_kind"], n["row"]["metric"]): n["row"]
            for n in csm.native_rows(write_fixture(tmp_path))}
    assert rows[("stt_arm_wer", "stt_corpus_wer")]["metric_direction"] == "lower_better"
    assert rows[("stt_arm_wer", "stt_corpus_wer")]["metric_direction_native"] == "lower"
    bc = rows[("interruption", "t_stop_backchannel_s")]
    assert bc["metric_direction"] == "higher_better"
    assert bc["metric_direction_native"] == "higher_is_correct"
    assert rows[("stt_fitting_screen", "stt_fitting_accept_ref")]["metric_direction"] == "lower_better"
    assert rows[("stt_lexicon_trial", "lexicon_term_recall")]["metric_direction"] == "higher_better"
    assert rows[("stt_lexicon_trial", "lexicon_insertions_per_hour")]["metric_direction"] == "lower_better"
    assert rows[("generic", "lid_accuracy")]["metric_direction"] == "higher_better"


def test_contradicting_direction_is_refused(tmp_path):
    rec = rec_of("stt_arm_wer")
    rec["metric_direction"] = "higher"
    with pytest.raises(csm.CaptureError, match="is lower_better"):
        write_fixture(tmp_path, [rec])


def test_reference_harness_row_is_never_a_serving_claim(tmp_path):
    row = _first_row(tmp_path, "generic")
    assert csm.REFERENCE_MARKER in row["claim"]
    tup = csm.project({"row": row})
    assert tup.extra["serving_claim"] is False
    assert any("never a serving claim" in c for c in tup.extra["cautions"])
    bad = _mutate(row, lambda r: r.__setitem__("claim", "lid accuracy 0.93"))
    assert any("reference-harness" in p for p in csm.validate_row(bad))


def test_base_harness_fields_are_required(tmp_path):
    base = rec_of("generic")
    for mutate in (lambda h: h.pop("quant"), lambda h: h.pop("host_lane"),
                   lambda h: h["runtime"].pop("upstream_digest"),
                   lambda h: h["co_tenant"].pop("sampled_during_row"),
                   lambda h: h.update(co_tenant={"present": True, "sampled_during_row": True}),
                   lambda h: h.update(llm_judged=True)):
        rec = copy.deepcopy(base)
        mutate(rec["harness"])
        with pytest.raises(csm.CaptureError):
            write_fixture(tmp_path, [rec])


def test_llm_judged_row_pins_the_judge(tmp_path):
    rec = copy.deepcopy(rec_of("generic"))
    rec["harness"]["llm_judged"] = True
    rec["harness"]["judge"] = {"model": "qwen3.8-27b", "model_digest": H["e"],
                               "prompt_sha256": H["d"], "temperature": 0, "seed": 7}
    nat = csm.native_rows(write_fixture(tmp_path, [rec]))
    assert any("SC58" in c for c in csm.project(nat[0]).extra["cautions"])


# --- protocol: v1 vs v2_candidate --------------------------------------------------------------

def test_v2_candidate_column_projects_as_an_observation(tmp_path):
    rec = rec_of("stt_arm_wer")
    rec["fields"].update(column="v2_candidate", candidate=True)
    tup = csm.project(csm.native_rows(write_fixture(tmp_path, [rec]))[0])
    assert tup.protocol_id == "" and tup.extra["protocol_id_native"] == "P-STT-1"
    assert tup.extra["protocol_status"] == "v2_candidate_column_unratified"
    assert ct.grade(tup)[0] == "Judged"


def test_unratified_protocol_on_other_kinds_is_kept_but_not_projected(tmp_path):
    rec = rec_of("vad_arm")
    rec["protocol_id"] = "CS-2-draft"
    tup = csm.project(csm.native_rows(write_fixture(tmp_path, [rec]))[0])
    assert tup.protocol_id == "" and tup.extra["protocol_id_native"] == "CS-2-draft"


# --- 1B: the scorer mapping and the two refusals -----------------------------------------------

def test_scorer_record_maps_by_renaming_only(tmp_path):
    scorer = {"schema_version": 1, "metric": "stt_corpus_wer", "metric_direction": "lower",
              "value": 4.76, "normaliser": {"id": "stt_norm/v1", "sha256": H["c"]},
              "reference_set": {"id": "fleurs-test", "track": "en"},
              "arm": {k: v for k, v in stt_fields().items()
                      if k in ("runner_id", "runner_commit", "ggml_version", "quant", "backend",
                               "device", "residency_proof", "weights_sha256", "decode_options",
                               "kv_dtype", "arm_id", "whisper_parity_gate_ref")},
              **{k: v for k, v in stt_fields().items()
                 if k in ("scorer_sha256", "manifest_sha256", "corpus_id", "language",
                          "language_mode", "n", "unk_count", "unk_ban", "segmentation_mode",
                          "stratum", "confirmation_reuse_n", "column", "candidate")},
              "taxonomy": {"ok": 340, "empty": 2}, "protocol_id": "P-STT-1"}
    rec = csm.stt_record_from_scorer(scorer, harness=harness())
    nat = csm.native_rows(write_fixture(tmp_path, [rec]))
    assert len(nat) == 1 and nat[0]["row"]["fields"]["native_schema_version"] == 1
    tup = csm.project(nat[0])
    assert tup.protocol_id == "" and tup.extra["protocol_id_native"] == "P-STT-1"
    assert ct.grade(tup)[:2] == ("Judged", "Located")


def test_refuses_non_production_runner_without_parity_gate_ref(tmp_path):
    row = _first_row(tmp_path, "stt_arm_wer")
    bad = _mutate(row, lambda r: r["fields"].pop("whisper_parity_gate_ref"))
    with pytest.raises(ct.ProjectionError, match="whisper_parity_gate_ref"):
        csm.project({"row": bad})
    rec = rec_of("stt_arm_wer")
    rec["fields"].pop("whisper_parity_gate_ref")
    with pytest.raises(csm.CaptureError, match="whisper_parity_gate_ref"):
        write_fixture(tmp_path, [rec])


def test_production_runner_needs_no_parity_ref_but_must_carry_the_production_commit(tmp_path):
    rec = rec_of("stt_arm_wer")
    rec["fields"].update(runner_id="whisper.cpp@production-speech-v1", runner_commit="b30737922")
    rec["fields"].pop("whisper_parity_gate_ref")
    assert csm.native_rows(write_fixture(tmp_path, [rec]))
    rec["fields"]["runner_commit"] = "deadbeef1"
    with pytest.raises(csm.CaptureError, match="cannot be claimed by a label"):
        write_fixture(tmp_path, [rec])


def test_refuses_confirmation_stratum_with_per_utterance_values(tmp_path):
    rec = rec_of("stt_arm_wer")
    rec["fields"]["stratum"] = "confirmation"
    assert csm.native_rows(write_fixture(tmp_path, [rec]))  # aggregates only: accepted
    row = _first_row(tmp_path, "stt_arm_wer")
    for leak in ({"per_utterance": [1.0, 2.0]}, {"utterance_ids": ["u1"]},
                 {"breakdown": [{"utterance_id": "u1", "wer": 3.0}]}):
        bad = _mutate(row, lambda r, leak=leak: (r["fields"].update(stratum="private", **leak)))
        with pytest.raises(ct.ProjectionError, match="per-utterance"):
            csm.project({"row": bad})


def test_transcribe_cpp_whisper_row_needs_kv_dtype(tmp_path):
    rec = rec_of("stt_arm_wer")
    rec["fields"].pop("kv_dtype")
    with pytest.raises(csm.CaptureError, match="kv_dtype"):
        write_fixture(tmp_path, [rec])


def test_streaming_arm_needs_its_lookahead(tmp_path):
    rec = rec_of("stt_arm_wer")
    rec["fields"]["streaming"] = True
    with pytest.raises(csm.CaptureError, match="lookahead"):
        write_fixture(tmp_path, [rec])
    rec["fields"]["lookahead"] = [70, 1, 13]
    assert csm.native_rows(write_fixture(tmp_path, [rec]))


def test_fitting_screen_must_share_the_write_with_its_wer_row(tmp_path):
    fit = rec_of("stt_fitting_screen")
    fit["fields"]["paired_wer_measurement_id"] = "csm_" + "0" * 24
    with pytest.raises(csm.CaptureError, match="same write"):
        write_fixture(tmp_path, [rec_of("stt_arm_wer"), fit])


# --- 1C ------------------------------------------------------------------------------------------

def test_refuses_vad_tuple_without_weights_sha(tmp_path):
    row = _first_row(tmp_path, "vad_arm")
    bad = _mutate(row, lambda r: r["fields"].pop("weights_sha256"))
    with pytest.raises(ct.ProjectionError, match="weights_sha256"):
        csm.project({"row": bad})


def test_eot_and_ttf_field_rules(tmp_path):
    eot = rec_of("end_of_turn")
    eot["fields"].pop("prompt_sha256")
    with pytest.raises(csm.CaptureError, match="prompt_sha256"):
        write_fixture(tmp_path, [eot])
    ttf = rec_of("time_to_final")
    ttf["fields"]["method_protocol"] = "other"
    with pytest.raises(csm.CaptureError, match="aa-forced-endpoint-v1"):
        write_fixture(tmp_path, [ttf])


# --- 1D ------------------------------------------------------------------------------------------

def test_refuses_interruption_whose_timing_oracle_is_the_gate_under_test(tmp_path):
    row = _first_row(tmp_path, "interruption")
    bad = _mutate(row, lambda r: r["fields"]["timing_oracle"].update(id="Silero-VAD-v5@0.5"))
    with pytest.raises(ct.ProjectionError, match="circular timing"):
        csm.project({"row": bad})


# --- 1E ------------------------------------------------------------------------------------------

def test_refuses_degraded_tuple_without_aba_arm_ids_or_claim(tmp_path):
    row = _first_row(tmp_path, "coresidency_degraded")
    for mutate in (lambda r: r["fields"]["legs"][2].pop("arm_id"),
                   lambda r: r["fields"]["legs"][2].update(arm_id="other"),
                   lambda r: r["fields"].pop("region_lock_claim_id")):
        with pytest.raises(ct.ProjectionError, match="REFUSED"):
            csm.project({"row": _mutate(row, mutate)})


# --- literature, tamper, foreign -----------------------------------------------------------------

def test_literature_rows_never_enter_as_measurements(tmp_path):
    sc = write_fixture(tmp_path)
    lit = csm.literature_rows(sc)
    assert len(lit) == 1 and lit[0]["source_class"] == "literature"
    assert lit[0]["fields"]["normaliser"] and lit[0]["fields"]["set_list"]
    assert all(n["row"]["record_kind"] != "literature_reference" for n in csm.native_rows(sc))
    with pytest.raises(ct.ProjectionError, match="literature-class"):
        csm.project({"row": lit[0]})
    rec = rec_of("literature_reference")
    rec["fields"].pop("normaliser")
    with pytest.raises(csm.CaptureError, match="normaliser"):
        write_fixture(tmp_path, [rec])


def test_tamper_voids_the_file_and_mutated_attestation_grades_down(tmp_path):
    sc = write_fixture(tmp_path)
    lines = sc.read_text().splitlines()
    row = json.loads(lines[0])
    row["value"] = 1.0
    lines[0] = json.dumps(row, sort_keys=True)
    sc.write_text("\n".join(lines) + "\n")
    assert csm.native_rows(sc) == ()
    sc = write_fixture(tmp_path)
    (tmp_path / "cs_results.json").write_text("tamper")
    nat = csm.native_rows(sc)
    assert nat and ct.grade(csm.project(nat[0]))[:2] != ("Witnessed", "Attested")


def test_foreign_row_refused_and_no_sidecar_is_zero_rows(tmp_path):
    assert csm.rows_for_run(tmp_path) == ()
    with pytest.raises(ct.ProjectionError):
        csm.project({"row": {"schema": "other"}})


def _bakeoff_scorer():
    import importlib
    import os
    root = Path(os.environ.get("STT_BAKEOFF_TEST_RESEARCH_ROOT",
                               "/workspace/repos/epyc-inference-research"))
    if not (root / "scripts/speech/stt_bakeoff/scorer.py").is_file():
        pytest.skip(f"research stt_bakeoff scorer not present under {root}")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return importlib.import_module("scripts.speech.stt_bakeoff.scorer")


def _bakeoff_manifest(S, stratum):
    import hashlib
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
    rows = [{"utterance_id": f"u{i}", "pcm_sha256": h(f"pcm{i}"),
             "reference_raw": "the cat sat on the mat",
             "hypothesis_raw": "the cat sat on a mat" if i % 3 == 0 else "the cat sat on the mat",
             "language": "en", "set_id": "fleurs-en", "reference_track": "verbatim",
             "content_stratum": "clean_read"} for i in range(12)]
    arm = {"arm_id": "parakeet-v3", "arm_kind": S.ARM_KIND_OFFLINE, "runner_id": "transcribe.cpp",
           "runner_commit": "db678a03", "ggml_version": "0.26.0", "quant": "f16", "backend": "cpu",
           "device": "cpu", "residency_proof": "verify_ggml_linkage PASS", "weights_sha256": h("w"),
           "decode_options": {"greedy": True}, "whisper_parity_gate_ref": "CS-8.STT3@fixture",
           "unk_ban": True}
    return {"schema_version": S.RAW_MANIFEST_SCHEMA_VERSION, "corpus_id": "synth", "stratum": stratum,
            "language_mode": "forced", "segmentation_mode": "none", "reference_set_id": "fleurs-test",
            "arm": arm, "rows": rows}


def test_real_bakeoff_scorer_record_maps_projects_and_grades(tmp_path):
    """Cross-repo seam: a record from the actual CS-8.STT1 scorer goes through the writer."""
    S = _bakeoff_scorer()
    rec0 = S.score_arm(_bakeoff_manifest(S, "public"), column="v1", bootstrap_resamples=50,
                       bootstrap_seed=42)["records"][0]
    hz = harness()
    hz["model"] = "parakeet-tdt-0.6b-v3"
    nat = csm.native_rows(write_fixture(tmp_path, [csm.stt_record_from_scorer(rec0, harness=hz)]))
    tup = csm.project(nat[0])
    assert tup.metric == "stt_corpus_wer" and tup.metric_direction == "lower_better"
    assert ct.grade(tup)[:2] == ("Judged", "Located")


def test_unsealed_confirmation_scorer_record_is_refused(tmp_path):
    """A confirmation stratum scored without custody carries no reuse counter: refused."""
    S = _bakeoff_scorer()
    rec0 = S.score_arm(_bakeoff_manifest(S, "confirmation"), column="v1", bootstrap_resamples=50,
                       bootstrap_seed=42)["records"][0]
    hz = harness()
    hz["model"] = "parakeet-tdt-0.6b-v3"
    with pytest.raises(Exception, match="confirmation_reuse_n"):
        write_fixture(tmp_path, [csm.stt_record_from_scorer(rec0, harness=hz)])
