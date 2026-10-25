"""Canary B side-effect guard (installed before any orchestrator/ROOT import).

PEP 578 audit hook that RAISES on:
  * any file write / create / rename / remove / mkdir outside the canary-B scratch roots
  * any socket connect (no HTTP to :8000, model ports, embedding servers, ntfy)
  * any subprocess other than read-only git (GIT_OPTIONAL_LOCKS=0) or a python child that is
    itself re-wrapped by canary_guard_child.py (which installs this same hook)
  * any sqlite3.connect that is neither under scratch nor a mode=ro URI
plus a sqlite3.connect shim that rewrites non-scratch DB paths to `file:...?mode=ro`.
Every blocked event is recorded (with the nearest non-guard caller file:line) in BLOCKED and
appended to <BASE>/B-copies/blocked_events.jsonl.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import traceback

BASE = "/mnt/raid0/llm/tmp/ws58-canary-20261025"
ALLOWED_WRITE_ROOTS = (
    BASE + "/B-copies",
    BASE + "/state/B-autopilot",
    BASE + "/alarm/alarm_state.B.json",
    BASE + "/alarm/alarm_state.B.json.lock",
    BASE + "/alarm/alarms.jsonl",
    BASE + "/B-context.txt",
    BASE + "/B-summary.json",
    "/dev/null",
)
CHILD_WRAPPER = BASE + "/harness/canary_guard_child.py"
BLOCK_LOG = BASE + "/B-copies/blocked_events.jsonl"
GIT_READ_SUBCOMMANDS = {"rev-parse", "status", "show", "log", "diff", "ls-files", "cat-file",
                        "describe", "branch", "config", "symbolic-ref", "merge-base"}

BLOCKED: list[dict] = []
ALLOWED_WRITES: set[str] = set()
SUBPROCESSES: list[dict] = []
_real_sqlite_connect = sqlite3.connect
_real_run = subprocess.run
_in_hook = False
_installed = False


def _under(path: str, roots=ALLOWED_WRITE_ROOTS) -> bool:
    try:
        rp = os.path.realpath(path)
    except Exception:
        rp = str(path)
    return any(rp == r or rp.startswith(r.rstrip("/") + "/") for r in roots)


def _caller() -> str:
    for fr in reversed(traceback.extract_stack()[:-3]):
        if "canary_guard" not in fr.filename:
            return f"{fr.filename}:{fr.lineno}"
    return "?"


def _block(kind: str, detail: str) -> None:
    rec = {"kind": kind, "detail": str(detail)[:400], "caller": _caller(), "pid": os.getpid()}
    BLOCKED.append(rec)
    try:
        global _in_hook
        _in_hook = True
        with open(BLOCK_LOG, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass
    finally:
        _in_hook = False
    raise PermissionError(f"canary guard blocked {kind}: {detail}"[:300])


_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC


def _hook(event: str, args) -> None:
    if _in_hook:
        return
    if event == "open":
        path, mode, flags = args
        if isinstance(path, int) or path is None:
            return
        path = os.fsdecode(path)
        writing = False
        if isinstance(mode, str):
            writing = any(c in mode for c in "wax+")
        elif isinstance(flags, int):
            writing = bool(flags & _WRITE_FLAGS)
        if writing:
            if _under(path):
                ALLOWED_WRITES.add(os.path.realpath(path))
            else:
                _block("write", f"{path} mode={mode} flags={flags}")
    elif event in ("os.rename", "os.replace", "os.link", "os.symlink", "shutil.copyfile",
                   "shutil.move", "shutil.copytree"):
        for p in args[:2]:
            if isinstance(p, (str, bytes, os.PathLike)) and event != "shutil.copyfile":
                if not _under(os.fsdecode(p)):
                    _block(event, f"{args[:2]}")
        if event == "shutil.copyfile" and not _under(os.fsdecode(args[1])):
            _block(event, f"{args[:2]}")
    elif event in ("os.remove", "os.rmdir", "os.truncate", "os.chmod", "os.chown", "os.utime",
                   "shutil.rmtree", "os.chflags", "os.setxattr", "os.removexattr"):
        p = args[0]
        if isinstance(p, int):
            return
        if not _under(os.fsdecode(p)):
            _block(event, f"{p}")
    elif event == "os.mkdir":
        p = os.fsdecode(args[0])
        if not _under(p) and not os.path.exists(p):
            _block(event, p)
    elif event in ("socket.connect", "socket.sendto", "socket.sendmsg"):
        _block(event, f"{args[1:] if len(args) > 1 else args}")
    elif event == "subprocess.Popen":
        executable, argv, cwd, env = args
        argv = [os.fsdecode(a) for a in (argv if isinstance(argv, (list, tuple)) else [argv])]
        SUBPROCESSES.append({"argv": argv[:6], "caller": _caller()})
        exe = os.path.basename(argv[0]) if argv else ""
        if exe == "git":
            sub = next((a for a in argv[1:] if not a.startswith("-") and a not in ("-C",)), "")
            # skip the value following -C
            toks = argv[1:]
            i = 0
            while i < len(toks):
                if toks[i] == "-C":
                    i += 2
                    continue
                if toks[i].startswith("-"):
                    i += 1
                    continue
                sub = toks[i]
                break
            if sub in GIT_READ_SUBCOMMANDS and (env is None or env.get("GIT_OPTIONAL_LOCKS") == "0"
                                                 or os.environ.get("GIT_OPTIONAL_LOCKS") == "0"):
                return
            _block("subprocess", f"git {sub}: {argv[:6]}")
        if len(argv) >= 2 and argv[1] == CHILD_WRAPPER:
            return
        _block("subprocess", f"{argv[:6]}")
    elif event == "sqlite3.connect":
        db = os.fsdecode(args[0]) if not isinstance(args[0], str) else args[0]
        if db.startswith("file:") and "mode=ro" in db:
            return
        if db == ":memory:" or _under(db):
            return
        _block("sqlite3.connect", db)


def _ro_connect(database, *a, **kw):
    db = os.fsdecode(database) if not isinstance(database, str) else database
    if db != ":memory:" and not db.startswith("file:") and not _under(db):
        uri = "file:" + os.path.realpath(db) + "?mode=ro"
        kw["uri"] = True
        return _real_sqlite_connect(uri, *a, **kw)
    return _real_sqlite_connect(database, *a, **kw)


def _guarded_run(args, *a, **kw):
    """Rewrite `python script.py ...` children through the guard wrapper; force read-only git."""
    argv = list(args) if isinstance(args, (list, tuple)) else args
    if isinstance(argv, list) and len(argv) >= 2 and str(argv[1]).endswith(".py") \
            and os.path.basename(str(argv[0])).startswith("python"):
        argv = [argv[0], CHILD_WRAPPER, *[str(x) for x in argv[1:]]]
    if isinstance(argv, list) and argv and os.path.basename(str(argv[0])) == "git":
        env = dict(kw.get("env") or os.environ)
        env["GIT_OPTIONAL_LOCKS"] = "0"
        kw["env"] = env
    return _real_run(argv, *a, **kw)


def install() -> None:
    global _installed
    if _installed:
        return
    _installed = True
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    os.environ["TMPDIR"] = BASE + "/B-copies/tmp"
    os.makedirs(BASE + "/B-copies/tmp", exist_ok=True)
    import tempfile
    tempfile.tempdir = BASE + "/B-copies/tmp"
    sqlite3.connect = _ro_connect
    subprocess.run = _guarded_run
    sys.addaudithook(_hook)
