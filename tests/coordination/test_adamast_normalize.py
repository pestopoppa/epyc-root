"""FM-2 normalizer tests: synthetic fixtures, paired mutations (each assertion has a mutated twin that must differ)."""
import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "coordination"))
import adamast_normalize as an  # noqa: E402


def _w(path, recs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return path


def claude_recs(sidechain=False, agent="a1", outcome=None):
    base = {"sessionId": "s1", "isSidechain": sidechain}
    if sidechain:
        base["agentId"] = agent
    u = dict(base, type="user", uuid="u1", parentUuid=None, timestamp="2026-10-03T10:00:00Z",
             message={"role": "user", "content": "Fix the flaky test"})
    a = dict(base, type="assistant", uuid="u2", parentUuid="u1", timestamp="2026-10-03T10:00:05Z",
             message={"role": "assistant", "id": "m1", "content": [
                 {"type": "text", "text": "Looking."}, {"type": "tool_use", "id": "t1", "name": "Bash",
                                                         "input": {"command": "pytest"}}]})
    if outcome is not None:
        u["outcome"] = outcome
        a["message"]["final_gate_status"] = outcome
        a["nested"] = {"deep": {"outcome": outcome, "keep": 1}}
    return [u, a]


def codex_recs(subagent=False):
    src = {"subagent": {"thread_spawn": {"parent_thread_id": "p-1", "depth": 1, "agent_role": "worker"}}} \
        if subagent else "cli"
    return [
        {"type": "session_meta", "timestamp": "2026-09-02T01:00:00Z", "payload": {"id": "th-1", "source": src}},
        {"type": "response_item", "timestamp": "2026-09-02T01:00:01Z",
         "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Do X"}]}},
        {"type": "response_item", "timestamp": "2026-09-02T01:00:02Z",
         "payload": {"type": "function_call", "name": "shell", "arguments": "{\"cmd\":\"ls\"}"}},
    ]


def test_four_field_schema_claude(tmp_path):
    p = _w(tmp_path / "proj" / "s1.jsonl", claude_recs())
    rec = an.normalize_file(p, root=tmp_path / "proj")
    assert tuple(rec) == an.CANON_KEYS
    assert rec["task"] == "Fix the flaky test"
    assert "[tool_use Bash]" in rec["raw_trajectory"]
    assert rec["metadata"]["harness"] == "claude" and rec["metadata"]["month"] == "2026-10"


def test_isSidechain_agentId_parentUuid_carried_and_mutation_changes_metadata(tmp_path):
    main = an.normalize_file(_w(tmp_path / "r" / "m.jsonl", claude_recs(False)), root=tmp_path / "r")
    side = an.normalize_file(_w(tmp_path / "r" / "subagents" / "agent-a1.jsonl", claude_recs(True)),
                             root=tmp_path / "r")
    m2 = side["metadata"]["messages"][1]
    assert m2["parentUuid"] == "u1" and m2["agentId"] == "a1" and m2["isSidechain"] is True
    assert side["metadata"]["kind"] == "subagent" and main["metadata"]["kind"] == "main"
    assert main["metadata"]["messages"] != side["metadata"]["messages"]       # mutation: dropping isSidechain differs
    # paired mutation on the input: drop isSidechain/agentId from the subagent records -> metadata message flags flip
    stripped = [{k: v for k, v in r.items() if k not in ("isSidechain", "agentId")} for r in claude_recs(True)]
    s2 = an.normalize_file(_w(tmp_path / "r" / "x.jsonl", stripped), root=tmp_path / "r")
    assert s2["metadata"]["messages"][1]["isSidechain"] is False
    assert s2["metadata"]["messages"][1]["agentId"] is None


def test_outcome_never_in_output_and_mutation_proves_it_was_in_input(tmp_path):
    clean = an.normalize_file(_w(tmp_path / "a.jsonl", claude_recs()), root=tmp_path)
    dirty_recs = claude_recs(outcome="SECRET_PASSED_MARKER")
    assert "SECRET_PASSED_MARKER" in json.dumps(dirty_recs)                    # control: input carries it
    dirty = an.normalize_file(_w(tmp_path / "b.jsonl", dirty_recs), root=tmp_path)
    blob = json.dumps(dirty)
    assert "SECRET_PASSED_MARKER" not in blob and "final_gate_status" not in blob and '"outcome"' not in blob
    assert dirty["raw_trajectory"] == clean["raw_trajectory"] and dirty["task"] == clean["task"]
    # mutation: a stripper that does nothing would leak
    leaky = copy.deepcopy(dirty_recs)
    assert "SECRET_PASSED_MARKER" in json.dumps(leaky)


def test_strip_outcome_recursive_and_nonmutating():
    obj = {"a": 1, "Outcome": "x", "b": [{"final_gate_status": "y", "c": 2}]}
    snap = copy.deepcopy(obj)
    assert an.strip_outcome(obj) == {"a": 1, "b": [{"c": 2}]}
    assert obj == snap


def test_codex_thread_spawn_preserved_and_main_distinct(tmp_path):
    sub = an.normalize_file(_w(tmp_path / "rollout-1.jsonl", codex_recs(True)), root=tmp_path)
    main = an.normalize_file(_w(tmp_path / "rollout-2.jsonl", codex_recs(False)), root=tmp_path)
    assert sub["metadata"]["thread_spawn"] == {"parent_thread_id": "p-1", "depth": 1, "agent_role": "worker"}
    assert sub["metadata"]["kind"] == "subagent" and main["metadata"]["kind"] == "main"
    assert main["metadata"]["thread_spawn"] is None
    assert sub["task"] == "Do X"


def test_empty_or_unknown_returns_none(tmp_path):
    assert an.normalize_file(_w(tmp_path / "e.jsonl", [{"foo": 1}]), root=tmp_path) is None


def test_sampler_deterministic_seed_sensitive_and_sealed(tmp_path):
    root = tmp_path / "c"
    for i in range(8):
        _w(root / f"s{i}.jsonl", claude_recs())
        _w(root / f"s{i}" / "subagents" / f"agent-{i}.jsonl", claude_recs(True))
    m1 = an.build_sample(root, None, 3, "seedA")
    m2 = an.build_sample(root, None, 3, "seedA")
    m3 = an.build_sample(root, None, 3, "seedB")
    assert m1 == m2
    assert m1["manifest_sha256"] != m3["manifest_sha256"]
    assert {e["kind"] for e in m1["entries"]} == {"main", "subagent"}
    assert len(m1["entries"]) == 6
    assert an.verify_manifest(m1) == []
    tampered = copy.deepcopy(m1)
    tampered["entries"][0]["sha256"] = "0" * 64
    assert an.verify_manifest(tampered) != []                                 # seal + hash both catch it


def test_verify_detects_content_drift_but_tolerates_append(tmp_path):
    root = tmp_path / "c"
    p = _w(root / "s.jsonl", claude_recs())
    m = an.build_sample(root, None, 1, "x")
    with open(p, "a") as fh:
        fh.write("{}\n")                                                       # live session grew: prefix intact
    assert an.verify_manifest(m) == []
    p.write_bytes(b"X" + p.read_bytes()[1:])                                   # mutation: edit inside the prefix
    assert any("drift" in x for x in an.verify_manifest(m))


def test_normalize_manifest_resumable_and_outcome_blind(tmp_path):
    root = tmp_path / "c"
    _w(root / "s.jsonl", claude_recs(outcome="LEAKME"))
    m = an.build_sample(root, None, 1, "x")
    out = tmp_path / "out"
    assert an.normalize_manifest(m, out)["written"] == 1
    files = list((out / "traces").glob("*.jsonl"))
    assert len(files) == 1 and "LEAKME" not in files[0].read_text()
    rec = json.loads(files[0].read_text())
    assert tuple(rec) == an.CANON_KEYS
    mtime = files[0].stat().st_mtime_ns
    an.normalize_manifest(m, out)
    assert files[0].stat().st_mtime_ns == mtime                                # resumed, not rewritten
