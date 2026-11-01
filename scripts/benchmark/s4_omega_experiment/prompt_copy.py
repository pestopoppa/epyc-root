"""Prompt override preparation compatible with metadata-denying seccomp.

This adapter is not installed by itself. The isolated driver must explicitly
bind it to the pinned native runner and include this file in its source manifest.
It copies file contents, never metadata; symlinks and special files are refused.
"""
from pathlib import Path
import shutil
import tempfile


def _copy_tree(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("prompt source must be a real directory")
    target.mkdir(mode=0o700)
    for entry in source.iterdir():
        destination = target / entry.name
        if entry.is_symlink():
            raise ValueError("symlinks in prompt tree are not supported")
        if entry.is_dir():
            _copy_tree(entry, destination)
        elif entry.is_file():
            shutil.copyfile(entry, destination)
        else:
            raise ValueError("special files in prompt tree are not supported")


def prepare_prompt_roots(*, run_id, override_base, prompt_dir, arm_specs):
    """Preserve native per-arm byte layout without copying file metadata."""
    prompt_dir = Path(prompt_dir)
    arms = arm_specs(prompt_dir)
    override_base = Path(override_base)
    override_base.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix=f"s4-omega-{run_id}-", dir=override_base))
    roots = {}
    try:
        for arm_id, _digest, source in arms:
            if arm_id not in ("baseline", "s4_omega") or arm_id in roots:
                raise ValueError("unexpected or duplicate arm")
            root = run_root / arm_id
            _copy_tree(prompt_dir, root)
            for variant in root.glob("root_lm_system.*.md"):
                variant.unlink()
            shutil.copyfile(source, root / "root_lm_system.md")
            if arm_id == "s4_omega":
                shutil.copyfile(source, root / "root_lm_system.s4_omega.md")
            roots[arm_id] = root
        if set(roots) != {"baseline", "s4_omega"}:
            raise ValueError("both native arms required")
    except Exception:
        shutil.rmtree(run_root, ignore_errors=True)
        raise
    return roots
