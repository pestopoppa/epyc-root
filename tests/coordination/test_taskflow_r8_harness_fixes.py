"""r8 harness fixes: mangled lane-path repair (proxy) and shell pipe/redirect allow variants (r7d evidence)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow.harness import local_llm as L  # noqa: E402

LANES = {"e9f8", "23ca", "5ad0", "84fd", "65a8", "d908"}
EX = LANES.__contains__
R = L.LANES_ROOT


def test_repairs_r7d_observed_manglings():
    cases = {
        "<mnt/raid0/llm/tf/e9f8": f"{R}/e9f8",
        "<mnt/raid0/llm/tf/23ca/docs/x.md": f"{R}/23ca/docs/x.md",
        "mnt/raid0/tf/e9f8/scripts/a.py": f"{R}/e9f8/scripts/a.py",
        ".mnt/raid0/llm/tf/5ad0/.taskflow-refs": f"{R}/5ad0/.taskflow-refs",
        "/mnt/raid0/84fd/src/v.py": f"{R}/84fd/src/v.py",
        "/mnt/raid0/llm/t/65a8/.folded.json": f"{R}/65a8/.folded.json",
        "sed -n '1,2p' /mnt/raid0/tf/d908/s.py": f"sed -n '1,2p' {R}/d908/s.py",
    }
    for bad, good in cases.items():
        assert L.repair_lane_paths(bad, EX) == (good, 1), bad


def test_leaves_correct_and_unrelated_paths():
    for s in (f"{R}/e9f8/a.py", "/mnt/raid0/llm/harness/opencode/x.ts", "/mnt/raid0/llm/tf/ffff/a.py",
              "src/x.py", "/mnt/raid0/llm/models/beef"):
        assert L.repair_lane_paths(s, EX) == (s, 0), s


def _sse(parts):
    return [("data: " + json.dumps({"choices": [{"index": 0, "delta": {"tool_calls": [
        {"index": 0, "function": {"arguments": p}}]}}]}) + "\n\n").encode() for p in parts] + [b"data: [DONE]\n\n"]


def _args(chunks):
    a = ""
    for ln in b"".join(chunks).split(b"\n"):
        if ln.startswith(b"data: {"):
            for tc in json.loads(ln[6:])["choices"][0]["delta"].get("tool_calls") or []:
                a += tc["function"].get("arguments") or ""
    return a


def test_sse_rewrite_split_across_deltas():
    chunks = _sse(['{"filePath": "<mnt/rai', 'd0/llm/tf/e9f8/a.py"}'])
    out, n = L.rewrite_sse_tool_args(chunks, EX)
    assert n == 1 and json.loads(_args(out)) == {"filePath": f"{R}/e9f8/a.py"}
    assert b"[DONE]" in b"".join(out)


def test_sse_unchanged_is_byte_identical():
    chunks = _sse(['{"filePath": "src/a.py"}'])
    out, n = L.rewrite_sse_tool_args(chunks, EX)
    assert n == 0 and out is chunks


def _bash(tmp_path, acc="pytest -q tests/x.py"):
    task = {"budget": {"turns": 30}, "acceptance": acc, "test_cmds": []}
    L.write_config(tmp_path, "http://x", "m", task)
    return json.loads((tmp_path / "xdg-config/opencode/opencode.json").read_text())["agent"][L.AGENT]["permission"]["bash"]


def test_r7d_denied_read_only_commands_now_allowed(tmp_path):
    b = _bash(tmp_path)
    for k in ("cat *", "sed -n *", "pwd", "git show *", "cat * | head *", "pytest -q tests/x.py 2>&1 | tail *",
              "pytest -q tests/x.py * 2>&1"):
        assert b.get(k) == "allow", k
    for k in ("sed *-i*", "find *-exec*", "* > *", "git push*", "*"):
        assert b.get(k) == "deny", k


def test_policy_matches_config():
    assert "cat" in L.POLICY and "sed -n" in L.POLICY and "head" in L.POLICY
    assert "no pipes" not in L.POLICY


def test_phase2_prompt_does_not_point_at_missing_brief_section():
    t = {"handoff": "h.md", "id": "X", "text_sha": "x", "goal": "g", "budget": {"turns": 30}, "forbidden": ["a"]}
    assert "WRITE BRIEF FIRST" not in L.task_suffix(t, {})
    assert "WRITE BRIEF FIRST" in L.task_suffix(dict(t, phase="brief"), {})
