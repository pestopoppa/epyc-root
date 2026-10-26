#!/usr/bin/env python3
"""M4.2b NON-GATING window diagnostics (read-only sysfs/procfs; never signals anything; exits when --parent dies).

Every --period s appends one JSON line to --out: busy % of the SMT-sibling cores 88-95 and of the job's host threads 184-191
(from /proc/stat deltas), MI210 gpu_busy_percent, card VRAM used, current sclk/mclk, edge/junction/mem temperature, power.
Purpose: if a load goes INVALID on C-solo drift (as M4.2a did, 282 -> 885 ms), say what drifted. Never part of the verdict.
"""
import argparse, json, os, time
from pathlib import Path


def cpu_times(cpus):
    out = {}
    for ln in Path("/proc/stat").read_text().splitlines():
        if ln.startswith("cpu") and ln[3:4].isdigit():
            f = ln.split()
            n = int(f[0][3:])
            if n in cpus:
                v = list(map(int, f[1:]))
                out[n] = (sum(v), v[3] + v[4])     # total, idle + iowait
    return out


def busy(a, b):
    res = {}
    for n in a:
        if n in b:
            dt, di = b[n][0] - a[n][0], b[n][1] - a[n][1]
            res[n] = round(100.0 * (dt - di) / dt, 1) if dt > 0 else None
    return res


def rd(p):
    try:
        return Path(p).read_text().strip()
    except OSError:
        return None


def cur_level(p):
    t = rd(p) or ""
    for ln in t.splitlines():
        if ln.rstrip().endswith("*"):
            return ln.split(":", 1)[1].strip(" *")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--parent", type=int, required=True)
    ap.add_argument("--period", type=float, default=10.0)
    ap.add_argument("--card", default="/sys/class/drm/card2/device")
    a = ap.parse_args()
    sib, own = set(range(88, 96)), set(range(184, 192))
    hw = next(iter(sorted(Path(a.card, "hwmon").glob("hwmon*"))), None)
    prev = cpu_times(sib | own)
    while True:
        time.sleep(a.period)
        try:
            os.kill(a.parent, 0)
        except OSError:
            return 0
        cur = cpu_times(sib | own)
        b = busy(prev, cur)
        prev = cur
        s = [b[n] for n in sorted(sib) if b.get(n) is not None]
        o = [b[n] for n in sorted(own) if b.get(n) is not None]
        rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "sib_88_95_busy_mean": round(sum(s) / len(s), 1) if s else None, "sib_88_95_busy_max": max(s) if s else None,
               "own_184_191_busy_mean": round(sum(o) / len(o), 1) if o else None,
               "gpu_busy_pct": rd(f"{a.card}/gpu_busy_percent"),
               "vram_used_gib": (round(int(rd(f"{a.card}/mem_info_vram_used")) / 2**30, 2) if rd(f"{a.card}/mem_info_vram_used") else None),
               "sclk": cur_level(f"{a.card}/pp_dpm_sclk"), "mclk": cur_level(f"{a.card}/pp_dpm_mclk"),
               "kfd_pids": sorted(os.listdir("/sys/class/kfd/kfd/proc")) if os.path.isdir("/sys/class/kfd/kfd/proc") else None}
        if hw:
            for i, lab in ((1, "edge"), (2, "junction"), (3, "mem")):
                v = rd(hw / f"temp{i}_input")
                rec[f"temp_{lab}_c"] = int(v) / 1000 if v else None
            pw = rd(hw / "power1_average")
            rec["power_w"] = int(pw) / 1e6 if pw else None
        with open(a.out, "a") as f:
            f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
