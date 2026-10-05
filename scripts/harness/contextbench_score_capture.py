#!/usr/bin/env python3
"""Explicit private pre-request capture for a deterministic ContextBench score invocation.

This producer accepts already-created task, prediction, disposition, and dataset files. It
does no checkout, discovery, search, model inference, or benchmark-arm execution. The request
and immutable input/source copies are written before importing and calling the scorer.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any
import uuid

SCHEMA = "epyc.contextbench_score_capture.v1"
REQUEST_SCHEMA = "epyc.contextbench_score_request.v1"
MAX_INPUT_BYTES = 512 * 1024 * 1024
MAX_SOURCE_BYTES = 4 * 1024 * 1024
ARTIFACT_LIMITS = {
    "dataset.bin": MAX_INPUT_BYTES,
    "tasks.jsonl": MAX_INPUT_BYTES,
    "predictions.jsonl": MAX_INPUT_BYTES,
    "dispositions.json": MAX_INPUT_BYTES,
    "scorer-source.bin": MAX_SOURCE_BYTES,
    "packer-source.bin": MAX_SOURCE_BYTES,
    "src-package-source.bin": MAX_SOURCE_BYTES,
    "producer-source.bin": MAX_SOURCE_BYTES,
    "scored-output.json": MAX_INPUT_BYTES,
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def regular_bytes(path: Path, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"input is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        if len(raw) > limit:
            raise ValueError(f"input exceeds the capture limit: {path}")
        return raw
    finally:
        os.close(fd)


def _write_exclusive(path: Path, raw: bytes, *, mode: int = 0o600) -> dict[str, Any]:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.fchmod(fd, 0o400)
    finally:
        os.close(fd)
    return {"name": path.name, "sha256": sha256(raw), "size": len(raw)}


def _private_run_dir(path: Path, capture_id: str) -> Path:
    root = Path(os.path.abspath(path))
    _check_custody_chain(root)
    created = root.lstat()
    if (not stat.S_ISDIR(created.st_mode) or created.st_uid != os.geteuid()
            or stat.S_IMODE(created.st_mode) != 0o700):
        raise ValueError("capture output root must already be an owned private directory")
    target = root / capture_id
    if os.path.lexists(target):
        raise ValueError("capture UUID directory already exists; overwrite is refused")
    target.mkdir(mode=0o700)
    created = target.lstat()
    if not stat.S_ISDIR(created.st_mode) or created.st_uid != os.geteuid() or stat.S_IMODE(created.st_mode) != 0o700:
        raise ValueError("capture output directory is not private")
    return target


def _check_custody_chain(path: Path) -> None:
    """Reject symlinked or writable ancestors before creating/opening private custody."""
    absolute = Path(os.path.abspath(path))
    for candidate in (Path("/"), *absolute.parents[::-1], absolute):
        try:
            info = candidate.lstat()
        except FileNotFoundError as exc:
            raise ValueError("capture custody ancestor does not exist") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("capture custody chain contains a symlink or non-directory")
        if info.st_uid not in (0, os.geteuid()):
            raise ValueError("capture custody ancestor has an untrusted owner")
        writable = stat.S_IMODE(info.st_mode) & 0o022
        sticky_trusted = bool(info.st_mode & stat.S_ISVTX) and info.st_uid == 0
        if writable and not sticky_trusted:
            raise ValueError("capture custody ancestor is group/world writable")


def _git(app_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(app_root), *args],
                                   text=True, stderr=subprocess.PIPE).strip()


def app_identity(app_root: Path) -> dict[str, Any]:
    root = app_root.resolve(strict=True)
    revision = _git(root, "rev-parse", "HEAD")
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("application checkout has an invalid HEAD")
    if _git(root, "status", "--porcelain"):
        raise ValueError("application checkout has tracked or untracked modifications")
    return {"root": str(root), "revision": revision, "tracked_clean": True}


def _verify_runtime_sources(expected: dict[str, tuple[Path, str, Any]]) -> None:
    for module_name, (source_path, expected_sha, module) in expected.items():
        if module is None or sys.modules.get(module_name) is not module:
            raise ValueError(f"runtime module {module_name} is absent or changed")
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str) or Path(origin).resolve(strict=True) != source_path.resolve(strict=True):
            raise ValueError(f"runtime module {module_name} came from a different application checkout")
        if sha256(regular_bytes(Path(origin), MAX_SOURCE_BYTES)) != expected_sha:
            raise ValueError(f"runtime module {module_name} source bytes drifted from the pre-request snapshot")


def _artifact_copy(run_dir: Path, source: Path, leaf: str, *, limit: int) -> dict[str, Any]:
    raw = regular_bytes(source, limit)
    return _write_exclusive(run_dir / leaf, raw)


def capture_score(*, dataset: Path, task_rows: Path, predictions: Path,
                  dispositions: Path, app_root: Path, output: Path,
                  dataset_label: str, applicability: str, arms: list[str],
                  capture: bool = False) -> Path:
    """Bind exact input bytes before invoking the reviewed scorer module."""
    if capture is not True:
        raise ValueError("score capture requires the explicit capture=True opt-in")
    if (not isinstance(dataset_label, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", dataset_label)
            or applicability not in {"synthetic_fixture", "local_precomputed_inputs"}
            or not arms or any(not isinstance(arm, str) or not arm for arm in arms)):
        raise ValueError("a bounded dataset label, explicit applicability, and declared arm names are required")
    if len(set(arms)) != len(arms):
        raise ValueError("duplicate arm name")
    app = app_identity(app_root)
    app_root = Path(app["root"])
    source_paths = {
        "scorer-source.bin": app_root / "src" / "contextbench_score.py",
        "packer-source.bin": app_root / "src" / "context_assembly.py",
        "src-package-source.bin": app_root / "src" / "__init__.py",
    }
    input_paths = {
        "dataset.bin": dataset,
        "tasks.jsonl": task_rows,
        "predictions.jsonl": predictions,
        "dispositions.json": dispositions,
    }
    # Read all inputs and code identities before creating the run; no input is reread after
    # capture, so later source-path changes cannot alter this invocation.
    source_bytes = {name: regular_bytes(path, MAX_SOURCE_BYTES)
                    for name, path in source_paths.items()}
    input_bytes = {name: regular_bytes(path, ARTIFACT_LIMITS[name])
                   for name, path in input_paths.items()}
    producer_path = Path(__file__).resolve()
    producer_bytes = regular_bytes(producer_path, MAX_SOURCE_BYTES)
    app["scorer_sha256"] = sha256(source_bytes["scorer-source.bin"])
    app["packer_sha256"] = sha256(source_bytes["packer-source.bin"])
    app["package_sha256"] = sha256(source_bytes["src-package-source.bin"])
    capture_id = uuid.uuid4().hex
    run_dir = _private_run_dir(output, capture_id)
    refs: dict[str, dict[str, Any]] = {}
    for name, raw in input_bytes.items():
        refs[name] = _write_exclusive(run_dir / name, raw)
    for name, raw in source_bytes.items():
        refs[name] = _write_exclusive(run_dir / name, raw)
    refs["producer-source.bin"] = _write_exclusive(run_dir / "producer-source.bin", producer_bytes)
    started = utc()
    request = {
        "schema": REQUEST_SCHEMA,
        "producer_id": "scripts/harness/contextbench_score_capture.py/v1",
        "capture_id": capture_id,
        "started_utc": started,
        "dataset": {"label": dataset_label, "artifact": refs["dataset.bin"]},
        "applicability": applicability,
        "task_rows": refs["tasks.jsonl"],
        "predictions": refs["predictions.jsonl"],
        "dispositions": refs["dispositions.json"],
        "application": app,
        "producer_source": refs["producer-source.bin"],
        "arms": list(arms),
        "metric_contract": {
            "schema": "epyc.contextbench_discovery_score.v1",
            "average": "macro_per_task",
            "direction": "higher_better",
            "budget_values": [2000, 4000, 8000],
            "integrity_proposition": (
                "The offline ContextBench score artifact is complete and internally consistent "
                "for applicability={applicability}; no discovery quality is asserted."
            ),
        },
        "environment": "not captured",
    }
    request_bytes = canonical(request)
    request_ref = _write_exclusive(run_dir / "execution-request.json", request_bytes)
    started_import = False
    ended = started
    status = "diagnostic"
    diagnostic_code = ""
    score_ref = None
    output_path = run_dir / "scored-output.json"
    output_write_started = False
    original_sys_path = list(sys.path)
    original_meta_path = list(sys.meta_path)
    original_src_modules = {name: module for name, module in sys.modules.items()
                            if name == "src" or name.startswith("src.")}
    try:
        # The reviewed app checkout is imported only after its source snapshot and request
        # are sealed. The reader never imports or executes these captured bytes.
        if any(name == "src" or name.startswith("src.") for name in sys.modules):
            raise ValueError("src package or scorer/packer module was already cached before this capture")
        app_root_resolved = app_root.resolve(strict=True)
        sys.path.insert(0, str(app_root_resolved))
        started_import = True
        scorer = importlib.import_module("src.contextbench_score")
        packer = sys.modules.get("src.context_assembly")
        expected_sources = {
            "src.contextbench_score": (app_root_resolved / "src" / "contextbench_score.py",
                                       sha256(source_bytes["scorer-source.bin"]), scorer),
            "src.context_assembly": (app_root_resolved / "src" / "context_assembly.py",
                                     sha256(source_bytes["packer-source.bin"]), packer),
            "src": (app_root_resolved / "src" / "__init__.py",
                    sha256(source_bytes["src-package-source.bin"]), sys.modules.get("src")),
        }
        _verify_runtime_sources(expected_sources)
        scored = scorer.score_contextbench_bytes(
            input_bytes["tasks.jsonl"], input_bytes["predictions.jsonl"],
            input_bytes["dispositions.json"], declared_arms=arms,
        )
        _verify_runtime_sources(expected_sources)
        output_bytes = canonical(scored) + b"\n"
        output_write_started = True
        score_ref = _write_exclusive(output_path, output_bytes)
        status = "scored"
    except Exception as exc:
        if output_write_started and os.path.lexists(output_path):
            output_path.unlink()
        score_ref = None
        diagnostic_code = type(exc).__name__
    finally:
        sys.path[:] = original_sys_path
        sys.meta_path[:] = original_meta_path
        for module_name in tuple(sys.modules):
            if ((module_name == "src" or module_name.startswith("src."))
                    and module_name not in original_src_modules):
                sys.modules.pop(module_name, None)
    ended = utc()
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "status": status,
        "diagnostic_code": diagnostic_code,
        "scorer_import_started": started_import,
        "started_utc": started,
        "ended_utc": ended,
        "request": request_ref,
        "artifacts": refs,
        "scored_output": score_ref,
        "integrity_result": True if status == "scored" else None,
        "integrity_proposition": (
            request["metric_contract"]["integrity_proposition"].format(
                applicability=request["applicability"])
            if status == "scored" else None
        ),
    }
    record["receipt_sha256"] = sha256(canonical(record))
    _write_exclusive(run_dir / "receipt.json", canonical(record) + b"\n")
    return run_dir / "receipt.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", required=True,
                        help="required explicit opt-in to create a private score capture")
    parser.add_argument("--dataset", type=Path, required=True,
                        help="local dataset bytes; no official release identity is inferred")
    parser.add_argument("--dataset-label", required=True,
                        help="bounded caller-declared label, bound to captured artifact SHA-256")
    parser.add_argument("--applicability", required=True,
                        choices=("synthetic_fixture", "local_precomputed_inputs"),
                        help="explicitly labels synthetic fixtures or locally precomputed inputs")
    parser.add_argument("--task-rows", type=Path, required=True, help="minimized selected task JSONL")
    parser.add_argument("--predictions", type=Path, required=True, help="per-task/per-arm discovery JSONL")
    parser.add_argument("--dispositions", type=Path, required=True, help="explicit complete disposition JSON")
    parser.add_argument("--app-root", type=Path, required=True, help="clean pinned epyc-orchestrator checkout")
    parser.add_argument("--output", type=Path, required=True,
                        help="existing dedicated owned-private root for UUID-named capture directories")
    parser.add_argument("--arms-json", required=True, help="JSON array naming the exact arm set")
    args = parser.parse_args(argv)
    try:
        arms = json.loads(args.arms_json)
        if not isinstance(arms, list):
            raise ValueError("--arms-json must decode to a list")
        receipt = capture_score(dataset=args.dataset, task_rows=args.task_rows,
            predictions=args.predictions, dispositions=args.dispositions,
            app_root=args.app_root, output=args.output, dataset_label=args.dataset_label,
            applicability=args.applicability, arms=arms, capture=args.capture)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"contextbench score capture refused: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(str(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
