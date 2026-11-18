"""Run the DCP-10 ColGREP CLI against explicitly mounted local inputs."""
from __future__ import annotations

import ast
import fcntl
import json
import math
import os
import resource
import shutil
import signal
import sqlite3
import stat
import subprocess
import tempfile
import time
from contextlib import closing
from pathlib import Path
from uuid import uuid4

IMAGE = "sha256:d9b8c34d61a9b9a3c44cab883d7d2f2619d674966ab520186f799cf32e3e0377"
VERSION = "1.2.0"
RUNTIME_NAME = "libonnxruntime.so.1.23.0"
BINARY_IN = "/dcp10/colgrep"
MODEL_IN = "/dcp10/model"
DATA_IN = "/dcp10/data"
RUNTIME_IN = f"/dcp10/{RUNTIME_NAME}"
MEMORY_BYTES = 8 * 1024**3
MAX_SIDECAR_BYTES = 32_768
NPY_V1 = b"\x93NUMPY\x01\x00"
NEXT_PLAID_V1_2_0 = "10806326cd665629070a06be1b338e876aa1aa62"


class IsolationError(RuntimeError):
    """The native process could not be confined or reliably cleaned up."""


class NativeError(RuntimeError):
    """An isolated ColGREP command failed or exceeded its timeout."""


def _canonical(path, mode):
    path = Path(path)
    if path.resolve(strict=True) != path or not mode(path.lstat().st_mode):
        raise ValueError(f"unexpected native ColGREP input: {path}")
    return path


def _inputs(assets, root, data_home):
    assets = _canonical(assets, stat.S_ISDIR)
    root = _canonical(root, stat.S_ISDIR)
    data_home = _canonical(data_home, stat.S_ISDIR)
    if (data_home != assets / "bases" / root.name
            or root.is_relative_to(assets) or assets.is_relative_to(root)
            or root.is_relative_to("/dcp10") or Path("/dcp10").is_relative_to(root)
            or not os.access(root, os.R_OK | os.X_OK)):
        raise ValueError("expected an independent base and its private native data directory")
    if (assets.stat().st_uid != os.geteuid() or stat.S_IMODE(assets.stat().st_mode) & 0o077
            or data_home.stat().st_uid != os.geteuid()):
        raise ValueError("native inputs must live in an owned private asset directory")
    binary = _canonical(assets / "bin/colgrep", stat.S_ISREG)
    if not os.access(binary, os.X_OK):
        raise ValueError("native ColGREP executable is missing or unreadable")
    return root, data_home, binary, _canonical(assets / "model", stat.S_ISDIR), _canonical(
        assets / "runtime" / RUNTIME_NAME, stat.S_ISREG)


def _project(root, data_home):
    indices = _canonical(data_home / "colgrep/indices", stat.S_ISDIR)
    projects = list(indices.iterdir())
    if len(projects) != 1:
        raise ValueError("expected exactly one private ColGREP project index")
    project = _canonical(projects[0], stat.S_ISDIR)
    info = json.loads(_canonical(project / "project.json", stat.S_ISREG).read_text())
    state = json.loads(_canonical(project / "state.json", stat.S_ISREG).read_text())
    if (not isinstance(info, dict) or info.get("project_path") != str(root)
            or not isinstance(state, dict) or state.get("cli_version") != VERSION
            or state.get("dirty") is not False or not state.get("files")):
        raise ValueError("private ColGREP index is incomplete or belongs to another checkout")
    _canonical(project / ".lock", stat.S_ISREG)
    _canonical(project / "index/metadata.json", stat.S_ISREG)
    _canonical(project / "index/metadata.db", stat.S_ISREG)
    return project


def _sidecars(db):
    return db.with_name(db.name + "-wal"), db.with_name(db.name + "-shm")


def _seal_sqlite(db):
    """Leave clean read-only WAL/SHM sidecars after the sole writer exits."""
    wal, shm = _sidecars(db)
    if wal.exists() or shm.exists():
        raise ValueError("ColGREP did not close its SQLite metadata cleanly")
    with closing(sqlite3.connect(db.as_uri() + "?mode=rw", uri=True)) as connection:
        if connection.execute("PRAGMA journal_mode").fetchone() != ("wal",):
            raise ValueError("expected ColGREP metadata in SQLite WAL mode")
        if connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone() != (0, 0, 0):
            raise ValueError("ColGREP metadata checkpoint did not quiesce")
        shm_bytes = shm.read_bytes()
        if wal.stat().st_size != 0 or len(shm_bytes) != MAX_SIDECAR_BYTES:
            raise ValueError("unexpected ColGREP SQLite WAL sidecars")
    for path, payload in ((wal, b""), (shm, shm_bytes)):
        with path.open("xb") as destination:
            destination.write(payload)


def _npy_chunk(path, dtype, rank, rows):
    with _canonical(path, stat.S_ISREG).open("rb") as source:
        prefix = source.read(10)
        if len(prefix) != 10 or prefix[:8] != NPY_V1:
            raise ValueError(f"unexpected ColGREP NumPy chunk version: {path}")
        header_size = int.from_bytes(prefix[8:], "little")
        header = ast.literal_eval(source.read(header_size).decode("ascii").strip())
        offset = source.tell()
    shape = header["shape"]
    if (header["descr"] != dtype or header["fortran_order"] is not False
            or not isinstance(shape, tuple) or len(shape) != rank
            or any(type(n) is not int or n <= 0 for n in shape) or shape[0] != rows):
        raise ValueError(f"unexpected ColGREP NumPy chunk shape or dtype: {path}")
    row_bytes = 8 if rank == 1 else shape[1]
    if path.stat().st_size != offset + rows * row_bytes:
        raise ValueError(f"incomplete ColGREP NumPy chunk: {path}")
    return offset, row_bytes


def _merged_header(dtype, shape):
    # next-plaid v1.2.0 mmap.rs:1159-1217 pads before adding the newline.
    dictionary = f"{{'descr': '{dtype}', 'fortran_order': False, 'shape': {shape}, }}".encode("ascii")
    header = dictionary + b" " * (-(10 + len(dictionary)) % 64) + b"\n"
    return NPY_V1 + len(header).to_bytes(2, "little") + header


def _time_left(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise NativeError("isolated ColGREP exhausted its index build timeout")
    return remaining


def _materialize_merged_arrays(index, deadline):
    """Apply the pinned mmap loader's lazy merges while the new index is writable."""
    metadata_path = index / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    count = metadata.get("num_chunks")
    if (metadata.get("next_plaid_compatible") is not True
            or type(count) is not int or count <= 0):
        raise ValueError("expected fresh NextPlaid-compatible ColGREP index chunks")
    lengths = [json.loads(_canonical(index / f"doclens.{chunk}.json", stat.S_ISREG).read_text())
               for chunk in range(count)]
    if any(not isinstance(items, list) or not items
           or any(type(n) is not int or n <= 0 for n in items) for items in lengths):
        raise ValueError("unexpected ColGREP document lengths")
    padding = max(max(items) for items in lengths) - lengths[-1][-1]
    rows_per_chunk = [sum(items) for items in lengths]
    total_rows = sum(rows_per_chunk) + padding

    materialized = {}
    for kind, dtype, rank in (("codes", "<i8", 1), ("residuals", "|u1", 2)):
        _time_left(deadline)
        paths = [index / f"{chunk}.{kind}.npy" for chunk in range(count)]
        chunks = [_npy_chunk(path, dtype, rank, rows)
                  for path, rows in zip(paths, rows_per_chunk, strict=True)]
        row_bytes = chunks[0][1]
        if any(width != row_bytes for _, width in chunks):
            raise ValueError(f"inconsistent ColGREP {kind} chunk widths")
        shape = (total_rows,) if rank == 1 else (total_rows, row_bytes)
        merged = index / f"merged_{kind}.npy"
        with merged.open("xb") as destination:
            destination.write(_merged_header(dtype, shape))
            for path, (offset, _) in zip(paths, chunks, strict=True):
                with path.open("rb") as source:
                    source.seek(offset)
                    while block := source.read(1024 * 1024):
                        _time_left(deadline)
                        destination.write(block)
            destination.write(bytes(padding * row_bytes))

        manifest = {
            "chunks": {path.name: {"rows": rows, "mtime": path.stat().st_mtime}
                       for path, rows in zip(paths, rows_per_chunk, strict=True)},
            "padding_rows": padding, "total_rows": total_rows,
            "ncols": 0 if rank == 1 else row_bytes, "num_chunks": count,
            "metadata_mtime": metadata_path.stat().st_mtime,
        }
        with (index / f"merged_{kind}.manifest.json").open("x") as destination:
            json.dump(manifest, destination, allow_nan=False)
        materialized[kind] = {"shape": shape, "bytes": merged.stat().st_size}
    return materialized


def _mount(source, target, *, writable=False):
    if any(mark in str(source) or mark in str(target) for mark in ',\n\r"'):
        raise ValueError("unsupported character in a ColGREP bind mount")
    mode = "bind-recursive=disabled" if writable else "readonly,bind-recursive=readonly"
    return f"type=bind,src={source},dst={target},bind-propagation=rprivate,{mode}"


def _docker_env():
    # Resolve the allocator's Docker wrapper through PATH, using only the local daemon.
    env = {"PATH": os.environ.get("PATH", os.defpath),
           "DOCKER_HOST": "unix:///var/run/docker.sock",
           "DOCKER_CONFIG": "/run/dcp10-no-docker-config", "LANG": "C.UTF-8"}
    for name in ("FILLER_ID", "FILLER_STOPFILE"):
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def _memory_limit():
    limit = MEMORY_BYTES
    address_space, _ = resource.getrlimit(resource.RLIMIT_AS)
    if address_space != resource.RLIM_INFINITY:
        limit = min(limit, address_space)
    try:
        value = Path("/sys/fs/cgroup/memory.max").read_text().strip()
    except FileNotFoundError:
        return limit
    return limit if value == "max" else min(limit, int(value))


def _stop_on_term(_signal, _frame):
    raise SystemExit(143)


def _remove_container(docker, env, name):
    try:
        result = subprocess.run([docker, "rm", "-f", name], env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IsolationError(f"could not confirm ColGREP container removal: {name}") from exc
    if result.returncode and "No such container" not in result.stderr:
        raise IsolationError(f"could not confirm ColGREP container removal: {name}")


def _run(arguments, inputs, timeout, *, build=False, lock=None):
    if (type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 < timeout <= 1800):
        raise ValueError("invalid ColGREP launch timeout")
    root, data_home, binary, model, runtime = inputs
    docker = shutil.which("docker")
    if docker is None:
        raise IsolationError("isolated ColGREP requires the local Docker launcher")
    env = _docker_env()
    name = f"dcp10-colgrep-{uuid4().hex}"
    cpus = ",".join(str(cpu) for cpu in sorted(os.sched_getaffinity(0)))
    memory = str(_memory_limit())
    command = [docker, "run", "--rm", "--pull=never", "--name", name, "--runtime=runc",
               "--network=none", "--read-only", "--cap-drop=ALL", "--log-driver=none",
               "--security-opt=no-new-privileges:true", "--pids-limit=256",
               "--user", f"{os.geteuid()}:{os.getegid()}", "--cpuset-cpus", cpus,
               "--memory", memory, "--memory-swap", memory,
               "--workdir", str(root), "--entrypoint", "/usr/bin/timeout"]
    for key, value in {"HOME": "/dcp10/home", "XDG_CONFIG_HOME": "/dcp10/config",
                       "XDG_DATA_HOME": DATA_IN, "XDG_CACHE_HOME": "/dcp10/cache",
                       "HF_HUB_OFFLINE": "1", "COLGREP_FORCE_CPU": "1",
                       "ORT_DYLIB_PATH": RUNTIME_IN}.items():
        command.extend(("--env", f"{key}={value}"))
    for source, target in ((root, root), (binary, BINARY_IN), (model, MODEL_IN),
                           (runtime, RUNTIME_IN)):
        command.extend(("--mount", _mount(source, target)))
    command.extend(("--mount", _mount(data_home, DATA_IN, writable=build)))
    if lock is not None:
        project, disposable = lock
        target = Path(DATA_IN) / project.relative_to(data_home) / ".lock"
        command.extend(("--mount", _mount(disposable, target, writable=True)))
    command.extend((IMAGE, "--foreground", "--signal=KILL", f"{timeout}s", BINARY_IN,
                    *arguments))
    previous = signal.signal(signal.SIGTERM, _stop_on_term)
    try:
        result = subprocess.run(command, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, encoding="utf-8", timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        # Killing an attached client alone can leave the container running.
        _remove_container(docker, env, name)
        raise NativeError("isolated ColGREP exceeded its launch timeout") from None
    except (KeyboardInterrupt, SystemExit, UnicodeError):
        _remove_container(docker, env, name)
        raise
    except OSError as exc:
        raise IsolationError("could not start isolated ColGREP") from exc
    finally:
        signal.signal(signal.SIGTERM, previous)
    if result.returncode:
        # Docker and GNU timeout reserve these codes for launch failures.
        error = IsolationError if result.returncode in (125, 126, 127) else NativeError
        if result.returncode < 0:
            _remove_container(docker, env, name)
        raise error(f"isolated ColGREP exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def build_index(assets, root, data_home, timeout):
    """Build and seal a fresh private index inside an admitted native row."""
    if (type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 < timeout <= 1800):
        raise ValueError("invalid ColGREP launch timeout")
    deadline = time.monotonic() + timeout
    inputs = _inputs(assets, root, data_home)
    root, data_home, *_ = inputs
    if any(data_home.iterdir()):
        raise ValueError("ColGREP init requires a fresh, empty private data directory")
    _run(["init", "--model", MODEL_IN, "--force-cpu", "-y", "--", str(root)],
         inputs, _time_left(deadline), build=True)
    project = _project(root, data_home)
    arrays = _materialize_merged_arrays(project / "index", deadline)
    try:
        _seal_sqlite(project / "index/metadata.db")
    except sqlite3.Error as exc:
        raise ValueError("could not seal private ColGREP metadata") from exc
    _time_left(deadline)
    with (data_home / "materialization.json").open("x") as destination:
        json.dump({"method": "next-plaid-mmap-copy-and-zero-padding", "inference": False,
                   "source_commit": NEXT_PLAID_V1_2_0, "arrays": arrays}, destination)


def search(argv, root, data_home, timeout):
    """Execute the comparator's fixed search using a sealed, read-only index."""
    if (len(argv) != 13 or argv[1:3] != ["search", "-k"]
            or not isinstance(argv[3], str) or not argv[3].isascii() or not argv[3].isdecimal()
            or not 1 <= int(argv[3]) <= 20 or argv[4:7] != ["--alpha", "0.95", "--model"]
            or argv[8:11] != ["--force-cpu", "--json", "--"]
            or not isinstance(argv[11], str) or not argv[11].strip() or argv[12] != str(root)):
        raise ValueError("unexpected native ColGREP search arguments")
    assets = Path(argv[0]).parent.parent
    inputs = _inputs(assets, root, data_home)
    root, data_home, binary, model, _ = inputs
    if argv[0] != str(binary) or argv[7] != str(model):
        raise ValueError("expected the sealed native ColGREP executable and model")
    project = _project(root, data_home)
    for kind in ("codes", "residuals"):
        _canonical(project / f"index/merged_{kind}.npy", stat.S_ISREG)
        _canonical(project / f"index/merged_{kind}.manifest.json", stat.S_ISREG)
    wal, shm = _sidecars(project / "index/metadata.db")
    if (_canonical(wal, stat.S_ISREG).stat().st_size != 0
            or _canonical(shm, stat.S_ISREG).stat().st_size != MAX_SIDECAR_BYTES):
        raise ValueError("expected sealed, checkpointed SQLite sidecars before retrieval")
    # v1.2.0 truncates .lock before trying LOCK_EX, then skips auto-indexing if the
    # lock is held. Only the disposable file is writable. Search-stat writes to
    # the read-only project fail harmlessly (commands/search.rs ignores them).
    with tempfile.TemporaryDirectory(prefix=".search-", dir=assets) as scratch:
        disposable = Path(scratch) / "lock"
        with disposable.open("xb") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            args = [*argv[1:7], MODEL_IN, *argv[8:]]
            return _run(args, inputs, timeout, lock=(project, disposable))
