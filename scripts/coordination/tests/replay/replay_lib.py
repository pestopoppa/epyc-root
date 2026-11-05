#!/usr/bin/env python3
"""replay_lib.py - the rowflow allocator REPLAY HARNESS (keeper-friction review 2026-11-05, P2.4 #4).

Operator 2026-11-05: "Harness first, then class fixes". Every rowflow deploy is gated on this harness.

TRACE FORMAT  epyc.rowflow.trace.v1 - JSONL (optionally .gz), content-addressed:
    {"kind": "header", "schema": "epyc.rowflow.trace.v1", "source": ..., "created": ...}
    {"kind": "blob", "h": <sha1>, "v": <object>}          # emitted once, before the first tick that cites it
    {"kind": "tick", "t": <epoch>, "rows": {rid: <blob h>}, "foreign": {region: tag},
     "util": {q0..q3: pct, gpu: {busy, vram_pct}}, "mem_gib": f, "vram_bytes": i, "disk_free_gib": f,
     "observed": {...what production did this tick, informational...}}
  A row blob is everything `rowflow.py allocate` reads about one row:
    {"manifest": ready/<id>.json, "launcher_text": str, "files": {abspath: text} (job files its --cmd names),
     "pass": PASS.json|null, "pass_matches": bool, "fails": [FAIL records], "stopped": bool,
     "smoke_queued": SMOKE-QUEUED.json|null, "running": RUNNING.json|null, "running_alive": bool,
     "dry_grant": dryrun/<id>/grants/*.grant text|null}
  A row absent from a tick's `rows` does not exist (not yet published, withdrawn, or ended outside the replay).

REPLAY  (closed loop) - each tick the sandbox flags dir is brought to the trace's world (rows, PASS/FAIL, STOP files,
  queued smokes, live dry runs, foreign region-lock holds, measured util, RAM, disk), the CANDIDATE rowflow.py's own
  `allocate()` runs against it (non-dry) with a fake clock, and the grants it writes become simulated jobs that hold
  their regions for estimate_s, then write `.ended`. Nothing real is ever touched: subprocess, os.kill/os.killpg,
  region-lock, /proc, rocm-smi, arming and launcher admission are replaced by recorders. Every path a row names
  (/mnt/raid0/..., /workspace/...) is rewritten under <sandbox>/fs.
  A stopped row's grant is released by the simulated engine WITHOUT an `.ended` (the F4 world): the allocator alone
  must keep it from being granted again.

INVARIANTS are evaluated by the harness's own oracle (`contract_lite`, parsed from the launcher text), never by the
candidate's code - see INVARIANTS below.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import glob
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess as _real_subprocess
import sys
import time as _real_time
import types

SCHEMA = "epyc.rowflow.trace.v1"
QUARTERS = ("q0", "q1", "q2", "q3")
GPU = "gpu-quiet"
GPU_THREADS = frozenset(range(184, 192))
IDLE_N_TICKS = 3            # INV-IDLE-NAMED: consecutive unexplained idle ticks tolerated
LIVENESS_TICKS = 3          # scenario liveness bound (a drain may take one tick)
TICK_CAP_S = 300            # idle-hours integration: a gap longer than this counts as TICK_CAP_S


# ------------------------------------------------------------------------------------------------ trace I/O
def _h(v):
    return hashlib.sha1(json.dumps(v, sort_keys=True).encode()).hexdigest()


class TraceWriter:
    def __init__(self, path, source, notes=""):
        self.path, self.seen = path, set()
        op = gzip.open if path.endswith(".gz") else open
        self.f = op(path, "wt")
        self._w({"kind": "header", "schema": SCHEMA, "source": source, "notes": notes,
                 "created": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})

    def _w(self, rec):
        self.f.write(json.dumps(rec, sort_keys=True) + "\n")

    def tick(self, t, rows, **world):
        ref = {}
        for rid, blob in sorted(rows.items()):
            h = _h(blob)
            if h not in self.seen:
                self.seen.add(h); self._w({"kind": "blob", "h": h, "v": blob})
            ref[rid] = h
        self._w(dict({"kind": "tick", "t": float(t), "rows": ref}, **world))

    def close(self):
        self.f.close()


def read_trace(path):
    """-> (header, [tick dicts with rows resolved to blobs])"""
    op = gzip.open if path.endswith(".gz") else open
    blobs, ticks, header = {}, [], None
    with op(path, "rt") as f:
        for line in f:
            r = json.loads(line)
            k = r.get("kind")
            if k == "header":
                header = r
            elif k == "blob":
                blobs[r["h"]] = r["v"]
            elif k == "tick":
                r = dict(r); r["row_h"] = r["rows"]; r["rows"] = {rid: blobs[h] for rid, h in r["rows"].items()}
                ticks.append(r)
    if not header or header.get("schema") != SCHEMA:
        raise ValueError(f"{path}: not an {SCHEMA} trace")
    return header, ticks


# ------------------------------------------------------------------------------------------------ token helpers
def qcores(q):
    n = int(q[1]) * 24
    return set(range(n, n + 24))


def cpu_set(s):
    out = set()
    for tok in str(s or "").split(","):
        tok = tok.strip()
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", tok)
        if m:
            a = int(m.group(1)); b = int(m.group(2) or a)
            out |= set(range(a, b + 1))
    return out


def tokens_to_cores(tokens):
    """{q0, c5, t101, gpu-quiet} -> physical core numbers (threads fold onto their core)."""
    out = set()
    for t in tokens:
        if t in QUARTERS:
            out |= qcores(t)
        elif re.fullmatch(r"c\d+", t):
            out.add(int(t[1:]))
        elif re.fullmatch(r"t\d+", t):
            out.add(int(t[1:]) - 96)
    return out


def _cpus_of(tokens):
    """hold tokens -> cpu numbers WITHOUT folding SMT siblings (a quarter = its cores and their siblings)."""
    out = set()
    for t in tokens:
        if t in QUARTERS:
            out |= qcores(t) | {c + 96 for c in qcores(t)}
        elif re.fullmatch(r"[ct]\d+", t):
            out.add(int(t[1:]))
    return out


def full_quarters(cores):
    return {q for q in QUARTERS if qcores(q) <= set(cores)}


# ------------------------------------------------------------------------------------------------ oracle
_THREADS = (re.compile(r"(?<![\w-])-t\s+['\"]?(\d+)\b"), re.compile(r"--threads[ =]+['\"]?(\d+)\b"),
            re.compile(r"--workers[ =]+['\"]?(\d+)\b"), re.compile(r"\bOMP_NUM_THREADS=['\"]?(\d+)\b"))


def contract_lite(blob):
    """The harness's independent reading of a row (never the candidate's): class, claim, gpu_quiet, role, threads,
    timing, evidence. Python `"-t", THREADS` with THREADS = "48" resolves (the npd1-step5 idiom)."""
    m = blob.get("manifest") or {}
    text = (blob.get("launcher_text") or "") + "\n" + "\n".join((blob.get("files") or {}).values())
    joined = re.sub(r"\\\n", " ", text)

    def opt(name):
        x = re.search(rf"{name}[ =]+(\"[^\"]*\"|'[^']*'|\S+)", joined)
        return x.group(1).strip("\"'") if x else ""
    pyv = dict(re.findall(r"^[ \t]*([A-Za-z_]\w*)\s*=\s*[\"']?(\d+)[\"']?\s*(?:#.*)?$", text, re.M))
    t2 = re.sub(r"""[\"'](-t|--threads|--workers)[\"']\s*,\s*(?:[\"'](\d+)[\"']|([A-Za-z_]\w*))""",
                lambda x: f" {x.group(1)} {x.group(2) or pyv.get(x.group(3), '')}", text)
    threads = None
    for line in t2.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for rx in _THREADS:
            for x in rx.finditer(line):
                n = int(x.group(1))
                if 0 < n <= 192:
                    threads = max(threads or 0, n)
    if threads is None and m.get("declared_threads"):
        threads = int(m["declared_threads"])
    p = blob.get("pass") or {}
    if p.get("measured_threads"):
        threads = max(threads or 0, int(p["measured_threads"]))
    cls, role = opt("--class"), opt("--role")
    regs = str(m.get("regions") or "")
    gpu_row = "mi210" in regs or cls in ("gpu", "cpu+gpu") or m.get("lane") == "gpu"
    gpu_uses = gpu_row and m.get("gpu_use") != "quiet-only" and not (cls == "cpu+gpu" and (p.get("vram_used_max_bytes") or 0) < (1 << 30) and "vram_used_max_bytes" in p)
    timing = role == "bench" or m.get("admission_class") in ("block-timing-pairable", "block-timing-quiet") \
        or str(m.get("timing") or "") in ("bench", "profile", "ak-keep-gate")
    evidence = (threads or 0) >= 48 or bool(str(m.get("baseline_ref") or "").strip()) or bool(str(m.get("shape_override") or "").strip())
    claim = opt("--claim-cpus")
    nofold = "--no-fold-siblings" in joined
    # lock set the engine takes (region-lock): a claim covering a whole quarter locks that quarter EXCLUSIVE; a
    # sub-quarter claim locks only its cores; a GPU row with --no-fold-siblings (GRANT_CPUS engines) locks its regions' cpus
    if cls == "gpu" and (nofold or not claim):
        lock_cores = cpu_set(",".join(x for x in regs.split(",") if not x.startswith("mi210")))
    else:
        lock_cores = cpu_set(claim)
    return {"class": cls, "role": role, "claim": claim, "gpu_quiet": opt("--gpu-quiet"), "threads": threads,
            "gpu_row": gpu_row, "gpu_uses": gpu_uses, "timing": timing, "evidence": evidence,
            "lock_cores": lock_cores, "lock_ex_quarters": full_quarters({c for c in lock_cores if c < 96}),
            "coexist_marked": m.get("coexist_quiet_host") == "gitnexus-q3"}


# ------------------------------------------------------------------------------------------------ sandbox runtime
class World:
    """Everything the patched module functions answer from."""
    def __init__(self):
        self.t = 0.0
        self.alive = set()
        self.kfd = {}
        self.rl = {}
        self.util = {"q0": 0.0, "q1": 0.0, "q2": 0.0, "q3": 0.0, "gpu": {"busy": 0, "vram_pct": 0.0, "vram_gib": 0.0}}
        self.mem_gib = 900.0
        self.vram = 0
        self.disk = 400.0
        self.kills = []
        self.spawned = []
        self.next_pid = 900000

    def pid(self):
        self.next_pid += 1
        self.alive.add(self.next_pid)
        return self.next_pid


W = World()


class _FakeProc:
    def __init__(self, args, *a, **k):
        self.args, self.pid, self.returncode = args, W.pid(), None
        W.spawned.append({"t": W.t, "pid": self.pid, "args": [str(a) for a in args]})

    def wait(self, timeout=None): return 0
    def poll(self): return None
    def kill(self): W.alive.discard(self.pid)
    terminate = kill


def _fake_run(args, *a, **k):
    W.spawned.append({"t": W.t, "run": [str(x) for x in (args if isinstance(args, (list, tuple)) else [args])]})
    return _real_subprocess.CompletedProcess(args, 1, "" if k.get("text") else b"", "" if k.get("text") else b"")


def _guard_subprocess():
    m = types.ModuleType("subprocess_guard")
    for k in dir(_real_subprocess):
        setattr(m, k, getattr(_real_subprocess, k))
    m.run, m.Popen = _fake_run, _FakeProc
    m.check_output = lambda *a, **k: b""
    m.call = lambda *a, **k: 1
    return m


class _FakeTime(types.ModuleType):
    def __init__(self):
        super().__init__("time_shim")
        for k in dir(_real_time):
            # never copy the real time/sleep/monotonic: an instance attribute shadows the fake methods below (found
            # 2026-11-05 by the idle-held scenarios: every candidate read the REAL clock, so grant ages were ~22 h)
            if not k.startswith("__") and k not in ("time", "sleep", "monotonic"):
                setattr(self, k, getattr(_real_time, k))

    def time(self): return W.t
    def sleep(self, s): W.t += float(s)
    def monotonic(self): return W.t


class _FakeDateTime(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return _dt.datetime.fromtimestamp(W.t, tz or _dt.timezone.utc)

    @classmethod
    def utcnow(cls):
        return _dt.datetime.utcfromtimestamp(W.t)


def _fake_dt():
    m = types.ModuleType("datetime_shim")
    for k in dir(_dt):
        if not k.startswith("__"):
            setattr(m, k, getattr(_dt, k))
    m.datetime = _FakeDateTime
    return m


def _kill(pid, sig):
    W.kills.append({"t": W.t, "pid": int(pid), "sig": int(sig)})
    W.alive.discard(abs(int(pid)))


def load_candidate(rowflow_dir, flags, tmp):
    """Import the candidate rowflow.py (and its sibling modules) from rowflow_dir, fully sandboxed."""
    os.environ.update(ROWFLOW_FLAGS=flags, ROWFLOW_TMP=tmp + "/", ROWFLOW_RL="/nonexistent/region-lock",
                      ROWFLOW_ALARM_CHANNEL="/nonexistent/alarm_channel.py")
    sys.path.insert(0, rowflow_dir)
    os.kill = _kill
    os.killpg = _kill
    sp, tm, dm = _guard_subprocess(), _FakeTime(), _fake_dt()
    for name in ("hostutil", "notify"):
        try:
            mod = __import__(name)
            for attr, val in (("subprocess", sp), ("time", tm), ("dt", dm)):
                if hasattr(mod, attr):
                    setattr(mod, attr, val)
        except Exception:  # noqa: BLE001 - an old tree may lack one
            pass
    spec = importlib.util.spec_from_file_location("rowflow_candidate", os.path.join(rowflow_dir, "rowflow.py"))
    rf = importlib.util.module_from_spec(spec)
    sys.modules["rowflow_candidate"] = rf
    spec.loader.exec_module(rf)
    rf.subprocess, rf.time, rf.dt = sp, tm, dm
    rf.FLAGS, rf.TMP = flags, tmp + "/"
    if hasattr(rf, "ALARM_CHANNEL"):
        rf.ALARM_CHANNEL = "/nonexistent/alarm_channel.py"

    def patch(name, fn):
        if hasattr(rf, name):
            setattr(rf, name, fn)
    patch("alive", lambda pid: bool(pid) and _int(pid) in W.alive)
    patch("rl_status", lambda: dict(W.rl))
    patch("measure_util", lambda *a, **k: json.loads(json.dumps(W.util)))
    patch("mem_available_gib", lambda: W.mem_gib)
    patch("vram_used_bytes", lambda: W.vram)
    patch("gpu_occupancy", lambda: {"pids": {int(k): int(v) for k, v in W.kfd.items()}, "vram_used": W.vram})
    patch("disk_free_gib", lambda *a, **k: W.disk)
    patch("cpu_sample", lambda *a, **k: {})
    patch("armed_engine_ok", lambda pid, rid, proc="/proc": bool(pid) and _int(pid) in W.alive)
    patch("row_orphans", lambda rid: [])
    patch("admit", lambda flags, rid, d, pid, regions, window_s: (True, f"replay-admit {rid} regions={regions}"))

    def arm_one(flags, rid, d, regions=None, log=print):
        pid = W.pid()
        rec = {"id": rid, "pid": pid, "regions": d.get("regions"), "at": rf.now_iso()}
        if hasattr(rf, "_engine_sha"):   # the real arm_one records the engine code the poller runs
            rec["engine_sha256"] = rf._engine_sha(d)
        rf.atomic_json(rf.armed_path(flags, rid), rec)
        return pid, f"ARMED {rid} pid={pid}"
    patch("arm_one", arm_one)
    try:
        import hostutil
        hostutil.measure = lambda *a, **k: json.loads(json.dumps(W.util))
    except Exception:  # noqa: BLE001
        pass
    try:
        import notify
        for fn in ("is_live",):
            if hasattr(notify, fn):
                setattr(notify, fn, lambda *a, **k: False)
        if hasattr(notify, "disk_floor_check"):
            notify.disk_floor_check = lambda *a, **k: None
    except Exception:  # noqa: BLE001
        pass
    return rf


def _int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return -1


_PATH_RX = re.compile(r"(?<![\w/.-])/(mnt/raid0|workspace)/")


def rewriter(fsroot):
    return lambda s: _PATH_RX.sub(lambda m: f"{fsroot}/{m.group(1)}/", s)


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def _jdump(path, obj):
    _write(path, json.dumps(obj, indent=1, sort_keys=True) + "\n")


def _iso(t):
    return _dt.datetime.fromtimestamp(t, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Sandbox:
    def __init__(self, root):
        self.root = root
        self.flags = os.path.join(root, "flags")
        self.fs = os.path.join(root, "fs")
        self.tmp = os.path.join(root, "tmp")
        for d in ("ready", "grants", "dryrun", "state", "filing-done"):
            os.makedirs(os.path.join(self.flags, d), exist_ok=True)
        os.makedirs(self.tmp, exist_ok=True)
        self.rw = rewriter(self.fs)
        self.mat = {}          # rid -> blob hash materialized
        self.sim = {}          # rid -> {start, end, holds, pid, granted_n}
        self.ended = set()     # rids the simulation ended
        self.engine_src = None    # the candidate's filler_run15.sh
        self.stop_released = {}  # rid -> times its grant was released by the stopped engine without .ended

    # -- world -> sandbox
    def materialize(self, tick, rf):
        rows = tick["rows"]
        for rid in list(self.mat):
            if rid not in rows:
                for p in (os.path.join(self.flags, "ready", rid + ".json"),):
                    with contextlib.suppress(OSError):
                        os.remove(p)
                self.mat.pop(rid)
                if rid in self.sim:
                    self._end(rid, "row-left-trace")
        for rid, blob in rows.items():
            h = tick["row_h"][rid]
            if self.mat.get(rid) == h:
                self._stopfile(rid, blob)
                continue
            self.mat[rid] = h
            man = json.loads(self.rw(json.dumps(blob["manifest"])))
            lp = man.get("launcher", {}).get("path") or os.path.join(self.fs, "launchers", rid, "launch.sh")
            _write(lp, self.rw(blob.get("launcher_text") or "#!/bin/bash\n"))
            for p, txt in (blob.get("files") or {}).items():
                _write(self.rw(p), self.rw(txt))
            # the engine a row runs is the CANDIDATE's engine (deploy ships rowflow.py and filler_run15.sh together)
            for ep in {man.get("engine", {}).get("path") or ""} | set(re.findall(r"(\S+/filler_run15\.sh)", self.rw(blob.get("launcher_text") or ""))):
                if ep.startswith(self.fs) and ep.endswith("filler_run15.sh") and self.engine_src and not os.path.exists(ep):
                    _write(ep, open(self.engine_src).read())
            lsha = _sha(lp)
            man.setdefault("launcher", {})["sha256"] = lsha
            _jdump(os.path.join(self.flags, "ready", rid + ".json"), man)
            dd = os.path.join(self.flags, "dryrun", rid)
            os.makedirs(dd, exist_ok=True)
            for old in glob.glob(os.path.join(dd, "FAIL-*.json")) + [os.path.join(dd, "PASS.json")]:
                with contextlib.suppress(OSError):
                    os.remove(old)
            if blob.get("pass"):
                p = dict(blob["pass"])
                p["launcher_sha256"] = lsha if blob.get("pass_matches", True) else "stale"
                _jdump(os.path.join(dd, "PASS.json"), json.loads(self.rw(json.dumps(p))))
            for i, f in enumerate(blob.get("fails") or []):
                f = dict(f); f["launcher_sha256"] = lsha if f.get("_matches", True) else "stale"
                f.pop("row_sha256", None)
                _jdump(os.path.join(dd, f"FAIL-{i + 1}.json"), f)
            if blob.get("smoke_queued") is not None:
                _jdump(os.path.join(dd, "SMOKE-QUEUED.json"), blob["smoke_queued"])
            if blob.get("running") is not None:
                r = dict(blob["running"])
                r["pid"] = W.pid() if blob.get("running_alive") else 1
                if not blob.get("running_alive"):
                    W.alive.discard(1)
                _jdump(os.path.join(dd, "RUNNING.json"), r)
            if blob.get("dry_grant"):
                _write(os.path.join(dd, "grants", rid + ".grant"), blob["dry_grant"])
            self._stopfile(rid, blob)

    def _stopfile(self, rid, blob):
        man = json.loads(self.rw(json.dumps(blob["manifest"])))
        sf = man.get("stop_file") or ""
        if not sf.startswith("/"):
            m = re.search(r"--stop[ =]+(\"[^\"]*\"|'[^']*'|\S+)", self.rw(blob.get("launcher_text") or ""))
            sf = m.group(1).strip("\"'") if m else ""
            if sf.startswith("$D/") or sf.startswith("${D}/"):
                sf = os.path.join(os.path.dirname(man["launcher"]["path"]), sf.split("/", 1)[1])
        if not sf.startswith("/"):
            return
        if blob.get("stopped"):
            if not os.path.exists(sf):
                _write(sf, "STOP\n")
        else:
            with contextlib.suppress(OSError):
                os.remove(sf)

    # -- simulated engine
    def _end(self, rid, reason, rc=0):
        g = os.path.join(self.flags, "grants", rid + ".grant")
        with contextlib.suppress(OSError):
            os.remove(g)
        _write(os.path.join(self.flags, "grants", rid + ".ended"), f"rc={rc} time={_iso(W.t)} reason={reason}\n")
        s = self.sim.pop(rid, None)
        if s:
            W.alive.discard(s.get("pid"))
        self.ended.add(rid)

    def advance(self, tick):
        """Simulated engines: a stopped row's engine releases its grant WITHOUT .ended (F4); a running job ends at its estimate."""
        for rid, s in list(self.sim.items()):
            blob = tick["rows"].get(rid)
            if blob and blob.get("stopped") and not s.get("started"):
                with contextlib.suppress(OSError):
                    os.remove(os.path.join(self.flags, "grants", rid + ".grant"))
                self.sim.pop(rid)
                self.stop_released[rid] = self.stop_released.get(rid, 0) + 1
                continue
            s["started"] = True
            if W.t >= s["end"]:
                self._end(rid, "complete")
        # smokes the candidate spawned: done after 300 s (queue record removed; the smoke's verdict is not simulated)
        for p in glob.glob(os.path.join(self.flags, "dryrun", "*", "SMOKE-PLACED.json")):
            try:
                r = json.load(open(p))
            except (OSError, ValueError):
                continue
            if W.t - (_epoch(r.get("at")) or W.t) >= 300:
                W.alive.discard(_int(r.get("pid")))
                for q in (p, os.path.join(os.path.dirname(p), "SMOKE-QUEUED.json")):
                    with contextlib.suppress(OSError):
                        os.remove(q)

    def stamp(self, since_real):
        """Files written during a tick get the fake clock as mtime (grant ages, idle-held, heal)."""
        for dp, _, fs in os.walk(self.flags):
            for f in fs:
                p = os.path.join(dp, f)
                with contextlib.suppress(OSError):
                    if os.path.getmtime(p) >= since_real - 1:
                        os.utime(p, (W.t, W.t))


def _epoch(s):
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try:
            return _dt.datetime.strptime(str(s), f).replace(tzinfo=_dt.timezone.utc).timestamp()
        except (ValueError, TypeError):
            pass
    return None


_LINE_KINDS = ("GRANT", "DRAIN", "DRAIN-HELD", "NO-DRAIN", "RANK-SKIP", "RANK-HOLD", "IDLE-WHY", "IDLE-VIOLATION",
               "IDLE-HELD", "SMOKE-WAIT", "SMOKE-PLACE", "WAIT", "SKIP", "ERROR", "HEAL", "SNAPSHOT", "CONFLICT",
               "ROW-ARM", "RE-PLAN", "PLAN", "SHAPE-DOWNSIZE", "BACKFILL", "RECLAIM", "REAP", "DRYRUN-REAP", "HOLD")


def _kind(line):
    w = line.split(" ", 1)[0]
    return w if w in _LINE_KINDS else "OTHER"


def run_replay(rowflow_dir, trace_path, out_dir, max_ticks=None):
    """Replay one trace through one candidate. Writes out_dir/decisions.jsonl; returns the decisions list."""
    os.makedirs(out_dir, exist_ok=True)
    sb = Sandbox(os.path.join(out_dir, "sandbox"))
    header, ticks = read_trace(trace_path)
    if max_ticks:
        ticks = ticks[:max_ticks]
    rf = load_candidate(rowflow_dir, sb.flags, sb.tmp)
    eng = os.path.join(rowflow_dir, "filler_run15.sh")
    sb.engine_src = eng if os.path.exists(eng) else None
    engine_locks = bool(sb.engine_src) and "CONTRACT_LOCK" in open(eng).read()
    decisions = []
    for i, tick in enumerate(ticks):
        W.t = float(tick["t"])
        W.rl = {r: ("EXCL", tag) for r, tag in (tick.get("foreign") or {}).items()}
        for r in QUARTERS + (GPU,):
            W.rl.setdefault(r, ("free", ""))
        if tick.get("util"):
            W.util = tick["util"]
        W.mem_gib = float(tick.get("mem_gib") or 900.0)
        W.vram = int(tick.get("vram_bytes") or 0)
        W.kfd = dict(tick.get("kfd") or {})   # host-view KFD clients {pid: vram bytes} (foreign containers included)
        W.disk = float(tick.get("disk_free_gib") or 400.0)
        sb.advance(tick)
        sb.materialize(tick, rf)
        open_before = {rid: dict(s) for rid, s in sb.sim.items()}
        kills0, fails0 = len(W.kills), set(glob.glob(os.path.join(sb.flags, "dryrun", "*", "FAIL-*.json")))
        lines, err = [], None
        real0 = _real_time.time()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rf.allocate(sb.flags, keeper_log=os.path.join(sb.flags, "keeper.log"), log=lambda m: lines.append(str(m)))
        except Exception as e:  # noqa: BLE001 - a crash is a decision too
            err = f"{type(e).__name__}: {e}"
        sb.stamp(real0)
        grants = []
        for ln in lines:
            m = re.match(r"GRANT (\S+) .*?regions=(\S+).*?holds=(\S+)", ln)
            if not m:
                continue
            rid, regions, holds = m.group(1), m.group(2), set(m.group(3).split(","))
            # lock=LIST counts as the engine's claim only when the candidate engine parses it (filler_run15 CONTRACT_LOCK)
            ml = re.search(r" lock=(\S+)", ln)
            lock = ml.group(1) if ml and engine_locks else ""
            blob = tick["rows"].get(rid) or {}
            est = float((blob.get("manifest") or {}).get("estimate_s") or (blob.get("manifest") or {}).get("window_s") or 600)
            a = rf.load_json(rf.armed_path(sb.flags, rid)) or {}
            sb.sim[rid] = {"start": W.t, "end": W.t + est, "holds": sorted(holds), "regions": regions, "pid": a.get("pid"),
                           "lock": lock}
            # the engine logs START so heal_grants sees a started grant
            _write(os.path.join(sb.flags, "dryrun", rid, "poller.out"), f"START regions={regions}\n")
            os.utime(os.path.join(sb.flags, "dryrun", rid, "poller.out"), (W.t + 1, W.t + 1))
            grants.append({"id": rid, "regions": regions, "holds": sorted(holds), "lock": lock, "ended_before": rid in sb.ended,
                           "stop_released_before": sb.stop_released.get(rid, 0)})
        running = {}
        for p in glob.glob(os.path.join(sb.flags, "dryrun", "*", "RUNNING.json")):
            r = json.load(open(p))
            running[os.path.basename(os.path.dirname(p))] = {"pid_alive": _int(r.get("pid")) in W.alive,
                                                             "started": r.get("started") or r.get("at"),
                                                             "regions": r.get("regions")}
        snap = next((l for l in lines if l.startswith("SNAPSHOT")), "")
        mc = re.search(r"cands=(\d+) assigned=(\d+)", snap)
        mb = re.search(r"busy=(\S+)", snap)
        decisions.append({
            "i": i, "t": W.t, "error": err, "grants": grants,
            "open_before": open_before, "open_after": {rid: dict(s) for rid, s in sb.sim.items()},
            "kills": W.kills[kills0:], "fails_new": sorted(set(glob.glob(os.path.join(sb.flags, "dryrun", "*", "FAIL-*.json"))) - fails0),
            "running_json": running, "cands": int(mc.group(1)) if mc else None, "assigned": int(mc.group(2)) if mc else None,
            "snapshot_busy": mb.group(1) if mb else "",
            "lines": [l for l in lines if _kind(l) != "OTHER" or l.startswith(("SMOKE", "IDLE", "DRAIN", "GPU-CONTAMINATED", "WAIT"))][:400],
            "foreign": tick.get("foreign") or {},
        })
    with open(os.path.join(out_dir, "decisions.jsonl"), "w") as f:
        for d in decisions:
            f.write(json.dumps(d, sort_keys=True, default=list) + "\n")
    return header, ticks, decisions


# ------------------------------------------------------------------------------------------------ invariants
INVARIANTS = {
    "INV-NO-CRASH": "allocate() never raises and logs no ERROR line",
    "INV-STOP": "a STOPped row is never granted",
    "INV-REGRANT": "no id is granted again after its grant vanished without an .ended (the F4 loop)",
    "INV-1THREAD": "a row whose oracle threads <= 4 never holds all four quarters",
    "INV-EVIDENCE": "the declared shape never bypasses evidence: >= 2 quarters (GPU lane) / all 4 quarters only with "
                    "whole-host evidence (threads >= 48, baseline_ref, shape_override, measured_threads >= 48)",
    "INV-GPU-TIMING-Q3": "while a GPU-timing grant is open no timing row and no whole-q3 claim is granted on q3 cores",
    "INV-LOCKSET": "two open grants never have intersecting engine lock sets (a 'co-run' that would block in region-lock)",
    "INV-DRYRUN-DEADLINE": "no live RUNNING.json older than start + max(first_progress_s, 300) + 600 + 120 s",
    "INV-DEADPID-RELEASE": "a dry run whose pid is dead keeps none of its cpus held past one tick",
    "INV-IDLE-NAMED": f"no free region idle with pending candidates for >= {IDLE_N_TICKS} ticks without a named blocking rule",
    "INV-IDLE-WHY-ALL": "every whole-free region (q0..q3 and gpu-quiet) has an IDLE-WHY line while candidates are pending",
}


def _lock_of(c, g, holds):
    """(lock cores, exclusive quarters) the engine takes for grant g: its lock= list when the engine honours it, else the
    oracle's reading of the launcher claim, else the holds."""
    if g.get("lock"):
        lc = cpu_set(g["lock"])
        return lc, full_quarters({x for x in lc if x < 96})
    return c["lock_cores"] or _cpus_of(holds), c["lock_ex_quarters"]


def _rows_at(ticks, i):
    return ticks[i]["rows"]


def _holds_quarters(holds):
    return full_quarters(tokens_to_cores(holds)) | {h for h in holds if h in QUARTERS}


def check_invariants(ticks, decisions, only=None):
    """-> {inv: [violation strings]} for every invariant (empty list = pass)."""
    v = {k: [] for k in INVARIANTS}
    idle_run, dead_held = {}, {}
    for d in decisions:
        i, t = d["i"], d["t"]
        rows = _rows_at(ticks, i)
        stamp = _iso(t)
        if d["error"] or any(l.startswith("ERROR") for l in d["lines"]):
            v["INV-NO-CRASH"].append(f"{stamp} {d['error'] or next(l for l in d['lines'] if l.startswith('ERROR'))[:160]}")
        for g in d["grants"]:
            blob = rows.get(g["id"]) or {}
            c = contract_lite(blob)
            holds = set(g["holds"])
            hq = _holds_quarters(holds)
            if blob.get("stopped"):
                v["INV-STOP"].append(f"{stamp} {g['id']} granted while its STOP file exists")
            if g["stop_released_before"] and not g["ended_before"]:
                v["INV-REGRANT"].append(f"{stamp} {g['id']} re-granted ({g['stop_released_before']} prior grant(s) released without .ended)")
            if c["threads"] is not None and c["threads"] <= 4 and hq >= set(QUARTERS):
                v["INV-1THREAD"].append(f"{stamp} {g['id']} threads={c['threads']} holds whole host {','.join(sorted(holds))[:80]}")
            if not c["evidence"] and (hq >= set(QUARTERS) or (c["gpu_uses"] and len(hq - {"q3"}) >= 1)):
                v["INV-EVIDENCE"].append(f"{stamp} {g['id']} holds {','.join(sorted(hq))} without whole-host evidence "
                                         f"(declared shape={blob.get('manifest', {}).get('shape')!r}, threads={c['threads']})")
            # GPU-timing q3 quiet
            for oid, o in d["open_before"].items():
                ob = rows.get(oid) or {}
                oc = contract_lite(ob)
                if oc["gpu_uses"] and oc["timing"] and oid != g["id"]:
                    gq3 = tokens_to_cores(holds) & set(range(72, 96))
                    if gq3 and (c["timing"] or "q3" in hq):
                        v["INV-GPU-TIMING-Q3"].append(f"{stamp} {g['id']} (timing={c['timing']}) granted q3 cores beside GPU-timing {oid}")
                # lock sets: the new grant vs every grant open before it
                lc_new, xq_new = _lock_of(c, g, holds)
                lc_old, xq_old = _lock_of(oc, o, set(o["holds"]))
                ex_new = {x + k for q in xq_new for x in qcores(q) for k in (0, 96)}
                ex_old = {x + k for q in xq_old for x in qcores(q) for k in (0, 96)}
                clash = (lc_new & lc_old) | (ex_new & lc_old) | (ex_old & lc_new)
                if oid != g["id"] and clash:
                    v["INV-LOCKSET"].append(f"{stamp} {g['id']} lock set meets open {oid} on cores "
                                            f"{min(clash)}..{max(clash)} ({len(clash)})")
        # dry-run deadline / dead pid
        for rid, r in d["running_json"].items():
            blob = rows.get(rid) or {}
            st = _epoch(r.get("started")) or t
            fp = int((blob.get("manifest") or {}).get("first_progress_s") or 300)
            if r["pid_alive"] and t > st + max(fp, 300) + 600 + 120:
                v["INV-DRYRUN-DEADLINE"].append(f"{stamp} {rid} dry run alive {int((t - st) / 60)} min past start, not reaped")
        # dead-pid release: a dead dry run's cpus still in the candidate's SNAPSHOT busy list (not explained by a grant
        # or a foreign hold) on two consecutive ticks
        sbusy = _snapshot_busy_cores(d) - _busy_cores(d)
        for rid, r in d["running_json"].items():
            cs = {c if c < 96 else c - 96 for c in cpu_set(r.get("regions"))}
            key = f"dead:{rid}"
            if not r["pid_alive"] and cs and cs <= sbusy:
                dead_held[key] = dead_held.get(key, 0) + 1
                if dead_held[key] == 2:
                    v["INV-DEADPID-RELEASE"].append(f"{stamp} {rid} dry run pid dead, cpus {r.get('regions')} still held")
            else:
                dead_held.pop(key, None)
        # idle naming
        pending = (d["cands"] or 0) - (d["assigned"] or 0)
        why = {}
        for l in d["lines"]:
            m = re.match(r"IDLE-WHY (\S+): (.*)", l)
            if m:
                why[m.group(1)] = m.group(2)
        viol = [l for l in d["lines"] if l.startswith("IDLE-VIOLATION")]
        free_regions = _free_regions(d)
        unnamed = [r for r in free_regions if pending > 0 and (r not in why or re.search(r"(^|; )blocked$", why[r]))]
        if pending > 0:
            for r in unnamed:
                v["INV-IDLE-WHY-ALL"].append(f"{stamp} {r} free with {pending} pending candidate(s), no IDLE-WHY naming a rule")
        bad = pending > 0 and bool(unnamed)   # an IDLE-VIOLATION beside a NAMED IDLE-WHY is explained
        idle_run = {"n": idle_run.get("n", 0) + 1, "since": idle_run.get("since", stamp)} if bad else {}
        if idle_run.get("n") == IDLE_N_TICKS:
            v["INV-IDLE-NAMED"].append(f"{idle_run['since']} idle with candidates {IDLE_N_TICKS}+ ticks unexplained "
                                       f"(unnamed: {','.join(unnamed)}; {(viol or [''])[0][:100]})")
    # dedupe noisy lists (keep first 20 + count)
    for k in v:
        if len(v[k]) > 20:
            v[k] = v[k][:20] + [f"... +{len(v[k]) - 20} more"]
    return {k: x for k, x in v.items() if only is None or k in only}


def _busy_cores(d, after=True):
    cores = set()
    for s in (d["open_after"] if after else d["open_before"]).values():
        cores |= tokens_to_cores(set(s["holds"]))
    for r in d.get("foreign") or {}:
        if r in QUARTERS:
            cores |= qcores(r)
    for rid, r in d["running_json"].items():   # live dry runs hold cpus too (the candidate sees them through RUNNING.json)
        pass
    return cores


def _snapshot_busy_cores(d):
    out = set()
    for x in (d.get("snapshot_busy") or "").split(","):
        tok = x.split(":")[0]
        if tok and tok != "-":
            out |= tokens_to_cores({tok})
    return out


def _free_regions(d):
    busy = _busy_cores(d)
    out = [q for q in QUARTERS if not (qcores(q) & busy)]
    gpu_busy = any(GPU in s["holds"] for s in d["open_after"].values()) or GPU in (d.get("foreign") or {})
    if not gpu_busy:
        out.append(GPU)
    # what the candidate itself considered busy (dry runs, smokes) also removes a region from 'free'
    sb = d.get("snapshot_busy") or ""
    held = {x.split(":")[0] for x in sb.split(",") if x and x != "-"}
    return [r for r in out if r not in held]


def idle_metrics(decisions):
    """Idle quarter-hours and gpu-hours with candidates pending, integrated over the replay."""
    q_h = g_h = 0.0
    for a, b in zip(decisions, decisions[1:] + [None]):
        dt_s = min(TICK_CAP_S, (b["t"] - a["t"]) if b else 120)
        pending = (a["cands"] or 0) - (a["assigned"] or 0)
        if pending <= 0:
            continue
        busy = _busy_cores(a)
        q_h += (96 - len(busy)) / 24.0 * dt_s / 3600
        if GPU in _free_regions(a):
            g_h += dt_s / 3600
    return {"idle_quarter_hours": round(q_h, 2), "idle_gpu_hours": round(g_h, 2),
            "grants": sum(len(d["grants"]) for d in decisions),
            "rows_granted": len({g["id"] for d in decisions for g in d["grants"]}), "ticks": len(decisions)}


# ------------------------------------------------------------------------------------------------ candidates
def checkout_commit(repo, sha, dst):
    """Extract scripts/coordination/rowflow at <sha> into dst (git archive; read-only on the repo)."""
    os.makedirs(dst, exist_ok=True)
    tar = _real_subprocess.run(["git", "-C", repo, "archive", "--format=tar", sha, "scripts/coordination/rowflow"],
                               capture_output=True, check=True).stdout
    _real_subprocess.run(["tar", "-x", "-C", dst, "--strip-components=3"], input=tar, check=True)
    return dst
