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
         "server": {"argv": argv or ["/x/bin/llama-server", "--port", "{PORT}"], "env": {}, "warmup": 1,
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
    w = G.witness_for(sp, "ON", txt, ["/s/bin/llama-perplexity", "-m", "m.gguf", "-f", "inputs/kld_text.txt"])
    assert not w["GGML_HIP_Q8MC"]["ok"] and "argv log level none < required 4" in w["GGML_HIP_Q8MC"]["note"]
    assert G.witness_for(sp, "ON", txt)["GGML_HIP_Q8MC"]["note"].startswith("no 'verbosity = N' banner")
    tbo = G.read_log(os.path.join(FIX, "q8mc", "c-tbo-on.log"))
    assert G.witness_for(sp, "ON", tbo)["GGML_HIP_Q8MC"]["ok"]


def test_ensure_lv_on_every_llama_binary():
    assert G.ensure_lv(["/s/bin/llama-perplexity", "-m", "x"], 4)[-2:] == ["-lv", "4"]
    assert G.ensure_lv(["/s/bin/llama-server", "-lv", "2"], 4) == ["/s/bin/llama-server", "-lv", "4"]
    assert G.ensure_lv(["/s/bin/llama-bench", "--verbosity=1"], 5) == ["/s/bin/llama-bench", "--verbosity=5"]
    assert G.ensure_lv(["/s/bin/llama-cli", "-lv", "6"], 4) == ["/s/bin/llama-cli", "-lv", "6"]
    assert G.ensure_lv(["/s/bin/test-backend-ops", "test"], 4) == ["/s/bin/test-backend-ops", "test"]
    assert G.ensure_lv(["/s/bin/test-dflash-dev-inject"], 4)[-2:] == ["-lv", "4"]
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
    with pytest.raises(G.SpecError, match="fresh_server_starts"):
        G.validate_spec(spec(fresh_server_starts=2))
    assert G.validate_spec(spec())


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
    sp = spec(argv=["/nonexistent/bin/llama-server", "--port", "{PORT}", "--slot-save-path", "{SLOTDIR}"],
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
    assert [u["arm"] for u in G.load_units(str(row / "out-smoke"))] == ["ON"]   # ON arm only
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
    sp = spec(correctness={"kind": "kld", "argv": ["/s/bin/llama-perplexity", "-m", "m", "-f", "inputs/kld_text.txt"]})
    noflag = ["/s/bin/llama-perplexity", "-m", "m", "-f", "inputs/kld_text.txt"]
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
    rec = G.replay(sp, str(new), str(prior), flags=str(tmp_path / "flags"), stream=QUIET)
    assert rec["verdict"] == "FUTILITY_HARNESS_WITNESS" and rec["mode"] == "units"
    assert "knob GGML_HIP_Q8MC arm ON unit c-kld-ON" in rec["observed"]["reason"] and "argv log level none" in \
        rec["observed"]["reason"]
    assert json.loads((new / "out" / G.RECEIPT).read_text())["logs_sha256"] == G.logs_sha256(str(prior))[0]


def test_replay_tailfuse2_logs_only_six_vs_five_knobs(tmp_path):
    prior = _prior(tmp_path, "ak-tf2-prior", logs=[("tailfuse2/smoke-ALL-server.log", "smoke-ALL-server.log")])
    six = spec({k: {"marker": m, "level": 4} for k, m in TF2.items()}, {"OFF": {}, "OFF2": {}, "ALL": {k: "1" for k in TF2}})
    r = G.replay(six, str(tmp_path / "n6"), str(prior), write_receipt=False, stream=QUIET)
    assert r["mode"] == "logs-only" and r["verdict"] == "FUTILITY_HARNESS_WITNESS"
    assert [m["knob"] for m in r["witness_mismatches"]] == ["GGML_CUDA_AK_TF2_G5"]
    five = {k: m for k, m in TF2.items() if not k.endswith("G5")}
    r = G.replay(spec({k: {"marker": m, "level": 4} for k, m in five.items()},
                      {"OFF": {}, "OFF2": {}, "ALL": {k: "1" for k in five}}), str(tmp_path / "n5"), str(prior),
                 write_receipt=False, stream=QUIET)
    assert r["verdict"] == "SMOKE_PASS", r["observed"]


def test_replay_devhandoff_draft_diff_output_equal(tmp_path):
    """r5: drafts differ at round 9 OFF vs ON (separate processes) with identical accepted counts and output."""
    c = {"kind": "identity", "mode": "cmd", "argv": ["/s/bin/test-dflash-dev-inject"], "n_prompts": 1,
         "arms": ["OFF", "ON"]}
    sp = spec(knobs={"LLAMA_DFLASH_DEV_INJECT": {"marker": INJ, "level": 4}},
              arms={"OFF": {}, "OFF2": {}, "ON": {"LLAMA_DFLASH_DEV_INJECT": "1"}}, correctness=c)
    units = [{"unit_id": f"c-id-{a}-p0", "kind": "c-id", "arm": a, "prompt": 0, "argv": ["test-dflash-dev-inject", "-lv", "4"],
              "rc": 0, "log": f"logs/c-id-{a}-p0.log"} for a in ("OFF", "ON")]
    prior = _prior(tmp_path, "ak-dh-prior", units, [("devhandoff/c-unit-inj-sel-p0-off.log", "c-id-OFF-p0.log"),
                                                    ("devhandoff/c-unit-inj-sel-p0-on.log", "c-id-ON-p0.log")])
    r = G.replay(sp, str(tmp_path / "n"), str(prior), write_receipt=False, stream=QUIET)
    assert r["verdict"] == "INCOMPLETE", r["observed"]                    # correctness passed; no timing units recorded
    r = G.replay(dict(sp, correctness=dict(c, strict_drafts=True)), str(tmp_path / "n2"), str(prior), write_receipt=False,
                 stream=QUIET)
    assert r["verdict"] == "FAIL_CORRECTNESS" and "draft" in r["observed"]["reason"]


# ------------------------------------------------------------------------------------------------ generator + preflight
def make_store(base, knobs_and_markers):
    root = base / "kernels" / "builds" / "gpu-20261125-abcdef123-gate"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "llama-server").write_text("\n".join(["-m", "--port", "-lv", "-np", "-c", "-ngl"]) + "\n")
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
    rc = MK.main(["gate", "new", "--id", rid, "--task", "x.md:T", "--model", "Qwen3.8-27B-Q8_0", "--root", str(root),
                  "--knob", f"GGML_HIP_Q8MC:{Q8MC_ARMED}:4", "--arm", "OFF:", "--arm", "OFF2:", "--arm", "ON:GGML_HIP_Q8MC=1",
                  "--metric", "ms_per_round", "--lower-is-better", "--keep-rule", "ci_lower>1.01,n=8,look=4,aa=0.02",
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
    assert spec_["fresh_server_per_visit"] is True and spec_["fresh_server_starts"] == 9
    assert {"out/logs", "out/prof", "out/servers/*.log"} <= set(spec_["keep"])          # evidence kept on FAIL/FUTILITY
    assert spec_["evidence"]["verdicts"] == ["FAIL_*", "FUTILITY_*"]
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


def test_gate_cli_refuses_contradicting_metric_direction(tmp_path):
    with pytest.raises(SystemExit, match="lower-is-better"):
        MK.main(["gate", "new", "--id", "ak-x-gpu-20261125", "--task", "x.md:T", "--model", "m", "--root", str(tmp_path),
                 "--knob", "GGML_A:A ran", "--arm", "OFF:", "--arm", "OFF2:", "--arm", "ON:GGML_A=1", "--metric",
                 "ms_per_round", "--higher-is-better", "--keep-rule", "ci_lower>1.01", "--server-argv-json",
                 '["/s/bin/llama-server", "--port", "{PORT}"]', "--prompt", "p"])
    assert MK.parse_knob("LLAMA_X:dflash2_dev_select: Q8-SERVED chain enabled:5") == (
        "LLAMA_X", {"kind": "env", "marker": "dflash2_dev_select: Q8-SERVED chain enabled", "level": 5, "cap": -1})


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


def test_receipt_required_after_failed_smoke_and_validated(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    flags, prev, prow = family(tmp_path)
    d, spec_ = gen_row(tmp_path, rid="ak-t-gate-gpu-20261125-r2")
    row = P.Row(spec_, str(d))
    got = P.check_replay_receipt(row, {"flags": str(flags)})
    assert [c for _l, c, _m in got] == ["REPLAY-RECEIPT-MISSING"] and "--replay" in got[0][2]
    # the new declaration replayed on the failed run's out/: same witness miss -> same class -> refused
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "job.py"), "--replay", str(prow)], capture_output=True,
                       text=True, env={"PATH": "/usr/bin:/bin", "ROWFLOW_FLAGS": str(flags)})
    assert p.returncode == 0, p.stderr
    rec = json.loads((d / "out" / G.RECEIPT).read_text())
    assert rec["prev_id"] == prev and rec["verdict"] == "FUTILITY_HARNESS_WITNESS"
    assert rec["prev_fail_sha256"] == P._sha256(str(flags / "dryrun" / prev / "FAIL-1.json"))
    got = P.check_replay_receipt(P.Row(spec_, str(d)), {"flags": str(flags)})
    assert [c for _l, c, _m in got] == ["REPLAY-RECEIPT-SAME-CLASS"] and "does not change the verdict" in got[0][2]
    # a fixed declaration (the marker the binary really prints) replays to SMOKE_PASS -> accepted
    (prow / "out" / "logs" / "smoke-ON.log").write_text(f"0.0 I cmn verbosity = 4\n0.1 I {Q8MC_ARMED} (M 2..8)\n")
    subprocess.run([sys.executable, "-I", "-B", str(d / "job.py"), "--replay", str(prow)], capture_output=True,
                   env={"PATH": "/usr/bin:/bin", "ROWFLOW_FLAGS": str(flags)}, check=True)
    assert json.loads((d / "out" / G.RECEIPT).read_text())["verdict"] == "SMOKE_PASS"
    assert P.check_replay_receipt(P.Row(spec_, str(d)), {"flags": str(flags)}) == []
    # bound to THIS failure: a changed launcher.out (another failure) makes the receipt stale
    (flags / "dryrun" / prev / "launcher.out").write_text("something else\n")
    got = P.check_replay_receipt(P.Row(spec_, str(d)), {"flags": str(flags)})
    assert "REPLAY-RECEIPT-STALE" in {c for _l, c, _m in got}
    # out/REPLAY-RECEIPT.json never trips STALE-OUT
    assert not [f for f in LINT.stale_out(str(d))]


def test_replay_decide_preflight_runs_the_new_decide_on_cpus_84_87(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    flags, prev, prow = family(tmp_path)
    d, spec_ = gen_row(tmp_path, rid="ak-t-gate-gpu-20261125-r2")
    ctx = {"flags": str(flags)}
    got = P.check_replay_decide(P.Row(spec_, str(d)), ctx)
    assert [c for _l, c, _m in got] == ["REPLAY-DECIDE-SAME-CLASS"]
    r = ctx["replay_decide"][spec_["id"]]
    assert r["observed"]["verdict"] == "FUTILITY_HARNESS_WITNESS" and r["prev_id"] == prev
    assert not (d / "out").exists()                                    # --decide-from writes nothing
    # the auto replay doubles as the R1 receipt once it reaches a different class
    (prow / "out" / "logs" / "smoke-ON.log").write_text(f"0.0 I cmn verbosity = 4\n0.1 I {Q8MC_ARMED}\n")
    ctx = {"flags": str(flags)}
    assert P.check_replay_decide(P.Row(spec_, str(d)), ctx) == []
    assert P.check_replay_receipt(P.Row(spec_, str(d)), ctx) == []
    # through publish_check, the replay lands in spec.preflight.replay_decide
    s = dict(spec_)
    P.publish_check(s, str(flags), warn=lambda w: None, queued={})
    assert s["preflight"]["replay_decide"]["observed"]["verdict"] == "SMOKE_PASS"
    assert "84-87" in " ".join(P.REPLAY_PIN)


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


def test_replay_checks_are_warn_first_and_publish_only():
    assert P.PREFLIGHT_ENFORCE["replay_receipt"] is False and P.PREFLIGHT_ENFORCE["replay_decide"] is False
    assert {"replay_receipt", "replay_decide"} <= set(P.PUBLISH_ONLY)
    assert P.CHECKS.index("replay_decide") < P.CHECKS.index("replay_receipt")
    assert "replay_receipt" not in P.DRIFT_CHECKS


def test_family_gate_receipt_unparks_and_enforce_switch(tmp_path, monkeypatch):
    """family_strikes.republish_allowed (R2 park) accepts a validated R1 receipt as the unpark reason; the R1 refusal
    applies only once PREFLIGHT_ENFORCE['replay_receipt'] is flipped."""
    import family_strikes as fs
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    flags, prev, prow = family(tmp_path)
    for i in range(fs.PARK_AT):
        fs.record_strike(str(flags), prev, "smoke", "witness miss", key=str(i), manifest={})
    d, spec_ = gen_row(tmp_path, rid="ak-t-gate-gpu-20261125-r2")
    ok, why = fs.republish_allowed(str(flags), spec_)
    assert not ok and why.startswith("PARKED")
    (prow / "out" / "logs" / "smoke-ON.log").write_text(f"0.0 I cmn verbosity = 4\n0.1 I {Q8MC_ARMED}\n")
    subprocess.run([sys.executable, "-I", "-B", str(d / "job.py"), "--replay", str(prow)], capture_output=True,
                   env={"PATH": "/usr/bin:/bin", "ROWFLOW_FLAGS": str(flags)}, check=True)
    assert fs.republish_allowed(str(flags), spec_)[0]                  # valid receipt = one attempt past the park
    os.remove(d / "out" / G.RECEIPT)
    fs.record_clear(str(flags), prev, "PASS")                          # not parked, no receipt: WARN-first lets it through
    assert fs.republish_allowed(str(flags), spec_)[0]
    monkeypatch.setitem(P.PREFLIGHT_ENFORCE, "replay_receipt", True)
    ok, why = fs.republish_allowed(str(flags), spec_)
    assert not ok and "REPLAY-RECEIPT-MISSING" in why


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/coordination/tests/test_ak_gate.py -q")
