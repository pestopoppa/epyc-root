"""VB-HSPROF1-WRITE: HS-PROF-1 profile-arm table carrier (writer + strict reader + projection).

Pinned here: an HS-PROF-1 OUT_DIR shaped like ``run_hs_prof1_beam_arm.sh`` leaves it projects to
per (ability, arm) mean claims plus per-ability paired-delta claims, graded by the ONE shared ladder;
judge identity is part of every claim (two judges on one arm are two claims); missing judge identity,
mock runs, an arm the harness did not record, a table that does not re-derive and a cross-judge pair
are refused; a tampered sidecar voids the whole file; a mutated attestation grades DOWN.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import hs_prof1_profile_arms as hp  # noqa: E402

WHEN = "2026-10-22T12:00:00Z"
ABILITIES = ("instruction_following", "preference_following")
# (pref_current, admission) per question: 3 per ability, with a win, a loss and a tie.
SCORES = {
    "instruction_following": [(0.5, 1.0), (1.0, 0.5), (1.0, 1.0)],
    "preference_following": [(0.0, 1.0), (0.5, 1.0), (0.5, 0.5)],
}
CLOUD = {"judge_backend": "cloud", "cloud_judge": "sonnet-5-5-low",
         "judge_model_id": "claude-sonnet-5-5", "judge_model": "sonnet-5-5-low:claude-sonnet-5-5",
         "judge_response_models": ["claude-sonnet-5-5"]}
INFERENCE = {"max_tokens": 2048, "temperature": 0.0, "enable_thinking": False,
             "endpoint": "chat_completions"}


def _qid(ability, i):
    return f"beam_100K_{i}_{ability}_0"


def _table(per_question):
    """Mirror of research ``hs_prof1_profile_arms.table`` (the producer's arithmetic)."""
    qa = {r["question_id"]: r for r in per_question["pref_current"]}
    qb = {r["question_id"]: r for r in per_question["admission"]}
    shared = sorted(set(qa) & set(qb))
    out = {"schema": "epyc.hs_prof1_table.v1", "arms": list(hp.ARMS),
           "delta": "admission minus pref_current", "n_shared_questions": len(shared),
           "only_in_one_arm": len(set(qa) ^ set(qb)), "per_ability": {}}
    for ability in sorted({qa[q]["ability"] for q in shared}):
        ids = [q for q in shared if qa[q]["ability"] == ability]
        d = [qb[q]["score"] - qa[q]["score"] for q in ids]
        out["per_ability"][ability] = {
            "n": len(ids), "pref_current": sum(qa[q]["score"] for q in ids) / len(ids),
            "admission": sum(qb[q]["score"] for q in ids) / len(ids), "mean_delta": sum(d) / len(d),
            "admission_wins": sum(1 for x in d if x > 0), "pref_wins": sum(1 for x in d if x < 0),
            "ties": sum(1 for x in d if x == 0)}
    out["judge_models"] = ["x"]
    return out


def make_out_dir(tmp, *, judge=None, usage_calls=12, mutate=None):
    """An HS-PROF-1 OUT_DIR as run_hs_prof1_beam_arm.sh leaves it after PHASE=judge."""
    out = Path(tmp)
    out.mkdir(parents=True, exist_ok=True)
    judge = dict(CLOUD if judge is None else judge)
    docs = {}
    for k, arm in enumerate(hp.ARMS):
        run_id = f"2026102{k}_0101{k}0"
        rows = {}
        per_q = []
        for ability in ABILITIES:
            for i, pair in enumerate(SCORES[ability]):
                q = _qid(ability, i)
                rows[q] = {"question_id": q, "response": "ok", "inference": dict(INFERENCE),
                           "finish_reason": "stop",
                           "provenance": {"suite": "beam", "split": "100K",
                                          "beam_source": "hf_parquet", "context_mode": "profile",
                                          "profile_arm": arm,
                                          "abilities": list(ABILITIES)}}
                per_q.append({"question_id": q, "ability": ability, "score": pair[k],
                              "basis": "nugget_mean", "n_nuggets": 2})
        result = {"model_role": "qwen36_35b_a3b_mtp_q8_local",
                  "model_path": "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf",
                  "config_name": "baseline", "run_id": run_id,
                  "timestamp": "2026-10-22T01:01:00", "results": {"beam": rows}}
        judged = {**judge, "schema": "epyc.beam_judged_run.v1", "run_id": run_id,
                  "model_role": result["model_role"], "config_name": "baseline", "split": "100K",
                  "judge_prompt_version": "beam-unified-b2da22ea+question/v1",
                  "question_in_judge_prompt": True, "result_questions": len(rows),
                  "context_mode_by_row": {"profile": len(rows)},
                  "records": [], "unjudged": []}
        if judge.get("judge_backend") == "cloud":
            judged["judge_usage_totals"] = {"input_tokens": 1000, "output_tokens": 50,
                                            "cache_read_input_tokens": 0,
                                            "cache_creation_input_tokens": 0,
                                            "total_cost_usd": 0.01, "calls": usage_calls}
        summary = {"scorer_version": 1, "run_id": run_id, "model_role": result["model_role"],
                   "split": "100K", "judge_prompt_version": judged["judge_prompt_version"],
                   "question_in_judge_prompt": True, "checked_against_dataset": True,
                   "context_mode_by_row": {"profile": len(rows)},
                   **{key: judged[key] for key in ("judge_backend", "cloud_judge", "judge_model",
                                                   "judge_model_id", "judge_response_models",
                                                   "judge_usage_totals") if key in judged}}
        docs[arm] = {"result": result, "judged": judged,
                     "scored": {"summary": summary, "per_question": per_q}}
    if mutate:
        mutate(docs)
    for arm, d in docs.items():
        rp = out / f"result_{arm}.json"
        rp.write_text(json.dumps(d["result"]))
        (out / f"arm_{arm}.result.path").write_text(f"{rp}\n")
        (out / f"judged_{arm}.json").write_text(json.dumps(d["judged"]))
        (out / f"scored_{arm}.json").write_text(json.dumps(d["scored"]))
        (out / f"snapshots_{arm}.json").write_text(json.dumps({"1": f"profile {arm}"}))
    table = out / "table.json"
    table.write_text(json.dumps(_table({a: docs[a]["scored"]["per_question"] for a in hp.ARMS})))
    return out, table


def write(tmp, **kw):
    pins = kw.pop("reader_pins", None)
    out, table = make_out_dir(tmp, **kw)
    return hp.write_belief_measurements(out, table_path=table, producer="hs_prof1_profile_arms.py",
                                        reader_pins=pins, emitted_at=WHEN)


def write_fixture(tmp):
    """Builder used by test_ingest_sources (one sidecar, six rows)."""
    return write(Path(tmp) / "hs-prof1")


# --- round trip ----------------------------------------------------------------------------------

def test_round_trip_grades_through_the_shared_ladder(tmp_path):
    side = write(tmp_path)
    natives = hp.native_rows(side)
    assert len(natives) == 6  # 2 abilities x (2 arm means + 1 paired delta)
    tups = [hp.project(n) for n in natives]
    assert len({t.measurement_id for t in tups}) == 6
    for t in tups:
        assert ct.grade(t)[:2] == ("Witnessed", "Attested")
    by = {(t.extra["kind"], t.extra["ability"], t.extra["arm"]): t for t in tups}
    pref = by[("arm_mean", "instruction_following", "pref_current")]
    assert pref.value == pytest.approx(2.5 / 3) and pref.reps == 3
    assert pref.category == "BASELINE" and pref.reps_basis == "scored:questions"
    adm = by[("arm_mean", "preference_following", "admission")]
    assert adm.category == "CANDIDATE" and adm.value == pytest.approx(2.5 / 3)
    delta = by[("paired_delta", "preference_following", hp.DELTA_ARM)]
    assert delta.value == pytest.approx(1.5 / 3)
    assert (delta.extra["admission_wins"], delta.extra["pref_wins"], delta.extra["ties"]) == (2, 0, 1)
    d_if = by[("paired_delta", "instruction_following", hp.DELTA_ARM)]
    assert (d_if.extra["admission_wins"], d_if.extra["pref_wins"], d_if.extra["ties"]) == (1, 1, 1)
    assert d_if.reps == 3 and d_if.reps_basis == "scored:paired_questions"
    # judge identity in the tuple and locator
    assert pref.extra["judge"]["cloud_judge"] == "sonnet-5-5-low"
    assert pref.extra["judge"]["judge_response_models"] == ["claude-sonnet-5-5"]
    assert pref.extra["judge_usage_totals_by_arm"]["admission"]["calls"] == 12
    assert "judge-cloud:sonnet-5-5-low:claude-sonnet-5-5" in pref.attestation_locator
    assert ct.registered()[hp.SOURCE_KIND] is hp.project
    assert len(hp.frames_for_sidecar(side, as_of=WHEN)) == 18


def test_reader_pins_absent_are_listed_never_invented(tmp_path):
    t = hp.project(hp.native_rows(write(tmp_path / "a"))[0])
    assert t.extra["reader_pins"] == {}
    assert t.extra["reader_pins_absent"] == sorted(hp.READER_PIN_FIELDS)
    assert t.extra["reader"]["admission"]["model_path"].endswith("Q8_0.gguf")
    assert t.extra["inputs"]["admission"]["snapshots_sha256"]
    t2 = hp.project(hp.native_rows(write(tmp_path / "b", reader_pins={
        "recipe_path": "artifacts/serving-recipes/eval/x.json", "recipe_sha256": "a" * 64}))[0])
    assert t2.extra["reader_pins_absent"] == ["argv", "model_sha256", "server_build"]


def test_served_judge_is_admissible_without_cloud_fields(tmp_path):
    side = write(tmp_path, judge={"judge_backend": "served",
                                  "judge_model": "gemma-4-26B-A4B-it-ORIG-Q8_0"})
    tups = [hp.project(n) for n in hp.native_rows(side)]
    assert len(tups) == 6
    assert tups[0].extra["judge"]["cloud_judge"] is None
    assert tups[0].extra["judge_usage_totals_by_arm"] is None


def test_absent_sidecar_is_zero_rows(tmp_path):
    make_out_dir(tmp_path)
    assert hp.rows_for_run(tmp_path) == ()


# --- judge identity ------------------------------------------------------------------------------

def test_judge_a_and_judge_b_give_distinct_claims(tmp_path):
    a = [hp.project(n) for n in hp.native_rows(write(tmp_path / "a"))]
    b = [hp.project(n) for n in hp.native_rows(write(tmp_path / "b", judge={
        **CLOUD, "cloud_judge": "opus-5-5-low", "judge_model_id": "claude-opus-5-5",
        "judge_model": "opus-5-5-low:claude-opus-5-5",
        "judge_response_models": ["claude-opus-5-5"]}))]
    assert not {t.measurement_id for t in a} & {t.measurement_id for t in b}
    assert not {t.attestation_locator for t in a} & {t.attestation_locator for t in b}
    # identity derivation alone (same run, same attested bytes) separates the judges
    parts = dict(kind="arm_mean", ability="preference_following", arm="admission",
                 run_ids={"pref_current": "r1", "admission": "r2"}, split="100K",
                 attested_sha256="c" * 64)
    ja = ns.content_hash(hp.judge_identity(CLOUD | {"judge_prompt_version": "v",
                                                    "question_in_judge_prompt": True}))
    jb = ns.content_hash(hp.judge_identity(CLOUD | {"judge_model_id": "claude-sonnet-5-6",
                                                    "judge_prompt_version": "v",
                                                    "question_in_judge_prompt": True}))
    assert hp.measurement_identity(**parts, judge_identity_sha256=ja) != \
        hp.measurement_identity(**parts, judge_identity_sha256=jb)


@pytest.mark.parametrize("drop", ["judge_backend", "judge_model", "cloud_judge", "judge_model_id",
                                  "judge_response_models"])
def test_missing_judge_identity_is_refused(tmp_path, drop):
    def mutate(docs):
        for d in docs.values():
            d["judged"].pop(drop, None)
            d["scored"]["summary"].pop(drop, None)
    with pytest.raises(hp.CaptureError, match="judge identity refused"):
        write(tmp_path, mutate=mutate)
    assert not (tmp_path / hp.SIDECAR_NAME).exists()


def test_pre_backend_payload_is_refused_not_backfilled_as_served(tmp_path):
    with pytest.raises(hp.CaptureError, match="judge_backend"):
        write(tmp_path, judge={"judge_model": "gemma-4-26B-A4B-it-ORIG-Q8_0"})


def test_cross_judge_pair_is_refused(tmp_path):
    def mutate(docs):
        for key in ("judged",):
            docs["admission"][key]["judge_model_id"] = "claude-sonnet-5-6"
        docs["admission"]["scored"]["summary"]["judge_model_id"] = "claude-sonnet-5-6"
    with pytest.raises(hp.CaptureError, match="different judge identities"):
        write(tmp_path, mutate=mutate)


def test_scored_summary_must_restate_the_judged_identity(tmp_path):
    def mutate(docs):
        docs["admission"]["scored"]["summary"]["cloud_judge"] = "sonnet-low"
    with pytest.raises(hp.CaptureError, match="differs from the judged"):
        write(tmp_path, mutate=mutate)


# --- mock / recorded-arm refusals ----------------------------------------------------------------

def test_mock_judge_is_refused(tmp_path):
    with pytest.raises(hp.CaptureError, match="mock"):
        write(tmp_path, judge={**CLOUD, "judge_model": "mock-judge"})


def test_cloud_judge_with_zero_calls_is_refused(tmp_path):
    with pytest.raises(hp.CaptureError, match="calls"):
        write(tmp_path, usage_calls=0)


def test_dry_run_reader_is_refused(tmp_path):
    def mutate(docs):
        docs["pref_current"]["result"]["dry_run"] = True
    with pytest.raises(hp.CaptureError, match="mock/dry_run"):
        write(tmp_path, mutate=mutate)


def test_mock_reader_run_is_refused(tmp_path):
    def mutate(docs):
        docs["pref_current"]["result"]["model_role"] = "mock_reader"
    with pytest.raises(hp.CaptureError, match="mock"):
        write(tmp_path, mutate=mutate)


def test_arm_not_recorded_by_the_harness_is_refused(tmp_path):
    def mutate(docs):
        row = next(iter(docs["admission"]["result"]["results"]["beam"].values()))
        row["provenance"]["profile_arm"] = "pref_current"
    with pytest.raises(hp.CaptureError, match="profile_arm=admission"):
        write(tmp_path, mutate=mutate)


def test_non_profile_context_mode_is_refused(tmp_path):
    def mutate(docs):
        docs["admission"]["scored"]["summary"]["context_mode_by_row"] = {"full": 6}
    with pytest.raises(hp.CaptureError, match="context_mode=profile"):
        write(tmp_path, mutate=mutate)


def test_unchecked_dataset_is_refused(tmp_path):
    def mutate(docs):
        docs["admission"]["scored"]["summary"]["checked_against_dataset"] = False
    with pytest.raises(hp.CaptureError, match="check-dataset"):
        write(tmp_path, mutate=mutate)


def test_table_that_does_not_rederive_is_refused(tmp_path):
    out, table = make_out_dir(tmp_path)
    t = json.loads(table.read_text())
    t["per_ability"]["preference_following"]["admission_wins"] = 3
    table.write_text(json.dumps(t))
    with pytest.raises(hp.CaptureError, match="does not re-derive"):
        hp.write_belief_measurements(out, table_path=table, producer="p", emitted_at=WHEN)


def test_paired_subset_is_stated_in_reps_basis(tmp_path):
    def mutate(docs):
        docs["admission"]["scored"]["per_question"] = [
            r for r in docs["admission"]["scored"]["per_question"]
            if r["question_id"] != _qid("preference_following", 2)]
    tups = [hp.project(n) for n in hp.native_rows(write(tmp_path, mutate=mutate))]
    pref = next(t for t in tups if t.extra["kind"] == "arm_mean"
                and t.extra["ability"] == "preference_following" and t.extra["arm"] == "pref_current")
    assert pref.reps == 2
    assert pref.reps_basis == "scored:questions (paired subset of 3 scored)"


# --- tamper --------------------------------------------------------------------------------------

def _rewrite(side, fn):
    rows = [json.loads(line) for line in side.read_text().splitlines()]
    fn(rows)
    side.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def test_tampered_row_hash_voids_the_whole_file(tmp_path):
    side = write(tmp_path)
    _rewrite(side, lambda rows: rows[0].__setitem__("row_sha256", "0" * 64))
    assert hp.native_rows(side) == ()


def test_tampered_value_resealed_still_fails_rederivation(tmp_path):
    side = write(tmp_path)

    def bump(rows):
        rows[0]["value"] = 0.99
        ns.seal(rows[0])
    _rewrite(side, bump)
    assert hp.native_rows(side) == ()


def test_tampered_judge_resealed_breaks_identity(tmp_path):
    side = write(tmp_path)

    def swap(rows):
        rows[0]["extra"]["judge"]["judge_model_id"] = "claude-opus-5-5"
        ns.seal(rows[0])
    _rewrite(side, swap)
    assert hp.native_rows(side) == ()


def test_mutated_attestation_grades_down_not_away(tmp_path):
    side = write(tmp_path)
    (tmp_path / "table.json").write_text("{}")
    tups = [hp.project(n) for n in hp.native_rows(side)]
    assert len(tups) == 6
    deltas = [t for t in tups if t.extra["kind"] == "paired_delta"]
    for t in deltas:
        assert t.attestation_present is False
        assert ct.grade(t)[:2] != ("Witnessed", "Attested")
    arms = [t for t in tups if t.extra["kind"] == "arm_mean"]
    assert all(ct.grade(t)[:2] == ("Witnessed", "Attested") for t in arms)


def test_project_refuses_a_bypassed_invalid_row(tmp_path):
    side = write(tmp_path)
    native = copy.deepcopy(hp.native_rows(side)[0])
    native["row"]["extra"]["judge"]["judge_backend"] = "mock"
    with pytest.raises(ct.ProjectionError):
        hp.project(native)
