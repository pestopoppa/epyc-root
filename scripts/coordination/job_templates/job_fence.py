#!/usr/bin/python3
"""Shared job write-fence + smoke admission (replaces the vendored write_fence.py / smoke_admission.py /
smoke_root_exec.py copies; operator decision 2026-11-06, friction review Pass 4 change 3b).

Deployed at /mnt/raid0/llm/tmp/compute-flags/bin/job_templates/job_fence.py; source of truth
scripts/coordination/job_templates/job_fence.py. Rows IMPORT or EXEC this file; they never copy it.

Fixes carried over from yarn-oolong v41/v42-gpu (port_v41_gpu.py, bump_v42.py), each of which cost a failed GPU run:
  1. GPU-token rows (`--gpu`): Landlock allows WRITE_FILE on /dev/kfd and beneath /dev/dri (HIP opens renderD* O_RDWR).
     The CPU-era template denied them -> "no ROCm-capable device" -> rc78.
  2. HIP gets a writable TMPDIR inside the fenced tree (comgr makes/removes comgr-* dirs at first kernel load;
     MAKE_DIR denied -> 'ROCm error: out of memory').
  3. Affinity admission is "every thread's cpus SUBSET OF the grant", not "exactly 2 cpus"; a ROCr runtime thread born
     with full-host affinity is re-pinned into the grant, refused only if the re-pin does not hold.
  4. Output scans tolerate HIP temp entries (comgr-*) vanishing mid-scan; any other vanish still fails.

CLI:
  job_fence.py fence [--gpu] <writable-dir>... -- /abs/exe args...     # exec under the fence
  job_fence.py smoke [--gpu] <smoke-root> -- /abs/exe args...           # smoke: only <smoke-root> + /dev/null (+gpu)
  Env MAX_FILE_MIB (default 128, max 8192) sets the per-file size limit; output dirs allow mkdir/rm recursively.
  job_fence.py admit --cpus 20,21 [--granted 20-23,116-119]             # smoke admission check, prints JSON
"""
import ctypes
import json
import os
import re
import resource
import shutil
import sys
import time
from pathlib import Path

# Landlock (ABI >= 3)
SYS_CREATE, SYS_ADD_RULE, SYS_RESTRICT = 444, 445, 446
PR_SET_NO_NEW_PRIVS = 38
WRITE_FILE, REMOVE_DIR, REMOVE_FILE, MAKE_DIR, MAKE_REG, TRUNCATE = 1 << 1, 1 << 4, 1 << 5, 1 << 7, 1 << 8, 1 << 14
HANDLED = sum(1 << i for i in (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14))
ALLOW = WRITE_FILE | MAKE_REG | TRUNCATE
OUT_ALLOW = ALLOW | MAKE_DIR | REMOVE_FILE | REMOVE_DIR  # declared output dirs, recursive (rocprofv3 trace/.rocprofv3)
TMP_ALLOW = ALLOW | REMOVE_DIR | REMOVE_FILE | MAKE_DIR
GPU_DEV = ("/dev/kfd", "/dev/dri")
TMP_ROOT = "/mnt/raid0/llm/tmp/"
HIP_TMP_MARKERS = ("comgr-",)
FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")
DISK_FLOOR = 151 * 1024 ** 3
MIB = 1024 ** 2
FSIZE_CAP = 128 * MIB
MAX_FILE_MIB_DEFAULT, MAX_FILE_MIB_CEILING = 128, 8192


class Ruleset(ctypes.Structure):
    _fields_ = [("access", ctypes.c_uint64)]


class PathBeneath(ctypes.Structure):
    _fields_ = [("access", ctypes.c_uint64), ("fd", ctypes.c_int32)]


def _lib():
    return ctypes.CDLL(None, use_errno=True)


def _add(lib, fd, path, rights, directory=False):
    flags = os.O_PATH | os.O_NOFOLLOW | (os.O_DIRECTORY if directory else 0)
    d = os.open(path, flags)
    try:
        rule = PathBeneath(rights, d)
        if lib.syscall(SYS_ADD_RULE, fd, 1, ctypes.byref(rule), 0):
            raise OSError(ctypes.get_errno(), f"landlock rule {path}")
    finally:
        os.close(d)


def hip_tmpdir(base):
    """Create <base>/.hip-tmp (inside the fence) and return it. Callers export it as TMPDIR."""
    p = Path(base) / ".hip-tmp"
    p.mkdir(mode=0o700, exist_ok=True)
    return str(p)


def gpu_rules(lib, fd, devices=GPU_DEV, tmpdir=None):
    """GPU-token rows: /dev/kfd + beneath /dev/dri writable, and TMPDIR (if under TMP_ROOT) gets mkdir/rm rights."""
    for name in devices:
        _add(lib, fd, name, WRITE_FILE)
    tmp = tmpdir if tmpdir is not None else os.environ.get("TMPDIR", "")
    if (tmp and os.path.isabs(tmp) and os.path.isdir(tmp) and not os.path.islink(tmp)
            and os.path.realpath(tmp).startswith(TMP_ROOT)):
        _add(lib, fd, tmp, TMP_ALLOW, directory=True)


def apply(paths, gpu=False, extra=(), devices=GPU_DEV, tmpdir=None, lib=None):
    """Restrict this process: writes only beneath `paths` (+ `extra` (path, rights) pairs; + GPU rules if gpu)."""
    lib = lib or _lib()
    if lib.syscall(SYS_CREATE, 0, 0, 1) < 3:
        raise RuntimeError("Landlock ABI below 3")
    rs = Ruleset(HANDLED)
    fd = lib.syscall(SYS_CREATE, ctypes.byref(rs), ctypes.sizeof(rs), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "landlock ruleset")
    try:
        for name in paths:
            p = Path(name)
            if not p.is_absolute() or p.is_symlink() or not p.is_dir():
                raise ValueError(f"invalid output directory {name}")
            _add(lib, fd, p, OUT_ALLOW, directory=True)
        for path, rights in extra:
            _add(lib, fd, path, rights)
        if gpu:
            gpu_rules(lib, fd, devices, tmpdir)
        if lib.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) or lib.syscall(SYS_RESTRICT, fd, 0):
            raise OSError(ctypes.get_errno(), "landlock restrict")
    finally:
        os.close(fd)


THREAD_ENV = ("OMP_NUM_THREADS", "AUTOKERNEL_BACKEND_THREADS", "AUTOKERNEL_CPU_N_THREADS", "GGML_N_THREADS",
              "LLAMA_ARG_THREADS")


def affinity_threads(getaff=os.sched_getaffinity):
    """N = number of logical CPUs in this process's affinity mask (NOT physical cores: a grant such as 184-191 is
    8 SMT-sibling CPUs and ggml/OMP schedule one thread per logical CPU). hardware_concurrency() ignores affinity
    and returns 192, so test-backend-ops / ggml CPU reference packed 192 threads onto 8 CPUs."""
    return max(1, len(getaff(0)))


def set_thread_defaults(env=None, getaff=os.sched_getaffinity):
    """Set THREAD_ENV to affinity_threads() in `env` (default os.environ) without overriding existing values."""
    env = os.environ if env is None else env
    n = str(affinity_threads(getaff))
    for k in THREAD_ENV:
        env.setdefault(k, n)
    return env


def max_file_mib(spec=None, env=None):
    """Per-row RLIMIT_FSIZE in MiB: row spec `max_file_mib`, else env MAX_FILE_MIB, else 128; clamped to [1, 8192]."""
    env = os.environ if env is None else env
    raw = (spec or {}).get("max_file_mib", env.get("MAX_FILE_MIB", MAX_FILE_MIB_DEFAULT))
    try:
        v = int(raw)
    except (TypeError, ValueError):
        v = MAX_FILE_MIB_DEFAULT
    return max(1, min(v, MAX_FILE_MIB_CEILING))


def summary_line(mib, dirs):
    return (f"job_fence: write fence allows {', '.join(dirs)}; file size limit {mib} MiB; "
            f"EACCES or SIGXFSZ means the fence denied it (set max_file_mib for size)")


def _exec(argv, env, dirs=(), spec=None):
    """Print the fence summary once, set RLIMIT_FSIZE, then EXEC argv: the job KEEPS this pid (and process group).
    PID identity is load-bearing: rows prove ownership of the server by Popen pid (socket inodes in /proc/<pid>/fd,
    own-PID KFD, /proc/<pid>/maps). Never fork/wait here. No post-exit message: nothing survives the exec.
    JOB_FENCE_PID (== the fence pid == the job pid) is exported in the job env."""
    mib = max_file_mib(spec, env)
    print(summary_line(mib, [str(d) for d in dirs]), file=sys.stderr, flush=True)
    resource.setrlimit(resource.RLIMIT_FSIZE, (mib * MIB, mib * MIB))
    env = dict(env, JOB_FENCE_PID=str(os.getpid()))
    os.execve(argv[0], argv, env)


def _split(args):
    if "--" not in args:
        raise ValueError("missing -- before command")
    i = args.index("--")
    head, argv = args[:i], args[i + 1:]
    gpu = "--gpu" in head
    head = [a for a in head if a != "--gpu"]
    if not argv or not Path(argv[0]).is_absolute():
        raise ValueError("absolute executable required")
    return head, argv, gpu


def fence_main(args):
    paths, argv, gpu = _split(args)
    env = set_thread_defaults(dict(os.environ))
    if gpu and not paths:
        raise ValueError("--gpu needs at least one writable dir for the HIP TMPDIR")
    if gpu:
        env["TMPDIR"] = hip_tmpdir(paths[0])
    apply(paths, gpu=gpu, tmpdir=env.get("TMPDIR"))
    return _exec(argv, env, paths)


def smoke_main(args):
    head, argv, gpu = _split(args)
    if len(head) != 1:
        raise ValueError("smoke takes exactly one smoke root")
    root = Path(head[0])
    if not root.is_dir() or root.is_symlink() or not root.is_absolute():
        raise ValueError("smoke root must be an absolute real directory")
    env = set_thread_defaults(dict(os.environ, TMPDIR=str(root)))
    apply([root], gpu=gpu, extra=[("/dev/null", WRITE_FILE | TRUNCATE)], tmpdir=str(root))
    return _exec(argv, env, [str(root)])


# ------------------------------------------------------------------ admission
def parse_cpulist(text):
    out = set()
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def affinity_subset(cpus, granted):
    """The admission rule: a non-empty cpu set inside the grant (NOT 'exactly two cpus')."""
    cpus = set(cpus)
    return bool(cpus) and cpus <= set(granted)


def repin_threads(pid, granted, getaff=os.sched_getaffinity, setaff=os.sched_setaffinity, proc="/proc"):
    """Re-pin every thread of `pid` whose affinity escapes `granted` (ROCr spawns one with all host cpus).
    Returns the tids that still escape after the re-pin (empty = admitted). Threads that exit mid-walk are skipped."""
    granted = set(granted)
    escaped = []
    try:
        tids = [int(t) for t in os.listdir(os.path.join(proc, str(pid), "task"))]
    except FileNotFoundError:
        return escaped
    for tid in tids:
        try:
            if getaff(tid) <= granted:
                continue
            setaff(tid, granted)
            if not getaff(tid) <= granted:
                escaped.append(tid)
        except (ProcessLookupError, FileNotFoundError):
            continue
    return escaped


def check(cpus, granted=None, flags=FLAGS, disk_path=None, floor=DISK_FLOOR, own=None):
    """Smoke admission. Fail closed on: own affinity outside the grant, a global HOLD, disk below the floor."""
    cpus = set(cpus)
    granted = set(granted) if granted is not None else cpus
    own = set(os.sched_getaffinity(0)) if own is None else set(own)
    if not affinity_subset(cpus, granted) or not affinity_subset(own, granted):
        raise RuntimeError(f"smoke affinity outside grant: own={sorted(own)} granted={sorted(granted)}")
    if [h for h in Path(flags).glob("HOLD_*") if re.fullmatch(r"HOLD_[A-Za-z0-9_-]+", h.name) and h.is_file()]:   # exact
        # names only (rowflow.operator_holds, 2026-11-07): a renamed HOLD_X.lifted-symlink / .disabled never holds
        raise RuntimeError("global HOLD")
    if shutil.disk_usage(disk_path or Path(__file__).resolve().parent).free < floor:
        raise RuntimeError("disk below 150 GiB floor plus 1 GiB output reserve")
    return {"kind": "rowflow-owner-smoke", "cpus": sorted(cpus), "granted": sorted(granted), "checked_epoch": time.time()}


# ------------------------------------------------------------------ output scans
def is_hip_temp(rel):
    return any(part.startswith(HIP_TMP_MARKERS) or part == ".hip-tmp" for part in Path(rel).parts)


def tree_usage(root):
    """(bytes, entries) under root. Entries vanishing mid-scan are skipped only inside HIP temp subtrees."""
    root = Path(root)
    total = count = 0

    def onerror(e):
        fn = getattr(e, "filename", "") or ""
        if isinstance(e, FileNotFoundError) and is_hip_temp(os.path.relpath(fn, root)):
            return
        raise e

    for parent, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        for n in files:
            p = Path(parent) / n
            count += 1
            try:
                st = p.lstat()
            except FileNotFoundError:
                if is_hip_temp(p.relative_to(root)):
                    continue
                raise
            total += max(st.st_size, st.st_blocks * 512)
        count += len(dirs)
    return total, count


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__, file=sys.stderr)
        return 64
    cmd, rest = argv[0], argv[1:]
    if cmd == "fence":
        return fence_main(rest)
    elif cmd == "smoke":
        return smoke_main(rest)
    elif cmd == "admit":
        import argparse
        ap = argparse.ArgumentParser(prog="job_fence.py admit")
        ap.add_argument("--cpus", required=True)
        ap.add_argument("--granted")
        a = ap.parse_args(rest)
        cpus = parse_cpulist(a.cpus)
        print(json.dumps(check(cpus, parse_cpulist(a.granted) if a.granted else None)))
        return 0
    else:
        print(f"unknown command {cmd}", file=sys.stderr)
        return 64
    return 0


if __name__ == "__main__":
    sys.exit(main())
