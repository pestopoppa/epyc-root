#!/usr/bin/env python3
"""mk_ak_row.py gate new runs the WHOLE publish rehearsal (publish_row.rehearse) before it writes anything and reports
every refusal at once (operator 2026-11-25: one AK gate row failed to publish three times, for three reasons, each found
only at the final publish). The rehearsal and publish share one check list, so they must agree."""
import contextlib
import io
import json
import os
import shutil
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_TESTS)))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
sys.path.insert(0, _TESTS)
import mk_ak_row as MK  # noqa: E402
import publish_row as PR  # noqa: E402
import rowflow as rf  # noqa: E402
from test_ak_gate import Q8MC_ARMED, make_store  # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isfile(MK.FILLER), reason="the deployed engine is not on this host")

BOX = ("- [ ] **AKR-1** [inference] AK gate: measure ms_per_round of GGML_HIP_Q8MC vs OFF/OFF2 on Qwen3.8-27B Q8_0, "
       "store gpu-20261125-abcdef123-gate, MI210; est 4200 s from the smoke; stop-on-answer when the CI lower bound clears 1.01; stop-on-futility "
       "on A/A > 0.02; gate-class = futility-only\n      · done when: verdict.json filed for the row")
TICKED_NOSTOP = ("- [x] **AKR-2** [inference] AK gate: measure ms_per_round of GGML_HIP_Q8MC on Qwen3.8-27B Q8_0, store "
                 "gpu-20261125-abcdef123-gate, MI210\n      · done when: verdict filed")
BAD_EBU = json.dumps({"tbo": {"ON": {"GGML_HIP_Q8MC": "present"}}})
TBO = json.dumps([{"kind": "tbo", "witness": True, "argv": ["/s/bin/test-backend-ops", "test"], "arms": ["OFF", "ON"],
                   "ops": {"OFF": "MUL_MAT", "ON": "MUL_MAT"}, "min_cases": {"OFF": 1, "ON": 1}}])


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "handoffs" / "active").mkdir(parents=True)
    shutil.copytree(os.path.join(_ROOT, "scripts", "handoffs"), repo / "scripts" / "handoffs",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    (repo / "handoffs" / "active" / "akr.md").write_text(f"# akr\n\n## Track\n\n{BOX}\n{TICKED_NOSTOP}\n")
    flags = tmp_path / "flags"
    for d in ("dryrun", "ready", "grants"):
        (flags / d).mkdir(parents=True)
    rows = tmp_path / "rows"
    rows.mkdir()
    monkeypatch.setattr(PR, "REPO", str(repo))
    monkeypatch.setattr(rf, "TMP", str(tmp_path) + "/")
    monkeypatch.setenv("ROWFLOW_NO_VIEW_REFRESH", "1")
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    monkeypatch.setattr(PR, "check_owner_roster", lambda spec, flags, repo=None, enforce=None: None)   # no roster here
    store = make_store(tmp_path, ["GGML_HIP_Q8MC", Q8MC_ARMED])
    os.chmod(store / "bin" / "llama-server", 0o755)
    model = tmp_path / "models" / "Qwen3.8-27B-Q8_0.gguf"
    model.parent.mkdir(parents=True)
    with open(model, "wb") as f:
        f.write(b"GGUF")
        f.truncate(4096)
    text = tmp_path / "kld_text.txt"
    text.write_text("some text\n" * 50)
    argv = [str(store / "bin" / "llama-server"), "-m", str(model), "--port", "{PORT}", "-np", "1", "-c", "4096", "-ngl", "99"]
    return {"repo": repo, "flags": flags, "rows": rows, "argv": argv, "text": text}


def decl(env, rid, task="akr.md:AKR-1", extra=()):
    return ["gate", "new", "--id", rid, "--task", task, "--model", "Qwen3.8-27B-Q8_0", "--root", str(env["rows"]),
            "--flags", str(env["flags"]), "--knob", f"GGML_HIP_Q8MC:{Q8MC_ARMED}::4", "--arm", "OFF:", "--arm", "OFF2:",
            "--arm", "ON:GGML_HIP_Q8MC=1", "--metric", "ms_per_round", "--lower-is-better",
            "--keep-rule", "ci_lower>1.01,n=8,look=4,aa=0.02", "--server-argv-json", json.dumps(env["argv"]),
            "--copy-input", f"{env['text']}:inputs/kld_text.txt", "--workload-input", "inputs/kld_text.txt",
            "--win-chars", "200", "--offsets", "0,100", *extra]


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = MK.main(argv)
    return rc, out.getvalue()


def nothing_under(flags):
    return [os.path.join(r, f) for r, _, fs in os.walk(flags) for f in fs]


def test_three_defects_reported_at_once_and_nothing_written(env):
    rid = "ak-r-gate-gpu-20261125"
    rc, out = run(decl(env, rid, task="akr.md:AKR-2", extra=["--correctness", TBO, "--expect-by-unit", BAD_EBU]))
    assert rc == 2, out
    assert "is [x], not open" in out                       # 1. ticked box
    assert "no sufficiency/stop rule" in out               # 2. missing stop rule (the same run: not hidden by 1)
    assert "witness scope: tbo unit" in out                # 3. witness the unit's binary can never print
    assert out.count("FIX:") >= 3
    assert not (env["rows"] / rid).exists()                # no row dir, no spec.json
    assert nothing_under(env["flags"]) == []               # nothing under flags/ (ready, dryrun, grants)


def test_clean_declaration_rehearses_then_publishes_with_zero_warnings(env, monkeypatch):
    rid = "ak-r-gate-gpu-20261125-r2"
    rc, out = run(decl(env, rid, extra=["--rank", "45"]))
    assert rc == 0, out
    assert "REHEARSAL PASS" in out and "publish warning" not in out, out
    sp = env["rows"] / rid / "spec.json"
    spec = json.loads(sp.read_text())
    assert spec["priority_rank"] == 45
    assert spec["futility"] == {"rule": "stop at look=4 if every candidate ci_upper<1.01"}
    monkeypatch.setattr(PR, "gpu_busy", lambda flags: True)    # queue the smoke; never run it in a test
    rc, pub = run_publish([str(sp), "--flags", str(env["flags"])])
    assert rc == 0, pub
    assert "WARN" not in pub and "REFUSED" not in pub, pub
    assert "smoke queued" in pub
    q = json.loads((env["flags"] / "dryrun" / rid / "GPU-SMOKE-QUEUED.json").read_text())
    assert not q["spec"].get("publish_warnings"), q["spec"].get("publish_warnings")


def run_publish(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        rc = PR.main(argv)
    return rc, out.getvalue()


def test_rowflow_preflight_collects_publish_refusals(env, monkeypatch):
    rid = "ak-r-gate-gpu-20261125-region"
    rc, out = run(decl(env, rid))
    assert rc == 0, out
    sp = env["rows"] / rid / "spec.json"
    spec = json.loads(sp.read_text())
    spec.update(regions="88-95,184-191", estimate_s=60)
    sp.write_text(json.dumps(spec))
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = rf.main(["--flags", str(env["flags"]), "preflight", str(sp)])
    assert rc != 0
    assert "gpu regions must name mi210_0" in out.getvalue()
    assert "under 5 min" in out.getvalue()
    spec["estimate_s"] = 4200
    sp.write_text(json.dumps(spec))
    monkeypatch.setattr(PR, "gpu_busy", lambda flags: True)
    rc, pub = run_publish([str(sp), "--flags", str(env["flags"])])
    assert rc != 0 and "gpu regions must name mi210_0" in pub


def test_check_only_on_an_existing_row_and_supersedes_flag(env):
    rid = "ak-r-gate-gpu-20261125-r3"
    rc, out = run(decl(env, rid, extra=["--supersedes", "ak-r-gate-gpu-20261125-r2"]))
    assert rc == 0, out
    d = env["rows"] / rid
    assert json.loads((d / "spec.json").read_text())["supersedes"] == "ak-r-gate-gpu-20261125-r2"
    before = sorted(os.listdir(d))
    rc, out = run(["gate", "new", "--check-only", str(d), "--flags", str(env["flags"])])
    assert rc == 0 and "REHEARSAL PASS" in out, out
    assert sorted(os.listdir(d)) == before and nothing_under(env["flags"]) == []
    rc, out = run(decl(env, "ak-r-gate-gpu-20261125-r4", extra=["--check-only"]))   # a declaration: nothing kept
    assert rc == 0 and not (env["rows"] / "ak-r-gate-gpu-20261125-r4").exists(), out


@pytest.mark.parametrize("mutate,needle", [
    (lambda s: s.update(handoff_task="akr.md:AKR-2"), "not open"),
    (lambda s: s.update(handoff_task="nope.md:X"), "names no handoffs/active"),
    (lambda s: s.update(priority_rank="high"), "priority_rank must be a number"),
    (lambda s: s.update(supersedes=["ak-r-gate-gpu-20261125-r6"]), "cannot supersede itself"),
    (lambda s: s["estimate_basis"].update(units=0), "ESTIMATE-BASIS"),
    (lambda s: s.update(estimate_s=60), "under 5 min"),
    (lambda s: None, None),
])
def test_publish_and_rehearsal_agree(env, monkeypatch, mutate, needle):
    rid = "ak-r-gate-gpu-20261125-r6"
    rc, out = run(decl(env, rid))
    assert rc == 0, out
    sp = env["rows"] / rid / "spec.json"
    spec = json.loads(sp.read_text())
    mutate(spec)
    sp.write_text(json.dumps(spec))
    rc_chk, chk = run(["gate", "new", "--check-only", str(env["rows"] / rid), "--flags", str(env["flags"])])
    monkeypatch.setattr(PR, "gpu_busy", lambda flags: True)
    rc_pub, pub = run_publish([str(sp), "--flags", str(env["flags"])])
    assert (rc_chk == 0) == (rc_pub == 0), (chk, pub)
    if needle:
        assert rc_chk == 2 and needle in chk and needle in pub, (chk, pub)
    assert not os.path.exists(rf.ready_path(str(env["flags"]), rid)) or rc_pub == 0


def test_create_box_prepares_a_compliant_stub_and_writes_no_handoff(env):
    before = (env["repo"] / "handoffs" / "active" / "akr.md").read_text()
    rc, out = run(["gate", "new", "--id", "ak-r-gate-gpu-20261125-r9", "--task", "akr.md:AKR-9", "--create-box",
                   "--track", "Track", "--knob", f"GGML_HIP_Q8MC:{Q8MC_ARMED}", "--metric", "ms_per_round",
                   "--model", "Qwen3.8-27B Q8_0 store gpu-20261125-abcdef123-gate"])
    assert rc == 0 and "handoff_box.py add" in out and "--done-when" in out and "stop-on-futility" in out, out
    assert (env["repo"] / "handoffs" / "active" / "akr.md").read_text() == before
    sys.path.insert(0, os.path.join(_ROOT, "scripts", "handoffs"))
    import task_lint as TL
    text = out.split("box text: ", 1)[1].split("\n", 1)[0]
    refuse, _ = TL.publish_findings("- [ ] **AKR-9** " + text, 0)
    assert refuse == [], refuse


def test_server_env_knob_is_refused_by_rehearsal_and_publish(env, monkeypatch):
    """q8wt-r3 shape: GGML_HIP_Q8MC declared as a knob AND passed via --server-env -> stripped from every arm."""
    rid = "ak-r-gate-gpu-20261125-r7"
    rc, out = run(decl(env, rid, extra=["--server-env", "GGML_HIP_Q8MC=6"]))
    assert rc == 2 and "server-env knob" in out and "--arm OFF:GGML_HIP_Q8MC=6" in out, out
    assert not (env["rows"] / rid).exists()
    import ak_gate as G
    import preflight as P
    sp = {"generator": {"profile": "gate"}}
    gspec = {"knobs": {"GGML_HIP_Q8_MF": {}}, "server": {"env": {"GGML_HIP_Q8_MF": "6"}}}
    assert G.server_env_knob_errors(gspec) and P.PREFLIGHT_ENFORCE["witness_scope"]
    row = P.Row(sp)
    row.code["job.py"] = "SPEC = " + repr(gspec)
    assert [f[1] for f in P.check_witness_scope(row, {})] == ["SERVER-ENV-KNOB"]


def test_ticked_box_and_missing_model_both_reported_by_publish(env, monkeypatch):
    """knee-batch-r4: a ticked box AND no model identity on the same box -> one run, both items (no stop at the first)."""
    p = env["repo"] / "handoffs" / "active" / "akr.md"
    p.write_text(p.read_text() + "- [x] **AKR-3** [inference] AK gate: measure ms_per_round; est 4200 s; stop-on-answer "
                 "when CI lower > 1.01; stop-on-futility on A/A > 0.02\n      · done when: verdict filed\n")
    refusals = PR.rehearse({"handoff_task": "akr.md:AKR-3", "owner": "autokernel"}, str(env["flags"]))
    box = [it for st, it, _ in refusals if st == "box"]
    assert any("not open" in x for x in box) and any("identity incomplete" in x for x in box), box
    assert {st for st, _, _ in refusals} >= {"box", "placement"}     # later stages ran too


def test_fix_ref_rehearsal_accepts_same_class_republish(env, tmp_path):
    from test_ak_gate import family
    flags, _, _ = family(tmp_path / "history")
    env["flags"] = flags
    rid = "ak-t-gate-gpu-20261125-r2"
    rc, out = run(decl(env, rid))
    assert rc == 2 and "REPLAY-RECEIPT-SAME-CLASS" in out, out
    store = os.path.dirname(os.path.dirname(env["argv"][0]))
    rc, out = run(decl(env, rid, extra=["--fix-ref", f"{store}:new kernel fix"]))
    assert rc == 0 and "REHEARSAL PASS" in out, out
    spec = json.loads((env["rows"] / rid / "spec.json").read_text())
    assert spec["fix_ref"] == {"store": store, "reason": "new kernel fix"}


@pytest.mark.parametrize("value", ["missing:reason", ":reason", "missing:", "missing:   ", "../escape:reason"])
def test_fix_ref_rejects_invalid_store_or_reason(env, value):
    rid = "ak-r-gate-gpu-20261125-r9"
    with pytest.raises(SystemExit, match="--fix-ref"):
        run(decl(env, rid, extra=["--fix-ref", value]))
    assert not (env["rows"] / rid).exists()


def test_gate_requires_explicit_futility_look(env):
    argv = decl(env, 'ak-r-no-look-20261125')
    argv[argv.index('--keep-rule') + 1] = 'ci_lower>1.01,n=8'
    rc, out = run(argv)
    assert rc == 2
    assert 'FIX: add look=<n//2> to --keep-rule' in out


def test_futility_check_gate_and_diagnostic():
    gate = {'owner': 'autokernel', 'keep_rule': {'n_blocks': 8, 'look_blocks': 4}}
    assert PR.futility_missing(gate) is None
    for look in (None, 0, 5):
        gate['keep_rule']['look_blocks'] = look
        with pytest.raises(rf.Refused, match='look='):
            PR.check_futility(gate, '')
    diagnostic = {'owner': 'autokernel', 'kind': 'compute'}
    with pytest.raises(rf.Refused, match='spec.futility.rule'):
        PR.check_futility(diagnostic, '')
    diagnostic['futility'] = {'rule': 'stop when the witness is absent'}
    assert PR.futility_missing(diagnostic) is None


def test_gate_explicit_futility_overrides_default(env):
    rid = "ak-r-explicit-futility-20261125"
    rc, out = run(decl(env, rid, extra=["--futility", "stop on witness miss", "--no-rehearse"]))
    assert rc == 0, out
    spec = json.loads((env["rows"] / rid / "spec.json").read_text())
    assert spec["futility"] == {"rule": "stop on witness miss"}


def test_missing_futility_hint_names_flag():
    missing = PR.futility_missing({"owner": "autokernel", "kind": "compute"})
    assert 'FIX: add --futility "..."' in PR.format_rehearsal([("futility", *missing)], [])


@pytest.mark.parametrize("option", ["--knob", "--observe"])
def test_marker_colon_typo_refused_at_declaration(env, option):
    rid = "ak-r-gate-gpu-20261125-colon"
    with pytest.raises(SystemExit) as exc:
        run(decl(env, rid, extra=[option, "GGML_BAD:marker:4"]))
    assert str(exc.value) == ("REFUSED: knob GGML_BAD marker ends in ':<n>' - the level separator is '::'. "
                              "FIX: --knob 'GGML_BAD:<marker>::<n>'")
    assert not (env["rows"] / rid).exists()


def test_existing_bad_marker_refused_by_rehearsal_and_publish(env, monkeypatch):
    rid = "ak-r-gate-gpu-20261125-colon-publish"
    rc, out = run(decl(env, rid))
    assert rc == 0, out
    row = env["rows"] / rid
    job = row / "job.py"
    source = job.read_text()
    assert Q8MC_ARMED in source
    job.write_text(source.replace(Q8MC_ARMED, Q8MC_ARMED + ":4"))
    rc_chk, chk = run(["gate", "new", "--check-only", str(row), "--flags", str(env["flags"])])
    monkeypatch.setattr(PR, "gpu_busy", lambda flags: True)
    rc_pub, pub = run_publish([str(row / "spec.json"), "--flags", str(env["flags"])])
    message = "REFUSED: knob GGML_HIP_Q8MC marker ends in ':<n>' - the level separator is '::'."
    assert rc_chk == 2 and message in chk, chk
    assert rc_pub != 0 and message in pub, pub
    assert not os.path.exists(rf.ready_path(str(env["flags"]), rid))


@pytest.mark.parametrize("budget,deadline", [(100, 300), (300, 420), (900, 1020)])
def test_gate_sets_first_progress_from_smoke_budget(env, budget, deadline):
    rid = f"ak-r-deadline-{budget}-20261125"
    rc, out = run(decl(env, rid, extra=["--smoke-budget-s", str(budget)]))
    assert rc == 0, out
    assert json.loads((env["rows"] / rid / "spec.json").read_text())["first_progress_s"] == deadline


def test_gate_deadline_refused_in_rehearsal_and_publish(env, monkeypatch):
    rid = "ak-r-deadline-20261125"
    rc, out = run(decl(env, rid, extra=["--smoke-budget-s", "900", "--first-progress-s", "959"]))
    assert rc == 2 and "FIX: --first-progress-s 960" in out
    assert not (env["rows"] / rid).exists()
    rc, out = run(decl(env, rid, extra=["--smoke-budget-s", "900", "--first-progress-s", "960"]))
    assert rc == 0, out
    row = env["rows"] / rid
    sp = row / "spec.json"
    spec = json.loads(sp.read_text())
    monkeypatch.setattr(PR, "gpu_busy", lambda flags: True)
    for value in (None, 959):
        if value is None:
            spec.pop("first_progress_s", None)
        else:
            spec["first_progress_s"] = value
        sp.write_text(json.dumps(spec))
        rc_chk, chk = run(["gate", "new", "--check-only", str(row), "--flags", str(env["flags"])])
        rc_pub, pub = run_publish([str(sp), "--flags", str(env["flags"])])
        assert rc_chk == 2 and rc_pub != 0
        assert "FIX: --first-progress-s 960" in chk and "FIX: --first-progress-s 960" in pub
        assert not os.path.exists(rf.ready_path(str(env["flags"]), rid))


def test_auto_smoke_budget_uses_latest_eligible_measure_and_correctness(env):
    old = env["rows"] / "predecessor"
    (old / "out-smoke").mkdir(parents=True)
    (old / "out-smoke" / "smoke_measure.json").write_text(json.dumps({"arm_load_s": {"OFF": 105, "ON": 110}, "correctness_unit_s": {"a": 35, "b": 40}}))
    other = env["rows"] / "same-model"
    (other / "out").mkdir(parents=True)
    (other / "spec.json").write_text(json.dumps({"model": "Qwen3.8-27B-Q8_0"}))
    (other / "out" / "TERMINAL-smoke.json").write_text(json.dumps({"arm_load_s": {"OFF": 120}}))
    rid = "ak-r-auto-20261125"
    corr = json.dumps({"kind": "tbo", "argv": [env["argv"][0], "test"],
                       "arms": ["OFF", "OFF2", "ON"], "ops": "MUL_MAT", "timeout_s": 40})
    rc, out = run(decl(env, rid, extra=["--supersedes", "predecessor", "--correctness", corr]))
    assert rc == 0, out
    assert "150 s/arm x 3 arms + 900 s correctness (3 units at 300 s) + 120 s = 1470 s" in out  # measured 120/40 floored (2026-11-26)
    assert "floored to 150 s" in out and "floored to 300 s" in out
    assert "same-model/out/TERMINAL-smoke.json" in out
    spec = json.loads((env["rows"] / rid / "spec.json").read_text())
    assert spec["first_progress_s"] == 1590
    assert "'budget_s': 1470" in (env["rows"] / rid / "job.py").read_text()


def test_auto_smoke_budget_default_and_explicit_override(env):
    rc, out = run(decl(env, "ak-r-gate-gpu-20261125-autodefault"))
    assert rc == 0, out
    assert "150 s/arm x 3 arms + 0 s correctness (0 units at 300 s) + 120 s = 570 s" in out
    rc, out = run(decl(env, "ak-r-auto-explicit-20261125", extra=["--smoke-budget-s", "3000"]))
    assert rc == 0 and "3000 s (explicit --smoke-budget-s)" in out
    assert "WARN: automatic smoke budget capped" not in out
    assert "'budget_s': 3000" in (env["rows"] / "ak-r-auto-explicit-20261125" / "job.py").read_text()


def test_auto_budget_accounts_for_served_quality_load(env):
    import argparse
    row = env["rows"] / "prior"
    (row / "out-smoke").mkdir(parents=True)
    (row / "out-smoke" / "smoke_measure.json").write_text(json.dumps({"arm_load_s": {"OFF": 200}}))
    args = argparse.Namespace(root=str(env["rows"]), model="model", supersedes="prior")
    spec = {"arms": {"OFF": {}, "OFF2": {}, "ON": {"K": "1"}}, "baseline": ["OFF", "OFF2"],
            "correctness": {"kind": "served_quality", "noise_arm": "OFF2", "timeout_s": 10}}
    assert MK.derive_smoke_budget(args, spec) == 1620


def test_auto_budget_caps_long_correctness_timeouts(env, capsys):
    import argparse
    args = argparse.Namespace(root=str(env["rows"]), model="model", supersedes=None)
    spec = {"arms": {"OFF": {}, "OFF2": {}, "ON": {"K": "1"}}, "baseline": ["OFF", "OFF2"],
            "correctness": {"kind": "tbo", "arms": ["OFF", "OFF2", "ON"], "timeout_s": 5400}}
    assert MK.derive_smoke_budget(args, spec) == 1470
    spec["arms"].update({f"arm{i}": {} for i in range(10)})
    assert MK.derive_smoke_budget(args, spec) == 2400
    assert "WARN: automatic smoke budget capped" in capsys.readouterr().out
