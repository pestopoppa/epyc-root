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
    # SC57 — the verifier-class element. WHAT THE CHECK ASSERTED, in the checker's own terms: the
    # theorem statement a prover discharged, the property a validator decided, the postcondition a
    # test pinned. A boolean records that SOMETHING passed; only this records WHAT. A machine-checked
    # verdict certifies the proposition the checker decided and binds it to nothing else — the
    # certificate "does not certify individual mathematical truth" (`intake-1307#05`), and in one
    # real pipeline an automated check labelled 73.6% of proved artifacts non-trivial-and-correct
    # while a manual audit put faithfulness far lower (`intake-1307#00`, admissible as an existence
    # proof that the gap is large, never as a rate). Empty on non-verifier classes, and NEVER
    # inferred on read: a proposition invented after the fact claims warrant the original check
    # never captured.
    decided_proposition: str = ""
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
        if not isinstance(self.decided_proposition, str):
            raise ProjectionError(
                "decided_proposition must be a string — the proposition the check actually "
                "decided, in the checker's own terms")


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


# --- the verifier class: what the check ASSERTED, never just whether it passed (SC57) ---------
#
# A third adapter class, and the only one with a projection precondition of its own. A verifier --
# a prover, a property checker, a schema validator, a contract test -- answers a question, and the
# answer is a boolean. The boolean is not the finding. `intake-1307#05`: a machine-checked
# certificate "does not certify individual mathematical truth"; it certifies THE PROPOSITION THE
# CHECKER DECIDED, which is a different sentence and is the one nobody records. `intake-1307#00` is
# the existence proof that the resulting gap is large -- an automated check labelled 73.6% of proved
# artifacts non-trivial-and-correct where a manual audit put faithfulness far lower (a reweighted
# projection from a 45-example single-annotator audit: admissible that the gap exists, never as a
# rate).
#
# So a verifier-class adapter MUST project `decided_proposition`, and the registry refuses one that
# emits pass/fail alone. This is a PROJECTION rule, not a grading rule: no verifier ladder is
# registered and none may be added here, because `claim_tuple.grade()` still decides (spec §4.7).
# What the recorded proposition licenses -- specifically, the statement-binding precondition that
# would cap an unbound verifier tuple at `Judged` -- is SC56 and is deliberately NOT implemented
# here; it changes grading semantics and is operator-reviewed.

MEASUREMENT_CLASS = "measurement"
LITERATURE_CLASS = "literature"
VERIFIER_CLASS = "verifier"
SOURCE_CLASSES = frozenset({MEASUREMENT_CLASS, LITERATURE_CLASS, VERIFIER_CLASS})

# What a check ANSWERS, as opposed to what it ASSERTS. Named explicitly so the refusal is
# mechanical rather than a comment somebody has to remember -- the same reason `frames.py` names
# its grade-bearing keys instead of describing them.
_BARE_VERDICT_TOKENS = frozenset({
    "0", "1", "accept", "accepted", "error", "fail", "failed", "failure", "false", "green",
    "invalid", "no", "not ok", "ok", "pass", "passed", "proved", "red", "reject", "rejected",
    "sat", "success", "true", "unknown", "unsat", "unverified", "valid", "verified", "yes",
})


def check_decided_proposition(value: object, *, where: str) -> str:
    """Refuse a verifier projection that records a verdict instead of a proposition.

    Two failures, one rule. An empty field says the adapter never captured what was decided, and
    that can never be recovered later: a proposition invented on read claims warrant the original
    check never captured. A bare verdict token is the same hole with a value in it -- "pass" is the
    answer, not the statement, and it is exactly what a downstream citer would have to guess at.
    """
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(
            f"{where}: a verifier-class projection must carry `decided_proposition` -- the "
            "proposition the checker actually decided. A boolean records that something passed; "
            "only the proposition records WHAT was decided, and it cannot be recovered on read "
            "(docs/design/vidya-pilot-spec.md §4.7)")
    normalized = value.strip().lower().rstrip(".")
    if normalized in _BARE_VERDICT_TOKENS:
        raise ProjectionError(
            f"{where}: `decided_proposition` is the bare verdict {value!r} -- that is what the "
            "check ANSWERED, not what it ASSERTED. Record the statement the checker discharged, "
            "in the checker's own terms")
    return value.strip()


# --- the projection registry ----------------------------------------------------------------

Projection = Callable[[Any], ClaimTuple]
_REGISTRY: dict[str, Projection] = {}
# The UNWRAPPED function per name. Duplicate detection must compare what the adapter wrote, not
# what the registry wrapped it in, or re-importing a verifier adapter would refuse itself.
_ORIGINALS: dict[str, Projection] = {}
_SOURCE_CLASS: dict[str, str] = {}


def _verifier_guard(name: str, fn: Projection, native_field: str) -> Projection:
    """Post-condition on a verifier projection: every tuple it emits names what was decided."""
    import functools

    @functools.wraps(fn)
    def guarded(*args, **kwargs):
        out = fn(*args, **kwargs)
        where = f"projection {name!r} (verifier class, native field {native_field!r})"
        candidates = out if isinstance(out, (list, tuple)) else [out]
        for item in candidates:
            if isinstance(item, ClaimTuple):
                check_decided_proposition(item.decided_proposition, where=where)
        return out

    guarded.__vidya_source_class__ = VERIFIER_CLASS
    guarded.__vidya_decided_proposition_field__ = native_field
    return guarded


def register(
    name: str,
    *,
    source_class: str = MEASUREMENT_CLASS,
    decided_proposition_field: str | None = None,
) -> Callable[[Projection], Projection]:
    """Register a source's projection. The registry is what makes the contract checkable: a
    conformance test can enumerate every source and assert each one produces a valid tuple,
    which is impossible when each adapter grades privately.

    `source_class="verifier"` (SC57) is REFUSED unless the adapter also names the native field its
    decided proposition is read from. The declaration is refused at import time, so an adapter that
    emits pass/fail alone never reaches the registry; the guard it installs is the backstop, so a
    field that is declared but left empty is refused at projection time instead of grading a
    boolean as though it were a finding.

    The class does NOT change grading. `claim_tuple.grade()` still decides, and no verifier ladder
    exists -- project, never grade (spec §4.7).
    """
    if source_class not in SOURCE_CLASSES:
        raise ProjectionError(
            f"projection {name!r}: unknown source_class {source_class!r}; declare one of "
            f"{sorted(SOURCE_CLASSES)} deliberately -- a new class of warrant is never an accident")
    if source_class == VERIFIER_CLASS and not (decided_proposition_field or "").strip():
        raise ProjectionError(
            f"projection {name!r} registers as verifier-class without naming the native field its "
            "decided proposition comes from: a verifier adapter that emits pass/fail alone is "
            "refused. Pass decided_proposition_field=<field on the native record> and project it "
            "into ClaimTuple.decided_proposition")
    if source_class != VERIFIER_CLASS and decided_proposition_field:
        raise ProjectionError(
            f"projection {name!r}: decided_proposition_field belongs to the verifier class only; "
            f"{source_class!r} records a measurement, not a decided proposition")

    def deco(fn: Projection) -> Projection:
        existing = _ORIGINALS.get(name)
        if existing is not None and existing is not fn:
            raise ProjectionError(f"projection {name!r} is already registered")
        _ORIGINALS[name] = fn
        _SOURCE_CLASS[name] = source_class
        _REGISTRY[name] = (
            _verifier_guard(name, fn, decided_proposition_field or "")
            if source_class == VERIFIER_CLASS
            else fn
        )
        return _REGISTRY[name]

    return deco


def registered() -> dict[str, Projection]:
    return dict(_REGISTRY)


def source_classes() -> dict[str, str]:
    """Projection name -> declared adapter class. Reported, so the contract is observable."""
    return dict(_SOURCE_CLASS)


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
    # SC57: the decided proposition rides in the CLAIM frame, next to the claim text it is meant to
    # be read against -- that adjacency is the whole point, and it is what SC56 would later bind.
    # Added only when the projection carried one, so a measurement-class tuple emits the identical
    # frame (and therefore the identical frame_id) it emitted before this field existed.
    claim_assertion = {"claim_id": claim_id, "display_text": tup.claim, "source_id": source_id}
    if tup.decided_proposition:
        claim_assertion["decided_proposition"] = tup.decided_proposition
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
            assertion=claim_assertion,
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
