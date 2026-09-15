#!/usr/bin/env python3
"""Preserve dirty AutoKernel worktrees named by a reviewed disk-sweep manifest.

The default is a dry-run.  ``--write`` publishes deterministic, content-addressed tar
archives under ``--archive-root``.  The source worktree is read only: every Git command
runs with optional locks disabled, and the tool never checks out, resets, cleans, stages,
commits, fetches, removes, or prunes anything.

Each archive contains:

* exact porcelain-v2/NUL Git status;
* repository, HEAD, branch, remote, and manifest provenance;
* ``git diff --binary HEAD``;
* every untracked, non-ignored regular file or symlink; and
* a standalone ``git bundle`` when HEAD is not contained by a network remote-tracking ref.

The tar is deterministic and self-describing.  ``ARCHIVE-MANIFEST.json`` hashes every
member.  Publication is atomic, archives are named by SHA-256, and a second identical run
verifies and reuses the existing object.  A before/after fingerprint prevents publishing a
snapshot if the source changes during capture.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

SWEEP_SCHEMA = "autokernel-disk-sweep-manifest/v1"
ARCHIVE_SCHEMA = "autokernel-dirty-worktree-archive/v1"
RECORD_SCHEMA = "autokernel-dirty-worktree-record/v1"
DEFAULT_ARCHIVE_ROOT = "/mnt/raid0/llm/archives/autokernel/dirty-worktrees"


class PreserveError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def git(path: Path, *args: str, check: bool = True) -> bytes:
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    proc = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, env=env, check=False,
    )
    if check and proc.returncode:
        raise PreserveError(f"git {' '.join(args)} failed in {path}: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def is_network_remote(url: str) -> bool:
    lower = url.lower()
    if lower.startswith(("https://", "http://", "ssh://", "git://")):
        return True
    if lower.startswith("file://") or url.startswith(("/", "./", "../")):
        return False
    # SCP-like Git URLs: git@example.org:owner/repo.git
    return "@" in url and ":" in url.split("@", 1)[1]


def nul_items(data: bytes) -> list[bytes]:
    if not data:
        return []
    if not data.endswith(b"\0"):
        raise PreserveError("expected NUL-terminated Git output")
    return data[:-1].split(b"\0")


def safe_relative(raw: bytes) -> str:
    try:
        value = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PreserveError(f"untracked path is not UTF-8: {raw!r}") from exc
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or any(part in ("", ".", "..") for part in p.parts):
        raise PreserveError(f"unsafe untracked path: {value!r}")
    return value


def read_remotes(path: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    network_names: list[str] = []
    for name_b in git(path, "remote").splitlines():
        name = name_b.decode()
        urls = [u.decode() for u in git(path, "remote", "get-url", "--all", name).splitlines()]
        network = any(is_network_remote(url) for url in urls)
        rows.append({"name": name, "urls": urls, "network": network})
        if network:
            network_names.append(name)
    return rows, network_names


def containing_network_refs(path: Path, head: str, network_names: Iterable[str]) -> list[str]:
    result: list[str] = []
    for remote in network_names:
        refs = git(path, "for-each-ref", "--format=%(refname)", f"refs/remotes/{remote}/").splitlines()
        for ref_b in refs:
            ref = ref_b.decode()
            proc = subprocess.run(
                ["git", "-C", str(path), "merge-base", "--is-ancestor", head, ref],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, check=False,
            )
            if proc.returncode == 0:
                result.append(ref)
            elif proc.returncode != 1:
                raise PreserveError(f"cannot test containment of {head} in {ref}")
    return sorted(result)


@dataclasses.dataclass(frozen=True)
class UntrackedEntry:
    path: str
    kind: str
    mode: int
    size: int
    sha256: str
    data: bytes | None = dataclasses.field(compare=False, repr=False)
    link_target: str | None = None

    def metadata(self) -> dict:
        return {k: v for k, v in dataclasses.asdict(self).items() if k != "data" and v is not None}


def status_untracked_paths(status_raw: bytes) -> set[str]:
    result: set[str] = set()
    for entry in nul_items(status_raw):
        if entry.startswith(b"? "):
            result.add(safe_relative(entry[2:]))
    return result


def read_untracked(root: Path, status_raw: bytes) -> list[UntrackedEntry]:
    raw_paths = nul_items(git(root, "ls-files", "--others", "--exclude-standard", "-z"))
    listed = {safe_relative(raw) for raw in raw_paths}
    reported = status_untracked_paths(status_raw)
    if listed != reported:
        missing = sorted(reported - listed)
        extra = sorted(listed - reported)
        special = []
        for rel in missing:
            try:
                mode = (root / rel).lstat().st_mode
            except OSError:
                continue
            if not stat.S_ISREG(mode) and not stat.S_ISLNK(mode):
                special.append(rel)
        if special:
            raise PreserveError(
                f"unsupported untracked special file (refusing incomplete archive): {special}"
            )
        raise PreserveError(
            "untracked enumeration disagrees with exact status; refusing incomplete archive: "
            f"missing={missing} extra={extra}"
        )
    entries: list[UntrackedEntry] = []
    for rel in sorted(listed):
        source = root / rel
        st = source.lstat()
        mode = stat.S_IMODE(st.st_mode)
        if stat.S_ISREG(st.st_mode):
            data = source.read_bytes()
            entries.append(UntrackedEntry(rel, "file", mode, len(data), sha256_bytes(data), data))
        elif stat.S_ISLNK(st.st_mode):
            target = os.readlink(source)
            payload = target.encode("utf-8", errors="surrogateescape")
            entries.append(
                UntrackedEntry(rel, "symlink", mode, len(payload), sha256_bytes(payload), None, target)
            )
        else:
            raise PreserveError(f"unsupported untracked special file (refusing incomplete archive): {source}")
    return entries


@dataclasses.dataclass
class Snapshot:
    root: Path
    metadata: dict
    status: bytes
    diff: bytes
    staged_diff: bytes
    worktree_diff: bytes
    untracked: list[UntrackedEntry]
    bundle: bytes | None

    def fingerprint(self) -> str:
        value = {
            "head": self.metadata["head"],
            "status_sha256": sha256_bytes(self.status),
            "diff_sha256": sha256_bytes(self.diff),
            "staged_diff_sha256": sha256_bytes(self.staged_diff),
            "worktree_diff_sha256": sha256_bytes(self.worktree_diff),
            "untracked": [x.metadata() for x in self.untracked],
        }
        return sha256_bytes(canonical_json(value))


def dirty_submodule(status_raw: bytes) -> bool:
    for entry in nul_items(status_raw):
        # Porcelain v2 ordinary and rename entries: field 3 is the four-character submodule state.
        if entry.startswith((b"1 ", b"2 ")):
            fields = entry.split(b" ", 4)
            if len(fields) >= 3 and fields[2] != b"N...":
                return True
    return False


def create_head_bundle(root: Path) -> bytes:
    # Git does not support a reliable binary stdout mode on every deployed version; use a private
    # temporary file outside the source and remove it immediately.
    fd, tmp = tempfile.mkstemp(prefix="autokernel-dirty-head-", suffix=".bundle")
    os.close(fd)
    try:
        git(root, "bundle", "create", tmp, "HEAD")
        return Path(tmp).read_bytes()
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def capture(root: Path, manifest_sha: str, row: dict, include_bundle: bool = True) -> Snapshot:
    if not root.is_dir():
        raise PreserveError(f"source worktree is absent: {root}")
    status_raw = git(root, "status", "--porcelain=v2", "-z", "--untracked-files=all")
    if not status_raw:
        raise PreserveError(f"manifest says KEEP-dirty but worktree is now clean: {root}")
    if dirty_submodule(status_raw):
        raise PreserveError(f"dirty submodule is unsupported; preserve it separately first: {root}")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    top = git(root, "rev-parse", "--show-toplevel").decode().strip()
    if os.path.realpath(top) != os.path.realpath(root):
        raise PreserveError(f"row path is not the worktree top: {root} != {top}")
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).decode().strip() or None
    common_dir = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()
    git_dir = git(root, "rev-parse", "--path-format=absolute", "--git-dir").decode().strip()
    remotes, network_names = read_remotes(root)
    contained = containing_network_refs(root, head, network_names)
    unpushed = not contained
    diff = git(root, "diff", "--binary", "HEAD", "--")
    staged_diff = git(root, "diff", "--cached", "--binary", "HEAD", "--")
    worktree_diff = git(root, "diff", "--binary", "--")
    untracked = read_untracked(root, status_raw)
    bundle = create_head_bundle(root) if unpushed and include_bundle else None
    metadata = {
        "schema": ARCHIVE_SCHEMA,
        "source_path": str(root),
        "sweep_manifest_sha256": manifest_sha,
        "sweep_row": row,
        "head": head,
        "branch": branch,
        "git_dir": git_dir,
        "git_common_dir": common_dir,
        "remotes": remotes,
        "network_remote_tracking_refs_containing_head": contained,
        "head_unpushed_to_network_remote": unpushed,
        "untracked": [x.metadata() for x in untracked],
    }
    return Snapshot(root, metadata, status_raw, diff, staged_diff, worktree_diff, untracked, bundle)


def archive_members(snapshot: Snapshot) -> tuple[list[tuple[str, str, int, bytes | str]], bytes]:
    members: list[tuple[str, str, int, bytes | str]] = [
        ("metadata.json", "file", 0o444, canonical_json(snapshot.metadata)),
        ("git-status-v2-z.bin", "file", 0o444, snapshot.status),
        ("git-diff-binary-head.patch", "file", 0o444, snapshot.diff),
        ("git-diff-binary-staged.patch", "file", 0o444, snapshot.staged_diff),
        ("git-diff-binary-worktree.patch", "file", 0o444, snapshot.worktree_diff),
    ]
    if snapshot.bundle is not None:
        members.append(("unpushed-head.bundle", "file", 0o444, snapshot.bundle))
    for item in snapshot.untracked:
        name = f"untracked/{item.path}"
        if item.kind == "file":
            assert item.data is not None
            members.append((name, "file", item.mode, item.data))
        else:
            assert item.link_target is not None
            members.append((name, "symlink", item.mode, item.link_target))
    members.sort(key=lambda x: x[0])
    index = []
    for name, kind, mode, value in members:
        payload = value if isinstance(value, bytes) else value.encode("utf-8", errors="surrogateescape")
        index.append(
            {
                "path": name,
                "kind": kind,
                "mode": mode,
                "size": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )
    manifest = canonical_json({"schema": ARCHIVE_SCHEMA, "members": index})
    return members, manifest


def add_tar_member(tf: tarfile.TarFile, name: str, kind: str, mode: int, value: bytes | str) -> None:
    info = tarfile.TarInfo(name)
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mode = mode
    if kind == "file":
        assert isinstance(value, bytes)
        info.size = len(value)
        tf.addfile(info, io.BytesIO(value))
    elif kind == "symlink":
        assert isinstance(value, str)
        info.type = tarfile.SYMTYPE
        info.linkname = value
        info.size = 0
        tf.addfile(info)
    else:
        raise PreserveError(f"unsupported archive member kind: {kind}")


def build_archive(snapshot: Snapshot, output: Path) -> str:
    members, manifest = archive_members(snapshot)
    with output.open("wb") as raw:
        with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tf:
            for member in members:
                add_tar_member(tf, *member)
            add_tar_member(tf, "ARCHIVE-MANIFEST.json", "file", 0o444, manifest)
        raw.flush()
        os.fsync(raw.fileno())
    return sha256_file(output)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_member_name(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(p.parts) and not p.is_absolute() and all(part not in ("", ".", "..") for part in p.parts)


def verify_archive(path: Path, source_repo: Path | None = None) -> dict:
    artifact_sha = sha256_file(path)
    if (
        len(path.stem) == 64
        and all(c in "0123456789abcdef" for c in path.stem.lower())
        and path.stem.lower() != artifact_sha
    ):
        raise PreserveError(f"content-address filename does not match archive SHA-256: {path}")
    with tarfile.open(path, "r:") as tf:
        members = tf.getmembers()
        if any(not safe_member_name(m.name) for m in members):
            raise PreserveError(f"archive contains unsafe member name: {path}")
        by_name = {m.name: m for m in members}
        if len(by_name) != len(members) or "ARCHIVE-MANIFEST.json" not in by_name:
            raise PreserveError(f"archive member duplication or missing manifest: {path}")
        mf = tf.extractfile(by_name["ARCHIVE-MANIFEST.json"])
        if mf is None:
            raise PreserveError(f"archive manifest is not a file: {path}")
        index = json.loads(mf.read())
        if index.get("schema") != ARCHIVE_SCHEMA:
            raise PreserveError(f"archive schema mismatch: {path}")
        expected = {x["path"]: x for x in index.get("members", [])}
        if set(by_name) != set(expected) | {"ARCHIVE-MANIFEST.json"}:
            raise PreserveError(f"archive member set does not match manifest: {path}")
        for name, item in expected.items():
            member = by_name[name]
            if stat.S_IMODE(member.mode) != item["mode"]:
                raise PreserveError(f"mode mismatch for {name}")
            if item["kind"] == "file":
                if not member.isfile():
                    raise PreserveError(f"expected regular file: {name}")
                fh = tf.extractfile(member)
                assert fh is not None
                payload = fh.read()
            elif item["kind"] == "symlink":
                if not member.issym():
                    raise PreserveError(f"expected symlink: {name}")
                payload = member.linkname.encode("utf-8", errors="surrogateescape")
            else:
                raise PreserveError(f"unknown member kind for {name}")
            if len(payload) != item["size"] or sha256_bytes(payload) != item["sha256"]:
                raise PreserveError(f"hash/size mismatch for {name}")
        metadata_fh = tf.extractfile(by_name["metadata.json"])
        assert metadata_fh is not None
        metadata = json.loads(metadata_fh.read())
        bundle = by_name.get("unpushed-head.bundle")
        if metadata.get("head_unpushed_to_network_remote") != bool(bundle):
            raise PreserveError("bundle presence does not match unpushed metadata")
        if bundle and source_repo is not None:
            bundle_fh = tf.extractfile(bundle)
            assert bundle_fh is not None
            fd, tmp = tempfile.mkstemp(prefix="autokernel-verify-", suffix=".bundle")
            try:
                with os.fdopen(fd, "wb") as out:
                    shutil.copyfileobj(bundle_fh, out)
                    out.flush()
                    os.fsync(out.fileno())
                git(source_repo, "bundle", "verify", tmp)
            finally:
                try:
                    os.unlink(tmp)
                except FileNotFoundError:
                    pass
    return {"archive_sha256": artifact_sha, "metadata": metadata, "members": len(expected)}


def load_reviewed_manifest(path: Path, expected_sha: str) -> tuple[dict, str]:
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != expected_sha.lower():
        raise PreserveError(f"manifest sha256 {actual} != reviewed --manifest-sha {expected_sha}")
    manifest = json.loads(data)
    if manifest.get("schema") != SWEEP_SCHEMA:
        raise PreserveError(f"unsupported sweep manifest schema: {manifest.get('schema')}")
    return manifest, actual


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(canonical_json(value))
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o444)
        os.replace(tmp, path)
        dirfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def preserve_one(row: dict, manifest_sha: str, archive_root: Path, write: bool) -> dict:
    root = Path(row["path"])
    first = capture(root, manifest_sha, row)
    before = first.fingerprint()
    temp_parent = archive_root if write else Path(tempfile.gettempdir())
    if write:
        temp_parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_s = tempfile.mkstemp(prefix=".autokernel-dirty-", suffix=".tar", dir=temp_parent)
    os.close(fd)
    tmp = Path(tmp_s)
    try:
        artifact_sha = build_archive(first, tmp)
        verified = verify_archive(tmp, root)
        second = capture(root, manifest_sha, row, include_bundle=False)
        after = second.fingerprint()
        if before != after:
            raise PreserveError(f"source changed during capture; archive not published: {root}")
        result = {
            "path": str(root), "head": first.metadata["head"], "source_fingerprint": before,
            "archive_sha256": artifact_sha, "bytes": tmp.stat().st_size,
            "unpushed_bundle": first.bundle is not None,
            "untracked_files": len(first.untracked), "verified_members": verified["members"],
            "action": "dry-run",
        }
        if not write:
            return result
        object_path = archive_root / "objects" / artifact_sha[:2] / f"{artifact_sha}.tar"
        object_path.parent.mkdir(parents=True, exist_ok=True)
        if object_path.exists():
            verify_archive(object_path, root)
            if sha256_file(object_path) != artifact_sha:
                raise PreserveError(f"content-address collision: {object_path}")
            result["action"] = "deduplicated"
        else:
            os.chmod(tmp, 0o444)
            os.replace(tmp, object_path)
            dirfd = os.open(object_path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
            verify_archive(object_path, root)
            result["action"] = "archived"
        result["archive"] = str(object_path)
        source_key = sha256_bytes(str(root).encode())
        record_path = archive_root / "records" / source_key[:2] / source_key / f"{artifact_sha}.json"
        # Runtime action is intentionally not durable content: the first run says ``archived``
        # and the identical resumed run says ``deduplicated``.  Everything else must match.
        record = {
            "schema": RECORD_SCHEMA,
            **{k: v for k, v in result.items() if k not in ("action", "record")},
            "sweep_manifest_sha256": manifest_sha,
        }
        if record_path.exists():
            existing = json.loads(record_path.read_bytes())
            if existing != record:
                raise PreserveError(f"record collision: {record_path}")
        else:
            atomic_json(record_path, record)
        result["record"] = str(record_path)
        return result
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", help="reviewed autokernel disk-sweep manifest")
    ap.add_argument("--manifest-sha", help="exact SHA-256 of the reviewed manifest")
    ap.add_argument("--archive-root", default=DEFAULT_ARCHIVE_ROOT)
    ap.add_argument("--path", action="append", help="preserve only this exact KEEP-dirty path (repeatable)")
    ap.add_argument("--limit", type=int, help="process at most N selected rows")
    ap.add_argument("--write", action="store_true", help="publish verified archives; default is dry-run")
    ap.add_argument("--verify-archive", action="append", help="verify an existing archive and exit")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verify_archive:
        if args.write or args.manifest or args.manifest_sha or args.path or args.limit is not None:
            raise PreserveError("--verify-archive cannot be combined with capture options")
        reports = [verify_archive(Path(p)) for p in args.verify_archive]
        print(json.dumps({"verified": reports}, indent=2, sort_keys=True))
        return 0
    if not args.manifest or not args.manifest_sha:
        raise PreserveError("--manifest and --manifest-sha are required")
    if args.limit is not None and args.limit < 1:
        raise PreserveError("--limit must be positive")
    manifest, manifest_sha = load_reviewed_manifest(Path(args.manifest), args.manifest_sha)
    rows = [r for r in manifest.get("rows", []) if r.get("verdict") == "KEEP-dirty"]
    by_path = {r.get("path"): r for r in rows}
    if len(by_path) != len(rows):
        raise PreserveError("duplicate KEEP-dirty path in manifest")
    if args.path:
        missing = sorted(set(args.path) - set(by_path))
        if missing:
            raise PreserveError(f"requested path is not KEEP-dirty in reviewed manifest: {missing}")
        rows = [by_path[p] for p in args.path]
    rows = sorted(rows, key=lambda r: r["path"])
    if args.limit is not None:
        rows = rows[: args.limit]
    results, errors = [], []
    for row in rows:
        try:
            results.append(preserve_one(row, manifest_sha, Path(args.archive_root), args.write))
        except Exception as exc:  # noqa: BLE001 - fail row closed, continue resumable batch
            errors.append({"path": row.get("path"), "error": str(exc)})
    report = {
        "mode": "write" if args.write else "dry-run", "manifest_sha256": manifest_sha,
        "selected": len(rows), "completed": len(results), "failed": len(errors),
        "results": results, "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PreserveError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
