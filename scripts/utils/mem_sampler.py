#!/usr/bin/env python3
"""Memory telemetry sampler (NIB2-97a).

Every INTERVAL seconds append one JSON line with MemAvailable/AnonPages/Cached/
Mlocked (kB) and /proc/pressure/memory PSI to a size-rotated log, so the next
OOM leaves a time series on disk (INC-20261021-earlyoom-session-kills had none).

    mem_sampler.py            # loop forever (30 s)
    mem_sampler.py --once     # one sample, then exit

Env: MEM_SAMPLER_LOG (default <repo>/logs/mem_telemetry.jsonl),
MEM_SAMPLER_INTERVAL, MEM_SAMPLER_MAX_BYTES (default 8 MiB), MEM_SAMPLER_KEEP (default 4).
Starting it (cron/launcher) is a host action; this file only defines the sampler.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

FIELDS = ("MemAvailable", "AnonPages", "Cached", "Mlocked")
DEFAULT_LOG = Path(__file__).resolve().parents[2] / "logs" / "mem_telemetry.jsonl"


def read_meminfo(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        k, _, rest = line.partition(":")
        if k in FIELDS:
            parts = rest.split()
            if parts and parts[0].isdigit():
                out[k + "_kB"] = int(parts[0])
    return out


def read_psi(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        kv = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        for key in ("avg10", "avg60", "avg300"):
            if key in kv:
                try:
                    out[f"psi_{parts[0]}_{key}"] = float(kv[key])
                except ValueError:
                    pass
    return out


def sample(meminfo="/proc/meminfo", psi="/proc/pressure/memory", now=None) -> dict:
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now if now is not None else time.time()))}
    for path, fn in ((meminfo, read_meminfo), (psi, read_psi)):
        try:
            rec.update(fn(Path(path).read_text()))
        except OSError as e:  # missing PSI is recorded, never fabricated as zero
            rec.setdefault("missing", []).append(f"{Path(path).name}:{e.errno}")
    return rec


def rotate(log: Path, max_bytes: int, keep: int) -> None:
    try:
        if log.stat().st_size < max_bytes:
            return
    except FileNotFoundError:
        return
    for i in range(keep, 0, -1):
        src = log if i == 1 else Path(f"{log}.{i - 1}")
        dst = Path(f"{log}.{i}")
        if src.exists():
            os.replace(src, dst)


def append(log: Path, rec: dict, max_bytes: int, keep: int) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    rotate(log, max_bytes, keep)
    with open(log, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args(argv)
    log = Path(os.environ.get("MEM_SAMPLER_LOG", DEFAULT_LOG))
    interval = float(os.environ.get("MEM_SAMPLER_INTERVAL", "30"))
    mx = int(os.environ.get("MEM_SAMPLER_MAX_BYTES", str(8 << 20)))
    keep = int(os.environ.get("MEM_SAMPLER_KEEP", "4"))
    while True:
        append(log, sample(), mx, keep)
        if a.once:
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
