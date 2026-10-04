#!/usr/bin/python3
"""KVU-16b replay — COPY (gpu-slot-ak-20261004) of /mnt/raid0/llm/tmp/gpu-block-27b-20261003/kvu16b_residency.py
(peer file untouched; original digest in SOURCES.sha256, verbatim copy in kvu16b_residency.orig.py).

Same scenario as the 2026-10-04T03:25Z run (results/kvu16b/20261004T032520Z, args in its report.json):
4 x ~80k distinct prompts (DS41 planner contexts C1..C7, rotation start 2k), streamed /completion with
ignore_eos and the same weighted n_predict budgets (0.42/0.30/0.19/0.09 of the 393216-pool headroom,
margin 8192), STAGGERED — request k+1 is sent when request k streams its first token.

Changes vs the original (all from /mnt/raid0/llm/tmp/kvu16b-rootcause-20261004/REPORT.md §0):
  1. FIXED decoding predicate. The original counted a slot as decoding iff `is_processing and n_decoded > 0`
     (kvu16b_residency.py:203,260), but n_decoded is reset only when a prompt finishes, so a prefilling slot
     reported its PREVIOUS task's n_decoded (slot 0 showed n_dec=1 while prefilling 60,720/79,836 at the
     "PASS" sample). Here a slot is decoding only if its task is mapped to one of OUR requests AND
     (n_prompt_tokens_processed + n_prompt_tokens_cache >= that request's prompt total, or that request's
     first token has been observed on its stream).
  2. Slot -> request mapping BY TASK ID. Requests are strictly staggered, so after sending request i the first
     /slots row that is processing a task id never seen before (baseline = every id_task present before the
     first send) is request i's task; its slot is recorded. Cross-checked offline against the server log's
     `id X | task T | processing task` lines (arrival-timestamped). Every per-slot result is keyed by REQUEST
     index, with server slot and task id alongside (the original keyed by server slot).
  3. Per-iteration prefill and decode rates. Each stream sends `return_progress: true`, so the server emits one
     prompt_progress event per server iteration while that request prefills (processed / total / server
     time_ms), and one event per generated token (tokens_predicted). Every event is persisted with its arrival
     time (events_req<i>.jsonl). iterations.json: per prefill iteration -> seconds, chunk tokens, occupied cells
     D (prefilling slot's processed + every decoding request's prompt + generated), decoders, decode tokens per
     decoder; plus per-request decode tok/s while each prefill runs, TTFTs, prefill rate per request.
  4. Targets a SCRATCH server (--base, never :8083: refused), its own server log (--server-log) and pid
     (--server-pid); no GPU-window gate (the caller owns the window and the device claim). Wall cap
     --max-wall-s (default 1200 s = 20 min, measured from the first send): at the cap the streams are closed
     (server cancels the tasks) and the verdict is CAPPED unless the PASS sample already happened.
  5. Prompts carry a FIXED per-request tag (not a random nonce): every arm gets byte-identical prompts.
     Each arm runs on a fresh server, so the prompt cache cannot leak between arms.
  6. KFD VRAM sampled at 1 Hz (was 0.5 s); idle slots are erased before the run (scratch server: --erase-idle-slots
     defaults on).

PASS iff: 4 requests decoding at once (fixed predicate) in one sample whose resident sum >= 300,000, zero bad
log lines, KFD peak <= 62 GiB, no request failed (our own abort after the hold or at the cap is not a failure).

Usage:
  kvu16b_residency_slot.py --dry-run [--base http://127.0.0.1:18183]
  kvu16b_residency_slot.py --i-own-the-window --base http://127.0.0.1:18183 --server-pid PID --server-log LOG
                           --out-dir DIR [--label L] [--max-wall-s 1200] [--n-batch 2048 --n-ubatch 2048]
Starts, stops and reloads nothing (the caller, kvu16b_arm.py, owns the server).
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import statistics
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_gpublock_slot as L  # noqa: E402

TAIL = "\n\n---\nContinue: write a long, detailed technical analysis of the material above, section by section.\n"
RE_PROC_TASK = re.compile(r"^(\d+\.\d+) .*id\s+(\d+) \| task (\d+) \| processing task")
D_BUCKET = 40000


def budgets(pool: int, prompts: list[int], margin: int, residual: int, weights: list[float]) -> tuple[int, list[int]]:
    head = pool - sum(prompts) - margin - residual
    ws = [w / sum(weights) for w in weights]
    return head, [max(0, int(head * w)) for w in ws]


def fixed_tag(k: int) -> str:
    return f"[kvu16b-slot request {k} fixed]\n"


class SlotsSampler(threading.Thread):
    """/slots poller that records request-start AND response time (mapping must not attribute a sample whose
    request left before an event to state after it)."""

    def __init__(self, base: str, interval: float, sink: L.JsonlSink, on_sample) -> None:
        super().__init__(daemon=True)
        self.base, self.interval, self.sink, self.on_sample = base, interval, sink, on_sample
        self.stop_ev = threading.Event()
        self.samples: list[tuple[float, float, list[dict]]] = []
        self.errors = 0

    def run(self) -> None:
        while not self.stop_ev.is_set():
            t_req = time.time()
            try:
                body = L.get_json(f"{self.base}/slots", 30.0)  # served between iterations (6-19 s at depth OFF)
                t_resp = time.time()
                rows = [L.slot_view(s) for s in (body or [])]
                self.samples.append((t_req, t_resp, rows))
                self.sink.add({"t_req": round(t_req, 3), "t": round(t_resp, 3), "slots": rows})
                self.on_sample(t_req, t_resp, rows)
            except Exception:  # noqa: BLE001 - a missed sample is not a verdict
                self.errors += 1
            self.stop_ev.wait(self.interval)


# ------------------------------------------------------------------ per-iteration analysis (from stream events)
def _ndec_at(tok_t: list[float], tok_n: list[int], t: float) -> int:
    i = bisect.bisect_right(tok_t, t) - 1
    return tok_n[i] if i >= 0 else 0


def iteration_analysis(reqs: list[dict], events: list[list[dict]], n_batch: int) -> dict:
    n = len(reqs)
    tok = []
    for i in range(n):
        tt = [e["t"] for e in events[i] if e["k"] == "tok"]
        tn = [e["n_dec"] for e in events[i] if e["k"] == "tok"]
        tok.append((tt, tn))
    ft = [r.get("t_first_token") for r in reqs]
    tend = [r.get("t_end") for r in reqs]
    total = [r.get("prompt_total") or r.get("prompt_tokens") or 0 for r in reqs]
    rows = []
    per_prefill = []
    for i in range(n):
        prog = [e for e in events[i] if e["k"] == "prog"]
        prog_rows = []
        for a, b in zip(prog, prog[1:]):
            chunk = b["processed"] - a["processed"]
            dt = (b["time_ms"] - a["time_ms"]) / 1e3
            if chunk <= 0 or dt <= 0:
                continue
            t = b["t"]
            dec = [j for j in range(n) if j != i and ft[j] is not None and ft[j] <= t and (tend[j] is None or tend[j] > t)]
            occ = b["processed"] + sum(total[j] + _ndec_at(*tok[j], t) for j in range(n)
                                       if j != i and ft[j] is not None and ft[j] <= t and (tend[j] is None or tend[j] > t))
            dtok = {j: _ndec_at(*tok[j], t) - _ndec_at(*tok[j], a["t"]) for j in dec}
            row = {"req": i, "t": round(t, 3), "s_iter": round(dt, 3), "chunk": chunk, "occupied": occ,
                   "own_len": b["processed"], "n_decoders": len(dec), "decode_tokens": dtok,
                   "s_per_2048": round(dt * 2048 / chunk, 3)}
            rows.append(row)
            prog_rows.append(row)
        # per-request decode tok/s while prefill i runs: window [first progress, first token (or end)]
        if prog:
            w0 = prog[0]["t"]
            w1 = ft[i] if ft[i] is not None else (tend[i] or prog[-1]["t"])
            dec_rates = {}
            for j in range(n):
                if j == i or ft[j] is None or ft[j] > w0:
                    continue
                a0, a1 = _ndec_at(*tok[j], w0), _ndec_at(*tok[j], w1)
                if w1 > w0:
                    dec_rates[j] = round((a1 - a0) / (w1 - w0), 3)
            pr = {"req": i, "window_s": round(w1 - w0, 1), "iterations": len(prog_rows),
                  "prefill_tps": round((prog[-1]["processed"] - prog[0]["processed"]) /
                                       max(1e-6, (prog[-1]["time_ms"] - prog[0]["time_ms"]) / 1e3), 1),
                  "median_s_iter": round(statistics.median([r["s_iter"] for r in prog_rows]), 3) if prog_rows else None,
                  "decode_tps_while_prefilling": dec_rates,
                  "decode_tps_sum": round(sum(dec_rates.values()), 3) if dec_rates else None,
                  "completed": ft[i] is not None}
            per_prefill.append(pr)
    buckets: dict[int, list[dict]] = {}
    for r in rows:
        buckets.setdefault(int(r["occupied"] // D_BUCKET), []).append(r)
    btab = []
    for b in sorted(buckets):
        rr = buckets[b]
        sdt = sum(r["s_iter"] for r in rr)
        dec_tok = sum(sum(r["decode_tokens"].values()) for r in rr)
        dec_n = statistics.mean(r["n_decoders"] for r in rr)
        btab.append({"occupied_lo": b * D_BUCKET, "occupied_hi": (b + 1) * D_BUCKET, "iterations": len(rr),
                     "median_s_iter": round(statistics.median(r["s_iter"] for r in rr), 3),
                     "mean_chunk": round(statistics.mean(r["chunk"] for r in rr), 1),
                     "median_s_per_2048": round(statistics.median(r["s_per_2048"] for r in rr), 3),
                     "mean_decoders": round(dec_n, 2),
                     "prefill_tps": round(sum(r["chunk"] for r in rr) / max(1e-6, sdt), 1),
                     "decode_tps_per_decoder": round(dec_tok / max(1e-6, sdt) / dec_n, 3) if dec_n else None})
    return {"n_batch": n_batch, "d_bucket": D_BUCKET, "rows": rows, "by_occupied": btab, "per_prefill": per_prefill}


def log_task_map(log_path: Path, start: int) -> list[dict]:
    out = []
    try:
        with log_path.open("rb") as fh:
            fh.seek(start)
            for raw in fh:
                m = RE_PROC_TASK.search(raw.decode(errors="replace"))
                if m:
                    out.append({"t": float(m.group(1)), "slot": int(m.group(2)), "task": int(m.group(3))})
    except OSError:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--i-own-the-window", action="store_true")
    ap.add_argument("--base", default="http://127.0.0.1:18183")
    ap.add_argument("--server-pid", type=int, default=None)
    ap.add_argument("--server-log", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--label", default="kvu16b")
    ap.add_argument("--n-batch", type=int, default=2048)
    ap.add_argument("--n-ubatch", type=int, default=2048)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--prompt-tokens", type=int, default=80000)
    ap.add_argument("--pool", type=int, default=393216)
    ap.add_argument("--margin", type=int, default=8192)
    ap.add_argument("--weights", default="0.42,0.30,0.19,0.09")
    ap.add_argument("--min-budget", type=int, default=2048)
    ap.add_argument("--resident-threshold", type=int, default=300000)
    ap.add_argument("--hold-s", type=float, default=90)
    ap.add_argument("--max-wall-s", type=float, default=1200)
    ap.add_argument("--slots-interval", type=float, default=2.0)
    ap.add_argument("--vram-interval", type=float, default=1.0)
    ap.add_argument("--kfd-budget-gib", type=float, default=62.0)
    ap.add_argument("--no-erase-idle-slots", dest="erase_idle_slots", action="store_false")
    args = ap.parse_args()
    weights = [float(w) for w in args.weights.split(",")]
    if len(weights) != args.n:
        raise SystemExit(f"--weights needs {args.n} values")
    port = int(args.base.rsplit(":", 1)[1])
    if port == 8083:
        raise SystemExit("REFUSING: --base points at production :8083; this replay runs on a scratch port only")

    if args.dry_run:
        problems: list[str] = []
        files = [L.check_file(L.VRAM_CARD, "MI210 vram sysfs", problems),
                 L.check_file(L.KFD_PROC, "KFD proc dir", problems)]
        corpus = L.context_corpus()
        if len(corpus) < 4:
            problems.append(f"only {len(corpus)} contexts under {L.CONTEXTS}")
        prompts = [L.fit_prompt(None, args.prompt_tokens, fixed_tag(k), start=2 * k, tail=TAIL)[1] for k in range(args.n)]
        head, bud = budgets(args.pool, [args.prompt_tokens] * args.n, args.margin, 0, weights)
        if min(bud) < args.min_budget:
            problems.append(f"budget {bud} below --min-budget {args.min_budget}")
        return L.print_plan(f"kvu16b_residency_slot.py ({args.label})", [
            ("target", [f"{args.base} (scratch server owned by kvu16b_arm.py; :8083 refused)",
                        f"server pid/log passed by the caller; n_batch {args.n_batch} n_ubatch {args.n_ubatch}"]),
            ("inputs", files + [f"{len(corpus)} contexts, {L.corpus_chars()} chars"]),
            ("prompts", [f"{args.n} x {args.prompt_tokens} tok, fixed tags (est. offline {prompts}; RUN trims to +-1% via /tokenize)"]),
            ("budgets", [f"headroom {head} (before residual) -> n_predict {bud} by weights {weights}"]),
            ("send pattern", [f"stream /completion ignore_eos return_progress; staggered on first token; hold {args.hold_s:.0f} s "
                              f"after the PASS sample; WALL CAP {args.max_wall_s:.0f} s from the first send"]),
            ("predicate (fixed)", ["decoding = task mapped to our request AND (n_proc+n_cache >= prompt total OR first token seen)"]),
            ("sampling", [f"/slots every {args.slots_interval} s (t_req + t_resp); KFD every {args.vram_interval} s; "
                          "stream events persisted per request; server log offset scan"]),
            ("outputs", ["<out-dir>/slots.jsonl requests.jsonl events_req<i>.jsonl iterations.json report.json report.md"]),
        ], problems)

    L.require_owner(args, "this sends four ~80k-token inference requests to the scratch server")
    if not (args.out_dir and args.server_log and args.server_pid):
        raise SystemExit("--out-dir, --server-log and --server-pid are required in run mode")
    od = args.out_dir
    od.mkdir(parents=True, exist_ok=True)
    pid = args.server_pid
    argv = L.proc_cmdline(pid)
    rep: dict = {"schema": "epyc.gpuslot.kvu16b.v2", "label": args.label, "started_at": L.now_iso(), "args": vars(args),
                 "server_pid": pid, "server_started": L.proc_lstart(pid), "server_argv": argv,
                 "argv_ok": "--kv-unified" in argv and "-c" in argv and argv[argv.index("-c") + 1] == str(args.pool),
                 "window": L.window_status(), "kfd_at_start": L.kfd_procs()}
    print("preflight:", json.dumps({k: rep[k] for k in ("server_pid", "argv_ok")}), flush=True)
    rows = [L.slot_view(s) for s in L.get_json(f"{args.base}/slots", 30)]
    if any(r["proc"] for r in rows):
        raise SystemExit("scratch server slots busy at start (unexpected: fresh server owned by the caller)")
    rep["slots_before"] = rows

    prompts = []
    for k in range(args.n):
        txt, n, _ = L.fit_prompt(args.base, args.prompt_tokens, fixed_tag(k), start=2 * k, tail=TAIL)
        prompts.append((txt, n))
    rep["prompt_tokens"] = [n for _, n in prompts]
    print("prompt tokens:", rep["prompt_tokens"], flush=True)

    log = L.LogWindow(args.server_log)
    rep["log_offset_start"] = log.start
    slots_sink = L.JsonlSink(od / "slots.jsonl")
    req_sink = L.JsonlSink(od / "requests.jsonl")

    # ---- residual cells: erase idle slots (scratch server; the coherence spot-check left a few tokens)
    residual = sum(r["n_tok"] for r in rows)
    purge: dict = {"residual_before": residual, "per_slot_before": {r["id"]: r["n_tok"] for r in rows}}
    if residual > 0 and args.erase_idle_slots:
        for r in rows:
            if r["n_tok"] > 0 and not r["proc"]:
                L.http_json(f"{args.base}/slots/{r['id']}?action=erase", {}, timeout=30)
        time.sleep(1)
        rows = [L.slot_view(s) for s in L.get_json(f"{args.base}/slots", 30)]
        residual = sum(r["n_tok"] for r in rows)
        purge["erased"] = True
    purge["residual_used_for_budget"] = residual
    rep["idle_purge_evidence"] = purge
    head, bud = budgets(args.pool, [n for _, n in prompts], args.margin, residual, weights)
    rep["headroom"], rep["budgets"] = head, bud
    print(f"residual {residual}, headroom {head}, budgets {bud}", flush=True)
    if min(bud) < args.min_budget:
        rep["verdict"] = "ABORTED"
        rep["abort_reason"] = f"budget {bud} < {args.min_budget}"
        L.write_json(od / "report.json", rep)
        return 2

    # ---- shared state: mapping + fixed predicate
    lock = threading.Lock()
    pre_tasks = {r["id_task"] for r in rows if r["id_task"] is not None}
    sent_t: list[float | None] = [None] * args.n
    first_t: list[float | None] = [None] * args.n
    prompt_total: list[int | None] = [None] * args.n
    task2req: dict[int, int] = {}
    req_slot: list[int | None] = [None] * args.n
    req_task: list[int | None] = [None] * args.n
    map_conflicts: list[dict] = []
    state = {"pass_t": None, "pass_sample": None, "max_dec": 0, "max_res": 0, "max_res_dec_n": 0}
    dec_hist: list[tuple[float, dict]] = []  # (t, {req: n_dec}) for samples with all n decoding

    def decoding_reqs(t_req: float, rows: list[dict]) -> dict[int, dict]:
        out = {}
        for r in rows:
            if not r["proc"]:
                continue
            i = task2req.get(r["id_task"])
            if i is None:
                continue
            tot = prompt_total[i] or rep["prompt_tokens"][i]
            seen_first = first_t[i] is not None and first_t[i] <= t_req
            if seen_first or (r["n_proc"] + r["n_cache"]) >= tot:
                out[i] = r
        return out

    def on_sample(t_req: float, t_resp: float, rows: list[dict]) -> None:
        with lock:
            # mapping by task id: a never-seen processing task after a send belongs to the oldest unmapped sent
            # request (task ids are monotonic and requests are staggered, so normally exactly one candidate)
            for r in sorted(rows, key=lambda x: x["id_task"] if x["id_task"] is not None else -1):
                tid = r["id_task"]
                if not r["proc"] or tid is None or tid in pre_tasks or tid in task2req:
                    continue
                cand = [k for k in range(args.n) if req_task[k] is None and sent_t[k] is not None and sent_t[k] <= t_resp]
                if not cand:
                    map_conflicts.append({"t": round(t_resp, 3), "task": tid, "slot": r["id"], "candidates": cand,
                                          "note": "unattributable new task (not ours?)"})
                    continue
                k = min(cand)
                if len(cand) > 1:
                    map_conflicts.append({"t": round(t_resp, 3), "task": tid, "slot": r["id"], "candidates": cand,
                                          "note": f"ambiguous; assigned to oldest unmapped request {k}"})
                task2req[tid], req_task[k], req_slot[k] = k, tid, r["id"]
                print(f"map: request {k} -> server slot {r['id']} task {tid}", flush=True)
            dec = decoding_reqs(t_req, rows)
            res = sum(r["n_tok"] for r in rows)
            state["max_dec"] = max(state["max_dec"], len(dec))
            state["max_res"] = max(state["max_res"], res)
            if len(dec) == args.n:
                dec_hist.append((t_resp, {i: r["n_dec"] for i, r in dec.items()}))
                state["max_res_dec_n"] = max(state["max_res_dec_n"], res)
                if res >= args.resident_threshold and state["pass_t"] is None:
                    state["pass_t"] = t_resp
                    state["pass_sample"] = {"t": round(t_resp, 3), "resident": res, "slots": rows,
                                            "decoding_requests": sorted(dec)}
                    print(f"PASS SAMPLE (fixed predicate): {args.n} requests decoding, resident {res}", flush=True)

    vs = L.VramSampler(pid, args.vram_interval)
    ss = SlotsSampler(args.base, args.slots_interval, slots_sink, on_sample)
    vs.start()
    ss.start()
    stop = threading.Event()
    results: list[dict] = [{} for _ in prompts]
    events: list[list[dict]] = [[] for _ in prompts]
    firsts = [threading.Event() for _ in prompts]

    def worker(i: int) -> None:
        sink = L.JsonlSink(od / f"events_req{i}.jsonl")

        def on_event(ev: dict) -> None:
            t = time.time()
            pp = ev.get("prompt_progress")
            if isinstance(pp, dict):
                e = {"t": round(t, 4), "k": "prog", "processed": pp.get("processed"), "total": pp.get("total"),
                     "cache": pp.get("cache"), "time_ms": pp.get("time_ms")}
                if prompt_total[i] is None and pp.get("total"):
                    prompt_total[i] = int(pp["total"])
            elif ev.get("content") or ev.get("tokens"):
                e = {"t": round(t, 4), "k": "tok", "n_dec": ev.get("tokens_predicted")}
                if first_t[i] is None:
                    first_t[i] = t
            else:
                return
            events[i].append(e)
            sink.add(e)

        body = {"prompt": prompts[i][0], "n_predict": bud[i], "ignore_eos": True, "return_progress": True}
        r = L.stream_request(f"{args.base}/completion", body, timeout=args.max_wall_s + 600,
                             on_first_token=firsts[i].set, stop=stop, on_event=on_event)
        firsts[i].set()
        r.pop("content", None)
        r.pop("reasoning", None)
        results[i] = {"i": i, "prompt_tokens": prompts[i][1], "prompt_total": prompt_total[i], "budget": bud[i],
                      "t_first_token": first_t[i], "t_end": time.time(), **r, **L.timing_summary(r.get("timings"))}
        req_sink.add(results[i])

    t0 = time.time()
    capped = False
    threads = []
    for i in range(args.n):
        with lock:
            sent_t[i] = time.time()
        th = threading.Thread(target=worker, args=(i,), daemon=True)
        th.start()
        threads.append(th)
        print(f"sent request {i} at +{time.time() - t0:.0f}s", flush=True)
        if i < args.n - 1:
            while not firsts[i].wait(5):
                if time.time() - t0 > args.max_wall_s:
                    capped = True
                    break
            if capped:
                print(f"WALL CAP {args.max_wall_s:.0f} s reached while request {i} prefilled; requests "
                      f"{list(range(i + 1, args.n))} never sent", flush=True)
                break
            print(f"request {i} first token at +{time.time() - t0:.0f}s", flush=True)
    while time.time() - t0 < args.max_wall_s:
        if state["pass_t"] and time.time() - state["pass_t"] >= args.hold_s:
            break
        if all(not th.is_alive() for th in threads):
            break
        time.sleep(1)
    else:
        capped = True
        print(f"WALL CAP {args.max_wall_s:.0f} s reached; closing streams", flush=True)
    stop.set()
    for th in threads:
        th.join(timeout=120)
    time.sleep(5)
    ss.stop_ev.set()
    vs.stop_ev.set()
    ss.join(timeout=40)
    vs.join(timeout=5)

    # ---- decode rates during the all-decoding phase, keyed by REQUEST index. Token counts come from the STREAM
    # events (tokens_predicted at arrival), not /slots n_decoded, which can be stale around the prompt->decode edge.
    rates, rates_slots = {}, {}
    if len(dec_hist) >= 2:
        (ta, da), (tb, db) = dec_hist[0], dec_hist[-1]
        for i in db:
            tt = [e["t"] for e in events[i] if e["k"] == "tok"]
            tn = [e["n_dec"] or 0 for e in events[i] if e["k"] == "tok"]
            rates[i] = round((_ndec_at(tt, tn, tb) - _ndec_at(tt, tn, ta)) / max(1e-6, tb - ta), 2)
            if first_t[i] is not None and first_t[i] <= ta:
                rates_slots[i] = round((db[i] - da.get(i, 0)) / max(1e-6, tb - ta), 2)
    for i in range(args.n):  # requests never sent (cap) or whose stream thread did not return have no result row
        if not results[i]:
            results[i] = {"i": i, "prompt_tokens": prompts[i][1], "budget": bud[i], "never_sent": sent_t[i] is None,
                          "no_result": sent_t[i] is not None, "t_first_token": first_t[i], "t_end": None}
    reqs = [{"prompt_tokens": prompts[i][1], "prompt_total": prompt_total[i], "t_first_token": first_t[i],
             "t_end": results[i].get("t_end")} for i in range(args.n)]
    it = iteration_analysis(reqs, events, args.n_batch)
    it["n_ubatch"] = args.n_ubatch
    L.write_json(od / "iterations.json", it)
    ltm = log_task_map(args.server_log, rep["log_offset_start"])
    log_map, used = {}, set(pre_tasks)
    for k in range(args.n):  # independent log mapping: first unused `processing task` line after request k's send
        if sent_t[k] is None:
            continue
        hit = next((x for x in ltm if x["t"] >= sent_t[k] - 0.2 and x["task"] not in used), None)
        if hit:
            used.add(hit["task"])
        log_map[k] = hit
    by_task = {x["task"]: x["slot"] for x in ltm}
    mapping = [{"req": k, "server_slot": req_slot[k], "task": req_task[k],
                "log_slot": (log_map.get(k) or {}).get("slot"), "log_task": (log_map.get(k) or {}).get("task"),
                "agree": ((log_map.get(k) or {}).get("task") == req_task[k] and by_task.get(req_task[k]) == req_slot[k])
                if req_task[k] is not None else None}
               for k in range(args.n)]
    vram = vs.summary()
    bad = log.counts()
    failed = [r["i"] for r in results if r.get("no_result") or (not r.get("never_sent") and
              (r.get("http_status") not in (200, None) or (r.get("error") and not r.get("aborted"))))]
    ok = (state["pass_t"] is not None and all(v == 0 for v in bad.values())
          and vram["kfd_peak_gib"] is not None and vram["kfd_peak_gib"] <= args.kfd_budget_gib and not failed)
    verdict = "PASS" if ok else ("CAPPED" if capped and state["pass_t"] is None else "FAIL")
    rep.update({
        "finished_at": L.now_iso(), "wall_s": round(time.time() - t0, 1), "capped": capped, "requests": results,
        "request_slot_task_map": mapping, "map_conflicts": map_conflicts,
        "ttft_own_send_s": [round(first_t[i] - sent_t[i], 1) if first_t[i] and sent_t[i] else None for i in range(args.n)],
        "first_token_since_t0_s": [round(first_t[i] - t0, 1) if first_t[i] else None for i in range(args.n)],
        "sent_since_t0_s": [round(sent_t[i] - t0, 1) if sent_t[i] else None for i in range(args.n)],
        "max_requests_decoding": state["max_dec"], "max_resident_tokens": state["max_res"],
        "max_resident_with_all_decoding": state["max_res_dec_n"], "pass_sample": state["pass_sample"],
        "decode_tps_per_request_all_decoding": rates, "decode_tps_per_request_all_decoding_slots_ndec": rates_slots,
        "decode_tps_sum_all_decoding": round(sum(rates.values()), 2) if rates else None,
        "per_prefill": it["per_prefill"], "by_occupied": it["by_occupied"],
        "slots_samples": len(ss.samples), "slots_errors": ss.errors, "vram": vram, "bad_line_counts": bad,
        "prompt_cache_events": L.prompt_cache_events(log.lines()), "failed_requests": failed,
        "log_offset_end": args.server_log.stat().st_size, "verdict": verdict,
    })
    L.write_json(od / "report.json", rep)
    md = [f"# KVU-16b replay {args.label} ({rep['finished_at']}): **{verdict}** (fixed predicate)", "",
          f"- -b {args.n_batch} -ub {args.n_ubatch}; prompts {rep['prompt_tokens']}; budgets {bud}; wall {rep['wall_s']} s "
          f"(cap {args.max_wall_s:.0f}, capped={capped})",
          f"- request -> slot/task: {mapping}",
          f"- TTFT own-send s {rep['ttft_own_send_s']}; first token since t0 {rep['first_token_since_t0_s']}",
          f"- max requests decoding at once {state['max_dec']}; max resident {state['max_res']}; "
          f"max resident while all {args.n} decoding {state['max_res_dec_n']}",
          f"- KFD peak {vram['kfd_peak_gib']} GiB (budget {args.kfd_budget_gib}); bad lines {bad}; failed {failed}",
          f"- decode tok/s per request with all decoding: {rates}"]
    (od / "report.md").write_text("\n".join(md) + "\n")
    print(f"VERDICT {verdict}; wrote {od}/report.md", flush=True)
    return 0 if ok else (4 if verdict == "CAPPED" else 1)


if __name__ == "__main__":
    sys.exit(main())
