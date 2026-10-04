#!/usr/bin/env python3
"""One KVU-16b replay arm on a SCRATCH llama-server this process starts and owns.

  1. env + argv: slot_common.arm_env(skip) + PREFIX + :8083's production argv with -b/-ub = the arm,
     --port <scratch>, -lv 4, --device ROCm0 --device-draft ROCm0, own --slot-save-path.
  2. start (own pid, own session; stdout/stderr arrival-timestamped), KFD/device VRAM at 1 Hz with phase marks,
     wait healthy, HIP dlopen proof (/proc/<pid>/maps), live env readback, /props build_info.
  3. ONE short greedy coherence spot-check (text saved; no classifier).
  4. kvu16b_residency_slot.py as our own child (wall cap passed through); hard timeout cap + 300 s.
  5. teardown: SIGTERM (180 s, lets -lv 4 print the exit memory breakdown) -> SIGKILL, ps -p verified, port free.
  6. arm.json (+ memory lines from the server log).

Usage: kvu16b_arm.py --label L --skip on|off --b 2048 --ub 2048 --out-root DIR [--port 18183]
                     [--max-wall-s 1200] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_common as C  # noqa: E402

RUNNER = HERE / "kvu16b_residency_slot.py"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--skip", choices=["on", "off"], required=True)
    ap.add_argument("--b", type=int, default=2048)
    ap.add_argument("--ub", type=int, default=2048)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--port", type=int, default=18183)
    ap.add_argument("--max-wall-s", type=float, default=1200)
    ap.add_argument("--bin-dir", default=None)
    ap.add_argument("--boot-timeout", type=float, default=600)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.port == 8083:
        raise SystemExit("REFUSING: scratch port only (8083 is production)")
    if a.bin_dir:
        C.set_bin(a.bin_dir)
    skip = a.skip == "on"
    od = a.out_root / a.label
    (od / "slots").mkdir(parents=True, exist_ok=True)  # llama-server refuses a missing --slot-save-path dir
    argv, notes, src = C.build_server_argv(a.port, a.b, a.ub, od / "slots")
    cmd = C.launch_cmd(skip, argv)
    base = f"http://127.0.0.1:{a.port}"
    runner = [sys.executable, "-B", str(RUNNER), "--i-own-the-window", "--base", base, "--server-pid", "<PID>",
              "--server-log", str(od / "server.log"), "--out-dir", str(od / "replay"), "--label", a.label,
              "--n-batch", str(a.b), "--n-ubatch", str(a.ub), "--max-wall-s", str(int(a.max_wall_s))]
    if a.dry_run:
        print(f"  [{a.label}] skip {a.skip}  -b {a.b} -ub {a.ub}  port {a.port}  out {od}/")
        print(f"  [{a.label}] argv source: {src['source']} (sha256 {src['sha256'][:16]}); "
              f"{src.get('cross_check_x0_argv_8083', '')}")
        print(f"  [{a.label}] transforms: {'; '.join(notes)}")
        print(f"  [{a.label}] server: {' '.join(cmd)}  > {od}/server.log (arrival-timestamped)")
        print(f"  [{a.label}] coherence: POST {base}/v1/chat/completions greedy, enable_thinking=false, 160 tok "
              f"-> {od}/coherence.json/.txt")
        print(f"  [{a.label}] replay: {' '.join(runner)}   (hard timeout {int(a.max_wall_s) + 300} s)")
        print(f"  [{a.label}] VRAM: device + every KFD pid at 1 Hz -> {od}/vram.jsonl")
        return 0

    od.mkdir(parents=True, exist_ok=True)
    rec: dict = {"schema": "gpuslot.kvu16b_arm.v1", "label": a.label, "skip": a.skip, "b": a.b, "ub": a.ub,
                 "started_at": C.now(), "argv_source": {k: src[k] for k in ("source", "sha256") if k in src},
                 "argv_transforms": notes, "cmd": cmd, "env": C.arm_env(skip)[1], "bin_dir": str(C.BIN),
                 "vram_before": C.vram_now(), "foreign_gpu_procs_before": C.foreign_gpu_procs()}
    sampler = C.VramSampler(od / "vram.jsonl", period=1.0).start()
    proc = None
    rc = 1
    try:
        sampler.mark("launch")
        proc = C.start_own(cmd, od / "server.log", env=C.child_env(skip))
        rec["pid"] = proc.pid
        (od / "server.pid").write_text(f"{proc.pid}\n")  # lets slot_run reap it if this driver is SIGKILLed
        rec["load_s"] = C.wait_healthy(base, proc, timeout=a.boot_timeout)
        sampler.mark("healthy")
        rec["kfd_at_healthy_gib"] = round(C.kfd_pids().get(proc.pid, {}).get("vram_b", 0) / 2**30, 3)
        rec["hip_dlopen_proof"] = C.hip_dlopen_proof(proc.pid)
        rec["live_env"] = C.live_env(proc.pid)
        props = C.http_json(base + "/props")
        rec["build_info"] = props.get("build_info")
        slots = C.http_json(base + "/slots")
        rec["n_slots"], rec["n_ctx_slot"] = len(slots), min(s.get("n_ctx", 0) for s in slots)
        print(f"[{a.label}] healthy in {rec['load_s']} s pid {proc.pid} build {rec['build_info']} "
              f"slots {rec['n_slots']}x{rec['n_ctx_slot']} hip-proof {rec['hip_dlopen_proof'].get('ok')} "
              f"live env {rec['live_env']}", flush=True)
        if not rec["hip_dlopen_proof"].get("ok"):
            raise RuntimeError(f"HIP dlopen proof failed: {rec['hip_dlopen_proof']}")
        if str(rec["build_info"] or "").find(C.EXPECT_BUILD.split()[0]) < 0:
            print(f"[{a.label}] WARNING build_info {rec['build_info']} != expected {C.EXPECT_BUILD}", flush=True)
        sampler.mark("coherence")
        coh = C.coherence_check(base, od / "coherence.json", a.label)
        rec["coherence"] = {k: coh.get(k) for k in ("text_sha", "finish", "predicted_n", "decode_tps", "error")}
        print(f"[{a.label}] coherence: sha {coh.get('text_sha')} finish {coh.get('finish')} "
              f"text {(coh.get('content_text') or coh.get('error') or '')[:160]!r}", flush=True)
        sampler.mark("replay")
        r_argv = [x if x != "<PID>" else str(proc.pid) for x in runner]
        rec["runner_argv"] = r_argv
        with open(od / "replay.log", "w") as fh:
            rp = subprocess.Popen(r_argv, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
            C.OWN_CHILDREN.append(rp)
            try:
                rec["runner_rc"] = rp.wait(timeout=a.max_wall_s + 300)
            except subprocess.TimeoutExpired:
                rec["runner_timeout"] = True
                rec["runner_teardown"] = C.stop_own(rp, term_wait=60)
                rec["runner_rc"] = rp.returncode
            if rp in C.OWN_CHILDREN:
                C.OWN_CHILDREN.remove(rp)
        sampler.mark("replay_done")
        rec["kfd_after_replay_gib"] = round(C.kfd_pids().get(proc.pid, {}).get("vram_b", 0) / 2**30, 3)
        rep = od / "replay" / "report.json"
        if rep.exists():
            r = json.loads(rep.read_text())
            rec["verdict"] = r.get("verdict")
            print(f"[{a.label}] replay verdict {r.get('verdict')} wall {r.get('wall_s')} s KFD peak "
                  f"{(r.get('vram') or {}).get('kfd_peak_gib')} GiB TTFT {r.get('ttft_own_send_s')}", flush=True)
        rc = 0 if rec.get("runner_rc") in (0, 1, 4) else 1  # PASS/FAIL/CAPPED are all measurements
        rec["status"] = "ok" if rc == 0 else "runner_error"
    except Exception as exc:  # noqa: BLE001
        rec["status"] = "failed"
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["traceback"] = traceback.format_exc()[-3000:]
        print(f"[{a.label}] FAILED: {rec['error']}", flush=True)
    finally:
        if proc is not None:
            sampler.mark("teardown")
            rec["teardown"] = C.stop_own(proc, term_wait=180)
        time.sleep(2)
        sampler.stop()
        rec["vram"] = sampler.summary(rec.get("pid"), rec["vram_before"].get("used_b"))
        rec["vram_marks"] = sampler.marks
        rec["port_free_after"] = not C.port_listening(a.port)
        rec["memory_lines"] = C.log_memory_lines(od / "server.log")
        rec["finished_at"] = C.now()
        C.write_json(od / "arm.json", rec)
        print(f"[{a.label}] done status {rec.get('status')} teardown {rec.get('teardown')} "
              f"KFD own peak {rec['vram'].get('own_pid_peak_vram_gib')} GiB", flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
