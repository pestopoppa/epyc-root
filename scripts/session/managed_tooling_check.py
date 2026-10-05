#!/usr/bin/env python3
"""Capture one prospective managed-interpreter import check.

This is deliberately a named check, not a host-health collector. The child imports
exactly one declared module once, reports identity over a private side channel, and
leaves its original stdout/stderr untouched for byte capture by this parent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time
import uuid

SCHEMA = "epyc.managed_tooling_check.v1"
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_IDENTITY_BYTES = 256 * 1024 * 1024
MAX_CHILD_METADATA_BYTES = 64 * 1024
CHILD_TIMEOUT_SECONDS = 15
TERM_GRACE_SECONDS = 2
KILL_GRACE_SECONDS = 1
CHILD_EXIT_CODE: int | None = None
CHILD_STARTED = False
CHILD_PID: int | None = None

# Kept as a literal and hashed into every request. The import runs only once, in
# this child; module and interpreter identity are emitted from that same process.
IMPORT_DRIVER = r'''import hashlib, importlib, json, os, pathlib, sys
fd = int(sys.argv[2])
module_name = sys.argv[1]
def file_identity(value):
    if not value:
        return {"path": None, "sha256": None}
    path = pathlib.Path(value).resolve()
    try:
        info = path.stat()
        if not path.is_file() or not stat_is_regular(info.st_mode) or info.st_size > 268435456:
            return {"path": str(path), "sha256": None}
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return {"path": str(path), "sha256": h.hexdigest()}
    except OSError:
        return {"path": str(path), "sha256": None}
def stat_is_regular(mode):
    import stat
    return stat.S_ISREG(mode)
executable = file_identity(sys.executable)
metadata = {"python": {"executable": executable, "version": sys.version,
                       "implementation": sys.implementation.name},
            "module": {"name": module_name, "origin": None, "sha256": None},
            "import_error": None,
            "import_succeeded": False, "metadata_error": None}
failure = None
try:
    imported = importlib.import_module(module_name)
    metadata["import_succeeded"] = True
except BaseException as exc:
    failure = exc
    metadata["import_error"] = {"type": type(exc).__name__, "message": str(exc)}
if metadata["import_succeeded"]:
    try:
        spec = getattr(imported, "__spec__", None)
        origin = getattr(spec, "origin", None) or getattr(imported, "__file__", None)
        module_file = file_identity(origin)
        metadata["module"].update({"origin": module_file["path"],
                                   "sha256": module_file["sha256"]})
    except BaseException as exc:
        metadata["metadata_error"] = {"type": type(exc).__name__, "message": str(exc)}
wire = json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
if len(wire) > 65536:
    raise RuntimeError("child metadata exceeded its bounded sidechannel")
offset = 0
while offset < len(wire):
    offset += os.write(fd, wire[offset:])
if failure is not None:
    raise failure
'''


def utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _read_regular(path: Path, limit: int | None = None) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("input is not a regular file")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read((limit + 1) if limit is not None else -1)
        if limit is not None and len(data) > limit:
            raise ValueError("input exceeds bounded capture size")
        return data
    finally:
        os.close(fd)


def _write_exclusive(path: Path, data: bytes, mode: int = 0o600) -> dict:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.fchmod(fd, 0o400)
    finally:
        os.close(fd)
    return {"name": path.name, "sha256": sha256(data), "size": len(data)}


def _ensure_private_output_root(path: Path) -> None:
    if path.is_symlink():
        raise ValueError("output root may not be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError("output root must be an owned private directory (mode 0700 or stricter)")


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _stop_owned_group(process: subprocess.Popen, pgid: int) -> bool:
    """Bounded TERM/KILL of only the process group created by this invocation."""
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + TERM_GRACE_SECONDS
    while _group_alive(pgid) and time.monotonic() < deadline:
        time.sleep(0.02)
    if _group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            return False
    deadline = time.monotonic() + KILL_GRACE_SECONDS
    while _group_alive(pgid) and time.monotonic() < deadline:
        time.sleep(0.02)
    return not _group_alive(pgid)


def _run_import(interpreter: Path, module_name: str) -> tuple[int | None, dict | None,
                                                               bytes | None, bytes | None, str,
                                                               list[str], bytes | None, bool, bool,
                                                               int | None]:
    read_fd, write_fd = os.pipe()
    os.set_inheritable(write_fd, True)
    argv = [str(interpreter), "-c", IMPORT_DRIVER, module_name, str(write_fd)]
    timed_out = False
    cleanup_ok = True
    leftover_group = False
    process = None
    try:
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                process = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                    stdout=stdout_file, stderr=stderr_file, close_fds=True,
                    pass_fds=(write_fd,), start_new_session=True)
            except OSError as exc:
                os.close(read_fd)
                os.close(write_fd)
                return (None, None, None, None, f"interpreter could not be started: {exc}",
                        argv, None, False, True, None)
            global CHILD_STARTED
            CHILD_STARTED = True
            global CHILD_PID
            CHILD_PID = process.pid
            os.close(write_fd)
            try:
                process.wait(timeout=CHILD_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                timed_out = True
                cleanup_ok = _stop_owned_group(process, process.pid)
            else:
                # A named import should not leave descendants. Reap only this
                # invocation's process group; any such child makes the record diagnostic.
                if _group_alive(process.pid):
                    leftover_group = True
                    cleanup_ok = _stop_owned_group(process, process.pid)
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout = stdout_file.read(MAX_OUTPUT_BYTES + 1)
            stderr = stderr_file.read(MAX_OUTPUT_BYTES + 1)
            if len(stdout) > MAX_OUTPUT_BYTES or len(stderr) > MAX_OUTPUT_BYTES:
                stdout = stdout[:MAX_OUTPUT_BYTES]
                stderr = stderr[:MAX_OUTPUT_BYTES]
                diagnostic = "captured output exceeded the per-stream limit"
            elif timed_out:
                diagnostic = "named import exceeded the bounded timeout"
            elif leftover_group:
                diagnostic = "owned descendants remained after the import process exited"
            elif not cleanup_ok:
                diagnostic = "owned process group did not settle after TERM/KILL"
            else:
                diagnostic = ""
            os.set_blocking(read_fd, False)
            metadata_chunks = []
            metadata_size = 0
            metadata_complete = False
            metadata_deadline = time.monotonic() + 0.5
            while time.monotonic() < metadata_deadline:
                try:
                    chunk = os.read(read_fd, min(8192, MAX_CHILD_METADATA_BYTES + 1 - metadata_size))
                except BlockingIOError:
                    time.sleep(0.01)
                    continue
                if not chunk:
                    metadata_complete = True
                    break
                metadata_chunks.append(chunk)
                metadata_size += len(chunk)
                if metadata_size > MAX_CHILD_METADATA_BYTES:
                    diagnostic = "child metadata exceeded its bounded sidechannel"
                    break
            metadata_bytes = b"".join(metadata_chunks)
            if not metadata_complete and not diagnostic:
                diagnostic = "child metadata sidechannel did not close within its bound"
            try:
                metadata = json.loads(metadata_bytes) if metadata_bytes else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                metadata = None
            if not diagnostic and not isinstance(metadata, dict):
                diagnostic = "child identity metadata missing or malformed"
            exit_code = process.returncode
            global CHILD_EXIT_CODE
            CHILD_EXIT_CODE = exit_code
            return (exit_code, metadata, stdout, stderr, diagnostic, argv, metadata_bytes,
                    timed_out, cleanup_ok, process.pid)
    except OSError as exc:
        pid = process.pid if process is not None else None
        if process is not None:
            cleanup_ok = _stop_owned_group(process, process.pid)
            exit_code = process.returncode
        else:
            exit_code = None
        return (exit_code, None, None, None,
                f"capture execution or output custody failed: {exc}", argv, None,
                False, cleanup_ok, pid)
    finally:
        for fd in (read_fd, write_fd):
            try:
                os.close(fd)
            except OSError:
                pass


def _capture(args) -> Path:
    started = utc()
    output_root = Path(args.output_root).absolute()
    run_dir: Path | None = None
    producer_path = Path(__file__).resolve()
    producer_bytes = _read_regular(producer_path, 4 * 1024 * 1024)
    driver_bytes = IMPORT_DRIVER.encode()
    record = {"schema": SCHEMA, "check_id": args.check_id, "module_name": args.module,
              "requested_interpreter": str(Path(args.interpreter).absolute()),
              "requested_interpreter_realpath": None,
              "interpreter_prebind": None,
              "check_source": str(Path(args.check_source).absolute()),
              "started_utc": started, "ended_utc": None, "execution_started": False,
              "exit_code": None, "child_timed_out": False, "child_cleanup_ok": True,
              "child_pid": None,
              "verdict": None, "diagnostic": "",
              "interpreter": None, "module": None, "stdout": None, "stderr": None,
              "child_metadata": None, "child_terminal": None,
              "import_error": None, "import_succeeded": None, "metadata_error": None,
              "argv": None, "request": None, "decided_proposition": None,
              "exclusions": ["transitive dependency completeness", "ambient environment contents",
                             "whole-host health", "installation or repair outcome",
                             "historical or pre-hook output"],
              "producer": {"path": str(producer_path), "sha256": sha256(producer_bytes)},
              "import_driver_sha256": sha256(driver_bytes),
              "argv_template": [str(Path(args.interpreter).absolute()), "-c",
                                "<import-driver sha256=" + sha256(driver_bytes) + ">",
                                args.module, "<private metadata fd>"]}
    _ensure_private_output_root(output_root)
    run_dir = output_root / (started.replace(":", "").replace("-", "") + "-" + uuid.uuid4().hex)
    run_dir.mkdir(mode=0o700)

    request = {"schema": SCHEMA, "check_id": args.check_id, "module_name": args.module,
               "requested_interpreter": record["requested_interpreter"],
               "check_source": record["check_source"], "producer": record["producer"],
               "import_driver_sha256": record["import_driver_sha256"],
               "argv_template": record["argv_template"]}
    try:
        check_bytes = _read_regular(Path(args.check_source).absolute(), 4 * 1024 * 1024)
        request["check_source_sha256"] = sha256(check_bytes)
        source_artifact = _write_exclusive(run_dir / "check-source.bin", check_bytes)
        producer_artifact = _write_exclusive(run_dir / "producer-source.bin", producer_bytes)
        driver_artifact = _write_exclusive(run_dir / "import-driver.bin", driver_bytes)
        request["readset"] = [{"role": "check_source", "artifact": source_artifact},
                              {"role": "producer", "artifact": producer_artifact},
                              {"role": "import_driver", "artifact": driver_artifact}]
    except (OSError, ValueError) as exc:
        record["diagnostic"] = f"check source unavailable or unbounded: {exc}"
        _finish(run_dir, record)
        return run_dir

    interpreter = Path(args.interpreter).absolute()
    try:
        interpreter_stat = interpreter.stat()
        if not stat.S_ISREG(interpreter_stat.st_mode) or not os.access(interpreter, os.X_OK):
            raise OSError("configured interpreter is not an executable regular file")
        resolved_interpreter = interpreter.resolve(strict=True)
        interpreter_prebind = {"path": str(resolved_interpreter),
                               "sha256": sha256(_read_regular(resolved_interpreter,
                                                              MAX_IDENTITY_BYTES))}
        record["requested_interpreter_realpath"] = str(resolved_interpreter)
        record["interpreter_prebind"] = interpreter_prebind
    except (OSError, ValueError) as exc:
        interpreter_prebind = None
        diagnostic = f"interpreter unavailable before execution: {exc}"
    request["interpreter_prebind"] = interpreter_prebind
    request["readset"].append({"role": "interpreter_prebind", "identity": interpreter_prebind})
    request_artifact = _write_exclusive(run_dir / "execution-request.json", canonical(request))
    record["request"] = {**request, "artifact": request_artifact}
    if interpreter_prebind is None:
        record["diagnostic"] = diagnostic
        _finish(run_dir, record)
        return run_dir

    timed_out, cleanup_ok = False, True
    child_pid = None
    try:
        record["execution_started"] = True
        (exit_code, metadata, stdout, stderr, diagnostic, actual_argv, metadata_bytes,
         timed_out, cleanup_ok, child_pid) = _run_import(interpreter, args.module)
        global CHILD_EXIT_CODE
        CHILD_EXIT_CODE = exit_code
        if metadata_bytes is not None:
            record["child_metadata"] = _write_exclusive(run_dir / "child-metadata.bin", metadata_bytes)
        record["argv"] = [*actual_argv[:2],
                          "<import-driver sha256=" + sha256(driver_bytes) + ">",
                          *actual_argv[3:]]
        if not CHILD_STARTED:
            record["execution_started"] = False
    except OSError as exc:
        exit_code, metadata, stdout, stderr = None, None, None, None
        metadata_bytes, timed_out, cleanup_ok = None, False, True
        diagnostic = f"capture launch failed before child start: {exc}"
        child_pid = CHILD_PID
        if not CHILD_STARTED:
            record["execution_started"] = False

    record["exit_code"], record["interpreter"] = exit_code, metadata and metadata.get("python")
    record["module"] = metadata and metadata.get("module")
    record["import_error"] = metadata and metadata.get("import_error")
    record["import_succeeded"] = metadata and metadata.get("import_succeeded")
    record["metadata_error"] = metadata and metadata.get("metadata_error")
    if stdout is not None and stderr is not None:
        try:
            record["stdout"] = _write_exclusive(run_dir / "stdout.bin", stdout)
            record["stderr"] = _write_exclusive(run_dir / "stderr.bin", stderr)
        except OSError as exc:
            diagnostic = "; ".join(filter(None, (diagnostic,
                f"original output custody failed: {exc}")))
    record["child_timed_out"] = timed_out
    record["child_cleanup_ok"] = cleanup_ok
    record["child_pid"] = child_pid
    record["diagnostic"] = diagnostic
    try:
        current_check = _read_regular(Path(args.check_source).absolute(), 4 * 1024 * 1024)
        if sha256(current_check) != request["check_source_sha256"]:
            record["diagnostic"] = "check source identity drifted during execution"
    except (OSError, ValueError) as exc:
        record["diagnostic"] = f"check source could not be revalidated: {exc}"
    try:
        current_producer = _read_regular(producer_path, 4 * 1024 * 1024)
        if sha256(current_producer) != record["producer"]["sha256"]:
            record["diagnostic"] = "producer source identity drifted during execution"
    except (OSError, ValueError) as exc:
        record["diagnostic"] = f"producer source could not be revalidated: {exc}"
    interpreter_identity = record["interpreter"] or {}
    module_identity = record["module"] or {}
    prebound_identity = record["interpreter_prebind"] or {}
    interpreter_matches = (interpreter_identity.get("executable", {}).get("path")
                           == record["requested_interpreter_realpath"]
                           and bool(interpreter_identity.get("executable", {}).get("sha256"))
                           and interpreter_identity.get("executable", {}).get("sha256")
                           == prebound_identity.get("sha256"))
    if interpreter_matches:
        try:
            current_executable = _read_regular(Path(interpreter_identity["executable"]["path"]),
                                               MAX_IDENTITY_BYTES)
            if sha256(current_executable) != interpreter_identity["executable"]["sha256"]:
                record["diagnostic"] = "interpreter binary identity drifted during execution"
        except (OSError, ValueError) as exc:
            record["diagnostic"] = f"interpreter binary could not be revalidated: {exc}"
    if module_identity.get("origin") and module_identity.get("sha256"):
        try:
            current_module = _read_regular(Path(module_identity["origin"]), MAX_IDENTITY_BYTES)
            if sha256(current_module) != module_identity["sha256"]:
                record["diagnostic"] = "imported module source identity drifted during execution"
        except (OSError, ValueError) as exc:
            record["diagnostic"] = f"imported module source could not be revalidated: {exc}"
    if (not record["diagnostic"] and record["execution_started"] and metadata
            and interpreter_matches and exit_code is not None):
        if exit_code == 0 and (not record["import_succeeded"] or record["import_error"]):
            record["diagnostic"] = "zero exit contradicted the child's import outcome"
        elif exit_code == 0 and record["metadata_error"]:
            record["diagnostic"] = "module identity metadata failed after import"
        elif exit_code == 0 and not (module_identity.get("origin") and module_identity.get("sha256")):
            record["diagnostic"] = "successful import did not yield a complete module identity"
        elif exit_code != 0 and (record["import_succeeded"] or not record["import_error"]):
            record["diagnostic"] = "failed child did not preserve a failed named import"
        else:
            record["verdict"] = (exit_code == 0)
    elif not record["diagnostic"]:
        record["diagnostic"] = "interpreter identity or import metadata incomplete"
    _finish(run_dir, record, timed_out=timed_out, cleanup_ok=cleanup_ok)
    return run_dir


def _seal(run_dir: Path, record: dict) -> None:
    record["receipt_sha256"] = sha256(canonical(record))
    _write_exclusive(run_dir / "receipt.json", canonical(record))


def _finish(run_dir: Path, record: dict, *, timed_out: bool = False,
            cleanup_ok: bool = True) -> None:
    record["ended_utc"] = record["ended_utc"] or utc()
    terminal = {"schema": "epyc.managed_tooling_child_terminal.v1",
                "check_id": record["check_id"], "started_utc": record["started_utc"],
                "ended_utc": record["ended_utc"],
                "execution_started": record["execution_started"],
                "exit_code": record["exit_code"], "timed_out": timed_out,
                "cleanup_ok": cleanup_ok, "child_pid": record["child_pid"],
                "argv": record["argv"]}
    record["child_terminal"] = _write_exclusive(run_dir / "child-terminal.json", canonical(terminal))
    if record["verdict"] is not None:
        record["decided_proposition"] = proposition(record)
    _seal(run_dir, record)


def proposition(record: dict) -> str:
    """The producer's exact, bounded assertion; the reader may only revalidate it."""
    action = "imported module" if record["verdict"] else "attempted to import module"
    return (f"Named managed import check {record['check_id']} {action} "
            f"{record['module_name']} using interpreter {record['interpreter']['executable']['path']} "
            f"sha256 {record['interpreter']['executable']['sha256']}; resolved module origin "
            f"{record['module'].get('origin')!r} sha256 {record['module'].get('sha256')!r}; "
            f"check source sha256 {record['request']['check_source_sha256']}; exit status "
            f"{record['exit_code']} at {record['ended_utc']}; passed: "
            f"{str(record['verdict']).lower()}.")


def main() -> int:
    global CHILD_EXIT_CODE, CHILD_STARTED, CHILD_PID
    CHILD_EXIT_CODE = None
    CHILD_STARTED = False
    CHILD_PID = None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-id", required=True,
                        choices=("epyc-orchestrator-pytest-import",
                                 "epyc-inference-research-pytest-import"))
    parser.add_argument("--interpreter", required=True)
    parser.add_argument("--module", required=True, choices=("pytest",))
    parser.add_argument("--check-source", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    try:
        run_dir = _capture(args)
        receipt = json.loads(_read_regular(run_dir / "receipt.json", 4 * 1024 * 1024))
        # Match the check's actual child status; custody diagnostics do not invent
        # an import failure or change the health-check verdict.
        if receipt["execution_started"] and receipt["exit_code"] is not None:
            return int(receipt["exit_code"] != 0)
        if receipt["execution_started"]:
            return 1
        # Capture refusal happened before import execution. Preserve the existing
        # health check's behavior with one bounded import attempt; this fallback
        # cannot produce a tuple because its check-source custody was incomplete.
        exit_code, _, _, _, _, _, _, _, _, _ = _run_import(Path(args.interpreter).absolute(), args.module)
        if exit_code is not None:
            return int(exit_code != 0)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if CHILD_STARTED:
            if CHILD_EXIT_CODE is not None:
                return int(CHILD_EXIT_CODE != 0)
            return 1
        if CHILD_EXIT_CODE is not None:
            return int(CHILD_EXIT_CODE != 0)
        try:
            exit_code, _, _, _, _, _, _, _, _, _ = _run_import(Path(args.interpreter).absolute(), args.module)
            if exit_code is not None:
                return int(exit_code != 0)
        except OSError:
            pass
        # Keep the caller's existing pass/fail semantics. The error remains visible
        # in stderr unless its caller intentionally suppresses check command output.
        print(f"managed tooling capture diagnostic: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
