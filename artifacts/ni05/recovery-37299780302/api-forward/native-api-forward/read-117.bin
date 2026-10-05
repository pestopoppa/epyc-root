"""Unit tests for src/batch_edit_runner.py (BEP-4 sandbox-stage → apply → verify)."""

from __future__ import annotations

from pathlib import Path

from src import batch_edit_runner as R
from src.batch_edit import PatchSet, FilePatch, Hunk, sha256_text
from src.batch_edit_runner import (
    ApplyResult,
    FailureType,
    compute_current_shas,
    stage_sandbox,
    apply_patchset_to_dir,
    apply_patchset_sandboxed,
    promote_sandbox,
    cleanup_sandbox,
)


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root


def _modify(path: str, original: str, hunks: list[Hunk]) -> FilePatch:
    return FilePatch(path=path, operation="modify", base_content_sha256=sha256_text(original), hunks=hunks)


# ─── current shas + staging ──────────────────────────────────────────────────────

def test_compute_current_shas(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "x\n"})
    ps = PatchSet(files=[_modify("a.py", "x\n", [Hunk(start_line=1, end_line=1, replacement="y\n")]),
                         FilePatch(path="new.py", operation="create", new_content="z")])
    shas = compute_current_shas(ps, root)
    assert shas == {"a.py": sha256_text("x\n")}  # create excluded; only existing modify target


def test_stage_sandbox_copies_touched(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "x\n", "untouched.py": "keep\n"})
    ps = PatchSet(files=[_modify("a.py", "x\n", [Hunk(start_line=1, end_line=1, replacement="y\n")])])
    sb = stage_sandbox(ps, root)
    assert (sb / "a.py").read_text() == "x\n"
    assert not (sb / "untouched.py").exists()  # only touched files staged
    cleanup_sandbox_dir(sb)


def test_stage_sandbox_full_tree_copies_untouched(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "x\n", "untouched.py": "keep\n"})
    ps = PatchSet(files=[_modify("a.py", "x\n", [Hunk(start_line=1, end_line=1, replacement="y\n")])])
    sb = stage_sandbox(ps, root, full_tree=True)
    assert (sb / "a.py").read_text() == "x\n"
    assert (sb / "untouched.py").read_text() == "keep\n"
    cleanup_sandbox_dir(sb)


def cleanup_sandbox_dir(p: Path) -> None:
    import shutil
    shutil.rmtree(p, ignore_errors=True)


# ─── apply core ──────────────────────────────────────────────────────────────────

def test_apply_modify_and_create_in_dir(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "1\n2\n3\n"})
    ps = PatchSet(files=[
        _modify("a.py", "1\n2\n3\n", [Hunk(start_line=2, end_line=2, replacement="TWO\n")]),
        FilePatch(path="b.py", operation="create", new_content="new\n"),
    ])
    shas = compute_current_shas(ps, root)
    sb = stage_sandbox(ps, root)
    res = apply_patchset_to_dir(ps, sb, shas)
    assert res.ok
    assert (sb / "a.py").read_text() == "1\nTWO\n3\n"
    assert (sb / "b.py").read_text() == "new\n"
    # live tree untouched
    assert (root / "a.py").read_text() == "1\n2\n3\n"
    assert not (root / "b.py").exists()
    cleanup_sandbox_dir(sb)


def test_stale_base_blocks_entire_set(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "CHANGED\n"})  # file changed since planning
    ps = PatchSet(files=[
        _modify("a.py", "ORIGINAL\n", [Hunk(start_line=1, end_line=1, replacement="x\n")]),
        FilePatch(path="b.py", operation="create", new_content="new\n"),
    ])
    shas = compute_current_shas(ps, root)
    sb = stage_sandbox(ps, root)
    res = apply_patchset_to_dir(ps, sb, shas)
    assert not res.ok
    assert any(f["failure_type"] == FailureType.STALE_BASE for f in res.failed)
    assert res.applied == []  # transactional: nothing applied
    assert not (sb / "b.py").exists()  # the clean create was NOT applied either
    cleanup_sandbox_dir(sb)


def test_conflict_blocks_set(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "1\n2\n3\n4\n5\n"})
    ps = PatchSet(files=[FilePatch(path="a.py", operation="modify",
                                   base_content_sha256=sha256_text("1\n2\n3\n4\n5\n"),
                                   hunks=[Hunk(start_line=1, end_line=3, replacement="x"),
                                          Hunk(start_line=2, end_line=4, replacement="y")])])
    shas = compute_current_shas(ps, root)
    sb = stage_sandbox(ps, root)
    res = apply_patchset_to_dir(ps, sb, shas)
    assert not res.ok
    assert any(f["failure_type"] == FailureType.CONFLICT for f in res.failed)
    cleanup_sandbox_dir(sb)


def test_under_evidenced_patch_blocks_set(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "old\n"})
    ps = PatchSet(
        files=[
            _modify("a.py", "old\n", [Hunk(start_line=1, end_line=1, replacement="new\n")]),
            FilePatch(path="b.py", operation="create", new_content="created\n"),
        ],
        bundle_id="dcp-bundle-1",
        omitted_context_paths=["a.py"],
    )
    sb = stage_sandbox(ps, root)
    res = apply_patchset_to_dir(ps, sb, compute_current_shas(ps, root))
    assert not res.ok
    assert any(f["failure_type"] == FailureType.UNDER_EVIDENCED for f in res.failed)
    assert (sb / "a.py").read_text() == "old\n"
    assert not (sb / "b.py").exists()
    cleanup_sandbox_dir(sb)


def test_dependency_order_respected(tmp_path: Path) -> None:
    # b depends on a; both creates → a applies in stage 0, b in stage 1 (order shouldn't error)
    root = _repo(tmp_path, {})
    ps = PatchSet(files=[
        FilePatch(path="a.py", operation="create", new_content="a\n"),
        FilePatch(path="b.py", operation="create", new_content="b\n", depends_on=["a.py"]),
    ])
    res = apply_patchset_to_dir(ps, stage_sandbox(ps, root), compute_current_shas(ps, root))
    assert res.ok and set(res.applied) == {"a.py", "b.py"}


def test_independent_stage_applies_files_concurrently(monkeypatch, tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "old-a\n", "b.py": "old-b\n"})
    ps = PatchSet(files=[
        _modify("a.py", "old-a\n", [Hunk(start_line=1, end_line=1, replacement="new-a\n")]),
        _modify("b.py", "old-b\n", [Hunk(start_line=1, end_line=1, replacement="new-b\n")]),
    ])
    sb = stage_sandbox(ps, root)

    import threading

    barrier = threading.Barrier(2)
    real_apply = R.apply_file_patch_to_text

    def blocking_apply(original, fp):
        barrier.wait(timeout=1)
        return real_apply(original, fp)

    monkeypatch.setattr(R, "apply_file_patch_to_text", blocking_apply)
    res = apply_patchset_to_dir(ps, sb, compute_current_shas(ps, root))
    assert res.ok, res.failed
    assert (sb / "a.py").read_text() == "new-a\n"
    assert (sb / "b.py").read_text() == "new-b\n"
    cleanup_sandbox_dir(sb)


def test_dependency_stage_waits_for_prior_stage(monkeypatch, tmp_path: Path) -> None:
    root = _repo(tmp_path, {})
    ps = PatchSet(files=[
        FilePatch(path="a.py", operation="create", new_content="a\n"),
        FilePatch(path="b.py", operation="create", new_content="b\n", depends_on=["a.py"]),
    ])
    sb = stage_sandbox(ps, root)
    real_apply_one = R._apply_one_file_patch

    def checked_apply_one(target_root, fp):
        if fp.path == "b.py":
            assert (target_root / "a.py").exists()
        return real_apply_one(target_root, fp)

    monkeypatch.setattr(R, "_apply_one_file_patch", checked_apply_one)
    res = apply_patchset_to_dir(ps, sb, compute_current_shas(ps, root))
    assert res.ok, res.failed
    assert (sb / "a.py").read_text() == "a\n"
    assert (sb / "b.py").read_text() == "b\n"
    cleanup_sandbox_dir(sb)


def test_parallel_stage_failure_rolls_back_sandbox_successes(monkeypatch, tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "old-a\n", "b.py": "old-b\n"})
    ps = PatchSet(files=[
        _modify("a.py", "old-a\n", [Hunk(start_line=1, end_line=1, replacement="new-a\n")]),
        _modify("b.py", "old-b\n", [Hunk(start_line=1, end_line=1, replacement="new-b\n")]),
    ])
    sb = stage_sandbox(ps, root)
    real_apply = R.apply_file_patch_to_text

    def flaky_apply(original, fp):
        if fp.path == "b.py":
            raise OSError("simulated patch failure")
        return real_apply(original, fp)

    monkeypatch.setattr(R, "apply_file_patch_to_text", flaky_apply)
    res = apply_patchset_to_dir(ps, sb, compute_current_shas(ps, root))
    assert not res.ok
    assert res.applied == []
    assert any(f["failure_type"] == FailureType.APPLY_ERROR for f in res.failed)
    assert (sb / "a.py").read_text() == "old-a\n"
    assert (sb / "b.py").read_text() == "old-b\n"
    cleanup_sandbox_dir(sb)


def test_parallel_create_delete_failure_rolls_back_sandbox(monkeypatch, tmp_path: Path) -> None:
    root = _repo(tmp_path, {"gone.py": "old-gone\n"})
    ps = PatchSet(files=[
        FilePatch(path="new.py", operation="create", new_content="created\n"),
        FilePatch(
            path="gone.py",
            operation="delete",
            base_content_sha256=sha256_text("old-gone\n"),
        ),
    ])
    sb = stage_sandbox(ps, root)
    real_unlink = Path.unlink

    def flaky_unlink(self, *args, **kwargs):
        if self == sb / "gone.py":
            raise OSError("simulated delete failure")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    res = apply_patchset_to_dir(ps, sb, compute_current_shas(ps, root))
    assert not res.ok
    assert res.applied == []
    assert any(f["failure_type"] == FailureType.APPLY_ERROR for f in res.failed)
    assert not (sb / "new.py").exists()
    assert (sb / "gone.py").read_text() == "old-gone\n"
    cleanup_sandbox_dir(sb)


def test_later_stage_failure_restores_rename_source_and_destination(monkeypatch, tmp_path: Path) -> None:
    root = _repo(tmp_path, {"old.py": "old-content\n", "b.py": "old-b\n"})
    ps = PatchSet(files=[
        FilePatch(
            path="old.py",
            operation="rename",
            rename_to="new.py",
            base_content_sha256=sha256_text("old-content\n"),
        ),
        FilePatch(
            path="b.py",
            operation="modify",
            base_content_sha256=sha256_text("old-b\n"),
            hunks=[Hunk(start_line=1, end_line=1, replacement="new-b\n")],
            depends_on=["old.py"],
        ),
    ])
    sb = stage_sandbox(ps, root)
    real_apply = R.apply_file_patch_to_text

    def flaky_apply(original, fp):
        if fp.path == "b.py":
            raise OSError("simulated later-stage failure")
        return real_apply(original, fp)

    monkeypatch.setattr(R, "apply_file_patch_to_text", flaky_apply)
    res = apply_patchset_to_dir(ps, sb, compute_current_shas(ps, root))
    assert not res.ok
    assert res.applied == []
    assert (sb / "old.py").read_text() == "old-content\n"
    assert not (sb / "new.py").exists()
    assert (sb / "b.py").read_text() == "old-b\n"
    cleanup_sandbox_dir(sb)


# ─── sandboxed end-to-end + verify + promote ─────────────────────────────────────

def test_sandboxed_with_passing_verify_then_promote(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "old\n"})
    ps = PatchSet(files=[_modify("a.py", "old\n", [Hunk(start_line=1, end_line=1, replacement="new\n")])])

    def verify_fn(sandbox: Path) -> bool:
        return (sandbox / "a.py").read_text() == "new\n"

    res = apply_patchset_sandboxed(ps, repo_root=root, verify_fn=verify_fn)
    assert res.ok and res.verify_passed is True
    assert (root / "a.py").read_text() == "old\n"  # NOT promoted yet
    assert promote_sandbox(res, root) is True
    assert (root / "a.py").read_text() == "new\n"  # promoted after accept
    cleanup_sandbox(res)


def test_sandboxed_failing_verify_does_not_promote(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "old\n"})
    ps = PatchSet(files=[_modify("a.py", "old\n", [Hunk(start_line=1, end_line=1, replacement="new\n")])])
    res = apply_patchset_sandboxed(ps, repo_root=root, verify_fn=lambda sb: False)
    assert res.verify_passed is False and not res.ok
    assert res.failed == [
        {"path": "*", "failure_type": FailureType.VERIFY_FAILED, "detail": "verify_fn returned False"}
    ]
    assert promote_sandbox(res, root) is False
    assert (root / "a.py").read_text() == "old\n"  # untouched
    cleanup_sandbox(res)


def test_full_tree_verifier_sees_cross_file_state(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "old\n", "untouched.py": "keep\n"})
    ps = PatchSet(files=[_modify("a.py", "old\n", [Hunk(start_line=1, end_line=1, replacement="new\n")])])

    def verify_fn(sandbox: Path) -> bool:
        return (
            (sandbox / "a.py").read_text() == "new\n"
            and (sandbox / "untouched.py").read_text() == "keep\n"
        )

    res = apply_patchset_sandboxed(ps, repo_root=root, verify_fn=verify_fn, full_tree=True)
    assert res.ok
    assert res.verify_passed is True
    cleanup_sandbox(res)


def test_sandboxed_no_verify_is_ok_but_promote_gated_on_ok(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "old\n"})
    ps = PatchSet(files=[_modify("a.py", "old\n", [Hunk(start_line=1, end_line=1, replacement="new\n")])])
    res = apply_patchset_sandboxed(ps, repo_root=root)  # no verify_fn
    assert res.verify_passed is None and res.ok  # not-requested → ok
    assert promote_sandbox(res, root) is False
    assert (root / "a.py").read_text() == "old\n"
    cleanup_sandbox(res)


def test_stale_in_sandboxed_path_never_touches_live(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.py": "CHANGED\n"})
    ps = PatchSet(files=[_modify("a.py", "ORIGINAL\n", [Hunk(start_line=1, end_line=1, replacement="x\n")])])
    res = apply_patchset_sandboxed(ps, repo_root=root, verify_fn=lambda sb: True)
    assert not res.ok
    assert promote_sandbox(res, root) is False
    assert (root / "a.py").read_text() == "CHANGED\n"
    cleanup_sandbox(res)


# ─── BEP-1b: delete / rename promotion to the live tree ──────────────────────────

def test_promote_delete_removes_from_live(tmp_path):
    root = _repo(tmp_path, {"keep.py": "x\n", "gone.py": "y\n"})
    ps = PatchSet(files=[FilePatch(path="gone.py", operation="delete",
                                   base_content_sha256=sha256_text("y\n"))])
    res = apply_patchset_sandboxed(
        ps,
        repo_root=root,
        current_shas=compute_current_shas(ps, root),
        verify_fn=lambda _sb: True,
    )
    assert res.ok, res.failed
    assert "gone.py" in res.deleted_paths
    assert promote_sandbox(res, root) is True
    assert not (root / "gone.py").exists()   # deletion promoted
    assert (root / "keep.py").exists()         # untouched


def test_promote_rename_moves_in_live(tmp_path):
    root = _repo(tmp_path, {"old.py": "content\n"})
    ps = PatchSet(files=[FilePatch(path="old.py", operation="rename", rename_to="new.py",
                                   base_content_sha256=sha256_text("content\n"))])
    res = apply_patchset_sandboxed(
        ps,
        repo_root=root,
        current_shas=compute_current_shas(ps, root),
        verify_fn=lambda _sb: True,
    )
    assert res.ok, res.failed
    assert ("old.py", "new.py") in res.renamed_paths
    assert promote_sandbox(res, root) is True
    assert (root / "new.py").read_text() == "content\n"  # rename-to promoted with content
    assert not (root / "old.py").exists()                # rename-from removed


def test_promote_missing_sandbox_source_refuses_without_mutation(tmp_path):
    root = _repo(tmp_path, {"a.py": "old\n"})
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    res = ApplyResult(
        applied=["a.py"],
        verify_passed=True,
        sandbox_path=str(sandbox),
        diff_paths=["a.py"],
    )
    assert promote_sandbox(res, root) is False
    assert (root / "a.py").read_text() == "old\n"


def test_promote_copy_failure_rolls_back_all_live_paths(monkeypatch, tmp_path):
    root = _repo(tmp_path, {"a.py": "old-a\n", "b.py": "old-b\n"})
    ps = PatchSet(files=[
        _modify("a.py", "old-a\n", [Hunk(start_line=1, end_line=1, replacement="new-a\n")]),
        _modify("b.py", "old-b\n", [Hunk(start_line=1, end_line=1, replacement="new-b\n")]),
    ])
    res = apply_patchset_sandboxed(
        ps,
        repo_root=root,
        current_shas=compute_current_shas(ps, root),
        verify_fn=lambda _sb: True,
    )
    assert res.promotable

    import shutil

    real_copy2 = shutil.copy2
    sandbox_root = Path(res.sandbox_path or "")
    copy_from_sandbox_count = 0

    def flaky_copy2(src, dst, *args, **kwargs):
        nonlocal copy_from_sandbox_count
        if sandbox_root in Path(src).parents:
            copy_from_sandbox_count += 1
            if copy_from_sandbox_count == 2:
                raise OSError("simulated second-copy failure")
        return real_copy2(src, dst, *args, **kwargs)

    monkeypatch.setattr(shutil, "copy2", flaky_copy2)
    assert promote_sandbox(res, root) is False
    assert (root / "a.py").read_text() == "old-a\n"
    assert (root / "b.py").read_text() == "old-b\n"
    cleanup_sandbox(res)


def test_promote_delete_failure_after_copy_rolls_back_all_live_paths(monkeypatch, tmp_path):
    root = _repo(tmp_path, {"a.py": "old-a\n", "gone.py": "old-gone\n"})
    ps = PatchSet(files=[
        _modify("a.py", "old-a\n", [Hunk(start_line=1, end_line=1, replacement="new-a\n")]),
        FilePatch(
            path="gone.py",
            operation="delete",
            base_content_sha256=sha256_text("old-gone\n"),
        ),
    ])
    res = apply_patchset_sandboxed(
        ps,
        repo_root=root,
        current_shas=compute_current_shas(ps, root),
        verify_fn=lambda _sb: True,
    )
    assert res.promotable

    real_unlink = Path.unlink

    def flaky_unlink(self, *args, **kwargs):
        if self == root / "gone.py":
            raise OSError("simulated delete failure")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    assert promote_sandbox(res, root) is False
    assert (root / "a.py").read_text() == "old-a\n"
    assert (root / "gone.py").read_text() == "old-gone\n"
    cleanup_sandbox(res)
