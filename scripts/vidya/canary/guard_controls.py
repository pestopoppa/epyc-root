#!/usr/bin/env python3
"""Run cooperative guard regressions against a scratch-only SQLite fixture."""
import contextlib
import io
import os
import runpy
import socket
import sqlite3
import subprocess
import sys
import types
from pathlib import Path

sys.dont_write_bytecode = True
base = Path(os.environ["CANARY_SCRATCH"]).resolve()
if not base.is_relative_to(Path("/mnt/raid0/llm/tmp")) or base == Path("/mnt/raid0/llm/tmp"):
    raise SystemExit("CANARY_SCRATCH must be a private scratch path")
here = Path(__file__).resolve().parent
script = here / "run.py"
real_run = subprocess.run
for marker in ("null", "[]", '{"status":"PASS"}', '{"status":"BOGUS"}'):
    subprocess.run = lambda *args, **kwargs: types.SimpleNamespace(
        stdout="CANARY_RESULT: " + marker + "\n", returncode=1)
    sys.argv = [str(script), "a"]
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 2, (marker, exc.code)
    else:
        raise AssertionError("missing UNKNOWN exit")
    assert '"status": "UNKNOWN"' in out.getvalue(), marker
subprocess.run = real_run
print("PASS malformed/inconsistent result markers -> UNKNOWN")

# Create only inside the task scratch before installing the cooperative guard.
fixture = base / "guard-control.sqlite"
with sqlite3.connect(fixture) as db:
    db.execute("CREATE TABLE IF NOT EXISTS t(x)")
child = base / "guard-control-child.py"
child.write_text("print('guarded child ok')\n")
sys.path.insert(0, str(here))
import canary_guard as guard
guard.install()
guard.ALLOWED_WRITE_ROOTS = (str(base / "B-copies"), "/dev/null")
for query in ("mode=rw&x=mode%3Dro", "mode=ro&mode=rw", "x=mode%3Dro"):
    try:
        sqlite3.connect(fixture.as_uri() + "?" + query, uri=True)
    except PermissionError:
        pass
    else:
        raise AssertionError("unsafe URI accepted: " + query)
with sqlite3.connect(fixture.as_uri() + "?mode=ro", uri=True) as db:
    db.execute("SELECT count(*) FROM t").fetchone()
print("PASS SQLite real read-only URI; reject disguised/duplicate write modes")

for args, kwargs in (([sys.executable, guard.CHILD_WRAPPER], {"executable": "/bin/true"}),
                     ("true", {"shell": True})):
    try:
        subprocess.run(args, **kwargs)
    except PermissionError:
        pass
    else:
        raise AssertionError("executable spoof or shell accepted")
print("PASS executable spoof and shell refused")

# Normal trusted Python child is rewrapped under the same audit hook.
result = subprocess.run([sys.executable, str(child)], capture_output=True, text=True)
assert result.returncode == 0 and "guarded child ok" in result.stdout, result.stderr
print("PASS trusted Python child rewrapped")

for path in ("/mnt/raid0/llm/state/vidya/ledger.jsonl",
             "/mnt/raid0/llm/tmp/seeding_batch_telemetry.jsonl"):
    try:
        open(path, "a")
    except PermissionError:
        pass
    else:
        raise AssertionError("live path write accepted")
try:
    socket.socket().connect(("127.0.0.1", 1))
except PermissionError:
    pass
else:
    raise AssertionError("socket allowed")
print("PASS live ledger/telemetry writes and socket refused")

# LOOP-SAFETY C1: the reader pin's exact read-only git forms pass; anything else stays refused.
repo = str(here)
z = "0" * 40
for tail in (["rev-parse", "--verify", "HEAD^{commit}"],
             ["merge-base", "--is-ancestor", z, z],
             ["rev-list", "--count", f"{z}..{z}"]):
    subprocess.run(["git", "-C", repo, *tail], capture_output=True)  # may exit non-zero; allowed
for tail in (["fetch", "origin"], ["merge-base", "--is-ancestor", "origin/main", "HEAD"],
             ["rev-list", "--count", "HEAD..origin/main"], ["rev-list", "--count", f"{z}...{z}"],
             ["update-ref", "refs/remotes/origin/main", z]):
    try:
        subprocess.run(["git", "-C", repo, *tail], capture_output=True)
    except PermissionError:
        pass
    else:
        raise AssertionError("git form accepted: " + " ".join(tail))
print("PASS reader-pin git reads allowed; fetch/update-ref/symbolic forms refused")
