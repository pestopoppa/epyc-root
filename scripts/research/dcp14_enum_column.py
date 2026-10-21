#!/usr/bin/env python3
"""DCP-17: sub-ask enumeration count column for the DCP-14 delegation propagation audit.

Report-only, no threshold, zero inference. EXTENSION of the DCP-14 detector
(artifacts/noninf-memeval-20261021/dcp14.py, sha256 aae5fcb26c1f4d3e), which is a
run-once script with import-time side effects; this module re-states ITS pairing rule
as functions so the column is testable on a fixture, and leaves dcp14.py untouched.

Pairing (identical to dcp14.py): 'start' events grouped by non-null parent_request_id;
delegate roles {worker_general, worker, worker_vision}; for each delegate call the parent
is the latest earlier non-delegate call in the group (else the earliest later one, tagged
'after'); groups without a parent-role call are 'no_parent_prompt'. Truncated prompts
(prompt_truncated true on either side) form a separate stratum and are never counted in the
enumeration columns. Unparsable = missing/non-str prompt.

Enumeration rule, FIXED before any run: a line is an enumerated sub-ask iff after leading
whitespace it begins with a bullet (-, *, +, a bullet dot), a number or single letter
followed by '.' or ')' (also '(1)'), or a markdown checkbox. Count = number of such lines.
Worker RESPONSE = concatenation of that request_id's 'chunk' events' text, in ts order.
Columns per pair: parent_enum, worker_input_enum, worker_response_enum.
No difference or match is derived: the three raw counts are given so the sub-task-count
stratum can be read downstream.
"""
import argparse, collections as C, json, re, sys

DEL = {"worker_general", "worker", "worker_vision"}
ENUM = re.compile(r"^[ \t]*(?:[-*+•]\s+(?:\[[ xX]\]\s+)?\S|(?:\d{1,3}|[A-Za-z])[.)]\s+\S|\(\d{1,3}\)\s+\S)", re.M)


def enum_count(text):
    return len(ENUM.findall(text)) if isinstance(text, str) else None


def build_pairs(events):
    starts = C.defaultdict(list)
    chunks = C.defaultdict(list)
    for e in events:
        if e.get("event") == "start" and e.get("parent_request_id"):
            starts[e["parent_request_id"]].append(e)
        elif e.get("event") == "chunk":
            chunks[e.get("request_id")].append(e)
    resp = {rid: "".join(c.get("text", "") for c in sorted(v, key=lambda x: float(x["ts_epoch"])))
            for rid, v in chunks.items()}
    pairs, nopar = [], C.Counter()
    for pid, v in starts.items():
        v.sort(key=lambda x: float(x["ts_epoch"]))
        par = [x for x in v if x["role"] not in DEL]
        for d in v:
            if d["role"] not in DEL:
                continue
            if not par:
                nopar[d["role"]] += 1
                continue
            before = [x for x in par if float(x["ts_epoch"]) <= float(d["ts_epoch"])]
            p = before[-1] if before else par[0]
            row = {"parent_request_id": pid, "parent_role": p["role"], "delegate_role": d["role"],
                   "parent_tag": "before" if before else "after", "status": "ok"}
            if not isinstance(p.get("prompt"), str) or not isinstance(d.get("prompt"), str):
                row["status"] = "unparsable"
            elif p.get("prompt_truncated") or d.get("prompt_truncated"):
                row["status"] = "truncated"
            else:
                row["parent_enum"] = enum_count(p["prompt"])
                row["worker_input_enum"] = enum_count(d["prompt"])
                row["worker_response_enum"] = enum_count(resp.get(d.get("request_id"), "")) if d.get("request_id") in resp else None
            pairs.append(row)
    return pairs, dict(nopar)


def report(events):
    pairs, nopar = build_pairs(events)
    return {"column": "sub_ask_enumeration_count", "pairs": pairs, "no_parent_prompt": nopar,
            "status_counts": dict(C.Counter(p["status"] for p in pairs))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events")
    ap.add_argument("--out")
    a = ap.parse_args()
    ev = [json.loads(l) for l in open(a.events) if l.strip()]
    r = report(ev)
    if a.out:
        json.dump(r, open(a.out, "w"), indent=1)
    print(json.dumps(r["status_counts"]), "pairs", len(r["pairs"]))
    for p in r["pairs"]:
        if p["status"] == "ok":
            print(p["parent_role"], "->", p["delegate_role"], p["parent_enum"], p["worker_input_enum"], p["worker_response_enum"])


if __name__ == "__main__":
    main()
