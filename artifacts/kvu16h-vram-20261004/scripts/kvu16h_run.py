#!/usr/bin/env python3
"""KVU-16h sequencer: attribute :8083's +7.2 GiB VRAM growth while serving to a NAMED allocator.

Launches :8083's PRODUCTION argv (source: live :8083 cmdline, else the stack launch record
logs/server_launches/8083.json; v10 store binary, DFlash2, np 4, -c 393216) on a SCRATCH port with -lv 4,
optionally under the hipMalloc interposer (shim/libhipmalloc_trace.so), and replays request shapes one phase at a
time. Every phase = traffic, then a 60 s idle sample. VRAM: 1 Hz KFD per-process + card sysfs (started BEFORE the
launch) and rocm-smi --showmeminfo vram. Hard ceiling: abort (stop traffic, graceful teardown) if own-pid KFD or
card used VRAM > --ceiling-gib (62.5).

ARM A (production argv, -lv 4, shim):   phases in order (ESSENTIAL = the brief; + = added, skipped first on budget)
  load        launch + healthy + 60 s idle                                          baseline after load
  short       1 x ~60-tok prompt (prefill on MMQ, ne11 <= 128), 256 generated (DFlash2 on): decode-only control
+ sweep       single requests 400..12800 tokens ascending, then the same sizes again (repeat => 0 growth if pool reuse)
  prefill80k  1 x 80k prompt, 64 generated
  dec4        4 concurrent ~1k prompts, 1000 generated each (ignore_eos)
  mix1        Q38-T7 shape: 2 decoding streams + 2 x 32k prefills concurrent (prefill shares ubatches with decode)
  mix2        mix1 again with fresh prompts                   (keeps growing, or plateau?)
+ t7c         Q38-T7 #1 phase-C shape: 4 x 16k concurrent, 300 generated
+ nodraft     speculative.n_max 0 requests (16k fresh, 2k fresh): Q38-T7 #2's no-draft needles grew +0.89 GiB
  idlecache   idle-slot caching path (cache_idle_slots is ON in production): 1 short task (idle slots are saved to
              the --cache-ram prompt cache and cleared), then prefill80k's prompt + a suffix (restore from RAM)
  longidle    120 s + the 60 s idle, no traffic (does anything give memory back?)
  teardown    graceful SIGTERM -> exit memory breakdown (TRACE, -lv>=4) + ~llama_context compute-size WARN
ARM B (optional, --arm-b auto|ub512|ub128|nographs|off): relaunch with ONE change, replay mix1, mix2:
  ub512    -b 512 -ub 512   (KVU-16f; bounds per-ubatch hipBLAS F16 temps in the legacy pool + the KQ mask)
  ub128    -ub 128          (Q8_0 stays on MMQ on gfx90a, ne11 <= 128: no dequant-to-pool path; mechanism proof)
  nographs GGML_CUDA_DISABLE_GRAPHS=1 (if the growth is HIP-runtime-internal, i.e. the shim's residual)
  auto     pool/compute/rocBLAS dominant -> ub512; residual dominant -> nographs; growth < 0.5 GiB -> none
GGML_CUDA_NO_VMM cannot be toggled: it is compile-time (GGML_HIP_NO_VMM=ON in the v10 CMakeCache; no env knob).

Exit: 0 = ran to completion (summary.md written), 2 = refused (preflight), 3 = VRAM ceiling abort (summary still
written), 4 = runtime error. Never touches :8083 or any process it did not start. No CPU region lock (the CPU side
is an HTTP client + samplers).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, "/mnt/raid0/llm/tmp/gpu-block-27b-20261003")
import lib_kvu16h as K  # noqa: E402
import lib_gpublock as L  # noqa: E402  (prompts, /tokenize, SSE client)

sys.stdout.reconfigure(line_buffering=True)
T0 = time.time()
IDLE_S = 60
LONGIDLE_S = 120

# phase: (essential, estimate_min incl. 60 s idle, cap_s for the traffic part)
PHASES_A = {
    "short": (True, 1.5, 180), "sweep": (False, 3.0, 420), "prefill80k": (True, 4.5, 600), "dec4": (True, 2.5, 300),
    "mix1": (True, 5.5, 720), "mix2": (True, 5.5, 720), "t7c": (False, 4.5, 540), "nodraft": (False, 2.5, 300),
    "idlecache": (True, 4.5, 540), "longidle": (True, 3.0, 120),
}
PHASES_B = {"mix1": (True, 6.0, 780), "mix2": (True, 6.0, 780)}
LOAD_MIN, TEARDOWN_MIN, RESERVE_MIN = 3.0, 2.5, 1.0
ARM_B = {"ub512": {"b": 512, "ub": 512, "env": {}}, "ub128": {"b": None, "ub": 128, "env": {}},
         "nographs": {"b": None, "ub": None, "env": {"GGML_CUDA_DISABLE_GRAPHS": "1"}}}


def elapsed_min() -> float:
    return (time.time() - T0) / 60


def say(msg: str) -> None:
    print(f"[kvu16h {time.strftime('%H:%M:%SZ', time.gmtime())} +{elapsed_min():.1f}m] {msg}", flush=True)


# ---------------------------------------------------------------- traffic
class Arm:
    def __init__(self, name: str, d: Path, port: int, sampler: K.VramSampler, marks: K.Marks, shim: bool) -> None:
        self.name, self.dir, self.port, self.base = name, d, port, f"http://127.0.0.1:{port}"
        self.sampler, self.marks, self.shim = sampler, marks, shim
        self.req = K.Jsonl(d / "requests.jsonl")
        self.saved_prompts: dict[str, str] = {}
        self.n = 0

    def prompt(self, tokens: int, tag: str, tail: str = "") -> tuple[str, int]:
        self.n += 1
        text, n, _ = L.fit_prompt(self.base, tokens, L.nonce(f"kvu16h {self.name} {tag} #{self.n}"), start=self.n % 7,
                                  tail=tail or L_TASK)
        return text, n

    def send(self, phase: str, tag: str, text: str, ntok: int, n_predict: int, stop: threading.Event,
             ignore_eos: bool = False, nodraft: bool = False, first_tok: threading.Event | None = None) -> dict:
        body = {"prompt": text, "n_predict": n_predict, "ignore_eos": ignore_eos, "cache_prompt": True,
                "temperature": 0.0, "top_k": 1}
        if nodraft:
            body["speculative.n_max"] = 0
        r = L.stream_request(f"{self.base}/completion", body, timeout=3600, stop=stop,
                             on_first_token=(first_tok.set if first_tok else None))
        row = {"t_end": round(time.time(), 3), "arm": self.name, "phase": phase, "tag": tag, "prompt_tokens": ntok,
               "n_predict": n_predict, "ignore_eos": ignore_eos, "nodraft": nodraft, "http": r.get("http_status"),
               "error": r.get("error"), "aborted": r.get("aborted"), "ttft_s": r.get("ttft_s"),
               "wall_s": r.get("wall_s"), "t_send": round(r["t_send"], 3), **L.timing_summary(r.get("timings"))}
        self.req.add(row)
        if first_tok is not None:
            first_tok.set()  # never leave a waiter hanging on a failed request
        return row


SHORT_PROMPT = ("In three short sentences, explain why the sky looks blue during the day and red at sunset.")
L_TASK = ("\n\n---\nTask: using the material above, reason about which single change to the tinyBLAS "
          "gemm4xN<3> kernel would most improve CPU decode throughput, then state it in one paragraph.")


def run_threads(fns: list) -> list[threading.Thread]:
    ts = [threading.Thread(target=f, daemon=True) for f in fns]
    for t in ts:
        t.start()
    return ts


def phase_traffic(arm: Arm, phase: str, stop: threading.Event) -> None:
    """Traffic only (prompts were fitted before the phase's begin marker where possible)."""
    P = arm.pre.get(phase, {})  # type: ignore[attr-defined]
    if phase == "short":
        text, n = P["p"]
        arm.send(phase, "short", text, n, 256, stop)
    elif phase == "sweep":
        for tag, (text, n) in P["ps"]:
            if stop.is_set():
                return
            arm.send(phase, tag, text, n, 32, stop)
    elif phase == "prefill80k":
        text, n = P["p"]
        arm.saved_prompts["prefill80k"] = text
        arm.send(phase, "80k", text, n, 64, stop)
    elif phase == "dec4":
        ts = run_threads([lambda i=i: arm.send(phase, f"dec{i}", *P["ps"][i], 1000, stop, ignore_eos=True)
                          for i in range(4)])
        for t in ts:
            t.join()
    elif phase in ("mix1", "mix2"):
        dec_stop = threading.Event()
        firsts = [threading.Event(), threading.Event()]
        decs = run_threads([lambda i=i: arm.send(phase, f"dec{i}", *P["dec"][i], 6000, dec_stop, ignore_eos=True,
                                                 first_tok=firsts[i]) for i in range(2)])
        t_wait = time.time()
        while not all(f.is_set() for f in firsts) and time.time() - t_wait < 180 and not stop.is_set():
            time.sleep(0.5)
        arm.marks.mark(phase, "decoders_streaming")
        pre = run_threads([lambda i=i: arm.send(phase, f"prefill{i}", *P["pf"][i], 64, stop) for i in range(2)])
        while any(t.is_alive() for t in pre) and not stop.is_set():
            time.sleep(0.5)
        arm.marks.mark(phase, "prefills_done")
        t_hold = time.time()
        while time.time() - t_hold < 10 and not stop.is_set():
            time.sleep(0.5)
        dec_stop.set()
        for t in decs + pre:
            t.join(timeout=120)
    elif phase == "t7c":
        ts = run_threads([lambda i=i: arm.send(phase, f"c{i}", *P["ps"][i], 300, stop) for i in range(4)])
        for t in ts:
            t.join()
    elif phase == "nodraft":
        for tag, (text, n) in P["ps"]:
            if stop.is_set():
                return
            arm.send(phase, tag, text, n, 300 if n > 8000 else 200, stop, nodraft=True)
    elif phase == "idlecache":
        text, n = P["trigger"]
        arm.send(phase, "trigger", text, n, 1, stop)       # launches a task -> idle slots saved + cleared
        time.sleep(5)
        base80 = arm.saved_prompts.get("prefill80k")
        if base80 and not stop.is_set():
            arm.send(phase, "restore80k", base80 + "\n\nIn one sentence: what is the main topic above?", -1, 32, stop)
    elif phase == "longidle":
        stop.wait(LONGIDLE_S)


def prepare(arm: Arm, phase: str) -> None:
    """Fit prompts with POST /tokenize BEFORE the phase's begin marker (tokenize allocates no VRAM, but keep it out
    of the window anyway)."""
    pre: dict = {}
    if phase == "short":  # literal ~60-token prompt: prefill stays on MMQ (ne11 <= 128), a decode-only control
        txt = L.nonce(f"kvu16h {arm.name} short") + SHORT_PROMPT
        pre["p"] = (txt, L.tokenize_count(arm.base, txt))
    elif phase == "sweep":
        sizes = [400, 800, 1600, 3200, 6400, 12800]
        pre["ps"] = [(f"up{s}", arm.prompt(s, f"up{s}")) for s in sizes] + \
                    [(f"rep{s}", arm.prompt(s, f"rep{s}")) for s in sizes]
    elif phase == "prefill80k":
        pre["p"] = arm.prompt(80000, "80k")
    elif phase == "dec4":
        pre["ps"] = [arm.prompt(1000, f"dec{i}") for i in range(4)]
    elif phase in ("mix1", "mix2"):
        pre["dec"] = [arm.prompt(1000, f"{phase}dec{i}") for i in range(2)]
        pre["pf"] = [arm.prompt(32000, f"{phase}pf{i}") for i in range(2)]
    elif phase == "t7c":
        pre["ps"] = [arm.prompt(16000, f"c{i}") for i in range(4)]
    elif phase == "nodraft":
        pre["ps"] = [("nd16k", arm.prompt(16000, "nd16k")), ("nd2k", arm.prompt(2000, "nd2k"))]
    elif phase == "idlecache":
        pre["trigger"] = arm.prompt(200, "trigger")
    arm.pre[phase] = pre  # type: ignore[attr-defined]


def run_phase(arm: Arm, phase: str, cap_s: float) -> dict:
    prepare(arm, phase)
    own0 = arm.sampler.last.get("own_vram_b")
    arm.marks.mark(phase, "begin", own_vram_b=own0)
    stop = threading.Event()
    t = threading.Thread(target=phase_traffic, args=(arm, phase, stop), daemon=True)
    t.start()
    t_start, capped = time.time(), False
    while t.is_alive():
        if arm.sampler.abort.is_set():
            stop.set()
            break
        if time.time() - t_start > cap_s:
            capped = True
            stop.set()
            break
        t.join(timeout=0.5)
    t.join(timeout=180)
    arm.marks.mark(phase, "traffic_end", capped=capped, aborted=arm.sampler.abort.is_set(),
                   own_vram_b=arm.sampler.last.get("own_vram_b"))
    if not arm.sampler.abort.is_set():
        arm.sampler.abort.wait(IDLE_S)
    own1 = arm.sampler.last.get("own_vram_b")
    arm.marks.mark(phase, "idle_end", own_vram_b=own1,
                   delta_gib=round((own1 - own0) / K.GIB, 3) if (own0 and own1) else None)
    return {"phase": phase, "capped": capped, "own_before_b": own0, "own_after_b": own1}


# ---------------------------------------------------------------- one arm = one server
def run_arm(args, run_dir: Path, label: str, src: dict, prod_env: dict, shim: bool, phases: dict,
            b: int | None = None, ub: int | None = None, extra_env: dict | None = None) -> dict:
    d = run_dir / label
    d.mkdir(parents=True, exist_ok=True)
    argv, notes = K.build_argv(src, args.port, d / "slots", args.lv, b=b, ub=ub)
    (d / "slots").mkdir(exist_ok=True)
    shim_log = d / "shim.log" if shim else None
    env, env_rec = K.child_env(prod_env, extra_env, shim_log)
    cmd = src["prefix"] + argv
    if args.mock:  # CPU-only self-test: same argv recorded, a stdlib mock server is what actually runs
        cmd_run = [sys.executable, str(HERE / "dryrun" / "mock_server.py"), "--port", str(args.port)]
    else:
        cmd_run = cmd
    K.write_json(d / "launch.json", {"cmd": cmd, "mock_cmd": cmd_run if args.mock else None, "argv_notes": notes, "argv_source": src["source"], "env": env_rec,
                                     "shim": shim, "b": b, "ub": ub, "extra_env": extra_env or {}})
    say(f"[{label}] launch: {' '.join(cmd)}")
    sampler = K.VramSampler(d / "vram.jsonl", args.ceiling_gib).start()   # BEFORE the launch
    smi = K.SmiSampler(d / "smi.jsonl", args.smi_period).start()
    marks = K.Marks(d / "marks.jsonl", d / "server.log", shim_log)
    time.sleep(3)
    marks.mark("load", "pre_launch", card_used_b=sampler.last.get("card_used_b"))
    proc = K.start_own(cmd_run, d / "server.log", env)
    (d / "server.pid").write_text(str(proc.pid))
    sampler.own_pid = proc.pid
    marks.mark("load", "launched", pid=proc.pid)
    res: dict = {"label": label, "pid": proc.pid, "phases": [], "skipped": [], "aborted": None}
    try:
        res["load_s"] = K.wait_healthy(f"http://127.0.0.1:{args.port}", proc, timeout=900, abort=sampler.abort)
        res["healthy"] = True
        maps = K.hip_dlopen_proof(proc.pid, K.EXPECT_BIN_REAL)
        props = {}
        try:
            props = K.http_json(f"http://127.0.0.1:{args.port}/props", timeout=10)
        except Exception as exc:  # noqa: BLE001
            props = {"err": str(exc)}
        build = str(props.get("build_info", ""))
        K.write_json(d / "residency.json", {"maps": maps, "build_info": build,
                                            "kfd_after_healthy_gib": round((sampler.last.get("own_vram_b") or 0) / K.GIB, 3)})
        marks.mark("load", "healthy", load_s=res["load_s"], build=build, hip_ok=maps.get("ok"),
                   shim_mapped=bool(maps.get("shim_mapped")), own_vram_b=sampler.last.get("own_vram_b"))
        if args.mock:
            pass  # no GPU in the self-test: residency/build/KFD proofs are recorded but not enforced
        elif not maps.get("ok") or "10303" not in build or "ffc1bac82" not in build:
            raise RuntimeError(f"residency/build proof failed: hip_ok={maps.get('ok')} build={build!r}")
        elif shim and not maps.get("shim_mapped"):
            raise RuntimeError("shim requested but not mapped in the server")
        elif (sampler.last.get("own_vram_b") or 0) < 40 * K.GIB:
            raise RuntimeError("server is not GPU-resident (KFD VRAM < 40 GiB after healthy)")
        sampler.abort.wait(IDLE_S)
        if sampler.abort.is_set():
            raise RuntimeError(f"VRAM ceiling abort: {sampler.abort_reason}")
        marks.mark("load", "idle_end", own_vram_b=sampler.last.get("own_vram_b"))
        arm = Arm(label, d, args.port, sampler, marks, shim)
        arm.pre = {}  # type: ignore[attr-defined]
        for ph, (essential, est, cap) in phases.items():
            if sampler.abort.is_set():
                break
            left = args.budget_min - elapsed_min() - TEARDOWN_MIN - RESERVE_MIN
            # essentials run whenever they fit; an added (+) phase in arm A also leaves arm B its reserve
            reserve_b = args.arm_b_min if (label.startswith("armA") and args.arm_b != "off" and not essential) else 0.0
            if est > left - reserve_b:
                res["skipped"].append({"phase": ph, "estimate_min": est, "left_min": round(left, 1),
                                       "arm_b_reserve_min": reserve_b})
                marks.mark(ph, "skipped_budget", estimate_min=est, left_min=round(left, 1), arm_b_reserve_min=reserve_b)
                continue
            res["phases"].append(run_phase(arm, ph, min(cap, max(60.0, left * 60 - IDLE_S))))
    except Exception as exc:  # noqa: BLE001
        res["error"] = f"{type(exc).__name__}: {exc}"[:600]
        say(f"[{label}] ERROR {res['error']}")
    finally:
        res["aborted"] = sampler.abort_reason
        marks.mark("teardown", "begin", own_vram_b=sampler.last.get("own_vram_b"))
        res["teardown"] = K.stop_own(proc, term_wait=120)
        marks.mark("teardown", "end", **{k: v for k, v in res["teardown"].items() if k != "at"})
        time.sleep(3)
        sampler.stop()
        smi.stop()
        res["peak_own_gib"] = round(sampler.peak_own_b / K.GIB, 3)
        K.write_json(d / "arm_result.json", res)
    return res


def preflight(args, src: dict) -> list[str]:
    probs = K.validate_prod_argv(src)
    if args.mock:  # the self-test touches no GPU and may run while another session holds the card
        return probs + ([f"scratch port {args.port} in use"] if K.port_listening(args.port) else [])
    if K.port_listening(8083):
        probs.append(":8083 is LISTENING: production must be stopped by the window owner first (two 27B do not fit)")
    if K.port_listening(args.port):
        probs.append(f"scratch port {args.port} in use")
    if args.port == 8083:
        probs.append("scratch port may not be 8083")
    f = K.foreign_gpu_procs()
    if f:
        probs.append("KFD processes hold VRAM: " + ", ".join(f"{p}:{v['name']}:{v['vram_b'] / K.GIB:.1f}GiB" for p, v in f.items()))
    used, _ = K.card_vram()
    if used is None or used > args.vram_free_max_gib * K.GIB:
        probs.append(f"card VRAM used {None if used is None else round(used / K.GIB, 2)} GiB > {args.vram_free_max_gib}")
    if args.shim and not (K.HERE / "shim" / "selftest.ok").exists():
        probs.append("shim self-test marker missing: run shim/build_shim.sh (gpu_slot_kvu16h.sh does)")
    if not os.environ.get("KVU16H_UNDER_CLAIM") and not args.no_claim:
        probs.append("not running under kvu16h_claim.py (the mi210_0 device claim); use gpu_slot_kvu16h.sh --execute")
    return probs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--port", type=int, default=18083)
    ap.add_argument("--lv", type=int, default=4, help="4 = TRACE (exit breakdown); 5 = DEBUG (adds ggml pool OOM-flush lines)")
    ap.add_argument("--budget-min", type=float, default=60.0)
    ap.add_argument("--ceiling-gib", type=float, default=62.5)
    ap.add_argument("--vram-free-max-gib", type=float, default=2.0)
    ap.add_argument("--smi-period", type=float, default=1.0)
    ap.add_argument("--arm-b", default="auto", choices=["auto", "off", *ARM_B])
    ap.add_argument("--arm-b-min", type=float, default=17.0, help="arm B starts only if this many minutes remain")
    ap.add_argument("--no-shim", dest="shim", action="store_false")
    ap.add_argument("--no-claim", action="store_true", help="debug only: run without the device-claim wrapper")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", action="store_true", help=argparse.SUPPRESS)  # CPU-only RUN-path self-test
    args = ap.parse_args()
    src = K.source_argv()
    penv = K.source_env()
    if args.dry_run:
        return dry_run(args, src, penv)
    if args.mock:
        global IDLE_S, LONGIDLE_S
        IDLE_S, LONGIDLE_S = 2, 2
        args.budget_min = min(args.budget_min, 60.0)
    K.install_signal_handlers()
    probs = preflight(args, src)
    if probs:
        for p in probs:
            say(f"REFUSE: {p}")
        return 2
    import analyze as A  # noqa: E402 (same dir)
    run_dir = args.results
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"task": "KVU-16h", "started": K.now_iso(), "argv_source": src["source"], "argv": src["prefix"] + src["argv"],
                "argv_sha256": src["sha256_raw"], "x0_cross_check": src.get("cross_check_x0"), "env": penv,
                "port": args.port, "lv": args.lv, "budget_min": args.budget_min, "ceiling_gib": args.ceiling_gib,
                "shim": args.shim, "shim_sha256": K.sha256_file(K.SHIM), "arm_b": args.arm_b,
                "sources_sha256": {p.name: K.sha256_file(p) for p in [HERE / "kvu16h_run.py", HERE / "lib_kvu16h.py",
                                   HERE / "analyze.py", HERE / "shim" / "hipmalloc_trace.c",
                                   Path(L.__file__)]},
                "region_lock": "none taken (CPU side is an HTTP client + 1 Hz samplers)"}
    K.write_json(run_dir / "run.json", manifest)
    rc = 0
    # ARM A
    shim = args.shim
    a = run_arm(args, run_dir, "armA", src, penv["env"], shim, PHASES_A)
    if shim and not a.get("healthy") and not a.get("aborted"):
        say("arm A died before healthy WITH the shim: relaunching once WITHOUT it (recorded)")
        manifest["shim_fallback"] = a.get("error")
        K.write_json(run_dir / "run.json", manifest)
        shim = False
        a = run_arm(args, run_dir, "armA_noshim", src, penv["env"], False, PHASES_A)
    if a.get("aborted"):
        rc = 3
    elif a.get("error"):
        rc = 4
    # ARM B decision
    choice, why = "off", "disabled"
    if rc == 0 and args.arm_b != "off":
        try:
            ra = A.analyze_arm(run_dir / a["label"])
            choice, why = A.decide_arm_b(ra) if args.arm_b == "auto" else (args.arm_b, "forced by --arm-b")
        except Exception as exc:  # noqa: BLE001
            choice, why = "off", f"analysis failed: {exc}"
        left = args.budget_min - elapsed_min()
        if choice != "off" and left < args.arm_b_min:
            why += f"; SKIPPED: {left:.1f} min left < {args.arm_b_min}"
            choice = "off"
    manifest["arm_b_decision"] = {"choice": choice, "why": why}
    K.write_json(run_dir / "run.json", manifest)
    say(f"arm B: {choice} ({why})")
    if choice != "off":
        o = ARM_B[choice]
        rb = run_arm(args, run_dir, f"armB_{choice}", src, penv["env"], shim, PHASES_B, b=o["b"], ub=o["ub"],
                     extra_env=o["env"])
        if rb.get("aborted"):
            rc = 3
    manifest["ended"] = K.now_iso()
    manifest["elapsed_min"] = round(elapsed_min(), 1)
    K.write_json(run_dir / "run.json", manifest)
    try:
        A.main([str(run_dir)])
        say(f"summary: {run_dir / 'summary.md'}")
    except Exception as exc:  # noqa: BLE001
        say(f"analysis failed (re-run analyze.py {run_dir}): {exc}")
        rc = rc or 4
    return rc


def dry_run(args, src: dict, penv: dict) -> int:
    print("=== DRY RUN kvu16h_run.py (nothing started, nothing sent) ===")
    print(f"[argv source] {src['source']}")
    print(f"  record argv_sha256 self-check: {src.get('record_sha_matches')}; X0 cross-check: {src.get('cross_check_x0')}")
    drift = K.validate_prod_argv(src)
    print(f"  production invariants: {'OK' if not drift else 'DRIFT ' + '; '.join(drift)}")
    print(f"[env] {penv['source']}")
    for k, v in penv["env"].items():
        print(f"  {k}={v}")
    for label, b, ub, extra in [("armA", None, None, {})] + [(f"armB_{k}", v['b'], v['ub'], v['env']) for k, v in ARM_B.items()]:
        argv, notes = K.build_argv(src, args.port, args.results / label / "slots", args.lv, b=b, ub=ub)
        print(f"[{label}] {'; '.join(notes)}{'; env ' + str(extra) if extra else ''}")
        if label == "armA":
            print("  " + " ".join(src["prefix"] + argv))
    print(f"[shim] {'ON' if args.shim else 'OFF'}: LD_PRELOAD={K.SHIM} (exists {K.SHIM.exists()}, sha "
          f"{(K.sha256_file(K.SHIM) or '-')[:16]}); self-test marker {(K.HERE / 'shim' / 'selftest.ok').exists()}")
    tot = LOAD_MIN + TEARDOWN_MIN
    print("[arm A phases] (essential*, estimate incl. 60 s idle, traffic cap)")
    for ph, (ess, est, cap) in PHASES_A.items():
        tot += est
        print(f"  {'*' if ess else '+'} {ph:<11} ~{est:>4.1f} min  cap {cap:>4.0f} s")
    totb = LOAD_MIN + TEARDOWN_MIN + sum(v[1] for v in PHASES_B.values())
    print(f"  arm A total ~{tot:.0f} min (load {LOAD_MIN} + teardown {TEARDOWN_MIN})")
    print(f"[arm B] --arm-b {args.arm_b}: phases {list(PHASES_B)} ~{totb:.0f} min; starts only if >= {args.arm_b_min} min left")
    print(f"[budget] {args.budget_min} min hard (non-essential phases skipped first); ceiling {args.ceiling_gib} GiB "
          f"(own KFD or card used) -> stop traffic, graceful teardown, exit 3")
    probs = preflight(args, src)
    print("[preflight now] " + ("would PASS" if not probs else "would REFUSE:"))
    for p in probs:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
