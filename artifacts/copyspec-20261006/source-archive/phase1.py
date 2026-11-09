#!/usr/bin/env python3
"""Phase-1 copy-speculation eval driver (acceptance/identity; tok/s informational only).
Subcommands: sample | run | finalstats | summary.  Never manages processes."""
import argparse, json, os, random, re, sys, time, urllib.request, urllib.error, collections, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = "/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl"
PROMPTS = os.path.join(HERE, "prompts_p1.jsonl")
RES = os.path.join(HERE, "results")
SEED = 20261006
QUOTA = {"debugbench": 40, "hotpotqa": 25, "general": 20}
HOTPOT_SUFFIX = ("\n\nBefore giving the final answer, quote the supporting sentences from the context "
                 "verbatim (copy them exactly), then give the answer inside <answer></answer> tags.")
MAX_TOKENS = 512
ARMS = ["P", "NM", "NO", "P2"]  # P2 = repeat of P (speed noise floor + identity noise floor)


def cmd_sample(a):
    if os.path.exists(PROMPTS) and not a.force:
        print(f"{PROMPTS} exists (fixed sample kept)"); return
    by = collections.defaultdict(list)
    with open(POOL) as f:
        for ln in f:
            r = json.loads(ln)
            if r.get("suite") in QUOTA and r.get("prompt"):
                by[r["suite"]].append(r)
    rng = random.Random(SEED)
    out = []
    for s, n in QUOTA.items():
        rows = sorted(by[s], key=lambda r: str(r["id"]))
        pick = rng.sample(rows, n)
        for r in pick:
            p = r["prompt"] + (HOTPOT_SUFFIX if s == "hotpotqa" else "")
            out.append({"id": str(r["id"]), "suite": s, "prompt": p, "suffix_added": s == "hotpotqa"})
    assert len({o["id"] for o in out}) == len(out), "duplicate prompt ids"
    assert len({o["prompt"] for o in out}) == len(out), "duplicate prompt texts"
    rng.shuffle(out)  # mixed order, identical for every arm
    with open(PROMPTS, "w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    print(f"wrote {len(out)} prompts -> {PROMPTS}", collections.Counter(o["suite"] for o in out))


STAT_RE = re.compile(r"statistics\s+(\S+):.*?#gen drafts =\s*(\d+),\s*#acc drafts =\s*(\d+),\s*#gen tokens =\s*(\d+),\s*#acc tokens =\s*(\d+)")


def parse_stats(path, start=0):
    """Last cumulative per-impl statistics line at/after byte offset `start` -> {impl: dict}."""
    res = {}
    try:
        with open(path, "rb") as f:
            f.seek(start)
            for ln in f:
                if b"statistics" not in ln:
                    continue
                m = STAT_RE.search(ln.decode("utf-8", "replace"))
                if m:
                    res[m.group(1)] = dict(gen_drafts=int(m.group(2)), acc_drafts=int(m.group(3)),
                                           gen_tokens=int(m.group(4)), acc_tokens=int(m.group(5)))
    except FileNotFoundError:
        pass
    return res


def post(base, body, timeout):
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:600]}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": f"{type(e).__name__}: {e}"}


def cmd_run(a):
    os.makedirs(RES, exist_ok=True)
    rows = [json.loads(l) for l in open(PROMPTS)]
    out = os.path.join(RES, f"{a.arm}.jsonl")
    done = set()
    if os.path.exists(out):  # resume: skip ids already persisted OK
        for l in open(out):
            try:
                r = json.loads(l)
                if r.get("ok"): done.add(r["id"])
            except Exception:  # noqa: BLE001
                pass
    n_ok = 0
    with open(out, "a") as fo:
        for i, p in enumerate(rows):
            if p["id"] in done:
                continue
            body = {"messages": [{"role": "user", "content": p["prompt"]}], "max_tokens": MAX_TOKENS,
                    "temperature": 0.0, "top_k": 1, "seed": 1, "cache_prompt": False, "id_slot": 0,
                    "chat_template_kwargs": {"enable_thinking": False}}
            off = os.path.getsize(a.log) if a.log and os.path.exists(a.log) else 0
            t0 = time.time()
            st, resp = post(a.base, body, a.timeout)
            wall = time.time() - t0
            t = (resp.get("timings") or {}) if isinstance(resp, dict) else {}
            ok = st == 200 and bool(resp.get("choices"))
            dn, da = t.get("draft_n"), t.get("draft_n_accepted")
            rec = {"arm": a.arm, "idx": i, "id": p["id"], "suite": p["suite"], "ok": ok, "http": st,
                   "wall_s": round(wall, 2), "error": None if ok else str(resp)[:600],
                   "text": (resp["choices"][0]["message"].get("content") or "") if ok else "",
                   "finish": resp["choices"][0].get("finish_reason") if ok else None,
                   "prompt_n": t.get("prompt_n"), "predicted_n": t.get("predicted_n"),
                   "tps": t.get("predicted_per_second"), "draft_n": dn, "draft_n_accepted": da,
                   "timings": t,
                   "log_stats_after": parse_stats(a.log, off) if a.log else {}}
            fo.write(json.dumps(rec) + "\n"); fo.flush(); os.fsync(fo.fileno())
            n_ok += ok
            print(f"[{a.arm}] {i+1}/{len(rows)} {p['suite']:10s} ok={ok} n={t.get('predicted_n')} "
                  f"tps={t.get('predicted_per_second')} draft={da}/{dn} wall={wall:.0f}s", flush=True)
            if st == 0:
                print("server unreachable; aborting arm", file=sys.stderr); sys.exit(3)
    print(f"[{a.arm}] done ok={n_ok}")


def cmd_finalstats(a):
    s = parse_stats(a.log)
    with open(os.path.join(RES, f"{a.arm}.logstats.json"), "w") as f:
        json.dump({"arm": a.arm, "log": a.log, "log_bytes": os.path.getsize(a.log) if os.path.exists(a.log) else None,
                   "impl_stats_last_seen": s}, f, indent=1)
    print(a.arm, s)


def load(arm):
    p = os.path.join(RES, f"{arm}.jsonl")
    d = {}
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l)
            if r.get("ok"): d[r["id"]] = r
    return d


def first_div(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]: return i
    return None if len(a) == len(b) else n


def cmd_summary(a):
    data = {arm: load(arm) for arm in ARMS}
    classes = list(QUOTA) + ["ALL"]
    L = ["# Phase-1 copy-speculation eval summary (full-host window)", "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M:%S')}. Greedy (temp 0, top_k 1), max_tokens {MAX_TOKENS}, "
         "distinct prompts, one request each per arm, server restarted between arms, cache_prompt=false, cache-ram 0.",
         "Arm order P, NM, NO, P2. P2 = repeat of P (noise floor). NO (ngram-mod alone) is a draft-only CONTROL, not a candidate.",
         "acceptance = sum(draft_n_accepted)/sum(draft_n) over requests (alarm if exactly 1.000).",
         "identity = byte-equal text vs P for the same prompt id; P2 vs P is the identity noise floor.", "",
         "## Acceptance and identity", "",
         "| class | arm | n | draft_n | accepted | acceptance | identical vs P | first-diverge (median char) | ngram-supplied reqs |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c in classes:
        for arm in ARMS:
            rs = [r for r in data[arm].values() if c == "ALL" or r["suite"] == c]
            if not rs:
                L.append(f"| {c} | {arm} | 0 | - | - | - | - | - | - |"); continue
            dn = sum(r["draft_n"] or 0 for r in rs); da = sum(r["draft_n_accepted"] or 0 for r in rs)
            acc = f"{da/dn:.3f}" + (" ALARM" if dn and da == dn else "") if dn else "n/a"
            if arm == "P":
                ident, fd = "(ref)", "-"
            else:
                cmp = [(r, data["P"].get(r["id"])) for r in rs if r["id"] in data["P"]]
                same = sum(1 for r, p in cmp if r["text"] == p["text"])
                divs = [first_div(r["text"], p["text"]) for r, p in cmp if r["text"] != p["text"]]
                ident = f"{same}/{len(cmp)}"
                fd = str(int(statistics.median(divs))) if divs else "-"
            ng = "-"
            if arm in ("NM", "NO"):
                prev = 0; cnt = 0; have = False
                for r in sorted(data[arm].values(), key=lambda r: r["idx"]):
                    st = next((v for k, v in (r.get("log_stats_after") or {}).items() if "ngram" in k), None)
                    if st:
                        have = True
                        cur = st["gen_drafts"]
                        if (c == "ALL" or r["suite"] == c) and cur > prev: cnt += 1
                        prev = max(prev, cur)
                ng = str(cnt) if have else "n/a (no per-request stats in log; see logstats.json)"
            L.append(f"| {c} | {arm} | {len(rs)} | {dn} | {da} | {acc} | {ident} | {fd} | {ng} |")
    L += ["", "## Speed (full host, 96 threads): P vs NM only, against the |P - P2| floor", "",
          "Mean timings.predicted_per_second per class. delta = NM vs mean(P,P2). floor = |P-P2|/mean(P,P2). "
          "A delta is only a signal if |delta| > floor; arm NO is excluded from speed (control).", "",
          "| class | P tok/s | P2 tok/s | NM tok/s | floor % | NM delta % | verdict |", "|---|---|---|---|---|---|---|"]
    def mtps(arm, c):
        v = [r["tps"] for r in data[arm].values() if r["tps"] and (c == "ALL" or r["suite"] == c)]
        return statistics.mean(v) if v else None
    for c in classes:
        p, p2, nm = mtps("P", c), mtps("P2", c), mtps("NM", c)
        if None in (p, p2, nm):
            L.append(f"| {c} | {p} | {p2} | {nm} | n/a | n/a | incomplete |"); continue
        base = (p + p2) / 2; floor = abs(p - p2) / base * 100; d = (nm - base) / base * 100
        v = "within noise" if abs(d) <= floor else ("NM faster" if d > 0 else "NM slower")
        L.append(f"| {c} | {p:.2f} | {p2:.2f} | {nm:.2f} | {floor:.2f} | {d:+.2f} | {v} |")
    L += ["", "## Arm-level ngram impl stats (last 'statistics' lines seen in each server log)", ""]
    for arm in ARMS:
        p = os.path.join(RES, f"{arm}.logstats.json")
        L.append(f"- {arm}: " + (json.dumps(json.load(open(p)).get("impl_stats_last_seen")) if os.path.exists(p) else "no logstats"))
    L += ["", "Note: draft_n/draft_n_accepted are totals over ALL impls that won a round (ngram or MTP); "
          "ngram-supplied counts come from the per-impl '#gen drafts' counter in the verbosity-4 log."]
    open(os.path.join(RES, "summary.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("sample"); s.add_argument("--force", action="store_true"); s.set_defaults(f=cmd_sample)
    r = sp.add_parser("run"); r.add_argument("--arm", required=True, choices=ARMS); r.add_argument("--base", default="http://127.0.0.1:18170")
    r.add_argument("--log"); r.add_argument("--timeout", type=float, default=3600); r.set_defaults(f=cmd_run)
    f = sp.add_parser("finalstats"); f.add_argument("--arm", required=True); f.add_argument("--log", required=True); f.set_defaults(f=cmd_finalstats)
    m = sp.add_parser("summary"); m.set_defaults(f=cmd_summary)
    a = ap.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
