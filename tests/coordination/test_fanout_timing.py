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
    assert row["schema"] == "fanout_timing.v2" and row["source"] == "claude"
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
                   is_subagent, first_ts, last_ts, terminal=True, report=None,
                   tokens=None, patch_paths=(), terminal_type=None, mentions=None):
    """`report`/`tokens`/`patch_paths`/`mentions` are the v2 (FM-5/FM-6) payloads;
    omitting them reproduces the v1 fixture byte for byte."""
    day = root / "2026" / "08" / "01"
    day.mkdir(parents=True, exist_ok=True)
    rows = [_codex_meta(session_id, rollout_id, parent_thread_id, depth, is_subagent, first_ts)]
    rows.append({"timestamp": first_ts, "type": "turn_started",
                 "payload": {"type": "turn_started"}})
    if tokens is not None:
        rows.append({"timestamp": first_ts, "type": "event_msg",
                     "payload": {"type": "token_count",
                                 "info": {"total_token_usage": tokens}}})
    for path in patch_paths:
        rows.append({"timestamp": first_ts, "type": "response_item",
                     "payload": {"type": "function_call", "name": "exec_command",
                                 "arguments": json.dumps({
                                     "cmd": f"apply_patch <<EOF\n*** Update File: {path}\nEOF"})}})
    if report is not None:
        rows.append({"timestamp": last_ts, "type": "event_msg",
                     "payload": {"type": "agent_message", "message": report}})
    for ts, text in (mentions or []):
        rows.append({"timestamp": ts, "type": "response_item",
                     "payload": {"type": "function_call", "name": "exec_command",
                                 "arguments": json.dumps({"cmd": text})}})
    payload = {"type": terminal_type or ("task_complete" if terminal else "token_count"),
               "agent_id": rollout_id}
    if report is not None and payload["type"] == "task_complete":
        payload["last_agent_message"] = report
    rows.append({"timestamp": last_ts, "type": "event_msg", "payload": payload})
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


# ===========================================================================
# FM-5 (outcome accounting) and FM-6 (reconnection requirement) — schema v2.
#
# Every positive case below is paired with a MUTATION case that removes exactly
# the signal under test, proving the assertion fires on the signal and not on
# the fixture. D9-ack: operator tasking 2026-09-07 (RTG-49 FM-5/FM-6).
# ===========================================================================

_PAST = ft._parse_ts("2026-07-01T00:00:00.000Z")      # committed BEFORE any run
_FUTURE = ft._parse_ts("2026-08-01T23:00:00.000Z")    # committed AFTER every run

#: `docs/used.md` is the cited artifact; `docs/written.md` is the one a subagent
#: actually mutates. A path absent from this index is not an artifact path.
def _git(**overrides):
    paths = {"docs/used.md": _PAST, "handoffs/active/fm.md": _PAST,
             "docs/written.md": _PAST}
    paths.update(overrides)
    return ft.GitPathIndex(paths)


REPORT_U = ("Done. I reconnected the collector and left the evidence in docs/used.md; "
            "the backlog row is handoffs/active/fm.md and nothing else changed.")


def _sub_records(agent_id, *, report=REPORT_U, usage=None, write_path=None,
                 api_error=False, session_id="sess"):
    rows = [_rec("user", "2026-08-01T10:01:00.000Z", uuid=f"{agent_id}1",
                 agent_id=agent_id, session_id=session_id, content="task")]
    if write_path is not None:
        wr = _rec("assistant", "2026-08-01T10:03:00.000Z", uuid=f"{agent_id}w",
                  agent_id=agent_id, session_id=session_id)
        wr["message"] = {"role": "assistant", "content": [
            {"type": "tool_use", "id": "tu1", "name": "Write",
             "input": {"file_path": f"/workspace/{write_path}", "content": "x"}}]}
        rows.append(wr)
    if report is not None:
        last = _rec("assistant", "2026-08-01T10:04:00.000Z", uuid=f"{agent_id}2",
                    agent_id=agent_id, session_id=session_id)
        last["message"] = {"role": "assistant",
                           "content": [{"type": "text", "text": report}],
                           "usage": usage or {"input_tokens": 10, "output_tokens": 20,
                                              "cache_creation_input_tokens": 5,
                                              "cache_read_input_tokens": 1000}}
        if api_error:
            last["isApiErrorMessage"] = True
        rows.append(last)
    return rows


def _notification(ts, agent_id, status, result):
    r = _rec("user", ts, uuid=f"n-{agent_id}", session_id="sess")
    status_tag = f"<status>{status}</status>" if status else ""
    r["message"] = {"role": "user", "content": (
        f"<task-notification><task-id>{agent_id}</task-id>{status_tag}"
        f"<result>{result}</result></task-notification>")}
    return r


def _parent_tool(ts, command, uuid="pt"):
    r = _rec("assistant", ts, uuid=uuid, session_id="sess")
    r["message"] = {"role": "assistant", "content": [
        {"type": "tool_use", "id": uuid, "name": "Bash", "input": {"command": command}}]}
    return r


def _outcome_corpus(root, *, parent_ref="cat docs/used.md", session=True,
                    status="completed", sub_kwargs=None, extra_parent=()):
    """One main session + one subagent U. The notification ALWAYS quotes U's
    report verbatim (that is how Claude records it) — so any test that lands on
    `produced-and-discarded` also proves the notification is not read as reuse."""
    sub_dir = root / "sess" / "subagents"
    _write_jsonl(sub_dir / "agent-U.jsonl", _sub_records("U", **(sub_kwargs or {})))
    if session:
        rows = [_rec("user", "2026-08-01T10:00:00.000Z", uuid="m1",
                     session_id="sess", content="go"),
                _notification("2026-08-01T10:05:00.000Z", "U", status, REPORT_U)]
        if parent_ref is not None:
            rows.append(_parent_tool("2026-08-01T10:06:00.000Z", parent_ref))
        rows.extend(extra_parent)
        _write_jsonl(root / "sess.jsonl", rows)
    else:
        # No main transcript on disk: the used/discarded split is unobservable.
        sub_dir.mkdir(parents=True, exist_ok=True)
    return root


def _one(root, git_index=None, queue_path=None):
    rows = ft.collect_claude(root, queue_path=queue_path,
                             git_index=git_index if git_index is not None else _git())
    assert len(rows) == 1
    return rows[0], {s["id"]: s for s in rows[0]["subagents"]}


# --------------------------------------------------------------- FM-5 ladder


def test_outcome_used_via_parent_reference(tmp_path):
    row, by_id = _one(_outcome_corpus(tmp_path))
    assert by_id["U"]["outcome"] == "produced-and-used"
    assert by_id["U"]["outcome_basis"] == "parent-reference"
    assert row["outcome_counts"]["produced-and-used"] == 1
    assert row["outcome_tokens"]["produced-and-used"] == by_id["U"]["tokens"]["total"]


def test_outcome_discarded_when_parent_reference_removed(tmp_path):
    """MUTATION of the test above: the parent's post-finish tool call no longer
    names the artifact. The notification still quotes the whole report (which
    contains `docs/used.md`) — if notifications counted as reuse this would
    still read 'used', so this case also proves the self-quote is excluded."""
    root = _outcome_corpus(tmp_path, parent_ref="cat docs/unrelated.md")
    session_text = (root / "sess.jsonl").read_text()
    assert "docs/used.md" in session_text  # the notification DOES carry it
    row, by_id = _one(root)
    assert by_id["U"]["outcome"] == "produced-and-discarded"
    assert by_id["U"]["outcome_basis"] == "no-reuse-observed"
    assert row["outcome_counts"]["produced-and-used"] == 0


def test_outcome_self_match_guard_rejects_quoted_report(tmp_path):
    """A parent record that merely PASTES the child's report back is not reuse:
    the child's report signature sits beside the hit."""
    quote = _rec("assistant", "2026-08-01T10:06:00.000Z", uuid="q1", session_id="sess")
    quote["message"] = {"role": "assistant", "content": [{"type": "text", "text": REPORT_U}]}
    root = _outcome_corpus(tmp_path, parent_ref=None, extra_parent=[quote])
    _, by_id = _one(root)
    assert by_id["U"]["outcome"] == "produced-and-discarded"


def test_outcome_self_match_guard_still_allows_a_real_later_mention(tmp_path):
    """MUTATION: same quoted report, PLUS an independent later mention far from
    the signature. The guard must not swallow that one."""
    quote = _rec("assistant", "2026-08-01T10:06:00.000Z", uuid="q1", session_id="sess")
    quote["message"] = {"role": "assistant", "content": [{"type": "text", "text": REPORT_U}]}
    later = _parent_tool("2026-08-01T10:07:00.000Z", "wc -l docs/used.md", uuid="q2")
    cmd = later["message"]["content"][0]["input"]
    cmd["command"] = ("#pad " * 1600) + cmd["command"]
    root = _outcome_corpus(tmp_path, parent_ref=None, extra_parent=[quote, later])
    _, by_id = _one(root)
    assert by_id["U"]["outcome"] == "produced-and-used"
    assert by_id["U"]["outcome_basis"] == "parent-reference"


def test_outcome_aborted_from_notification_status(tmp_path):
    row, by_id = _one(_outcome_corpus(tmp_path, status="killed"))
    assert by_id["U"]["outcome"] == "aborted"
    assert by_id["U"]["outcome_basis"] == "notification:killed"
    assert row["outcome_counts"]["aborted"] == 1
    # aborted outranks the reuse evidence, which is still present in the fixture
    assert "docs/used.md" in (root_ref := (tmp_path / "sess.jsonl").read_text()) and root_ref


def test_outcome_not_aborted_when_status_is_completed(tmp_path):
    """MUTATION: the only change is `killed` -> `completed`."""
    _, by_id = _one(_outcome_corpus(tmp_path, status="completed"))
    assert by_id["U"]["outcome"] == "produced-and-used"


def test_outcome_blocked_on_api_error_tail(tmp_path):
    _, by_id = _one(_outcome_corpus(
        tmp_path, sub_kwargs={"report": "You've hit your session limit",
                              "api_error": True}))
    assert by_id["U"]["outcome"] == "blocked"
    assert by_id["U"]["outcome_basis"] == "claude:api-error-tail"


def test_outcome_not_blocked_without_the_api_error_flag(tmp_path):
    """MUTATION: identical transcript with `isApiErrorMessage` removed."""
    _, by_id = _one(_outcome_corpus(
        tmp_path, sub_kwargs={"report": "You've hit your session limit",
                              "api_error": False}))
    assert by_id["U"]["outcome"] != "blocked"
    assert by_id["U"]["outcome"] == "produced-and-discarded"


def test_outcome_no_output_when_subagent_never_reports(tmp_path):
    row, by_id = _one(_outcome_corpus(tmp_path, sub_kwargs={"report": None}))
    assert by_id["U"]["outcome"] == "no-output"
    assert by_id["U"]["outcome_basis"] == "no-final-report"
    assert row["outcome_counts"]["no-output"] == 1


def test_outcome_no_output_flips_when_a_report_exists(tmp_path):
    """MUTATION: the same transcript with one assistant text block added."""
    _, by_id = _one(_outcome_corpus(tmp_path, sub_kwargs={"report": REPORT_U}))
    assert by_id["U"]["outcome"] != "no-output"


def test_outcome_unknown_when_parent_transcript_is_absent(tmp_path):
    """The used/discarded split is NOT observable without the parent side, so it
    is reported as `unknown` — never folded into `produced-and-discarded`."""
    row, by_id = _one(_outcome_corpus(tmp_path, session=False))
    assert by_id["U"]["outcome"] == "unknown"
    assert by_id["U"]["outcome_basis"] == "parent-transcript-absent"
    assert row["outcome_counts"]["produced-and-discarded"] == 0


def test_outcome_unknown_resolves_once_the_parent_exists(tmp_path):
    """MUTATION: only the presence of `sess.jsonl` changes."""
    _, by_id = _one(_outcome_corpus(tmp_path, session=True,
                                    parent_ref="cat docs/unrelated.md"))
    assert by_id["U"]["outcome"] == "produced-and-discarded"


def test_outcome_unknown_when_parent_index_truncated(tmp_path):
    """A parent index that hit its byte cap before the subagent's window cannot
    prove absence of reuse -> `unknown`, not `produced-and-discarded`."""
    index = ft.ParentIndex(cap=1)
    index.add(ft._parse_ts("2026-08-01T10:00:00.000Z"), "early line")
    index.add(ft._parse_ts("2026-08-01T10:09:00.000Z"), "late line docs/used.md")
    index.finalize()
    assert index.truncated
    sub = {"produced_output": True, "written_paths": [], "output_paths": ["docs/used.md"],
           "output_tasks": [], "finish_epoch": ft._parse_ts("2026-08-01T10:04:00.000Z"),
           "report_signature": "sig"}
    assert ft.classify_outcome(sub, index, _git()) == ("unknown", "parent-index-truncated")


def test_outcome_discarded_when_index_is_not_truncated(tmp_path):
    """MUTATION of the above: the same records under a cap that fits."""
    index = ft.ParentIndex(cap=10_000)
    index.add(ft._parse_ts("2026-08-01T10:00:00.000Z"), "early line")
    index.add(ft._parse_ts("2026-08-01T10:09:00.000Z"), "late line docs/OTHER.md")
    index.finalize()
    assert not index.truncated
    sub = {"produced_output": True, "written_paths": [], "output_paths": ["docs/used.md"],
           "output_tasks": [], "finish_epoch": ft._parse_ts("2026-08-01T10:04:00.000Z"),
           "report_signature": "sig"}
    assert ft.classify_outcome(sub, index, _git()) == ("produced-and-discarded",
                                                       "no-reuse-observed")


# --------------------------------------------------------------- git landing


def test_outcome_used_when_a_written_path_lands_in_git(tmp_path):
    root = _outcome_corpus(tmp_path, parent_ref="cat docs/unrelated.md",
                           sub_kwargs={"write_path": "docs/written.md"})
    _, by_id = _one(root, git_index=_git(**{"docs/written.md": _FUTURE}))
    assert by_id["U"]["written_paths"] == ["docs/written.md"]
    assert by_id["U"]["outcome"] == "produced-and-used"
    assert by_id["U"]["outcome_basis"] == "git-landed"


def test_outcome_not_used_when_the_commit_predates_the_subagent(tmp_path):
    """MUTATION: identical corpus, the commit epoch moved BEFORE the finish."""
    root = _outcome_corpus(tmp_path, parent_ref="cat docs/unrelated.md",
                           sub_kwargs={"write_path": "docs/written.md"})
    _, by_id = _one(root, git_index=_git(**{"docs/written.md": _PAST}))
    assert by_id["U"]["written_paths"] == ["docs/written.md"]
    assert by_id["U"]["outcome"] == "produced-and-discarded"


def test_git_landing_ignores_a_merely_cited_path(tmp_path):
    """A path the subagent only CITED, committed later by somebody else, is not
    evidence its work was used — only paths it MUTATED count."""
    root = _outcome_corpus(tmp_path, parent_ref="cat docs/unrelated.md")
    _, by_id = _one(root, git_index=_git(**{"docs/used.md": _FUTURE}))
    assert by_id["U"]["output_paths"] == ["docs/used.md", "handoffs/active/fm.md"]
    assert by_id["U"]["written_paths"] == []
    assert by_id["U"]["outcome"] == "produced-and-discarded"


# --------------------------------------------------------------- FM-6 orphans


def test_orphan_when_output_links_to_nothing(tmp_path):
    root = _outcome_corpus(tmp_path, parent_ref=None,
                           sub_kwargs={"report": "I looked around and formed an opinion."})
    row, by_id = _one(root)
    assert by_id["U"]["orphan"] is True
    assert by_id["U"]["output_paths"] == [] and by_id["U"]["output_tasks"] == []
    assert row["orphan_agents"] == 1 and row["linked_agents"] == 0
    assert row["measured_fanout_width"] == 0
    assert row["max_overlapping_subagents"] == 1  # v1 field stays orphan-BLIND


def test_orphan_clears_when_the_report_cites_a_committed_path(tmp_path):
    """MUTATION: the only change is one sentence naming a path git knows."""
    root = _outcome_corpus(tmp_path, parent_ref=None,
                           sub_kwargs={"report": "I formed an opinion; see docs/used.md."})
    row, by_id = _one(root)
    assert by_id["U"]["orphan"] is False
    assert row["orphan_agents"] == 0 and row["linked_agents"] == 1
    assert row["measured_fanout_width"] == 1


def test_orphan_when_the_cited_path_is_unknown_to_git(tmp_path):
    """MUTATION on the ORACLE rather than the fixture: same report, empty git
    index. A path nobody ever committed is not an artifact path."""
    root = _outcome_corpus(tmp_path, parent_ref=None,
                           sub_kwargs={"report": "I formed an opinion; see docs/used.md."})
    _, by_id = _one(root, git_index=ft.GitPathIndex())
    assert by_id["U"]["orphan"] is True


def test_orphan_clears_on_a_queue_task_id(tmp_path):
    queue = tmp_path / "q" / "queue.jsonl"   # never inside the corpus root
    _write_jsonl(queue, [{"task_id": "fleet-fanout-measurement--FM-5-L55"}])
    root = _outcome_corpus(
        tmp_path / "corpus", parent_ref=None,
        sub_kwargs={"report": "Row fleet-fanout-measurement--FM-5-L55 is done."})
    _, by_id = _one(root, git_index=ft.GitPathIndex(), queue_path=queue)
    assert by_id["U"]["output_tasks"] == ["fleet-fanout-measurement--FM-5-L55"]
    assert by_id["U"]["orphan"] is False


def test_measured_width_excludes_orphans(tmp_path):
    """Two subagents overlap; one is an orphan. The orphan-blind width is 2, the
    reconnected width is 1 — the distinction FM-6 exists to make."""
    sub_dir = tmp_path / "sess" / "subagents"
    _write_jsonl(sub_dir / "agent-U.jsonl", _sub_records("U"))
    _write_jsonl(sub_dir / "agent-V.jsonl",
                 _sub_records("V", report="No artifacts, just a view."))
    _write_jsonl(tmp_path / "sess.jsonl", [
        _rec("user", "2026-08-01T10:00:00.000Z", uuid="m1", session_id="sess", content="go")])
    rows = ft.collect_claude(tmp_path, git_index=_git())
    row = rows[0]
    assert row["max_overlapping_subagents"] == 2
    assert row["measured_fanout_width"] == 1
    assert row["orphan_agents"] == 1


# --------------------------------------------------------------- token totals


def test_tokens_summed_from_usage(tmp_path):
    _, by_id = _one(_outcome_corpus(tmp_path))
    tok = by_id["U"]["tokens"]
    assert tok == {"input": 10, "output": 20, "cache_creation": 5,
                   "cache_read": 1000, "new": 35, "total": 1035}


def test_tokens_move_with_usage(tmp_path):
    """MUTATION: usage doubled; both totals must move, and `new` must NOT
    absorb the cache-read column."""
    _, by_id = _one(_outcome_corpus(tmp_path, sub_kwargs={
        "usage": {"input_tokens": 20, "output_tokens": 40,
                  "cache_creation_input_tokens": 10, "cache_read_input_tokens": 2000}}))
    tok = by_id["U"]["tokens"]
    assert tok["new"] == 70 and tok["total"] == 2070


# --------------------------------------------------------------- Codex v2


def _codex_outcome_corpus(root, *, terminal_type=None, report="Patched docs/written.md.",
                          patch_paths=("docs/written.md",), mention_ts="2026-08-01T10:09:00.000Z",
                          mention="cat docs/written.md"):
    _codex_rollout(root, "main", "SES", "main-1", None, None, False,
                   "2026-08-01T10:00:00.000Z", "2026-08-01T10:10:00.000Z",
                   mentions=[(mention_ts, mention)] if mention else None)
    _codex_rollout(root, "s1", "SES", "sub-1", "main-1", 1, True,
                   "2026-08-01T10:01:00.000Z", "2026-08-01T10:05:00.000Z",
                   report=report, patch_paths=patch_paths, terminal_type=terminal_type,
                   tokens={"input_tokens": 900, "cached_input_tokens": 800,
                           "output_tokens": 50, "total_tokens": 950})
    return root


def _codex_one(root, git_index=None):
    rows = ft.collect_codex(root, git_index=git_index if git_index is not None else _git())
    assert len(rows) == 1
    return rows[0], {s["id"]: s for s in rows[0]["subagents"]}


def test_codex_outcome_used_via_parent_reference(tmp_path):
    _, by_id = _codex_one(_codex_outcome_corpus(tmp_path))
    assert by_id["sub-1"]["written_paths"] == ["docs/written.md"]
    assert by_id["sub-1"]["outcome"] == "produced-and-used"
    assert by_id["sub-1"]["outcome_basis"] == "parent-reference"


def test_codex_outcome_discarded_when_the_parent_never_mentions_it(tmp_path):
    """MUTATION: the parent's post-finish command names a different file."""
    _, by_id = _codex_one(_codex_outcome_corpus(tmp_path, mention="cat docs/other.md"))
    assert by_id["sub-1"]["outcome"] == "produced-and-discarded"


def test_codex_parent_mention_before_the_finish_is_not_reuse(tmp_path):
    """MUTATION on the CLOCK: the same mention, moved before the subagent ended."""
    _, by_id = _codex_one(_codex_outcome_corpus(
        tmp_path, mention_ts="2026-08-01T10:02:00.000Z"))
    assert by_id["sub-1"]["outcome"] == "produced-and-discarded"


def test_codex_outcome_aborted_on_turn_aborted(tmp_path):
    row, by_id = _codex_one(_codex_outcome_corpus(tmp_path, terminal_type="turn_aborted"))
    assert by_id["sub-1"]["outcome"] == "aborted"
    assert by_id["sub-1"]["outcome_basis"] == "codex:turn_aborted"
    assert row["outcome_counts"]["aborted"] == 1


def test_codex_outcome_not_aborted_on_task_complete(tmp_path):
    """MUTATION: the single terminal payload type flips back."""
    _, by_id = _codex_one(_codex_outcome_corpus(tmp_path, terminal_type="task_complete"))
    assert by_id["sub-1"]["outcome"] != "aborted"


def test_codex_no_output_without_an_agent_message(tmp_path):
    _, by_id = _codex_one(_codex_outcome_corpus(tmp_path, report=None))
    assert by_id["sub-1"]["outcome"] == "no-output"


def test_codex_tokens_from_last_token_count(tmp_path):
    _, by_id = _codex_one(_codex_outcome_corpus(tmp_path))
    assert by_id["sub-1"]["tokens"] == {"input": 100, "output": 50, "cache_creation": 0,
                                        "cache_read": 800, "new": 150, "total": 950}


def test_codex_tokens_move_with_the_token_count_record(tmp_path):
    """MUTATION: rewrite the rollout's token_count payload in place."""
    root = _codex_outcome_corpus(tmp_path)
    target = root / "2026/08/01/rollout-s1.jsonl"
    lines = target.read_text().splitlines()
    for i, line in enumerate(lines):
        rec = json.loads(line)
        if rec.get("payload", {}).get("type") == "token_count":
            rec["payload"]["info"]["total_token_usage"] = {
                "input_tokens": 300, "cached_input_tokens": 100,
                "output_tokens": 7, "total_tokens": 307}
            lines[i] = json.dumps(rec)
    target.write_text("\n".join(lines) + "\n")
    _, by_id = _codex_one(root)
    assert by_id["sub-1"]["tokens"]["new"] == 207
    assert by_id["sub-1"]["tokens"]["total"] == 307


def test_codex_apply_patch_paths_are_the_only_written_paths(tmp_path):
    """MUTATION: with no apply_patch header there are no written paths, so the
    git-landing branch cannot fire even when the commit is in the future."""
    root = _codex_outcome_corpus(tmp_path, patch_paths=(), mention=None)
    _, by_id = _codex_one(root, git_index=_git(**{"docs/written.md": _FUTURE}))
    assert by_id["sub-1"]["written_paths"] == []
    assert by_id["sub-1"]["outcome_basis"] != "git-landed"


def test_codex_git_landing_on_apply_patch_path(tmp_path):
    root = _codex_outcome_corpus(tmp_path, mention=None)
    _, by_id = _codex_one(root, git_index=_git(**{"docs/written.md": _FUTURE}))
    assert by_id["sub-1"]["outcome"] == "produced-and-used"
    assert by_id["sub-1"]["outcome_basis"] == "git-landed"


# --------------------------------------------------------------- report / v1


def _v1_row(subagent_ids):
    return {"schema": "fanout_timing.v1", "source": "claude", "workflow_id": "old",
            "declared_agents": len(subagent_ids), "started_agents": len(subagent_ids),
            "completed_agents": len(subagent_ids), "workflow_span_s": 10.0,
            "parallel_utilization": 0.5, "workflow_depth": 2,
            "max_overlapping_subagents": len(subagent_ids),
            "subagents": [{"id": i, "parent": "main", "depth": 2, "start_ts": None,
                           "finish_ts": None, "active_s": 1.0} for i in subagent_ids],
            "queue_task_ids": [], "collected_at": "2026-08-25T00:00:00.000Z",
            "collector_sha256": "0" * 64}


def test_report_does_not_fold_v1_rows_into_a_bucket(tmp_path):
    v2 = ft.collect_claude(_outcome_corpus(tmp_path / "c"), git_index=_git())
    path = tmp_path / "mixed.jsonl"
    ft._atomic_write_jsonl(path, v2 + [_v1_row(["old-1", "old-2"])])
    report = ft.outcome_report([path])
    assert report["subagents"] == 3
    assert report["schema_v1_no_outcome"] == 2
    assert report["classified_subagents"] == 1
    assert sum(report["outcome_counts"].values()) == 1
    assert report["workflows_v1"] == 1


def test_report_counts_v2_rows_only_when_they_are_v2(tmp_path):
    """MUTATION: the same two subagents carried as v2 rows are classified."""
    v2 = ft.collect_claude(_outcome_corpus(tmp_path / "c"), git_index=_git())
    path = tmp_path / "pure.jsonl"
    ft._atomic_write_jsonl(path, v2)
    report = ft.outcome_report([path])
    assert report["schema_v1_no_outcome"] == 0
    assert report["classified_subagents"] == 1
    assert report["used_token_share"] + report["unused_token_share"] \
        + report["unknown_token_share"] == pytest.approx(1.0)


def test_report_unused_share_denominator_excludes_unknown(tmp_path):
    """`unknown` tokens are reported on their own line and are NOT counted as
    unused — the whole point of keeping the bucket."""
    root = _outcome_corpus(tmp_path / "u", session=False)
    rows = ft.collect_claude(root, git_index=_git())
    path = tmp_path / "unk.jsonl"
    ft._atomic_write_jsonl(path, rows)
    report = ft.outcome_report([path])
    assert report["outcome_counts"]["unknown"] == 1
    assert report["unknown_token_share"] == pytest.approx(1.0)
    assert report["unused_token_share"] == pytest.approx(0.0)


def test_merge_still_accepts_v1_rows(tmp_path):
    claude_path, codex_path = tmp_path / "c.jsonl", tmp_path / "x.jsonl"
    ft._atomic_write_jsonl(claude_path, [_v1_row(["old-1"])])
    ft._atomic_write_jsonl(codex_path, ft.collect_codex(_codex_outcome_corpus(tmp_path / "x")))
    rows = ft.merge(claude_path, codex_path, tmp_path / "m.jsonl")
    assert [r["schema"] for r in rows] == ["fanout_timing.v1", "fanout_timing.v2"]


def test_merge_rejects_an_unknown_schema(tmp_path):
    """MUTATION: one character of the schema string."""
    claude_path, codex_path = tmp_path / "c.jsonl", tmp_path / "x.jsonl"
    bad = _v1_row(["old-1"])
    bad["schema"] = "fanout_timing.v0"
    ft._atomic_write_jsonl(claude_path, [bad])
    ft._atomic_write_jsonl(codex_path, ft.collect_codex(_codex_outcome_corpus(tmp_path / "x")))
    with pytest.raises(ValueError):
        ft.merge(claude_path, codex_path, tmp_path / "m.jsonl")


def test_v2_is_a_superset_of_v1_fields(tmp_path):
    """Every v1 field survives with its v1 meaning; v2 only ADDS."""
    row = ft.collect_claude(_claude_corpus(tmp_path / "c"))[0]
    for field in ("declared_agents", "started_agents", "completed_agents",
                  "workflow_span_s", "parallel_utilization", "workflow_depth",
                  "max_overlapping_subagents", "queue_task_ids", "collected_at",
                  "collector_sha256"):
        assert field in row
    for field in ("measured_fanout_width", "orphan_agents", "linked_agents",
                  "outcome_counts", "outcome_tokens"):
        assert field in row
    for sub in row["subagents"]:
        assert set(sub) >= {"id", "parent", "depth", "start_ts", "finish_ts", "active_s",
                            "outcome", "outcome_basis", "orphan", "tokens",
                            "output_paths", "output_tasks", "written_paths"}


def test_cli_report_subcommand(tmp_path):
    script = Path(__file__).parents[2] / "scripts/coordination/fanout_timing.py"
    rows = ft.collect_claude(_outcome_corpus(tmp_path / "c"), git_index=_git())
    path = tmp_path / "in.jsonl"
    ft._atomic_write_jsonl(path, rows)
    out = tmp_path / "rollup.json"
    run = subprocess.run([sys.executable, str(script), "report", "--input", str(path),
                          "--output", str(out)], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    payload = json.loads(out.read_text())
    assert payload["classified_subagents"] == 1
    assert set(payload["outcome_counts"]) == set(ft.OUTCOME_BUCKETS)


def test_worktree_path_resolves_to_the_repo_path(tmp_path):
    """A lane subagent writes through `/mnt/raid0/llm/worktrees/<...>/<lane>/`;
    the nesting depth varies, so the git index — not a fixed prefix rule —
    decides which suffix is the repo path."""
    root = _outcome_corpus(
        tmp_path, parent_ref="cat docs/unrelated.md",
        sub_kwargs={"write_path": "mnt/raid0/llm/worktrees/mains/laneX/docs/written.md"})
    _, by_id = _one(root, git_index=_git(**{"docs/written.md": _FUTURE}))
    assert by_id["U"]["written_paths"] == ["docs/written.md"]
    assert by_id["U"]["outcome_basis"] == "git-landed"


def test_worktree_resolution_does_not_promote_a_scratch_path(tmp_path):
    """MUTATION: the same shape under a path git does not know. No suffix
    resolves, so nothing is promoted and git-landing cannot fire."""
    root = _outcome_corpus(
        tmp_path, parent_ref="cat docs/unrelated.md",
        sub_kwargs={"write_path": "mnt/raid0/llm/tmp/scratch/docs/notwritten.md"})
    _, by_id = _one(root, git_index=_git(**{"docs/written.md": _FUTURE}))
    assert by_id["U"]["written_paths"] == ["mnt/raid0/llm/tmp/scratch/docs/notwritten.md"]
    assert by_id["U"]["outcome_basis"] != "git-landed"


def test_suffix_resolution_only_applies_under_a_container_root(tmp_path):
    """MUTATION on the ORACLE: an identical suffix under a non-container first
    segment is left alone, so `tmp/...` cannot borrow a repo path's identity."""
    rec = ft.Reconnector(git_index=_git())
    assert rec.resolve("mnt/raid0/llm/worktrees/mains/laneX/docs/used.md") == "docs/used.md"
    assert rec.resolve("tmp/whatever/docs/used.md") == "tmp/whatever/docs/used.md"
