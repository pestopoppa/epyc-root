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


def _message(path: Path, worker: str, now: float) -> tuple[str, str] | None:
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
        if stamp.tzinfo is None or not 0 <= now - stamp.timestamp() <= MAX_AGE:
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
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, OverflowError):
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
            if row.get("kind") != "ack" or (row.get("payload") or {}).get("disposition") in {"done", "declined", "handed-off", "superseded"}:
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


def reconcile(bus_root: Path, agent: str, repo: Path, *, common: Path | None = None) -> None:
    if agent != "coordinator-agent":
        return
    handled = _handled(bus_root, agent)
    if handled is None:
        return
    common = common or _common_dir(repo)
    if common is None:
        return
    source = common / "worker-checkpoints"
    if not _directory(source):
        return
    receipt_root = bus_root / "checkpoint-notices"
    try:
        receipt_root.mkdir(mode=0o700, exist_ok=True)
        if not _directory(receipt_root):
            return
        owner = receipt_root / agent
        owner.mkdir(mode=0o700, exist_ok=True)
        if not _directory(owner):
            return
        count = 0
        emitted = 0
        for worker in WORKERS:
            directory = source / worker
            if not _directory(directory):
                continue
            for path in sorted(directory.iterdir()):
                count += 1
                if count > MAX_FILES:
                    return
                if not CHECKPOINT.fullmatch(path.stem) or path.suffix != ".json":
                    continue
                candidate = _message(path, worker, time.time())
                if candidate is None:
                    continue
                key, message_id = candidate
                if message_id in handled:
                    continue
                line = f"checkpoint notice: {worker} {key} {message_id} journal=worker-checkpoints/{worker}/{key}.json"
                size = len((line + "\n").encode("utf-8"))
                if emitted + size > MAX_NOTICE_BYTES:
                    return
                lock_path = owner / (key + ".lock")
                fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                try:
                    if not stat.S_ISREG(os.fstat(fd).st_mode):
                        continue
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue
                    done = owner / (key + ".json")
                    if done.is_symlink():
                        continue
                    if done.exists():
                        try:
                            previous = json.loads(_read_stable(done, 4096))
                        except (OSError, ValueError, json.JSONDecodeError):
                            continue  # unknown receipt; do not invent its meaning
                        if previous == {"checkpoint_id": key, "message_id": message_id}:
                            continue
                        continue
                    # Recheck after locking: producer may have replaced its journal.
                    if _message(path, worker, time.time()) != candidate:
                        continue
                    print(line, file=sys.stderr, flush=True)
                    emitted += size
                    # A crash here may repeat a notice; it must never lose one.
                    out, tmp = tempfile.mkstemp(prefix=".notice-", dir=owner)
                    try:
                        with os.fdopen(out, "w") as f:
                            json.dump({"checkpoint_id": key, "message_id": message_id}, f, sort_keys=True)
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
                finally:
                    os.close(fd)
    except OSError:
        # Unknown is never treated as evidence that an artifact was handled.
        return
