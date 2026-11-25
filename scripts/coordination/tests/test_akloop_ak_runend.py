#!/usr/bin/env python3
"""AKPL-P3 wiring: ak_runend (watcher ENDED hook) and the keeper's record_fail failure classifier. Temp dirs only."""
import json
import os
import sys
from types import SimpleNamespace

_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_COORD, "akloop"))
sys.path.insert(0, os.path.join(_COORD, "rowflow"))
import ak_runend as AR  # noqa: E402


class FakeNotify:
    def __init__(self):
        self.calls = []

    def emit(self, flags, kind, rid, disc, summary, severity, **kw):
        self.calls.append((kind, rid, disc))
        return {"kind": kind}

    def smoke_fail(self, *a, **k):
        return None


def _row(tmp_path, rid, result):
    flags = tmp_path / "flags"
    rp = tmp_path / f"{rid}.RESULT.json"
    if result is not None:
        rp.write_text(json.dumps(result))
    (flags / "ready").mkdir(parents=True, exist_ok=True)
    (flags / "ready" / f"{rid}.json").write_text(json.dumps({"id": rid, "owner": "autokernel", "result_path": str(rp)}))
    return str(flags)


def test_chain_row_files_with_gate_eval_and_routes_harness(tmp_path):
    flags = _row(tmp_path, "akc-x-oracle-kld-20261121", {"complete": True, "verdict": "FUTILITY_RESIDENCY (proof)"})
    seen, nm = [], FakeNotify()
    run = lambda argv, **k: seen.append(argv) or SimpleNamespace(stdout="AUTO-FILE akc-x: FAIL\n", returncode=0)
    rep = AR.handle("akc-x-oracle-kld-20261121", flags, runend_run=run, notify_mod=nm, census=lambda r, p: "c")
    assert seen and seen[0][-3:] == ["akc-x-oracle-kld-20261121", "--gate-eval", "--file"]
    assert rep["filed"].startswith("AUTO-FILE") and rep["class"]["side"] == "harness" and rep["class"]["routed"]
    assert nm.calls and nm.calls[0][0] == "ak-harness-failure"
    assert "lineage" not in rep


def test_candidate_failure_is_not_routed(tmp_path):
    flags = _row(tmp_path, "akc-x-ab-timing-20261121", {"complete": True, "verdict": "FAIL_NO_GAIN", "polar": "FAIL"})
    nm = FakeNotify()
    rep = AR.handle("akc-x-ab-timing-20261121", flags, runend_run=lambda a, **k: SimpleNamespace(stdout="", returncode=0),
                    notify_mod=nm, census=lambda r, p: "c")
    assert rep["class"]["side"] == "candidate" and not nm.calls


def test_composite_row_triggers_lineage_and_no_filing(tmp_path):
    flags = _row(tmp_path, "c18-fold-gpu-20261121-r1", {"complete": True, "verdict": "PASS", "polar": "PASS"})
    got = []
    rep = AR.handle("c18-fold-gpu-20261121-r1", flags, runend_run=lambda *a, **k: (_ for _ in ()).throw(AssertionError),
                    lineage=lambda rid: got.append(rid) or "/tmp/lin", notify_mod=FakeNotify(),
                    census=lambda r, p: "c")
    assert got == ["c18-fold-gpu-20261121-r1"] and rep["lineage"] == "/tmp/lin" and "filed" not in rep
    assert "AK-RUNEND c18-fold-gpu-20261121-r1" in AR.line(rep)


def test_census_step_fires_with_the_result_path(tmp_path):
    flags = _row(tmp_path, "ak-x-op-gpu-20261122", {"complete": True, "verdict": "OP_PASS"})
    got = []
    rep = AR.handle("ak-x-op-gpu-20261122", flags, notify_mod=FakeNotify(),
                    census=lambda r, p: got.append((r, p)) or "BW-CENSUS {}")
    assert got == [("ak-x-op-gpu-20261122", str(tmp_path / "ak-x-op-gpu-20261122.RESULT.json"))]
    assert "census=BW-CENSUS" in AR.line(rep)


def test_census_update_skips_missing_result(tmp_path):
    assert AR.census_update("r", str(tmp_path / "nope.json"), kernel_rnd="/nonexistent") == "-"


def test_dry_run_runs_nothing(tmp_path):
    flags = _row(tmp_path, "akc-x-build-20261121", None)
    rep = AR.handle("akc-x-build-20261121", flags, dry_run=True,
                    runend_run=lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert rep["filed"].startswith("dry-run") and rep["class"]["klass"] == "result_contract"
    assert "routed" not in rep["class"]


def test_record_fail_classifies_ak_rows_only(tmp_path, monkeypatch):
    import rowflow as rf
    nm = FakeNotify()
    monkeypatch.setattr(rf, "notify", nm)
    flags = str(tmp_path / "flags")
    os.makedirs(os.path.join(flags, "dryrun", "akc-x-build-20261121"))
    launcher = tmp_path / "launch.sh"
    launcher.write_text("#!/bin/bash\n")
    d = {"launcher": {"path": str(launcher)}, "owner": "pipeline-mgmt"}
    monkeypatch.setattr(rf, "row_sha", lambda flags, rid: "x")
    rec = rf.record_fail(flags, "akc-x-build-20261121", d, "smoke_predicate `test -s x` never exited 0", {})
    assert rec["failclass"]["side"] == "harness" and rec["failclass"]["routed"]
    assert ("ak-harness-failure", "akc-x-build-20261121") == nm.calls[0][:2]
    os.makedirs(os.path.join(flags, "dryrun", "other-row-20261121"))
    rec2 = rf.record_fail(flags, "other-row-20261121", d, "smoke_predicate `x` never exited 0", {})
    assert "failclass" not in rec2
    on_disk = json.load(open(os.path.join(flags, "dryrun", "akc-x-build-20261121", "FAIL-1.json")))
    assert on_disk["failclass"]["klass"] == "smoke_wiring"


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/coordination/tests/test_akloop_ak_runend.py -q")


def test_census_update_passes_merge_static_every_run(tmp_path):
    kr = tmp_path / "kr"
    loop = kr / "autokernel" / "loop"
    (loop / "census").mkdir(parents=True)
    (loop / "census" / "mi210_bandwidth_census.json").write_text("{}")
    (loop / "census_update.py").write_text("# supports --merge-static-from\n")
    res = tmp_path / "r.json"
    res.write_text("{}")
    state = tmp_path / "state"
    (state).mkdir()
    (state / "mi210_bandwidth_census.json").write_text("{}")  # live file already exists: seed-copy branch is skipped
    seen = []

    def fake(argv, **kw):
        seen.append(argv)
        return type("R", (), {"stdout": "BW-CENSUS {}", "stderr": "", "returncode": 0})()

    AR.census_update("r", str(res), kernel_rnd=str(kr), state=str(state), run=fake)
    assert "--merge-static-from" in seen[0]
    assert seen[0][seen[0].index("--merge-static-from") + 1].endswith("mi210_bandwidth_census.json")
    (loop / "census_update.py").write_text("# old\n")  # snapshot predating the flag must not receive it
    AR.census_update("r", str(res), kernel_rnd=str(kr), state=str(state), run=fake)
    assert "--merge-static-from" not in seen[1]


def _kr_with_inbox(tmp_path, present=True):
    loop = tmp_path / "kr" / "autokernel" / "loop"
    loop.mkdir(parents=True)
    if present:
        (loop / "census_inbox.py").write_text("# RSL-R2\n")
    return str(tmp_path / "kr")


def test_census_inbox_tolerates_module_absent_from_the_snapshot(tmp_path):
    boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run"))
    assert AR.census_inbox("r", kernel_rnd=_kr_with_inbox(tmp_path, present=False), run=boom) == "-"


def test_census_inbox_runs_the_module_against_the_live_census_and_store(tmp_path):
    seen = []

    def fake(argv, **kw):
        seen.append((argv, kw))
        return type("R", (), {"stdout": 'BW-INBOX {"written": 2}', "stderr": "", "returncode": 0})()

    out = AR.census_inbox("r", kernel_rnd=_kr_with_inbox(tmp_path), state="/s", store="/st", run=fake)
    argv, kw = seen[0]
    assert out == 'BW-INBOX {"written": 2}' and "autokernel.loop.census_inbox" in argv
    assert argv[argv.index("--census") + 1] == "/s/mi210_bandwidth_census.json" and argv[argv.index("--store") + 1] == "/st"
    assert kw["cwd"].endswith("kr")


def test_inbox_follows_the_census_step_and_never_fails_the_runend(tmp_path):
    flags = _row(tmp_path, "ak-x-op-gpu-20261122", {"complete": True, "verdict": "OP_PASS"})
    got = []
    rep = AR.handle("ak-x-op-gpu-20261122", flags, notify_mod=FakeNotify(), census=lambda r, p: "BW-CENSUS {}",
                    inbox=lambda r: got.append(r) or "BW-INBOX {}")
    assert got == ["ak-x-op-gpu-20261122"] and AR.line(rep).endswith("inbox=BW-INBOX {}")
    bad = AR.handle("ak-x-op-gpu-20261122", flags, notify_mod=FakeNotify(), census=lambda r, p: "BW-CENSUS {}",
                    inbox=lambda r: 1 / 0)
    assert bad["inbox"].startswith("error ZeroDivisionError") and bad["class"]["side"]  # the run-end still completed
    got.clear()
    AR.handle("ak-x-op-gpu-20261122", flags, notify_mod=FakeNotify(), census=lambda r, p: "-", inbox=got.append)
    AR.handle("ak-x-op-gpu-20261122", flags, notify_mod=FakeNotify(), census=lambda r, p: "BW-CENSUS {}")  # injected census: live store untouched
    assert got == []


# ---- FX1: registry from origin/main, inbox state file the hub reads, path-gates report -------------------------------

def _ok(out="BW-INBOX {}"):
    return type("R", (), {"stdout": out, "stderr": "", "returncode": 0})()


def test_census_steps_get_the_origin_main_registry_in_their_env(tmp_path):
    kr = tmp_path / "kr"
    (kr / "autokernel" / "loop").mkdir(parents=True)
    (kr / "autokernel" / "loop" / "census_inbox.py").write_text("# RSL-R2\n")
    (kr / "autokernel" / "loop" / "census_update.py").write_text("# x\n")
    res = tmp_path / "r.json"
    res.write_text("{}")
    st = tmp_path / "state"
    st.mkdir()
    (st / "mi210_bandwidth_census.json").write_text("{}")
    seen = []

    def fake(argv, **kw):
        seen.append(kw.get("env"))
        return _ok()

    AR.census_update("r", str(res), kernel_rnd=str(kr), state=str(st), run=fake, registry="/x/reg.yaml")
    AR.census_inbox("r", kernel_rnd=str(kr), state=str(st), run=fake, registry="/x/reg.yaml")
    assert [e["EPYC_ORCH_REGISTRY"] for e in seen] == ["/x/reg.yaml", "/x/reg.yaml"]
    seen.clear()
    AR.census_inbox("r", kernel_rnd=str(kr), state=str(st), run=fake)    # injected run + no registry: no clone is touched
    assert seen == [None]


def test_registry_snapshot_is_git_show_of_origin_main_not_the_working_tree(tmp_path):
    calls = []

    def fake(argv, **kw):
        calls.append(argv)
        if "rev-parse" in argv:
            return type("R", (), {"stdout": "c0ffee\n", "stderr": "", "returncode": 0})()
        if "show" in argv:
            return type("R", (), {"stdout": b"server_mode: {}\n", "stderr": b"", "returncode": 0})()
        return _ok("")

    p = AR.registry_snapshot(repo="/orch", cache=str(tmp_path), run=fake)
    assert p == str(tmp_path / "c0ffee" / "model_registry.yaml") and open(p).read() == "server_mode: {}\n"
    show = next(a for a in calls if "show" in a)
    assert show[-1] == "c0ffee:orchestration/model_registry.yaml"
    n = len(calls)
    assert AR.registry_snapshot(repo="/orch", cache=str(tmp_path), run=fake) == p     # cached per commit: no second show
    assert not any("show" in a for a in calls[n:])

    def boom(argv, **kw):
        raise OSError("no git")
    assert AR.registry_snapshot(repo="/orch", cache=str(tmp_path / "other"), run=boom) is None   # fail-soft


def test_census_inbox_reports_a_nonzero_exit_as_an_error(tmp_path):
    bad = lambda argv, **kw: type("R", (), {"stdout": "BW-INBOX {}", "stderr": "x", "returncode": 3})()
    out = AR.census_inbox("r", kernel_rnd=_kr_with_inbox(tmp_path), state="/s", store="/st", run=bad)
    assert out.startswith("error rc=3")
    assert AR.inbox_status(out) == "error" and AR.inbox_status("-") == "absent" and AR.inbox_status("BW-INBOX {}") == "ok"
    assert AR.inbox_status("error ZeroDivisionError: x") == "error" and AR.inbox_status("") == "error"


def test_inbox_outcome_is_written_where_the_hub_reads_it(tmp_path):
    flags = _row(tmp_path, "ak-x-op-gpu-20261122", {"complete": True, "verdict": "OP_PASS"})
    st = tmp_path / "state"
    AR.handle("ak-x-op-gpu-20261122", flags, notify_mod=FakeNotify(), census=lambda r, p: "BW-CENSUS {}",
              inbox=lambda r: 1 / 0, state=str(st), gates=lambda r: "paths=0")
    rec = json.load(open(st / "inbox-state.json"))
    assert (rec["status"], rec["row"]) == ("error", "ak-x-op-gpu-20261122") and rec["detail"].startswith("error ZeroDivisionError")
    AR.handle("ak-x-op-gpu-20261122", flags, notify_mod=FakeNotify(), census=lambda r, p: "BW-CENSUS {}",
              inbox=lambda r: "BW-INBOX {}", state=str(st))
    assert json.load(open(st / "inbox-state.json"))["status"] == "ok"
    # the hub's reader sees exactly what the hook wrote
    sys.path.insert(0, os.path.normpath(os.path.join(_COORD, "..", "..")))
    from dashboard import bw_census
    assert bw_census.read_inbox_state(st / "mi210_bandwidth_census.json")["status"] == "ok"


def _failed():
    return {"status": AR.REGISTRY_FAILED, "path": None, "commit": None}


def test_failed_registry_snapshot_is_named_and_no_registry_env_is_passed(tmp_path, monkeypatch):
    """N9: a failed origin/main extract is NOT a silent fallback: the child gets an EPYC_ORCH_REGISTRY that cannot exist (an inherited one is
    stripped too) and the failure is recorded on the census line and in path-gates.json."""
    monkeypatch.setenv("EPYC_ORCH_REGISTRY", "/shared/working-tree/model_registry.yaml")
    monkeypatch.setattr(AR, "registry_snapshot", lambda *a, **k: None)
    assert AR._registry_resolve(None, live=True) == _failed()
    bad = AR._env_for(_failed())["EPYC_ORCH_REGISTRY"]
    assert bad.startswith("/nonexistent/") and not os.path.exists(bad)  # never the inherited shared working tree
    assert AR._registry_env(None, live=True)["EPYC_ORCH_REGISTRY"].startswith("/nonexistent/")
    kr = tmp_path / "kr"
    (kr / "autokernel" / "loop").mkdir(parents=True)
    (kr / "autokernel" / "loop" / "census_update.py").write_text("# x\n")
    (kr / "autokernel" / "loop" / "stage_bodies.py").write_text("# x\n")
    res = tmp_path / "r.json"
    res.write_text("{}")
    st = tmp_path / "state"
    st.mkdir()
    (st / "mi210_bandwidth_census.json").write_text("{}")
    seen = []

    def fake(argv, **kw):
        seen.append(kw.get("env"))
        return type("R", (), {"stdout": "BW-CENSUS ok\n" if "census_update" in " ".join(argv) else json.dumps({"p|cpu": {}}),
                              "stderr": "", "returncode": 0})()

    monkeypatch.setattr(AR, "_registry_resolve", lambda registry, live=True: _failed())
    line = AR.census_update("r", str(res), kernel_rnd=str(kr), state=str(st), run=fake)
    assert line.startswith("BW-CENSUS") and AR.REGISTRY_FAILED in line     # the BW-CENSUS prefix the inbox gate keys on survives
    assert AR.path_gates(kernel_rnd=str(kr), state=str(st), run=fake, now=1.0).endswith(f"[{AR.REGISTRY_FAILED}]")
    assert all(e["EPYC_ORCH_REGISTRY"].startswith("/nonexistent/") for e in seen) and len(seen) == 2
    d = json.load(open(st / "path-gates.json"))
    assert d["registry"] == {"status": AR.REGISTRY_FAILED, "commit": None, "path": None}
    import flow_status as FS
    assert FS.read_path_gates(str(st / "path-gates.json"))["registry"]["status"] == AR.REGISTRY_FAILED


def test_path_gates_records_the_registry_commit_used(tmp_path, monkeypatch):
    snap = {"status": "snapshot", "path": "/c/e6f33a2b/model_registry.yaml", "commit": "e6f33a2b"}
    monkeypatch.setattr(AR, "_registry_resolve", lambda registry, live=True: snap)
    kr = tmp_path / "kr"
    (kr / "autokernel" / "loop").mkdir(parents=True)
    (kr / "autokernel" / "loop" / "stage_bodies.py").write_text("# x\n")
    seen = []

    def fake(argv, **kw):
        seen.append(kw.get("env"))
        return type("R", (), {"stdout": json.dumps({"p|cpu": {}}), "stderr": "", "returncode": 0})()

    assert AR.path_gates(kernel_rnd=str(kr), state=str(tmp_path / "st"), run=fake, now=1.0) == "paths=1"
    d = json.load(open(tmp_path / "st" / "path-gates.json"))
    assert d["registry"]["commit"] == "e6f33a2b" and d["registry"]["status"] == "snapshot"
    assert seen[0]["EPYC_ORCH_REGISTRY"] == "/c/e6f33a2b/model_registry.yaml"
    assert AR.registry_commit("/mnt/x/cache/abc123/model_registry.yaml") == "abc123" and AR.registry_commit(None) is None


def test_path_gates_report_is_written_and_failures_are_recorded(tmp_path):
    kr = tmp_path / "kr"
    (kr / "autokernel" / "loop").mkdir(parents=True)
    (kr / "autokernel" / "loop" / "stage_bodies.py").write_text("# x\n")
    st = tmp_path / "st"
    rep = {"27b-q8_0|mi210": {"status": "live", "device": "mi210", "timing": "cell", "quality": "gated", "op_perf": "floored"}}
    ok = lambda argv, **kw: type("R", (), {"stdout": "noise\n" + json.dumps(rep), "stderr": "", "returncode": 0})()
    assert AR.path_gates(kernel_rnd=str(kr), state=str(st), run=ok, now=7.0) == "paths=1"
    assert json.load(open(st / "path-gates.json"))["report"] == rep
    bad = lambda argv, **kw: type("R", (), {"stdout": "", "stderr": "registry unreadable", "returncode": 1})()
    assert AR.path_gates(kernel_rnd=str(kr), state=str(st), run=bad, now=8.0).startswith("error")
    d = json.load(open(st / "path-gates.json"))
    assert "report" not in d and "registry unreadable" in d["error"]     # no stale all-gated report survives a failure
    import flow_status as FS
    assert FS.read_path_gates(str(st / "path-gates.json"))["present"] is False


def test_watch_rows_routes_plain_ak_rows_to_the_hook_and_keeps_gate_eval():
    wr = open(os.path.normpath(os.path.join(_COORD, "..", "..", ".claude", "skills", "row-owner-loop", "scripts",
                                            "watch_rows.sh"))).read()
    arm = wr[wr.index("ak-*|akx-*)"):wr.index("        *)\n")]
    assert "ak_runend.py" in arm and "--gate-eval" in arm        # the hook AND what the `*)` arm gave ak-* rows
    assert wr.index("akc-*|") < wr.index("ak-*|akx-*)") < wr.index("        *)\n")   # ordered before the catch-all



def test_research_snapshot_includes_scripts_lib_for_path_gates(tmp_path):
    """path-gates (stage_bodies.coverage_report) imports scripts/lib/canonical_recipe.py: the snapshot must carry it."""
    import subprocess
    repo = tmp_path / "repo"
    (repo / "scripts/kernel_rnd/autokernel/lineage").mkdir(parents=True)
    (repo / "scripts/kernel_rnd/autokernel/lineage/__init__.py").write_text("")
    (repo / "scripts/lib").mkdir(parents=True)
    (repo / "scripts/lib/canonical_recipe.py").write_text("X = 1\n")
    (repo / "scripts/benchmark").mkdir(parents=True)
    (repo / "scripts/benchmark/__init__.py").write_text("")
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
    g("init", "-q", "-b", "main"); g("add", "-A")
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x")
    g("update-ref", "refs/remotes/origin/main", "HEAD")
    kr = AR.research_snapshot(repo=str(repo), ref="origin/main", cache=str(tmp_path / "cache"))
    root = os.path.dirname(os.path.dirname(kr))
    assert os.path.isfile(os.path.join(root, "scripts", "lib", "canonical_recipe.py"))
    assert os.path.isdir(os.path.join(kr, "autokernel", "lineage"))
    assert os.path.isfile(os.path.join(root, "scripts", "benchmark", "__init__.py"))
