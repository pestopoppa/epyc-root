#!/usr/bin/env python3
"""INF-70 harness1 -> `coherence_gate` (TD-30d item 2): paired verdict between two arm row files.

Replaces per-arm absolute labels (`classify.py`, frozen v1/v1.1, DEPRECATED 2026-10-04) with the
shared PAIRED gate: `base` = the anchor arm, `cand` = the arm under test. Reads the `*.rows.jsonl`
that `client.py` writes ({id, text, token_ids, finish, verdict, ...}); a row that failed over HTTP
(`verdict == "HTTP-ERROR"`, no text) cannot be judged, so it is DROPPED FROM BOTH SIDES and listed
under `dropped_http_error`; the gate then cannot PASS on a partial pair set without saying so (the
list is in the output and a non-empty list forces `gate_with_drops` != PASS).

Real token ids are required (or a tokenizer); the library refuses synthetic ids. The old 16-char
`sha` is not a digest the library can use and is ignored.

  python3 gate_arms.py --base A.rows.jsonl --cand B.rows.jsonl --anchor-arm LABEL \
      --anchor-binary 10303 [--truth question_pool.jsonl] [--tokenizer tokenizer.json] [--out v.json]

Exit 0 only for gate PASS with nothing dropped; 1 FAIL; 2 INCOMPLETE or drops; 3 bad input.
No server, no inference.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

LIB = os.environ.get("COHERENCE_GATE_LIB", "/mnt/raid0/llm/epyc-inference-research/scripts/lib")


def _gate():
    if LIB not in sys.path:
        sys.path.insert(0, LIB)
    import coherence_gate  # noqa: PLC0415

    return coherence_gate


def load_rows(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def usable(rows):
    """(rows the gate can read, ids dropped for HTTP failure / missing text)."""
    keep, dropped = [], []
    for r in rows:
        if r.get("verdict") == "HTTP-ERROR" or r.get("text") is None:
            dropped.append(str(r.get("id")))
        else:
            keep.append(r)
    return keep, dropped


def gate_arms(base_rows, cand_rows, *, anchor, truth=None, tokenizer=None, allow_text_only=False):
    CG = _gate()
    b, db = usable(base_rows)
    c, dc = usable(cand_rows)
    dropped = sorted(set(db) | set(dc))
    b = [r for r in b if str(r["id"]) not in dropped]
    c = [r for r in c if str(r["id"]) not in dropped]
    report = CG.evaluate(b, c, truth, tokenizer=tokenizer, allow_text_only=allow_text_only,
                         anchor=anchor)
    report["dropped_http_error"] = dropped
    gate = report["aggregate"]["gate"]
    report["gate_with_drops"] = gate if not dropped or gate == "FAIL" else "INCOMPLETE"
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--cand", required=True)
    ap.add_argument("--anchor-arm", required=True, help="what the base arm IS (recorded)")
    ap.add_argument("--anchor-binary", required=True, help="binary version of the anchor (recorded)")
    ap.add_argument("--truth")
    ap.add_argument("--tokenizer", help="tokenizer.json (HFTokenizer) when rows lack token_ids")
    ap.add_argument("--allow-text-only", action="store_true",
                    help="declared text-only surrogate; recorded in the report")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    CG = _gate()
    try:
        tok = CG.HFTokenizer(a.tokenizer) if a.tokenizer else None
        truth = CG.load_jsonl(a.truth) if a.truth else None
        report = gate_arms(load_rows(a.base), load_rows(a.cand),
                           anchor={"arm": a.anchor_arm, "binary_version": a.anchor_binary},
                           truth=truth, tokenizer=tok, allow_text_only=a.allow_text_only)
    except (CG.GateInputError, CG.TokenProvenanceError, OSError, ValueError) as e:
        print(f"gate_arms: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    report["inputs"] = {"base": str(a.base), "cand": str(a.cand)}
    text = json.dumps(report, indent=1, sort_keys=True)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    ag = report["aggregate"]
    print(json.dumps({"gate": ag["gate"], "gate_with_drops": report["gate_with_drops"], "n": ag["n"],
                      "identical": ag["identical"], "regressions": ag["regressions"],
                      "needs_review": ag["needs_review"], "dropped_http_error": report["dropped_http_error"]}))
    gwd = report["gate_with_drops"]
    return 0 if gwd == "PASS" else (1 if gwd == "FAIL" else 2)


if __name__ == "__main__":
    sys.exit(main())
