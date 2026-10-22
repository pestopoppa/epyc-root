"""Dev-harness projector / AgentRun converter / privacy gate (UTM-LB2, DHM-7, F3-LB1).

All fixtures are synthetic and built programmatically (json.dumps at runtime), so no
transcript-shaped line is ever staged in this public repo.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/dev_harness"))

import agentrun  # noqa: E402
import dh_privacy  # noqa: E402
import dh_sources as src  # noqa: E402
import projector  # noqa: E402

SENTINEL = "ZQX-sentinel-content-never-leaves-memory"
SID = "11111111-2222-3333-4444-555555555555"


def jl(rows):
    return "".join(json.dumps(r) + "\n" for r in rows)


def claude_rows(sid=SID, sidechain=False, agent_id=None):
    base = {"sessionId": sid, "version": "2.1.999", "isSidechain": sidechain, "userType": "external"}
    if agent_id:
        base["agentId"] = agent_id

    def row(**kw):
        r = dict(base)
        r["parentUuid"] = None
        r.update(kw)
        return r

    usage = {"input_tokens": 10, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 5, "output_tokens": 7}
    return [
        row(type="permission-mode", permissionMode="auto"),
        row(type="user", timestamp="2026-10-20T10:00:00Z", message={"role": "user", "content": f"please do it {SENTINEL}"}),
        # one assistant message streamed as two lines repeating usage -> one usage record
        row(type="assistant", timestamp="2026-10-20T10:00:01Z",
            message={"id": "msg_A", "model": "claude-x", "content": [{"type": "text", "text": "ok"}], "usage": usage}),
        row(type="assistant", timestamp="2026-10-20T10:00:02Z",
            message={"id": "msg_A", "model": "claude-x", "stop_reason": "tool_use",
                     "content": [{"type": "tool_use", "id": "tu1", "name": "Bash", "input": {"command": "git commit"}}],
                     "usage": dict(usage, output_tokens=9)}),
        row(type="user", timestamp="2026-10-20T10:00:03Z", message={"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tu1", "is_error": False,
             "content": "[main abc1234] commit message\n 1 file changed"}]}),
        row(type="assistant", timestamp="2026-10-20T10:00:04Z",
            message={"id": "msg_B", "model": "claude-x", "content": [
                {"type": "tool_use", "id": "tu2", "name": "Bash", "input": {"command": "rm -rf x"}},
                {"type": "tool_use", "id": "tu3", "name": "Agent", "input": {"subagent_type": "fork", "prompt": "p"}}],
                     "usage": usage}),
        row(type="user", timestamp="2026-10-20T10:00:05Z", message={"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tu2", "is_error": True,
             "content": "The user doesn't want to proceed with this tool use."},
            {"type": "tool_result", "tool_use_id": "tu3", "is_error": True,
             "content": "PreToolUse:Bash hook error: BLOCKED: nope"}]}),
        row(type="user", timestamp="2026-10-20T10:00:06Z",
            message={"role": "user", "content": [{"type": "text", "text": "[Request interrupted by user for tool use]"}]}),
        row(type="user", timestamp="2026-10-21T09:00:00Z",
            message={"role": "user", "content": [{"type": "text", "text": "[Request interrupted by user]"}]}),
        row(type="system", subtype="compact_boundary", timestamp="2026-10-21T09:00:01Z", content="Conversation compacted"),
        row(type="user", timestamp="2026-10-21T09:00:02Z", message={"role": "user", "content": "second task"}),
    ]


def codex_rows(thread="th-child", parent="th-root"):
    def r(t, payload, ts="2026-10-20T10:00:00Z"):
        return {"timestamp": ts, "ordinal": 0, "type": t, "payload": payload}
    u = {"input_tokens": 200, "cached_input_tokens": 150, "cache_write_input_tokens": 0, "output_tokens": 20,
         "reasoning_output_tokens": 5, "total_tokens": 220}
    return [
        r("session_meta", {"id": thread, "session_id": parent, "parent_thread_id": parent, "forked_from_id": parent,
                           "cli_version": "0.999.0", "agent_nickname": "Socrates",
                           "source": {"subagent": {"thread_spawn": {"parent_thread_id": parent, "depth": 1}}}}),
        r("turn_context", {"model": "gpt-x"}),
        r("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "go"}]}),
        r("response_item", {"type": "function_call", "name": "exec_command", "call_id": "c1",
                            "arguments": json.dumps({"cmd": "false"})}),
        r("response_item", {"type": "function_call_output", "call_id": "c1", "output": "Process exited with code 1"}),
        r("event_msg", {"type": "token_count", "info": {"total_token_usage": u}}),
        r("event_msg", {"type": "token_count", "info": {"total_token_usage": u}}),
        r("token_usage_record", {"response_id": "resp1", "usage": u}),
        r("token_usage_record", {"response_id": "resp1", "usage": u}),   # duplicate -> deduped
        r("event_msg", {"type": "turn_aborted", "reason": "interrupted"}),
    ]


def make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    proj = vault / "epyc/claude/-workspace"
    proj.mkdir(parents=True)
    (proj / f"{SID}.jsonl").write_text(jl(claude_rows()))
    subdir = proj / SID / "subagents"
    subdir.mkdir(parents=True)
    (subdir / "agent-a1.jsonl").write_text(jl(claude_rows(sidechain=True, agent_id="a1")))
    (subdir / "agent-a1.meta.json").write_text(json.dumps({"agentType": "fork", "toolUseId": "tu3"}))
    (subdir / "agent-a2.jsonl").write_text(jl(claude_rows(sidechain=True, agent_id="a2")))
    cdir = vault / "epyc/codex/2026/10/20"
    cdir.mkdir(parents=True)
    (cdir / "rollout-2026-10-20T10-00-00-th-child.jsonl").write_text(jl(codex_rows()))
    return vault


def make_opencode(tmp_path: Path) -> Path:
    db = tmp_path / "opencode.db"
    c = sqlite3.connect(db)
    c.executescript("""
      CREATE TABLE session (id TEXT PRIMARY KEY, project_id TEXT, parent_id TEXT, version TEXT, agent TEXT,
                            model TEXT, time_created INTEGER);
      CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER, data TEXT);
      CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
      CREATE TABLE session_message (id TEXT PRIMARY KEY, session_id TEXT, type TEXT, seq INTEGER,
                                    time_created INTEGER, data TEXT);
      CREATE TABLE credential (id TEXT PRIMARY KEY, value TEXT);
    """)
    c.execute("INSERT INTO credential VALUES ('x', 'SECRET-NEVER-READ')")
    c.execute("INSERT INTO session VALUES ('ses_1', 'p', NULL, '1.0.0', 'build', NULL, 1790000000000)")
    c.execute("INSERT INTO message VALUES ('msg_u', 'ses_1', 1790000000001, ?)",
              (json.dumps({"role": "user", "agent": "build"}),))
    c.execute("INSERT INTO part VALUES ('prt_1', 'msg_u', 'ses_1', 1790000000001, ?)",
              (json.dumps({"type": "text", "text": f"hello {SENTINEL}"}),))
    c.execute("INSERT INTO message VALUES ('msg_a', 'ses_1', 1790000000002, ?)",
              (json.dumps({"role": "assistant", "modelID": "m", "finish": "tool-calls",
                           "tokens": {"input": 10, "output": 3, "reasoning": 1, "cache": {"read": 90, "write": 0}},
                           "error": {"name": "MessageAbortedError"}}),))
    c.execute("INSERT INTO part VALUES ('prt_2', 'msg_a', 'ses_1', 1790000000003, ?)",
              (json.dumps({"type": "tool", "tool": "bash", "callID": "call1",
                           "state": {"status": "error", "input": {"command": "x"}, "error": "Tool execution aborted"}}),))
    c.execute("INSERT INTO part VALUES ('prt_3', 'msg_a', 'ses_1', 1790000000004, ?)",
              (json.dumps({"type": "step-finish", "tokens": {"input": 999999}}),))
    c.commit()
    c.close()
    return db


def snapshot(root: Path) -> dict:
    return {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(root.rglob("*"))}


# ─── sources ─────────────────────────────────────────────────────────────────

def test_claude_parse_usage_dedupe_tools_interrupts_denials(tmp_path):
    vault = make_vault(tmp_path)
    u = src.claude_file_unit(vault / f"epyc/claude/-workspace/{SID}.jsonl", "vault_file")
    assert u.conversation_id == SID and u.agent_name == "main" and u.edge_kind is None
    usage = [r for r in u.records if r["kind"] == "usage"]
    assert len(usage) == 2                                   # msg_A once, msg_B once
    a = next(r for r in usage if r["response_id"] == "msg_A")
    assert a["usage"]["output"] == 9                          # last line wins
    assert a["usage"]["input_inclusive"] == 115               # 10 + 100 + 5 (OTel inclusive)
    assert a["usage"]["raw"]["input_tokens"] == 10
    ints = [r["interrupt"] for r in u.records if r["kind"] == "interrupt"]
    assert ints == ["tool_use", "plain"]
    dens = sorted(r["denial"] for r in u.records if r.get("denial"))
    assert dens == ["hook_block", "user_reject"]
    assert any(r.get("commit_shas") == ["abc1234"] for r in u.records)
    assert any(r["kind"] == "compaction" for r in u.records)
    assert [r["operation"] for r in u.records if r["kind"] == "tool_call"] == ["execute_tool", "execute_tool", "invoke_agent"]
    assert sum(1 for r in u.records if r.get("human")) == 2
    assert u.source_schema_key().startswith("claude_code|v=claude-code/2.1.999|types=")


def test_claude_subagent_edges(tmp_path):
    vault = make_vault(tmp_path)
    sub = vault / f"epyc/claude/-workspace/{SID}/subagents"
    fork = src.claude_file_unit(sub / "agent-a1.jsonl", "vault_file")
    assert (fork.edge_kind, fork.edge_fidelity, fork.agent_name, fork.parent_tool_call_id) == ("fork", "observed", "fork", "tu3")
    assert fork.parent_conversation_id == SID and fork.unit_key == f"{SID}.agent-a1"
    assert not any(r.get("human") for r in fork.records)     # sidechain prompts are not operator turns
    spawn = src.claude_file_unit(sub / "agent-a2.jsonl", "vault_file")
    assert (spawn.edge_kind, spawn.edge_fidelity) == ("spawn", "inferred")


def test_codex_parse_usage_record_only_and_spawn(tmp_path):
    vault = make_vault(tmp_path)
    f = next((vault / "epyc/codex").rglob("rollout-*.jsonl"))
    u = src.codex_file_unit(f, "vault_file")
    usage = [r for r in u.records if r["kind"] == "usage"]
    assert len(usage) == 1                                   # token_count never summed; record deduped
    assert usage[0]["usage"]["input_inclusive"] == 200 and usage[0]["usage"]["cache_read"] == 150
    assert (u.edge_kind, u.edge_fidelity, u.parent_conversation_id) == ("spawn", "observed", "th-root")
    assert u.unit_key == "th-child" and u.agent_name == "Socrates"
    res = next(r for r in u.records if r["kind"] == "tool_result")
    assert res["is_error"] and res["fidelity"] == "inferred"
    assert [r["interrupt"] for r in u.records if r["kind"] == "interrupt"] == ["turn_aborted:interrupted"]


def test_opencode_immutable_read_and_allowlist(tmp_path):
    db = make_opencode(tmp_path)
    before = snapshot(tmp_path)
    units = list(src.select_opencode_units(db, limit=5))
    assert snapshot(tmp_path) == before                      # no write, no -wal/-shm
    (u,) = units
    usage = [r for r in u.records if r["kind"] == "usage"]
    assert len(usage) == 1 and usage[0]["usage"]["input_inclusive"] == 100   # step-finish not summed
    assert sorted(r["interrupt"] for r in u.records if r["kind"] == "interrupt") == ["message_aborted", "tool_aborted"]
    assert not any("SECRET-NEVER-READ" in (r.get("text") or "") for r in u.records)


def test_tarball_streaming(tmp_path):
    tb = tmp_path / "ai-sessions-test.tar.gz"
    with tarfile.open(tb, "w:gz") as tf:
        for name, text in ((f"projects/-workspace/{SID}.jsonl", jl(claude_rows())),
                           ("sessions/2026/10/20/rollout-x.jsonl", jl(codex_rows())),
                           ("projects/-workspace/memory/note.md", "not a transcript")):
            data = text.encode()
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
    units = list(src.iter_tarball_units(tb))
    assert sorted(u.harness for u in units) == ["claude_code", "codex"]
    assert all(u.collection_method == "tarball_member" for u in units)


def test_last_vault_sync(tmp_path):
    log = tmp_path / "backup.log"
    log.write_text("2026-10-21T02:00:04Z VAULT x\n  host: claude=1\n2026-10-22T02:00:05Z VAULT y\n2026-10-22T02:16:37Z STATUS OK\n")
    assert src.last_vault_sync(log).isoformat() == "2026-10-22T02:00:05+00:00"


# ─── projector ───────────────────────────────────────────────────────────────

def _args(parser, tmp_path, vault, db, *extra):
    return parser.parse_args(["--private-root", str(tmp_path / "priv"), "--vault", str(vault), "--claude", "0",
                              "--codex", "0", "--opencode", "0", "--opencode-db", str(db), "--run-id", "t",
                              "--no-resolve-commits", *extra])


def test_projector_end_to_end_private_and_content_free(tmp_path):
    vault = make_vault(tmp_path)
    db = make_opencode(tmp_path)
    before = snapshot(vault)
    m = projector.run(_args(projector.build_parser(), tmp_path, vault, db))
    assert snapshot(vault) == before                         # the vault is never modified
    out = Path(m["out_dir"])
    assert m["units"] == {"claude_code": 3, "codex": 1, "opencode": 1}
    for p in [out, *out.rglob("*")]:
        mode = p.stat().st_mode & 0o777
        assert mode == (0o700 if p.is_dir() else 0o600), (p, oct(mode))
        if p.is_file():
            assert SENTINEL not in p.read_text()             # content never leaves memory
    sessions = [json.loads(line) for line in (out / "sessions.jsonl").read_text().splitlines()]
    main = next(s for s in sessions if s["unit_key"] == SID)
    assert main["interrupts"] == {"tool_use": 1, "plain": 1}
    assert main["commit_shas"] == ["abc1234"] and main["usage"]["n_usage_records"] == 2
    assert main["semconv"] == projector.SEMCONV["commit"]
    ev = [json.loads(line) for line in (out / f"events/claude_code/epyc/{SID}.jsonl").read_text().splitlines()]
    assert all(e["schema"] == projector.EVENT_SCHEMA and e["fidelity"] in ("observed", "inferred") for e in ev)
    usage_ev = next(e for e in ev if e["event_kind"] == "usage")
    d = usage_ev["detail_json"]
    assert d["gen_ai.operation.name"] == "chat" and d["gen_ai.conversation.id"] == SID
    assert d["gen_ai.usage.input_tokens"] == 115 and d["dh.usage_raw"]["input_tokens"] == 10
    first_user = next(e for e in ev if e["event_kind"] == "chat")
    assert first_user["content"]["block_hashes"] and first_user["content"]["n_chars"] > 0
    joins = [json.loads(line) for line in (out / "commits.jsonl").read_text().splitlines()]
    assert {j["sha"] for j in joins} == {"abc1234"}


def test_block_hashes_keyed_and_deterministic():
    text = " ".join(f"w{i}" for i in range(130))
    n, h1 = projector.block_hashes(text, b"k1")
    _, h2 = projector.block_hashes(text, b"k1")
    _, h3 = projector.block_hashes(text, b"k2")
    assert n == 130 and len(h1) == 3 and h1 == h2 and h1 != h3


# ─── AgentRun converter ──────────────────────────────────────────────────────

def test_agentrun_segments_markers_and_tool_errors(tmp_path):
    vault = make_vault(tmp_path)
    u = src.claude_file_unit(vault / f"epyc/claude/-workspace/{SID}.jsonl", "vault_file")
    runs = agentrun.segment(u, max_messages=120, max_chars=60000, max_msg_chars=4000)
    assert len(runs) == 2                                    # two operator prompts -> two task windows
    msgs = runs[0]["transcripts"][0]["messages"]
    texts = [m["content"] for m in msgs if m["role"] == "user"]
    assert "[Request interrupted by user for tool use]" in texts and "[Request interrupted by user]" in texts
    tools = [m for m in msgs if m["role"] == "tool"]
    assert [t["function"] for t in tools] == ["Bash", "Bash", "Agent"]
    assert [(t["error"] or {}).get("type") for t in tools] == [None, "denial:user_reject", "denial:hook_block"]
    asst = [m for m in msgs if m["role"] == "assistant" and m["tool_calls"]]
    assert asst[0]["tool_calls"][0]["arguments"] == {"command": "git commit"}
    md = runs[0]["metadata"]
    assert md["has_denial"] and md["day"] == "2026-10-20" and not md["continuation"]
    capped = agentrun.segment(u, max_messages=3, max_chars=60000, max_msg_chars=10)
    assert len(capped) > 2 and any(r["metadata"]["continuation"] for r in capped)


def test_agentrun_run_writes_private_index(tmp_path):
    vault = make_vault(tmp_path)
    db = make_opencode(tmp_path)
    a = _args(agentrun.build_parser(), tmp_path, vault, db)
    s = agentrun.run(a)
    out = Path(s["out_dir"])
    idx = [json.loads(line) for line in (out / "index.jsonl").read_text().splitlines()]
    assert len(idx) == s["segments"] and s["segments_with_denial"] >= 1
    oc = [r for r in idx if r["harness"] == "opencode"]
    seg = json.loads(Path(oc[0]["path"]).read_text())
    assert any(m["content"] in ("[message_aborted]", "[tool_aborted]") and m["metadata"]["marker_synthesized"]
               for m in seg["transcripts"][0]["messages"] if m["role"] == "user")
    assert all(p.stat().st_mode & 0o077 == 0 for p in out.rglob("*"))


# ─── privacy gate ────────────────────────────────────────────────────────────

def test_private_path_refusals(tmp_path, monkeypatch):
    with pytest.raises(dh_privacy.PrivacyError):
        dh_privacy.check_private_path(ROOT / "tmp-dev-harness-out")          # inside a git work tree
    monkeypatch.setattr(dh_privacy, "VAULT_ROOT", tmp_path / "vault")
    with pytest.raises(dh_privacy.PrivacyError):
        dh_privacy.private_write(tmp_path / "vault/x.json", "{}")
    assert not (tmp_path / "vault").exists()
    k1 = dh_privacy.hmac_key(tmp_path / "priv")
    assert k1 == dh_privacy.hmac_key(tmp_path / "priv") and len(k1) == 32
    assert (tmp_path / "priv/keys/block_hmac.key").stat().st_mode & 0o777 == 0o600


def test_validate_aggregate():
    good = {"schema": dh_privacy.AGGREGATE_SCHEMA, "counts": {"claude_code": {"interrupts": 3, "rate": 0.5}},
            "rules": ["interrupt = user text marker"], "source": "projector run t"}
    assert dh_privacy.validate_aggregate(good) == []
    bad = dict(good, counts={"x": {"session_id": 1}})
    assert any("per-session key" in e for e in dh_privacy.validate_aggregate(bad))
    assert dh_privacy.validate_aggregate(dict(good, counts={"x": ["a"]}))
    assert dh_privacy.validate_aggregate(dict(good, extra=1))


def test_publish_aggregate_requires_preflight_pass(tmp_path, monkeypatch):
    good = {"schema": dh_privacy.AGGREGATE_SCHEMA, "counts": {"n": 1}, "rules": []}
    dest = tmp_path / "pub/agg.json"
    monkeypatch.setattr(dh_privacy, "run_preflight", lambda *a, **k: 2)
    with pytest.raises(dh_privacy.PrivacyError):
        dh_privacy.publish_aggregate(good, dest, private_root=tmp_path / "priv")
    assert not dest.exists()
    monkeypatch.setattr(dh_privacy, "run_preflight", lambda *a, **k: 0)
    assert dh_privacy.publish_aggregate(good, dest, private_root=tmp_path / "priv") == dest
    assert json.loads(dest.read_text())["counts"] == {"n": 1}
