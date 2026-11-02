#!/usr/bin/env python3
"""EXPERIMENTAL isolated-lifecycle successor to COPY (gpu-slot-ak-20261004) of /mnt/raid0/llm/tmp/x0-27b-quants/p3_kvu_probe_v2.py (peer file untouched; digest in
SOURCES.sha256, verbatim copy in p3_kvu_probe_v2.orig.py). Same P3v2 arms and A1/B protocol; changes for the
combined KVU-19a+19b build gpu-20261004-c7f5ac9ad (build 10312):
  * --out-dir: results go to gpu-slot-ak-20261004/results/<ts>/p3v2/<label>/ (never the peer's results/p3v2).
  * arm env from slot_common.arm_env: on = GGML_CUDA_FA_MASK_SKIP, _MIN_KV and GGML_CUDA_FA_SEQ_ROWS unset;
    off = GGML_CUDA_FA_MASK_SKIP=0 GGML_CUDA_FA_SEQ_ROWS=0 (19a AND 19b off in the same binary).
  * server argv = :8083 production argv via slot_common.build_server_argv (live pid > launch record > X0 file),
    -b 2048 -ub 2048 explicit (== production effective), -lv 4, --device ROCm0 --device-draft ROCm0, plus P3's
    own --metrics --no-cache-idle-slots and slot-save-path; launch prefix numactl --membind=3 taskset 184-191.
  * VRAM sampled at 1 Hz; server stdout arrival-timestamped; one greedy coherence spot-check per launch.
  * --phase default a1 (the slot budget has no room for B; --phase all keeps the driver's own B budget guard).
  * report moved to slot_report.py (a1_summary/b_summary kept here and imported).

P3v2: re-run of the P3 unified-KV decode probe against workspace-ec's FA masked-KV-block-skip build
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
import p3_draft_guard as DG
import slot_common as C  # noqa: E402  (own-PID lifecycle, 1 Hz VRAM sampler, HIP proof, prod argv, arm env)
SB = C  # stream_chat(+text_sha), summarize, TASK live in slot_common

P3V1 = Path("/mnt/raid0/llm/tmp/x0-27b-quants/results/p3")
ARMS = {"on": "arm1_maskskip_on", "off": "arm2_maskskip_off"}
OUT = C.SLOT / "results" / "_unset"  # per-arm dir, set in main() from --out-dir
LOGS = OUT / "logs"
SLOTDIR = OUT / "slots"
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
ACTIVE_VARIANT = "drafted"
SHARED_NONCE = None
ARM = "on"
T0 = time.time()


def say(msg: str) -> None:
    print(f"[p3v2 {ARM} {time.strftime('%H:%M:%SZ', time.gmtime())} +{(time.time() - T0) / 60:.1f}m] {msg}", flush=True)


def elapsed_min() -> float:
    return (time.time() - T0) / 60


# ------------------------------------------------------------------ env / launch prefix
def arm_env() -> tuple[list[str], dict]:
    """`env` prefix (env exec's, so the captured PID stays the server's) + the overrides it applies."""
    return C.arm_env(ARM == "on")


def launch(argv: list[str]) -> list[str]:
    return C.launch_cmd(ARM == "on", argv)


def child_env() -> dict:
    env = C.child_env(ARM == "on")
    env.pop("LLAMA_KV_CACHE_DEBUG", None)
    return env


# ------------------------------------------------------------------ argv
def server_argv(port: int) -> tuple[list[str], list[str]]:
    a, notes, src = C.build_server_argv(port, 2048, 2048, SLOTDIR, extra=["--metrics", "--no-cache-idle-slots"])
    notes = [f"argv source {src['source']} sha256 {src['sha256'][:16]}"] + notes + \
        ["(--no-cache-idle-slots keeps idle neighbours resident: P3 protocol)"]
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
            "tasks": {x["id"]: x.get("id_task") for x in s},
            "decoded": {x["id"]: (x.get("next_token") or {}).get("n_decoded") for x in s},
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
        during = [s for s in ok if 0 in s["busy"] and
                  type(s.get("decoded", {}).get(0)) is int and s["decoded"][0] > 0]
        ids = {s.get("tasks", {}).get(0) for s in during}
        ids.discard(None)
        slot_ids = set.intersection(*(set(s["per_slot"]) for s in during)) if during else set()
        return {"n_samples": len(ok), "n_during_decode": len(during),
                "task_ids": sorted(ids),
                "task_ids_complete": all(type(s.get("tasks", {}).get(0)) is int for s in during),
                "per_slot_min": {k: min(s["per_slot"][k] for s in during) for k in slot_ids},
                "per_slot_max": {k: max(s["per_slot"][k] for s in during) for k in slot_ids}}


def chat(base: str, msg: str, slot: int, max_tokens: int, extra: dict | None = None) -> dict:
    body = {"messages": [{"role": "user", "content": msg}], "max_tokens": max_tokens, "id_slot": slot,
            **TEMP0, **(extra or {})}
    if any(k in body for k in ("speculative.n_max", "speculative")):
        raise ValueError("request-level speculation override forbidden")
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
        if ACTIVE_VARIANT == "nodraft":
            self.argv = DG.dedicated_no_draft_argv(self.argv)
            if any(k.startswith("LLAMA_ARG_") and ("DRAFT" in k or "SPEC" in k) for k in child_env()):
                raise RuntimeError("draft-related environment prevents no-draft custody")
        elif not any(x.split("=", 1)[0] in DG.DRAFT_MODEL_FLAGS for x in self.argv):
            raise RuntimeError("drafted server requires explicit draft model")
        self.base = f"http://127.0.0.1:{port}"
        self.log = LOGS / f"{name}.server.log"
        self.proc = None
        self.sampler = None
        self.rec: dict = {"argv": launch(self.argv), "argv_transforms": self.notes, "env": arm_env()[1],
                          "bin_dir": str(C.BIN), "bin_overridden": C.BIN_OVERRIDDEN}

    def start(self):
        check = subprocess.run(["ss", "-ltnH", f"sport = :{self.port}"], capture_output=True, text=True)
        if check.returncode != 0 or check.stdout.strip():
            raise RuntimeError("scratch port not verified free")
        self.rec["vram_before"] = C.vram_now()
        self.rec["foreign_gpu_procs_before"] = C.foreign_gpu_procs()
        self.sampler = C.VramSampler(LOGS / f"{self.name}.vram.jsonl", period=1.0).start()
        self.proc = C.start_own(launch(self.argv), self.log, env=child_env())
        self.rec["pid"] = self.proc.pid
        (OUT / "server.pid").write_text(f"{self.proc.pid}\n")  # lets slot_run reap it if this driver is SIGKILLed
        self.rec["load_s"] = C.wait_healthy(self.base, self.proc, timeout=900)
        listeners = subprocess.run(["ss", "-ltnp", f"sport = :{self.port}"], capture_output=True, text=True)
        if listeners.returncode != 0 or f"pid={self.proc.pid}," not in listeners.stdout:
            raise RuntimeError("listener is not owned by captured server")
        self.rec["hip_dlopen_proof"] = C.hip_dlopen_proof(self.proc.pid)
        self.rec["live_env"] = C.live_env(self.proc.pid)
        if not self.rec["hip_dlopen_proof"].get("ok"):
            raise RuntimeError(f"HIP dlopen proof failed: {self.rec['hip_dlopen_proof']}")
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
        self.rec["memory_lines"] = C.log_memory_lines(self.log)
        check = subprocess.run(["ss", "-ltnH", f"sport = :{self.port}"], capture_output=True, text=True)
        self.rec["port_free_after"] = check.returncode == 0 and not check.stdout.strip()
        if not self.rec["port_free_after"] or not self.rec.get("teardown", {}).get("verified_dead"):
            raise RuntimeError("server teardown not verified")


# ------------------------------------------------------------------ phase A1
def measure_level(srv: Server, P: str, p_tok: int, level: str, fill: int, rows: list, out: Path, rec: dict) -> None:
    for i, (variant, extra) in enumerate(((ACTIVE_VARIANT, None), (ACTIVE_VARIANT, None))):
        before = resident(srv.base)
        if before["busy"]:
            raise RuntimeError("server has active work before measurement")
        previous_task = before["tasks"].get(0)
        if type(previous_task) is not int:
            raise RuntimeError("previous slot task identity unavailable")
        with SlotPoller(srv.base) as poll:
            r = chat(srv.base, P, 0, GEN, extra)
        draft_n = r.get("draft_n")
        if variant == "drafted" and (type(draft_n) is not int or draft_n <= 0):
            raise RuntimeError("drafted measurement did not report draft tokens")
        if variant == "nodraft" and draft_n is not None and (type(draft_n) is not int or draft_n != 0):
            raise RuntimeError("no-draft measurement reported draft tokens")
        row = {"level": level, "fill_tokens": fill, "variant": variant, "rep": i + 1, **r,
               "kv_resident": poll.summary()}
        observed = row["kv_resident"]
        ids, minima, maxima = observed["task_ids"], observed["per_slot_min"], observed["per_slot_max"]
        if observed["n_during_decode"] < 2 or not observed["task_ids_complete"] or len(ids) != 1:
            raise RuntimeError("need two decode samples for one identified task")
        if previous_task is not None and ids[0] == previous_task:
            raise RuntimeError("decode task identity did not advance")
        if minima.get(0, 0) < 0.95 * p_tok:
            raise RuntimeError("measurement prefix not resident during decode")
        neighbours = (1, 2, 3) if level == "L3" else ()
        if any(minima.get(k, 0) < 0.9 * NB_TOK for k in neighbours):
            raise RuntimeError("neighbour not resident during decode")
        if any(maxima.get(k) != 0 for k in (1, 2, 3) if k not in neighbours):
            raise RuntimeError("unexpected neighbour resident or unobserved during decode")
        row["task_binding"] = "slot-0 temporal correlation; response has no native task ID"
        row["decode_only"] = (r.get("prompt_n") or 0) < 64 and (r.get("cache_n") or 0) > 0.95 * p_tok
        if not row["decode_only"]:
            raise RuntimeError("measurement was not decode-only")
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


def phase_a1_single(a) -> int:
    out = OUT / "a1.json"
    nonce = SHARED_NONCE
    srv = Server("a1", a.port)
    rec = {"schema": "p3v2.a1.v1", "arm": ARM, "started_at": C.now(), "nonce": nonce, "park_mode": a.park_mode,
           "park_mode_effective": a.park_mode, "pool_cells": POOL, "rows": [], "parks": [], "residency": []}
    rc = 1
    restored: dict[int, int] = {}
    try:
        srv.start()
        rec["server"] = srv.rec
        rec["warmup"] = chat(srv.base, "Say hello.", 0, 64)
        coh = C.coherence_check(srv.base, OUT / "coherence.json", f"p3v2 {OUT.name}")
        rec["coherence"] = {k: coh.get(k) for k in ("text_sha", "finish", "predicted_n", "error")}
        say(f"coherence: sha {coh.get('text_sha')} {(coh.get('content_text') or coh.get('error') or '')[:120]!r}")
        meas, pool = texts()
        cpt_m = len(meas) / len(C.http_json(srv.base + "/tokenize", {"content": meas}, timeout=300)["tokens"])
        cpt_p = len(pool) / len(C.http_json(srv.base + "/tokenize", {"content": pool}, timeout=300)["tokens"])
        # fixed tag (not the nonce) so arm on/off see byte-identical P -> text_sha comparable across arms
        P = "[p3v2 meas fixed]\n" + meas[: int(MEAS_TOK * cpt_m)] + SB.TASK
        rec["measurement_prompt_sha256"] = __import__("hashlib").sha256(P.encode()).hexdigest()
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
                raise RuntimeError(f"slot {k} holds only {have} tokens")
            if res["per_slot"].get(0, 0) < 0.95 * p_tok:
                raise RuntimeError("slot 0 lost measurement prefix")
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
        try:
            srv.stop()
        except Exception as exc:
            rec["status"] = "failed"
            rec["cleanup_error"] = f"{type(exc).__name__}: {exc}"
            rc = 1
        rec["server"] = srv.rec
        rec["finished_at"] = C.now()
        C.write_json(out, rec)
    return rc


def phase_a1(a) -> int:
    """Run each variant on its own server, with its own prefix and parked slots."""
    global OUT, LOGS, SLOTDIR, ACTIVE_VARIANT, SHARED_NONCE
    if a.park_mode != "prefill":
        raise ValueError("isolated A1 requires observable prefilled neighbour slots")
    root = OUT
    SHARED_NONCE = uuid.uuid4().hex[:12]
    captures = []
    try:
        for variant in ("drafted", "nodraft"):
            ACTIVE_VARIANT = variant
            OUT = root / variant
            LOGS, SLOTDIR = OUT / "logs", OUT / "slots"
            for directory in (OUT, LOGS, SLOTDIR):
                directory.mkdir(parents=True, exist_ok=True)
            rc = phase_a1_single(a)
            capture = json.loads((OUT / "a1.json").read_text())
            captures.append(capture)
            server = capture.get("server", {})
            if (rc or capture.get("status") != "ok" or
                server.get("teardown", {}).get("verified_dead") is not True or
                server.get("port_free_after") is not True or
                not isinstance(server.get("pid"), int) or
                any(c.get("server", {}).get("pid") == server.get("pid") for c in captures[:-1])):
                raise RuntimeError("variant failed or server cleanup unverified")
        left, right = captures
        if left.get("measurement_prompt_sha256") != right.get("measurement_prompt_sha256"):
            raise RuntimeError("measurement prefixes differ")
        if len(left["rows"]) != 6 or len(right["rows"]) != 6:
            raise RuntimeError("incomplete variant rows")
        differences = []
        for arow, brow in zip(left["rows"], right["rows"]):
            if (arow["level"], arow["rep"]) != (brow["level"], brow["rep"]):
                raise RuntimeError("variant row ordering differs")
            slots = (0, 1, 2, 3) if arow["level"] == "L3" else (0,)
            for slot in slots:
                av = arow["kv_resident"]["per_slot_min"].get(str(slot), 0)
                bv = brow["kv_resident"]["per_slot_min"].get(str(slot), 0)
                if not av or not bv:
                    raise RuntimeError("during-decode slot occupancy missing")
                differences.append({"level": arow["level"], "rep": arow["rep"], "slot": slot,
                                    "drafted": av, "nodraft": bv,
                                    "relative_difference": abs(av - bv) / max(av, bv)})
        C.write_json(root / "a1.json", {**left, "rows": [r for c in captures for r in c["rows"]],
                                       "variant_runs": captures, "dedicated_server_per_variant": True,
                                       "occupancy_differences": differences,
                                       "occupancy_reference": "Separate P3 replay specified 5%; reference only, not a pass rule for this successor"})
        return 0
    except Exception as exc:
        C.write_json(root / "a1.json", {"status": "failed", "rows": [], "variant_runs": captures,
                                       "error": f"{type(exc).__name__}: {exc}"})
        return 1
    finally:
        OUT = root
        LOGS, SLOTDIR = OUT / "logs", OUT / "slots"
        ACTIVE_VARIANT, SHARED_NONCE = "drafted", None


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
    log = LOGS / f"b.{name}.log"
    rec = {"argv": launch(argv), "env": arm_env()[1], "vram_before": C.vram_now()}
    sampler = C.VramSampler(LOGS / f"b.{name}.vram.jsonl", period=1.0).start()
    proc = C.start_own(launch(argv), log, env=child_env())
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


# ------------------------------------------------------------------ dry run
def dry(a) -> int:
    meas, pool = texts()
    pre, _ = arm_env()
    print(f"  [{ARM}] results -> {OUT}/ (a1.json, b.json, coherence.json/.txt, logs/)   slot files -> {SLOTDIR}/")
    print(f"  [{ARM}] bin {C.BIN} (override={C.BIN_OVERRIDDEN}); env prefix: {' '.join(pre)}")
    if a.phase in ("all", "a1"):
        argv, notes = server_argv(a.port)
        print(f"  [{ARM} A1] transforms: {'; '.join(notes)}")
        print(f"  [{ARM} A1] cmd: " + " ".join(launch(argv)) + f"  > {LOGS}/a1.server.log")
        print(f"  [{ARM} A1] P: '[p3v2 meas fixed]' + C2+C4[:~{MEAS_TOK} tok] (source ~{int(len(meas) / CPT_EST)} tok)"
              f" + TASK, id_slot 0; neighbours ~{NB_TOK} tok from C1,C3,C5,C6,C7 ({len(pool)} chars)")
        print(f"  [{ARM} A1] plan: sequential dedicated drafted and no-draft servers, each warmup -> prime P -> L0_base -> nb1 prefill+save -> nb2,nb3 restore -> L3 (~355k)"
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
    ap.add_argument("--phase", default="a1", choices=["all", "a1", "b"])
    ap.add_argument("--port", type=int, default=18183)
    ap.add_argument("--out-dir", type=Path, required=True, help="per-arm results dir (results/<ts>/p3v2/<label>)")
    ap.add_argument("--park-mode", default="prefill", choices=["prefill"])
    ap.add_argument("--budget-min", type=float, default=34)
    ap.add_argument("--b-npp-list", default=None)
    ap.add_argument("--keep-slot-file", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    global SLOTDIR
    if not a.arm:
        ap.error("--arm on|off is required")
    if a.port == 8083:
        ap.error("scratch port only (8083 is production)")
    ARM = a.arm
    if a.bin_dir:
        C.set_bin(a.bin_dir)
    OUT = a.out_dir
    LOGS = OUT / "logs"
    SLOTDIR = OUT / "slots"
    if a.dry_run:
        return dry(a)
    for d in (OUT, LOGS, SLOTDIR):
        d.mkdir(parents=True, exist_ok=True)
    say(f"bin {C.BIN} env {arm_env()[1]} out {OUT}")
    rc = 0
    if a.phase in ("all", "a1"):
        rc |= phase_a1(a)
    if not a.keep_slot_file:
        for f in SLOTDIR.glob("p3v2-nb*.bin"):
            say(f"removing slot file {f} ({f.stat().st_size / 2**30:.1f} GiB)")
            f.unlink()
    if a.phase in ("all", "b") and rc == 0:
        rc |= phase_b(a)
    say(f"done rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
