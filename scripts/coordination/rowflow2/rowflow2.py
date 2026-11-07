#!/usr/bin/env python3
"""rowflow2 - the minimal compute-keeper scheduler (SHADOW-ONLY build, 2026-11-05).

Design: docs/reports/coordination/keeper-friction-review-20261105.md, Pass 3 (P3.4-P3.7). Owner:
operator-adhoc-rowflow2 (operator decision 2026-11-05 "Freeze current + build rowflow2").

The model, in full:
  * Resources are tokens: cores c0..c95 (SMT sibling c+96 follows its core), `gpu` (the MI210 together with its host
    threads 184-191, which are therefore never CPU tokens), and two counters (ram_gib, disk_gib). A quarter `qN` is
    only shorthand for cores 24N..24N+23, expanded when the spec is read. The smoke lane (SMOKE_CORES) is never a row
    token.
  * A row DECLARES what it needs (SPEC_FIELDS). Nothing is inferred from job text, argv, OMP or regexes - ever.
  * A grant is the declaration stamped with a window. The tick is reconcile() -> admit() -> file(); smokes run FIFO,
    one at a time, on the fixed smoke lane with a deadline, and never produce a COMPLETE.

Pure core (tests drive these): parse_cpus, grant_need, validate, map_legacy, admit, reconcile, smoke_step, file_decisions.
IO adapters: load_world, tick (live mode; used only by the tests' temp flags dir), shadow, diff, status, map-report.
In shadow mode a process-wide audit hook refuses every write-intent filesystem event under the flags dir.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import glob
import hashlib
import itertools
import json
import os
import re
import shlex
import sys
import time
from dataclasses import dataclass, field, replace

# ============================================================== tunables (exactly eight - P3.7)
SMOKE_CORES = frozenset(range(20, 24))  # fixed smoke lane c20-23 (+ siblings 116-119); never granted to a row
IDLE_SAMPLES = 2                         # consecutive samples before an idle core / unused gpu / dead poller acts
IDLE_PCT = 2.0                           # a core below this % busy (both SMT threads) is idle in a sample
SMOKE_DEADLINE_S = 1200                  # a smoke past this is killed and FAILs (deadline)
OVERRUN_FACTOR = 1.5                     # grant window = factor x max(estimate_s, min_window_s); overrun alert at factor x estimate
QUIET_MAX_RANK = 10                      # quiet: true needs priority_rank < this (or an operator quiet_reason)
FILE_OWNERLESS_S = 1200                  # an unclaimed prose-rule .ended older than this is routed owner-less
CLAIM_TTL_S = 7200                       # a filing claim older than this without .FILED re-opens the row
IDLE_HELD_S = 900                        # a grant wholly idle (every core < IDLE_PCT, no own KFD pid) this long ends rc=75 and
                                         # is re-queued; the owner is warned at IDLE_HELD_S // 3 (operator 2026-11-05,
                                         # rock-aiter-tests-r3 held the MI210 20 min at 0%). The 9th tunable: the 8 were
                                         # kept, nothing else expresses a wall-clock idle budget.
TUNABLES = ("SMOKE_CORES", "IDLE_SAMPLES", "IDLE_PCT", "SMOKE_DEADLINE_S", "OVERRUN_FACTOR", "QUIET_MAX_RANK",
            "FILE_OWNERLESS_S", "CLAIM_TTL_S", "IDLE_HELD_S")

# ============================================================== config (paths / env - not tunables)
FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/" + "tmp/compute-flags")
KFD_PROC = os.environ.get("ROWFLOW2_KFD_PROC", "/sys/class/kfd/kfd/proc")
PROC = os.environ.get("ROWFLOW2_PROC", "/proc")
RAM_BOOKABLE_GIB = float(os.environ.get("ROWFLOW2_RAM_GIB", "1069"))     # rowflow QUARTER_RAM_GIB x 4, rounded
DISK_PATH = os.environ.get("ROWFLOW2_DISK_PATH", "/mnt/raid0")
DISK_FLOOR_GIB = float(os.environ.get("ROWFLOW2_DISK_FLOOR_GIB", "150"))  # == filler_run15 FILLER_DISK_FLOOR_GIB
GPU_BUSY_GLOB = os.environ.get("ROWFLOW2_GPU_BUSY_GLOB", "/sys/class/drm/card*/device/gpu_busy_percent")  # amdgpu utilisation
CONFIG = ("FLAGS", "KFD_PROC", "PROC", "RAM_BOOKABLE_GIB", "DISK_PATH", "DISK_FLOOR_GIB", "GPU_BUSY_GLOB")

# ============================================================== host facts + vocabulary (not tunables)
NCORES = 96
GPU_HOST_THREADS = frozenset(range(184, 192))   # part of the gpu token
GPU_SIBLING_CORES = frozenset(c - 96 for c in GPU_HOST_THREADS)   # 88-95: their SMT siblings are the gpu host threads
QUARTERS = tuple(frozenset(range(24 * q, 24 * q + 24)) - SMOKE_CORES for q in range(4))
ROW_CORES = frozenset(range(NCORES)) - SMOKE_CORES
SCHEMA = "epyc.row.v4"
LEGACY_SCHEMA = "epyc.row.v3"
GPU_MODES = ("none", "shared", "exclusive")
ENDED_REASONS = ("complete", "exit", "stopped", "superseded", "withdrawn", "dead-poller", "disk-floor", "window-end", "idle-held")
IDLE_WARN_S = IDLE_HELD_S // 3                  # derived, not a tunable: the owner warning (300 s) precedes the end (900 s)
IDLE_HELD_RETRY = 1                             # fixed rule: one re-queue after an idle-held end; the second end is terminal
# ---- Pass 4 rules (keeper-friction-review-20261105.md P4.3 #1, #2, #4; INF-22 GPU ordering 2026-11-06). Each carries a
# switch so its test has a NEGATIVE CONTROL (the old path must fail the new assertion); the switches are facts, not tunables.
PARK_ON_REFUSAL = True       # P4.3 #1: an admission refusal (launcher precond / not-engine / grant released unrun) parks the
                             # row ONCE: one FAIL-refused record, one alert; retried only after its launcher or spec sha
                             # changes or an operator `unpark`. False = the pre-P4 path (re-granted every tick, a FAIL per tick).
REFUSAL_RCS = {12: "precond", 15: "launcher-not-engine", 5: "build-missing"}   # rc -> refusal kind (filler_run15 / grant_ok_launcher)
REFUSAL_REASONS = ("build-missing", "not-ready", "precond", "released")        # .ended reason bases that are refusals
COMPLETE_BEATS_DEAD = True   # P4.3 #2: a dead poller whose row holds a completion receipt (.complete, or .ended rc=0
                             # reason=complete) is a COMPLETION, never a dead-poller rc=75 (11 of 11 live rc=14 were false)
GPU_IDLE_BY_GPU_SIGNALS = True   # P4.3 #4: a gpu-token grant is busy/idle by its own KFD pid set + GPU utilisation only;
                                 # CPU % never judges it (no release-cores / over-declared / idle-held by CPU for gpu grants)
GPU_IDLE_PCT = 5.0           # GPU utilisation below this reads idle in a sample (sysfs gpu_busy_percent is integer %)
RANK_AT_GRANT_TIME = True    # INF-22 2026-11-06: once the device is quiet, the best-RANKED grantable GPU row is granted,
                             # re-ranked at grant time over every grantable row; False = first grantable row in id order
SMOKE_RANK_GATE = True       # keeper batch 2026-11-06: a GPU row ranked worse than a queued GPU smoke waits (WAIT-FOR-SMOKE);
                             # False = the old path (ready rows ignore the smoke queue's rank)
VRAM_SAMPLE_S = 1            # residency sampled at 1 s (was 5 s: a short job fell between samples)
RESIDENCY_SCHEMA = "epyc.rowflow.residency.v1"
RESIDENCY_MIN_BYTES = 64 << 20
SPEC_FIELDS = {"id": str, "owner": str, "handoff_task": str, "launcher": str, "stop_file": str, "cpus": (int, str),
               "threads": int, "gpu": str, "quiet": bool, "ram_gib": (int, float), "disk_gib": (int, float),
               "estimate_s": (int, float), "min_window_s": (int, float), "decision_rule": str,
               "priority_rank": (int, float)}
SPEC_OPTIONAL = {"quiet_reason": str, "measured_ack": str, "supersedes": (str, list), "fix_ref": str,
                 "published_at": str, "schema": str, "legacy": dict, "timing": bool, "width_justification": str, "smoke_predicate": str}
FACTS = ("NCORES", "GPU_HOST_THREADS", "GPU_SIBLING_CORES", "QUARTERS", "ROW_CORES", "SCHEMA", "LEGACY_SCHEMA", "GPU_MODES",
         "ENDED_REASONS", "SPEC_FIELDS", "SPEC_OPTIONAL", "FACTS", "TUNABLES", "CONFIG", "IDLE_WARN_S", "IDLE_HELD_RETRY",
         "PARK_ON_REFUSAL", "REFUSAL_RCS", "REFUSAL_REASONS", "COMPLETE_BEATS_DEAD", "GPU_IDLE_BY_GPU_SIGNALS", "GPU_IDLE_PCT",
         "RANK_AT_GRANT_TIME", "SMOKE_RANK_GATE", "VRAM_SAMPLE_S", "RESIDENCY_SCHEMA", "RESIDENCY_MIN_BYTES")


# ============================================================== util
def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    for f in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z"):
        try:
            return dt.datetime.strptime(s, f).timestamp()
        except ValueError:
            pass
    return None


def load_json(path):
    try:
        with open(path) as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


_ENGINE_RE = re.compile(r"filler_run(\d+)\.sh$")
_ABS_TOKEN = re.compile(r"(?<![\w.])(/[^\s'\"`;|&()<>]+)")


def launcher_refs(path):
    """Port of rowflow parse_launcher + referenced_paths (K:347, K:601), file-reference rule only: the absolute, existing
    paths the filler engine line executes or uses (engine, --cmd / --complete-cmd tokens, --workdir) after resolving the
    launcher's top-level VAR= assignments and $(dirname "$0"). No engine line -> [] (the launcher alone is hashed)."""
    text = open(path, errors="replace").read()
    assigns = {m[1]: m[3] for m in re.finditer(r'^(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)=("?)([^\n"]*)\2\s*$', text, re.M)}
    assigns.setdefault("HERE", os.path.dirname(path))

    def expand(x):
        for _ in range(3):
            x = re.sub(r"\$\{([A-Za-z_][A-Za-z_0-9]*)(?::[-?][^}]*)?\}|\$([A-Za-z_][A-Za-z_0-9]*)",
                       lambda m: assigns.get(m.group(1) or m.group(2), m.group(0)), x)
            x = x.replace('$(dirname "$0")', os.path.dirname(path)).replace("$(dirname $0)", os.path.dirname(path))
        return x
    line = next((el for el in (expand(l) for l in re.sub(r"\\\n", " ", text).splitlines())
                 if re.search(r"filler_run\d+\.sh", el) and "--id" in el), None)
    if not line:
        return []
    toks = shlex.split(line, comments=True)
    i = next((i for i, t in enumerate(toks) if _ENGINE_RE.search(t)), None)
    if i is None:
        return []
    o, opt = {"engine": toks[i], "workdir": "/workspace"}, {"--cmd": "cmd", "--complete-cmd": "complete_cmd", "--workdir": "workdir"}
    for j in range(i + 1, len(toks) - 1):
        if toks[j] in opt:
            o[opt[toks[j]]] = toks[j + 1]
    out = []
    for v in (o.get("engine", ""), o.get("cmd", ""), o.get("complete_cmd", ""), o.get("workdir", "")):
        for t in _ABS_TOKEN.findall(" " + str(v)):
            t = t.rstrip("/.,:") or t
            if os.path.exists(t) and t not in out:
                out.append(t)
    return out


def job_sha(launcher_path, sha_cache=None):
    """sha256 over the launcher and every existing file it references (rowflow job_sha, K:255, operator 2026-11-06): a
    changed job.py under an unchanged launcher is a new attempt. Raises OSError when the launcher is unreadable."""
    sha_cache = {} if sha_cache is None else sha_cache
    try:
        refs = launcher_refs(launcher_path)
    except (ValueError, StopIteration):
        refs = []
    files = sorted({os.path.realpath(x) for x in refs if os.path.isfile(x)} | {os.path.realpath(launcher_path)})
    parts = []
    for f in files:
        st = os.stat(f)
        key = (f, st.st_mtime, st.st_size)
        parts.append(f"{f} {sha_cache.get(key) or sha_cache.setdefault(key, sha256(f))}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def head1(path):
    try:
        with open(path, errors="replace") as f:
            return f.readline().strip()
    except OSError:
        return ""


def cpulist(cores):
    """Compress cores to '48-51,60' (cores only; siblings are implied)."""
    out, run = [], []
    for c in sorted(cores):
        if run and c == run[-1] + 1:
            run.append(c)
        else:
            if run:
                out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]))
            run = [c]
    if run:
        out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]))
    return ",".join(out)


def taskset_list(cores, gpu):
    """The cpu list a filler pins: each core + its SMT sibling, except siblings that belong to the gpu token; the gpu
    token adds its host threads."""
    ts = set(cores) | {c + NCORES for c in cores if c + NCORES not in GPU_HOST_THREADS}
    if gpu != "none":
        ts |= GPU_HOST_THREADS
    return cpulist(ts)


# ============================================================== shadow write guard (enforced, not advisory)
_GUARD_ROOTS: list = []
_WRITE_EVENTS = {"os.rename", "os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.utime", "os.link",
                 "os.symlink", "os.truncate", "shutil.rmtree", "shutil.copyfile", "shutil.move"}
_WFLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


class ShadowWriteRefused(PermissionError):
    pass


def _under_guard(p):
    try:
        p = os.path.realpath(os.fsdecode(p)) if not isinstance(p, int) else None
    except (TypeError, ValueError):
        return False
    return bool(p) and any(p == r or p.startswith(r + os.sep) for r in _GUARD_ROOTS)


def _audit(event, args):
    if not _GUARD_ROOTS:
        return
    if event == "open":
        path, mode, flags = (list(args) + [None, None, None])[:3]
        w = (isinstance(mode, str) and any(ch in mode for ch in "wax+")) or (isinstance(flags, int) and flags & _WFLAGS)
        if w and _under_guard(path):
            raise ShadowWriteRefused(f"shadow mode: refusing write-open of {path}")
    elif event in _WRITE_EVENTS:
        for a in args[:2]:
            if isinstance(a, (str, bytes, os.PathLike)) and _under_guard(a):
                raise ShadowWriteRefused(f"shadow mode: refusing {event} on {a}")


sys.addaudithook(_audit)


def guard_readonly(root):
    """Arm the guard: from now on no write-intent filesystem event may touch `root` in this process."""
    r = os.path.realpath(root)
    if r not in _GUARD_ROOTS:
        _GUARD_ROOTS.append(r)


def unguard():
    _GUARD_ROOTS.clear()


def write_text(path, text, append=False):
    """Every rowflow2 write goes through here (the audit hook backs it up for anything that does not)."""
    if _under_guard(path):
        raise ShadowWriteRefused(f"shadow mode: refusing write to {path}")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if append:
        with open(path, "a") as f:
            f.write(text)
        return
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


# ============================================================== token algebra
@dataclass(frozen=True)
class Need:
    options: tuple | None   # explicit alternatives (concrete set = 1 option; any-quarter = the quarters)
    pool: frozenset          # for "pick width cores from pool" needs
    width: int | None        # None for option needs (width = |option|)
    fixed: frozenset = frozenset()   # cores every grant of a width need must also hold (gpu-q3 NARROW: 88-95); never in pool

    def min_width(self):
        return (self.width + len(self.fixed)) if self.options is None else min(len(o) for o in self.options)

    def allowed(self):
        return (self.pool if self.options is None else frozenset().union(*self.options)) | self.fixed


def _expand(text):
    out = set()
    for p in (x.strip() for x in str(text).split(",")):
        if not p:
            continue
        m = re.fullmatch(r"q([0-3])", p)
        if m:
            out |= set(range(24 * int(m[1]), 24 * int(m[1]) + 24))
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", p)
        if not m:
            raise ValueError(f"bad cpu item {p!r}")
        a, b = int(m[1]), int(m[2] or m[1])
        if b < a or b >= 2 * NCORES:
            raise ValueError(f"bad cpu range {p!r}")
        for c in range(a, b + 1):
            if c in GPU_HOST_THREADS:
                raise ValueError("threads 184-191 belong to the gpu token, not to cpus")
            out.add(c % NCORES)
    return frozenset(out)


def parse_cpus(v):
    """cpus: int N (any N row cores) | "48-71" / "q2" / "q0,q1" (concrete) | "any-quarter" | "any-quarter-of-q0,q1"
    | "any-N-of-<concrete>". The smoke lane is carved out of every expansion. Raises ValueError."""
    if isinstance(v, bool):
        raise ValueError("cpus must be int or str")
    if isinstance(v, int):
        if not 0 <= v <= len(ROW_CORES):
            raise ValueError(f"cpus {v} out of range 0..{len(ROW_CORES)}")
        return Need(None, ROW_CORES, v) if v else Need((frozenset(),), frozenset(), None)
    s = str(v).strip()
    if s == "any-quarter":
        return Need(QUARTERS, ROW_CORES, None)
    m = re.fullmatch(r"any-([23])-quarters", s)   # emergency 2026-11-06 (mirrors rowflow): N whole quarters, q0-q2 combinations first
    if m:
        combos = sorted(itertools.combinations(range(4), int(m[1])), key=lambda c: (3 in c, c))
        return Need(tuple(frozenset().union(*[QUARTERS[i] for i in c]) for c in combos), ROW_CORES, None)
    m = re.fullmatch(r"any-quarter-of-(q[0-3](?:,q[0-3])*)", s)
    if m:
        return Need(tuple(QUARTERS[int(x[1])] for x in sorted(set(m[1].split(",")))), ROW_CORES, None)
    m = re.fullmatch(r"any-(\d+)-of-(.+)", s)
    if m:
        pool, n = _expand(m[2]) - SMOKE_CORES, int(m[1])
        if not 0 < n <= len(pool):
            raise ValueError(f"cpus {s!r}: width {n} not in 1..{len(pool)}")
        return Need(None, pool, n)
    cores = _expand(s) - SMOKE_CORES
    if not cores:
        raise ValueError(f"cpus {s!r} is empty after carving the smoke lane")
    return Need((cores,), cores, None)


def timing_need(need):
    """A timing row without the gpu token may not use cores 88-95: their SMT siblings are the gpu host threads, which
    it cannot hold (inc. INF22 2026-11-05: q3 timing grant shared physical cores with a 27B reload). None if nothing
    is left."""
    if need.options is not None:
        opts = tuple(o for o in need.options if not (o & GPU_SIBLING_CORES))
        return Need(opts, need.pool - GPU_SIBLING_CORES, None) if opts else None
    pool = need.pool - GPU_SIBLING_CORES
    return Need(None, pool, need.width) if len(pool) >= need.width else None


def quiet_ok_cores(need):
    return timing_need(need) is not None


def gpu_timing_need(need):
    """gpu-q3 NARROW (operator 2026-11-05 "Narrow + emergency deploy"): a gpu-EXCLUSIVE (timing) row also holds cores
    88-95 - the SMT siblings of the gpu host threads 184-191 it runs on - and NEVER the rest of q3: 72-87 stay grantable
    to CPU rows beside it. A gpu-shared row (correctness, production) holds the gpu token alone. Origin: q38p4b-int8
    (GPU timing) refused "q3 busy" by an 8-core AITER build on 80-87 while the keeper booked all of q3 for it."""
    if need.options is not None:
        opts = tuple(dict.fromkeys(o | GPU_SIBLING_CORES for o in need.options))
        return Need(opts, need.pool | GPU_SIBLING_CORES, None)
    return Need(None, need.pool - GPU_SIBLING_CORES, need.width, GPU_SIBLING_CORES)


_Q3_CORES = QUARTERS[3]
_MULTI_QUARTER_MIN_WIDTH = max(len(q) for q in QUARTERS) + 1   # wider than any one quarter: the grant spans quarters


def cpu_multi_quarter_need(need):
    """operator 2026-11-06 "Yes, both": a CPU row's multi-quarter booking uses q0-q2 ONLY. q3's cores 88-95 are the physical
    cores behind the gpu host threads 184-191 (inc. lsa-quality-32k-r5-pca granted q1+q3: c7-q38-ppl-bisect-r5 waited 600 s
    on q3, rc75, MI210 idle ~40 min). A width need wider than one quarter drops q3 from its pool and waits for q0-q2 when
    they are busy; a host-wide width that cannot fit q0-q2 (> 3 quarters) and concrete / one-quarter needs are unchanged."""
    if need.options is not None:   # any-N-quarters (legacy accepted multi-quarter(N)): drop every option touching q3
        multi = [o for o in need.options if len(o) >= _MULTI_QUARTER_MIN_WIDTH]
        if len(need.options) > 1 and multi and len(multi) == len(need.options):
            opts = tuple(o for o in need.options if not (o & _Q3_CORES))
            if opts:
                return Need(opts, need.pool - _Q3_CORES, None)
        return need
    if need.width is None or need.width < _MULTI_QUARTER_MIN_WIDTH:
        return need
    pool = need.pool - _Q3_CORES
    return Need(None, pool, need.width, need.fixed) if len(pool) >= need.width else need


def grant_need(s):
    """The Need admit() grants for spec s: parse_cpus, then the timing SMT rule (no 88-95 without the gpu exclusive;
    None when nothing is left), then gpu-q3 NARROW (gpu exclusive, not quiet: + 88-95). A quiet row takes every core."""
    need = parse_cpus(s["cpus"])
    if s["gpu"] == "none" and not s["quiet"]:
        need = cpu_multi_quarter_need(need)
    if s.get("timing") and s["gpu"] != "exclusive" and not s["quiet"]:
        need = timing_need(need)
        if need is None:
            return None
    if is_gpu_timing(s):
        need = gpu_timing_need(need)
    return need


def is_gpu_timing(s):
    """decision 10 (2026-11-07): only a GPU TIMING row holds 88-95 beside the gpu - `timing: true` (legacy block-timing-*)
    or legacy shape gpu-q3. A class-less legacy `shape: gpu` row stays gpu-exclusive (decision 1) but holds gpu + 184-191
    only, as in the keeper (SKILL.md: shape gpu = GPU + 184-191, q3 stays grantable)."""
    return (s["gpu"] == "exclusive" and not s["quiet"]
            and bool(s.get("timing") or (s.get("legacy") or {}).get("shape") == "gpu-q3"))


def fits_need(need, cores):
    """Two-sided invariant (i): is `cores` a legal grant for `need`?"""
    cores = frozenset(cores)
    if need.options is not None:
        return cores in need.options
    rest = cores - need.fixed
    return need.fixed <= cores and len(rest) == need.width and rest <= need.pool


# ============================================================== schema + publish-time admission (P3.5)
_RULE_NODES = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.Compare, ast.Name, ast.Load,
               ast.Constant, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Tuple, ast.List)


def machine_rule(text):
    """A decision_rule the keeper can evaluate itself: a boolean expression over `rc` and `reason` only."""
    try:
        tree = ast.parse(str(text).strip(), mode="eval")
    except (SyntaxError, ValueError):
        return None
    for n in ast.walk(tree):
        if not isinstance(n, _RULE_NODES) or (isinstance(n, ast.Name) and n.id not in ("rc", "reason")):
            return None
    return compile(tree, "<decision_rule>", "eval")


def validate(spec, pred=None, launcher_exists=os.path.isfile):
    """All refusal reasons for a spec ([] = admitted). `pred` = the predecessor's measured record
    {busy_p95, cpus} (from its .ended) for the measured-busy feedback check. O(1); no job text is read."""
    errs = []
    for k, t in SPEC_FIELDS.items():
        if k not in spec:
            errs.append(f"missing {k}")
        elif not isinstance(spec[k], t) or (t is int and isinstance(spec[k], bool)):
            errs.append(f"{k} has type {type(spec[k]).__name__}")
    for k, v in spec.items():
        if k not in SPEC_FIELDS and k not in SPEC_OPTIONAL:
            errs.append(f"unknown field {k}")
        elif k in SPEC_OPTIONAL and not isinstance(v, SPEC_OPTIONAL[k]):
            errs.append(f"{k} has type {type(v).__name__}")
    if errs:
        return errs
    try:
        need = parse_cpus(spec["cpus"])
    except ValueError as e:
        return [f"cpus: {e}"]
    if spec["gpu"] not in GPU_MODES:
        return [f"gpu {spec['gpu']!r} not in {GPU_MODES}"]
    n = need.min_width()
    budget = n + (len(GPU_HOST_THREADS) if spec["gpu"] != "none" else 0)
    if not 1 <= spec["threads"] <= budget:                                     # 1
        errs.append(f"threads {spec['threads']} not in 1..{budget} (|cpus|={n}{' + 8 gpu host threads' if budget > n else ''})")
    if n >= 24 and spec["threads"] < 12:                                       # 2
        errs.append(f"over-declared: |cpus|={n} needs threads >= 12 (declared {spec['threads']}); declare fewer cpus")
    if n == 0 and spec["gpu"] == "none":
        errs.append("no cpus and gpu none: the row needs nothing")
    if spec["quiet"] and not (spec["priority_rank"] < QUIET_MAX_RANK or spec.get("quiet_reason")):  # 3
        errs.append(f"quiet needs priority_rank < {QUIET_MAX_RANK} or quiet_reason (rank {spec['priority_rank']:g})")
    if spec["gpu"] == "exclusive" and not (spec["estimate_s"] <= 7200 or spec.get("quiet_reason")):  # 4
        errs.append(f"gpu exclusive needs estimate_s <= 7200 or quiet_reason (estimate {spec['estimate_s']:g})")
    if spec.get("timing") and spec["gpu"] != "exclusive" and not quiet_ok_cores(need):    # 8 (SMT siblings)
        errs.append("timing row on cores 88-95 (siblings = gpu host threads 184-191) must declare gpu exclusive "
                    "(gpu-quiet); otherwise place it on q0-q2")
    wj = spec.get("width_justification")                                       # operator 2026-11-06 (mirrors rowflow)
    q012 = frozenset().union(*QUARTERS[:3])
    if wj is not None:
        if len(wj.strip()) < 20:
            errs.append("width_justification must be >= 20 characters naming why the extra width helps")
        elif n <= 24 and not (spec["gpu"] != "none" and n >= 20):   # q0 is 20 cores: the smoke lane is carved out
            errs.append(f"width_justification is for a multi-quarter CPU width; |cpus|={n} needs none")
        elif spec["quiet"] or (spec.get("timing") and spec["gpu"] == "none"):
            errs.append("width_justification never applies to quiet rows or CPU timing rows (placement rules unchanged)")
        elif spec["gpu"] != "none" and not (need.options is not None
                                           and all(o <= q012 for o in need.options)):
            errs.append("a gpu row's width_justification admits whole CPU quarters from q0-q2 only: never q3 72-87, never the whole host")
    if not os.path.isabs(spec["stop_file"]) or "$" in spec["stop_file"]:       # 5
        errs.append(f"stop_file {spec['stop_file']!r} is not an absolute literal path")
    if not launcher_exists(spec["launcher"]):                                  # 6
        errs.append(f"launcher {spec['launcher']} does not exist")
    owner = spec["owner"].strip()
    if not (machine_rule(spec["decision_rule"]) or (owner and owner != "?")):  # 7
        errs.append("decision_rule is not machine-evaluable and owner does not resolve")
    if spec["estimate_s"] <= 0 or spec["min_window_s"] < 0 or spec["ram_gib"] < 0 or spec["disk_gib"] < 0:
        errs.append("estimate_s/min_window_s/ram_gib/disk_gib out of range")
    if pred and pred.get("busy_p95") is not None and pred.get("cpus") and not spec.get("measured_ack"):
        if pred["busy_p95"] < 0.25 and n >= pred["cpus"]:
            errs.append(f"measured: predecessor used busy_p95={pred['busy_p95']:.2f} of {pred['cpus']} cpus; "
                        f"successor declares {n} - declare fewer cpus or set measured_ack")
    return errs


# ============================================================== legacy (epyc.row.v3) -> spec
_TIMING_CLASSES = ("block-timing-pairable", "block-timing-quiet")
_SHARED_CLASSES = ("correctness", "diagnostic", "block-correctness")


def map_legacy(m):
    """(spec, None) or (None, reason). Only declared fields are read - never launcher text."""
    rid = m.get("id")
    if m.get("schema") != LEGACY_SCHEMA or not rid:
        return None, f"schema {m.get('schema')!r} is not {LEGACY_SCHEMA}"
    regions, shape, ac = str(m.get("regions") or "").strip(), m.get("shape"), m.get("admission_class")
    items = [x.strip() for x in regions.split(",") if x.strip()]
    gpu_need = any(x.startswith("mi210") for x in items) or shape in ("gpu", "gpu-q3")
    keep, nums, gpu_threads = [], set(), 0
    for x in items:
        r = re.fullmatch(r"(\d+)(?:-(\d+))?", x)
        if x.startswith("mi210"):
            continue
        if not r:
            keep.append(x)    # qN stays shorthand; anything else fails parse_cpus with its own reason
            continue
        for c in range(int(r[1]), int(r[2] or r[1]) + 1):
            if c in GPU_HOST_THREADS:
                gpu_threads += 1
            else:
                nums.add(c % NCORES)
    cpu_items = keep + ([cpulist(nums)] if nums else [])
    if gpu_threads and not gpu_need:
        return None, f"regions {regions!r} name gpu host threads 184-191 but the row declares no gpu"
    wq = re.fullmatch(r"multi-quarter\(([23])\)", str(m.get("declared_shape") or shape or ""))
    if regions == "any-cpu-quarter":
        # emergency 2026-11-06: an ACCEPTED multi-quarter shape (shape_override or width_justification) is the width booked;
        # it used to collapse to one quarter here (r4/r5-pca: declared multi-quarter(2), granted q1 only)
        cpus = f"any-{wq[1]}-quarters" if (wq and not gpu_need and (m.get("shape_override") or m.get("width_justification"))) else "any-quarter"
    elif regions.startswith("any-of "):
        cpus = "any-quarter-of-" + regions[len("any-of "):].replace(" ", "")
    else:
        cpus = ",".join(cpu_items) if cpu_items else 0
    try:
        need = parse_cpus(cpus)
    except ValueError as e:
        return None, f"regions {regions!r}: {e}"
    if gpu_need and shape != "quiet-host" and len({c for c in nums if c < 72}) >= 24 and not (
            m.get("width_justification") or m.get("shape_override") or m.get("baseline_ref")):
        return None, (f"regions {regions!r}: a gpu row books whole q0-q2 CPU quarters beside its gpu grant only with a "
                      "width_justification (>= 20 chars); operator 2026-11-06 \"Allow, q0-q2 only\" (mirrors rowflow)")
    if not gpu_need:
        gpu = "none"
    elif shape in ("gpu-q3", "quiet-host") or ac in _TIMING_CLASSES:
        gpu = "exclusive"          # operator ruling: timing exclusive
    elif ac in _SHARED_CLASSES:
        gpu = "shared"             # operator ruling: correctness shares
    else:
        gpu = "exclusive"          # undeclared purpose: the conservative reading (a timing row must not be shared)
    t = m.get("declared_threads")
    if isinstance(t, int) and not isinstance(t, bool) and t >= 1:
        threads = t
    else:
        threads = need.min_width() or (gpu_threads or len(GPU_HOST_THREADS))
    launcher = (m.get("launcher") or {}).get("path") if isinstance(m.get("launcher"), dict) else m.get("launcher")
    for k, v in (("launcher", launcher), ("estimate_s", m.get("estimate_s")), ("min_window_s", m.get("min_window_s")),
                 ("decision_rule", m.get("decision_rule")), ("handoff_task", m.get("handoff_task")), ("owner", m.get("owner"))):
        if v in (None, ""):
            return None, f"legacy manifest has no {k}"
    try:
        rank = float(m.get("priority_rank"))
    except (TypeError, ValueError):
        return None, f"priority_rank {m.get('priority_rank')!r} is not a number"
    spec = {"id": rid, "owner": str(m["owner"]), "handoff_task": str(m["handoff_task"]), "launcher": str(launcher),
            "stop_file": str(m.get("stop_file") or ""), "cpus": cpus, "threads": int(threads), "gpu": gpu,
            "quiet": shape == "quiet-host", "ram_gib": float(m.get("gib") or 0),
            "disk_gib": float(m.get("budget_gib") if m.get("budget_gib") is not None else 1.0),  # rowflow DEFAULT_BUDGET_GIB
            "estimate_s": float(m["estimate_s"]), "min_window_s": float(m["min_window_s"]),
            "decision_rule": str(m["decision_rule"]), "priority_rank": rank,
            "published_at": str(m.get("published_at") or ""), "legacy": {"regions": regions, "shape": shape}}
    if ac in _TIMING_CLASSES:
        spec["timing"] = True
    for k in ("supersedes", "fix_ref", "width_justification", "smoke_predicate"):
        if m.get(k):
            spec[k] = m[k]
    if spec["quiet"] and m.get("shape_override"):
        spec["quiet_reason"] = str(m["shape_override"])   # the only legacy field carrying an operator quiet sanction
    return spec, None


# ============================================================== grants
@dataclass(frozen=True)
class Grant:
    id: str
    cores: frozenset
    gpu: str = "none"
    quiet: bool = False
    ram_gib: float = 0.0
    disk_gib: float = 0.0
    start: float = 0.0
    end: float = 0.0
    estimate_s: float = 0.0
    smoke: bool = False      # a live (legacy keeper) dry run occupying production tokens

    def line(self):
        reg = taskset_list(self.cores, self.gpu) + (",mi210_0" if self.gpu != "none" else "")
        return (f"regions={reg.lstrip(',')} cpus={cpulist(self.cores) or '-'} gpu={self.gpu} quiet={int(self.quiet)} "
                f"ram={self.ram_gib:g} disk={self.disk_gib:g} est={self.estimate_s:g} start={iso(self.start)} end={iso(self.end)}")


def window_s(spec):
    return OVERRUN_FACTOR * max(float(spec["estimate_s"]), float(spec["min_window_s"]))


def tokens_of_legacy(text):
    """(cores, gpu_mode) from a legacy keeper regions/holds text: qN, a-b, tNNN, mi210_0, gpu-quiet."""
    cores, gpu, quiet = set(), False, False
    for x in (y.strip() for y in str(text).split(",")):
        if not x:
            continue
        if x.startswith("mi210"):
            gpu = True
        elif x == "gpu-quiet":
            gpu = quiet = True
        elif re.fullmatch(r"q[0-3]", x):
            cores |= set(range(24 * int(x[1]), 24 * int(x[1]) + 24))
        else:
            r = re.fullmatch(r"t?(\d+)(?:-(\d+))?", x)
            if r:
                for c in range(int(r[1]), int(r[2] or r[1]) + 1):
                    if c in GPU_HOST_THREADS:
                        gpu = True
                    elif c < 2 * NCORES:
                        cores.add(c % NCORES)
    return frozenset(cores), ("exclusive" if quiet else "shared" if gpu else "none")


def parse_grant(rid, line, ram_gib=0.0, now=0.0):
    kv = dict(re.findall(r"(\w+)=(\S+)", line))
    start, end = parse_iso(kv.get("start")) or now, parse_iso(kv.get("end")) or now
    if "cpus" in kv:   # a rowflow2 grant
        cores = frozenset() if kv["cpus"] == "-" else _expand(kv["cpus"])
        return Grant(rid, cores, kv.get("gpu", "none"), kv.get("quiet") == "1", float(kv.get("ram", 0)),
                     float(kv.get("disk", 0)), start, end, float(kv.get("est", 0)))
    c1, g1 = tokens_of_legacy(kv.get("regions", ""))
    c2, g2 = tokens_of_legacy(kv.get("holds", ""))
    gpu = "exclusive" if "exclusive" in (g1, g2) else "shared" if "shared" in (g1, g2) else "none"
    return Grant(rid, c1 | c2, gpu, False, ram_gib, 0.0, start, end, max(0.0, end - start))


# ============================================================== admit (pure)
@dataclass
class Hold:
    id: str
    rank: float
    cores: frozenset
    gpu: bool
    eta: float


@dataclass
class Plan:
    grants: list = field(default_factory=list)
    hold: Hold | None = None
    skipped: dict = field(default_factory=dict)     # id -> reason
    idle: list = field(default_factory=list)        # (class, free_count, reason)
    basis: list = field(default_factory=list)       # the open grants (after reconcile) this plan was admitted against


def _order(specs):
    return sorted(specs, key=lambda s: (float(s["priority_rank"]), s.get("published_at") or "", s["id"]))


def _pick(need, usable):
    """Choose cores for `need` from `usable` (a set), or None."""
    if not need.fixed <= usable:
        return None
    if need.options is not None:
        return next((o for o in need.options if o <= usable), None)
    cand = (need.pool & usable) - need.fixed
    if len(cand) < need.width:
        return None
    by_q = sorted(((len(q & cand), i) for i, q in enumerate(QUARTERS) if len(q & cand) >= need.width))
    if by_q:   # best fit: the fullest quarter that still holds the whole width (NUMA-local)
        return frozenset(sorted(QUARTERS[by_q[0][1]] & cand)[:need.width]) | need.fixed
    return frozenset(sorted(cand)[:need.width]) | need.fixed


def gpu_quiet_step(n, foreign_kfd):
    """Device-level quiet counter (ONE per device, never per row): consecutive samples with no foreign KFD client.
    Returns (n', quiet) with quiet = n' >= IDLE_SAMPLES. Foreign = a KFD pid outside every open grant's process tree."""
    n = n + 1 if not foreign_kfd else 0
    return n, n >= IDLE_SAMPLES


def admit(pending, grants, now, ram_cap=RAM_BOOKABLE_GIB, disk_free=None, smoke_busy=False, gpu_quiet=True, quiet_n=None):
    """Strict priority by rank (ties: publish time, id). Each row that fits the free tokens is granted. The FIRST row
    that does not fit holds the tokens it needs: a later (worse-ranked) row may take a held token only if its whole
    window ends by the held row's ETA (plain backfilling: no budget, no counter, the top row's
    start is never delayed). `quiet` takes every row token plus the gpu, and waits
    for an idle smoke lane. A `timing` row never gets cores 88-95 unless it also holds the gpu exclusive (SMT); a gpu
    EXCLUSIVE row holds 88-95 with the gpu and never the rest of q3 (gpu-q3 NARROW, operator 2026-11-05).
    GPU QUIET (INF-22 2026-11-06): `gpu_quiet` is the DEVICE's state (gpu_quiet_step: IDLE_SAMPLES consecutive samples
    without a foreign KFD client). While it is False every gpu-EXCLUSIVE row is skipped and takes no hold (shared rows
    run beside foreign clients); the moment it is True the ranking below runs over EVERY grantable row as it stands
    NOW, so the best-ranked exclusive row is granted - never the one whose wait happened to start first, and never one
    that arrived mid-wait unless it is the best-ranked."""
    plan, seen = Plan(), set()
    quiet_why = None if gpu_quiet else ("device not quiet: foreign KFD client" if not quiet_n else
                                        f"device quiet {quiet_n}/{IDLE_SAMPLES} samples")
    order = _order(pending) if RANK_AT_GRANT_TIME else sorted(pending, key=lambda s: s["id"])   # False = legacy control
    busy = set().union(*[g.cores for g in grants]) if grants else set()
    free = set(ROW_CORES) - busy
    gx = any(g.gpu == "exclusive" or g.quiet for g in grants)
    gs = any(g.gpu == "shared" for g in grants)
    qopen = any(g.quiet for g in grants)
    ram = sum(g.ram_gib for g in grants)
    disk = sum(g.disk_gib for g in grants if not g.smoke)
    free_at = {c: now for c in ROW_CORES}
    gpu_free_at = shared_free_at = now
    for g in grants:
        for c in g.cores & ROW_CORES:
            free_at[c] = max(free_at[c], g.end)
        if g.gpu != "none" or g.quiet:
            gpu_free_at = max(gpu_free_at, g.end)
        if g.gpu == "exclusive" or g.quiet:
            shared_free_at = max(shared_free_at, g.end)
    for s in order:
        rid = s["id"]
        if rid in seen:   # one decision per id per tick: a twice-published id can never be granted twice
            continue
        seen.add(rid)
        need, win = grant_need(s), window_s(s)
        if need is None:
            plan.skipped[rid] = "timing row needs gpu exclusive on cores 88-95"
            continue
        h = plan.hold
        h_ok = h is None or now + win <= h.eta
        usable = free if h_ok else free - h.cores
        gpu_need = "exclusive" if s["quiet"] else s["gpu"]
        if gpu_need == "exclusive" and quiet_why:   # gated rows wait without a hold (the keeper's held_back), like the device
            plan.skipped[rid] = "gpu-quiet EXCLUSIVE needs a quiet device: " + quiet_why
            continue
        why = None
        if qopen:
            why = "a quiet grant is open"
        elif gpu_need == "exclusive" and (gx or gs):
            why = "gpu busy"
        elif gpu_need == "shared" and gx:
            why = "gpu held exclusive"
        elif gpu_need != "none" and h and h.gpu and not h_ok:
            why = f"gpu held-for {h.id} until {iso(h.eta)}"
        elif ram + s["ram_gib"] > ram_cap:
            why = f"ram {ram:g}+{s['ram_gib']:g} > {ram_cap:g} GiB"
        elif disk_free is not None and disk + s["disk_gib"] > disk_free:
            why = f"disk {disk:g}+{s['disk_gib']:g} > {disk_free:g} GiB free above floor"
        if s["quiet"] and not why:
            if busy or len(free) != len(ROW_CORES) or smoke_busy or plan.grants:
                why = "quiet needs an empty host" + (" (smoke lane busy)" if smoke_busy else "")
            elif h and not h_ok:
                why = f"held-for {h.id} until {iso(h.eta)}"
            pick = frozenset(ROW_CORES) if not why else None
        elif not why:
            pick = _pick(need, usable)
            if pick is None:
                why = "cpus busy" if _pick(need, free) is None else f"cpus held-for {h.id} until {iso(h.eta)}"
        if why:
            plan.skipped[rid] = why
            if plan.hold is None:
                plan.hold = _make_hold(s, need, gpu_need, free_at, gpu_free_at, shared_free_at, now, grants, ram_cap)
            continue
        g = Grant(rid, pick, gpu_need if not s["quiet"] else "exclusive", bool(s["quiet"]), float(s["ram_gib"]),
                  float(s["disk_gib"]), now, now + win, float(s["estimate_s"]))
        plan.grants.append(g)
        free -= pick
        busy |= pick
        ram += g.ram_gib
        disk += g.disk_gib
        for c in pick:
            free_at[c] = g.end
        if g.gpu == "exclusive":
            gx, gpu_free_at, shared_free_at = True, max(gpu_free_at, g.end), max(shared_free_at, g.end)
        elif g.gpu == "shared":
            gs, gpu_free_at = True, max(gpu_free_at, g.end)
        qopen = qopen or g.quiet
    plan.idle = _idle_why(plan, pending, free, gx or gs)
    return plan


def _make_hold(s, need, gpu_need, free_at, gpu_free_at, shared_free_at, now, grants, ram_cap):
    if s["quiet"]:
        cores = frozenset(ROW_CORES)
    elif need.options is not None:
        cores = min(need.options, key=lambda o: (max([free_at[c] for c in o] or [now]), need.options.index(o)))
    else:
        cores = frozenset(sorted(need.pool, key=lambda c: (free_at[c], c))[:need.width]) | need.fixed
    eta = max([free_at[c] for c in cores] or [now])
    if gpu_need == "exclusive":
        eta = max(eta, gpu_free_at)
    elif gpu_need == "shared":
        eta = max(eta, shared_free_at)
    ram = sum(g.ram_gib for g in grants)
    for g in sorted(grants, key=lambda g: g.end):   # a ram-blocked row waits until enough grants end
        if ram + s["ram_gib"] <= ram_cap:
            break
        ram -= g.ram_gib
        eta = max(eta, g.end)
    return Hold(s["id"], float(s["priority_rank"]), cores, gpu_need != "none", eta)


def _idle_why(plan, pending, free, gpu_busy):
    out, granted = [], {g.id for g in plan.grants}
    waiting = [s for s in _order(pending) if s["id"] not in granted]
    h = plan.hold
    for i, q in enumerate(QUARTERS):
        n = len(q & free)
        if not n:
            continue
        if h and q & free & h.cores:
            why = f"held-for {h.id} (rank {h.rank:g}) until {iso(h.eta)}"
        elif not waiting:
            why = "no pending row"
        else:
            users = [s for s in waiting if s["quiet"] or q & (grant_need(s) or parse_cpus(s["cpus"])).allowed()]
            why = (f"best user {users[0]['id']} (rank {users[0]['priority_rank']:g}): {plan.skipped.get(users[0]['id'], '?')}"
                   if users else f"no pending row allows q{i} ({len(waiting)} pending)")
        out.append((f"q{i}", n, why))
    if not gpu_busy:
        users = [s for s in waiting if s["gpu"] != "none" or s["quiet"]]
        if h and h.gpu:
            why = f"held-for {h.id} (rank {h.rank:g}) until {iso(h.eta)}"
        elif not users:
            why = "no pending gpu row"
        else:
            why = f"best user {users[0]['id']} (rank {users[0]['priority_rank']:g}): {plan.skipped.get(users[0]['id'], '?')}"
        out.append(("gpu", 1, why))
    return out


# ============================================================== reconcile (pure)
@dataclass
class Measurement:
    core_busy: dict | None = None   # core -> % busy (max over its SMT threads); None = not measured
    own_kfd: dict = field(default_factory=dict)   # grant id -> set of KFD pids inside its process tree
    alive: dict = field(default_factory=dict)     # grant id -> poller alive (True/False); absent = unknown
    gpu_util: float | None = None                 # device utilisation % (amdgpu gpu_busy_percent); None = not measured
    complete: frozenset = frozenset()             # grant ids holding a completion receipt (.complete / .ended rc=0 complete)
    foreign_kfd: frozenset = frozenset()          # KFD pids outside every open grant's process tree (device quiet gate)


def gpu_idle_sample(mine, gpu_util):
    """P4.3 #4: a gpu-token grant's sample is idle ONLY when its own KFD pid set is KNOWN and empty AND the device
    utilisation (when measured) is ~0; any own KFD pid = busy. CPU % plays no part. None = the KFD side is unmeasured."""
    if mine is None:
        return None
    if mine:
        return False
    return gpu_util is None or gpu_util < GPU_IDLE_PCT


def reconcile(grants, meas, state, now):
    """Pure: (actions, new_state). Actions: ('release-cores', id, cores), ('release-gpu', id), ('overrun', id),
    ('dead-poller', id), ('completed', id), ('over-declared', id, declared, measured_busy), ('idle-warn', id, idle_s),
    ('idle-end', id, idle_s).
    Quiet grants never release cores. IDLE-HELD (operator 2026-11-05): a CPU grant is wholly idle in a sample when every
    core it holds reads < IDLE_PCT; a grant with nothing measurable (no cores, no gpu, or an unmeasured side) is never idle.
    GPU grants (P4.3 #4, GPU_IDLE_BY_GPU_SIGNALS): busy/idle comes from gpu_idle_sample() alone - own KFD pids + device
    utilisation across IDLE_SAMPLES consecutive samples; CPU % never releases their cores, never flags over-declaration and
    never starts their idle clock (43 of 72 live OVER-DECLARED and every IDLE-HELD gpu-quiet notify were CPU readings of
    GPU work). Continuous idleness >= IDLE_WARN_S warns once, >= IDLE_HELD_S ends; one busy sample resets the clock. No
    grace field: a load, compile or build phase keeps a core busy, so it never reads idle; the clock cannot predate the
    grant's first sample, so the first IDLE_HELD_S after start are the grace.
    DEAD POLLER (P4.3 #2, COMPLETE_BEATS_DEAD): a poller dead IDLE_SAMPLES samples whose row is in meas.complete is a
    ('completed', id), never a ('dead-poller', id) - every live rc=14 "pid dead" since 11-04 had a .complete."""
    acts, new = [], {}
    for g in grants:
        if g.smoke:
            continue
        st = dict(state.get(g.id) or {"idle": {}, "gpu0": 0, "dead": 0, "alerted": False, "busy": [], "worked": False,
                                      "declared": len(g.cores), "gpu_used": False, "idle_since": None, "idle_warned": False})
        st["idle"] = dict(st["idle"])
        gpu_grant = g.gpu != "none" and GPU_IDLE_BY_GPU_SIGNALS
        if meas.core_busy is not None and g.cores and not gpu_grant:
            nb = sum(1 for c in g.cores if meas.core_busy.get(c, 0.0) >= IDLE_PCT)
            st["busy"] = (st["busy"] + [nb])[-720:]
            st["worked"] = st["worked"] or nb > 0
            rel = set()
            for c in g.cores:
                st["idle"][c] = st["idle"].get(c, 0) + 1 if meas.core_busy.get(c, 0.0) < IDLE_PCT else 0
                if st["idle"][c] >= IDLE_SAMPLES and st["worked"] and not g.quiet:
                    rel.add(c)
            if rel:
                acts.append(("release-cores", g.id, frozenset(rel)))
                if not st.get("od_logged"):
                    acts.append(("over-declared", g.id, st["declared"], max(st["busy"])))
                    st["od_logged"] = True
                for c in rel:
                    st["idle"].pop(c, None)
        mine = meas.own_kfd.get(g.id) if g.gpu != "none" else None
        g_idle = gpu_idle_sample(mine, meas.gpu_util if GPU_IDLE_BY_GPU_SIGNALS else None) if g.gpu != "none" else None
        if g.gpu != "none":
            if g_idle is False:
                st["gpu0"], st["gpu_used"] = 0, True
            elif g_idle:
                st["gpu0"] += 1
            if g.gpu == "exclusive" and not g.quiet and g_idle and st["gpu0"] >= IDLE_SAMPLES:
                acts.append(("release-gpu", g.id))
        if gpu_grant:   # the gpu token's own signals decide (IDLE_WARN_S of continuous idleness spans >= IDLE_SAMPLES samples)
            wholly_idle = bool(g_idle)
        else:
            cores_idle = not g.cores or (meas.core_busy is not None and all(meas.core_busy.get(c, 0.0) < IDLE_PCT for c in g.cores))
            gpu_idle = g.gpu == "none" or (mine is not None and not mine)
            wholly_idle = bool(g.cores or g.gpu != "none") and cores_idle and gpu_idle   # an unmeasured side is never idle
        if wholly_idle:
            if st.get("idle_since") is None:
                st["idle_since"] = now
            idle_s = int(now - st["idle_since"])
            if idle_s >= IDLE_HELD_S:
                acts.append(("idle-end", g.id, idle_s))
            elif idle_s >= IDLE_WARN_S and not st.get("idle_warned"):
                acts.append(("idle-warn", g.id, idle_s))
                st["idle_warned"] = True
        else:
            st["idle_since"], st["idle_warned"] = None, False
        if g.estimate_s and now > g.start + OVERRUN_FACTOR * g.estimate_s and not st["alerted"]:
            acts.append(("overrun", g.id))
            st["alerted"] = True
        a = meas.alive.get(g.id)
        st["dead"] = st["dead"] + 1 if a is False else 0
        if st["dead"] >= IDLE_SAMPLES:
            acts.append(("completed", g.id) if (COMPLETE_BEATS_DEAD and g.id in meas.complete) else ("dead-poller", g.id))
        new[g.id] = st
    return acts, new


def completion_receipt(flags, rid):
    """P4.3 #2: the row's terminal success evidence - grants/<id>.complete, or grants/<id>.ended whose first line says
    rc=0 and reason=complete. A poller that is gone AFTER this is a finished job, not a dead one."""
    G = os.path.join(flags, "grants")
    if _ex(G, rid + ".complete"):
        return "complete"
    e = ended_fields(head1(os.path.join(G, rid + ".ended")))
    return "ended rc=0 complete" if e["rc"] == 0 and e["base"] == "complete" else None


def refusal_kind(e):
    """P4.3 #1: the admission-refusal kind of an .ended record, or None. A refusal is the LAUNCHER declining to run the
    job (precond-cmd rc=12 / build-missing rc=5, launcher-is-not-the-engine rc=15, 'released' = grant dropped unrun) - the
    job never started, so nothing about the host changed and re-granting next tick can only repeat it."""
    if e["base"] in REFUSAL_REASONS or e["base"].startswith("precond"):
        return e["base"]
    return REFUSAL_RCS.get(e["rc"])


def spec_sha(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def measured_summary(st):
    b = sorted(st.get("busy") or [])
    if not b or not st.get("declared"):
        return None
    p95 = b[min(len(b) - 1, int(round(0.95 * (len(b) - 1))))]
    return {"busy_p95": round(p95 / st["declared"], 3), "cpus": st["declared"], "gpu_used": bool(st.get("gpu_used"))}


# ============================================================== smoke lane (pure)
def smoke_order_key(s):
    try:
        rank = float(s.get("priority_rank", 100))
    except (TypeError, ValueError):
        rank = 100.0
    return (rank, s.get("published_at") or "", s["id"])


def smoke_step(queue, running, quiet_active, now):
    """One at a time, on SMOKE_CORES, by priority_rank then published_at then id (operator 2026-11-06: never alphabetical or
    arrival-only). running = (id, start, deadline) | None. Paused while quiet is open/held."""
    if running:
        rid, start, deadline = running
        return [("smoke-kill", rid)] if now > deadline else []
    if queue and not quiet_active:
        head = sorted(queue, key=smoke_order_key)[0]
        return [("smoke-start", head["id"], now, now + SMOKE_DEADLINE_S)]
    return []


def smoke_env(spec):
    """Env the smoke runner gives a smoke (mirrors rowflow dryrun_run): FILLER_SMOKE_UNITS=1 (stop after one unit) is set only
    for a row WITHOUT smoke_predicate - a predicate row is a multi-stage smoke that stops when its predicate holds."""
    env = {"FILLER_SMOKE": "1", "FILLER_DISK_FLOOR_GIB": "20", "FILLER_VRAM_SAMPLE_S": str(VRAM_SAMPLE_S)}
    if not str(spec.get("smoke_predicate") or "").strip():
        env["FILLER_SMOKE_UNITS"] = "1"
    return env


def smoke_may_stop(spec, units, predicate_ok):
    """True when a running smoke may be stopped now: a predicate row only when smoke_predicate holds, any other row after
    its first unit."""
    if str(spec.get("smoke_predicate") or "").strip():
        return bool(predicate_ok)
    return units >= 1


def smoke_rank_gate(pending, smoke_queue):
    """(kept, waiting): GPU rows ranked worse than the best queued GPU smoke wait for it (keeper batch 2026-11-06)."""
    if not SMOKE_RANK_GATE:
        return list(pending), []
    gq = [smoke_order_key(s)[0] for s in smoke_queue if s.get("gpu", "none") != "none"]
    if not gq:
        return list(pending), []
    best = min(gq)
    waiting = [s for s in pending if s.get("gpu", "none") != "none" and smoke_order_key(s)[0] > best]
    return [s for s in pending if s not in waiting], waiting


def verify_job_residency(rec, tracked, kfd_seen, t0):
    """A job-written residency record is NOT trusted: accepted only when its pid is in the smoke's process tree AND was seen as
    a KFD client holding VRAM in a harness sample, and it is no older than the smoke. Returns (bytes, why); 0 = rejected."""
    if not isinstance(rec, dict):
        return 0, "no residency record"
    try:
        pid, vb = int(rec["pid"]), int(rec["vram_bytes"])
    except (KeyError, TypeError, ValueError):
        return 0, "residency record malformed"
    if rec.get("schema") != RESIDENCY_SCHEMA:
        return 0, "residency record schema mismatch"
    if pid not in tracked:
        return 0, f"residency pid {pid} is not in the smoke's process tree"
    if pid not in kfd_seen:
        return 0, f"residency pid {pid} was never seen as a KFD client holding VRAM"
    at = parse_iso(rec.get("at"))
    if at is None or at < t0 - 1:
        return 0, "residency record predates the smoke"
    return max(vb, 0), f"job residency record pid {pid} {vb} B, verified as KFD client"


def smoke_resident(vram_samples, rec, tracked, kfd_seen, t0):
    """GPU smoke residency verdict: harness VRAM samples (taken every VRAM_SAMPLE_S) or a verified job record reach 64 MiB."""
    mx = max([v for v in vram_samples if v is not None] or [0])
    if mx >= RESIDENCY_MIN_BYTES:
        return True, f"vram sampled {mx} B"
    jb, why = verify_job_residency(rec, tracked, kfd_seen, t0)
    return jb >= RESIDENCY_MIN_BYTES, why


def escalation_tag(options):
    """NEEDS-OWNER when every listed option is owner-level; NEEDS-OPERATOR only when an operator-only action is listed.
    options: [(text, operator_only)]."""
    return "NEEDS-OPERATOR" if any(op for _, op in options) else "NEEDS-OWNER"


def write_escalation(flags, rid, why, options, now):
    """operator-escalations/<id>.md with the honest heading (mirrors rowflow). Never raises."""
    try:
        L = [f"# PARKED {escalation_tag(options)} - row `{rid}` ({why}; written {iso(now)} by rowflow2)", "",
             "Options: " + "; ".join(f"{i}. {t}" for i, (t, _) in enumerate(options, 1)) + ".", ""]
        write_text(os.path.join(flags, "operator-escalations", rid + ".md"), "\n".join(L))
    except Exception:  # noqa: BLE001
        pass


# ============================================================== file (pure)
def ended_fields(text):
    kv = dict(re.findall(r"(\w+)=(\S+)", text or ""))
    rc = int(kv["rc"]) if re.fullmatch(r"-?\d+", kv.get("rc", "")) else None
    reason = kv.get("reason", "complete" if (text or "").startswith("complete") else "")
    return {"rc": rc, "reason": reason, "base": reason.split(":")[0], "time": parse_iso(kv.get("time") or kv.get("at")),
            "busy_p95": float(kv["busy_p95"]) if "busy_p95" in kv else None,
            "cpus": int(kv["measured_cpus"]) if "measured_cpus" in kv else None}


def file_decisions(ended, specs, claims, now):
    """ended: {id: (fields, mtime)}; claims: {id: claim_at}.
    Actions: ('file', id, verdict, how) | ('route-owner', id, owner) | ('owner-less', id) | ('reopen', id) |
    ('wait-claim', id)."""
    acts = []
    for rid, (e, mt) in sorted(ended.items()):
        s = specs.get(rid) or {}
        t0 = e["time"] or mt
        if e["base"] in ("superseded", "withdrawn"):
            acts.append(("file", rid, "withdrawn", e["reason"]))
            continue
        rule = machine_rule(s.get("decision_rule", ""))
        if rule is not None and e["rc"] is not None:
            ok = bool(eval(rule, {"__builtins__": {}}, {"rc": e["rc"], "reason": e["base"]}))  # noqa: S307 - ast-whitelisted
            acts.append(("file", rid, "pass" if ok else "fail", "machine-rule"))
        elif rid in claims:
            acts.append(("reopen", rid) if now - claims[rid] > CLAIM_TTL_S else ("wait-claim", rid))
        elif now - t0 > FILE_OWNERLESS_S or not str(s.get("owner") or "").strip():
            acts.append(("owner-less", rid))
        else:
            acts.append(("route-owner", rid, s.get("owner")))
    return acts


# ============================================================== IO: the world
@dataclass
class World:
    specs: dict = field(default_factory=dict)
    pending: list = field(default_factory=list)
    smoke_queue: list = field(default_factory=list)
    smoke_running: tuple | None = None
    grants: list = field(default_factory=list)
    ever_granted: set = field(default_factory=set)
    unmapped: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)       # id -> state word
    ended: dict = field(default_factory=dict)       # id -> (fields, mtime) for .ended without .FILED
    smoke_finished: list = field(default_factory=list)
    parked: dict = field(default_factory=dict)      # id -> PARKED.json record still binding (launcher + spec sha unchanged)
    stale_parks: list = field(default_factory=list)  # ids whose PARKED.json names an older launcher/spec sha (auto-unpark)
    launcher_sha: dict = field(default_factory=dict)  # id -> current launcher sha256 (rows that reached the sha check)


def _ex(*p):
    return os.path.exists(os.path.join(*p))


def load_world(flags, now, sha_cache=None):
    """Read-only. Mirrors rowflow._status_raw minimally: done | running | unmapped | stopped | smoking | failed |
    pending (smoke PASS for the current launcher sha) | needs-smoke."""
    w, G, D = World(), os.path.join(flags, "grants"), os.path.join(flags, "dryrun")
    sha_cache = {} if sha_cache is None else sha_cache
    manifests = {}
    for p in sorted(glob.glob(os.path.join(flags, "ready", "*.json"))):
        d = load_json(p)
        if d and d.get("id"):
            manifests[d["id"]] = d
    for gp in glob.glob(os.path.join(G, "*.grant")):
        rid = os.path.basename(gp)[:-6]
        w.ever_granted.add(rid)
        if _ex(G, rid + ".ended") or _ex(G, rid + ".complete"):
            continue
        m = manifests.get(rid) or {}
        w.grants.append(parse_grant(rid, head1(gp), float(m.get("ram_gib", m.get("gib")) or 0), now))
    for rp in glob.glob(os.path.join(D, "*", "RUNNING.json")):   # a live (legacy) dry run occupies production tokens
        r = load_json(rp) or {}
        dl = parse_iso(r.get("deadline"))
        if dl and dl > now:
            cores, gpu = tokens_of_legacy(r.get("regions", ""))
            rid = os.path.basename(os.path.dirname(rp))
            w.grants.append(Grant("smoke:" + rid, cores, gpu, False, 0.0, 0.0, parse_iso(r.get("started")) or now, dl, 0.0, True))
    for sp in glob.glob(os.path.join(D, "*", "SMOKE.json")):     # a rowflow2 smoke on the smoke lane
        r = load_json(sp) or {}
        rid, start = os.path.basename(os.path.dirname(sp)), float(r.get("start", now))
        outs = glob.glob(os.path.join(D, rid, "PASS.json")) + glob.glob(os.path.join(D, rid, "FAIL-*.json"))
        if any(os.path.getmtime(f) >= start - 1 for f in outs):
            w.smoke_finished.append(rid)      # the harness wrote its verdict: the lane is free
        else:
            w.smoke_running = (rid, start, float(r.get("deadline", now)))
    for rid, d in manifests.items():
        if _ex(G, rid + ".ended") or _ex(G, rid + ".complete") or _ex(flags, "filing-done", rid + ".FILED"):
            w.state[rid] = "done"
            w.specs[rid] = d if d.get("schema") == SCHEMA else (map_legacy(d)[0] or {})   # file() needs its rule
            continue
        if rid in {g.id for g in w.grants}:
            w.state[rid] = "running"
            continue
        if d.get("schema") == SCHEMA:
            spec, why = d, None
        else:
            spec, why = map_legacy(d)
        if spec is None:
            w.unmapped[rid], w.state[rid] = "map: " + why, "unmapped"
            continue
        pred = None
        sup = spec.get("supersedes")
        for s in ([sup] if isinstance(sup, str) else sup or []):
            e = ended_fields(head1(os.path.join(G, s + ".ended")) + " " + _text(os.path.join(G, s + ".ended")))
            if e["busy_p95"] is not None:
                pred = {"busy_p95": e["busy_p95"], "cpus": e["cpus"]}
        errs = validate(spec, pred)
        if errs:
            w.unmapped[rid], w.state[rid] = "admit: " + "; ".join(errs), "unmapped"
            continue
        w.specs[rid] = spec
        if os.path.exists(spec["stop_file"]):
            w.state[rid] = "stopped"
            continue
        if w.smoke_running and w.smoke_running[0] == rid:
            w.state[rid] = "smoking"
            continue
        lp = spec["launcher"]
        try:
            st = os.stat(lp)
            key = (lp, st.st_mtime, st.st_size)
            cur = sha_cache.get(key) or sha_cache.setdefault(key, sha256(lp))
        except OSError:
            w.unmapped[rid], w.state[rid] = "admit: launcher unreadable", "unmapped"
            continue
        w.launcher_sha[rid] = cur
        try:
            jcur = job_sha(lp, sha_cache)
        except OSError:
            jcur = None

        def same(rec):   # decision 10: launcher sha AND job sha (an unrecorded job sha matches, as in rowflow fresh_attempt)
            return rec.get("launcher_sha256") == cur and rec.get("job_sha256") in (None, jcur)
        pk = load_json(os.path.join(D, rid, "PARKED.json"))   # P4.3 #1: a refusal park binds the row AS PUBLISHED
        if pk:
            if same(pk) and pk.get("spec_sha256") == spec_sha(d):
                w.parked[rid], w.state[rid] = pk, "parked"
                continue
            w.stale_parks.append(rid)   # the launcher or the manifest changed: the park no longer binds (tick removes it)
        p = load_json(os.path.join(D, rid, "PASS.json"))
        un_at = os.path.getmtime(os.path.join(D, rid, "UNPARK.json")) if os.path.exists(os.path.join(D, rid, "UNPARK.json")) else 0.0
        smoke_fails = [f for f in glob.glob(os.path.join(D, rid, "FAIL-*.json"))
                       if not os.path.basename(f).startswith("FAIL-refused-") and os.path.getmtime(f) > un_at]   # an unpark forgives older smoke FAILs
        if p and same(p):
            w.pending.append(spec)
            w.state[rid] = "pending"
        elif any(same(load_json(f) or {}) for f in smoke_fails):
            w.state[rid] = "failed"
        else:
            w.smoke_queue.append(spec)
            w.state[rid] = "needs-smoke"
    for ep in glob.glob(os.path.join(G, "*.ended")):
        rid = os.path.basename(ep)[:-6]
        if not _ex(flags, "filing-done", rid + ".FILED"):
            try:
                w.ended[rid] = (ended_fields(_text(ep)), os.path.getmtime(ep))
            except OSError:
                pass
    return w


def _text(path):
    try:
        with open(path, errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def disk_free_gib(path=DISK_PATH):
    try:
        s = os.statvfs(path)
        return s.f_bavail * s.f_frsize / (1 << 30) - DISK_FLOOR_GIB
    except OSError:
        return None


# ============================================================== IO: measurement
def proc_stat(path=None):
    out = {}
    try:
        with open(path or os.path.join(PROC, "stat")) as f:
            for line in f:
                m = re.match(r"cpu(\d+)\s+(.*)", line)
                if m:
                    v = [int(x) for x in m[2].split()]
                    out[int(m[1])] = (v[0] + v[1] + v[2] + v[5] + v[6] + v[7], sum(v[:8]))
    except OSError:
        pass
    return out


def core_busy(s0, s1):
    """core -> max % busy over the core's two SMT threads (gpu host threads are not part of a core)."""
    pct = {}
    for t, (b1, a1) in s1.items():
        b0, a0 = s0.get(t, (b1, a1))
        pct[t] = 100.0 * (b1 - b0) / (a1 - a0) if a1 > a0 else 0.0
    return {c: max(pct.get(c, 0.0), 0.0 if c + NCORES in GPU_HOST_THREADS else pct.get(c + NCORES, 0.0))
            for c in range(NCORES)}


def kfd_pids():
    try:
        return {int(p) for p in os.listdir(KFD_PROC) if p.isdigit()}
    except OSError:
        return set()


def descendants(pid):
    kids = {}
    for sp in glob.glob(os.path.join(PROC, "[0-9]*", "stat")):
        try:
            with open(sp) as f:
                s = f.read()
            kids.setdefault(int(s[s.rindex(")") + 2:].split()[1]), []).append(int(s.split()[0]))
        except (OSError, ValueError, IndexError):
            pass
    out, todo = {pid}, [pid]
    while todo:
        for k in kids.get(todo.pop(), []):
            if k not in out:
                out.add(k)
                todo.append(k)
    return out


# ============================================================== IO: live tick (temp flags dirs only in this build)
def write_grant(flags, g):
    p = os.path.join(flags, "grants", g.id + ".grant")
    if os.path.exists(p) and not (_ex(flags, "grants", g.id + ".ended") or _ex(flags, "grants", g.id + ".complete")):
        raise RuntimeError(f"DOUBLE-GRANT refused: {g.id} already holds an open grant")
    write_text(p, g.line() + "\n")


def template_warnings(launcher):
    """Lane-template lint (friction review Pass 4 change 3): a job dir that vendors a known-bad write_fence /
    smoke_admission / smoke_root_exec copy or a one-process gitnexus-impact job.py. Warnings only; a lint that
    cannot load is silent. Lives here, not in the frozen rowflow/publish_row.py (would need a keeper deploy)."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        for d in (os.path.join(here, "..", "job_templates"), os.path.join(here, "job_templates")):
            if os.path.isfile(os.path.join(d, "template_lint.py")):
                sys.path.insert(0, d)
                break
        import template_lint
        return template_lint.lint_dir(launcher)
    except Exception:  # noqa: BLE001 - a lint never blocks publish
        return []


def publish(spec, flags, log=print):
    """Validate and write ready/<id>.json (schema v4); supersede predecessors. Returns refusal reasons ([] = ok)."""
    spec = dict(spec, schema=SCHEMA)
    spec.setdefault("published_at", iso(time.time()))
    pred = None
    sups = spec.get("supersedes")
    sups = [sups] if isinstance(sups, str) else list(sups or [])
    for s in sups:
        e = ended_fields(_text(os.path.join(flags, "grants", s + ".ended")))
        if e["busy_p95"] is not None:
            pred = {"busy_p95": e["busy_p95"], "cpus": e["cpus"]}
    errs = validate(spec, pred)
    if errs:
        log(f"REFUSED {spec.get('id')}: {'; '.join(errs)}")
        return errs
    for w in template_warnings(spec["launcher"]):   # WARN only, never a refusal (operator 2026-11-06)
        log(f"WARN {spec['id']}: {w}")
    write_text(os.path.join(flags, "ready", spec["id"] + ".json"), json.dumps(spec, indent=1, sort_keys=True) + "\n")
    for s in sups:
        withdraw(flags, s, f"superseded:{spec['id']}", log)
    log(f"PUBLISHED {spec['id']} cpus={spec['cpus']} threads={spec['threads']} gpu={spec['gpu']} quiet={spec['quiet']}")
    return []


def withdraw(flags, rid, reason, log=print):
    """withdraw = STOP + .ended. A running row finishes: its STOP is not touched and no .ended is written for it."""
    G = os.path.join(flags, "grants")
    if _ex(G, rid + ".ended") or _ex(G, rid + ".complete"):
        return "TERMINAL"
    if _ex(G, rid + ".grant"):
        log(f"SUPERSEDE-PENDING {rid}: running; it finishes")
        return "PENDING"
    d = load_json(os.path.join(flags, "ready", rid + ".json")) or {}
    sf = d.get("stop_file") or ""
    if os.path.isabs(sf):
        write_text(sf, "", append=True)
    write_text(os.path.join(G, rid + ".ended"), f"rc=75 reason={reason} time={iso(time.time())}\n")
    log(f"WITHDRAWN {rid} reason={reason}")
    return "WITHDRAWN"


def smoke_alert(flags, rid, now, deadline=False):
    """Operator 2026-11-06: a smoke that is not a PASS alerts the owner (id, FAIL reason, fix_task, FAIL path) - the row never
    just disappears from the queue. Called once per smoke end (the caller removes SMOKE.json right after). Never raises."""
    try:
        dd = os.path.join(flags, "dryrun", rid)
        start = float((load_json(os.path.join(dd, "SMOKE.json")) or {}).get("start", 0))
        if not deadline and any(os.path.getmtime(f) >= start - 1 for f in glob.glob(os.path.join(dd, "PASS.json"))):
            return
        fails = sorted((f for f in glob.glob(os.path.join(dd, "FAIL-*.json")) if not os.path.basename(f).startswith("FAIL-refused-")),
                       key=os.path.getmtime)
        fp = fails[-1] if fails else None
        rec = (load_json(fp) or {}) if fp else {}
        reason = str(rec.get("reason") or ("smoke deadline" if deadline else "smoke ended with no PASS and no FAIL reason"))[:300]
        fix = rec.get("fix_task") or f"fix the smoke failure of {rid}: {reason} (see {dd}/launcher.out), then republish"
        write_text(os.path.join(flags, "rowflow2-alerts.jsonl"),
                   json.dumps({"kind": "smoke-fail", "row_id": rid, "at": iso(now), "reason": reason, "fix_task": fix,
                               "fail_file": fp}) + "\n", append=True)
    except Exception:  # noqa: BLE001 - an alert failure never stops the tick
        pass


def stamp_job_sha(flags, rid):
    """The harness writes PASS / FAIL-* with the launcher sha only: copy the job sha the smoke started under (SMOKE.json)
    into this smoke's verdicts, so a later job.py edit under the same launcher re-smokes the row (decision 10)."""
    dd = os.path.join(flags, "dryrun", rid)
    sm = load_json(os.path.join(dd, "SMOKE.json")) or {}
    if not sm.get("job_sha256"):
        return
    for f in glob.glob(os.path.join(dd, "PASS.json")) + glob.glob(os.path.join(dd, "FAIL-*.json")):
        r = load_json(f)
        if r is not None and "job_sha256" not in r and os.path.getmtime(f) >= float(sm.get("start", 0)) - 1:
            r["job_sha256"] = sm["job_sha256"]
            write_text(f, json.dumps(r) + "\n")


def park(flags, rid, spec, kind, e, now, log):
    """P4.3 #1: ONE FAIL-refused record + ONE alert per refusal episode; PARKED.json binds the row as published (launcher
    sha + spec sha); the refusing .ended is kept as evidence under dryrun/ and the grant is dropped, so the row is neither
    done nor pending: it is `parked` until its launcher or manifest changes or an operator runs `unpark`."""
    dd, G = os.path.join(flags, "dryrun", rid), os.path.join(flags, "grants")
    n = len(glob.glob(os.path.join(dd, "FAIL-refused-*.json"))) + 1
    try:
        lsha, jsha = sha256(spec["launcher"]), job_sha(spec["launcher"])
    except (OSError, KeyError):
        lsha = jsha = None
    ssha = spec_sha(load_json(os.path.join(flags, "ready", rid + ".json")) or spec)
    fix = (f"{rid}: launcher refused at admission ({kind}, rc={e.get('rc')}, reason={e.get('reason') or '-'}); parked - "
           f"fix the launcher/precond target or the manifest and republish, or `rowflow2.py unpark --id {rid}`")
    rec = {"id": rid, "kind": "refused", "refusal": kind, "rc": e.get("rc"), "reason": e.get("reason"), "at": iso(now),
           "launcher_sha256": lsha, "job_sha256": jsha, "spec_sha256": ssha, "attempt": n, "fix_task": fix}
    write_text(os.path.join(dd, f"FAIL-refused-{n}.json"), json.dumps(rec) + "\n")
    write_text(os.path.join(dd, "PARKED.json"), json.dumps(rec) + "\n")
    if _ex(G, rid + ".ended"):
        os.replace(os.path.join(G, rid + ".ended"), os.path.join(dd, f"REFUSED-{n}.ended"))
    if _ex(G, rid + ".grant"):
        os.remove(os.path.join(G, rid + ".grant"))
    write_escalation(flags, rid, f"launcher refused at admission: {kind}",
                     [("fix the launcher/precond target or the manifest and republish", False),
                      (f"`rowflow2.py unpark --id {rid}` (the owner may)", False), ("drop (remove ready/<id>.json)", False)], now)
    write_text(os.path.join(flags, "rowflow2-alerts.jsonl"),
               json.dumps({"kind": "refused", "row_id": rid, "at": iso(now), "refusal": kind, "attempt": n, "fix_task": fix}) + "\n", append=True)
    log(f"REFUSED {rid} {kind} rc={e.get('rc')} reason={e.get('reason') or '-'}: parked (dryrun/{rid}/FAIL-refused-{n}.json); "
        f"retried only after a launcher/spec sha change or `rowflow2.py unpark --id {rid}`")


def unpark(flags, rid, log=print):
    """Operator unpark: the refusal park no longer binds; the next tick re-admits the row (its PASS still stands)."""
    dd = os.path.join(flags, "dryrun", rid)
    had = _ex(dd, "PARKED.json")
    if had:
        os.remove(os.path.join(dd, "PARKED.json"))
    targets = [dd]
    if not _ex(flags, "ready", rid + ".json"):   # operator 2026-11-06: a lineage id (no ready/ row of its own) unparks its members
        targets += [x for x in glob.glob(os.path.join(flags, "dryrun", rid + "*")) if os.path.isdir(x) and x != dd]
    for t in targets:
        os.makedirs(t, exist_ok=True)
        write_text(os.path.join(t, "UNPARK.json"), json.dumps({"id": os.path.basename(t), "at": iso(time.time())}) + "\n")
        if t != dd:
            had = had or _ex(t, "PARKED.json")
            if _ex(t, "PARKED.json"):
                os.remove(os.path.join(t, "PARKED.json"))
    log(f"UNPARK {rid}" + ("" if had else " (was not parked)") + (f" +{len(targets) - 1} lineage member(s)" if len(targets) > 1 else ""))
    return had or len(targets) > 1


def tick(flags, now, meas, state, log, runner=None):
    """One live tick: reconcile -> admit -> smoke lane -> file. Writes only under `flags`. Returns (plan, state)."""
    w = load_world(flags, now)
    G = os.path.join(flags, "grants")
    for rid in w.stale_parks:
        os.remove(os.path.join(flags, "dryrun", rid, "PARKED.json"))
        log(f"UNPARK-AUTO {rid}: launcher or manifest sha changed since the refusal park")
    if PARK_ON_REFUSAL:   # P4.3 #1: refusals seen this tick, each parked exactly once
        tracked = set(state.get("grants") or {}) | set(state.get("granted_last") or [])   # incl. last tick's fresh grants
        live, parked_now = {g.id for g in w.grants}, set()
        for rid, (e, _mt) in sorted(w.ended.items()):
            kind = refusal_kind(e)
            if kind and rid in w.specs and not _ex(G, rid + ".complete"):
                park(flags, rid, w.specs[rid], kind, e, now, log)
                parked_now.add(rid)
                w.ended.pop(rid, None)
                w.state[rid] = "parked"
                w.pending = [s for s in w.pending if s["id"] != rid]
        for rid in sorted(tracked - live - parked_now):   # a grant we held last tick vanished with no .ended/.complete: released unrun
            if rid in w.specs and not _ex(G, rid + ".ended") and not _ex(G, rid + ".complete") and not _ex(G, rid + ".grant"):
                park(flags, rid, w.specs[rid], "released", {"rc": None, "reason": "released: grant dropped by the launcher, job unrun"}, now, log)
                w.state[rid] = "parked"
                w.pending = [s for s in w.pending if s["id"] != rid]
    acts, state_new = reconcile(w.grants, meas, state.get("grants", {}), now)
    state["gpu_quiet_n"], gpu_quiet = gpu_quiet_step(int(state.get("gpu_quiet_n") or 0), meas.foreign_kfd)
    byid = {g.id: g for g in w.grants}
    for a in acts:
        g = byid.get(a[1])
        if a[0] == "release-cores" and g:
            g2 = replace(g, cores=g.cores - a[2])
            byid[g.id] = g2
            write_text(os.path.join(G, g.id + ".grant"), g2.line() + "\n")
            log(f"RELEASE {g.id} cores={cpulist(a[2])} (idle {IDLE_SAMPLES} samples)")
        elif a[0] == "release-gpu" and g:
            byid[g.id] = g2 = replace(g, gpu="none")
            write_text(os.path.join(G, g.id + ".grant"), g2.line() + "\n")
            log(f"RELEASE {g.id} gpu (no own KFD pid {IDLE_SAMPLES} samples)")
        elif a[0] == "overrun":
            log(f"OVERRUN {a[1]} past {OVERRUN_FACTOR:g} x estimate")
        elif a[0] == "over-declared":
            log(f"OVER-DECLARED {a[1]} declared {a[2]} measured {a[3]}")
        elif a[0] == "dead-poller" and g:
            how = completion_receipt(flags, g.id) if COMPLETE_BEATS_DEAD else None   # P4.3 #2: re-read at write time (race)
            if how:
                log(f"COMPLETED {g.id}: poller gone after its completion receipt ({how}); not a dead poller")
            else:
                write_text(os.path.join(G, g.id + ".ended"), f"rc=75 reason=dead-poller time={iso(now)}\n")
                log(f"DEAD-POLLER {g.id}: grant removed")
            byid.pop(g.id)
        elif a[0] == "completed" and g:
            log(f"COMPLETED {g.id}: poller gone after its completion receipt ({completion_receipt(flags, g.id) or 'measured'}); not a dead poller")
            byid.pop(g.id)
        elif a[0] == "idle-warn":
            log(f"IDLE-HELD-WARN {a[1]} idle {a[2]}s (every core < {IDLE_PCT:g}%, no own KFD pid): owner warned; "
                f"ends rc=75 and re-queues at {IDLE_HELD_S}s")
        elif a[0] == "idle-end" and g:
            dd = os.path.join(flags, "dryrun", g.id)
            n = len(glob.glob(os.path.join(dd, "IDLE-HELD-*.json"))) + 1
            write_text(os.path.join(dd, f"IDLE-HELD-{n}.json"), json.dumps({"id": g.id, "at": iso(now), "idle_s": a[2], "rc": 75,
                       "reason": "idle-held", "attempt": n, "cores": cpulist(g.cores), "gpu": g.gpu, "terminal": n > IDLE_HELD_RETRY,
                       "fix_task": f"{g.id} held {cpulist(g.cores) or '-'} gpu={g.gpu} wholly idle for {a[2]}s: "
                                   f"unstick the job (stale lock? hung load?) before it runs again"}) + "\n")
            if n > IDLE_HELD_RETRY:
                write_text(os.path.join(G, g.id + ".ended"), f"rc=75 reason=idle-held time={iso(now)}\n")
                log(f"IDLE-END {g.id} rc=75 idle {a[2]}s: terminal after {n} idle-held ends (dryrun/{g.id}/IDLE-HELD-{n}.json)")
            else:
                os.remove(os.path.join(G, g.id + ".grant"))
                log(f"IDLE-END {g.id} rc=75 idle {a[2]}s: grant ended, row re-queued (attempt {n} of {IDLE_HELD_RETRY + 1})")
            byid.pop(g.id)
            state_new.pop(g.id, None)   # a re-grant of the same id starts a fresh idle clock
    # measured feedback onto every .ended of a grant we tracked (once)
    for gid, st in list((state.get("grants") or {}).items()):
        if gid not in state_new and _ex(G, gid + ".ended") and gid not in state.get("measured_done", []):
            m = measured_summary(st)
            if m:
                write_text(os.path.join(G, gid + ".ended"), f"measured busy_p95={m['busy_p95']} measured_cpus={m['cpus']} "
                                                            f"gpu_used={int(m['gpu_used'])}\n", append=True)
            state.setdefault("measured_done", []).append(gid)
    grants = list(byid.values())
    for rid in w.smoke_finished:
        stamp_job_sha(flags, rid)
        smoke_alert(flags, rid, now)
        os.remove(os.path.join(flags, "dryrun", rid, "SMOKE.json"))
    pend, waiting = smoke_rank_gate(w.pending, w.smoke_queue)
    if waiting:
        log(f"WAIT-FOR-SMOKE: queued GPU smoke runs first; GPU row(s) {','.join(s['id'] for s in waiting[:5])} (worse rank) wait")
    plan = admit(pend, grants, now, disk_free=None, smoke_busy=bool(w.smoke_running), gpu_quiet=gpu_quiet,
                 quiet_n=state["gpu_quiet_n"])
    plan.basis = grants
    for g in plan.grants:
        write_grant(flags, g)
        log(f"GRANT {g.id} {g.line()}")
    state["granted_last"] = [g.id for g in plan.grants]   # a grant the launcher drops before the next tick is still ours
    if plan.hold:
        log(f"HOLD {plan.hold.id} cpus={cpulist(plan.hold.cores)} gpu={int(plan.hold.gpu)} eta={iso(plan.hold.eta)}")
    for cls, n, why in plan.idle:
        log(f"IDLE-WHY {cls} free={n}: {why}")
    quiet = any(g.quiet for g in grants + plan.grants) or bool(plan.hold and plan.hold.cores == ROW_CORES)
    for a in smoke_step(w.smoke_queue, w.smoke_running, quiet, now):
        dd = os.path.join(flags, "dryrun", a[1])
        if a[0] == "smoke-start":
            spec = w.specs[a[1]]
            write_text(os.path.join(dd, "SMOKE.json"), json.dumps({"id": a[1], "start": a[2], "deadline": a[3],
                       "cores": cpulist(SMOKE_CORES), "launcher_sha256": sha256(spec["launcher"]),
                       "job_sha256": job_sha(spec["launcher"]),
                       "env": smoke_env(spec)}) + "\n")
            log(f"SMOKE-START {a[1]} cores={cpulist(SMOKE_CORES)} deadline={iso(a[3])}")
            if runner:
                runner.start(a[1], SMOKE_CORES, a[3])
        else:
            if runner:
                runner.kill(a[1])
            spec = w.specs.get(a[1]) or {}
            write_text(os.path.join(dd, "FAIL-deadline.json"), json.dumps({"reason": "smoke deadline", "at": iso(now),
                       "launcher_sha256": sha256(spec["launcher"]) if spec else None,
                       "job_sha256": (load_json(os.path.join(dd, "SMOKE.json")) or {}).get("job_sha256")}) + "\n")
            smoke_alert(flags, a[1], now, deadline=True)
            os.remove(os.path.join(dd, "SMOKE.json"))
            log(f"SMOKE-DEADLINE {a[1]} killed")
    file_step(flags, w, now, log)
    state["grants"] = state_new
    return plan, state


def file_step(flags, w, now, log):
    G, F = os.path.join(flags, "grants"), os.path.join(flags, "filing-done")
    for cp in glob.glob(os.path.join(G, "*.complete")):   # a COMPLETE must come from a grant, never from a smoke
        rid = os.path.basename(cp)[:-9]
        if not _ex(G, rid + ".grant"):
            os.replace(cp, cp + "-rejected-no-grant")
            log(f"COMPLETE-WITHOUT-GRANT {rid}: rejected (smokes never complete a row)")
    claims = {}
    for cp in glob.glob(os.path.join(flags, "filing-claims", "*.json")):
        c = load_json(cp) or {}
        claims[os.path.basename(cp)[:-5]] = parse_iso(c.get("at")) or os.path.getmtime(cp)
    routed = set(re.findall(r'"id": "([^"]+)"', _text(os.path.join(flags, "filing-owner-less.jsonl"))))
    for a in file_decisions(w.ended, w.specs, claims, now):
        rid = a[1]
        if a[0] == "file":
            write_text(os.path.join(F, rid + ".verdict.json"), json.dumps({"schema": "epyc.filed.verdict.v1", "id": rid,
                       "outcome": a[2], "filed_by": "rowflow2:" + a[3], "at": iso(now)}) + "\n")
            write_text(os.path.join(F, rid + ".FILED"), f"{iso(now)} {a[2].upper()} filed_by=rowflow2:{a[3]}\n")
            log(f"FILED {rid} {a[2]} ({a[3]})")
        elif a[0] == "owner-less" and rid not in routed:
            write_text(os.path.join(flags, "filing-owner-less.jsonl"), json.dumps({"id": rid, "at": iso(now)}) + "\n", append=True)
        elif a[0] == "reopen":
            os.replace(os.path.join(flags, "filing-claims", rid + ".json"),
                       os.path.join(flags, "filing-claims", rid + ".json.expired"))
            log(f"FILING-REOPEN {rid}: claim older than {CLAIM_TTL_S}s")


# ============================================================== shadow
def _logged(path):
    seen = set()
    try:
        with open(path, errors="replace") as f:
            for line in f:
                m = re.match(r"\S+ (SHADOW-GRANT|SHADOW-UNMAPPED) (\S+?):? ", line)
                if m:
                    seen.add((m[1], m[2]))
    except OSError:
        pass
    return seen


def gpu_util():
    """Device utilisation % from amdgpu sysfs (max over matching cards), or None when unreadable."""
    vals = []
    for p in glob.glob(GPU_BUSY_GLOB):
        try:
            vals.append(float(head1(p)))
        except ValueError:
            pass
    return max(vals) if vals else None


def measure(flags, grants, prev_stat):
    """(Measurement, stat sample). A grant's own KFD pids = KFD clients inside its poller's process tree (ARMED.json
    pid), known only when that pid is visible here; poller liveness is never guessed from an invisible pid. Foreign KFD
    pids (device quiet gate) = every KFD client outside all known grant trees; completion receipts feed the dead-poller rule."""
    s1 = proc_stat()
    kfd, own = kfd_pids(), {}
    for g in grants:
        pid = (load_json(os.path.join(flags, "dryrun", g.id, "ARMED.json")) or {}).get("pid")
        if pid and os.path.exists(os.path.join(PROC, str(pid))):
            own[g.id] = kfd & descendants(int(pid))
    foreign = frozenset(kfd - set().union(*own.values())) if own else frozenset(kfd)
    done = frozenset(g.id for g in grants if not g.smoke and completion_receipt(flags, g.id))
    return Measurement(core_busy(prev_stat, s1) if prev_stat else None, own, {}, gpu_util(), done, foreign), s1


def shadow_once(flags, log_path, now=None, seen=None, sha_cache=None, ctx=None):
    """Read flags (guarded read-only), decide what rowflow2 WOULD release and grant now, append to log_path only.
    ctx carries the previous /proc/stat sample and the reconcile state across loop ticks."""
    flags, now = os.path.realpath(flags), time.time() if now is None else now
    if _under_guard(log_path) or os.path.realpath(log_path).startswith(flags + os.sep):
        raise ShadowWriteRefused(f"shadow log {log_path} lies under the flags dir")
    guard_readonly(flags)
    seen = _logged(log_path) if seen is None else seen
    w = load_world(flags, now, sha_cache)
    t, lines = iso(now), []
    if ctx is not None:
        if "stat" not in ctx:
            ctx["stat"] = proc_stat()
            time.sleep(1)
        meas, ctx["stat"] = measure(flags, w.grants, ctx["stat"])
        acts, ctx["rstate"] = reconcile(w.grants, meas, ctx.get("rstate", {}), now)
        byid = {g.id: g for g in w.grants}
        for a in acts:
            if a[0] == "release-cores":
                byid[a[1]] = replace(byid[a[1]], cores=byid[a[1]].cores - a[2])
                lines.append(f"{t} SHADOW-RELEASE {a[1]} cores={cpulist(a[2])}")
            elif a[0] == "release-gpu":
                byid[a[1]] = replace(byid[a[1]], gpu="none")
                lines.append(f"{t} SHADOW-RELEASE {a[1]} gpu")
            elif a[0] in ("idle-warn", "idle-end"):
                lines.append(f"{t} SHADOW-{a[0].upper()} {a[1]} idle={a[2]}s" + (" rc=75 re-queue" if a[0] == "idle-end" else ""))
                if a[0] == "idle-end":
                    byid.pop(a[1], None)
            else:
                lines.append(f"{t} SHADOW-{a[0].upper()} {a[1]}" + (f" declared {a[2]} measured {a[3]}" if len(a) > 2 else ""))
        w.grants = list(byid.values())
        ctx["gpu_quiet_n"], ctx["gpu_quiet"] = gpu_quiet_step(int(ctx.get("gpu_quiet_n") or 0), meas.foreign_kfd)
    gq = ctx.get("gpu_quiet", True) if ctx is not None else True
    plan = admit(smoke_rank_gate(w.pending, w.smoke_queue)[0], w.grants, now, disk_free=disk_free_gib(), smoke_busy=False, gpu_quiet=gq,
                 quiet_n=(ctx or {}).get("gpu_quiet_n"))
    for rid, why in sorted(w.unmapped.items()):
        if ("SHADOW-UNMAPPED", rid) not in seen:
            seen.add(("SHADOW-UNMAPPED", rid))
            lines.append(f"{t} SHADOW-UNMAPPED {rid}: {why}")
    for g in plan.grants:
        if ("SHADOW-GRANT", g.id) not in seen:
            seen.add(("SHADOW-GRANT", g.id))
            s = w.specs[g.id]
            lines.append(f"{t} SHADOW-GRANT {g.id} cpus={cpulist(g.cores) or '-'} gpu={g.gpu} ram={g.ram_gib:g} "
                         f"start={iso(g.start)} end={iso(g.end)} rank={s['priority_rank']:g} quiet={int(g.quiet)}")
    if plan.hold:
        h = plan.hold
        lines.append(f"{t} SHADOW-HOLD {h.id} cpus={cpulist(h.cores)} gpu={int(h.gpu)} eta={iso(h.eta)}")
    for cls, n, why in plan.idle:
        lines.append(f"{t} SHADOW-IDLE-WHY {cls} free={n}: {why}")
    if w.smoke_queue:
        lines.append(f"{t} SHADOW-SMOKE-QUEUE depth={len(w.smoke_queue)} head="
                     f"{sorted(w.smoke_queue, key=smoke_order_key)[0]['id']}")
    lines.append(f"{t} SHADOW-TICK pending={len(w.pending)} grants={len(plan.grants)} open={len(w.grants)} "
                 f"unmapped={len(w.unmapped)} smoke_queue={len(w.smoke_queue)}")
    with open(log_path, "a") as f:
        f.write("\n".join(lines) + "\n")
    return w, plan


# ============================================================== diff
_LINE = re.compile(r"^(\S+Z) (GRANT|SHADOW-GRANT|IDLE-WHY|SHADOW-IDLE-WHY) (\S+?):? (.*)$")


def _parse_log(path, date, kinds):
    out = []
    with open(path, errors="replace") as f:
        for line in f:
            m = _LINE.match(line.rstrip("\n"))
            if m and m[1].startswith(date) and m[2] in kinds:
                out.append((parse_iso(m[1]), m[2], m[3], m[4]))
    return out


def _idle_hours(lines, interval_s):
    """quarter-hours and gpu-hours: each IDLE-WHY line counts until the next one of the same class (cap 2 x interval),
    weighted by free cores / 24 for quarters (a line without a count is one whole quarter)."""
    by, q, gp = {}, 0.0, 0.0
    for t, _, cls, rest in lines:
        by.setdefault(cls, []).append((t, rest))
    for cls, xs in by.items():
        xs.sort()
        for i, (t, rest) in enumerate(xs):
            dt_s = min((xs[i + 1][0] - t) if i + 1 < len(xs) else interval_s, 2 * interval_s)
            m = re.search(r"free=(\d+)|(\d+) cores free", rest)
            if re.fullmatch(r"q[0-3]", cls):
                q += dt_s / 3600 * ((int(m[1] or m[2]) / 24) if m else 1.0)
            elif cls in ("gpu", "gpu-quiet"):
                gp += dt_s / 3600
    return round(q, 2), round(gp, 2)


def diff(keeper_log, shadow_log, date, interval_s=120):
    live = _parse_log(keeper_log, date, {"GRANT", "IDLE-WHY"})
    sh = _parse_log(shadow_log, date, {"SHADOW-GRANT", "SHADOW-IDLE-WHY"})
    lg = {}
    for t, k, rid, rest in live:
        if k == "GRANT":
            lg.setdefault(rid, []).append((t, rest))
    sg = {rid: (t, rest) for t, k, rid, rest in sh if k == "SHADOW-GRANT"}
    rows, dis = [], []
    for rid in sorted(set(lg) | set(sg)):
        r = {"id": rid, "live_grants": len(lg.get(rid, []))}
        if rid in lg:
            t, rest = lg[rid][0]
            kv = dict(re.findall(r"(\w+)=(\S+)", rest))
            c1, g1 = tokens_of_legacy(kv.get("regions", ""))
            c2, g2 = tokens_of_legacy(kv.get("holds", ""))
            r.update(live_at=iso(t), live_cpus=cpulist(c1), live_gpu="exclusive" if "exclusive" in (g1, g2) else g1)
        if rid in sg:
            t2, rest2 = sg[rid]
            kv2 = dict(re.findall(r"(\w+)=(\S+)", rest2))
            r.update(shadow_at=iso(t2), shadow_cpus=kv2.get("cpus"), shadow_gpu=kv2.get("gpu"))
        if rid in lg and rid in sg:
            r["start_delta_s"] = int(lg[rid][0][0] - sg[rid][0])
            sc = set() if r["shadow_cpus"] in (None, "-") else _expand(r["shadow_cpus"])
            r["cpus_match"] = sc == (_expand(r["live_cpus"]) if r["live_cpus"] else set())
            r["gpu_match"] = r["shadow_gpu"] == r["live_gpu"]
            if not (r["cpus_match"] and r["gpu_match"]) or abs(r["start_delta_s"]) > 2 * interval_s:
                dis.append(r)
        else:
            r["only"] = "live" if rid in lg else "shadow"
            dis.append(r)
        if r["live_grants"] > 1:
            r["double_grant"] = True
        rows.append(r)
    lq, lgp = _idle_hours([x for x in live if x[1] == "IDLE-WHY"], interval_s)
    sq, sgp = _idle_hours([x for x in sh if x[1] == "SHADOW-IDLE-WHY"], interval_s)
    return {"date": date, "live_grants": sum(len(v) for v in lg.values()), "shadow_grants": len(sg),
            "matched": sum(1 for r in rows if "start_delta_s" in r), "only_live": sum(1 for r in rows if r.get("only") == "live"),
            "only_shadow": sum(1 for r in rows if r.get("only") == "shadow"),
            "idle": {"live": {"quarter_h": lq, "gpu_h": lgp}, "shadow": {"quarter_h": sq, "gpu_h": sgp}},
            "rows": rows, "disagreements": dis}


def diff_markdown(d):
    out = [f"# rowflow2 shadow diff {d['date']}", "",
           f"live GRANTs {d['live_grants']} · shadow GRANTs {d['shadow_grants']} · matched {d['matched']} · "
           f"live-only {d['only_live']} · shadow-only {d['only_shadow']}", "",
           "| side | idle quarter-h | idle gpu-h |", "|---|---|---|",
           f"| live | {d['idle']['live']['quarter_h']} | {d['idle']['live']['gpu_h']} |",
           f"| shadow | {d['idle']['shadow']['quarter_h']} | {d['idle']['shadow']['gpu_h']} |", "",
           "## Disagreements", "", "| id | live at / cpus / gpu | shadow at / cpus / gpu | Δstart s | note |", "|---|---|---|---|---|"]
    for r in d["disagreements"]:
        note = r.get("only", "") and f"{r['only']}-only"
        if r.get("double_grant"):
            note += " DOUBLE-GRANT"
        out.append(f"| {r['id']} | {r.get('live_at', '-')} / {r.get('live_cpus', '-')} / {r.get('live_gpu', '-')} | "
                   f"{r.get('shadow_at', '-')} / {r.get('shadow_cpus', '-')} / {r.get('shadow_gpu', '-')} | "
                   f"{r.get('start_delta_s', '-')} | {note} |")
    return "\n".join(out) + "\n"


# ============================================================== CLI
def map_report(flags):
    out = {"total": 0, "mapped": 0, "unmapped": 0, "live_unmapped": 0, "reasons": {}, "rows": []}
    for p in sorted(glob.glob(os.path.join(flags, "ready", "*.json"))):
        d = load_json(p)
        if not d or not d.get("id"):
            continue
        out["total"] += 1
        spec, why = (d, None) if d.get("schema") == SCHEMA else map_legacy(d)
        errs = validate(spec) if spec else []
        if spec and not errs:
            out["mapped"] += 1
            continue
        reason = ("map: " + why) if why else "admit: " + "; ".join(errs)
        done = any(_ex(flags, "grants", d["id"] + x) for x in (".ended", ".complete")) or _ex(flags, "filing-done", d["id"] + ".FILED")
        out["unmapped"] += 1
        out["live_unmapped"] += 0 if done else 1
        key = re.sub(r"\d+(\.\d+)?", "N", re.sub(r"/\S+", "<path>", reason.split(";")[0]))[:90]
        out["reasons"][key] = out["reasons"].get(key, 0) + 1
        out["rows"].append({"id": d["id"], "done": done, "reason": reason})
    out["reasons"] = dict(sorted(out["reasons"].items(), key=lambda kv: -kv[1]))
    return out


def status_json(flags, now=None):
    w = load_world(flags, time.time() if now is None else now)
    return {"at": iso(time.time()), "counts": {s: list(w.state.values()).count(s) for s in sorted(set(w.state.values()))},
            "open_grants": [{"id": g.id, "cpus": cpulist(g.cores), "gpu": g.gpu, "quiet": g.quiet, "end": iso(g.end),
                             "smoke": g.smoke} for g in w.grants],
            "rows": {rid: {"state": st, "reason": w.unmapped.get(rid)} for rid, st in sorted(w.state.items())}}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rowflow2.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("shadow")
    s.add_argument("--flags", default=FLAGS)
    s.add_argument("--log", required=True)
    s.add_argument("--once", action="store_true")
    s.add_argument("--interval", type=int, default=120)
    d = sub.add_parser("diff")
    d.add_argument("--keeper-log", required=True)
    d.add_argument("--shadow-log", required=True)
    d.add_argument("--date", required=True)
    d.add_argument("--json", action="store_true")
    st = sub.add_parser("status")
    st.add_argument("--flags", default=FLAGS)
    st.add_argument("--json", action="store_true")
    mr = sub.add_parser("map-report")
    mr.add_argument("--flags", default=FLAGS)
    mr.add_argument("--json", action="store_true")
    up = sub.add_parser("unpark", help="operator: lift a refusal park so the row is re-admitted next tick")
    up.add_argument("--flags", default=FLAGS)
    up.add_argument("--id", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "unpark":
        return 0 if unpark(a.flags, a.id) else 1
    if a.cmd in ("status", "map-report"):
        guard_readonly(a.flags)   # read-only surfaces
    if a.cmd == "shadow":
        seen, cache, ctx = None, {}, {}
        while True:
            w, plan = shadow_once(a.flags, a.log, seen=seen, sha_cache=cache, ctx=ctx)
            seen = _logged(a.log)
            if a.once:
                print(f"shadow: pending={len(w.pending)} would-grant={len(plan.grants)} unmapped={len(w.unmapped)} -> {a.log}")
                return 0
            time.sleep(a.interval)
    if a.cmd == "diff":
        r = diff(a.keeper_log, a.shadow_log, a.date)
        print(json.dumps(r, indent=1) if a.json else diff_markdown(r))
        return 0
    if a.cmd == "status":
        print(json.dumps(status_json(a.flags), indent=1))
        return 0
    if a.cmd == "map-report":
        r = map_report(a.flags)
        if a.json:
            print(json.dumps(r, indent=1))
        else:
            print(f"total {r['total']} mapped {r['mapped']} unmapped {r['unmapped']} (not done: {r['live_unmapped']})")
            for k, v in r["reasons"].items():
                print(f"{v:5d}  {k}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
