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
    (lambda s: s.update(supersedes=["ak-r-gate-gpu-20261125-r5"]), "cannot supersede itself"),
    (lambda s: s["estimate_basis"].update(units=0), "ESTIMATE-BASIS"),
    (lambda s: s.update(estimate_s=60), "under 5 min"),
    (lambda s: None, None),
])
def test_publish_and_rehearsal_agree(env, monkeypatch, mutate, needle):
    rid = "ak-r-gate-gpu-20261125-r5"
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
