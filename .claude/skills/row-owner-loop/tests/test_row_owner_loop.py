import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import brief  # noqa: E402
import row_scaffold as rs  # noqa: E402
import runend  # noqa: E402


# ---------------------------------------------------------------- runend verdict mapping
def test_drop_never_pass():
    assert runend.map_verdict("DROP(FUTILITY_DECODE)", {"rc": "0", "reason": "complete"}) == "fail"
    assert runend.map_verdict("FUTILITY_ORACLE", {"rc": "0", "reason": "complete"}) == "inconclusive"
    assert runend.map_verdict("STOPPED early", {"rc": "0", "reason": "complete"}) == "inconclusive"
    assert runend.map_verdict("PASS but DROP(diagnostic)", {}) != "pass"


def test_rc75_rc143_partial_never_pass():
    for rc, reason in (("75", "partial-native-incomplete"), ("143", "killed"), ("0", "stopped")):
        assert runend.map_verdict("PASS(ops clean)", {"rc": rc, "reason": reason}) == "inconclusive"


def test_fail_and_pass():
    assert runend.map_verdict("FAIL(crash 27b: rc=-11)", {"rc": "0", "reason": "complete"}) == "fail"
    assert runend.map_verdict("PASS(ops clean)", {"rc": "0", "reason": "complete"}) == "pass"
    assert runend.map_verdict("KEEP", {}) == "pass"
    assert runend.map_verdict("", {}) == "inconclusive"
    assert runend.map_verdict("weird", {}) == "inconclusive"


def test_lint_verdict():
    assert runend.lint_verdict({"verdict": "pass", "rationale": "no numbers"}) == ["rationale cites no number"]
    errs = runend.lint_verdict({"verdict": "pass", "rationale": "DROP(diagnostic) 3 of 4"})
    assert any("DROP" in e for e in errs)
    assert runend.lint_verdict({"verdict": "fail", "rationale": "tg 0.71x at kv 32k"}) == []
    assert runend.lint_verdict({"verdict": "maybe", "rationale": "1"})


def test_parse_ended():
    e = runend.parse_ended("rc=0 time=2026-11-19T23:07:42Z reason=complete\nowner=autokernel\n")
    assert e["rc"] == "0" and e["reason"] == "complete" and e["owner"] == "autokernel"


# ---------------------------------------------------------------- row_scaffold lint
def _mkrow(tmp_path, pred_other=False, cpu_gputhr=False, threads=24, regions="0-23", seal_stale=False):
    d = tmp_path / "row-x"
    (d / "out").mkdir(parents=True)
    hf = tmp_path / "h.md"
    hf.write_text("- [ ] **BOX-1** do it. model: Qwen 27B. stop-on futility. est 1200 s\n")
    pred = f"/usr/bin/test -s {d}/out/T.json"
    if pred_other:
        pred = "/usr/bin/test -s /mnt/raid0/llm/tmp/other-row/out/T.json"
    reg = "88-95" if cpu_gputhr else regions
    spec = {"id": "row-x", "lane": "cpu", "regions": reg, "claim_cpus": reg, "estimate_s": 1200,
            "estimate_justification": "8 units x 120 s x 1.25 = 1200 s", "smoke_predicate": pred,
            "handoff_task": "h.md:BOX-1", "declared_threads": threads}
    (d / "spec.json").write_text(json.dumps(spec))
    (d / "launch.sh").write_text(f"exec x --id row-x -t {threads}\n")
    (d / "check_complete.py").write_text(f'open("{d}/out/RESULT.json")\n')
    names = ["spec.json", "launch.sh", "check_complete.py"]
    with open(d / "SOURCE.sha256", "w") as f:
        for n in names:
            f.write(hashlib.sha256((d / n).read_bytes()).hexdigest() + "  " + n + "\n")
    if seal_stale:
        (d / "launch.sh").write_text(f"exec x --id row-x -t {threads} # edited\n")
    return str(d), str(hf)


def test_lint_clean(tmp_path):
    d, hf = _mkrow(tmp_path)
    assert rs.lint(d, hf) == []


def test_lint_copied_predicate(tmp_path):
    d, hf = _mkrow(tmp_path, pred_other=True)
    errs = rs.lint(d, hf)
    assert any(e.startswith("PRED-PATH") and "other-row" in e for e in errs)


def test_lint_cpu_gpu_threads(tmp_path):
    d, hf = _mkrow(tmp_path, cpu_gputhr=True, threads=8)
    assert any(e.startswith("CPU-GPUTHR") for e in rs.lint(d, hf))


def test_lint_width(tmp_path):
    d, hf = _mkrow(tmp_path, threads=24, regions="0-71")
    assert any(e.startswith("WIDTH") for e in rs.lint(d, hf))


def test_lint_stale_seal(tmp_path):
    d, hf = _mkrow(tmp_path, seal_stale=True)
    assert any(e.startswith("SEAL") for e in rs.lint(d, hf))


def test_lint_box_fields():
    errs = rs.lint_box("- [ ] BOX-1 do it\n", "BOX-1")
    codes = {e.split(":")[0] for e in errs}
    assert codes == {"BOX-ID", "BOX-MODEL", "BOX-STOP", "BOX-EST"}


def test_lint_est_arith(tmp_path):
    d, hf = _mkrow(tmp_path)
    s = json.load(open(os.path.join(d, "spec.json")))
    s["estimate_justification"] = "about twenty minutes"
    open(os.path.join(d, "spec.json"), "w").write(json.dumps(s))
    assert any(e.startswith("EST-ARITH") for e in rs.lint(d, hf))


def test_scaffold_then_lint(tmp_path):
    hf = tmp_path / "h.md"
    hf.write_text("- [ ] **BOX-2** x. model: A3B. stop-on answer. est 1500 s\n")
    rc = rs.main(["new", "row-y", "--handoff", str(hf), "--box", "BOX-2", "--lane", "cpu", "--regions", "0-23",
                  "--threads", "24", "--units", "10", "--unit-s", "120", "--model", "model: A3B Q8_0",
                  "--root", str(tmp_path)])
    assert rc == 0
    d = tmp_path / "row-y"
    assert json.load(open(d / "spec.json"))["estimate_s"] == 1500
    assert rs.lint(str(d), str(hf)) == []
    assert rs.main(["new", "row-z", "--handoff", str(hf), "--box", "BOX-2", "--lane", "cpu", "--regions", "72-95",
                    "--threads", "24", "--units", "1", "--unit-s", "1", "--model", "m", "--root", str(tmp_path)]) == 1


def test_scaffold_defaults_to_estimate_from_history(tmp_path):
    flags = tmp_path / "flags"
    (flags / "grants").mkdir(parents=True)
    for i, w in enumerate((100, 200, 300, 400)):
        (flags / "grants" / f"fam-h-2026112{i}.ended").write_text(
            f"rc=0 time=2026-11-20T10:{w // 60:02d}:{w % 60:02d}Z reason=complete\nstarted=2026-11-20T10:00:00Z\n")
    hf = tmp_path / "h.md"
    hf.write_text("- [ ] **BOX-3** x. model: A3B. stop-on answer. est 375 s\n")
    base = ["--handoff", str(hf), "--box", "BOX-3", "--lane", "cpu", "--regions", "0-23", "--threads", "24",
            "--model", "model: A3B Q8_0", "--root", str(tmp_path), "--flags", str(flags)]
    assert rs.main(["new", "fam-h-20261130", *base]) == 0
    spec = json.load(open(tmp_path / "fam-h-20261130" / "spec.json"))
    assert spec["estimate_s"] == 375 and spec["estimate_justification"].startswith("history fam-h")
    assert not [e for e in rs.lint(str(tmp_path / "fam-h-20261130"), str(hf)) if e.startswith("EST-ARITH")]
    # no measured estimate and no history -> refused, nothing created
    assert rs.main(["new", "unknown-fam-20261130", *base]) == 1
    assert not (tmp_path / "unknown-fam-20261130").exists()


def _git(*a, cwd=None):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def test_scaffold_gpu_copies_harness_from_origin_main(tmp_path):
    hf = tmp_path / "h.md"
    hf.write_text("- [ ] **BOX-3** x. model: none. stop-on answer. est 150 s\n")
    up = tmp_path / "up"
    hp = up / "scripts/kernel_rnd/autokernel/harness"
    hp.mkdir(parents=True)
    env_id = ["-c", "user.name=t", "-c", "user.email=t@t"]
    _git("init", "-q", "-b", "main", cwd=up)
    (hp / "gpu_common.py").write_text("X = 1\n")
    (hp / "gpuproof_row.py").write_text("P = 1\n")
    _git("add", "-A", cwd=up)
    _git(*env_id, "commit", "-q", "-m", "v1", cwd=up)
    clone = tmp_path / "clone"
    _git("clone", "-q", str(up), str(clone))
    (hp / "gpu_common.py").write_text("X = 2\n")  # origin/main moves past the clone's checkout
    _git(*env_id, "commit", "-qam", "v2", cwd=up)
    head, status = _git("rev-parse", "HEAD", cwd=clone), _git("status", "--porcelain", cwd=clone)
    rc = rs.main(["new", "row-g", "--handoff", str(hf), "--box", "BOX-3", "--lane", "gpu", "--regions", "88-95,184-191",
                  "--threads", "8", "--units", "1", "--unit-s", "120", "--model", "model: none", "--root", str(tmp_path),
                  "--research-repo", str(clone)])
    assert rc == 0
    d = tmp_path / "row-g"
    assert (d / "gpu_common.py").read_text() == "X = 2\n"  # origin/main, not the clone's stale checkout
    job = (d / "job.py").read_text()
    assert hashlib.sha256(b"X = 2\n").hexdigest() in job and "import gpu_common as G" in job
    assert _git("rev-parse", "HEAD", cwd=up) in job  # pinned commit = the fetched origin/main tip
    seal = (d / "SOURCE.sha256").read_text()
    assert "gpu_common.py" in seal and "gpuproof_row.py" in seal
    assert _git("rev-parse", "HEAD", cwd=clone) == head and _git("status", "--porcelain", cwd=clone) == status
    assert (clone / "scripts/kernel_rnd/autokernel/harness/gpu_common.py").read_text() == "X = 1\n"
    compile(job, "job.py", "exec")
    r = subprocess.run([sys.executable, "-I", "-c", job.split("raise SystemExit(\"TODO")[0].split('"""', 2)[2]],
                       cwd=str(d), capture_output=True, text=True, env={"PYTHONPATH": ""})
    assert "FUTILITY_MISSING_INPUT" not in r.stderr
    assert rs.main(["new", "row-h", "--handoff", str(hf), "--box", "BOX-3", "--lane", "gpu", "--regions", "88-95",
                    "--threads", "8", "--units", "1", "--unit-s", "1", "--model", "m", "--root", str(tmp_path),
                    "--research-repo", str(tmp_path / "nope")]) == 1
    assert not (tmp_path / "row-h").exists()


# ---------------------------------------------------------------- brief
def test_brief_forces_build_and_rules():
    class A:
        goal = "g"; box = None; model = "sonnet"; effort = "low"; build = "claim"; build_detail = "q0 0-23 40 min"
        report = "verdict"; paths = ["/abs/x"]; worktree = "wt"; owner = "autokernel"
    out = brief.render(A, box="")
    assert "HARD-RULES v1" in out and "region-lock claim" in out and "background tasks" in out and "verdict" in out
    A.build_detail = None
    try:
        brief.render(A, box="")
        raise AssertionError("expected refusal")
    except SystemExit:
        pass


def test_watch_rows_syntax():
    sh = os.path.join(HERE, "..", "scripts", "watch_rows.sh")
    assert subprocess.run(["bash", "-n", sh]).returncode == 0


# ---------------------------------------------------------------- runend --gate-eval (AKPL-P1)
def test_runend_gate_eval_draft_uses_the_evaluator(tmp_path, monkeypatch):
    pkg = tmp_path / "kr" / "autokernel" / "loop"
    pkg.mkdir(parents=True)
    (tmp_path / "kr" / "autokernel" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "gate_eval.py").write_text(
        "import json, sys\n"
        "assert sys.argv[1].endswith('/row-g/out/RESULT.json') and '--row' in sys.argv\n"
        "print(json.dumps({'filed_verdict': 'fail', 'verdict': 'FAIL', 'gate_id': 'graph_kld.gpu.q38_27b',"
        " 'rationale': 'mean_kld=0.0041 <= 0.003 failed; rc=0', 'native_verdict': 'PASS', 'checks': []}))\n")
    monkeypatch.setattr(runend, "TMP", str(tmp_path))
    monkeypatch.setattr(runend, "FLAGS", str(tmp_path / "flags"))
    v = runend.gate_eval_draft("row-g", kernel_rnd=str(tmp_path / "kr"))
    assert v["verdict"] == "fail" and v["drafted_by"] == "gate_eval"
    assert "graph_kld.gpu.q38_27b" in v["rationale"] and runend.lint_verdict(v) == []


def _gdraft(verdict, decided, gate="graph_kld.gpu.q38_27b"):
    return lambda row: {"verdict": verdict, "rationale": f"gate_eval {gate}: rc=0", "native_verdict": "",
                        "answer": verdict.upper(), "gate_eval": {"gate_id": gate}, "policy_decided": decided}


def test_runend_gate_eval_file_autofiles_policy_decided(tmp_path, monkeypatch):
    monkeypatch.setattr(runend, "TMP", str(tmp_path))
    (tmp_path / "row-a").mkdir()
    filed = []
    rc = runend.auto_file("row-a", "o", draft_fn=_gdraft("fail", True), file_fn=lambda r, o: filed.append(r) or 0)
    assert rc == 0 and filed == ["row-a"]          # zero LLM turns: filed straight from the evaluator
    assert json.load(open(tmp_path / "row-a" / "verdict.json"))["verdict"] == "fail"


def test_runend_gate_eval_file_refuses_non_policy_decided(tmp_path, monkeypatch):
    monkeypatch.setattr(runend, "TMP", str(tmp_path))
    (tmp_path / "row-b").mkdir()
    filed = []
    rc = runend.auto_file("row-b", "o", draft_fn=_gdraft("fail", False, "declared.negative"),
                          file_fn=lambda r, o: filed.append(r) or 0)
    assert rc == 4 and filed == [] and (tmp_path / "row-b" / "verdict.json").exists()


def test_runend_file_row_terminal_skips_lint(tmp_path, monkeypatch):
    # a no-result rule verdict (SUPERSEDED/WITHDRAWN) is filed through file_result's terminal path, not linted
    monkeypatch.setattr(runend, "TMP", str(tmp_path))
    monkeypatch.setattr(runend, "FLAGS", str(tmp_path / "flags"))
    (tmp_path / "row-c").mkdir()
    (tmp_path / "row-c" / "verdict.json").write_text(json.dumps({"verdict": "WITHDRAWN", "rationale": "no result"}))
    calls = []

    class R:
        returncode = 0

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if "file_result.py" in " ".join(map(str, cmd)):
            os.makedirs(tmp_path / "flags" / "filing-done", exist_ok=True)
            (tmp_path / "flags" / "filing-done" / "row-c.FILED").write_text("FILED")
        return R()
    assert runend.file_row("row-c", "o", run=fake_run) == 0
    assert any("--verdict-json" in c for c in calls)


def test_check_complete_requires_polar_token(tmp_path):
    (tmp_path / "out").mkdir()
    chk = tmp_path / "check_complete.py"
    chk.write_text(rs.CHECK_T.format(dir=str(tmp_path)))
    res = tmp_path / "out" / "RESULT.json"

    def rc(d):
        res.write_text(json.dumps(d))
        return subprocess.run([sys.executable, str(chk)]).returncode
    assert rc({"complete": True, "verdict": "FAIL(x)"}) == 1                     # no polar token
    assert rc({"complete": True, "verdict": "FAIL(x)", "polar": "FAIL"}) == 0
    assert rc({"complete": True, "verdict": "FUTILITY_HARNESS_INPUT"}) == 0
    assert rc({"complete": True, "verdict": "FUTILITY_CANDIDATE_BELOW_BASELINE"}) == 0
    assert rc({"complete": False, "verdict": "PASS", "polar": "PASS"}) == 1
    assert "FUTILITY_CANDIDATE" in rs.JOB_T and '"polar"' in rs.JOB_T
