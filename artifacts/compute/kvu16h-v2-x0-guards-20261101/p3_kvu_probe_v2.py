#!/usr/bin/env python3
"""P3v2: re-run of the P3 unified-KV decode probe against workspace-ec's FA masked-KV-block-skip build
(experimental/fa-maskskip-20261003, a0d0ae238, build 10310). Copy of p3_kvu_probe.py; the original
and its results/p3/ are untouched. Results go to results/p3v2/<arm>/.

Changes vs P3 (v1):
  * --bin-dir override (default unchanged = the v10 store bin). With an override every child runs
    under `env -u LD_LIBRARY_PATH ... LD_LIBRARY_PATH=<bin>:/opt/rocm/lib` (nothing inherited).
  * --arm on|off: on = GGML_CUDA_FA_MASK_SKIP unset (feature default ON; _MIN_KV unset = 4096);
    off = GGML_CUDA_FA_MASK_SKIP=0 (in-binary control, same .so files).
  * A1 shortened: L0_base -> park nb1 (prefill + save) / nb2, nb3 (restore of nb1's state) -> L3
    (~355k of 393216) -> erase -> L0_after (ABA). No L1/L2 measurement. Per level drafted, no-draft,
    drafted, no-draft (2 reps each), 512 tok, temp 0, decode-only. Fill is computed from /slots PLUS
    the restore responses' n_restored (v1 showed /slots reports 0 n_prompt_tokens for restored slots).
  * A0 skipped (answered by v1).
  * B: llama-batched-bench -kvu vs -no-kvu, npl 4, -npp 16384 (direct v1 comparison) plus the largest
    of 65536/32768 that fits the remaining budget (estimate scaled from v1's measured 226 s @16384 by
    (npp/16384)^1.5); --b-npp-list fixes the list (the wrapper passes arm1's choice to arm2).
  * text_sha (sha256 of the streamed text) per request: on/off outputs should be bit-identical.

Usage: p3_kvu_probe_v2.py --arm on|off [--bin-dir DIR] [--phase all|a1|b] [--port 18084]
                          [--park-mode restore|prefill] [--budget-min 34] [--b-npp-list 16384,32768]
                          [--keep-slot-file] [--dry-run]
       p3_kvu_probe_v2.py --phase report          (arm1 vs arm2 vs v1 -> results/p3v2/report.md)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import x0_common_v2 as C  # noqa: E402  (own-PID lifecycle, VRAM sampler, HIP proof; set_bin override)
import x0_shape_b_v2 as SB  # noqa: E402  (argv parsing/_set, stream_chat(+text_sha), summarize)

P3V1 = C.RESULTS / "p3"
P3V2 = C.RESULTS / "p3v2"
ARMS = {"on": "arm1_maskskip_on", "off": "arm2_maskskip_off"}
OUT = P3V2  # per-arm dir, set in main()
LOGS = OUT / "logs"
SLOTDIR = P3V2 / "slots"
ARGV_FILE = Path("/mnt/raid0/llm/tmp/ds41-c95/X0_ARGV_8083.txt")
CTX = Path("/mnt/raid0/llm/tmp/ds41-c95/contexts")
POOL = 393216
MEAS_TOK, NB_TOK, GEN = 57000, 100000, 512
CPT_EST = 2.9312
TEMP0 = {"temperature": 0.0, "top_k": 1, "top_p": 1.0}
NODRAFT = {"speculative.n_max": 0}
FAIL_PATTERNS = ["failed to find a memory slot", "context size has been exceeded",
                 "failed to find free space in the KV cache", "exceeds the available context size",
                 "purging slot", "Unable to restore slot"]
B_V1_WALL_S, B_V1_NPP = 226.3, 16384  # v1 measured: kvu 124.3 s + nokvu 102.0 s, incl. loads
EXPECT = {"L3_drafted_min": 33.0, "L3_nodraft_min": 19.0, "b_kvu_vs_nokvu_tg_min_pct": -5.0}
V1_REF = {"L3_drafted": 15.37, "L3_nodraft": 8.257, "b_kvu_vs_nokvu_tg_pct": -15.23}
ARM = "on"
T0 = time.time()


def say(msg: str) -> None:
    print(f"[p3v2 {ARM} {time.strftime('%H:%M:%SZ', time.gmtime())} +{(time.time() - T0) / 60:.1f}m] {msg}", flush=True)


def elapsed_min() -> float:
    return (time.time() - T0) / 60


# ------------------------------------------------------------------ env / launch prefix
def arm_env() -> tuple[list[str], dict]:
    """`env` prefix (env exec's, so the captured PID stays the server's) + the overrides it applies."""
    unset = ["LD_LIBRARY_PATH"] + (["GGML_CUDA_FA_MASK_SKIP", "GGML_CUDA_FA_MASK_SKIP_MIN_KV"] if ARM == "on"
                                   else ["GGML_CUDA_FA_MASK_SKIP_MIN_KV"])
    sets = {"LD_LIBRARY_PATH": C.ld_path(), **SB.STACK_ENV}
    if ARM == "off":
        sets["GGML_CUDA_FA_MASK_SKIP"] = "0"
    pre = ["env"] + [x for u in unset for x in ("-u", u)] + [f"{k}={v}" for k, v in sets.items()]
    return pre, {"unset": unset, "set": sets}


def launch(argv: list[str]) -> list[str]:
    return arm_env()[0] + SB.PREFIX + argv


def set_env() -> None:
    """Mirror the prefix in our own env (gpu_env() copies it; belt and braces)."""
    _, ov = arm_env()
    for u in ov["unset"]:
        os.environ.pop(u, None)
    os.environ.update(ov["set"])
    os.environ.pop("LLAMA_KV_CACHE_DEBUG", None)


# ------------------------------------------------------------------ argv
def server_argv(port: int) -> tuple[list[str], list[str]]:
    src = SB.read_argv(ARGV_FILE)
    a = [str(C.BIN / "llama-server")] + src[1:]
    notes = [] if src[0] == a[0] else [f"binary {src[0]} -> {a[0]}"]
    for names, val in ((("--host",), "127.0.0.1"), (("--port",), str(port)),
                       (("--slot-save-path",), str(SLOTDIR))):
        before = list(a)
        a = SB._set(a, names, val)
        if a != before:
            notes.append(f"{names[0]} -> {val}")
    a += ["--metrics", "--no-cache-idle-slots"]
    notes += ["+ --metrics", "+ --no-cache-idle-slots (keep idle neighbours resident)"]
    return a, notes


def bench_argv(kvu: bool, npps: list[int], ntg: int, npl: int) -> list[str]:
    ctx = int(math.ceil(npl * (max(npps) + ntg) / 1024) * 1024 + 1024)
    return [str(C.BIN / "llama-batched-bench"), "-m", str(C.MODELS["q8"]), "-c", str(ctx), "-b", "2048",
            "-ub", "2048", "-t", "8", "-ngl", "99", "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0", "--no-mmap",
            "-dev", "ROCm0", "-kvu" if kvu else "-no-kvu", "-npp", ",".join(map(str, npps)), "-ntg", str(ntg),
            "-npl", str(npl), "--output-format", "jsonl"]


# ------------------------------------------------------------------ prompts / HTTP (as v1)
def texts() -> tuple[str, str]:
    meas = (CTX / "C2/prompt.inline.txt").read_text() + "\n\n" + (CTX / "C4/prompt.inline.txt").read_text()
    pool = "\n\n".join((CTX / f"{c}/prompt.inline.txt").read_text() for c in ("C1", "C3", "C5", "C6", "C7"))
    return meas, pool


def nb_text(pool: str, k: int, nchars: int, nonce: str) -> str:
    off = (k - 1) * (len(pool) // 3)
    body = (pool[off:] + "\n\n" + pool)[:nchars]
    return f"[p3 neighbour {k} {nonce}]\n" + body + SB.TASK


def slots(base: str) -> list[dict]:
    return C.http_json(base + "/slots", timeout=30)


def resident(base: str) -> dict:
    s = slots(base)
    per = {x["id"]: int(x.get("n_prompt_tokens") or 0) for x in s}
    return {"per_slot": per, "sum": sum(per.values()), "busy": [x["id"] for x in s if x.get("is_processing")],
            "frac_pool": round(sum(per.values()) / POOL, 4)}


def slot_action(base: str, sid: int, action: str, filename: str | None = None) -> dict:
    body = {"filename": filename} if filename else {}
    return C.http_json(f"{base}/slots/{sid}?action={action}", body, timeout=600)


def metrics(base: str) -> dict:
    try:
        with urllib.request.urlopen(base + "/metrics", timeout=30) as r:
            txt = r.read().decode()
        return {ln.split()[0]: float(ln.split()[1]) for ln in txt.splitlines() if ln.startswith("llamacpp:")}
    except Exception as exc:  # noqa: BLE001
        return {"err": str(exc)[:200]}


class SlotPoller:
    def __init__(self, base: str, period: float = 2.0):
        self.base, self.period, self.samples = base, period, []
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            try:
                r = resident(self.base)
                r["t"] = round(time.time(), 2)
                self.samples.append(r)
            except Exception as exc:  # noqa: BLE001
                self.samples.append({"t": round(time.time(), 2), "err": str(exc)[:120]})
            self._stop.wait(self.period)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *_a):
        self._stop.set()
        self._t.join(timeout=30)

    def summary(self) -> dict:
        ok = [s for s in self.samples if "sum" in s]
        during = [s for s in ok if s["busy"]] or ok
        sums = [s["sum"] for s in during]
        return {"n_samples": len(ok), "n_during_busy": len([s for s in ok if s["busy"]]),
                "resident_min": min(sums) if sums else None, "resident_max": max(sums) if sums else None,
                "per_slot_at_max": max(during, key=lambda s: s["sum"])["per_slot"] if during else None}


def chat(base: str, msg: str, slot: int, max_tokens: int, extra: dict | None = None) -> dict:
    body = {"messages": [{"role": "user", "content": msg}], "max_tokens": max_tokens, "id_slot": slot,
            **TEMP0, **(extra or {})}
    return SB.summarize(SB.stream_chat(base, body))


def log_scan(path: Path) -> dict:
    try:
        txt = path.read_text(errors="replace")
    except OSError as exc:
        return {"err": str(exc)}
    out = {p: txt.count(p) for p in FAIL_PATTERNS}
    out["saving_idle_slot_lines"] = txt.count("saving idle slot to prompt cache")
    return out


# ------------------------------------------------------------------ server lifecycle wrapper
class Server:
    def __init__(self, name: str, port: int):
        self.name, self.port = name, port
        self.argv, self.notes = server_argv(port)
        self.base = f"http://127.0.0.1:{port}"
        self.log = LOGS / f"{name}.server.log"
        self.proc = None
        self.sampler = None
        self.rec: dict = {"argv": launch(self.argv), "argv_transforms": self.notes, "env": arm_env()[1],
                          "bin_dir": str(C.BIN), "bin_overridden": C.BIN_OVERRIDDEN}

    def start(self):
        set_env()
        self.rec["vram_before"] = C.vram_now()
        self.sampler = C.VramSampler(LOGS / f"{self.name}.vram.jsonl").start()
        self.proc = C.start_own(launch(self.argv), self.log)
        self.rec["pid"] = self.proc.pid
        self.rec["load_s"] = C.wait_healthy(self.base, self.proc, timeout=900)
        self.rec["hip_dlopen_proof"] = C.hip_dlopen_proof(self.proc.pid)
        try:
            env = Path(f"/proc/{self.proc.pid}/environ").read_bytes().split(b"\0")
            pairs = (e.decode(errors="replace").split("=", 1) for e in env if b"=" in e)
            self.rec["live_env"] = {k: v for k, v in pairs if k in
                                    ("LD_LIBRARY_PATH", "GGML_CUDA_FA_MASK_SKIP", "GGML_CUDA_FA_MASK_SKIP_MIN_KV")}
        except OSError as exc:
            self.rec["live_env"] = {"err": str(exc)}
        props = C.http_json(self.base + "/props")
        self.rec["build_info"] = props.get("build_info")
        s = slots(self.base)
        self.rec["n_slots"], self.rec["n_ctx_slot"] = len(s), min(x.get("n_ctx", 0) for x in s)
        say(f"{self.name}: healthy in {self.rec['load_s']} s, pid {self.proc.pid}, build {self.rec['build_info']}, "
            f"slots {self.rec['n_slots']} x n_ctx {self.rec['n_ctx_slot']}, "
            f"hip-proof {self.rec['hip_dlopen_proof'].get('ok')}, live env {self.rec['live_env']}")

    def stop(self):
        if self.sampler:
            self.sampler.stop()
        if self.proc is not None:
            self.rec["teardown"] = C.stop_own(self.proc, term_wait=180)
            self.proc = None
        if self.sampler:
            self.rec["vram"] = self.sampler.summary(self.rec.get("pid"), self.rec["vram_before"].get("used_b"))
        self.rec["log_scan"] = log_scan(self.log)
        free = subprocess.run(["ss", "-ltnH", f"sport = :{self.port}"], capture_output=True, text=True).stdout.strip()
        self.rec["port_free_after"] = not free


# ------------------------------------------------------------------ phase A1
def measure_level(srv: Server, P: str, p_tok: int, level: str, fill: int, rows: list, out: Path, rec: dict) -> None:
    raise RuntimeError("KVU-16h: A1 requires separate drafted and no-draft servers")
    for i, (variant, extra) in enumerate((("drafted", None), ("nodraft", NODRAFT),
                                          ("drafted", None), ("nodraft", NODRAFT))):
        with SlotPoller(srv.base) as poll:
            r = chat(srv.base, P, 0, GEN, extra)
        row = {"level": level, "fill_tokens": fill, "variant": variant, "rep": i // 2 + 1, **r,
               "kv_resident": poll.summary()}
        row["decode_only"] = (r.get("prompt_n") or 0) < 64 and (r.get("cache_n") or 0) > 0.95 * p_tok
        rows.append(row)
        say(f"A1 {level} (fill {fill} = {fill / POOL:.3f} pool) {variant} r{row['rep']}: decode {r['decode_tps']} "
            f"tok/s acc {r['draft_acc']} prompt {r['prompt_n']} (cache {r['cache_n']}) sha {r['text_sha']} "
            f"decode_only={row['decode_only']}")
        C.write_json(out, {**rec, "status": "partial"})


def park(srv: Server, k: int, pool: str, cpt: float, nonce: str, mode: str, rec: dict) -> dict:
    fname = "p3v2-nb1.bin"
    if k == 1 or mode == "prefill":
        msg = nb_text(pool, k, int(NB_TOK * cpt), nonce)
        with SlotPoller(srv.base, period=5) as poll:
            r = chat(srv.base, msg, k, 1)
        ev = {"nb": k, "how": "prefill", **{x: r[x] for x in ("prompt_n", "cache_n", "prefill_tps", "ttft_s")},
              "kv_resident": poll.summary()}
        if k == 1 and mode == "restore":
            try:
                ev["save"] = slot_action(srv.base, 1, "save", fname)
            except Exception as exc:  # noqa: BLE001
                ev["save_error"] = f"{type(exc).__name__}: {exc}"[:300]
                rec["park_mode_effective"] = "prefill (save failed)"
        return ev
    if rec.get("park_mode_effective", "").startswith("prefill"):
        return park(srv, k, pool, cpt, nonce, "prefill", rec)
    try:
        res = slot_action(srv.base, k, "restore", fname)
        return {"nb": k, "how": "restore(nb1 state)", "restore": res, "n_restored": res.get("n_restored")}
    except Exception as exc:  # noqa: BLE001
        say(f"A1 restore into slot {k} failed ({exc}); falling back to prefill")
        rec["park_mode_effective"] = f"prefill (restore failed at nb{k})"
        ev = park(srv, k, pool, cpt, nonce, "prefill", rec)
        ev["restore_error"] = f"{type(exc).__name__}: {exc}"[:300]
        return ev


def fill_tokens(res: dict, restored: dict) -> int:
    """/slots tokens, with restored slots (which /slots reports as 0) counted from n_restored."""
    return sum(max(res["per_slot"].get(k, 0), restored.get(k, 0)) for k in set(res["per_slot"]) | set(restored))


def phase_a1(a) -> int:
    raise RuntimeError("KVU-16h: A1 requires separate drafted and no-draft servers")
    out = OUT / "a1.json"
    nonce = uuid.uuid4().hex[:12]
    srv = Server("a1", a.port)
    rec = {"schema": "p3v2.a1.v1", "arm": ARM, "started_at": C.now(), "nonce": nonce, "park_mode": a.park_mode,
           "park_mode_effective": a.park_mode, "pool_cells": POOL, "rows": [], "parks": [], "residency": []}
    rc = 1
    restored: dict[int, int] = {}
    try:
        srv.start()
        rec["server"] = srv.rec
        rec["warmup"] = chat(srv.base, "Say hello.", 0, 64)
        meas, pool = texts()
        cpt_m = len(meas) / len(C.http_json(srv.base + "/tokenize", {"content": meas}, timeout=300)["tokens"])
        cpt_p = len(pool) / len(C.http_json(srv.base + "/tokenize", {"content": pool}, timeout=300)["tokens"])
        # fixed tag (not the nonce) so arm on/off see byte-identical P -> text_sha comparable across arms
        P = "[p3v2 meas fixed]\n" + meas[: int(MEAS_TOK * cpt_m)] + SB.TASK
        rec["cpt_meas"], rec["cpt_pool"] = round(cpt_m, 4), round(cpt_p, 4)
        rec["prime"] = chat(srv.base, P, 0, GEN)
        p_tok = rec["prime"]["prompt_n"] + (rec["prime"]["cache_n"] or 0)
        rec["p_tokens"] = p_tok
        say(f"A1 prime: P = {p_tok} tok, prefill {rec['prime']['prefill_tps']} tok/s, decode {rec['prime']['decode_tps']}")
        res = resident(srv.base)
        rec["residency"].append({"at": "L0", **res, "metrics": metrics(srv.base)})
        measure_level(srv, P, p_tok, "L0_base", fill_tokens(res, restored), rec["rows"], out, rec)
        for k in (1, 2, 3):
            ev = park(srv, k, pool, cpt_p, nonce, a.park_mode, rec)
            rec["parks"].append(ev)
            if ev.get("n_restored"):
                restored[k] = int(ev["n_restored"])
            res = resident(srv.base)
            fill = fill_tokens(res, restored)
            rec["residency"].append({"at": f"park{k}", **res, "fill_tokens": fill})
            have = max(res["per_slot"].get(k, 0), restored.get(k, 0))
            say(f"A1 parked nb{k} ({ev['how']}): /slots {res['per_slot']} restored {restored} -> fill {fill} "
                f"= {fill / POOL:.3f} of pool")
            if have < 0.9 * NB_TOK:
                say(f"A1 WARNING: slot {k} holds only {have} tokens")
            if res["per_slot"].get(0, 0) < 0.95 * p_tok:
                say("A1 WARNING: slot 0 lost P (measurement would re-prefill)")
        res = resident(srv.base)
        fill = fill_tokens(res, restored)
        rec["residency"].append({"at": "L3", **res, "fill_tokens": fill, "metrics": metrics(srv.base)})
        measure_level(srv, P, p_tok, "L3", fill, rec["rows"], out, rec)
        for k in (1, 2, 3):
            rec.setdefault("erase", []).append(slot_action(srv.base, k, "erase"))
        restored.clear()
        res = resident(srv.base)
        rec["residency"].append({"at": "L0_after", **res, "metrics": metrics(srv.base)})
        measure_level(srv, P, p_tok, "L0_after", fill_tokens(res, restored), rec["rows"], out, rec)
        rec["status"] = "ok"
        rc = 0
    except Exception as exc:  # noqa: BLE001
        rec["status"] = "failed"
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["traceback"] = traceback.format_exc()[-3000:]
        say(f"A1 FAILED: {rec['error']}")
    finally:
        srv.stop()
        rec["server"] = srv.rec
        rec["finished_at"] = C.now()
        C.write_json(out, rec)
    return rc


# ------------------------------------------------------------------ phase B
def b_est_min(npps: list[int]) -> float:
    return sum(B_V1_WALL_S * (n / B_V1_NPP) ** 1.5 for n in npps) / 60


def b_plan(a) -> tuple[list[int], str]:
    if a.b_npp_list:
        return [int(x) for x in a.b_npp_list.split(",")], "fixed (--b-npp-list)"
    remaining = a.budget_min - elapsed_min()
    for top in (65536, 32768):
        if b_est_min([B_V1_NPP, top]) <= remaining:
            return [B_V1_NPP, top], f"guard: est {b_est_min([B_V1_NPP, top]):.1f} min <= remaining {remaining:.1f}"
    if b_est_min([B_V1_NPP]) <= remaining + 2:
        return [B_V1_NPP], f"guard: only {B_V1_NPP} fits (remaining {remaining:.1f} min)"
    return [], f"guard: skip (remaining {remaining:.1f} min)"


def run_bench(name: str, argv: list[str], timeout_s: float) -> dict:
    set_env()
    log = LOGS / f"b.{name}.log"
    rec = {"argv": launch(argv), "env": arm_env()[1], "vram_before": C.vram_now()}
    sampler = C.VramSampler(LOGS / f"b.{name}.vram.jsonl").start()
    proc = C.start_own(launch(argv), log)
    rec["pid"] = proc.pid
    t0 = time.time()
    try:
        while proc.poll() is None and time.time() - t0 < timeout_s:
            if "hip_dlopen_proof" not in rec and time.time() - t0 > 20:
                rec["hip_dlopen_proof"] = C.hip_dlopen_proof(proc.pid)
            time.sleep(2)
        rec["timed_out"] = proc.poll() is None
    finally:
        sampler.stop()
        rec["teardown"] = C.stop_own(proc, term_wait=60)
        rec["vram"] = sampler.summary(rec["pid"], rec["vram_before"].get("used_b"))
    rec["wall_s"] = round(time.time() - t0, 1)
    rows = []
    for ln in log.read_text(errors="replace").splitlines():
        i = ln.find('{"n_kv_max"')
        if i >= 0:
            try:
                rows.append(json.loads(ln[i:]))
            except ValueError:
                pass
    rec["rows"] = rows
    rec["log_scan"] = log_scan(log)
    return rec


def phase_b(a) -> int:
    out = OUT / "b.json"
    npps, why = b_plan(a)
    rec = {"schema": "p3v2.b.v1", "arm": ARM, "started_at": C.now(), "elapsed_min_at_start": round(elapsed_min(), 1),
           "npp_list": npps, "plan_reason": why, "runs": {}}
    if not npps:
        rec["status"] = "skipped (budget guard)"
        C.write_json(out, rec)
        say(f"B skipped: {why}")
        return 0
    rc = 0
    for name, kvu in (("kvu", True), ("nokvu", False)):
        say(f"B {name}: npp {npps} ntg 64 npl 4 ({why})")
        r = run_bench(name, bench_argv(kvu, npps, 64, 4), timeout_s=25 * 60)
        rec["runs"][name] = r
        for row in r["rows"]:
            say(f"B {name}: npp {row['pp']} pl {row['pl']} n_kv {row['n_kv']} S_PP {row['speed_pp']:.1f} "
                f"S_TG {row['speed_tg']:.2f}")
        if len(r["rows"]) < len(npps):
            rc = 1
        C.write_json(out, rec)
    rec["status"] = "ok" if rc == 0 else "failed"
    C.write_json(out, rec)
    return rc


# ------------------------------------------------------------------ report (arm1 vs arm2 vs v1)
def mean(xs):
    xs = [x for x in xs if x]
    return round(sum(xs) / len(xs), 3) if xs else None


def a1_summary(path: Path) -> dict | None:
    if not path.exists():
        return None
    a1 = json.loads(path.read_text())
    rows = a1.get("rows", [])
    lv3 = next((lv for lv in dict.fromkeys(r["level"] for r in rows) if lv.startswith("L3")), None)
    t = {}
    for key, lv in (("L0_base", "L0_base"), ("L3", lv3), ("L0_after", "L0_after")):
        for var in ("drafted", "nodraft"):
            rr = [r for r in rows if r["level"] == lv and r["variant"] == var]
            t[f"{key}.{var}"] = mean([r["decode_tps"] for r in rr])
            t[f"{key}.{var}.acc"] = mean([r["draft_acc"] for r in rr])
            t[f"{key}.{var}.sha"] = sorted({r.get("text_sha") for r in rr if r.get("text_sha")})
    srv = a1.get("server") or {}
    out = {"status": a1.get("status"), "tab": t, "p_tokens": a1.get("p_tokens"),
           "fill_L3": next((r.get("fill_tokens") for r in rows if r["level"] == lv3), None),
           "build": srv.get("build_info"), "live_env": srv.get("live_env"),
           "hip_proof": (srv.get("hip_dlopen_proof") or {}).get("ok"), "log_scan": srv.get("log_scan"),
           "vram_own_peak_gib": (srv.get("vram") or {}).get("own_pid_peak_vram_gib")}
    for v in ("drafted", "nodraft"):
        base = mean([t.get(f"L0_base.{v}"), t.get(f"L0_after.{v}")])
        x = t.get(f"L3.{v}")
        out[f"base.{v}"] = base
        out[f"loss_L3.{v}"] = round((base - x) / base * 100, 2) if base and x else None
        b0, b1 = t.get(f"L0_base.{v}"), t.get(f"L0_after.{v}")
        out[f"aba.{v}"] = round((b1 - b0) / b0 * 100, 2) if b0 and b1 else None
    return out


def b_summary(path: Path) -> dict | None:
    if not path.exists():
        return None
    b = json.loads(path.read_text())
    res = {"status": b.get("status"), "rows": {}}
    for name, r in (b.get("runs") or {}).items():
        for row in r.get("rows", []):
            res["rows"][f"{name}.{row['pp']}"] = {"s_pp": row["speed_pp"], "s_tg": row["speed_tg"], "n_kv": row["n_kv"]}
    for npp in sorted({int(k.split(".")[1]) for k in res["rows"]}):
        k, n = res["rows"].get(f"kvu.{npp}"), res["rows"].get(f"nokvu.{npp}")
        if k and n:
            res[f"tg_pct.{npp}"] = round((k["s_tg"] - n["s_tg"]) / n["s_tg"] * 100, 2)
            res[f"pp_pct.{npp}"] = round((k["s_pp"] - n["s_pp"]) / n["s_pp"] * 100, 2)
    return res


def fmt(x, suf=""):
    if isinstance(x, float):
        x = round(x, 2)
    return "-" if x is None else f"{x}{suf}"


def phase_report(_a) -> int:
    cols = [("v1 (v10 ffc1bac82)", a1_summary(P3V1 / "a1.json"), b_summary(P3V1 / "b.json")),
            ("arm1 maskskip ON", a1_summary(P3V2 / ARMS["on"] / "a1.json"), b_summary(P3V2 / ARMS["on"] / "b.json")),
            ("arm2 maskskip OFF (=0)", a1_summary(P3V2 / ARMS["off"] / "a1.json"),
             b_summary(P3V2 / ARMS["off"] / "b.json"))]
    A = [c[1] or {} for c in cols]
    B = [c[2] or {} for c in cols]
    hdr = "| metric | " + " | ".join(c[0] for c in cols) + " | expectation (workspace-ec) |"
    sep = "|---" * (len(cols) + 2) + "|"
    L = ["# P3v2: unified-KV decode vs occupied pool, FA masked-block skip (a0d0ae238, build 10310) vs v1", "",
         "MI210, Qwen3.8-27B Q8_0 + DFlash2 (n-max 7), :8083 argv on a scratch port + --no-cache-idle-slots; "
         "L3 = P (~57k, slot 0) + 3 parked ~100k neighbours (~355k of 393216). arm2 = same binary with "
         "GGML_CUDA_FA_MASK_SKIP=0. v1 = results/p3 (its L3 row is named L3_156k because /slots under-reports "
         "restored slots; the fill was ~355k).", "",
         "## A1 decode (tok/s, mean of 2 reps; decode-only)", "", hdr, sep]

    def row(label, vals, exp=""):
        L.append(f"| {label} | " + " | ".join(vals) + f" | {exp} |")
    row("build / status", [f"{fmt(a.get('build'))} / {fmt(a.get('status'))}" for a in A])
    row("L3 fill tokens (slots + n_restored)", [fmt(a.get("fill_L3")) for a in A])
    for v in ("drafted", "nodraft"):
        row(f"L0 base {v}", [fmt(a.get(f"base.{v}")) for a in A])
        row(f"**L3 {v}**", [fmt((a.get("tab") or {}).get(f"L3.{v}")) for a in A],
            f">= ~{EXPECT['L3_' + v + '_min']} (v1 {V1_REF['L3_' + v]})")
        row(f"L3 loss vs L0 {v}", [fmt(a.get(f"loss_L3.{v}"), "%") for a in A])
        row(f"ABA drift {v}", [fmt(a.get(f"aba.{v}"), "%") for a in A])
    row("L3 draft acceptance", [fmt((a.get("tab") or {}).get("L3.drafted.acc")) for a in A])
    row("VRAM own peak GiB", [fmt(a.get("vram_own_peak_gib")) for a in A])
    row("live GGML_CUDA_FA_MASK_SKIP", [fmt((a.get("live_env") or {}).get("GGML_CUDA_FA_MASK_SKIP", "unset")
                                            if a.get("live_env") is not None else None) for a in A])
    L += ["", "## B llama-batched-bench npl 4, no drafter (S_TG / S_PP t/s)", "", hdr, sep]
    npps = sorted({int(k.split(".")[1]) for b in B for k in (b.get("rows") or {})})
    for npp in npps:
        for cfg in ("kvu", "nokvu"):
            for m, lab in (("s_tg", "S_TG"), ("s_pp", "S_PP")):
                row(f"{cfg} npp {npp} {lab}", [fmt(((b.get("rows") or {}).get(f"{cfg}.{npp}") or {}).get(m)) for b in B])
        row(f"**kvu vs no-kvu TG npp {npp}**", [fmt(b.get(f"tg_pct.{npp}"), "%") for b in B],
            f"within ~5% (v1 {V1_REF['b_kvu_vs_nokvu_tg_pct']}% @16384)")
        row(f"kvu vs no-kvu PP npp {npp}", [fmt(b.get(f"pp_pct.{npp}"), "%") for b in B])
    t1, t2 = A[1].get("tab") or {}, A[2].get("tab") or {}
    chk = []
    for v in ("drafted", "nodraft"):
        x = t1.get(f"L3.{v}")
        chk.append(f"arm1 L3 {v} {fmt(x)} vs >= {EXPECT['L3_' + v + '_min']}: "
                   + ("UNMEASURED" if x is None else ("MET" if x >= EXPECT[f'L3_{v}_min'] else "MISSED")))
    for npp in npps:
        x = B[1].get(f"tg_pct.{npp}")
        chk.append(f"arm1 B kvu vs no-kvu TG @{npp} {fmt(x, '%')} vs >= {EXPECT['b_kvu_vs_nokvu_tg_min_pct']}%: "
                   + ("UNMEASURED" if x is None else ("MET" if x >= EXPECT["b_kvu_vs_nokvu_tg_min_pct"] else "MISSED")))
    for key in ("L0_base.nodraft", "L3.nodraft", "L3.drafted"):
        s1, s2 = t1.get(f"{key}.sha"), t2.get(f"{key}.sha")
        if s1 and s2:
            chk.append(f"text sha {key}: on {s1} vs off {s2}: {'IDENTICAL' if s1 == s2 else 'DIFFERENT'}")
    on3, off3 = t1.get("L3.nodraft"), t2.get("L3.nodraft")
    if on3 and off3:
        chk.append(f"in-binary effect at L3 no-draft: on/off = {on3 / off3:.2f}x")
    off_v1 = (t2.get("L3.nodraft"), (A[0].get("tab") or {}).get("L3.nodraft"))
    if all(off_v1):
        chk.append(f"control: arm2 (off) vs v1 at L3 no-draft {(off_v1[0] - off_v1[1]) / off_v1[1] * 100:+.1f}% "
                   "(expected ~0: champion 90c12df42 base vs v10)")
    L += ["", "## Verdict vs expectations", ""] + [f"- {c}" for c in chk]
    L += ["", "- server log scans: " + "; ".join(f"{c[0]}: {a.get('log_scan')}" for c, a in zip(cols, A))]
    C.write_json(P3V2 / "p3v2_result.json", {"schema": "p3v2.result.v1", "at": C.now(), "expect": EXPECT,
                                              "v1_ref": V1_REF, "a1": {"v1": A[0], ARMS["on"]: A[1], ARMS["off"]: A[2]},
                                              "b": {"v1": B[0], ARMS["on"]: B[1], ARMS["off"]: B[2]}, "checks": chk})
    (P3V2 / "report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


# ------------------------------------------------------------------ dry run
def dry(a) -> int:
    meas, pool = texts()
    pre, _ = arm_env()
    print(f"  [{ARM}] results -> {OUT}/ (a1.json, b.json, logs/)   slot files -> {SLOTDIR}/")
    print(f"  [{ARM}] bin {C.BIN} (override={C.BIN_OVERRIDDEN}); env prefix: {' '.join(pre)}")
    if a.phase in ("all", "a1"):
        argv, notes = server_argv(a.port)
        print(f"  [{ARM} A1] argv source {ARGV_FILE}; transforms: {'; '.join(notes)}")
        print(f"  [{ARM} A1] cmd: " + " ".join(launch(argv)) + f"  > {LOGS}/a1.server.log")
        print(f"  [{ARM} A1] P: '[p3v2 meas fixed]' + C2+C4[:~{MEAS_TOK} tok] (source ~{int(len(meas) / CPT_EST)} tok)"
              f" + TASK, id_slot 0; neighbours ~{NB_TOK} tok from C1,C3,C5,C6,C7 ({len(pool)} chars)")
        print(f"  [{ARM} A1] plan: warmup -> prime P -> L0_base -> nb1 prefill+save -> nb2,nb3 restore -> L3 (~355k)"
              " -> erase 1-3 -> L0_after; per level drafted,nodraft,drafted,nodraft x 512 tok temp0")
    if a.phase in ("all", "b"):
        if a.b_npp_list:
            npps, why = b_plan(a)
        else:  # elapsed ~0 at dry-run time: show what the guard picks after a ~15 min A1
            npps, why = b_plan(argparse.Namespace(b_npp_list=None, budget_min=a.budget_min - 15))
            why += " (simulated: A1 took 15 min)"
        for name, kvu in (("kvu", True), ("nokvu", False)):
            print(f"  [{ARM} B {name}] " + " ".join(launch(bench_argv(kvu, npps or [B_V1_NPP], 64, 4)))
                  + f"  > {LOGS}/b.{name}.log")
        print(f"  [{ARM} B] npp {npps}: {why}; est {b_est_min(npps):.1f} min (v1-rate scaled, pessimistic for ON)")
    return 0


def main() -> int:
    global ARM, OUT, LOGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=sorted(ARMS))
    ap.add_argument("--bin-dir", default=None, help=f"override build bin dir (default {C.BIN})")
    ap.add_argument("--phase", default="all", choices=["all", "a1", "b", "report"])
    ap.add_argument("--port", type=int, default=18084)
    ap.add_argument("--park-mode", default="restore", choices=["restore", "prefill"])
    ap.add_argument("--budget-min", type=float, default=34)
    ap.add_argument("--b-npp-list", default=None)
    ap.add_argument("--keep-slot-file", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.phase in ("all", "a1"):
        ap.error("KVU-16h: A1 requires separate drafted and no-draft servers")
    if a.phase == "report":
        return phase_report(a)
    if not a.arm:
        ap.error("--arm on|off is required (except --phase report)")
    ARM = a.arm
    if a.bin_dir:
        C.set_bin(a.bin_dir)
    OUT = P3V2 / ARMS[ARM]
    LOGS = OUT / "logs"
    if a.dry_run:
        return dry(a)
    for d in (OUT, LOGS, SLOTDIR):
        d.mkdir(parents=True, exist_ok=True)
    say(f"bin {C.BIN} override={C.BIN_OVERRIDDEN} env {arm_env()[1]}")
    rc = 0
    if a.phase in ("all", "a1"):
        rc |= phase_a1(a)
    if not a.keep_slot_file:
        for f in SLOTDIR.glob("p3v2-nb*.bin"):
            say(f"removing slot file {f} ({f.stat().st_size / 2**30:.1f} GiB)")
            f.unlink()
    if a.phase in ("all", "b"):
        rc |= phase_b(a)
    say(f"done rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
