"""R2b — certificates for the absence classes the pilot can actually prove.

Spec: docs/design/vidya-pilot-spec.md §11.2; research note
`research/deep-dives/vidya-r1-r2-stratified-negation.md` §3.

**The scope discipline is the whole point.** "We looked and found nothing" is not a certificate,
and neither is a query returning zero rows. This module implements only the two absence classes
that are provable from an authenticated ledger, and it refuses the third rather than approximating
it:

    KEY_NON_MEMBERSHIP    provable  -- no frame exists with this canonical key
    SCAN_COMPLETENESS     provable  -- this declared scan boundary was covered in full
    DERIVED_EMPTINESS     REFUSED   -- "no rule can produce X" needs the stratified-negation
                                       machinery that R1 leaves unresolved, and negating a least
                                       fixed point is a safety game whose explanation does not run
                                       backwards (1907.08470 p.18)

Every certificate names the exact domain it covers. An absence certificate over the wrong domain is
worse than none, because it converts "we did not find it" into "it is not there".
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from canonical import content_hash  # noqa: E402

__all__ = ["AbsenceClass", "AbsenceCertificate", "certify_key_absence",
           "certify_scan_completeness", "AbsenceRefused"]


class AbsenceClass:
    KEY_NON_MEMBERSHIP = "key-non-membership"
    SCAN_COMPLETENESS = "scan-completeness"
    DERIVED_EMPTINESS = "derived-emptiness"   # refused; see module docstring

    PROVABLE = frozenset({KEY_NON_MEMBERSHIP, SCAN_COMPLETENESS})


class AbsenceRefused(Exception):
    """An absence was requested that this pilot cannot prove."""


@dataclass
class AbsenceCertificate:
    absence_class: str
    domain: str                        # the EXACT scope covered -- never implicit
    subject: str
    frontier: int
    as_of: str
    checkpoint_root: str | None = None
    covered_keys: int = 0
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        body = {
            "_type": "epyc.vidya/absence-certificate/v1",
            "absence_class": self.absence_class,
            "domain": self.domain,
            "subject": self.subject,
            "frontier": self.frontier,
            "as_of": self.as_of,
            "checkpoint_root": self.checkpoint_root,
            "covered_keys": self.covered_keys,
            "reasons": self.reasons,
            "proves": (
                f"that no frame satisfying the subject exists within the domain '{self.domain}' "
                f"at frontier {self.frontier} -- and NOTHING about anything outside that domain, "
                "nor about what a rule might derive"
            ),
        }
        body["certificate_hash"] = content_hash(body)
        return body


def _key_of(frame: dict, key_field: str) -> str | None:
    for section in ("assertion", "provenance", "pubinfo"):
        value = frame.get(section, {}).get(key_field)
        if isinstance(value, str):
            return value
    return None


def certify_key_absence(
    frames: Sequence[dict],
    *,
    key_field: str,
    key_value: str,
    domain: str,
    as_of: str,
    checkpoint_root: str | None = None,
) -> AbsenceCertificate:
    """Certify that no frame in the ledger carries ``key_field == key_value``.

    This is provable because the ledger is authenticated and totally enumerated: absence over a
    fully scanned, hash-chained set is a statement about a closed domain. Bind it to a checkpoint
    root where one exists, so the certificate names the exact history it scanned rather than
    "the ledger as it was when somebody looked".
    """
    hits = [f.get("frame_id") for f in frames if _key_of(f, key_field) == key_value]
    if hits:
        raise AbsenceRefused(
            f"cannot certify absence: {len(hits)} frame(s) carry {key_field}={key_value!r} "
            f"(first: {hits[0]})"
        )
    covered = sum(1 for f in frames if _key_of(f, key_field) is not None)
    return AbsenceCertificate(
        absence_class=AbsenceClass.KEY_NON_MEMBERSHIP,
        domain=domain,
        subject=f"{key_field}={key_value}",
        frontier=len(frames),
        as_of=as_of,
        checkpoint_root=checkpoint_root,
        covered_keys=covered,
        reasons=[
            f"scanned all {len(frames)} frames at this frontier; {covered} carry a {key_field}",
            "the ledger is hash-chained and totally enumerated, so this domain is closed",
        ],
    )


def certify_scan_completeness(
    frames: Sequence[dict],
    *,
    expected_sources: Iterable[str],
    domain: str,
    as_of: str,
    checkpoint_root: str | None = None,
) -> AbsenceCertificate:
    """Certify that every declared source in a scan boundary produced at least one frame.

    Refuses when a declared source is missing, because a scan with an unexplained gap cannot
    support a completeness claim -- and reporting it as complete is exactly how a missing adapter
    becomes an assertion that nothing was there.
    """
    expected = sorted(set(expected_sources))
    seen = {
        sid for f in frames
        if isinstance(sid := f.get("assertion", {}).get("source_id"), str)
    }
    missing = [s for s in expected if s not in seen]
    if missing:
        raise AbsenceRefused(
            f"cannot certify scan completeness: {len(missing)} declared source(s) produced no "
            f"frame ({missing[:5]}{'...' if len(missing) > 5 else ''}). A gap in the scan is not "
            "evidence that the gap is empty."
        )
    return AbsenceCertificate(
        absence_class=AbsenceClass.SCAN_COMPLETENESS,
        domain=domain,
        subject=f"{len(expected)} declared sources",
        frontier=len(frames),
        as_of=as_of,
        checkpoint_root=checkpoint_root,
        covered_keys=len(expected),
        reasons=[f"all {len(expected)} declared sources produced at least one frame"],
    )


def certify_derived_emptiness(*_args, **_kwargs):
    """Always refuses. Kept as a named function so the refusal is discoverable rather than absent.

    "No rule can produce X" requires provenance through stratified negation, which R1 leaves
    unresolved, and negating a least fixed point is a safety game whose explanatory machinery does
    not run backwards. A plausible implementation here would be the most dangerous code in the
    repository: an unprovable absence that looks like a proof.
    """
    raise AbsenceRefused(
        "derived emptiness is not provable by this pilot (R1 unresolved; see "
        "research/deep-dives/vidya-r1-r2-stratified-negation.md §3.3). Use a key-non-membership "
        "or scan-completeness certificate scoped to an authenticated domain instead."
    )
