#!/usr/bin/env python3
"""cc-extract/v1 — deterministic committed-conclusion PROPOSER (VB-CC-2).

Design: docs/design/committed-conclusions-belief-capture-2026-10-25.md §3.2 step 1 and the §3.5
"planned refinement": gate on the item (an UNTICKED checkbox is never a conclusion), then score
per SENTENCE, not per item, because one item often mixes "adds runner + tests" with the result.

It only PROPOSES. Every output row is a DRAFT for the confirmer (§3.2 step 2, §3.4): it carries
`"draft": true` and no `confirmed_by`, and it never writes the register. A confirmed row is
written through `cli.py conclusion add`, which resolves the git anchor and audits the quote.
This module contains no grading rule and no ladder: the score is a proposal threshold only;
grade is decided by `claim_tuple.grade()` at projection, as for every other row.

Candidate streams (all read from a git ref, default origin/main, never the working tree):
  * handoff items: `handoffs/{active,completed,archived,blocked}/*.md`, a checkbox/bullet line
    plus its continuation lines (`committed_conclusion.item_extent`), ticked or verdict-led prose;
  * progress lines: bullets and table rows under `### Results / Verdict / Findings` headings in
    `progress/**/*.md`.

Usage:
  cc_extract.py scan [--ref origin/main] [--paths GLOB ...] [--out drafts.jsonl]
  cc_extract.py items --items class_a_items.json [--labels gold.json] [--out ac0.json]
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapters import committed_conclusion as ccm  # noqa: E402

EXTRACTOR = "cc-extract/v1"
THRESHOLD = 2            # proposal stage, tuned low (AC0). Chosen IN-SAMPLE on the 120 Class-A items:
                         # best-sentence >= 3 gave R 0.74; >= 2 gives R 0.926 at P 0.60. Confirmation
                         # removes false positives (design §3.2); held-out precision comes from it.

# ------------------------------------------------------------------ lexicon (det.py v2 + §3.5 adds)
VERDICT = re.compile(
    r"\b(KEEP|NULL|NO-GO|GO|PASS(?:ED)?|FAIL(?:ED)?|REGRESS(?:ED|ION)|REJECTED|PARKED|DEAD|"
    r"CONFIRMED|REFUTED|FALSIFIED|RETRACTED|DROPPED|ADOPTED|SHELVED|INCONCLUSIVE|NEGATIVE|"
    r"VERDICT|NOT FOLDED|NOT significant|NOT SIGNIFICANT|DETECTED|WINS|LOSES|CORRECTED|"
    r"VALIDATED|REVERSAL|SURVIVES?)\b")
OUTCOME = re.compile(
    r"(?i)\b(?:verdict|falsified|refuted|rejected|within noise|(?:did|does|do) not "
    r"(?:reproduce|land|survive|discriminate|replicate)|not significant|not folded|negative|"
    r"inverts?|no keeps?|collapses|not met|beats?|wins(?: outright)?|loses|agree[sd]?|leaks?|"
    r"non-?determinis\w+|not a bug|faster|slower|regress\w*|improv\w*|is linear|ties|passed|"
    r"NOT recoverable|exceeds|catches up|survives?|matches|differs?|reversal|outperform\w*|"
    r"underperform\w*|no gain|no effect|gains?|drops?|loads coherently)\b")
QTY = re.compile(
    r"(?i)(?<![\w.])[+−-]?\d+(?:\.\d+)?(?:e-?\d+)?\s*(?:t/s|tok/s|tokens?/s|%|ms\b|s\b|x\b|"
    r"×|pp\b|GiB|MiB|GB|ppl|kld|nmse|acc\b|xRT)|pass@\d+|\bp\s*[=<≈]\s*0?\.\d+|"
    r"\bn\s*=\s*\d+|\bppl\b|\bwer\b")
FRAC = re.compile(r"\b\d+\s*(?:/|of)\s*\d+\b|\b\d+(?:\.\d+)?\s*(?:->|→)\s*\d+(?:\.\d+)?")
DELTA = re.compile(r"[+−-]\d+(?:\.\d+)?\s*(?:%|pp)|\bvs\.?\b|\bA/B\b|\bpaired\b|\bbaseline\b")
PLUMB = re.compile(
    r"(?i)\b(?:adds?|added|implement\w*|wiring|wire[sd]?|scaffold(?!-)\w*|runner|builders?|"
    r"plumbing|dry-?run|harness|fixture|landed|merged|BUILT|filed|seed\w*|plan|designed|"
    r"delivered|decision package|re-?base|ratif\w+|hardening|worktree|logging|schema|preflight|"
    r"CLI|API|download\w*|restored|rename\w*|wrapper|generator|helper|tests? pass)\b")
NUMBER = re.compile(r"(?<![\w.-])\d+(?:\.\d+)?(?![\w-])")

CHECKBOX = re.compile(r"^\s*(?:>\s*)?[-*] \[([ xX])\]")
TASK_ID = re.compile(r"\*\*(?=[A-Za-z0-9.-]*\d)([A-Z][A-Za-z0-9]*(?:[-./][A-Za-z0-9]+)*)\b")
DATE = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})|\b(20\d{2}-\d{2}-\d{2})\b")
SENT_SPLIT = re.compile(r"(?<=[.;!?])\s+(?=[A-Z*(`\[|~0-9])|\s+\|\s+|\s+[—–]\s+|\n")
RESULTS_HEAD = re.compile(r"(?i)^#{2,4}\s.*\b(results?|verdicts?|findings?|outcomes?)\b")

# scope proposals (§2.5): proposals only, the confirmer owns scope.model_file
MODEL = re.compile(r"\b((?:Qwen|gemma|Gemma|GLM|DeepSeek|DS|Llama|Mistral|Hy-MT|whisper|Kimi|"
                   r"MiniMax|gpt-oss|Phi)[\w.\-]*(?:-\d+(?:\.\d+)?[BbMm](?:-A\d+[Bb])?)?[\w.\-]*)")
QUANT = re.compile(r"\b((?:UD-)?(?:IQ\d_[A-Z0-9_]+|Q\d_(?:K_[SML]|K|0|1)|Q\d_\d|f16|bf16|F16|BF16|"
                   r"NVFP4|MXFP4|int8|q8_0))\b")
GPU = re.compile(r"(?i)\b(MI210|gfx90a|gpu|hip|rocm)\b")
CPU = re.compile(r"(?i)\b(cpu|epyc|numa|9655)\b")
METRIC = re.compile(r"(?i)([+−-]?\d+(?:\.\d+)?)\s*(t/s|tok/s|%|ms|x|×|pp|xRT)(?![\w])")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if s and s.strip()]


def score_sentence(s: str) -> tuple[int, list[str]]:
    """Additive §3.5 v2 features evaluated on ONE sentence. Returns (score, fired features)."""
    head = s[:140]
    v, o, q = bool(VERDICT.search(s)), bool(OUTCOME.search(s)), bool(QTY.search(s))
    f, d = bool(FRAC.search(s)), bool(DELTA.search(s))
    pl = bool(PLUMB.search(head)) and not v and not (o and q)
    feats = [n for n, on in (("verdict", v), ("outcome", o), ("qty", q), ("frac", f),
                             ("delta", d), ("plumbing", pl)) if on]
    sc = 3 * v + 2 * o + 2 * q + f + d + (1 if o and NUMBER.search(s) else 0) - 2 * pl
    return sc, feats


def tick_state(text: str) -> bool | None:
    m = CHECKBOX.match(text)
    return None if not m else m.group(1) in "xX"


def score_item(text: str) -> dict[str, Any]:
    """Gate on the item, then score per sentence; the item scores its best sentence."""
    tick = tick_state(text)
    if tick is False:
        return {"tick": False, "score": None, "proposed": False, "gate": "unticked",
                "best_sentence": None, "features": []}
    best, best_s, best_f = -99, "", []
    for s in _sentences(text):
        sc, feats = score_sentence(s)
        if sc > best:
            best, best_s, best_f = sc, s, feats
    return {"tick": tick, "score": best, "proposed": best >= THRESHOLD, "gate": "pass",
            "best_sentence": best_s[:300], "features": best_f}


# ------------------------------------------------------------------ draft row fields

def stated_of(text: str) -> dict[str, Any]:
    m = VERDICT.search(text)
    metrics = []
    for mm in METRIC.finditer(text):
        val = mm.group(1).replace("−", "-")
        try:
            metrics.append({"metric": None, "value": float(val), "unit": mm.group(2)})
        except ValueError:
            continue
        if len(metrics) >= 8:
            break
    n = re.search(r"\bn\s*=\s*(\d+)", text)
    dm = DATE.search(text)
    return {"verdict_native": m.group(1) if m else None, "metrics": metrics,
            "n": int(n.group(1)) if n else None, "protocol_named": None,
            "date": (dm.group(1) or dm.group(2)) if dm else None}


def scope_of(text: str, heading: str = "") -> tuple[dict[str, Any], str]:
    def probe(t: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if (m := MODEL.search(t)):
            out["model_hint"] = m.group(1)
        if (m := QUANT.search(t)):
            out["quant"] = m.group(1)
        if GPU.search(t):
            out["backend"] = "gpu"
        elif CPU.search(t):
            out["backend"] = "cpu"
        return out
    sc = probe(text)
    if sc:
        return sc, "line"
    sc = probe(heading)
    return (sc, "heading") if sc else ({}, "none")


def dedup_key(text: str) -> str:
    """task_id when present, else the normalised quote (§3.2): merges progress restatements."""
    m = TASK_ID.search(text)
    if m:
        return "task:" + m.group(1)
    return "quote:" + hashlib.sha256(ccm.cc_norm(text).lower().encode()).hexdigest()[:24]


def draft_row(path: str, start: int, end: int, text: str, heading: str = "") -> dict[str, Any]:
    first = text.split("\n", 1)[0]
    hn = ccm.head_norm(first)
    sc = score_item(text)
    scope, ev = scope_of(text, heading)
    tid = TASK_ID.search(text)
    return {
        "draft": True, "extractor": EXTRACTOR,
        "cc_id": ccm.cc_id(path, hn), "dedup_key": dedup_key(text),
        "kind": "result", "task_id": tid.group(1) if tid else None,
        "anchor_hint": {"path": path, "line_start": start, "line_end": end,
                        "quote_sha256": ccm.quote_sha(text), "head_norm": hn,
                        "quote_norm_rule": ccm.NORM_RULE},
        "quote": text, "stated": stated_of(text),
        "scope_proposal": scope, "scope_evidence": ev,
        "proposal": sc,
    }


# ------------------------------------------------------------------ git streams

def _git(ref_repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(ref_repo), *args], capture_output=True, check=True)
    return r.stdout.decode("utf-8", "replace")


def iter_handoff_items(lines: list[str]) -> Iterable[tuple[int, int, str, str]]:
    heading = ""
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            heading = ln
        t = tick_state(ln)
        verdict_led = t is None and bool(VERDICT.search(ln[:160])) and bool(ln.strip())
        if t is True or verdict_led:
            try:
                s, e = ccm.item_extent(lines, i + 1)
            except ccm.ProjectionError:
                i += 1
                continue
            yield s, e, "\n".join(lines[s - 1:e]), heading
            i = e
            continue
        i += 1


def iter_progress_lines(lines: list[str]) -> Iterable[tuple[int, int, str, str]]:
    heading, in_res = "", False
    for i, ln in enumerate(lines):
        if ln.startswith("#"):
            heading, in_res = ln, bool(RESULTS_HEAD.match(ln))
            continue
        if in_res and re.match(r"^\s*(?:[-*]|\d+\.|\|)", ln) and not re.match(r"^\s*\|[\s:|-]+\|?$", ln):
            yield i + 1, i + 1, ln, heading


def scan(repo: Path, ref: str, globs: list[str]) -> list[dict[str, Any]]:
    files = _git(repo, "ls-tree", "-r", "--name-only", ref).split("\n")
    out: list[dict[str, Any]] = []
    for path in sorted(f for f in files if f.endswith(".md")):
        handoff = re.match(r"handoffs/(active|completed|archived|blocked)/", path)
        progress = path.startswith("progress/")
        if not (handoff or progress):
            continue
        if globs and not any(fnmatch.fnmatch(path, g) for g in globs):
            continue
        lines = _git(repo, "show", f"{ref}:{path}").split("\n")
        it = iter_handoff_items(lines) if handoff else iter_progress_lines(lines)
        for s, e, text, heading in it:
            row = draft_row(path, s, e, text, heading)
            if row["proposal"]["proposed"]:
                out.append(row)
    return merge_restatements(out)


def merge_restatements(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One draft per dedup key: a handoff anchor wins, progress restatements become also_anchored."""
    by: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for r in sorted(rows, key=lambda r: (not r["anchor_hint"]["path"].startswith("handoffs/"),
                                         r["anchor_hint"]["path"], r["anchor_hint"]["line_start"])):
        k = r["dedup_key"]
        if k not in by:
            by[k] = dict(r, also_anchored=[])
            order.append(k)
        else:
            a = r["anchor_hint"]
            by[k]["also_anchored"].append({"path": a["path"], "line": a["line_start"],
                                           "line_end": a["line_end"],
                                           "quote_sha256": a["quote_sha256"]})
    return [by[k] for k in order]


# ------------------------------------------------------------------ AC0

def ac0(items: list[dict[str, Any]], gold: set[int]) -> dict[str, Any]:
    rows = []
    for i, it in enumerate(items):
        sc = score_item(it["text"])
        rows.append({"idx": i, "handoff": it.get("handoff"), "start": it.get("start"),
                     "gold": i in gold, **sc})
    prop = {r["idx"] for r in rows if r["proposed"]}
    tp = len(prop & gold)
    recall = tp / len(gold) if gold else 0.0
    precision = tp / len(prop) if prop else 0.0
    return {"extractor": EXTRACTOR, "threshold": THRESHOLD, "n_items": len(items),
            "n_gold": len(gold), "n_proposed": len(prop), "true_positives": tp,
            "recall": round(recall, 4), "precision": round(precision, 4),
            "pass": tp >= 50 and recall >= 0.92,
            "missed_gold": sorted(gold - prop), "false_positives": sorted(prop - gold),
            "items": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--repo", default=str(ccm.REPO))
    s.add_argument("--ref", default="origin/main")
    s.add_argument("--paths", nargs="*", default=[])
    s.add_argument("--out")
    a = sub.add_parser("items")
    a.add_argument("--items", required=True)
    a.add_argument("--labels")
    a.add_argument("--out")
    args = ap.parse_args(argv)
    if args.cmd == "scan":
        rows = scan(Path(args.repo), args.ref, args.paths)
        text = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"{len(rows)} draft rows -> {args.out}")
        else:
            sys.stdout.write(text)
        return 0
    items = json.loads(Path(args.items).read_text(encoding="utf-8"))
    gold = set(json.loads(Path(args.labels).read_text())) if args.labels else set()
    res = ac0(items, gold)
    blob = json.dumps(res, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(blob, encoding="utf-8")
    summary = {k: res[k] for k in ("n_items", "n_gold", "n_proposed", "true_positives",
                                   "recall", "precision", "pass", "missed_gold")}
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
