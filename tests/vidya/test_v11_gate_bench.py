"""VB-HARVEST-1022.a: V11 gate llama-bench A/B timing -> OBSERVATION tuples graded by the one shared ladder."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import v11_gate_bench as vg  # noqa: E402

REAL = sorted(Path("/mnt/raid0/llm/tmp/v11-runs/050").glob("*/DECISION.json"))
WHEN = "2026-11-07T00:00:00Z"
PRE = b"# PREDECLARED -- V11-999\nwritten before any run\n"
A, B = (100.0, 102.0, 101.0), (90.0, 91.0, 89.0)


def _row(ts, commit, hardened=False):
    return {"build_commit": commit, "model_filename": "/m/q.gguf", "n_prompt": 512, "n_gen": 0, "n_depth": 0,
            "autokernel_hardened": hardened, "avg_ts": ts}


def _med(v):
    return sorted(v)[1]


def build(d: Path, *, hardened=False, lie=False):
    d.mkdir(parents=True)
    (d / "COMPLETE").write_text("x")
    (d / "PREDECLARED.md").write_bytes(PRE)
    for i in range(3):
        (d / f"bench_main-A{i}.json").write_text(json.dumps([_row(A[i], "aaaaaaaaa")]))
        (d / f"bench_main-B{i}.json").write_text(json.dumps([_row(B[i], "bbbbbbbbb", hardened and i == 1)]))
    eff = round(100 * (_med(B) / _med(A) - 1), 3) + (5.0 if lie else 0.0)
    spread = lambda v: round(100 * (max(v) - min(v)) / _med(v), 3)
    (d / "DECISION.json").write_text(json.dumps({
        "complete": True, "item": "V11-999", "decision": "hold", "decided_at": "2026-11-06T01:00:00Z",
        "predeclared_sha256": hashlib.sha256(PRE).hexdigest(),
        "effects": {"pp512": {"effect_pct": eff, "base_spread_pct": spread(A), "arm_spread_pct": spread(B),
                              "n_base": 3, "n_arm": 3}}}))
    return d


def test_synthetic_projects_observation_graded_by_shared_ladder(tmp_path):
    rows = vg.native_rows(build(tmp_path / "run"))
    assert len(rows) == 1
    t = vg.project(rows[0])
    q, _, _ = ct.grade(t)
    assert t.protocol_id == "" and t.metric == "v11_bench_effect_pct" and t.reps == 3
    assert q != "Witnessed"  # no protocol -> capped by the shared ladder, never by this adapter
    assert vg.frames_for_path(tmp_path / "run", as_of=WHEN)


def test_negative_controls_refuse(tmp_path):
    with pytest.raises(ct.ProjectionError, match="does not re-derive"):
        vg.native_rows(build(tmp_path / "lie", lie=True))
    with pytest.raises(ct.ProjectionError, match="autokernel_hardened"):
        vg.native_rows(build(tmp_path / "hard", hardened=True))
    d = build(tmp_path / "pre")
    (d / "PREDECLARED.md").write_bytes(PRE + b"edited\n")
    with pytest.raises(ct.ProjectionError, match="sha256 differs"):
        vg.native_rows(d)
    d = build(tmp_path / "inc")
    (d / "COMPLETE").unlink()
    with pytest.raises(ct.ProjectionError, match="COMPLETE"):
        vg.native_rows(d)


def test_absent_decision_declines(tmp_path):
    assert vg.native_rows(tmp_path) == ()
    assert vg.units(tmp_path) == []


@pytest.mark.skipif(not REAL, reason="real v11-050 run dir not present")
def test_real_v11_runs_rederive():
    for item, n in (("050", 3), ("051", 8), ("052", 16)):
        d = sorted(Path(f"/mnt/raid0/llm/tmp/v11-runs/{item}").glob("*/"))[0]
        assert len(vg.native_rows(d)) == n


@pytest.mark.skipif(not REAL, reason="real v11-050 run dir not present")
def test_real_run_tamper_copy_refuses(tmp_path):
    d = tmp_path / "t"
    shutil.copytree(REAL[0].parent, d, ignore=shutil.ignore_patterns("slots"))
    f = d / "bench_main-B1.json"
    rows = json.loads(f.read_text())
    rows[0]["avg_ts"] *= 1.2
    f.write_text(json.dumps(rows))
    with pytest.raises(ct.ProjectionError, match="does not re-derive"):
        vg.native_rows(d)
