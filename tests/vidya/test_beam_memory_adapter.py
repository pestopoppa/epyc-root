"""SC68 — the BEAM write-side hook and its strict reader.

What is pinned here:

* the doctrine boundary — a folded/judged BEAM artifact with no producer sidecar emits ZERO rows;
* the ladder is not reimplemented — the grade asserted is whatever ``claim_tuple.grade()`` returns;
* BOTH folds are recorded: the BEAM-fold headline is the claim, and the rubric-item micro-average
  and binarised pass count ride as context in the SAME tuple (never a second claim);
* the claim value must re-derive as the unweighted mean of its ten ability columns, so the other
  fold can never be written under this metric;
* the judge is identity, the locator names the run, and a tampered sidecar voids whole.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import beam_memory as reader  # noqa: E402
from adapters import beam_memory_capture as capture  # noqa: E402

_SCORES = {
    "abstention": 0.9, "contradiction_resolution": 0.05, "event_ordering": 0.3,
    "information_extraction": 0.6, "instruction_following": 0.7, "knowledge_update": 0.55,
    "multi_session_reasoning": 0.25, "preference_following": 0.65, "summarization": 0.35,
    "temporal_reasoning": 0.2,
}
PER_ABILITY = {a: {"questions": 40, "score": s} for a, s in sorted(_SCORES.items())}
HEADLINE = sum(PER_ABILITY[a]["score"] for a in sorted(PER_ABILITY)) / 10

SUMMARY = {
    "scorer_version": 1,
    "run_id": "beam-20260915-a",
    "model_role": "ingest_long_context",
    "split": "100K",
    "judge_model": "qwen3.8-27b-judge",
    "judge_prompt_version": "beam-unified-b2da22ea+question/v1",
    "question_in_judge_prompt": True,
    "checked_against_dataset": True,
    "context_mode_by_row": {"full": 400},
    "fold": "beam_macro",
    "fold_version": 1,
    "headline": HEADLINE,
    "per_ability": PER_ABILITY,
    "abilities_reported": sorted(_SCORES),
    "abilities_missing": [],
    "n_questions": 400,
    "n_nuggets": 1051,
    "event_ordering_basis": "nugget_mean_fallback",
    "secondary_diagnostics": {
        "label": "SECONDARY DIAGNOSTICS - not the BEAM fold; never quote as a BEAM score",
        "rubric_item_micro_average": 0.4012,
        "binarised_threshold": 0.5,
        "binarised_pass_count": 515,
        "binarised_total_checks": 1051,
        "binarised_pass_rate": 515 / 1051,
    },
}


def make_run(root: Path, *, name: str = "beam-20260915-a") -> Path:
    run = root / name
    run.mkdir()
    (run / "beam_score.json").write_text(json.dumps({"summary": SUMMARY, "per_question": []}))
    return run


def write_sidecar(run: Path, *, summary=None, **overrides) -> Path:
    kwargs = dict(summary=summary or SUMMARY, run_id="beam-20260915-a",
                  producer="score_beam_run.py", arm="full", emitted_at="2026-09-15T12:00:00Z")
    kwargs.update(overrides)
    return capture.write_belief_measurements(run / "beam_score.json", **kwargs)


def _rewrite(sidecar: Path, mutate, *, rehash: bool = False) -> None:
    rows = [json.loads(line) for line in sidecar.read_text().splitlines()]
    mutate(rows)
    if rehash:
        for row in rows:
            row["row_sha256"] = capture.row_digest(row)
    sidecar.write_text("".join(json.dumps(r) + "\n" for r in rows))


# --- the round trip, graded by THE ladder ---------------------------------------------------

def test_well_formed_sidecar_projects_one_claim_at_witnessed_attested(tmp_path):
    natives = reader.native_rows(write_sidecar(make_run(tmp_path)))
    assert len(natives) == 1, "the BEAM-fold headline is the ONLY claim per arm"
    q, t, reasons = ct.grade(reader.project(natives[0]))
    assert (q, t) == ("Witnessed", "Attested"), reasons
    assert reasons == []


def test_both_folds_are_recorded_in_the_same_tuple(tmp_path):
    tup = reader.project(reader.native_rows(write_sidecar(make_run(tmp_path)))[0])
    assert tup.metric == capture.METRIC
    assert tup.value == pytest.approx(HEADLINE)
    assert tup.extra["fold"] == "beam_macro"
    assert tup.extra["rubric_item_micro_average"] == 0.4012
    assert tup.extra["binarised_pass_count"] == 515
    assert tup.extra["binarised_total_checks"] == 1051
    assert tup.extra["binarised_threshold"] == 0.5
    assert "NOT the claim" in tup.claim and "micro-average 0.4012" in tup.claim
    assert "515/1051" in tup.claim


def test_tuple_carries_judge_identity_arm_and_harness_note(tmp_path):
    tup = reader.project(reader.native_rows(write_sidecar(make_run(tmp_path)))[0])
    assert tup.extra["judge_model"] == "qwen3.8-27b-judge"
    assert tup.extra["judge_prompt_version"] == "beam-unified-b2da22ea+question/v1"
    assert tup.extra["question_in_judge_prompt"] is True
    assert tup.extra["arm"] == "full" and tup.extra["split"] == "100K"
    assert tup.extra["event_ordering_basis"] == "nugget_mean_fallback"
    assert "single-nugget refusal template" in tup.extra["harness_note"]
    assert tup.reps == 400 and tup.reps_basis == "scored:questions"
    assert tup.metric_direction == "higher_better"


def test_locator_names_the_run_never_a_per_question_file(tmp_path):
    tup = reader.project(reader.native_rows(write_sidecar(make_run(tmp_path)))[0])
    assert tup.attestation_locator == "beam:beam-20260915-a:100K:arm-full:judge-qwen3.8-27b-judge"


def test_identity_is_stable_and_separates_arms_and_judges(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    first = reader.project(reader.native_rows(sidecar)[0]).measurement_id
    assert first == reader.project(reader.native_rows(sidecar)[0]).measurement_id
    ids = {first}
    for i, arm in enumerate(sorted(capture.ARMS - {"full"})):
        ids.add(reader.project(reader.native_rows(
            write_sidecar(make_run(tmp_path, name=f"r{i}"), arm=arm,
                          summary={**SUMMARY, "context_mode_by_row": {arm: 400}}))[0]
        ).measurement_id)
    ids.add(reader.project(reader.native_rows(write_sidecar(
        make_run(tmp_path, name="judge2"),
        summary={**SUMMARY, "judge_model": "gpt-4.1-mini"}))[0]).measurement_id)
    assert len(ids) == 4


# --- the fold is the claim, re-derived ------------------------------------------------------

def test_writer_refuses_the_micro_average_written_as_the_claim(tmp_path):
    run = make_run(tmp_path)
    micro = {**SUMMARY, "headline": SUMMARY["secondary_diagnostics"]["rubric_item_micro_average"]}
    with pytest.raises(capture.CaptureError, match="unweighted mean"):
        write_sidecar(run, summary=micro)
    binarised = {**SUMMARY, "headline": 515 / 1051}
    with pytest.raises(capture.CaptureError, match="unweighted mean"):
        write_sidecar(run, summary=binarised)
    assert not (run / capture.SIDECAR_NAME).exists(), "refusal must not half-write"


def test_reader_refuses_a_rehashed_row_whose_value_is_not_the_fold(tmp_path):
    sidecar = write_sidecar(make_run(tmp_path))
    _rewrite(sidecar, lambda rows: rows[0].update(value=0.4012), rehash=True)
    assert reader.native_rows(sidecar) == ()


def test_writer_refuses_a_headline_over_fewer_than_ten_columns(tmp_path):
    partial_abilities = {k: v for k, v in PER_ABILITY.items() if k != "abstention"}
    partial = {**SUMMARY, "per_ability": partial_abilities,
               "abilities_reported": sorted(partial_abilities), "n_questions": 360,
               "headline": sum(c["score"] for _, c in sorted(partial_abilities.items())) / 9}
    with pytest.raises(capture.CaptureError, match="ten"):
        write_sidecar(make_run(tmp_path), summary=partial)


def test_writer_refuses_a_run_without_the_second_fold(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="BOTH folds"):
        write_sidecar(run, summary={k: v for k, v in SUMMARY.items()
                                    if k != "secondary_diagnostics"})
    no_micro = {**SUMMARY, "secondary_diagnostics": {
        **SUMMARY["secondary_diagnostics"], "rubric_item_micro_average": None}}
    with pytest.raises(capture.CaptureError, match="rubric_item_micro_average"):
        write_sidecar(run, summary=no_micro)


def test_writer_refuses_inconsistent_binarised_counts(tmp_path):
    bad = {**SUMMARY, "secondary_diagnostics": {
        **SUMMARY["secondary_diagnostics"], "binarised_pass_count": 2000}}
    with pytest.raises(capture.CaptureError, match="cannot exceed"):
        write_sidecar(make_run(tmp_path), summary=bad)


@pytest.mark.parametrize("key", ["judge_model", "judge_prompt_version"])
def test_writer_refuses_a_run_without_judge_identity(tmp_path, key):
    with pytest.raises(capture.CaptureError, match=key):
        write_sidecar(make_run(tmp_path), summary={**SUMMARY, key: ""})


def test_writer_refuses_an_unrecorded_judge_question_flag(tmp_path):
    with pytest.raises(capture.CaptureError, match="question_in_judge_prompt"):
        write_sidecar(make_run(tmp_path), summary={**SUMMARY, "question_in_judge_prompt": None})


def test_writer_refuses_a_foreign_fold_name_or_version(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="fold"):
        write_sidecar(run, summary={**SUMMARY, "fold": "rubric_micro_binarised"})
    with pytest.raises(capture.CaptureError, match="scorer_version"):
        write_sidecar(run, summary={**SUMMARY, "scorer_version": 0})


# --- doctrine: pre-hook runs emit zero rows -------------------------------------------------

def test_pre_hook_run_emits_zero_rows(tmp_path):
    run = make_run(tmp_path)
    assert reader.rows_for_run(run) == ()


def test_missing_and_empty_sidecars_emit_zero_rows_without_error(tmp_path):
    run = make_run(tmp_path)
    assert reader.native_rows(run / capture.SIDECAR_NAME) == ()
    (run / capture.SIDECAR_NAME).write_text("")
    assert reader.native_rows(run / capture.SIDECAR_NAME) == ()


# --- strictness -----------------------------------------------------------------------------

def test_any_malformed_row_voids_the_whole_sidecar(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    _rewrite(sidecar, lambda rows: rows[0].update(schema="something.else/v1"))
    assert reader.native_rows(sidecar) == ()

    write_sidecar(run)
    _rewrite(sidecar, lambda rows: rows[0].update(category="OPTIMUM"))  # breaks the self-hash
    assert reader.native_rows(sidecar) == ()

    write_sidecar(run)
    with open(sidecar, "a") as handle:
        handle.write("{not json\n")
    assert reader.native_rows(sidecar) == ()

    write_sidecar(run)
    _rewrite(sidecar, lambda rows: rows.append(dict(rows[0])))
    assert reader.native_rows(sidecar) == ()


def test_reader_refuses_an_unknown_arm_even_if_rehashed(tmp_path):
    sidecar = write_sidecar(make_run(tmp_path))
    _rewrite(sidecar, lambda rows: rows[0]["extra"].update(arm="memory_on"), rehash=True)
    assert reader.native_rows(sidecar) == ()


def test_project_rejects_a_mutated_or_bare_native(tmp_path):
    native = reader.native_rows(write_sidecar(make_run(tmp_path)))[0]
    with pytest.raises(ct.ProjectionError):
        reader.project({**native, "row": {**native["row"], "value": 1.0}})
    with pytest.raises(ct.ProjectionError):
        reader.project({"sidecar_path": "x"})
    with pytest.raises(ct.ProjectionError):
        reader.project(native["row"])


def test_decayed_attestation_grades_down_not_away(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    (run / "beam_score.json").write_text("mutated after score-time\n")
    natives = reader.native_rows(sidecar)
    assert len(natives) == 1, "a decayed artifact must surface, not vanish"
    q, t, reasons = ct.grade(reader.project(natives[0]))
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("not on disk" in r for r in reasons)


# --- the writer refuses to guess ------------------------------------------------------------

def test_writer_refuses_an_unknown_arm(tmp_path):
    run = make_run(tmp_path)
    for arm in ("whatever", ""):
        with pytest.raises(capture.CaptureError, match="arm must be one of"):
            write_sidecar(run, arm=arm)
    assert not (run / capture.SIDECAR_NAME).exists()


def test_writer_refuses_when_the_scored_artifact_is_absent(tmp_path):
    run = make_run(tmp_path)
    (run / "beam_score.json").unlink()
    with pytest.raises(capture.CaptureError, match="scored artifact missing"):
        write_sidecar(run)


def test_writer_does_not_recompute_the_metric(tmp_path):
    row = json.loads(write_sidecar(make_run(tmp_path)).read_text())
    assert row["value"] == SUMMARY["headline"]
    assert row["extra"]["per_ability"] == PER_ABILITY


# --- carrier conformance --------------------------------------------------------------------

def test_projection_is_registered_under_the_shared_measurement_class():
    assert "beam-memory-measurement" in ct.registered()
    assert ct.source_classes()["beam-memory-measurement"] == ct.MEASUREMENT_CLASS


def test_adapter_registers_no_ladder_of_its_own():
    """An adapter projects; it never grades (§4.7)."""
    for module in (reader, capture):
        source = Path(module.__file__).read_text()
        assert "register_ladder" not in source
    assert "Witnessed" not in Path(reader.__file__).read_text().split('"""', 2)[2]


def test_abilities_mirror_the_research_fold():
    """The ten columns must match beam_scoring.BEAM_ABILITIES when the research repo is visible."""
    assert len(capture.BEAM_ABILITIES) == 10 == len(set(capture.BEAM_ABILITIES))
    import os
    for candidate in (os.environ.get("EPYC_RESEARCH"), "/mnt/raid0/llm/epyc-inference-research"):
        if not candidate:
            continue
        module = Path(candidate) / "scripts/benchmark/beam_scoring.py"
        if module.is_file():
            import importlib.util
            spec = importlib.util.spec_from_file_location("beam_scoring_mirror", module)
            loaded = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loaded)
            assert tuple(loaded.BEAM_ABILITIES) == capture.BEAM_ABILITIES
            assert loaded.FOLD_NAME == capture.FOLD_NAME
            return
    pytest.skip("epyc-inference-research beam_scoring.py not on this host")


def test_frames_go_through_the_shared_emitter(tmp_path):
    frames = reader.frames_for_sidecar(write_sidecar(make_run(tmp_path)),
                                       as_of="2026-09-15T13:00:00Z")
    assert len(frames) == 3  # 1 row x (source, claim, support)
    supports = [f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1")]
    assert len(supports) == 1
    assert supports[0]["assertion"]["grade"] == {"Q": "Witnessed", "T": "Attested"}


# --- M-12 B2: the arm is what the rows record ------------------------------------------------

def test_arm_vocabulary_is_the_m12b_arms():
    assert capture.ARMS == {"full", "rag", "trace"}


@pytest.mark.parametrize("by_row", [
    {"rag": 400}, {"full": 200, "trace": 200}, {"unrecorded": 400}, None, {"full": 0},
])
def test_writer_refuses_an_arm_the_rows_do_not_record(tmp_path, by_row):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="not what the result rows record"):
        write_sidecar(run, summary={**SUMMARY, "context_mode_by_row": by_row})
    assert not (run / capture.SIDECAR_NAME).exists()


def test_reader_refuses_a_row_whose_arm_and_row_record_disagree(tmp_path):
    sidecar = write_sidecar(make_run(tmp_path))
    _rewrite(sidecar, lambda rows: rows[0]["extra"].update(context_mode_by_row={"rag": 400}),
             rehash=True)
    assert reader.native_rows(sidecar) == ()
