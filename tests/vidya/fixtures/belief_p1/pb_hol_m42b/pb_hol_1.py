#!/usr/bin/env python3
"""PB-HOL-1 (M4.2b copy) — M4.2b edits (2026-10-24, workspace-f8; copied from ../m4-srpf-pbhol-2a/pb_hol_1.py, sha256 8d3b7f23...8923):
  * phase off512ch = off512 on the CHAMPION image (--champion-image), same -b/-ub 512, same arm order, no M4 flags;
  * --c-reps N: N solo shorts (C) at the start AND at the end of every load (default 1 = the M4.2/M4.2a order, unchanged);
  * --m4-bin default = the store copy kernels/builds/gpu-20261023-c6ca031ac-m4 (byte-identical to the M4.1 build).
  Nothing else changed: collision protocol, prompts, validity fields, proofs, estimate model.
--- M4.2 docstring follows ---
PB-HOL-1 (M4.2 copy) — slot-order head-of-line collision probe for llama-server's pending-prompt loop.

COPY of /mnt/raid0/llm/tmp/pb-hol-1/pb_hol_1.py (the original is untouched), edited 2026-10-23 by workspace-f8 for M4.2: measures the M4
candidate (--prefill-order srpf / --prefill-contend-cap) instead of the budget-on phase. Differences from the original:
  * named PHASES (srpf512, srpf2048, off512, srpf2048cap0) each with its own -b/-ub (--batch name=N overrides) and server args;
    --server-extra-args is appended to EVERY phase's server argv; the budget-on phase and the feeder arms are not used here;
  * completion phases comp-champion / comp-m4off: a fixed-seed temp-0 set, run twice per server, for the byte-identity check;
  * binary = the M4.1 build (--m4-bin); champion image (--champion-image) only for comp-champion;
  * per-server proofs: HIP graphs ON from /proc/<pid>/environ, own-pid KFD VRAM >= 40 GiB residency, 60 GiB own-pid ceiling (GPU-LEAK-1);
  * the verdict is computed by verdict.py from the jsonl rows (PREDECLARATION.md), not by this file.
--- original docstring follows ---

Hypothesis (server-context.cpp ~3205-3232 @ ffc1bac82): the pending-prompt batch is filled in fixed slot-index order
and `if (!add_ok || batch.size() >= n_batch) return;` stops every LATER slot once the batch is full, so a short
prompt in a HIGHER slot than an in-flight long prefill waits for the whole remaining prefill.

Arms (-np 3, id_slot pinned, cache_prompt=false, slots erased between runs):
  A  short slot BELOW long slot   (long -> slot 2, short -> slot 0)
  B  short slot ABOVE long slot   (long -> slot 0, short -> slot 2)
  C  solo short reference on the idle server (start and end)
Order: C, A,B,A,B,A,B, C.  Predeclared rule: B_median >= 2 x A_median short TTFT => CONFIRMED, else NOT_REPRODUCED.
Budget-on arms (pb512, second server launch, -b/-ub 2048): A-on, B-on with a feeder decoding in slot 1, and B-on-nodec.

Reuses kpf18_gate.py (Server start/stop-by-PID/verify-dead, KFD VRAM sampler, linkage check, mi210_0 device claim).
Never signals anything but its own server child. --dry-run starts nothing, sends nothing, takes no claim.
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import shlex
import signal
import statistics
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KPF_DIR = Path("/mnt/raid0/llm/tmp/kpf-p1-20261004/kpf18")
sys.dont_write_bytecode = True
sys.path.insert(0, str(KPF_DIR))
import kpf18_gate as K  # noqa: E402

SCHEMA = "epyc.pbhol1.run.v1"
M4_BIN = Path("/mnt/raid0/llm/kernels/builds/gpu-20261023-c6ca031ac-m4/bin/llama-server")   # store copy of the M4.1 build (c6ca031ac)
CHAMPION_IMG = Path("/mnt/raid0/llm/kernels/builds/gpu-20261023-141e4bcf5-lbh/bin/llama-server")   # M4's base image, no M4 flags
CHAMPION = M4_BIN
ARGV_FILE = Path("/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt")
PROMPT_SET = Path("/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/prompt_set.jsonl")
LONG_GROUP, SHORT_GROUP, SHORT_SUFFIX = 6, 3, 0   # 72k trunk of group 6 truncated; 512-token suffix of group 3 truncated
LONG_TOKENS, SHORT_TOKENS, COLLIDE_FRAC = 64000, 128, 0.5
N_PRED_LONG, N_PRED_SHORT = 4, 8
NP, PORT = 3, 18090
ARMS = {"A": (0, 2), "B": (2, 0)}          # arm -> (short slot, long slot)
FEED_SLOT = 1                               # unused here (no feeder arms); run_collision keeps the code path
ORDER_OFF = ["C", "A", "B", "A", "B", "A", "B", "C"]    # every candidate phase: 3 reps of A and B, C solo at start and end
# name -> (-b = -ub, extra server args). srpf-2048 uses the default --prefill-contend-cap (512); cap0 turns the cap off.
PHASES = {
    "srpf512": ("512", ["--prefill-order", "srpf"]),
    "srpf2048": ("2048", ["--prefill-order", "srpf"]),
    "off512": ("512", []),
    "srpf2048cap0": ("2048", ["--prefill-order", "srpf", "--prefill-contend-cap", "0"]),
    "off512ch": ("512", []),          # M4.2b: off512 on the champion image
}
CHAMPION_PHASES = {"off512ch"}         # M4.2b: PHASES entries that run on --champion-image
OFF_PHASES = {"off512", "off512ch"}    # the slow-B (slot-order HOL) estimate applies
COMP_PHASES = {"comp-champion": ("champion", "512", []), "comp-m4off": ("m4", "512", [])}   # -b 512, NO M4 flags
COMP_N_PRED, COMP_PASSES = 96, 2
PROG_RE = re.compile(r"id\s+(\d+) \| task (\d+) \| prompt processing, n_tokens =\s*(\d+), progress = ([0-9.]+)")
LOGTS_RE = re.compile(r"^(\d+\.\d+) ")
RULE = "see PREDECLARATION.md / verdict.py (B_median/A_median < 2.0 under srpf at -b 512 and 2048; off512 B/A in 22.05 +-10%; off completions byte-identical)"
DEFERRED = []
RES_MIN_GIB = 40.0      # 27B Q8 + KV on ROCm0 peaks ~48-51 GiB own VRAM; a CPU fallback / partial offload stays far below 40
GIB = 1024 ** 3
# estimate model (seconds)
LOAD_S, LINK_S, STOP_S = 115.0, 5.0, 20.0
COMP_PASS_S = 100.0     # 6 prompts, ~36.6K prompt tokens + 7 x 96 decoded tokens




def parse_deadline(s: str) -> float:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return float(calendar.timegm(time.strptime(s, fmt)))
        except ValueError:
            continue
    if re.fullmatch(r"\d{1,2}:\d\d", s):  # HH:MM today (UTC), rolled to tomorrow if already past
        h, m = map(int, s.split(":"))
        t = time.gmtime()
        d = float(calendar.timegm((t.tm_year, t.tm_mon, t.tm_mday, h, m, 0)))
        return d if d > time.time() else d + 86400
    raise SystemExit(f"bad --deadline {s!r}: use 2026-10-21T16:40:00Z or HH:MM (UTC)")


def load_prompts(path: Path) -> tuple[list[int], list[int], dict]:
    long_ids = short_ids = None
    for ln in path.read_text().splitlines():
        r = json.loads(ln)
        if r.get("kind") == "trunk" and r["group"] == LONG_GROUP:
            long_ids = r["ids"][:LONG_TOKENS]
        elif r.get("kind") == "pair" and r["group"] == SHORT_GROUP and r["suffix_index"] == SHORT_SUFFIX:
            short_ids = r["suffix_ids"][:SHORT_TOKENS]
    if not long_ids or len(long_ids) < LONG_TOKENS or not short_ids or len(short_ids) < SHORT_TOKENS:
        raise SystemExit(f"prompt set {path} lacks group {LONG_GROUP} trunk >= {LONG_TOKENS} or group {SHORT_GROUP} suffix")
    meta = {"path": str(path), "sha256": K.sha256_file(path), "long_group": LONG_GROUP, "long_tokens": len(long_ids),
            "short_group": SHORT_GROUP, "short_suffix_index": SHORT_SUFFIX, "short_tokens": len(short_ids),
            "first_tokens_distinct": long_ids[0] != short_ids[0]}
    return long_ids, short_ids, meta


def est_long_s() -> float:
    return K.pf_s(LONG_TOKENS, 0) + 3.0


def plan_estimate(phases: list[str]) -> tuple[float, list[tuple[str, float]]]:
    L = est_long_s()
    A = 0.5 * L + 15       # long aborted once the short has answered (measured A-off ~52 s: conservative)
    steps = []
    for ph in phases:
        if ph in COMP_PHASES:
            steps += [(f"{ph}: load + linkage + residency", LOAD_S + LINK_S + 10),
                      (f"{ph}: {COMP_PASSES} passes of the 6-prompt completion set", COMP_PASS_S * COMP_PASSES),
                      (f"{ph}: stop by PID + verify dead", STOP_S)]
            continue
        steps += [(f"{ph} (-b/-ub {PHASES[ph][0]} {' '.join(PHASES[ph][1]) or 'no M4 flags'}): load + linkage + residency", LOAD_S + LINK_S + 10),
                  (f"{ph}: solo long calibration (64K prefill)", L + 5)]
        for i, a in enumerate(ORDER_OFF):
            B = (L + 10) if ph in OFF_PHASES else A     # off: the short waits out the whole remaining prefill; srpf: it should not
            steps.append((f"{ph} run {i + 1}: " + ("C solo short" if a == "C" else f"arm {a} collision"),
                          3 if a == "C" else (A if a == "A" else B) + 5))
        steps.append((f"{ph}: stop by PID + verify dead", STOP_S))
    return sum(s for _, s in steps), steps


def port_owner_ok(pid: int, port: int) -> tuple[bool, str]:
    """True iff `pid` holds the LISTEN socket for `port` (inode from /proc/net/tcp{,6} matched against /proc/pid/fd)."""
    inodes = set()
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            for ln in Path(f).read_text().splitlines()[1:]:
                p = ln.split()
                if len(p) > 9 and p[3] == "0A" and int(p[1].rsplit(":", 1)[1], 16) == port:
                    inodes.add(p[9])
        except (OSError, ValueError):
            pass
    if not inodes:
        return False, f"nothing listening on {port}"
    try:
        mine = {os.readlink(f"/proc/{pid}/fd/{fd}") for fd in os.listdir(f"/proc/{pid}/fd")}
    except OSError as exc:
        return False, f"cannot read /proc/{pid}/fd: {exc}"
    hit = [i for i in inodes if f"socket:[{i}]" in mine]
    return (bool(hit), f"listen inodes {sorted(inodes)}; pid {pid} owns {hit}")


class LogTail:
    """Reads the server log (timestamped by the runner's pump) from a byte offset."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def size(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return 0

    def lines_from(self, off: int) -> list[str]:
        try:
            with open(self.path, "rb") as fh:
                fh.seek(off)
                return fh.read().decode(errors="replace").splitlines()
        except OSError:
            return []

    def progress(self, off: int, slot: int) -> tuple[int, float, float] | None:
        """latest (n_tokens, progress_frac, log_epoch) of `slot`'s prompt processing after offset."""
        best = None
        for ln in self.lines_from(off):
            m = PROG_RE.search(ln)
            if m and int(m.group(1)) == slot:
                t = LOGTS_RE.match(ln)
                best = (int(m.group(3)), float(m.group(4)), float(t.group(1)) if t else 0.0)
        return best


class Probe:
    def __init__(self, args) -> None:
        self.args = args
        self.out = Path(args.out)
        self.rows = K.Jsonl(self.out / "pb_hol_1.jsonl")
        self.srv: K.Server | None = None      # current phase server
        self.servers: list[K.Server] = []     # every server launched (for summary / stop)
        self.client: K.Client | None = None
        self.log: LogTail | None = None
        self.phase = None
        self.cal_s: float | None = None
        self.deadline_hit = threading.Event()
        self.stop_lock = threading.Lock()
        self.long_ids, self.short_ids, self.ps_meta = load_prompts(Path(args.prompt_set))
        self.decoder_ids = load_decoder(Path(args.prompt_set))
        self.comp_prompts = load_comp_prompts(Path(args.prompt_set))

    # ---- lifecycle
    def stop_server(self) -> None:
        with self.stop_lock:
            for srv in self.servers:
                if getattr(srv, "_pbhol_stopped", False):
                    continue
                srv._pbhol_stopped = True
                try:
                    srv.stop()
                except Exception as exc:  # noqa: BLE001
                    print(f"[pbhol] stop failed: {exc}", flush=True)
                    self.rows.add({"kind": "stop_error", "label": srv.label, "err": str(exc)})
                if srv.stop_rec:
                    self.rows.add({"kind": "server_stop", "label": srv.label, **srv.stop_rec})

    def watchdog(self) -> None:
        while time.time() < self.args.deadline_epoch:
            if self.deadline_hit.wait(5):
                return
        print("[pbhol] DEADLINE reached: stopping server by PID", flush=True)
        self.deadline_hit.set()
        self.stop_server()

    def check(self) -> None:
        if self.deadline_hit.is_set() or time.time() >= self.args.deadline_epoch:
            raise K.Abort("deadline reached")
        if self.srv and self.srv.sampler and self.srv.sampler.abort.is_set():
            raise K.Abort(f"VRAM: {self.srv.sampler.abort_reason}")
        if self.srv and self.srv.proc and self.srv.proc.poll() is not None:
            raise K.Abort(f"server died rc={self.srv.proc.returncode}")
        w = K.window_status()
        if w.get("preempt_requested_at"):
            raise K.Abort(f"GPU window preempt requested at {w['preempt_requested_at']}")

    def start_phase(self, name: str, binary: Path, batch: str, extra: list[str]) -> None:
        self.check()
        ctx, srv = build_server(self.args, self.out, name, binary, batch, extra)
        self.servers.append(srv)
        self.srv, self.phase = srv, name
        srv.start()           # port-free check, no foreign KFD, linkage, residency read-back (kpf18 Server)
        self.client, self.log = ctx.client, LogTail(srv.log)
        ok, why = port_owner_ok(srv.proc.pid, self.args.port)
        self.rows.add({"kind": "port_ownership", "phase": name, "ok": ok, "detail": why, "pid": srv.proc.pid,
                       "argv": srv.argv, "binary": str(binary), "binary_sha256": K.sha256_file(binary)})
        if not ok:
            raise K.Abort(f"port {self.args.port} not owned by our pid {srv.proc.pid}: {why}")
        # HIP graphs ON/OFF from the server's own environ (production condition = graphs ON) + HSA knob
        try:
            env = dict(x.split("=", 1) for x in Path(f"/proc/{srv.proc.pid}/environ").read_bytes().decode(errors="replace").split("\0") if "=" in x)
        except OSError as exc:
            raise K.Abort(f"cannot read /proc/{srv.proc.pid}/environ: {exc}")
        graphs = "OFF" if "GGML_CUDA_DISABLE_GRAPHS" in env else "ON"
        gp = {"kind": "graphs_proof", "phase": name, "pid": srv.proc.pid, "graphs": graphs,
              "GGML_CUDA_DISABLE_GRAPHS": env.get("GGML_CUDA_DISABLE_GRAPHS"),
              "HSA_OVERRIDE_CPU_AFFINITY_DEBUG": env.get("HSA_OVERRIDE_CPU_AFFINITY_DEBUG"), "source": "/proc/<pid>/environ"}
        self.rows.add(gp)
        if graphs != "ON":
            raise K.Abort(f"HIP graphs OFF in server environ ({gp['GGML_CUDA_DISABLE_GRAPHS']}): the production condition is graphs ON")
        if env.get("HSA_OVERRIDE_CPU_AFFINITY_DEBUG") != "0":
            raise K.Abort("HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0 missing from the server environ")
        # residency by own-pid KFD VRAM (never log text)
        peak = srv.sampler.own_peak if srv.sampler else 0
        self.rows.add({"kind": "residency", "phase": name, "pid": srv.proc.pid, "own_vram_gib": round(peak / GIB, 3),
                       "min_gib": RES_MIN_GIB, "ok": peak >= RES_MIN_GIB * GIB, "n_own_nonzero": srv.sampler.n_own_nonzero if srv.sampler else 0})
        if peak < RES_MIN_GIB * GIB:
            raise K.Abort(f"residency: own pid KFD VRAM {peak / GIB:.2f} GiB < {RES_MIN_GIB} GiB (not resident on the MI210)")

    def end_phase(self) -> None:
        self.stop_server()
        self.client = None
        self.srv = None   # 2026-10-21 fix: check() at the next start_phase read the stopped server as 'died'

    def wait_idle(self, tmo: float = 30.0) -> None:
        t0 = time.time()
        while time.time() - t0 < tmo:
            if not any(x.get("is_processing") for x in self.client.slots()):
                return
            time.sleep(0.5)

    def erase_all(self) -> None:
        self.wait_idle()
        for s in range(NP):
            self.client.erase(s)
        busy = [x.get("id") for x in self.client.slots() if x.get("is_processing")]
        if busy:
            raise K.Abort(f"slots still busy after erase: {busy}")

    def short_req(self, slot: int) -> dict:
        body = K.body_for(self.short_ids, N_PRED_SHORT, slot, fork=None, cache=False, n_probs=0)
        return self.client.stream(body, timeout=900)

    def run_solo(self, tag: str, rep: int, slot: int = 0) -> dict:
        self.check()
        self.erase_all()
        r = self.short_req(slot)
        rec = {"kind": "run", "phase": self.phase, "budget": False, "arm": "C", "rep": rep, "tag": tag, "short_slot": slot,
               "long_slot": None, "short_ttft_ms": r.get("ttft_ms"), "short_t_send": r["t_send"],
               "short_http": r.get("http"), "short_timings": r.get("timings"), "short_error": r.get("error")}
        self.rows.add(rec)
        print(f"[pbhol] C{rep}: short TTFT {rec['short_ttft_ms']} ms", flush=True)
        return rec

    def calibrate(self) -> None:
        self.check()
        self.erase_all()
        body = K.body_for(self.long_ids, N_PRED_LONG, 0, fork=None, cache=False, n_probs=0)
        r = self.client.stream(body, timeout=1800)
        self.cal_s = (r.get("ttft_ms") or 0) / 1000.0   # prefill duration = TTFT of the long
        self.rows.add({"kind": "calibration", "phase": self.phase, "long_ttft_s": self.cal_s, "http": r.get("http"),
                       "error": r.get("error"), "timings": r.get("timings")})
        if not self.cal_s:
            raise K.Abort(f"calibration failed: {r.get('error')}")
        print(f"[pbhol] calibration: solo 64K prefill {self.cal_s:.1f} s", flush=True)

    def run_collision(self, label: str, arm: str, rep: int, feeder: bool, budget: bool) -> dict:
        short_slot, long_slot = ARMS[arm]
        self.check()
        need = (self.cal_s or est_long_s()) * 1.1 + 40
        if self.args.deadline_epoch - time.time() < need:
            rec = {"kind": "run", "phase": self.phase, "arm": label, "rep": rep,
                   "skipped": f"insufficient time before deadline (< {need:.0f} s left)"}
            self.rows.add(rec)
            print(f"[pbhol] {label}{rep}: SKIPPED ({rec['skipped']})", flush=True)
            return rec
        self.erase_all()
        off = self.log.size()
        stop_long, stop_feed = threading.Event(), threading.Event()
        long_res: dict = {}
        feed_res: dict = {}
        feed_tokens = [0]
        th_feed = None
        if feeder:   # a third slot decoding for the whole collision (arms the decode-gated budget)
            fb = K.body_for(self.decoder_ids, 8192, FEED_SLOT, fork=None, cache=False, n_probs=0)

            def _feed():
                feed_res.update(self.client.stream(fb, stop=stop_feed, on_token=lambda n: feed_tokens.__setitem__(0, n),
                                                   timeout=1800))
            th_feed = threading.Thread(target=_feed, daemon=True)
            th_feed.start()
            t0 = time.time()
            while feed_tokens[0] < 8 and time.time() - t0 < 90 and th_feed.is_alive():
                time.sleep(0.1)
            if feed_tokens[0] < 8:
                stop_feed.set()
                raise K.Abort(f"feeder never started decoding (tokens={feed_tokens[0]}, {feed_res.get('error')})")
        long_body = K.body_for(self.long_ids, N_PRED_LONG, long_slot, fork=None, cache=False, n_probs=0)

        def _long():
            long_res.update(self.client.stream(long_body, stop=stop_long, timeout=1800))

        th = threading.Thread(target=_long, daemon=True)
        t_long = time.time()
        th.start()
        cal = self.cal_s or est_long_s()
        trigger = None
        while True:
            self.check()
            prog = self.log.progress(off, long_slot)
            if prog and prog[1] >= COLLIDE_FRAC:
                trigger = "log_progress"
                break
            if time.time() - t_long > cal * COLLIDE_FRAC * 1.3 + 15:
                trigger = "calibration_time_fallback"
                break
            if not th.is_alive():
                trigger = "long_finished_early"
                break
            time.sleep(0.05)
        try:
            slots_snap = [{k: s.get(k) for k in ("id", "is_processing", "n_ctx", "n_prompt_tokens",
                                                 "n_prompt_tokens_processed", "next_token") if k in s}
                          for s in self.client.slots()]
        except Exception as exc:  # noqa: BLE001
            slots_snap = {"err": str(exc)[:200]}
        deferred_max, stop_poll = [0.0], threading.Event()

        def _poll():
            while not stop_poll.is_set():
                try:
                    deferred_max[0] = max(deferred_max[0], self.client.metrics().get("llamacpp:requests_deferred", 0.0))
                except Exception:  # noqa: BLE001
                    pass
                stop_poll.wait(0.5)

        threading.Thread(target=_poll, daemon=True).start()
        prog_at_send = self.log.progress(off, long_slot)
        feed_at_send = feed_tokens[0]
        short = self.short_req(short_slot)
        t_first = short["t_send"] + (short.get("ttft_ms") or 0) / 1000.0
        prog_at_first = self.log.progress(off, long_slot)
        stop_poll.set()
        long_done_before_abort = not th.is_alive()
        stop_long.set()      # the short has answered: the long prefill is no longer needed
        stop_feed.set()
        th.join(timeout=60)
        if th_feed:
            th_feed.join(timeout=60)
        win = [ln for ln in self.log.lines_from(off)
               if (m := LOGTS_RE.match(ln)) and short["t_send"] - 3 <= float(m.group(1)) <= t_first + 3]
        budget_iters = [ln for ln in win if "prefill-budget" in ln]
        ivals, prev = [], None
        for ln in self.log.lines_from(off):
            m, t = PROG_RE.search(ln), LOGTS_RE.match(ln)
            if m and t and int(m.group(1)) == long_slot:
                cur = (int(m.group(3)), float(t.group(1)))
                if prev and cur[0] > prev[0] and short["t_send"] - 10 <= cur[1] <= short["t_send"]:
                    ivals.append((cur[1] - prev[1]) / ((cur[0] - prev[0]) / 512.0))
                prev = cur
        rec = {"kind": "run", "phase": self.phase, "budget": budget, "arm": label, "placement": arm, "rep": rep,
               "feeder": feeder, "short_slot": short_slot, "long_slot": long_slot, "feeder_slot": FEED_SLOT if feeder else None,
               "feeder_tokens_at_send": feed_at_send, "feeder_tokens_final": feed_tokens[0],
               "trigger": trigger, "short_t_send": short["t_send"], "short_t_first_token": t_first,
               "short_ttft_ms": short.get("ttft_ms"), "short_http": short.get("http"), "short_error": short.get("error"),
               "short_timings": short.get("timings"), "long_t_send": t_long,
               "long_ttft_ms": long_res.get("ttft_ms"), "long_finished_before_abort": long_done_before_abort,
               "long_error": long_res.get("error"),
               "long_progress_at_send": prog_at_send, "long_progress_at_short_first_token": prog_at_first,
               "requests_deferred_max": deferred_max[0], "slots_at_collision": slots_snap,
               "iter_interval_s_per_512": round(statistics.median(ivals), 4) if ivals else None,
               "budget_iter_lines_in_window": len(budget_iters),
               "server_log_window": win[:120], "server_log_window_truncated": len(win) > 120}
        self.rows.add(rec)
        print(f"[pbhol] {label}{rep}: short slot {short_slot} long slot {long_slot} trigger {trigger} "
              f"long@{prog_at_send[1] if prog_at_send else None} -> short TTFT {rec['short_ttft_ms']} ms", flush=True)
        return rec

    # ---- summary
    # ---- completion set (byte-identity of the off path) --------------------------------------------------
    def detok(self, toks: list[int]) -> str | None:
        st, body = self.client._req("POST", "/detokenize", {"tokens": toks}, timeout=120)
        return body.get("content") if st == 200 and isinstance(body, dict) else None

    def run_completion_pass(self, label: str, npass: int) -> None:
        import hashlib
        for name, ids in self.comp_prompts:
            self.check()
            if name == "pair4k":      # two prompts at once on slots 0 and 2: exercises the multi-slot batch fill of the changed loop
                self.erase_all()
                res: dict = {}

                def _one(nm, slot, pids):
                    res[nm] = self.client.complete(K.body_for(pids, COMP_N_PRED, slot, fork=None, cache=False, n_probs=0), timeout=900)
                ths = [threading.Thread(target=_one, args=(f"pair4k.{i}", sl, p)) for i, (sl, p) in enumerate(zip((0, 2), ids))]
                [t.start() for t in ths]
                [t.join() for t in ths]
                items = sorted(res.items())
            else:
                self.erase_all()
                items = [(name, self.client.complete(K.body_for(ids, COMP_N_PRED, 0, fork=None, cache=False, n_probs=0), timeout=900))]
            for nm, r in items:
                toks = r.get("tokens") or []
                txt = self.detok(toks) if toks else None
                self.rows.add({"kind": "completion", "phase": self.phase, "label": label, "pass": npass, "prompt": nm,
                               "http": r.get("http"), "error": r.get("error"), "n_tokens": len(toks), "tokens": toks, "text": txt,
                               "tokens_sha256": hashlib.sha256(json.dumps(toks).encode()).hexdigest(),
                               "text_sha256": hashlib.sha256(txt.encode()).hexdigest() if txt is not None else None})
                print(f"[pbhol] completion {label} pass {npass} {nm}: http {r.get('http')} {len(toks)} tokens", flush=True)

    # ---- summary
    def summarize(self, status: str) -> dict:
        f = self.out / "pb_hol_1.jsonl"
        rows = [json.loads(ln) for ln in f.read_text().splitlines()] if f.exists() else []
        runs = [r for r in rows if r.get("kind") in ("run", "calibration") ]
        by: dict = {}
        for r in rows:
            if r.get("kind") == "run" and r.get("short_ttft_ms") is not None and not r.get("skipped"):
                by.setdefault(r["arm"] if r["arm"] != "C" else f"C-{r['phase']}", []).append(r["short_ttft_ms"])
        arms = {k: {"ttft_ms": v, "median_ms": statistics.median(v)} for k, v in sorted(by.items())}
        s = {"schema": SCHEMA, "status": status, "verdict": "see verdict.py (PREDECLARATION.md)", "arms": arms,
             "n_rows": len(rows), "n_runs_attempted": sum(1 for r in rows if r.get("kind") == "run"),
             "calibrations": [{"phase": r["phase"], "long_ttft_s": r.get("long_ttft_s")} for r in rows if r.get("kind") == "calibration"],
             "graphs_proofs": [r for r in rows if r.get("kind") == "graphs_proof"],
             "residency": [r for r in rows if r.get("kind") == "residency"],
             "prompts": self.ps_meta, "binaries": sorted({str(x.binary) for x in self.servers}),
             "servers": [{"label": x.label, "binary": str(x.binary), "binary_sha256": K.sha256_file(x.binary),
                          "readback": x.readback, "linkage": x.linkage,
                          "vram": x.sampler.summary() if x.sampler else None, "stop": x.stop_rec} for x in self.servers],
             "finished": K.now_iso()}
        K.write_json(self.out / "summary.json", s)
        md = [f"# PB-HOL-1 / M4.2 phase summary ({s['finished']})", "", f"status: {status}", "", "| arm | short TTFT ms (reps) | median |", "|---|---|---|"]
        md += [f"| {k} | {v['ttft_ms']} | {v['median_ms']} |" for k, v in arms.items()]
        (self.out / "summary.md").write_text("\n".join(md) + "\n")
        return s


def load_comp_prompts(path: Path) -> list[tuple[str, object]]:
    """Fixed completion set (names are part of the predeclaration): 5 single prompts of growing length + one 2-slot pair."""
    trunk, pair = {}, {}
    for ln in path.read_text().splitlines():
        r = json.loads(ln)
        if r.get("kind") == "trunk":
            trunk[r["group"]] = r["ids"]
        elif r.get("kind") == "pair":
            pair[(r["group"], r["suffix_index"])] = r["suffix_ids"]
    out = [("short128", pair[(3, 0)][:128]), ("p512", pair[(3, 0)]), ("p4000", pair[(3, 2)]), ("t8000", trunk[0][:8000]),
           ("t16000", trunk[6][:16000]), ("pair4k", [trunk[1][:4000], trunk[2][:4000]])]
    for nm, ids in out:
        if nm != "pair4k" and not ids:
            raise SystemExit(f"completion prompt {nm} empty in {path}")
    return out


def load_decoder(path: Path) -> list[int]:
    for ln in path.read_text().splitlines():
        if '"kind":"decoder"' in ln:
            return json.loads(ln)["ids"]
    raise SystemExit(f"no decoder prompt in {path}")


def build_server(args, out: Path, name: str, binary: Path, batch: str, extra: list[str]) -> tuple[K.Ctx, K.Server]:
    argv, _ = K.parse_argv_file(Path(args.argv_file))
    argv = K.set_flag(argv, ("-np", "--parallel"), str(NP))
    argv = K.set_flag(argv, ("-b", "--batch-size"), batch)
    argv = K.set_flag(argv, ("-ub", "--ubatch-size"), batch)
    extra = list(extra) + shlex.split(args.server_extra_args or "")
    ctx = K.Ctx(args, None, argv, args.launch_prefix.split(), {"source": str(args.argv_file)})
    ctx.out = out
    return ctx, K.Server(ctx, f"pbhol-{name}-{K.utc_tag()}", Path(binary), None, extra_args=extra)




def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deadline", required=True, help="hard stop, e.g. 2026-10-21T16:40:00Z or HH:MM (UTC)")
    ap.add_argument("--m4-bin", default=str(M4_BIN), help="the M4.1 build's llama-server (phases srpf*/off512/comp-m4off)")
    ap.add_argument("--champion-image", default=str(CHAMPION_IMG), help="champion GPU image's llama-server (phase comp-champion only)")
    ap.add_argument("--champion-bin", default=None, help=argparse.SUPPRESS)   # compat with the original CLI: ignored
    ap.add_argument("--argv-file", default=str(ARGV_FILE))
    ap.add_argument("--prompt-set", default=str(PROMPT_SET))
    ap.add_argument("--launch-prefix", default="env HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0 numactl --membind=3 -- taskset -c 184-191")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--out", default=None)
    ap.add_argument("--gpu-window-id", default=os.environ.get("PBHOL_GPU_WINDOW_ID"))
    ap.add_argument("--vram-ceiling-gib", type=float, default=60.0, help="own-pid ceiling (GPU-LEAK-1 guard)")
    ap.add_argument("--vram-free-max-gib", type=float, default=2.0)
    ap.add_argument("--load-timeout-s", type=float, default=600)
    ap.add_argument("--card", default=str(K.DEFAULT_CARD))
    ap.add_argument("--no-device-claim", default=None, metavar="REASON")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--phases", default="srpf512,srpf2048,off512,comp-champion,comp-m4off,srpf2048cap0",
                    help="comma list from: " + ",".join(list(PHASES) + list(COMP_PHASES)))
    ap.add_argument("--server-extra-args", default="", help="appended (shlex-split) to EVERY phase's server argv, after the phase's own args")
    ap.add_argument("--c-reps", type=int, default=1, help="M4.2b: solo shorts (C) at the start and at the end of every load (default 1)")
    ap.add_argument("--batch", default="", help="per-phase -b/-ub override: name=N[,name=N...] (defaults: " +
                    ",".join(f"{k}={v[0]}" for k, v in PHASES.items()) + ")")
    args = ap.parse_args()
    global ORDER_OFF
    if args.c_reps < 1:
        raise SystemExit("--c-reps must be >= 1")
    ORDER_OFF = ["C"] * args.c_reps + ["A", "B", "A", "B", "A", "B"] + ["C"] * args.c_reps
    args.deadline_epoch = parse_deadline(args.deadline)
    args.out = args.out or str(HERE / "out" / ("run-" + K.utc_tag()))
    args.champion_bin = args.m4_bin     # Probe/summary compat

    phases_req = [x.strip() for x in args.phases.split(",") if x.strip()]
    bad = [p for p in phases_req if p not in PHASES and p not in COMP_PHASES]
    if bad:
        raise SystemExit(f"unknown phase(s) {bad}; known: {list(PHASES) + list(COMP_PHASES)}")
    for kv in [x for x in args.batch.split(",") if x.strip()]:
        k, _, v = kv.partition("=")
        if k.strip() not in PHASES or not v.strip().isdigit():
            raise SystemExit(f"bad --batch entry {kv!r}")
        PHASES[k.strip()] = (v.strip(), PHASES[k.strip()][1])

    def phase_spec(ph):   # -> (binary, batch, extra)
        if ph in COMP_PHASES:
            w, b, e = COMP_PHASES[ph]
            return (Path(args.champion_image) if w == "champion" else Path(args.m4_bin)), b, e
        b, e = PHASES[ph]
        return (Path(args.champion_image) if ph in CHAMPION_PHASES else Path(args.m4_bin)), b, e

    # ---- preflight (read-only)
    probs, notes = [], []
    for label, p, want_m4 in (("M4 build", Path(args.m4_bin), True), ("champion image", Path(args.champion_image), False)):
        if label == "champion image" and not any((x in COMP_PHASES and COMP_PHASES[x][0] == "champion") or x in CHAMPION_PHASES for x in phases_req):
            continue
        if label == "M4 build" and not any(phase_spec(x)[0] == p for x in phases_req):
            continue
        if not (p.is_file() and os.access(p, os.X_OK)):
            probs.append(f"{label} binary {p} not an executable file" + (" (M4.1 not PASSED yet?)" if want_m4 else ""))
            continue
        if os.path.realpath(p).startswith(str(K.FROZEN_TREE) + "/"):
            probs.append(f"{label} binary resolves inside the frozen tree")
            continue
        common = p.parent / "libllama-common.so"
        have = K.bytes_contain(common, b"--prefill-order")
        notes.append(f"{label}: --prefill-order compiled into {common.name}: {have}")
        if want_m4 != bool(have):
            probs.append(f"{label}: --prefill-order {'missing from' if want_m4 else 'present in'} {common} (wrong image)")
    if not (1024 <= args.port <= 65535) or 8000 <= args.port <= 8999:
        probs.append(f"--port {args.port} refused (8000-8999 are production ports)")
    if K.port_listening(args.port):
        probs.append(f"port {args.port} already listening")
    for f in (K.LINKAGE, Path(args.argv_file), Path(args.prompt_set)):
        if not f.exists():
            probs.append(f"missing {f}")
    long_ids = short_ids = None
    ps_meta = {}
    if Path(args.prompt_set).exists():
        try:
            long_ids, short_ids, ps_meta = load_prompts(Path(args.prompt_set))
            comp_names = [n for n, _ in load_comp_prompts(Path(args.prompt_set))]
            notes.append(f"completion set: {comp_names} x {COMP_PASSES} passes, n_predict {COMP_N_PRED}, temp 0, seed 42")
        except (SystemExit, KeyError) as exc:
            probs.append(f"prompt set: {exc}")
    hard, drift = K.argv_problems(K.parse_argv_file(Path(args.argv_file))[0], True) if Path(args.argv_file).exists() else ([], [])
    probs += hard
    drift = [d for d in drift if not d.startswith("-np")]
    if drift:
        notes.append("argv shape drift vs gate: " + "; ".join(drift))
    if K.port_listening(8083):
        notes.append("production :8083 is LISTENING now (an execute run refuses until its owner stops it)")
    total, steps = plan_estimate(phases_req)
    now = time.time()
    left = args.deadline_epoch - now
    if left < total * 1.15:
        probs.append(f"only {K.fmt_s(left)} until deadline; plan needs ~{K.fmt_s(total)} (x1.15 margin)")

    print("PB-HOL-1 / M4.2 plan")
    print(f"  deadline {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(args.deadline_epoch))} (in {K.fmt_s(left)}), out {args.out}")
    print(f"  M4 build {args.m4_bin}\n  champion image {args.champion_image} (comp-champion only)\n  argv   {args.argv_file} with -np {NP}; prefix: {args.launch_prefix}; port {args.port}")
    print(f"  prompts {ps_meta}")
    print(f"  long = {LONG_TOKENS} tok (group {LONG_GROUP} trunk), short = {SHORT_TOKENS} tok (group {SHORT_GROUP} suffix {SHORT_SUFFIX}); "
          f"short sent when long prefill >= {COLLIDE_FRAC:.0%}")
    for ph in phases_req:
        b, bs, ex = phase_spec(ph)[1], None, None
        print(f"  phase {ph}: binary {phase_spec(ph)[0].parent.parent.name}, -b/-ub {phase_spec(ph)[1]}, extra {phase_spec(ph)[2] + shlex.split(args.server_extra_args)}"
              + (f", order {ORDER_OFF}" if ph in PHASES else f", {COMP_PASSES} completion passes"))
    print("  A = short slot 0 / long slot 2, B = short slot 2 / long slot 0; cache_prompt=false, slots erased between runs; long aborted once the short has answered")
    print(f"  proofs per server: linkage, own-pid :{args.port}, HIP graphs ON from /proc/<pid>/environ, HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0, "
          f"own-pid KFD VRAM >= {RES_MIN_GIB:.0f} GiB, ceiling {args.vram_ceiling_gib} GiB (abort)")
    print(f"  rule: {RULE}")
    for d, sec in steps:
        print(f"   - {d}: ~{K.fmt_s(sec)}")
    print(f"  ESTIMATE total ~{K.fmt_s(total)} ({total / 60:.1f} min) against a {K.fmt_s(left)} budget; "
          f"long prefill model {est_long_s():.0f} s (replaced by the measured calibration at run time)")
    for n in notes:
        print("  note:", n)
    for p in probs:
        print("  PROBLEM:", p)
    if args.dry_run:
        print("PREFLIGHT:", "FAIL" if probs else "PASS")
        print("DRY RUN complete: no process was started, nothing was sent, no claim taken.")
        return 0
    if probs:
        print("REFUSED (preflight).")
        return 2
    if not args.gpu_window_id:
        print("REFUSED: no --gpu-window-id / PBHOL_GPU_WINDOW_ID")
        return 64

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    probe = Probe(args)
    stack, rc = [], 0

    def on_sig(signum, _f):
        probe.deadline_hit.set()
        probe.stop_server()
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, on_sig)
    signal.signal(signal.SIGINT, on_sig)
    threading.Thread(target=probe.watchdog, daemon=True).start()
    try:
        if args.no_device_claim is None:
            sys.path.insert(0, str(K.CLAIM_MOD_DIR))
            from autokernel.resource import device_claim as dc  # noqa: E402
            journal = dc.ClaimJournal(out / "claim" / "device-claim-journal.jsonl")
            try:
                cm = dc.acquire_device_claim("mi210_0", purpose=f"M4.2 PB-HOL-1 on :{args.port}",
                                             campaign_id="PB-HOL-1", journal=journal, holder_label="pbhol1-m4", timeout_s=0,
                                             max_hold_s=max(600, left + 600))
            except dc.DeviceClaimError as exc:
                print(f"[pbhol] REFUSED: mi210_0 device claim not acquired: {exc}", flush=True)
                return 75
            claim = cm.__enter__()
            stack.append(cm)
            K.write_json(out / "claim" / "device-claim-receipt.json", claim.receipt().to_dict())
        K.write_json(out / "run_meta.json", {"args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
                                              "started": K.now_iso(), "estimate_s": total, "notes": notes,
                                              "gpu_window_id": args.gpu_window_id, "prompts": ps_meta, "phases": phases_req,
                                              "phase_table": {k: list(v) for k, v in PHASES.items()},
                                              "device_claim": args.no_device_claim or "mi210_0 held"})
        for ph in phases_req:
            binary, batch, extra = phase_spec(ph)
            probe.start_phase(ph, binary, batch, extra)
            if ph in COMP_PHASES:
                for npass in range(1, COMP_PASSES + 1):
                    probe.run_completion_pass(ph, npass)
            else:
                probe.calibrate()
                reps = {"A": 0, "B": 0, "C": 0}
                for tag in ORDER_OFF:
                    reps[tag] += 1
                    if tag == "C":
                        probe.run_solo(f"C{reps[tag]}", reps[tag])
                    else:
                        probe.run_collision(f"{tag}-{ph}", tag, reps[tag], False, False)
            probe.end_phase()
        status = "complete"
    except K.Abort as exc:
        print(f"[pbhol] ABORT: {exc}", flush=True)
        status, rc = f"abort: {exc}", 3
    except SystemExit:
        status, rc = "signalled", 5
    except Exception as exc:  # noqa: BLE001
        print(f"[pbhol] ERROR: {type(exc).__name__}: {exc}", flush=True)
        status, rc = f"error: {type(exc).__name__}: {exc}", 4
    finally:
        probe.deadline_hit.set()
        probe.stop_server()
        try:
            s = probe.summarize(locals().get("status", "aborted-before-status"))
            print(f"[pbhol] summary {out}/summary.md arms={ {k: v['median_ms'] for k, v in s['arms'].items()} }")
        except Exception as exc:  # noqa: BLE001
            print(f"[pbhol] summary failed: {exc}", flush=True)
        for cm in reversed(stack):
            try:
                cm.__exit__(None, None, None)
            except Exception as exc:  # noqa: BLE001
                print(f"[pbhol] claim release failed: {exc}", flush=True)
        dead = all((x.stop_rec.get("verified_dead") if x.stop_rec else x.proc is None) for x in probe.servers)
        print(f"[pbhol] server verified dead: {dead}")
        if not dead:
            rc = rc or 6
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
