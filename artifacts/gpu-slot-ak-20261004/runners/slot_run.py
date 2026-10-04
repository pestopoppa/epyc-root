#!/usr/bin/env python3
"""gpu-slot-ak-20261004 sequencer: runs the arms in VALUE order inside a GPU-minute budget.

Order (value first) and caps — each item starts only if its estimate fits the remaining budget:
  1 kvu_on_b2048   KVU-16b replay, skip ON  (19a+19b defaults), -b 2048 -ub 2048   replay cap 20 min, est ~18 min
  2 kvu_off_b2048  KVU-16b replay, skip OFF (MASK_SKIP=0 SEQ_ROWS=0), -b 2048        replay cap 20 min, est ~24 min (cap-bound)
  3 kvu_on_b512    KVU-16b replay, skip ON, -b 512 -ub 512                           replay cap 20 min, est ~20 min
  4 p3 pairs       P3v2 A1, skip ON then OFF (AB); a second AB pair (=> ABAB) only if it still fits
                   est ~15 + ~16.5 min per pair; a pair starts only if BOTH arms fit (an unpaired arm is useless)
KVU items 1-2 are the must-run comparison: their replay cap shrinks to the remaining budget (minimum useful
replay 8 min, else skipped). Overhead per KVU arm ~4 min (load ~1, coherence, tokenize, graceful teardown with
the -lv 4 memory breakdown). Budget default 90 min from the moment the device claim is held.

Every arm is a child process of this sequencer (own session); each arm driver owns exactly one llama-server.
On timeout/TERM the arm driver gets SIGTERM and 420 s to tear its server down; if it must be SIGKILLed, the
server pid it recorded (<arm>/server.pid) is reaped only if that pid is still a llama-server on OUR scratch port
started from OUR bin dir. Nothing is signalled by name. No CPU region lock is taken.

Usage: slot_run.py --results DIR [--port 18183] [--budget-min 90] [--order kvu_on_b2048,kvu_off_b2048,kvu_on_b512,p3]
                   [--kvu-cap-min 20] [--p3-pairs 2] [--p3-phase a1] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_common as C  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)

PY = [sys.executable, "-B"]
KVU = {  # label: (skip, b, ub, estimate_min_at_full_cap)
    "kvu_on_b2048": ("on", 2048, 2048, 18.0),
    "kvu_off_b2048": ("off", 2048, 2048, 24.0),
    "kvu_on_b512": ("on", 512, 512, 20.0),
    "kvu_off_b512": ("off", 512, 512, 22.0),
}
KVU_OVERHEAD_MIN = 4.0
KVU_MIN_REPLAY_MIN = 8.0
P3_EST = {"on": 15.0, "off": 16.5}  # A1 only: v1 A1 took 20.4 min incl. L1/L2 (~5.5 min) -> v2 A1 ~15; OFF slower at L3
P3_HARD_MIN = {"a1": 25.0, "all": 42.0}
TERM_GRACE_S = 420

T0 = time.time()
CUR: dict = {"proc": None, "label": None, "dir": None}
STOP = {"flag": False}


def say(msg: str) -> None:
    print(f"[slot {time.strftime('%H:%M:%SZ', time.gmtime())} +{(time.time() - T0) / 60:.1f}m] {msg}", flush=True)


def elapsed_min() -> float:
    return (time.time() - T0) / 60


def reap_recorded_server(arm_dir: Path, port: int) -> dict | None:
    """Only after our arm driver was SIGKILLed: its recorded server pid, if still OUR llama-server."""
    f = arm_dir / "server.pid"
    if not f.exists():
        return None
    pid = int(f.read_text().strip() or 0)
    try:
        argv = [x for x in Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0") if x]
    except OSError:
        return {"pid": pid, "alive": False}
    ours = (any(x.endswith("llama-server") and x.startswith(str(C.BIN)) for x in argv)
            and "--port" in argv and argv[argv.index("--port") + 1] == str(port))
    if not ours:
        return {"pid": pid, "alive": True, "ours": False, "note": "pid reused by something else - NOT signalled"}
    rec = {"pid": pid, "ours": True, "sent": []}
    for sig, wait in ((signal.SIGTERM, 180), (signal.SIGKILL, 30)):
        try:
            os.kill(pid, sig)
            rec["sent"].append(sig.name)
        except ProcessLookupError:
            break
        t = time.time()
        while time.time() - t < wait and subprocess.run(["ps", "-p", str(pid)], capture_output=True).returncode == 0:
            time.sleep(1)
        if subprocess.run(["ps", "-p", str(pid)], capture_output=True).returncode != 0:
            break
    rec["verified_dead"] = subprocess.run(["ps", "-p", str(pid)], capture_output=True).returncode != 0
    return rec


def stop_child(p: subprocess.Popen, arm_dir: Path | None, port: int) -> dict:
    rec = {"pid": p.pid, "sent": []}
    if p.poll() is None:
        p.send_signal(signal.SIGTERM)
        rec["sent"].append("TERM")
        try:
            p.wait(timeout=TERM_GRACE_S)
        except subprocess.TimeoutExpired:
            p.send_signal(signal.SIGKILL)
            rec["sent"].append("KILL")
            p.wait(timeout=30)
            if arm_dir is not None:
                rec["server_reap"] = reap_recorded_server(arm_dir, port)
    rec["verified_dead"] = subprocess.run(["ps", "-p", str(p.pid)], capture_output=True).returncode != 0
    rec["rc"] = p.returncode
    return rec


def on_signal(signum, _frame):
    STOP["flag"] = True
    say(f"signal {signum}: stopping the current arm ({CUR['label']}) and exiting")
    if CUR["proc"] is not None:
        CUR["teardown"] = stop_child(CUR["proc"], CUR["dir"], ARGS.port)
        say(f"current arm teardown: {CUR['teardown']}")
    raise SystemExit(128 + signum)


def run_child(label: str, argv: list[str], log: Path, hard_s: float, arm_dir: Path) -> dict:
    t = time.time()
    with open(log, "w") as fh:
        p = subprocess.Popen(argv, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
        CUR.update(proc=p, label=label, dir=arm_dir)
        rec = {"label": label, "argv": argv, "pid": p.pid, "hard_timeout_s": round(hard_s), "log": str(log)}
        try:
            rec["rc"] = p.wait(timeout=hard_s)
        except subprocess.TimeoutExpired:
            say(f"{label}: HARD TIMEOUT {hard_s:.0f} s - SIGTERM own child {p.pid}")
            rec["hard_timeout_hit"] = True
            rec["teardown"] = stop_child(p, arm_dir, ARGS.port)
            rec["rc"] = p.returncode
        CUR.update(proc=None, label=None, dir=None)
    rec["wall_min"] = round((time.time() - t) / 60, 2)
    return rec


def gpu_clear(wait_s: float = 60) -> dict:
    """Between arms: our previous server must be gone from KFD before the next one loads."""
    t = time.time()
    while True:
        f = C.foreign_gpu_procs()
        if not f or time.time() - t > wait_s:
            return {"kfd_holders": {str(k): v for k, v in f.items()}, "waited_s": round(time.time() - t, 1)}
        time.sleep(2)


def kvu_argv(label: str, cap_min: float, dry: bool) -> list[str]:
    skip, b, ub, _ = KVU[label]
    a = PY + [str(HERE / "kvu16b_arm.py"), "--label", label, "--skip", skip, "--b", str(b), "--ub", str(ub),
              "--out-root", str(ARGS.results), "--port", str(ARGS.port), "--max-wall-s", str(int(cap_min * 60)),
              "--bin-dir", str(C.BIN)]
    return a + (["--dry-run"] if dry else [])


def p3_argv(arm: str, label: str, budget_min: float, dry: bool) -> list[str]:
    a = PY + [str(HERE / "p3_kvu_probe_slot.py"), "--arm", arm, "--bin-dir", str(C.BIN), "--port", str(ARGS.port),
              "--out-dir", str(ARGS.results / "p3v2" / label), "--phase", ARGS.p3_phase,
              "--budget-min", f"{budget_min:.1f}"]
    if ARGS.p3_npp_list:
        a += ["--b-npp-list", ARGS.p3_npp_list]
    return a + (["--dry-run"] if dry else [])


def plan() -> list[tuple]:
    items = []
    for it in ARGS.order.split(","):
        if it in KVU:
            items.append(("kvu", it))
        elif it == "p3":
            for r in range(1, ARGS.p3_pairs + 1):
                items.append(("p3pair", r))
        else:
            raise SystemExit(f"unknown order item {it}")
    return items


def main() -> int:
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--port", type=int, default=18183)
    ap.add_argument("--budget-min", type=float, default=90)
    ap.add_argument("--order", default="kvu_on_b2048,kvu_off_b2048,kvu_on_b512,p3")
    ap.add_argument("--kvu-cap-min", type=float, default=20)
    ap.add_argument("--p3-pairs", type=int, default=2)
    ap.add_argument("--p3-phase", default="a1", choices=["a1", "all"])
    ap.add_argument("--p3-npp-list", default=None)
    ap.add_argument("--bin-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ARGS = ap.parse_args()
    if ARGS.port == 8083:
        raise SystemExit("REFUSING: scratch port only")
    if ARGS.bin_dir:
        C.set_bin(ARGS.bin_dir)
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    items = plan()

    if ARGS.dry_run:
        say(f"PLAN (budget {ARGS.budget_min:.0f} GPU-min, value order {ARGS.order}, scratch :{ARGS.port}, bin {C.BIN})")
        t = 0.0
        for kind, x in items:
            if kind == "kvu":
                est = min(KVU[x][3], ARGS.kvu_cap_min + KVU_OVERHEAD_MIN)
                t += est
                print(f"  {x:<14} est {est:5.1f} min (replay cap {ARGS.kvu_cap_min:.0f} min + ~{KVU_OVERHEAD_MIN:.0f} overhead)"
                      f"  cumulative {t:5.1f}  {'FITS' if t <= ARGS.budget_min else 'OVER BUDGET -> skipped/shrunk at run time'}")
            else:
                est = P3_EST["on"] + P3_EST["off"]
                fits = t + est <= ARGS.budget_min
                if fits:
                    t += est
                print(f"  p3 pair {x} (ON,OFF) est {est:5.1f} min  cumulative {t:5.1f}  "
                      f"{'FITS' if fits else 'does NOT fit at estimates -> runs only if earlier arms finish early'}")
        print(f"  total at estimates (fitted items): {t:.1f} min of {ARGS.budget_min:.0f}")
        sys.stdout.flush()
        for kind, x in items:
            if kind == "kvu":
                subprocess.run(kvu_argv(x, ARGS.kvu_cap_min, True), check=False)
        for arm in ("on", "off"):
            subprocess.run(p3_argv(arm, f"pair1_{arm}", P3_HARD_MIN[ARGS.p3_phase], True), check=False)
        subprocess.run(PY + [str(HERE / "kvu16b_residency_slot.py"), "--dry-run", "--base",
                             f"http://127.0.0.1:{ARGS.port}"], check=False)
        print(f"  [report] {' '.join(PY)} {HERE / 'slot_report.py'} {ARGS.results}  -> {ARGS.results}/report.md")
        return 0

    ARGS.results.mkdir(parents=True, exist_ok=True)
    run = {"schema": "gpuslot.run.v1", "started_at": C.now(), "budget_min": ARGS.budget_min, "order": ARGS.order,
           "port": ARGS.port, "bin": str(C.BIN), "kvu_cap_min": ARGS.kvu_cap_min, "items": []}

    def save():
        C.write_json(ARGS.results / "slot_run.json", run)

    save()
    rc_all = 0
    for kind, x in items:
        if STOP["flag"]:
            break
        remaining = ARGS.budget_min - elapsed_min()
        if kind == "kvu":
            cap = min(ARGS.kvu_cap_min, remaining - KVU_OVERHEAD_MIN)
            if cap < KVU_MIN_REPLAY_MIN:
                run["items"].append({"label": x, "status": "skipped", "reason": f"budget: {remaining:.1f} min left"})
                say(f"{x}: SKIPPED (only {remaining:.1f} min left)")
                save()
                continue
            pre = gpu_clear()
            if pre["kfd_holders"]:
                run["items"].append({"label": x, "status": "aborted", "reason": "foreign KFD VRAM holder", **pre})
                say(f"{x}: ABORT - KFD holders present {pre['kfd_holders']}")
                rc_all |= 2
                break
            say(f"{x}: start (replay cap {cap:.1f} min, remaining {remaining:.1f} min)")
            r = run_child(x, kvu_argv(x, cap, False), ARGS.results / f"{x}.driver.log",
                          cap * 60 + 1200, ARGS.results / x)
            r.update(kind="kvu", replay_cap_min=round(cap, 1), started_at_min=round(elapsed_min() - r["wall_min"], 1))
            try:
                r["verdict"] = json.loads((ARGS.results / x / "replay" / "report.json").read_text()).get("verdict")
            except (OSError, ValueError):
                r["verdict"] = None
            r["status"] = "ok" if r["rc"] == 0 else "failed"
            rc_all |= 0 if r["rc"] == 0 else 1
            say(f"{x}: done rc {r['rc']} verdict {r['verdict']} in {r['wall_min']} min")
        else:
            need = P3_EST["on"] + P3_EST["off"]
            if remaining < need:
                run["items"].append({"label": f"p3 pair{x}", "status": "skipped",
                                     "reason": f"budget: {remaining:.1f} min left < {need} for an ON+OFF pair"})
                say(f"p3 pair{x}: SKIPPED ({remaining:.1f} min left < {need})")
                save()
                continue
            for arm in ("on", "off"):
                pre = gpu_clear()
                if pre["kfd_holders"]:
                    run["items"].append({"label": f"p3 pair{x} {arm}", "status": "aborted", **pre})
                    rc_all |= 2
                    STOP["flag"] = True
                    break
                label = f"pair{x}_{arm}"
                b_budget = ARGS.budget_min - elapsed_min() - (P3_EST["off"] if arm == "on" else 0)
                say(f"p3 {label}: start (remaining {ARGS.budget_min - elapsed_min():.1f} min)")
                r = run_child(f"p3_{label}", p3_argv(arm, label, max(0.0, b_budget), False),
                              ARGS.results / f"p3_{label}.driver.log", P3_HARD_MIN[ARGS.p3_phase] * 60,
                              ARGS.results / "p3v2" / label)
                r.update(kind="p3", arm=arm, pair=x, status="ok" if r["rc"] == 0 else "failed")
                rc_all |= 0 if r["rc"] == 0 else 1
                say(f"p3 {label}: done rc {r['rc']} in {r['wall_min']} min")
                run["items"].append(r)
                save()
            continue
        run["items"].append(r)
        save()
    run["finished_at"] = C.now()
    run["elapsed_min"] = round(elapsed_min(), 1)
    run["gpu_after"] = gpu_clear(wait_s=30)
    save()
    rr = subprocess.run(PY + [str(HERE / "slot_report.py"), str(ARGS.results)], check=False)
    say(f"ALL DONE rc {rc_all} (report rc {rr.returncode}) in {run['elapsed_min']} min -> {ARGS.results}/report.md")
    return rc_all


ARGS: argparse.Namespace

if __name__ == "__main__":
    raise SystemExit(main())
