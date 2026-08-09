"""The query-time freshness gate, and the certificate a passing answer carries.

Spec: docs/design/vidya-pilot-spec.md §8.2 (gate outcomes), §11.2 (certificates), §12 (proof
standards).

**The promise, and its exact shape.** A consumer never unknowingly uses stale state as current. The
gate does NOT promise to make a belief fresh -- it promises that when it cannot, it says so and
says what is missing. Those are very different guarantees, and conflating them is how a system
starts manufacturing confident answers out of unavailable evidence.

Five honest outcomes. `ABSTAIN` and `BLOCK` are successes of the gate, not failures of it: an
abstention with a named next action is a better answer than a plausible one, which is the whole
argument for refusal semantics over advisory banners.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from canonical import content_hash  # noqa: E402
from fold import Belief, FoldResult  # noqa: E402
from lattice import Grade, satisfies_conjunctive  # noqa: E402

__all__ = ["Outcome", "UsePolicy", "GateResult", "evaluate", "Standard",
           "query_served_frame", "obligation_disposition_frame"]


class Outcome:
    ALLOW = "allow"                      # current, policy-eligible
    ALLOW_WITH_WARNING = "allow_with_warning"   # served, labelled, never as authoritative
    RECOMPUTE = "recompute"              # a deterministic refold would settle it
    ABSTAIN = "abstain"                  # evidence is insufficient; no next action will change that cheaply
    BLOCK = "block"                      # a named human/verifier/source action is required first


class Standard:
    """Proof standards as consumer-policy vocabulary (spec §12).

    SE and DV are computable from the certified lattice core. PE/CCE/BRD additionally need advisory
    degrees, which the pilot does not compute -- asking for one is refused rather than silently
    downgraded, because a policy that thinks it got beyond-reasonable-doubt and got scintilla is
    worse off than one that got an error.
    """

    SE = "SE"    # scintilla: at least one applicable pro path
    DV = "DV"    # dialectical validity: pro exists, no applicable con
    PE = "PE"
    CCE = "CCE"
    BRD = "BRD"

    CERTIFIABLE = frozenset({SE, DV})
    ADVISORY_ONLY = frozenset({PE, CCE, BRD})


@dataclass(frozen=True)
class UsePolicy:
    """What a consumer declares before asking. Every field changes what an answer means."""

    use: str                      # e.g. "wiki-authoritative", "exploration", "planning"
    floor: Grade
    standard: str = Standard.DV
    conjunctive: bool = True
    allow_conflicted: bool = False
    allow_review_required: bool = False
    allow_labelled_stale: bool = False   # exploratory consumers may opt in
    min_disjoint_supports: int = 1

    def digest(self) -> str:
        return content_hash(
            {
                "use": self.use,
                "floor": self.floor.as_dict(),
                "standard": self.standard,
                "conjunctive": self.conjunctive,
                "allow_conflicted": self.allow_conflicted,
                "allow_review_required": self.allow_review_required,
                "allow_labelled_stale": self.allow_labelled_stale,
                "min_disjoint_supports": self.min_disjoint_supports,
            }
        )


@dataclass
class GateResult:
    outcome: str
    claim_id: str
    reasons: list[str] = field(default_factory=list)
    required_next_actions: list[str] = field(default_factory=list)
    certificate: dict | None = None

    @property
    def usable_as_current(self) -> bool:
        return self.outcome == Outcome.ALLOW

    def as_dict(self) -> dict:
        return {
            "result": self.outcome,
            "claim_id": self.claim_id,
            "reasons": self.reasons,
            "required_next_actions": self.required_next_actions,
            "certificate": self.certificate,
        }


def _disjoint_supports(belief: Belief) -> int:
    """Leaf-disjoint support count, capped at 5 and under-approximate when the cap binds.

    With `Corroborated` removed from the carrier this is the ONLY mechanical notion of
    independence in the system (spec §7.3), so a bound that binds must be reported as an
    under-approximation at the point of use rather than silently treated as the answer.
    """
    labels = [label for label, _ in belief.pro_paths]
    return min(len(set(labels)), 5)


def _build_certificate(
    belief: Belief, policy: UsePolicy, fold_result: FoldResult, satisfying: list[str]
) -> dict:
    """A replayable record of how this answer was reached.

    Field set mapped from the SLSA verification-summary attestation (spec §11.2). It proves the
    derivation followed the registered evidence and rules -- NOT that the claim is true, which is a
    distinction the certificate states in its own body rather than leaving to documentation.

    `input_attestations` is the replayability hook: same policy digest + same input digests => same
    result, checkable offline.
    """
    cert = {
        "_type": "epyc.vidya/certificate/v1",
        "verifier": {"id": "vidya.gate", "fold_version": fold_result.__class__.__module__},
        "resource": {"claim_id": belief.claim_id, "question": policy.use},
        "policy": {"digest": policy.digest(), "standard": policy.standard},
        "input_attestations": sorted(
            {label for label, _ in belief.pro_paths + belief.con_paths}
        ),
        "frontier": fold_result.frontier,
        "as_of": fold_result.as_of,
        "result": "PASSED",
        "verified_levels": {
            "pro": belief.pro.as_dict(),
            "con": belief.con.as_dict(),
            "standard_met": policy.standard,
        },
        "satisfying_paths": sorted(satisfying),
        "disjoint_supports": _disjoint_supports(belief),
        "disjoint_supports_is_under_approximation": _disjoint_supports(belief) >= 5,
        "proves": (
            "that this derivation followed the registered evidence and rules at the stated "
            "frontier -- NOT that the underlying proposition is true"
        ),
    }
    cert["certificate_hash"] = content_hash(cert)
    return cert


def evaluate(
    claim_id: str,
    fold_result: FoldResult,
    policy: UsePolicy,
    *,
    requested_frontier: int | None = None,
) -> GateResult:
    """Apply a use policy to one claim. Never mutates; never calls a model."""
    reasons: list[str] = []
    actions: list[str] = []

    if policy.standard in Standard.ADVISORY_ONLY:
        return GateResult(
            outcome=Outcome.BLOCK,
            claim_id=claim_id,
            reasons=[
                f"standard {policy.standard} needs advisory degrees, which the certified core does "
                "not compute; it is not silently downgraded to a weaker standard"
            ],
            required_next_actions=[
                "use SE or DV, or enable the advisory overlay and accept a non-certified answer"
            ],
        )
    if policy.standard not in Standard.CERTIFIABLE:
        return GateResult(
            outcome=Outcome.BLOCK, claim_id=claim_id,
            reasons=[f"unknown proof standard {policy.standard!r}"],
            required_next_actions=[f"use one of {sorted(Standard.CERTIFIABLE)}"],
        )

    belief = fold_result.beliefs.get(claim_id)
    if belief is None:
        return GateResult(
            outcome=Outcome.ABSTAIN, claim_id=claim_id,
            reasons=["no such claim at this frontier"],
            required_next_actions=["ingest a source that proposes this claim"],
        )

    # A stale frontier is recomputable, not fatal -- and this is the one outcome the gate can fix
    # by itself, which is why it is separated from ABSTAIN.
    if requested_frontier is not None and fold_result.frontier < requested_frontier:
        return GateResult(
            outcome=Outcome.RECOMPUTE, claim_id=claim_id,
            reasons=[
                f"folded at frontier {fold_result.frontier}, caller requires {requested_frontier}"
            ],
            required_next_actions=[f"refold at frontier >= {requested_frontier}"],
        )

    pro_ok, satisfying = satisfies_conjunctive(belief.pro_paths, policy.floor) if policy.conjunctive \
        else (belief.pro.dominates(policy.floor), [l for l, _ in belief.pro_paths])
    con_ok, _ = satisfies_conjunctive(belief.con_paths, policy.floor) if policy.conjunctive \
        else (belief.con.dominates(policy.floor), [])

    if belief.review_required and not policy.allow_review_required:
        return GateResult(
            outcome=Outcome.BLOCK, claim_id=claim_id,
            reasons=[
                f"{len(belief.corrections)} unreviewed correction(s) recorded against this claim"
            ],
            required_next_actions=[
                "review the recorded correction and record its effect on this claim, "
                "or use a policy that accepts review-required beliefs"
            ],
        )

    if con_ok and not policy.allow_conflicted:
        if pro_ok:
            return GateResult(
                outcome=Outcome.BLOCK, claim_id=claim_id,
                reasons=["conflicted: support and opposition both clear the floor"],
                required_next_actions=[
                    "adjudicate the conflict, or use a policy that accepts conflict explicitly"
                ],
            )
        return GateResult(
            outcome=Outcome.ABSTAIN, claim_id=claim_id,
            reasons=["opposed at this floor"],
            required_next_actions=["find support meeting the floor, or accept the opposition"],
        )

    if not pro_ok:
        reading = "conjunctive" if policy.conjunctive else "join"
        reasons.append(
            f"no {reading}-reading support path clears {policy.floor} "
            f"(best pro is {belief.pro})"
        )
        # Naming the missing AXIS is what makes the refusal actionable rather than a shrug.
        if belief.pro.q < policy.floor.q:
            actions.append(
                f"raise warrant quality to {policy.floor.q_name}: verify the claim against "
                "primary source"
            )
        if belief.pro.t < policy.floor.t:
            actions.append(
                f"raise traceability to {policy.floor.t_name}: record a claim_anchors entry "
                "with the exact span, and its hash and source revision"
            )
        if policy.allow_labelled_stale:
            return GateResult(Outcome.ALLOW_WITH_WARNING, claim_id, reasons, actions)
        return GateResult(Outcome.ABSTAIN, claim_id, reasons, actions)

    disjoint = _disjoint_supports(belief)
    if disjoint < policy.min_disjoint_supports:
        return GateResult(
            outcome=Outcome.ABSTAIN, claim_id=claim_id,
            reasons=[
                f"{disjoint} independent support path(s), policy requires "
                f"{policy.min_disjoint_supports}"
            ],
            required_next_actions=["find an independent corroborating source"],
        )

    return GateResult(
        outcome=Outcome.ALLOW,
        claim_id=claim_id,
        reasons=[f"{policy.standard} met at {policy.floor}"],
        certificate=_build_certificate(belief, policy, fold_result, satisfying),
    )


# --------------------------------------------------------------------- R5b

def query_served_frame(result: GateResult, policy: UsePolicy, *, frontier: int, at: str) -> dict:
    """A frame recording that a query was served, and how.

    **This is a write-time decision that cannot be undone by hindsight.** Reuse and abstention
    rates are unobservable unless queries are recorded as they happen -- no amount of later
    analysis reconstructs a query nobody logged. R5 stays unanswerable however long the pilot runs
    without this, which is why it costs one append per authoritative query rather than being
    deferred with the rest of the longitudinal work.

    Deliberately records the OUTCOME, not just the hit: an abstention is the datum that tells you
    the gate is refusing too much, and a log of successes only would hide exactly that.
    """
    from frames import make_frame  # noqa: PLC0415

    return make_frame(
        frame_type="epyc.vidya/frame/query_served/v1",
        assertion={
            "claim_id": result.claim_id,
            "use": policy.use,
            "outcome": result.outcome,
            "usable_as_current": result.usable_as_current,
            "certificate_hash": (result.certificate or {}).get("certificate_hash"),
        },
        provenance={
            "method": "vidya.gate/evaluate",
            "about": result.claim_id,
            "policy_digest": policy.digest(),
            "frontier": frontier,
        },
        actor="vidya.gate",
        authority_scope="query-telemetry",
        created_at=at,
    )


def obligation_disposition_frame(
    obligation_id: str, disposition: str, *, actor: str, at: str, note: str = ""
) -> dict:
    """Record what a human actually did about a surfaced obligation.

    Also write-time-only. The spec's auto-downgrade rule -- a class of obligations exceeding a
    ratified no-action threshold stops interrupting people -- has no input without this, so an
    obligation system without disposition recording can never learn that it is being ignored.
    """
    allowed = {"accepted", "acted", "deferred", "dismissed"}
    if disposition not in allowed:
        raise ValueError(f"disposition must be one of {sorted(allowed)}, got {disposition!r}")
    from frames import make_frame  # noqa: PLC0415

    return make_frame(
        frame_type="epyc.vidya/frame/obligation_disposition/v1",
        assertion={"obligation_id": obligation_id, "disposition": disposition, "note": note},
        provenance={"method": "human-disposition", "about": obligation_id},
        actor=actor,
        authority_scope="obligation-disposition",
        created_at=at,
    )
