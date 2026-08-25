#!/usr/bin/env python3
"""duplicate_task_scan.py — cross-file semantic duplicate-TASK detector.

Owning handoff: handoffs/active/handoff-index-and-backlog-graph.md (RTG-46, open item:
"Cross-file duplicate-TASK detector (semantic, not exact-text)").

WHY THIS EXISTS. Exact-text scanning is proven insufficient: `stale-open-audit-2026-07-18.md`
returned 0 duplicates while the hand-built C2 list in the (superseded)
`coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md` documents 14 real pairs — index
rows and handoff boxes that describe the same unit of work in different words. This tool
exists to rediscover that class mechanically, so the C2 list can be re-homed and pruned.

WHAT IT DOES. Every checkbox row in `handoffs/active/*.md` (open AND closed) is compared
against every row in every OTHER file, using a three-part similarity over the row's FULL
body (first line + continuation lines, so a multi-line row is compared whole):

    seq     — difflib.SequenceMatcher on the normalized text
    dice    — 2·|A∩B|/(|A|+|B|) over stopword-filtered word tokens
    contain — |A∩B|/min(|A|,|B|)  (catches an index-row SUMMARY vs the long box it summarizes)

score = max(seq, dice, contain), and a pair is REPORTED when score >= threshold
(default 0.38). Candidate generation is two-channel to stay tractable on ~1,500 rows:
shared word-bigrams (df<=60) >= 3, OR shared distinctive unigrams (df<=200) >= 5. The
document-frequency caps remove the trivial overlap from generic words.

MEASURED (2026-08-24, live corpus: 1528 open boxes across 62 files):

  * Recall (validation set = the 14 hand-built C2 duplicate pairs, resolved by TASK TEXT
    to their current rows — the queue's file:line anchors are 60%+ rotted, text is the
    identity): 10 of the 14 still exist as live cross-file rows; the other 4 were closed,
    superseded, or their index-row member was retired. ALL 10 are rediscovered at the
    default threshold 0.38 (recall 1.00), including the hardest reworded pair
    (FrontierCS floor probe, 0.391) and the summary-vs-detail pairs (RE-2/EV-12 at 1.000).
  * Precision (every one of the 148 pairs >= 0.38 hand-classified by reading both rows):
    55/64 pairs >= 0.60 are the same unit of work filed twice (0.86); the 9 others are
    same-family-different-task rows whose shared vocabulary overstates identity (e.g.
    `llamacpp-v6:109 ~ non-inference:107` share the word "streaming", not the task).
    In 0.38-0.60 the same-unit share drops to 30/84 (0.36), but 49 of the remaining 54
    are closely-RELATED rows worth reading (cross-referencing task IDs, owner pointers,
    or sibling subtasks), so 0.94 of the full report is worth a human glance. The tool
    is a REVIEW PROMPT, not a verdict — mirroring `backlog_row_check.py`'s settled rule
    that a screen which silently refuses is a new fail-closed of its own.

DELIBERATELY NOT DETECTED (both measured as false positives at every threshold tried):
  * index-pointer rows — an index row whose next_action duplicates a box in the handoff
    it points AT is the thin-row contract working as designed, not a duplicate (C2 called
    this "index pointer vs owner"). Rows are keyed by their own file, so an index row and
    its own handoff's box are not compared against each other at all.
  * same-file rows — two boxes in one handoff are sequencing, not duplication.

Usage:
    duplicate_task_scan.py [--threshold 0.38] [--min-score N] [--max N] [--json]
    duplicate_task_scan.py --validate          # recall on the C2 ground truth
Exit codes: 0 clean, 1 found duplicates above threshold (or validation recall < 1)
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIVE = REPO_ROOT / "handoffs" / "active"
_ACTIVE_INDICES = {
    "inference-research-index.md", "routing-and-optimization-index.md",
    "research-evaluation-index.md", "user-facing-harness-index.md",
    "pipeline-integration-index.md", "reviewer-control-plane-index.md",
    "master-handoff-index.md", "CURRENT-CAMPAIGN.md",
}

# Rows shorter than this carry no usable signal and only add noise.
_MIN_TOKENS = 4

# Candidate-generation caps. These are the ONLY place document frequency enters:
# a word (or bigram) that appears in more than this many rows is generic and its
# co-occurrence proves nothing. Measured: caps of 60/200 keep the candidate set at
# ~18k pairs while preserving all 10 resolvable C2 pairs; loosening to 200/500
# triples the candidate count without recovering the 1 miss (a task-id-only pair).
_DF_BIGRAM = 60
_DF_UNIGRAM = 200
_SHARED_BIGRAMS = 3
_SHARED_UNIGRAMS = 5

_STOP = frozenset("""
a an and are as at be by for from in is it of on or that the this to was were with will
our their its your we you i they he she them these those there here what which who whom
when where why how has have had do does did not no but so if then than too very can could
should would may might must shall about into over under again further once only own same
more most other some such each few both also its than them then
""".split())


def _norm(text: str) -> str:
    """Normalized row text: links → label, markdown stripped, task-id prefix removed."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # link -> its label
    t = re.sub(r"[*`_#>]", " ", t)                      # markdown punctuation
    t = re.sub(r"✅.*$", "", t)                          # completion stamps
    t = re.sub(r"^\s*[A-Z]{2,6}-\d+\s*[—·:]\s*", "", t)  # leading task-id
    return " ".join(t.lower().split())


def _tokens(s: str) -> list[str]:
    return [w for w in s.split() if w not in _STOP and len(w) > 1]


def _bigrams(s: str) -> set[tuple[str, str]]:
    t = _tokens(s)
    return set(zip(t, t[1:]))


def _full_body(path: Path, lineno: int) -> str:
    """The whole row: first line plus continuation lines (until blank/box/heading).

    The single-line body that `backlog_row_check` passes around is the row's FIRST line;
    duplicate detection must see the whole row, or a box whose task text wraps onto its
    second line (the measured `numa-topology-cutover` case) compares only half itself.
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = [re.sub(r"^\s*- \[[ xX]\]\s*", "", lines[lineno - 1])]
    i = lineno
    while i < len(lines):
        nxt = lines[i]
        if not nxt.strip() or nxt.lstrip().startswith("#") or re.match(r"^\s*- \[[ xX]\]", nxt):
            break
        out.append(nxt)
        i += 1
    return " ".join(out)


_ROW_ID = re.compile(r"^\|\s*([A-Z]{3}-\d+)\s*\|")
_SPLIT = re.compile(r"(?<!\\)\|")
_LINK = re.compile(r"\(([A-Za-z0-9._/-]+\.md)\)")


def _index_rows() -> list[tuple[str, int, str, str, str | None]]:
    """(file, lineno, state='row', next_action_text, owned_handoff) for index table rows.

    Index rows are TABLE rows (`| EVL-01 | … | [handoff](x.md) | next action | deps |`),
    not checkboxes, and their next_action cell is a task summary — exactly the class
    C2 caught (`research-evaluation-index.md:81 ≡ backlog-roi-audit-…:16`). The row's
    OWNED handoff is carried so the scan can exclude the BY-DESIGN pointer case: an
    index row whose next_action duplicates a box in the handoff it points AT is the
    thin-row contract seeding, not a duplicate.
    """
    out: list[tuple[str, int, str, str, str | None]] = []
    for index in _ACTIVE_INDICES:
        p = ACTIVE / index
        if not p.exists():
            continue
        for lineno, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if not _ROW_ID.match(line):
                continue
            cells = _SPLIT.split(line)[1:6]                     # id | track | handoff | action | deps
            if len(cells) < 4:
                continue
            links = _LINK.findall(cells[2])
            owned = Path(links[0]).name if links else None
            n = _norm(cells[3])
            if len(_tokens(n)) < _MIN_TOKENS:
                continue
            out.append((index, lineno, "row", n, owned))
    return out


def _rows() -> list[tuple[str, int, str, str, set, set, str | None]]:
    """(file, lineno, state, normalized_body, bigrams, unigrams, owned_handoff).

    Every checkbox row (owned_handoff=None) plus every index table row
    (owned_handoff = the handoff its cell points at).
    """
    raw: list[tuple[str, int, str, str, str | None]] = []
    for p in sorted(ACTIVE.glob("*.md")):
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for lineno, line in enumerate(lines, 1):
            m = re.match(r"^\s*- \[([ xX])\]\s*(.*)", line)
            if not m:
                continue
            n = _norm(_full_body(p, lineno))
            if len(_tokens(n)) < _MIN_TOKENS:
                continue
            raw.append((p.name, lineno, m.group(1).strip().lower(), n, None))
    raw.extend(_index_rows())

    df_b: Counter = Counter(x for _, _, _, n, _ in raw for x in _bigrams(n))
    df_u: Counter = Counter(w for _, _, _, n, _ in raw for w in _tokens(n))

    rows: list[tuple[str, int, str, str, set, set, str | None]] = []
    for f, ln, st, n, owned in raw:
        gb = {x for x in _bigrams(n) if df_b[x] <= _DF_BIGRAM}
        gu = {x for x in _tokens(n) if df_u[x] <= _DF_UNIGRAM}
        if gb or gu:
            rows.append((f, ln, st, n, gb, gu, owned))
    return rows


def _score(n1: str, n2: str) -> tuple[float, float, float, float]:
    c1, c2 = Counter(_tokens(n1)), Counter(_tokens(n2))
    shared = sum((c1 & c2).values())
    dice = 2 * shared / max(1, sum(c1.values()) + sum(c2.values()))
    contain = shared / max(1, min(sum(c1.values()), sum(c2.values())))
    seq = SequenceMatcher(None, n1, n2).ratio()
    return max(seq, contain, dice), dice, contain, seq


def scan(threshold: float = 0.38) -> list[dict]:
    rows = _rows()
    inv_b: dict = {}
    inv_u: dict = {}
    for i, (f, ln, st, n, gb, gu, _o) in enumerate(rows):
        for gram in gb:
            inv_b.setdefault(gram, []).append(i)
        for gram in gu:
            inv_u.setdefault(gram, []).append(i)

    def _pointer_pair(a: int, b: int) -> bool:
        """BY-DESIGN index-pointer: an index row vs a box in the handoff it points AT.

        The thin-row contract seeds an index row's next_action from its handoff's
        first open box, so row-vs-own-handoff near-identity is the contract working,
        not a duplicate (C2: "index pointer vs owner"). Nothing else is excluded:
        an index row matching a DIFFERENT handoff's box is exactly the C2 class.
        """
        oa, ob = rows[a][6], rows[b][6]
        return (oa is not None and oa == rows[b][0]) or (ob is not None and ob == rows[a][0])

    def _candidates() -> set[tuple[int, int]]:
        seen: set[tuple[int, int]] = set()
        for idxs in inv_b.values():
            for a, b in itertools.combinations(sorted(set(idxs)), 2):
                if rows[a][0] == rows[b][0] or _pointer_pair(a, b):
                    continue
                if len(rows[a][4] & rows[b][4]) >= _SHARED_BIGRAMS:
                    seen.add((a, b) if a < b else (b, a))
        for idxs in inv_u.values():
            for a, b in itertools.combinations(sorted(set(idxs)), 2):
                if rows[a][0] == rows[b][0] or _pointer_pair(a, b):
                    continue
                if len(rows[a][5] & rows[b][5]) >= _SHARED_UNIGRAMS:
                    seen.add((a, b) if a < b else (b, a))
        return seen

    out = []
    for a, b in _candidates():
        f1, l1, s1, n1, _, _, _ = rows[a]
        f2, l2, s2, n2, _, _, _ = rows[b]
        sc, dice, contain, seq = _score(n1, n2)
        if sc < threshold:
            continue
        out.append({
            "score": round(sc, 4), "dice": round(dice, 4),
            "contain": round(contain, 4), "seq": round(seq, 4),
            "a": {"file": f1, "line": l1, "state": s1, "text": n1[:120]},
            "b": {"file": f2, "line": l2, "state": s2, "text": n2[:120]},
        })
    out.sort(key=lambda d: (-d["score"], d["a"]["file"], d["a"]["line"]))
    return out


# ---------------------------------------------------------------------------
# Validation: the C2 duplicate pairs, resolved by TASK TEXT to current rows.
#
# The queue's file:line anchors are 60%+ rotted (measured 2026-08-24); text is the
# identity. Each entry names its two distinctive task texts; resolution finds the
# current row containing each. Entries whose member rows were closed, superseded, or
# whose index-row member was retired are marked RESOLVED — they cannot be rediscovered
# because the duplicate no longer exists.
# ---------------------------------------------------------------------------
_GROUND_TRUTH = [
    # (member-A task text, member-B task text, disposition note)
    ("execution-free patch verifier", "execution-free patch verifier as gating signal",
     "RE-2 ≡ EV-12"),
    ("review-finding-f1 suite", "review-finding-f1 suite (m;", "RE-3 ≡ EV-13"),
    ("ordered_subsequence", "add an ordered_subsequence verifier", "ID-7 ≡ scoring-infra"),
    ("frontiercs floor probe", "frontier-tier candidate — frontiercs", "ID-8 ≡ EV-9"),
    ("re-open the ap-21 gepa_ratio", "ap-21 re-open, on corrected facts", "ID-3 ≡ AP-21"),
    ("z-lab/gemma-4-26b-a4b-it-dflash", "measure z-lab/gemma-4-26b-a4b-it-dflash",
     "ID-29 ≡ gemma DFlash"),
    ("header-gate the davidau qwen3.6-27b mtp ggufs", "davidau qwen3.6-27b mtp ggufs",
     "ID-15 ≡ DavidAU header gate"),
    ("re-baseline odl end-to-end on the full 1651-page set",
     "re-baseline odl end-to-end on the full set", "ODL full-set re-baseline"),
    ("port only if t2 wins", "decision-flipper", "iqk T3 ≡ tq3 gate"),
    ("gate trellis in ik", "measure iq4 kt vs q4 k m and iq2 kt", "iqk T2 ≡ tq3"),
]


def validate(threshold: float = 0.38) -> int:
    found = {(d["a"]["file"], d["a"]["line"], d["b"]["file"], d["b"]["line"])
             for d in scan(threshold)}
    found |= {(b, lb, a, la) for a, la, b, lb in found}

    def _resolve(text: str, exclude: tuple[str, int] | None = None) -> tuple[str, int, str] | None:
        t = _norm(text)
        for p in sorted(ACTIVE.glob("*.md")):
            if exclude and p.name == exclude[0]:
                continue
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            for lineno, line in enumerate(lines, 1):
                if not re.match(r"^\s*- \[", line):
                    continue
                if t in _norm(_full_body(p, lineno)):
                    m = re.match(r"^\s*- \[([ xX])\]", line)
                    return p.name, lineno, m.group(1)
        return None

    hits = misses = 0
    for ta, tb, note in _GROUND_TRUTH:
        ra = _resolve(ta)
        # Resolve the second member in a DIFFERENT file: the C2 pairs are
        # cross-file by construction, and both texts usually also match the
        # first member's own row (each row contains its own summary).
        rb = _resolve(tb, exclude=(ra[0], ra[1]) if ra else None)
        if ra is None or rb is None:
            print(f"  RESOLVED (member gone)  {note}")
            continue
        key = (ra[0], ra[1], rb[0], rb[1])
        if key in found:
            hits += 1
            print(f"  DETECTED  {note}: {ra[0]}:{ra[1]} ≡ {rb[0]}:{rb[1]}")
        else:
            misses += 1
            print(f"  MISSED    {note}: {ra[0]}:{ra[1]} ≡ {rb[0]}:{rb[1]}  "
                  f"[{ra[2]}/{rb[2]}]")
    total = hits + misses
    print(f"\nresolvable pairs: {total}  detected: {hits}  recall: "
          f"{hits/total:.2f}" if total else "no resolvable pairs")
    return 0 if misses == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--threshold", type=float, default=0.38,
                    help="report pairs with score >= this (default 0.38)")
    ap.add_argument("--min-score", type=float, default=None,
                    help="alias of --threshold")
    ap.add_argument("--max", type=int, default=None,
                    help="print at most this many pairs (default: all)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--validate", action="store_true",
                    help="measure recall against the C2 ground-truth pairs")
    args = ap.parse_args(argv)
    threshold = args.min_score if args.min_score is not None else args.threshold

    if args.validate:
        return validate(threshold)

    dups = scan(threshold)
    if args.json:
        print(json.dumps(dups, indent=1))
    else:
        if not dups:
            print(f"no cross-file duplicate-task candidates at score >= {threshold}")
            return 0
        print(f"{len(dups)} cross-file duplicate-task candidate pair(s) at "
              f"score >= {threshold}:")
        for d in dups[:args.max] if args.max else dups:
            print(f"\n  {d['score']:.3f}  {d['a']['file']}:{d['a']['line']} "
                  f"[{d['a']['state'] or ' '}]  ~  {d['b']['file']}:{d['b']['line']} "
                  f"[{d['b']['state'] or ' '}]")
            print(f"      A: {d['a']['text']}")
            print(f"      B: {d['b']['text']}")
        print("\nREAD, don't auto-action: a screen that silently refuses is a new "
              "fail-closed. Index-pointer rows (an index row vs the handoff it points at) "
              "are the thin-row contract working as designed and are not compared.")
    return 1 if dups else 0


if __name__ == "__main__":
    sys.exit(main())
