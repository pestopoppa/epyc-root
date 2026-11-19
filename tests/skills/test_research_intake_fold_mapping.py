"""Fold-mapping resolution across handoff status directories (2026-11-06).

A committed fold is authored while its destination is active. The destination
can be archived later, with every track intact — and in the 2026-11-05 mi210
archive it was. The resolver must keep citations through that fold resolvable
while still refusing a fold whose destination is not a handoff, and while still
requiring the named track to exist.

The regression that motivated this file: one fold destination per route list
pointed at ``handoffs/completed/mi210-serving-program.md`` and the loader
accepted only ``handoffs/active/``. The mapping_error then failed **every**
cross-reference through it, producing 5,877 validator errors from two entries.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / ".claude" / "skills" / "research-intake" / "scripts")
)

from validate_intake import _HandoffReferences  # noqa: E402


def make_root(tmp_path: Path, folds: list[dict], registry: dict | None = None,
              excluded: list[str] | None = None) -> Path:
    root = tmp_path
    design = root / "docs" / "design" / "backlog-refactor-2026-11"
    design.mkdir(parents=True)
    data = {"schema": "brf-fold-list-1a.v1", "folds": folds}
    if excluded:
        data["excluded"] = {"model_evaluation_queue_BRF-T1-MEQ": excluded}
    (design / "fold-list-1a.json").write_text(json.dumps(data))
    (root / "handoffs" / "active").mkdir(parents=True)
    (root / "handoffs" / "completed").mkdir(parents=True)
    if registry is not None:
        (root / "handoffs" / "active" / ".folded.json").write_text(json.dumps({"files": registry, "ids": {}}))
    return root


def fold(destination: str, source: str, target: str, tracks: list[dict] | None = None) -> dict:
    return {
        "destination": destination,
        "redirects": {"files": {source: target}},
        "tracks": tracks or [],
    }


def test_active_destination_resolves(tmp_path: Path) -> None:
    root = make_root(tmp_path, [fold("handoffs/active/owner.md", "old.md", "owner.md#track:t")])
    (root / "handoffs" / "active" / "owner.md").write_text("# owner\n\n## Track: t\n")
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error is None
    owner, track = refs.resolve("old.md")
    assert owner == (root / "handoffs" / "active" / "owner.md").resolve()
    assert track == "t"


def test_archived_destination_still_resolves(tmp_path: Path) -> None:
    """The archived owner is terminal history, not a dangling fold."""
    root = make_root(
        tmp_path,
        [fold("handoffs/completed/owner.md", "old.md", "owner.md#track:t")],
    )
    (root / "handoffs" / "completed" / "owner.md").write_text("# owner\n\n## Track: t\n")
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error is None
    owner, track = refs.resolve("old.md")
    assert owner == (root / "handoffs" / "completed" / "owner.md").resolve()
    assert track == "t"


def test_non_handoff_destination_is_refused(tmp_path: Path) -> None:
    root = make_root(tmp_path, [fold("docs/owner.md", "old.md", "owner.md")])
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error is not None
    assert "invalid fold destination" in refs.mapping_error
    with pytest.raises(ValueError, match="invalid committed fold mapping"):
        refs.resolve("old.md")


def test_missing_track_in_archived_destination_is_refused(tmp_path: Path) -> None:
    root = make_root(
        tmp_path,
        [fold("handoffs/completed/owner.md", "old.md", "owner.md#track:t")],
    )
    (root / "handoffs" / "completed" / "owner.md").write_text("# owner\n\n## Track: other\n")
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    with pytest.raises(ValueError, match="missing '## Track: t'"):
        refs.resolve("old.md")


def test_meq_registry_target_that_was_archived_resolves(tmp_path: Path) -> None:
    root = make_root(
        tmp_path,
        [],
        registry={"old-meq.md": {"target": "archived-owner.md", "track": "t"}},
        excluded=["old-meq.md"],
    )
    (root / "handoffs" / "completed" / "archived-owner.md").write_text(
        "# owner\n\n## Track: t\n"
    )
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error is None
    owner, track = refs.resolve("old-meq.md")
    assert owner == (root / "handoffs" / "completed" / "archived-owner.md").resolve()
    assert track == "t"


def test_meq_registry_target_missing_is_refused(tmp_path: Path) -> None:
    root = make_root(
        tmp_path,
        [],
        registry={"old-meq.md": {"target": "nowhere.md", "track": None}},
        excluded=["old-meq.md"],
    )
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error is not None
    assert "dangling MEQ fold target" in refs.mapping_error


def test_same_basename_in_two_statuses_is_ambiguous(tmp_path: Path) -> None:
    root = make_root(
        tmp_path,
        [],
        registry={"old-meq.md": {"target": "owner.md", "track": None}},
        excluded=["old-meq.md"],
    )
    (root / "handoffs" / "active" / "owner.md").write_text("# live\n")
    (root / "handoffs" / "completed" / "owner.md").write_text("# archived\n")
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error is not None
    assert "ambiguous handoff" in refs.mapping_error
