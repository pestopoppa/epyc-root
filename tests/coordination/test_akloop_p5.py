"""P5 tests: handback_verify (a) and failclass (b). All git/flags state is a throwaway tmp tree."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts", "coordination", "akloop"))
import failclass as fc  # noqa: E402
import handback_verify as hv  # noqa: E402


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t"})


@pytest.fixture
def world(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(origin), str(repo)], check=True, capture_output=True)
    (repo / "h.md").write_text("- [x] TASK-1 done [belief: cc]\n- [x] TASK-2 done\n- [ ] TASK-3\n")
    git(repo, "add", "h.md")
    git(repo, "commit", "-qm", "c1")
    git(repo, "push", "-q", "origin", "HEAD:main")
    git(repo, "fetch", "-q", "origin")
    pushed = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    git(repo, "checkout", "-qb", "feat")
    (repo / "x").write_text("x")
    git(repo, "add", "x")
    git(repo, "commit", "-qm", "c2")
    local = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    flags = tmp_path / "flags"
    for d in ("ready", "dryrun", "filing-done"):
        (flags / d).mkdir(parents=True)
    return hv.Ctx(str(repo), str(flags)), pushed, local, flags


def one(ctx, **c):
    return hv.verify([c], ctx)["results"][0]


def test_pushed_true_and_false(world):
    ctx, pushed, local, _ = world
    assert one(ctx, type="pushed", sha=pushed)["ok"]
    r = one(ctx, type="pushed", sha=local)
    assert not r["ok"] and "not on origin/main" in r["detail"]
    assert not one(ctx, type="pushed", sha="deadbeefdead")["ok"]


def test_pushed_branch_with_unpushed_commits(world):
    ctx, pushed, _, _ = world
    r = one(ctx, type="pushed", sha=pushed, branch="feat")
    assert not r["ok"] and "unpushed" in r["detail"]


def test_branch_contains(world):
    ctx, pushed, local, _ = world
    assert one(ctx, type="branch_contains", branch="feat", sha=pushed)["ok"]
    assert not one(ctx, type="branch_contains", branch="main", sha=local)["ok"]


def test_published_filed_and_missing(world):
    ctx, _, _, flags = world
    assert not one(ctx, type="published", id="row-x-20261121")["ok"]
    (flags / "ready" / "row-x-20261121.json").write_text("{}")
    assert one(ctx, type="published", id="row-x-20261121")["ok"]
    assert not one(ctx, type="filed", id="row-x-20261121")["ok"]
    (flags / "filing-done" / "row-x-20261121.FILED").write_text("")
    assert one(ctx, type="filed", id="row-x-20261121")["ok"]


def test_smoke_pass_requires_pass_newer_than_publish(world):
    ctx, _, _, flags = world
    rid = "row-s-20261121"
    d = flags / "dryrun" / rid
    d.mkdir()
    (flags / "ready" / f"{rid}.json").write_text("{}")
    (d / "launcher.out").write_text("==== dry run 2026 regions=0-3\n==== dry run PASS: first progress: x\n")
    assert not one(ctx, type="smoke_pass", id=rid)["ok"]          # no PASS.json
    (d / "PASS.json").write_text("{}")
    os.utime(d / "PASS.json", (time.time() - 100, time.time() - 100))
    assert not one(ctx, type="smoke_pass", id=rid)["ok"]          # older than publish
    os.utime(d / "PASS.json", None)
    assert one(ctx, type="smoke_pass", id=rid)["ok"]
    (d / "launcher.out").write_text("==== dry run PASS: a\n==== dry run FAIL: later\n")
    assert not one(ctx, type="smoke_pass", id=rid)["ok"]          # LAST verdict line wins


def test_built_symbol_is_content_not_mtime(world, tmp_path):
    ctx = world[0]
    lib = tmp_path / "lib.so"
    lib.write_bytes(b"\x00GGML_FIX_KNOB\x00")
    assert one(ctx, type="built", lib=str(lib), symbol="GGML_FIX_KNOB")["ok"]
    assert not one(ctx, type="built", lib=str(lib), symbol="GGML_OTHER")["ok"]


def test_ticked_needs_x_and_belief(world):
    ctx = world[0]
    assert one(ctx, type="ticked", id="TASK-1", file="h.md")["ok"]
    assert "belief" in one(ctx, type="ticked", id="TASK-2", file="h.md")["detail"]
    assert not one(ctx, type="ticked", id="TASK-3", file="h.md")["ok"]
    assert not one(ctx, type="ticked", id="TASK-9", file="h.md")["ok"]


def test_tests_log_and_rerun(world, tmp_path):
    ctx = world[0]
    good, bad = tmp_path / "good.log", tmp_path / "bad.log"
    good.write_text("==== 12 passed in 1.0s ====")
    bad.write_text("==== 1 failed, 11 passed in 1.0s ====")
    assert one(ctx, type="tests", log=str(good))["ok"]
    assert not one(ctx, type="tests", log=str(bad))["ok"]
    assert not one(ctx, type="tests", log=str(good), expect_passed=99)["ok"]
    assert not one(ctx, type="tests")["ok"]                       # nothing to prove it
    assert not one(ctx, type="tests", cmd="echo '3 passed'")["ok"]  # no --rerun
    ctx.rerun = True
    assert one(ctx, type="tests", cmd="echo '3 passed'")["ok"]
    assert not one(ctx, type="tests", cmd="echo '3 passed 1 failed'; exit 1")["ok"]


def test_stamp_semantics(world):
    ctx, pushed, local, _ = world
    assert hv.verify([], ctx)["stamp"] == "UNVERIFIED"           # vacuous is not verified
    assert hv.verify([{"type": "pushed", "sha": pushed}], ctx)["stamp"] == "VERIFIED"
    s = hv.verify([{"type": "pushed", "sha": pushed}, {"type": "pushed", "sha": local}], ctx)
    assert s["stamp"] == "UNVERIFIED" and "1 of 2" in s["reason"]
    assert hv.verify([{"type": "nonsense"}], ctx)["stamp"] == "UNVERIFIED"


def test_text_extraction_and_cli(world, tmp_path, capsys):
    ctx, pushed, local, flags = world
    t = tmp_path / "hb.md"
    t.write_text(f"Done.\npushed `{pushed}` to main\nfiled row-q-20261121\nirrelevant prose\n")
    claims = hv.extract_claims(t.read_text())
    assert [c["type"] for c in claims] == ["pushed", "filed"]
    rc = hv.main(["--text", str(t), "--repo", ctx.repo, "--flags", str(flags), "--json-out", str(tmp_path / "s.json")])
    assert rc == 1                                               # the filed claim is false
    assert json.load(open(tmp_path / "s.json"))["stamp"] == "UNVERIFIED"
    (flags / "filing-done" / "row-q-20261121.FILED").write_text("")
    assert hv.main(["--text", str(t), "--repo", ctx.repo, "--flags", str(flags)]) == 0
    cj = tmp_path / "c.json"
    cj.write_text(json.dumps({"claims": [{"type": "pushed", "sha": pushed}]}))
    assert hv.main(["--claims", str(cj), "--repo", ctx.repo]) == 0
    cj.write_text("{not json")
    assert hv.main(["--claims", str(cj)]) == 2


# ------------------------------------------------------------------ failclass
def fail(reason, tail=()):
    return {"id": "row-1", "reason": reason, "launcher_out_tail": list(tail)}


@pytest.mark.parametrize("reason,side,klass", [
    ("admission refused the armed poller: refuse rc=12: not ready: precond-cmd failed", "harness", "admission_refused"),
    ("poller did not log 'launcher up pid=' within 60 s of arming", "harness", "launcher_not_started"),
    ("GPU row produced a unit but VRAM never showed residency (max 0 B sampled)", "harness", "residency_unproven"),
    ("job ended rc=5 time=x reason=build-missing::18183 already in use after 5s", "harness", "build_missing"),
    ("job ended rc=? (no ended record) after 9s", "harness", "no_ended_record"),
])
def test_fail_reason_rules(reason, side, klass):
    c = fc.classify_fail(fail(reason))
    assert (c.side, c.klass) == (side, klass) and c.rule and c.row_id == "row-1"


def test_job_rc_uses_launcher_text():
    r = "job ended rc=1 reason=job-rc-1:exited after 48s, before its first progress"
    assert fc.classify_fail(fail(r, ["ServerDied: HTTP Error 500"])).side == "harness"
    comp = fc.classify_fail(fail(r, ["src/ggml.c:12: error: expected ';'"]))
    assert (comp.side, comp.klass) == ("candidate", "compile")
    assert fc.classify_fail(fail(r, ["REJECT_CORRECTNESS on MUL_MAT"])).klass == "correctness_gate"
    unk = fc.classify_fail(fail(r, ["smoke rc=-11 cases=0"]))
    assert unk.side == "unknown"                                 # no evidence -> no guess


def test_launcher_text_file_argument():
    r = "job ended rc=1 reason=job-rc-1:exited after 4s, before its first progress"
    assert fc.classify_fail(fail(r), "Permission denied: /x").klass == "job_script_error"


@pytest.mark.parametrize("res,side,klass", [
    ({"verdict": "PASS(unique_ids, neutral)"}, "ok", "pass"),
    ({"verdict": "KEEP"}, "ok", "keep"),
    ({"verdict": "REJECT_CORRECTNESS"}, "candidate", "correctness_gate"),
    ({"verdict": "DROP(op)"}, "candidate", "timing_loss"),
    ({"verdict": "FAIL(dup_ids)"}, "candidate", "correctness_gate"),
    ({"verdict": "INCONCLUSIVE(fa_drop in [0.1])", "status": "complete"}, "candidate", "noise"),
    ({"verdict": "FAIL_FOREIGN_LOAD"}, "harness", "instrument_noise"),
    ({"verdict": "FUTILITY_NOISY_NOT_REGISTERED"}, "harness", "instrument_noise"),
    ({"status": "complete"}, "ok", "complete"),
    ({"verdict": "SOMETHING_NEW", "status": "complete"}, "unknown", "unrecognised_verdict"),
    ({"complete": False}, "harness", "incomplete_run"),
    ({"correct": False}, "candidate", "correctness_gate"),
])
def test_result_rules(res, side, klass):
    c = fc.classify_result(res)
    assert (c.side, c.klass) == (side, klass)


def test_result_not_a_dict():
    assert fc.classify_result([1]).side == "unknown"


def test_fallback_is_interface_only_and_unwired():
    assert fc._FALLBACK is None                                  # nothing registers one
    assert fc.classify_fail(fail("something novel")).side == "unknown"

    class Fb(fc.FallbackClassifier):
        def classify(self, payload):
            return fc.Classification("harness", "model_says", "m")

    fc.set_fallback(Fb())
    try:
        c = fc.classify_fail(fail("something novel"))
        assert (c.side, c.rule) == ("harness", "fallback:m")
        assert fc.classify_fail(fail("admission refused")).rule == "reason:admission"   # rules still win
        assert fc.classify_result({"verdict": "KEEP"}).side == "ok"
    finally:
        fc.set_fallback(None)


def test_broken_fallback_cannot_break_rules():
    class Boom(fc.FallbackClassifier):
        def classify(self, payload):
            raise RuntimeError("x")
    fc.set_fallback(Boom())
    try:
        assert fc.classify_fail(fail("something novel")).side == "unknown"
    finally:
        fc.set_fallback(None)


def test_route_only_harness_goes_to_pipeline_inbox(tmp_path, monkeypatch):
    monkeypatch.delenv("ROWFLOW_BUS_ROOT", raising=False)
    flags = str(tmp_path)
    h = fc.classify_fail(fail("admission refused the armed poller: refuse rc=12"))
    m = fc.route(h, flags)
    assert m and m["record"]["kind"] == "ak-harness-failure" and m["record"]["row_owner"] == "pipeline-mgmt"
    lines = (tmp_path / "rowflow-alerts.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["detail"]["klass"] == "admission_refused"
    fc.route(h, flags)                                           # idempotent
    assert len((tmp_path / "rowflow-alerts.jsonl").read_text().splitlines()) == 1
    assert str(m["bus"]).startswith("skipped:")                  # scratch flags never post to the fleet bus
    for c in (fc.classify_result({"verdict": "KEEP"}), fc.classify_result({"verdict": "DROP"}),
              fc.classify_fail(fail("novel"))):
        assert fc.route(c, flags) is None
    assert len((tmp_path / "rowflow-alerts.jsonl").read_text().splitlines()) == 1


def test_cli_fail_and_result(tmp_path, capsys):
    p = tmp_path / "FAIL-1.json"
    p.write_text(json.dumps(fail("poller did not log 'launcher up pid='")))
    assert fc.main(["--fail", str(p)]) == 1
    assert json.loads(capsys.readouterr().out)["klass"] == "launcher_not_started"
    r = tmp_path / "RESULT.json"
    r.write_text(json.dumps({"verdict": "KEEP"}))
    assert fc.main(["--result", str(r)]) == 0
