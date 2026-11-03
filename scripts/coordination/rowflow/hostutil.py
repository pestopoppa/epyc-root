#!/usr/bin/env python3
"""hostutil.py - ONE measured-utilisation reading for every status surface (2026-11-03 session review item 2).

A grant file, a flock or a pid is not evidence that hardware is busy. Every surface that says "running" prints the
number this module measures instead: per-quarter CPU busy % over a short /proc/stat window and the MI210's busy % and
VRAM from sysfs (amdgpu `gpu_busy_percent`, `mem_info_vram_used/total`; read-only, no rocm-smi subprocess).

    python3 hostutil.py                 -> util q0=97% q1=3% q2=0% q3=0% gpu=100% vram=74%
    python3 hostutil.py --cpus 0-23     -> util q0=97% ... claim=96% gpu=...
    python3 hostutil.py --json          -> {"q0": 97.1, ..., "gpu": {"busy": 100, "vram_pct": 74.5, "vram_gib": 47.6}}

Quarter qN = cores 24N..24N+23 plus their SMT siblings 24N+96..24N+119 (the ws58 region map). IDLE_PCT is the
threshold every consumer uses for "held but idle".
"""
import argparse
import glob
import json
import os
import sys
import time

IDLE_PCT = 10.0          # a held region below this is IDLE-HELD / IDLE-GRANT
SAMPLE_S = 1.0           # default measurement window
QUARTERS = ("q0", "q1", "q2", "q3")
DRM_GLOB = "/sys/class/drm/card*/device"


def quarter_cpus(q):
    lo = int(q[1]) * 24
    return list(range(lo, lo + 24)) + list(range(lo + 96, lo + 120))


def parse_cpus(spec):
    """'0-23,96-119' -> [0..23, 96..119]."""
    out = []
    for t in str(spec).split(","):
        t = t.strip()
        if not t:
            continue
        if "-" in t:
            a, b = t.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(t))
    return out


def cpu_sample(path="/proc/stat"):
    """per-cpu (busy, total) jiffies."""
    out = {}
    try:
        for l in open(path):
            if l.startswith("cpu") and l[3].isdigit():
                f = l.split(); v = [int(x) for x in f[1:9]]
                out[int(f[0][3:])] = (sum(v) - v[3] - v[4], sum(v))
    except (OSError, ValueError, IndexError):
        pass
    return out


def busy_pct(s0, s1, cpus):
    """Busy % of `cpus` between two samples; None when the window is empty (no jiffies elapsed or cpus unknown)."""
    b = sum(s1.get(c, (0, 0))[0] - s0.get(c, (0, 0))[0] for c in cpus)
    t = sum(s1.get(c, (0, 0))[1] - s0.get(c, (0, 0))[1] for c in cpus)
    return round(100.0 * b / t, 1) if t > 0 else None


def gpu_sample(drm_glob=DRM_GLOB):
    """{"busy": int%, "vram_pct": float, "vram_gib": float, "card": name} from the first amdgpu card, or None."""
    for dev in sorted(glob.glob(drm_glob)):
        try:
            busy = int(open(os.path.join(dev, "gpu_busy_percent")).read().strip())
            used = int(open(os.path.join(dev, "mem_info_vram_used")).read().strip())
            total = int(open(os.path.join(dev, "mem_info_vram_total")).read().strip())
        except (OSError, ValueError):
            continue
        return {"busy": busy, "vram_pct": round(100.0 * used / total, 1) if total else None,
                "vram_gib": round(used / 2 ** 30, 1), "card": os.path.basename(os.path.dirname(dev))}
    return None


def from_samples(s0, s1, groups=None, gpu=None):
    """PURE: utilisation dict from two cpu samples (+ an optional gpu reading). groups: {name: [cpus]} beyond the quarters."""
    u = {q: busy_pct(s0, s1, quarter_cpus(q)) for q in QUARTERS}
    for name, cpus in (groups or {}).items():
        u[name] = busy_pct(s0, s1, cpus)
    u["gpu"] = gpu
    return u


def measure(sample_s=SAMPLE_S, groups=None, sleep=time.sleep):
    """Measured utilisation now: two /proc/stat samples `sample_s` apart + one sysfs GPU reading."""
    s0 = cpu_sample()
    sleep(sample_s)
    return from_samples(s0, cpu_sample(), groups, gpu_sample())


def pct(v):
    return "?" if v is None else f"{v:.0f}%"


def line(u, prefix="util"):
    """Fixed one-line form: util q0=97% q1=3% q2=0% q3=0% [name=..%] gpu=100% vram=74%."""
    parts = [f"{k}={pct(v)}" for k, v in u.items() if k != "gpu"]
    g = u.get("gpu")
    parts.append(f"gpu={pct(g['busy']) if g else '?'}")
    parts.append(f"vram={pct(g['vram_pct']) if g else '?'}")
    return f"{prefix} " + " ".join(parts)


def regions_pct(u, regions):
    """Utilisation of a set of region tokens: {'q1': 3.0, 'gpu-quiet': 100} (quarters -> cpu %, gpu-quiet -> gpu busy)."""
    out = {}
    for r in regions:
        if r in QUARTERS:
            out[r] = u.get(r)
        elif r.startswith("gpu") or r.startswith("mi210"):
            out[r] = (u.get("gpu") or {}).get("busy")
    return out


def idle_regions(u, regions, idle_pct=IDLE_PCT):
    """Region tokens of `regions` whose measured utilisation is below idle_pct (unknown readings never count as idle)."""
    return sorted(r for r, v in regions_pct(u, regions).items() if v is not None and v < idle_pct)


def main(argv=None):
    ap = argparse.ArgumentParser(description="measured per-quarter CPU% and GPU%/VRAM in one fixed line")
    ap.add_argument("--sample-s", type=float, default=SAMPLE_S)
    ap.add_argument("--cpus", help="an extra cpu list to report as claim=..% (e.g. 0-23,96-119)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    groups = {"claim": parse_cpus(a.cpus)} if a.cpus else None
    u = measure(a.sample_s, groups)
    print(json.dumps(u) if a.json else line(u))
    return 0


if __name__ == "__main__":
    sys.exit(main())
