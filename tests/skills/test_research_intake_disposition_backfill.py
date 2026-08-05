"""Unit tests for the text-preserving disposition migration helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/research-intake/scripts/backfill_dispositions.py"
)
SPEC = importlib.util.spec_from_file_location("backfill_dispositions", SCRIPT_PATH)
backfill = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(backfill)


def test_extract_ids_expands_slash_shorthand() -> None:
    assert backfill._extract_ids("See intake-902/903/intake-907 and intake-12.") == {
        "intake-012",
        "intake-902",
        "intake-903",
        "intake-907",
    }


def test_append_fields_replaces_empty_route_without_reflowing_entry() -> None:
    block = """- id: intake-001
  title: Original formatting stays
  handoffs_updated: []
"""

    rewritten = backfill._append_fields(
        block,
        "integrated",
        "Direct citation in owner.",
        ["handoffs/active/owner.md"],
    )
    parsed = yaml.safe_load(rewritten)

    assert "title: Original formatting stays" in rewritten
    assert parsed[0]["handoffs_updated"] == ["handoffs/active/owner.md"]
    assert parsed[0]["integration_disposition"] == "integrated"
