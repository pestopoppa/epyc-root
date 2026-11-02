"""KT-1 lint passes and KT-4 renderer: fixtures with a known orphan, unsourced bullet,
section-sourced bullet, pending contradiction, and a lossless/idempotent restructure."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".claude" / "skills" / "project-wiki" / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"pw_{name}", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


lint = _load("lint_wiki")
render = _load("render_wiki")

PAGE = """# Topic

**Last compiled**: 2026-11-01 (sweep). Earlier: 2026-10-01.

## Compiled Update — 2026-11-01 (sweep)

- Cited claim from intake-123#02.
- A bare assertion nobody sourced.

### Open questions

- Is this exempt?

## Compiled Update — 2026-10-01 (older)

- Section-sourced bullet with no inline source.

### Source References

- [handoff](../handoffs/active/x.md)

## Summary

The topic is about things. Second sentence.

## Related Categories

- [Other](other.md)
"""


def _wiki(tmp_path):
    w = tmp_path / "wiki"
    w.mkdir()
    (w / "INDEX.md").write_text("# Index\n\n- [Topic](topic.md)\n")
    (w / "topic.md").write_text(PAGE)
    (w / "other.md").write_text("# Other\n\n## Summary\n\nOther page.\n")
    (w / "lonely.md").write_text("# Lonely\n\n## Summary\n\nNobody links here.\n")
    return w


def test_orphans(tmp_path):
    issues = lint.check_wiki_orphans(_wiki(tmp_path))
    assert [t for _, t, _ in issues] == ["wiki/lonely.md"]


def test_unsourced_bullets(tmp_path):
    issues = lint.check_unsourced_bullets(_wiki(tmp_path))
    by = {(sev, msg.split(":")[0]) for sev, _, msg in issues}
    assert by == {("WARNING", "unsourced bullet"), ("INFO", "section-sourced bullet")}
    assert len(issues) == 2  # cited and open-question bullets are not flagged


def test_contradictions_pass(tmp_path):
    q = tmp_path / "q.jsonl"
    q.write_text(json.dumps({"id": "ctr_x", "status": "pending",
                             "a": {"path": "wiki/a.md", "line": 3},
                             "b": {"path": "wiki/b.md", "line": 9}}) + "\n"
                 + json.dumps({"id": "ctr_y", "status": "resolved",
                               "a": {"path": "a", "line": 1}, "b": {"path": "b", "line": 1}}) + "\n")
    issues = lint.check_contradictions(q)
    assert len(issues) == 1 and "ctr_x" in issues[0][2]


def test_restructure_lossless_and_idempotent():
    out = render.restructure_text(PAGE)
    assert render.check_lossless(PAGE, out)
    assert render.restructure_text(out) == out
    body, log = out.split(render.LOG_HEADING)
    assert "## Summary" in body and "Compiled Update" not in body and "Last compiled" not in body
    assert "### Compiled Update — 2026-11-01" in log and "#### Source References" in log
    assert "(../handoffs/active/x.md)" in log


def test_index_and_edges(tmp_path):
    w = _wiki(tmp_path)
    pages = {p.name: p.read_text() for p in w.glob("*.md") if p.name != "INDEX.md"}
    idx = render.render_index((w / "INDEX.md").read_text(), pages)
    assert "[Topic](topic.md) — The topic is about things." in idx
    assert render.render_index(idx, pages) == idx
    kinds = {(e["kind"], e["dst"]) for e in render.wiki_edges(w)}
    assert ("intake_citation", "intake-123#02") in kinds
    assert ("md_link", "handoffs/active/x.md") in kinds


def test_unsourced_counts_survive_restructure(tmp_path):
    w = _wiki(tmp_path)
    before = lint.check_unsourced_bullets(w)
    (w / "topic.md").write_text(render.restructure_text(PAGE))
    assert sorted(m for *_, m in lint.check_unsourced_bullets(w)) == sorted(m for *_, m in before)
