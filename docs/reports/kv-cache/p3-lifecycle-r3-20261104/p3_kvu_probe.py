#!/usr/bin/env python3
"""P3 (intake-1849, llama.cpp #28495): does --kv-unified make every decode step on the MI210 attend
over the whole OCCUPIED pool (other sequences' cells included)?

Phases (driver for p3_kvu_probe.sh; every process is our own captured PID, x0_common lifecycle):
  A1  parked-neighbour serving test. Production :8083 argv on a scratch port with exactly three
      deviations: --port, --slot-save-path -> results/p3/slots (needed for slot save/restore/erase),
      and --no-cache-idle-slots + --metrics. WHY --no-cache-idle-slots: the v10 server defaults
      cache_idle_slots=true, and with --cache-ram + --kv-unified it SAVES EVERY IDLE SLOT TO THE RAM
      CACHE AND CLEARS ITS KV the moment any new completion task launches
      (tools/server/server-context.cpp:2469-2483, [TAG_IDLE_SLOT_CLEAR]). Under production flags an
      idle "parked" neighbour therefore cannot stay resident during another slot's decode; A0 proves
      that empirically. A1 isolates the attention-scan mechanism with neighbours resident but idle.
      Measurement prompt P (~57k tok, C2+C4, run-nonce prefixed) is pinned to slot 0 via id_slot;
      neighbours (~100k tok each) are pinned to slots 1..3. Fill levels:
        L0 base (P only, ~58k) -> L1 (+nb1, ~158k) -> L2 (+nb2, ~258k) -> L3 (+nb3, ~358k of 393216)
        -> L0' (neighbours erased; ABA drift control).
      Per level: drafted, no-draft (speculative.n_max 0), drafted, no-draft; 512 tok, temp 0, P cached
      (decode-only). /slots polled every 2 s DURING every decode (resident tokens per slot).
      nb1 is prefilled; nb2/nb3 are slot-restored copies of nb1's saved state (--park-mode restore,
      default; saves ~8 min of prefill; attention cost does not depend on cell CONTENT) with automatic
      fallback to prefilling distinct text if save/restore fails. --park-mode prefill forces prefill.
  A0  production-flag residency check (exact prod argv + scratch port/slot path + --metrics, -lv 5,
      LLAMA_KV_CACHE_DEBUG=1): restore nb1 into slot 1, launch a short task on slot 0, verify slot 1
      is purged (/slots n_prompt_tokens -> 0; KV-level `used =` lines in the server log).
  B   llama-batched-bench, 27B Q8_0 no drafter, -kvu vs -no-kvu, npl 4 concurrent decode (the only way
      foreign cells are resident under production flags), npp sized by the budget guard.

Usage: p3_kvu_probe.py [--phase all|a1|a0|b|report] [--dry-run] [--port 18084] [--park-mode restore|prefill]
                       [--budget-min 30] [--b-npp 32768] [--keep-slot-file]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
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
sys.path.append(os.environ.get("KVU16H_X0_DIR", "/mnt/raid0/llm/tmp/x0-27b-quants"))
import draft_guard as DG
import x0_common as C  # noqa: E402  (read-only reuse: own-PID lifecycle, VRAM sampler, HIP proof)
import x0_shape_b as SB  # noqa: E402  (read-only reuse: argv parsing/_set, stream_chat, summarize)

C.BIN = Path("/mnt/raid0/llm/kernels/production/gpu")
P3 = Path(os.environ.get("KVU16H_OUT", str(Path(__file__).resolve().parent / "results")))
LOGS = P3 / "logs"
SLOTDIR = P3 / "slots"
ARGV_FILE = Path(__file__).resolve().parent / "server-argv.txt"
CTX = Path(__file__).resolve().parent / "contexts"
POOL = 393216
MEAS_TOK, NB_TOK, GEN = 57000, 100000, 512
SMOKE = os.environ.get("KVU16H_SMOKE") == "1"
if SMOKE:
    POOL, MEAS_TOK, NB_TOK, GEN = 1024, 32, 32, 4
    SB.PREFIX = ["numactl", "--membind=3", "--", "taskset", "-c", "184-185"]
CPT_EST = 2.9312  # measured chars/token on C2+C4 by X0 shape b (dry-run estimates only)
TEMP0 = {"temperature": 0.0, "top_k": 1, "top_p": 1.0}
NODRAFT = {"speculative.n_max": 0}
SERVER_ARGV = {}
ACTIVE_VARIANT = "drafted"
SHARED_NONCE = None
FAIL_PATTERNS = ["failed to find a memory slot", "context size has been exceeded",
                 "failed to find free space in the KV cache", "exceeds the available context size",
                 "purging slot", "Unable to restore slot"]
T0 = time.time()


def say(msg: str) -> None:
    print(f"[p3 {time.strftime('%H:%M:%SZ', time.gmtime())} +{(time.time() - T0) / 60:.1f}m] {msg}", flush=True)


def elapsed_min() -> float:
    return (time.time() - T0) / 60


# ------------------------------------------------------------------ argv
def server_argv(port: int, prod_idle: bool, debug: bool) -> tuple[list[str], list[str]]:
    src = SB.read_argv(ARGV_FILE)
    a = [str(C.BIN / "llama-server")] + src[1:]
    notes = [] if src[0] == a[0] else [f"binary {src[0]} -> {a[0]}"]
    for names, val in ((("--host",), "127.0.0.1"), (("--port",), str(port)),
                       (("--slot-save-path",), str(SLOTDIR))):
        before = list(a)
        a = SB._set(a, names, val)
        if a != before:
            notes.append(f"{names[0]} -> {val}")
    if SMOKE:
        a = SB._set(a, ("-c", "--ctx-size"), str(POOL))
        a = SB._set(a, ("--cache-ram",), "0")
        a = SB._set(a, ("-t", "--threads"), "2")
    a.append("--metrics")
    notes.append("+ --metrics")
    if not prod_idle:
        a.append("--no-cache-idle-slots")
        notes.append("+ --no-cache-idle-slots (keep idle neighbours resident)")
    if debug:
        a += ["-lv", "5"]
        notes.append("+ -lv 5 (+ env LLAMA_KV_CACHE_DEBUG=1): KV-level used-cell lines")
    return a, notes


def bench_argv(kvu: bool, npp: int, ntg: int, npls: str) -> list[str]:
    npl_max = max(int(x) for x in npls.split(","))
    ctx = int(math.ceil(npl_max * (npp + ntg) / 1024) * 1024 + 1024)
    return [str(C.BIN / "llama-batched-bench"), "-m", str(C.MODELS["q8"]), "-c", str(ctx), "-b", "2048",
            "-ub", "2048", "-t", "8", "-ngl", "99", "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0", "--no-mmap",
            "-dev", "ROCm0", "-kvu" if kvu else "-no-kvu", "-npp", str(npp), "-ntg", str(ntg), "-npl", npls,
            "--output-format", "jsonl"]


def set_env(debug: bool = False) -> None:
    os.environ.update(SB.STACK_ENV)
    os.environ["LD_LIBRARY_PATH"] = f"{C.BIN}:/opt/rocm/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
    if debug:
        os.environ["LLAMA_KV_CACHE_DEBUG"] = "1"
    else:
        os.environ.pop("LLAMA_KV_CACHE_DEBUG", None)


# ------------------------------------------------------------------ prompts
def texts() -> tuple[str, str]:
    meas = (CTX / "C2/prompt.inline.txt").read_text() + "\n\n" + (CTX / "C4/prompt.inline.txt").read_text()
    pool = "\n\n".join((CTX / f"{c}/prompt.inline.txt").read_text() for c in ("C1", "C3", "C5", "C6", "C7"))
    return meas, pool


def nb_text(pool: str, k: int, nchars: int, nonce: str) -> str:
    off = (k - 1) * (len(pool) // 3)
    body = (pool[off:] + "\n\n" + pool)[:nchars]
    return f"[p3 neighbour {k} {nonce}]\n" + body + SB.TASK


# ------------------------------------------------------------------ HTTP helpers
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
    """Poll /slots every `period` s DURING a request (the residency evidence the stack owner asked for)."""

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
        during = [s for s in ok if 0 in s["busy"]]
        sums = [s["sum"] for s in during]
        return {"n_samples": len(ok), "n_during_busy": len(during),
                "resident_min": min(sums) if sums else None, "resident_max": max(sums) if sums else None,
                "resident_max_frac_pool": round(max(sums) / POOL, 4) if sums else None,
                "per_slot_at_max": max(during, key=lambda s: s["sum"])["per_slot"] if during else None,
                "busy_per_slot_min": {k: min(s["per_slot"].get(k, 0) for s in during)
                                      for k in set().union(*(s["per_slot"] for s in during))},
                "busy_per_slot_max": {k: max(s["per_slot"].get(k, 0) for s in during)
                                      for k in set().union(*(s["per_slot"] for s in during))}}


def chat(base: str, msg: str, slot: int, max_tokens: int, extra: dict | None = None) -> dict:
    body = {"messages": [{"role": "user", "content": msg}], "max_tokens": max_tokens, "id_slot": slot,
            **TEMP0, **(extra or {})}
    DG.validate_request(SERVER_ARGV[base], body)
    return SB.summarize(SB.stream_chat(base, body))


def log_scan(path: Path) -> dict:
    try:
        txt = path.read_text(errors="replace")
    except OSError as exc:
        return {"err": str(exc)}
    out = {p: txt.count(p) for p in FAIL_PATTERNS}
    out["saving_idle_slot_lines"] = txt.count("saving idle slot to prompt cache")
    kv = [(int(m.group(1)), int(m.group(2))) for m in
          re.finditer(r"stream\[\d+\], n = +(\d+), used = +(\d+)", txt)]  # LLAMA_KV_CACHE_DEBUG lines only
    used, nmax = [u for _, u in kv], [n for n, _ in kv]
    if used:
        out["kv_debug_used_max"], out["kv_debug_used_last"] = max(used), used[-1]
    if nmax:
        out["kv_debug_n_kv_max"] = max(nmax)
    return out


# ------------------------------------------------------------------ server lifecycle wrapper
class Server:
    def __init__(self, name: str, port: int, prod_idle: bool, debug: bool):
        self.name, self.port = name, port
        self.argv, self.notes = server_argv(port, prod_idle, debug)
        if ACTIVE_VARIANT == "nodraft":
            self.argv = DG.dedicated_no_draft_argv(self.argv)
            self.notes.append("dedicated no-draft process; all drafter arguments removed")
        self.debug = debug
        self.base = f"http://127.0.0.1:{port}"
        SERVER_ARGV[self.base] = self.argv
        self.log = LOGS / f"{name}.server.log"
        self.proc = None
        self.sampler = None
        self.rec: dict = {"argv": SB.PREFIX + self.argv, "argv_transforms": self.notes,
                          "env_overrides": {**SB.STACK_ENV, **({"LLAMA_KV_CACHE_DEBUG": "1"} if debug else {})}}

    def start(self):
        check = subprocess.run(["ss", "-ltnH", f"sport = :{self.port}"], capture_output=True, text=True)
        if check.returncode != 0 or check.stdout.strip():
            raise RuntimeError("scratch port not verified free")
        set_env(self.debug)
        self.rec["vram_before"] = C.vram_now()
        self.sampler = C.VramSampler(LOGS / f"{self.name}.vram.jsonl").start()
        self.proc = C.start_own(SB.PREFIX + self.argv, self.log)
        self.rec["pid"] = self.proc.pid
        self.rec["load_s"] = C.wait_healthy(self.base, self.proc, timeout=900)
        listeners = subprocess.run(["ss", "-ltnp", f"sport = :{self.port}"], capture_output=True, text=True).stdout
        if f"pid={self.proc.pid}," not in listeners:
            raise RuntimeError("health port is not owned by captured server pid")
        self.rec["hip_dlopen_proof"] = C.hip_dlopen_proof(self.proc.pid)
        props = C.http_json(self.base + "/props")
        self.rec["build_info"] = props.get("build_info")
        s = slots(self.base)
        self.rec["n_slots"], self.rec["n_ctx_slot"] = len(s), min(x.get("n_ctx", 0) for x in s)
        say(f"{self.name}: healthy in {self.rec['load_s']} s, pid {self.proc.pid}, slots {self.rec['n_slots']}"
            f" x n_ctx {self.rec['n_ctx_slot']}, hip-proof {self.rec['hip_dlopen_proof'].get('ok')}")

    def stop(self):
        errors = []
        if self.sampler:
            try:
                self.sampler.stop()
            except Exception as exc:
                errors.append(f"sampler stop: {exc}")
        if self.proc is not None:
            try:
                self.rec["teardown"] = C.stop_own(self.proc, term_wait=180)
                if self.rec["teardown"].get("verified_dead") is True:
                    self.proc = None
                else:
                    errors.append("captured server termination not verified")
            except Exception as exc:
                errors.append(f"server stop: {exc}")
        if self.sampler:
            try:
                self.rec["vram"] = self.sampler.summary(self.rec.get("pid"), self.rec["vram_before"].get("used_b"))
            except Exception as exc:
                errors.append(f"sampler summary: {exc}")
        self.rec["log_scan"] = log_scan(self.log)
        check = subprocess.run(["ss", "-ltnH", f"sport = :{self.port}"], capture_output=True, text=True)
        self.rec["port_free_after"] = check.returncode == 0 and not check.stdout.strip()
        if not self.rec["port_free_after"]:
            errors.append("port not verified free")
        if errors:
            raise RuntimeError("; ".join(errors))


# ------------------------------------------------------------------ phase A1
def require_draft_count(variant: str, result: dict) -> int | None:
    value = result.get("draft_n")
    if variant == "nodraft" and value is None:
        return None  # Missing native metric is UNKNOWN, never observed zero.
    if type(value) is not int or value < 0:
        raise RuntimeError("explicit nonnegative integer draft_n required")
    if variant == "nodraft" and value != 0:
        raise RuntimeError("dedicated no-draft server returned nonzero draft_n")
    if variant == "drafted" and value <= 0:
        raise RuntimeError("drafted arm did not produce draft tokens")
    return value


def measure_level(srv: Server, P: str, p_tok: int, level: str, rows: list, out: Path, rec: dict) -> None:
    variant = ACTIVE_VARIANT
    extra = None  # Dedicated no-draft process; never use request-local zero.
    for i in range(2):
        with SlotPoller(srv.base) as poll:
            r = chat(srv.base, P, 0, GEN, extra)
        require_draft_count(variant, r)
        row = {"level": level, "variant": variant, "rep": i + 1, **r, "draft_count_observation": "unknown" if r.get("draft_n") is None else "reported", "kv_resident": poll.summary()}
        row["decode_only"] = (r.get("prompt_n") or 0) < 64 and (r.get("cache_n") or 0) > 0.95 * p_tok
        if not row["decode_only"]:
            raise RuntimeError("measurement was not decode-only")
        poll_summary = row["kv_resident"]
        if poll_summary["n_during_busy"] < 2:
            raise RuntimeError("insufficient during-decode residency samples")
        level_num = int(level[1])
        minima = poll_summary["busy_per_slot_min"]
        if minima.get(0, 0) < 0.95 * p_tok or any(minima.get(k, 0) < 0.9 * NB_TOK for k in range(1, level_num + 1)):
            raise RuntimeError("required slots did not remain resident during decode")
        if any(poll_summary["busy_per_slot_max"].get(k, 0) != 0 for k in range(level_num + 1, 4)):
            raise RuntimeError("unexpected neighbour resident during decode")
        rows.append(row)
        say(f"A1 {level} {variant} r{row['rep']}: decode {r['decode_tps']} tok/s acc {r['draft_acc']} "
            f"prompt {r['prompt_n']} (cache {r['cache_n']}) resident max {row['kv_resident']['resident_max']}"
            f" ({row['kv_resident']['resident_max_frac_pool']} of pool) decode_only={row['decode_only']}")
        C.write_json(out, {**rec, "status": "partial"})


def park(srv: Server, k: int, pool: str, cpt: float, nonce: str, mode: str, rec: dict) -> dict:
    fname = "p3-nb1.bin"
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
        return {"nb": k, "how": "restore(nb1 state)", "restore": res}
    except Exception as exc:  # noqa: BLE001
        say(f"A1 restore into slot {k} failed ({exc}); falling back to prefill")
        rec["park_mode_effective"] = f"prefill (restore failed at nb{k})"
        ev = park(srv, k, pool, cpt, nonce, "prefill", rec)
        ev["restore_error"] = f"{type(exc).__name__}: {exc}"[:300]
        return ev


def phase_a1_single(a) -> int:
    variant_started = time.monotonic()
    out = P3 / "a1.json"
    nonce = SHARED_NONCE or uuid.uuid4().hex[:12]
    srv = Server("a1", a.port, prod_idle=False, debug=False)
    rec = {"schema": "p3.a1.v1", "started_at": C.now(), "nonce": nonce, "park_mode": a.park_mode,
           "park_mode_effective": a.park_mode, "pool_cells": POOL, "rows": [], "parks": [], "residency": []}
    rc = 1
    try:
        srv.start()
        rec["server"] = srv.rec
        rec["warmup"] = chat(srv.base, "Say hello.", 0, 64)
        meas, pool = texts()
        cpt_m = len(meas) / len(C.http_json(srv.base + "/tokenize", {"content": meas}, timeout=300)["tokens"])
        cpt_p = len(pool) / len(C.http_json(srv.base + "/tokenize", {"content": pool}, timeout=300)["tokens"])
        P = f"[p3 meas {nonce}]\n" + meas[: int(MEAS_TOK * cpt_m)] + SB.TASK
        rec["cpt_meas"], rec["cpt_pool"] = round(cpt_m, 4), round(cpt_p, 4)
        rec["prime"] = chat(srv.base, P, 0, GEN)  # pays the ~57k prefill on slot 0; not a timed row
        p_tok = rec["prime"]["prompt_n"] + (rec["prime"]["cache_n"] or 0)
        rec["p_tokens"] = p_tok
        say(f"A1 prime: P = {p_tok} tok, prefill {rec['prime']['prefill_tps']} tok/s, decode {rec['prime']['decode_tps']}")
        rec["residency"].append({"at": "L0", **resident(srv.base), "metrics": metrics(srv.base)})
        measure_level(srv, P, p_tok, "L0_base", rec["rows"], out, rec)
        for k in (1, 2, 3):
            ev = park(srv, k, pool, cpt_p, nonce, a.park_mode, rec)
            rec["parks"].append(ev)
            res = resident(srv.base)
            rec["residency"].append({"at": f"L{k}", **res, "metrics": metrics(srv.base)})
            say(f"A1 parked nb{k} ({ev['how']}): resident {res['per_slot']} sum {res['sum']} = {res['frac_pool']} of pool")
            if any(res["per_slot"].get(j, 0) < 0.9 * NB_TOK for j in range(1, k + 1)):
                raise RuntimeError("parked neighbour occupancy below threshold")
            if res["per_slot"].get(0, 0) < 0.95 * p_tok:
                raise RuntimeError("measurement slot lost its prefix")
            measure_level(srv, P, p_tok, f"L{k}_{res['sum'] // 1000}k", rec["rows"], out, rec)
        for k in (1, 2, 3):
            rec.setdefault("erase", []).append(slot_action(srv.base, k, "erase"))
        res = resident(srv.base)
        rec["residency"].append({"at": "L0_after", **res, "metrics": metrics(srv.base)})
        measure_level(srv, P, p_tok, "L0_after", rec["rows"], out, rec)
        if SMOKE:
            rec["smoke_extra_requests"] = 0
            while time.monotonic() - variant_started < 30:
                chat(srv.base, P, 0, GEN)
                rec["smoke_extra_requests"] += 1
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
    global P3, LOGS, SLOTDIR, ACTIVE_VARIANT, SHARED_NONCE
    root = P3
    captures = []
    SHARED_NONCE = uuid.uuid4().hex[:12]
    try:
        for variant in ("drafted", "nodraft"):
            ACTIVE_VARIANT = variant
            P3 = root / variant
            LOGS, SLOTDIR = P3 / "logs", P3 / "slots"
            for directory in (P3, LOGS, SLOTDIR):
                directory.mkdir(parents=True, exist_ok=True)
            rc = phase_a1_single(a)
            capture = json.loads((P3 / "a1.json").read_text())
            captures.append(capture)
            server = capture.get("server", {})
            residency_ok = (server.get("hip_dlopen_proof", {}).get("ok") is True
                            and (server.get("vram", {}).get("nonzero_samples") or 0) >= 2
                            and server.get("teardown", {}).get("verified_dead") is True
                            and server.get("port_free_after") is True
                            and capture.get("status") == "ok"
                            and isinstance(server.get("pid"), int)
                            and all(c.get("server", {}).get("pid") != server.get("pid") for c in captures[:-1]))
            if not residency_ok:
                capture["residency_or_cleanup_refused"] = True
                rc = 1
            if rc:
                C.write_json(root / "a1.json", {"status": "failed", "rows": [], "variant_runs": captures})
                return rc
        # Match each independently prepared level and repetition by slot occupancy.
        left, right = captures[0]["rows"], captures[1]["rows"]
        if len(left) != 10 or len(right) != 10:
            raise RuntimeError("incomplete variant rows")
        for arow, brow in zip(left, right):
            level_a, level_b = arow["level"].split("_")[0], brow["level"].split("_")[0]
            if (level_a != level_b or arow["rep"] != brow["rep"] or
                    (level_a == "L0" and arow["level"] != brow["level"])):
                raise RuntimeError("variant row ordering differs")
            for slot in range(int(level_a[1]) + 1):
                av = arow["kv_resident"]["busy_per_slot_min"].get(str(slot), 0)
                bv = brow["kv_resident"]["busy_per_slot_min"].get(str(slot), 0)
                if not av or not bv or abs(av - bv) > 0.05 * max(av, bv):
                    raise RuntimeError("variant occupancy differs by more than 5%")
        merged = {**captures[0], "rows": [row for c in captures for row in c["rows"]],
                  "variant_runs": captures, "dedicated_server_per_variant": True}
        C.write_json(root / "a1.json", merged)
        return 0
    except Exception as exc:
        C.write_json(root / "a1.json", {"status": "failed", "rows": [], "variant_runs": captures,
                                      "error": f"{type(exc).__name__}: {exc}"})
        return 1
    finally:
        P3 = root
        LOGS, SLOTDIR = P3 / "logs", P3 / "slots"
        ACTIVE_VARIANT = "drafted"
        SHARED_NONCE = None


# ------------------------------------------------------------------ phase A0
def phase_a0(a) -> int:
    out = P3 / "a0.json"
    srv = Server("a0", a.port, prod_idle=True, debug=True)
    rec = {"schema": "p3.a0.v1", "started_at": C.now()}
    rc = 1
    try:
        srv.start()
        f = SLOTDIR / "p3-nb1.bin"
        if f.exists():
            rec["restore"] = slot_action(srv.base, 1, "restore", f.name)
        else:  # A1 did not leave a file: park a ~20k neighbour by prefill instead
            _, pool = texts()
            rec["prefill_nb"] = chat(srv.base, nb_text(pool, 1, int(20000 * CPT_EST), "a0"), 1, 1)
        rec["before"] = resident(srv.base)
        with SlotPoller(srv.base, period=1) as poll:
            rec["short_task"] = chat(srv.base, "Say hello.", 0, 64)
        rec["during"] = poll.summary()
        rec["after"] = resident(srv.base)
        rec["metrics"] = metrics(srv.base)
        purged = rec["before"]["per_slot"].get(1, 0) > 0 and rec["after"]["per_slot"].get(1, 0) == 0
        rec["idle_neighbour_purged_by_new_task"] = purged
        say(f"A0 (prod flags): slot1 before {rec['before']['per_slot'].get(1)} -> after "
            f"{rec['after']['per_slot'].get(1)} tokens; purged={purged}")
        rec["status"] = "ok"
        rc = 0
    except Exception as exc:  # noqa: BLE001
        rec["status"], rec["error"] = "failed", f"{type(exc).__name__}: {exc}"
        rec["traceback"] = traceback.format_exc()[-3000:]
        say(f"A0 FAILED: {rec['error']}")
    finally:
        srv.stop()
        rec["server"] = srv.rec
        rec["finished_at"] = C.now()
        C.write_json(out, rec)
    return rc


# ------------------------------------------------------------------ phase B
def b_plan(a) -> list[tuple[str, bool, int, str]]:
    npp = a.b_npp
    remaining = a.budget_min - elapsed_min()

    def est(n):  # minutes: 2 loads + kvu(npl4) + no-kvu(npl4) prefill at ~500 tok/s + decode/teardown
        return (2 * 45 + (4 * n + 4 * n) / 500 + 2 * 20) / 60

    while npp > 16384 and est(npp) > remaining:
        npp //= 2
    if est(npp) > remaining + 2:
        return []
    return [("kvu", True, npp, "4"), ("nokvu", False, npp, "4")]


def run_bench(name: str, argv: list[str], timeout_s: float) -> dict:
    set_env(False)
    log = LOGS / f"b.{name}.log"
    rec = {"argv": SB.PREFIX + argv, "vram_before": C.vram_now()}
    sampler = C.VramSampler(LOGS / f"b.{name}.vram.jsonl").start()
    proc = C.start_own(SB.PREFIX + argv, log)
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
    out = P3 / "b.json"
    plan = b_plan(a)
    rec = {"schema": "p3.b.v1", "started_at": C.now(), "elapsed_min_at_start": round(elapsed_min(), 1),
           "plan": [(n, k, p, l) for n, k, p, l in plan], "runs": {}}
    if not plan:
        rec["status"] = "skipped (budget guard)"
        C.write_json(out, rec)
        say("B skipped by budget guard")
        return 0
    rc = 0
    for name, kvu, npp, npls in plan:
        say(f"B {name}: npp {npp} ntg 64 npl {npls}")
        r = run_bench(name, bench_argv(kvu, npp, 64, npls), timeout_s=20 * 60)
        rec["runs"][name] = r
        for row in r["rows"]:
            say(f"B {name}: pl {row['pl']} n_kv {row['n_kv']} S_PP {row['speed_pp']:.1f} S_TG {row['speed_tg']:.2f}")
        if not r["rows"]:
            rc = 1
        C.write_json(out, rec)
    rec["status"] = "ok" if rc == 0 else "failed"
    C.write_json(out, rec)
    return rc


# ------------------------------------------------------------------ report
def mean(xs):
    xs = [x for x in xs if x]
    return round(sum(xs) / len(xs), 3) if xs else None


def phase_report(_a) -> int:
    L = ["# P3: unified-KV decode cost vs occupied pool (MI210, v10 ffc1bac82, Qwen3.8-27B Q8_0 + DFlash2)", ""]
    res = {"schema": "p3.result.v1", "at": C.now()}
    a1 = json.loads((P3 / "a1.json").read_text()) if (P3 / "a1.json").exists() else None
    if a1:
        rows = a1.get("rows", [])
        levels = list(dict.fromkeys(r["level"] for r in rows))
        tab = {}
        for lv in levels:
            for var in ("drafted", "nodraft"):
                rr = [r for r in rows if r["level"] == lv and r["variant"] == var]
                tab[(lv, var)] = {"tps": mean([r["decode_tps"] for r in rr]),
                                  "acc": mean([r["draft_acc"] for r in rr]),
                                  "res": max((r["kv_resident"]["resident_max"] or 0) for r in rr) if rr else None,
                                  "decode_only": all(r["decode_only"] for r in rr)}
        base = {v: mean([tab.get((lv, v), {}).get("tps") for lv in ("L0_base", "L0_after")]) for v in ("drafted", "nodraft")}
        L += [f"## A1 parked neighbours (resident, idle; --no-cache-idle-slots), status {a1.get('status')}", "",
              f"P = {a1.get('p_tokens')} tok on slot 0; park mode {a1.get('park_mode_effective')}; pool {POOL} cells.", "",
              "| level | resident max (frac pool) | drafted tok/s | Δ vs base | acc | no-draft tok/s | Δ vs base | decode-only |",
              "|---|---|---|---|---|---|---|---|"]
        for lv in levels:
            d, n = tab.get((lv, "drafted"), {}), tab.get((lv, "nodraft"), {})

            def dl(x, b):
                return f"{(x - b) / b * 100:+.1f}%" if x and b else "-"
            L.append(f"| {lv} | {d.get('res')} ({round((d.get('res') or 0) / POOL, 3)}) | {d.get('tps')} | "
                     f"{dl(d.get('tps'), base['drafted'])} | {d.get('acc')} | {n.get('tps')} | "
                     f"{dl(n.get('tps'), base['nodraft'])} | {d.get('decode_only') and n.get('decode_only')} |")
        top = [lv for lv in levels if lv.startswith("L3")]
        loss = {}
        for v in ("drafted", "nodraft"):
            x = tab.get((top[0], v), {}).get("tps") if top else None
            loss[v] = round((base[v] - x) / base[v] * 100, 2) if x and base[v] else None
        drift = None
        b0, b1 = tab.get(("L0_base", "nodraft"), {}).get("tps"), tab.get(("L0_after", "nodraft"), {}).get("tps")
        if b0 and b1:
            drift = round((b1 - b0) / b0 * 100, 2)
        peak_res = max([r.get("sum", 0) for r in a1.get("residency", [])] +
                       [(r["kv_resident"]["resident_max"] or 0) for r in rows] or [0])
        res["a1"] = {"base_tps": base, "loss_pct_at_L3": loss, "aba_drift_nodraft_pct": drift,
                     "peak_resident_tokens": peak_res, "peak_resident_frac": round(peak_res / POOL, 4),
                     "log_scan": (a1.get("server") or {}).get("log_scan"),
                     "vram_peak_gib": ((a1.get("server") or {}).get("vram") or {}).get("peak_used_gib"),
                     "own_pid_peak_vram_gib": ((a1.get("server") or {}).get("vram") or {}).get("own_pid_peak_vram_gib")}
        L += ["", f"- Baseline (mean L0_base, L0_after): drafted {base['drafted']}, no-draft {base['nodraft']} tok/s; "
              f"ABA drift (no-draft) {drift}%.",
              f"- **Decode loss at the >=300k fill (L3)**: no-draft {loss['nodraft']}%, drafted {loss['drafted']}%.",
              f"- Peak resident KV tokens {peak_res} / {POOL} = {round(peak_res / POOL, 3)} (from /slots, sampled during decodes).",
              f"- Server log counts: {res['a1']['log_scan']}",
              f"- VRAM peak {res['a1']['vram_peak_gib']} GiB device, own pid {res['a1']['own_pid_peak_vram_gib']} GiB."]
        v = loss.get("nodraft")
        verdict = ("UNMEASURED" if v is None else
                   f"P5 trigger (>=5%): {'MET' if v >= 5 else 'not met'}; split-per-slot trigger (>=15% at >=300k): "
                   f"{'MET' if v >= 15 else 'not met'}")
        res["verdict"] = verdict
        L += ["", f"**Verdict (no-draft isolates attention): {verdict}.**"]
    a0 = json.loads((P3 / "a0.json").read_text()) if (P3 / "a0.json").exists() else None
    if a0:
        res["a0"] = {k: a0.get(k) for k in ("idle_neighbour_purged_by_new_task", "before", "after", "status")}
        res["a0"]["log_scan"] = (a0.get("server") or {}).get("log_scan")
        L += ["", "## A0 production flags (cache_idle_slots default on)", "",
              f"- idle neighbour purged when another slot starts a task: **{a0.get('idle_neighbour_purged_by_new_task')}** "
              f"(slot 1 {((a0.get('before') or {}).get('per_slot') or {}).get('1', ((a0.get('before') or {}).get('per_slot') or {}).get(1))}"
              f" -> {((a0.get('after') or {}).get('per_slot') or {}).get('1', ((a0.get('after') or {}).get('per_slot') or {}).get(1))} tokens)",
              f"- log scan: {res['a0']['log_scan']}"]
    b = json.loads((P3 / "b.json").read_text()) if (P3 / "b.json").exists() else None
    if b:
        L += ["", f"## B llama-batched-bench (no drafter), status {b.get('status')}", "",
              "| config | pl | n_kv | S_PP t/s | S_TG t/s | VRAM own peak GiB |", "|---|---|---|---|---|---|"]
        res["b"] = {}
        for name, r in (b.get("runs") or {}).items():
            for row in r.get("rows", []):
                L.append(f"| {name} | {row['pl']} | {row['n_kv']} | {row['speed_pp']:.1f} | {row['speed_tg']:.2f} | "
                         f"{(r.get('vram') or {}).get('own_pid_peak_vram_gib')} |")
                res["b"][f"{name}.pl{row['pl']}"] = {"n_kv": row["n_kv"], "s_pp": row["speed_pp"], "s_tg": row["speed_tg"]}
        k4, n4 = res["b"].get("kvu.pl4"), res["b"].get("nokvu.pl4")
        if k4 and n4:
            res["b"]["kvu_vs_nokvu_tg_pct"] = round((k4["s_tg"] - n4["s_tg"]) / n4["s_tg"] * 100, 2)
            L.append(f"\n- npl4 concurrent decode, -kvu vs -no-kvu S_TG: {res['b']['kvu_vs_nokvu_tg_pct']:+.2f}%")
    C.write_json(P3 / "p3_result.json", res)
    (P3 / "report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


# ------------------------------------------------------------------ dry run
def dry(a) -> int:
    meas, pool = texts()
    print(f"  results -> {P3}/ (a1.json, a0.json, b.json, p3_result.json, report.md, logs/*.server.log)")
    print(f"  env: {' '.join(f'{k}={v}' for k, v in SB.STACK_ENV.items())} LD_LIBRARY_PATH={C.BIN}:/opt/rocm/lib:...")
    if a.phase in ("all", "a1"):
        argv, notes = server_argv(a.port, prod_idle=False, debug=False)
        print(f"  [A1] argv source {ARGV_FILE}; transforms: {'; '.join(notes)}")
        print("  [A1] cmd: " + " ".join(SB.PREFIX + argv) + f"  > {LOGS}/a1.server.log")
        print(f"  [A1] measurement prompt P: '[p3 meas <nonce>]' + C2+C4[:{int(MEAS_TOK * CPT_EST)} chars] "
              f"(~{MEAS_TOK} tok; source {len(meas)} chars ~{int(len(meas) / CPT_EST)} tok) + TASK, id_slot 0")
        print(f"  [A1] neighbours: '[p3 neighbour k <nonce>]' + rotate(C1,C3,C5,C6,C7 = {len(pool)} chars "
              f"~{int(len(pool) / CPT_EST)} tok, offset k*{len(pool) // 3})[:~{NB_TOK} tok], id_slot k, max_tokens 1")
        print(f"  [A1] park mode {a.park_mode}: nb1 prefill -> POST /slots/1?action=save p3-nb1.bin -> "
              "POST /slots/{2,3}?action=restore p3-nb1.bin (fallback: prefill distinct text)")
        print(f"  [A1] plan: warmup(64) -> prime P ({GEN} tok, pays prefill) -> L0_base -> park nb1 -> L1 -> nb2 -> L2 "
              "-> nb3 -> L3 -> erase slots 1-3 -> L0_after")
        print(f"  [A1] two sequential dedicated server lifecycles (drafted then nodraft); 2 requests per level; {GEN} tok temp0 top_k1; "
              "/slots polled every 2 s during each request; expected fills ~58k/158k/258k/358k of 393216")
    if a.phase in ("all", "a0"):
        argv, notes = server_argv(a.port, prod_idle=True, debug=True)
        print(f"  [A0] transforms: {'; '.join(notes)}")
        print("  [A0] cmd: LLAMA_KV_CACHE_DEBUG=1 " + " ".join(SB.PREFIX + argv) + f"  > {LOGS}/a0.server.log")
        print("  [A0] plan: restore p3-nb1.bin -> slot 1; /slots; short task (64 tok) on slot 0 with /slots @1 s; "
              "/slots after -> purged iff slot1 n_prompt_tokens >0 -> 0")
    if a.phase in ("all", "b"):
        plan = b_plan(a) or [("(budget guard would skip B)", True, a.b_npp, "4")]
        for name, kvu, npp, npls in plan:
            print(f"  [B {name}] " + " ".join(SB.PREFIX + bench_argv(kvu, npp, 64, npls)) + f"  > {LOGS}/b.{name}.log")
        print(f"  [B] budget guard: npp halves (min 16384) until est fits budget {a.budget_min} min minus elapsed")
    print(f"  [report] {P3}/report.md + p3_result.json (loss% at L3 no-draft/drafted vs mean(L0_base,L0_after); "
          "P5 >=5%, split-per-slot >=15%)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all", choices=["all", "a1", "a0", "b", "report"])
    ap.add_argument("--port", type=int, default=18084)
    ap.add_argument("--park-mode", default="restore", choices=["restore", "prefill"])
    ap.add_argument("--budget-min", type=float, default=30)
    ap.add_argument("--b-npp", type=int, default=32768)
    ap.add_argument("--keep-slot-file", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        return dry(a)
    for d in (P3, LOGS, SLOTDIR):
        d.mkdir(parents=True, exist_ok=True)
    rc = 0
    if a.phase in ("all", "a1"):
        rc |= phase_a1(a)
        if rc:
            return rc  # Never start another server after a failed or unverified teardown.
    if a.phase in ("all", "a0"):
        rc |= phase_a0(a)
    if not a.keep_slot_file and not a.phase in ("all", "a1"):
        for f in SLOTDIR.glob("p3-nb*.bin"):
            say(f"removing slot file {f} ({f.stat().st_size / 2**30:.1f} GiB)")
            f.unlink()
    if a.phase in ("all", "b"):
        rc |= phase_b(a)
    phase_report(a)
    say(f"done rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
