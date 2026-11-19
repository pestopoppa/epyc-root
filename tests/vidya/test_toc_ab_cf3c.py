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


def test_incomplete_and_errored_windows_refuse(fx):
    path, _ = fx
    base = json.loads(path.read_text())
    for patch, why in (({"coverage_complete": False}, "incomplete"), ({"error": "boom"}, "error")):
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
