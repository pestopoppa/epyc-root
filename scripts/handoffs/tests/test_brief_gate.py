"""Task-brief layer P2: rule k in the diff gate, brief fields in `.box-index.json`, `handoff_box.py add --brief` and
`brief accept` (docs/design/task-brief-layer.md §6/§7)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import box_index as BI  # noqa: E402
import handoff_box as HB  # noqa: E402
import task_lint as TL  # noqa: E402

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t"}
HANDOFF = "# fx\n\n## Track: T\n\n### Backlog\n\n"
B = HB._brief_mod()


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True, env=ENV).stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv(B.GITNEXUS_ENV, "")
    B._GN_STATUS.clear()
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/fx.md").write_text(HANDOFF)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/x.py").write_text("def parse(s):\n    return s\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def _add(repo, bid="BR-1", brief=True, extra=()):
    argv = ["add", "--file", str(repo / "handoffs/active/fx.md"), "--track", "T", "--id", bid,
            "--class", "non-inference", "--text", f"fix the parser {bid}", "--done-when", "`python3 scripts/x.py`"]
    if brief:
        argv += ["--brief", "--where", "epyc-root:scripts/x.py::parse", "--approach", "make it strict", *extra]
    monkey_root = HB.REPO_ROOT
    try:
        HB.REPO_ROOT = repo                    # all_ids() scans the fixture
        return HB.main(argv)
    finally:
        HB.REPO_ROOT = monkey_root


def test_add_with_brief_writes_compiling_sidecar(repo):
    assert _add(repo) == 0
    doc = B.parse_text((repo / "handoffs/active/briefs/BR-1.md").read_text())
    assert doc["acceptance"] == "python3 scripts/x.py" and doc["accepted"] == "auto"
    _git(repo, "add", ".")
    lines, n = TL.diff_gate(repo, None, "default")
    assert n == 0 and not any("rule k" in l for l in lines), lines


def test_new_box_without_brief_warns(repo):
    assert _add(repo, brief=False) == 0
    _git(repo, "add", ".")
    lines, n = TL.diff_gate(repo, None, "default")
    assert n == 0 and any(l.startswith("WARN") and "rule k " in l for l in lines), lines
    assert TL.diff_gate(repo, None, "enforce")[1] == 0          # enforce is the a/f switch; k stays warn


def test_mismatched_brief_fails(repo):
    assert _add(repo) == 0
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "box + brief")
    p = repo / "handoffs/active/briefs/BR-1.md"
    p.write_text(p.read_text().replace(B.parse_text(p.read_text())["box_text_sha"], "deadbeefdeadbeef"))
    _git(repo, "add", ".")
    lines, n = TL.diff_gate(repo, None, "default")
    assert n == 1 and any("ERROR" in l and "k-mismatch" in l for l in lines), lines
    assert TL.diff_gate(repo, None, "warn")[1] == 0


def test_box_field_edit_with_orphaned_brief_fails(repo):
    assert _add(repo) == 0
    p = repo / "handoffs/active/briefs/BR-1.md"
    p.write_text(p.read_text().replace(B.parse_text(p.read_text())["box_text_sha"], "deadbeefdeadbeef"))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "box + bad brief")
    HB.REPO_ROOT, old = repo, HB.REPO_ROOT
    try:
        assert HB.main(["gate", "--file", str(repo / "handoffs/active/fx.md"), "BR-1", "--add", "XYZ-1"]) == 0
    finally:
        HB.REPO_ROOT = old
    _git(repo, "add", ".")
    lines, n = TL.diff_gate(repo, None, "default")
    assert n >= 1 and any("k-mismatch" in l and "fx.md" in l for l in lines), lines


def test_box_index_brief_fields_and_coverage(repo):
    assert _add(repo) == 0
    assert _add(repo, "BR-2", brief=False) == 0
    B.compile_brief("BR-1", repo)
    doc = BI.build(repo, {"fx.md": repo / "handoffs/active/fx.md"}, {}, {}, {})
    b1, b2 = doc["boxes"]["BR-1"], doc["boxes"]["BR-2"]
    assert b1["brief"] == "fresh" and b1["accepted"] == "auto" and b1["brief_sha"]
    assert b2["brief"] == "none"
    assert doc["counts"]["briefed"] == 1 and doc["counts"]["brief_total"] == 2


def test_brief_accept_refuses_orphan(repo):
    assert _add(repo, extra=["--brief-author", "self"]) == 0
    assert B.parse_text((repo / "handoffs/active/briefs/BR-1.md").read_text())["review"] == "backfill"
    assert HB.main(["brief", "accept", "BR-1", "--root", str(repo)]) == 0
    assert "review" not in B.parse_text((repo / "handoffs/active/briefs/BR-1.md").read_text())
    p = repo / "handoffs/active/briefs/BR-1.md"
    p.write_text(p.read_text().replace(B.parse_text(p.read_text())["box_text_sha"], "deadbeefdeadbeef"))
    assert HB.main(["brief", "accept", "BR-1", "--root", str(repo)]) == 1
