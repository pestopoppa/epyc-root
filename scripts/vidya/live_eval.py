"""PR2 — run the P5c evaluation against a corpus drawn from the LIVE ledger.

Spec: docs/design/vidya-pilot-spec.md §17.2 (HoH scoring); the gap this closes is named in
research/deep-dives/vidya-p5c-evaluation-and-decision.md §3 — 28/28 on 19 hand-built anchored gold
claims, versus `0 verified unaffected / 4,190 unmapped` on real data, with nothing measuring the
distance between them.

The honest constraint, discovered while building this: **per-claim gold labels cannot be derived
from the live index.** `dive_corrections` is free prose ("2026-07-25 ID-37 re-read. CORRECTLY
FILED. …") with no claim index, so which of an entry's claims a correction actually falsified is
not recorded anywhere a program can read. Inventing labels by matching correction prose to claim
prose would be scoring the engine against a guess and calling the guess ground truth.

So this module scores the labels that ARE derivable from recorded state, and reports the rest as
explicitly **uncoverable** rather than quietly omitting them:

* `never_believed` — claims of `stage1-unverified` entries must not clear a decision-gating floor.
  Real, and it is the floor discipline the whole gate rests on.
* `retracted` — retracting an entry's evidence token must move that entry's own claims.
* `unaffected` — claims of entries with no evidential relationship to the mutated one.
* `propagated` — claims that `depends_on` a claim of the mutated entry. These MUST move: a human
  applied the counterfactual test and wrote down that they would. This is the only scorable
  propagation in the system, and it exists only where somebody authored the edge.
* **uncoverable** — claims of entries that merely CITE the mutated entry with no `depends_on`. The
  engine reports these unaffected because citation is not an evidential edge (measured: 18% of
  dived-source citations are evidential, so inferring it would be wrong 4 times in 5). Scoring them
  either way would manufacture an answer. Counted, never scored.

That last bucket is the actual result this module produces. A suite that scored it would report a
number; a suite that dropped it would look complete.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fold import fold  # noqa: E402
from impact import impact_of_retracting  # noqa: E402
from lattice import parse_grade  # noqa: E402

__all__ = ["draw_families", "score_live_family", "run_live"]

FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"
FT_SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"
FT_DEPENDS = "epyc.vidya/frame/claim_depends_on/v1"
DEFAULT_FLOOR = "Verified/Anchored"

# Evidence tokens are minted per CLAIM on live data (`evd_clm_intake_096_00`), not per source, so
# retracting a token reaches exactly one claim. That is the third instance of the same defect:
# claim identity, source identity and now evidence identity are all per-record. The gold corpus's
# sharpest family (E2 — one stale extractor underpinning several conclusions) is therefore not
# expressible in live data through a token retraction at all.
#
# The mutation used here is a SOURCE retraction: every support frame carrying the entry's
# `source_id`. That is the "this source is discredited" event the gold corpus models, and unlike a
# token retraction it is expressible against the live graph.


def _entry_of(claim_id: str) -> str:
    parts = claim_id.rsplit("_", 1)
    return parts[0] if len(parts) == 2 and parts[1].isdigit() else claim_id


def _index_claims(frames: list[dict]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """(entry -> claim ids, source id -> support frame ids). Deterministic order for a stable draw."""
    by_entry: dict[str, list[str]] = {}
    by_source: dict[str, list[str]] = {}
    for frame in frames:
        ftype = frame.get("frame_type")
        assertion = frame.get("assertion") or {}
        cid = assertion.get("claim_id")
        if not isinstance(cid, str):
            continue
        if ftype == FT_CLAIM:
            by_entry.setdefault(_entry_of(cid), []).append(cid)
        elif ftype == FT_SUPPORT and assertion.get("source_id"):
            by_source.setdefault(assertion["source_id"], []).append(frame.get("frame_id", ""))
    for claims in by_entry.values():
        claims.sort()
    return by_entry, by_source


def _dependents(frames: list[dict]) -> dict[str, list[str]]:
    """Entry id -> claim ids that declare a `depends_on` edge into it."""
    out: dict[str, list[str]] = {}
    for frame in frames:
        if frame.get("frame_type") != FT_DEPENDS:
            continue
        a = frame.get("assertion") or {}
        target, cid = a.get("depends_on_entry"), a.get("claim_id")
        if isinstance(target, str) and isinstance(cid, str):
            out.setdefault(target, []).append(cid)
    for v in out.values():
        v.sort()
    return out


def draw_families(
    frames: list[dict],
    index_entries: list[dict],
    *,
    count: int = 12,
    require_verified: bool = False,
) -> list[dict]:
    """Draw mutation families from the live ledger, preferring entries that others cite.

    Cited entries are drawn first because they are the only ones that can populate the uncoverable
    bucket, which is what this evaluation exists to size. The draw is deterministic — sorted by
    (citation count desc, entry id) — so a rerun scores the same corpus.
    """
    by_entry, by_source = _index_claims(frames)
    dependents = _dependents(list(frames))
    entries = {e["id"]: e for e in index_entries if isinstance(e.get("id"), str)}

    cited_by: dict[str, set[str]] = {}
    for entry in index_entries:
        eid = entry.get("id")
        refs = ((entry.get("cross_references") or {}).get("intake_entries")) or []
        for ref in refs:
            if isinstance(ref, str):
                cited_by.setdefault(ref, set()).add(eid)

    def claim_key(entry_id: str) -> str:
        return "clm_" + entry_id.replace("-", "_")

    # Drawing purely by citation count exercises only the floor: of the 60 most-cited live
    # entries, 50 have no verification at all and 9 are dived, so every family comes back
    # `never_believed` and the retraction path is never touched. `require_verified` draws the
    # other stratum so both halves of the engine get measured.
    candidates = []
    for entry_id in entries:
        if require_verified and entries[entry_id].get("verification") not in (
            "dive-verified", "dive-overturned"
        ):
            continue
        key = claim_key(entry_id)
        claims = by_entry.get(key) or []
        source_id = "src_" + entry_id.replace("-", "_")
        if not claims or not by_source.get(source_id):
            continue
        candidates.append((len(cited_by.get(entry_id, ())), entry_id))
    candidates.sort(key=lambda t: (-t[0], t[1]))

    families = []
    for n_citing, entry_id in candidates[:count]:
        key = claim_key(entry_id)
        # Recomputed per drawn entry. Reusing the candidate loop's variable here silently
        # retracted the LAST candidate's source for every family, and still reported a plausible
        # score -- the test that caught it asserts which claims moved, not that a number came out.
        source_id = "src_" + entry_id.replace("-", "_")
        citing_claims = sorted(
            c
            for other in cited_by.get(entry_id, ())
            for c in by_entry.get(claim_key(other), [])
        )
        unverified = entries[entry_id].get("verification") in (None, "stage1-unverified")
        families.append(
            {
                "family_id": entry_id,
                "mutated_claims": by_entry[key],
                "source_id": source_id,
                "target_frames": sorted(by_source[source_id]),
                "citing_claims": [c for c in citing_claims
                                  if c not in set(dependents.get(entry_id, []))],
                "dependent_claims": dependents.get(entry_id, []),
                "citing_entries": n_citing,
                "expect_never_believed": unverified,
            }
        )
    return families


def score_live_family(family: dict, frames: list[dict], *, as_of: str, floor: str) -> dict:
    """Score one drawn family. Uncoverable claims are counted and excluded from the score."""
    report = impact_of_retracting(frames, family["target_frames"], as_of=as_of)
    flagged = {i.claim_id for i in report.affected}
    before = fold(frames, as_of=as_of)
    grade_floor = parse_grade(floor)

    rows: list[dict] = []
    points: list[int] = []

    for cid in family["mutated_claims"]:
        belief = before.beliefs.get(cid)
        if family["expect_never_believed"]:
            # An unverified entry's claim must not clear a decision-gating floor, retraction or no.
            supported = bool(belief and belief.verdict(grade_floor) == "Supported")
            correct, harmful, expected = not supported, supported, "never_believed"
        else:
            correct = cid in flagged
            harmful = not correct
            expected = "retracted"
        points.append(1 if correct else (-1 if harmful else 0))
        rows.append({"claim_id": cid, "expected": expected, "correct": correct})

    # Declared dependents MUST move. This is the only scorable propagation the system has, and it
    # exists exactly where a human wrote the edge — which is why authoring them is the unblock, not
    # inferring them.
    for cid in family.get("dependent_claims", []):
        correct = cid in flagged
        points.append(1 if correct else -1)
        rows.append({"claim_id": cid, "expected": "propagated", "correct": correct})

    # Discrimination control: claims of entries with no evidential relationship at all. Drawn from
    # the fold rather than the index so a claim that exists only in the ledger is still eligible.
    excluded = (set(family["mutated_claims"]) | set(family["citing_claims"])
                | set(family.get("dependent_claims", [])))
    controls = [c for c in sorted(before.beliefs) if c not in excluded][:20]
    for cid in controls:
        correct = cid not in flagged
        points.append(1 if correct else 0)  # over-flagging is work, not danger (spec §17.2)
        rows.append({"claim_id": cid, "expected": "unaffected", "correct": correct})

    scorable = [r for r in rows
                if r["expected"] in ("retracted", "never_believed", "propagated")]
    controls_rows = [r for r in rows if r["expected"] == "unaffected"]
    return {
        "family": family["family_id"],
        "source_id": family["source_id"],
        "score": sum(points),
        "max_score": len(points),
        "invalidation_recall": (
            sum(1 for r in scorable if r["correct"]) / len(scorable) if scorable else None
        ),
        "discrimination": (
            sum(1 for r in controls_rows if r["correct"]) / len(controls_rows)
            if controls_rows
            else None
        ),
        "uncoverable_claims": len(family["citing_claims"]),
        "propagation_claims": len(family.get("dependent_claims", [])),
        "citing_entries": family["citing_entries"],
        "verified_unaffected": len(report.verified_unaffected),
        "unaffected_but_unmapped": len(report.unaffected_but_unmapped),
        "rows": rows,
    }


def run_live(
    frames: list[dict],
    index_entries: list[dict],
    *,
    as_of: str,
    count: int = 12,
    floor: str = DEFAULT_FLOOR,
    require_verified: bool = False,
) -> dict[str, Any]:
    families = draw_families(
        frames, index_entries, count=count, require_verified=require_verified
    )
    results = [score_live_family(f, frames, as_of=as_of, floor=floor) for f in families]
    recalls = [r["invalidation_recall"] for r in results if r["invalidation_recall"] is not None]
    discs = [r["discrimination"] for r in results if r["discrimination"] is not None]
    harmful = sum(1 for r in results for row in r["rows"] if not row["correct"]
                  and row["expected"] in ("retracted", "never_believed", "propagated"))
    return {
        "corpus": "live-ledger",
        "as_of": as_of,
        "floor": floor,
        "families": results,
        "score": sum(r["score"] for r in results),
        "max_score": sum(r["max_score"] for r in results),
        "invalidation_recall": sum(recalls) / len(recalls) if recalls else None,
        "discrimination": sum(discs) / len(discs) if discs else None,
        "harmful_outcomes": harmful,
        "uncoverable_claims": sum(r["uncoverable_claims"] for r in results),
        "propagation_claims": sum(r["propagation_claims"] for r in results),
        "coverage_note": (
            "Claims of entries that CITE a mutated entry are counted as uncoverable, never "
            "scored: the ledger holds no cross-entry evidential edge, so the engine reports them "
            "unaffected by construction and scoring that would manufacture an answer to the open "
            "question. Per-claim correction labels are not derivable at all -- dive_corrections is "
            "free prose with no claim index."
        ),
    }
