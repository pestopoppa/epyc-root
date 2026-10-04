#!/usr/bin/env python3
"""gpu-slot-ak-20261004 copy of /mnt/raid0/llm/tmp/x0-27b-quants/p3_claim_v2.py (results dir is a flag, campaign
GPU-SLOT-AK-20261004, holder gpu-slot-ak; ONE claim held across the whole slot so nothing can take the MI210
between arms). Takes NO CPU region lock (a CPU AutoKernel measurement may be running; the device claim is the
only lock this slot needs). P3v2 copy of p3_claim.py (results/p3v2, campaign id). P3 copy of x0_claim.py (paths/campaign changed only). Hold the MI210 device claim (`mi210_0`, autokernel.resource.device_claim) around one command.

Single non-blocking attempt (timeout_s=0): if anyone holds the claim, refuse (exit 75) instead of
waiting or stealing. The command runs as our own child; the claim is released when it exits.
Journal + receipt go to results/claim/.

Usage: slot_claim.py --results-dir DIR --purpose TEXT [--max-hold-s S] -- cmd args...
"""
from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "/workspace/repos/epyc-inference-research/scripts/kernel_rnd")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--purpose", required=True)
    ap.add_argument("--max-hold-s", type=float, default=6600)
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        ap.error("no command")
    from autokernel.resource import device_claim  # noqa: E402
    out = a.results_dir / "claim"
    out.mkdir(parents=True, exist_ok=True)
    journal = device_claim.ClaimJournal(out / "device-claim-journal.jsonl")
    try:
        cm = device_claim.acquire_device_claim(
            "mi210_0", purpose=a.purpose, campaign_id="GPU-SLOT-AK-20261004", journal=journal,
            holder_label="gpu-slot-ak", timeout_s=0, max_hold_s=a.max_hold_s)
    except device_claim.DeviceClaimError as exc:
        print(f"[slot-claim] REFUSED: mi210_0 claim not acquired: {type(exc).__name__}: {exc}", flush=True)
        return 75
    with cm as claim:
        (out / "device-claim-receipt.json").write_text(json.dumps(claim.receipt().to_dict(), indent=2) + "\n")
        print(f"[slot-claim] holding mi210_0 for: {a.purpose}", flush=True)
        p = subprocess.Popen(cmd)
        # forward TERM/INT to our own child (the inner runner), which tears down its own servers
        signal.signal(signal.SIGTERM, lambda *_: p.send_signal(signal.SIGTERM))
        signal.signal(signal.SIGINT, lambda *_: p.send_signal(signal.SIGTERM))
        try:
            while True:
                try:
                    return p.wait()
                except InterruptedError:
                    continue
        except BaseException:
            p.terminate()
            try:
                p.wait(timeout=300)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
            raise


if __name__ == "__main__":
    raise SystemExit(main())
