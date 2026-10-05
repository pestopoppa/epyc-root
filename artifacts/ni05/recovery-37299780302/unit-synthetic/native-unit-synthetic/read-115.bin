"""Unit tests for src/batch_edit.py (BEP-1 schema/analysis + BEP-4 pure applier)."""

from __future__ import annotations

import pytest

from src.batch_edit import (
    EditOperation,
    Hunk,
    FilePatch,
    PatchSet,
    sha256_text,
    validate_patchset,
    check_stale_base,
    detect_conflicts,
    dependency_stages,
    under_evidenced,
    apply_file_patch_to_text,
)


# ─── validation ──────────────────────────────────────────────────────────────────

def test_valid_modify_patchset() -> None:
    ps = PatchSet(
        base_repo_sha="repo1",
        files=[FilePatch(
            path="a.py", operation=EditOperation.MODIFY, base_content_sha256="sha-a",
            hunks=[Hunk(start_line=2, end_line=3, replacement="x\n")],
        )],
    )
    validate_patchset(ps)  # no raise


def test_modify_requires_base_sha_and_hunks() -> None:
    with pytest.raises(ValueError, match="base_content_sha256"):
        FilePatch(path="a.py", operation="modify", hunks=[Hunk(start_line=1, end_line=1, replacement="x")]).validate()
    with pytest.raises(ValueError, match=">=1 hunk"):
        FilePatch(path="a.py", operation="modify", base_content_sha256="s").validate()


def test_create_requires_new_content_only() -> None:
    FilePatch(path="n.py", operation="create", new_content="hi\n").validate()
    with pytest.raises(ValueError, match="new_content"):
        FilePatch(path="n.py", operation="create").validate()
    with pytest.raises(ValueError, match="base sha"):
        FilePatch(path="n.py", operation="create", new_content="x", base_content_sha256="s").validate()


def test_delete_and_rename_validation() -> None:
    FilePatch(path="d.py", operation="delete", base_content_sha256="s").validate()
    with pytest.raises(ValueError):
        FilePatch(path="d.py", operation="delete").validate()
    FilePatch(path="old.py", operation="rename", rename_to="new.py", base_content_sha256="s").validate()
    with pytest.raises(ValueError, match="rename_to"):
        FilePatch(path="old.py", operation="rename", base_content_sha256="s").validate()


def test_invalid_operation_and_empty_set() -> None:
    with pytest.raises(ValueError):
        FilePatch(path="a", operation="frobnicate").validate()
    with pytest.raises(ValueError, match="no files"):
        validate_patchset(PatchSet(files=[]))


def test_duplicate_path_rejected() -> None:
    ps = PatchSet(files=[
        FilePatch(path="a.py", operation="create", new_content="1"),
        FilePatch(path="a.py", operation="create", new_content="2"),
    ])
    with pytest.raises(ValueError, match="duplicate path"):
        validate_patchset(ps)


def test_hunk_styles_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="cannot mix"):
        Hunk(start_line=1, end_line=1, replacement="x", unified_diff="@@ -1 +1 @@").validate()
    with pytest.raises(ValueError, match="empty"):
        Hunk(unified_diff="   ").validate()


# ─── stale-base protection (audit #2) ────────────────────────────────────────────

def test_check_stale_base() -> None:
    ps = PatchSet(files=[
        FilePatch(path="a.py", operation="modify", base_content_sha256="sha-old",
                  hunks=[Hunk(start_line=1, end_line=1, replacement="x")]),
        FilePatch(path="b.py", operation="modify", base_content_sha256="sha-b",
                  hunks=[Hunk(start_line=1, end_line=1, replacement="y")]),
        FilePatch(path="new.py", operation="create", new_content="z"),  # create: never stale
    ])
    stale = check_stale_base(ps, {"a.py": "sha-NEW", "b.py": "sha-b"})
    assert stale == ["a.py"]  # b matches; new.py is create; a.py changed
    # missing-from-map modify target is stale
    assert "b.py" in check_stale_base(ps, {"a.py": "sha-old"})


# ─── conflict detection (audit #3) ───────────────────────────────────────────────

def test_detect_overlapping_hunks() -> None:
    fp = FilePatch(path="a.py", operation="modify", base_content_sha256="s", hunks=[
        Hunk(start_line=1, end_line=5, replacement="x"),
        Hunk(start_line=4, end_line=8, replacement="y"),
    ])
    conflicts = detect_conflicts(PatchSet(files=[fp]))
    assert any("overlapping hunks" in c for c in conflicts)


def test_detect_duplicate_target() -> None:
    ps = PatchSet(files=[
        FilePatch(path="a.py", operation="create", new_content="1"),
        FilePatch(path="a.py", operation="create", new_content="2"),
    ])
    assert any("same file" in c for c in detect_conflicts(ps))


def test_no_conflict_on_disjoint_hunks() -> None:
    fp = FilePatch(path="a.py", operation="modify", base_content_sha256="s", hunks=[
        Hunk(start_line=1, end_line=3, replacement="x"),
        Hunk(start_line=10, end_line=12, replacement="y"),
    ])
    assert detect_conflicts(PatchSet(files=[fp])) == []


# ─── dependency stages (audit #3) ────────────────────────────────────────────────

def test_dependency_stages_layering() -> None:
    ps = PatchSet(files=[
        FilePatch(path="schema.py", operation="create", new_content="1"),
        FilePatch(path="model.py", operation="create", new_content="2", depends_on=["schema.py"]),
        FilePatch(path="api.py", operation="create", new_content="3", depends_on=["model.py"]),
        FilePatch(path="docs.md", operation="create", new_content="4"),  # independent
    ])
    stages = dependency_stages(ps)
    assert stages[0] == ["docs.md", "schema.py"]  # both have no deps (sorted)
    assert stages[1] == ["model.py"]
    assert stages[2] == ["api.py"]


def test_dependency_cycle_raises() -> None:
    ps = PatchSet(files=[
        FilePatch(path="a.py", operation="create", new_content="1", depends_on=["b.py"]),
        FilePatch(path="b.py", operation="create", new_content="2", depends_on=["a.py"]),
    ])
    with pytest.raises(ValueError, match="cycle"):
        dependency_stages(ps)


def test_dependency_ignores_unknown_paths() -> None:
    ps = PatchSet(files=[FilePatch(path="a.py", operation="create", new_content="1",
                                   depends_on=["not-in-set.py"])])
    assert dependency_stages(ps) == [["a.py"]]


# ─── under-evidenced (audit #6) ──────────────────────────────────────────────────

def test_under_evidenced_flags_blind_edits() -> None:
    ps = PatchSet(
        files=[FilePatch(path="a.py", operation="create", new_content="1"),
               FilePatch(path="b.py", operation="create", new_content="2")],
        omitted_context_paths=["b.py", "c.py"],
    )
    assert under_evidenced(ps) == ["b.py"]  # b was only codemap_only/excluded in the bundle


# ─── BEP-4 pure deterministic applier ────────────────────────────────────────────

def test_apply_create() -> None:
    fp = FilePatch(path="n.py", operation="create", new_content="line1\nline2\n")
    assert apply_file_patch_to_text("", fp) == "line1\nline2\n"


def test_apply_modify_replace_range() -> None:
    original = "a\nb\nc\nd\n"
    fp = FilePatch(path="f.py", operation="modify", base_content_sha256=sha256_text(original),
                   hunks=[Hunk(start_line=2, end_line=3, replacement="B\nC\n")])
    assert apply_file_patch_to_text(original, fp) == "a\nB\nC\nd\n"


def test_apply_modify_insertion() -> None:
    original = "a\nb\n"
    # insert before line 2 (end_line = start_line - 1)
    fp = FilePatch(path="f.py", operation="modify", base_content_sha256=sha256_text(original),
                   hunks=[Hunk(start_line=2, end_line=1, replacement="INS\n")])
    assert apply_file_patch_to_text(original, fp) == "a\nINS\nb\n"


def test_apply_multi_hunk_bottom_up() -> None:
    original = "1\n2\n3\n4\n5\n"
    fp = FilePatch(path="f.py", operation="modify", base_content_sha256=sha256_text(original),
                   hunks=[
                       Hunk(start_line=1, end_line=1, replacement="ONE\n"),
                       Hunk(start_line=5, end_line=5, replacement="FIVE\n"),
                   ])
    assert apply_file_patch_to_text(original, fp) == "ONE\n2\n3\n4\nFIVE\n"


def test_apply_rejects_stale_base() -> None:
    fp = FilePatch(path="f.py", operation="modify", base_content_sha256="wrong-sha",
                   hunks=[Hunk(start_line=1, end_line=1, replacement="x\n")])
    with pytest.raises(ValueError, match="stale base"):
        apply_file_patch_to_text("a\n", fp)


def test_apply_rejects_unified_diff_hunk() -> None:
    original = "a\n"
    fp = FilePatch(path="f.py", operation="modify", base_content_sha256=sha256_text(original),
                   hunks=[Hunk(unified_diff="@@ -1 +1 @@\n-a\n+b\n")])
    with pytest.raises(ValueError, match="runner"):
        apply_file_patch_to_text(original, fp)
