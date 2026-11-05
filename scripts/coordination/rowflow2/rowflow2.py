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

Pure core (tests drive these): parse_cpus, validate, map_legacy, admit, reconcile, smoke_step, file_decisions.
IO adapters: load_world, tick (live mode; used only by the tests' temp flags dir), shadow, diff, status, map-report.
In shadow mode a process-wide audit hook refuses every write-intent filesystem event under the flags dir.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import glob
import hashlib
import json
import os
import re
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
TUNABLES = ("SMOKE_CORES", "IDLE_SAMPLES", "IDLE_PCT", "SMOKE_DEADLINE_S", "OVERRUN_FACTOR", "QUIET_MAX_RANK",
            "FILE_OWNERLESS_S", "CLAIM_TTL_S")

# ============================================================== config (paths / env - not tunables)
FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/" + "tmp/compute-flags")
KFD_PROC = os.environ.get("ROWFLOW2_KFD_PROC", "/sys/class/kfd/kfd/proc")
PROC = os.environ.get("ROWFLOW2_PROC", "/proc")
RAM_BOOKABLE_GIB = float(os.environ.get("ROWFLOW2_RAM_GIB", "1069"))     # rowflow QUARTER_RAM_GIB x 4, rounded
DISK_PATH = os.environ.get("ROWFLOW2_DISK_PATH", "/mnt/raid0")
DISK_FLOOR_GIB = float(os.environ.get("ROWFLOW2_DISK_FLOOR_GIB", "150"))  # == filler_run15 FILLER_DISK_FLOOR_GIB
CONFIG = ("FLAGS", "KFD_PROC", "PROC", "RAM_BOOKABLE_GIB", "DISK_PATH", "DISK_FLOOR_GIB")

# ============================================================== host facts + vocabulary (not tunables)
NCORES = 96
GPU_HOST_THREADS = frozenset(range(184, 192))   # part of the gpu token
QUARTERS = tuple(frozenset(range(24 * q, 24 * q + 24)) - SMOKE_CORES for q in range(4))
ROW_CORES = frozenset(range(NCORES)) - SMOKE_CORES
SCHEMA = "epyc.row.v4"
LEGACY_SCHEMA = "epyc.row.v3"
GPU_MODES = ("none", "shared", "exclusive")
ENDED_REASONS = ("complete", "exit", "stopped", "superseded", "withdrawn", "dead-poller", "disk-floor", "window-end")
SPEC_FIELDS = {"id": str, "owner": str, "handoff_task": str, "launcher": str, "stop_file": str, "cpus": (int, str),
               "threads": int, "gpu": str, "quiet": bool, "ram_gib": (int, float), "disk_gib": (int, float),
               "estimate_s": (int, float), "min_window_s": (int, float), "decision_rule": str,
               "priority_rank": (int, float)}
SPEC_OPTIONAL = {"quiet_reason": str, "measured_ack": str, "supersedes": (str, list), "fix_ref": str,
                 "published_at": str, "schema": str, "legacy": dict}
FACTS = ("NCORES", "GPU_HOST_THREADS", "QUARTERS", "ROW_CORES", "SCHEMA", "LEGACY_SCHEMA", "GPU_MODES",
         "ENDED_REASONS", "SPEC_FIELDS", "SPEC_OPTIONAL", "FACTS", "TUNABLES", "CONFIG")


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

    def min_width(self):
        return self.width if self.options is None else min(len(o) for o in self.options)

    def allowed(self):
        return self.pool if self.options is None else frozenset().union(*self.options)


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


def fits_need(need, cores):
    """Two-sided invariant (i): is `cores` a legal grant for `need`?"""
    if need.options is not None:
        return frozenset(cores) in need.options
    return len(cores) == need.width and frozenset(cores) <= need.pool


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
    if regions == "any-cpu-quarter":
        cpus = "any-quarter"
    elif regions.startswith("any-of "):
        cpus = "any-quarter-of-" + regions[len("any-of "):].replace(" ", "")
    else:
        cpus = ",".join(cpu_items) if cpu_items else 0
    try:
        need = parse_cpus(cpus)
    except ValueError as e:
        return None, f"regions {regions!r}: {e}"
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
    for k in ("supersedes", "fix_ref"):
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
    if need.options is not None:
        return next((o for o in need.options if o <= usable), None)
    cand = need.pool & usable
    if len(cand) < need.width:
        return None
    by_q = sorted(((len(q & cand), i) for i, q in enumerate(QUARTERS) if len(q & cand) >= need.width))
    if by_q:   # best fit: the fullest quarter that still holds the whole width (NUMA-local)
        return frozenset(sorted(QUARTERS[by_q[0][1]] & cand)[:need.width])
    return frozenset(sorted(cand)[:need.width])


def admit(pending, grants, now, ram_cap=RAM_BOOKABLE_GIB, disk_free=None, smoke_busy=False):
    """Strict priority by rank (ties: publish time, id). Each row that fits the free tokens is granted. The FIRST row
    that does not fit holds the tokens it needs: a later (worse-ranked) row may take a held token only if its whole
    window ends by the held row's ETA. `quiet` takes every row token plus the gpu, and waits for an idle smoke lane."""
    plan, seen = Plan(), set()
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
    for s in _order(pending):
        rid = s["id"]
        if rid in seen:   # one decision per id per tick: a twice-published id can never be granted twice
            continue
        seen.add(rid)
        need, win = parse_cpus(s["cpus"]), window_s(s)
        h = plan.hold
        h_ok = h is None or now + win <= h.eta
        usable = free if h_ok else free - h.cores
        gpu_need = "exclusive" if s["quiet"] else s["gpu"]
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
        cores = frozenset(sorted(need.pool, key=lambda c: (free_at[c], c))[:need.width])
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
            users = [s for s in waiting if s["quiet"] or q & parse_cpus(s["cpus"]).allowed()]
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


def reconcile(grants, meas, state, now):
    """Pure: (actions, new_state). Actions: ('release-cores', id, cores), ('release-gpu', id), ('overrun', id),
    ('dead-poller', id), ('over-declared', id, declared, measured_busy). Quiet grants never release."""
    acts, new = [], {}
    for g in grants:
        if g.smoke:
            continue
        st = dict(state.get(g.id) or {"idle": {}, "gpu0": 0, "dead": 0, "alerted": False, "busy": [], "worked": False,
                                      "declared": len(g.cores), "gpu_used": False})
        st["idle"] = dict(st["idle"])
        if meas.core_busy is not None and g.cores:
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
        if g.gpu == "exclusive" and not g.quiet:
            mine = meas.own_kfd.get(g.id)
            if mine:
                st["gpu0"], st["gpu_used"] = 0, True
            elif mine is not None:
                st["gpu0"] += 1
                if st["gpu0"] >= IDLE_SAMPLES:
                    acts.append(("release-gpu", g.id))
        if g.estimate_s and now > g.start + OVERRUN_FACTOR * g.estimate_s and not st["alerted"]:
            acts.append(("overrun", g.id))
            st["alerted"] = True
        a = meas.alive.get(g.id)
        st["dead"] = st["dead"] + 1 if a is False else 0
        if st["dead"] >= IDLE_SAMPLES:
            acts.append(("dead-poller", g.id))
        new[g.id] = st
    return acts, new


def measured_summary(st):
    b = sorted(st.get("busy") or [])
    if not b or not st.get("declared"):
        return None
    p95 = b[min(len(b) - 1, int(round(0.95 * (len(b) - 1))))]
    return {"busy_p95": round(p95 / st["declared"], 3), "cpus": st["declared"], "gpu_used": bool(st.get("gpu_used"))}


# ============================================================== smoke lane (pure)
def smoke_step(queue, running, quiet_active, now):
    """FIFO, one at a time, on SMOKE_CORES. running = (id, start, deadline) | None. Paused while quiet is open/held."""
    if running:
        rid, start, deadline = running
        return [("smoke-kill", rid)] if now > deadline else []
    if queue and not quiet_active:
        head = sorted(queue, key=lambda s: (s.get("published_at") or "", s["id"]))[0]
        return [("smoke-start", head["id"], now, now + SMOKE_DEADLINE_S)]
    return []


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


# ============================================================== lineage / supersede
def lineage_fails(rid, specs, fails):
    """FAIL count along the supersedes chain back to (and including) the nearest row naming fix_ref."""
    n, cur, seen = 0, rid, set()
    while cur and cur not in seen:
        seen.add(cur)
        n += fails.get(cur, 0)
        d = specs.get(cur) or {}
        if d.get("fix_ref"):
            break
        sup = d.get("supersedes")
        cur = sup[0] if isinstance(sup, list) and sup else sup if isinstance(sup, str) else None
    return n


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
        p = load_json(os.path.join(D, rid, "PASS.json"))
        if p and p.get("launcher_sha256") == cur:
            w.pending.append(spec)
            w.state[rid] = "pending"
        elif any((load_json(f) or {}).get("launcher_sha256") == cur for f in glob.glob(os.path.join(D, rid, "FAIL-*.json"))):
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


def tick(flags, now, meas, state, log, runner=None):
    """One live tick: reconcile -> admit -> smoke lane -> file. Writes only under `flags`. Returns (plan, state)."""
    w = load_world(flags, now)
    G = os.path.join(flags, "grants")
    acts, state_new = reconcile(w.grants, meas, state.get("grants", {}), now)
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
            write_text(os.path.join(G, g.id + ".ended"), f"rc=75 reason=dead-poller time={iso(now)}\n")
            byid.pop(g.id)
            log(f"DEAD-POLLER {g.id}: grant removed")
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
        os.remove(os.path.join(flags, "dryrun", rid, "SMOKE.json"))
    plan = admit(w.pending, grants, now, disk_free=None, smoke_busy=bool(w.smoke_running))
    plan.basis = grants
    for g in plan.grants:
        write_grant(flags, g)
        log(f"GRANT {g.id} {g.line()}")
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
                       "cores": cpulist(SMOKE_CORES), "launcher_sha256": sha256(spec["launcher"])}) + "\n")
            log(f"SMOKE-START {a[1]} cores={cpulist(SMOKE_CORES)} deadline={iso(a[3])}")
            if runner:
                runner.start(a[1], SMOKE_CORES, a[3])
        else:
            if runner:
                runner.kill(a[1])
            spec = w.specs.get(a[1]) or {}
            write_text(os.path.join(dd, "FAIL-deadline.json"), json.dumps({"reason": "smoke deadline", "at": iso(now),
                       "launcher_sha256": sha256(spec["launcher"]) if spec else None}) + "\n")
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


def measure(flags, grants, prev_stat):
    """(Measurement, stat sample). A grant's own KFD pids = KFD clients inside its poller's process tree (ARMED.json
    pid), known only when that pid is visible here; poller liveness is never guessed from an invisible pid."""
    s1 = proc_stat()
    kfd, own = kfd_pids(), {}
    for g in grants:
        pid = (load_json(os.path.join(flags, "dryrun", g.id, "ARMED.json")) or {}).get("pid")
        if pid and os.path.exists(os.path.join(PROC, str(pid))):
            own[g.id] = kfd & descendants(int(pid))
    return Measurement(core_busy(prev_stat, s1) if prev_stat else None, own, {}), s1


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
            else:
                lines.append(f"{t} SHADOW-{a[0].upper()} {a[1]}" + (f" declared {a[2]} measured {a[3]}" if len(a) > 2 else ""))
        w.grants = list(byid.values())
    plan = admit(w.pending, w.grants, now, disk_free=disk_free_gib(), smoke_busy=False)
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
                     f"{sorted(w.smoke_queue, key=lambda s: (s.get('published_at') or '', s['id']))[0]['id']}")
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
    a = ap.parse_args(argv)
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
