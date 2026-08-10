"""The measurement ingestion contract: one grammar, one grader, many projections.

WHY THIS EXISTS. Different loops record measurements in different shapes — an autopilot trial row,
an AutoKernel `evaluation_event`, a sealed benchmark manifest, a llama-bench sweep. Each adapter
that arrived was written with its own reading of `MEASUREMENT_POLICY.md`, and on 2026-08-10 two of
them were caught disagreeing about the same case:

    record with no protocol and no attestation
      measurement_record.grade()  ->  Judged/T0
      sealed_manifest.grade()     ->  Judged/Located

Same constitution, same rule, two answers on the T axis. Neither is obviously wrong, which is the
point: a rule reimplemented per source becomes N dialects of itself, and the divergence surfaces as
unexplainable grade differences between corpora long after anyone remembers there were two
functions. The substrate exists to catch exactly this class of defect, so it may not contain it.

THE CONTRACT. An adapter's only job is **projection**: map its native record into the canonical
tuple below. It never grades, and it never invents an element it cannot find — a missing element is
reported and grades the claim down, which is a true statement about the measurement.

    native record  --project-->  ClaimTuple  --grade()-->  (Q, T, reasons)  --> frames

The vocabulary is not invented here either. It is AutoKernel's `claim_grammar`
(`epyc-inference-research` `scripts/kernel_rnd/autokernel/schemas.py`), which already enforces
`MEASUREMENT.md:13` as a REQUIRED schema block. Aligning on it means the strictest existing
producer defines the shape, rather than the newest adapter redefining it.

WHAT GRADING MEANS. Straight from the constitution's own words, one ladder for every source:

  * full tuple, artifact present and hashed  -> `Witnessed/Attested`  (decision-gating)
  * full tuple, artifact named but unhashed  -> `Witnessed/Anchored`  (re-derivable, not pinned)
  * protocol cited, tuple incomplete         -> `Verified/Located`    (a result, not gating)
  * no protocol citation                     -> `Judged/…`            (an OBSERVATION)

The last row is load-bearing. An observation is worth recording — it is what hypotheses are made of
— and grading it honestly at `Judged` is what stops it being cited later as though it had gated a
decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]

# Borrowed verbatim from AutoKernel schemas.py. Kept as literals rather than imported: the research
# repo is a sibling working tree that may be absent, and a conformance test pins that the two
# vocabularies stay identical, which is stronger than an import that silently follows a rename.
CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})
METRIC_DIRECTIONS = frozenset({"higher_better", "lower_better"})


class ProjectionError(ValueError):
    """An adapter produced something that is not a claim tuple."""


@dataclass(frozen=True)
class ClaimTuple:
    """`MEASUREMENT.md:13` — (metric, protocol-id, n/reps, date, attestation ref) — plus the two
    labels `:85-95` requires so a number is never unlabelled: `category` and `metric_direction`."""

    measurement_id: str
    metric: str
    value: Any
    date: str
    category: str
    claim: str
    metric_direction: str = "higher_better"
    protocol_id: str = ""
    reps: int | None = None
    # Whether `reps` counted what SCORED or merely what was ATTEMPTED. "n=55 attempted" and
    # "n=55 scored" are different claims; a tuple that cannot tell them apart overstates its sample.
    reps_basis: str = ""
    unit: str = ""
    attestation_path: str = ""
    attestation_sha256: str = ""
    attestation_locator: str = ""
    # Whether the attested artifact exists. `None` means "derive it from `attestation_path`", which
    # is right when the path IS the artifact. A projector that determines presence some other way
    # — a sealed manifest checks its `authority/*` files, not the manifest itself — sets it
    # explicitly. Without this the ladder silently downgraded every sealed run to Anchored.
    attestation_present: bool | None = None
    source_kind: str = "measurement"
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Only IDENTITY and LABELS are structural. `date`, `protocol_id`, `reps` and the
        # attestation are gradable elements: a measurement missing them is a real measurement with
        # a low grade, and refusing to represent it would delete the very thing the ladder exists
        # to describe. An earlier draft required `date` here and made dateless runs unrepresentable
        # — caught by the sealed-manifest tests, which is exactly what they are for.
        for name in ("measurement_id", "metric", "claim"):
            if not str(getattr(self, name) or "").strip():
                raise ProjectionError(f"{name} is required and must be non-empty")
        if self.category not in CATEGORIES:
            raise ProjectionError(
                f"category must be exactly one of {sorted(CATEGORIES)} (got {self.category!r}) — "
                "MEASUREMENT.md:85-95, an unlabelled measurement is not decision-grade")
        if self.metric_direction not in METRIC_DIRECTIONS:
            raise ProjectionError(
                f"metric_direction must be one of {sorted(METRIC_DIRECTIONS)} "
                f"(got {self.metric_direction!r}) — a number whose direction is unknown cannot be "
                "compared to anything")
        if self.reps is not None and (not isinstance(self.reps, int) or self.reps < 1):
            raise ProjectionError("reps must be a positive integer when present; zero reps is not "
                                  "a measurement")
        if self.attestation_sha256 and len(self.attestation_sha256) != 64:
            raise ProjectionError("attestation_sha256 must be a 64-character hex digest")


def artifact_present(tup: ClaimTuple) -> bool:
    """True when the attestation names a file actually on disk.

    A hash over an artifact that no longer exists proves nothing — the constitution's own reason
    for making the top T level require the artifact to be present, not merely referenced.

    Containment is checked on the UNRESOLVED path: reject absolute paths and any `..` component.
    Resolving first would follow `repos/<name>` out to its real location under /mnt/raid0 (the
    working-tree symlink every repo here uses) and reject a legitimate sibling-repo artifact as an
    escape, while `../../etc/passwd` is still caught by the `..` test.
    """
    if tup.attestation_present is not None:
        return tup.attestation_present
    if not tup.attestation_path:
        return False
    rel = PurePosixPath(tup.attestation_path)
    if rel.is_absolute() or ".." in rel.parts:
        return False
    return (REPO_ROOT / rel).is_file()


def grade(tup: ClaimTuple) -> tuple[str, str, list[str]]:
    """THE grading ladder. One implementation, every source.

    `reasons` names every missing element, so a low grade is self-explaining and nobody has to
    reverse-engineer why their measurement failed to reach Witnessed.
    """
    reasons: list[str] = []
    has_protocol = bool(tup.protocol_id.strip())
    has_ref = bool(tup.attestation_path or tup.attestation_locator)

    if not has_protocol:
        reasons.append("no protocol citation — this is an OBSERVATION, never decision-gating "
                       "(MEASUREMENT.md:13)")
        # An observation that names where it came from is Located; one that names nothing is T0.
        # This is the case the two former implementations disagreed on; resolved toward the more
        # informative reading, since a locator genuinely does locate the claim.
        return "Judged", ("Located" if has_ref else "T0"), reasons

    if tup.reps is None:
        reasons.append("no n/reps recorded")
    if not tup.date:
        reasons.append("no date recorded")
    if not has_ref:
        reasons.append("no attestation reference — a result, but not decision-gating")
    elif not tup.attestation_sha256:
        reasons.append("attestation named but not hashed")
    elif not artifact_present(tup):
        reasons.append("attestation hashed but the artifact is not on disk — a hash over a file "
                       "that no longer exists proves nothing")
    if tup.reps is not None and tup.reps_basis.startswith("attempted"):
        reasons.append(f"n is the ATTEMPTED count ({tup.reps_basis}), not the scored one")

    if not (tup.reps is not None and tup.date and has_ref):
        return "Verified", "Located", reasons
    if tup.attestation_sha256 and artifact_present(tup):
        return "Witnessed", "Attested", reasons
    return "Witnessed", "Anchored", reasons


# --- source classes: one carrier, one vocabulary, one ladder PER CLASS ----------------------
#
# The carrier is shared; the grading rule is not, and pretending otherwise would be its own
# category error. Two classes exist:
#
#   * `measurement` — graded by the constitution's claim rule (protocol / n / date / attestation).
#     Reaches `Witnessed`, because a protocol-admissible measurement with durable attestation is
#     exactly what that level means.
#   * `literature`  — graded by verification status (anchored against the primary source, dive
#     verified or overturned). CAPS at `Verified` by construction: an intake entry is a record of
#     what someone else reported, and no amount of careful reading turns it into a measurement.
#
# What must be unified across classes is the lattice vocabulary, the projection discipline, the
# identity scheme and frame emission. What must NOT be unified is the ladder. So each class
# registers exactly one, and a conformance test fails if a second appears — the check that would
# have caught `measurement_record` and `sealed_manifest` drifting apart on 2026-08-10.

Ladder = Callable[..., tuple]
_LADDERS: dict[str, tuple[str, Ladder]] = {}


def register_ladder(source_class: str, module: str) -> Callable[[Ladder], Ladder]:
    """Declare THE grading ladder for a source class. A second registration is an error."""

    def deco(fn: Ladder) -> Ladder:
        existing = _LADDERS.get(source_class)
        if existing and existing[1] is not fn:
            raise ProjectionError(
                f"source class {source_class!r} already has a ladder in {existing[0]!r}; a second "
                "implementation of one rule becomes two dialects of it")
        _LADDERS[source_class] = (module, fn)
        return fn

    return deco


def ladders() -> dict[str, tuple[str, Ladder]]:
    return dict(_LADDERS)


register_ladder("measurement", "scripts/vidya/claim_tuple.py")(grade)


# --- the projection registry ----------------------------------------------------------------

Projection = Callable[[Any], ClaimTuple]
_REGISTRY: dict[str, Projection] = {}


def register(name: str) -> Callable[[Projection], Projection]:
    """Register a source's projection. The registry is what makes the contract checkable: a
    conformance test can enumerate every source and assert each one produces a valid tuple,
    which is impossible when each adapter grades privately."""

    def deco(fn: Projection) -> Projection:
        if name in _REGISTRY and _REGISTRY[name] is not fn:
            raise ProjectionError(f"projection {name!r} is already registered")
        _REGISTRY[name] = fn
        return fn

    return deco


def registered() -> dict[str, Projection]:
    return dict(_REGISTRY)


def to_frames(tup: ClaimTuple, *, as_of: str, adapter_id: str,
              authority: str = "measurement") -> list[dict]:
    """Emit source + claim + supporting-evidence frames for one graded tuple.

    Shared so that every source lands in the ledger with the same shape. An adapter that emitted
    its own frames could quietly use a different claim-id scheme, and identity divergence is how
    three A/B arms merged into one belief earlier in this program.
    """
    from frames import make_frame  # local import: keeps this module importable without the ledger

    q, t, reasons = grade(tup)
    ident = tup.measurement_id
    source_id, claim_id = f"src_{ident}", f"clm_{ident}"
    return [
        make_frame(
            frame_type="epyc.vidya/frame/source_observed/v1",
            assertion={"source_id": source_id,
                       "locator": tup.attestation_locator or tup.attestation_path or f"measurement:{ident}",
                       "source_kind": tup.source_kind, "title": tup.metric,
                       "revision_observed": tup.date},
            provenance={"method": adapter_id, "about": ident, "retrofit": False},
            actor=adapter_id, authority_scope=authority, created_at=as_of),
        make_frame(
            frame_type="epyc.vidya/frame/claim_proposed/v1",
            assertion={"claim_id": claim_id, "display_text": tup.claim, "source_id": source_id},
            provenance={"method": adapter_id, "derived_from": source_id, "about": ident},
            actor=adapter_id, authority_scope=authority, created_at=as_of),
        make_frame(
            frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
            assertion={"claim_id": claim_id, "evidence_id": f"evd_{ident}",
                       "grade": {"Q": q, "T": t}, "source_id": source_id,
                       "protocol_id": tup.protocol_id, "reps": tup.reps,
                       "category": tup.category, "metric_direction": tup.metric_direction},
            provenance={"evidence": f"evd_{ident}", "about": claim_id, "method": adapter_id,
                        "grade_reasons": reasons, "reps_basis": tup.reps_basis},
            actor=adapter_id, authority_scope=authority, created_at=as_of),
    ]
