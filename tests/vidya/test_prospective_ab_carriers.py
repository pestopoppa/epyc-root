"""VB-TOC-AB-WRITE, VB-SKILLBANK-AB-WRITE, VB-HIL-WRITE-FIELDS, VB-AK-HISTORY.

Four self-hashed prospective carriers on one plumbing module. Pinned here: the round trip is graded
by the one shared ladder (``claim_tuple.grade()``); a missing sidecar emits zero rows (no
retrospective tuple); a tampered or re-derivation-breaking sidecar voids the whole file; a moved or
mutated attestation grades DOWN rather than vanishing; and each carrier's own refusals.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import ak_history, harness_improvement, skillbank_ab, toc_ab  # noqa: E402

WHEN = "2026-10-21T10:00:00Z"
D = "d" * 64


def toc_write(tmp_path, **kw):
    traj = tmp_path / "trajectory.jsonl"
    traj.write_text('{"e":1}\n')
    def tasks(solved):
        return [{"task_id": f"t{i}", "terminal_state": "finished" if s else "turn-exhausted",
                 "solved": bool(s), "turns": 5 + i, "rolling_input_tokens": 1000 * (i + 1),
                 "prefix_cache_invalidations": i, "compressor_wall_s": 0.5 * i}
                for i, s in enumerate(solved)]
    arms = {
        "control": {"policy_digest": D, "trigger_fraction": None, "window_denominator": "n_ctx",
                    "summary_placement": "none", "is_control": True, "tasks": tasks([1, 0, 1, 1])},
        "elide-0.5": {"policy_digest": "e" * 64, "trigger_fraction": 0.5,
                      "window_denominator": "n_ctx", "summary_placement": "tail",
                      "is_control": False, "tasks": tasks([1, 1, 0, 1])},
    }
    arms.update(kw)
    toc_write.traj = traj
    return toc_ab.write_belief_measurements(tmp_path, run_id="r1", producer="traj-writer",
                                            trajectory_path=traj, arms=arms, emitted_at=WHEN)


def sk_cell(role="worker", pin="gemma4-26B", on=(30, 40, 42), off=(25, 40, 41)):
    mk = lambda t: {"correct": t[0], "scored": t[1], "attempted": t[2]}
    return {"role": role, "model_pin": pin, "skill_on": mk(on), "skill_off": mk(off),
            "bootstrap_ci95": [-0.05, 0.2], "bootstrap_resamples": 1000,
            "min_detectable_difference": 0.1, "detector_digest": D,
            "adoption": {"injected": 20, "applied": 7}}


def sk_write(tmp_path, cells=None):
    log = tmp_path / "requests.jsonl"
    log.write_text('{"skill_ids":[1]}\n')
    return skillbank_ab.write_belief_measurements(
        tmp_path, run_id="m23", producer="m23-runner", request_log_path=log,
        cells=cells or [sk_cell(), sk_cell("coder", "q-coder", on=(10, 40, 40), off=(20, 40, 40))],
        emitted_at=WHEN)


PINS = {"tool_surface_sha256": "a" * 64, "served_context_window": 65536,
        "compaction_policy_sha256": "b" * 64, "wall_time_budget_s": 1800.0, "turn_budget": 40,
        "final_result_selection_rule": "last assistant message"}


def hil_obs(arm="CANDIDATE", pins=None, **kw):
    o = {"feature_id": "HS-14", "arm": arm, "objective": "pass_at_1", "metric": "pass_at_1",
         "value": 0.5, "unit": "fraction", "metric_direction": "higher_better",
         "native_verdict": "pass", "suite_id": "shell-bench", "suite_version": "v1",
         "split": "heldout", "scored": 18, "attempted": 20, "prompt_param_path": "p/prompt.md",
         "prompt_param_sha256": "c" * 64, "harness_pin": "opencode@abc", "config_sha256": "f" * 64,
         "arm_pins": dict(PINS if pins is None else pins), "identities": {"model": "gemma4"}}
    o.update(kw)
    return o


def hil_write(tmp_path, obs=None):
    raw = tmp_path / "raw.jsonl"
    raw.write_text("x\n")
    return harness_improvement.write_belief_measurements(
        tmp_path, run_id="hil1", producer="hil-runner", results_path=raw,
        observations=obs or [hil_obs("BASELINE", value=0.4), hil_obs()], emitted_at=WHEN)


def ak_trial(i=1, **kw):
    t = {"trial_id": f"trial-{i}", "trial_ordinal": i, "cumulative_tokens": 1000 * i,
         "trial_tokens": 900, "failure_class": None,
         "stage_seconds": {"planner": 3.0, "critic": None, "author": 20.5, "gate": 40.0,
                           "measure": 12.5},
         "mechanism_family_bucket": "tiling", "knob_descriptor": {"kind": "env", "v": 4}}
    t.update(kw)
    return t


def ak_write(tmp_path, trials=None):
    return ak_history.write_belief_measurements(
        tmp_path, campaign_id="c1", store_id="s1", epoch="e1", producer="loop",
        trials=trials or [ak_trial(1), ak_trial(2)], emitted_at=WHEN)


CARRIERS = {"toc": (toc_ab, toc_write, 2), "skillbank": (skillbank_ab, sk_write, 2),
            "hil": (harness_improvement, hil_write, 2), "ak": (ak_history, ak_write, 2)}


@pytest.fixture(params=sorted(CARRIERS))
def carrier(request):
    return CARRIERS[request.param]


def test_round_trip_is_graded_by_the_shared_ladder(carrier, tmp_path):
    mod, write, n = carrier
    natives = mod.native_rows(write(tmp_path))
    assert len(natives) == n
    for nat in natives:
        tup = mod.project(nat)
        q, t, reasons = ct.grade(tup)
        # OBSERVATION (empty protocol_id): never Witnessed/Attested without a ratified protocol.
        assert tup.protocol_id == ""
        assert (q, t) == ("Judged", "Located") and reasons
        assert tup.attestation_present is True and tup.attestation_verified is True
    ids = {mod.project(x).measurement_id for x in natives}
    assert len(ids) == n
    assert ids == {mod.project(x).measurement_id for x in mod.native_rows(write(tmp_path))}


def test_no_sidecar_means_zero_rows(carrier, tmp_path):
    mod, _, _ = carrier
    assert mod.rows_for_run(tmp_path) == ()
    assert mod.native_rows(tmp_path / "nope.jsonl") == ()


def test_tampered_row_voids_the_whole_file(carrier, tmp_path):
    mod, write, _ = carrier
    sc = write(tmp_path)
    lines = sc.read_text().splitlines()
    row = json.loads(lines[0])
    row["claim"] = row["claim"] + " (edited)"
    lines[0] = json.dumps(row, sort_keys=True)
    sc.write_text("\n".join(lines) + "\n")
    assert mod.native_rows(sc) == ()


def test_garbage_line_voids_the_whole_file(carrier, tmp_path):
    mod, write, _ = carrier
    sc = write(tmp_path)
    sc.write_text(sc.read_text() + "not json\n")
    assert mod.native_rows(sc) == ()


def test_mutated_attestation_grades_down_not_away(carrier, tmp_path):
    mod, write, n = carrier
    sc = write(tmp_path)
    path = Path(json.loads(sc.read_text().splitlines()[0])["results_path"])
    good = {ct.grade(mod.project(x))[:2] for x in mod.native_rows(sc)}
    path.write_text(path.read_text() + "tamper")
    natives = mod.native_rows(sc)
    assert len(natives) == n
    bad = mod.project(natives[0])
    assert bad.attestation_present is False
    assert ct.grade(bad)[:2] not in {("Witnessed", "Attested")}
    assert good


def test_projection_refuses_a_foreign_row(carrier):
    mod, _, _ = carrier
    with pytest.raises(ct.ProjectionError):
        mod.project({"row": {"schema": "other"}})


def test_frames_emit_through_the_shared_carrier(carrier, tmp_path):
    mod, write, n = carrier
    frames = mod.frames_for_sidecar(write(tmp_path), as_of="2026-10-21T11:00:00Z")
    assert len(frames) >= n


# --- TOC --------------------------------------------------------------------------------------

def test_toc_rederives_totals_and_rate(tmp_path):
    rows = {n["row"]["extra"]["arm_label"]: n["row"] for n in toc_ab.native_rows(toc_write(tmp_path))}
    c = rows["control"]
    assert c["value"] == 0.75 and c["category"] == "BASELINE"
    assert c["extra"]["total_rolling_input_tokens"] == 10000
    assert c["extra"]["total_prefix_cache_invalidations"] == 6
    assert c["extra"]["total_compressor_wall_s"] == 3.0
    assert rows["elide-0.5"]["extra"]["trigger_fraction"] == 0.5


def test_toc_refuses_bad_terminal_state_and_unnamed_denominator(tmp_path):
    arm = {"policy_digest": D, "trigger_fraction": 0.25, "window_denominator": "n_ctx",
           "summary_placement": "top", "is_control": False,
           "tasks": [{"task_id": "a", "terminal_state": "oom", "solved": True, "turns": 1,
                      "rolling_input_tokens": 1, "prefix_cache_invalidations": 0,
                      "compressor_wall_s": 0.0}]}
    with pytest.raises(ns.CaptureError, match="terminal_state"):
        toc_write(tmp_path, bad=arm)
    ok = dict(arm, window_denominator="", tasks=[dict(arm["tasks"][0], terminal_state="killed")])
    with pytest.raises(ns.CaptureError, match="denominator"):
        toc_write(tmp_path, bad=ok)
    assert not (tmp_path / toc_ab.SIDECAR_NAME).exists()


def test_toc_refuses_hand_edited_totals(tmp_path):
    sc = toc_write(tmp_path)
    rows = [json.loads(x) for x in sc.read_text().splitlines()]
    rows[0]["extra"]["total_turns"] += 1
    rows[0]["row_sha256"] = ns.row_digest(rows[0])
    assert any("total_turns" in p for p in toc_ab.validate_row(rows[0]))


# --- SkillBank ---------------------------------------------------------------------------------

def test_skillbank_negative_cell_stays_a_row_and_no_pool(tmp_path):
    rows = {n["row"]["extra"]["role"]: n["row"] for n in skillbank_ab.native_rows(sk_write(tmp_path))}
    assert rows["coder"]["value"] < 0 and rows["coder"]["extra"]["negative_cell"] is True
    assert rows["worker"]["extra"]["negative_cell"] is False
    assert set(rows) == {"worker", "coder"}  # no pooled row


def test_skillbank_deltas_rederive_pp_and_itt(tmp_path):
    w = [n for n in skillbank_ab.native_rows(sk_write(tmp_path))
         if n["row"]["extra"]["role"] == "worker"][0]["row"]
    assert w["value"] == pytest.approx(30 / 40 - 25 / 40)
    assert w["extra"]["itt_delta"] == pytest.approx(30 / 42 - 25 / 41)
    assert w["reps"] == 40 and "attempted on/off=42/41" in w["reps_basis"]


@pytest.mark.parametrize("bad", ["pooled", "ALL"])
def test_skillbank_refuses_pooled_cell(tmp_path, bad):
    with pytest.raises(ns.CaptureError, match="pooled"):
        sk_write(tmp_path, [sk_cell(role=bad)])


def test_skillbank_refuses_impossible_counts_and_duplicates(tmp_path):
    with pytest.raises(ns.CaptureError, match="correct <= scored <= attempted"):
        sk_write(tmp_path, [sk_cell(on=(5, 4, 9))])
    with pytest.raises(ns.CaptureError, match="duplicate"):
        sk_write(tmp_path, [sk_cell(), sk_cell()])


def test_skillbank_requires_declared_mdd_and_detector(tmp_path):
    c = sk_cell()
    c["min_detectable_difference"] = None
    with pytest.raises(ns.CaptureError, match="min_detectable_difference"):
        sk_write(tmp_path, [c])


# --- HIL ---------------------------------------------------------------------------------------

def test_hil_item14_pins_are_required_and_carried(tmp_path):
    nat = harness_improvement.native_rows(hil_write(tmp_path))
    pins = nat[0]["row"]["extra"]["arm_pins"]
    assert set(pins) == set(harness_improvement.ARM_PIN_FIELDS)
    tup = harness_improvement.project(nat[1])
    assert tup.protocol_id == ""  # OBSERVATION: a non-empty id would be read as a protocol
    assert harness_improvement.NO_PROTOCOL == ""
    assert tup.reps == 18 and "attempted 20" in tup.reps_basis


@pytest.mark.parametrize("drop", list(harness_improvement.ARM_PIN_FIELDS))
def test_hil_refuses_any_missing_pin(tmp_path, drop):
    pins = {k: v for k, v in PINS.items() if k != drop}
    with pytest.raises(ns.CaptureError, match=drop):
        hil_write(tmp_path, [hil_obs(pins=pins)])


def test_hil_refuses_unknown_pin_and_nonmatching_category(tmp_path):
    with pytest.raises(ns.CaptureError, match="unknown fields"):
        hil_write(tmp_path, [hil_obs(pins=dict(PINS, extra_knob=1))])
    assert harness_improvement.arm_pin_problems(dict(PINS)) == []


def test_hil_duplicate_cell_refused(tmp_path):
    with pytest.raises(ns.CaptureError, match="duplicate"):
        hil_write(tmp_path, [hil_obs(), hil_obs()])


# --- AK history ---------------------------------------------------------------------------------

def test_ak_value_is_sum_of_recorded_stages_and_nulls_stay_null(tmp_path):
    nat = ak_history.native_rows(ak_write(tmp_path))[0]
    assert nat["row"]["value"] == 76.0
    f = nat["row"]["extra"]["fields"]
    assert f["stage_seconds"]["critic"] is None and f["failure_class"] is None
    tup = ak_history.project(nat)
    assert tup.metric_direction == "lower_better" and tup.reps == 1


def test_ak_refuses_untimed_trial_unknown_field_and_missing_budget_axis(tmp_path):
    none = {k: None for k in ak_history.STAGES}
    with pytest.raises(ns.CaptureError, match="no timed stage"):
        ak_write(tmp_path, [ak_trial(stage_seconds=none)])
    with pytest.raises(ns.CaptureError, match="closed carrier"):
        ak_write(tmp_path, [dict(ak_trial(), attempt_id="x")])
    # Hosted actors report no token counts: the budget axis stays unknown,
    # while the timed stage remains a valid prospective measurement.
    path = ak_write(tmp_path, [ak_trial(cumulative_tokens=None)])
    assert ak_history.native_rows(path)[0]["row"]["extra"]["fields"]["cumulative_tokens"] is None
    with pytest.raises(ns.CaptureError, match="trial_ordinal is required"):
        ak_write(tmp_path, [ak_trial(trial_ordinal=None)])


def test_ak_duplicate_trial_id_refused(tmp_path):
    with pytest.raises(ns.CaptureError, match="duplicate"):
        ak_write(tmp_path, [ak_trial(1), ak_trial(1)])


@pytest.mark.parametrize("legacy", ["observation:none", "epyc.vidya.same_as_schema"])
def test_legacy_pseudo_protocol_rows_still_project_as_observation(tmp_path, legacy):
    """Rows already on disk with a pseudo-protocol id (literal or the capture schema) re-project empty."""
    natives = harness_improvement.native_rows(hil_write(tmp_path))
    nat = dict(natives[0]); row = dict(nat["row"])
    row["protocol_id"] = legacy if legacy == "observation:none" else row["schema"]
    row.pop("row_sha256", None); ns.seal(row)
    nat["row"] = row
    assert harness_improvement.project(nat).protocol_id == ""
