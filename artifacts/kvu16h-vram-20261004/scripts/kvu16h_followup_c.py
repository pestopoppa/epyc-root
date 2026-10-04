#!/usr/bin/env python3
"""KVU-16h follow-up + ARM C: prove (or refute) the mechanism behind :8083's +8.08 GiB VRAM growth, and test the fix.

ARM C COPY (kvu16h_followup_c.py, 2026-10-04). Copied from kvu16h_followup.py, which is left untouched. It adds:
  ARM C  `--arm-c-bin <dir>`: the SAME production argv, env, shim and traffic as arm A (graphs ON), but the
         llama-server and LD_LIBRARY_PATH bin dir are replaced by <dir>. <dir> is a GPU store build of
         experimental/mmvq-graph-cache-pool-20261004 (656c9a66b on top of the champion fold candidate 1bceceb05):
         the HIP-graph mmvq q8_1 cache carves its buffers from a private per-context arena instead of ctx.pool().
         Phases warm, t7a.                                          PREDICTION t7a ~0 GiB, decode tok/s == arm A
         Preflight: <dir>/llama-server + libggml-hip.so exist; <dir>/../BUILD.log src sha has the fix commit as an
         ancestor (git -C /mnt/raid0/llm/llama.cpp, read-only); CMakeCache recipe keys equal the v10 store build's.
         Residency: /proc/<pid>/maps must map <dir>'s libggml*; /props build_info must carry the BUILD.log sha.
  Order A -> C -> B (B, the graphs-off diagnostic, runs only if the budget allows; arm C is reserved during A).
  `--no-arm-a` runs C (and B) without A; the H1 verdict is then N/A and arm C is judged absolutely.
  Shim: hipMallocs whose chain has ggml_cuda_mul_mat_vec_q but not ggml_cuda_pool_leg are counted as mmvq_arena.
  Verdict adds `fix`: HOLDS | FAILS | N/A (+ decode tok/s C vs A).

HYPOTHESIS H1 (from the KVU-16h analysis, 2026-10-04):
  v10's local HIP-graph `mmvq_q8_1_graph_cache` (ggml/src/ggml-cuda/mmvq.cu ~2236-2430, HIP+GGML_HIP_GRAPHS only)
  keeps one `ggml_cuda_pool_alloc` per eligible MMVQ node (Q8_0/Q4_K/Q6_K, ne11 == 1, stream 0) for the LIFETIME of
  a HIP-graph capture; it is cleared only by the NEXT eligible capture on that context. The allocations come from
  the same legacy pool (GGML_HIP_NO_VMM=ON -> ggml_cuda_pool_leg, best-fit, never shrinks) as the cuBLAS F16
  dequant temps. A batch-1 capture needs ~250 entries (> the pool's free buffers), so it pins EVERY free pool
  buffer, including the ~105 / 178.5 MiB src0 dequant buffers. The next prefill (> 128 tokens -> Q8_0 cuBLAS path on
  gfx90a) finds the pool empty and hipMallocs a fresh ~0.29 GiB set. When the next capture clears the cache the
  old set returns and is immediately re-pinned. Net: +~0.29 GiB per "single-slot no-draft decode -> fresh prefill"
  transition, monotonic, NOT flushable by the pool's OOM retry (pinned buffers are not in the pool).
  Why it REPEATS instead of saturating: a faithful simulation of ggml_cuda_pool_leg (256-slot free array, best-fit,
  overflow -> hipFree) shows growth stops after one set when a capture pins < 256 buffers, and is LINEAR
  (~0.28 GiB/cycle) when it pins >= 256: the released pins overflow the 256-slot array, so each capture again drains
  every free buffer, the big ones included. The replay's capture pinned ~266 (254 new + ~12 existing) -> linear.
  Batch-1 single-slot decodes only arise in volume from per-request `speculative.n_max: 0` (Q38-T7 no-draft arms).
  Event model fit: replay 1 event -> +0.289; Q38-T7 #1 25 events -> +7.19 (0.288/event); Q38-T7 #2 3 events ->
  +0.894 (0.298/event); KVU-16b / B4g (no n_max 0) -> 0.

DESIGN (one scratch server per arm; production argv from logs/server_launches/8083.json, only --port,
--slot-save-path, -lv changed; v10 store binary; LD_PRELOAD hipMalloc shim; KFD 1 Hz sampler started BEFORE launch):
  ARM A  graphs ON (production):
    warm  2 drafted chat requests (T7-B corpus, ~24k + ~2.5k, max_tokens 64): first-touch allocations (EC-2 analogue)
    ctrl  Q38-T7 #1 phase A, the dflash2 arm ONLY: the 24 identical bodies (distinct prefill sizes, cache_prompt
          false, chat endpoint), no batch-1 capture.                                      PREDICTION ~0 GiB
    t7a   Q38-T7 #1 phase A BYTE-FAITHFUL: 24 x (dflash2, nodraft[speculative.n_max 0]) = 48 requests in run-#1
          order, same JSON bodies (sha256 recorded).                PREDICTION +0.29 GiB x events (~21 -> ~+6 GiB)
  + t7b2  Q38-T7 #2 sequence (2k, 16k: drafted 1500 / no-draft cached 1500 / needle / needle no-draft; fresh
          nonces).                                                    PREDICTION +0.29 x 3 = ~+0.9 GiB (optional)
  ARM B  GGML_CUDA_DISABLE_GRAPHS=1 (compiled-in env knob; no capture -> the mmvq cache is never used):
    warm, t7a                                                                              PREDICTION ~0 GiB
  Every request: own-KFD before/after (after a settle), shim byte range, body sha256 -> per-request attribution:
  pool_big (>= 1 MiB ggml_cuda_pool_leg allocs: the cuBLAS dequant set), mmvq_pin (pool allocs whose chain has
  ggml_cuda_mul_mat_vec_q: the graph-cache pins), other. Decode tok/s per arm = the price of the arm-B knob.
VERDICT (summary.md / summary.json): CONFIRMED | PARTIAL | NOT REPRODUCED, plus the KVU-16i term it implies.

Limits: hard ceiling 62.5 GiB (own KFD or card used; lib VramSampler) -> stop, graceful teardown, exit 3.
Soft ceiling 60.5 GiB (own KFD): stop the current phase, skip the rest of THAT arm (the answer is in by then).
Budget 25 min hard: optional phases are skipped first; arm B keeps its reserve.
Exit: 0 done, 2 refused (preflight), 3 hard-ceiling abort, 4 runtime error. Kills only its own PIDs (lib stop_own:
TERM -> KILL, ps -p verified). Never touches :8083. CPU side = HTTP client + 1 Hz samplers (no region lock needed);
the --mock self-test spawns a CPU stdlib mock server (run it under the region lock if the host is busy).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
GPUBLOCK = Path("/mnt/raid0/llm/tmp/gpu-block-27b-20261003")
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(GPUBLOCK))
import lib_kvu16h as K  # noqa: E402
import lib_gpublock as L  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)

T7_RUN1_SRC = GPUBLOCK / "q38_t7.py.orig-20261004"          # the exact source that produced run #1's bodies
T7_RUN1_CALLS = GPUBLOCK / "results/q38_t7/20261004T025247Z/calls.jsonl"
T7_RUN2_CALLS = GPUBLOCK / "results/q38_t7/20261004T040110Z/calls.jsonl"
MOCK = HERE / "dryrun" / "mock_server_chat.py"
EVENT_GIB = 0.29          # per pin->prefill transition, fitted on replay / T7 #1 / T7 #2 (0.289 / 0.288 / 0.298)
MIB = 1024 ** 2
T0 = time.time()
IDLE_S = 30.0
SETTLE_S = 1.5            # > 1 sampler period so the after-sample is post-request
LOAD_MIN, TEARDOWN_MIN, RESERVE_MIN = 1.5, 1.0, 0.5

# phase: (essential, estimate_min incl. idle, traffic cap s)
PHASES_A = {"warm": (True, 1.5, 180), "ctrl": (True, 2.5, 240), "t7a": (True, 5.5, 420), "t7b2": (False, 5.5, 420)}
PHASES_B = {"warm": (True, 1.5, 180), "t7a": (True, 6.0, 480)}
ARM_B_ENV = {"GGML_CUDA_DISABLE_GRAPHS": "1"}
PHASES_C = {"warm": (True, 1.5, 180), "t7a": (True, 6.0, 480)}
MOCK_C = HERE / "dryrun" / "mock_server_chat_c.py"   # arm-C-aware copy of the mock (KVU16H_MOCK_ARENA=1)
ARM_C_FIX_SHA = "656c9a66b6434c15bf15a8703da0890015867124"                          # experimental/mmvq-graph-cache-pool-20261004 (prefix)
LLAMA_REPO = Path("/mnt/raid0/llm/llama.cpp")          # read-only: git merge-base --is-ancestor
RECIPE_KEYS = ("GGML_HIP", "GGML_HIP_GRAPHS", "GGML_HIP_NO_VMM", "GGML_HIP_ROCWMMA_FATTN", "GPU_TARGETS",
               "GGML_NATIVE", "CMAKE_BUILD_TYPE", "GGML_CUDA_FA_ALL_QUANTS", "GGML_CUDA_GRAPHS")


class BinSpec:
    """Which llama-server an arm runs and how its residency/build is proven."""

    def __init__(self, bin_dir: Path, build_tokens: tuple[str, ...]) -> None:
        self.bin_dir = bin_dir                       # as given (may be a symlink)
        self.bin_real = Path(os.path.realpath(bin_dir))
        self.build_tokens = build_tokens

    def cmd(self, src: dict, argv: list[str]) -> list[str]:
        if self.bin_real == K.EXPECT_BIN_REAL:
            return src["prefix"] + argv
        return src["prefix"] + [str(self.bin_dir / "llama-server")] + argv[1:]

    def env(self, prod_env: dict) -> dict:
        if self.bin_real == K.EXPECT_BIN_REAL:
            return dict(prod_env)
        e = dict(prod_env)
        parts = [p for p in e.get("LD_LIBRARY_PATH", "").split(":") if p]
        parts = [str(self.bin_dir) if os.path.realpath(p) == str(K.EXPECT_BIN_REAL) else p for p in parts]
        if str(self.bin_dir) not in parts:
            parts.insert(0, str(self.bin_dir))
        e["LD_LIBRARY_PATH"] = ":".join(parts)
        return e


PROD_BIN = BinSpec(K.EXPECT_BIN_REAL, ("10303", "ffc1bac82"))


def arm_c_build_sha(bin_dir: Path) -> str | None:
    try:
        line = (bin_dir.resolve().parent / "BUILD.log").read_text().splitlines()[0]
        return line.split("src=", 1)[1].split()[0]
    except Exception:  # noqa: BLE001
        return None


def cmake_recipe(bin_dir: Path) -> dict:
    out = {}
    try:
        for ln in (Path(os.path.realpath(bin_dir)).parent / "CMakeCache.txt").read_text().splitlines():
            k, _, v = ln.partition("=")
            k = k.split(":", 1)[0]
            if k in RECIPE_KEYS:
                out[k] = v
    except OSError as exc:
        out["err"] = str(exc)
    return out


def arm_c_problems(bin_dir: Path) -> list[str]:
    import subprocess
    probs = []
    for f in ("llama-server", "libggml-hip.so", "libggml-base.so", "libllama.so"):
        if not (bin_dir / f).exists():
            probs.append(f"arm C: {bin_dir / f} missing")
    sha = arm_c_build_sha(bin_dir)
    if not sha:
        probs.append(f"arm C: no 'src=<sha>' in {bin_dir.resolve().parent / 'BUILD.log'}")
    else:
        r = subprocess.run(["git", "-C", str(LLAMA_REPO), "merge-base", "--is-ancestor", ARM_C_FIX_SHA, sha],
                           capture_output=True, text=True)
        if r.returncode != 0:
            probs.append(f"arm C: build source {sha[:12]} does not contain the fix {ARM_C_FIX_SHA} (rc {r.returncode})")
    rc, rp = cmake_recipe(bin_dir), cmake_recipe(K.EXPECT_BIN_REAL)
    if rc != rp:
        probs.append(f"arm C: CMakeCache recipe differs from the v10 store build: {rc} vs {rp}")
    return probs


def elapsed_min() -> float:
    return (time.time() - T0) / 60


def say(msg: str) -> None:
    print(f"[kvu16h-fu {time.strftime('%H:%M:%SZ', time.gmtime())} +{elapsed_min():.1f}m] {msg}", flush=True)


def load_t7_run1():
    """Import run #1's own source (constants + needles); its top level only defines things."""
    spec = importlib.util.spec_from_loader("q38_t7_run1", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(T7_RUN1_SRC)
    exec(compile(T7_RUN1_SRC.read_text(), str(T7_RUN1_SRC), "exec"), mod.__dict__)  # noqa: S102 - own file
    return mod


T7 = load_t7_run1()


def chat_body(content: str, **kw) -> dict:   # identical to q38_t7.chat_body (key order matters for the bytes)
    return {"messages": [{"role": "user", "content": content}], **kw}


def body_sha(body: dict, stream: bool) -> str:
    b = {**body, "stream": True} if stream else body           # what L.stream_request / L.http_json put on the wire
    return hashlib.sha256(json.dumps(b).encode()).hexdigest()


def t7_run1_rows() -> list[dict]:
    return [json.loads(x) for x in T7_RUN1_CALLS.read_text().splitlines() if x.strip()]


# ---------------------------------------------------------------- one arm
class Arm:
    def __init__(self, label: str, d: Path, port: int, sampler, marks, shim_log: Path | None, soft_b: int) -> None:
        self.label, self.dir, self.base = label, d, f"http://127.0.0.1:{port}"
        self.sampler, self.marks, self.shim_log, self.soft_b = sampler, marks, shim_log, soft_b
        self.req = K.Jsonl(d / "requests.jsonl")
        self.soft_hit = threading.Event()
        self.cap_stop = threading.Event()
        self.rows: list[dict] = []

    def own(self) -> int | None:
        return self.sampler.last.get("own_vram_b")

    def shim_off(self) -> int | None:
        try:
            return self.shim_log.stat().st_size if self.shim_log else None
        except OSError:
            return None

    def halted(self) -> bool:
        return self.sampler.abort.is_set() or self.soft_hit.is_set() or self.cap_stop.is_set()

    def send(self, phase: str, tag: str, body: dict, stream: bool, **meta) -> dict:
        k0, s0, t0 = self.own(), self.shim_off(), time.time()
        url = f"{self.base}/v1/chat/completions"
        if stream:
            r = L.stream_request(url, body, timeout=3600)
            http, err, timings, finish = r.get("http_status"), r.get("error"), r.get("timings"), r.get("finish")
        else:
            http, resp = L.http_json(url, body, timeout=1800)
            err = None if http == 200 else str(resp)[:300]
            timings = (resp or {}).get("timings") if isinstance(resp, dict) else None
            finish = (((resp or {}).get("choices") or [{}])[0] or {}).get("finish_reason") if isinstance(resp, dict) else None
        t1 = time.time()
        self.sampler.abort.wait(SETTLE_S)
        k1, s1 = self.own(), self.shim_off()
        row = {"arm": self.label, "phase": phase, "tag": tag, "t_send": round(t0, 3), "t_end": round(t1, 3),
               "wall_s": round(t1 - t0, 3), "stream": stream, "body_sha256": body_sha(body, stream),
               "nodraft": body.get("speculative.n_max") == 0, "max_tokens": body.get("max_tokens"),
               "http": http, "error": err, "finish": finish, "kfd_before_b": k0, "kfd_after_b": k1,
               "delta_gib": round((k1 - k0) / K.GIB, 3) if (k0 is not None and k1 is not None) else None,
               "shim_off": [s0, s1], **L.timing_summary(timings), **meta}
        self.rows.append(row)
        self.req.add(row)
        if k1 is not None and k1 > self.soft_b and not self.soft_hit.is_set():
            self.soft_hit.set()
            self.marks.mark(phase, "soft_ceiling", own_vram_b=k1)
            say(f"[{self.label}] soft ceiling: own KFD {k1 / K.GIB:.3f} GiB > {self.soft_b / K.GIB:.1f}: stopping this arm")
        say(f"[{self.label}] {phase}/{tag}: http {http} prompt_n {row['prompt_n']} pred {row['predicted_n']} "
            f"nodraft {row['nodraft']} dKFD {row['delta_gib']}")
        return row


def b_corpus(base: str) -> tuple[str, float]:
    text = (T7.PROBE_DIR / "contexts/C2/prompt.inline.txt").read_text() + "\n\n" + \
        (T7.PROBE_DIR / "contexts/C4/prompt.inline.txt").read_text()
    full = L.tokenize_count(base, text)
    return text, len(text) / max(1, full)


def phase_traffic(arm: Arm, phase: str) -> None:
    if phase == "warm":
        text, cpt = b_corpus(arm.base)
        for tok in (24000, 2500):
            if arm.halted():
                return
            cut = text[: int(min(len(text), tok * cpt))]
            arm.send(phase, f"warm{tok}", chat_body(L.nonce(f"kvu16h-fu warm {tok}") + cut + T7.TASK, max_tokens=64),
                     stream=True)
    elif phase in ("ctrl", "t7a"):
        prompts = json.loads(L.PROD_MIX.read_text())
        arms = {"dflash2": {}, "nodraft": {"speculative.n_max": 0}}
        if phase == "ctrl":
            arms = {"dflash2": {}}
        ref = {(r["id"], r["arm"]): r for r in t7_run1_rows() if r.get("phase") == "A"}
        for p in prompts:
            for a, extra in arms.items():
                if arm.halted():
                    return
                body = chat_body(p["prompt"], max_tokens=200, temperature=0.0, cache_prompt=False,
                                 chat_template_kwargs={"enable_thinking": False}, **extra)
                rr = ref.get((p["id"], a)) or {}
                arm.send(phase, f"{p['id']}|{a}", body, stream=False, t7_id=p["id"], t7_arm=a,
                         t7_run1_prompt_n=rr.get("prompt_n"), t7_run1_predicted_n=rr.get("predicted_n"))
    elif phase == "t7b2":   # Q38-T7 #2: phase B, targets 2000,16000, reps 1, gen 1500, gen_nodraft 1500
        text, cpt = b_corpus(arm.base)
        for target in (2000, 16000):
            cut = text[: int(min(len(text), target * cpt))]
            n1, n2, _facts = T7.needles(target)
            cut = T7.insert_needles(cut, n1, n2)
            prefix = L.nonce(f"q38t7 {target}") + cut
            seq = [("drafted", chat_body(prefix + T7.TASK, max_tokens=1500), True),
                   ("nodraft_cached", chat_body(prefix + T7.TASK, max_tokens=1500, **{"speculative.n_max": 0}), True),
                   ("needle", chat_body(prefix + T7.QUESTION, max_tokens=64, temperature=0.0,
                                        chat_template_kwargs={"enable_thinking": False}), False),
                   ("needle_nodraft", chat_body(prefix + T7.QUESTION, max_tokens=64, temperature=0.0,
                                                chat_template_kwargs={"enable_thinking": False},
                                                **{"speculative.n_max": 0}), False)]
            for tag, body, stream in seq:
                if arm.halted():
                    return
                arm.send(phase, f"{target}|{tag}", body, stream=stream)


def run_phase(arm: Arm, phase: str, cap_s: float) -> dict:
    own0 = arm.own()
    arm.marks.mark(phase, "begin", own_vram_b=own0)
    t = threading.Thread(target=phase_traffic, args=(arm, phase), daemon=True)
    t.start()
    t_start, capped = time.time(), False
    while t.is_alive():
        if arm.sampler.abort.is_set():
            break
        if time.time() - t_start > cap_s:
            capped = True       # the in-flight request finishes; no new one starts (halted())
            arm.cap_stop.set()
            break
        t.join(timeout=0.5)
    t.join(timeout=600)
    arm.marks.mark(phase, "traffic_end", capped=capped, aborted=arm.sampler.abort.is_set(), own_vram_b=arm.own())
    if not arm.sampler.abort.is_set():
        arm.sampler.abort.wait(IDLE_S)
    own1 = arm.own()
    arm.marks.mark(phase, "idle_end", own_vram_b=own1,
                   delta_gib=round((own1 - own0) / K.GIB, 3) if (own0 and own1) else None)
    arm.cap_stop.clear()        # a cap ends only its own phase
    return {"phase": phase, "capped": capped, "own_before_b": own0, "own_after_b": own1,
            "delta_gib": round((own1 - own0) / K.GIB, 3) if (own0 and own1) else None}


def run_arm(args, run_dir: Path, label: str, src: dict, prod_env: dict, phases: dict, extra_env: dict,
            budget_end_min: float, reserve_min: float, binspec: BinSpec = PROD_BIN, mock_env: dict | None = None) -> dict:
    d = run_dir / label
    d.mkdir(parents=True, exist_ok=True)
    (d / "slots").mkdir(exist_ok=True)
    argv, notes = K.build_argv(src, args.port, d / "slots", args.lv)
    shim_log = d / "shim.log" if args.shim else None
    env, env_rec = K.child_env(binspec.env(prod_env), {**extra_env, **((mock_env or {}) if args.mock else {})}, shim_log)
    cmd = binspec.cmd(src, argv)
    cmd_run = [sys.executable, "-B", str(MOCK_C), "--port", str(args.port)] if args.mock else cmd
    K.write_json(d / "launch.json", {"cmd": cmd, "mock_cmd": cmd_run if args.mock else None, "argv_notes": notes,
                                     "argv_source": src["source"], "env": env_rec, "shim": args.shim,
                                     "extra_env": extra_env, "bin_dir": str(binspec.bin_dir),
                                     "bin_real": str(binspec.bin_real), "build_tokens": binspec.build_tokens})
    say(f"[{label}] launch ({'MOCK ' if args.mock else ''}env {extra_env or '{}'}): {' '.join(cmd)}")
    sampler = K.VramSampler(d / "vram.jsonl", args.ceiling_gib).start()
    smi = K.SmiSampler(d / "smi.jsonl", 1.0).start()
    marks = K.Marks(d / "marks.jsonl", d / "server.log", shim_log)
    time.sleep(2)
    marks.mark("load", "pre_launch", card_used_b=sampler.last.get("card_used_b"))
    proc = K.start_own(cmd_run, d / "server.log", env)
    (d / "server.pid").write_text(str(proc.pid))
    sampler.own_pid = proc.pid
    marks.mark("load", "launched", pid=proc.pid)
    res: dict = {"label": label, "pid": proc.pid, "extra_env": extra_env, "phases": [], "skipped": [], "aborted": None}
    try:
        res["load_s"] = K.wait_healthy(f"http://127.0.0.1:{args.port}", proc, timeout=900, abort=sampler.abort)
        res["healthy"] = True
        maps = K.hip_dlopen_proof(proc.pid, binspec.bin_real)
        try:
            props = K.http_json(f"http://127.0.0.1:{args.port}/props", timeout=10)
        except Exception as exc:  # noqa: BLE001
            props = {"err": str(exc)}
        build = str(props.get("build_info", ""))
        envp = K.proc_environ(proc.pid)
        env_proof = {k: envp.get(k) for k in ("GGML_CUDA_DISABLE_GRAPHS", "LD_PRELOAD", "LD_LIBRARY_PATH")}
        K.write_json(d / "residency.json", {"maps": maps, "build_info": build, "env_proof": env_proof,
                                            "kfd_after_healthy_gib": round((sampler.last.get("own_vram_b") or 0) / K.GIB, 3)})
        marks.mark("load", "healthy", load_s=res["load_s"], build=build, hip_ok=maps.get("ok"),
                   shim_mapped=bool(maps.get("shim_mapped")), own_vram_b=sampler.last.get("own_vram_b"))
        if not args.mock:
            if not maps.get("ok") or not all(t in build for t in binspec.build_tokens):
                raise RuntimeError(f"residency/build proof failed: hip_ok={maps.get('ok')} build={build!r}")
            if args.shim and not maps.get("shim_mapped"):
                raise RuntimeError("shim requested but not mapped in the server")
            if (sampler.last.get("own_vram_b") or 0) < 40 * K.GIB:
                raise RuntimeError("server is not GPU-resident (KFD VRAM < 40 GiB after healthy)")
        for k, v in extra_env.items():
            if env_proof.get(k) != v and not args.mock:
                raise RuntimeError(f"arm env knob not in the server's environ: {k}={env_proof.get(k)!r}")
        sampler.abort.wait(IDLE_S)
        if sampler.abort.is_set():
            raise RuntimeError(f"VRAM ceiling abort: {sampler.abort_reason}")
        marks.mark("load", "idle_end", own_vram_b=sampler.last.get("own_vram_b"))
        arm = Arm(label, d, args.port, sampler, marks, shim_log, int(args.soft_ceiling_gib * K.GIB))
        for ph, (essential, est, cap) in phases.items():
            if sampler.abort.is_set() or arm.soft_hit.is_set():
                res["skipped"].append({"phase": ph, "why": "abort" if sampler.abort.is_set() else "soft ceiling"})
                continue
            left = budget_end_min - elapsed_min() - TEARDOWN_MIN - RESERVE_MIN - (0.0 if essential else reserve_min)
            if est > left:
                res["skipped"].append({"phase": ph, "why": "budget", "estimate_min": est, "left_min": round(left, 1)})
                marks.mark(ph, "skipped_budget", estimate_min=est, left_min=round(left, 1))
                continue
            res["phases"].append(run_phase(arm, ph, min(cap, max(60.0, left * 60 - IDLE_S))))
        res["soft_ceiling_hit"] = arm.soft_hit.is_set()
    except Exception as exc:  # noqa: BLE001
        res["error"] = f"{type(exc).__name__}: {exc}"[:600]
        say(f"[{label}] ERROR {res['error']}")
    finally:
        res["aborted"] = sampler.abort_reason
        marks.mark("teardown", "begin", own_vram_b=sampler.last.get("own_vram_b"))
        res["teardown"] = K.stop_own(proc, term_wait=120)
        marks.mark("teardown", "end", **{k: v for k, v in res["teardown"].items() if k != "at"})
        time.sleep(2)
        sampler.stop()
        smi.stop()
        res["peak_own_gib"] = round(sampler.peak_own_b / K.GIB, 3)
        K.write_json(d / "arm_result.json", res)
    return res


# ---------------------------------------------------------------- analysis
def parse_shim(path: Path, lo: int | None, hi: int | None) -> dict:
    """Classify hipMalloc/hipFree in [lo, hi) bytes of the shim log."""
    out = {"pool_big_n": 0, "pool_big_b": 0, "mmvq_pin_n": 0, "mmvq_pin_b": 0, "pool_other_n": 0, "pool_other_b": 0,
           "nonpool_b": 0, "free_n": 0, "pool_big_sizes_mib": [], "mmvq_arena_n": 0, "mmvq_arena_b": 0}
    if path is None or lo is None or hi is None or hi <= lo or not path.exists():
        return out
    with open(path, "rb") as fh:
        fh.seek(lo)
        blob = fh.read(hi - lo).decode(errors="replace")
    for ln in blob.splitlines():
        if ln.startswith("F "):
            out["free_n"] += 1
            continue
        if not ln.startswith("A "):
            continue
        head, _, chain = ln.partition(" | ")
        h = head.split()
        try:
            size = int(h[4])
        except (IndexError, ValueError):
            continue
        if "pool_leg" not in chain:
            out["nonpool_b"] += size
            if "mul_mat_vec_q" in chain:      # arm C: the private q8_1 arena (also counted in nonpool_b)
                out["mmvq_arena_n"] += 1
                out["mmvq_arena_b"] += size
        elif "mul_mat_vec_q" in chain:
            out["mmvq_pin_n"] += 1
            out["mmvq_pin_b"] += size
        elif size >= MIB:
            out["pool_big_n"] += 1
            out["pool_big_b"] += size
            out["pool_big_sizes_mib"].append(round(size / MIB, 2))
        else:
            out["pool_other_n"] += 1
            out["pool_other_b"] += size
    return out


def event_model(rows: list[dict]) -> list[dict]:
    """H1's event rule: a sequential no-draft request that decoded >= 3 tokens pins the pool (batch-1 capture
    needs 2 stable warm-up steps first); the next request with > 128 new prompt tokens (cuBLAS) is an EVENT."""
    pinned, out = False, []
    for r in rows:
        ev = bool(pinned and (r.get("prompt_n") or 0) > 128)
        if ev:
            pinned = False
        out.append({**r, "event": ev})
        if r.get("nodraft") and (r.get("predicted_n") or 0) >= 3:
            pinned = True
    return out


def analyze(run_dir: Path, arms: list[str]) -> dict:
    summ: dict = {"run": str(run_dir), "event_gib_model": EVENT_GIB, "arms": {}}
    for label in arms:
        d = run_dir / label
        if not (d / "requests.jsonl").exists():
            continue
        rows = [json.loads(x) for x in (d / "requests.jsonl").read_text().splitlines() if x.strip()]
        shim = d / "shim.log"
        rows = event_model(rows)
        for r in rows:
            r["shim"] = parse_shim(shim, *(r.get("shim_off") or [None, None]))
        res = json.loads((d / "arm_result.json").read_text()) if (d / "arm_result.json").exists() else {}
        A: dict = {"result": {k: res.get(k) for k in ("pid", "load_s", "aborted", "error", "skipped", "peak_own_gib",
                                                       "soft_ceiling_hit", "extra_env")}, "phases": {}}
        for ph in dict.fromkeys(r["phase"] for r in rows):
            pr = [r for r in rows if r["phase"] == ph]
            ev = [r for r in pr if r["event"]]
            k0 = next((r["kfd_before_b"] for r in pr if r.get("kfd_before_b") is not None), None)
            k1 = next((r["kfd_after_b"] for r in reversed(pr) if r.get("kfd_after_b") is not None), None)
            g = round((k1 - k0) / K.GIB, 3) if (k0 is not None and k1 is not None) else None
            ev_kfd = sum(r["delta_gib"] for r in ev if r.get("delta_gib") is not None)
            big_b = sum(r["shim"]["pool_big_b"] for r in pr)
            big_ev_b = sum(r["shim"]["pool_big_b"] for r in ev)
            nd = [r for r in pr if r.get("nodraft") and r.get("decode_tps")]
            dr = [r for r in pr if not r.get("nodraft") and r.get("decode_tps")]
            fid = [r for r in pr if r.get("t7_run1_prompt_n") is not None]
            A["phases"][ph] = {
                "n_requests": len(pr), "http_non200": sum(1 for r in pr if r.get("http") != 200),
                "kfd_growth_gib": g, "events": len(ev), "predicted_gib": round(len(ev) * EVENT_GIB, 3),
                "kfd_in_event_requests_gib": round(ev_kfd, 3),
                "kfd_per_event_gib": round(ev_kfd / len(ev), 3) if ev else None,
                "shim_pool_big_gib": round(big_b / K.GIB, 3),
                "shim_pool_big_in_events_frac": round(big_ev_b / big_b, 3) if big_b else None,
                "shim_mmvq_pins": sum(r["shim"]["mmvq_pin_n"] for r in pr),
                "shim_mmvq_pins_in_nodraft": sum(r["shim"]["mmvq_pin_n"] for r in pr if r.get("nodraft")),
                "shim_nonpool_gib": round(sum(r["shim"]["nonpool_b"] for r in pr) / K.GIB, 3),
                "shim_mmvq_arena_n": sum(r["shim"]["mmvq_arena_n"] for r in pr),
                "shim_mmvq_arena_mib": round(sum(r["shim"]["mmvq_arena_b"] for r in pr) / MIB, 2),
                "decode_tps_nodraft_median": median([r["decode_tps"] for r in nd]),
                "decode_tps_drafted_median": median([r["decode_tps"] for r in dr]),
                "t7_run1_fidelity": {"n": len(fid), "prompt_n_equal": sum(1 for r in fid if r.get("prompt_n") == r["t7_run1_prompt_n"]),
                                     "predicted_n_equal": sum(1 for r in fid if r.get("predicted_n") == r.get("t7_run1_predicted_n"))},
                "event_requests": [{"tag": r["tag"], "prompt_n": r.get("prompt_n"), "dKFD": r.get("delta_gib"),
                                    "pool_big_mib": r["shim"]["pool_big_sizes_mib"]} for r in ev][:40],
            }
        A["rows"] = [{k: r.get(k) for k in ("phase", "tag", "nodraft", "prompt_n", "predicted_n", "event", "delta_gib")}
                     | {"pool_big_mib": round(r["shim"]["pool_big_b"] / MIB, 1), "mmvq_pins": r["shim"]["mmvq_pin_n"]}
                     for r in rows]
        summ["arms"][label] = A
    summ["verdict"] = verdict(summ)
    if "armA" not in summ["arms"]:
        summ["verdict"]["verdict"] = "N/A (arm A not run)"
        summ["verdict"]["kvu16i_term"] = "H1 not re-tested in this run (arm A not run)"
    summ["verdict_c"] = verdict_c(summ, summ["verdict"])
    return summ


def median(xs: list) -> float | None:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else round((xs[m - 1] + xs[m]) / 2, 2)


def verdict_c(s: dict, base: dict) -> dict:
    """Arm C (fix build, graphs ON): t7a must stay flat although the H1 event rule fires, no pool pins by mmvq."""
    if "armC_fix" not in s["arms"]:
        return {"fix": "N/A (arm C not run)"}
    A = (s["arms"].get("armA") or {}).get("phases", {}).get("t7a") or {}
    C = s["arms"]["armC_fix"]["phases"].get("t7a") or {}
    use_shim = C.get("kfd_growth_gib") is None
    gC = C.get("shim_pool_big_gib") if use_shim else C.get("kfd_growth_gib")
    gA = base.get("t7a_growth_gib")
    ev = C.get("events") or 0
    checks = {
        "armC_t7a_has_events": ev >= 5,
        "armC_t7a_flat": None if gC is None else gC <= max(0.3, 0.25 * (gA or 0) if gA else 0.3),
        "armC_no_mmvq_pool_pins": None if C.get("shim_mmvq_pins") is None else C["shim_mmvq_pins"] == 0,
        "armC_arena_bounded": None if C.get("shim_mmvq_arena_mib") is None else C["shim_mmvq_arena_mib"] <= 64,
    }
    if C.get("n_requests") is None or not checks["armC_t7a_has_events"]:
        v = "N/A (arm C t7a did not exercise >= 5 H1 events)"
    elif all(c is not False for c in checks.values()):
        v = "HOLDS"
    else:
        v = "FAILS"
    ratio = lambda c, a: None if not (c and a) else round(c / a, 4)  # noqa: E731
    return {"fix": v, "armC_t7a_growth_gib": gC, "armC_t7a_events": ev, "armA_t7a_growth_gib": gA, "checks": checks,
            "decode_tps": {"nodraft_A": A.get("decode_tps_nodraft_median"), "nodraft_C": C.get("decode_tps_nodraft_median"),
                           "nodraft_C_over_A": ratio(C.get("decode_tps_nodraft_median"), A.get("decode_tps_nodraft_median")),
                           "drafted_A": A.get("decode_tps_drafted_median"), "drafted_C": C.get("decode_tps_drafted_median"),
                           "drafted_C_over_A": ratio(C.get("decode_tps_drafted_median"), A.get("decode_tps_drafted_median"))},
            "arena": {"n": C.get("shim_mmvq_arena_n"), "mib": C.get("shim_mmvq_arena_mib")}}


def verdict(s: dict) -> dict:
    A = (s["arms"].get("armA") or {}).get("phases", {})
    B = (s["arms"].get("armB_nographs") or {}).get("phases", {})
    t7a, ctrl, bt7a = A.get("t7a") or {}, A.get("ctrl") or {}, B.get("t7a") or {}
    use_shim = t7a.get("kfd_growth_gib") is None          # mock / no KFD: fall back to the shim's pool bytes
    gA = t7a.get("shim_pool_big_gib") if use_shim else t7a.get("kfd_growth_gib")
    gC = ctrl.get("shim_pool_big_gib") if use_shim else ctrl.get("kfd_growth_gib")
    gB = bt7a.get("shim_pool_big_gib") if use_shim else bt7a.get("kfd_growth_gib")
    ev, pred = t7a.get("events") or 0, t7a.get("predicted_gib") or 0.0
    checks = {
        "t7a_reproduces": bool(ev >= 5 and gA is not None and gA >= 0.5 * pred),
        "ctrl_flat": None if gC is None else gC <= 0.25,
        "armB_flat": None if gB is None else gB <= max(0.3, 0.25 * (gA or 0)),
        "shim_big_allocs_in_events": None if t7a.get("shim_pool_big_in_events_frac") is None
        else t7a["shim_pool_big_in_events_frac"] >= 0.7,
        "shim_pins_in_nodraft": None if not t7a.get("shim_mmvq_pins") else
        t7a["shim_mmvq_pins_in_nodraft"] >= 0.9 * t7a["shim_mmvq_pins"],
    }
    if not checks["t7a_reproduces"]:
        v = "NOT REPRODUCED"
        term = ("KVU-16i keeps the production figure: +8.08 GiB (51.69 -> 59.77, still rising) is UNEXPLAINED; "
                "do not use the 1.42 GiB replay term")
    elif all(c is True for c in checks.values()):
        v = "CONFIRMED"
        term = ("KVU-16i runtime term = 1.42 GiB (bounded warm-up) ONLY for traffic without single-slot no-draft "
                f"decodes; every 'speculative.n_max 0 decode -> fresh prefill' transition adds ~{(t7a.get('kfd_per_event_gib') or EVENT_GIB):.2f} GiB "
                "with no bound below OOM (pinned buffers are invisible to the pool's OOM flush). Gate: no per-request "
                "n_max 0 against :8083 (bench runners use scratch servers), or GGML_CUDA_DISABLE_GRAPHS=1 at the "
                "decode cost shown, or fix the cache on llama.cpp-experimental (dedicated exact-size pool / release "
                "at capture end)")
    else:
        v = "PARTIAL"
        term = ("growth reproduces under the T7 sequence but a control check failed; KVU-16i carries the observed "
                f"T7 slope ({(t7a.get('kfd_per_event_gib') or EVENT_GIB):.2f} GiB/event) on top of 1.42 until resolved")
    return {"verdict": v, "basis": "shim pool bytes (no KFD: mock)" if use_shim else "own-pid KFD",
            "t7a_growth_gib": gA, "t7a_events": ev, "t7a_predicted_gib": pred, "ctrl_growth_gib": gC,
            "armB_t7a_growth_gib": gB, "checks": checks, "kvu16i_term": term,
            "graphs_off_decode_cost": {"nodraft_tps_A": t7a.get("decode_tps_nodraft_median"),
                                       "nodraft_tps_B": bt7a.get("decode_tps_nodraft_median"),
                                       "drafted_tps_A": t7a.get("decode_tps_drafted_median"),
                                       "drafted_tps_B": bt7a.get("decode_tps_drafted_median")}}


def write_summary(run_dir: Path, s: dict) -> None:
    K.write_json(run_dir / "summary.json", s)
    v = s["verdict"]
    md = [f"# KVU-16h follow-up + arm C — pool pinning by the HIP-graph mmvq q8_1 cache, and its fix ({K.now_iso()})", "",
          f"- run `{run_dir}`", f"- **verdict: {v['verdict']}** (basis: {v['basis']})",
          f"- arm A t7a growth {v['t7a_growth_gib']} GiB over {v['t7a_events']} events "
          f"(model {v['t7a_predicted_gib']} GiB at {EVENT_GIB}/event); ctrl {v['ctrl_growth_gib']} GiB; "
          f"arm B (graphs off) t7a {v['armB_t7a_growth_gib']} GiB",
          f"- checks: {v['checks']}", f"- graphs-off decode cost (median tok/s): {v['graphs_off_decode_cost']}",
          f"- **KVU-16i**: {v['kvu16i_term']}",
          f"- **arm C (fix 656c9a66b, graphs ON): {s['verdict_c'].get('fix')}** — {s['verdict_c']}", ""]
    for label, A in s["arms"].items():
        md += [f"## {label}", "", f"- result: {A['result']}", "",
               "| phase | req | non-200 | KFD growth GiB | events | model GiB | KFD in events GiB | per event | shim pool_big GiB | big in events | mmvq pins (in nodraft) | nonpool GiB | tps nodraft / drafted | T7#1 fidelity prompt_n= / pred= | mmvq arena n / MiB |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for ph, p in A["phases"].items():
            f = p["t7_run1_fidelity"]
            md.append(f"| {ph} | {p['n_requests']} | {p['http_non200']} | {p['kfd_growth_gib']} | {p['events']} | "
                      f"{p['predicted_gib']} | {p['kfd_in_event_requests_gib']} | {p['kfd_per_event_gib']} | "
                      f"{p['shim_pool_big_gib']} | {p['shim_pool_big_in_events_frac']} | {p['shim_mmvq_pins']} "
                      f"({p['shim_mmvq_pins_in_nodraft']}) | {p['shim_nonpool_gib']} | {p['decode_tps_nodraft_median']} / "
                      f"{p['decode_tps_drafted_median']} | {f['prompt_n_equal']}/{f['n']} , {f['predicted_n_equal']}/{f['n']} | "
                      f"{p.get('shim_mmvq_arena_n')} / {p.get('shim_mmvq_arena_mib')} |")
        md += ["", "Per request (event = pin->prefill transition by the H1 rule):", "",
               "| phase | tag | nodraft | prompt_n | pred | event | dKFD GiB | pool_big MiB | mmvq pins |", "|---|---|---|---|---|---|---|---|---|"]
        for r in A["rows"]:
            md.append(f"| {r['phase']} | {r['tag']} | {r['nodraft']} | {r['prompt_n']} | {r['predicted_n']} | "
                      f"{'**EVENT**' if r['event'] else ''} | {r['delta_gib']} | {r['pool_big_mib']} | {r['mmvq_pins']} |")
        md.append("")
    (run_dir / "summary.md").write_text("\n".join(md) + "\n")


# ---------------------------------------------------------------- preflight / main
def preflight(args, src: dict) -> list[str]:
    probs = K.validate_prod_argv(src)
    if args.no_arm_a and args.arm_c_bin is None:
        probs.append("--no-arm-a without --arm-c-bin: nothing to compare")
    if args.arm_c_bin is not None and not args.mock:
        probs += arm_c_problems(args.arm_c_bin)
    if not T7_RUN1_SRC.exists() or not T7_RUN1_CALLS.exists() or not L.PROD_MIX.exists():
        probs.append("T7 run-#1 source/calls or the 24-prompt mix is missing")
    else:
        ids = [r["id"] for r in t7_run1_rows() if r.get("phase") == "A"][::2]
        if ids != [p["id"] for p in json.loads(L.PROD_MIX.read_text())]:
            probs.append("prompt mix order differs from T7 run #1 (not byte-faithful)")
    if args.port == 8083:
        probs.append("scratch port may not be 8083")
    if K.port_listening(args.port):
        probs.append(f"scratch port {args.port} in use")
    if args.mock:
        return probs
    if K.port_listening(8083):
        probs.append(":8083 is LISTENING: production must be stopped by the window owner first (two 27B do not fit)")
    f = K.foreign_gpu_procs()
    if f:
        probs.append("KFD processes hold VRAM: " + ", ".join(f"{p}:{v['name']}:{v['vram_b'] / K.GIB:.1f}GiB" for p, v in f.items()))
    used, _ = K.card_vram()
    if used is None or used > args.vram_free_max_gib * K.GIB:
        probs.append(f"card VRAM used {None if used is None else round(used / K.GIB, 2)} GiB > {args.vram_free_max_gib}")
    if args.shim and not (HERE / "shim" / "selftest.ok").exists():
        probs.append("shim self-test marker missing: run shim/build_shim.sh (the slot wrapper does)")
    if not os.environ.get("KVU16H_UNDER_CLAIM") and not args.no_claim:
        probs.append("not running under kvu16h_claim.py (mi210_0 device claim); use gpu_slot_kvu16h_followup_c.sh --execute")
    return probs


def plan_minutes(phases: dict, with_optional: bool) -> float:
    return LOAD_MIN + TEARDOWN_MIN + sum(e for ess, e, _ in phases.values() if ess or with_optional)


def dry_run(args, src: dict, penv: dict) -> int:
    print("=== DRY RUN kvu16h_followup_c.py (nothing started, nothing sent) ===")
    print(f"[argv source] {src['source']}; production invariants: "
          f"{'OK' if not K.validate_prod_argv(src) else 'DRIFT ' + '; '.join(K.validate_prod_argv(src))}")
    argv, notes = K.build_argv(src, args.port, args.results / "armA" / "slots", args.lv)
    print("  " + " ".join(src["prefix"] + argv))
    print(f"  changes: {'; '.join(notes)}")
    print(f"[env] {penv['source']}: {penv['env']}")
    print(f"[shim] {'ON' if args.shim else 'OFF'} {K.SHIM} exists {K.SHIM.exists()}; marker {(HERE / 'shim' / 'selftest.ok').exists()}")
    rows = t7_run1_rows()
    a_rows = [r for r in rows if r.get("phase") == "A"]
    evs = sum(r["event"] for r in event_model([{**r, "nodraft": r.get("arm") == "nodraft"} for r in a_rows]))
    print(f"[t7a source] {T7_RUN1_SRC.name} + {L.PROD_MIX}: {len(a_rows)} requests, H1 events in run #1's own "
          f"phase A = {evs} -> model +{evs * EVENT_GIB:.2f} GiB")
    print(f"[arm A] graphs ON  phases {list(PHASES_A)}: {plan_minutes(PHASES_A, False):.1f} min essential, "
          f"{plan_minutes(PHASES_A, True):.1f} with t7b2")
    print(f"[arm B] env {ARM_B_ENV} phases {list(PHASES_B)}: {plan_minutes(PHASES_B, True):.1f} min"
          f"{' (DISABLED --no-arm-b)' if args.no_arm_b else ''}")
    if args.arm_c_bin is not None:
        cs = arm_c_build_sha(args.arm_c_bin)
        bc = BinSpec(args.arm_c_bin, (cs[:9],) if cs else ("?",))
        print(f"[arm C] {args.arm_c_bin} -> {bc.bin_real}; build src {cs}; phases {list(PHASES_C)}: "
              f"{plan_minutes(PHASES_C, True):.1f} min")
        print("  " + " ".join(bc.cmd(src, argv)))
        print(f"  LD_LIBRARY_PATH {bc.env(penv['env']).get('LD_LIBRARY_PATH')}")
        print(f"  recipe C {cmake_recipe(args.arm_c_bin)}")
    tot = (0.0 if args.no_arm_a else plan_minutes(PHASES_A, False)) + (0.0 if args.no_arm_b else plan_minutes(PHASES_B, True)) \
        + (plan_minutes(PHASES_C, True) if args.arm_c_bin is not None else 0.0)
    print(f"[budget] {args.budget_min} min hard; essential plan {tot:.1f} min; t7b2 runs only if it fits with arm B's "
          f"reserve. Ceilings: hard {args.ceiling_gib} (own KFD or card) -> exit 3; soft {args.soft_ceiling_gib} "
          f"(own KFD) -> stop that arm")
    probs = preflight(args, src)
    print("[preflight now] " + ("would PASS" if not probs else "would REFUSE:"))
    for p in probs:
        print(f"  - {p}")
    return 0


def main() -> int:
    global IDLE_S, SETTLE_S
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--port", type=int, default=18083)
    ap.add_argument("--lv", type=int, default=4)
    ap.add_argument("--budget-min", type=float, default=35.0)
    ap.add_argument("--ceiling-gib", type=float, default=62.5)
    ap.add_argument("--soft-ceiling-gib", type=float, default=60.5)
    ap.add_argument("--vram-free-max-gib", type=float, default=2.0)
    ap.add_argument("--no-arm-b", action="store_true")
    ap.add_argument("--no-arm-a", action="store_true", help="skip arm A (arm C is then judged absolutely)")
    ap.add_argument("--arm-c-bin", type=Path, default=None,
                    help="bin dir of the fix build (e.g. /mnt/raid0/llm/kernels/builds/gpu-20261004-656c9a66b/bin)")
    ap.add_argument("--no-shim", dest="shim", action="store_false")
    ap.add_argument("--no-claim", action="store_true", help="debug only")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", action="store_true", help="CPU self-test against dryrun/mock_server_chat.py")
    ap.add_argument("--analyze-only", action="store_true", help="re-run the analysis on --results")
    args = ap.parse_args()
    if args.analyze_only:
        s = analyze(args.results, [p.name for p in sorted(args.results.iterdir()) if p.is_dir() and p.name.startswith("arm")])
        write_summary(args.results, s)
        print(json.dumps(s["verdict"], indent=1))
        return 0
    src, penv = K.source_argv(), K.source_env()
    if args.dry_run:
        return dry_run(args, src, penv)
    if args.mock:
        IDLE_S, SETTLE_S = 0.5, 0.05
    K.install_signal_handlers()
    probs = preflight(args, src)
    if probs:
        for p in probs:
            say(f"REFUSE: {p}")
        return 2
    run_dir = args.results
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"task": "KVU-16h follow-up", "started": K.now_iso(), "mock": args.mock, "argv_source": src["source"],
                "argv": src["prefix"] + src["argv"], "argv_sha256": src["sha256_raw"], "env": penv, "port": args.port,
                "budget_min": args.budget_min, "ceiling_gib": args.ceiling_gib, "soft_ceiling_gib": args.soft_ceiling_gib,
                "shim": args.shim, "event_gib_model": EVENT_GIB, "no_arm_a": args.no_arm_a, "no_arm_b": args.no_arm_b,
                "sources_sha256": {p.name: K.sha256_file(p) for p in [Path(__file__).resolve(), HERE / "lib_kvu16h.py",
                                   T7_RUN1_SRC, T7_RUN1_CALLS, L.PROD_MIX, Path(L.__file__), MOCK_C]}}
    K.write_json(run_dir / "run.json", manifest)
    rc = 0
    reserve_b = 0.0 if args.no_arm_b else plan_minutes(PHASES_B, True)
    reserve_c = 0.0 if args.arm_c_bin is None else plan_minutes(PHASES_C, True)
    manifest["arm_c"] = None if args.arm_c_bin is None else {
        "bin_dir": str(args.arm_c_bin), "bin_real": os.path.realpath(args.arm_c_bin),
        "build_src": arm_c_build_sha(args.arm_c_bin), "fix_sha": ARM_C_FIX_SHA, "recipe": cmake_recipe(args.arm_c_bin)}
    K.write_json(run_dir / "run.json", manifest)
    if not args.no_arm_a:
        # arm A reserves arm C only: C is the question this copy adds; B (diagnostic) runs only if budget is left
        a = run_arm(args, run_dir, "armA", src, penv["env"], PHASES_A, {}, args.budget_min, reserve_c)
        if a.get("aborted"):
            rc = 3
        elif a.get("error"):
            rc = 4
    if rc == 0 and args.arm_c_bin is not None:
        left = args.budget_min - elapsed_min()
        if left < plan_minutes(PHASES_C, True) - 0.5:
            manifest["armC"] = f"SKIPPED: {left:.1f} min left"
            say(manifest["armC"])
        else:
            cs = arm_c_build_sha(args.arm_c_bin) or "?"
            c = run_arm(args, run_dir, "armC_fix", src, penv["env"], PHASES_C, {}, args.budget_min, 0.0,
                        binspec=BinSpec(args.arm_c_bin, (cs[:9],)), mock_env={"KVU16H_MOCK_ARENA": "1"})
            rc = 3 if c.get("aborted") else (4 if c.get("error") else rc)
    if rc == 0 and not args.no_arm_b:
        left = args.budget_min - elapsed_min()
        if left < plan_minutes(PHASES_B, True) - 0.5:
            manifest["armB"] = f"SKIPPED: {left:.1f} min left"
            say(manifest["armB"])
        else:
            b = run_arm(args, run_dir, "armB_nographs", src, penv["env"], PHASES_B, ARM_B_ENV, args.budget_min, 0.0)
            rc = 3 if b.get("aborted") else (4 if b.get("error") else rc)
    manifest["ended"], manifest["elapsed_min"] = K.now_iso(), round(elapsed_min(), 1)
    K.write_json(run_dir / "run.json", manifest)
    try:
        s = analyze(run_dir, ["armA", "armC_fix", "armB_nographs"])
        write_summary(run_dir, s)
        say(f"verdict {s['verdict']['verdict']}: {s['verdict']['kvu16i_term']}")
        say(f"arm C fix: {s['verdict_c'].get('fix')}")
        say(f"summary: {run_dir / 'summary.md'}")
    except Exception as exc:  # noqa: BLE001
        say(f"analysis failed (re-run with --analyze-only --results {run_dir}): {exc}")
        rc = rc or 4
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
