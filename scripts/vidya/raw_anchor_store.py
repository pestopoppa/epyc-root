"""Content-addressed custody helpers for prospective research-intake anchors.

No default storage location is assumed. Without an explicitly configured private
artifact root, callers can still describe a machine match but cannot claim that
its original source was retained or re-verified.
"""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT_ENV = "EPYC_VIDYA_RAW_ANCHOR_ROOT"
SCHEMA_VERSION = 1
MAX_ARTIFACT_BYTES = 20 * 1024 * 1024
_REQUIRED_KEYS = frozenset({
    "schema_version", "snapshot_id", "relative_path", "raw_sha256", "byte_length",
    "entry_url", "requested_url", "effective_url", "retrieved_at_utc", "media_type",
    "extractor_id", "extractor_sha256",
})
_WRITER_METADATA_KEYS = _REQUIRED_KEYS - {
    "schema_version", "snapshot_id", "relative_path", "raw_sha256", "byte_length",
}


class ArtifactUnavailable(ValueError):
    """The source artifact cannot safely support a verification claim."""


def _open_directory(path: Path, *, create: bool) -> int:
    """Open an absolute directory component-by-component without following links."""
    if not path.is_absolute():
        raise ArtifactUnavailable("artifact root must be absolute")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ArtifactUnavailable("filesystem does not support no-follow directory opens")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open("/", flags)
    try:
        for part in path.parts[1:]:
            if part in ("", ".", ".."):
                raise ArtifactUnavailable("artifact root has unsafe component")
            try:
                child = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise ArtifactUnavailable("artifact root is missing")
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
                child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode):
            raise ArtifactUnavailable("artifact root is not a directory")
        if info.st_uid != os.geteuid():
            raise ArtifactUnavailable("artifact root is not owned by the current user")
        if (info.st_mode & 0o700) != 0o700 or info.st_mode & 0o077:
            raise ArtifactUnavailable("artifact root permissions must exclude group/other")
        return fd
    except Exception:
        os.close(fd)
        raise


def _open_child_dir(parent_fd: int, name: str, *, create: bool) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise ArtifactUnavailable("artifact object is missing")
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
            os.fsync(parent_fd)
        except FileExistsError:
            pass
        fd = os.open(name, flags, dir_fd=parent_fd)
    info = os.fstat(fd)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or (info.st_mode & 0o700) != 0o700
        or info.st_mode & 0o077
    ):
        os.close(fd)
        raise ArtifactUnavailable("artifact directory is unsafe")
    return fd


def _relative_path(digest: str) -> str:
    return f"sha256/{digest[:2]}/{digest}.raw"


def store_raw_bytes(raw: bytes, metadata: dict[str, Any], *, root: Path | None = None) -> dict[str, Any] | None:
    """Store one response buffer create-once and return strict source metadata.

    Existing objects are verified in full and reused only on exact digest match.
    """
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_ARTIFACT_BYTES:
        raise ArtifactUnavailable("raw response is empty, not bytes, or exceeds the size limit")
    if not isinstance(metadata, dict) or set(metadata) != _WRITER_METADATA_KEYS:
        raise ArtifactUnavailable("source metadata fields do not match the writer schema")
    configured = root if root is not None else os.environ.get(ROOT_ENV)
    if configured is None or str(configured).strip() == "":
        return None
    root_path = Path(configured)
    digest = hashlib.sha256(raw).hexdigest()
    relative = _relative_path(digest)
    envelope = {
        **metadata,
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": f"sha256:{digest}",
        "relative_path": relative,
        "raw_sha256": digest,
        "byte_length": len(raw),
    }
    validate_artifact_metadata(envelope)
    try:
        root_fd = _open_directory(root_path, create=True)
        try:
            sha_fd = _open_child_dir(root_fd, "sha256", create=True)
            try:
                shard_fd = _open_child_dir(sha_fd, digest[:2], create=True)
                try:
                    try:
                        fd = os.open(
                            f"{digest}.raw",
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                            0o600,
                            dir_fd=shard_fd,
                        )
                    except FileExistsError:
                        fd = os.open(
                            f"{digest}.raw", os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                            dir_fd=shard_fd,
                        )
                        try:
                            info = os.fstat(fd)
                            if (
                                not stat.S_ISREG(info.st_mode)
                                or info.st_uid != os.geteuid()
                                or (info.st_mode & 0o600) != 0o600
                                or info.st_mode & 0o077
                            ):
                                raise ArtifactUnavailable("existing artifact is not a private regular file")
                            existing = bytearray()
                            while len(existing) <= MAX_ARTIFACT_BYTES:
                                chunk = os.read(fd, min(1024 * 1024, MAX_ARTIFACT_BYTES + 1 - len(existing)))
                                if not chunk:
                                    break
                                existing.extend(chunk)
                            if bytes(existing) != raw:
                                raise ArtifactUnavailable("content-addressed object conflicts with response bytes")
                        finally:
                            os.close(fd)
                    else:
                        try:
                            view = memoryview(raw)
                            while view:
                                written = os.write(fd, view)
                                if written <= 0:
                                    raise ArtifactUnavailable("short write while retaining source bytes")
                                view = view[written:]
                            os.fsync(fd)
                        finally:
                            os.close(fd)
                        os.fsync(shard_fd)
                finally:
                    os.close(shard_fd)
            finally:
                os.close(sha_fd)
        finally:
            os.close(root_fd)
    except OSError as exc:
        raise ArtifactUnavailable("artifact storage filesystem could not be opened safely") from exc

    return envelope


def validate_artifact_metadata(artifact: Any) -> None:
    if not isinstance(artifact, dict) or set(artifact) != _REQUIRED_KEYS:
        raise ArtifactUnavailable("artifact metadata schema is missing or has unknown fields")
    if type(artifact.get("schema_version")) is not int or artifact.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactUnavailable("artifact metadata schema version is unsupported")
    digest = artifact.get("raw_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ArtifactUnavailable("raw digest is malformed")
    if artifact.get("snapshot_id") != f"sha256:{digest}":
        raise ArtifactUnavailable("snapshot id does not match raw digest")
    if artifact.get("relative_path") != _relative_path(digest):
        raise ArtifactUnavailable("artifact relative path is not canonical")
    if type(artifact.get("byte_length")) is not int or not 0 < artifact["byte_length"] <= MAX_ARTIFACT_BYTES:
        raise ArtifactUnavailable("artifact byte length is invalid")
    for key in ("entry_url", "requested_url", "effective_url", "retrieved_at_utc", "media_type", "extractor_id", "extractor_sha256"):
        if not isinstance(artifact.get(key), str) or not artifact[key].strip():
            raise ArtifactUnavailable(f"artifact {key} is missing")
    for key in ("entry_url", "requested_url", "effective_url"):
        try:
            parsed = urlsplit(artifact[key])
        except ValueError as exc:
            raise ArtifactUnavailable(f"artifact {key} is malformed") from exc
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ArtifactUnavailable(f"artifact {key} is not a safe HTTPS locator")
    if artifact["media_type"] not in {"text/html", "application/xhtml+xml", "text/plain"}:
        raise ArtifactUnavailable("artifact media type is unsupported")
    try:
        from datetime import datetime, timezone
        retrieved = datetime.fromisoformat(artifact["retrieved_at_utc"].replace("Z", "+00:00"))
        if retrieved.tzinfo is None or retrieved.utcoffset() != timezone.utc.utcoffset(retrieved):
            raise ValueError("retrieval time is not UTC")
    except ValueError as exc:
        raise ArtifactUnavailable("artifact retrieval time is malformed") from exc
    if len(artifact["extractor_sha256"]) != 64 or any(
        c not in "0123456789abcdef" for c in artifact["extractor_sha256"]
    ):
        raise ArtifactUnavailable("extractor digest is malformed")


def read_raw_bytes(artifact: Any, *, root: Path | None = None) -> bytes:
    """Open a bound artifact through no-follow directory handles and verify its bytes."""
    validate_artifact_metadata(artifact)
    configured = root if root is not None else os.environ.get(ROOT_ENV)
    if configured is None or str(configured).strip() == "":
        raise ArtifactUnavailable("no artifact root is configured")
    try:
        root_fd = _open_directory(Path(configured), create=False)
    except OSError as exc:
        raise ArtifactUnavailable("artifact root cannot be opened without following links") from exc
    try:
        sha_fd = _open_child_dir(root_fd, "sha256", create=False)
        try:
            shard_fd = _open_child_dir(sha_fd, artifact["raw_sha256"][:2], create=False)
            try:
                fd = os.open(
                    f"{artifact['raw_sha256']}.raw",
                    os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=shard_fd,
                )
                try:
                    before = os.fstat(fd)
                    if (
                        not stat.S_ISREG(before.st_mode)
                        or before.st_uid != os.geteuid()
                        or (before.st_mode & 0o600) != 0o600
                        or before.st_mode & 0o077
                    ):
                        raise ArtifactUnavailable("artifact is not a private regular file")
                    if before.st_size != artifact["byte_length"] or before.st_size > MAX_ARTIFACT_BYTES:
                        raise ArtifactUnavailable("artifact size disagrees with metadata")
                    chunks = bytearray()
                    while len(chunks) <= MAX_ARTIFACT_BYTES:
                        data = os.read(fd, min(1024 * 1024, MAX_ARTIFACT_BYTES + 1 - len(chunks)))
                        if not data:
                            break
                        chunks.extend(data)
                    after = os.fstat(fd)
                    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
                    ):
                        raise ArtifactUnavailable("artifact changed while being read")
                finally:
                    os.close(fd)
            finally:
                os.close(shard_fd)
        finally:
            os.close(sha_fd)
    finally:
        os.close(root_fd)
    raw = bytes(chunks)
    if len(raw) != artifact["byte_length"] or hashlib.sha256(raw).hexdigest() != artifact["raw_sha256"]:
        raise ArtifactUnavailable("artifact bytes do not match the retained digest")
    return raw
