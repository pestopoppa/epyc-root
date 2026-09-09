"""Task-local expected-inventory author. Never opens the declared model root."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REVISION = "d425e572fb9686125831f476129e51cea34bc5b4"
REMOTE_REPOSITORY = "unsloth/GLM-5.3-Flash-GGUF"
QUANTIZATION = "UD-Q4_K_XL"
BASENAMES = tuple(f"GLM-5.3-Flash-UD-Q4_K_XL-{n:05d}-of-00006.gguf"
                  for n in range(1, 7))
TREE_CAP = 64 * 1024
METADATA_CAP = 4096
PACKET_CAP = 1024 * 1024
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


class AuthoringRefused(ValueError):
    pass


def canonical(value: Any) -> bytes:
    # Exactly the owning CaptureModelIdentity normalized JSON convention.
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized_absolute(value: str) -> str:
    if type(value) is not str or not value or "\0" in value:
        raise AuthoringRefused("path must be nonempty text")
    if not value.startswith("/") or value.startswith("//") \
            or os.path.normpath(value) != value or ".." in Path(value).parts:
        raise AuthoringRefused("path must be normalized and absolute")
    return value


def _regular_bytes(path: Path, cap: int) -> bytes:
    """Open each component without symlink traversal; never block on a FIFO."""
    normalized_absolute(str(path))
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    descriptor = None
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                                | os.O_CLOEXEC, dir_fd=directory)
            os.close(directory)
            directory = following
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                             | os.O_CLOEXEC, dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > cap:
            raise AuthoringRefused("source must be a bounded regular file")
        chunks = []
        retained = 0
        while True:
            block = os.read(descriptor, min(65536, cap + 1 - retained))
            if not block:
                break
            chunks.append(block)
            retained += len(block)
            if retained > cap:
                raise AuthoringRefused("source exceeded byte cap")
        after = os.fstat(descriptor)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, field) != getattr(after, field) for field in fields) \
                or retained != before.st_size:
            raise AuthoringRefused("source changed during bounded read")
        return b"".join(chunks)
    except OSError as exc:
        raise AuthoringRefused(f"cannot reopen bounded source: {path}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuthoringRefused("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise AuthoringRefused(f"nonfinite JSON constant: {value}")


def _json(raw: bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuthoringRefused("invalid source JSON") from exc


def _sha(value: Any) -> str:
    if type(value) is not str or SHA_RE.fullmatch(value) is None:
        raise AuthoringRefused("expected lowercase full LFS SHA-256")
    return value


def assemble(cache_root: str, model_root: str) -> dict[str, bytes]:
    """Return small expected-only artifacts; model_root is never stat'ed/opened."""
    cache = Path(normalized_absolute(cache_root))
    model_root = normalized_absolute(model_root)
    tree_path = cache / "trees" / f"{REVISION}.json"
    tree_bytes = _regular_bytes(tree_path, TREE_CAP)
    tree = _json(tree_bytes)
    if type(tree) is not dict or set(tree) != {"format_version", "files"} \
            or type(tree["format_version"]) is not int or tree["format_version"] != 1 \
            or type(tree["files"]) is not dict:
        raise AuthoringRefused("unsupported cache tree shape/version")
    expected = {f"{QUANTIZATION}/{name}" for name in BASENAMES}
    selected = {name for name in tree["files"] if name.startswith(f"{QUANTIZATION}/")}
    if selected != expected:
        raise AuthoringRefused("selected quantization is not exactly six expected shards")
    rows = []
    provenance_rows = []
    encoded_tree = base64.b64encode(tree_bytes) + b"\n"
    artifacts = {"source-tree.json.base64": encoded_tree}
    for index, name in enumerate(BASENAMES, 1):
        remote_name = f"{QUANTIZATION}/{name}"
        row = tree["files"][remote_name]
        if type(row) is not dict or set(row) != {
                "size", "blob_id", "lfs_sha256", "lfs_size", "xet_hash"}:
            raise AuthoringRefused("selected LFS metadata fields differ")
        if type(row["size"]) is not int or row["size"] <= 0 \
                or type(row["lfs_size"]) is not int or row["lfs_size"] != row["size"]:
            raise AuthoringRefused("declared LFS sizes differ or are invalid")
        lfs = _sha(row["lfs_sha256"])
        _sha(row["xet_hash"])
        if type(row["blob_id"]) is not str \
                or re.fullmatch(r"[0-9a-f]{40}", row["blob_id"]) is None:
            raise AuthoringRefused("invalid cached Git blob identity")
        metadata_path = cache / "download" / QUANTIZATION / f"{name}.metadata"
        metadata_bytes = _regular_bytes(metadata_path, METADATA_CAP)
        try:
            lines = metadata_bytes.decode("utf-8").splitlines()
        except UnicodeError as exc:
            raise AuthoringRefused("invalid download metadata encoding") from exc
        if len(lines) != 3 or lines[0] != REVISION or lines[1] != lfs:
            raise AuthoringRefused("download revision/etag/three-line shape mismatch")
        try:
            timestamp = Decimal(lines[2])
        except InvalidOperation as exc:
            raise AuthoringRefused("invalid cached download timestamp") from exc
        if not timestamp.is_finite() or timestamp <= 0 or lines[2].strip() != lines[2]:
            raise AuthoringRefused("invalid cached download timestamp")
        retained_path = f"download/{index:05d}.metadata"
        artifacts[retained_path] = metadata_bytes
        rows.append({"path": name, "sha256": lfs})
        provenance_rows.append({
            "remote_name": remote_name, "declared_size_bytes": row["size"],
            "lfs_size_bytes": row["lfs_size"], "expected_lfs_sha256": lfs,
            "git_blob_id": row["blob_id"], "xet_hash": row["xet_hash"],
            "download_metadata_path": str(metadata_path),
            "download_metadata_sha256": digest(metadata_bytes),
            "retained_download_metadata": retained_path, "etag": lines[1],
            "cached_download_timestamp": lines[2],
        })
    manifest = {"schema": "epyc.autokernel.model_identity.v1",
                "model_path": model_root, "files": rows}
    manifest_bytes = canonical(manifest) + b"\n"
    material = {"model_path": model_root, "files": rows}
    artifacts["model-identity.expected.json"] = manifest_bytes
    sidecar = {
        "schema": "epyc.autokernel.expected_model_inventory_preparation.v1",
        "disposition": "metadata_declared_expected", "local_model_bytes_verified": False,
        "remote_metadata_freshly_authenticated": False,
        "remote_repository": REMOTE_REPOSITORY, "remote_revision": REVISION,
        "source_tree_path": str(tree_path), "source_tree_sha256": digest(tree_bytes),
        "source_tree_size_bytes": len(tree_bytes),
        "retained_source_tree": "source-tree.json.base64",
        "retained_source_tree_encoding": "base64",
        "retained_source_tree_sha256": digest(encoded_tree),
        "model_path": model_root,
        "expected_manifest": "model-identity.expected.json",
        "expected_manifest_sha256": digest(manifest_bytes),
        "expected_normalized_inventory_sha256": digest(canonical(material)),
        "entry_path": f"{model_root}/{BASENAMES[0]}",
        "expected_entry_sha256": rows[0]["sha256"],
        "declared_total_size_bytes": sum(row["declared_size_bytes"] for row in provenance_rows),
        "members": provenance_rows,
    }
    artifacts["expected-inventory-provenance.json"] = canonical(sidecar) + b"\n"
    if sum(len(value) for value in artifacts.values()) > PACKET_CAP:
        raise AuthoringRefused("authored metadata packet exceeds bound")
    return artifacts


def write_new_packet(output: str, artifacts: dict[str, bytes]) -> None:
    """Write only a new private directory, never replace an existing packet."""
    root = Path(normalized_absolute(output))
    for parent in (root.parent, *root.parent.parents):
        if parent.is_symlink():
            raise AuthoringRefused("output parent must not traverse symlinks")
    if any(name.startswith("/") or ".." in Path(name).parts for name in artifacts):
        raise AuthoringRefused("unsafe packet member")
    root.mkdir(mode=0o700, exist_ok=False)
    (root / "download").mkdir(mode=0o700)
    for name, payload in sorted(artifacts.items()):
        descriptor = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--model-root", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    artifacts = assemble(arguments.cache_root, arguments.model_root)
    write_new_packet(arguments.output, artifacts)
    print(json.dumps({"disposition": "metadata_declared_expected", "files": len(artifacts),
                      "local_model_bytes_verified": False, "output": arguments.output},
                     sort_keys=True))


if __name__ == "__main__":
    main()
