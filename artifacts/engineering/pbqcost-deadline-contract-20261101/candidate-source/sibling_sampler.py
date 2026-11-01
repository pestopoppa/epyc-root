#!/usr/bin/env python3
"""Sample /proc/stat busy fraction of the SMT siblings (default CPUs 88-95 = siblings of 184-191) every 5 s; every 30 s of samples is one
window.  Writes out/sibling_load.csv (append) and, on SIGTERM/exit or every window, out/sibling_summary.json.  Read-only; no processes touched.
  python3 -B sibling_sampler.py OUTDIR [cpu-list]"""
import json, os, signal, statistics, sys, time
out, cpus = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "88-95")
ids = []
for part in cpus.split(","):
    a, _, b = part.partition("-")
    ids += list(range(int(a), int(b or a) + 1))
want = {f"cpu{i}" for i in ids}
def snap():
    d = {}
    for ln in open("/proc/stat"):
        f = ln.split()
        if f[0] in want:
            v = list(map(int, f[1:9]))
            d[f[0]] = (sum(v) - v[3] - v[4], sum(v))     # busy = total - idle - iowait
    return d
stop = False
def _t(*_):
    global stop
    stop = True
signal.signal(signal.SIGTERM, _t); signal.signal(signal.SIGINT, _t)
os.makedirs(out, exist_ok=True)
wins, cur, prev, t0 = [], [], snap(), time.time()
def write():
    if not wins:
        return
    m = statistics.median(wins)
    json.dump({"cpus": cpus, "windows": len(wins), "median_busy_frac": round(m, 4), "max_busy_frac": round(max(wins), 4),
               "frac_windows_gt_25pct": round(sum(w > 0.25 for w in wins) / len(wins), 4), "window_s": 30,
               "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(os.path.join(out, "sibling_summary.json.tmp"), "w"))
    os.replace(os.path.join(out, "sibling_summary.json.tmp"), os.path.join(out, "sibling_summary.json"))
with open(os.path.join(out, "sibling_load.csv"), "a") as fh:
    while not stop:
        time.sleep(5)
        now = snap()
        b = sum(now[k][0] - prev[k][0] for k in now); t = sum(now[k][1] - prev[k][1] for k in now)
        prev = now
        frac = b / t if t else 0.0
        fh.write(f"{time.time():.0f},{frac:.4f}\n"); fh.flush()
        cur.append(frac)
        if len(cur) >= 6:
            wins.append(statistics.fmean(cur)); cur = []; write()
write()
