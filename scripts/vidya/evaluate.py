"""P5c: run the gold-corpus mutation suite and score it.

Corpus: docs/design/vidya-pilot-corpus.md. Metrics: pilot spec §17.2.

Scoring uses the HoH scheme adopted in the spec — **+1 correct / 0 abstained / −1 harmful** —
because it is the only one that prices the failure this pilot exists to prevent. A system that
abstains scores zero; a system that confidently reports a stale claim as untouched scores negative.
Accuracy alone would rank those two the same.

Two scores are reported and never merged:

* **invalidation recall** — did the mutation reach what it should have?
* **discrimination** — did it leave alone what it should have?

An engine that flags everything gets perfect recall and zero discrimination, which is why a single
number would hide exactly the behaviour worth measuring.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fold import fold  # noqa: E402
from gold_corpus import CORPUS, MUTATION_ROUNDS, corpus_frames  # noqa: E402
from impact import frames_carrying_evidence, impact_of_retracting  # noqa: E402

__all__ = ["run_round", "run_all", "score_family"]

AS_OF = "2026-08-09T00:00:00Z"


def score_family(family, frames_list: list[dict]) -> dict:
    """Mutate one family and compare the impact report against its gold expectations."""
    target_claim = next(c for c in family.claims if c.claim_id == family.mutation)
    # Retract the evidence TOKEN, not a single edge: one discredited source underpins every claim
    # it supports.
    targets = frames_carrying_evidence(frames_list, target_claim.evidence_id)

    report = impact_of_retracting(frames_list, targets, as_of=AS_OF)
    after = fold(
        frames_list + [{
            "frame_type": "epyc.vidya/frame/retraction/v1",
            "assertion": {"retracts": fid},
            "provenance": {"method": "eval", "about": fid},
            "pubinfo": {"actor": "eval", "authority_scope": "eval", "created_at": AS_OF},
            "frame_id": f"eval-retraction-{fid[:16]}",
        } for fid in targets],
        as_of=AS_OF,
    )
    before = fold(frames_list, as_of=AS_OF)
    changed = {i.claim_id for i in report.affected}

    rows, points = [], []
    for claim in family.claims:
        b, a = before.beliefs.get(claim.claim_id), after.beliefs.get(claim.claim_id)
        moved = bool(b and a and (b.pro != a.pro or b.con != a.con))
        flagged = claim.claim_id in changed

        if claim.expect == "retracted":
            correct = flagged and moved
            harmful = not flagged
        elif claim.expect == "downgraded":
            correct = flagged and moved
            harmful = not flagged
        elif claim.expect == "unaffected":
            correct = not flagged
            # Reporting an unaffected claim as affected is over-invalidation: work, not danger.
            harmful = False
        else:  # never_believed -- the claim should not have cleared a decision-gating floor at all
            from lattice import parse_grade  # noqa: PLC0415

            floor = parse_grade("Verified/Anchored")
            correct = not (b and b.verdict(floor) == "Supported")
            harmful = bool(b and b.verdict(floor) == "Supported")

        score = 1 if correct else (-1 if harmful else 0)
        points.append(score)
        rows.append({
            "claim_id": claim.claim_id,
            "expected": claim.expect,
            "flagged": flagged,
            "moved": moved,
            "correct": correct,
            "score": score,
        })

    should_flag = [r for r in rows if r["expected"] in ("retracted", "downgraded")]
    should_not = [r for r in rows if r["expected"] == "unaffected"]
    return {
        "family": family.family_id,
        "title": family.title,
        "mutation": f"retract evidence of {family.mutation}",
        "rows": rows,
        "score": sum(points),
        "max_score": len(points),
        "invalidation_recall": (
            sum(1 for r in should_flag if r["correct"]) / len(should_flag) if should_flag else None
        ),
        "discrimination": (
            sum(1 for r in should_not if r["correct"]) / len(should_not) if should_not else None
        ),
        "coverage": {i.claim_id: i.coverage for i in report.affected},
        "verified_unaffected": len(report.verified_unaffected),
        "unaffected_but_unmapped": len(report.unaffected_but_unmapped),
    }


def run_round(round_no: int) -> dict:
    label, family_ids = MUTATION_ROUNDS[round_no]
    frames_list = corpus_frames()
    results = [score_family(f, frames_list) for f in CORPUS if f.family_id in family_ids]
    total = sum(r["score"] for r in results)
    maximum = sum(r["max_score"] for r in results)
    recalls = [r["invalidation_recall"] for r in results if r["invalidation_recall"] is not None]
    discs = [r["discrimination"] for r in results if r["discrimination"] is not None]
    return {
        "round": round_no,
        "label": label,
        "families": results,
        "score": total,
        "max_score": maximum,
        "invalidation_recall": sum(recalls) / len(recalls) if recalls else None,
        "discrimination": sum(discs) / len(discs) if discs else None,
    }


def run_all() -> dict:
    rounds = [run_round(n) for n in sorted(MUTATION_ROUNDS)]
    score = sum(r["score"] for r in rounds)
    maximum = sum(r["max_score"] for r in rounds)
    recalls = [r["invalidation_recall"] for r in rounds if r["invalidation_recall"] is not None]
    discs = [r["discrimination"] for r in rounds if r["discrimination"] is not None]
    harmful = sum(
        1 for r in rounds for f in r["families"] for row in f["rows"] if row["score"] == -1
    )
    return {
        "rounds": rounds,
        "score": score,
        "max_score": maximum,
        "invalidation_recall": sum(recalls) / len(recalls) if recalls else None,
        "discrimination": sum(discs) / len(discs) if discs else None,
        "harmful_outcomes": harmful,
        "scoring_note": (
            "+1 correct / 0 abstained / -1 harmful (HoH scheme, spec §17.2). Recall and "
            "discrimination are reported separately and never merged: an engine that flags "
            "everything scores perfect recall and zero discrimination."
        ),
    }
