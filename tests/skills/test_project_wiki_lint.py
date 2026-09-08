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


CLONE_REPOS_FARM = """#!/bin/bash
repos=(
    epyc-orchestrator:epyc-orchestrator:epyc-orchestrator
    epyc-inference-research:epyc-inference-research:epyc-inference-research
    epyc-llama:llama.cpp:llama.cpp
)
"""


def _write_farm_definition(root: Path) -> None:
    _write(root / "scripts" / "clone-repos.sh", CLONE_REPOS_FARM)


def _wiki_page_with_links() -> str:
    return """# Page

**Category**: `agent_architecture`

## Summary

Summary.

## Source References

- [handoff](../handoffs/active/real.md)
- [missing handoff](../handoffs/active/missing.md)
- [research chapter](../repos/epyc-inference-research/docs/chapters/06-benchmarking-framework.md)
- [unknown repo](../repos/not-a-farm-member/docs/x.md)
"""


def test_wiki_link_targets_skips_cross_repo_targets_when_farm_absent(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _write_farm_definition(tmp_path)
    _write(tmp_path / "handoffs" / "active" / "real.md", "# Real\n")
    _write(tmp_path / "wiki" / "agent-architecture.md", _wiki_page_with_links())

    issues = module.check_wiki_link_targets(tmp_path / "wiki")

    errors = [issue for issue in issues if issue[0] == module.ERROR]
    infos = [issue for issue in issues if issue[0] == module.INFO]
    assert len(errors) == 2
    assert [error[2] for error in errors] == [
        "Dangling link target: ../handoffs/active/missing.md "
        f"(resolves to {tmp_path / 'handoffs' / 'active' / 'missing.md'})",
        "Dangling link target: ../repos/not-a-farm-member/docs/x.md "
        f"(resolves to {tmp_path / 'repos' / 'not-a-farm-member' / 'docs' / 'x.md'})",
    ]
    assert len(infos) == 1
    assert "cross-repo target under repos/" in infos[0][2]


def test_wiki_link_targets_verifies_cross_repo_targets_when_farm_present(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _write_farm_definition(tmp_path)
    _write(
        tmp_path / "repos" / "epyc-inference-research" / "docs" / "ok.md",
        "# Ok\n",
    )
    _write(
        tmp_path / "wiki" / "agent-architecture.md",
        """# Page

**Category**: `agent_architecture`

## Summary

Summary.

## Source References

- [present](../repos/epyc-inference-research/docs/ok.md)
- [absent](../repos/epyc-inference-research/docs/gone.md)
""",
    )

    issues = module.check_wiki_link_targets(tmp_path / "wiki")

    errors = [issue for issue in issues if issue[0] == module.ERROR]
    assert [error[1] for error in errors] == ["wiki/agent-architecture.md"]
    assert "gone.md" in errors[0][2]
    assert all("cross-repo" not in error[2] for error in errors)


def test_missing_crossrefs_skips_cross_repo_targets_when_farm_absent(
    tmp_path: Path,
) -> None:
    module = _load_module()
    _write_farm_definition(tmp_path)
    active_dir = tmp_path / "handoffs" / "active"
    completed_dir = tmp_path / "handoffs" / "completed"
    _write(active_dir / "owner.md", "# Owner\n")
    _write(
        active_dir / "links.md",
        """# Links

- [research notes](../../repos/epyc-inference-research/research/notes.md)
- [missing](../../handoffs/completed/never-was.md)
""",
    )

    issues = module.check_missing_crossrefs(active_dir, completed_dir)

    assert issues == [
        (
            module.INFO,
            "links.md",
            "cross-repo target under repos/epyc-inference-research cannot be "
            "verified from this worktree (the repos/ symlink farm exists only "
            "in /workspace); skipped, not flagged dangling: "
            "../../repos/epyc-inference-research/research/notes.md",
        ),
        (
            module.ERROR,
            "links.md",
            "Broken link: [../../handoffs/completed/never-was.md] target not found",
        ),
    ]


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
    assert "[legacy-needs-disposition]" in issues[0][2]


def test_unactioned_intake_reports_distinct_disposition_categories(tmp_path: Path) -> None:
    module = _load_module()
    index_path = tmp_path / "intake_index.yaml"
    active_dir = tmp_path / "active"
    completed_dir = tmp_path / "completed"
    active_dir.mkdir()
    completed_dir.mkdir()
    old_date = (date.today() - timedelta(days=60)).isoformat()
    _write(
        index_path,
        f"""entries:
  - id: intake-101
    title: Direct route missing metadata
    verdict: worth_investigating
    ingested_date: {old_date}
  - id: intake-102
    title: Slash route missing metadata
    verdict: worth_investigating
    ingested_date: {old_date}
  - id: intake-103
    title: Stage one
    verdict: new_opportunity
    ingested_date: {old_date}
    verification: stage1-unverified
    integration_disposition: awaiting_dive
  - id: intake-104
    title: Verified but unactioned
    verdict: worth_investigating
    ingested_date: {old_date}
    verification: dive-verified
  - id: intake-105
    title: Explicit monitor
    verdict: worth_investigating
    ingested_date: {old_date}
    integration_disposition: monitor
""",
    )
    _write(active_dir / "owner.md", "Uses intake-101/102 for the owner design.\n")

    issues = module.check_unactioned_intake(
        index_path,
        max_age_days=30,
        active_dir=active_dir,
        completed_dir=completed_dir,
    )

    categories = {issue[1]: issue[2].split("]", 1)[0] + "]" for issue in issues}
    assert categories == {
        "intake-101": "[missing-routing-metadata]",
        "intake-102": "[missing-routing-metadata]",
        "intake-103": "[stage1-awaiting-dive]",
        "intake-104": "[verified-unactioned]",
    }
