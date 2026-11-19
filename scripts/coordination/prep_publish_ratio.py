#!/usr/bin/env python3
"""Over-preparation detector (RTG-100 box "Sessions over-prepare instead of publishing", operator 2026-11-10).

Read-only. Measures, per session (row owner), over a recent window (default 48 h):
  * rows PUBLISHED  -- ready/<id>.json (also ready/<sub>/ and ready/.withdrawn/) whose published_at is in the window;
  * PREPARATION artifacts written -- in a job dir under the scratch tmp root: PREDECLARATION*.md, *packet* files/dirs,
    spec.json; and dry-run dirs under compute-flags/dryrun/<id>.
and, per preparation STEP, how many artifacts older than the conversion horizon (default 7 days) never led to a
published row. A step whose every aged artifact is unconverted is a CUT CANDIDATE: removing it from the dispatcher's
path is the box's done-criterion and stays a human/dispatcher-owner decision; this script only measures.

Attribution: a job dir converts when some published row's scratch_root / workdir / launcher / published_from lives in it;
a dry-run dir converts when a published row has its id. A job dir's owner is the owner of any row in it, else the
"owner" field of its spec.json, else "unattributed".

Exit: 0 = report written; 3 = --alert-ratio given and some session's prep/published ratio exceeds it (or it prepared
>= --alert-min-prep artifacts and published nothing).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

LLM = "/mnt/raid0/llm/"
FLAGS = os.environ.get("ROWFLOW_FLAGS", LLM + "tmp/compute-flags")
TMP = os.environ.get("PREP_TMP_ROOT", LLM + "tmp")
STEPS = ("predeclaration", "packet", "spec", "dryrun")


def _ts(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def published_rows(flags):
    """[{id, owner, at, dirs}] for every published row record (live, filed sub-dirs, withdrawn)."""
    out, seen = [], set()
    pats = [os.path.join(flags, "ready", "*.json"), os.path.join(flags, "ready", "*", "*.json")]
    for p in sorted(set(sum((glob.glob(x) for x in pats), []))) + sorted(glob.glob(os.path.join(flags, "ready", ".withdrawn", "*.json"))):
        d = _load(p)
        if not d or not d.get("id") or d["id"] in seen:
            continue
        seen.add(d["id"])
        at = _ts(d.get("published_at")) or _ts((d.get("publisher") or {}).get("at") if isinstance(d.get("publisher"), dict) else None)
        if at is None:
            try:
                at = os.path.getmtime(p)
            except OSError:
                continue
        dirs = set()
        for k in ("scratch_root", "workdir", "published_from"):
            v = d.get(k)
            if isinstance(v, str) and v:
                dirs.add(v)
        lp = d.get("launcher")
        if isinstance(lp, dict):
            lp = lp.get("path")
        if isinstance(lp, str) and lp:
            dirs.add(lp)
        out.append({"id": d["id"], "owner": str(d.get("owner") or "unattributed"), "at": at, "dirs": dirs})
    return out


def job_dir(path, tmp):
    """The top-level job dir under tmp a path lives in (tmp/<job>/...), or None."""
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(tmp))
    if rel.startswith(".."):
        return None
    head = rel.split(os.sep, 1)[0]
    return os.path.join(os.path.abspath(tmp), head) if head not in (".", "") else None


def classify(name):
    n = name.lower()
    if n.startswith("predeclaration") and n.endswith(".md"):
        return "predeclaration"
    if "packet" in n:
        return "packet"
    if n == "spec.json":
        return "spec"
    return None


def prep_artifacts(tmp, flags, since, max_depth=3):
    """[{step, path, job, mtime}] for preparation artifacts modified at or after `since`."""
    out = []
    flags_abs = os.path.abspath(flags)
    try:
        tops = [os.path.join(tmp, e) for e in os.listdir(tmp)]
    except OSError:
        tops = []
    for top in tops:
        if os.path.abspath(top) == flags_abs or not os.path.isdir(top) or os.path.islink(top):
            continue
        try:
            if os.path.getmtime(top) < since:
                continue
        except OSError:
            continue
        base = top.rstrip(os.sep).count(os.sep)
        for root, dirs, files in os.walk(top):
            if root.count(os.sep) - base >= max_depth:
                dirs[:] = []
            for name in files + list(dirs):
                step = classify(name)
                if not step:
                    continue
                p = os.path.join(root, name)
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    continue
                if m >= since:
                    out.append({"step": step, "path": p, "job": os.path.abspath(top), "mtime": m})
            dirs[:] = [d for d in dirs if "packet" not in d.lower()]   # a packet dir counts once, not its contents
    for d in glob.glob(os.path.join(flags, "dryrun", "*")):
        try:
            m = os.path.getmtime(d)
        except OSError:
            continue
        if os.path.isdir(d) and m >= since:
            out.append({"step": "dryrun", "path": d, "job": None, "rid": os.path.basename(d), "mtime": m})
    return out


def analyse(rows, prep, now, window_s, horizon_s, tmp):
    row_ids = {r["id"] for r in rows}
    job_rows = defaultdict(list)
    for r in rows:
        for d in r["dirs"]:
            j = job_dir(d, tmp)
            if j:
                job_rows[j].append(r)
    spec_owner = {}
    for a in prep:
        if a["step"] == "spec" and a["job"] not in spec_owner:
            o = (_load(a["path"]) or {}).get("owner")
            if o:
                spec_owner[a["job"]] = str(o)

    def converted(a):
        if a["step"] == "dryrun":
            return a["rid"] in row_ids
        return any(r["at"] >= a["mtime"] - 86400 for r in job_rows.get(a["job"], []))

    def owner(a):
        if a["step"] == "dryrun":
            return next((r["owner"] for r in rows if r["id"] == a["rid"]), "unattributed")
        rs = job_rows.get(a["job"])
        return rs[0]["owner"] if rs else spec_owner.get(a["job"], "unattributed")

    sess = defaultdict(lambda: {"published": 0, "prep": 0, "prep_by_step": defaultdict(int)})
    for r in rows:
        if r["at"] >= now - window_s:
            sess[r["owner"]]["published"] += 1
    for a in prep:
        if a["mtime"] >= now - window_s:
            s = sess[owner(a)]
            s["prep"] += 1
            s["prep_by_step"][a["step"]] += 1
    steps = {k: {"aged": 0, "converted": 0, "unconverted_examples": []} for k in STEPS}
    for a in prep:
        if a["mtime"] > now - horizon_s:
            continue                     # too young to judge: the row may still come
        st = steps[a["step"]]
        st["aged"] += 1
        if converted(a):
            st["converted"] += 1
        elif len(st["unconverted_examples"]) < 5:
            st["unconverted_examples"].append(a["path"])
    for k, st in steps.items():
        st["conversion"] = round(st["converted"] / st["aged"], 3) if st["aged"] else None
        st["cut_candidate"] = bool(st["aged"]) and st["converted"] == 0
    sessions = {}
    for o, s in sorted(sess.items()):
        sessions[o] = {"published": s["published"], "prep": s["prep"], "prep_by_step": dict(s["prep_by_step"]),
                       "prep_per_published": round(s["prep"] / s["published"], 2) if s["published"] else None}
    return {"sessions": sessions, "steps": steps}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--tmp", default=TMP)
    ap.add_argument("--hours", type=float, default=48.0, help="session window (default 48)")
    ap.add_argument("--horizon-days", type=float, default=7.0, help="a prep artifact older than this with no row is unconverted")
    ap.add_argument("--lookback-days", type=float, default=14.0, help="oldest prep artifact scanned")
    ap.add_argument("--alert-ratio", type=float, default=None, help="exit 3 when a session's prep/published exceeds this")
    ap.add_argument("--alert-min-prep", type=int, default=5, help="...or it wrote this many prep artifacts and published none")
    ap.add_argument("--now", type=float, default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    now = a.now if a.now is not None else time.time()
    rows = published_rows(a.flags)
    prep = prep_artifacts(a.tmp, a.flags, now - a.lookback_days * 86400)
    rep = analyse(rows, prep, now, a.hours * 3600, a.horizon_days * 86400, a.tmp)
    rep.update(generated_at=datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               window_h=a.hours, horizon_days=a.horizon_days)
    alerts = []
    if a.alert_ratio is not None:
        for o, s in rep["sessions"].items():
            if (s["published"] and s["prep"] / s["published"] > a.alert_ratio) or (not s["published"] and s["prep"] >= a.alert_min_prep):
                alerts.append(o)
    rep["alerts"] = alerts
    json.dump(rep, sys.stdout, indent=1, sort_keys=True)
    print()
    return 3 if alerts else 0


if __name__ == "__main__":
    raise SystemExit(main())
