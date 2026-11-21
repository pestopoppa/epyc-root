#!/usr/bin/env python3
"""Tests for akloop/chain.py (AK parallel loop P2): chain scaffold, dry-run lint, successor emitter. Never publishes.

Temp dirs only; the GPU harness fetch is stubbed; estimate history is injected.
Run: python3 -m pytest -q scripts/coordination/tests/test_akloop_chain.py
"""
import json
import os
import sys
from pathlib import Path

import pytest

_COORD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_COORD / "akloop"))

import chain as C  # noqa: E402

HARNESS = {"gpu_common.py": b"# gpu_common stub\n", "gpuproof_row.py": b"# gpuproof stub\n"}


def _recs():
    """Usable history: 4 builds ~240 s, 3 kld gates ~1000 s, 3 fold rows ~5000 s; timing has < 3 runs."""
    out = []
    for i, w in enumerate((230, 240, 245, 250)):
        out.append({"row": f"ak-x{i}-build-20261120", "usable": True, "wall_s": w, "units": None, "overrun": False})
    for i, w in enumerate((900, 1000, 1100)):
        out.append({"row": f"ak-y{i}-kld-gpu-20261120", "usable": True, "wall_s": w, "units": None, "overrun": False})
    for i, w in enumerate((4000, 5000, 5200)):
        out.append({"row": f"c1{i}-fold-gpu-20261120", "usable": True, "wall_s": w, "units": None, "overrun": False})
    out.append({"row": "ak-z-timing-20261120", "usable": True, "wall_s": 700, "units": None, "overrun": False})
    out.append({"row": "unrelated-row-20261120", "usable": True, "wall_s": 99999, "units": None, "overrun": False})
    return out


@pytest.fixture
def cand():
    return C.candidate("4bc50bd65187", "2944feaff502", "AK-GAP-1-IDSORT", "+13.8%")


@pytest.fixture(autouse=True)
def stub_harness(monkeypatch):
    monkeypatch.setattr(C.RS, "fetch_harness", lambda repo, ref="origin/main": ("deadbeef", dict(HARNESS)))


def _chain(tmp_path, cand, **kw):
    return C.scaffold_chain(cand, root=str(tmp_path / "rows"), date="20261121", handoff="churn-pipeline.md",
                            recs=_recs(), **kw)


def test_candidate_validation():
    with pytest.raises(ValueError):
        C.candidate("not-a-sha", "2944feaff502", "H", "x")
    with pytest.raises(ValueError):
        C.candidate("4bc50bd65187", "2944feaff502", "", "x")
    assert C.candidate("4bc50bd65187", "2944feaff502", "AK-X", "+1%")["id"] == "cand-ak-x-2944feaff"


def test_stage_estimates_from_history():
    est, just = C.stage_estimate(C.STAGE_BY_NAME["build"], _recs())
    assert est == 307 and "p75" in just                      # nearest-rank p75 245 x 1.25 -> 307
    est, just = C.stage_estimate(C.STAGE_BY_NAME["ab-timing"], _recs())
    assert est == C.STAGE_BY_NAME["ab-timing"].fallback_s and "< 3" in just   # 1 run: stated fallback
    est, _ = C.stage_estimate(C.STAGE_BY_NAME["fold-check"], _recs())
    assert est == 6500                                       # p75 5200 x 1.25


def test_chain_shapes_deps_and_lint(tmp_path, cand):
    rep = _chain(tmp_path, cand)
    assert rep["published"] is False and rep["lint_clean"], [r["lint"] for r in rep["rows"]]
    rows = {r["stage"]: r for r in rep["rows"]}
    assert list(rows) == ["build", "oracle-kld", "ab-timing", "fold-check"]
    specs = {k: json.load(open(os.path.join(r["rowdir"], "spec.json"))) for k, r in rows.items()}
    # builds on one CPU quarter, never q3
    assert specs["build"]["lane"] == "cpu" and specs["build"]["regions"] == "q1"
    # GPU timing holds 88-95; the oracle row does not book the timing cores
    assert "88-95" in specs["ab-timing"]["regions"] and specs["ab-timing"]["timing"] == "ak-keep-gate"
    assert specs["ab-timing"]["admission_class"] == "block-timing-quiet"
    assert "88-95" not in specs["oracle-kld"]["regions"]
    # resumable where safe; the A/B timing window is one grant
    assert specs["build"]["resumable"] and specs["fold-check"]["resumable"] and not specs["ab-timing"]["resumable"]
    # lineage / supersedes / gate deps / P1 gate ids
    for k, s in specs.items():
        assert s["lineage"] == cand["id"] and "supersedes" in s and s["gate_ids"]
    assert specs["build"]["gate"] == []
    assert specs["oracle-kld"]["gate"] == [rows["build"]["box"]]
    assert specs["fold-check"]["gate"] == [rows["ab-timing"]["box"]]
    assert "graph_kld.gpu.q38_27b" in specs["oracle-kld"]["gate_ids"]
    box = open(rep["box_file"]).read()
    assert f"· gate: {rows['build']['box']}" in box and "est 307 s" in box


def test_prior_rows_become_supersedes(tmp_path, cand):
    rep = _chain(tmp_path, cand, prior={"fold-check": "c17-fold-gpu-20261121-r2"})
    fold = json.load(open(os.path.join(rep["rows"][-1]["rowdir"], "spec.json")))
    assert fold["supersedes"] == "c17-fold-gpu-20261121-r2"


def test_lint_catches_q3_build(tmp_path, cand):
    rep = _chain(tmp_path, cand)
    d = rep["rows"][0]["rowdir"]
    sp = json.load(open(os.path.join(d, "spec.json")))
    sp["regions"] = sp["claim_cpus"] = "q3"
    json.dump(sp, open(os.path.join(d, "spec.json"), "w"))
    C.RS.seal(d, ["job.py", "check_complete.py", "launch.sh", "spec.json"])
    errs = C.lint_row(d, rep["box_file"])
    assert any("CHAIN-Q3" in e or "CPU-GPUTHR" in e for e in errs)


def test_successor_changes_only_the_named_clause(tmp_path, cand):
    rep = _chain(tmp_path, cand)
    d = rep["rows"][2]["rowdir"]
    (Path(d) / "out" / "RESULT.json").write_text(json.dumps({"complete": True, "verdict": "FUTILITY_HARNESS_CAP"}))
    old = json.load(open(os.path.join(d, "spec.json")))
    r = C.successor(d, {"estimate_s": 2400}, "cap raised to 2400 s after r1 hit the window", ["box line 12"])
    new = json.load(open(os.path.join(r["rowdir"], "spec.json")))
    assert new["id"] == old["id"] + "-r2" and new["supersedes"] == old["id"]
    assert C.spec_diff(old, new) == ["estimate_s", "notes", "successor_of", "supersedes"]
    assert new["successor_of"]["changed"] == {"estimate_s": {"from": old["estimate_s"], "to": 2400}}
    assert any(e.endswith("RESULT.json") for e in new["successor_of"]["evidence"])
    assert C.lint_row(r["rowdir"], rep["box_file"]) == []
    assert f"--id {new['id']}" in open(os.path.join(r["rowdir"], "launch.sh")).read()
    for n in ("launch.sh", "check_complete.py", "job.py", "spec.json"):   # the new dir holds the old id: no double rewrite
        assert "-r2-r2" not in open(os.path.join(r["rowdir"], n)).read()
    r3 = C.successor(r["rowdir"], {"min_window_s": 900}, "rule change")
    assert r3["id"].endswith("-r3")
    assert "--min-window 900" in open(os.path.join(r3["rowdir"], "launch.sh")).read()


def test_successor_refuses_other_clauses(tmp_path, cand):
    rep = _chain(tmp_path, cand)
    with pytest.raises(ValueError):
        C.successor(rep["rows"][0]["rowdir"], {"owner": "someone"}, "x")
    with pytest.raises(ValueError):
        C.successor(rep["rows"][0]["rowdir"], {}, "x")


def test_candidate_from_ledger():
    ledger = {"current_fold": "llama.cpp-experimental-c17-20261121", "next_c": 18,
              "features": [{"tag": "AK-GAP-1-IDSORT", "keep_sha": "2944feaff50257f2ecd0fc42b9981fd8b1868666",
                            "hypothesis": "x (AK-GAP-1-IDSORT; r3 KEEP, A3B e2e +13.8%)", "test_files": ["t.cpp"]}]}
    c = C.candidate_from_ledger(ledger, "AK-GAP-1-IDSORT", git=lambda *a: "4bc50bd6518703341b32388ce87aaf97fd4aeeaa")
    assert c["base_sha"].startswith("4bc50bd") and c["predicted_effect"] == "+13.8%" and c["next_c"] == 18
    with pytest.raises(ValueError):
        C.candidate_from_ledger(ledger, "NOPE")


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest scripts/coordination/tests/test_akloop_chain.py -q")
