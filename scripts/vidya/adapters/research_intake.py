"""Research-intake adapter: intake_index.yaml -> Vidya frames.

Spec: docs/design/vidya-pilot-spec.md §4.5 (status-to-grade mapping, ratified 2026-08-09).
Program: handoffs/active/vidya-belief-substrate-program.md §P2.

READ-ONLY with respect to the index. This adapter never writes to `research/intake_index.yaml`;
it reads it and emits frames into the Vidya ledger, which lives under `.vidya/`.

**What this adapter is, and what it deliberately is not.** The high-fidelity path is instrumenting
the intake skill's writes so frames are emitted *at write time*, with the anchor the author
actually had in hand. This is the retrofit: it parses records written for humans, and the ceiling
that imposes is the interesting output, not a limitation to work around.

Concretely, the retrofit cannot reach `T2 Anchored`. An index entry identifies a *document* (url,
arxiv_id, sometimes a retrieval date or commit) but carries no span anchor for any individual
claim -- `key_claims` are prose sentences with no byte range, heading path, or content hash tying
them to a location in the source. So every claim this adapter emits tops out at `T1 Located`, and
a policy that asks for `Verified/Anchored` will not be satisfied by *any* retrofitted entry, no
matter how thoroughly it was dived.

That is a measurement, and it is the one P2 exists to produce: it prices the difference between
instrumenting writes and parsing prose, in the currency the policy layer actually uses.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from frames import make_frame  # noqa: E402
from lattice import Grade, parse_grade  # noqa: E402

__all__ = ["ingest_intake_index", "grade_for_entry", "ADAPTER_ID"]

ADAPTER_ID = "vidya.adapters.research_intake/v1"
AUTHORITY = "research-verification"

FT_SOURCE = "epyc.vidya/frame/source_observed/v1"
FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"
FT_SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"
FT_OPPOSE = "epyc.vidya/frame/evidence_opposes_claim/v1"
FT_CORRECTION = "epyc.vidya/frame/correction_recorded/v1"


def _anchors_by_claim(entry: dict) -> dict[int, dict]:
    """Index an entry's `claim_anchors` by the claim they anchor (P2b)."""
    out: dict[int, dict] = {}
    for anchor in entry.get("claim_anchors") or []:
        if isinstance(anchor, dict) and isinstance(anchor.get("claim_index"), int):
            out[anchor["claim_index"]] = anchor
    return out


def _t_level(entry: dict, anchor: dict | None = None) -> str:
    """Traceability for a claim from this entry.

    Without a per-claim anchor the ceiling is `T1 Located`: an index entry names a document, not a
    location within it. `T0` is for an entry that identifies no retrievable document at all -- a
    `locator_note` explains *why* the material cannot be retrieved, which is honest but is still
    not a locator.

    With a `claim_anchors` entry (P2b) the claim reaches `Anchored`, and `Attested` when the
    anchor also pins the source revision it was read at AND carries a hash of the quoted span --
    the pair is what makes the anchor checkable later rather than merely specific.

    An anchor marked `located_by: machine` tops out at `MachineLocated` (spec §4.2 amendment,
    2026-08-10) however complete it is. Revision and quote hash make a machine anchor *checkable*;
    they do not make it *read*, and the level above records a person's judgment that the passage
    says what the claim says. Capping here rather than at the policy layer means a machine anchor
    cannot reach `Anchored` by being unusually well-formed.
    """
    if anchor:
        has_span = bool(anchor.get("quote") or anchor.get("locator"))
        if not has_span:
            pass
        elif anchor.get("located_by") == "machine":
            return "MachineLocated" if anchor.get("quote_sha256") else "Located"
        elif anchor.get("quote_sha256") and anchor.get("source_revision"):
            return "Attested"
        else:
            return "Anchored"
    if entry.get("url") or entry.get("arxiv_id"):
        return "Located"
    return "T0"


def _q_level(entry: dict) -> tuple[str, bool]:
    """Warrant quality from the verification lifecycle. Returns ``(Q level, is_opposition)``.

    Mapping per spec §4.5:
      stage1-unverified -> Hinted   (discovery only; cannot gate an integration plan)
      dive-verified     -> Verified (Stage-2 accepted against primary source)
      dive-overturned   -> Verified opposition (the dive established the claim is wrong)

    Nothing here reaches `Witnessed`: that requires a protocol-admissible measurement with durable
    attestation, and an intake entry is a literature record, not a measurement.
    """
    verification = entry.get("verification")
    if verification == "dive-verified":
        return "Verified", False
    if verification == "dive-overturned":
        return "Verified", True
    return "Hinted", False


def grade_for_entry(entry: dict, anchor: dict | None = None) -> tuple[Grade, bool]:
    """The (Q x T) grade a claim inherits, and whether it is opposition."""
    q, is_opposition = _q_level(entry)
    return parse_grade({"Q": q, "T": _t_level(entry, anchor)}), is_opposition


def _claim_id(entry_id: str, index: int) -> str:
    return f"clm_{entry_id.replace('-', '_')}_{index:02d}"


def _source_id(entry: dict) -> str:
    return f"src_{entry['id'].replace('-', '_')}"


def _frames_for_entry(entry: dict, as_of: str) -> list[dict]:
    """Build the frame set for one index entry: one source, N claims, N support/oppose edges."""
    out: list[dict] = []
    entry_id = entry["id"]
    src_id = _source_id(entry)
    # The revision the entry was true at, when it recorded one. The external-citation provenance
    # contract (2026-08-09) requires this; many older entries predate it, and their absence here is
    # itself worth surfacing rather than papering over with a default.
    revision = entry.get("ingested_date")

    out.append(
        make_frame(
            frame_type=FT_SOURCE,
            assertion={
                "source_id": src_id,
                "locator": entry.get("url"),
                "arxiv_id": entry.get("arxiv_id"),
                "source_kind": entry.get("source_type"),
                "title": entry.get("title"),
                "revision_observed": revision,
            },
            provenance={
                "method": ADAPTER_ID,
                "about": entry_id,
                "retrofit": True,
            },
            actor=ADAPTER_ID,
            authority_scope=AUTHORITY,
            created_at=as_of,
        )
    )

    claims = entry.get("key_claims") or []
    anchors = _anchors_by_claim(entry)
    for i, text in enumerate(claims):
        if not isinstance(text, str):
            continue
        cid = _claim_id(entry_id, i)
        anchor = anchors.get(i)
        grade, is_opposition = grade_for_entry(entry, anchor)
        out.append(
            make_frame(
                frame_type=FT_CLAIM,
                assertion={"claim_id": cid, "display_text": text, "source_id": src_id},
                provenance={"method": ADAPTER_ID, "derived_from": src_id, "about": entry_id},
                actor=ADAPTER_ID,
                authority_scope=AUTHORITY,
                created_at=as_of,
            )
        )
        if anchor:
            anchor_payload = {
                "kind": anchor.get("kind", "unspecified"),
                "locator": anchor.get("locator"),
                "quote_sha256": anchor.get("quote_sha256"),
                "source_revision": anchor.get("source_revision"),
                "verified_by": anchor.get("verified_by"),
            }
        else:
            # An absent anchor is recorded explicitly. Inferring it from a low grade would make the
            # two indistinguishable from "anchored but weakly verified", which is a different thing.
            anchor_payload = {
                "kind": "document-level",
                "span": None,
                "reason": "index entry carries no per-claim span anchor",
            }
        out.append(
            make_frame(
                frame_type=FT_OPPOSE if is_opposition else FT_SUPPORT,
                assertion={
                    "claim_id": cid,
                    "evidence_id": f"evd_{cid}",
                    "grade": grade.as_dict(),
                    "source_id": src_id,
                },
                provenance={
                    "method": ADAPTER_ID,
                    "derived_from": src_id,
                    "anchor": anchor_payload,
                    "verification_status": entry.get("verification", "stage1-unverified"),
                },
                actor=ADAPTER_ID,
                authority_scope=AUTHORITY,
                created_at=as_of,
            )
        )

    # P2c -- corrections. A `dive_corrections` field means a dive CHANGED something about this
    # entry. Which claims, and how, is prose; this adapter deliberately does NOT try to parse that.
    # Keyword-scanning for "OVERTURNED"/"CORRECTED" would be deterministic and plausible and
    # sometimes wrong, which is precisely the failure mode the substrate exists to prevent.
    #
    # What it records instead is checkable and useful: a correction EXISTS, here is its verbatim
    # text, and these are the claims from the entry it may bear on. The fold turns that into a
    # review-required marker on those beliefs -- a freshness signal, not a grade change. Deciding
    # what the correction actually did to each claim is a dive's job, and this frame is the thing
    # that stops that job from being silently skipped.
    correction = entry.get("dive_corrections")
    if isinstance(correction, str) and correction.strip():
        out.append(
            make_frame(
                frame_type=FT_CORRECTION,
                assertion={
                    "entry_id": entry_id,
                    "claim_ids": [
                        _claim_id(entry_id, i)
                        for i, c in enumerate(claims)
                        if isinstance(c, str)
                    ],
                    "correction_text": correction.strip(),
                    "classification": None,
                },
                provenance={
                    "method": ADAPTER_ID,
                    "about": entry_id,
                    "derived_from": src_id,
                    "parsed": False,
                    "note": (
                        "verbatim dive_corrections text; semantic effect on individual claims is "
                        "NOT parsed and must be established by review"
                    ),
                },
                actor=ADAPTER_ID,
                authority_scope=AUTHORITY,
                created_at=as_of,
            )
        )

    return out


def ingest_intake_index(
    ledger,
    *,
    index_path: Path,
    as_of: str,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Emit frames for intake entries. Returns a report; appends unless `dry_run`."""
    with open(index_path) as fh:
        entries = yaml.safe_load(fh) or []
    if not isinstance(entries, list):
        raise ValueError(f"{index_path}: expected a list of entries")
    if limit is not None:
        entries = entries[:limit]

    # Frames are content-addressed, so re-ingesting an UNCHANGED entry produces byte-identical
    # frames with identical ids. Skipping ids already in the ledger makes re-ingest incremental and
    # keeps the ledger append-only across runs -- which matters because a rebuilt ledger silently
    # invalidates every prior checkpoint, making a legitimate regeneration indistinguishable from
    # tampering. Append-only across re-ingests keeps that distinction sharp.
    existing_ids = {
        rec.frame.get("frame_id") for rec in ledger.read_all() if isinstance(rec.frame, dict)
    }
    skipped = 0

    grade_counts: Counter[str] = Counter()
    verification_counts: Counter[str] = Counter()
    anchored_claims = 0
    corrections_emitted = 0
    emitted = 0
    claims_total = 0
    no_revision = 0

    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        # Count per CLAIM, not per entry: anchors are per-claim, so an entry-level grade would
        # hide the very effect this adapter exists to measure.
        anchors = _anchors_by_claim(entry)
        n_claims = 0
        for i, c in enumerate(entry.get("key_claims") or []):
            if not isinstance(c, str):
                continue
            n_claims += 1
            grade, is_opposition = grade_for_entry(entry, anchors.get(i))
            grade_counts[f"{grade}{' (opposition)' if is_opposition else ''}"] += 1
        claims_total += n_claims
        verification_counts[entry.get("verification", "<unset>")] += 1
        if not entry.get("ingested_date"):
            no_revision += 1

        anchored_claims += sum(1 for i in range(n_claims) if i in anchors)
        if isinstance(entry.get("dive_corrections"), str) and entry["dive_corrections"].strip():
            corrections_emitted += 1
        for frame in _frames_for_entry(entry, as_of):
            if frame.get("frame_id") in existing_ids:
                skipped += 1
                continue
            emitted += 1
            if not dry_run:
                ledger.append(frame)
                existing_ids.add(frame["frame_id"])

    return {
        "adapter": ADAPTER_ID,
        "index_path": str(index_path),
        "as_of": as_of,
        "dry_run": dry_run,
        "entries_read": len(entries),
        "claims_seen": claims_total,
        "frames_emitted": emitted,
        "frames_skipped_already_present": skipped,
        "grade_distribution": dict(grade_counts.most_common()),
        "anchored_claims": anchored_claims,
        "correction_frames": corrections_emitted,
        "verification_distribution": dict(verification_counts.most_common()),
        "entries_without_revision": no_revision,
        "ceiling_note": (
            "Claims without a `claim_anchors` record top out at T1 Located: an index entry names a "
            "document, not a span within it, so no amount of diving raises the T axis on its own. "
            "Claims WITH an anchor reach T2 Anchored, or T3 Attested when the anchor also pins the "
            "source revision and a hash of the quoted span. This is the measured price of "
            "recording the anchor at dive time versus reconstructing it later."
        ),
    }
