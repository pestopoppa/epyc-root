#!/usr/bin/python3
"""KVU-16b — corrected concurrent-residency proof for the :8083 393216-cell unified pool
(kv-unified-stack-rollout.md KVU-16b).

Why the 2026-10-03 13:51Z probe failed its own criterion: the server prefilled the four
~90k prompts largely serially and `n_predict 64` freed each request's cells right after its
prefill, so at most 92,343 cells were ever in flight. This runner keeps every context
DECODING until all four are resident at once:

  * 4 DISTINCT prompts (nonce first, different rotation of the DS41 planner contexts C1..C7),
    sized with POST /tokenize; sent STAGGERED — request k+1 goes out when request k streams
    its first token (prefill done), so each finished prefill keeps decoding while the next
    one prefills;
  * streamed /completion with `ignore_eos` and an n_predict BUDGET per request. The budgets
    are a static overflow guarantee: sum(prompt) + sum(budget) + margin + residual cells
    <= pool (393216), split by weight so the earliest request (which waits longest) gets
    the most;
  * once a /slots sample shows all 4 slots decoding (is_processing, n_decoded > 0) with
    resident tokens >= 300k (sum of n_prompt_tokens = prompt.tokens.size(), which includes
    generated tokens — server-context.cpp:535), it keeps sampling for --hold-s and then
    closes the streams (the server cancels the tasks);
  * samples /slots every 2 s (cheap with SLOTS_DEBUG off), KFD per-process VRAM every 0.5 s,
    and scans the server log from its start offset for "failed to find a memory slot" and
    "Context size has been exceeded".

Why ~80k and not ~90k prompts: 4 x 90k = 360k leaves only ~25k cells of decode headroom in
the 393216 pool, so a static no-overflow budget would be too small to outlast the slowest
neighbour's prefill. 4 x 80k = 320k already clears the 300k criterion and leaves ~65k.

Residual cells: if idle slots still hold tokens from earlier steps (T7), one 1-token
"purge probe" request is sent first. With production's default `cache_idle_slots` ON, its
launch should save-and-clear every idle slot (server-context.cpp:2469-2483). The before/after
/slots and the `clearing prompt with N tokens` lines are recorded as live evidence for the
UFH14-B4i purge question. Anything still resident is subtracted from the budget, or erased
with --erase-idle-slots (POST /slots/{id}?action=erase; no inference).

PASS iff: 4 slots decoding at once in one sample whose resident sum >= 300,000, zero bad log
lines, KFD peak <= 62 GiB, and no request failed (our own abort after the hold is not a
failure).

Usage:
  kvu16b_residency.py --dry-run
  kvu16b_residency.py --i-own-the-window [--erase-idle-slots]
Starts, stops and reloads nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_gpublock as L  # noqa: E402

TAIL = "\n\n---\nContinue: write a long, detailed technical analysis of the material above, section by section.\n"


def budgets(pool: int, prompts: list[int], margin: int, residual: int, weights: list[float]) -> tuple[int, list[int]]:
    head = pool - sum(prompts) - margin - residual
    ws = [w / sum(weights) for w in weights]
    return head, [max(0, int(head * w)) for w in ws]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--i-own-the-window", action="store_true")
    ap.add_argument("--base", default="http://127.0.0.1:8083")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--prompt-tokens", type=int, default=80000)
    ap.add_argument("--pool", type=int, default=393216)
    ap.add_argument("--margin", type=int, default=8192)
    ap.add_argument("--weights", default="0.42,0.30,0.19,0.09")
    ap.add_argument("--min-budget", type=int, default=2048)
    ap.add_argument("--resident-threshold", type=int, default=300000)
    ap.add_argument("--hold-s", type=float, default=90)
    ap.add_argument("--max-wall-s", type=float, default=4200)
    ap.add_argument("--slots-interval", type=float, default=2.0)
    ap.add_argument("--vram-interval", type=float, default=0.5)
    ap.add_argument("--kfd-budget-gib", type=float, default=62.0)
    ap.add_argument("--erase-idle-slots", action="store_true")
    args = ap.parse_args()
    weights = [float(w) for w in args.weights.split(",")]
    if len(weights) != args.n:
        raise SystemExit(f"--weights needs {args.n} values")

    if args.dry_run:
        problems: list[str] = []
        files = [L.check_file(L.LOG_8083, ":8083 server log", problems),
                 L.check_file(L.VRAM_CARD, "MI210 vram sysfs", problems),
                 L.check_file(L.KFD_PROC, "KFD proc dir", problems)]
        corpus = L.context_corpus()
        if len(corpus) < 4:
            problems.append(f"only {len(corpus)} contexts under {L.CONTEXTS}")
        prompts = [L.fit_prompt(None, args.prompt_tokens, L.nonce(f"kvu16b {k}"), start=2 * k, tail=TAIL)[1]
                   for k in range(args.n)]
        head, bud = budgets(args.pool, [args.prompt_tokens] * args.n, args.margin, 0, weights)
        if min(bud) < args.min_budget:
            problems.append(f"budget {bud} below --min-budget {args.min_budget}; lower --prompt-tokens")
        if args.n * args.prompt_tokens + 0 < args.resident_threshold * 0.95:
            problems.append("prompts alone sit far under the resident threshold")
        h90, b90 = budgets(args.pool, [90000] * args.n, args.margin, 0, weights)
        # prefill estimate: 89,921 tokens took 263 s alone on this pool, then 419/646/838 s
        # increments with resident neighbours (13:51Z probe) -> scale by prompt size
        inc = [263, 419, 646, 838][: args.n]
        prefill_s = sum(inc) * args.prompt_tokens / 89921
        return L.print_plan("kvu16b_residency.py (KVU-16b)", [
            ("target", [f"{args.base} directly (bypasses the one-long-prefill gate on purpose: the pool is under test); "
                        ":8083 roles PARKED", "preflight (run): live pid/argv, window parked, all slots idle (waits <= 10 min)"]),
            ("inputs", files + [f"{len(corpus)} contexts, {L.corpus_chars()} chars (~{int(L.corpus_chars() / L.EST_CHARS_PER_TOKEN)} tok est.)"]),
            ("prompts", [f"{args.n} x {args.prompt_tokens} tokens (est. offline {prompts}; RUN mode trims to +-1% via /tokenize)",
                         f"sum {args.n * args.prompt_tokens} vs threshold {args.resident_threshold}"]),
            ("budgets (no-overflow guarantee)", [
                f"pool {args.pool} - prompts {args.n * args.prompt_tokens} - margin {args.margin} - residual (measured) = headroom {head}",
                f"n_predict budgets by weight {weights}: {bud}",
                f"for reference, 4 x 90000 would leave headroom {h90} -> budgets {b90}"]),
            ("send pattern", ["optional 1-token purge probe if idle slots hold tokens (records idle-purge evidence)",
                              "streamed /completion, ignore_eos, staggered on first token; hold "
                              f"{args.hold_s:.0f} s after the PASS sample, then close streams", f"max wall {args.max_wall_s:.0f} s"]),
            ("sampling", [f"/slots every {args.slots_interval} s; KFD VRAM every {args.vram_interval} s; server log offset scan"]),
            ("PASS", [f"{args.n} slots decoding in one sample with resident >= {args.resident_threshold}; 0 bad lines; "
                      f"KFD peak <= {args.kfd_budget_gib} GiB; no request failed"]),
            ("estimate", [f"prefills ~{round(prefill_s / 60)} min (scaled from the 13:51Z probe) + hold "
                          f"{args.hold_s / 60:.1f} min + setup ~2 min = ~{round((prefill_s + args.hold_s + 120) / 60)} min"]),
            ("outputs", [f"{L.RESULTS}/kvu16b/<ts>/slots.jsonl, requests.jsonl, report.json, report.md; exit 0 PASS, 1 FAIL"]),
        ], problems)

    L.require_owner(args, "this sends four ~80k-token inference requests to :8083")
    od = L.out_dir("kvu16b")
    port = int(args.base.rsplit(":", 1)[1])
    pid = L.port_pid(port)
    argv = L.proc_cmdline(pid) if pid else []
    rep: dict = {"schema": "epyc.gpublock.kvu16b.v1", "started_at": L.now_iso(), "args": vars(args),
                 "server_pid": pid, "server_started": L.proc_lstart(pid) if pid else None,
                 "argv_ok": "--kv-unified" in argv and "-c" in argv and argv[argv.index("-c") + 1] == str(args.pool),
                 "slots_debug_env": L.proc_environ(pid).get("LLAMA_SERVER_SLOTS_DEBUG") if pid else None,
                 "window": L.window_status(), "kfd_at_start": L.kfd_procs()}
    print("preflight:", json.dumps({k: rep[k] for k in ("server_pid", "argv_ok", "slots_debug_env")}
                                   | {"parked": rep["window"].get("parked_8083")}), flush=True)
    t_idle = time.time() + 600
    while time.time() < t_idle:
        rows = [L.slot_view(s) for s in L.get_json(f"{args.base}/slots", 10)]
        if not any(r["proc"] for r in rows):
            break
        time.sleep(10)
    else:
        raise SystemExit("slots still busy after 10 min; is :8083 parked?")
    rep["slots_before"] = rows

    prompts = []
    for k in range(args.n):
        txt, n, _ = L.fit_prompt(args.base, args.prompt_tokens, L.nonce(f"kvu16b {k}"), start=2 * k, tail=TAIL)
        prompts.append((txt, n))
    rep["prompt_tokens"] = [n for _, n in prompts]
    print("prompt tokens:", rep["prompt_tokens"], flush=True)

    log = L.LogWindow(L.LOG_8083)
    rep["log_offset_start"] = log.start
    slots_sink = L.JsonlSink(od / "slots.jsonl")
    req_sink = L.JsonlSink(od / "requests.jsonl")

    # ---- residual cells and the idle-purge evidence
    residual = sum(r["n_tok"] for r in rows)
    purge: dict = {"residual_before": residual, "per_slot_before": {r["id"]: r["n_tok"] for r in rows}}
    if residual > 0:
        st, _ = L.http_json(f"{args.base}/completion", {"prompt": L.nonce("kvu16b purge-probe") + "Say OK.",
                                                         "n_predict": 1, "temperature": 0}, timeout=120)
        time.sleep(2)
        after = [L.slot_view(s) for s in L.get_json(f"{args.base}/slots", 10)]
        ev = L.prompt_cache_events(log.lines())
        purge.update({"probe_http": st, "per_slot_after": {r["id"]: r["n_tok"] for r in after},
                      "idle_saves_logged": ev["idle_saves"], "clear_nonzero_logged": ev["clear_nonzero"],
                      "clear_nonzero_tokens": ev["clear_nonzero_tokens"]})
        purge["purged"] = ev["clear_nonzero"] > 0 and sum(r["n_tok"] for r in after) < residual
        residual = sum(r["n_tok"] for r in after)
        if residual > 0 and args.erase_idle_slots:
            for r in after:
                if r["n_tok"] > 0 and not r["proc"]:
                    L.http_json(f"{args.base}/slots/{r['id']}?action=erase", {}, timeout=30)
            time.sleep(1)
            residual = sum(L.slot_view(s)["n_tok"] for s in L.get_json(f"{args.base}/slots", 10))
            purge["erased"] = True
    purge["residual_used_for_budget"] = residual
    rep["idle_purge_evidence"] = purge
    head, bud = budgets(args.pool, [n for _, n in prompts], args.margin, residual, weights)
    rep["headroom"], rep["budgets"] = head, bud
    print(f"residual {residual}, headroom {head}, budgets {bud}", flush=True)
    if min(bud) < args.min_budget:
        rep["verdict"] = "ABORTED"
        rep["abort_reason"] = f"budget {bud} < {args.min_budget}: lower --prompt-tokens or use --erase-idle-slots"
        L.write_json(od / "report.json", rep)
        print(rep["abort_reason"], flush=True)
        return 2

    # ---- samplers + staggered streams
    stop = threading.Event()
    state = {"pass_t": None, "pass_sample": None, "max_dec": 0, "max_res": 0, "max_res_dec_n": 0}

    def on_sample(t: float, rows: list[dict]) -> None:
        dec = [r for r in rows if r["proc"] and r["n_dec"] > 0]
        res = sum(r["n_tok"] for r in rows)
        state["max_dec"] = max(state["max_dec"], len(dec))
        state["max_res"] = max(state["max_res"], res)
        if len(dec) == args.n:
            state["max_res_dec_n"] = max(state["max_res_dec_n"], res)
            if res >= args.resident_threshold and state["pass_t"] is None:
                state["pass_t"] = t
                state["pass_sample"] = {"t": round(t, 3), "resident": res, "slots": rows}
                print(f"PASS SAMPLE: {args.n} decoding, resident {res}", flush=True)

    vs = L.VramSampler(pid, args.vram_interval)
    ss = L.SlotsSampler(args.base, args.slots_interval, sink=slots_sink, on_sample=on_sample)
    vs.start()
    ss.start()
    results: list[dict] = [{} for _ in prompts]
    firsts = [threading.Event() for _ in prompts]

    def worker(i: int) -> None:
        body = {"prompt": prompts[i][0], "n_predict": bud[i], "ignore_eos": True}
        r = L.stream_request(f"{args.base}/completion", body, timeout=args.max_wall_s + 600,
                             on_first_token=firsts[i].set, stop=stop)
        firsts[i].set()
        r.pop("content", None)
        r.pop("reasoning", None)
        results[i] = {"i": i, "prompt_tokens": prompts[i][1], "budget": bud[i], **r,
                      **L.timing_summary(r.get("timings"))}
        req_sink.add(results[i])

    t0 = time.time()
    threads = []
    for i in range(args.n):
        th = threading.Thread(target=worker, args=(i,), daemon=True)
        th.start()
        threads.append(th)
        print(f"sent request {i} at +{time.time() - t0:.0f}s", flush=True)
        if i < args.n - 1:
            while not firsts[i].wait(5):
                if time.time() - t0 > args.max_wall_s:
                    break
            print(f"request {i} first token at +{time.time() - t0:.0f}s", flush=True)
    while time.time() - t0 < args.max_wall_s:
        if state["pass_t"] and time.time() - state["pass_t"] >= args.hold_s:
            break
        if all(not th.is_alive() for th in threads):
            break
        time.sleep(1)
    stop.set()
    for th in threads:
        th.join(timeout=120)
    time.sleep(5)
    ss.stop_ev.set()
    vs.stop_ev.set()
    ss.join(timeout=10)
    vs.join(timeout=5)

    # ---- decode rates during the all-decoding phase (decode tax with resident neighbours)
    all_dec = [(t, rows) for t, rows in ss.samples if sum(1 for r in rows if r["proc"] and r["n_dec"] > 0) == args.n]
    rates = {}
    if len(all_dec) >= 2:
        (ta, ra), (tb, rb) = all_dec[0], all_dec[-1]
        da = {r["id"]: r["n_dec"] for r in ra}
        for r in rb:
            rates[r["id"]] = round((r["n_dec"] - da.get(r["id"], 0)) / max(1e-6, tb - ta), 2)
    vram = vs.summary()
    bad = log.counts()
    failed = [r["i"] for r in results if r.get("http_status") not in (200, None) or (r.get("error") and not r.get("aborted"))]
    ok = (state["pass_t"] is not None and all(v == 0 for v in bad.values())
          and vram["kfd_peak_gib"] is not None and vram["kfd_peak_gib"] <= args.kfd_budget_gib and not failed)
    rep.update({
        "finished_at": L.now_iso(), "wall_s": round(time.time() - t0, 1), "requests": results,
        "first_token_s": [round(r["t_send"] + r["ttft_s"] - t0, 1) if r.get("ttft_s") else None for r in results],
        "max_slots_decoding": state["max_dec"], "max_resident_tokens": state["max_res"],
        "max_resident_with_all_decoding": state["max_res_dec_n"], "pass_sample": state["pass_sample"],
        "decode_tps_per_slot_all_decoding": rates, "decode_tps_sum_all_decoding": round(sum(rates.values()), 2) if rates else None,
        "slots_samples": len(ss.samples), "slots_errors": ss.errors, "vram": vram, "bad_line_counts": bad,
        "prompt_cache_events": L.prompt_cache_events(log.lines()), "failed_requests": failed,
        "log_offset_end": L.LOG_8083.stat().st_size, "window_at_end": L.window_status(),
        "verdict": "PASS" if ok else "FAIL",
    })
    L.write_json(od / "report.json", rep)
    md = [f"# KVU-16b — concurrent residency on the 393216 pool ({rep['finished_at']}): **{rep['verdict']}**", "",
          f"- prompts {rep['prompt_tokens']} (sum {sum(rep['prompt_tokens'])}); budgets {bud}; residual before {purge['residual_before']}",
          f"- first token at +s {rep['first_token_s']}",
          f"- max slots decoding at once {state['max_dec']}; max resident {state['max_res']}; "
          f"max resident while all {args.n} decoding {state['max_res_dec_n']} (threshold {args.resident_threshold})",
          f"- bad lines {bad}; KFD peak {vram['kfd_peak_gib']} GiB (budget {args.kfd_budget_gib}); failed requests {failed}",
          f"- decode tok/s per slot with all {args.n} decoding: {rates} (sum {rep['decode_tps_sum_all_decoding']})",
          f"- idle-purge evidence (production flags): {json.dumps(purge)}",
          f"- server log bytes {rep['log_offset_start']}-{rep['log_offset_end']} of {L.LOG_8083}"]
    (od / "report.md").write_text("\n".join(md) + "\n")
    print(f"VERDICT {rep['verdict']}; wrote {od}/report.md", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
