#!/usr/bin/env python3
"""Private, explicit custody for one StrategyStore projection-report invocation.

Input identities are hash-only declarations: this capsule does not copy journal or store
contents and makes no transitive-read or immutable-database claim. The reader never executes
captured source. The explicit root wrapper creates the private request before importing the
pinned report modules; ``main`` is invoked once and its returned CLI status is retained verbatim.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any
import uuid

SCHEMA = "epyc.strategy_projection_report_capture.v1"
REQUEST_SCHEMA = "epyc.strategy_projection_report_request.v1"
PROPOSITION = (
    "The original StrategyStore projection report recorded report.ok as the exact boolean "
    "result of its journal-derived projection comparison; counts are descriptive only."
)
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_INPUT_BYTES = 2 * 1024 * 1024 * 1024
MAX_SHARDS = 4096
SOURCE_FILES = {
    "report-source.bin": "scripts/autopilot/strategy_projection_report.py",
    "journal-source.bin": "scripts/autopilot/experiment_journal.py",
    "shards-source.bin": "scripts/autopilot/journal_shards.py",
    "store-source.bin": "orchestration/repl_memory/strategy_store.py",
    "faiss-source.bin": "orchestration/repl_memory/faiss_store.py",
    "embedder-source.bin": "orchestration/repl_memory/embedder.py",
    "memory-record-source.bin": "orchestration/repl_memory/memory_record.py",
    "src-package-source.bin": "src/__init__.py",
    "lock-source.bin": "src/inference_lock.py",
    "lock-runtime-source.bin": "src/runtime/inference_lock.py",
    "tier-spec-source.bin": "src/autopilot_core/tier_specs.py",
}
TRUSTED_APP_SOURCES = {
    "report-source.bin": "08286a31d98404758b7d09eecc5a2ab90181bf63484f66566361906c0e7d1f1b",
    "journal-source.bin": "f5f29d0d99311e45b4f0aa50f812622993fe714f7652218e86c2906c1135d756",
    "shards-source.bin": "d7ed426ccc3972b6950f23a1af0e26ae6ed5e3e9dde7e6401f963cd63923adda",
    "store-source.bin": "8a5cd857d9723827ec2f5346057aa89d5ec358a2fdceeaf7a4566e2ae7889f64",
    "faiss-source.bin": "ac73aade178f0a13430c3ea01cd50d7c971e6059817673d3976fd13347f6f39d",
    "embedder-source.bin": "4697fd6f877fd1a1d9792c78300319c4bae96b75309e5a71b9f921354bb4bf75",
    "memory-record-source.bin": "7a41ca1bc46febe0efbaaa1a6b96f84e40b4338d6a690dae0ca09b9e7d85fe2b",
    "src-package-source.bin": "16e20bce77e6470646b90def0e3d653a3bd9fb024b484f7cd034f96ff8a0a5f8",
    "lock-source.bin": "642b6a902a8c45949402d23aaf3237327619d338ee80f27f141ecb0dbb49f2c0",
    "lock-runtime-source.bin": "659a51c1f1bd1c8db0e07d4092c5e9ddbf05f989be0ac84cb251a23be0ca9a36",
    "tier-spec-source.bin": "89ee24c066c8bed1b18a4c6c577fef530a447abd3db9fbf0fd308974ea18d095",
}
ARTIFACT_LIMITS = {
    "execution-request.json": 2 * 1024 * 1024,
    "producer-source.bin": MAX_SOURCE_BYTES,
    **{name: MAX_SOURCE_BYTES for name in SOURCE_FILES},
    "stdout.bin": 32 * 1024 * 1024,
    "stderr.bin": 32 * 1024 * 1024,
    "report-markdown.bin": 32 * 1024 * 1024,
    "terminal.json": 1024 * 1024,
}
ARTIFACT_NAMES = set(ARTIFACT_LIMITS)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _regular_bytes(path: Path, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("declared input is not a regular file")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        after = os.fstat(fd)
        if (len(raw) > limit or (before.st_dev, before.st_ino, before.st_size,
                                 before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise ValueError("declared input changed or exceeded its byte limit while hashing")
        return raw
    finally:
        os.close(fd)


def _hash_regular(path: Path, limit: int) -> tuple[str, os.stat_result]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("declared input is not regular or exceeds its hash limit")
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(fd, "rb", closefd=False) as handle:
            while chunk := handle.read(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise ValueError("declared input exceeded its hash limit")
                digest.update(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("declared input changed while hashing")
        return digest.hexdigest(), before
    finally:
        os.close(fd)


def _write_exclusive(path: Path, raw: bytes) -> dict[str, Any]:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.fchmod(fd, 0o400)
    finally:
        os.close(fd)
    return {"name": path.name, "sha256": sha256(raw), "size": len(raw)}


def _custody_chain(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    for candidate in (Path("/"), *absolute.parents[::-1], absolute):
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("capture custody chain contains a symlink or non-directory")
        if info.st_uid not in (0, os.geteuid()):
            raise ValueError("capture custody chain has an untrusted owner")
        writable = stat.S_IMODE(info.st_mode) & 0o022
        if writable and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX):
            raise ValueError("capture custody ancestor is group/world writable")


def _new_run_dir(root: Path, capture_id: str) -> Path:
    root = Path(os.path.abspath(root))
    _custody_chain(root)
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError("capture output root must already be owned and private (0700)")
    target = root / capture_id
    if os.path.lexists(target):
        raise ValueError("capture UUID already exists")
    target.mkdir(mode=0o700)
    return target


def _artifact_identity(path: Path, role: str, *, absent_ok: bool = True) -> dict[str, Any]:
    raw_path = Path(os.path.abspath(path))
    try:
        info = raw_path.lstat()
    except FileNotFoundError:
        if absent_ok:
            return {"role": role, "path": str(raw_path), "state": "absent"}
        raise
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError("declared input must be a non-symlink regular file")
    if info.st_size > MAX_INPUT_BYTES:
        raise ValueError("declared input exceeds the identity hash limit")
    digest, hashed = _hash_regular(raw_path, MAX_INPUT_BYTES)
    after = raw_path.lstat()
    if (stat.S_ISLNK(after.st_mode) or not stat.S_ISREG(after.st_mode)
            or (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) !=
            (hashed.st_dev, hashed.st_ino, hashed.st_size, hashed.st_mtime_ns)):
        raise ValueError("declared input path changed while hashing")
    return {"role": role, "path": str(raw_path), "state": "present",
            "sha256": digest, "size": info.st_size, "device": info.st_dev,
            "inode": info.st_ino, "mtime_ns": info.st_mtime_ns}


def declared_inputs(journal_dir: Path, strategy_path: Path) -> list[dict[str, Any]]:
    """Hash bounded declared inputs only; never copy them or claim dependency completeness."""
    journal_dir = Path(os.path.abspath(journal_dir))
    strategy_path = Path(os.path.abspath(strategy_path))
    info = journal_dir.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValueError("journal input must be an existing non-symlink directory")
    shards = []
    batches = []
    pattern = re.compile(r"^autopilot_journal(?:_(\d+))?\.jsonl$")
    for child in journal_dir.iterdir():
        match = pattern.fullmatch(child.name)
        if not match:
            continue
        if match.group(1) is not None and match.group(1) != str(int(match.group(1))):
            raise ValueError("journal shard has a noncanonical numeric suffix")
        batch = 0 if match.group(1) is None else int(match.group(1))
        if batch == 0 and match.group(1) is not None:
            raise ValueError("journal shard batch zero must use the base filename")
        if batch in batches:
            raise ValueError("journal shard directory contains duplicate batch identities")
        batches.append(batch)
        if len(shards) >= MAX_SHARDS:
            raise ValueError("journal shard count exceeds the declared limit")
        shards.append(child)
    shards.sort(key=lambda item: (0 if item.name == "autopilot_journal.jsonl"
                                  else int(pattern.fullmatch(item.name).group(1)), item.name))
    identities = [_artifact_identity(path, f"journal-shard-{index}", absent_ok=False)
                  for index, path in enumerate(shards)]
    # StrategyStore opens this DB and its FAISS constructor inspects the named index/id-map.
    # SQLite sidecars are bound as present/absent names; this is a hash-only declaration.
    for name, role in (("strategies.db", "sqlite-db"), ("strategies.db-wal", "sqlite-wal"),
                       ("strategies.db-shm", "sqlite-shm"),
                       ("strategy_embeddings.faiss", "faiss-index"),
                       ("strategy_id_map.npy", "faiss-id-map")):
        identities.append(_artifact_identity(strategy_path / name, role))
    return identities


def _directory_identity(path: Path, role: str) -> dict[str, Any]:
    info = Path(path).lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValueError("declared input root must be a non-symlink directory")
    return {"role": role, "path": str(Path(os.path.abspath(path))),
            "device": info.st_dev, "inode": info.st_ino, "mtime_ns": info.st_mtime_ns}


def _post_identity(app_root: Path, journal_dir: Path, strategy_path: Path,
                   expected_sources: dict[str, bytes], capture_id: str) -> dict[str, Any]:
    current_sources = _app_source_bytes(app_root)
    if current_sources != expected_sources:
        raise ValueError("application source changed during the report invocation")
    return {"schema": SCHEMA + ".input-identity", "capture_id": capture_id,
            "captured_utc": utc(),
            "roots": [_directory_identity(journal_dir, "journal-directory"),
                      _directory_identity(strategy_path, "strategy-store-directory")],
            "files": declared_inputs(journal_dir, strategy_path),
            "application_source_sha256": {name: sha256(raw)
                                           for name, raw in current_sources.items()}}


def _journal_inputs_unchanged(request: dict, post_identity: dict) -> bool:
    pre_root = next(row for row in request["input_roots"]
                    if row["role"] == "journal-directory")
    post_root = next(row for row in post_identity["roots"]
                     if row["role"] == "journal-directory")
    pre_files = [row for row in request["declared_inputs"]
                 if row["role"].startswith("journal-shard-")]
    post_files = [row for row in post_identity["files"]
                  if row["role"].startswith("journal-shard-")]
    return pre_root == post_root and pre_files == post_files


def _app_source_bytes(app_root: Path) -> dict[str, bytes]:
    app_root = app_root.resolve(strict=True)
    sources = {}
    for artifact, relpath in SOURCE_FILES.items():
        raw = _regular_bytes(app_root / relpath, MAX_SOURCE_BYTES)
        if sha256(raw) != TRUSTED_APP_SOURCES[artifact]:
            raise ValueError("application report source differs from the reviewed source pin")
        sources[artifact] = raw
    return sources


def capture_report(*, app_root: Path, journal_dir: Path, strategy_path: Path,
                   output_root: Path, write_missing: bool = False,
                   allow_hash_fallback: bool = False, capture: bool = False,
                   strict: bool = True) -> Path:
    """Run the pinned CLI once after sealing its pre-call request and source snapshots."""
    if capture is not True:
        raise ValueError("strategy report capture requires capture=True")
    if type(write_missing) is not bool or type(allow_hash_fallback) is not bool or strict is not True:
        raise ValueError("capture requires literal mode booleans and the strict CLI exit contract")
    app_root = Path(app_root).resolve(strict=True)
    journal_dir_arg, strategy_path_arg = Path(journal_dir).expanduser(), Path(strategy_path).expanduser()
    if journal_dir_arg.is_symlink() or strategy_path_arg.is_symlink():
        raise ValueError("journal and strategy input roots cannot be symlinks")
    journal_dir = journal_dir_arg.resolve(strict=True)
    strategy_path = strategy_path_arg.resolve(strict=True)
    source_bytes = _app_source_bytes(app_root)
    input_identities = declared_inputs(journal_dir, strategy_path)
    producer_bytes = _regular_bytes(Path(__file__).resolve(), MAX_SOURCE_BYTES)
    capture_id = uuid.uuid4().hex
    run_dir = _new_run_dir(Path(output_root), capture_id)
    source_refs = {name: _write_exclusive(run_dir / name, raw)
                   for name, raw in source_bytes.items()}
    producer_ref = _write_exclusive(run_dir / "producer-source.bin", producer_bytes)
    started = utc()
    request = {"schema": REQUEST_SCHEMA, "capture_id": capture_id,
               "started_utc": started, "producer_source": producer_ref,
               "applicability": "captured_cli",
               "application_root": str(app_root), "application_sources": source_refs,
               "input_roots": [_directory_identity(journal_dir, "journal-directory"),
                               _directory_identity(strategy_path, "strategy-store-directory")],
               "declared_inputs": input_identities,
               "mode": {"write_missing": write_missing,
                        "allow_hash_fallback": allow_hash_fallback,
                        "strict": strict}, "integrity_proposition": PROPOSITION,
               "input_claim": "hash_only_declared_identity_no_transitive_completeness",
               "exclusions": ["transitive dependency completeness", "environment contents",
                              "embedding quality", "historical pre-hook output",
                              "whole-host health", "immutable SQLite snapshot",
                              "auxiliary StrategyStore temporary-file cleanup"]}
    # Request bytes are durably written before any application module import or call.
    request_ref = _write_exclusive(run_dir / "execution-request.json", canonical(request) + b"\n")
    original_sys_path, original_meta_path = list(sys.path), list(sys.meta_path)
    initial_modules = set(sys.modules)
    stdout_io, stderr_io = io.StringIO(), io.StringIO()
    execution_started = False
    exit_code = None
    exception_type = None
    report_ok = None
    proposition = None
    markdown = b""
    stdout = stderr = b""
    ended = started
    post_identity = None
    post_identity_error = None
    module = None
    try:
        forbidden_cached = ("src", "src.inference_lock", "src.autopilot_core",
                            "src.autopilot_core.tier_specs", "orchestration",
                            "orchestration.repl_memory",
                            "orchestration.repl_memory.strategy_store",
                            "orchestration.repl_memory.faiss_store",
                            "orchestration.repl_memory.embedder",
                            "orchestration.repl_memory.memory_record", "scripts.autopilot",
                            "scripts.autopilot.journal_shards", "strategy_projection_report",
                            "experiment_journal", "journal_shards")
        if any(name in sys.modules for name in forbidden_cached):
            raise ValueError("application package was already cached before the pre-bound invocation")
        sys.path.insert(0, str(app_root / "scripts" / "autopilot"))
        sys.path.insert(0, str(app_root))
        execution_started = True
        with redirect_stdout(stdout_io), redirect_stderr(stderr_io):
            module = importlib.import_module("strategy_projection_report")
            _verify_runtime_sources(app_root, source_bytes)
            argv = ["--journal-dir", str(journal_dir), "--strategy-path", str(strategy_path),
                    "--strict", "--json"]
            if write_missing:
                argv.append("--write-missing")
            if allow_hash_fallback:
                argv.append("--allow-hash-fallback")
            exit_code = module.main(argv)
            stdout = stdout_io.getvalue().encode("utf-8", "surrogatepass")
            stderr = stderr_io.getvalue().encode("utf-8", "surrogatepass")
            if not stdout.endswith(b"\n") or b"\n" in stdout[:-1]:
                raise ValueError("original CLI stdout is not exactly one JSON line")
            report = _strict_json(stdout[:-1])
            if not isinstance(report, dict) or type(report.get("ok")) is not bool:
                raise ValueError("original CLI JSON lacks a strict boolean report.ok")
            report_ok = report["ok"]
            proposition = PROPOSITION
            markdown = module.render_markdown(report).encode("utf-8")
            _verify_runtime_sources(app_root, source_bytes, include_store=True)
    except Exception as exc:  # retain one original terminal; never rerun
        # The actual return status is retained separately if the CLI returned before
        # a later custody/parsing/rendering failure.
        exception_type = type(exc).__name__
        if not stdout:
            stdout = stdout_io.getvalue().encode("utf-8", "surrogatepass")
        if not stderr:
            stderr = stderr_io.getvalue().encode("utf-8", "surrogatepass")
        if report_ok is None:
            proposition = None
    finally:
        ended = utc()
        try:
            post_identity = _post_identity(app_root, journal_dir, strategy_path,
                                           source_bytes, capture_id)
            if not _journal_inputs_unchanged(request, post_identity):
                post_identity_error = "DeclaredJournalDrift"
        except Exception as exc:
            post_identity_error = type(exc).__name__
        sys.path[:] = original_sys_path
        sys.meta_path[:] = original_meta_path
        for name in set(sys.modules) - initial_modules:
            if (name in {"strategy_projection_report", "experiment_journal", "journal_shards"}
                    or name.startswith(("orchestration", "src", "scripts.autopilot"))):
                sys.modules.pop(name, None)
    custody_complete = post_identity is not None and post_identity_error is None
    capture_complete = (custody_complete and report_ok is not None and bool(markdown)
                        and exception_type is None
                        and exit_code == (0 if report_ok else 1))
    terminal = {"schema": SCHEMA + ".terminal", "capture_id": capture_id,
                "started_utc": started, "ended_utc": ended,
                "execution_started": execution_started, "exit_code": exit_code,
                "exception_type": exception_type, "custody_complete": custody_complete,
                "capture_complete": capture_complete,
                "post_identity_error": post_identity_error}
    refs = {"stdout": _write_exclusive(run_dir / "stdout.bin", stdout),
            "stderr": _write_exclusive(run_dir / "stderr.bin", stderr),
            "terminal": _write_exclusive(run_dir / "terminal.json", canonical(terminal) + b"\n")}
    if markdown:
        refs["report_markdown"] = _write_exclusive(run_dir / "report-markdown.bin", markdown)
    if post_identity is not None:
        refs["post_input_identity"] = _write_exclusive(
            run_dir / "post-input-identity.json", canonical(post_identity) + b"\n")
    record = {"schema": SCHEMA, "capture_id": capture_id, "applicability": "captured_cli",
              "started_utc": started, "ended_utc": ended,
              "execution_started": execution_started, "exit_code": exit_code,
              "exception_type": exception_type, "report_ok": report_ok,
              "integrity_proposition": proposition,
              "custody_complete": custody_complete, "capture_complete": capture_complete,
              "post_identity_error": post_identity_error,
              "request": request_ref, "stdout": refs["stdout"], "stderr": refs["stderr"],
              "report_markdown": refs.get("report_markdown"),
              "terminal": refs["terminal"],
              "post_input_identity": refs.get("post_input_identity")}
    record["receipt_sha256"] = sha256(canonical(record))
    receipt = run_dir / "receipt.json"
    _write_exclusive(receipt, canonical(record) + b"\n")
    return receipt


def _strict_json(raw: bytes) -> Any:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON member")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _x: (_ for _ in ()).throw(
        ValueError("non-finite JSON value")))


def _verify_runtime_sources(app_root: Path, source_bytes: dict[str, bytes], *,
                            include_store: bool = False) -> None:
    expected = {"strategy_projection_report": ("report-source.bin", "scripts/autopilot/strategy_projection_report.py"),
                "experiment_journal": ("journal-source.bin", "scripts/autopilot/experiment_journal.py"),
                "orchestration.repl_memory.strategy_store": ("store-source.bin", "orchestration/repl_memory/strategy_store.py"),
                "orchestration.repl_memory.faiss_store": ("faiss-source.bin", "orchestration/repl_memory/faiss_store.py"),
                "orchestration.repl_memory.embedder": ("embedder-source.bin", "orchestration/repl_memory/embedder.py"),
                "orchestration.repl_memory.memory_record": ("memory-record-source.bin", "orchestration/repl_memory/memory_record.py"),
                "src": ("src-package-source.bin", "src/__init__.py"),
                "src.inference_lock": ("lock-runtime-source.bin", "src/runtime/inference_lock.py"),
                "src.autopilot_core.tier_specs": ("tier-spec-source.bin", "src/autopilot_core/tier_specs.py")}
    lazy_store_modules = {
        "orchestration.repl_memory.strategy_store",
        "orchestration.repl_memory.faiss_store",
        "orchestration.repl_memory.embedder",
        "orchestration.repl_memory.memory_record",
    }
    for name, (artifact, relpath) in expected.items():
        if name in lazy_store_modules and not include_store:
            continue
        module = sys.modules.get(name)
        if module is None:
            if name == "orchestration.repl_memory.embedder" and module is None:
                # The report imports this on StrategyStore construction; absence means the
                # intended report path was not reached, so source custody is incomplete.
                raise ValueError("runtime embedder module was not loaded")
            raise ValueError("required runtime module was not loaded")
        origin = getattr(module, "__file__", None)
        expected_path = (app_root / relpath).resolve(strict=True)
        if not isinstance(origin, str) or Path(origin).resolve(strict=True) != expected_path:
            raise ValueError("runtime module came from a different application checkout")
        actual = _regular_bytes(expected_path, MAX_SOURCE_BYTES)
        if actual != source_bytes[artifact] or sha256(actual) != TRUSTED_APP_SOURCES[artifact]:
            raise ValueError("runtime module source differs from its pre-call trusted snapshot")
    shard_module = (sys.modules.get("scripts.autopilot.journal_shards")
                    or sys.modules.get("journal_shards"))
    if shard_module is None:
        raise ValueError("required journal shard module was not loaded")
    shard_origin = getattr(shard_module, "__file__", None)
    shard_path = (app_root / "scripts/autopilot/journal_shards.py").resolve(strict=True)
    shard_raw = _regular_bytes(shard_path, MAX_SOURCE_BYTES)
    if (not isinstance(shard_origin, str) or Path(shard_origin).resolve(strict=True) != shard_path
            or shard_raw != source_bytes["shards-source.bin"]):
        raise ValueError("journal shard module differs from its pre-call trusted snapshot")
