#!/usr/bin/env python3
"""Tests for akloop/chain.py (AK parallel loop P2): chain scaffold, dry-run lint, successor emitter. Never publishes.

Temp dirs only; the GPU harness fetch is stubbed; estimate history is injected.
Run: python3 -m pytest -q scripts/coordination/tests/test_akloop_chain.py
"""
import json
import os
import re
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
    monkeypatch.setattr(C, "research_head", lambda repo=None, ref="origin/main": "f" * 40)


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


#: Publish-lint errors every scaffolded chain row carries on origin/main (they predate op-perf and apply to GPU rows
#: and to the whole-host CPU rows alike): the estimate is not smoke-derived, the seal lists spec.json, and a GPU row's
#: launch.sh `C=` is not a cpu list. A chain row's OWN lint (CHAIN-*, WIDTH, CPU-GPUTHR, ...) must still be clean.
_KNOWN_PUBLISH_LINT = ("PUBLISH-LINT", "ESTIMATE-UNMEASURED", "SEALED-SPEC", "CLAIM-PARSE")


def _own_lint(row):
    """The row's lint problems minus the known publish-lint codes (matched by their CODE: prefix, not by message text)."""
    out = []
    for e in row["lint"]:
        if e.startswith("PUBLISH-LINT"):
            out += [f"PUBLISH-LINT {c}" for c in re.findall(r"\b([A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+):", e)
                    if c not in _KNOWN_PUBLISH_LINT]
        else:
            out.append(e)
    return out


def _specs(rep):
    return {r["stage"]: json.load(open(os.path.join(r["rowdir"], "spec.json"))) for r in rep["rows"]}


def test_chain_shapes_deps_and_lint(tmp_path, cand):
    rep = _chain(tmp_path, cand)
    assert rep["published"] is False and not [_own_lint(r) for r in rep["rows"] if _own_lint(r)]
    rows = {r["stage"]: r for r in rep["rows"]}
    # the 5-stage order of research stage_bodies.STAGES: op-perf sits before ab-timing
    assert list(rows) == ["build", "oracle-kld", "op-perf", "ab-timing", "fold-check"]
    assert [s.name for s in C.STAGES] == list(rows)
    specs = {k: json.load(open(os.path.join(r["rowdir"], "spec.json"))) for k, r in rows.items()}
    # builds on one CPU quarter, never q3
    assert specs["build"]["lane"] == "cpu" and specs["build"]["regions"] == "any-of q0,q1,q2"
    # GPU timing holds 88-95; the oracle row does not book the timing cores
    assert "88-95" in specs["ab-timing"]["regions"] and specs["ab-timing"]["timing"] == "ak-keep-gate"
    assert specs["ab-timing"]["admission_class"] == "block-timing-quiet"
    assert "88-95" not in specs["oracle-kld"]["regions"]
    # op-perf on a GPU path is a GPU timing row like ab-timing
    assert specs["op-perf"]["lane"] == "gpu" and specs["op-perf"]["regions"] == "mi210_0,88-95,184-191"
    assert specs["op-perf"]["shape"] == "gpu-q3" and specs["op-perf"]["admission_class"] == "block-timing-quiet"
    # resumable where safe; the A/B timing window is one grant
    assert specs["build"]["resumable"] and specs["fold-check"]["resumable"] and not specs["ab-timing"]["resumable"]
    # lineage / supersedes / gate deps / P1 gate ids
    for k, s in specs.items():
        assert s["lineage"] == cand["id"] and "supersedes" in s and s["gate_ids"]
    assert specs["build"]["gate"] == []
    assert specs["oracle-kld"]["gate"] == [rows["build"]["box"]]
    assert specs["op-perf"]["gate"] == [rows["oracle-kld"]["box"]]
    assert specs["ab-timing"]["gate"] == [rows["op-perf"]["box"]]
    assert specs["fold-check"]["gate"] == [rows["ab-timing"]["box"]]
    assert "graph_kld.gpu.q38_27b" in specs["oracle-kld"]["gate_ids"]
    box = open(rep["box_file"]).read()
    assert f"· gate: {rows['build']['box']}" in box and "est 307 s" in box
    assert f"· gate: {rows['op-perf']['box']}" in box and "never a PASS" in box


def test_gpu_candidate_unchanged_by_serving_path(tmp_path, cand):
    """No serving_path == the explicit default 27b-q8_0|mi210: every spec field identical, and the default is written
    into candidate.json so the stage driver never has to guess."""
    base = _specs(_chain(tmp_path / "a", cand))
    expl = _specs(_chain(tmp_path / "b", dict(cand, serving_path="27b-q8_0|mi210")))
    for st in base:
        a, b = dict(base[st]), dict(expl[st])
        for x in (a, b):
            for k in ("launcher", "result_path", "scratch_root", "workdir", "stop_file"):
                x.pop(k, None)
        assert json.dumps(a, sort_keys=True).replace(str(tmp_path / "a"), "<R>") == \
            json.dumps(b, sort_keys=True).replace(str(tmp_path / "b"), "<R>"), st
    assert base["ab-timing"]["regions"] == C.GPU_TIMING_REGIONS and base["ab-timing"]["lane"] == "gpu"
    assert base["ab-timing"]["shape"] == "gpu-q3" and "requires_quiet_host" not in base["ab-timing"]
    assert base["fold-check"]["lane"] == "gpu" and base["oracle-kld"]["regions"] == C.GPU_PLAIN_REGIONS
    cj = json.load(open(os.path.join(str(tmp_path / "a" / "rows"), base["ab-timing"]["id"], "candidate.json")))
    assert cj["serving_path"] == "27b-q8_0|mi210"


def test_candidate_json_carries_serving_path_and_shape_class(tmp_path, cand):
    """The research op-perf stage refuses a candidate with no shape_class and resolves its path from candidate.json
    (default = the 27B pin): CAND_FIELDS must carry both through to every stage's row."""
    assert {"serving_path", "shape_class"} <= set(C.CAND_FIELDS)
    sc = {"op_family": "MUL_MAT", "dims": {"k": [5120]}}
    rep = _chain(tmp_path, dict(cand, serving_path="a3b-q8_0-cpu|cpu", shape_class=sc))
    for st, spec in _specs(rep).items():
        cj = json.load(open(os.path.join(str(tmp_path / "rows"), spec["id"], "candidate.json")))
        assert cj["serving_path"] == "a3b-q8_0-cpu|cpu" and cj["shape_class"] == sc, st


def test_gpu_path_oracle_kld_keeps_its_gpu_plain_shape(tmp_path, cand):
    specs = _specs(_chain(tmp_path, dict(cand, serving_path="a3b-mtp-mi210|mi210")))
    assert specs["oracle-kld"]["lane"] == "gpu" and specs["oracle-kld"]["regions"] == C.GPU_PLAIN_REGIONS
    assert specs["oracle-kld"]["resumable"] is True and "requires_quiet_host" not in specs["oracle-kld"]


def _knob(cand, **kw):
    """A serving-knob candidate (research serving_knobs.emit_candidate shape): a served-recipe delta, no source change, so
    base == patch == the champion sha it rides."""
    return dict(cand, kind="serving-knob", server="frontdoor-27b", mechanism_id="serving-knob:S1:a1", delta_digest="d" * 64,
                screening_only=True, steady_results="/x/steady.jsonl", arm_map={"A": "a1"},
                burst_results={"a1": "/x/burst.jsonl"}, floor_result="/x/floor.json", **kw)


@pytest.mark.parametrize("path,lane", [("27b-q8_0|mi210", "gpu"), ("a3b-q8_0-cpu|cpu", "cpu")])
def test_serving_knob_candidate_chain_is_one_screen_only_stage(tmp_path, cand, path, lane):
    kc = _knob(cand, serving_path=path)
    assert [s.name for s in C.chain_stages(kc)] == ["serving-screen"]
    rep = _chain(tmp_path, kc)
    assert [r["stage"] for r in rep["rows"]] == ["serving-screen"] and rep["lint_clean"], rep["rows"][0]["lint"]
    s = _specs(rep)["serving-screen"]
    assert s["lane"] == lane and s["serving_path"] == path and s["gate"] == [] and s["gate_ids"]
    if lane == "gpu":
        assert s["regions"] == C.GPU_PLAIN_REGIONS and "timing" not in s
    else:
        assert s["regions"] == "q0,q1,q2,q3" and s["requires_quiet_host"] is True and s["shape"] == "host"
    d = os.path.dirname(s["launcher"])
    cj = json.load(open(os.path.join(d, "candidate.json")))     # the measurement refs reach the stage driver
    assert cj["kind"] == "serving-knob" and cj["steady_results"] == "/x/steady.jsonl" and cj["arm_map"] == {"A": "a1"}
    assert cj["burst_results"] == {"a1": "/x/burst.jsonl"} and cj["floor_result"] == "/x/floor.json"
    box = open(rep["box_file"]).read()
    assert "never a PASS" in box and "serving-screen" in box and "polar PASS/FAIL" not in box


def test_serving_screen_is_never_a_fold_input_or_for_other_candidates(cand):
    assert "serving-screen" not in [s.name for s in C.STAGES]
    for stages in (["build", "serving-screen", "fold-check"], ["serving-screen"]):
        with pytest.raises(ValueError):
            C.chain_stages(dict(cand, stages=stages))
    with pytest.raises(ValueError):
        C.chain_stages(_knob(cand, stages=["build", "oracle-kld", "fold-check"]))
    assert "serving-screen" in C.SCREEN_STAGE_NAMES and "op-perf" in C.SCREEN_STAGE_NAMES


@pytest.mark.parametrize("path", ["q38fn-ud-iq4xs-cpu|cpu", "a3b-q8_0-cpu|cpu"])
def test_cpu_path_oracle_op_perf_and_ab_timing_are_whole_host_quiet_cpu_rows(tmp_path, cand, path):
    rep = _chain(tmp_path, dict(cand, serving_path=path))
    assert not [_own_lint(r) for r in rep["rows"] if _own_lint(r)], [r["lint"] for r in rep["rows"]]
    specs = _specs(rep)
    assert list(specs) == ["build", "oracle-kld", "op-perf", "ab-timing", "fold-check"]
    for st in ("oracle-kld", "op-perf", "ab-timing"):
        s = specs[st]
        # the published whole-host quiet CPU shape (ak-q38fn-cpu-aa-floor / ak-a3b-cpu-aa-floor rows), never gpu-q3
        assert s["lane"] == "cpu" and s["regions"] == "q0,q1,q2,q3" and s["claim_cpus"] == "any-of q0,q1,q2"
        assert s["shape"] == "host" and s["declared_threads"] == 96 and s["requires_quiet_host"] is True
        assert s["role"] == "bench" and s["resumable"] is False and s["serving_path"] == path
        assert "mi210" not in s["regions"] and "184" not in s["regions"]
        assert "timing" not in s and "admission_class" not in s          # no GPU timing grant
        assert len(s["width_justification"]) >= 20 and s["baseline_ref"] and s["threads_evidence"]
        assert s["family"] == f"akchain-{st}" and s["gate_ids"]
        d = os.path.dirname(s["launcher"])
        launch = open(os.path.join(d, "launch.sh")).read()
        assert "--class cpu" in launch and "--claim-cpus" not in launch and "\nC=" not in launch
        assert "mi210" not in launch
        cj = json.load(open(os.path.join(d, "candidate.json")))
        assert cj["serving_path"] == path
        assert "STAGE, LANE, ROW = " + repr(st) + ", 'cpu'" in open(os.path.join(d, "job.py")).read()
        assert not _own_lint({"lint": C.lint_row(d, rep["box_file"])})
    # the CPU path's history is its own: GPU timing rows are not its samples (the `_recs` ab-timing row is a GPU row)
    assert "usable runs < 3" in specs["ab-timing"]["estimate_justification"]
    assert specs["ab-timing"]["estimate_s"] == C.CPU_PATH_FALLBACK_S["ab-timing"]
    assert specs["op-perf"]["estimate_s"] == C.CPU_PATH_FALLBACK_S["op-perf"]
    # oracle-kld on a CPU path is a whole-host quiet cpu row so the path's own CPU KLD clauses can run (no population yet:
    # a stated provisional fallback, never a GPU-oracle borrow)
    assert specs["oracle-kld"]["estimate_s"] == C.CPU_PATH_FALLBACK_S["oracle-kld"]
    assert specs["oracle-kld"]["estimate_basis"]["provisional"] is True
    assert specs["oracle-kld"]["gate"] == [rep["rows"][0]["box"]]
    # gates still chain in order; build and fold-check keep today's lanes
    assert specs["ab-timing"]["gate"] == [rep["rows"][2]["box"]] and specs["op-perf"]["gate"] == [rep["rows"][1]["box"]]
    assert specs["build"]["lane"] == "cpu" and specs["build"]["regions"] == "any-of q0,q1,q2"
    assert specs["fold-check"]["lane"] == "gpu"
    assert specs["fold-check"]["regions"] == C.GPU_TIMING_REGIONS
    box = open(rep["box_file"]).read()
    assert f"served path {path}" in box


def test_cpu_path_narrowed_chain_and_bad_paths(tmp_path, cand):
    narrowed = dict(cand, serving_path="a3b-q8_0-cpu|cpu", stages=["build", "oracle-kld", "fold-check"])
    assert [s.name for s in C.chain_stages(narrowed)] == ["build", "oracle-kld", "fold-check"]
    ab = dict(cand, serving_path="a3b-q8_0-cpu|cpu", stages=["build", "op-perf", "ab-timing", "fold-check"])
    assert [(s.name, s.lane) for s in C.chain_stages(ab)] == [("build", "cpu"), ("op-perf", "cpu"), ("ab-timing", "cpu"),
                                                             ("fold-check", "gpu")]
    assert [(s.name, s.lane) for s in C.chain_stages(narrowed)][1] == ("oracle-kld", "cpu")
    for bad in ("a3b-q8_0-cpu", "a3b|gpu", "|cpu", "A3B|cpu"):
        with pytest.raises(ValueError):
            C.chain_stages(dict(cand, serving_path=bad))


def test_lint_catches_cpu_path_row_on_a_gpu_shape(tmp_path, cand):
    rep = _chain(tmp_path, dict(cand, serving_path="q38fn-ud-iq4xs-cpu|cpu"))
    d = next(r["rowdir"] for r in rep["rows"] if r["stage"] == "ab-timing")
    sp = json.load(open(os.path.join(d, "spec.json")))
    sp.update({"lane": "gpu", "shape": "gpu-q3", "regions": C.GPU_TIMING_REGIONS, "timing": "ak-keep-gate"})
    json.dump(sp, open(os.path.join(d, "spec.json"), "w"))
    C.RS.seal(d, ["job.py", "check_complete.py", "launch.sh", "spec.json"])
    assert any("CHAIN-PATHLANE" in e for e in C.lint_row(d, rep["box_file"]))
    sp.update({"lane": "cpu", "shape": "quarter", "regions": "q0,q1,q2", "requires_quiet_host": False})
    sp.pop("timing")
    json.dump(sp, open(os.path.join(d, "spec.json"), "w"))
    C.RS.seal(d, ["job.py", "check_complete.py", "launch.sh", "spec.json"])
    assert any("CHAIN-CPUPATH" in e for e in C.lint_row(d, rep["box_file"]))


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
    d = next(r["rowdir"] for r in rep["rows"] if r["stage"] == "ab-timing")
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


# ---- AKPL-P3: stage driver, stage subsets, rebase chains -------------------------------------------------------

def test_job_runs_pinned_stage_driver(tmp_path, cand):
    rep = _chain(tmp_path, cand)
    rows = {r["stage"]: r for r in rep["rows"]}
    job = open(os.path.join(rows["oracle-kld"]["rowdir"], "job.py")).read()
    assert "FUTILITY_HARNESS_STAGE_DRIVER_MISSING" not in job
    assert "autokernel.loop.stage_bodies" in job and "git\", \"-C\", RESEARCH_REPO, \"archive\"" in job
    assert "f" * 40 in job                                         # pinned research commit
    assert os.path.join(rows["build"]["rowdir"], "out", "RESULT.json") in job   # upstream RESULT handed down
    bjob = open(os.path.join(rows["build"]["rowdir"], "job.py")).read()
    assert 'os.environ["HIP_VISIBLE_DEVICES"] = "-1"' in bjob and "LANE, ROW = 'build', 'cpu'" in bjob
    cj = json.load(open(os.path.join(rows["build"]["rowdir"], "candidate.json")))
    assert cj["patch_sha"] == cand["patch_sha"] and cj["base_sha"] == cand["base_sha"]
    assert "candidate.json" in open(os.path.join(rows["build"]["rowdir"], "SOURCE.sha256")).read()


def test_offline_rows_never_publishable(tmp_path, cand):
    rep = _chain(tmp_path, cand, research_tree=str(tmp_path), test_mode=True)
    assert all(any(e.startswith("CHAIN-TESTMODE") for e in r["lint"]) for r in rep["rows"])
    rep2 = C.scaffold_chain(dict(cand), root=str(tmp_path / "rows2"), date="20261121", handoff="churn-pipeline.md",
                            recs=_recs(), research_tree=str(tmp_path))
    assert all(any(e.startswith("CHAIN-DRIVER") for e in r["lint"]) for r in rep2["rows"])


def test_rebase_chain_subset_and_distinct_ids(tmp_path, cand):
    first = _chain(tmp_path, cand)
    rb = dict(cand, patch_sha="7777777aaaaa", base_sha="9999999bbbbb", stages=["build", "oracle-kld", "fold-check"],
              skip_stages=["ab-timing"], rebase_of={"candidate": cand["id"]})
    rep = _chain(tmp_path, rb)
    assert [r["stage"] for r in rep["rows"]] == ["build", "oracle-kld", "fold-check"]
    assert not {r["id"] for r in rep["rows"]} & {r["id"] for r in first["rows"]}
    assert all("-rb7777777-" in r["id"] for r in rep["rows"])
    fold = json.load(open(os.path.join(rep["rows"][-1]["rowdir"], "spec.json")))
    assert fold["gate"] == [rep["rows"][1]["box"]] and fold["rebase_of"]["candidate"] == cand["id"]
    with pytest.raises(ValueError):
        C.chain_stages(dict(cand, stages=["oracle-kld", "fold-check"]))


@pytest.mark.parametrize("path", [None, "a3b-q8_0-cpu|cpu"])
def test_every_scaffolded_row_passes_publish_lint_with_zero_fails(tmp_path, cand, path):
    """CPU and GPU shapes: no ESTIMATE-UNMEASURED, SEALED-SPEC or CLAIM-PARSE (ak_row_lint) on any chain row."""
    import ak_row_lint as AL
    rep = _chain(tmp_path, dict(cand, serving_path=path) if path else cand)
    assert {r["lane"] for r in rep["rows"]} >= ({"cpu"} if path else {"gpu", "cpu"})
    for r in rep["rows"]:
        fails = [x for x in AL.lint_dir(r["rowdir"], selftest=False) if x[0] == "FAIL"]
        codes = {x[1] for x in fails}
        assert not codes & {"ESTIMATE-UNMEASURED", "SEALED-SPEC", "CLAIM-PARSE"}, (r["id"], fails)
        assert C.lint_row(r["rowdir"], rep["box_file"]) == [], r["id"]
        assert "spec.json" not in open(os.path.join(r["rowdir"], "SOURCE.sha256")).read()
