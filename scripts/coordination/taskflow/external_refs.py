"""Stage and verify content-pinned controller inputs inside the worker lane."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from . import schema


def read_sources(task: dict, lane_root: Path) -> list[tuple[dict[str, str], bytes]]:
    """Read and authenticate every source before creating a lane."""
    files = []
    for entry in schema.external_readonly_inputs(task):
        source = Path(entry["path"]).resolve(strict=True)
        if source.is_relative_to(lane_root.resolve()) or not source.is_file():
            raise ValueError(f"external input must be a regular file outside worker lanes: {source}")
        data = source.read_bytes()
        if sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"external input digest changed: {source}")
        files.append((entry, data))
    return files


def _target(lane: Path, name: str) -> Path:
    path = lane
    for part in Path(name).parts:
        path /= part
        if path.is_symlink():
            raise ValueError(f"external input traverses a symlink: {path.relative_to(lane)}")
    return path


def stage(lane: Path, files: list[tuple[dict[str, str], bytes]]) -> None:
    for entry, data in files:
        target = _target(lane, entry["lane_path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(data)
        target.chmod(0o444)


def verify(lane: Path, task: dict) -> str | None:
    """Return a refusal reason for a missing, replaced or modified reference."""
    try:
        for entry in schema.external_readonly_inputs(task):
            target = _target(lane, entry["lane_path"])
            if not target.is_file():
                return f"external input missing: {entry['lane_path']}"
            if target.stat().st_mode & 0o222 or sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
                return f"external input changed: {entry['lane_path']}"
    except (OSError, ValueError) as exc:
        return str(exc)
    return None
