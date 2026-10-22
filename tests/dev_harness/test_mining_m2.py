"""M2 mining (DHM-2/3/4/7.2): guard predicates, lesson registry, label sheet, clustering, driver.

Fixtures are synthetic and built at runtime; no transcript-shaped line is stored in this repo.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/dev_harness"))

import agentrun  # noqa: E402
import dh_privacy  # noqa: E402
import m2_cluster  # noqa: E402
import m2_label_sheet  # noqa: E402
import m2_lessons  # noqa: E402
import mine_m2  # noqa: E402
from m2_common import Call, build_unit, flatten_call  # noqa: E402
from m2_guards import shell_classes, unit_hits, write_classes  # noqa: E402


@pytest.mark.parametrize("cmd,cls", [
    ("pkill -f llama-server", "pattern_kill"),
    ("pgrep -af autopilot.py", "pgrep_pattern"),
    ("cd /workspace && git add -A && git commit -m x", "wholesale_git_add"),
    ("git commit -am 'msg'", "wholesale_git_add"),
    ("git stash -q && pytest", "git_stash"),
    ("python3 -m pytest -q tests | tail -1 && git push origin main", "piped_gate_push"),
    ("python3 scripts/handoffs/index_state.py --check | tail -1 && git push", "piped_gate_push"),
    ("cd d && rm -rf receipt-ab/paired-*", "glob_rm"),
    ("git clean -fdx", "git_clean"),
    ("git worktree prune", "git_worktree_prune_or_force"),
    ("git worktree remove --force /mnt/raid0/llm/worktrees/x", "git_worktree_prune_or_force"),
    ("git reset --hard origin/main", "git_reset_hard"),
    ("git commit --no-verify -m x", "no_verify"),
    ("git -c core.hooksPath=/dev/null commit -m x", "hooks_path_null"),
    ("llama-cli -m model.gguf -p hi", "llama_cli_unbounded"),
    ("python3 -m pytest -n auto tests", "pytest_xdist_auto"),
    ("python3 -m pytest tests --deselect tests/test_a.py::test_b", "test_deselect"),
    ("git rm tests/test_widget.py", "test_deleted"),
    ("gitnexus analyze", "bare_gitnexus_analyze"),
    ("echo hi > /etc/motd", "write_outside_allowlist"),
])
def test_shell_predicates_fire(cmd, cls):
    assert cls in shell_classes(cmd, "/workspace")


@pytest.mark.parametrize("cmd", [
    "echo 'pkill -f llama-server is forbidden'",
    "git commit -m 'add -A to the docs'",
    "git add scripts/a.py && git commit -m x",
    "set -o pipefail; pytest -q | tail -1 && git push",
    "git show --stat HEAD | tail -4 && git push origin HEAD:main",
    "pytest -q | tail -1; git push",
    "rm build/a.o",
    "git clean -n",
    "timeout 60 llama-cli -m m.gguf -p hi",
    "grep -n llama-cli docs/x.md",
    "git stash list",
    "cat > /workspace/x.md <<'EOF'\ngit add -A\npkill -f foo\nEOF",
    "scripts/gitnexus-analyze.sh",
    "kill 1234",
])
def test_shell_predicates_quiet(cmd):
    hits = shell_classes(cmd, "/workspace")
    assert hits == {}, hits


def test_quoted_glob_is_not_glob_rm():
    # the production containment scanner refuses a quoted rm target as unresolvable; glob_rm must not fire
    assert "glob_rm" not in shell_classes("rm -rf 'receipt-ab/paired-*'", "/workspace")


def test_truncated_heredoc_is_data():
    cmd = "cat > /workspace/r.md <<'EOF'\nran llama-cli -m x for 11h\n…[truncated 900 chars]"
    assert "llama_cli_unbounded" not in shell_classes(cmd, "/workspace")


def test_write_classes():
    c = Call(0, None, "Edit", "t1", {"file_path": "/workspace/tests/test_x.py",
                                     "old_string": "def test_a():\n    pass\ndef test_b():\n    pass",
                                     "new_string": "@pytest.mark.skip\ndef test_a():\n    pass"})
    c.write_paths = ["/workspace/tests/test_x.py"]
    hits = write_classes(c)
    assert {"test_skip_added", "test_deleted"} <= set(hits)
    w = Call(0, None, "Write", "t2", {"file_path": "/etc/cron.d/x", "content": ""})
    w.write_paths = ["/etc/cron.d/x"]
    assert "write_tool_outside_allowlist" in write_classes(w)


def test_flatten_codex_exec_and_list_command():
    js = 'text(await tools.exec_command({cmd:"git add -A && git commit -m \\"x\\"", yield_time_ms: 1}))'
    c = flatten_call(0, None, {"id": "c1", "function": "exec", "arguments": {"input": js}})
    assert c.commands == ['git add -A && git commit -m "x"']
    c2 = flatten_call(0, None, {"id": "c2", "function": "shell", "arguments": {"command": ["bash", "-lc", "git stash"]}})
    assert c2.commands == ["git stash"]
    patch = "*** Begin Patch\n*** Update File: /etc/hosts\n@@\n-a\n+b\n*** End Patch"
    c3 = flatten_call(0, None, {"id": "c3", "function": "apply_patch", "arguments": {"input": patch}})
    assert c3.write_paths == ["/etc/hosts"]


# ── synthetic AgentRun dir ───────────────────────────────────────────────────

def _msg(role, ts, **kw):
    md = {"ts": ts, "kind": kw.pop("kind", "chat")}
    md.update(kw.pop("md", {}))
    m = {"role": role, "metadata": md}
    m.update(kw)
    return m


def _unit_messages(i):
    day = f"2026-10-{10 + i % 5:02d}"
    t = lambda s: f"{day}T10:00:{s:02d}Z"  # noqa: E731
    return [
        _msg("user", t(0), content=f"please run the tests {i}", md={"human": True}),
        _msg("assistant", t(1), content=[], kind="tool_call", tool_calls=[
            {"id": f"a{i}", "type": "function", "function": "Bash",
             "arguments": {"command": "nohup ./run.sh &", "run_in_background": True}},
            {"id": f"b{i}", "type": "function", "function": "Bash",
             "arguments": {"command": "pkill -f llama-server"}}]),
        _msg("tool", t(2), content="started", tool_call_id=f"a{i}", function="Bash", error=None, kind="tool_result"),
        _msg("tool", t(3), content="BLOCKED: pkill against a NAME PATTERN", tool_call_id=f"b{i}", function="Bash",
             error={"type": "denial:hook_block", "message": "BLOCKED: pkill against a NAME PATTERN (check_process_pattern_kill)"},
             kind="tool_result"),
        _msg("assistant", t(4), content=[], kind="tool_call", tool_calls=[
            {"id": f"c{i}", "type": "function", "function": "Edit",
             "arguments": {"file_path": "/workspace/run.sh", "old_string": "a", "new_string": "b"}}]),
        _msg("tool", t(5), content="ok", tool_call_id=f"c{i}", function="Edit", error=None, kind="tool_result"),
        _msg("user", t(6), content="[Request interrupted by user]", kind="interrupt", md={"interrupt": "plain"}),
        _msg("user", t(9), content=f"no, stop editing that script {i}", md={"human": True}),
    ]


@pytest.fixture()
def synth_run(tmp_path):
    root = tmp_path / "private"
    ar = root / "agentrun" / "synth"
    ar.mkdir(parents=True)
    rows = []
    for i in range(6):
        p = ar / f"u{i}.seg-000.json"
        msgs = _unit_messages(i)
        meta = {"schema": agentrun.AGENTRUN_SCHEMA, "harness": "claude_code", "source": "epyc",
                "unit_key": f"unit-{i}", "segment_index": 0, "day": msgs[0]["metadata"]["ts"][:10],
                "first_ts": msgs[0]["metadata"]["ts"], "agent_name": "main"}
        p.write_text(json.dumps({"id": f"claude_code:epyc:unit-{i}:seg000",
                                 "transcripts": [{"messages": msgs}], "metadata": meta}))
        rows.append({**meta, "id": f"claude_code:epyc:unit-{i}:seg000", "path": str(p),
                     "source_path": f"/mnt/raid0/llm/cloud-llm-vault/epyc/claude/-workspace/unit-{i}.jsonl"})
    (ar / "index.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (root / "projections" / "synth").mkdir(parents=True)
    return root


def test_unit_hits_outcomes_and_running_script(synth_run):
    from m2_common import iter_units
    units = list(iter_units(synth_run / "agentrun" / "synth"))
    assert len(units) == 6 and units[0].is_main
    hits = {h["class"]: h for h in unit_hits(units[0])}
    assert hits["pattern_kill"]["outcome"] == "blocked_hook"
    assert hits["pattern_kill"]["hook_era"] == "hook_present"
    assert hits["edit_running_script"]["outcome"] == "slipped_through"


def test_driver_end_to_end(synth_run):
    a = mine_m2.build_parser().parse_args(["--projection", str(synth_run / "projections" / "synth"),
                                           "--private-root", str(synth_run), "--sheet-n", "4"])
    s = mine_m2.run(a)
    assert s["aggregate_valid"], s["aggregate_errors"]
    out = Path(s["out_dir"])
    agg = json.loads((out / "aggregate.json").read_text())
    assert dh_privacy.validate_aggregate(agg) == []
    assert agg["counts"]["dhm2"]["classes"]["pattern_kill"]["claude_code"]["epyc"]["blocked_hook"] == 6
    assert agg["counts"]["dhm4"]["interrupt_candidates"] == 6
    rows = list(csv.DictReader(io.StringIO((out / "dhm4_label_sheet.csv").read_text())))
    assert len(rows) == 4 and all(r["label"] == "" for r in rows)       # the OPERATOR labels it
    assert rows[0]["next_operator_message"].startswith("no, stop editing")
    md = (out / "dhm4_label_sheet.md").read_text()
    assert "[ ] slow/hanging" in md and "trigger-phrased applicability" in md
    assert (out / "aggregate.json").stat().st_mode & 0o077 == 0
    seg = agg["counts"]["dhm3"]["pattern_kill"]["segments"]
    assert all("control_per_1k_tool_calls" in v for v in seg.values())


def test_label_reader():
    text = "item_id,label\nDHM4-001,correction\nDHM4-002,slow/hanging\nDHM4-003,bogus\nDHM4-004,\n"
    r = m2_label_sheet.read_labels(text)
    assert r["labels"] == {"DHM4-001": "correction", "DHM4-002": "slow_hanging"}
    assert r["invalid"] == ["DHM4-003"]


def test_sample_is_stratified_and_deterministic():
    cands = [{"key": f"k{i}", "harness": h, "source": s, "interrupt_ts": f"2026-10-{i % 28 + 1:02d}"}
             for i, (h, s) in enumerate([("claude_code", "epyc")] * 200 + [("codex", "host")] * 90 +
                                        [("opencode", "twyne")] * 10)]
    a = m2_label_sheet.sample([dict(c) for c in cands], n=100)
    b = m2_label_sheet.sample([dict(c) for c in cands], n=100)
    assert len(a) == 100 and [x["key"] for x in a] == [x["key"] for x in b]
    mix = {}
    for x in a:
        mix[x["harness"]] = mix.get(x["harness"], 0) + 1
    assert mix == {"claude_code": 67, "codex": 30, "opencode": 3}


def test_cluster_planted_recovery_and_report_rule():
    docs = []
    for i in range(30):
        docs.append({"id": f"d{i}", "session": f"s{i % 5}", "harness": "codex", "source": "host",
                     "day": f"2026-09-0{1 + i % 3}", "tools": m2_cluster.Counter({"exec": 1}),
                     "etypes": m2_cluster.Counter({"tool_error": 1}),
                     "text": "exec ModuleNotFoundError: No module named numpy in /usr/lib/python3"})
    agg, rows = m2_cluster.run(docs, k=8)
    assert agg["planted_recovered"] >= 4
    assert agg["clusters_reported"] >= 1
    assert all(not r["id"].startswith("planted") for r in rows)
    assert dh_privacy.validate_aggregate({"schema": dh_privacy.AGGREGATE_SCHEMA, "counts": agg}) == []


def test_registry_builder(tmp_path):
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "MEMORY.md").write_text("- [no wholesale add](feedback_no_wholesale_git_add_shared_files.md)\n")
    (mem / "feedback_no_wholesale_git_add_shared_files.md").write_text(
        "---\nname: x\nmetadata:\n  type: feedback\n---\n2026-05-27: it happened, then 2026-06-01 again\n")
    (mem / "project_other.md").write_text("---\ntype: project\n---\n")
    inc = tmp_path / "INC.md"
    inc.write_text("# log\n\n## INC-20261004-glob-rm-deleted-receipt-evidence\ntext\n")
    cm = tmp_path / "CLAUDE.md"
    cm.write_text("# T\n## Process Management\n- **NEVER `pkill` on a name pattern** here\n")
    reg = m2_lessons.build_registry(mem, inc, cm)
    by = {l["id"]: l for l in reg["lessons"]}
    m = by["feedback_no_wholesale_git_add_shared_files"]
    assert (m["date"], m["channel"], m["detector"]) == ("2026-05-27", "memory", ["wholesale_git_add"])
    assert m["enforced_by"][0]["since"] == "2026-07-27"
    assert by["INC-20261004-glob-rm-deleted-receipt-evidence"]["detector"] == ["glob_rm"]
    assert by["claude_md:process-management:1"]["detector"] == ["pattern_kill", "pgrep_pattern"]
    assert "project_other" not in by


def test_committed_registry_covers_pilot():
    reg = m2_lessons.load_registry()
    ids = {l["id"]: l for l in reg["lessons"]}
    for cls, lids in reg["pilot"].items():
        assert any(i in ids and ids[i]["date"] and cls in ids[i]["detector"] for i in lids), cls
    assert reg["detector_map_ids_not_found"] == []


def test_gguf_embedder_contract_and_cluster_hook(monkeypatch):
    """The neural embedder is a drop-in: normalised matrix, same shape contract, wired through run(embedder=)."""
    import numpy as np
    import m2_embed_gguf

    calls = []

    def fake_runner(cmd, **kw):
        path = cmd[cmd.index("-f") + 1]
        n = len(open(path).read().split(m2_embed_gguf.SEP))
        calls.append(n)

        class R:
            returncode, stderr = 0, ""
            stdout = __import__("json").dumps({"data": [{"index": i, "embedding": [float(i % 3), 1.0, 0.5]}
                                                         for i in reversed(range(n))]})
        return R()
    monkeypatch.setattr(m2_embed_gguf, "BATCH", 4)
    out = m2_embed_gguf.embed_texts(["a doc"] * 10, runner=fake_runner)
    assert len(out) == 10 and calls == [4, 4, 2]
    assert out[1][0] == 1.0                       # re-sorted by index despite reversed reply
    monkeypatch.setattr(m2_embed_gguf, "embed_texts", lambda texts, gguf=None: [[3.0, 4.0]] * len(texts))
    X = m2_embed_gguf.make_embedder("x")([{"text": "t"}] * 3)
    assert np.allclose(np.linalg.norm(X, axis=1), 1.0)
    docs = [{"id": f"r{i}", "session": f"s{i}", "harness": "h", "source": "epyc", "day": f"2026-09-0{1 + i % 3}",
             "tools": m2_cluster.Counter({"exec": 1}), "etypes": m2_cluster.Counter({"tool_error": 1}),
             "text": "exec boom"} for i in range(8)]
    agg, _ = m2_cluster.run(docs, k=7, embedder=lambda ds: np.tile(np.array([[1.0, 0.0]]), (len(ds), 1)))
    assert agg["n_docs"] == 8 and agg["clusters_total"] >= 1
