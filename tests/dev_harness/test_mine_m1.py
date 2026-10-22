"""Mining wave M1 (DHM-1, DHM-5, OAB-LB1, UFH14-LB8) over synthetic fixtures.

Every fixture is built at runtime (json.dumps / sqlite3) so no transcript-shaped line is staged.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/dev_harness"))

import dh_privacy  # noqa: E402
import mine_m1 as m  # noqa: E402


def jl(rows):
    return "".join(json.dumps(r) + "\n" for r in rows)


# ─── statistics ──────────────────────────────────────────────────────────────

def test_wilson_reference_values():
    lo, hi = m.wilson(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-4) and hi == pytest.approx(0.7634, abs=1e-4)
    lo, hi = m.wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-4)
    assert m.wilson(0, 0) == (0.0, 0.0)
    rb = m.rate_block(3, 1000)
    assert rb["per_1000"] == 3.0 and rb["ci95_lo"] < 3.0 < rb["ci95_hi"]


def test_dist_and_bimodality():
    d = m.dist([1, 2, 3, 4, 5])
    assert d["n"] == 5 and d["p50"] == 3.0 and d["min"] == 1.0 and d["max"] == 5.0
    assert m.dist([]) == {"n": 0}
    two_modes = [1.0] * 50 + [10.0] * 50
    assert m.bimodality_coefficient(two_modes) > 0.555
    assert m.log2_hist([0, 1, 3, 1024]) == {"le0": 1, "2^0": 1, "2^1": 1, "2^10": 1}


@pytest.mark.parametrize("cmd,exe", [
    ("rg -n foo src", "rg"),
    ("cd /x && FOO=1 nice -n 19 timeout 30 python3 a.py | tail", "python3"),
    (["bash", "-lc", "git status --short"], "git"),
    ("/usr/bin/cmake --build build", "cmake"),
    ("for f in a b; do echo $f; done", "shell_compound"),
    ("", "unknown"),
])
def test_executable_of(cmd, exe):
    assert m.executable_of(cmd) == exe


def test_classify_error():
    assert m.classify_error("Rate limit reached for requests") == "rate_limit"
    assert m.classify_error("stream disconnected before completion") == "stream_disconnect"
    assert m.classify_error("something odd") == "other"


# ─── DHM-1 / DHM-5 over a synthetic projection ───────────────────────────────

def _ev(h, uk, kind, ts, src_path, **d):
    return {"harness": h, "unit_key": uk, "event_kind": kind, "ts": ts,
            "source_path": src_path, "source_line": 1, "detail_json": d,
            "content": {"n_chars": d.pop("_chars", 0), "n_tokens": 0, "block_hashes": []}}


def _usage(h, uk, ts, sp, rid, inp, cr, out):
    return _ev(h, uk, "usage", ts, sp, **{"gen_ai.response.id": rid, "gen_ai.usage.input_tokens": inp,
                                          "gen_ai.usage.cache_read.input_tokens": cr,
                                          "gen_ai.usage.output_tokens": out, "dh.role": "assistant"})


@pytest.fixture()
def projection(tmp_path):
    proj = tmp_path / "proj"
    cpath = "/mnt/raid0/llm/cloud-llm-vault/epyc/claude/p/a.jsonl"
    xpath = "/mnt/raid0/llm/cloud-llm-vault/host/codex/2026/r.jsonl"
    opath = "/mnt/raid0/llm/opencode-db/epyc.db#session=s"
    sessions = [
        {"harness": "claude_code", "unit_key": "c1", "conversation_id": "c1", "parent_conversation_id": None,
         "source": "epyc", "source_path": cpath, "first_ts": "2026-10-01T00:00:00Z", "human_turns": 2},
        {"harness": "claude_code", "unit_key": "c1.agent-x", "conversation_id": "c1",
         "parent_conversation_id": "c1", "source_path": cpath, "first_ts": "2026-10-01T00:00:05Z",
         "human_turns": 0},
        {"harness": "codex", "unit_key": "k1", "conversation_id": "k1", "parent_conversation_id": "p0",
         "source_path": xpath, "first_ts": "2026-10-02T00:00:00Z", "human_turns": 0},
        {"harness": "opencode", "unit_key": "o1", "conversation_id": "o1", "parent_conversation_id": None,
         "source_path": opath, "first_ts": "2026-10-03T00:00:00Z", "human_turns": 1},
    ]
    (proj / "events" / "claude_code").mkdir(parents=True)
    (proj / "events" / "codex").mkdir(parents=True)
    (proj / "events" / "opencode").mkdir(parents=True)
    (proj / "sessions.jsonl").write_text(jl(sessions))
    (proj / "events/claude_code/c1.jsonl").write_text(jl([
        _usage("claude_code", "c1", "2026-10-01T00:00:01Z", cpath, "m1", 20000, 0, 10),
        _ev("claude_code", "c1", "interrupt", "2026-10-01T00:00:02Z", cpath, **{"dh.interrupt": "plain"}),
        _usage("claude_code", "c1", "2026-10-01T00:00:03Z", cpath, "m2", 21000, 20000, 10),
    ]))
    # the subagent copy carries the SAME interrupt (same ts, same family) -> counted once
    (proj / "events/claude_code/c1.agent-x.jsonl").write_text(jl([
        _ev("claude_code", "c1.agent-x", "interrupt", "2026-10-01T00:00:02Z", cpath, **{"dh.interrupt": "plain"}),
        _usage("claude_code", "c1.agent-x", "2026-10-01T00:00:06Z", cpath, "m3", 15000, 0, 10),
    ]))
    # codex child: interrupt + usage inside the 5 s replay window are excluded; later ones count
    (proj / "events/codex/k1.jsonl").write_text(jl([
        _ev("codex", "k1", "interrupt", "2026-10-02T00:00:01Z", xpath, **{"dh.interrupt": "turn_aborted:interrupted"}),
        _usage("codex", "k1", "2026-10-02T00:00:01Z", xpath, None, 9000, 0, 5),
        _usage("codex", "k1", "2026-10-02T00:01:00Z", xpath, None, 12000, 8000, 5),
        _ev("codex", "k1", "interrupt", "2026-10-02T00:02:00Z", xpath, **{"dh.interrupt": "turn_aborted:interrupted"}),
    ]))
    # opencode: one non-reasoning response calibrates chars/token (3600 chars / 1000 tokens)
    (proj / "events/opencode/o1.jsonl").write_text(jl([
        _ev("opencode", "o1", "chat", "2026-10-03T00:00:01Z", opath,
            **{"dh.role": "assistant", "gen_ai.response.id": "r1", "_chars": 7200}),
        _usage("opencode", "o1", "2026-10-03T00:00:02Z", opath, "r1", 18000, 0, 2000),
    ]))
    return proj


def test_mine_projection_dhm1_dhm5(projection, tmp_path):
    out = dh_privacy.private_dir(tmp_path / "priv" / "mining" / "t" / "m1")
    cm = tmp_path / "CLAUDE.md"
    cm.write_text("x" * 3600)
    am = tmp_path / "AGENTS.md"
    am.write_text("y" * 360)
    mem = tmp_path / "MEMORY.md"
    mem.write_text("z" * 360)
    res = m.mine_projection(projection, out, {"CLAUDE.md": cm, "AGENTS.md": am, "MEMORY.md": mem})
    d1 = res["dhm1"]["counts"]["by_harness"]
    assert d1["claude_code"]["epyc"]["main"]["per_1000_turns"]["plain"]["k"] == 1
    assert d1["claude_code"]["epyc"]["subagent"]["per_1000_turns"]["any"]["k"] == 0   # deduped copy
    cx = d1["codex"]["host"]["subagent"]
    assert cx["turns"] == 1 and cx["per_1000_turns"]["any"]["k"] == 1
    assert cx["replay_excluded"] == {"interrupts": 1, "turns": 1}
    d5 = res["dhm5"]["counts"]
    assert d5["chars_per_token_calibration"]["applied"]["chars_per_token"] == 3.6
    assert d5["chars_per_token_calibration"]["applied"]["assumed_default"] == 0
    main = d5["by_harness"]["claude_code"]["epyc"]["main"]
    assert main["first_turn_prompt_tok"]["p50"] == 20000
    assert main["always_on_files_est_tok_per_turn"] == pytest.approx((3600 + 360) / 3.6, abs=0.1)
    assert d5["by_harness"]["claude_code"]["epyc"]["subagent"]["always_on_files_est_tok_per_turn"] == 1000.0
    for doc in res.values():
        assert dh_privacy.validate_aggregate(doc) == []
    rows = (out / "dhm1.sessions.jsonl").read_text().splitlines()
    assert len(rows) == 4


# ─── OAB-LB1 over synthetic rollouts ─────────────────────────────────────────

def _rollout(cwd, turn_ids, parent=None, abort=None, error=None):
    meta = {"type": "session_meta", "payload": {"id": "t", "cwd": cwd, "originator": "codex_exec",
                                                "timestamp": "2026-09-01T00:00:00Z"}}
    if parent:
        meta["payload"]["forked_from_id"] = parent
    rows = [meta]
    for tid in turn_ids:
        rows.append({"type": "event_msg", "payload": {"type": "task_started", "turn_id": tid}})
        rows.append({"type": "response_item", "payload": {
            "type": "custom_tool_call", "call_id": f"c-{tid}", "name": "exec",
            "input": 'const r = await tools.exec_command(' + json.dumps({"cmd": "cd /x && cmake --build b"}) + ')'}})
        rows.append({"type": "response_item", "payload": {
            "type": "custom_tool_call_output", "call_id": f"c-{tid}",
            "output": [{"type": "input_text", "text": "Script completed\nWall time 12.5 seconds\nOutput:\n"}]}})
        rows.append({"type": "event_msg", "payload": {"type": "task_complete", "turn_id": tid, "duration_ms": 20000}})
    if abort:
        rows.append({"type": "event_msg", "payload": {"type": "task_started", "turn_id": abort}})
        rows.append({"type": "event_msg", "payload": {"type": "turn_aborted", "turn_id": abort, "reason": "interrupted"}})
    if error:
        rows.append({"type": "event_msg", "payload": {"type": "error", "message": error}})
    return jl(rows)


def test_mine_oab(tmp_path):
    vault = tmp_path / "vault"
    d = vault / "epyc" / "codex" / "2026" / "09" / "01"
    d.mkdir(parents=True)
    (d / "rollout-a.jsonl").write_text(_rollout("/mnt/raid0/llm/tmp/ak-lanes/l1", ["t1", "t2"], abort="t3",
                                                error="Rate limit reached"))
    # forked child replays t1/t2/t3, then runs t4: only t4 is new
    (d / "rollout-b.jsonl").write_text(_rollout("/mnt/raid0/llm/tmp/ak-lanes/l1", ["t1", "t2", "t4"],
                                                parent="a", abort="t3"))
    (d / "rollout-c.jsonl").write_text(_rollout("/workspace", ["u1"]))       # not an AK lane
    out = dh_privacy.private_dir(tmp_path / "priv" / "m1")
    doc = m.mine_oab(vault, out)
    g = doc["counts"]["by_source"]["all"]
    assert g["threads"] == 2 and g["child_threads"] == 1
    assert g["turns_started"] == 4 and g["turns_completed"] == 3
    assert g["turn_failure"]["aborted_interrupted"]["k"] == 1
    assert g["turn_failure"]["no_terminal_event"]["k"] == 0
    assert g["error_events"] == {"error:rate_limit": 1}
    assert g["exec_by_executable"]["cmake"]["calls"] == 3    # replayed t1/t2 tool calls skipped
    assert g["exec_by_executable"]["cmake"]["wall_s_total"] == 37.5
    assert dh_privacy.validate_aggregate(doc) == []


# ─── UFH14-LB8 over a synthetic opencode snapshot ────────────────────────────

def _oc_db(path: Path):
    c = sqlite3.connect(path)
    c.executescript("""
      CREATE TABLE session (id text primary key, parent_id text, model text, version text, time_created integer);
      CREATE TABLE message (id text primary key, session_id text, time_created integer, data text);
      CREATE TABLE part (id text primary key, message_id text, session_id text, time_created integer, data text);
    """)
    c.execute("INSERT INTO session VALUES ('s1', NULL, ?, '1.2.3', 1790000000000)", (json.dumps({"providerID": "qwen-gpu"}),))
    c.execute("INSERT INTO session VALUES ('s2', NULL, ?, '1.2.3', 1790000000001)", (json.dumps({"providerID": "deepseek"}),))
    msgs = [("u1", 1000, "user", None), ("a1", 1001, "assistant", "qwen-gpu"),
            ("a2", 5000, "assistant", "qwen-gpu"), ("u2", 60000, "user", None), ("a3", 60001, "assistant", "qwen-gpu")]
    for mid, tc, role, prov in msgs:
        c.execute("INSERT INTO message VALUES (?, 's1', ?, ?)", (mid, tc, json.dumps({"role": role, "providerID": prov})))
    n = 0

    def part(mid, tc, data):
        nonlocal n
        n += 1
        c.execute("INSERT INTO part VALUES (?, ?, 's1', ?, ?)", (f"p{n:03d}", mid, tc, json.dumps(data)))

    def step(mid, t0, t1, inp, read, out):
        part(mid, t0, {"type": "step-start"})
        part(mid, t1, {"type": "step-finish", "tokens": {"input": inp, "output": out, "cache": {"read": read, "write": 0}}})

    step("a1", 1002, 2000, 10000, 0, 100)
    part("a1", 2001, {"type": "tool", "tool": "bash", "state": {"status": "completed", "time": {"start": 2001, "end": 4001}}})
    step("a2", 5001, 6000, 600, 10100, 50)          # tool gap 3.001 s, append 600
    step("a3", 60002, 61000, 300, 10700, 20)        # human gap (u2 inside), append 11000-(10700+50)=250
    c.commit()
    c.close()


def test_mine_opencode(tmp_path):
    db = tmp_path / "snap.db"
    _oc_db(db)
    out = dh_privacy.private_dir(tmp_path / "priv" / "m1")
    doc = m.mine_opencode({"epyc": db}, out)
    g = doc["counts"]["by_source"]["epyc"]["qwen-gpu"]
    assert g["sessions"] == 1 and g["steps"] == 3
    assert g["gap_s"]["tool"]["n"] == 1 and g["gap_s"]["tool"]["p50"] == pytest.approx(3.001)
    assert g["gap_s"]["human"]["n"] == 1
    assert g["append_tok"]["tool"]["p50"] == 600 and g["append_tok"]["human"]["p50"] == 250
    assert g["prefix_hit"]["token_weighted"] == pytest.approx(20800 / 31700, abs=1e-4)
    assert g["tool_duration_s"]["bash"]["p50"] == 2.0
    assert g["opencode_versions"] == {"1.2.3": 1} and g["frame"]["distinct_days"] == 1
    assert dh_privacy.validate_aggregate(doc) == []


def test_live_opencode_store_refused(tmp_path):
    import dh_sources as src
    with pytest.raises(src.LiveOpencodeStoreError):
        m.mine_opencode({"epyc": Path.home() / ".local/share/opencode/opencode.db"}, tmp_path)


# ─── DHM-1 correction keyword pass ───────────────────────────────────────────

def test_mine_history(tmp_path):
    ms = 1790000000000          # 2026-09
    h = tmp_path / "h.jsonl"
    h.write_text(jl([
        {"display": "no, that's not what I asked", "timestamp": ms},
        {"display": "please add the tests", "timestamp": ms + 1},
        {"display": "/clear", "timestamp": ms + 2},
        {"display": "wrong file", "timestamp": 1700000000000},       # before since
    ]))
    doc = m.mine_history(h, since="2026-03-01")
    tot = doc["counts"]["total"]
    assert tot["correction_rate"]["k"] == 1 and tot["correction_rate"]["n"] == 2
    assert tot["slash_commands"] == 1 and tot["pattern_no_comma"] == 1
    assert dh_privacy.validate_aggregate(doc) == []


def test_main_end_to_end(projection, tmp_path, monkeypatch):
    monkeypatch.setenv("DEV_HARNESS_ALLOW_NOT_NICE", "1")
    db = tmp_path / "snap.db"
    _oc_db(db)
    rc = m.main(["--projection", str(projection), "--private-root", str(tmp_path / "priv"),
                 "--vault", str(tmp_path / "novault"), "--opencode-db", f"epyc={db}"])
    assert rc == 0
    agg = tmp_path / "priv" / "mining" / "proj" / "m1" / "aggregates"
    assert sorted(p.name for p in agg.iterdir()) == ["dhm1.aggregate.json", "dhm5.aggregate.json",
                                                     "oab_lb1.aggregate.json", "ufh14_lb8.aggregate.json"]
    doc = json.loads((agg / "dhm1.aggregate.json").read_text())
    assert doc["source"].startswith("mine_m1 run=proj ") and doc["counts"]["frame"]["units"] == 4
