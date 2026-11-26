"""Task-brief layer P3 (docs/design/task-brief-layer.md §7/§11): the brief merged into epyc.task.v1, the worker
suffix sections (WHERE / APPROACH / NON-GOALS / STALE), the retrieval tool allowlist, and a byte-identical stable
prefix across tasks with different brief states."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
from taskflow import brief as B, schema  # noqa: E402
from taskflow.harness import local_llm  # noqa: E402

BOX = "- [ ] **BR-1** [non-inference] fix the parser in `scripts/x.py`"


def _tree(tmp_path):
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/h.md").write_text(
        f"# H\n## Track: T\n### Backlog\n{BOX}\n      · done when: `python3 scripts/x.py`\n      · gate: none\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/x.py").write_text("def parse(s):\n    return s\n")
    return tmp_path


def _rec(root):
    return {"file": "handoffs/active/h.md", "line": 4, "id": "BR-1", "class": "non-inference",
            "text_sha": schema.text_sha(BOX)}


def _task(**kw):
    t = {"handoff": "handoffs/active/h.md", "id": "BR-1", "text_sha": "0" * 16, "goal": BOX,
         "done_when": "`python3 scripts/x.py`", "test_cmds": ["python3 scripts/x.py"], "refs": [],
         "forbidden": ["handoffs/**"], "budget": dict(schema.DEFAULT_BUDGET), "where": [], "approach": None,
         "non_goals": [], "acceptance": None, "brief_state": "none", "stale": [], "blast_radius": {}}
    t.update(kw)
    return t


def test_merge_brief_into_task(tmp_path, monkeypatch):
    monkeypatch.setenv(B.GITNEXUS_ENV, "")
    B._GN_STATUS.clear()
    root = _tree(tmp_path)
    monkeypatch.setitem(schema.REPOS, "epyc-root", root)
    t = schema.build(_rec(root), root=root)
    assert t["brief_state"] == "none" and t["where"] == [] and t["stale"] == []
    B.write_brief("BR-1", ["epyc-root:scripts/x.py::parse"], "make parse strict by rejecting non-string input early", "python3 scripts/x.py",
                  ["no new deps"], root=root, today="2026-11-20")
    t = schema.build(_rec(root), root=root)
    assert t["brief_state"] == "fresh" and t["where"] == ["epyc-root:scripts/x.py::parse"]
    assert t["approach"] == "make parse strict by rejecting non-string input early" and t["acceptance"] == "python3 scripts/x.py"
    assert t["non_goals"] == ["no new deps"] and t["acceptance_matches_done_when"] is True
    assert t["brief_accepted"] == "auto" and t["brief_path"] == "handoffs/active/briefs/BR-1.md"
    (root / "scripts/x.py").unlink()
    t = schema.build(_rec(root), root=root)
    assert t["brief_state"] == "stale" and any("x.py" in s for s in t["stale"])


SNAPSHOT = """## BOX (handoffs/active/h.md, id BR-1)
- [ ] **BR-1** [non-inference] fix the parser in `scripts/x.py`

## DONE WHEN
`python3 scripts/x.py`
## WHERE
- epyc-root:scripts/x.py::parse  (blast radius HIGH: change with care)
## APPROACH
make parse strict
## NON-GOALS (doing any of these is drift)
- no new deps
## STALE (the brief no longer matches the tree)
- where: epyc-root:scripts/y.py: path missing at HEAD
## ALLOWED COMMANDS
pytest -q tests/test_x.py
python3 scripts/x.py
Read-only helpers: gitnexus query|context|impact <name>.
Untracked scratch files: `taskflow-scratch rm <relative path>` or `taskflow-scratch mv <relative src> <relative dst>`.
## FORBIDDEN
handoffs/** …
## LIMITS
30 tool turns max. Be brief.
"""


def test_suffix_snapshot_shows_brief_sections():
    t = _task(where=["epyc-root:scripts/x.py::parse"], approach="make parse strict\n", non_goals=["no new deps"],
              acceptance="pytest -q tests/test_x.py", brief_state="stale",
              stale=["where: epyc-root:scripts/y.py: path missing at HEAD"], blast_radius={"parse": "HIGH"})
    assert local_llm.task_suffix(t, {}) == SNAPSHOT


def test_suffix_write_brief_first_phase():
    s = local_llm.task_suffix(_task(phase="brief"), {})
    assert "## WRITE BRIEF FIRST" in s and local_llm.BRIEF_RESULT in s and "## WHERE" not in s
    assert s.index("## DONE WHEN") < s.index("## WRITE BRIEF FIRST") < s.index("## ALLOWED COMMANDS")


def test_prefix_byte_identity_across_three_tasks(tmp_path, monkeypatch):
    """Everything that reaches the stable prefix (instructions file + its bytes + the config outside the per-task bash
    allow patterns) is byte-identical for a briefed, a stale-briefed and an unbriefed task."""
    monkeypatch.setattr(local_llm, "POLICY_DIR", tmp_path / "pol")
    tasks = [_task(where=["epyc-root:scripts/x.py"], approach="a", acceptance="pytest -q tests/a.py",
                   brief_state="fresh"),
             _task(brief_state="stale", stale=["x"], test_cmds=[]),
             _task(phase="brief", test_cmds=["bash scripts/t.sh"])]
    cfgs, pols = [], []
    for n, t in enumerate(tasks):
        c = json.loads(local_llm.write_config(tmp_path / f"r{n}", "http://x/v1", "m", t).read_text())
        pols.append(Path(c["instructions"][0]).read_bytes())
        perm = c["agent"][local_llm.AGENT]["permission"]
        for ro in local_llm.RETRIEVAL:
            assert perm["bash"][ro] == "allow"                         # tool allowlist (P3)
        perm.pop("bash"), perm.pop("shell")
        cfgs.append(json.dumps(c, sort_keys=True).encode())
    assert len(set(cfgs)) == 1 and len(set(pols)) == 1
    assert pols[0] == local_llm.POLICY.encode()
    c0 = json.loads(local_llm.write_config(tmp_path / "a0", "http://x/v1", "m", tasks[0]).read_text())
    bash = c0["agent"][local_llm.AGENT]["permission"]["bash"]
    assert bash["pytest -q tests/a.py"] == "allow"                     # acceptance allowed, listed first
    assert local_llm.allowed_commands(tasks[0])[0] == "pytest -q tests/a.py"
