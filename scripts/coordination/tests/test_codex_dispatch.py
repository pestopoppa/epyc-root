"""PM-CODEX-DISPATCH-DETERMINISTIC: the `codex` lane type of taskflow/dispatch.py (harness/codex.py).

A fake `codex` binary stands in for the lane; everything else (drive.py resume loop, sparse lane worktree, artifact
verdict, dispatcher test re-run) runs for real against a throwaway origin + clone.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
from taskflow.harness import codex as CX  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import os, re, subprocess, sys, json
args = sys.argv[1:]
prompt = sys.stdin.read()
print(json.dumps({"type": "thread.started", "thread_id": "T1"}).replace(" ", ""))
if "resume" in args:
    sys.exit(0)
mode = os.environ["FAKE_MODE"]
wt = re.search(r"your worktree (\S+) \(branch (\S+),", prompt)
wt, lane = wt.group(1), wt.group(2)
report = re.search(r"Then write (\S+) with EXACTLY", prompt).group(1)
box = re.search(r"^Task (\S+) ", prompt, re.M).group(1)
repo = os.environ["FAKE_REPO"]
if mode == "blocked":
    open(report, "w").write("LANE-STATUS: BLOCKED `foo.py` raises KeyError\n")
    sys.exit(0)
if mode == "textonly":
    open(report, "w").write(f"LANE-STATUS: DONE\n{box} {repo} {lane} {'a' * 40}\nTEST: python3 -m pytest -q t_ok.py\n1 passed\nPUSH VERIFIED\n")
    sys.exit(0)
open(os.path.join(wt, "t_ok.py"), "w").write("def test_ok():\n    assert True\n")
g = lambda *a: subprocess.run(["git", "-C", wt, *a], check=True, capture_output=True, text=True).stdout.strip()
g("add", "t_ok.py"); g("-c", "user.name=f", "-c", "user.email=f@x", "commit", "-qm", "lane work")
g("push", "-q", "origin", "HEAD:main")
sha = g("rev-parse", "HEAD")
open(report, "w").write(f"LANE-STATUS: DONE\n{box} {repo} {lane} {sha}\nTEST: nice -n 19 taskset -c 84-87 python3 -m pytest -q t_ok.py\n1 passed\nPUSH VERIFIED — origin/main carries HEAD\n")
'''


def _git(*a, cwd=None):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def env(tmp_path, monkeypatch):
    origin = tmp_path / "origin.git"
    _git("init", "-q", "--bare", "-b", "main", str(origin))
    clone = tmp_path / "clone"
    _git("clone", "-q", str(origin), str(clone))
    (clone / "README").write_text("x\n")
    _git("add", "README", cwd=clone)
    _git("-c", "user.name=f", "-c", "user.email=f@x", "commit", "-qm", "init", cwd=clone)
    _git("push", "-q", "origin", "HEAD:main", cwd=clone)
    _git("fetch", "-q", "origin", cwd=clone)
    root = tmp_path / "root"
    (root / "handoffs/active/briefs").mkdir(parents=True)
    for b in ("BX-1", "BX-2", "BX-3"):
        (root / f"handoffs/active/briefs/{b}.md").write_text(f"brief for {b}\n")
    (root / "handoffs/active/churn-pipeline.md").write_text("# Handoff\n")
    fake = tmp_path / "codex"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    wt_root = tmp_path / "wt"
    wt_root.mkdir()
    monkeypatch.setattr(CX, "WT_ROOT", wt_root)
    monkeypatch.setenv("FAKE_REPO", str(clone))
    return {"root": root, "clone": clone, "fake": str(fake), "out": tmp_path / "out", "wt": wt_root}


def rec(bid, **kw):
    r = {"id": bid, "state": "open", "class": "non-inference", "file": "handoffs/active/churn-pipeline.md", "line": 10,
         "text": f"- [ ] **{bid}** [non-inference] do the thing", "done_when": "it is done", "brief": "unverified",
         "holds": [], "gate": [], "gate_open": False, "gate_unknown": [], "inputs_missing": [], "lint": {"ok": True},
         "needs_brief": False, "needs_owner": False, "frozen_until": None, "outside_backlog": False,
         "proposed_by": None, "row_rank": 1, "pos_in_backlog": 1}
    r.update(kw)
    return r


def doc(*recs):
    return {"holds_source": "handoffs/active/holds.yaml", "boxes": {r["id"]: r for r in recs}}


def go(e, d, mode, monkeypatch, **kw):
    monkeypatch.setenv("FAKE_MODE", mode)
    calls = {"tick": [], "tag": [], "remove": []}
    hooks = {"tick": lambda r, v, *a: calls["tick"].append(r["id"]) or {"ticked": True, "detail": "WRAPPED x"},
             "tag": lambda r, why, *a: calls["tag"].append((r["id"], why)) or {"tagged": True},
             "remove": lambda repo, wt: calls["remove"].append(str(wt)) or {"removed": True},
             "already_done": lambda r: False}
    hooks.update(kw.pop("hooks", {}))
    rows = CX.dispatch(root=e["root"], root_repo=e["clone"], out=e["out"], files=("handoffs/active/churn-pipeline.md",),
                       doc=d, codex=e["fake"], max_rounds=2, apply=True, hooks=hooks, repos={"r": str(e["clone"])}, **kw)
    return rows, calls


# ------------------------------------------------------------------------------------------------- eligibility
@pytest.mark.parametrize("kw,why", [
    ({"state": "frozen", "frozen_until": "X"}, "state-frozen"),
    ({"state": "needs-owner", "needs_owner": True}, "state-needs-owner"),
    ({"holds": ["H1"]}, "held"),
    ({"gate_open": True}, "gate-open"),
    ({"gate_unknown": ["Q"]}, "gated"),
    ({"class": "inference"}, "class-inference"),
    ({"class": "operator-decision"}, "class-operator-decision"),
    ({"done_when": ""}, "no-done-when"),
    ({"brief": "none"}, "no-brief"),
    ({"text": "- [ ] **BX-1** [non-inference] needs an operator-decision first"}, "operator-decision"),
])
def test_eligibility_filter(env, kw, why):
    assert CX.codex_skip(rec("BX-1", **kw), env["root"]) == why
    assert CX.codex_skip(rec("BX-1"), env["root"]) is None


LIVE_DONE_WHENS = {
    "AKPL-P0": "≥30 iterations of stage timings and a per-`unit_key` estimate table exist and `row_scaffold.py` can consume it (AK-TAIL-SPLIT GO/NO-GO data is a by-product).",
    "AKPL-P1": "replay agreement ≥95% with every disagreement explained; new rows file with zero LLM turns.",
    "PM-REPLAN-C-SOAK": 'a soak report shows 7 shadow days meeting all six criteria of docs/design/rowflow-replanning-scheduler.md section 11, and rowflow.py on origin/main has REPLAN_MODE = "enforce" with the live keeper start time after that deploy',
    "TF-R8G-REFUSAL-HINT": "a test shows a denied worker shell command returns text naming orch-py.sh -m pytest, orch-py.sh -c and rm/mv of untracked lane files, and the next canary's events show that text; code on origin/main",
    "PM-SMOKE-ENFORCE-REENABLE": "rowflow.py on origin/main has SMOKE_MEASURE_ENFORCE = True and is deployed live with zero queued rows failing SMOKE-NO-MEASURE",
}


@pytest.mark.parametrize("bid", sorted(LIVE_DONE_WHENS))
def test_live_observation_skipped(env, bid):
    why = CX.codex_skip(rec("BX-1", done_when=LIVE_DONE_WHENS[bid]), env["root"])
    assert why and why.startswith("needs-live-observation:")


def test_live_observation_names_pattern_word_bounded_case_insensitive(env):
    assert CX.codex_skip(rec("BX-1", done_when="A SOAK passes"), env["root"]) == "needs-live-observation:soak"
    assert CX.codex_skip(rec("BX-1", done_when="the alive-check module is renamed"), env["root"]) is None
    assert CX.live_observation_match(rec("BX-1", done_when=">=30 iterations of stage timings"))
    assert CX.live_observation_match(rec("BX-1", done_when="replay agreement >=95%"))


def _brief(env, bid, where=None, approach="x"):
    w = "".join(f"- {x}\n" for x in (where or []))
    (env["root"] / f"handoffs/active/briefs/{bid}.md").write_text(
        f"---\nid: {bid}\n" + (f"where:\n{w}" if where else "") + f"approach: '{approach}'\n---\n")


def test_real_handoff_edit_boxes_skipped(env):
    _brief(env, "TF-DUPID-HS4", ["handoffs/active/harness-program.md", "scripts/handoffs/box_index.py"])
    r = rec("TF-DUPID-HS4", text="- [ ] **TF-DUPID-HS4** [non-inference] Resolve the duplicate box ID HS-4 (x3 occurrences) in harness-program: give each a unique ID and fix gate references.", done_when="box_index reports no duplicate id HS-4")
    assert CX.codex_skip(r, env["root"]).startswith("needs-handoff-edit:id:")
    _brief(env, "TF-ACCEPT-CD-CLEANUP", ["scripts/handoffs/task_lint_core.py", "scripts/handoffs"], "run it over committed briefs")
    r = rec("TF-ACCEPT-CD-CLEANUP", text="- [ ] **TF-ACCEPT-CD-CLEANUP** [non-inference] Deterministic cleanup of `cd X &&` acceptances in box briefs: rewrite to worktree-relative commands (86 committed + 56 uncommitted briefs fail rule f).", done_when="task_lint reports zero rule-f failures across committed briefs and a test trips the rewriter")
    assert CX.codex_skip(r, env["root"]).startswith("needs-handoff-edit:bulk:")
    _brief(env, "BX-1", ["handoffs/active/x.md"])
    assert CX.codex_skip(rec("BX-1"), env["root"]).startswith("needs-handoff-edit:where:")


def test_handoff_citing_scripts_box_not_skipped(env):
    _brief(env, "BX-1", ["scripts/foo/bar.py"])
    r = rec("BX-1", text="- [ ] **BX-1** [non-inference] fix the parser; context in handoffs/active/churn-pipeline.md and fix ids there are NOT in scope")
    assert CX.codex_skip(r, env["root"]) is None


def test_no_where_needs_edit_text(env):
    assert CX.codex_skip(rec("BX-1", text="- [ ] **BX-1** [non-inference] see handoffs/active/x.md for context, add a helper"), env["root"]) is None
    assert CX.codex_skip(rec("BX-1", text="- [ ] **BX-1** [non-inference] rename the rows in handoffs/active/x.md"), env["root"]).startswith("needs-handoff-edit:text:")


def test_pytest_done_when_not_skipped(env):
    dw = "nice -n 19 python3 -m pytest scripts/x/tests/test_y.py passes against the live fixture"
    assert CX.codex_skip(rec("BX-1", done_when=dw), env["root"]) is None


def test_no_brief_file_and_attempted_and_ticked(env):
    assert CX.codex_skip(rec("BX-9"), env["root"]) == "no-brief"                # brief state ok, file missing
    assert CX.codex_skip(rec("BX-1"), env["root"], {"BX-1"}) == "attempted-before"
    assert CX.codex_skip(rec("BX-1"), env["root"], base_state=lambda r: "ticked") == "box-ticked-at-origin"


def test_select_order_and_limit(env):
    chosen, hist = CX.select(doc(rec("BX-2", row_rank=2), rec("BX-1"), rec("BX-3", row_rank=3)), env["root"],
                             ("handoffs/active/churn-pipeline.md",), n=2)
    assert [k for k, _ in chosen] == ["BX-1", "BX-2"] and hist["over-limit"] == 1


def test_recent_landed_requires_box_id_in_subject_or_body(env):
    _brief(env, "BX-1", ["scripts/shared.py"])
    r = rec("BX-1")
    for msg in ("BX-1: landed", "fix\n\nWork for BX-1 in scripts/shared.py"):
        assert CX.codex_skip(r, env["root"], recent_messages=(msg,)) == "already-landed"
    for msg in ("BX-10: landed", "fix scripts/shared.py", "unrelated"):
        assert CX.codex_skip(r, env["root"], recent_messages=(msg,)) is None


def test_recent_messages_origin_main_window_and_one_log(env, monkeypatch):
    clone = env["clone"]
    old_env = dict(os.environ, GIT_AUTHOR_DATE="2000-01-01T00:00:00Z", GIT_COMMITTER_DATE="2000-01-01T00:00:00Z")
    subprocess.run(["git", "-C", str(clone), "-c", "user.name=f", "-c", "user.email=f@x", "commit",
                    "--allow-empty", "-qm", "BX-2 old"], env=old_env, check=True)
    _git("-c", "user.name=f", "-c", "user.email=f@x", "commit", "--allow-empty", "-qm", "fix", "-m", "BX-1 landed", cwd=clone)
    _git("push", "-q", "origin", "HEAD:main", cwd=clone)
    _git("-c", "user.name=f", "-c", "user.email=f@x", "commit", "--allow-empty", "-qm", "BX-3 local only", cwd=clone)
    calls = []
    real_git = CX.git
    def counting_git(repo, *args, **kwargs):
        if args[0] == "log":
            calls.append(args)
        return real_git(repo, *args, **kwargs)
    monkeypatch.setattr(CX, "git", counting_git)
    messages = CX.recent_commit_messages(clone)
    chosen, hist = CX.select(doc(rec("BX-1"), rec("BX-2"), rec("BX-3")), env["root"], n=3, recent_messages=messages)
    assert [k for k, _ in chosen] == ["BX-2", "BX-3"]
    assert hist["already-landed"] == 1 and len(calls) == 1


def test_holds_source_missing_fails_closed(env):
    assert CX.select({"boxes": {"BX-1": rec("BX-1")}}, env["root"])[0] == []


def test_test_cmd_parse():
    assert CX.test_cmd("TEST: nice -n 19 taskset -c 84-87 python3 -m pytest -q a.py — 3 passed")[1:] == ["-m", "pytest", "-q", "a.py"]
    assert CX.test_cmd("TEST: bash -c 'rm -rf /'") is None
    assert CX.test_cmd("TEST: pytest a.py; rm x") is None
    assert CX.done_when_tests({"done_when": "pytest scripts/x/test_a.py passes with y"})[-1] == "scripts/x/test_a.py"


# ----------------------------------------------------------------------------------------------- end to end
def test_done_verified_from_artifacts_and_ticked(env, monkeypatch):
    rows, calls = go(env, doc(rec("BX-1")), "done", monkeypatch)
    assert rows[0]["verdict"] == "DONE", rows[0]
    assert rows[0]["test_rc"] == 0 and calls["tick"] == ["BX-1"] and calls["tag"] == []
    assert calls["remove"] == [str(env["wt"] / f"{rows[0]['lane']}-wt")]          # lane tree removed via the gate
    led = CX.read_ledger(env["out"])
    assert led[-1]["box"] == "BX-1" and led[-1]["verdict"] == "DONE"


def test_lane_worktree_is_sparse(env, monkeypatch):
    (env["clone"] / "artifacts").mkdir()
    (env["clone"] / "artifacts" / "big").write_text("x")
    _git("add", "artifacts", cwd=env["clone"])
    _git("-c", "user.name=f", "-c", "user.email=f@x", "commit", "-qm", "a", cwd=env["clone"])
    _git("push", "-q", "origin", "HEAD:main", cwd=env["clone"])
    _git("fetch", "-q", "origin", cwd=env["clone"])
    wt = CX.sparse_worktree(env["clone"], env["wt"] / "s-wt", "s")
    assert (wt / "README").exists() and not (wt / "artifacts" / "big").exists()


def test_report_says_done_but_no_commit_on_main_is_not_done(env, monkeypatch):
    rows, calls = go(env, doc(rec("BX-1")), "textonly", monkeypatch)
    assert rows[0]["verdict"] == "NOT-DONE" and "not in" in rows[0]["why"]
    assert calls["tick"] == [] and calls["tag"][0][0] == "BX-1"


def test_old_commit_already_on_main_is_not_done(env, monkeypatch):
    head = _git("rev-parse", "HEAD", cwd=env["clone"])
    v = CX.judge(f"LANE-STATUS: DONE\nBX-1 r main {head}\nTEST: pytest -q x.py\nPUSH VERIFIED\n", "BX-1",
                 {"r": str(env["clone"])}, {str(env["clone"]): head}, rerun=lambda *a: (0, ""))
    assert not v["done"] and "before dispatch" in v["why"]


def test_failed_rerun_is_not_done(env, monkeypatch):
    rows, calls = go(env, doc(rec("BX-1")), "done", monkeypatch, hooks={"rerun": lambda *a: (1, "1 failed")})
    assert rows[0]["verdict"] == "NOT-DONE" and "rc=1" in rows[0]["why"] and calls["tick"] == []


def test_blocked_tags_needs_owner_and_never_retries(env, monkeypatch):
    rows, calls = go(env, doc(rec("BX-1")), "blocked", monkeypatch)
    assert rows[0]["verdict"] == "NOT-DONE" and calls["tag"][0][0] == "BX-1"
    assert calls["remove"]                                   # BLOCKED and clean -> lane tree removed too
    rows2, calls2 = go(env, doc(rec("BX-1")), "done", monkeypatch)
    assert rows2 == [] and calls2["tick"] == []              # ledger: attempted-before, no automatic retry


def test_tick_refused_is_recorded_box_left_open(env, monkeypatch):
    rows, _ = go(env, doc(rec("BX-1")), "done", monkeypatch,
                 hooks={"tick": lambda *a: {"ticked": False, "detail": "tick refused (done-when not met)"}})
    assert rows[0]["verdict"] == "DONE" and rows[0]["tick_refused"] is True


def test_stop_file(env, monkeypatch):
    env["out"].mkdir()
    (env["out"] / "STOP").write_text("")
    rows, calls = go(env, doc(rec("BX-1")), "done", monkeypatch)
    assert rows == [] and not CX.read_ledger(env["out"])


def test_width_cap_constant():
    assert CX.MAX_CODEX_LANES == 4 and CX.PIN[:3] == ["taskset", "-c", "84-87"] and "ionice" in CX.PIN


@pytest.mark.parametrize("term", ["scripts/coordination/rowflow/x.py", "scripts/coordination/churn/x.py",
                                  "ak_gate", "ak_row", "mk_ak_row", "publish_row", "preflight",
                                  "the keeper", "/mnt/raid0/llm/tmp/compute-flags"])
def test_live_pipeline_exclusions(env, term):
    assert CX.codex_skip(rec("BX-1", text=term), env["root"]) == "touches-live-pipeline"
    _brief(env, "BX-1", [term])
    assert CX.codex_skip(rec("BX-1"), env["root"]) == "touches-live-pipeline"


@pytest.mark.parametrize("term", ["model", "server", "GPU", "benchmark"])
def test_compute_exclusions(env, term):
    assert CX.codex_skip(rec("BX-1", text=f"requires {term}"), env["root"]) == "needs-compute"


def test_hygiene_scope_and_ownership(env):
    root = env["root"]
    (root / "handoffs/active/owned.md").write_text("# Handoff\n**Owner**: session-a\n")
    (root / "handoffs/active/unowned.md").write_text("# Handoff\n**Domain**: software\n")
    rows = [rec("BX-1", file=CX.HYGIENE_FILE), rec("BX-2", file="handoffs/active/owned.md"),
            rec("BX-3", file="handoffs/active/unowned.md")]
    chosen, _ = CX.select(doc(*rows), root, files=None, n=10, scope="hygiene")
    assert {k for k, _ in chosen} == {"BX-1", "BX-3"}
    assert CX.has_owner(rec("BX-3", file="handoffs/active/unowned.md", owner="session-b"), root)
    assert CX.has_owner(rows[1], root)


def test_width_rejected(env):
    with pytest.raises(ValueError, match="width"):
        CX.dispatch(root=env["root"], width=5)


def test_quiet_hold_grants_and_latest_idle(tmp_path):
    grants = tmp_path / "grants"
    grants.mkdir()
    grant = grants / "row.json"
    grant.write_text(json.dumps({"shape": "host", "end": "2999-01-01T00:00:00Z"}))
    assert "grant" in CX.quiet_hold(tmp_path)
    grant.write_text(json.dumps({"shape": "quiet-host", "end": "2000-01-01T00:00:00Z"}))
    assert CX.quiet_hold(tmp_path) is None
    log = tmp_path / "ws58-calendar-keeper.log"
    log.write_text("IDLE-WHY q0: WAIT row quiet-host needs 15%\n")
    assert "IDLE-WHY" in CX.quiet_hold(tmp_path)
    log.write_text(log.read_text() + "IDLE-WHY q0: no runnable row\n")
    assert CX.quiet_hold(tmp_path) is None


def test_quiet_hold_prevents_lane(env, monkeypatch, capsys):
    calls = []
    rows, _ = go(env, doc(rec("BX-1")), "blocked", monkeypatch, run_limit_s=0.01,
                 hooks={"quiet_hold": lambda flags: "quiet-host", "sleep": lambda n: calls.append(n)})
    assert not rows and calls and "QUIET-HOLD" in capsys.readouterr().out


def test_width_runs_lanes_concurrently(env, monkeypatch):
    import threading
    barrier = threading.Barrier(2, timeout=5)
    active = []
    def lane(*args):
        active.append(args[0])
        barrier.wait()
        return 0
    rows, _ = go(env, doc(rec("BX-1"), rec("BX-2")), "blocked", monkeypatch, width=2,
                 hooks={"mklane": lambda: None, "lane": lane, "quiet_hold": lambda flags: None})
    assert len(rows) == len(active) == 2


def test_owned_box_never_ticked(env, monkeypatch):
    rows, calls = go(env, doc(rec("BX-1", owner="someone")), "done", monkeypatch,
                     hooks={"quiet_hold": lambda flags: None})
    assert rows[0]["verdict"] == "DONE" and calls["tick"] == []


def test_grant_file_and_ready_manifest(tmp_path):
    (tmp_path / "grants").mkdir()
    (tmp_path / "ready").mkdir()
    (tmp_path / "grants/row.grant").write_text("end=2999-01-01T00:00Z\n")
    (tmp_path / "ready/row.json").write_text('{"shape":"host"}')
    assert "grant" in CX.quiet_hold(tmp_path)
