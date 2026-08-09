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


def _t_level(entry: dict) -> str:
    """Traceability ceiling for a retrofitted index entry.

    `T2 Anchored` requires an exact durable span. An index entry has none -- it names a document,
    not a location within it -- so the ceiling here is `T1 Located`, and `T0` is for an entry that
    does not even identify a retrievable document.
    """
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


def grade_for_entry(entry: dict) -> tuple[Grade, bool]:
    """The (Q x T) grade an entry's claims inherit, and whether it is opposition."""
    q, is_opposition = _q_level(entry)
    return parse_grade({"Q": q, "T": _t_level(entry)}), is_opposition


def _claim_id(entry_id: str, index: int) -> str:
    return f"clm_{entry_id.replace('-', '_')}_{index:02d}"


def _source_id(entry: dict) -> str:
    return f"src_{entry['id'].replace('-', '_')}"


def _frames_for_entry(entry: dict, as_of: str) -> list[dict]:
    """Build the frame set for one index entry: one source, N claims, N support/oppose edges."""
    out: list[dict] = []
    entry_id = entry["id"]
    src_id = _source_id(entry)
    grade, is_opposition = grade_for_entry(entry)

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
    for i, text in enumerate(claims):
        if not isinstance(text, str):
            continue
        cid = _claim_id(entry_id, i)
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
                    # No span anchor exists to record. Saying so explicitly is the point: an
                    # absent anchor must be visible in the data, not inferred from a low grade.
                    "anchor": {"kind": "document-level", "span": None, "reason":
                               "index entries carry no per-claim span anchor"},
                    "verification_status": entry.get("verification", "stage1-unverified"),
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

    grade_counts: Counter[str] = Counter()
    verification_counts: Counter[str] = Counter()
    emitted = 0
    claims_total = 0
    no_revision = 0

    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        grade, is_opposition = grade_for_entry(entry)
        n_claims = sum(1 for c in (entry.get("key_claims") or []) if isinstance(c, str))
        claims_total += n_claims
        grade_counts[f"{grade}{' (opposition)' if is_opposition else ''}"] += n_claims
        verification_counts[entry.get("verification", "<unset>")] += 1
        if not entry.get("ingested_date"):
            no_revision += 1

        for frame in _frames_for_entry(entry, as_of):
            emitted += 1
            if not dry_run:
                ledger.append(frame)

    return {
        "adapter": ADAPTER_ID,
        "index_path": str(index_path),
        "as_of": as_of,
        "dry_run": dry_run,
        "entries_read": len(entries),
        "claims_seen": claims_total,
        "frames_emitted": emitted,
        "grade_distribution": dict(grade_counts.most_common()),
        "verification_distribution": dict(verification_counts.most_common()),
        "entries_without_revision": no_revision,
        "ceiling_note": (
            "T2 Anchored is unreachable by retrofit: index entries identify a document, not a "
            "span within it. A conjunctive policy requiring Verified/Anchored is satisfied by "
            "ZERO retrofitted claims, however thoroughly dived. Instrumenting the intake skill's "
            "writes is what raises the T axis."
        ),
    }
