"""C5 (AK audit B10/B11): FRESHNESS and row checks are diff-scoped; the generated files have ONE writer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import index_state as I  # noqa: E402

STATE = {"rows": {"RTG-1": {"index": "x-index.md", "line": 7}, "RTG-2": {"index": "x-index.md", "line": 9}}}
LONG = "PROSE: row RTG-1 next-action is 156 chars (max 140)"


def test_row_checks_fail_only_for_rows_in_the_diff(monkeypatch):
    monkeypatch.setattr(I, "commit_diff", lambda base: ({"handoffs/active/x-index.md"}, {"handoffs/active/x-index.md": {9}}))
    errs, warns = I.diff_scope([LONG, "BAD DEP: row RTG-2 depends on unknown id ZZZ-9"], STATE, None)
    assert errs == ["BAD DEP: row RTG-2 depends on unknown id ZZZ-9"] and warns[0].startswith(LONG)   # touched Y only
    monkeypatch.setattr(I, "commit_diff", lambda base: ({"handoffs/active/x-index.md"}, {"handoffs/active/x-index.md": {7}}))
    errs, _ = I.diff_scope([LONG], STATE, None)
    assert errs == [LONG]                                                                              # touched X: fail


def test_freshness_warns_unless_the_commit_touches_generated_files(monkeypatch):
    f = "FRESHNESS: master index generated block is stale — run without --check"
    monkeypatch.setattr(I, "commit_diff", lambda base: ({"handoffs/active/a.md"}, {}))
    assert I.diff_scope([f, "ORPHAN: a.md has no index row"], STATE, None)[0] == ["ORPHAN: a.md has no index row"]
    monkeypatch.setattr(I, "commit_diff", lambda base: ({"handoffs/active/.index-state.json"}, {}))
    assert I.diff_scope([f], STATE, None)[0] == [f]


def test_writer_guard(monkeypatch):
    monkeypatch.delenv("EPYC_INDEX_WRITER", raising=False)
    sys.path.insert(0, str(I.REPO_ROOT / "scripts" / "coordination"))
    import toolroot
    monkeypatch.setattr(toolroot, "HUB", "/nonexistent/hub")
    assert I.writer_allowed() is False
    monkeypatch.setenv("EPYC_INDEX_WRITER", "hub")
    assert I.writer_allowed() is True
    monkeypatch.delenv("EPYC_INDEX_WRITER")
    monkeypatch.setattr(toolroot, "HUB", str(I.REPO_ROOT))
    assert I.writer_allowed() is True
