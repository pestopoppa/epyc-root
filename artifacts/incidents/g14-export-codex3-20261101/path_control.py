"""Preflight-only control; never launches a model or owns a process."""
from pathlib import Path


def fresh_output(scratch: Path, name: str, protected: list[Path]) -> Path:
    # Require an existing, physical, symlink-free scratch path.
    if not scratch.is_absolute() or not scratch.is_dir():
        raise ValueError("scratch must be an existing absolute directory")
    if any(part.is_symlink() for part in (scratch, *scratch.parents)):
        raise ValueError("symlink in scratch path")
    root = scratch.resolve(strict=True)
    if not name or name in (".", "..") or Path(name).name != name:
        raise ValueError("output must be one new directory name")
    candidate = root / name
    for item in protected:
        resolved = item.resolve(strict=True)
        if candidate == resolved or root == resolved or resolved in root.parents:
            raise ValueError("scratch or output aliases protected path")
    # Never reuse an existing path, including files, hardlinks, and dangling links.
    candidate.mkdir(mode=0o700, exist_ok=False)
    if candidate.is_symlink() or candidate.resolve(strict=True).parent != root:
        raise RuntimeError("output containment changed")
    if any(candidate.samefile(item) for item in protected):
        raise RuntimeError("output inode aliases protected path")
    return candidate
