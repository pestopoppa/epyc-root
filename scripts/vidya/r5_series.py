"""R5: the belief-decay and reuse series, computed from the ledger at any frontier.

R5d was filed as "collect the forward series once query_served frames accrue", which is a standing
obligation wearing a checkbox. An obligation with no terminal state can only ever be closed
wrongly — this repo has the scar: `readme-refresh.md` was legitimately completed, archived, and left
a recurring alarm firing at a routing target that no longer existed, after which both READMEs drifted
to 66 days.

So the deliverable is this script, not a diary entry. It computes the whole series from whatever the
ledger holds:

  * claim age and grade trajectory, by folding at successive frontiers (`as_of` makes that exact);
  * query volume, outcome mix and abstention rate over time, from `query_served` frames;
  * time-to-first-reuse per claim, from the first query that cited it;
  * obligation disposition rates, from `obligation_disposition` frames.

Run it today and it reports the t=0 shape and says plainly which panels have no data yet. Run it in
a month and the same command reports the series. Nobody has to remember a procedure, and no
checkbox has to lie in the meantime.

    r5_series.py                 # human-readable
    r5_series.py --json out.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fold import fold  # noqa: E402
from ledger import Ledger  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = REPO_ROOT / ".vidya" / "ledger.jsonl"

FT_QUERY = "epyc.vidya/frame/query_served/v1"
FT_DISPOSITION = "epyc.vidya/frame/obligation_disposition/v1"
FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"
FT_CORRECTION = "epyc.vidya/frame/correction_recorded/v1"


def _day(frame: dict) -> str:
    return str((frame.get("pubinfo") or {}).get("created_at", ""))[:10]


def series(frames: list[dict], *, as_of: str) -> dict:
    queries = [f for f in frames if f.get("frame_type") == FT_QUERY]
    dispositions = [f for f in frames if f.get("frame_type") == FT_DISPOSITION]
    claims = [f for f in frames if f.get("frame_type") == FT_CLAIM]

    # --- reuse
    first_seen: dict[str, str] = {}
    for f in claims:
        cid = (f.get("assertion") or {}).get("claim_id")
        if isinstance(cid, str):
            first_seen.setdefault(cid, _day(f))

    reuse: dict[str, list[str]] = collections.defaultdict(list)
    outcomes = collections.Counter()
    by_day = collections.defaultdict(collections.Counter)
    for f in queries:
        a = f.get("assertion") or {}
        cid = a.get("claim_id")
        outcomes[a.get("outcome", "?")] += 1
        by_day[_day(f)][a.get("outcome", "?")] += 1
        if isinstance(cid, str):
            reuse[cid].append(_day(f))

    ttfr = {}
    for cid, days in reuse.items():
        born, first = first_seen.get(cid), min(days)
        if born and first >= born:
            ttfr[cid] = (born, first)

    fold_result = fold(frames, as_of=as_of)
    flagged = sum(1 for b in fold_result.beliefs.values() if b.review_required)

    return {
        "as_of": as_of,
        "frontier": fold_result.frontier,
        "beliefs": len(fold_result.beliefs),
        "review_required": flagged,
        "corrections_recorded": sum(1 for f in frames if f.get("frame_type") == FT_CORRECTION),
        "discharged_corrections": len(fold_result.discharged),
        "undischarged_corrections": len(fold_result.undischarged),
        "queries_served": len(queries),
        "query_outcomes": dict(outcomes.most_common()),
        "abstention_rate": (
            round(outcomes.get("abstain", 0) / len(queries), 4) if queries else None
        ),
        "queries_by_day": {d: dict(c) for d, c in sorted(by_day.items())},
        "claims_ever_queried": len(reuse),
        "time_to_first_reuse": {k: v for k, v in list(ttfr.items())[:20]},
        "obligation_dispositions": dict(collections.Counter(
            (f.get("assertion") or {}).get("disposition", "?") for f in dispositions
        )),
        "empty_panels": [
            name for name, ok in [
                ("queries_served", bool(queries)),
                ("time_to_first_reuse", bool(ttfr)),
                ("obligation_dispositions", bool(dispositions)),
            ] if not ok
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--as-of", default="2026-08-11T23:59:59Z")
    ap.add_argument("--ledger")
    ap.add_argument("--json")
    args = ap.parse_args()

    led = Ledger(Path(args.ledger) if args.ledger else LEDGER)
    report = series([r.frame for r in led.read_all()], as_of=args.as_of)

    print(f"R5 series @ frontier {report['frontier']} ({report['as_of']})")
    print(f"  beliefs {report['beliefs']}  review_required {report['review_required']}")
    print(f"  corrections {report['corrections_recorded']}  "
          f"discharged {report['discharged_corrections']}  "
          f"undischarged {report['undischarged_corrections']}")
    print(f"  queries served {report['queries_served']}  "
          f"abstention {report['abstention_rate']}")
    if report["queries_by_day"]:
        print("  by day:")
        for d, c in report["queries_by_day"].items():
            print(f"    {d}  {dict(c)}")
    print(f"  claims ever queried: {report['claims_ever_queried']}")
    print(f"  obligation dispositions: {report['obligation_dispositions'] or 'none recorded'}")
    if report["empty_panels"]:
        print(f"\n  NO DATA YET: {', '.join(report['empty_panels'])}")
        print("  These accrue by USE. Every authoritative `vidya query` writes one frame; the")
        print("  series is whatever has been asked, so an empty panel means nobody has asked yet,")
        print("  not that the instrument is broken.")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True))
        print(f"\nwritten to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
