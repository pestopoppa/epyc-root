"""FM-1 collector tests: fixtures built in tmp_path, never the real corpus.

Covers: Claude parent/child edges from `parentUuid` + timing math, Codex
thread_spawn depth/parent edges, mutation tests (edge removal degrades depth,
timestamp change moves active_s/span, serial => utilization 0), idempotence,
and the edge cases (empty dir, malformed lines, incomplete subagent).

D9-ack: operator tasking 2026-08-23 (RTG-49 FM-1).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.coordination import fanout_timing as ft


def _rec(typ, ts, uuid=None, agent_id=None, parent_uuid=None, prompt_id=None,
         session_id="S", content=None, extra=None):
    r = {"type": typ, "timestamp": ts, "sessionId": session_id}
    if uuid is not None:
        r["uuid"] = uuid
    if agent_id is not None:
        r["agentId"] = agent_id
    if parent_uuid is not None:
        r["parentUuid"] = parent_uuid
    if prompt_id is not None:
        r["promptId"] = prompt_id
    if content is not None:
        r["content"] = content
    if extra:
        r.update(extra)
    return r


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


# --------------------------------------------------------------------------- Claude


def _claude_corpus(root, *, strip_parent_uuid=False, shift_finish=None):
    sid = "session-A"
    sub = root / sid / "subagents"
    # Main session transcript: two uuids the subagents' parentUuid can resolve to.
    _write_jsonl(root / f"{sid}.jsonl", [
        _rec("user", "2026-08-01T10:00:00.000Z", uuid="m1", session_id=sid, content="do it"),
        _rec("assistant", "2026-08-01T10:01:00.000Z", uuid="m2", session_id=sid),
        _rec("user", "2026-08-01T10:06:30.000Z", uuid="m3", session_id=sid),
    ])
    # A: concurrent sibling, spawns D (nested via parentUuid -> A's record uuid).
    _write_jsonl(sub / "agent-A.jsonl", [
        _rec("user", "2026-08-01T10:00:10.000Z", uuid="a1", agent_id="A",
             parent_uuid="m1", session_id=sid, content="A task"),
        _rec("assistant", "2026-08-01T10:02:00.000Z", uuid="a2", agent_id="A",
             parent_uuid="a1", session_id=sid),
        _rec("assistant", "2026-08-01T10:04:10.000Z", uuid="a3", agent_id="A",
             parent_uuid="a2", session_id=sid),
    ])
    # B: concurrent with A.
    _write_jsonl(sub / "agent-B.jsonl", [
        _rec("user", "2026-08-01T10:00:40.000Z", uuid="b1", agent_id="B",
             parent_uuid="m2", session_id=sid, content="B task"),
        _rec("assistant", "2026-08-01T10:03:10.000Z", uuid="b2", agent_id="B",
             parent_uuid="b1", session_id=sid),
    ])
    # C: strictly serial (after A and B finish).
    _write_jsonl(sub / "agent-C.jsonl", [
        _rec("user", "2026-08-01T10:05:00.000Z", uuid="c1", agent_id="C",
             parent_uuid="m3", session_id=sid, content="C task"),
        _rec("assistant", "2026-08-01T10:06:00.000Z", uuid="c2", agent_id="C",
             parent_uuid="c1", session_id=sid),
    ])
    # D: nested child of A, via the real parentUuid edge.
    rows = [
        _rec("user", "2026-08-01T10:02:00.000Z", uuid="d1", agent_id="D",
             parent_uuid="a2" if not strip_parent_uuid else None, session_id=sid,
             content="D task"),
        _rec("assistant", "2026-08-01T10:02:30.000Z", uuid="d2", agent_id="D",
             parent_uuid="d1", session_id=sid),
    ]
    if shift_finish:
        rows[-1]["timestamp"] = shift_finish
    _write_jsonl(sub / "agent-D.jsonl", rows)
    return root


def _collect(root):
    stats = {}
    rows = ft.collect_claude(root, queue_path=None, stats=stats)
    return rows, stats


def test_claude_fanout_metrics_and_real_edges(tmp_path):
    rows, _ = _collect(_claude_corpus(tmp_path))
    assert len(rows) == 1
    row = rows[0]
    assert row["schema"] == "fanout_timing.v1" and row["source"] == "claude"
    assert row["workflow_id"] == "session-A"
    assert row["declared_agents"] == 4
    assert row["started_agents"] == 4
    assert row["completed_agents"] == 4
    # span = min start (10:00:00 main) -> max finish (10:06:30 main) = 390 s
    assert row["workflow_span_s"] == pytest.approx(390.0)
    # max overlap: 10:02:00-10:02:30 has A, B and D active -> 3
    assert row["max_overlapping_subagents"] == 3
    # active: A=240, B=150, C=60, D=30 -> sum 480
    # utilization = 480 / (3 * 390) = 0.410256... (collector rounds to 6 dp)
    assert row["parallel_utilization"] == pytest.approx(round(480.0 / (3 * 390.0), 6))
    # D is depth 3 (main=1, A=2, D=3); everyone else depth 2.
    assert row["workflow_depth"] == 3
    by_id = {s["id"]: s for s in row["subagents"]}
    assert by_id["D"]["parent"] == "A"
    assert by_id["A"]["parent"] == "main"
    assert by_id["D"]["depth"] == 3
    assert by_id["A"]["depth"] == 2
    assert by_id["D"]["active_s"] == pytest.approx(30.0)
    assert by_id["C"]["active_s"] == pytest.approx(60.0)


def test_claude_edge_removal_degrades_depth(tmp_path):
    rows, _ = _collect(_claude_corpus(tmp_path, strip_parent_uuid=True))
    row = rows[0]
    # parentUuid removed -> D's edge to A disappears, parent falls back to main.
    by_id = {s["id"]: s for s in row["subagents"]}
    assert by_id["D"]["parent"] == "main"
    assert row["workflow_depth"] == 2


def test_claude_timestamp_change_moves_active_and_span(tmp_path):
    rows, _ = _collect(_claude_corpus(tmp_path, shift_finish="2026-08-01T10:07:00.000Z"))
    row = rows[0]
    by_id = {s["id"]: s for s in row["subagents"]}
    assert by_id["D"]["active_s"] == pytest.approx(300.0)
    # D's finish now exceeds the main's 10:06:30 finish -> span moves with it.
    assert row["workflow_span_s"] == pytest.approx(420.0)


def test_claude_serial_workflow_utilization_zero(tmp_path):
    root = tmp_path / "serial"
    _write_jsonl(root / "sess.jsonl", [
        _rec("user", "2026-08-01T10:00:00.000Z", uuid="x1", session_id="sess"),
        _rec("user", "2026-08-01T10:30:00.000Z", uuid="x2", session_id="sess"),
    ])
    rows, _ = _collect(root)
    assert len(rows) == 1
    row = rows[0]
    assert row["declared_agents"] == 0
    assert row["completed_agents"] == 0
    assert row["parallel_utilization"] == 0
    assert row["workflow_depth"] == 1
    assert row["workflow_span_s"] == pytest.approx(1800.0)


def test_claude_incomplete_subagent_started_not_completed(tmp_path):
    root = tmp_path / "incomplete"
    sub = root / "sess" / "subagents"
    _write_jsonl(root / "sess.jsonl", [
        _rec("user", "2026-08-01T10:00:00.000Z", uuid="m1", session_id="sess"),
    ])
    _write_jsonl(sub / "agent-X.jsonl", [
        _rec("user", "2026-08-01T10:01:00.000Z", uuid="x1", agent_id="X",
             session_id="sess"),
    ])
    # Torn tail: last line is not parseable JSON -> no finish.
    with (sub / "agent-Y.jsonl").open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(_rec("user", "2026-08-01T10:02:00.000Z", uuid="y1",
                                 agent_id="Y", session_id="sess")) + "\n")
        fh.write('{"type": "user", "timestamp": "2026-08-01T10:03:00.000Z",\n')
    rows, stats = _collect(root)
    assert stats["malformed_lines"] == 1
    row = rows[0]
    assert row["declared_agents"] == 2
    assert row["started_agents"] == 2
    assert row["completed_agents"] == 1


def test_claude_empty_dir(tmp_path):
    rows, stats = _collect(tmp_path)
    assert rows == []
    assert stats["workflows"] == 0


# --------------------------------------------------------------------------- Codex


def _codex_meta(session_id, rollout_id, parent_thread_id, depth, is_subagent, spawn_ts):
    source = {}
    if is_subagent:
        source = {"subagent": {"thread_spawn": {
            "parent_thread_id": parent_thread_id, "depth": depth,
            "agent_path": "/w", "agent_role": None}}}
    return {
        "timestamp": spawn_ts, "type": "session_meta",
        "payload": {"session_id": session_id, "id": rollout_id,
                    "parent_thread_id": parent_thread_id, "thread_source": "subagent" if is_subagent else "user",
                    "source": source},
    }


def _codex_rollout(root, name, session_id, rollout_id, parent_thread_id, depth,
                   is_subagent, first_ts, last_ts, terminal=True):
    day = root / "2026" / "08" / "01"
    day.mkdir(parents=True, exist_ok=True)
    rows = [_codex_meta(session_id, rollout_id, parent_thread_id, depth, is_subagent, first_ts)]
    rows.append({"timestamp": first_ts, "type": "turn_started",
                 "payload": {"type": "turn_started"}})
    rows.append({"timestamp": last_ts, "type": "event_msg",
                 "payload": {"type": "task_complete" if terminal else "token_count",
                             "agent_id": rollout_id}})
    _write_jsonl(day / f"rollout-{name}.jsonl", rows)


def _codex_corpus(root):
    # main -> s1 -> s2 -> s3 (thread_spawn depth chain of 3 subagents).
    _codex_rollout(root, "main", "SES", "main-1", None, None, False,
                   "2026-08-01T10:00:00.000Z", "2026-08-01T10:10:00.000Z")
    _codex_rollout(root, "s1", "SES", "sub-1", "main-1", 1, True,
                   "2026-08-01T10:00:30.000Z", "2026-08-01T10:05:00.000Z")
    _codex_rollout(root, "s2", "SES", "sub-2", "sub-1", 2, True,
                   "2026-08-01T10:01:00.000Z", "2026-08-01T10:04:00.000Z")
    _codex_rollout(root, "s3", "SES", "sub-3", "sub-2", 3, True,
                   "2026-08-01T10:02:00.000Z", "2026-08-01T10:03:00.000Z")
    return root


def test_codex_thread_spawn_chain_depth_and_parents(tmp_path):
    stats = {}
    rows = ft.collect_codex(_codex_corpus(tmp_path), stats=stats)
    assert stats["workflows"] == 1
    row = rows[0]
    assert row["source"] == "codex"
    assert row["declared_agents"] == 3
    assert row["completed_agents"] == 3
    assert row["workflow_depth"] == 4  # main=1 + chain of 3
    by_id = {s["id"]: s for s in row["subagents"]}
    assert by_id["sub-1"]["parent"] == "main"
    assert by_id["sub-2"]["parent"] == "sub-1"
    assert by_id["sub-3"]["parent"] == "sub-2"
    assert [by_id[k]["depth"] for k in ("sub-1", "sub-2", "sub-3")] == [2, 3, 4]
    # max overlap 3 (10:02-10:03), span 600s (main 10:00:00 -> 10:10:00)
    assert row["max_overlapping_subagents"] == 3
    # active: s1=270, s2=180, s3=60 -> 510; span 600; collector rounds to 6 dp
    assert row["parallel_utilization"] == pytest.approx(round(510.0 / (3 * 600.0), 6))


def test_codex_edge_removal_degrades_depth(tmp_path):
    root = _codex_corpus(tmp_path)
    # Strip the parent->child edge carriers: thread_spawn.parent_thread_id and
    # the payload-level parent_thread_id fallback. Classification (thread_source)
    # survives — only the EDGE is removed.
    for path in root.glob("**/rollout-*.jsonl"):
        lines = path.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[0])
        payload = meta["payload"]
        payload["source"] = {"subagent": {}}
        payload["parent_thread_id"] = None
        lines[0] = json.dumps(meta)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows = ft.collect_codex(root)
    row = rows[0]
    assert row["workflow_depth"] == 2  # all fall back to main
    assert all(s["parent"] == "main" for s in row["subagents"])


def test_codex_nonterminal_rollout_not_completed(tmp_path):
    root = _codex_corpus(tmp_path)
    # s3's last record is not a terminal payload type.
    target = root / "2026/08/01/rollout-s3.jsonl"
    lines = target.read_text(encoding="utf-8").splitlines()
    last = json.loads(lines[-1])
    last["payload"]["type"] = "token_count"
    lines[-1] = json.dumps(last)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    stats = {}
    rows = ft.collect_codex(root, stats=stats)
    row = rows[0]
    assert row["completed_agents"] == 2
    assert row["started_agents"] == 3


# --------------------------------------------------------------------------- cross-cutting


def test_collector_idempotence(tmp_path):
    root = _claude_corpus(tmp_path / "c")
    rows_a = ft.collect_claude(root)
    rows_b = ft.collect_claude(root)
    assert rows_a == rows_b
    out_a, out_b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    ft._atomic_write_jsonl(out_a, rows_a)
    ft._atomic_write_jsonl(out_b, rows_b)
    assert out_a.read_bytes() == out_b.read_bytes()


def test_merge_sorted_and_combined(tmp_path):
    claude_root = _claude_corpus(tmp_path / "c")
    codex_root = _codex_corpus(tmp_path / "x")
    claude_path = tmp_path / "c.jsonl"
    codex_path = tmp_path / "x.jsonl"
    merged_path = tmp_path / "merged.jsonl"
    ft._atomic_write_jsonl(claude_path, ft.collect_claude(claude_root))
    ft._atomic_write_jsonl(codex_path, ft.collect_codex(codex_root))
    rows = ft.merge(claude_path, codex_path, merged_path)
    assert [r["source"] for r in rows] == ["claude", "codex"]
    merged = merged_path.read_bytes()
    # deterministic: merging again is byte-identical
    rows2 = ft.merge(claude_path, codex_path, tmp_path / "merged2.jsonl")
    assert len(rows2) == 2
    assert (tmp_path / "merged2.jsonl").read_bytes() == merged
    with pytest.raises(ValueError):
        ft.merge(claude_path, claude_path, tmp_path / "bad.jsonl")


def test_queue_join_empty_when_no_tokens(tmp_path):
    # No queue file -> no fabrication of joins.
    root = _claude_corpus(tmp_path)
    rows = ft.collect_claude(root, queue_path=None)
    assert rows[0]["queue_task_ids"] == []
    rows2 = ft.collect_claude(root, queue_path=tmp_path / "missing.jsonl")
    assert rows2[0]["queue_task_ids"] == []


def test_queue_join_matches_real_token(tmp_path):
    queue = tmp_path / "queue.jsonl"
    _write_jsonl(queue, [{"task_id": "repl-turn-efficiency--003-L101", "status": "READY"},
                         {"task_id": "R3-staleness-guard", "status": "READY"}])
    root = tmp_path / "q"
    sub = root / "sess" / "subagents"
    _write_jsonl(root / "sess.jsonl", [
        _rec("user", "2026-08-01T10:00:00.000Z", uuid="m1", session_id="sess",
             content="dispatch repl-turn-efficiency--003-L101 to the worker"),
    ])
    _write_jsonl(sub / "agent-Q.jsonl", [
        _rec("user", "2026-08-01T10:01:00.000Z", uuid="q1", agent_id="Q",
             session_id="sess", content="Q task"),
    ])
    rows = ft.collect_claude(root, queue_path=queue)
    assert rows[0]["queue_task_ids"] == ["repl-turn-efficiency--003-L101"]


def test_cli_help_and_collect_subprocess(tmp_path):
    script = Path(__file__).parents[2] / "scripts/coordination/fanout_timing.py"
    help_run = subprocess.run([sys.executable, str(script), "--help"],
                              capture_output=True, text=True, check=False)
    assert help_run.returncode == 0
    for cmd in ("collect-claude", "collect-codex", "merge"):
        assert cmd in help_run.stdout
    root = _claude_corpus(tmp_path / "c")
    out = tmp_path / "out.jsonl"
    run = subprocess.run([sys.executable, str(script), "collect-claude",
                          "--root", str(root), "--output", str(out)],
                         capture_output=True, text=True, check=False)
    assert run.returncode == 0
    lines = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    assert len(lines) == 1 and lines[0]["declared_agents"] == 4
