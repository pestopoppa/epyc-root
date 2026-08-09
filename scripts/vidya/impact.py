"""Reverse impact analysis, coverage classes, and obligation state.

Spec: docs/design/vidya-pilot-spec.md §5.5 (retraction), §10 (obligations), and the exactness
contract in §0 / §14.

**Impact analysis is hypothetical retraction.** It runs the same mechanism as a real retraction and
throws the result away: zero the tokens a proposed change would invalidate, refold, diff. There is
no second code path to keep in sync, which is deliberate -- an impact report computed differently
from the retraction it predicts is a report that can be wrong in exactly the case that matters.

**The exactness contract is enforced here, not just documented.** Every impact report carries a
coverage class per item, and `unaffected` is only ever claimed for items whose dependencies are
actually mapped. Saying "these 38 beliefs are untouched" about items with no registered edges
would be the single most dangerous output this system could produce -- confidently precise and
quietly wrong -- so the report distinguishes "verified unaffected" from "not reachable through
edges we happen to have".
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fold import Belief, FoldResult, fold  # noqa: E402
from lattice import Grade  # noqa: E402

__all__ = [
    "Coverage", "ImpactItem", "ImpactReport", "impact_of_retracting",
    "frames_carrying_evidence", "impact_of_retracting_evidence",
    "Obligation", "ObligationState", "derive_obligations",
]


class Coverage:
    """How completely an item's dependencies are mapped.

    `UNAFFECTED` may only be asserted for `CLAIM_COMPLETE` items. For anything less, the honest
    statement is "not reachable through the edges we have", which is a different claim.
    """

    CLAIM_COMPLETE = "claim-complete"    # claim and evidence edges registered at claim granularity
    SOURCE_COMPLETE = "source-complete"  # only document-level dependencies are known
    PARTIAL = "partial"                  # some dependencies registered
    UNMAPPED = "unmapped"                # no reliable dependency declaration


def coverage_of(belief: Belief) -> str:
    """Classify how well this belief's support is mapped.

    An anchored support path means the claim is tied to a location, which is what makes a
    dependency statement about it checkable. Document-level support gives source-completeness at
    best -- if the source changes, we know the claim *might* be affected and nothing finer.
    """
    if not belief.pro_paths and not belief.con_paths:
        return Coverage.UNMAPPED
    anchored = [g for _, g in belief.pro_paths + belief.con_paths if g.t >= 2]
    if anchored and len(anchored) == len(belief.pro_paths) + len(belief.con_paths):
        return Coverage.CLAIM_COMPLETE
    if anchored:
        return Coverage.PARTIAL
    return Coverage.SOURCE_COMPLETE


@dataclass
class ImpactItem:
    claim_id: str
    before_pro: Grade
    after_pro: Grade
    before_con: Grade
    after_con: Grade
    coverage: str
    broken_paths: list[str] = field(default_factory=list)
    surviving_paths: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.before_pro != self.after_pro or self.before_con != self.after_con

    @property
    def fragile(self) -> bool:
        """Lost support with nothing left -- the signal worth surfacing first."""
        return self.changed and not self.surviving_paths

    def as_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "before": {"pro": self.before_pro.as_dict(), "con": self.before_con.as_dict()},
            "after": {"pro": self.after_pro.as_dict(), "con": self.after_con.as_dict()},
            "coverage": self.coverage,
            "broken_paths": self.broken_paths,
            "surviving_paths": self.surviving_paths,
            "fragile": self.fragile,
        }


@dataclass
class ImpactReport:
    retracted_frames: list[str]
    affected: list[ImpactItem]
    verified_unaffected: list[str]
    unaffected_but_unmapped: list[str]
    as_of: str

    def as_dict(self) -> dict:
        return {
            "retracted_frames": self.retracted_frames,
            "affected": [i.as_dict() for i in sorted(self.affected, key=lambda x: x.claim_id)],
            "affected_count": len(self.affected),
            "fragile_count": sum(1 for i in self.affected if i.fragile),
            # These two are kept apart on purpose. Collapsing them into one "unaffected" number is
            # the mistake the exactness contract exists to prevent.
            "verified_unaffected": sorted(self.verified_unaffected),
            "verified_unaffected_count": len(self.verified_unaffected),
            "unaffected_but_unmapped": sorted(self.unaffected_but_unmapped),
            "unaffected_but_unmapped_count": len(self.unaffected_but_unmapped),
            "as_of": self.as_of,
            "exactness_note": (
                "Exact relative to the registered edges at this frontier -- never complete "
                "relative to dependencies that were never declared. 'verified_unaffected' is "
                "asserted only for claim-complete items; everything else is reported as "
                "'unaffected_but_unmapped', which is a weaker statement and is not a clean bill "
                "of health."
            ),
        }


def impact_of_retracting(
    frames: Sequence[dict],
    frame_ids: Iterable[str],
    *,
    as_of: str,
) -> ImpactReport:
    """What changes if these frames were retracted? Computes, diffs, and discards.

    Implemented as a real fold over a frame set with a synthetic retraction appended -- the same
    path a committed retraction takes -- rather than as a separate traversal.
    """
    targets = list(frame_ids)
    before = fold(frames, as_of=as_of)

    hypothetical = list(frames) + [
        {
            "frame_type": "epyc.vidya/frame/retraction/v1",
            "assertion": {"retracts": fid},
            "provenance": {"method": "impact.hypothetical", "about": fid},
            "pubinfo": {
                "actor": "vidya.impact",
                "authority_scope": "hypothetical",
                "created_at": as_of,
            },
            "frame_id": f"hypothetical-retraction-of-{fid}",
        }
        for fid in targets
    ]
    after = fold(hypothetical, as_of=as_of)

    affected: list[ImpactItem] = []
    verified_unaffected: list[str] = []
    unaffected_unmapped: list[str] = []

    for claim_id in sorted(set(before.beliefs) | set(after.beliefs)):
        b = before.beliefs.get(claim_id) or Belief(claim_id=claim_id)
        a = after.beliefs.get(claim_id) or Belief(claim_id=claim_id)
        before_labels = {label for label, _ in b.pro_paths + b.con_paths}
        after_labels = {label for label, _ in a.pro_paths + a.con_paths}
        item = ImpactItem(
            claim_id=claim_id,
            before_pro=b.pro, after_pro=a.pro,
            before_con=b.con, after_con=a.con,
            coverage=coverage_of(b),
            broken_paths=sorted(before_labels - after_labels),
            surviving_paths=sorted(after_labels),
        )
        if item.changed or item.broken_paths:
            affected.append(item)
        elif item.coverage == Coverage.CLAIM_COMPLETE:
            verified_unaffected.append(claim_id)
        else:
            unaffected_unmapped.append(claim_id)

    return ImpactReport(
        retracted_frames=sorted(targets),
        affected=affected,
        verified_unaffected=verified_unaffected,
        unaffected_but_unmapped=unaffected_unmapped,
        as_of=as_of,
    )


def frames_carrying_evidence(frames: Sequence[dict], evidence_id: str) -> list[str]:
    """Every frame id asserting support/opposition from this evidence token.

    Retraction operates on frames, but evidence lives in TOKENS, and one token routinely supports
    several claims through several edges. Retracting the token means retracting all of them --
    retracting a single edge would leave the same discredited evidence still supporting its other
    claims, which is the shape of the real 2026-07-24 scorer artifact: one stale extractor
    underpinning two separate conclusions.
    """
    return [
        f["frame_id"]
        for f in frames
        if f.get("assertion", {}).get("evidence_id") == evidence_id and "frame_id" in f
    ]


def impact_of_retracting_evidence(
    frames: Sequence[dict], evidence_id: str, *, as_of: str
) -> ImpactReport:
    """Impact of retracting an evidence TOKEN — every edge it supports."""
    targets = frames_carrying_evidence(frames, evidence_id)
    if not targets:
        raise KeyError(f"no frame carries evidence token {evidence_id!r}")
    return impact_of_retracting(frames, targets, as_of=as_of)


# ---------------------------------------------------------------- obligations

class ObligationState:
    PROPOSED = "proposed"   # defined, but no authority frame has opened it
    OPEN = "open"
    SATISFIED = "satisfied"
    REOPENED = "reopened"   # was satisfied; its activation condition fired again


@dataclass
class Obligation:
    """A governed requirement with declared activation and satisfaction.

    The condition language is capped at the spec's four predicate types with one nesting level
    (§10). That cap is the feature: an obligation DSL grows until it needs its own semantics, and
    anything that does not fit routes to human review instead of growing the language.
    """

    obligation_id: str
    title: str
    activation: dict
    satisfaction: dict
    authority_frame: str | None = None
    state: str = ObligationState.PROPOSED
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "obligation_id": self.obligation_id,
            "title": self.title,
            "state": self.state,
            "authority_frame": self.authority_frame,
            "reasons": self.reasons,
        }


_PREDICATES = {"belief_state_in", "belief_changed", "projection_current", "review_status"}


def _evaluate(expr: dict, beliefs: dict[str, Belief], floor: Grade, ctx: dict) -> tuple[bool, list[str]]:
    """Evaluate one capped condition expression. Returns (result, human reasons)."""
    if not isinstance(expr, dict) or len(expr) != 1:
        raise ValueError(f"condition must be a single-key mapping, got {expr!r}")
    (key, value), = expr.items()

    if key in ("any", "all"):
        if not isinstance(value, list):
            raise ValueError(f"'{key}' takes a list of predicates")
        results, reasons = [], []
        for sub in value:
            if not isinstance(sub, dict) or len(sub) != 1 or set(sub) & {"any", "all"}:
                # One nesting level, enforced rather than documented.
                raise ValueError("condition nesting is capped at one level (spec §10)")
            ok, why = _evaluate(sub, beliefs, floor, ctx)
            results.append(ok)
            reasons.extend(why)
        return (any(results) if key == "any" else all(results)), reasons

    if key not in _PREDICATES:
        raise ValueError(f"unknown predicate {key!r}; allowed: {sorted(_PREDICATES)}")

    if key == "belief_state_in":
        claim_id, states = value["claim_id"], set(value["states"])
        b = beliefs.get(claim_id)
        verdict = b.verdict(floor) if b else "Unknown"
        hit = verdict in states
        return hit, [f"{claim_id} is {verdict}" + (" (matches)" if hit else "")]

    if key == "belief_changed":
        claim_id = value if isinstance(value, str) else value["claim_id"]
        hit = claim_id in set(ctx.get("changed_claims", ()))
        return hit, [f"{claim_id} {'changed' if hit else 'unchanged'} at this frontier"]

    if key == "projection_current":
        pid = value if isinstance(value, str) else value["projection_id"]
        hit = pid in set(ctx.get("current_projections", ()))
        return hit, [f"projection {pid} {'current' if hit else 'not current'}"]

    if key == "review_status":
        want = value if isinstance(value, str) else value["status"]
        hit = ctx.get("review_status") == want
        return hit, [f"review status is {ctx.get('review_status')!r}, wanted {want!r}"]

    raise AssertionError("unreachable")


def derive_obligations(
    obligations: Sequence[Obligation],
    fold_result: FoldResult,
    *,
    floor: Grade,
    context: dict | None = None,
) -> list[Obligation]:
    """Derive obligation state from belief state. Pure; returns new objects."""
    ctx = context or {}
    out: list[Obligation] = []
    for ob in obligations:
        activated, why_a = _evaluate(ob.activation, fold_result.beliefs, floor, ctx)
        satisfied, why_s = _evaluate(ob.satisfaction, fold_result.beliefs, floor, ctx)

        if ob.authority_frame is None:
            # No authority frame means nobody opened it. An obligation that activates itself would
            # be the system granting itself work, which is the intent plane's job, not the fold's.
            state, reasons = ObligationState.PROPOSED, ["no authority frame: cannot open"]
        elif satisfied:
            state, reasons = ObligationState.SATISFIED, why_s
        elif activated:
            was_satisfied = ob.state == ObligationState.SATISFIED
            state = ObligationState.REOPENED if was_satisfied else ObligationState.OPEN
            reasons = why_a
        else:
            state, reasons = ob.state, ["activation condition not met"]

        out.append(
            Obligation(
                obligation_id=ob.obligation_id,
                title=ob.title,
                activation=ob.activation,
                satisfaction=ob.satisfaction,
                authority_frame=ob.authority_frame,
                state=state,
                reasons=reasons,
            )
        )
    return out
