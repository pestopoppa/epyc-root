#!/usr/bin/env python3
"""Does the GPU-resident set need more VRAM than its static sum says?

Two DIFFERENT questions, deliberately separated, because they have different
remedies:

  TRANSIENT PEAK -- how far above steady state does VRAM go while the residents
  are actually working? Per-image mmproj buffers on the vision model, per-chunk
  buffers in whisper/TTS, and the compute buffer scaling with batch are all real
  allocations that a static weights+KV sum does not contain. Remedy: reserve that
  much headroom.

  FRAGMENTATION -- does VRAM RATCHET across repeated identical cycles instead of
  returning to the same level? HIP's allocator does not compact, so repeated
  alloc/free of differently-sized buffers can leave unusable holes. Remedy: none
  available to us; it would cap the context we can safely declare.

A peak is not fragmentation. Reporting one as the other is how "we need headroom"
turns into a mechanism nobody measured -- which is exactly what this probe exists
to stop me doing again.

The verdict is a BAND, never a point: a 30-second sample of a workload that never
loaded an image proves nothing about image buffers, so the probe reports what it
actually exercised and refuses to imply coverage it does not have.

Read-only. Starts nothing, kills nothing. Run it against an already-serving
stack while driving real load through it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

KFD = Path("/sys/class/kfd/kfd/proc")
GIB = 1024 ** 3


def per_process_vram() -> dict[int, float]:
    """VRAM per KFD process, in GiB, from sysfs rather than a name pattern."""
    out: dict[int, float] = {}
    if not KFD.is_dir():
        return out
    for proc in KFD.iterdir():
        try:
            pid = int(proc.name)
        except ValueError:
            continue
        total = 0
        for node in proc.glob("vram_*"):
            try:
                total += int(node.read_text().strip())
            except (OSError, ValueError):
                continue
        if total:
            out[pid] = total / GIB
    return out


def exe_of(pid: int) -> str:
    try:
        return str(Path(f"/proc/{pid}/exe").resolve())
    except OSError:
        return "<gone>"


def sample() -> dict:
    procs = per_process_vram()
    return {
        "at": time.time(),
        "total_gib": round(sum(procs.values()), 4),
        "per_pid": {str(p): round(v, 4) for p, v in sorted(procs.items())},
        "pids": sorted(procs),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=120.0,
                    help="how long to sample (default 120)")
    ap.add_argument("--interval", type=float, default=0.5,
                    help="sample cadence in seconds (default 0.5)")
    ap.add_argument("--cycle-marks", type=str, default="",
                    help="comma-separated seconds-since-start at which a workload "
                         "CYCLE boundary occurs; the ratchet test compares the "
                         "trough after each cycle")
    ap.add_argument("--exercised", type=str, default="",
                    help="comma-separated names of what the concurrent workload "
                         "ACTUALLY exercised, e.g. 'text-long,vision-image,stt,tts'. "
                         "Recorded verbatim so the verdict cannot overclaim.")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    if not args.exercised.strip():
        print("REFUSED: --exercised is required. A headroom verdict that does not "
              "say what it exercised is unfalsifiable: a window that never loaded "
              "an image proves nothing about image buffers.", file=sys.stderr)
        return 2

    marks = [float(x) for x in args.cycle_marks.split(",") if x.strip()]
    started = time.time()
    samples: list[dict] = []
    while time.time() - started < args.seconds:
        samples.append(sample())
        time.sleep(args.interval)

    if not samples:
        print("REFUSED: no samples taken", file=sys.stderr)
        return 2

    totals = [s["total_gib"] for s in samples]
    baseline = min(totals)
    peak = max(totals)

    # Ratchet: the trough WITHIN each cycle window. If troughs climb, allocation
    # is not being returned -- that is the fragmentation signature.
    troughs: list[float] = []
    if marks:
        bounds = [0.0] + marks + [args.seconds]
        for lo, hi in zip(bounds, bounds[1:]):
            window = [s["total_gib"] for s in samples
                      if lo <= (s["at"] - started) < hi]
            if window:
                troughs.append(min(window))

    ratchet_gib = (troughs[-1] - troughs[0]) if len(troughs) >= 2 else None

    report = {
        "schema": "epyc.vram_headroom_probe.v1",
        "exercised": [x.strip() for x in args.exercised.split(",") if x.strip()],
        "samples": len(samples),
        "duration_s": round(time.time() - started, 2),
        "interval_s": args.interval,
        "steady_gib": round(baseline, 3),
        "peak_gib": round(peak, 3),
        "transient_headroom_gib": round(peak - baseline, 3),
        "cycle_troughs_gib": [round(t, 3) for t in troughs] or None,
        "ratchet_gib": round(ratchet_gib, 3) if ratchet_gib is not None else None,
        "fragmentation_verdict": (
            "NOT TESTED - no --cycle-marks given, so no repeated cycle to compare"
            if ratchet_gib is None else
            "NO RATCHET - VRAM returns to the same trough after each cycle"
            if ratchet_gib <= 0.05 else
            f"RATCHET {ratchet_gib:.3f} GiB across cycles - allocation is not being returned"),
        "resident_pids": {str(p): exe_of(p) for p in samples[-1]["pids"]},
        "caveat": ("transient_headroom_gib is a FLOOR on what to reserve, valid only "
                   "for the workload named in `exercised`. It is not a bound over "
                   "workloads this window did not run."),
        "series": [{"t": round(s["at"] - started, 2), "gib": s["total_gib"]} for s in samples],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"  exercised          : {', '.join(report['exercised'])}")
    print(f"  samples            : {report['samples']} over {report['duration_s']}s")
    print(f"  steady             : {report['steady_gib']} GiB")
    print(f"  peak               : {report['peak_gib']} GiB")
    print(f"  transient headroom : {report['transient_headroom_gib']} GiB  (floor, for this workload)")
    print(f"  fragmentation      : {report['fragmentation_verdict']}")
    print(f"  written            : {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
