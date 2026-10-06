#!/usr/bin/env python3
"""Deterministic at-risk list for the intake re-verification handoff.
Usage: python3 at_risk_list.py [research/intake_index.yaml] > at_risk.tsv
At risk = dive-verified|dive-overturned AND any of:
  A  empty/absent claim_anchors
  B  dive text mentions WebFetch / digest / abs page
  C  no recorded full-read evidence: read_depth not FULL/PARTIAL AND no read-depth keyword in dive text
"""
import re, sys, yaml
path = sys.argv[1] if len(sys.argv) > 1 else "research/intake_index.yaml"
d = yaml.load(open(path), Loader=yaml.CSafeLoader)
KEYS = ("notes", "dive_corrections", "dive_notes", "source_revision", "source_fetch_gaps",
        "unverifiable_from_stage2", "verification_notes")
BAD = re.compile(r"webfetch|digest|abs page", re.I)
GOOD = re.compile(r"\bPDF\b|pages?\b|Table|\bEq\b|\bline|clone|§|Section|Appendix|Figure|html|sha", re.I)
dived = [e for e in d if e.get("verification") in ("dive-verified", "dive-overturned")]
rows = []
for e in dived:
    t = " ".join(str(e.get(k, "")) for k in KEYS)
    a = not e.get("claim_anchors")
    b = bool(BAD.search(t))
    c = e.get("read_depth") not in ("FULL", "PARTIAL") and not GOOD.search(t)
    if a or b or c:
        rows.append((e["id"], e.get("ingested_date"), e["verification"], e.get("verdict"),
                     "".join(k for k, v in zip("ABC", (a, b, c)) if v)))
print("id\tingested\tverification\tverdict\tflags")
for r in sorted(rows, key=lambda r: int(r[0].split("-")[1])):
    print("\t".join(map(str, r)))
print(f"# dived={len(dived)} at_risk={len(rows)} A={sum('A' in r[4] for r in rows)} "
      f"B={sum('B' in r[4] for r in rows)} C={sum('C' in r[4] for r in rows)}", file=sys.stderr)
