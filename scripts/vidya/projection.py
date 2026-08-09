"""Projections: dependency-declared derived artifacts, and their staleness.

Spec: docs/design/vidya-pilot-spec.md §9.

A projection is a consumer-facing artifact -- a wiki section, a context pack, a report -- that
declares exactly which belief versions it rendered. Compilation splits into four steps, and only
one of them is generative:

    select  (deterministic)  policy picks eligible beliefs
    render  (generative)     a model or human writes prose from that bounded context
    map     (deterministic)  each factual assertion is anchored to the beliefs it rests on
    publish (deterministic)  manifest written, staleness computable from then on

This module owns the deterministic three. Rendering is left to a caller, and the pilot ships a
trivial deterministic renderer so the dependency machinery can be tested without a model in the
loop -- the part being validated is staleness propagation, not prose quality.

**The omissions lane is not optional.** A manifest that lists only what a page asserts can be
invalidated when those beliefs change, and is silent about the beliefs the page *should* have
mentioned and did not. Silent omission is the failure a reader cannot see, so `select` records what
it excluded and why, and the manifest carries it.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from canonical import content_hash  # noqa: E402
from fold import Belief, FoldResult  # noqa: E402
from lattice import Grade, satisfies_conjunctive  # noqa: E402

__all__ = [
    "SelectionPolicy", "Selection", "Assertion", "ProjectionManifest",
    "select_beliefs", "build_manifest", "freshness_of", "Freshness",
    "deterministic_renderer",
]


class Freshness:
    """Projection freshness, mapped onto `dashboard/freshness.py` rather than forked (spec §8.1)."""

    CURRENT = "current"    # -> fresh
    STALE = "stale"        # -> stale: a rendered belief version moved
    INVALID = "invalid"    # -> missing: the artifact no longer matches its manifest hash
    REVIEW = "review"      # -> aging: a rendered belief carries an unreviewed correction


@dataclass(frozen=True)
class SelectionPolicy:
    """What a projection is allowed to render."""

    policy_id: str
    floor: Grade
    conjunctive: bool = True          # authoritative default (spec §4.4b)
    allow_conflicted: bool = False
    allow_review_required: bool = False

    def digest(self) -> str:
        return content_hash(
            {
                "policy_id": self.policy_id,
                "floor": self.floor.as_dict(),
                "conjunctive": self.conjunctive,
                "allow_conflicted": self.allow_conflicted,
                "allow_review_required": self.allow_review_required,
            }
        )


@dataclass
class Selection:
    included: list[Belief] = field(default_factory=list)
    # (claim_id, reason) -- the omissions lane. Every excluded belief is named with why.
    omitted: list[tuple[str, str]] = field(default_factory=list)


def select_beliefs(
    fold_result: FoldResult, policy: SelectionPolicy, *, claim_ids: Sequence[str] | None = None
) -> Selection:
    """Deterministically pick the beliefs a projection may render, and record every exclusion."""
    sel = Selection()
    candidates = claim_ids if claim_ids is not None else sorted(fold_result.beliefs)
    for cid in candidates:
        b = fold_result.beliefs.get(cid)
        if b is None:
            sel.omitted.append((cid, "no such belief at this frontier"))
            continue
        verdict = b.verdict(policy.floor, conjunctive=policy.conjunctive)
        if verdict == "Conflicted" and not policy.allow_conflicted:
            sel.omitted.append((cid, "conflicted and policy rejects conflict"))
            continue
        if b.review_required and not policy.allow_review_required:
            sel.omitted.append((cid, "unreviewed correction recorded against it"))
            continue
        if verdict not in ("Supported", "Conflicted"):
            reading = "conjunctive" if policy.conjunctive else "join"
            sel.omitted.append(
                (cid, f"{verdict} under {policy.floor} ({reading} reading)")
            )
            continue
        sel.included.append(b)
    return sel


@dataclass
class Assertion:
    """One factual statement in a rendered artifact, tied to the beliefs it rests on."""

    assertion_id: str
    rendered_text: str
    belief_ids: list[str]
    rhetorical_role: str = "factual"

    def as_dict(self) -> dict:
        return {
            "assertion_id": self.assertion_id,
            "rendered_text_hash": content_hash(self.rendered_text),
            "belief_ids": sorted(self.belief_ids),
            "rhetorical_role": self.rhetorical_role,
        }


@dataclass
class ProjectionManifest:
    projection_id: str
    artifact_path: str
    content_hash: str
    rendered_frontier: int
    fold_version: str
    policy_digest: str
    as_of: str
    # claim_id -> the exact belief fingerprint rendered. Staleness is a comparison against these,
    # which is why they are stored per-belief rather than as one aggregate hash: an aggregate would
    # tell you something changed without telling you what, and every consumer would have to
    # regenerate to find out.
    belief_versions: dict[str, str] = field(default_factory=dict)
    assertions: list[Assertion] = field(default_factory=list)
    omissions: list[dict] = field(default_factory=list)
    unresolved_conflicts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "projection_id": self.projection_id,
            "artifact": {"path": self.artifact_path, "content_hash": self.content_hash},
            "rendered_frontier": self.rendered_frontier,
            "fold_version": self.fold_version,
            "policy_digest": self.policy_digest,
            "as_of": self.as_of,
            "belief_versions": dict(sorted(self.belief_versions.items())),
            "assertions": [a.as_dict() for a in self.assertions],
            "omissions": self.omissions,
            "unresolved_conflicts": sorted(self.unresolved_conflicts),
        }


def belief_version(belief: Belief) -> str:
    """A fingerprint of everything a projection depends on for this belief.

    Includes corrections: a projection rendered before a correction was recorded is stale even
    though the grade did not move, because the reader would not know a review is outstanding.
    """
    return content_hash(
        {
            "claim_id": belief.claim_id,
            "pro": belief.pro.as_dict(),
            "con": belief.con.as_dict(),
            "pro_paths": sorted(label for label, _ in belief.pro_paths),
            "con_paths": sorted(label for label, _ in belief.con_paths),
            "corrections": sorted(belief.corrections),
        }
    )


def deterministic_renderer(beliefs: Sequence[Belief]) -> tuple[str, list[Assertion]]:
    """A minimal, model-free renderer.

    Real compilation puts a model or a human here. This exists so the dependency and staleness
    machinery can be exercised end-to-end without one -- what is under test is whether a changed
    belief marks the right sections stale, not whether the prose reads well.
    """
    lines, assertions = [], []
    for i, b in enumerate(sorted(beliefs, key=lambda x: x.claim_id)):
        text = (
            f"{b.claim_id} is supported at {b.pro} "
            f"(witnesses: {', '.join(b.pro_witnesses) or 'none'})."
        )
        lines.append(f"- {text}")
        assertions.append(
            Assertion(assertion_id=f"ast_{i:04d}", rendered_text=text, belief_ids=[b.claim_id])
        )
    return "\n".join(lines) + "\n", assertions


def build_manifest(
    *,
    projection_id: str,
    artifact_path: str,
    selection: Selection,
    fold_result: FoldResult,
    policy: SelectionPolicy,
    fold_version: str,
    renderer: Callable[[Sequence[Belief]], tuple[str, list[Assertion]]] = deterministic_renderer,
) -> tuple[str, ProjectionManifest]:
    """Render and build the manifest. Returns ``(artifact_text, manifest)``.

    Verification is part of publication, not a later step: every assertion must map to a belief
    that selection actually included. A rendered sentence citing an excluded belief is a defect
    caught here rather than discovered by a reader.
    """
    text, assertions = renderer(selection.included)
    included_ids = {b.claim_id for b in selection.included}

    for a in assertions:
        if a.rhetorical_role != "factual":
            continue
        unknown = set(a.belief_ids) - included_ids
        if unknown:
            raise ValueError(
                f"{projection_id}: assertion {a.assertion_id} cites beliefs the policy did not "
                f"select: {sorted(unknown)}"
            )
        if not a.belief_ids:
            raise ValueError(
                f"{projection_id}: assertion {a.assertion_id} is marked factual but cites no "
                "belief -- label it non-factual or give it a source"
            )

    manifest = ProjectionManifest(
        projection_id=projection_id,
        artifact_path=artifact_path,
        content_hash=content_hash(text),
        rendered_frontier=fold_result.frontier,
        fold_version=fold_version,
        policy_digest=policy.digest(),
        as_of=fold_result.as_of,
        belief_versions={b.claim_id: belief_version(b) for b in selection.included},
        assertions=assertions,
        omissions=[{"claim_id": cid, "reason": why} for cid, why in sorted(selection.omitted)],
        unresolved_conflicts=[
            b.claim_id
            for b in selection.included
            if b.verdict(policy.floor, conjunctive=policy.conjunctive) == "Conflicted"
        ],
    )
    return text, manifest


def freshness_of(
    manifest: ProjectionManifest,
    fold_result: FoldResult,
    *,
    artifact_text: str | None = None,
) -> tuple[str, list[str]]:
    """Compare a manifest against current state. Returns ``(freshness, reasons)``.

    Cheap and mechanical by design: comparing stored fingerprints costs nothing, so dirty-marking
    happens immediately on every source change while regeneration stays lazy and demand-driven.
    Deferring the marking would be the one thing that makes lazy refresh unsafe.
    """
    reasons: list[str] = []

    if artifact_text is not None and content_hash(artifact_text) != manifest.content_hash:
        return Freshness.INVALID, [
            "artifact content no longer matches its manifest hash -- the prose was edited "
            "outside the compiler, so nothing here describes what is on disk"
        ]

    for claim_id, rendered in sorted(manifest.belief_versions.items()):
        b = fold_result.beliefs.get(claim_id)
        if b is None:
            reasons.append(f"{claim_id}: belief no longer exists at this frontier")
            continue
        if belief_version(b) != rendered:
            reasons.append(f"{claim_id}: belief version changed since rendering")

    if reasons:
        return Freshness.STALE, reasons

    review = sorted(
        cid for cid in manifest.belief_versions
        if (b := fold_result.beliefs.get(cid)) and b.review_required
    )
    if review:
        return Freshness.REVIEW, [f"{cid}: unreviewed correction recorded" for cid in review]

    return Freshness.CURRENT, []
