#!/usr/bin/env python3
"""idle_alarm.py -- zero-token idle-compute alarm that wakes the AGENT, not the operator (steering report item 3).

Replaces the ad-hoc churn_alarm4.sh watcher. Reads the calendar keeper's log (SNAPSHOT + IDLE-WHY lines) and
queue_status --json, and raises `idle-with-backlog` when a CPU quarter (q0..q3) or the GPU (gpu-quiet) has been free
for more than --idle-s seconds (default 300) across consecutive keeper snapshots while READY rows that could use it
exist. The alarm reason is the keeper's own IDLE-WHY line for that region, copied verbatim.

Also alarms (as the old watcher did): keeper-stale (newest SNAPSHOT older than --stale-s, default 360 s) and
keeper-traceback (a Traceback in the log tail since the last check, --watch only).

Suppressed (known, intended causes -- never an alarm):
  * DISK-PAUSE or an operator HOLD-ADMISSIONS file (rowflow diskpause.admission_gate: no new grants by design);
  * quiet-guard regions: quarters a RUNNING row booked on purpose and keeps idle (ready/<id>.json quiet_guard_regions);
  * a GPU smoke gap shorter than one keeper tick (the GPU's IDLE-WHY names a smoke and the free streak < 2 ticks);
  * "free" in the keeper's list but measurably busy (snapshot util >= 20 %, or a RUNNING grant covers the region).

    idle_alarm.py [--flags DIR] [--json]          one evaluation; exit 0 = no alarm, 3 = alarm (flag written)
    idle_alarm.py --watch [--interval 120]        loop; exits 3 on the FIRST alarm (run with run_in_background)

Flag file: <flags>/idle-with-backlog.flag (JSON), rewritten on every alarm and retired when a one-shot evaluation
finds no alarm (renamed to idle-with-backlog.flag.cleared: never deleted). Zero LLM, stdlib only, reads everything, writes only that flag.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

DEFAULT_FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
KEEPER_LOG = "ws58-calendar-keeper.log"
FLAG_NAME = "idle-with-backlog.flag"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUEUE_STATUS = os.path.join(ROOT, ".claude/skills/inference-backlog-scheduling/scripts/queue_status.py")
REGIONS = ("q0", "q1", "q2", "q3", "gpu-quiet")
BUSY_UTIL_PCT = 20.0
LOG_TAIL_BYTES = 600_000
TS_RE = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) ")
ALARM, NO_ALARM = 3, 0


def _ts(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def parse_log(text: str) -> tuple[list[dict], dict[str, tuple[float, str]], list[str]]:
    """-> (snapshots oldest-first, latest IDLE-WHY per region {region: (ts, line)}, traceback lines)."""
    snaps, why, tb = [], {}, []
    for ln in text.splitlines():
        m = TS_RE.match(ln)
        if "Traceback" in ln:
            tb.append(ln)
        if not m:
            continue
        t = _ts(m.group(1))
        body = ln[m.end():]
        if body.startswith("SNAPSHOT "):
            kv = {}
            for tok in body.split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    kv.setdefault(k, v)   # first occurrence wins (util q0=.. comes after; parsed below)
            util = {k: float(v.rstrip("%")) for k, v in re.findall(r"\b(q[0-3]|gpu)=(\d+(?:\.\d+)?)%", body)}
            snaps.append({"t": t, "free": set(filter(None, kv.get("free", "").split(","))),
                          "busy": [b for b in kv.get("busy", "").split(",") if b],
                          "cands": int(kv.get("cands", "0") or 0), "util": util})
        elif body.startswith("IDLE-WHY "):
            r = body[len("IDLE-WHY "):].split(":", 1)[0].strip()
            why[r] = (t, ln)
    return snaps, why, tb


def _util_key(region: str) -> str:
    return "gpu" if region == "gpu-quiet" else region


def free_streak(snaps: list[dict], region: str) -> float:
    """Seconds the region has been continuously free-and-idle, newest snapshot backwards (0 when busy now)."""
    first = None
    for s in reversed(snaps):
        idle = region in s["free"] and s["util"].get(_util_key(region), 0.0) < BUSY_UTIL_PCT \
            and not any(b.startswith(region + ":") for b in s["busy"])
        if not idle:
            break
        first = s["t"]
    return 0.0 if first is None else snaps[-1]["t"] - first


def tick_s(snaps: list[dict]) -> float:
    s = snaps[-12:]
    gaps = sorted(b["t"] - a["t"] for a, b in zip(s, s[1:]) if b["t"] > a["t"])
    return gaps[len(gaps) // 2] if gaps else 150.0


def _covers(regions: str, region: str) -> bool:
    """Does a RUNNING grant's region string cover this region? (cpu ranges for quarters, mi210 for the GPU)."""
    regions = str(regions or "")
    if region == "gpu-quiet":
        return "mi210" in regions or "gpu" in regions
    q = int(region[1])
    lo, hi = q * 24, q * 24 + 23
    if region in regions.split(","):
        return True
    for a, b in re.findall(r"\b(\d+)-(\d+)\b", regions):
        if int(a) <= hi and int(b) >= lo and int(a) < 96:
            return True
    return False


def ready_for(region: str, grantable: list[dict]) -> list[dict]:
    out = []
    for r in grantable:
        shape = str(r.get("shape") or "")
        gpu = "gpu" in shape
        if (region == "gpu-quiet" and (gpu or shape == "quiet-host")) or (region != "gpu-quiet" and not gpu):
            out.append(r)
    return out


def evaluate(snaps, why, qjson, *, guards=(), admission=None, now=None, idle_s=300.0, stale_s=360.0) -> dict:
    """Pure decision. -> {"alarm": bool, "alarms": [...], "suppressed": [...]}"""
    now = time.time() if now is None else now
    res = {"alarm": False, "alarms": [], "suppressed": []}
    if not snaps:
        res["alarms"].append({"kind": "keeper-stale", "region": None, "reason": "no SNAPSHOT line in the keeper log"})
        res["alarm"] = True
        return res
    age = now - snaps[-1]["t"]
    if age > stale_s:
        res["alarms"].append({"kind": "keeper-stale", "region": None,
                              "reason": f"newest keeper SNAPSHOT is {age:.0f}s old (> {stale_s:.0f}s)"})
    buckets = (qjson or {}).get("buckets") or {}
    grantable = buckets.get("GRANTABLE") or []
    running = buckets.get("RUNNING") or []
    tk = tick_s(snaps)
    for r in REGIONS:
        st = free_streak(snaps, r)
        if st <= idle_s:
            continue
        cands = ready_for(r, grantable)
        if not cands:
            continue
        line = (why.get(r) or (0, f"(no IDLE-WHY line logged for {r})"))[1]
        base = {"region": r, "free_s": round(st), "ready": [c.get("id") for c in cands[:5]], "ready_n": len(cands),
                "reason": line}
        if admission:
            res["suppressed"].append(dict(base, cause=admission))
        elif r in guards:
            res["suppressed"].append(dict(base, cause="quiet-guard region of a RUNNING row"))
        elif any(_covers(x.get("regions"), r) for x in running):
            res["suppressed"].append(dict(base, cause="a RUNNING grant covers it (keeper free list lags)"))
        elif r == "gpu-quiet" and "smoke" in line.lower() and st < 2 * tk:
            res["suppressed"].append(dict(base, cause=f"GPU smoke gap < one tick ({tk:.0f}s)"))
        else:
            res["alarms"].append(dict(base, kind="idle-with-backlog"))
    res["alarm"] = bool(res["alarms"])
    return res


# ---------------------------------------------------------------- live inputs
def read_log(flags: str) -> str:
    p = os.path.join(flags, KEEPER_LOG)
    try:
        with open(p, "rb") as fh:
            fh.seek(0, 2)
            n = fh.tell()
            fh.seek(max(0, n - LOG_TAIL_BYTES))
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return ""


def queue_json(flags: str) -> dict:
    try:
        p = subprocess.run([sys.executable, QUEUE_STATUS, "--flags", flags, "--json"], capture_output=True,
                           text=True, timeout=90)
        return json.loads(p.stdout[p.stdout.index("{"):])
    except (subprocess.SubprocessError, ValueError, OSError):
        return {}


def quiet_guards(flags: str, qjson: dict) -> set[str]:
    g = set()
    for x in ((qjson.get("buckets") or {}).get("RUNNING") or []):
        try:
            m = json.load(open(os.path.join(flags, "ready", f"{x.get('id')}.json")))
        except (OSError, ValueError):
            continue
        g.update(m.get("quiet_guard_regions") or [])
        g.update(x.get("guard") or [])
    return g


def admission_reason(flags: str) -> str | None:
    d = os.path.join(flags, "bin", "rowflow")
    try:
        if d not in sys.path:
            sys.path.insert(0, d)
        import diskpause  # type: ignore
        return diskpause.admission_gate(flags, log=lambda *a, **k: None, persist=False)
    except Exception:   # noqa: BLE001 - fall back to the two files the gate reads
        if os.path.exists(os.path.join(flags, "HOLD-ADMISSIONS")):
            return "HOLD-ADMISSIONS present"
        return None


def run_once(flags: str, idle_s: float, stale_s: float) -> dict:
    snaps, why, _ = parse_log(read_log(flags))
    q = queue_json(flags)
    return evaluate(snaps, why, q, guards=quiet_guards(flags, q), admission=admission_reason(flags),
                    idle_s=idle_s, stale_s=stale_s)


def write_flag(flags: str, res: dict) -> str:
    p = os.path.join(flags, FLAG_NAME)
    doc = dict(res, schema="epyc.idle_alarm.v1", at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    tmp = p + f".tmp{os.getpid()}"
    with open(tmp, "w") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    os.replace(tmp, p)
    return p


def render(res: dict) -> str:
    out = []
    for a in res["alarms"]:
        if a["kind"] == "idle-with-backlog":
            out.append(f"ALARM idle-with-backlog {a['region']} free {a['free_s']}s, {a['ready_n']} READY "
                       f"({', '.join(a['ready'])})\n  {a['reason'][:400]}")
        else:
            out.append(f"ALARM {a['kind']}: {a['reason'][:400]}")
    for s in res["suppressed"]:
        out.append(f"suppressed {s['region']} free {s['free_s']}s: {s['cause']}")
    return "\n".join(out) or "OK no idle-with-backlog"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--idle-s", type=float, default=300.0)
    ap.add_argument("--stale-s", type=float, default=360.0)
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=float, default=120.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.watch:
        res = run_once(a.flags, a.idle_s, a.stale_s)
        if res["alarm"]:
            write_flag(a.flags, res)
        elif os.path.exists(os.path.join(a.flags, FLAG_NAME)):
            os.replace(os.path.join(a.flags, FLAG_NAME), os.path.join(a.flags, FLAG_NAME + ".cleared"))
        print(json.dumps(res, indent=1) if a.json else render(res))
        return ALARM if res["alarm"] else NO_ALARM
    lp = os.path.join(a.flags, KEEPER_LOG)
    size = lambda: os.path.getsize(lp) if os.path.exists(lp) else 0  # noqa: E731
    seen = size()
    while True:
        time.sleep(a.interval)
        n = size()
        tail = ""
        if n != seen:
            with open(lp, "rb") as fh:
                fh.seek(seen if n > seen else 0)   # rotated/truncated -> read from the start
                tail = fh.read(LOG_TAIL_BYTES).decode("utf-8", "replace")
        seen = n
        tb = [ln for ln in tail.splitlines() if "Traceback" in ln]
        if tb:
            res = {"alarm": True, "alarms": [{"kind": "keeper-traceback", "region": None, "reason": tb[0]}],
                   "suppressed": []}
        else:
            res = run_once(a.flags, a.idle_s, a.stale_s)
        if res["alarm"]:
            write_flag(a.flags, res)
            print(json.dumps(res, indent=1) if a.json else render(res))
            return ALARM


if __name__ == "__main__":
    sys.exit(main())
