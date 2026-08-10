"""SC13: the correction adjudication queue — draining the 571 claims nobody has ruled on.

**What the ledger currently holds, and why it is stuck.** A Stage-2 dive writes free prose into an
entry's `dive_corrections`, and the intake adapter records it verbatim with `parsed: false` and the
note *"semantic effect on individual claims is NOT parsed and must be established by review"*. That
is the honest thing to record -- a summariser deciding which claims a correction kills is precisely
the failure mode intake-896 exists to memorialise. But honesty costs: `fold` marks every claim of a
corrected entry `review_required`, and the freshness gate BLOCKS a review-required belief for
authoritative use. 571 claims sit in that state, and until 2026-08-10 nothing in the repository could
move one out of it: the 103 `correction_reviewed` frames in the ledger came from a one-off backfill
script, and no code path emitted them.

So this is the missing half. A correction is adjudicated by recording, per claim, what it actually
did -- one of `CORRECTION_EFFECTS`, imported from the adapter that consumes them rather than
restated here.

**Ranked by citations, not by id.** A queue of 571 items drained in id order is a queue nobody
finishes. Each row is scored by how many project documents actually cite the entry, because a
correction against an entry that eight handoffs rest on is worth adjudicating today and one against
an entry nothing cites can wait forever. That count comes from the same scanner `citation_gate`
uses.

**The worksheet starts at `pending` and emits nothing for it**, exactly as the alias worksheet does.
A generator that pre-filled the obvious verdicts would be the fold making the judgment with extra
steps, and the judgments here are the ones a machine provably gets wrong.

**Two outputs, deliberately separate.** `correction_reviewed` frames go to the ledger and unblock the
gate. The `claim_corrections` YAML block goes into `research/intake_index.yaml` and is what makes the
next re-ingest grade an overturned claim as opposition. Recording only the first would unblock a
claim while leaving it graded as though the correction never happened -- the worse of the two
half-states, since it reads as adjudicated.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "adapters"))

from frames import make_frame  # noqa: E402
from wiki_dependents import cited_ids, live_entry_ids, merge_redirects, resolve  # noqa: E402

from adapters.research_intake import CORRECTION_EFFECTS  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FT_CORRECTION = "epyc.vidya/frame/correction_recorded/v1"
FT_REVIEWED = "epyc.vidya/frame/correction_reviewed/v1"
ACTOR = "vidya.correction_queue/v1"
AUTHORITY = "research-verification"

#: Same document set `citation_gate` treats as rationale. Kept as one constant so "what counts as a
#: citation that matters" cannot drift between the gate that reports it and the queue that ranks by it.
from citation_gate import DEFAULT_PATHS  # noqa: E402,E501


@dataclass
class PendingCorrection:
    """One correction, however many times the ledger records it.

    `correction_frame_ids` is a LIST because re-ingesting the intake index mints a fresh frame for
    an unchanged correction: `created_at` is inside the envelope hash, so identical text ingested at
    three different `--as-of` values is three frame_ids. Measured 2026-08-10: 485 correction frames
    carrying 155 distinct corrections, up to 4 copies each.

    That matters here and nowhere else, because `fold` blocks a claim while ANY unreviewed copy
    names it. A reviewer must see the correction once and the ledger must receive a
    `correction_reviewed` frame per copy -- review one copy of four and the claim stays blocked with
    no indication why. The 2026-08-09 backfill got this right by accident of being a bulk script;
    stating it here is what stops the next reviewer getting it wrong.
    """

    correction_frame_ids: list[str]
    entry_id: str
    correction_text: str
    claim_ids: list[str] = field(default_factory=list)
    claim_texts: dict[str, str] = field(default_factory=dict)
    cited_by: list[str] = field(default_factory=list)

    @property
    def citations(self) -> int:
        return len(self.cited_by)

    @property
    def copies(self) -> int:
        return len(self.correction_frame_ids)

    def as_dict(self) -> dict:
        return {
            "correction_frame_ids": self.correction_frame_ids,
            "copies": self.copies,
            "entry_id": self.entry_id,
            "correction_text": self.correction_text,
            "claim_ids": self.claim_ids,
            "cited_by": self.cited_by,
            "citations": self.citations,
        }


def citation_counts(paths=DEFAULT_PATHS) -> dict[str, list[str]]:
    """entry number -> the documents citing it, resolved forward through the merge map."""
    redirects, live = merge_redirects(), live_entry_ids()
    out: dict[str, list[str]] = {}
    for base in paths:
        root = REPO / base
        if not root.exists():
            continue
        for f in sorted(root.rglob("*.md")):
            text = f.read_text(encoding="utf-8", errors="ignore")
            rel = str(f.relative_to(REPO))
            for num in cited_ids(text):
                resolved, _ = resolve(num, redirects, live)
                if resolved:
                    out.setdefault(resolved, []).append(rel)
    return {k: sorted(set(v)) for k, v in out.items()}


def pending(frames, fold_result, *, citations: dict[str, list[str]] | None = None
            ) -> list[PendingCorrection]:
    """Corrections with no `correction_reviewed` frame, ranked by citation weight then size."""
    reviewed = set(getattr(fold_result, "reviewed_corrections", ()) or ())
    citations = citation_counts() if citations is None else citations

    texts: dict[str, str] = {}
    for f in frames:
        if f.get("frame_type", "").endswith("claim_proposed/v1"):
            a = f.get("assertion") or {}
            if a.get("claim_id"):
                texts[a["claim_id"]] = a.get("display_text", "")

    # Which claims a correction blocks is read back OUT of the fold, never recomputed from the
    # frame's `claim_ids`. The fold canonicalises through the alias map before recording a
    # correction, so a correction naming `clm_intake_378_03` blocks `clm_intake_374_03` when those
    # two are aliased. Trusting the raw assertion missed exactly one claim on the live ledger and
    # would have put it in a worksheet under an id whose `claim_index` points at a different entry.
    blocks: dict[str, list[str]] = {}
    for claim_id, belief in fold_result.beliefs.items():
        for fid in belief.corrections:
            blocks.setdefault(fid, []).append(claim_id)

    # Group by what the correction SAYS, not by the frame that says it -- see PendingCorrection.
    grouped: dict[tuple[str, str], dict] = {}
    for f in frames:
        if f.get("frame_type") != FT_CORRECTION:
            continue
        fid = f.get("frame_id", "")
        if fid in reviewed:
            continue
        a = f.get("assertion") or {}
        entry_id = a.get("entry_id") or ""
        # A claim can carry several corrections; one already adjudicated elsewhere must not
        # reappear here as though it were untouched. `blocks` holds only what still binds.
        claim_ids = blocks.get(fid, [])
        if not claim_ids:
            continue
        slot = grouped.setdefault(
            (entry_id, a.get("correction_text", "")),
            {"fids": [], "claims": set()},
        )
        slot["fids"].append(fid)
        slot["claims"].update(claim_ids)

    rows: list[PendingCorrection] = []
    for (entry_id, text), slot in grouped.items():
        num = entry_id.split("-")[-1] if entry_id else ""
        claim_ids = sorted(slot["claims"])
        rows.append(PendingCorrection(
            correction_frame_ids=sorted(slot["fids"]), entry_id=entry_id, correction_text=text,
            claim_ids=claim_ids,
            claim_texts={c: texts.get(c, "") for c in claim_ids},
            cited_by=citations.get(str(int(num)) if num.isdigit() else num, []),
        ))
    rows.sort(key=lambda r: (-r.citations, -len(r.claim_ids), r.entry_id))
    return rows


def _claim_index(claim_id: str) -> int:
    return int(claim_id.rsplit("_", 1)[-1])


def worksheet(rows, *, generated_at: str, limit: int | None = None) -> dict:
    """A review worksheet with every decision `pending` — the only legal initial value."""
    out_rows = []
    for r in (rows[:limit] if limit else rows):
        out_rows.append({
            "correction_frame_ids": r.correction_frame_ids,
            "copies": r.copies,
            "entry_id": r.entry_id,
            "citations": r.citations,
            "cited_by": r.cited_by[:8],
            "correction_text": r.correction_text,
            "claims": [
                {"claim_id": c, "claim_index": _claim_index(c),
                 "text": r.claim_texts.get(c, ""), "effect": "pending", "note": ""}
                for c in r.claim_ids
            ],
        })
    return {
        "generated_at": generated_at,
        "effects_allowed": list(CORRECTION_EFFECTS),
        "instructions": (
            "For each claim set `effect` to one of effects_allowed and write a `note` saying what "
            "the correction did to THAT claim. Leave `effect: pending` for anything you did not "
            "adjudicate -- pending rows emit nothing. A row emits only when every one of its claims "
            "has a non-pending effect, because a partially reviewed correction that unblocked the "
            "gate would be worse than an unreviewed one."
        ),
        "rows": out_rows,
    }


def _validate(ws: dict) -> list[dict]:
    """Rows whose every claim carries a legal, non-pending effect."""
    ready = []
    for row in ws.get("rows") or []:
        claims = row.get("claims") or []
        if not claims:
            continue
        effects = [c.get("effect") for c in claims]
        if any(e == "pending" or e is None for e in effects):
            continue
        bad = [e for e in effects if e not in CORRECTION_EFFECTS]
        if bad:
            raise ValueError(
                f"{row.get('entry_id')}: effect(s) {sorted(set(bad))} not in {list(CORRECTION_EFFECTS)}"
            )
        ready.append(row)
    return ready


def frames_from_worksheet(ws: dict, *, at: str, actor: str = ACTOR) -> list[dict]:
    """One `correction_reviewed` frame per fully adjudicated row.

    The frame targets the correction's `frame_id`, which is what `fold` matches on
    (`assertion.reviewed`). Targeting the entry instead would silently review every correction the
    entry ever received, including ones written after this review.
    """
    out = []
    for row in _validate(ws):
        verdicts = {c["claim_id"]: c["effect"] for c in row["claims"]}
        # One frame per COPY. `fold` matches on frame_id, so reviewing three of four copies leaves
        # every claim of this correction blocked -- and blocked with no visible reason, which is
        # worse than untouched.
        for fid in row["correction_frame_ids"]:
            out.append(make_frame(
                frame_type=FT_REVIEWED,
                assertion={"entry_id": row["entry_id"], "reviewed": fid},
                provenance={
                    "method": "vidya.correction_queue/adjudicate",
                    "about": fid,
                    "per_claim_effect": dict(sorted(verdicts.items())),
                    "rationale": (
                        "Adjudicated from the correction-queue worksheet; the effect on each claim "
                        "is recorded here and mirrored into the entry's `claim_corrections` so the "
                        "next re-ingest grades opposition per claim rather than per entry."
                    ),
                },
                actor=actor, authority_scope=AUTHORITY, created_at=at,
            ))
    return out


def index_blocks(ws: dict) -> dict[str, str]:
    """entry id -> the `claim_corrections:` YAML text to insert into `research/intake_index.yaml`.

    Rendered with `safe_dump` over the SMALL block only, never over the index. Round-tripping the
    whole 1,068-entry file reorders keys and reflows every string, producing a diff nobody can
    review -- the reason this program parses that file as text everywhere else.
    """
    import yaml  # noqa: PLC0415

    out = {}
    for row in _validate(ws):
        recs = [
            {"claim_index": c["claim_index"], "effect": c["effect"],
             "note": c.get("note") or row.get("correction_text", "")[:400]}
            for c in sorted(row["claims"], key=lambda c: c["claim_index"])
        ]
        dumped = yaml.safe_dump({"claim_corrections": recs}, sort_keys=False,
                                allow_unicode=True, width=100)
        out[row["entry_id"]] = "\n".join("  " + ln if ln.strip() else ln
                                         for ln in dumped.rstrip("\n").splitlines())
    return out


def main(argv=None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap.add_argument("--ledger", default=str(REPO / ".vidya" / "ledger.jsonl"))

    p_list = sub.add_parser("list", help="ranked pending corrections")
    p_list.add_argument("--as-of", required=True)
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--json", action="store_true")

    p_ws = sub.add_parser("worksheet", help="write a review worksheet (all decisions pending)")
    p_ws.add_argument("--as-of", required=True)
    p_ws.add_argument("--out", required=True)
    p_ws.add_argument("--limit", type=int, default=25)

    p_em = sub.add_parser("emit", help="turn a completed worksheet into frames")
    p_em.add_argument("--worksheet", required=True)
    p_em.add_argument("--at", required=True)
    p_em.add_argument("--actor", default=ACTOR)
    p_em.add_argument("--apply", action="store_true", help="append the frames to the ledger")
    p_em.add_argument("--show-index-blocks", action="store_true")

    args = ap.parse_args(argv)

    import yaml  # noqa: PLC0415

    from ledger import Ledger  # noqa: PLC0415

    if args.cmd == "emit":
        ws = yaml.safe_load(Path(args.worksheet).read_text())
        frames = frames_from_worksheet(ws, at=args.at, actor=args.actor)
        if args.show_index_blocks:
            for entry, block in sorted(index_blocks(ws).items()):
                print(f"# --- paste into {entry} in research/intake_index.yaml ---")
                print(block)
                print()
        if args.apply:
            led = Ledger(args.ledger)
            for f in frames:
                rec = led.append(f)
                print(f"appended seq={rec.seq} reviewed={f['assertion']['reviewed'][:23]}…")
        print(f"{len(frames)} correction_reviewed frame(s) "
              f"{'appended' if args.apply else 'built (dry run; pass --apply)'}")
        return 0

    from fold import fold  # noqa: PLC0415

    frames = [r.frame for r in Ledger(args.ledger).read_all()]
    result = fold(frames, as_of=args.as_of)
    rows = pending(frames, result)

    if args.cmd == "worksheet":
        ws = worksheet(rows, generated_at=args.as_of, limit=args.limit)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump(ws, sort_keys=False, allow_unicode=True, width=100))
        print(f"worksheet: {out}  rows={len(ws['rows'])} of {len(rows)} pending")
        return 0

    blocked = sum(len(r.claim_ids) for r in rows)
    cited = sum(1 for r in rows if r.citations)
    if args.json:
        print(json.dumps({"pending": len(rows), "claims_blocked": blocked,
                          "rows": [r.as_dict() for r in rows]}, indent=2, sort_keys=True))
        return 0
    print(f"{len(rows)} unadjudicated correction(s) blocking {blocked} claim(s); "
          f"{cited} are cited by project documents")
    print()
    for r in rows[:args.limit]:
        print(f"  {r.entry_id}  citations={r.citations}  claims={len(r.claim_ids)}"
              + (f"  copies={r.copies}" if r.copies > 1 else ""))
        if r.cited_by:
            print(f"     cited by: {', '.join(r.cited_by[:4])}"
                  + (f" (+{len(r.cited_by) - 4})" if len(r.cited_by) > 4 else ""))
        print(f"     {r.correction_text[:220].strip()}")
    if len(rows) > args.limit:
        print(f"\n  ... and {len(rows) - args.limit} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
