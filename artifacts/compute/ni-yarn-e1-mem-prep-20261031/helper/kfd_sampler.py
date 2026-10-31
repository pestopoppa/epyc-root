#!/usr/bin/env python3
"""1 Hz KFD VRAM sampler for one server PID (read-only: /sys and /proc only).

    kfd_sampler.py --pid PID --out results/kfd_A1.jsonl [--interval 1.0]

Each line: {t, iso, pid_vram_gib, card_vram_gib, kfd_pids}. Exits by itself when PID is gone (or on
SIGTERM) and writes <out>.summary.json: own-PID peak, card peak, sample count, first/last time, and
the other KFD processes seen (a second GPU tenant during E1 invalidates timing and VRAM claims).
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path

KFD = Path("/sys/class/kfd/kfd/proc")
CARD = Path("/sys/class/drm/card2/device/mem_info_vram_used")   # the MI210
GIB = 1024 ** 3
STOP = False


def _stop(*_):
    global STOP
    STOP = True


def pid_vram(pid: int) -> int | None:
    d = KFD / str(pid)
    if not d.exists():
        return None
    tot = 0
    for f in d.glob("vram_*"):
        try:
            tot += int(f.read_text())
        except (OSError, ValueError):
            pass
    return tot


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=1.0)
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, _stop)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    peak = card_peak = 0
    n = 0
    others: set[int] = set()
    t0 = time.time()
    with open(out, "a") as fh:
        while not STOP and Path(f"/proc/{a.pid}").exists():
            pv = pid_vram(a.pid)
            try:
                cv = int(CARD.read_text())
            except (OSError, ValueError):
                cv = None
            pids = sorted(int(p.name) for p in KFD.iterdir() if p.name.isdigit()) if KFD.exists() else []
            others.update(p for p in pids if p != a.pid)
            rec = {"t": round(time.time(), 3), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "pid_vram_gib": round(pv / GIB, 3) if pv is not None else None,
                   "card_vram_gib": round(cv / GIB, 3) if cv is not None else None, "kfd_pids": pids}
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            n += 1
            peak = max(peak, pv or 0)
            card_peak = max(card_peak, cv or 0)
            time.sleep(a.interval)
    summ = {"pid": a.pid, "n_samples": n, "interval_s": a.interval, "started": t0, "ended": time.time(),
            "kfd_peak_gib": round(peak / GIB, 3), "card_peak_gib": round(card_peak / GIB, 3),
            "other_kfd_pids_seen": sorted(others), "sampler_pid": os.getpid()}
    Path(str(out) + ".summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps(summ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
