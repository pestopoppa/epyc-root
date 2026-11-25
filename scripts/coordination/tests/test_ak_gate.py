#!/usr/bin/env python3
"""ak_gate.py (the declared gate harness) + `mk_ak_row.py gate new` + the preflight replay gates (R1 receipt, R4 replay
smoke). No GPU, no model: a fake llama-server / identity binary (tests/fixtures/ak_gate/) stands in, and the replay
fixtures are REAL log excerpts from the 2026-11-24/25 failing rows (q8mc perplexity without -lv, tail-fuse2's six-knob
AND miss, devhandoff's draft diff with equal outputs)."""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROWFLOW = os.path.join(os.path.dirname(_TESTS), "rowflow")
sys.path.insert(0, _ROWFLOW)
import ak_gate as G  # noqa: E402
import ak_row_harness as H  # noqa: E402
import ak_row_lint as LINT  # noqa: E402
import mk_ak_row as MK  # noqa: E402
import preflight as P  # noqa: E402

FIX = os.path.join(_TESTS, "fixtures", "ak_gate")
_BIN_TMP = tempfile.TemporaryDirectory(prefix="ak-gate-test-bin-")
FIX_BIN = _BIN_TMP.name
for _name in ("llama-server", "llama-perplexity", "test-backend-ops", "test-dflash-dev-inject", "test-q8ip-two-ctx"):
    os.symlink("/bin/true", os.path.join(FIX_BIN, _name))

Q8MC_ARMED = "ggml_cuda_q8_mc: GGML_HIP_Q8MC=1 multi-column Q8_0 GEMV armed"
TF2 = {"GGML_CUDA_AK_ADD_RMS_NORM": "AK-RF-27B-TAIL-FUSE G1 add+rms_norm+mul fused path ran",
       "GGML_HIP_ACTQ_FUSE": "q8sk zero-fold ran",
       "GGML_CUDA_AK_TF2_G2": "AK-RF-27B-TAIL-FUSE-2 G2 swiglu into the q8mf6 down-proj pre-pass fused path ran",
       "GGML_CUDA_AK_TF2_G3": "AK-RF-27B-TAIL-FUSE-2 G3 gdn gate add+softplus+mul fused path ran",
       "GGML_CUDA_AK_TF2_G5": "AK-RF-27B-TAIL-FUSE-2 G5 gated rms_norm+mul+silu*mul fused path ran",
       "GGML_CUDA_AK_TF2_G6": "AK-RF-27B-TAIL-FUSE-2 G6 mrope+view+set_rows fused path ran"}
INJ = "LLAMA_DFLASH_DEV_INJECT=1 -> dev_inject=1"
QUIET = open(os.devnull, "w")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def spec(knobs=None, arms=None, expect=None, argv=None, **kw):
    knobs = knobs or {"GGML_HIP_Q8MC": {"kind": "env", "marker": Q8MC_ARMED, "level": 4}}
    arms = arms or {"OFF": {}, "OFF2": {}, "ON": {k: "1" for k in knobs}}
    exp = expect or {a: {k: ("present" if k in s else "absent") for k in knobs} for a, s in arms.items()}
    s = {"row_id": "ak-t-gate-gpu-20261125", "task": "x.md:T", "knobs": knobs, "arms": arms, "expect": exp,
         "baseline": [a for a in arms if not arms[a]],
         "server": {"argv": argv or [os.path.join(FIX_BIN, "llama-server"), "--port", "{PORT}"], "env": {}, "warmup": 1,
                    "ready_timeout_s": 30},
         "workload": {"prompts": ["hello there"], "n_predict": 8}, "metric": {"name": "tok_s", "higher_is_better": True},
         "keep": {"threshold": 1.01, "n_blocks": 4, "look_blocks": 2}, "correctness": None,
         "smoke": {"prompt_chars": 200, "n_predict": 4, "budget_s": 120}}
    s.update(kw)
    return s


def fake_bin(tmp_path, name, src):
    b = tmp_path / "bin"
    b.mkdir(exist_ok=True)
    shutil.copy(os.path.join(FIX, src), b / name)
    os.chmod(b / name, 0o755)
    return str(b / name)


def visit_stub(sp, out_dir, speed=None, calls=None):
    fn = G.stub_visit(sp, out_dir, speed or {})

    def wrap(uid, arm, *a, **k):
        if calls is not None:
            calls.append(uid)
        return fn(uid, arm, *a, **k)
    return wrap


# ------------------------------------------------------------------------------------------------ witness parser
def test_witness_each_knob_alone_per_arm_presence_and_absence():
    k = {"GGML_A": {"marker": "A path ran", "level": 4}, "GGML_B": {"marker": "B path ran", "level": 4}}
    arms = {"OFF": {}, "OFF2": {}, "A": {"GGML_A": "1"}, "BOTH": {"GGML_A": "1", "GGML_B": "1"}}
    sp = spec(k, arms)
    lv = ["llama-server", "-lv", "4"]
    w = G.witness_for(sp, "BOTH", "x\nI A path ran (call 1)\n", lv, "b.log")
    assert w["GGML_A"]["ok"] and not w["GGML_B"]["ok"]                   # one miss never turns the other knob False
    assert w["GGML_B"]["expected"] == "present" and w["GGML_B"]["observed"] == "absent"
    assert w["GGML_B"]["lines_scanned"] == 2 and w["GGML_B"]["log"] == "b.log"
    w = G.witness_for(sp, "A", "I A path ran\nI B path ran\n", lv)       # B must be ABSENT in arm A
    assert w["GGML_A"]["ok"] and not w["GGML_B"]["ok"] and w["GGML_B"]["expected"] == "absent"
    w = G.witness_for(sp, "OFF", "I A path ran\n", lv)                   # inverted: OFF shows a knob -> named mismatch
    assert not w["GGML_A"]["ok"] and w["GGML_B"]["ok"]
    m = G.mismatches([{"unit_id": "b1-OFF", "arm": "OFF", "witness": w}])
    txt = G.mismatch_text(m[0])
    assert "knob GGML_A arm OFF unit b1-OFF: expected absent, observed present" in txt and "1 lines scanned" in txt
    assert G.witness_for(sp, "OFF", None)["GGML_A"]["observed"] == "no-log"


def test_witness_regex_marker_and_explicit_expect_override():
    k = {"GGML_A": {"marker": r"re:A path ran \(call \d+\)", "level": 4}}
    sp = spec(k, {"OFF": {}, "OFF2": {}, "ON": {"GGML_A": "0"}},
              expect={"OFF": {"GGML_A": "absent"}, "OFF2": {"GGML_A": "absent"}, "ON": {"GGML_A": "absent"}})
    assert G.witness_for(sp, "ON", "nothing\n", ["llama-server", "-lv", "4"])["GGML_A"]["ok"]
    assert not G.witness_for(sp, "ON", "A path ran (call 3)\n")["GGML_A"]["ok"]


def test_tailfuse2_real_log_six_knobs_names_only_g5():
    """r1/r2 smoke FAILED with every knob False because one marker (G5) was ANDed in; per knob only G5 is missing."""
    arms = {"OFF": {}, "OFF2": {}, "ALL": {k: "1" for k in TF2}}
    sp = spec({k: {"marker": m, "level": 4} for k, m in TF2.items()}, arms)
    txt = G.read_log(os.path.join(FIX, "tailfuse2", "smoke-ALL-server.log"))
    w = G.witness_for(sp, "ALL", txt, ["llama-server", "-lv", "4"], "logs/smoke-ALL-server.log")
    assert [k for k, v in w.items() if not v["ok"]] == ["GGML_CUDA_AK_TF2_G5"]
    assert w["GGML_CUDA_AK_TF2_G5"]["log_lv"] == 4 and w["GGML_CUDA_AK_TF2_G5"]["note"] == ""


def test_q8mc_real_perplexity_log_without_lv_is_a_named_loglevel_miss():
    sp = spec()
    txt = G.read_log(os.path.join(FIX, "q8mc", "k-on-u8.log"))
    w = G.witness_for(sp, "ON", txt, [os.path.join(FIX_BIN, "llama-perplexity"), "-m", "m.gguf", "-f", "inputs/kld_text.txt"])
    assert not w["GGML_HIP_Q8MC"]["ok"] and "argv log level none < required 4" in w["GGML_HIP_Q8MC"]["note"]
    assert G.witness_for(sp, "ON", txt)["GGML_HIP_Q8MC"]["note"].startswith("no 'verbosity = N' banner")
    tbo = G.read_log(os.path.join(FIX, "q8mc", "c-tbo-on.log"))
    assert G.witness_for(sp, "ON", tbo)["GGML_HIP_Q8MC"]["ok"]


def test_ensure_lv_on_every_llama_binary():
    assert G.ensure_lv([os.path.join(FIX_BIN, "llama-perplexity"), "-m", "x"], 4)[-2:] == ["-lv", "4"]
    assert G.ensure_lv(["/s/bin/llama-server", "-lv", "2"], 4) == ["/s/bin/llama-server", "-lv", "4"]
    assert G.ensure_lv(["/s/bin/llama-bench", "--verbosity=1"], 5) == ["/s/bin/llama-bench", "--verbosity=5"]
    assert G.ensure_lv(["/s/bin/llama-cli", "-lv", "6"], 4) == ["/s/bin/llama-cli", "-lv", "6"]
    assert G.ensure_lv([os.path.join(FIX_BIN, "test-backend-ops"), "test"], 4) == [os.path.join(FIX_BIN, "test-backend-ops"), "test"]
    assert G.ensure_lv([os.path.join(FIX_BIN, "test-dflash-dev-inject")], 4)[-2:] == ["-lv", "4"]
    assert G.ensure_lv(["/usr/bin/taskset", "-c", "1", "/s/bin/llama-server"], 4)[-2:] == ["-lv", "4"]
    assert G.argv_lv(["llama-server", "--log-verbose"]) == 99


def test_spec_validation_names_every_defect():
    sp = spec()
    del sp["expect"]["ON"]
    with pytest.raises(G.SpecError, match=r"expect\[ON\]\[GGML_HIP_Q8MC\]"):
        G.validate_spec(sp)
    with pytest.raises(G.SpecError, match="higher_is_better must be False"):
        G.validate_spec(spec(metric={"name": "ms_per_round", "higher_is_better": True}))
    with pytest.raises(G.SpecError, match="A/A guard needs two baseline arms"):
        G.validate_spec(spec(arms={"OFF": {}, "ON": {"GGML_HIP_Q8MC": "1"}}))
    with pytest.raises(G.SpecError, match="PORT"):
        G.validate_spec(spec(argv=["/x/bin/llama-server"]))
    with pytest.raises(G.SpecError, match=r"unknown key\(s\) \['strict_draft'\]"):   # F7: a typo is never silently ignored
        G.validate_spec(spec(correctness={"kind": "identity", "mode": "cmd", "argv": ["x"], "strict_draft": True}))
    assert G.validate_spec(spec())


@pytest.mark.parametrize("source", ["workload", "offsets", "identity"])
def test_identity_prompt_count_validation(source, tmp_path):
    c = {"kind": "identity", "n_prompts": 6}
    w = {"prompts": ["a", "b", "c", "d"]}
    if source == "offsets":
        w = {"input": "input.txt", "offsets": [0, 1, 2, 3]}
        (tmp_path / "input.txt").write_text("abcdef")
    elif source == "identity":
        c["prompts"] = ["a", "b", "c", "d"]
    sp = spec(workload=w, correctness=[c])
    message = r"n_prompts=6 exceeds available prompts \(4\); FIX: set n_prompts <= 4"
    with pytest.raises(G.SpecError, match=message):
        G.validate_spec(sp)
    with pytest.raises(G.SpecError, match=message):
        G.identity_prompts(sp, str(tmp_path))
    c["n_prompts"] = 4
    assert G.validate_spec(sp)
    assert len(G.identity_prompts(sp, str(tmp_path))) == 4


# ------------------------------------------------------------------------------------------------ order / A/A / decide
def test_abba_order_balances_positions():
    two = spec(arms={"OFF": {}, "ON": {"GGML_HIP_Q8MC": "1"}}, keep={"threshold": 1.0, "n_blocks": 4, "aa_max": None})
    assert [G.block_order(two, b) for b in (1, 2, 3, 4)] == [["OFF", "ON"], ["ON", "OFF"], ["ON", "OFF"], ["OFF", "ON"]]
    four = spec(arms={"OFF": {}, "OFF2": {}, "A": {"GGML_HIP_Q8MC": "1"}, "B": {"GGML_HIP_Q8MC": "2"}},
                keep={"threshold": 1.0, "n_blocks": 8})
    pos = {}
    for b in range(1, 9):
        for i, a in enumerate(G.block_order(four, b)):
            pos.setdefault(a, []).append(i)
    assert all(sorted(v) == [0, 0, 1, 1, 2, 2, 3, 3] for v in pos.values()), pos
    assert G.blocks(four)[0] == 0 and G.block_order(four, 0) == G.block_order(four, 1)   # block 0 = unscored dummy


def _units(sp, speed, n):
    us = []
    for b in range(1, n + 1):
        for a in G.arm_list(sp):
            ms = 1000.0 / speed.get(a, 1.0) * (1 + 0.002 * ((b * 3 + len(a)) % 3 - 1))
            us.append({"unit_id": f"b{b}-{a}", "kind": "visit", "arm": a, "block": b,
                       "metric": G.metric_of(sp, [{"predicted_n": 100, "predicted_ms": ms}]), "witness": {}})
    return us


def test_decide_keep_no_keep_aa_and_futility():
    sp = spec()
    assert G.decide(sp, _units(sp, {"ON": 1.2}, 4))["verdict"] == "KEEP_ON"
    assert G.decide(sp, _units(sp, {}, 4))["verdict"] in ("NO_KEEP", "FUTILITY_CANDIDATE_BELOW_FLOOR")
    d = G.decide(sp, _units(sp, {"OFF2": 1.10, "ON": 1.2}, 2))
    assert d["verdict"] == "FUTILITY_HARNESS_AA" and d["polar"] is None
    d = G.decide(sp, _units(sp, {"ON": 0.9}, 2))
    assert d["verdict"] == "FUTILITY_CANDIDATE_BELOW_FLOOR" and d["polar"] == "FAIL"
    assert G.decide(sp, _units(sp, {"ON": 1.2}, 1))["terminal"] is False
    lo = spec(metric={"name": "ms_per_token", "higher_is_better": False})   # lower-is-better: same speed -> KEEP
    assert G.decide(lo, _units(lo, {"ON": 1.2}, 4))["verdict"] == "KEEP_ON"


# ------------------------------------------------------------------------------------------------ run / resume
def test_resume_skips_completed_units(tmp_path):
    sp = spec()
    g = G.Gate(sp, str(tmp_path / "row"), env={"FILLER_PORTS": "1"}, stream=QUIET)
    calls = []
    g.visit_fn = visit_stub(sp, g.out, {"ON": 1.2}, calls)
    first = [f"b{b}-{a}" for b in (0, 1) for a in G.block_order(sp, b)]
    g.prepare()
    for uid in first:
        b = int(uid[1:].split("-")[0])
        u = g.finish_unit(dict(g.visit_fn(uid, uid.split("-", 1)[1], ["p"], 8, 1, 5), block=b))
        H.append_unit(u, g.out)
    calls.clear()
    assert g.run() == 0
    assert not set(calls) & set(first) and len(calls) == 3 * 3          # blocks 2..4 only
    res = json.load(open(os.path.join(g.out, "RESULT.json")))
    assert res["verdict"] == "KEEP_ON" and res["complete"] and res["polar"] == "PASS"
    assert set(res) >= {"per_arm", "witness", "aa", "witness_mismatches", "blocks_scored"}


def test_full_run_fake_server_fresh_server_per_visit(tmp_path):
    srv = fake_bin(tmp_path, "llama-server", "fake_llama_server.py")
    starts = tmp_path / "starts.txt"
    sp = spec(argv=[srv, "--port", "{PORT}"])
    sp["server"]["env"] = {"FAKE_MARKERS": json.dumps({"GGML_HIP_Q8MC": Q8MC_ARMED}), "FAKE_SPEEDUP_IF": "GGML_HIP_Q8MC",
                           "FAKE_SPEEDUP": "1.3", "FAKE_STARTS": str(starts)}
    sp["keep"] = {"threshold": 1.01, "n_blocks": 2, "look_blocks": 2}
    g = G.Gate(sp, str(tmp_path / "row"), env={"FILLER_PORTS": str(free_port()), "FILLER_ID": "t"}, stream=QUIET)
    assert g.run() == 0
    res = json.load(open(os.path.join(g.out, "RESULT.json")))
    assert res["verdict"] == "KEEP_ON", res["reason"]
    lines = starts.read_text().split()
    assert len(lines) // 2 == 3 * 3                                    # 3 blocks (dummy + 2) x 3 arms, one start each
    us = G.load_units(g.out)
    assert all(u["argv"][-2:] == ["-lv", "4"] for u in us)             # -lv injected (the fake prints INFO only at 4)
    assert all(u["witness"]["GGML_HIP_Q8MC"]["ok"] for u in us) and not g.procs


# ------------------------------------------------------------------------------------------------ correctness / identity
def identity_spec(tmp_path, **c):
    b = fake_bin(tmp_path, "test-dflash-fake", "fake_identity.py")
    sp = spec(knobs={"LLAMA_DFLASH_DEV_INJECT": {"marker": INJ, "level": 4}},
              arms={"OFF": {}, "OFF2": {}, "ON": {"LLAMA_DFLASH_DEV_INJECT": "1"}})
    sp["workload"]["prompts"] = ["hello there", "second prompt"]
    sp["correctness"] = dict({"kind": "identity", "mode": "cmd", "argv": [b, "--prompt", "{PROMPT_INDEX}"], "n_prompts": 2},
                             **c)
    sp["server"]["env"] = {"FAKE_MARKERS": json.dumps({"LLAMA_DFLASH_DEV_INJECT": INJ}),
                           "FAKE_ID_KNOB": "LLAMA_DFLASH_DEV_INJECT", "FAKE_ID_PIDS": str(tmp_path / "pids.txt")}
    return sp


def test_identity_separate_processes_drafts_diagnostic_by_default(tmp_path):
    sp = identity_spec(tmp_path)
    g = G.Gate(sp, str(tmp_path / "row"), env={"FILLER_PORTS": "1", "FILLER_ID": "t"}, stream=QUIET)
    g.visit_fn = visit_stub(sp, g.out, {"ON": 1.2})
    assert g.run() == 0
    pids = (tmp_path / "pids.txt").read_text().split("\n")
    assert len({ln.split()[0] for ln in pids if ln}) == 2 * 3          # 2 prompts x 3 arms, each its own process
    res = json.load(open(os.path.join(g.out, "RESULT.json")))
    assert res["verdict"] == "KEEP_ON", res["reason"]
    assert res["correctness"]["draft_diff_prompts"] == 2 and res["correctness"]["gated_fields"] == ["output", "accepted"]


def test_identity_strict_drafts_and_output_flip_fail(tmp_path):
    sp = identity_spec(tmp_path, strict_drafts=True)
    g = G.Gate(sp, str(tmp_path / "a"), env={"FILLER_PORTS": "1", "FILLER_ID": "t"}, stream=QUIET)
    g.visit_fn = visit_stub(sp, g.out)
    g.run()
    assert json.load(open(os.path.join(g.out, "RESULT.json")))["verdict"] == "FAIL_CORRECTNESS"
    sp = identity_spec(tmp_path)
    sp["server"]["env"]["FAKE_ID_OUTPUT_FLIP"] = "1"
    g = G.Gate(sp, str(tmp_path / "b"), env={"FILLER_PORTS": "1", "FILLER_ID": "t"}, stream=QUIET)
    g.visit_fn = visit_stub(sp, g.out)
    g.run()
    res = json.load(open(os.path.join(g.out, "RESULT.json")))
    assert res["verdict"] == "FAIL_CORRECTNESS" and "output" in json.dumps(res["correctness"]["failed"])
    assert not (tmp_path / "b" / "out" / "logs" / "b1-OFF.log").exists()   # stopped before any timing visit


def test_identity_baseline_aa_difference_is_nondet_not_the_knob(tmp_path):
    sp = identity_spec(tmp_path)
    sp["arms"]["OFF2"] = {}
    sp["server"]["env"]["FAKE_ID_KNOB"] = "FAKE_OFF2_TOKEN"
    g = G.Gate(sp, str(tmp_path / "row"), env={"FILLER_PORTS": "1", "FILLER_ID": "t"}, stream=QUIET)
    units = [dict(u, output_sha="a" if u["arm"] != "OFF2" else "b") for u in
             [{"unit_id": uid, "kind": kind, "arm": arm, "prompt": ex["prompt"], "output_sha": "a", "accepted_sha": "x",
               "draft_sha": "d", "gate_unit": True} for uid, kind, arm, ex in G.plan_correctness(sp)]]
    assert G.decide(sp, units)["verdict"] == "FUTILITY_HARNESS_NONDET"
    assert g.spec is sp


# ------------------------------------------------------------------------------------------------ smoke
def test_smoke_makes_dirs_and_checks_inputs_first(tmp_path):
    sp = spec(argv=[os.path.join(FIX_BIN, "llama-server"), "--port", "{PORT}", "--slot-save-path", "{SLOTDIR}"],
              inputs={"inputs/kld_text.txt": None}, dirs=["out/prof"])
    g = G.Gate(sp, str(tmp_path / "row"), env={"FILLER_PORTS": "1", "FILLER_SMOKE": "1"}, stream=QUIET)
    assert g.smoke() == 3
    term = json.load(open(os.path.join(g.out, H.TERMINAL_SMOKE)))
    assert term["ok"] is False and "input inputs/kld_text.txt missing" in term["reason"]
    assert os.path.isdir(os.path.join(g.out, "kv_slots")) and os.path.isdir(os.path.join(g.d, "out", "prof"))


def test_smoke_fake_server_passes_and_writes_measure(tmp_path):
    srv = fake_bin(tmp_path, "llama-server", "fake_llama_server.py")
    sp = spec(argv=[srv, "--port", "{PORT}"])
    sp["server"]["env"] = {"FAKE_MARKERS": json.dumps({"GGML_HIP_Q8MC": Q8MC_ARMED})}
    row = tmp_path / "row"
    g = G.Gate(sp, str(row), env={"FILLER_PORTS": str(free_port()), "FILLER_SMOKE": "1"}, stream=QUIET)
    assert g.smoke() == 0, (row / "out" / H.TERMINAL_SMOKE).read_text()
    assert json.loads((row / "out-smoke" / H.SMOKE_MEASURE).read_text())["unit_s"] > 0
    assert [u["arm"] for u in G.load_units(str(row / "out-smoke"))] == ["OFF", "OFF2", "ON"]   # every declared arm
    sp["server"]["env"]["FAKE_MARKERS"] = "{}"                                   # knob never prints -> smoke FAIL, named
    g = G.Gate(sp, str(tmp_path / "row2"), env={"FILLER_PORTS": str(free_port()), "FILLER_SMOKE": "1"}, stream=QUIET)
    assert g.smoke() == 3
    r = json.loads((tmp_path / "row2" / "out" / H.TERMINAL_SMOKE).read_text())["reason"]
    assert "knob GGML_HIP_Q8MC arm ON unit smoke-ON: expected present, observed absent" in r


# ------------------------------------------------------------------------------------------------ replay (real fixtures)
def _prior(tmp_path, name, units=(), logs=()):
    row = tmp_path / name
    (row / "out" / "logs").mkdir(parents=True)
    for src, dst in logs:
        shutil.copy(os.path.join(FIX, src), row / "out" / "logs" / dst)
    for u in units:
        H.append_unit(dict(u, gate_unit=True), str(row / "out"))
    return row


def test_replay_q8mc_kld_unit_without_lv_is_futility_witness(tmp_path):
    sp = spec(correctness={"kind": "kld", "argv": [os.path.join(FIX_BIN, "llama-perplexity"), "-m", "m", "-f", "inputs/kld_text.txt"]})
    noflag = [os.path.join(FIX_BIN, "llama-perplexity"), "-m", "m", "-f", "inputs/kld_text.txt"]
    units = [{"unit_id": "c-kld-base-OFF", "kind": "c-kld", "arm": "OFF", "mode": "base", "argv": noflag, "rc": 0,
              "log": "logs/c-kld-base-OFF.log"},
             {"unit_id": "c-kld-OFF2", "kind": "c-kld", "arm": "OFF2", "mode": "kld", "argv": noflag, "rc": 0,
              "log": "logs/c-kld-OFF2.log"},
             {"unit_id": "c-kld-ON", "kind": "c-kld", "arm": "ON", "mode": "kld", "argv": noflag, "rc": 0,
              "log": "logs/c-kld-ON.log"}]
    prior = _prior(tmp_path, "ak-q8mc-prior", units, [("q8mc/k-on-u8.log", "c-kld-base-OFF.log"),
                                                      ("q8mc/k-on-u8.log", "c-kld-OFF2.log"),
                                                      ("q8mc/k-on-u8.log", "c-kld-ON.log")])
    new = tmp_path / "new"
    new.mkdir()
    rec = G.replay(sp, str(new), str(prior), stream=QUIET)
    assert rec["verdict"] == "FUTILITY_HARNESS_WITNESS" and rec["mode"] == "units" and rec["n_witnessed"] == 3
    assert "knob GGML_HIP_Q8MC arm ON unit c-kld-ON" in rec["observed"]["reason"] and "argv log level none" in \
        rec["observed"]["reason"]
    assert rec["mismatch_pairs"] == [("GGML_HIP_Q8MC", "ON")] and not (new / "out").exists()   # replay writes nothing


def test_replay_tailfuse2_logs_only_six_vs_five_knobs(tmp_path):
    prior = _prior(tmp_path, "ak-tf2-prior", logs=[("tailfuse2/smoke-ALL-server.log", "smoke-ALL-server.log")])
    six = spec({k: {"marker": m, "level": 4} for k, m in TF2.items()}, {"OFF": {}, "OFF2": {}, "ALL": {k: "1" for k in TF2}})
    r = G.replay(six, str(tmp_path / "n6"), str(prior), stream=QUIET)
    assert r["mode"] == "logs-only" and r["verdict"] == "FUTILITY_HARNESS_WITNESS"
    assert [m["knob"] for m in r["witness_mismatches"]] == ["GGML_CUDA_AK_TF2_G5"]
    five = {k: m for k, m in TF2.items() if not k.endswith("G5")}
    r = G.replay(spec({k: {"marker": m, "level": 4} for k, m in five.items()},
                      {"OFF": {}, "OFF2": {}, "ALL": {k: "1" for k in five}}), str(tmp_path / "n5"), str(prior), stream=QUIET)
    assert r["verdict"] == "SMOKE_PASS", r["observed"]


def test_replay_devhandoff_draft_diff_output_equal(tmp_path):
    """r5: drafts differ at round 9 OFF vs ON (separate processes) with identical accepted counts and output."""
    c = {"kind": "identity", "mode": "cmd", "argv": [os.path.join(FIX_BIN, "test-dflash-dev-inject")], "n_prompts": 1,
         "arms": ["OFF", "OFF2", "ON"]}
    sp = spec(knobs={"LLAMA_DFLASH_DEV_INJECT": {"marker": INJ, "level": 4}},
              arms={"OFF": {}, "OFF2": {}, "ON": {"LLAMA_DFLASH_DEV_INJECT": "1"}}, correctness=c)
    units = [{"unit_id": f"c-id-{a}-p0", "kind": "c-id", "arm": a, "prompt": 0, "argv": ["test-dflash-dev-inject", "-lv", "4"],
              "rc": 0, "log": f"logs/c-id-{a}-p0.log"} for a in ("OFF", "OFF2", "ON")]
    prior = _prior(tmp_path, "ak-dh-prior", units, [("devhandoff/c-unit-inj-sel-p0-off.log", "c-id-OFF-p0.log"),
                                                    ("devhandoff/c-unit-inj-sel-p0-on.log", "c-id-ON-p0.log"),
                                                    ("devhandoff/c-unit-inj-sel-p0-off.log", "c-id-OFF2-p0.log")])
    r = G.replay(sp, str(tmp_path / "n"), str(prior), stream=QUIET)
    assert r["verdict"] == "INCOMPLETE", r["observed"]                    # correctness passed; no timing units recorded
    r = G.replay(dict(sp, correctness=dict(c, strict_drafts=True)), str(tmp_path / "n2"), str(prior), stream=QUIET)
    assert r["verdict"] == "FAIL_CORRECTNESS" and "draft" in r["observed"]["reason"]


# ------------------------------------------------------------------------------------------------ generator + preflight
def make_store(base, knobs_and_markers):
    root = base / "kernels" / "builds" / "gpu-20261125-abcdef123-gate"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "llama-server").write_text("\n".join(["-m", "--port", "-lv", "-np", "-c", "-ngl"]) + "\n")
    (root / "bin" / "llama-server").chmod(0o755)
    (root / "bin" / "libggml-hip.so").write_text("\n".join(knobs_and_markers) + "\n")
    rels = ["bin/llama-server", "bin/libggml-hip.so"]
    import hashlib
    (root / "SHA256SUMS").write_text("".join(f"{hashlib.sha256((root / r).read_bytes()).hexdigest()}  {r}\n" for r in rels))
    (root / "BUILD-IDENTITY.json").write_text(json.dumps({"source_sha": "abcdef1234567"}))
    return root


def gen_row(tmp_path, rid="ak-t-gate-gpu-20261125", extra=()):
    store = make_store(tmp_path, ["GGML_HIP_Q8MC", Q8MC_ARMED])
    model = tmp_path / "models" / "Qwen3.8-27B-Q8_0.gguf"
    model.parent.mkdir(parents=True, exist_ok=True)
    with open(model, "wb") as f:
        f.write(b"GGUF")
        f.truncate(4096)
    text = tmp_path / "kld_text.txt"
    text.write_text("some text\n" * 50)
    argv = [str(store / "bin" / "llama-server"), "-m", str(model), "--port", "{PORT}", "-np", "1", "-c", "4096",
            "-ngl", "99"]
    root = tmp_path / "rows"
    root.mkdir(exist_ok=True)
    rc = MK.main(["gate", "new", "--no-rehearse", "--id", rid, "--task", "x.md:T", "--model", "Qwen3.8-27B-Q8_0", "--root", str(root),
                  "--knob", f"GGML_HIP_Q8MC:{Q8MC_ARMED}::4", "--arm", "OFF:", "--arm", "OFF2:", "--arm", "ON:GGML_HIP_Q8MC=1",
                  "--metric", "ms_per_round", "--keep-rule", "ci_lower>1.01,n=8,look=4,aa=0.02",
                  "--server-argv-json", json.dumps(argv), "--copy-input", f"{text}:inputs/kld_text.txt",
                  "--workload-input", "inputs/kld_text.txt", "--win-chars", "200", "--offsets", "0,100", *extra])
    assert rc == 0
    d = root / rid
    return d, json.loads((d / "spec.json").read_text())


def test_generated_row_is_a_thin_declaration_and_lints_clean(tmp_path):
    d, spec_ = gen_row(tmp_path)
    job = (d / "job.py").read_text()
    assert "import ak_gate as G" in job and "def " not in job and "G.main(SPEC, D" in job
    assert "SERVER_ARGV = [" in job and "'-lv', '4'" in job and "KNOBS = ['GGML_HIP_Q8MC']" in job
    assert spec_["generator"]["profile"] == "gate" and spec_["resumable"] is True
    assert spec_["fresh_server_per_visit"] is True and "gate" not in spec_ and "evidence" not in spec_
    assert {"out/logs", "out/results.jsonl", "out-smoke"} <= set(spec_["keep"])         # the replay input stays
    assert "ak_gate.py" in (d / "SOURCE.sha256").read_text() and "inputs/kld_text.txt" in (d / "SOURCE.sha256").read_text()
    fails = [f for f in LINT.lint_dir(str(d)) if f[0] == "FAIL"]
    assert not fails, fails
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "job.py"), "--selftest"], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0 and "selftest ok" in p.stdout, p.stderr
    assert not (d / "out").exists()
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "job.py")], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 64                                                            # never by hand


def test_generated_row_preflight_zero_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    d, spec_ = gen_row(tmp_path)
    flags = tmp_path / "flags"
    (flags / "dryrun").mkdir(parents=True)
    (flags / "ready").mkdir()
    res = P.run(spec_, row_dir=str(d), flags=str(flags), queued={}, run_selftest=True)
    fails = [f for f in res if f[1] == "FAIL"]
    assert not fails, fails
    assert not any(f[0] in ("replay_decide", "replay_receipt") for f in res)               # no family history: silent


def test_gate_cli_parse_knob_and_model_inference(tmp_path):
    with pytest.raises(SystemExit, match="level separator"):
        MK.parse_knob("LLAMA_X:dflash2_dev_select: chain n_threads:8")
    assert MK.parse_knob("LLAMA_X:dflash2_dev_select: chain enabled::5")[1]["level"] == 5
    rc = MK.main(["gate", "new", "--no-rehearse", "--id", "ak-x-gpu-20261125", "--task", "x.md:T", "--root", str(tmp_path),
                  "--knob", "GGML_A:A ran", "--arm", "OFF:", "--arm", "OFF2:", "--arm", "ON:GGML_A=1", "--metric",
                  "tok_s", "--keep-rule", "ci_lower>1.01", "--server-argv-json",
                  json.dumps([os.path.join(FIX_BIN, "llama-server"), "-m", "/m/Qwen3.8-27B-Q8_0.gguf", "--port", "{PORT}"]), "--prompt", "p"])
    assert rc == 0 and json.loads((tmp_path / "ak-x-gpu-20261125" / "spec.json").read_text())["model"] == "Qwen3.8-27B-Q8_0"
    with pytest.raises(G.SpecError, match="unknown key"):
        MK.main(["gate", "new", "--no-rehearse", "--id", "ak-y-gpu-20261125", "--task", "x.md:T", "--root", str(tmp_path),
                 "--knob", "GGML_A:A ran", "--arm", "OFF:", "--arm", "OFF2:", "--arm", "ON:GGML_A=1", "--metric",
                 "tok_s", "--keep-rule", "ci_lower>1.01", "--server-argv-json",
                 json.dumps([os.path.join(FIX_BIN, "llama-server"), "-m", "/m/x.gguf", "--port", "{PORT}"]), "--prompt", "p",
                 "--correctness", json.dumps({"kind": "kld", "argv": [os.path.join(FIX_BIN, "llama-perplexity")], "max_kl": 0.01})])


# ------------------------------------------------------------------------------------------------ R1 receipt / R4 replay
def family(tmp_path, reason="SMOKE FAIL rc=3: FUTILITY_HARNESS_WITNESS: knob GGML_HIP_Q8MC arm ON: expected present"):
    """A failed predecessor ak-t-gate-gpu-20261125 (smoke FAIL record + launcher.out + out/ with the knob absent)."""
    flags = tmp_path / "flags"
    prev = "ak-t-gate-gpu-20261125"
    dd = flags / "dryrun" / prev
    dd.mkdir(parents=True)
    (flags / "ready").mkdir(exist_ok=True)
    prow = tmp_path / "prevrow"
    (prow / "out" / "logs").mkdir(parents=True)
    (prow / "spec.json").write_text(json.dumps({"id": prev}))
    (prow / "out" / "logs" / "smoke-ON.log").write_text("0.0 I cmn verbosity = 4\nnothing armed\n")
    H.append_unit({"unit_id": "smoke-ON", "kind": "smoke", "arm": "ON", "argv": ["llama-server", "-lv", "4"],
                   "log": "logs/smoke-ON.log", "req": [{"predicted_n": 4, "predicted_ms": 40}], "gate_unit": True},
                  str(prow / "out-smoke"))
    H.end_smoke("FAIL", 3, reason, str(prow / "out"), stream=QUIET)
    (dd / "unpublished.json").write_text(json.dumps({"id": prev, "scratch_root": str(prow)}))
    (dd / "FAIL-1.json").write_text(json.dumps({"id": prev, "at": "2026-11-25T10:00:00Z", "reason": "job-rc-3 " + reason}))
    (dd / "launcher.out").write_text(reason + "\n")
    return flags, prev, prow


def _armed_log(prow):
    (prow / "out" / "logs" / "smoke-ON.log").write_text(f"0.0 I cmn verbosity = 4\n0.1 I {Q8MC_ARMED} (M 2..8)\n")


def test_receipt_is_the_preflight_replay_and_same_failure_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    flags, prev, prow = family(tmp_path)
    d, spec_ = gen_row(tmp_path, rid="ak-t-gate-gpu-20261125-r2")
    row = P.Row(spec_, str(d))
    got = P.check_replay_receipt(row, {"flags": str(flags)})               # no replay ran in this ctx
    assert [c for _l, c, _m in got] == ["REPLAY-RECEIPT-MISSING"] and "--replay" in got[0][2]
    ctx = {"flags": str(flags)}
    assert [c for _l, c, _m in P.check_replay_decide(row, ctx)] == ["REPLAY-DECIDE-SAME-CLASS"]
    got = P.check_replay_receipt(row, ctx)
    assert [c for _l, c, _m in got] == ["REPLAY-RECEIPT-SAME-CLASS"] and "does not change the verdict" in got[0][2]
    assert ctx["replay_decide"][spec_["id"]]["observed"]["verdict"] == "FUTILITY_HARNESS_WITNESS"
    assert "84-87" in " ".join(P.REPLAY_PIN) and not (d / "out").exists()     # --decide-from writes nothing
    _armed_log(prow)                                                           # a declaration that matches the binary
    ctx = {"flags": str(flags)}
    assert P.check_replay_decide(row, ctx) == [] and P.check_replay_receipt(row, ctx) == []
    s = dict(spec_)
    P.publish_check(s, str(flags), warn=lambda w: None, queued={})              # recorded for the family gate (R2 hook)
    assert s["preflight"]["replay_decide"]["observed"]["verdict"] == "SMOKE_PASS"
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "job.py"), "--replay", str(prow)], capture_output=True,
                       text=True, env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0 and "-> SMOKE_PASS" in p.stdout and not (d / "out").exists()   # the dev fix loop


def _judge(tmp_path, units, logs, reason, sp=None):
    """check_replay_receipt for a replay `units` + `logs` of a failed predecessor whose FAIL said `reason`."""
    flags, prev, prow = family(tmp_path, reason=reason)
    shutil.rmtree(prow / "out-smoke")
    os.remove(prow / "out" / "logs" / "smoke-ON.log")
    for name, txt in logs.items():
        (prow / "out" / "logs" / name).write_text(txt)
    for u in units:
        H.append_unit(dict(u, gate_unit=True), str(prow / "out"))
    rec = G.replay(sp or spec(), str(tmp_path / "new"), str(prow), stream=QUIET)
    row = P.Row({"id": "ak-t-gate-gpu-20261125-r2", "owner": "autokernel"}, str(tmp_path / "new"))
    rec["prev_id"] = prev
    return P.check_replay_receipt(row, {"flags": str(flags), "replay_decide": {row.id: rec}}), rec


def test_f1_infra_failure_is_not_replayable_and_witness_compares_knob_arm(tmp_path):
    srv = {"unit_id": "smoke-ON", "kind": "smoke", "arm": "ON", "error": "server not ready within 900 s",
           "error_class": "SERVER"}
    got, rec = _judge(tmp_path / "a", [srv], {}, "SMOKE FAIL rc=3: FUTILITY_HARNESS_SERVER: smoke-ON: server not ready")
    assert rec["verdict"] == "FUTILITY_HARNESS_SERVER" and got == []           # a retry / timeout fix cannot show offline
    k = {"GGML_A": {"marker": "A path ran", "level": 4}, "GGML_B": {"marker": "B path ran", "level": 4}}
    sp = spec(k, {"OFF": {}, "OFF2": {}, "ON": {"GGML_A": "1", "GGML_B": "1"}})
    log = {"smoke-ON.log": "verbosity = 4\nI A path ran\n"}                   # A fixed, B never armed in the old run
    u = [{"unit_id": "smoke-ON", "kind": "smoke", "arm": "ON", "argv": ["llama-server", "-lv", "4"],
          "log": "logs/smoke-ON.log", "req": [{"predicted_n": 4, "predicted_ms": 40}]}]
    got, rec = _judge(tmp_path / "b", u, log, "FUTILITY_HARNESS_WITNESS: knob GGML_A arm ON unit smoke-ON: expected present", sp)
    assert rec["mismatch_pairs"] == [("GGML_B", "ON")] and got == []             # a different (knob, arm): not the same
    got, _ = _judge(tmp_path / "c", u, log, "FUTILITY_HARNESS_WITNESS: knob GGML_B arm ON unit smoke-ON: expected present", sp)
    assert [c for _l, c, _m in got] == ["REPLAY-RECEIPT-SAME-CLASS"]


def test_f2_zero_units_and_undeclared_arm_close_the_false_pass(tmp_path):
    got, rec = _judge(tmp_path / "a", [], {"smoke-ALL-server.log": "I something\n"}, "FUTILITY_HARNESS_WITNESS: x")
    assert rec["n_units"] == 0 and [c for _l, c, _m in got] == ["REPLAY-RECEIPT-NO-UNITS"]
    u = [{"unit_id": "smoke-ON1", "kind": "smoke", "arm": "ON1", "argv": ["llama-server", "-lv", "4"],
          "log": "logs/smoke-ON1.log", "req": [{"predicted_n": 4, "predicted_ms": 40}]}]
    got, rec = _judge(tmp_path / "b", u, {"smoke-ON1.log": "verbosity = 4\n"},
                      "FUTILITY_HARNESS_WITNESS: knob GGML_HIP_Q8MC arm ON1 unit smoke-ON1: expected present")
    assert rec["verdict"] == "FUTILITY_HARNESS_WITNESS" and rec["witness_mismatches"][0]["observed"] == "no-arm"


def test_f3_removed_correctness_gate_and_f4_token_before_text(tmp_path):
    c = {"unit_id": "c-kld-ON", "kind": "visit", "arm": "ON", "block": 1, "argv": ["llama-server", "-lv", "4"],
         "log": "logs/b1-ON.log", "req": [{"predicted_n": 4, "predicted_ms": 40}]}
    got, rec = _judge(tmp_path / "a", [c], {"b1-ON.log": f"verbosity = 4\nI {Q8MC_ARMED}\n"},
                      "FAIL_CORRECTNESS: kld ON 0.01 > 0.003 (argv ... -lv 4 ...)")
    assert rec["correctness_kind"] is None and [cc for _l, cc, _m in got] == ["REPLAY-RECEIPT-GATE-REMOVED"]
    assert P._fine_class("FAIL_CORRECTNESS: ... -lv 4 verbosity") == "correctness"     # the token wins over the text
    assert P._fine_class("FUTILITY_HARNESS_TIMEOUT: c-tbo-ON") == "server"


def test_replay_decide_legacy_job_is_warn_and_crash_is_fail(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    flags, prev, prow = family(tmp_path)
    d = tmp_path / "legacy"
    d.mkdir()
    (d / "job.py").write_text("import sys\nsys.exit(0)\n")
    s = {"id": "ak-t-gate-gpu-20261125-r3", "owner": "autokernel", "launcher": str(d / "launch.sh")}
    got = P.check_replay_decide(P.Row(s, str(d)), {"flags": str(flags)})
    assert [(l, c) for l, c, _m in got] == [("WARN", "REPLAY-DECIDE-UNSUPPORTED")]
    (d / "job.py").write_text("import sys\n# --decide-from\nraise SystemExit(5)\n")
    got = P.check_replay_decide(P.Row(s, str(d)), {"flags": str(flags)})
    assert [(l, c) for l, c, _m in got] == [("FAIL", "REPLAY-DECIDE-CRASH")]


def test_replay_checks_enforcement_and_publish_only():
    assert P.PREFLIGHT_ENFORCE["replay_receipt"] is True and P.PREFLIGHT_ENFORCE["replay_decide"] is False
    assert {"replay_receipt", "replay_decide"} <= set(P.PUBLISH_ONLY)
    assert P.CHECKS.index("replay_decide") < P.CHECKS.index("replay_receipt")
    assert "replay_receipt" not in P.DRIFT_CHECKS


def test_family_gate_receipt_unparks_and_enforce_switch(tmp_path, monkeypatch):
    """family_strikes.republish_allowed (R2 park) accepts a validated R1 receipt as the unpark reason; the R1 refusal
    applies by default and can still be switched off."""
    import family_strikes as fs
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    flags, prev, prow = family(tmp_path)
    for i in range(fs.PARK_AT):
        fs.record_strike(str(flags), prev, "smoke", "witness miss", key=str(i), manifest={})
    d, spec_ = gen_row(tmp_path, rid="ak-t-gate-gpu-20261125-r2")
    ok, why = fs.republish_allowed(str(flags), spec_)
    assert not ok and why.startswith("PARKED")
    new_store = tmp_path / "new-store"
    new_store.mkdir()
    fixed = dict(spec_, fix_ref={"store": str(new_store), "reason": "new kernel"})
    assert fs.republish_allowed(str(flags), fixed)[0]  # structured fix un-parks the family
    fixed["fix_ref"] = {"store": str(new_store), "reason": " "}
    assert not fs.republish_allowed(str(flags), fixed)[0]
    _armed_log(prow)
    s = dict(spec_)
    P.publish_check(s, str(flags), warn=lambda w: None, queued={})      # publish order: row_preflight, then the family gate
    assert fs.republish_allowed(str(flags), s)[0]                      # valid receipt = one attempt past the park
    fs.record_clear(str(flags), prev, "PASS")                          # not parked, but missing receipt is refused
    ok, why = fs.republish_allowed(str(flags), spec_)
    assert not ok and "REPLAY-RECEIPT-MISSING" in why
    monkeypatch.setitem(P.PREFLIGHT_ENFORCE, "replay_receipt", False)
    assert fs.republish_allowed(str(flags), spec_)[0]                  # warn-only switch lets it through


# ------------------------------------------------------------------------------------------------ A: selftest_bin + verdict map
DET = "V5 deterministic split-tile reduction enabled (GGML_HIP_Q8_MF6_DET=1)"
V5I = "ggml_cuda_q8ip: in-place Q8_0 stage-contiguous repack enabled"
VMAP = {"PASS": {"KEEP": "PASS_DET_NOREGRESS"},
        "FAIL": {"FAIL_CORRECTNESS": "FAIL_FIX_NONDET", "NO_KEEP": "FAIL_PERF_REGRESS",
                 "FUTILITY_CANDIDATE_BELOW_FLOOR": "FAIL_PERF_REGRESS"}}


def q8ip_spec(argv):
    return spec(knobs={"GGML_HIP_Q8_MF6_DET": {"marker": DET, "level": 4}, "V5I": {"kind": "observe", "marker": V5I}},
                arms={"BASE": {}, "FIX": {"GGML_HIP_Q8_MF6_DET": "1"}},
                expect={"BASE": {"GGML_HIP_Q8_MF6_DET": "absent", "V5I": "present"},
                        "FIX": {"GGML_HIP_Q8_MF6_DET": "present", "V5I": "present"}},
                metric={"name": "ms_per_round", "higher_is_better": False},
                keep={"threshold": 0.99, "n_blocks": 2, "look_blocks": 2, "aa_max": None}, verdict_map=VMAP,
                correctness={"kind": "selftest_bin", "argv": argv, "runs": 3,
                             "mismatch_rx": r"^summary: prompts=\d+ mismatches=(\d+)", "max_mismatch": {"FIX": 0}})


def test_a_selftest_bin_replay_on_the_real_bisect_log(tmp_path):
    """ak-27b-second-ctx-nondet-bisect smoke-0.log (AA, 4/4 MISMATCH, V5I on): BASE reports it, FIX gates on 0."""
    real = open(os.path.join(FIX, "q8ip", "aa-base-smoke-0.log")).read()
    sp = q8ip_spec([os.path.join(FIX_BIN, "test-q8ip-two-ctx"), "-lv", "4"])

    def prior(name, fix_log):
        units, logs = [], []
        row = tmp_path / name
        (row / "out" / "logs").mkdir(parents=True)
        for uid, kind, arm, ex in G.plan_correctness(sp):
            (row / "out" / "logs" / f"{uid}.log").write_text(real if arm == "BASE" else fix_log)
            H.append_unit({"unit_id": uid, "kind": kind, "arm": arm, "argv": ["test-q8ip-two-ctx", "-lv", "4"], "rc": 0,
                           "log": f"logs/{uid}.log", "gate_unit": True, **ex}, str(row / "out"))
        return row
    nondet = real.replace(V5I, f"0.0 I {DET}\n0.1 I {V5I}")               # FIX armed but still 4/4 mismatches
    r = G.replay(sp, str(tmp_path / "n"), str(prior("p1", nondet)), stream=QUIET)
    assert r["verdict"] == "FAIL_FIX_NONDET" and r["observed"]["polar"] == "FAIL"
    assert r["observed"]["native_verdict"] == "FAIL_CORRECTNESS" and '"FIX"' in r["observed"]["reason"]
    assert P.observed_class(r["observed"])["fine"] == "correctness"        # the row's own name never re-classes
    fixed = nondet.replace("mismatches=4", "mismatches=0")
    r = G.replay(sp, str(tmp_path / "n2"), str(prior("p2", fixed)), stream=QUIET)
    assert r["verdict"] == "INCOMPLETE"                                     # correctness passed; BASE 12 reported only
    r = G.replay(sp, str(tmp_path / "n3"), str(prior("p3", real)), stream=QUIET)    # FIX without the DET line
    assert r["verdict"] == "FUTILITY_HARNESS_WITNESS" and r["mismatch_pairs"][0] == ("GGML_HIP_Q8_MF6_DET", "FIX")


def test_a_selftest_bin_live_fresh_processes_and_mapped_keep(tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    (b / "test-q8ip-two-ctx").write_text(
        "#!/usr/bin/env python3\nimport os\n"
        "open(os.environ['PIDS'], 'a').write(str(os.getpid()) + '\\n')\n"
        f"print('0.1 I {V5I}')\n"
        f"det = os.environ.get('GGML_HIP_Q8_MF6_DET')\nprint('0.2 I {DET}') if det else None\n"
        "print('summary: prompts=4 mismatches=%d engaged=1' % (0 if det else 3))\n")
    os.chmod(b / "test-q8ip-two-ctx", 0o755)
    sp = q8ip_spec([str(b / "test-q8ip-two-ctx")])
    sp["server"]["env"] = {"PIDS": str(tmp_path / "pids")}
    g = G.Gate(sp, str(tmp_path / "row"), env={"FILLER_PORTS": "1", "FILLER_ID": "t"}, stream=QUIET)
    g.visit_fn = visit_stub(sp, g.out, {"FIX": 1.0})
    assert g.run() == 0
    res = json.load(open(os.path.join(g.out, "RESULT.json")))
    assert res["verdict"] == "PASS_DET_NOREGRESS" and res["polar"] == "PASS" and res["native_verdict"] == "KEEP_FIX"
    assert res["correctness"]["mismatches"] == {"BASE": 9, "FIX": 0}
    assert len(set((tmp_path / "pids").read_text().split())) == 6            # 3 runs x 2 arms, each its own process
    assert all(u["argv"][-2:] == ["-lv", "4"] for u in G.load_units(g.out) if u["kind"] == "c-st")
    chk = MK.GATE_CHECK.format(result=os.path.join(g.out, "RESULT.json"))
    assert subprocess.run([sys.executable, "-c", chk]).returncode == 0       # the keeper's completion check accepts it


# ------------------------------------------------------------------------------------------------ B: several correctness kinds
def q8mc_b_spec(max_kld=0.0001, k=3.0, ops_min=(37, 44)):
    tbo = {"kind": "tbo", "argv": [os.path.join(FIX_BIN, "test-backend-ops"), "test", "-b", "ROCm0"], "witness": True,
           "ops": {"OFF": "MUL_MAT", "ON": "MUL_MAT,Q8MC"}, "min_cases": {"OFF": ops_min[0], "ON": ops_min[1]}}
    kld = {"kind": "kld", "argv": [os.path.join(FIX_BIN, "llama-perplexity"), "-m", "m", "-f", "inputs/kld_text.txt"], "max_kld": max_kld}
    if k is not None:
        kld["max_kld_noise_k"] = k
    return spec(correctness=[tbo, kld],
                expect_by_unit={"kld": {"ON": {"GGML_HIP_Q8MC": "ignore"}}})   # the KLD run printed no INFO (no -lv)


def q8mc_b_prior(tmp_path, name):
    """The real ak-c22-q8mc-gate-gpu-20261124 tbo (OFF 37 / ON 44 cases) and KLD (OFF2 0.000398, ON 0.000412) logs."""
    row = tmp_path / name
    (row / "out" / "logs").mkdir(parents=True)
    src = {"c-tbo-OFF": "c-tbo-off-head.log", "c-tbo-OFF2": "c-tbo-off-head.log", "c-tbo-ON": "c-tbo-on-head.log", "c-kld-base-OFF": "k-off2-u8.log",
           "c-kld-OFF2": "k-off2-u8.log", "c-kld-ON": "k-on-u8.log"}
    for uid, kind, arm, ex in G.plan_correctness(q8mc_b_spec()):
        shutil.copy(os.path.join(FIX, "q8mc", src[uid]), row / "out" / "logs" / f"{uid}.log")
        H.append_unit({"unit_id": uid, "kind": kind, "arm": arm, "rc": 0, "log": f"logs/{uid}.log",
                       "argv": [os.path.join(FIX_BIN, "llama-perplexity"), "-lv", "4"] if kind == "c-kld" else None, "gate_unit": True,
                       **ex}, str(row / "out"))
    return row


def test_b_tbo_and_kld_all_must_pass_with_noise_floor_bound(tmp_path):
    prior = q8mc_b_prior(tmp_path, "p")
    r = G.replay(q8mc_b_spec(), str(tmp_path / "n1"), str(prior), stream=QUIET)
    assert r["verdict"] == "INCOMPLETE" and r["correctness_kind"] == "tbo+kld"     # both passed: ON 0.000412 <= 3 x 0.000398
    r = G.replay(q8mc_b_spec(k=None), str(tmp_path / "n2"), str(prior), stream=QUIET)
    assert r["verdict"] == "FAIL_CORRECTNESS" and "ON" in r["observed"]["reason"]   # absolute 0.0001 alone fails it
    r = G.replay(q8mc_b_spec(ops_min=(37, 45)), str(tmp_path / "n3"), str(prior), stream=QUIET)
    assert r["verdict"] == "FAIL_CORRECTNESS" and "c-tbo-ON" in r["observed"]["reason"]   # 44 < the arm's 45 cases
    sp = q8mc_b_spec()
    del sp["expect_by_unit"]
    r = G.replay(sp, str(tmp_path / "n4"), str(prior), stream=QUIET)                  # unscoped: the KLD miss counts
    assert r["verdict"] == "FUTILITY_HARNESS_WITNESS" and r["mismatch_pairs"] == [("GGML_HIP_Q8MC", "ON")]
    assert [p[0] for p in G.plan_correctness(q8mc_b_spec())][:3] == ["c-tbo-OFF", "c-tbo-OFF2", "c-tbo-ON"]   # tbo first, then KLD


def test_b_per_arm_ops_argv_scoped_witness_and_validation(tmp_path):
    sp = q8mc_b_spec()
    g = G.Gate(sp, str(tmp_path / "row"), env={"FILLER_PORTS": "1"}, stream=QUIET)
    seen = []
    g.run_fn = lambda argv, env, log, to: (seen.append(argv), open(log, "w").write(""), {"rc": 0, "secs": 0})[2]
    g.prepare()
    g.run_correctness_unit("c-tbo-ON", "c-tbo", "ON", {})
    assert seen[-1][-2:] == ["-o", "MUL_MAT,Q8MC"]
    w = G.witness_for(sp, "ON", "nothing\n", ["llama-perplexity", "-lv", "4"], unit_type="kld")
    assert w["GGML_HIP_Q8MC"]["ok"] and w["GGML_HIP_Q8MC"]["expected"] == "ignore"
    assert not G.witness_for(sp, "ON", "nothing\n", ["llama-server", "-lv", "4"])["GGML_HIP_Q8MC"]["ok"]   # served
    with pytest.raises(G.SpecError, match="one unit per kind"):
        G.validate_spec(dict(sp, correctness=sp["correctness"] + [sp["correctness"][1]]))
    with pytest.raises(G.SpecError, match="expect_by_unit"):
        G.validate_spec(dict(sp, expect_by_unit={"kld": {"ON": {"GGML_HIP_Q8MC": "maybe"}}}))
    with pytest.raises(G.SpecError, match="arm NOPE not declared"):
        G.validate_spec(dict(sp, correctness=[dict(sp["correctness"][0], ops={"NOPE": "X"})]))



def test_b_generator_emits_one_argv_literal_per_correctness_kind(tmp_path):
    corr = [{"kind": "tbo", "argv": [os.path.join(FIX_BIN, "test-backend-ops"), "test"], "ops": {"OFF": "A", "ON": "A,B"},
             "min_cases": {"OFF": 2, "ON": 3}},
            {"kind": "kld", "argv": [os.path.join(FIX_BIN, "llama-perplexity"), "-m", "m"], "max_kld": 0.003, "max_kld_noise_k": 3}]
    d, spec_ = gen_row(tmp_path, extra=["--correctness", json.dumps(corr),
                                        "--expect-by-unit", '{"kld": {"ON": {"GGML_HIP_Q8MC": "ignore"}}}'])
    job = (d / "job.py").read_text()
    assert "CORRECTNESS_ARGV_TBO = [" in job and "CORRECTNESS_ARGV_KLD = [" in job and "'-lv', '4']" in job
    assert "'argv': CORRECTNESS_ARGV_KLD" in job and "'expect_by_unit'" in job
    assert [t["tool"] for t in spec_["tool_argv_delta"]] == ["llama-perplexity"]      # tbo argv untouched


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/coordination/tests/test_ak_gate.py -q")


# ------------------------------------------------------------------------------------------------ generator gaps (2026-11-25)
GAP_CORR = [{"kind": "selftest_bin", "runs": 2, "arms": ["ON", "OFF", "OFF2"], "timeout_s": 60, "env": {"GGML_HIP_Q8_SKINNY": "0"},
             "argv": [os.path.join(FIX_BIN, "test-q8ip-two-ctx"), "-m", "/m/x.gguf"],
             "mismatch_rx": r"summary: prompts=\d+ mismatches=(\d+)", "max_mismatch": {"ON": 0}}]


def test_gpu_gate_row_regions_units_zero_publish_and_preflight_warnings(tmp_path, monkeypatch):
    import publish_row as PR
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    d, spec_ = gen_row(tmp_path, rid="ak-t-gate-gpu-20261125-r2", extra=["--lower-is-better"])
    assert spec_["regions"] == "mi210_0,88-95,184-191" and spec_["claim_cpus"] == "88-95,184-191"   # the published GPU shape
    assert spec_["estimate_basis"]["units"] == 27 and spec_["estimate_basis"]["provisional"] is True
    flags = tmp_path / "flags"
    (flags / "dryrun").mkdir(parents=True)
    (flags / "ready").mkdir()
    res = P.run(spec_, row_dir=str(d), flags=str(flags), queued={}, run_selftest=True)
    assert not [f for f in res if f[1] in ("FAIL", "WARN")], res
    sp = dict(spec_)
    PR.check_smoke_estimate(sp)
    PR.lint(sp)
    assert not sp.get("publish_warnings"), sp.get("publish_warnings")


def test_cpu_gate_row_keeps_its_bare_claim(tmp_path):
    d, spec_ = gen_row(tmp_path, rid="ak-t-gate-cpu-20261125", extra=["--lane", "cpu", "--claim", "0-7"])
    assert spec_["regions"] == "0-7" and spec_["claim_cpus"] == "0-7"


def test_direction_flags_assert_the_metric_direction(tmp_path):
    base = ["gate", "new", "--no-rehearse", "--task", "x.md:T", "--root", str(tmp_path), "--knob", "GGML_A:A ran", "--arm", "OFF:", "--arm",
            "OFF2:", "--arm", "ON:GGML_A=1", "--keep-rule", "ci_lower>1.01", "--prompt", "p", "--server-argv-json",
            json.dumps([os.path.join(FIX_BIN, "llama-server"), "-m", "/m/x.gguf", "--port", "{PORT}"])]
    assert MK.main(base + ["--id", "ak-d1-gpu-20261125", "--metric", "ms_per_round", "--lower-is-better"]) == 0
    assert MK.main(base + ["--id", "ak-d2-gpu-20261125", "--metric", "tok_s", "--higher-is-better"]) == 0
    with pytest.raises(SystemExit, match="contradicts"):
        MK.main(base + ["--id", "ak-d3-gpu-20261125", "--metric", "tok_s", "--lower-is-better"])


def test_per_unit_and_per_arm_env_are_applied_to_the_subprocess_env(tmp_path):
    d, spec_ = gen_row(tmp_path, rid="ak-t-gate-gpu-20261125-r3",
                       extra=["--correctness", json.dumps(GAP_CORR), "--arm-env", "ON:LLAMA_PER_ARM=7"])
    import importlib.util
    spc = importlib.util.spec_from_file_location("gate_job_under_test", str(d / "job.py"))
    mod = importlib.util.module_from_spec(spc)
    sys.path.insert(0, str(d))
    try:
        spc.loader.exec_module(mod)
    finally:
        sys.path.remove(str(d))
        sys.modules.pop("ak_gate_vendored", None)
    ns = {"SPEC": mod.SPEC}
    sp = ns["SPEC"]
    assert sp["arm_env"] == {"ON": {"LLAMA_PER_ARM": "7"}} and sp["correctness"][0]["env"] == {"GGML_HIP_Q8_SKINNY": "0"}
    g = G.Gate(sp, str(d), env={"FILLER_PORTS": "1"})
    unit = g.proc_env("ON", "/s/bin/x", sp["correctness"][0]["env"])
    assert unit["GGML_HIP_Q8_SKINNY"] == "0" and unit["LLAMA_PER_ARM"] == "7"
    off = g.proc_env("OFF", "/s/bin/x")
    assert "LLAMA_PER_ARM" not in off and "GGML_HIP_Q8_SKINNY" not in off
    with pytest.raises(G.SpecError, match="declared knob"):
        G.validate_spec(dict(sp, arm_env={"ON": {"GGML_HIP_Q8MC": "1"}}))


def test_job_cli_flags_are_not_server_flags_and_vendored_gate_smoke_is_accepted(tmp_path):
    argvs = [("job.py", 1, ["/s/llama-server", "--replay", "--decide-from", "-m", "x"])]
    assert P.argv_flags(argvs) == {"-m"}
    d, _ = gen_row(tmp_path, rid="ak-t-gate-gpu-20261125-r4")
    own = {"job.py": (d / "job.py").read_text() + "\n# TERMINAL-smoke\n"}
    assert LINT.smoke_checks(str(d), {}, own) == []


def test_q8wt_tbo_unit_without_lv_is_exempt_from_witness_but_server_unit_still_fails():
    """ak-c22-q8wt-gate-gpu-20261125: test-backend-ops takes no -lv, so the OFF tbo log can never carry the V5I_INPLACE INFO
    line; the harness used to call that FUTILITY_HARNESS_WITNESS. A served unit missing its witness must still fail."""
    k = {"GGML_HIP_Q8_MF": {"marker": "q8wt design 6 throttled packed path ran", "level": 4},
         "V5I_INPLACE": {"marker": "ggml_cuda_q8ip: in-place Q8_0 stage-contiguous repack enabled", "level": 4}}
    sp = spec(k, {"OFF": {}, "Q8WT": {"GGML_HIP_Q8_MF": "7"}, "OFF2": {}})
    sp["expect"] = {"OFF": {"GGML_HIP_Q8_MF": "absent", "V5I_INPLACE": "present"},
                    "Q8WT": {"GGML_HIP_Q8_MF": "present", "V5I_INPLACE": "present"},
                    "OFF2": {"GGML_HIP_Q8_MF": "absent", "V5I_INPLACE": "present"}}
    txt = G.read_log(os.path.join(FIX, "q8wt", "c-tbo-OFF-head.log"))
    assert G.witness_for(sp, "OFF", txt, None, "c-tbo-OFF.log", "tbo") == {}
    assert not G.mismatches([{"unit_id": "c-tbo-OFF", "arm": "OFF", "witness": G.witness_for(sp, "OFF", txt, None, "x", "tbo")}])
    w = G.witness_for(sp, "OFF", txt, ["llama-server", "-lv", "4"], "smoke.log", "served")   # server unit: still a miss
    assert not w["V5I_INPLACE"]["ok"]
    sp["expect_by_unit"] = {"tbo": {"OFF": {"V5I_INPLACE": "present"}}}                     # explicit opt-in is honoured
    assert not G.witness_for(sp, "OFF", txt, None, "x", "tbo")["V5I_INPLACE"]["ok"]


def test_tbo_return_code_default_and_explicit_opt_out(capsys):
    c = {"kind": "tbo", "argv": [os.path.join(FIX_BIN, "test-backend-ops")]}
    u = {"arm": "ON", "rc": 0, "n_cases": 1, "n_ok": 1, "n_fail": 0}
    assert G.tbo_pass(c, u)
    assert not G.tbo_pass(c, dict(u, rc=139))
    assert not G.tbo_pass(c, dict(u, rc=None))
    assert not G.tbo_pass(dict(c, require_rc0=True), dict(u, rc=139))
    assert G.tbo_pass(dict(c, require_rc0=False), dict(u, rc=139))
    assert not G.tbo_pass(dict(c, require_rc0=False), dict(u, rc=139, n_fail=1))
    for invalid in (None, 0, 1, "false"):
        with pytest.raises(G.SpecError, match="require_rc0 must be a boolean"):
            G.validate_spec(spec(correctness=[dict(c, require_rc0=invalid)]))
    assert G.validate_spec(spec(correctness=[dict(c, require_rc0=False)]))
    assert "WARNING" in capsys.readouterr().err
    assert G.validate_spec(spec(correctness=[c]))
    assert not capsys.readouterr().err


def test_knee_batch_tbo_not_supported_is_skipped_and_failing_baseline_is_harness():
    """ak-c22-knee-batch-gate-gpu-20261125-r3: OFF itself ended 1744/2085 ok with rc 0 because 'not supported [ROCm0]' lines
    were counted as failures. Skipped is not failed; a baseline that fails is a harness verdict, never FAIL_CORRECTNESS."""
    txt = open(os.path.join(FIX, "knee", "c-tbo-OFF-excerpt.log"), errors="replace").read()
    cases = G.H.tbo_cases(G.ANSI.sub("", txt))
    cnt = G.tbo_counts(cases)
    assert cnt["n_skipped"] >= 5 and cnt["n_fail"] == 0 and cnt["n_ok"] == cnt["n_cases"] > 0 and not cnt["fails"]
    c = {"kind": "tbo", "require_rc0": True, "min_cases": 1}
    u = dict(cnt, arm="OFF", rc=0)
    assert G.tbo_pass(c, u)
    assert not G.tbo_pass(c, dict(u, rc=1))
    assert not G.tbo_pass(c, dict(u, n_fail=1, n_ok=u["n_ok"]))   # an explicit FAIL always fails
    f = G.H.tbo_cases(G.ANSI.sub("", "  MUL_MAT(a=1): \x1b[1;31mFAIL\x1b[0m\n"))
    assert f[0]["ok"] is False and not f[0]["skipped"]
    sp = spec({"K": {"marker": "m", "level": 4}}, {"OFF": {}, "ON": {"K": "1"}})
    sp["baseline"] = ["OFF"]
    sp["correctness"] = [dict(c, arms=["OFF", "ON"])]
    okc = dict(unit_id="c-tbo-ON", kind="c-tbo", arm="ON", rc=0, n_cases=3, n_ok=3, n_fail=0, n_skipped=2, fails=[])
    badc = dict(okc, unit_id="c-tbo-OFF", arm="OFF", n_ok=1, n_fail=2)
    v, det, done = G._decide_one(sp, sp["correctness"][0], [dict(okc, unit_id="c-tbo-OFF", arm="OFF"), okc])
    assert v is None and done
    v, det, done = G._decide_one(sp, sp["correctness"][0], [badc, okc])
    assert v == "FUTILITY_HARNESS_BASELINE" and done                    # OFF fails -> harness, never FAIL_CORRECTNESS
    v, det, done = G._decide_one(sp, sp["correctness"][0], [dict(okc, unit_id="c-tbo-OFF", arm="OFF"), dict(okc, n_ok=1, n_fail=2)])
    assert v == "FAIL_CORRECTNESS"                                      # candidate fails while OFF passes


def test_sampler_request_body_paired_across_arms(tmp_path):
    sp = spec(sampler={"temperature": 0.3, "top_k": 20, "top_p": 0.95}, seed_base=4242)
    g = G.Gate(sp, str(tmp_path), env={"FILLER_PORTS": "1"}, stream=QUIET)
    g.prepare()
    bodies = []
    g.start_server = lambda *args: object()
    g.wait_ready = lambda *args: None
    g.stop_server = lambda *args: None
    g.request = lambda port, body, timeout: (bodies.append(body) or {}, {})
    for arm in ("OFF", "ON"):
        g._visit(arm, arm, ["first", "second"], 8, 0, 1)
    assert [b["seed"] for b in bodies] == [4242, 4243, 4242, 4243]
    assert all((b["temperature"], b["top_k"], b["top_p"]) == (0.3, 20, 0.95) for b in bodies)
    assert G.request_body(spec(), "x", 1)["top_k"] == 1
    assert G.request_body(sp, "x", 1, {"temperature": 1.0})["temperature"] == 1.0
    with pytest.raises(G.SpecError):
        G.validate_spec(spec(sampler={"top_p": 2}))


def test_generator_multi_sampler_and_report_only_load(tmp_path):
    d, _ = gen_row(tmp_path, extra=["--sampler", "T=0.3,top_k=20,top_p=0.95", "--sampler", "T=1.0,top_k=20",
                                     "--seed-base", "4242", "--load-unit", '{"arms":["OFF","ON"],"blocks":2,"concurrency":4}'])
    import importlib.util
    modspec = importlib.util.spec_from_file_location("gate_sampler_job", str(d / "job.py"))
    mod = importlib.util.module_from_spec(modspec)
    sys.path.insert(0, str(d))
    try:
        modspec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(d))
        sys.modules.pop("ak_gate_vendored", None)
    sp = mod.SPEC
    assert sp["seed_base"] == 4242 and [p["temperature"] for p in sp["sampler"]] == [0.3, 1.0]
    g = G.Gate(sp, str(d), env={"FILLER_PORTS": "1"}, stream=QUIET)
    calls = []
    g.visit_fn = visit_stub(sp, g.out, {"ON": 1.2}, calls)
    assert g.run() == 0
    units = G.load_units(g.out)
    assert {u["sampler_index"] for u in units if u["kind"] == "visit"} == {0, 1}
    report = [u for u in units if u["kind"] == "load"]
    assert len(report) == 4 and all(u["report_only"] for u in report)
    result = json.load(open(os.path.join(g.out, "RESULT.json")))
    assert len(result["report_only"]) == 4 and len(result["sampler_results"]) == 2
    bad = dict(report[0], kind="visit", error="broken", report_only=True)
    assert G.decide(sp, units + [bad])["verdict"] == G.decide(sp, units)["verdict"]
    replayed, _, _ = G.replay_units(sp, g.out, str(d))
    assert not any(u.get("report_only") or u["kind"] == "load" for u in replayed)
    with pytest.raises(G.SpecError):
        G.validate_spec(dict(sp, units=[{"kind": "load", "arms": ["UNKNOWN"]}]))


@pytest.mark.parametrize("kind", ["env", "observe"])
def test_marker_colon_level_typo_is_refused(kind):
    message = "REFUSED: knob GGML_A marker ends in ':<n>' - the level separator is '::'. FIX: --knob 'GGML_A:<marker>::<n>'"
    with pytest.raises(SystemExit) as exc:
        MK.parse_knob("GGML_A:path ran:42", kind=kind)
    assert str(exc.value) == message
    with pytest.raises(G.SpecError) as exc:
        G.validate_spec(spec(knobs={"GGML_A": {"kind": kind, "marker": "path ran:42"}}))
    assert message in str(exc.value)
    assert MK.parse_knob("GGML_A:path:42 ran::5", kind=kind)[1]["marker"] == "path:42 ran"
    with pytest.raises(SystemExit):
        MK.parse_knob("GGML_A:path:42::5", kind=kind)


def test_correctness_arms_require_each_baseline():
    sp = spec(correctness={"kind": "identity", "arms": ["ON"]})
    with pytest.raises(G.SpecError, match="FIX: add OFF to the unit's arms"):
        G.validate_spec(sp)


def test_missing_identity_baseline_writes_result(tmp_path):
    sp = spec(correctness={"kind": "identity", "arms": ["ON"]})
    units = [{"unit_id": "c-id-ON-p0", "kind": "c-id", "arm": "ON", "prompt": 0}]
    sp["correctness"]["arms"] = ["OFF", "OFF2", "ON"]
    g = G.Gate(sp, str(tmp_path), env={"FILLER_PORTS": "1"}, stream=QUIET)
    sp["correctness"]["arms"] = ["ON"]
    os.makedirs(g.out, exist_ok=True)
    g.finish(units, G.decide(sp, units))
    res = json.loads((tmp_path / "out" / "RESULT.json").read_text())
    assert res["verdict"] == "FUTILITY_HARNESS_NO_BASELINE"
    assert "OFF" in res["reason"] and "identity" in res["reason"]


def test_decide_exception_writes_result(tmp_path, monkeypatch):
    sp = spec(correctness={"kind": "identity"})
    def fail(*args):
        raise ValueError("injected")
    monkeypatch.setattr(G, "_plan_one", fail)
    g = G.Gate(sp, str(tmp_path), env={"FILLER_PORTS": "1"}, stream=QUIET)
    os.makedirs(g.out, exist_ok=True)
    g.finish([], G.decide(sp, []))
    res = json.loads((tmp_path / "out" / "RESULT.json").read_text())
    assert res["verdict"] == "FUTILITY_HARNESS_DECIDE"
    assert "ValueError: injected" in res["reason"] and "identity" in res["reason"]

# Predecessor reuse uses the same durable ledger as resume, with a content-bound key.
def _reuse_rows(tmp_path):
    binary = tmp_path / "kernel"
    binary.write_text("kernel v1")
    binary.chmod(0o755)
    sp = spec(argv=[str(binary), "--port", "{PORT}"],
              correctness={"kind": "tbo", "argv": [str(binary)], "min_cases": 1})
    rows = []
    for name in ("old", "new"):
        row = tmp_path / name
        row.mkdir()
        for f in ("ak_gate.py", "ak_row_harness.py"):
            shutil.copy(os.path.join(_ROWFLOW, f), row / f)
        (row / "spec.json").write_text(json.dumps({"supersedes": "old"} if name == "new" else {}))
        gate = G.Gate(sp, str(row), env={}, stream=QUIET)
        gate.prepare()
        rows.append(gate)
    return sp, binary, rows


def test_predecessor_exact_match_and_provenance(tmp_path):
    import io
    sp, _, (old, new) = _reuse_rows(tmp_path)
    for uid, kind, arm, extra in G.plan_correctness(sp):
        u = {"unit_id": uid, "kind": kind, "arm": arm, "rc": 0, "pass": True,
             "n_cases": 1, "n_ok": 1, "n_fail": 0, "gate_unit": True}
        old.mark_reusable(u, extra)
        H.append_unit(u, old.out)
    calls = []
    new.stream = io.StringIO()
    new.run_correctness_unit = lambda *args: pytest.fail("reused unit ran")
    new.visit_fn = visit_stub(sp, new.out, calls=calls)
    assert new.run() == 0
    records = G.load_units(new.out)
    reused = [u for u in records if u.get("reused_from")]
    assert len(reused) == 3 and all(u["reused_from"] == "old" for u in reused)
    assert "UNIT-REUSED c-tbo-ON from old" in new.stream.getvalue()
    assert len([u for u in json.load(open(os.path.join(new.out, "RESULT.json")))["units"] if u.get("reused_from")]) == 3
    assert calls  # timing units still execute


@pytest.mark.parametrize("change", ["kernel_path", "kernel_sha", "knob", "arm_env", "unit_env", "prompt", "argv", "kind_params", "gate_sha", "harness_sha", "partial", "crash"])
def test_predecessor_key_mismatch_reruns(tmp_path, change):
    import copy
    sp, binary, (old, new) = _reuse_rows(tmp_path)
    u = {"unit_id": "c-tbo-ON", "kind": "c-tbo", "arm": "ON", "rc": 0, "pass": True,
         "n_cases": 1, "n_ok": 1, "n_fail": 0, "gate_unit": True}
    old.mark_reusable(u, {})
    if change == "partial":
        u.pop("unit_verdict")
    if change == "crash":
        u["rc"] = 139
    H.append_unit(u, old.out)
    new.spec = copy.deepcopy(sp)
    if change == "kernel_path":
        other = tmp_path / "other"
        shutil.copy(binary, other)
        new.spec["server"]["argv"][0] = str(other)
    elif change == "kernel_sha":
        binary.write_text("kernel v2")
    elif change == "knob":
        new.spec["arms"]["ON"]["GGML_HIP_Q8MC"] = "2"
    elif change == "arm_env":
        new.spec["arm_env"] = {"ON": {"X": "2"}}
    elif change == "unit_env":
        new.spec["correctness"]["env"] = {"X": "2"}
    elif change == "prompt":
        new.spec["workload"]["prompts"] = ["different"]
    elif change == "argv":
        new.spec["server"]["argv"].append("--different")
    elif change == "kind_params":
        new.spec["correctness"]["min_cases"] = 2
    elif change in ("gate_sha", "harness_sha"):
        with open(os.path.join(new.d, "ak_gate.py" if change == "gate_sha" else "ak_row_harness.py"), "a") as f:
            f.write("# change\n")
    assert new.reuse_unit("c-tbo-ON", "c-tbo", "ON", {}) is None
    assert not G.load_units(new.out)


def test_smoke_reuse_and_no_timing_reuse(tmp_path):
    sp, _, (old, new) = _reuse_rows(tmp_path)
    calls = []
    old.run_correctness_unit = new.run_correctness_unit = lambda uid, kind, arm, extra: {"unit_id": uid, "kind": kind, "arm": arm, "rc": 0, "n_cases": 1, "n_ok": 1, "gate_unit": True}
    old.visit_fn = visit_stub(sp, old.out, calls=calls)
    assert old.smoke() == 0
    new.visit_fn = lambda *args, **kwargs: pytest.fail("smoke should reuse")
    assert new.smoke() == 0
    assert G.load_units(new.out)[0]["reused_from"] == "old"
    assert json.load(open(os.path.join(new.out, "RESULT.json")))["units"][0]["reused_from"] == "old"
    timing = {"unit_id": "b1-ON", "kind": "visit", "arm": "ON", "gate_unit": True,
              "unit_verdict": "PASS", "reuse_key": "anything"}
    H.append_unit(timing, old.out)
    assert new.reuse_unit("b1-ON", "visit", "ON", {}) is None


def test_kld_noise_arm_is_report_only_and_sets_floor():
    arms = {"OFF": {}, "OFF2": {}, "ON": {"GGML_HIP_Q8MC": "1"}, "NOISE": {}}
    kld = {"kind": "kld", "argv": [os.path.join(FIX_BIN, "llama-perplexity")], "arms": ["OFF", "OFF2", "ON"],
           "max_kld": 0.001, "max_kld_noise_k": 3, "noise_arm": "NOISE"}
    identity = {"kind": "identity", "arms": list(arms)}
    sp = spec(arms=arms, baseline=["OFF", "OFF2"], candidates=["ON", "NOISE"], correctness=[kld, identity])
    G.validate_spec(sp)
    assert G.candidate_arms(sp) == ["ON"]
    assert G.arm_list(sp) == ["OFF", "ON", "OFF2"]
    plan = G.plan_correctness(sp)
    assert sum(arm == "NOISE" and kind == "c-kld" for _, kind, arm, _ in plan) == 1
    assert all(arm != "NOISE" for _, kind, arm, _ in plan if kind == "c-id")
    units = [dict(unit_id=uid, kind=kind, arm=arm, **extra,
                  mean_kld={"OFF": 0.0, "OFF2": 0.0, "ON": 0.005, "NOISE": 0.002}.get(arm))
             for uid, kind, arm, extra in G._plan_one(sp, kld)]
    verdict, detail, done = G._decide_one(sp, kld, units)
    assert verdict is None and done
    assert detail["max_kld"] == 0.006 and detail["noise_kld"] == 0.002
    assert detail["kld_floor_source"] == "NOISE"
    doc = G.result_doc(sp, units, {"verdict": "INCOMPLETE", "correctness": detail})
    assert doc["correctness"]["noise_kld"] == 0.002
    assert doc["aa"]["arms"] == ["OFF", "OFF2"]
    kld["max_kld_noise_k"] = 0.25
    units[-2]["mean_kld"] = 0.0005
    assert G._decide_one(sp, kld, units)[0] is None  # noise exceeds the floor but is never judged
    units[-2]["mean_kld"] = 0.005
    kld["max_kld_noise_k"] = 3
    units[-1]["mean_kld"] = None
    assert G._decide_one(sp, kld, units)[0] == "FUTILITY_HARNESS_MISSING_OUTPUT"
    del kld["noise_arm"]
    verdict, detail, _ = G._decide_one(sp, kld, units)
    assert verdict == "FAIL_CORRECTNESS" and detail["kld_floor_source"] == "OFF2"
    assert detail["noise_kld"] == 0.0 and detail["max_kld"] == 0.001


@pytest.mark.parametrize("noise", ["MISSING", "OFF", "OFF2"])
def test_kld_noise_arm_must_be_declared_nonbaseline(noise):
    sp = spec(correctness={"kind": "kld", "argv": [os.path.join(FIX_BIN, "llama-perplexity")], "noise_arm": noise})
    with pytest.raises(G.SpecError, match="noise_arm"):
        G.validate_spec(sp)


@pytest.mark.parametrize("wrapper", [[], ["env", "A=1"], ["taskset", "-c", "84-87"],
                                     ["numactl", "--membind=0", "--", "env", "A=1"]])
def test_validate_executable_server_and_correctness(tmp_path, wrapper):
    binary = tmp_path / "missing"
    sp = spec(argv=wrapper + [str(binary), "--port", "{PORT}"],
              correctness={"kind": "kld", "argv": wrapper + [str(binary)]})
    with pytest.raises(G.SpecError) as exc:
        G.validate_spec(sp)
    msg = str(exc.value)
    assert "server:" in msg and "correctness kld:" in msg and str(binary) in msg
    assert msg.count("FIX: point argv[0] at an existing binary in the store") == 2
    binary.write_text("stub")
    with pytest.raises(G.SpecError):
        G.validate_spec(sp)
    binary.chmod(0o755)
    assert G.validate_spec(sp)


def test_selftest_excludes_noise_arm_from_keep(tmp_path):
    import io
    arms = {"OFF": {}, "OFF2": {}, "ON": {"GGML_HIP_Q8MC": "1"}, "NOISE": {}}
    sp = spec(arms=arms, baseline=["OFF", "OFF2"],
              correctness={"kind": "kld", "argv": [os.path.join(FIX_BIN, "llama-perplexity")], "noise_arm": "NOISE"})
    output = io.StringIO()
    assert G.selftest(sp, str(tmp_path), stream=output) == 0
    assert "KEEP_ON" in output.getvalue() and "NOISE" not in output.getvalue()


def test_generated_declaration_rejects_missing_correctness_binary(tmp_path):
    missing = str(tmp_path / "missing-perplexity")
    with pytest.raises(G.SpecError, match="correctness kld.*missing-perplexity.*FIX: point argv"):
        gen_row(tmp_path, extra=["--correctness", json.dumps({"kind": "kld", "argv": [missing]})])


def test_validate_command_uses_path_and_load_override(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", FIX_BIN)
    assert G.validate_spec(spec(argv=["llama-server", "--port", "{PORT}"]))
    sp = spec(units=[{"kind": "load", "arms": ["ON"], "argv": ["env", "X=1", str(tmp_path / "missing"), "{PORT}"]}])
    with pytest.raises(G.SpecError, match="load unit server.*missing.*FIX: point argv"):
        G.validate_spec(sp)


def test_smoke_residency_floor_reports_measured_footprint(tmp_path):
    sp = spec()
    sp["server"]["kfd_min_vram_gib"] = 8
    row = tmp_path / "row"
    row.mkdir()
    g = G.Gate(sp, str(row))
    stub = visit_stub(sp, str(row / "out"))
    def visit(*args, **kwargs):
        return dict(stub(*args, **kwargs), vram_b=2 * (1 << 30))
    g.visit_fn = visit
    assert g.smoke() == 3
    terminal = json.loads((row / "out" / H.TERMINAL_SMOKE).read_text())
    assert terminal["verdict"] == "FUTILITY_HARNESS_RESIDENCY"
    assert "server.kfd_min_vram_gib" in terminal["fix"]
    assert str(2 * (1 << 30)) in terminal["reason"]
    assert terminal["failclass"]["side"] == "harness"


def test_smoke_checks_witness_on_each_arm(tmp_path):
    sp = spec()
    row = tmp_path / "row"
    row.mkdir()
    g = G.Gate(sp, str(row))
    stub = visit_stub(sp, str(row / "out"))
    def visit(uid, arm, *args, **kwargs):
        u = stub(uid, arm, *args, **kwargs)
        if arm == "OFF2":
            with open(row / "out" / u["log"], "a") as f:
                f.write("\n" + Q8MC_ARMED + "\n")
        return u
    g.visit_fn = visit
    assert g.smoke() == 3
    result = json.loads((row / "out" / H.TERMINAL_SMOKE).read_text())
    assert result["verdict"] == "FUTILITY_HARNESS_WITNESS"
    assert "OFF2" in result["reason"]
    assert "expect." in result["fix"]


def test_smoke_identity_aa_uses_full_judge(tmp_path):
    sp = spec(correctness={"kind": "identity", "mode": "server", "n_prompts": 2})
    sp["workload"]["prompts"] = ["one", "two"]
    row = tmp_path / "row"
    g = G.Gate(sp, str(row), stream=QUIET)
    g.visit_fn = visit_stub(sp, g.out)
    seen = []
    def correctness(uid, kind, arm, extra):
        seen.append((arm, extra["prompt"]))
        return {"unit_id": uid, "kind": kind, "arm": arm, "prompt": extra["prompt"],
                "output_sha": "different" if arm == "OFF2" else "same", "accepted_sha": "a", "draft_sha": "d"}
    g.run_correctness_unit = correctness
    assert g.smoke() == 3
    result = json.loads((row / "out" / H.TERMINAL_SMOKE).read_text())
    assert result["verdict"] == "FUTILITY_HARNESS_NONDET"
    assert "correctness.identity" in result["fix"]
    assert seen == [("OFF", 0), ("OFF2", 0), ("ON", 0)]


def test_smoke_kld_missing_binary_is_harness_failure(tmp_path):
    sp = spec(correctness={"kind": "kld", "argv": [os.path.join(FIX_BIN, "llama-perplexity")]})
    g = G.Gate(sp, str(tmp_path / "row"), stream=QUIET)
    g.visit_fn = visit_stub(sp, g.out)
    def missing(*args):
        raise FileNotFoundError("missing binary")
    g.run_fn = missing
    assert g.smoke() == 3
    result = json.loads((tmp_path / "row" / "out" / H.TERMINAL_SMOKE).read_text())
    assert result["verdict"] == "FUTILITY_HARNESS_MISSING_OUTPUT"
    assert "correctness.<kind>.argv" in result["fix"]
