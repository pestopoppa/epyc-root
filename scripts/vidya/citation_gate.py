"""SC12: gate an intake citation at the point it is used as rationale.

**The failure this exists to catch, stated concretely.** `intake-896` claim 03 asserted that Claude
Code's `/doctor` performs four specific steps. A Stage-2 dive found the description **fabricated by a
Stage-1 summariser** -- the source post contains two generic sentences and none of those behaviours.
That claim now sits at `pro=Q0/T0, con=Verified/Located` in the ledger, which is the substrate
working exactly as designed. It is worth nothing at all if the next person to write "per intake-896,
/doctor rebuilds the index" never asks.

So this is the read side of that whole investment: a scanner that finds `intake-NNN` citations in
project documents, resolves them, and applies a use policy to what they actually rest on.

**Entry-level citations inherit every defect in the entry, and that is not a bug.** An entry holds
several claims; citing the entry cites all of them, because prose that says "per intake-896" gives a
reader no way to know which claim carried the weight. The escape hatch is precision, not leniency:
`intake-896#01` gates exactly claim 01 and is unaffected by claim 03's refutation. Making imprecise
citations noisier than precise ones is the point -- the gate teaches the citation form that lets it
give a clean answer.

**Why `review` warns instead of blocking (spec §10's auto-downgrade rule).** 571 claims currently
carry a correction nobody has adjudicated, so a policy that blocked on `review_required` would fail
most citations in the repository on its first run, and a gate that fires on everything gets switched
off within a day. The spec anticipates this: a class of surfaced obligations that exceeds a no-action
threshold must stop interrupting and revert to a passive queue. That queue is `correction_queue.py`.
Blocking is therefore reserved for the three states a citer can actually act on immediately --
the cited entry does not exist, or what it says has been refuted, or it is contested.

Nothing here writes to the ledger. A document scan is not a query: it reads hundreds of claims that
nobody is relying on yet, and logging those as `query_served` would drown the R5 reuse series in
telemetry from a linter. `--log` opts in for the case where a scan really is a considered use.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fold import FoldResult  # noqa: E402
from gate import Outcome, UsePolicy, evaluate  # noqa: E402
from lattice import parse_grade  # noqa: E402
from wiki_dependents import cited_refs, live_entry_ids, merge_redirects, resolve  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

# Where rationale actually lives. Deliberately not the whole repo: `research/` holds the intake index
# itself and `progress/` is a historical record, and gating either would report the corpus citing
# itself rather than anyone relying on it.
DEFAULT_PATHS = ("handoffs/active", "handoffs/blocked", "wiki", "docs")

_CLAIM_ID = re.compile(r"^clm_intake_(\d+)_(\d+)$")

# Ordered worst-first. `dangling` outranks `overturned` because a citation that resolves to nothing
# cannot even be argued about.
SEVERITY = ("dangling", "overturned", "conflicted", "review", "weak", "unknown", "ok")

#: Statuses that make the gate exit non-zero. See the module docstring for why `review` is not here.
BLOCKING = frozenset({"dangling", "overturned", "conflicted"})


@dataclass
class CitationVerdict:
    path: str
    entry: str                      # as written, e.g. "896" or "896#03"
    resolved: str | None
    how: str                        # direct / merged / dangling
    status: str
    claims: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "path": self.path, "entry": self.entry, "resolved": self.resolved,
            "how": self.how, "status": self.status, "claims": self.claims, "notes": self.notes,
        }


def claims_by_entry(fold_result: FoldResult) -> dict[str, list[str]]:
    """entry number -> its claim ids, read from the fold rather than reconstructed.

    The claim-id convention zero-pads to three digits (`clm_intake_096_00`) but entry ids in the
    index do not, so building ids by formatting would silently miss every four-digit entry. Parsing
    what the fold actually holds has no such failure mode.
    """
    out: dict[str, list[str]] = {}
    for claim_id in fold_result.beliefs:
        m = _CLAIM_ID.match(claim_id)
        if m:
            out.setdefault(str(int(m.group(1))), []).append(claim_id)
    for ids in out.values():
        ids.sort()
    return out


def _classify(belief, result) -> str:
    """One claim's contribution to its entry's status."""
    if belief.pro.q_name == "Q0" and belief.con.q_name != "Q0":
        return "overturned"
    if belief.con.q_name != "Q0" and belief.pro.q_name != "Q0":
        return "conflicted"
    if belief.review_required:
        return "review"
    return "ok" if result.outcome == Outcome.ALLOW else "weak"


def check_text(
    text: str,
    fold_result: FoldResult,
    policy: UsePolicy,
    *,
    path: str = "-",
    redirects: dict[str, str] | None = None,
    live: set[str] | None = None,
    by_entry: dict[str, list[str]] | None = None,
) -> list[CitationVerdict]:
    """Apply `policy` to every intake citation in `text`."""
    redirects = merge_redirects() if redirects is None else redirects
    live = live_entry_ids() if live is None else live
    by_entry = claims_by_entry(fold_result) if by_entry is None else by_entry

    verdicts: list[CitationVerdict] = []
    for num, claim_index in sorted(cited_refs(text), key=lambda r: (int(r[0]), r[1] or -1)):
        label = num if claim_index is None else f"{num}#{claim_index:02d}"
        resolved, how = resolve(num, redirects, live)
        if resolved is None:
            verdicts.append(CitationVerdict(
                path=path, entry=label, resolved=None, how=how, status="dangling",
                notes=["cited entry resolves to no live index entry, and to no merge survivor"]))
            continue

        candidates = by_entry.get(resolved, [])
        if claim_index is not None:
            want = f"_{claim_index:02d}"
            candidates = [c for c in candidates if c.endswith(want)]

        if not candidates:
            note = ("entry exists but no claim of it has been ingested"
                    if claim_index is None else
                    f"entry exists but claim {claim_index:02d} is not in the ledger")
            verdicts.append(CitationVerdict(
                path=path, entry=label, resolved=resolved, how=how, status="unknown",
                notes=[note + " -- a coverage gap in the substrate, not a defect in the citation"]))
            continue

        rows, statuses = [], []
        for cid in candidates:
            belief = fold_result.beliefs[cid]
            res = evaluate(cid, fold_result, policy)
            status = _classify(belief, res)
            statuses.append(status)
            rows.append({
                "claim_id": cid, "status": status, "outcome": res.outcome,
                "pro": f"{belief.pro.q_name}/{belief.pro.t_name}",
                "con": f"{belief.con.q_name}/{belief.con.t_name}",
                "reasons": res.reasons, "next_actions": res.required_next_actions,
            })

        worst = min(statuses, key=SEVERITY.index)
        notes = []
        if how == "merged":
            notes.append(f"citation resolved forward through the merge map: {num} -> {resolved}")
        if claim_index is None and worst in BLOCKING and len(candidates) > 1:
            bad = [r["claim_id"] for r in rows if r["status"] == worst]
            notes.append(
                f"entry-level citation inherits {worst} from {', '.join(bad)}; "
                f"cite the specific claim (e.g. intake-{resolved}#NN) if you meant a different one")
        verdicts.append(CitationVerdict(path=path, entry=label, resolved=resolved, how=how,
                                        status=worst, claims=rows, notes=notes))
    return verdicts


def iter_files(paths):
    for p in paths:
        path = Path(p)
        if not path.is_absolute():
            path = REPO / path
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.md"))


def check_paths(paths, fold_result: FoldResult, policy: UsePolicy) -> list[CitationVerdict]:
    paths = list(paths) if paths else list(DEFAULT_PATHS)
    redirects, live = merge_redirects(), live_entry_ids()
    by_entry = claims_by_entry(fold_result)
    out: list[CitationVerdict] = []
    for f in iter_files(paths):
        text = f.read_text(encoding="utf-8", errors="ignore")
        rel = str(f.relative_to(REPO)) if str(f).startswith(str(REPO)) else str(f)
        out.extend(check_text(text, fold_result, policy, path=rel, redirects=redirects,
                              live=live, by_entry=by_entry))
    return out


def summarize(verdicts) -> dict:
    counts = {s: 0 for s in SEVERITY}
    for v in verdicts:
        counts[v.status] += 1
    return {
        "citations": len(verdicts),
        "documents": len({v.path for v in verdicts}),
        "by_status": counts,
        "blocking": sum(counts[s] for s in BLOCKING),
    }


def main(argv=None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*", default=list(DEFAULT_PATHS))
    ap.add_argument("--as-of", required=True)
    # Default chosen by measurement, not taste. Over the 1,755 live citations: Verified/Located
    # flags 1,520 as `weak` (87%) and buries the 10 actionable ones; Hinted/Located flags 5, each
    # a citation whose entry has no working locator. The strict floor is the right check when a
    # citation is load-bearing -- `--floor Verified/Located` -- and the wrong one to fire by default,
    # for the same reason §10 caps obligation surfacing.
    ap.add_argument("--floor", default="Hinted/Located")
    ap.add_argument("--use", default="handoff-rationale")
    ap.add_argument("--standard", default="DV")
    ap.add_argument("--ledger", default=str(REPO / ".vidya" / "ledger.jsonl"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="list every citation, not just the flagged")
    args = ap.parse_args(argv)

    from ledger import Ledger  # noqa: PLC0415

    from fold import fold  # noqa: PLC0415

    result = fold([r.frame for r in Ledger(args.ledger).read_all()], as_of=args.as_of)
    policy = UsePolicy(use=args.use, floor=parse_grade(args.floor), standard=args.standard)
    verdicts = check_paths(args.paths or list(DEFAULT_PATHS), result, policy)
    summary = summarize(verdicts)

    if args.json:
        print(json.dumps({"summary": summary, "verdicts": [v.as_dict() for v in verdicts]},
                         indent=2, sort_keys=True))
        return 3 if summary["blocking"] else 0

    print(f"{summary['citations']} intake citation(s) across {summary['documents']} document(s)"
          f"   policy: use={args.use} floor={args.floor}")
    print("  " + "  ".join(f"{s}={summary['by_status'][s]}" for s in SEVERITY
                           if summary["by_status"][s]))
    print()

    # Blocking citations get the full derivation; everything else gets one line. A report whose
    # actionable rows are outnumbered 150:1 by advisory ones is a report nobody reads twice.
    for v in verdicts:
        if v.status not in BLOCKING:
            continue
        print(f"  [{v.status.upper()}] intake-{v.entry}  {v.path}")
        for note in v.notes:
            print(f"      note: {note}")
        for row in v.claims:
            if row["status"] == "ok" and not args.all:
                continue
            print(f"      {row['claim_id']}  pro={row['pro']} con={row['con']}  "
                  f"-> {row['outcome']}")
            for r in row["reasons"]:
                print(f"        reason: {r}")
            for a in row["next_actions"][:2]:
                print(f"        next:   {a}")

    advisory = [v for v in verdicts if v.status not in BLOCKING and v.status != "ok"]
    if advisory and not args.all:
        print(f"  --- {len(advisory)} advisory (not blocking); --all for detail ---")
        for v in advisory[:12]:
            head = v.notes[0] if v.notes else f"{len(v.claims)} claim(s)"
            print(f"  [{v.status}] intake-{v.entry}  {v.path}  {head[:90]}")
        if len(advisory) > 12:
            print(f"  ... and {len(advisory) - 12} more")
    elif args.all:
        for v in verdicts:
            if v.status in BLOCKING or (v.status == "ok" and not args.all):
                continue
            print(f"  [{v.status}] intake-{v.entry}  {v.path}")
            for note in v.notes:
                print(f"      note: {note}")

    if summary["by_status"]["review"]:
        print(f"\n{summary['by_status']['review']} citation(s) rest on a claim with an "
              f"unadjudicated correction -- drain with: scripts/vidya/correction_queue.py list")
    if summary["blocking"]:
        print(f"\n{summary['blocking']} blocking citation(s) "
              f"({', '.join(sorted(BLOCKING))}) -- exit 3")
    return 3 if summary["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
