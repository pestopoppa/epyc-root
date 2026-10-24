"""DHM-5.1 (always-on prefix from turn-1 usage fields) over synthetic fixtures.

Every fixture is built at runtime (dicts / sqlite3); no transcript-shaped line is staged.
"""
from __future__ import annotations

import json
import random
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/dev_harness"))

import dh_privacy  # noqa: E402
import mine_dhm51 as m  # noqa: E402


# ─── Claude Code turn-1 parse ────────────────────────────────────────────────

def _att(kind, rendered, **kw):
    return {"type": "attachment", "version": "2.1.300", "cwd": "/w", "attachment": {"type": kind, **kw},
            "rendered": [{"content": rendered}]}


def test_claude_turn1_classes_and_usage():
    recs = [
        _att("skill_listing", "s" * 300),
        _att("instructions", "i" * 1200, files=[{"path": "/w/CLAUDE.md", "type": "Project", "content": "c" * 800},
                                                {"path": "/m/memory/MEMORY.md", "type": "AutoMem", "content": "x" * 300}]),
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": "m" * 50}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "u" * 400}]}},
        {"type": "assistant", "message": {"model": "claude-x", "usage": {"input_tokens": 10,
                                                                         "cache_creation_input_tokens": 900,
                                                                         "cache_read_input_tokens": 5000}}},
        {"type": "assistant", "message": {"model": "claude-x", "usage": {"input_tokens": 99}}},
    ]
    r = m.claude_turn1(recs)
    assert r["prompt_tok"] == 5910 and r["cache_read_tok"] == 5000 and r["cache_creation_tok"] == 900
    assert r["chars"] == {"always_on": 1200, "reminder": 350, "system": 0, "user": 400, "history": 0}
    assert r["file_chars"] == {"claude_md": 800, "memory_index": 300}
    assert r["instr_logged"] and r["version"] == "2.1.300" and r["role"] == "main"


def test_claude_turn1_history_and_synthetic_skipped():
    recs = [
        {"type": "user", "isCompactSummary": True, "message": {"content": "h" * 70}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "t" * 30}]}},
        {"type": "assistant", "message": {"model": "<synthetic>", "usage": {"input_tokens": 0},
                                          "content": [{"type": "text", "text": "y" * 5}]}},
        {"type": "assistant", "isSidechain": True, "message": {"model": "c", "usage": {"input_tokens": 7}}},
    ]
    r = m.claude_turn1(recs)
    assert r["chars"]["history"] == 105 and r["prompt_tok"] == 7 and not r["instr_logged"]
    assert r["role"] == "subagent"
    assert m.claude_turn1([{"type": "user", "message": {"content": "x"}}]) is None


# ─── Codex turn-1 parse ──────────────────────────────────────────────────────

def _msg(role, *texts):
    return {"type": "response_item", "payload": {"type": "message", "role": role,
                                                 "content": [{"type": "input_text", "text": t} for t in texts]}}


def _tc(inp, cached):
    return {"type": "event_msg", "payload": {"type": "token_count", "info": {
        "last_token_usage": {"input_tokens": inp, "cached_input_tokens": cached}}}}


def test_codex_turn1_classes_and_own_output_not_history():
    recs = [
        {"type": "session_meta", "payload": {"cli_version": "0.1.0", "cwd": "/w",
                                             "base_instructions": {"text": "b" * 500}}},
        {"type": "turn_context", "payload": {"model": "gpt-x"}},
        _msg("developer", "<skills>" + "d" * 92),
        _msg("user", "# AGENTS.md instructions for /w\n" + "a" * 968, "<environment_context>" + "e" * 79),
        _msg("user", "do the thing"),
        {"type": "response_item", "payload": {"type": "reasoning", "summary": [], "content": None}},
        {"type": "response_item", "payload": {"type": "function_call", "arguments": "z" * 40}},
        _tc(4000, 3000),
    ]
    r = m.codex_turn1(recs)
    assert r["prompt_tok"] == 4000 and r["cache_read_tok"] == 3000 and r["model"] == "gpt-x"
    assert r["chars"]["always_on"] == 1000 and r["chars"]["system"] == 500
    assert r["chars"]["reminder"] == 100 + 100 and r["chars"]["user"] == len("do the thing")
    assert r["chars"]["history"] == 0 and r["role"] == "main"


def test_codex_fork_replay_counts_as_history():
    recs = [
        {"type": "session_meta", "payload": {"forked_from_id": "p", "base_instructions": {"text": ""}}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant",
                                              "content": [{"type": "output_text", "text": "o" * 60}]}},
        _msg("user", "next"),
        _tc(10, 0),
    ]
    r = m.codex_turn1(recs)
    assert r["role"] == "subagent" and r["chars"]["history"] == 60
    assert m.codex_turn1([_msg("user", "x"), {"type": "event_msg", "payload": {"type": "token_count", "info": None}}]) is None


# ─── opencode ────────────────────────────────────────────────────────────────

def test_rule_file_sizer_findup_absent_and_current(tmp_path):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / "sub").mkdir()
    (root / "CLAUDE.md").write_text("c" * 123)
    s = m.RuleFileSizer()
    # no AGENTS.md anywhere up to the git root -> CLAUDE.md (opencode's order); not tracked -> current size
    assert s.chars(str(root / "sub"), "2026-10-01T00:00:00Z") == (123, "current")
    (root / "sub" / "AGENTS.md").write_text("a" * 40)
    assert s.chars(str(root / "sub"), None) == (40, "current")
    bare = tmp_path / "bare"
    (bare / ".git").mkdir(parents=True)
    assert m.RuleFileSizer().chars(str(bare), None) == (0, "absent")
    assert m.RuleFileSizer().chars(str(tmp_path / "missing"), None) == (None, "unresolved")


def test_opencode_turn1(tmp_path):
    d = tmp_path / "w"
    (d / ".git").mkdir(parents=True)
    (d / "AGENTS.md").write_text("a" * 900)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE message (id TEXT, session_id TEXT, time_created INT, data TEXT)")
    conn.execute("CREATE TABLE part (id TEXT, message_id TEXT, time_created INT, data TEXT)")
    conn.execute("INSERT INTO message VALUES ('m1','s',1,?)", (json.dumps({"role": "user", "agent": "build"}),))
    conn.execute("INSERT INTO part VALUES ('p1','m1',1,?)", (json.dumps({"type": "text", "text": "u" * 30}),))
    conn.execute("INSERT INTO part VALUES ('p2','m1',2,?)", (json.dumps({"type": "text", "synthetic": True,
                                                                        "text": "r" * 20}),))
    conn.execute("INSERT INTO message VALUES ('m2','s',2,?)", (json.dumps(
        {"role": "assistant", "modelID": "ds", "tokens": {"input": 100, "cache": {"read": 2000, "write": 5}}}),))
    r = m.opencode_turn1(conn, "s", str(d), None, m.RuleFileSizer())
    assert r["prompt_tok"] == 2105 and r["cache_read_tok"] == 2000 and r["agent_type"] == "build"
    assert r["chars"]["always_on"] == 900 and r["chars"]["user"] == 30 and r["chars"]["reminder"] == 20
    assert r["role"] == "main" and r["instr_logged"]


# ─── fitting recovers a planted prefix ───────────────────────────────────────

def _synthetic(n=400, beta_ao=0.3, base=None, seed=7, harness="claude_code", role="subagent", warm=True):
    base = base or {"a": 10000, "b": 14000}
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        mdl = "a" if i % 3 == 0 else "b"
        ao = 0 if i % 10 == 0 else rng.randrange(20000, 45000)
        rem, usr = rng.randrange(5000, 9000), rng.randrange(100, 8000)
        tok = base[mdl] + beta_ao * ao + 0.5 * rem + 0.4 * usr + rng.gauss(0, 50)
        rows.append({"harness": harness, "role": role, "model": mdl, "version": "1.0.0", "cwd": "/w",
                     "agent_type": None, "prompt_tok": int(tok), "cache_read_tok": base[mdl] if warm else 0,
                     "cache_creation_tok": 0, "uncached_tok": 0, "instr_logged": True,
                     "chars": {"always_on": ao, "reminder": rem, "system": 0, "user": usr, "history": 0},
                     "file_chars": {"claude_md": ao // 2, "memory_index": ao - ao // 2}})
    return rows


def test_fit_group_recovers_planted_slope_and_baseline():
    rows = _synthetic()
    f = m.fit_group(rows, "model", boot=60)
    assert f["identified"] == 1 and f["buckets"] == 2
    b = f["beta_always_on_tok_per_char"]
    assert b["ci95_lo"] <= 0.3 <= b["ci95_hi"] and abs(b["est"] - 0.3) < 0.005
    assert abs(f["baseline_system_tools_tok"]["est"] - 14000) < 300   # bucket b is the largest (2 of 3 rows)
    p50 = f["always_on_chars_p50"]
    assert abs(f["always_on_tok_p50"]["est"] - 0.3 * p50) < 0.01 * p50
    assert f["_dominant_bucket"] == "b"


def test_fit_group_unidentified_without_always_on_variation():
    rows = _synthetic()
    for r in rows:
        r["chars"]["always_on"] = 5000
    f = m.fit_group(rows, "model", boot=10)
    assert f["identified"] == 0


def test_fit_cache_split_recovers_slope():
    f = m.fit_cache_split(_synthetic(), boot=60)
    assert f["identified"] == 1 and abs(f["beta_always_on_tok_per_char"]["est"] - 0.3) < 0.005
    assert abs(f["intercept_tok"]["est"]) < 200


def test_aggregate_is_publishable_and_picks_primary():
    rows = _synthetic() + _synthetic(harness="codex", role="main", seed=9)
    agg = m.aggregate(rows, {"claude_code|subagent": 8326.4})
    assert dh_privacy.validate_aggregate(agg) == []
    g = agg["counts"]["by_harness"]["claude_code"]["subagent"]
    assert g["dhm5_file_size_estimate_tok"] == 8326.4
    assert g["primary"]["identified"] == 1 and g["primary"]["spec_model_version"] == 1
    assert g["primary"]["measured"] == 1
    assert "fit_cache_split" in g and "fit_cache_split" not in agg["counts"]["by_harness"]["codex"]["main"]
    assert "/w" not in json.dumps(agg)        # directories never reach the aggregate


def test_version_helpers():
    assert m.version_key("2.1.261") < m.version_key("2.1.300")
    assert m.version_num((2, 1, 199)) == 2001199 and m.version_num(None) == 0
