#!/usr/bin/env python3
"""Read-only: how much of the INFERENCE backlog has produced a DECISION, not just a run.

Classes (strict; "rc0"/"complete" alone is never DECIDED):
  DECIDED          a verdict word (PASS/FAIL/KEEP/REJECT/NEGATIVE/PERSISTS/...) is recorded on a tagged or ticked
                   handoff line that names the row, one of its FILLERS ids, or its item code
  DIAGNOSTIC-ONLY  decision column / basis says diagnostic, a run completed, an observation line is filed
  RAN-NO-VERDICT   >=1 run ended rc0/rc75 (or .complete) and no verdict line was found
  RAN-FAILED-ONLY  every run ended in another rc
  NEVER-RUN        no mapped run at all

Mapping: row id -> handoff via the domain-index tables; row -> FILLERS rows via row id in id/owner/decision cells,
else handoff file name anywhere in the row, else curated prep_aliases. Ambiguous mappings are flagged, not guessed.
Usage: verdict_count.py [--days 14] [--json OUT] [--repo DIR] [--fillers F] [--grants D]
"""
import argparse, collections, datetime as dt, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FILLERS = Path("/mnt/raid0/llm/tmp/compute-flags/FILLERS.md")
GRANTS = Path("/mnt/raid0/llm/tmp/compute-flags/grants")
OKRC = {0, 75}
HARD = re.compile(r"\b(KEEP|REJECT(?:ED)?|NEGATIVE|PERSISTS|NO-GO|ADOPT(?:ED)?|REFUTED|NOT-FAIL|VETO)\b|"
                  r"\bverdict\W{1,3}(?:\*\*)?(?:PASS|FAIL|KEEP|REJECT|NEGATIVE|POSITIVE|NOT|GO)", re.I if False else 0)
SOFT = re.compile(r"\b(PASS(?:ED)?|FAIL(?:ED)?|CONFIRMED|HOLDS|ACCEPTED|SUPPORTED|NULL)\b")
GATEW = re.compile(r"gate|pre-?reg|predeclared|criterion|threshold|McNemar|band|decision rule|verdict", re.I)
RUNFAIL = re.compile(r"\brc[1-9]\d*\b|SIGKILL|INVALID|INCONCLUSIVE|INCOMPLETE|NOT_RUN|crash|died|dead")


def verdict_of(l):
    m = HARD.search(l)
    if m and not (RUNFAIL.search(l) and not re.search(r"KEEP|REJECT|NEGATIVE|PERSISTS|NO-GO|REFUTED|NOT-FAIL", l)):
        return m.group(0)
    m = SOFT.search(l)
    if m and GATEW.search(l) and not RUNFAIL.search(l):
        return m.group(0)
    return None


TAG = re.compile(r"\[(?:belief: (?:clm_\S+|cc)|no-belief: [^\]]*)\]")
DATE = re.compile(r"(20\d\d-\d\d-\d\d)")
ROWID = re.compile(r"\b[A-Z]{2,4}-\d{2}\b")
ITEM = re.compile(r"\b[A-Z][A-Z0-9]{1,}(?:-[A-Z0-9][A-Z0-9.]*)+\b")


# Hand-reviewed lines that carry a verdict word but are NOT a recorded outcome for the row (task text / incidental citation).
# Keyed (row, handoff file, line number substring-stable text prefix).
NOT_A_VERDICT = {("INF-60", "qwen38-27b-replace-qwen36.md", "Q38-T10.1 \u2014 Serving gate"),
                 ("EVL-47", "vidya-belief-substrate-program.md", "VB-NEW13-WIRE")}
PATH = re.compile(r"/mnt/raid0/llm/[\w./\-]+")


def load_fillers(p):
    rows = []
    for l in p.read_text().splitlines():
        if not l.startswith("| ") or l.startswith("| filler-id") or l.startswith("|---"):
            continue
        c = [x.strip() for x in l.strip().strip("|").split(" | ")]
        if len(c) < 8:
            continue
        rows.append(dict(id=c[0], owner=c[1], status=c[7], line=l, decision=c[14] if len(c) > 15 else "-",
                         min_effect=c[15] if len(c) > 15 else "-", short=len(c) < 18))
    return rows


def run_info(gdir, fid):
    rc = t = None
    e = gdir / f"{fid}.ended"
    if e.exists():
        m = re.search(r"rc=(\d+)", e.read_text())
        tm = re.search(r"time=(\S+)", e.read_text())
        rc = int(m.group(1)) if m else None
        t = tm.group(1) if tm else None
    comp = (gdir / f"{fid}.complete")
    if comp.exists():
        tm = re.search(r"time=(\S+)", comp.read_text())
        if rc is None:
            rc, t = 0, (tm.group(1) if tm else None)
    return rc, t


def index_map(repo):
    own = collections.defaultdict(list)
    for f in sorted((repo / "handoffs/active").glob("*index*.md")):
        for l in f.read_text().splitlines():
            m = re.match(r"\|\s*([A-Z]{2,4}-\d{2})\s*\|", l)
            if m:
                for h in re.findall(r"\(([\w.\-]+\.md)\)", l):
                    if h not in own[m.group(1)]:
                        own[m.group(1)].append(h)
    return own


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=REPO)
    ap.add_argument("--fillers", type=Path, default=FILLERS)
    ap.add_argument("--grants", type=Path, default=GRANTS)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--today", default=None)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    repo = a.repo
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    bp = json.loads((repo / "handoffs/active/backlog-priority.json").read_text())
    rows = {k: v for k, v in bp["rows"].items() if v["kind"] in ("inference-prep", "inference-ready")}
    cur = repo / "scripts/handoffs/backlog_priority_curated.json"
    aliases = {k: v for k, v in json.loads(cur.read_text()).get("prep_aliases", {}).items() if k != "_doc"} if cur.exists() else {}
    own = index_map(repo)
    h_rows = collections.defaultdict(set)
    for r in rows:
        for h in own.get(r, []):
            h_rows[h].add(r)
    fil = load_fillers(a.fillers)
    # ---- filler -> rows
    f2r = {}
    for f in fil:
        cells = " ".join([f["id"], f["owner"], f["decision"]])
        ids = [x for x in ROWID.findall(cells) if x in rows]
        how, amb = None, ""
        if ids:
            how, tgt = "row-id", sorted(set(ids))
        else:
            hs = sorted({h for h in re.findall(r"[\w.\-]+\.md", f["line"]) if h in h_rows})
            tgt = sorted({r for h in hs for r in h_rows[h]})
            if tgt:
                how = "handoff"
                if len(tgt) > 1:
                    amb = "handoff shared by " + ",".join(tgt)
            else:
                for rx, rid in aliases.items():
                    if rid in rows and re.search(rx, f["id"]):
                        how, tgt = "alias", [rid]
                        break
                else:
                    weak = sorted({x for x in ROWID.findall(f["line"]) if x in rows})
                    if weak:
                        how, tgt, amb = "weak-row-id", weak, "row id only in notes"
        if how:
            f2r[f["id"]] = (how, tgt, amb, f)
    # ---- text corpora
    hand_lines = {}
    for p in (repo / "handoffs/active").glob("*.md"):
        hand_lines[p.name] = p.read_text(errors="replace").splitlines()
    prog = []
    for p in sorted((repo / "progress").glob("*/*.md")):
        m = DATE.search(p.name)
        if m:
            prog.append((m.group(1), p.name, p.read_text(errors="replace").splitlines()))
    out, events = [], collections.defaultdict(set)
    for rid, rv in rows.items():
        mine = [(fid, v) for fid, v in f2r.items() if rid in v[1]]
        runs = []
        for fid, (how, tgt, amb, f) in mine:
            rc, t = run_info(a.grants, fid)
            if rc is not None:
                runs.append((t or "", fid, rc))
        runs.sort()
        ok = [x for x in runs if x[2] in OKRC]
        hs = own.get(rid, [])
        tokens = {rid} | {fid for fid, _ in mine}
        item_tok = set(ITEM.findall(rv.get("basis", "")))
        item_tok = {t for t in item_tok if not re.match(r"T\d|INF-|P-|I-", t) and len(t) > 4}
        tokens |= item_tok
        tokens = {t for t in tokens if len(t) >= 5}
        verdicts = []
        for h in hs:
            for i, l in enumerate(hand_lines.get(h, []), 1):
                vd = verdict_of(l)
                if not vd:
                    continue
                if not (TAG.search(l) or re.search(r"\[x\]", l)):
                    continue
                if not any(t in l for t in tokens):
                    continue
                if any(r_ == rid and h == f_ and k in l for r_, f_, k in NOT_A_VERDICT):
                    continue
                d = DATE.search(l)
                verdicts.append(dict(file=h, line=i, date=d.group(1) if d else None,
                                     verdict=vd, text=re.sub(r"\s+", " ", l.strip())[:220]))
        pverd = []
        for d, fn, ls in prog:
            for i, l in enumerate(ls, 1):
                if verdict_of(l) and any(t in l for t in tokens):
                    pverd.append((d, fn, i))
        decs = [f for _, (_, _, _, f) in mine]
        okf = {x[1] for x in ok}
        rule = [f["decision"] for f in decs if f["decision"] not in ("-", "", "n/a")]
        okdec = [f for f in decs if f["id"] in okf]
        diag = bool(okdec) and all(re.search(r"diagnostic|n/a|observe|calibrat|census|profile|why |what ", f["decision"], re.I)
                                   for f in okdec)
        obs = False
        if diag:
            for h in hs:
                for l in hand_lines.get(h, []):
                    if (TAG.search(l) or "[x]" in l) and DATE.search(l) and any(f["id"] in l for f in okdec):
                        obs = True
                        break
        if verdicts:
            cls = "DECIDED"
        elif diag and obs:
            cls = "DIAGNOSTIC-ONLY"
        elif ok:
            cls = "RAN-NO-VERDICT"
        elif runs:
            cls = "RAN-FAILED-ONLY"
        else:
            cls = "NEVER-RUN"
        best = None
        for t, fid, rc in reversed(ok):
            f = f2r[fid][3]
            if f["decision"] not in ("-", "", "n/a") and not re.search(r"^enables", f["decision"], re.I):
                best = dict(filler=fid, rc=rc, time=t, decision=f["decision"][:200], min_effect=f["min_effect"][:100],
                            paths=PATH.findall(f["line"])[:2])
                break
        for v in verdicts:
            if v["date"]:
                events[v["date"]].add((rid, v["file"], v["line"]))
        for d, fn, i in pverd:
            events[d].add((rid, "progress:" + fn, i))
        amb = sorted({x[2] for _, x in mine if x[2]})
        if not mine:
            amb.append("no FILLERS row mapped")
        if not hs:
            amb.append("no index row/handoff")
        last = runs[-1] if runs else None
        out.append(dict(row=rid, kind=rv["kind"], handoff=hs, cls=cls, score=rv.get("score"),
                        verdict=verdicts[:1] and verdicts[0], n_verdict_lines=len(verdicts), n_progress_lines=len(pverd),
                        fillers=[(fid, v[0]) for fid, v in mine], n_runs=len(runs), n_ok=len(ok),
                        last_run=dict(filler=last[1], rc=last[2], time=last[0]) if last else None,
                        last_ok=dict(filler=ok[-1][1], rc=ok[-1][2], time=ok[-1][0]) if ok else None,
                        rules=rule[:2], diag=diag, best_ok=best, ambiguity=amb, basis=rv.get("basis", "")[:160]))
    cnt = collections.Counter(x["cls"] for x in out)
    series = {}
    for i in range(a.days - 1, -1, -1):
        d = (today - dt.timedelta(days=i)).isoformat()
        ev = events.get(d, set())
        series[d] = dict(handoff_ticks=sum(1 for e in ev if not e[1].startswith("progress:")),
                         progress_lines=sum(1 for e in ev if e[1].startswith("progress:")),
                         rows=len({e[0] for e in ev}))
    ds = list(series)
    w1 = sum(series[d]["rows"] for d in ds[-7:])
    w0 = sum(series[d]["rows"] for d in ds[-14:-7])
    print(f"inference rows: {len(out)}  (" + ", ".join(f"{k}={cnt.get(k,0)}" for k in
          ["DECIDED", "DIAGNOSTIC-ONLY", "RAN-NO-VERDICT", "RAN-FAILED-ONLY", "NEVER-RUN"]) + ")")
    print("decisions/day (rows with a verdict line dated that day; ticks; progress-log lines):")
    for d, s in series.items():
        print(f"  {d}  rows={s['rows']:2d} ticks={s['handoff_ticks']:2d} progress={s['progress_lines']:2d}")
    print(f"decisions/week (distinct row-days): last 7d={w1}  prior 7d={w0}")
    if a.top:
        cand = [x for x in out if x["cls"] == "RAN-NO-VERDICT" and x["best_ok"]]
        cand.sort(key=lambda x: (not re.search(r"\d", x["best_ok"]["min_effect"]) or x["best_ok"]["min_effect"].startswith("n/a"), -(x["score"] or 0)))
        print(f"top {a.top} RAN-NO-VERDICT rows with a decision-bearing rc0/rc75 run (unread results):")
        for x in cand[:a.top]:
            b = x["best_ok"]
            print(f"  {x['row']:7s} {b['filler']} rc{b['rc']} {b['time']}  {b['decision'][:90]}")
    if a.json:
        a.json.write_text(json.dumps(dict(today=str(today), counts=cnt, series=series, week=dict(last7=w1, prior7=w0),
                                          rows=out), indent=1, default=list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
