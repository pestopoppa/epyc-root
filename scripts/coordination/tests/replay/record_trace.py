#!/usr/bin/env python3
"""record_trace.py - write epyc.rowflow.trace.v1 traces (format: replay_lib.py). READ-ONLY toward the flags dir.

    record_trace.py live     --flags /mnt/raid0/llm/tmp/compute-flags --out T.jsonl [--every 120 --count 30] [--rl]
        one tick per sample of what `rowflow.py allocate` reads: ready/ manifests (+ launcher and job text), PASS/FAIL,
        STOP files, queued smokes, live dry runs (RUNNING.json + pid liveness via `ps`), open grants (observed),
        region-lock state (--rl runs `region-lock status`, read-only), measured util, MemAvailable, free disk, clock.
        Rows already done (.ended/.complete/.FILED) are omitted. Nothing is written under --flags.

    record_trace.py from-log --flags F --log F/ws58-calendar-keeper.log --day 2026-11-05 --step 120 --out T.jsonl.gz
        RECONSTRUCTS a day from the keeper log: one tick per SNAPSHOT (down-sampled to --step), the clock and measured
        util from the SNAPSHOT line, foreign region holds from its busy= list ('?' holders and holders that are not
        rows), and the row world from the files that survive: a manifest exists from published_at (withdrawn ones until
        their move), PASS from passed_at, FAIL records from their `at`, a STOP file from its mtime, and the row leaves
        the world at its .ended/.complete/.FILED mtime. Limits (coarse by construction): launcher text is today's,
        STOP files deleted before the capture are invisible, queued smokes and live dry runs are not reconstructed
        (those classes are covered by the scenario fixtures), sub-quarter foreign holds are dropped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from replay_lib import QUARTERS, GPU, TraceWriter  # noqa: E402

SCHEMA_ROW = "epyc.row.v3"


def _load(p):
    try:
        with open(p) as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def _ep(s):
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try:
            return dt.datetime.strptime(str(s), f).replace(tzinfo=dt.timezone.utc).timestamp()
        except (ValueError, TypeError):
            pass
    return None


def _mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return None


def _read(p, cap=1 << 20):
    try:
        with open(p, errors="replace") as f:
            return f.read(cap)
    except OSError:
        return None


def _sha(p):
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def stop_path(man, text):
    sf = str(man.get("stop_file") or "")
    if sf.startswith("/") and "$" not in sf:
        return sf
    m = re.search(r"--stop[ =]+(\"[^\"]*\"|'[^']*'|\S+)", re.sub(r"\\\n", " ", text or ""))
    sf = sf or (m.group(1).strip("\"'") if m else "")
    m2 = re.match(r"^\$(?:D|\{D\})(/.*)$", sf)
    if not m2:
        return sf if sf.startswith("/") else None
    defs = set(re.findall(r"^[ \t]*(?:export\s+)?D=(.*?)\s*(?:#.*)?$", text or "", re.M))
    if len(defs) != 1:
        return None
    v = defs.pop().strip("\"'")
    base = v if v.startswith("/") and "$" not in v else os.path.dirname(man["launcher"]["path"])
    return os.path.normpath(base + m2.group(1))


class RowSource:
    """Static facts of one row, read once; blob(t) picks what existed at t (None for live = everything)."""
    def __init__(self, flags, mpath):
        self.man = _load(mpath)
        self.ok = bool(self.man and self.man.get("schema") == SCHEMA_ROW and self.man.get("id"))
        if not self.ok:
            return
        rid = self.rid = self.man["id"]
        lp = (self.man.get("launcher") or {}).get("path") or ""
        self.text = _read(lp)
        self.ok = self.text is not None
        if not self.ok:
            return
        self.lsha = _sha(lp)
        self.files = {}
        for m in re.finditer(r"(/[^\s'\"`;|&()<>]+\.(?:sh|py))", self.text):
            p = m.group(1)
            if p != lp and "filler_run" not in p and len(self.files) < 6:
                t = _read(p)
                if t is not None:
                    self.files[p] = t
        dd = os.path.join(flags, "dryrun", rid)
        self.pass_ = _load(os.path.join(dd, "PASS.json"))
        self.fails = [f for f in (_load(p) for p in sorted(glob.glob(os.path.join(dd, "FAIL-*.json")))) if f]
        self.stop = stop_path(self.man, self.text)
        self.stop_mt = _mtime(self.stop) if self.stop else None
        g = os.path.join(flags, "grants", rid)
        ends = [x for x in (_mtime(g + ".ended"), _mtime(g + ".complete"), _mtime(os.path.join(flags, "filing-done", rid + ".FILED"))) if x]
        self.ended_at = min(ends) if ends else None
        self.published = _ep(self.man.get("published_at")) or _mtime(mpath)
        self.dd = dd
        self.cache = {}

    def blob(self, t=None, live=False):
        p = self.pass_ if (self.pass_ and (t is None or (_ep(self.pass_.get("passed_at")) or 0) <= t)) else None
        fails = [dict(f, _matches=f.get("launcher_sha256") == self.lsha) for f in self.fails
                 if t is None or (_ep(f.get("at")) or 0) <= t]
        stopped = bool(self.stop_mt and (t is None or self.stop_mt <= t))
        key = (bool(p), len(fails), stopped)
        if not live and key in self.cache:
            return self.cache[key]
        b = {"manifest": self.man, "launcher_text": self.text, "files": self.files, "pass": p,
             "pass_matches": bool(p) and p.get("launcher_sha256") == self.lsha, "fails": fails, "stopped": stopped,
             "smoke_queued": None, "running": None, "running_alive": False, "dry_grant": None}
        if live:
            b["smoke_queued"] = _load(os.path.join(self.dd, "SMOKE-QUEUED.json"))
            run = _load(os.path.join(self.dd, "RUNNING.json"))
            if run:
                b["running"] = run
                b["running_alive"] = _pid_alive(run.get("pid"))
                gs = sorted(glob.glob(os.path.join(self.dd, "grants", "*.grant")))
                b["dry_grant"] = _read(gs[-1]) if gs else None
        else:
            self.cache[key] = b
        return b


def _pid_alive(pid):
    try:
        return subprocess.run(["ps", "-o", "pid=", "-p", str(int(pid))], capture_output=True).returncode == 0
    except (TypeError, ValueError):
        return False


def sources(flags, withdrawn=True):
    out = {}
    paths = glob.glob(os.path.join(flags, "ready", "*.json"))
    if withdrawn:
        paths += glob.glob(os.path.join(flags, "ready", ".withdrawn", "*.json"))
    for p in sorted(paths):
        s = RowSource(flags, p)
        if s.ok:
            s.withdrawn_at = _mtime(p) if "/.withdrawn/" in p else None
            out.setdefault(s.rid, s)
    return out


def _util_line(s):
    u = {q: None for q in QUARTERS}
    for k, v in re.findall(r"\b(q[0-3]|gpu|vram)=(\d+)%", s):
        u[k] = float(v)
    g = {"busy": u.pop("gpu", None), "vram_pct": u.pop("vram", None), "vram_gib": None}
    u["gpu"] = g if g["busy"] is not None else None
    return u


def _meminfo():
    try:
        for l in open("/proc/meminfo"):
            if l.startswith("MemAvailable:"):
                return int(l.split()[1]) / 1048576
    except OSError:
        pass
    return None


# ----------------------------------------------------------------------------------------------------- live
def record_live(flags, out, every=0, count=1, rl=False):
    w = TraceWriter(out, f"live {flags}")
    for n in range(count):
        src = sources(flags, withdrawn=False)
        rows = {}
        for rid, s in src.items():
            if s.ended_at:
                continue
            rows[rid] = s.blob(live=True)
        foreign = {}
        if rl:
            rlbin = os.environ.get("ROWFLOW_RL", "/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock")
            try:
                st = subprocess.run([rlbin, "status"], capture_output=True, text=True, timeout=15).stdout
            except (OSError, subprocess.TimeoutExpired):
                st = ""
            for l in st.splitlines():
                b = l.split()
                if len(b) > 1 and b[0] in QUARTERS + (GPU,) and b[1] != "free":
                    tag = b[-1] if len(b) > 2 else "?"
                    if not (tag.startswith("filler-") and tag[7:] in src):
                        foreign[b[0]] = tag
        try:
            sys.path.insert(0, os.path.join(flags, "bin", "rowflow"))
            import hostutil
            util = hostutil.measure(1.0)
        except Exception:  # noqa: BLE001
            util = None
        st = os.statvfs(flags)
        grants = sorted(os.path.basename(g)[:-6] for g in glob.glob(os.path.join(flags, "grants", "*.grant")))
        w.tick(time.time(), rows, foreign=foreign, util=util, mem_gib=_meminfo(), disk_free_gib=st.f_bavail * st.f_frsize / 2 ** 30,
               observed={"open_grants": grants})
        if n + 1 < count:
            time.sleep(every)
    w.close()


# ----------------------------------------------------------------------------------------------------- from log
_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (\S+) ?(.*)$")


def record_from_log(flags, log, day, out, step=120, until=None):
    src = sources(flags)
    t_lo = _ep(day + "T00:00:00Z"); t_hi = t_lo + 86400
    snaps, grants = [], []
    with open(log, errors="replace") as f:
        for line in f:
            if not line.startswith(day):
                continue
            m = _TS.match(line.rstrip("\n"))
            if not m:
                continue
            t, kind, rest = _ep(m.group(1)), m.group(2), m.group(3)
            if kind == "SNAPSHOT":
                snaps.append((t, rest))
            elif kind == "GRANT":
                grants.append((t, rest.split(" ", 1)[0]))
    picked, last = [], -1e18
    for t, rest in snaps:
        if until and t > until:
            break
        if t - last >= step:
            picked.append((t, rest)); last = t
    w = TraceWriter(out, f"from-log {log} day={day} step={step}",
                    notes="reconstructed: coarse (see record_trace.py docstring)")
    gi = 0
    for k, (t, rest) in enumerate(picked):
        rows = {}
        for rid, s in src.items():
            if s.published and s.published > t:
                continue
            if s.ended_at and s.ended_at <= t:
                continue
            if s.withdrawn_at and s.withdrawn_at <= t:
                continue
            if s.ended_at and s.ended_at < t_lo:
                continue
            rows[rid] = s.blob(t)
        foreign = {}
        mb = re.search(r"busy=(\S+)", rest)
        for tok in (mb.group(1).split(",") if mb else []):
            if ":" not in tok:
                continue
            reg, holder = tok.split(":", 1)
            if reg in QUARTERS + (GPU,) and (holder == "?" or holder not in src):
                foreign[reg] = holder or "?"
        nxt = picked[k + 1][0] if k + 1 < len(picked) else t_hi
        obs = []
        while gi < len(grants) and grants[gi][0] < nxt:
            if grants[gi][0] >= t:
                obs.append(grants[gi][1])
            gi += 1
        mc = re.search(r"cands=(\d+) assigned=(\d+)", rest)
        w.tick(t, rows, foreign=foreign, util=_util_line(rest), mem_gib=900.0, disk_free_gib=400.0,
               observed={"grants": obs, "cands": int(mc.group(1)) if mc else None})
    w.close()
    return len(picked)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    a1 = sp.add_parser("live"); a1.add_argument("--flags", required=True); a1.add_argument("--out", required=True)
    a1.add_argument("--every", type=float, default=120); a1.add_argument("--count", type=int, default=1); a1.add_argument("--rl", action="store_true")
    a2 = sp.add_parser("from-log"); a2.add_argument("--flags", required=True); a2.add_argument("--log", required=True)
    a2.add_argument("--day", required=True); a2.add_argument("--out", required=True); a2.add_argument("--step", type=float, default=120)
    a2.add_argument("--until")
    a = ap.parse_args(argv)
    if a.cmd == "live":
        record_live(a.flags, a.out, a.every, a.count, a.rl)
    else:
        n = record_from_log(a.flags, a.log, a.day, a.out, a.step, _ep(a.until) if a.until else None)
        print(f"{n} ticks -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
