"""VB-CF3C-POLICY-WIRE (first slice): the strict ``epyc.cf3c.native.v1`` reader, its refusal
controls and the recipient planning-context canary.

The valid fixture is built from a COPY of real cells of the real cf3c-live window (6 of its 18
cells: 3 cases x arms A0 and A1-k4), re-sealed in a test tmp dir. It is skipped when the real
window is absent. The canary runs on a SCRATCH ledger only.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
import loop_beliefs as lb  # noqa: E402
from adapters import toc_ab_cf3c as cf  # noqa: E402
from ledger import Ledger  # noqa: E402

REAL = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c/native")
pytestmark = pytest.mark.skipif(not (REAL / "RESULT.json").is_file(),
                                reason="real cf3c-live window not on this host")
KEEP_ARMS = ("A0", "A1-k4")
AS_OF = "2026-11-19T12:00:00+00:00"
MODEL = "Qwen3.6-35B-A3B-MTP-Q8_0.gguf"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _seal(root: Path, window: Path, result: dict) -> Path:
    result["window_sha256"] = {p.relative_to(window).as_posix(): _sha(p)
                               for p in sorted(window.rglob("*")) if p.is_file()}
    out = root / "RESULT.json"
    out.write_text(json.dumps(result, indent=1, sort_keys=True))
    return out


def _fixture(tmp: Path) -> tuple[Path, Path]:
    real = json.loads((REAL / "RESULT.json").read_text())
    real_window = REAL / Path(real["window"]).name
    wjson = json.loads((real_window / "WINDOW.json").read_text())
    sched = [e for e in wjson["schedule"] if e["arm"] in KEEP_ARMS]
    root = tmp / "native"
    window = root / real_window.name
    window.mkdir(parents=True)
    for p in real_window.iterdir():
        if p.is_file():
            shutil.copy2(p, window / p.name)
    for e in sched:
        shutil.copytree(real_window / f"cell-{e['ordinal']:02d}", window / f"cell-{e['ordinal']:02d}")
    wjson["schedule"] = sched
    (window / "WINDOW.json").write_text(json.dumps(wjson, indent=2, sort_keys=True))
    paired = {}
    for case, v in real["paired"].items():
        arms = {a: c for a, c in v["arms"].items() if a in KEEP_ARMS}
        paired[case] = {**v, "arms": arms}
    result = {**real, "arms": {a: real["arms"][a] for a in KEEP_ARMS}, "paired": paired,
              "scheduled": len(sched), "completed": len(sched), "recorded": len(sched)}
    return _seal(root, window, result), window


@pytest.fixture()
def fx(tmp_path):
    return _fixture(tmp_path)


def _reseal(path: Path, window: Path) -> None:
    result = json.loads(path.read_text())
    _seal(path.parent, window, result)


def test_valid_fixture_derives_the_numbers_in_the_result(fx):
    path, _ = fx
    unit = cf.read_unit(path)
    real = json.loads((REAL / "RESULT.json").read_text())["arms"]
    for arm in KEEP_ARMS:
        d = unit["derived"][arm]
        for key in ("scheduled", "correct", "graded", "abstained", "attempted", "tokens_cases"):
            assert d[key] == real[arm][key]
        for key in ("accuracy_over_attempted", "accuracy_among_graded", "mean_total_tokens", "mean_wall_s"):
            assert d[key] == pytest.approx(real[arm][key], rel=1e-9)
    # A1-k4 abstained twice: its accuracy over scheduled must show 1/3, not the 1/1 among graded.
    assert unit["derived"]["A1-k4"]["accuracy_over_scheduled"] == pytest.approx(1 / 3)
    assert unit["scope"] == {"model_file": MODEL, "quant": "Q8_0", "backend": "cpu",
                             "model_sha256": unit["scope"]["model_sha256"]}


def test_real_window_all_six_arms_match_the_summary_and_seal():
    unit = cf.read_unit(REAL / "RESULT.json")
    real = json.loads((REAL / "RESULT.json").read_text())
    assert len(unit["cells"]) == 18 and len(real["window_sha256"]) == 223
    assert set(unit["derived"]) == set(real["arms"]) and len(unit["derived"]) == 6
    assert all(d["scheduled"] == 3 for d in unit["derived"].values())
    assert len(cf.native_rows(REAL / "RESULT.json")) == 18  # 6 arms x 3 metrics


def test_projection_is_an_observation_that_carries_n_equals_3(fx):
    path, _ = fx
    tuples = [cf.project(n) for n in cf.native_rows(path)]
    assert len(tuples) == 6
    for t in tuples:
        q, tier, reasons = ct.grade(t)
        assert (q, tier) == ("Judged", "Located")  # no protocol => OBSERVATION, never Witnessed
        assert t.reps == 3 and "n=3" in t.claim and "no adoption claim" in t.claim
        assert t.applicability["model_file"] == MODEL and t.applicability["backend"] == "cpu"
        assert "context_tokens" not in t.applicability and "stack_regime" not in t.applicability
        assert t.protocol_id == "" and t.category == "CANDIDATE"
    acc = {t.extra["arm"]: t for t in tuples if t.metric == cf.M_ACC}
    assert acc["A0"].value == 1.0 and acc["A1-k4"].value == pytest.approx(1 / 3)
    assert "abstained 2" in acc["A1-k4"].claim
    assert {t.metric_direction for t in tuples if t.metric != cf.M_ACC} == {"lower_better"}


def test_hash_mismatch_refuses_the_whole_unit(fx):
    path, window = fx
    victim = next(window.glob("cell-*/completion.response.body"))
    victim.write_bytes(victim.read_bytes() + b"x")
    with pytest.raises(ct.ProjectionError, match="hash mismatch"):
        cf.native_rows(path)


def test_missing_sealed_file_refuses(fx):
    path, window = fx
    next(window.glob("cell-*/tokenize.response.body")).unlink()
    with pytest.raises(ct.ProjectionError, match="sealed file missing"):
        cf.native_rows(path)


def test_unsealed_extra_file_refuses(fx):
    path, window = fx
    (window / "stray.txt").write_text("not sealed")
    with pytest.raises(ct.ProjectionError, match="does not seal"):
        cf.native_rows(path)


def test_summary_that_does_not_rederive_refuses(fx):
    path, _ = fx
    result = json.loads(path.read_text())
    result["arms"]["A1-k4"]["accuracy_over_attempted"] = 1.0
    path.write_text(json.dumps(result))
    with pytest.raises(ct.ProjectionError, match="does not re-derive"):
        cf.native_rows(path)


def test_tampered_trajectory_resealed_still_refuses(fx):
    """Re-sealing hides the hash mismatch; the trajectory must still agree with RESULT.paired."""
    path, window = fx
    traj = next(window.glob("cell-*/TRAJECTORY.json"))
    cell = json.loads(traj.read_text())
    cell["wall_s"] += 1.0
    traj.write_text(json.dumps(cell, indent=2, sort_keys=True))
    _reseal(path, window)
    with pytest.raises(ct.ProjectionError, match="paired disagrees|not sealed under the same digest"):
        cf.native_rows(path)


def test_false_coverage_counts_and_live_server_refuse(fx):
    path, _ = fx
    base = json.loads(path.read_text())
    for patch, why in (({"coverage_complete": False}, "counts/coverage"),
                       ({"recorded": 0}, "counts/coverage"),
                       ({"server_exited": False}, "server still running")):
        path.write_text(json.dumps({**base, **patch}))
        with pytest.raises(ct.ProjectionError, match=why):
            cf.native_rows(path)


def test_foreign_result_json_declines_and_projection_revalidates(fx, tmp_path):
    other = tmp_path / "RESULT.json"
    other.write_text(json.dumps({"schema": "something.else"}))
    assert cf.native_rows(other) == ()
    path, window = fx
    natives = cf.native_rows(path)
    next(window.glob("cell-*/original-messages.json")).write_text("{}")
    with pytest.raises(ct.ProjectionError):  # a forged/stale native cannot project over drifted bytes
        cf.project(natives[0])


def _ingest(tmp_path, path):
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "toc-ab-cf3c", "--path", str(path),
                   "--as-of", "2026-11-19T00:00:00Z"])
    return rc, ledger


class _Sync:
    def status(self, ledger, index):
        return {"fresh": True, "lag_entries": 0, "index_max_id": 1, "synced_max_id": 1,
                "last_sync": "2026-11-19T11:00:00Z"}

    def sync(self, ledger, index):
        return {"action": "noop"}


def _prepare(tmp_path, ledger, target):
    cfg = tmp_path / "alarm.yaml"
    cfg.write_text(f"backend: file\nfile:\n  path: {tmp_path / 'alarms.jsonl'}\n")
    ans = lb.prepare("test.loop", target, ledger=ledger, index_path=tmp_path / "index.yaml",
                     as_of=AS_OF, sync_module=_Sync(), known_good=tmp_path / "kg.json",
                     alarm_state=tmp_path / "st.json", alarm_config=cfg)
    assert ans["status"] == "ready", ans.get("detail")
    return ans["evidence"]


def test_cli_ingest_and_refusal(fx, tmp_path, capsys):
    path, window = fx
    rc, ledger = _ingest(tmp_path, path)
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report["refused"] == [] and report["rows_projected"] == 6
    assert len(list(Ledger(ledger).read_all())) == 18  # 6 tuples x (source, claim, support)
    next(window.glob("cell-*/policy.json")).write_text("{}")
    (tmp_path / "second").mkdir()
    rc, ledger2 = _ingest(tmp_path / "second", path)
    report = json.loads(capsys.readouterr().out)
    assert len(report["refused"]) == 1 and report["frames_emitted"] == 0
    assert not ledger2.exists() or not list(Ledger(ledger2).read_all())


def test_planning_context_canary_on_scratch_ledger(fx, tmp_path, capsys):
    """The recipient sees the cf3c claims at their regime, with the small n and OBSERVATION grade."""
    path, _ = fx
    _, ledger = _ingest(tmp_path, path)
    capsys.readouterr()
    ev = _prepare(tmp_path, ledger, {"model_file": MODEL, "quant": "Q8_0", "backend": "cpu"})
    assert ev["tiers"]["target"] >= 1 and ev["nonempty_target"] is True
    blob = json.dumps(ev)
    assert "cf3c deterministic-policy pilot" in blob and "n=3" in blob and "no adoption claim" in blob
    # A different model must not see it.
    other = _prepare(tmp_path, ledger, {"model_file": "Other-7B-Q4_K_M.gguf", "quant": "Q4_K_M",
                                        "backend": "cpu"})
    assert other["tiers"]["target"] == 0
    print("CANARY", json.dumps({"tiers": ev["tiers"], "nonempty_target": ev["nonempty_target"],
                                "claims": [c.get("claim_id") for c in ev["claims"]][:3]}))


def _partial(fx):
    """A producer-shaped failure: one UNKNOWN record, one unattempted cell, scheduled unchanged."""
    path, window = fx
    result = json.loads(path.read_text())
    schedule = json.loads((window / "WINDOW.json").read_text())["schedule"]
    unknown, absent = [e for e in schedule if e["arm"] == "A1-k4"][:2]
    folder = window / f"cell-{unknown['ordinal']:02d}"
    cell = json.loads((folder / "TRAJECTORY.json").read_text())
    for name in list(cell["evidence_sha256"]):
        if name.startswith("completion."):
            del cell["evidence_sha256"][name]
            (folder / name).unlink()
    cell.update(status="UNKNOWN", correct=None, error="native request failed", non_termination=None)
    cell.pop("usage", None)
    (folder / "TRAJECTORY.json").write_text(json.dumps(cell))
    result["paired"][cell["case"]]["arms"][cell["arm"]] = cell
    shutil.rmtree(window / f"cell-{absent['ordinal']:02d}")
    result["paired"][absent["case"]]["arms"][absent["arm"]] = {"status": "unattempted", "correct": None}
    # Reproduce native summary semantics independently, including all recorded attempts.
    for arm in KEEP_ARMS:
        entries = [v["arms"][arm] for v in result["paired"].values()
                   if v["arms"][arm]["status"] != "unattempted"]
        summary = result["arms"][arm]
        graded = [e for e in entries if e["status"] == "graded"]
        correct = sum(e["correct"] is True for e in graded)
        tokens = [e["usage"]["total_tokens"] for e in entries if "usage" in e]
        summary.update(attempted=len(entries), graded=len(graded), correct=correct,
                       abstained=sum(e["status"] == "abstained" for e in entries),
                       UNKNOWN=sum(e["status"] == "UNKNOWN" for e in entries),
                       NA=sum(e["status"] == "NA" for e in entries),
                       non_termination=sum(e["non_termination"] == 1 for e in entries),
                       tokens_cases=len(tokens), mean_total_tokens=sum(tokens)/len(tokens) if tokens else None,
                       mean_wall_s=sum(e["wall_s"] for e in entries)/len(entries),
                       accuracy_among_graded=correct/len(graded) if graded else None,
                       accuracy_over_attempted=correct/len(entries))
    result.update(recorded=5, completed=4, coverage_complete=False, error="native request failed")
    partial = path.with_name("PARTIAL.json")
    _seal(path.parent, window, result).rename(partial)
    return partial, window


def test_partial_unknown_preserves_denominators_and_missing_pairs(fx):
    path, _ = _partial(fx)
    unit = cf.read_unit(path)
    d = unit["derived"]["A1-k4"]
    assert (d["scheduled"], d["attempted"], d["UNKNOWN"], d["unattempted"]) == (3, 2, 1, 1)
    assert (d["tokens_cases"], d["wall_cases"]) == (1, 2)
    assert d["accuracy_over_scheduled"] == d["correct"] / 3
    pairs = unit["paired_deltas"]["A1-k4"]
    assert len(pairs) == 3
    for pair in pairs[:2]:
        assert pair["correct"] is None and pair["total_tokens"] is None
    tuples = [cf.project(n) for n in cf.native_rows(path)]
    assert len(tuples) == 6
    acc = next(t for t in tuples if t.metric == cf.M_ACC and t.extra["arm"] == "A1-k4")
    assert acc.reps == 3 and "UNKNOWN 1" in acc.claim and "unattempted 1" in acc.claim
    assert acc.extra["window_error"] == "native request failed"
    assert ct.grade(acc)[:2] == ("Judged", "Located")


def test_partial_cli_discovery_and_planning_canary(fx, tmp_path, capsys):
    path, _ = _partial(fx)
    rc, ledger = _ingest(tmp_path, path.parent)
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report["rows_projected"] == 6 and report["refused"] == []
    ev = _prepare(tmp_path, ledger, {"model_file": MODEL, "quant": "Q8_0", "backend": "cpu"})
    assert ev["nonempty_target"] is True
    assert "UNKNOWN 1" in json.dumps(ev) and "unattempted 1" in json.dumps(ev)


def test_activation_receipts_and_paired_differences_are_carried(fx):
    path, _ = fx
    unit = cf.read_unit(path)
    for cell in unit["cells"]:
        receipt = unit["activation_witnesses"][cell["unit"]]
        assert receipt["policy"]["arm"] == cell["arm"]
        assert "original-messages.json" in receipt["evidence_sha256"]
    for pair in unit["paired_deltas"]["A1-k4"]:
        arms = unit["result"]["paired"][pair["case"]]["arms"]
        assert pair["total_tokens"] == arms["A1-k4"]["usage"]["total_tokens"] - arms["A0"]["usage"]["total_tokens"]
        assert pair["wall_s"] == arms["A1-k4"]["wall_s"] - arms["A0"]["wall_s"]
    assert any(w["policy"]["changed_observations"] for w in unit["activation_witnesses"].values())


@pytest.mark.parametrize("tamper", ["activation", "duplicate", "seed", "missing", "unsupported"])
def test_resealed_native_custody_refusals(fx, tamper):
    path, window = fx
    result = json.loads(path.read_text())
    wpath = window / "WINDOW.json"
    w = json.loads(wpath.read_text())
    if tamper == "duplicate":
        w["schedule"][1] = w["schedule"][0]
        wpath.write_text(json.dumps(w))
    elif tamper == "seed":
        result["paired"][w["schedule"][0]["case"]]["seed"] += 1
    elif tamper == "missing":
        shutil.rmtree(window / f"cell-{w['schedule'][0]['ordinal']:02d}")
    else:
        entry = w["schedule"][0]
        folder = window / f"cell-{entry['ordinal']:02d}"
        traj = json.loads((folder / "TRAJECTORY.json").read_text())
        if tamper == "activation":
            policy = json.loads((folder / "policy.json").read_text())
            policy["changed_observations"] = [999]
            (folder / "policy.json").write_text(json.dumps(policy))
            traj["evidence_sha256"]["policy.json"] = _sha(folder / "policy.json")
        else:
            traj["status"] = "rendered"
        (folder / "TRAJECTORY.json").write_text(json.dumps(traj))
        result["paired"][entry["case"]]["arms"][entry["arm"]] = traj
    _seal(path.parent, window, result)
    with pytest.raises(ct.ProjectionError):
        cf.native_rows(path)


def test_unattempted_arm_emits_no_fabricated_cost_metrics(fx):
    path, window = _partial(fx)
    result = json.loads(path.read_text())
    for case in result["paired"].values():
        cell = case["arms"]["A1-k4"]
        if "ordinal" in cell:
            shutil.rmtree(window / f"cell-{cell['ordinal']:02d}")
        case["arms"]["A1-k4"] = {"status": "unattempted", "correct": None}
    result["arms"]["A1-k4"] = dict(scheduled=3, attempted=0, graded=0, correct=0,
        abstained=0, UNKNOWN=0, NA=0, non_termination=0, tokens_cases=0,
        mean_total_tokens=None, mean_wall_s=None, accuracy_among_graded=None,
        accuracy_over_attempted=None)
    result.update(recorded=3, completed=3)
    path = _seal(path.parent, window, result)
    rows = [n for n in cf.native_rows(path) if n["arm"] == "A1-k4"]
    assert [n["metric"] for n in rows] == [cf.M_ACC]
    claim = cf.project(rows[0])
    assert claim.reps == 3 and claim.reps_basis == "scheduled:cells"
    assert "unattempted 3" in claim.claim and "recorded 0/3" in claim.claim


def test_na_is_terminal_but_not_a_graded_or_cost_observation(fx):
    path, window = _partial(fx)
    result = json.loads(path.read_text())
    cell = next(v["arms"]["A1-k4"] for v in result["paired"].values()
                if v["arms"]["A1-k4"]["status"] == "UNKNOWN")
    cell.update(status="NA", non_termination=1, finish_reason="context_budget")
    cell.pop("error")
    (window / f"cell-{cell['ordinal']:02d}" / "TRAJECTORY.json").write_text(json.dumps(cell))
    result["completed"] += 1
    result["arms"]["A1-k4"].update(UNKNOWN=0, NA=1, non_termination=1)
    path = _seal(path.parent, window, result)
    d = cf.read_unit(path)["derived"]["A1-k4"]
    assert (d["NA"], d["UNKNOWN"], d["attempted"], d["tokens_cases"]) == (1, 0, 2, 1)
    t = cf.project({"result_path": str(path), "arm": "A1-k4", "metric": cf.M_ACC})
    assert "NA 1" in t.claim and t.extra["outcomes"]["NA"] == 1
