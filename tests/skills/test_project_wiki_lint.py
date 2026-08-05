from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / ".claude" / "skills" / "project-wiki" / "scripts" / "lint_wiki.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "project_wiki_lint",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_wiki_article_structure_accepts_reviewable_article(tmp_path: Path) -> None:
    module = _load_module()
    wiki_dir = tmp_path / "wiki"
    _write(
        wiki_dir / "agent-architecture.md",
        """# Agent Architecture

**Category**: `agent_architecture`

## Summary

Short summary.

## Key Findings

- Finding.

## Open Questions

- Question.

## Related Categories

- [Routing](routing-intelligence.md)

## Source References

- [handoff](../handoffs/active/example.md)
""",
    )
    _write(wiki_dir / "INDEX.md", "# Index\n\n")

    assert module.check_wiki_article_structure(wiki_dir) == []


def test_wiki_article_structure_flags_corrupt_generated_article(tmp_path: Path) -> None:
    module = _load_module()
    wiki_dir = tmp_path / "wiki"
    _write(
        wiki_dir / "routing-intelligence.md",
        """Body without a title.

**Category**: `routing_intelligence`

## Key Findings

- Finding.
""",
    )

    issues = module.check_wiki_article_structure(wiki_dir)

    assert (module.ERROR, "wiki/routing-intelligence.md", "Missing top-level H1 heading") in issues
    assert (
        module.ERROR,
        "wiki/routing-intelligence.md",
        "Missing required section: ## Summary",
    ) in issues
    assert (
        module.ERROR,
        "wiki/routing-intelligence.md",
        "Missing source-reference section: ## Source References or ## References",
    ) in issues


def test_wiki_article_structure_treats_uncategorized_page_as_legacy(
    tmp_path: Path,
) -> None:
    module = _load_module()
    wiki_dir = tmp_path / "wiki"
    _write(
        wiki_dir / "chat-templates.md",
        """# Chat Templates

## Family Notes

Reference page with a hand-curated shape.
""",
    )

    assert module.check_wiki_article_structure(wiki_dir) == [
        (
            module.WARNING,
            "wiki/chat-templates.md",
            "Missing **Category** metadata; treating as a legacy/reference page",
        )
    ]


def test_unactioned_intake_accepts_created_or_updated_handoff(tmp_path: Path) -> None:
    module = _load_module()
    index_path = tmp_path / "intake_index.yaml"
    old_date = (date.today() - timedelta(days=60)).isoformat()
    _write(
        index_path,
        f"""entries:
  - id: intake-created
    title: Created route
    verdict: worth_investigating
    ingested_date: {old_date}
    handoffs_created: [created.md]
  - id: intake-updated
    title: Updated route
    verdict: new_opportunity
    ingested_date: {old_date}
    handoffs_updated: [updated.md]
  - id: intake-unrouted
    title: Unrouted item
    verdict: worth_investigating
    ingested_date: {old_date}
""",
    )

    issues = module.check_unactioned_intake(index_path, max_age_days=30)

    assert len(issues) == 1
    assert issues[0][0] == module.WARNING
    assert issues[0][1] == "intake-unrouted"
    assert "no handoff created or updated" in issues[0][2]
