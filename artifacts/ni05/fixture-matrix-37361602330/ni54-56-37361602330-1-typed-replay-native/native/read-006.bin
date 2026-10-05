"""Frame envelope construction and validation.

Spec: docs/design/vidya-pilot-spec.md §3.

The envelope is the nanopublication decomposition rendered in JSON rather than three named RDF
graphs, and the two lint rules are adopted verbatim because they are what keep the parts from
collapsing into each other:

* every ``provenance`` field must reference the assertion -- provenance may not smuggle in new
  world-claims;
* ``pubinfo`` may speak only of the frame -- never of the world.

The second rule is the reason ``triggered_by`` lives in ``pubinfo``: "why this frame was emitted"
is a statement about the frame. It carries no grade, no authority and no freshness, and
`validate_frame` enforces that a caller has not tried to attach one.

``supersedes_reason`` (SC59) lives there for exactly the same reason and under exactly the same
prohibition: "this frame replaced that one because the recipe changed" is a statement about the
frame, it is free text for a human, and it moves no lattice value. A retraction states its own
reason in its ``assertion`` instead, because a retraction is a first-class claim frame whose
assertion IS the retraction (spec §3.5) -- so the reason is part of what it asserts, not a note
about it.
"""

from __future__ import annotations

import re
from typing import Any

from canonical import CanonicalizationError, canonical_bytes, envelope_hash

__all__ = [
    "FrameValidationError",
    "make_frame",
    "validate_frame",
    "FRAME_TYPE_RE",
]

# frame_type is a versioned URI-shaped string -- the in-toto predicateType discipline. The trailing
# /vN is required so that a schema change is visible in the data instead of inferred.
FRAME_TYPE_RE = re.compile(r"^epyc\.vidya/frame/[a-z0-9_]+/v\d+$")

# What the fold's `_digest_of` parses out of a subject digest mapping: sha256 over 64 hex digits,
# case-insensitive and normalized on read. The envelope accepts exactly that set, so a digest the
# fold would silently drop is refused here instead (SC72).
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

_REQUIRED_TOP = ("frame_type", "assertion", "provenance", "pubinfo")
_ALLOWED_TOP = set(_REQUIRED_TOP) | {"subjects", "frame_id", "signatures"}

_REQUIRED_PUBINFO = ("actor", "authority_scope", "created_at")

# Fields that would give a trigger evidential weight. Named explicitly so the prohibition is
# mechanical rather than a comment somebody has to remember.
_GRADE_BEARING = {"grade", "Q", "T", "support", "derived_from", "evidence"}


class FrameValidationError(ValueError):
    """A frame does not satisfy the envelope contract."""


def _fail(msg: str) -> None:
    raise FrameValidationError(msg)


def validate_frame(frame: dict) -> None:
    """Raise `FrameValidationError` unless the envelope satisfies §3.

    Deliberately strict about unknown top-level keys: an envelope is a trust boundary, and a typo'd
    key that is silently preserved is a key that silently does nothing.
    """
    if not isinstance(frame, dict):
        _fail("frame must be a mapping")

    for key in _REQUIRED_TOP:
        if key not in frame:
            _fail(f"missing required top-level key {key!r}")

    unknown = set(frame) - _ALLOWED_TOP
    if unknown:
        _fail(f"unknown top-level keys: {sorted(unknown)}")

    ftype = frame["frame_type"]
    if not isinstance(ftype, str) or not FRAME_TYPE_RE.match(ftype):
        _fail(
            f"frame_type must match {FRAME_TYPE_RE.pattern!r} "
            f"(versioned URI, e.g. 'epyc.vidya/frame/claim_proposed/v1'); got {ftype!r}"
        )

    for part in ("assertion", "provenance", "pubinfo"):
        if not isinstance(frame[part], dict):
            _fail(f"{part} must be a mapping")

    pubinfo = frame["pubinfo"]
    for key in _REQUIRED_PUBINFO:
        if key not in pubinfo:
            _fail(f"pubinfo missing required key {key!r}")

    # Lint rule 1: provenance must reference the assertion.
    provenance = frame["provenance"]
    if not provenance:
        _fail("provenance must not be empty -- it must say how the assertion came to be")
    references_assertion = any(
        k in provenance
        for k in ("derived_from", "evidence", "anchor", "method", "produced_by", "about")
    )
    if not references_assertion:
        _fail(
            "provenance must reference the assertion (one of: derived_from, evidence, anchor, "
            "method, produced_by, about) -- provenance may not introduce new world-claims"
        )

    # Lint rule 2: pubinfo speaks only of the frame.
    if "triggered_by" in pubinfo:
        trig = pubinfo["triggered_by"]
        if not isinstance(trig, str):
            _fail("pubinfo.triggered_by must be a frame_id string")
    if "supersedes" in pubinfo and not isinstance(pubinfo["supersedes"], str):
        _fail("pubinfo.supersedes must be a frame_id string")
    # SC59: WHY the ground moved. "This frame replaced that one, because ..." is a statement about
    # the frame, so it belongs in pubinfo beside `supersedes` -- and it carries no grade, for the
    # same reason a correction carries none: we know the ground shifted, not by how much. A reason
    # with nothing to be the reason FOR is refused, because a dangling explanation reads as an
    # explanation of the whole frame.
    if "supersedes_reason" in pubinfo:
        reason = pubinfo["supersedes_reason"]
        if not isinstance(reason, str) or not reason.strip():
            _fail("pubinfo.supersedes_reason must be a non-empty string")
        if "supersedes" not in pubinfo:
            _fail("pubinfo.supersedes_reason without pubinfo.supersedes: a reason must say what "
                  "it is the reason for")
    for key in _GRADE_BEARING:
        if key in pubinfo:
            _fail(
                f"pubinfo must not carry {key!r}: pubinfo speaks only about the frame, and a "
                "triggered frame inherits nothing -- not grade, not authority, not freshness"
            )

    subjects = frame.get("subjects")
    if subjects is not None:
        if not isinstance(subjects, list):
            _fail("subjects must be a list")
        for i, subj in enumerate(subjects):
            if not isinstance(subj, dict) or "name" not in subj or "digest" not in subj:
                _fail(f"subjects[{i}] must be a mapping with 'name' and 'digest'")
            if not isinstance(subj["name"], str) or not subj["name"].strip():
                _fail(f"subjects[{i}].name must be a non-empty string -- a digest with no name "
                      "is pinned but anonymous, and a move in an anonymous artifact is "
                      "undetectable")
            digest = subj["digest"]
            if not isinstance(digest, dict) or not digest:
                _fail(f"subjects[{i}].digest must be a non-empty {{algorithm: hex}} mapping")
            # SC72: presence is not well-formedness. A digest-shaped string that is not a digest
            # ({"sha256": "aa"}) used to pass the envelope and was silently dropped by the fold's
            # parser -- the SC69 defect one layer down. The envelope accepts exactly what the
            # fold's `_digest_of` parses: one entry, algorithm sha256, 64 hex digits.
            if len(digest) != 1:
                _fail(f"subjects[{i}].digest must name exactly one algorithm, got "
                      f"{sorted(digest)}")
            (alg, hexdigest), = digest.items()
            if not isinstance(alg, str) or alg.strip().lower() != "sha256":
                _fail(f"subjects[{i}].digest algorithm must be 'sha256' (got {alg!r}) -- the "
                      "fold tracks sha256 digests only, and a digest the fold cannot parse is "
                      "dropped silently")
            if not isinstance(hexdigest, str) or not _SHA256_HEX_RE.match(
                    hexdigest.strip().lower()):
                _fail(f"subjects[{i}].digest sha256 must be 64 hex digits, got {hexdigest!r}")

    sigs = frame.get("signatures")
    if sigs is not None and not isinstance(sigs, list):
        _fail("signatures must be a list (reserved; detached, added later)")

    # Canonicalizability is part of validity: a frame that cannot be hashed deterministically has
    # no identity, so the float ban is enforced here rather than at write time.
    try:
        canonical_bytes({k: v for k, v in frame.items() if k not in ("frame_id", "signatures")})
    except CanonicalizationError as exc:
        _fail(str(exc))

    if "frame_id" in frame:
        expected = envelope_hash(frame)
        if frame["frame_id"] != expected:
            _fail(
                f"frame_id does not match content: declared {frame['frame_id']}, computed {expected}"
            )


def make_frame(
    *,
    frame_type: str,
    assertion: dict,
    provenance: dict,
    actor: str,
    authority_scope: str,
    created_at: str,
    subjects: list[dict] | None = None,
    triggered_by: str | None = None,
    supersedes: str | None = None,
    supersedes_reason: str | None = None,
    extra_pubinfo: dict[str, Any] | None = None,
) -> dict:
    """Build a validated, content-addressed frame.

    `created_at` is an explicit argument rather than a clock read: the fold is a pure function of
    its inputs, and a module that reaches for the wall clock is the easiest way to lose that.
    """
    pubinfo: dict[str, Any] = {
        "actor": actor,
        "authority_scope": authority_scope,
        "created_at": created_at,
    }
    if triggered_by is not None:
        pubinfo["triggered_by"] = triggered_by
    if supersedes is not None:
        pubinfo["supersedes"] = supersedes
    if supersedes_reason is not None:
        pubinfo["supersedes_reason"] = supersedes_reason
    if extra_pubinfo:
        overlap = set(extra_pubinfo) & set(pubinfo)
        if overlap:
            raise FrameValidationError(f"extra_pubinfo would overwrite {sorted(overlap)}")
        pubinfo.update(extra_pubinfo)

    frame: dict[str, Any] = {
        "frame_type": frame_type,
        "assertion": assertion,
        "provenance": provenance,
        "pubinfo": pubinfo,
    }
    if subjects:
        frame["subjects"] = subjects

    validate_frame(frame)
    frame["frame_id"] = envelope_hash(frame)
    frame["signatures"] = []
    return frame
