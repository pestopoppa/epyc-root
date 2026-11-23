#!/usr/bin/env python3
"""AP-BSV2-ACCEPT-RIGOR offline replay (read-only).

Reads ALL autopilot journal shards (base + rotated, numeric order) and counts how
many past accepts would survive the amended BSV-2 rules R1-R5. Light parsing only.
Usage: bsv2_accept_rigor_replay.py <orchestration_dir>
"""
import json
import re
import sys
from pathlib import Path

MUT = {"numeric_trial", "structural_experiment", "prompt_mutation", "gepa_optimize", "code_mutation"}
pat = re.compile(r"^autopilot_journal(?:_(\d+))?\.jsonl$")


def shards(d):
    out = []
    for p in Path(d).iterdir():
        m = pat.match(p.name)
        if m:
            out.append((int(m.group(1) or 0), p))
    return [p for _, p in sorted(out)]


def has_key(o, sub):
    if isinstance(o, dict):
        return any(sub in k or has_key(v, sub) for k, v in o.items())
    return False


def main(d):
    recs, bad = [], 0
    files = shards(d)
    for p in files:
        for line in p.open():
            try:
                r = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if "trial_id" in r:
                recs.append(r)
    recs.sort(key=lambda r: r.get("timestamp", ""))
    seen = set()  # qids of every earlier trial = the search history
    by_id = {}
    stats = dict(total=len(recs), accepts=0, with_qr=0, R1=0, R2=0, R3=0, R4=0, R5=0, all=0)
    for r in recs:
        ed = r.get("eval_details") or {}
        qr = ed.get("question_results") or []
        qids = {q["qid"] for q in qr if "qid" in q}
        if r.get("keep_revert_decision") == "keep" and r.get("action_type") in MUT:
            stats["accepts"] += 1
            stats["with_qr"] += bool(qr)
            r1 = bool(qids) and not (qids & seen)
            # fresh parent re-run: a same-trial paired baseline eval (not the parent's journaled outcome)
            r2 = any(k in ed for k in ("seq_paired_baseline", "bsv2_baseline", "fresh_parent_eval"))
            aud = {q["qid"] for q in qr if q.get("partition") == "audit"}
            r3 = bool(aud) and not (aud & seen)
            blob = {**ed, **(r.get("harness_metrics") or {})}
            r4 = has_key(blob, "tokens_per_accepted") or has_key(blob, "status_split")
            r5 = has_key(blob, "rollout_budget") or has_key(blob, "token_budget")
            for k, v in (("R1", r1), ("R2", r2), ("R3", r3), ("R4", r4), ("R5", r5)):
                stats[k] += v
            stats["all"] += r1 and r2 and r3 and r4 and r5
        seen |= qids
        by_id[r["trial_id"]] = r
    print(json.dumps(dict(shards=[p.name for p in files], unparseable=bad, **stats), indent=1))


main(sys.argv[1])
