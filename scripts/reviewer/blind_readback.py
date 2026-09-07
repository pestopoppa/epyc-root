"""RA-13 — blind read-back: the auditor brief, its record format, and its write-time meter.

WHAT THIS IS. A reviewer that knows what a change was *supposed* to do tends to confirm that
expectation rather than read what is actually there. The countermeasure is to hand an auditing
sub-agent the **artifact only** — a diff, a gate script, or a handoff row — plus a read-back spec,
and nothing else. It emits a literal DESCRIPTION of what the artifact does and asserts. A human
compares that description against the original ask. The auditor never sees the ask, so it cannot
accidentally agree with it.

THREE PROPERTIES ARE LOAD-BEARING (handoffs/active/reviewer-typed-artifacts.md § RA-13). Remove any
one and this degenerates into decomposition-by-ROLE, which project doctrine ratified *against*
(`OPERATING_CONSTRAINTS.md` -> *Parallel Subagent Fan-Out*, *When NOT to fan out*):

  (i)   **No authority is transferred.** The auditor describes; a human adjudicates. Encoded here as
        an absence: `ReadBackRecord` has no pass/fail/approve/score/verdict field, the description
        sections are a closed whitelist that contains no such section, and `authority_bearing_names`
        exists so a test can prove the absence rather than assert it by eye.
  (ii)  **The split is an information WHITELIST over the same task**, not a skill or work-stage
        boundary. That is what makes it information-hiding instead of role decomposition. Encoded as
        `BRIEF_FIELD_WHITELIST` / `ARTIFACT_FIELD_WHITELIST`: `build_brief` accepts a mapping and
        refuses **any** key it does not positively name. A blacklist of forbidden fields would be
        unauditable — you cannot enumerate every name an author might give their intent — while a
        whitelist is readable in one line and refuses `intent`, `task_statement`, `request`,
        `why_we_are_doing_this` and every name nobody thought of, identically.
  (iii) **Blinding is re-established with a fresh context on every artifact revision**, so the
        auditor cannot be progressively contaminated across iterations. Encoded in
        `ContextManifest`: `fresh_context` must be true, `context_revision` must equal the revision
        of the artifact actually shown, and `prior_revisions_in_context` must be empty.

CITATION BOUND, NON-NEGOTIABLE. The source record for this mechanism (`intake-1308#record`,
`intake-1299#record`) is citable for **mechanism and rationale only**: its repository contains no
efficacy measurement of any kind — no hit rate, no caught-error count, no false-agreement rate, no
A/B against unblinded self-review. RA-13b exists because of that gap, and **RA-13b gates RA-13a's
citability**: `citable_summary` refuses to emit below `CITATION_THRESHOLD_N` runs and always states
its denominator. Adopting an unmeasured control and then citing it would reproduce exactly the
warrant inflation this plane exists to prevent, so the refusal is a raised error, never a flag.

WHAT RA-13c CLOSES. The source stores only the judge's model NAME. A captain who skipped the
blinding entirely therefore produces a byte-identical record — the artifact is indistinguishable
from the evidence. So a record here is not evidence unless it carries all four of: judge model id,
spec version, a hash of the **exact artifact text shown**, and a context manifest attesting the
blinding actually held. Missing any one is a `RecordValidationError`, not a warning: a warning is
a record that still gets counted.

The pilot (N=20 completed edits) needs live model calls and is a separate, operator-gated task. This
module is the harness, the record format and the meter only; it runs no inference.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Default home for emitted records. Nothing is written until a run actually happens.
RECORD_DIR = REPO_ROOT / "artifacts" / "reviewer" / "blind-readback"

READBACK_SPEC_VERSION = "1.0.0"

#: The read-back authoring rules, lifted from RA-13a. They are given to the auditor VERBATIM and
#: hashed, so a record can prove which rules the description was produced under. Note that no rule
#: here refers to intent, a task, a request, or an author: the spec must be safe to show a blinded
#: reader, or the spec itself would break the blinding.
SPEC_TEXT = """\
You are given one artifact and nothing else. You do not know why it was written, who asked for it,
or what it was supposed to achieve. Do not guess, and do not ask.

Produce a literal read-back: describe what the artifact DOES and what it ASSERTS.

1. Account for EVERY binder and precondition. Omitting one is the worst failure mode of a read-back:
   a condition you drop is a condition the reader will assume you checked.
2. EXPAND non-standard names rather than restating them. If the artifact defines or relies on a name
   whose meaning is not standard, say what it stands for in the artifact's own terms.
3. Surface degenerate cases and any condition that could be satisfied VACUOUSLY — an empty input, a
   check that cannot fail, a branch that is unreachable.
4. Say only what the artifact says. If the artifact says less than it appears to promise, your
   read-back must say less. Do not supply what seems to be missing.

Emit a description. Do NOT emit a verdict, a score, an approval, a rejection, or a recommendation.
Whether this artifact is correct or wanted is not yours to decide and not answerable from what you
have been given.
"""

# --- the whitelist (property ii) ------------------------------------------------------------

#: Everything the auditor sub-agent is given. Positive, closed, and short enough to audit by eye.
BRIEF_FIELD_WHITELIST: tuple[str, ...] = ("artifact", "spec")

#: Everything an artifact may carry into the brief. `kind` and `revision_id` are metadata about the
#: text, never about the ask; there is deliberately no slot for a title, a description, a ticket, a
#: rationale, or an author.
ARTIFACT_FIELD_WHITELIST: tuple[str, ...] = ("kind", "text", "revision_id")

ARTIFACT_KINDS: tuple[str, ...] = ("diff", "gate_script", "handoff_row")

#: The closed set of description sections. There is no verdict section, and no section may be added
#: at runtime; `validate_description` refuses anything else.
DESCRIPTION_SECTION_WHITELIST: tuple[str, ...] = (
    "summary",
    "assertions",
    "binders",
    "preconditions",
    "expanded_names",
    "degenerate_cases",
    "vacuous_satisfaction_risks",
    "unstated_in_artifact",
)

#: Name segments that would signal authority transfer (property i). Used to PROVE the absence, in a
#: form a test can also mutate to show the check is not vacuous.
AUTHORITY_TOKENS: frozenset[str] = frozenset(
    {
        "verdict", "approve", "approved", "approval", "reject", "rejected", "pass", "passed",
        "fail", "failed", "score", "decision", "decide", "recommend", "recommendation",
        "blocking", "accept", "accepted", "ok", "grade", "rating",
    }
)

# --- RA-13b ---------------------------------------------------------------------------------

#: No read-back result may be cited as evidence below this many valid runs, with a stated
#: denominator (RA-13b). This is a hard floor on citability, not a quality heuristic.
CITATION_THRESHOLD_N = 20


class BlindingViolation(ValueError):
    """The caller tried to put something in the auditor's context that is not on the whitelist."""


class RecordValidationError(ValueError):
    """A read-back record is missing something RA-13c requires, so it is not evidence."""


class NotCitableError(RuntimeError):
    """Fewer valid runs than RA-13b's floor; there is nothing citable to emit."""


def sha256_text(text: str) -> str:
    """Hash of the exact bytes shown. UTF-8, no normalisation — a whitespace edit is a new artifact."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def authority_bearing_names(names: Iterable[str]) -> tuple[str, ...]:
    """Names that would give the auditor a verdict slot (property i).

    Segment-wise, so `artifact_sha256` is clean while `overall_score` is not; substring matching
    would flag `passed_binders` for the wrong reason and miss `verdict2`.
    """
    offending = []
    for name in names:
        segments = [seg for seg in name.replace("-", "_").lower().split("_") if seg]
        if any(seg in AUTHORITY_TOKENS for seg in segments):
            offending.append(name)
    return tuple(offending)


def _require_nonempty_str(value: Any, label: str, exc: type[Exception]) -> None:
    if not isinstance(value, str) or not value.strip():
        raise exc(f"{label} must be a non-empty string (got {value!r})")


# --- artifact + spec ------------------------------------------------------------------------


@dataclass(frozen=True)
class Artifact:
    """The one thing the auditor sees. Three fields, all on `ARTIFACT_FIELD_WHITELIST`."""

    kind: str
    text: str
    revision_id: str

    def __post_init__(self) -> None:
        if self.kind not in ARTIFACT_KINDS:
            raise BlindingViolation(
                f"artifact kind {self.kind!r} is not one of {ARTIFACT_KINDS}"
            )
        _require_nonempty_str(self.text, "artifact text", BlindingViolation)
        _require_nonempty_str(self.revision_id, "artifact revision_id", BlindingViolation)

    @property
    def sha256(self) -> str:
        return sha256_text(self.text)

    @classmethod
    def from_fields(cls, fields: Mapping[str, Any]) -> "Artifact":
        """Build from a mapping, refusing every key not positively whitelisted.

        Takes a mapping rather than `**kwargs` on purpose: a caller assembling artifact metadata
        programmatically hits the whitelist instead of silently splatting a dict that happens to
        carry `intent` or `ticket_summary`.
        """
        _refuse_unwhitelisted(fields, ARTIFACT_FIELD_WHITELIST, "artifact")
        missing = [k for k in ARTIFACT_FIELD_WHITELIST if k not in fields]
        if missing:
            raise BlindingViolation(f"artifact is missing required fields: {missing}")
        return cls(kind=fields["kind"], text=fields["text"], revision_id=fields["revision_id"])


@dataclass(frozen=True)
class ReadBackSpec:
    """The instructions given alongside the artifact. Versioned and hashed."""

    version: str = READBACK_SPEC_VERSION
    text: str = SPEC_TEXT

    def __post_init__(self) -> None:
        _require_nonempty_str(self.version, "spec version", BlindingViolation)
        _require_nonempty_str(self.text, "spec text", BlindingViolation)

    @property
    def sha256(self) -> str:
        return sha256_text(self.text)


def _refuse_unwhitelisted(fields: Mapping[str, Any], whitelist: Sequence[str], what: str) -> None:
    extras = [k for k in fields if k not in whitelist]
    if extras:
        raise BlindingViolation(
            f"{what} whitelist refuses {sorted(extras)}; the auditor is given ONLY "
            f"{list(whitelist)}. This is a positive whitelist: a field is refused because it is "
            f"not named, not because it was recognised as intent-bearing."
        )


# --- the brief (RA-13a) ---------------------------------------------------------------------

BRIEF_SPEC_HEADER = "=== READ-BACK SPEC ==="
BRIEF_ARTIFACT_HEADER = "=== ARTIFACT ==="
BRIEF_ARTIFACT_END = "=== END ARTIFACT ==="


@dataclass(frozen=True)
class AuditorBrief:
    """Exactly what goes into the auditor's context: an artifact and a spec. Nothing else.

    The type has two fields, so there is no slot to smuggle intent through, and `render` is a total
    function of those two — a test pins its output byte-for-byte, which fails the moment anything
    else is interpolated.
    """

    artifact: Artifact
    spec: ReadBackSpec

    def render(self) -> str:
        return (
            f"{BRIEF_SPEC_HEADER}\n"
            f"{self.spec.text}\n"
            f"{BRIEF_ARTIFACT_HEADER} (kind: {self.artifact.kind})\n"
            f"{self.artifact.text}\n"
            f"{BRIEF_ARTIFACT_END}\n"
        )

    @property
    def sha256(self) -> str:
        return sha256_text(self.render())

    @property
    def fields_supplied(self) -> tuple[str, ...]:
        return BRIEF_FIELD_WHITELIST

    def context_manifest(self) -> "ContextManifest":
        """The attestation that goes into the record — computed FROM the brief, never asserted."""
        return ContextManifest(
            brief_sha256=self.sha256,
            artifact_sha256=self.artifact.sha256,
            spec_sha256=self.spec.sha256,
            fields_supplied=self.fields_supplied,
            context_revision=self.artifact.revision_id,
            fresh_context=True,
            prior_revisions_in_context=(),
        )


def build_brief(fields: Mapping[str, Any]) -> AuditorBrief:
    """The only supported way to assemble an auditor brief.

    `fields` must carry exactly `artifact` and `spec`. Any other key — `intent`, `task`,
    `request`, `author_notes`, or a name nobody has thought of — is refused by the whitelist.
    """
    if not isinstance(fields, Mapping):
        raise BlindingViolation("build_brief takes a mapping of whitelisted fields")
    _refuse_unwhitelisted(fields, BRIEF_FIELD_WHITELIST, "brief")
    if "artifact" not in fields:
        raise BlindingViolation("brief requires an 'artifact'")
    artifact = fields["artifact"]
    if isinstance(artifact, Mapping):
        artifact = Artifact.from_fields(artifact)
    if not isinstance(artifact, Artifact):
        raise BlindingViolation("brief 'artifact' must be an Artifact or a whitelisted mapping")
    spec = fields.get("spec") or ReadBackSpec()
    if not isinstance(spec, ReadBackSpec):
        raise BlindingViolation("brief 'spec' must be a ReadBackSpec")
    return AuditorBrief(artifact=artifact, spec=spec)


# --- the record (RA-13c) --------------------------------------------------------------------


@dataclass(frozen=True)
class ContextManifest:
    """Attests that the blinding held — and is checkable, which is the whole point.

    The source stores the model name and nothing else, so a run with no blinding at all yields a
    byte-identical record. Here the manifest pins the hash of the exact rendered brief, so a record
    can be re-derived from the brief (`verify_brief_binding`) and a contaminated context produces a
    different hash. `fields_supplied` must equal the whitelist exactly: a manifest that ADMITS an
    extra field is refused rather than accepted with a caveat.
    """

    brief_sha256: str
    artifact_sha256: str
    spec_sha256: str
    fields_supplied: tuple[str, ...]
    context_revision: str
    fresh_context: bool
    prior_revisions_in_context: tuple[str, ...] = ()

    def validate(self, *, artifact_revision: str | None = None) -> None:
        for label in ("brief_sha256", "artifact_sha256", "spec_sha256"):
            value = getattr(self, label)
            _require_nonempty_str(value, f"context_manifest.{label}", RecordValidationError)
            if len(value) != 64:
                raise RecordValidationError(
                    f"context_manifest.{label} is not a sha256 hex digest: {value!r}"
                )
        supplied = tuple(self.fields_supplied)
        if sorted(supplied) != sorted(BRIEF_FIELD_WHITELIST):
            raise RecordValidationError(
                f"context_manifest.fields_supplied={list(supplied)} does not match the brief "
                f"whitelist {list(BRIEF_FIELD_WHITELIST)}; the blinding did not hold, so this "
                f"record is not evidence"
            )
        if not self.fresh_context:
            raise RecordValidationError(
                "context_manifest.fresh_context is false; blinding must be re-established with a "
                "fresh context on every artifact revision (RA-13 property iii)"
            )
        if tuple(self.prior_revisions_in_context):
            raise RecordValidationError(
                f"context carried prior revisions {list(self.prior_revisions_in_context)}; a "
                f"progressively contaminated auditor is not blinded"
            )
        _require_nonempty_str(
            self.context_revision, "context_manifest.context_revision", RecordValidationError
        )
        if artifact_revision is not None and self.context_revision != artifact_revision:
            raise RecordValidationError(
                f"context_manifest.context_revision={self.context_revision!r} is stale against "
                f"artifact revision {artifact_revision!r}"
            )

    def as_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["fields_supplied"] = list(self.fields_supplied)
        d["prior_revisions_in_context"] = list(self.prior_revisions_in_context)
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ContextManifest":
        missing = [
            k
            for k in ("brief_sha256", "artifact_sha256", "spec_sha256", "fields_supplied",
                      "context_revision", "fresh_context")
            if k not in d
        ]
        if missing:
            raise RecordValidationError(f"context_manifest is missing {missing}")
        return cls(
            brief_sha256=d["brief_sha256"],
            artifact_sha256=d["artifact_sha256"],
            spec_sha256=d["spec_sha256"],
            fields_supplied=tuple(d["fields_supplied"]),
            context_revision=d["context_revision"],
            fresh_context=bool(d["fresh_context"]),
            prior_revisions_in_context=tuple(d.get("prior_revisions_in_context", ())),
        )


@dataclass(frozen=True)
class RunInstrumentation:
    """RA-13b, written when the HUMAN adjudicates the read-back against the original ask.

    `adjudicator` is required because property (i) is what makes this legal at all: the description
    carries no authority, so a run with no human comparer produced no result. The three counts must
    partition the denominator — every adjudicated statement is exactly one of caught, false, or
    agreement — which is what stops an undercounted denominator from inflating a rate.
    """

    adjudicator: str
    denominator: int
    caught_discrepancies: int
    false_discrepancies: int
    agreements_with_author: int

    def validate(self) -> None:
        _require_nonempty_str(
            self.adjudicator, "instrumentation.adjudicator", RecordValidationError
        )
        counts = {
            "denominator": self.denominator,
            "caught_discrepancies": self.caught_discrepancies,
            "false_discrepancies": self.false_discrepancies,
            "agreements_with_author": self.agreements_with_author,
        }
        for label, value in counts.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise RecordValidationError(
                    f"instrumentation.{label} must be a non-negative int (got {value!r})"
                )
        if self.denominator == 0:
            raise RecordValidationError(
                "instrumentation.denominator is 0; a rate with no denominator is not a measurement"
            )
        total = (
            self.caught_discrepancies
            + self.false_discrepancies
            + self.agreements_with_author
        )
        if total != self.denominator:
            raise RecordValidationError(
                f"instrumentation counts do not partition the denominator: "
                f"{self.caught_discrepancies}+{self.false_discrepancies}+"
                f"{self.agreements_with_author}={total} != {self.denominator}"
            )

    @property
    def agreement_rate(self) -> float:
        return self.agreements_with_author / self.denominator

    def as_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["agreement_rate"] = self.agreement_rate
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RunInstrumentation":
        missing = [
            k
            for k in ("adjudicator", "denominator", "caught_discrepancies",
                      "false_discrepancies", "agreements_with_author")
            if k not in d
        ]
        if missing:
            raise RecordValidationError(f"instrumentation is missing {missing}")
        return cls(
            adjudicator=d["adjudicator"],
            denominator=d["denominator"],
            caught_discrepancies=d["caught_discrepancies"],
            false_discrepancies=d["false_discrepancies"],
            agreements_with_author=d["agreements_with_author"],
        )


def validate_description(description: Any) -> None:
    """The auditor's output is a DESCRIPTION, never a verdict.

    Sections are a closed whitelist, so `verdict`, `approved`, `score` and every other authority
    slot is refused on the way in — including on a record deserialised from JSON, which is the path
    an over-helpful auditor's extra key would actually arrive by.
    """
    if not isinstance(description, Mapping) or not description:
        raise RecordValidationError("description must be a non-empty mapping of sections")
    extras = [k for k in description if k not in DESCRIPTION_SECTION_WHITELIST]
    if extras:
        raise RecordValidationError(
            f"description sections {sorted(extras)} are not on the whitelist "
            f"{list(DESCRIPTION_SECTION_WHITELIST)}; the auditor describes, a human adjudicates "
            f"(RA-13 property i)"
        )
    if "summary" not in description:
        raise RecordValidationError("description requires a 'summary' section")
    for key, value in description.items():
        if isinstance(value, str):
            if not value.strip():
                raise RecordValidationError(f"description.{key} is empty")
        elif isinstance(value, (list, tuple)):
            if any(not isinstance(item, str) for item in value):
                raise RecordValidationError(f"description.{key} must hold strings")
        else:
            raise RecordValidationError(
                f"description.{key} must be a string or a list of strings (got {type(value).__name__})"
            )


#: Pinned so that adding ANY field to the record — a verdict field above all — fails a test.
RECORD_FIELDS: tuple[str, ...] = (
    "record_id",
    "judge_model_id",
    "spec_version",
    "artifact_sha256",
    "artifact_kind",
    "artifact_revision",
    "context_manifest",
    "description",
    "instrumentation",
    "created_utc",
)

#: The four RA-13c requirements, named so a validation error can point at the missing one.
RA13C_REQUIRED_FIELDS: tuple[str, ...] = (
    "judge_model_id",
    "spec_version",
    "artifact_sha256",
    "context_manifest",
)


@dataclass(frozen=True)
class ReadBackRecord:
    """One blind read-back run.

    There is deliberately no pass/fail/approve/score/verdict field anywhere in this type or in the
    description it carries. `tests/reviewer/test_blind_readback.py` pins `RECORD_FIELDS` and scans
    every field name for authority tokens, so adding one fails a test.
    """

    record_id: str
    judge_model_id: str
    spec_version: str
    artifact_sha256: str
    artifact_kind: str
    artifact_revision: str
    context_manifest: ContextManifest
    description: dict
    instrumentation: RunInstrumentation
    created_utc: str

    def as_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "judge_model_id": self.judge_model_id,
            "spec_version": self.spec_version,
            "artifact_sha256": self.artifact_sha256,
            "artifact_kind": self.artifact_kind,
            "artifact_revision": self.artifact_revision,
            "context_manifest": self.context_manifest.as_dict(),
            "description": dict(self.description),
            "instrumentation": self.instrumentation.as_dict(),
            "created_utc": self.created_utc,
        }


def build_record(
    *,
    record_id: str,
    judge_model_id: str,
    brief: AuditorBrief,
    description: Mapping[str, Any],
    instrumentation: RunInstrumentation,
    context_manifest: ContextManifest | None = None,
    created_utc: str | None = None,
) -> ReadBackRecord:
    """Assemble a record from the brief that was actually rendered.

    The artifact hash and the manifest are DERIVED from the brief rather than passed in, so the
    common path cannot claim a blinding it did not perform. `context_manifest` is overridable only
    so a caller can attest a real contamination (which `validate_record` will then refuse).
    """
    record = ReadBackRecord(
        record_id=record_id,
        judge_model_id=judge_model_id,
        spec_version=brief.spec.version,
        artifact_sha256=brief.artifact.sha256,
        artifact_kind=brief.artifact.kind,
        artifact_revision=brief.artifact.revision_id,
        context_manifest=context_manifest or brief.context_manifest(),
        description=dict(description),
        instrumentation=instrumentation,
        created_utc=created_utc or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    validate_record(record)
    return record


def validate_record(record: ReadBackRecord) -> None:
    """Refuse a record that RA-13c does not accept as evidence. Raises; never warns.

    A warning here would be a record that still gets counted, which is the defect being closed:
    the whole reason the manifest exists is that a run with no blinding must be REFUSED, not
    flagged.
    """
    if not isinstance(record, ReadBackRecord):
        raise RecordValidationError(f"not a ReadBackRecord: {type(record).__name__}")

    missing = []
    for name in RA13C_REQUIRED_FIELDS:
        value = getattr(record, name, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(name)
    if missing:
        raise RecordValidationError(
            f"record is missing RA-13c required field(s) {missing}; a record lacking judge model "
            f"id, spec version, artifact hash, or context manifest is NOT evidence"
        )

    for name in ("record_id", "artifact_kind", "artifact_revision", "created_utc"):
        _require_nonempty_str(getattr(record, name, None), f"record.{name}", RecordValidationError)
    if record.artifact_kind not in ARTIFACT_KINDS:
        raise RecordValidationError(f"record.artifact_kind {record.artifact_kind!r} is unknown")
    if len(record.artifact_sha256) != 64:
        raise RecordValidationError(
            f"record.artifact_sha256 is not a sha256 hex digest: {record.artifact_sha256!r}"
        )

    if not isinstance(record.context_manifest, ContextManifest):
        raise RecordValidationError("record.context_manifest must be a ContextManifest")
    record.context_manifest.validate(artifact_revision=record.artifact_revision)
    if record.context_manifest.artifact_sha256 != record.artifact_sha256:
        raise RecordValidationError(
            "record.artifact_sha256 disagrees with the context manifest; the record does not "
            "describe the text that was shown"
        )

    validate_description(record.description)

    if not isinstance(record.instrumentation, RunInstrumentation):
        raise RecordValidationError("record.instrumentation must be a RunInstrumentation")
    record.instrumentation.validate()


def record_from_dict(d: Mapping[str, Any]) -> ReadBackRecord:
    """Deserialise and validate. Unknown top-level keys are refused, verdicts included."""
    if not isinstance(d, Mapping):
        raise RecordValidationError("record must be a mapping")
    extras = [k for k in d if k not in RECORD_FIELDS]
    if extras:
        raise RecordValidationError(
            f"record carries fields outside the pinned set: {sorted(extras)}"
        )
    missing = [k for k in RA13C_REQUIRED_FIELDS if k not in d]
    if missing:
        raise RecordValidationError(
            f"record is missing RA-13c required field(s) {missing}; a record lacking judge model "
            f"id, spec version, artifact hash, or context manifest is NOT evidence"
        )
    record = ReadBackRecord(
        record_id=d.get("record_id", ""),
        judge_model_id=d.get("judge_model_id", ""),
        spec_version=d.get("spec_version", ""),
        artifact_sha256=d.get("artifact_sha256", ""),
        artifact_kind=d.get("artifact_kind", ""),
        artifact_revision=d.get("artifact_revision", ""),
        context_manifest=ContextManifest.from_dict(d["context_manifest"]),
        description=dict(d.get("description") or {}),
        instrumentation=RunInstrumentation.from_dict(d.get("instrumentation") or {}),
        created_utc=d.get("created_utc", ""),
    )
    validate_record(record)
    return record


def verify_brief_binding(record: ReadBackRecord, brief: AuditorBrief) -> None:
    """Re-derive the hashes from the brief the auditor was actually given.

    This is what makes the manifest an attestation rather than a claim: a record produced against a
    different artifact, a different spec, or a context that carried anything extra cannot survive
    re-derivation.
    """
    validate_record(record)
    if record.artifact_sha256 != brief.artifact.sha256:
        raise RecordValidationError(
            "artifact hash mismatch: the record does not describe this brief's artifact"
        )
    if record.context_manifest.brief_sha256 != brief.sha256:
        raise RecordValidationError(
            "brief hash mismatch: the context shown was not this brief"
        )
    if record.context_manifest.spec_sha256 != brief.spec.sha256:
        raise RecordValidationError("spec hash mismatch: a different read-back spec was used")
    if record.spec_version != brief.spec.version:
        raise RecordValidationError("spec version mismatch against the brief")


def write_record(record: ReadBackRecord, root: Path | None = None) -> Path:
    """Persist one validated record. Write-time, per run — RA-13b cannot be retrofitted."""
    validate_record(record)
    root = Path(root) if root is not None else RECORD_DIR
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{record.record_id}.json"
    path.write_text(json.dumps(record.as_dict(), indent=2, sort_keys=True) + "\n")
    return path


def load_records(root: Path) -> list[ReadBackRecord]:
    """Load every valid record under `root`. Invalid records are skipped, never repaired."""
    records = []
    for path in sorted(Path(root).glob("*.json")):
        try:
            records.append(record_from_dict(json.loads(path.read_text())))
        except (RecordValidationError, json.JSONDecodeError):
            continue
    return records


# --- RA-13b: the meter ----------------------------------------------------------------------


@dataclass(frozen=True)
class CitableSummary:
    """A summary that may be cited as evidence — which is why it always states its denominator."""

    n_runs: int
    denominator: int
    caught_discrepancies: int
    false_discrepancies: int
    agreements_with_author: int
    threshold_n: int = CITATION_THRESHOLD_N
    citable: bool = True

    @property
    def agreement_rate(self) -> float:
        return self.agreements_with_author / self.denominator

    @property
    def caught_rate(self) -> float:
        return self.caught_discrepancies / self.denominator

    @property
    def false_discrepancy_rate(self) -> float:
        return self.false_discrepancies / self.denominator

    def as_dict(self) -> dict:
        return {
            "citable": True,
            "n_runs": self.n_runs,
            "denominator": self.denominator,
            "caught_discrepancies": self.caught_discrepancies,
            "false_discrepancies": self.false_discrepancies,
            "agreements_with_author": self.agreements_with_author,
            "agreement_rate": self.agreement_rate,
            "caught_rate": self.caught_rate,
            "false_discrepancy_rate": self.false_discrepancy_rate,
            "threshold_n": self.threshold_n,
            "denominator_statement": (
                f"n={self.n_runs} read-back runs over {self.denominator} adjudicated statements"
            ),
        }


def _tally(records: Sequence[ReadBackRecord]) -> tuple[list[ReadBackRecord], dict]:
    valid = []
    totals = {"denominator": 0, "caught": 0, "false": 0, "agree": 0}
    for record in records:
        try:
            validate_record(record)
        except RecordValidationError:
            continue  # not evidence, so it does not count toward n
        valid.append(record)
        inst = record.instrumentation
        totals["denominator"] += inst.denominator
        totals["caught"] += inst.caught_discrepancies
        totals["false"] += inst.false_discrepancies
        totals["agree"] += inst.agreements_with_author
    return valid, totals


def citable_summary(records: Sequence[ReadBackRecord]) -> CitableSummary:
    """Emit a citable read-back summary, or refuse.

    RA-13b, non-negotiable: no read-back result may be cited as evidence until n>=20 with a stated
    denominator. Below that this raises `NotCitableError` rather than returning a caveated number,
    because a caveated number is what gets cited. Records that fail RA-13c validation are not
    evidence and do not count toward n.
    """
    valid, totals = _tally(records)
    n = len(valid)
    if n < CITATION_THRESHOLD_N:
        raise NotCitableError(
            f"not citable: n={n} valid read-back runs (denominator={totals['denominator']} "
            f"adjudicated statements), below the RA-13b floor of n>={CITATION_THRESHOLD_N}. No "
            f"read-back result may be cited as evidence until n>={CITATION_THRESHOLD_N} with a "
            f"stated denominator. The source (intake-1308#record) carries no efficacy measurement "
            f"of any kind, so there is nothing to fall back on."
        )
    return CitableSummary(
        n_runs=n,
        denominator=totals["denominator"],
        caught_discrepancies=totals["caught"],
        false_discrepancies=totals["false"],
        agreements_with_author=totals["agree"],
    )


def provisional_summary(records: Sequence[ReadBackRecord]) -> dict:
    """Counts below the floor, marked `citable: False` and carrying the reason.

    This exists so progress is visible during the pilot without inventing a citable number. It is
    a dict, not a `CitableSummary`, so the two cannot be confused by a consumer.
    """
    valid, totals = _tally(records)
    n = len(valid)
    return {
        "citable": False,
        "n_runs": n,
        "threshold_n": CITATION_THRESHOLD_N,
        "denominator": totals["denominator"],
        "caught_discrepancies": totals["caught"],
        "false_discrepancies": totals["false"],
        "agreements_with_author": totals["agree"],
        "reason": (
            f"n={n} < {CITATION_THRESHOLD_N}; RA-13b forbids citing this as evidence"
            if n < CITATION_THRESHOLD_N
            else "at or above the floor; call citable_summary() for a citable result"
        ),
    }


# --- CLI ------------------------------------------------------------------------------------


def _cmd_brief(args: argparse.Namespace) -> int:
    text = Path(args.artifact_file).read_text()
    brief = build_brief(
        {
            "artifact": {"kind": args.kind, "text": text, "revision_id": args.revision},
            "spec": ReadBackSpec(),
        }
    )
    if args.json:
        print(
            json.dumps(
                {
                    "brief_text": brief.render(),
                    "brief_sha256": brief.sha256,
                    "artifact_sha256": brief.artifact.sha256,
                    "spec_version": brief.spec.version,
                    "fields_supplied": list(brief.fields_supplied),
                    "context_manifest": brief.context_manifest().as_dict(),
                },
                indent=2,
            )
        )
    else:
        sys.stdout.write(brief.render())
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        record = record_from_dict(json.loads(Path(args.record).read_text()))
    except RecordValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(f"VALID: {record.record_id} (judge={record.judge_model_id}, spec={record.spec_version})")
    return 0


def _cmd_summarize(args: argparse.Namespace) -> int:
    records = load_records(Path(args.records_dir))
    try:
        summary = citable_summary(records)
    except NotCitableError as exc:
        print(json.dumps(provisional_summary(records), indent=2))
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(summary.as_dict(), indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="blind_readback",
        description="RA-13 blind read-back: build auditor briefs, validate records, meter runs.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_brief = sub.add_parser("brief", help="render the auditor brief (artifact + spec, nothing else)")
    p_brief.add_argument("--artifact-file", required=True)
    p_brief.add_argument("--kind", required=True, choices=list(ARTIFACT_KINDS))
    p_brief.add_argument("--revision", required=True, help="artifact revision id; fresh context per revision")
    p_brief.add_argument("--json", action="store_true")
    p_brief.set_defaults(func=_cmd_brief)

    p_val = sub.add_parser("validate", help="validate one record against RA-13c")
    p_val.add_argument("--record", required=True)
    p_val.set_defaults(func=_cmd_validate)

    p_sum = sub.add_parser("summarize", help="emit a citable summary, or refuse below n>=20")
    p_sum.add_argument("--records-dir", default=str(RECORD_DIR))
    p_sum.set_defaults(func=_cmd_summarize)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
