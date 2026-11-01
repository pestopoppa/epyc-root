"""One-shot, delivery-independent worker checkpoint notifications at drain.

Only the coordinator reads the worker_checkpoint.v1 journals. A completed
receipt records a flushed notification, never a planned delivery. Locks are
per checkpoint and abandoned locks are automatically released by the OS.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_ARTIFACT = 256 * 1024
MAX_OUTBOX = 8 * 1024 * 1024
MAX_FILES = 1024
MAX_NOTICE_BYTES = 4096
MAX_AGE = 7 * 86400
WORKERS = ("mainA", "mainB", "mainC", "mainD")
CHECKPOINT = re.compile(r"wcp-[0-9a-f]{24}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


def _read_stable(path: Path, cap: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > cap:
            raise ValueError("unsafe or oversized file")
        chunks = []
        remaining = cap + 1
        while remaining:
            part = os.read(fd, min(remaining, 65536))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b"".join(chunks)
        after = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(data) > cap or signature(before) != signature(after) or signature(after) != signature(named):
            raise ValueError("file changed during read")
        return data
    finally:
        os.close(fd)


def _directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.stat(follow_symlinks=False).st_mode)
    except OSError:
        return False


def _message(path: Path, worker: str, now: float, *, allow_stale: bool = False) -> tuple[str, str] | None:
    try:
        if path.stat(follow_symlinks=False).st_uid != path.parent.stat(follow_symlinks=False).st_uid:
            return None
        raw = _read_stable(path, MAX_ARTIFACT)
        journal = json.loads(raw)
        identity = journal["identity"]
        receipt = journal["receipt"]
        payload = receipt["payload"]
        key = journal["checkpoint_id"]
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        expected = "wcp-" + hashlib.sha256(canonical.encode()).hexdigest()[:24]
        stamp = datetime.fromisoformat(journal["completed_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None or now < stamp.timestamp() or (not allow_stale and now - stamp.timestamp() > MAX_AGE):
            return None
        if (journal["schema_version"] != "worker_checkpoint.v1" or
            journal["phase"] not in ("receipt_ready", "published") or
            not CHECKPOINT.fullmatch(key) or path.name != key + ".json" or key != expected or
            journal["boundary_id"] != key or identity["agent"] != worker or
            receipt["schema_version"] != "worker_checkpoint.receipt.v1" or
            receipt["kind"] != "task-checkpoint" or receipt["checkpoint_id"] != key or
            payload["boundary_id"] != key or payload["agent"] != worker or
            payload["task_id"] != identity["task_id"] or payload["task_text"] != identity["task_text"] or
            payload["outcome"] != identity["outcome"] or payload["completed_at"] != journal["completed_at"] or
            payload["commit_sha"] != journal["commit_sha"] or not SHA.fullmatch(payload["commit_sha"]) or
            payload["branch"] != "lane/" + worker or
            payload["pushed_ref"] != "refs/remotes/origin/lane/" + worker or
            journal["pushed_ref"] != payload["pushed_ref"]):
            return None
        message_id = f"msg-{stamp.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}-{int(key[4:19], 16)}-{worker}"
        if journal["phase"] == "published" and journal.get("bus_message_id") != message_id:
            return None
        return key, message_id
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, json.JSONDecodeError, OverflowError):
        return None


def _handled(bus_root: Path, agent: str) -> set[str] | None:
    try:
        raw = _read_stable(bus_root / "outbox" / (agent + ".jsonl"), MAX_OUTBOX)
        aliases = {}
        inbox = _read_stable(bus_root / "inbox" / (agent + ".jsonl"), MAX_OUTBOX)
        for line in inbox.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                return None
            if row.get("relayed_src") and isinstance(row.get("id"), str) and isinstance(row["relayed_src"], str):
                aliases[row["id"]] = row["relayed_src"]
        result = set()
        for line in raw.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("from") != agent:
                return None
            corrs = [row.get("corr_id")] + (row.get("corr_ids") or [])
            if not isinstance(corrs, list) or any(c is not None and not isinstance(c, str) for c in corrs):
                return None
            # Triage treats every correlated non-ack as actioned. This
            # backstop is deliberately narrower: only an explicit terminal
            # disposition proves the checkpoint was handled.
            if (row.get("payload") or {}).get("disposition") in {"done", "declined", "handed-off", "superseded"}:
                result.update(aliases.get(c, c) for c in corrs if c)
        return result
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return None


def _common_dir(repo: Path) -> Path | None:
    try:
        p = subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           check=True, capture_output=True, text=True, timeout=3)
        return Path(p.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return None


def _source_signature(path: Path) -> list[int]:
    info = path.stat(follow_symlinks=False)
    if (not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARTIFACT or
            info.st_uid != path.parent.stat(follow_symlinks=False).st_uid):
        raise ValueError("unsafe source")
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def _receipt(path: Path, key: str, worker: str) -> dict | None:
    try:
        if path.stat(follow_symlinks=False).st_uid != path.parent.stat(follow_symlinks=False).st_uid:
            raise ValueError("foreign receipt")
        record = json.loads(_read_stable(path, 4096))
    except FileNotFoundError:
        return None
    if not isinstance(record, dict) or record.get("checkpoint_id") != key:
        raise ValueError("invalid receipt")
    msg = record.get("message_id")
    if not isinstance(msg, str) or not re.fullmatch(
            rf"msg-[0-9]{{8}}T[0-9]{{6}}Z-{int(key[4:19], 16)}-{worker}", msg):
        raise ValueError("invalid receipt identity")
    if set(record) == {"checkpoint_id", "message_id"}:
        return record  # v1 notified receipt, must revalidate source before caching
    if set(record) != {"checkpoint_id", "message_id", "kind", "source_signature"}:
        raise ValueError("invalid receipt fields")
    if record["kind"] not in ("notified", "handled") or not isinstance(record["source_signature"], list):
        raise ValueError("invalid receipt kind or signature")
    return record


def _write_receipt(owner: Path, done: Path, record: dict) -> None:
    out, tmp = tempfile.mkstemp(prefix=".notice-", dir=owner)
    try:
        with os.fdopen(out, "w") as f:
            json.dump(record, f, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, done)
        dirfd = os.open(owner, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def reconcile(bus_root: Path, agent: str, repo: Path, *, common: Path | None = None) -> dict:
    """Notify once; return coverage instead of making unknowns an all-clear."""
    coverage = {"scanned": 0, "unknown": 0, "truncated": False}
    if agent != "coordinator-agent":
        return coverage
    handled = _handled(bus_root, agent)
    if handled is None:
        coverage["unknown"] += 1
        return coverage
    common = common or _common_dir(repo)
    if common is None:
        coverage["unknown"] += 1
        return coverage
    source = common / "worker-checkpoints"
    if not _directory(source):
        if source.exists() or source.is_symlink():
            coverage["unknown"] += 1
        return coverage
    receipt_root = bus_root / "checkpoint-notices"
    try:
        receipt_root.mkdir(mode=0o700, exist_ok=True)
        if not _directory(receipt_root):
            coverage["unknown"] += 1
            return coverage
        owner = receipt_root / agent
        owner.mkdir(mode=0o700, exist_ok=True)
        if not _directory(owner):
            coverage["unknown"] += 1
            return coverage
        emitted = 0
        for worker in WORKERS:
            directory = source / worker
            if not _directory(directory):
                if directory.exists() or directory.is_symlink():
                    coverage["unknown"] += 1
                continue
            for path in sorted(directory.iterdir()):
                if not CHECKPOINT.fullmatch(path.stem) or path.suffix != ".json":
                    continue
                key = path.stem
                done = owner / (key + ".json")
                try:
                    signature = _source_signature(path)
                    previous = _receipt(done, key, worker)
                    # Cached proof remains valid only while its exact source stays
                    # unchanged and its completed_at is within the freshness window.
                    if previous and previous.get("source_signature") == signature:
                        stamp = datetime.strptime(previous["message_id"][4:20], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                        age = time.time() - stamp.timestamp()
                        if age < 0 or age > MAX_AGE:
                            coverage["unknown"] += 1
                        continue
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    coverage["unknown"] += 1
                    continue
                if coverage["scanned"] >= MAX_FILES:
                    coverage["truncated"] = True
                    return coverage
                coverage["scanned"] += 1
                legacy = previous is not None and "kind" not in previous
                candidate = _message(path, worker, time.time(), allow_stale=legacy)
                if candidate is None:
                    coverage["unknown"] += 1
                    continue
                _, message_id = candidate
                lock_path = owner / (key + ".lock")
                fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                try:
                    if not stat.S_ISREG(os.fstat(fd).st_mode):
                        coverage["unknown"] += 1
                        continue
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        coverage["unknown"] += 1
                        continue
                    try:
                        current = _source_signature(path)
                        previous = _receipt(done, key, worker)
                        if current != signature or _message(path, worker, time.time(), allow_stale=legacy) != candidate or _source_signature(path) != signature:
                            coverage["unknown"] += 1
                            continue
                        if previous:
                            if previous["message_id"] != message_id:
                                coverage["unknown"] += 1
                                continue
                            kind = previous.get("kind", "notified")
                            stamp = datetime.strptime(message_id[4:20], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                            if time.time() - stamp.timestamp() > MAX_AGE:
                                coverage["unknown"] += 1
                        elif message_id in handled:
                            kind = "handled"
                        else:
                            line = f"checkpoint notice: {worker} {key} {message_id} journal=worker-checkpoints/{worker}/{key}.json"
                            size = len((line + "\n").encode("utf-8"))
                            if emitted + size > MAX_NOTICE_BYTES:
                                coverage["truncated"] = True
                                return coverage
                            print(line, file=sys.stderr, flush=True)
                            emitted += size
                            kind = "notified"
                        _write_receipt(owner, done, {"checkpoint_id": key, "message_id": message_id,
                                                     "kind": kind, "source_signature": signature})
                    except (OSError, ValueError, TypeError, json.JSONDecodeError):
                        coverage["unknown"] += 1
                finally:
                    os.close(fd)
    except OSError:
        coverage["unknown"] += 1
    return coverage
