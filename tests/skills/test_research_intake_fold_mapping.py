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


# ---- 2026-11-21: stale-destination relocation and archive-successor records ----

def write_successors(root: Path, entries: list[dict]) -> None:
    (root / "docs" / "design" / "backlog-refactor-2026-11" / "archive-successors.json").write_text(
        json.dumps({"schema": "brf-archive-successors.v1", "successors": entries}))


def succ(frm: str, to: str) -> dict:
    return {"from": frm, "to": to, "commit": "abc1234"}


def test_active_destination_archived_resolves_by_basename(tmp_path: Path) -> None:
    """Cause (a): fold recorded handoffs/active/X.md, X.md later moved to completed/."""
    root = make_root(tmp_path, [fold("handoffs/active/owner.md", "old.md", "owner.md#track:t")])
    (root / "handoffs" / "completed" / "owner.md").write_text("# o\n\n## Track: t\n")
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    owner, track = refs.resolve("old.md")
    assert owner == (root / "handoffs" / "completed" / "owner.md").resolve()
    assert track == "t"


def test_relocated_destination_still_requires_track(tmp_path: Path) -> None:
    root = make_root(tmp_path, [fold("handoffs/active/owner.md", "old.md", "owner.md#track:t")])
    (root / "handoffs" / "completed" / "owner.md").write_text("# o\n\n## Track: other\n")
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    with pytest.raises(ValueError, match="missing '## Track: t'"):
        refs.resolve("old.md")


def test_relocated_destination_ambiguous_basename_refused(tmp_path: Path) -> None:
    root = make_root(tmp_path, [fold("handoffs/active/owner.md", "old.md", "owner.md")])
    (root / "handoffs" / "completed" / "owner.md").write_text("# a\n")
    (root / "handoffs" / "archived").mkdir()
    (root / "handoffs" / "archived" / "owner.md").write_text("# b\n")
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    with pytest.raises(ValueError, match="ambiguous"):
        refs.resolve("old.md")


def test_unknown_handoff_is_still_refused(tmp_path: Path) -> None:
    root = make_root(tmp_path, [fold("handoffs/active/owner.md", "old.md", "owner.md")])
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    with pytest.raises(ValueError, match="dangling committed fold target"):
        refs.resolve("old.md")
    with pytest.raises(ValueError, match="not found"):
        refs.resolve("never-existed.md")


def test_renamed_archive_resolves_via_successor_record(tmp_path: Path) -> None:
    """Cause (b1): destination archived under a renamed file."""
    root = make_root(tmp_path, [fold("handoffs/active/arch.md", "old.md", "arch.md#track:t")])
    (root / "handoffs" / "completed" / "arch-completed-1.md").write_text("# a\n\n## Track: t\n")
    write_successors(root, [succ("arch.md", "handoffs/completed/arch-completed-1.md")])
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error is None
    owner, track = refs.resolve("old.md")
    assert owner.name == "arch-completed-1.md" and track == "t"
    assert refs.resolve("arch.md#track:t")[0].name == "arch-completed-1.md"


def test_split_track_resolves_via_successor_record(tmp_path: Path) -> None:
    """Cause (b2): a track moved out of its fold destination into its own file."""
    root = make_root(tmp_path, [fold("handoffs/active/parent.md", "old.md", "parent.md#track:moved")])
    (root / "handoffs" / "active" / "parent.md").write_text("# p\n\n## Track: kept\n")
    (root / "handoffs" / "completed" / "split.md").write_text("# s\n")
    write_successors(root, [succ("parent.md#moved", "handoffs/completed/split.md")])
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    owner, track = refs.resolve("old.md")
    assert owner.name == "split.md" and track is None
    with pytest.raises(ValueError, match="missing '## Track: nope'"):
        refs.resolve("parent.md#track:nope")


def test_successor_with_missing_target_is_refused(tmp_path: Path) -> None:
    root = make_root(tmp_path, [])
    write_successors(root, [succ("a.md", "handoffs/completed/gone.md")])
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error and "successor target missing" in refs.mapping_error


def test_successor_with_missing_track_is_refused(tmp_path: Path) -> None:
    root = make_root(tmp_path, [])
    (root / "handoffs" / "completed" / "t.md").write_text("# t\n\n## Track: x\n")
    write_successors(root, [succ("a.md", "handoffs/completed/t.md#y")])
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error and "successor track missing" in refs.mapping_error


def test_successor_cycle_is_refused(tmp_path: Path) -> None:
    root = make_root(tmp_path, [])
    (root / "handoffs" / "completed" / "a.md").write_text("# a\n")
    (root / "handoffs" / "completed" / "b.md").write_text("# b\n")
    write_successors(root, [succ("a.md", "handoffs/completed/b.md"),
                            succ("b.md", "handoffs/completed/a.md")])
    refs = _HandoffReferences(root, [root / "handoffs" / "active"])
    assert refs.mapping_error and "cyclic" in refs.mapping_error
