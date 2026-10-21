"""Run gate_1017.py under a guard that RAISES on any stat/open/listdir/scandir/access/readlink/subprocess touching the Sept Q4 or the DSpark drafter."""
import os, sys, builtins, io, runpy, subprocess, json
BAD = ("DeepSeek-V4.1-Flash-Q4.gguf", "DeepSeek-V4.1-Flash-DSpark.gguf")
hits = []
def bad(p):
    try: s = os.fsdecode(p) if not isinstance(p, int) else ""
    except Exception: return False
    return any(b in s for b in BAD)
def wrap(mod, name):
    orig = getattr(mod, name)
    def g(path, *a, **k):
        if bad(path):
            hits.append((name, os.fsdecode(path))); raise PermissionError(f"GUARD: {name}({path}) touches a retired Sept artifact")
        return orig(path, *a, **k)
    setattr(mod, name, g)
for n in ("stat", "lstat", "access", "listdir", "scandir", "readlink", "open", "truncate", "utime", "chmod", "realpath"):
    for m in (os,):
        if hasattr(m, n): wrap(m, n)
import posix
for n in ("stat", "lstat", "access", "listdir", "scandir", "readlink", "open"):
    if hasattr(posix, n): wrap(posix, n)
wrap(builtins, "open"); wrap(io, "open")
orig_realpath = os.path.realpath
def rp(path, *a, **k):
    if bad(path): hits.append(("realpath", os.fsdecode(path))); raise PermissionError("GUARD realpath")
    return orig_realpath(path, *a, **k)
os.path.realpath = rp
def audit(ev, args):
    if ev == "open" and bad(args[0]) : hits.append(("audit-open", str(args[0]))); raise PermissionError("GUARD audit open")
    if ev in ("os.listdir", "os.scandir") and args and args[0] and bad(args[0]): hits.append((ev, str(args[0]))); raise PermissionError("GUARD audit " + ev)
    if ev == "subprocess.Popen" and any(bad(str(x)) for x in (args[1] if isinstance(args[1], (list, tuple)) else [args[1]])): hits.append((ev, str(args[1]))); raise PermissionError("GUARD popen")
sys.addaudithook(audit)
# self-test of the guard
sept = "/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-Q4.gguf"
from pathlib import Path
for label, fn in (("os.stat", lambda: os.stat(sept)), ("Path.is_file", lambda: Path(sept).is_file()), ("open", lambda: open(sept, "rb")), ("os.path.exists", lambda: os.path.exists(sept))):
    n0 = len(hits)
    try: fn()
    except OSError: pass
    if len(hits) == n0: print("GUARD SELFTEST FAILED to record a hit:", label); sys.exit(9)   # exists()/is_file() swallow OSError, so the HIT LIST is the criterion
hits.clear(); print("guard self-test OK (stat / Path.is_file / open / exists all raise on the Sept path)", flush=True)
script = sys.argv[1]; sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(script))
rc = 0
try: runpy.run_path(script, run_name="__main__")
except SystemExit as e: rc = e.code or 0
print("GUARD HITS:", json.dumps(hits)); sys.exit(rc)
