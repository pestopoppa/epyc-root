#!/usr/bin/env python3
"""Opt-in, read-only capture for the production kernel-store verifier.

This writes dependency evidence only. It never emits a ClaimTuple and never
starts a server or benchmark. Ordinary session initialization does not invoke it.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
import uuid
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KERNEL_ROOT = Path("/mnt/raid0/llm/kernels")
DEFAULT_RESOLVER = Path("/mnt/raid0/llm/epyc-orchestrator/src/registry/kernel_paths.py")
DEFAULT_LINKAGE = Path("/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
VERIFIER = ROOT / "scripts/session/verify_kernel_store.sh"
CAPTURE_MARKER = b"__NI28_LINKAGE_CAPTURE_V1__\t"
SAFE_RUN_ID = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")


class ReceiptError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _stat_identity(path: Path, *, follow_symlinks: bool) -> dict[str, int]:
    info = path.stat() if follow_symlinks else path.lstat()
    return {"device": info.st_dev, "inode": info.st_ino, "mode": stat.S_IMODE(info.st_mode),
            "size": info.st_size, "mtime_ns": info.st_mtime_ns}


def _load_resolver(path: Path, rocm_path: str) -> dict[str, Any]:
    if not path.is_file() or not os.access(path, os.R_OK):
        raise ReceiptError(f"resolver is missing or unreadable: {path}")
    name = "_ni28_kernel_paths_capture"
    module = type(sys)(name)
    module.__file__ = str(path)
    saved_env = dict(os.environ)
    try:
        os.environ.clear()
        if rocm_path:
            os.environ["ROCM_PATH"] = rocm_path
        source = path.read_bytes()
        exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)
    except Exception as exc:
        raise ReceiptError(f"resolver import failed: {exc}") from exc
    finally:
        os.environ.clear()
        os.environ.update(saved_env)
    binaries = getattr(module, "BACKEND_BINARIES", None)
    if not isinstance(binaries, dict) or not binaries:
        raise ReceiptError("resolver declares an empty or invalid BACKEND_BINARIES map")
    no_prepend = getattr(module, "_BACKENDS_NEEDING_NO_PREPEND", frozenset())
    vendor_dirs = getattr(module, "BACKEND_VENDOR_LIB_DIRS", {})
    rows = []
    for backend in sorted(binaries):
        binary_name = binaries[backend]
        vendors = vendor_dirs.get(backend, ())
        if not isinstance(backend, str) or not backend or not isinstance(binary_name, str) \
                or not binary_name or any(ch in backend + binary_name for ch in "\t\r\n"):
            raise ReceiptError("resolver has an invalid backend or binary name")
        vendor_values = [str(item) for item in vendors]
        if any(not item or any(ch in item for ch in "\t\r\n") for item in vendor_values):
            raise ReceiptError(f"resolver has invalid vendor directories for {backend}")
        rows.append({"backend": backend, "binary_name": binary_name,
                     "needs_prepend": backend not in no_prepend,
                     "vendor_dirs": vendor_values})
    return {"rows": rows, "resolver_sha256": sha256_file(path)}


def _backend_snapshot(kernel_root: Path, row: dict[str, Any], ambient_ld: str) -> dict[str, Any]:
    backend = row["backend"]
    link = kernel_root / "production" / backend
    if not link.is_symlink():
        raise ReceiptError(f"production backend path is not a symlink: {link}")
    raw_target = os.readlink(link)
    target = link.resolve(strict=True)
    if not target.is_dir():
        raise ReceiptError(f"production backend target is not a directory: {target}")
    binary = target / row["binary_name"]
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ReceiptError(f"backend executable missing or not executable: {binary}")
    actual_ld = ambient_ld
    if row["needs_prepend"]:
        prefix = [str(target), *row["vendor_dirs"]]
        actual_ld = ":".join([*prefix, ambient_ld]) if ambient_ld else ":".join(prefix)
    search_dirs = [str(target), *row["vendor_dirs"],
                   *(part for part in actual_ld.split(":") if part)]
    library_candidates = {}
    for directory in dict.fromkeys(search_dirs):
        root = Path(directory)
        if not root.is_dir():
            continue
        for pattern in ("libggml*", "libwhisper*", "libllama*", "libmtmd*", "libparakeet*"):
            for candidate in root.glob(pattern):
                try:
                    resolved = candidate.resolve(strict=True)
                    if not resolved.is_file():
                        continue
                    library_candidates[str(candidate)] = {
                        "path": str(candidate), "realpath": str(resolved),
                        "sha256": sha256_file(resolved),
                        "symlink_target_text": os.readlink(candidate) if candidate.is_symlink() else None,
                        "path_lstat": _stat_identity(candidate, follow_symlinks=False),
                        "resolved_stat": _stat_identity(resolved, follow_symlinks=True),
                    }
                except OSError:
                    # An uninspectable candidate stays absent; a verifier row that
                    # resolves there will become an explicit unknown below.
                    continue
    return {
        **row,
        "link_path": str(link),
        "symlink_target_text": raw_target,
        "symlink_lstat": _stat_identity(link, follow_symlinks=False),
        "target_path": str(target),
        "target_stat": _stat_identity(target, follow_symlinks=True),
        "binary_path": str(binary),
        "binary_sha256": sha256_file(binary),
        "binary_stat": _stat_identity(binary, follow_symlinks=True),
        "launch_ld_library_path": actual_ld,
        "ambient_ld_library_path": ambient_ld,
        "library_candidates": [library_candidates[key] for key in sorted(library_candidates)],
    }


def _source_snapshot(producer: Path, verifier: Path, resolver: Path, linkage: Path) -> list[dict[str, str]]:
    values = (("producer", producer), ("store_verifier", verifier),
              ("resolver", resolver), ("linkage_verifier", linkage))
    result = []
    for role, path in values:
        if not path.is_file() or not os.access(path, os.R_OK):
            raise ReceiptError(f"{role} source is missing or unreadable: {path}")
        result.append({"role": role, "path": str(path.resolve()),
                       "sha256": sha256_file(path), "size": path.stat().st_size})
    return result


def _write_exclusive(path: Path, value: Any) -> str:
    raw = canonical_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return sha256_bytes(raw)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _live_owned_group_pids(pgid: int) -> list[int]:
    """Return live members of this newly-created child process group."""
    live = []
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            raw = stat_path.read_text()
            tail = raw[raw.rfind(")") + 2:].split()
            # After comm, fields start with state (3), ppid (4), pgrp (5).
            if len(tail) >= 3 and int(tail[2]) == pgid and tail[0] != "Z":
                live.append(int(stat_path.parent.name))
        except (OSError, ValueError):
            continue
    return live


def _wait_owned_group_empty(pgid: int, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not _live_owned_group_pids(pgid):
            return True
        time.sleep(0.05)
    return not _live_owned_group_pids(pgid)


def _stop_owned_group(child: subprocess.Popen[bytes], *, grace: float = 1.0
                      ) -> tuple[bytes, bytes, bool]:
    """TERM then KILL only the process group created for this invocation."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    stdout = stderr = b""
    try:
        stdout, stderr = child.communicate(timeout=grace)
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
    if not _wait_owned_group_empty(child.pid, grace):
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = child.communicate(timeout=grace)
        except subprocess.TimeoutExpired as exc:
            stdout = stdout or exc.stdout or b""
            stderr = stderr or exc.stderr or b""
    empty = _wait_owned_group_empty(child.pid, grace)
    try:
        child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            empty = False
    for pipe in (child.stdout, child.stderr):
        if pipe is not None:
            pipe.close()
    return stdout, stderr, empty and child.poll() is not None


def _decode_capture_line(line: bytes) -> dict[str, Any] | None:
    if not line.startswith(CAPTURE_MARKER):
        return None
    fields = line.rstrip(b"\r\n").split(b"\t")
    if len(fields) != 8 or fields[0] != CAPTURE_MARKER.rstrip(b"\t"):
        raise ReceiptError("malformed NI28 child-capture marker")
    try:
        backend, phase = fields[1].decode("ascii"), fields[2].decode("ascii")
        status = int(fields[3])
        binary, target, ldpath, output = (base64.b64decode(item, validate=True) for item in fields[4:])
        return {"backend": backend, "phase": phase, "exit_code": status,
                "argv": ["bash", "<bound-linkage-verifier>", binary.decode("utf-8"),
                         target.decode("utf-8")],
                "binary_path": binary.decode("utf-8"), "target_path": target.decode("utf-8"),
                "ld_library_path": ldpath.decode("utf-8"),
                "combined_output_b64": base64.b64encode(output).decode("ascii"),
                "combined_output_sha256": sha256_bytes(output)}
    except (ValueError, UnicodeDecodeError) as exc:
        raise ReceiptError(f"invalid NI28 child-capture marker: {exc}") from exc


def _expected_phases(backends: list[dict[str, Any]]) -> list[tuple[str, str]]:
    expected = []
    for row in backends:
        expected.append((row["backend"], "launch"))
        if row["needs_prepend"]:
            expected.append((row["backend"], "ambient"))
    return expected


def _check_child_records(request: dict[str, Any], records: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    ambient_notes: list[str] = []
    expected_map = {row["backend"]: row for row in request["backends"]}
    expected_phases = set(_expected_phases(request["backends"]))
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (record["backend"], record["phase"])
        if key in seen:
            problems.append(f"duplicate child record: {key}")
        seen.add(key)
        row = expected_map.get(record["backend"])
        if row is None or key not in expected_phases:
            problems.append(f"unexpected child record: {key}")
            continue
        expected_ld = (row["launch_ld_library_path"] if record["phase"] == "launch"
                       else row["ambient_ld_library_path"])
        note = ambient_notes if record["phase"] == "ambient" else problems
        if record["binary_path"] != row["binary_path"] or record["target_path"] != row["target_path"]:
            note.append(f"child binary/target identity differs from request: {key}")
        if record["ld_library_path"] != expected_ld:
            note.append(f"child loader environment differs from request: {key}")
        raw = base64.b64decode(record["combined_output_b64"], validate=True).decode("utf-8", "replace")
        candidate_by_realpath = {item["realpath"]: item["sha256"]
                                 for item in row["library_candidates"]}
        resolved_libraries = []
        for match in re.finditer(
                r"^\s+(OK|BAD)\s+(\S+)\s+->\s+(\S+)\s*$", raw, re.MULTILINE):
            state, soname, libpath = match.groups()
            realpath = os.path.realpath(libpath)
            digest = candidate_by_realpath.get(realpath)
            resolved_libraries.append({"status": state, "soname": soname,
                                       "path": libpath, "realpath": realpath,
                                       "sha256": digest})
            if digest is None:
                note.append(f"resolved library lacks pre-execution digest: {key} {realpath}")
            if record["phase"] == "launch" and not Path(realpath).is_relative_to(
                    Path(row["target_path"])):
                problems.append(f"launch library resolves outside its backend target: {key} {realpath}")
        if "resolved_libraries" in record and record["resolved_libraries"] != resolved_libraries:
            note.append(f"resolved library digest rows differ from original output: {key}")
        record["resolved_libraries"] = resolved_libraries
        if record["phase"] == "launch":
            if record["exit_code"] != 0 or "PASS:" not in raw or "FAIL:" in raw:
                problems.append(f"launch linkage did not pass: {key} rc={record['exit_code']}")
            good_rows = re.findall(r"^\s+OK\s+lib(?:ggml|whisper|llama|mtmd|parakeet)[^\s]*\s+->\s+\S+",
                                   raw, re.MULTILINE)
            core_rows = re.findall(r"^\s+OK\s+libggml-base\.so[^\s]*\s+->\s+\S+",
                                   raw, re.MULTILINE)
            bad_rows = re.findall(r"^\s+BAD\s+lib(?:ggml|whisper|llama|mtmd|parakeet)[^\s]*\s+->\s+\S+",
                                  raw, re.MULTILINE)
            if not good_rows or len(core_rows) != 1 or bad_rows:
                problems.append(f"launch linkage was vacuous, had a bad row, or did not have exactly one libggml-base: {key}")
        elif record["exit_code"] != 0 or "PASS:" not in raw or "FAIL:" in raw:
            ambient_notes.append(f"ambient diagnostic failed: {key} rc={record['exit_code']}")
    launch_status = {(record["backend"], "launch"): record.get("exit_code")
                     for record in records if record.get("phase") == "launch"}
    for row in request["backends"]:
        launch_key = (row["backend"], "launch")
        if launch_key not in seen:
            problems.append(f"missing child capture: {launch_key}")
        elif row["needs_prepend"] and launch_status.get(launch_key) == 0:
            ambient_key = (row["backend"], "ambient")
            if ambient_key not in seen:
                problems.append(f"missing child capture: {ambient_key}")
    return problems, ambient_notes


def _run_env(args: argparse.Namespace, allowed: dict[str, str]) -> dict[str, str]:
    env = {"PATH": allowed["PATH"], "LD_LIBRARY_PATH": allowed["LD_LIBRARY_PATH"],
           "ROCM_PATH": allowed["ROCM_PATH"], "LANG": "C", "LC_ALL": "C",
           "KERNEL_STORE_ROOT": str(args.kernel_root),
           "KERNEL_STORE_CAPTURE_RESOLVER": str(args.resolver),
           "KERNEL_STORE_CAPTURE_LINKAGE_VERIFIER": str(args.linkage_verifier)}
    return env


def _make_request(args: argparse.Namespace, allowed: dict[str, str]) -> dict[str, Any]:
    root = args.kernel_root.resolve(strict=True)
    if not root.is_dir():
        raise ReceiptError(f"kernel store root is not a directory: {root}")
    resolver_info = _load_resolver(args.resolver, allowed["ROCM_PATH"])
    backends = [_backend_snapshot(root, row, allowed["LD_LIBRARY_PATH"])
                for row in resolver_info["rows"]]
    if not backends:
        raise ReceiptError("resolver produced an empty backend map")
    sources = _source_snapshot(Path(__file__).resolve(), VERIFIER, args.resolver,
                               args.linkage_verifier)
    map_bytes = canonical_bytes(resolver_info["rows"])
    return {
        "schema": "epyc.kernel_store_verification.request.v1",
        "created_utc": utc_now(),
        "kernel_root": str(root),
        "allowed_environment": allowed,
        "cwd": str(ROOT),
        "invocation_paths": {"resolver": str(args.resolver),
                             "linkage_verifier": str(args.linkage_verifier)},
        "sources": sources,
        "declared_backend_map": resolver_info["rows"],
        "declared_backend_map_sha256": sha256_bytes(map_bytes),
        "backends": backends,
        "possible_child_phases": [list(key) for key in _expected_phases(backends)],
        "synthetic_mode": bool(args.synthetic),
    }


def _write_refusal(run_dir: Path, exc: Exception, args: argparse.Namespace) -> None:
    refusal = {"schema": "epyc.kernel_store_verification.refusal.v1",
               "created_utc": utc_now(), "state": "pre_execution_refused",
               "reason": str(exc), "execution_started": False,
               "requested_kernel_root": str(args.kernel_root),
               "requested_resolver": str(args.resolver),
               "requested_linkage_verifier": str(args.linkage_verifier)}
    _write_exclusive(run_dir / "refusal.json", refusal)


def capture(args: argparse.Namespace) -> int:
    args.kernel_root = args.kernel_root.resolve()
    args.resolver = args.resolver.resolve()
    args.linkage_verifier = args.linkage_verifier.resolve()
    if not args.synthetic and (args.kernel_root != DEFAULT_KERNEL_ROOT
                               or args.resolver != DEFAULT_RESOLVER
                               or args.linkage_verifier != DEFAULT_LINKAGE):
        raise ReceiptError("path overrides require explicit --synthetic mode")
    receipt_root = args.receipt_root.resolve(strict=True)
    if not receipt_root.is_dir():
        raise ReceiptError(f"receipt root is not a directory: {receipt_root}")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_id = f"{stamp}-{uuid.uuid4().hex[:12]}"
    if not SAFE_RUN_ID.fullmatch(run_id):
        raise ReceiptError("generated receipt run id has an invalid shape")
    run_dir = receipt_root / run_id
    run_dir.mkdir(mode=0o700)
    _fsync_directory(receipt_root)
    allowed = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH", ""),
               "ROCM_PATH": os.environ.get("ROCM_PATH", "/opt/rocm")}
    try:
        request = _make_request(args, allowed)
    except Exception as exc:
        _write_refusal(run_dir, exc, args)
        os.chmod(run_dir, 0o500)
        _fsync_directory(run_dir)
        _fsync_directory(receipt_root)
        print(f"receipt={run_dir}")
        print(f"REFUSED before verifier execution: {exc}", file=sys.stderr)
        return 2
    request_hash = _write_exclusive(run_dir / "request.json", request)
    _fsync_directory(run_dir)
    env = _run_env(args, allowed)
    argv = ["/bin/bash", str(VERIFIER), "--capture-v1"]
    execution_started_utc = utc_now()
    cleanup_verified = False
    try:
        # Own a fresh process group so timeout cleanup reaches the verifier and
        # linkage-verifier descendants. The group id is this Popen child PID; it
        # is never selected by a name/pattern scan.
        child = subprocess.Popen(argv, cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = child.communicate(timeout=args.timeout)
            exit_code: int | None = child.returncode
            execution_error = None
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, cleanup_verified = _stop_owned_group(child)
            exit_code = None
            stdout = stdout or exc.stdout or b""
            stderr = stderr or exc.stderr or b""
            execution_error = "timeout"
        else:
            # communicate() can return after the outer shell closes its pipes
            # while a descendant remains alive. Check the owned group separately.
            if _live_owned_group_pids(child.pid):
                stdout, stderr, cleanup_verified = _stop_owned_group(child)
                execution_error = "orphaned_descendant_cleanup"
            else:
                cleanup_verified = child.poll() is not None
    except OSError as exc:
        exit_code = None
        stdout = b""
        stderr = str(exc).encode("utf-8", "replace")
        execution_error = f"execution_error:{exc.__class__.__name__}"
    child_records = []
    marker_errors = []
    for line in stdout.splitlines(keepends=True):
        if line.startswith(CAPTURE_MARKER):
            try:
                record = _decode_capture_line(line)
                if record is not None:
                    record["argv"][1] = str(args.linkage_verifier)
                    record["cwd"] = str(ROOT)
                    record["environment"] = {**env, "LD_LIBRARY_PATH": record["ld_library_path"]}
                    child_records.append(record)
            except ReceiptError as exc:
                marker_errors.append(str(exc))
    input_changed = []
    try:
        after = _make_request(args, allowed)
        if after["sources"] != request["sources"]:
            input_changed.append("source readset changed during execution")
        if after["declared_backend_map_sha256"] != request["declared_backend_map_sha256"]:
            input_changed.append("declared backend map changed during execution")
        if after["backends"] != request["backends"]:
            input_changed.append("store path/binary identities changed during execution")
    except Exception as exc:
        input_changed.append(f"post-execution readback failed: {exc}")
    child_problems, ambient_notes = _check_child_records(request, child_records)
    diagnostics = marker_errors + child_problems + input_changed
    if execution_error == "orphaned_descendant_cleanup":
        diagnostics.append("owned verifier descendant remained after outer exit and was terminated")
    if not cleanup_verified:
        diagnostics.append("owned verifier process group cleanup could not be verified")
    ok = exit_code == 0 and execution_error is None and not diagnostics
    capture_doc = {
        "schema": "epyc.kernel_store_verification.capture.v1",
        "run_id": run_id,
        "request_sha256": request_hash,
        "started_utc": execution_started_utc,
        "completed_utc": utc_now(),
        "outer_invocation": {"argv": argv, "cwd": str(ROOT), "environment": env,
                             "exit_code": exit_code, "execution_error": execution_error,
                             "owned_process_group_cleanup_verified": cleanup_verified,
                             "stdout_b64": base64.b64encode(stdout).decode("ascii"),
                             "stderr_b64": base64.b64encode(stderr).decode("ascii"),
                             "stdout_sha256": sha256_bytes(stdout),
                             "stderr_sha256": sha256_bytes(stderr)},
        "child_linkage_invocations": child_records,
        "diagnostics": diagnostics,
        "ambient_diagnostics": ambient_notes,
        "dependency_verification_passed": ok,
    }
    capture_hash = _write_exclusive(run_dir / "capture.json", capture_doc)
    receipt_body = {"schema": "epyc.kernel_store_verification.receipt.v1",
                    "run_id": run_id, "request_sha256": request_hash,
                    "capture_sha256": capture_hash,
                    "dependency_verification_passed": ok,
                    "diagnostics": diagnostics}
    receipt = {**receipt_body, "receipt_sha256": sha256_bytes(canonical_bytes(receipt_body))}
    _write_exclusive(run_dir / "receipt.json", receipt)
    os.chmod(run_dir, 0o500)
    _fsync_directory(run_dir)
    _fsync_directory(receipt_root)
    print(f"receipt={run_dir}")
    print(f"dependency_verification_passed={str(ok).lower()}")
    return 0 if ok else 1


def verify(run_dir: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    try:
        if not SAFE_RUN_ID.fullmatch(run_dir.name):
            raise ReceiptError("receipt directory has an invalid run id")
        if not (run_dir / "receipt.json").exists() and (run_dir / "refusal.json").is_file():
            refusal = json.loads((run_dir / "refusal.json").read_bytes())
            return False, [f"pre-execution refusal (no verifier run): {refusal.get('reason', 'unknown')}" ]
        request_raw = (run_dir / "request.json").read_bytes()
        capture_raw = (run_dir / "capture.json").read_bytes()
        receipt_raw = (run_dir / "receipt.json").read_bytes()
        request = json.loads(request_raw)
        capture_doc = json.loads(capture_raw)
        receipt = json.loads(receipt_raw)
    except (OSError, json.JSONDecodeError, ReceiptError) as exc:
        return False, [f"cannot read sealed receipt: {exc}"]
    if not all(isinstance(value, dict) for value in (request, capture_doc, receipt)):
        return False, ["request, capture, and receipt roots must be JSON objects"]
    request_hash, capture_hash = sha256_bytes(request_raw), sha256_bytes(capture_raw)
    if run_dir.stat().st_mode & 0o222:
        problems.append("receipt directory is writable; exclusive immutable storage was lost")
    for filename in ("request.json", "capture.json", "receipt.json"):
        if (run_dir / filename).stat().st_mode & 0o222:
            problems.append(f"sealed receipt component is writable: {filename}")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    if receipt.get("schema") != "epyc.kernel_store_verification.receipt.v1" \
            or receipt.get("receipt_sha256") != sha256_bytes(canonical_bytes(body)):
        problems.append("receipt seal is invalid")
    if receipt_raw != canonical_bytes(receipt):
        problems.append("receipt bytes are not in canonical immutable form")
    if request_raw != canonical_bytes(request):
        problems.append("request bytes are not in canonical immutable form")
    if capture_raw != canonical_bytes(capture_doc):
        problems.append("capture bytes are not in canonical immutable form")
    if receipt.get("request_sha256") != request_hash or capture_doc.get("request_sha256") != request_hash:
        problems.append("request digest binding is invalid")
    if receipt.get("capture_sha256") != capture_hash:
        problems.append("capture digest binding is invalid")
    if request.get("schema") != "epyc.kernel_store_verification.request.v1" \
            or capture_doc.get("schema") != "epyc.kernel_store_verification.capture.v1":
        problems.append("unsupported request/capture schema")
    declared_map = request.get("declared_backend_map")
    backend_rows = request.get("backends")
    if not isinstance(declared_map, list) or not declared_map \
            or not isinstance(backend_rows, list) or not backend_rows:
        problems.append("request backend map and backend snapshots must both be nonempty lists")
    elif request.get("declared_backend_map_sha256") != sha256_bytes(canonical_bytes(declared_map)):
        problems.append("declared backend map digest is invalid")
    else:
        try:
            map_names = [row["backend"] for row in declared_map]
            snapshot_names = [row["backend"] for row in backend_rows]
            if len(set(map_names)) != len(map_names) or len(set(snapshot_names)) != len(snapshot_names) \
                    or set(map_names) != set(snapshot_names):
                problems.append("declared map and backend snapshots lack exact unique coverage")
            map_by_name = {row["backend"]: row for row in declared_map}
            for row in backend_rows:
                spec = map_by_name.get(row.get("backend"), {})
                if any(row.get(field) != spec.get(field)
                       for field in ("backend", "binary_name", "needs_prepend", "vendor_dirs")):
                    problems.append(f"backend snapshot does not match declared map: {row.get('backend')}")
            expected_phases = [list(item) for item in _expected_phases(backend_rows)]
            if request.get("possible_child_phases") != expected_phases:
                problems.append("declared possible child phases differ from backend map")
        except (KeyError, TypeError):
            problems.append("declared backend map or snapshots are malformed")
    if receipt.get("run_id") != run_dir.name or capture_doc.get("run_id") != run_dir.name:
        problems.append("run id does not match the sealed directory")
    try:
        source_roles = {item.get("role") for item in request.get("sources", [])}
        if source_roles != {"producer", "store_verifier", "resolver", "linkage_verifier"} \
                or len(request.get("sources", [])) != 4:
            problems.append("source readset roles are incomplete or duplicated")
        for source in request.get("sources", []):
            path = Path(source["path"])
            if not path.is_file() or sha256_file(path) != source["sha256"]:
                problems.append(f"source bytes changed/unavailable: {path}")
        for row in request.get("backends", []):
            link = Path(row["link_path"])
            target = Path(row["target_path"])
            binary = Path(row["binary_path"])
            if not link.is_symlink() or os.readlink(link) != row["symlink_target_text"] \
                    or str(link.resolve(strict=True)) != str(target):
                problems.append(f"backend symlink/target changed: {row['backend']}")
                continue
            if _stat_identity(link, follow_symlinks=False) != row["symlink_lstat"] \
                    or _stat_identity(target, follow_symlinks=True) != row["target_stat"]:
                problems.append(f"backend target identity changed: {row['backend']}")
            if not binary.is_file() or sha256_file(binary) != row["binary_sha256"] \
                    or _stat_identity(binary, follow_symlinks=True) != row["binary_stat"]:
                problems.append(f"backend binary changed: {row['backend']}")
            for candidate in row.get("library_candidates", []):
                candidate_path = Path(candidate["path"])
                resolved_path = candidate_path.resolve(strict=True)
                target_text = os.readlink(candidate_path) if candidate_path.is_symlink() else None
                if str(resolved_path) != candidate["realpath"] \
                        or target_text != candidate["symlink_target_text"] \
                        or _stat_identity(candidate_path, follow_symlinks=False) != candidate["path_lstat"] \
                        or _stat_identity(resolved_path, follow_symlinks=True) != candidate["resolved_stat"] \
                        or sha256_file(resolved_path) != candidate["sha256"]:
                    problems.append(f"candidate library changed: {row['backend']} {candidate_path}")
    except (KeyError, OSError, TypeError) as exc:
        problems.append(f"request input readback failed: {exc}")
    diagnostics = capture_doc.get("diagnostics")
    if not isinstance(diagnostics, list):
        problems.append("capture diagnostics are malformed")
    else:
        problems.extend(str(item) for item in diagnostics)
    outer = capture_doc.get("outer_invocation", {})
    try:
        source_by_role = {item["role"]: item["path"] for item in request["sources"]}
        allowed = request["allowed_environment"]
        expected_outer_env = {"PATH": allowed["PATH"],
                              "LD_LIBRARY_PATH": allowed["LD_LIBRARY_PATH"],
                              "ROCM_PATH": allowed["ROCM_PATH"], "LANG": "C", "LC_ALL": "C",
                              "KERNEL_STORE_ROOT": request["kernel_root"],
                              "KERNEL_STORE_CAPTURE_RESOLVER": request["invocation_paths"]["resolver"],
                              "KERNEL_STORE_CAPTURE_LINKAGE_VERIFIER":
                                  request["invocation_paths"]["linkage_verifier"]}
        if outer.get("argv") != ["/bin/bash", source_by_role["store_verifier"], "--capture-v1"] \
                or outer.get("cwd") != request.get("cwd"):
            problems.append("outer verifier argv/cwd differ from the bound request")
        if outer.get("environment") != expected_outer_env:
            problems.append("outer allowlisted environment differs from the bound request")
        outer_stdout = base64.b64decode(outer.get("stdout_b64", ""), validate=True)
        outer_stderr = base64.b64decode(outer.get("stderr_b64", ""), validate=True)
        if outer.get("stdout_sha256") != sha256_bytes(outer_stdout):
            problems.append("outer stdout bytes do not match their digest")
        if outer.get("stderr_sha256") != sha256_bytes(outer_stderr):
            problems.append("outer stderr bytes do not match their digest")
        marker_records = []
        for line in outer_stdout.splitlines(keepends=True):
            parsed = _decode_capture_line(line)
            if parsed is not None:
                parsed["argv"][1] = source_by_role["linkage_verifier"]
                parsed["cwd"] = request["cwd"]
                parsed["environment"] = {**outer.get("environment", {}),
                                          "LD_LIBRARY_PATH": parsed["ld_library_path"]}
                marker_records.append(parsed)
        stored_records = capture_doc.get("child_linkage_invocations", [])
        marker_index = {(r["backend"], r["phase"]): r for r in marker_records}
        stored_index = {(r["backend"], r["phase"]): r for r in stored_records}
        if set(marker_index) != set(stored_index):
            problems.append("child records differ from original verifier stdout markers")
        for key in marker_index.keys() & stored_index.keys():
            for field in ("exit_code", "binary_path", "target_path", "ld_library_path",
                          "combined_output_b64", "combined_output_sha256"):
                if marker_index[key].get(field) != stored_index[key].get(field):
                    problems.append(f"child record differs from original stdout marker: {key} {field}")
        for record in stored_records:
            expected_child_env = {**expected_outer_env,
                                  "LD_LIBRARY_PATH": record.get("ld_library_path")}
            expected_argv = ["bash", request["invocation_paths"]["linkage_verifier"],
                             record.get("binary_path"), record.get("target_path")]
            if record.get("environment") != expected_child_env or record.get("argv") != expected_argv \
                    or record.get("cwd") != request.get("cwd"):
                problems.append(f"child argv/env/cwd differ from the bound request: "
                                f"{record.get('backend')} {record.get('phase')}")
        replay_problems, ambient_notes = _check_child_records(request, stored_records)
        problems.extend(replay_problems)
        if ambient_notes != capture_doc.get("ambient_diagnostics"):
            problems.append("ambient diagnostics differ from retained child output")
    except (KeyError, TypeError, ValueError, ReceiptError) as exc:
        problems.append(f"capture bytes/child records are malformed: {exc}")
    computed_pass = (outer.get("exit_code") == 0 and outer.get("execution_error") is None
                     and outer.get("owned_process_group_cleanup_verified") is True
                     and capture_doc.get("diagnostics") == [] and not problems)
    if capture_doc.get("dependency_verification_passed") is not computed_pass \
            or receipt.get("dependency_verification_passed") is not computed_pass:
        problems.append("capture and receipt dependency status differs from validated evidence")
    if receipt.get("diagnostics") != capture_doc.get("diagnostics"):
        problems.append("receipt diagnostics differ from capture diagnostics")
    if not receipt.get("dependency_verification_passed") or outer.get("exit_code") != 0:
        problems.append("native store verification did not pass")
    return not problems, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture_parser = sub.add_parser("capture", help="explicitly run and retain a store check")
    capture_parser.add_argument("--receipt-root", type=Path, required=True)
    capture_parser.add_argument("--timeout", type=float, default=180.0)
    capture_parser.add_argument("--synthetic", action="store_true",
                                help="permit explicit synthetic resolver/linkage paths")
    capture_parser.add_argument("--kernel-root", type=Path, default=DEFAULT_KERNEL_ROOT)
    capture_parser.add_argument("--resolver", type=Path, default=DEFAULT_RESOLVER)
    capture_parser.add_argument("--linkage-verifier", type=Path, default=DEFAULT_LINKAGE)
    verify_parser = sub.add_parser("verify", help="verify a stored receipt without execution")
    verify_parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            return capture(args)
        valid, problems = verify(args.run_dir.resolve(strict=True))
        print("VALID" if valid else "REFUSED")
        for problem in problems:
            print(f"- {problem}")
        return 0 if valid else 2
    except (OSError, ReceiptError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
