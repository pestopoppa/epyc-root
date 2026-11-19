#!/usr/bin/env python3
"""Copy-speculation sweep driver (acceptance/identity vs ngram cap; tok/s paired-only).
Subcommands: sample | run | finalstats | summary.  Never manages processes.
Parametrised by env (set by the .sh):
  EVAL_ARMS   space-separated arm order (first must be P; P2 = repeat of P)
  EVAL_CAPS   json {arm: ngram n-max cap}
  EVAL_TITLE  summary title        EVAL_BASE  default server base url
  EVAL_NOTE   extra note line in summary
Prompt set: prompts_sweep.jsonl = prompts_p1.jsonl (debugbench 40 + hotpotqa 25, general dropped)
            + 25 REAL PROSE prompts (suite 'prose'), selection rule in cmd_sample."""
import argparse, json, os, random, re, sys, time, urllib.request, urllib.error, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = "/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl"
P1 = "/mnt/raid0/llm/tmp/copy-spec-eval-20261006/width/prompts_p1.jsonl"
PROMPTS = os.path.join(HERE, "prompts_sweep.jsonl")
RES = os.path.join(HERE, "results")
SEED = 20261006
MAX_TOKENS = 512
ARMS = os.environ.get("EVAL_ARMS", "P W16 W32 W64 W16m8 P2").split()
CAPS = json.loads(os.environ.get("EVAL_CAPS", "{}"))
TITLE = os.environ.get("EVAL_TITLE", "Copy-speculation ngram-cap sweep")
NOTE = os.environ.get("EVAL_NOTE", "")
CLASSES = ["debugbench", "hotpotqa", "prose"]

# --- PROSE selection rule -------------------------------------------------------------
# suite == instruction_precision (IFEval-derived free-form writing tasks; question_pool has NO suite-level MCQ flag,
# the MCQ marker is the per-row field scoring_method == 'multiple_choice', excluded explicitly; suites general/thinking/
# mmlu_pro/gpqa are all MCQ and never considered).  Then: prompt <= 1500 chars; drop rows whose constraint distorts the
# prose (case-forcing, no-comma, JSON wrap, translation/foreign-language, repeat-the-request, P.S.).  Tier A = prompt
# explicitly asks for >= 300 words.  Tier B = long-form keyword (essay/explain/article/story/...).
# Sample = all of tier A (sorted by id) + seeded fill from tier B to 25.
EX = re.compile(r"all (lower|upper)case|capital letters|lowercase|json|wrap (the|your) entire|no commas?|do not use any comma|"
                r"repeat the request|\bP\.S\.|translate|in (german|french|spanish|hindi|korean|arabic|bengali|russian|japanese|"
                r"italian|portuguese|telugu|marathi|kannada|tamil)", re.I)
LEN = re.compile(r"(\d{3,4})\+? words|at least (\d{3,4}) words|(\d{3,4}) or more words", re.I)
SHORT = re.compile(r"(less than|fewer than|at most|under|no more than|maximum of|within)\s+\d+\s+(words|sentences)|\b(short|brief|briefly|riddle|haiku|limerick|one sentence|single sentence|two sentences)\b", re.I)
KW = re.compile(r"\b(essay|explain|article|blog post|story|detailed|in depth|describe|discuss|analy[sz]e|history of|speech|review|report)\b", re.I)


def cmd_sample(a):
    if os.path.exists(PROMPTS) and not a.force:
        print(f"{PROMPTS} exists (fixed sample kept)"); return
    out = []
    for l in open(P1):
        r = json.loads(l)
        if r["suite"] in ("debugbench", "hotpotqa"):
            out.append(r)
    A, B = [], []
    for l in open(POOL):
        r = json.loads(l)
        if r.get("__pool_metadata__") or r.get("suite") != "instruction_precision": continue
        if r.get("scoring_method") == "multiple_choice" or not r.get("prompt"): continue
        p = r["prompt"]
        if EX.search(p) or SHORT.search(p) or len(p) > 1500: continue
        m = LEN.search(p)
        if m and int([g for g in m.groups() if g][0]) >= 300: A.append(r)
        elif KW.search(p): B.append(r)
    A.sort(key=lambda r: str(r["id"])); B.sort(key=lambda r: str(r["id"]))
    rng = random.Random(SEED)
    pick = A[:25] + rng.sample(B, max(0, 25 - len(A[:25])))
    for r in pick:
        out.append({"id": str(r["id"]), "suite": "prose", "prompt": r["prompt"], "suffix_added": False})
    assert len({o["id"] for o in out}) == len(out), "duplicate prompt ids"
    assert sum(o["suite"] == "prose" for o in out) == 25, "need 25 prose prompts"
    order = random.Random(SEED + 1)
    order.shuffle(out)
    with open(PROMPTS, "w") as f:
        for o in out: f.write(json.dumps(o) + "\n")
    import collections
    print(f"wrote {len(out)} prompts -> {PROMPTS}", dict(collections.Counter(o["suite"] for o in out)),
          f"(prose tierA={len(A)} tierB={len(B)})")


STAT_RE = re.compile(r"statistics\s+(\S+):.*?#gen drafts =\s*(\d+),\s*#acc drafts =\s*(\d+),\s*#gen tokens =\s*(\d+),\s*#acc tokens =\s*(\d+)")


def parse_stats(path, start=0):
    res = {}
    try:
        with open(path, "rb") as f:
            f.seek(start)
            for ln in f:
                if b"statistics" not in ln: continue
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
    if os.path.exists(out):
        for l in open(out):
            try:
                r = json.loads(l)
                if r.get("ok"): done.add(r["id"])
            except Exception:  # noqa: BLE001
                pass
    n_ok = 0
    with open(out, "a") as fo:
        for i, p in enumerate(rows):
            if p["id"] in done: continue
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
                   "timings": t, "log_stats_after": parse_stats(a.log, off) if a.log else {}}
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


def ngram_deltas(rs_all, cls):
    """per-request deltas of the cumulative ngram 'statistics' counters, restricted to class cls."""
    prev = pa = pg = 0; cnt = sd = sa = sg = 0; have = False
    for r in sorted(rs_all.values(), key=lambda r: r["idx"]):
        st = next((v for k, v in (r.get("log_stats_after") or {}).items() if "ngram" in k), None)
        if not st: continue
        have = True; cur = st["gen_drafts"]
        if (cls == "ALL" or r["suite"] == cls) and cur > prev:
            cnt += 1; sd += cur - prev; sa += st["acc_tokens"] - pa; sg += st["gen_tokens"] - pg
        prev = max(prev, cur); pa = max(pa, st["acc_tokens"]); pg = max(pg, st["gen_tokens"])
    return have, cnt, sd, sa, sg


def cmd_summary(a):
    data = {arm: load(arm) for arm in ARMS}
    classes = CLASSES + ["ALL"]
    L = [f"# {TITLE}", ""]
    if NOTE: L += [NOTE, ""]
    L += [f"Generated {time.strftime('%Y-%m-%d %H:%M:%S')}. Greedy (temp 0, top_k 1), max_tokens {MAX_TOKENS}, "
          "distinct prompts (debugbench 40, hotpotqa 25, prose 25), one request each per arm, server restarted between arms, cache_prompt=false.",
          f"Arm order: {' '.join(ARMS)} (P2 = repeat of P, noise floor). Caps: {json.dumps(CAPS)}.",
          "acceptance = sum(draft_n_accepted)/sum(draft_n) over requests (alarm if exactly 1.000).",
          "identity = byte-equal text vs P for the same prompt id; P2 vs P is the identity noise floor.", "",
          "## Acceptance and identity", "",
          "| class | arm | n | draft_n | accepted | acceptance | identical vs P | first-diverge (median char) | ngram-supplied reqs | mean accepted len / ngram draft | mean gen len / ngram draft |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in classes:
        for arm in ARMS:
            rs = [r for r in data[arm].values() if c == "ALL" or r["suite"] == c]
            if not rs:
                L.append(f"| {c} | {arm} | 0 | - | - | - | - | - | - | - | - |"); continue
            dn = sum(r["draft_n"] or 0 for r in rs); da = sum(r["draft_n_accepted"] or 0 for r in rs)
            acc = (f"{da/dn:.3f}" + (" ALARM" if da == dn else "")) if dn else "n/a"
            if arm == "P": ident, fd = "(ref)", "-"
            else:
                cmp_ = [(r, data["P"].get(r["id"])) for r in rs if r["id"] in data["P"]]
                same = sum(1 for r, p in cmp_ if r["text"] == p["text"])
                divs = [first_div(r["text"], p["text"]) for r, p in cmp_ if r["text"] != p["text"]]
                ident = f"{same}/{len(cmp_)}"; fd = str(int(statistics.median(divs))) if divs else "-"
            ng = mal = mgl = "-"
            if arm in CAPS:
                have, cnt, sd, sa, sg = ngram_deltas(data[arm], c)
                ng = str(cnt) if have else "n/a (no per-request stats)"
                if have and sd: mal = f"{sa/sd:.2f}"; mgl = f"{sg/sd:.2f}"
            L.append(f"| {c} | {arm} | {len(rs)} | {dn} | {da} | {acc} | {ident} | {fd} | {ng} | {mal} | {mgl} |")
    L += ["", "## Mean accepted ngram draft length versus cap (ALL classes, then per class)", "",
          "cap = --spec-ngram-mod-n-max. gen/cap = mean generated ngram draft length over the cap (1.0 = every draft saturates the cap); "
          "acc/gen = fraction of generated ngram tokens accepted. Rising mean accepted length with cap = width is being used.", "",
          "| arm | cap | class | ngram drafts | mean gen len | mean accepted len | gen/cap | acc/gen |", "|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        if arm not in CAPS: continue
        for c in ["ALL"] + CLASSES:
            have, cnt, sd, sa, sg = ngram_deltas(data[arm], c)
            if not (have and sd):
                L.append(f"| {arm} | {CAPS[arm]} | {c} | n/a | - | - | - | - |"); continue
            L.append(f"| {arm} | {CAPS[arm]} | {c} | {sd} | {sg/sd:.2f} | {sa/sd:.2f} | {sg/sd/CAPS[arm]:.2f} | {sa/sg if sg else 0:.2f} |")
    L += ["", "## Speed (paired-only): each non-P arm vs the |P - P2| floor", "",
          "Mean timings.predicted_per_second per class. delta = arm vs mean(P,P2). floor = |P-P2|/mean(P,P2). "
          "A delta is only a signal if |delta| > floor.", "",
          "| class | arm | tok/s | delta % vs mean(P,P2) | floor % | verdict |", "|---|---|---|---|---|---|"]
    def mtps(arm, c):
        v = [r["tps"] for r in data[arm].values() if r["tps"] and (c == "ALL" or r["suite"] == c)]
        return statistics.mean(v) if v else None
    for c in classes:
        p, p2 = mtps("P", c), mtps("P2", c)
        for arm in ARMS:
            if arm in ("P", "P2"): continue
            w = mtps(arm, c)
            if None in (p, p2, w):
                L.append(f"| {c} | {arm} | {w} | n/a | n/a | incomplete |"); continue
            base = (p + p2) / 2; floor = abs(p - p2) / base * 100; d = (w - base) / base * 100
            v = "within noise" if abs(d) <= floor else ("faster" if d > 0 else "slower")
            L.append(f"| {c} | {arm} | {w:.2f} | {d:+.2f} | {floor:.2f} | {v} |")
    L += ["", "## Arm-level impl stats (last 'statistics' lines seen in each server log)", ""]
    for arm in ARMS:
        p = os.path.join(RES, f"{arm}.logstats.json")
        L.append(f"- {arm}: " + (json.dumps(json.load(open(p)).get("impl_stats_last_seen")) if os.path.exists(p) else "no logstats"))
    L += ["", "Note: draft_n/draft_n_accepted are totals over ALL impls that won a round; "
          "ngram-supplied counts come from the per-impl '#gen drafts' counter in the verbosity-4 log."]
    open(os.path.join(RES, "summary.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("sample"); s.add_argument("--force", action="store_true"); s.set_defaults(f=cmd_sample)
    r = sp.add_parser("run"); r.add_argument("--arm", required=True, choices=ARMS)
    r.add_argument("--base", default=os.environ.get("EVAL_BASE", "http://127.0.0.1:18170"))
    r.add_argument("--log"); r.add_argument("--timeout", type=float, default=3600); r.set_defaults(f=cmd_run)
    f = sp.add_parser("finalstats"); f.add_argument("--arm", required=True); f.add_argument("--log", required=True); f.set_defaults(f=cmd_finalstats)
    m = sp.add_parser("summary"); m.set_defaults(f=cmd_summary)
    a = ap.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
