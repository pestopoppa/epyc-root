"""Canary B frontier assertion: NOT_EXERCISED without a real row, controls gate the verdict."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya" / "canary"))
import canary_b_frontier as cbf  # noqa: E402

FENCE = cbf.FENCE_TS_DEFAULT


def fake_renderer(rows, scratch):
    """Mimics the fenced archive: only post-fence frontier keeps reach the frontier channels."""
    kept = [r for r in rows if cbf.qualifies(r, FENCE)]
    text = "\n".join(f"  #{r['trial_id']} q={r['quality']:.3f}" for r in kept)
    return {"pareto_summary": text, "pareto_geometry": "", "insights_structured": ""}


def leaky_renderer(rows, scratch):
    return {"pareto_summary": "\n".join(f"#{r['trial_id']} q={r['quality']:.3f}" for r in rows)}


def blind_renderer(rows, scratch):
    return {"pareto_summary": ""}


def test_fixture_shapes():
    pos, neg = cbf.synthetic_rows(FENCE)
    assert cbf.qualifies(pos, FENCE) and not cbf.qualifies(neg, FENCE)
    assert pos["hypothesis"] == cbf.SYNTHETIC_LABEL == neg["hypothesis"]
    # real trial 1472 shape: pre-fence + excluded
    assert not cbf.qualifies({"trial_id": 1472, "timestamp": "2026-08-04T17:05:00+00:00",
                              "pareto_status": "frontier", "keep_revert_decision": "excluded"}, FENCE)


def test_no_real_row_is_not_exercised_not_fail(tmp_path):
    ctrl = cbf.run_controls(fake_renderer, tmp_path)
    assert ctrl["ok"]
    v = cbf.frontier_verdict([], {}, ctrl)
    assert v["status"] == cbf.NOT_EXERCISED
    # a pre-fence frontier row is still not a trigger
    pre = {"trial_id": 1472, "timestamp": "2026-08-04T17:05:00+00:00",
           "pareto_status": "frontier", "keep_revert_decision": "keep", "quality": 2.025}
    assert cbf.frontier_verdict([pre], {}, ctrl)["status"] == cbf.NOT_EXERCISED


def test_real_row_pass_and_fail(tmp_path):
    ctrl = cbf.run_controls(fake_renderer, tmp_path)
    pos, _ = cbf.synthetic_rows(FENCE)
    real = dict(pos, trial_id=1600, quality=2.5)
    assert cbf.frontier_verdict([real], {"pareto_summary": "#1600 q=2.500"}, ctrl)["status"] == cbf.PASS
    v = cbf.frontier_verdict([real], {"pareto_summary": "nothing"}, ctrl)
    assert v["status"] == cbf.FAIL and v["missing"] == [1600]


def test_broken_controls_are_control_failed(tmp_path):
    for r in (leaky_renderer, blind_renderer):
        ctrl = cbf.run_controls(r, tmp_path)
        assert not ctrl["ok"]
        assert cbf.frontier_verdict([], {}, ctrl)["status"] == cbf.CONTROL_FAILED

    def boom(rows, scratch):
        raise RuntimeError("x")
    ctrl = cbf.run_controls(boom, tmp_path)
    assert not ctrl["ok"] and "RuntimeError" in ctrl["error"]
