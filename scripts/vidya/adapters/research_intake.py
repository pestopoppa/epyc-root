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

from intake_assertion_kinds import validate_assertion_kinds as _validated_assertion_kinds  # noqa: E402
from machine_anchor import verify_source_anchor  # noqa: E402
from claim_tuple import register_ladder  # noqa: E402
from frames import make_frame  # noqa: E402
from lattice import Grade, Q_LEVELS, parse_grade  # noqa: E402

__all__ = ["ingest_intake_index", "emit_read_depth_correction", "emit_warrant_withdrawal",
           "grade_for_entry", "ADAPTER_ID"]

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


def _t_level(
    entry: dict,
    anchor: dict | None = None,
    source_verification: tuple[bool, str] | None = None,
    claim: str | None = None,
) -> str:
    """Traceability for a claim from this entry.

    Without a per-claim anchor the ceiling is `T1 Located`: an index entry names a document, not a
    location within it. `T0` is for an entry that identifies no retrievable document at all -- a
    `locator_note` explains *why* the material cannot be retrieved, which is honest but is still
    not a locator.

    With a `claim_anchors` entry (P2b), the source-bound raw artifact must be available and
    re-verifiable before the quoted span raises traceability above document-level `Located`.
    A missing or invalid original is reported as unknown and cannot gain warrant from its own
    quote/hash/source-revision fields.

    A source-verified anchor marked `located_by: machine` tops out at `MachineLocated` (spec §4.2
    amendment, 2026-08-10) however complete it is. Re-finding and hashing its quote proves the
    source span, not that the span says what the claim says; a numeric mismatch is refused using
    the existing source-span magnitude check, while broader semantic judgment still requires a
    person. Capping here rather than at the policy layer means a machine anchor cannot reach
    `Anchored` by being unusually well-formed.
    """
    if anchor:
        has_span = bool(anchor.get("quote") or anchor.get("locator"))
        if not has_span:
            pass
        else:
            valid, _status = source_verification or verify_source_anchor(
                anchor, entry_url=entry.get("url"), claim=claim)
            if not valid:
                return "Located" if entry.get("url") or entry.get("arxiv_id") else "T0"
            if anchor.get("located_by") == "machine":
                return "MachineLocated"
            if anchor.get("quote_sha256") and anchor.get("source_revision"):
                return "Attested"
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


@register_ladder("literature", "scripts/vidya/adapters/research_intake.py")
def grade_for_entry(
    entry: dict,
    anchor: dict | None = None,
    source_verification: tuple[bool, str] | None = None,
    claim: str | None = None,
) -> tuple[Grade, bool]:
    """The (Q x T) grade a claim inherits, and whether it is opposition.

    THE ladder for the `literature` source class, declared as such so the conformance test can
    tell a legitimate second class apart from an accidental second dialect of the measurement rule
    — which is what `measurement_record` and `sealed_manifest` had become by 2026-08-10.
    """
    q, is_opposition = _q_level(entry)
    return parse_grade({"Q": q, "T": _t_level(entry, anchor, source_verification, claim)}), is_opposition


def _claim_id(entry_id: str, index: int) -> str:
    return f"clm_{entry_id.replace('-', '_')}_{index:02d}"


def _source_id(entry: dict) -> str:
    return f"src_{entry['id'].replace('-', '_')}"


def _drop_nulls(value):
    """Strip null-valued keys, recursively. See `_dedup_key`."""
    if isinstance(value, dict):
        return {k: _drop_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_nulls(v) for v in value]
    return value


def _dedup_key(frame: dict) -> str:
    """Identity of what a frame ASSERTS, ignoring when it was written.

    Re-ingest has to be idempotent: the index is re-read routinely and a fresh `--as-of` must not
    mint a second copy of every claim. Content addressing is still what identifies a frame in the
    ledger; this is only the adapter's "have I already said this?" test.

    **Nulls are dropped before hashing, and that is the whole point of `_drop_nulls`.** Adding an
    optional assertion field changes this key for every frame that does not populate it, so a purely
    additive schema change re-emits the entire corpus. It already happened: `per_claim_effects` is
    computed as `{...} or None`, so every correction on an entry without per-claim verdicts started
    carrying an explicit null, and re-ingest minted a second copy of each. Measured on the live
    ledger 2026-08-10: **485 correction frames carrying 155 distinct corrections.**

    That is not cosmetic. `fold` blocks a claim while ANY unreviewed correction names it, and each
    copy is a separate frame_id needing its own `correction_reviewed`, so every re-ingest quietly
    raised the cost of clearing a claim. `{"a": 1}` and `{"a": 1, "b": None}` assert the same thing;
    this makes the dedup test agree.
    """
    from canonical import content_hash  # noqa: PLC0415

    return content_hash({
        "frame_type": frame.get("frame_type"),
        "assertion": _drop_nulls(frame.get("assertion")),
    })


#: The per-claim verdict vocabulary, defined ONCE here because `_frames_for_entry` below is what
#: gives each value its meaning. `correction_queue` writes these values and imports this set rather
#: than restating it -- a reviewer worksheet offering an `effect` this adapter does not recognise
#: would silently fall through to "narrowed / reattributed" and quietly un-oppose a refuted claim.
CORRECTION_EFFECTS = ("overturned", "narrowed", "reattributed", "unaffected", "uncertain")


def apply_claim_verdict(grade: Grade, is_opposition: bool, per_claim: dict | None
                        ) -> tuple[Grade, bool]:
    """Fold a per-claim `claim_corrections` verdict into the entry-level grade.

    **A per-claim `overturned` is dive-established, so it carries dive warrant.** The entry-level
    path already knows this: `verification: dive-overturned` maps to *Verified* opposition. The
    per-claim path used to flip only the DIRECTION and inherit the entry's Q, so on an entry with no
    entry-level verdict a refutation was recorded at `Hinted` — the same grade as the stage-1 support
    it refutes — and the fold reported the claim `conflicted` rather than overturned.

    intake-110 claim 4 was the live instance and the only conflicted claim in 4,233 beliefs: it is
    the only entry in the corpus carrying a per-claim overturn without an entry-level one. The
    substance is not in dispute — the authors revised the "+9-16 points" figure away themselves — so
    "conflicted" was the adapter mis-recording settled history as a live disagreement.

    **`uncertain` keeps the entry-level verdict — a chosen default, not an inherited one (SC16,
    decided 2026-08-26).** `clm_intake_922_01` is the live instance: entry 922 carries a
    dive-overturned entry-level verdict with `effect: uncertain` on claim 01, and the fold reports
    `pro=Q0/T0 con=Verified/MachineLocated` — the dive's inability to decide about the claim is
    recorded as the entry-level refutation, never as a weaker one. The alternative, clearing the
    claim's opposition on `uncertain`, was considered and rejected: it would conflate "could not
    tell" with "found fine", and on an overturned entry it would silently un-refute claims whose own
    entry the dive rejected — the absence-of-evidence category error this adapter exists to prevent.
    The failure mode of keeping is a true statement about the entry; the failure mode of clearing
    would be a verdict the dive never gave. `unaffected`, `narrowed` and `reattributed` remain the
    affirmative clearances; `uncertain` is deliberately not one of them.

    Used by BOTH the emitter and the run report, because those two drifted apart once before (the
    report claimed 112 opposition while the adapter emitted 106).
    """
    if not per_claim:
        return grade, is_opposition
    effect = per_claim.get("effect")
    if effect == "overturned":
        # max on the ORDINAL: never downgrade an entry-level dive-overturned, and never move T --
        # a dive establishes warrant quality, not where the span is.
        return Grade(q=max(Q_LEVELS.index("Verified"), grade.q), t=grade.t), True
    if effect == "uncertain":
        return grade, is_opposition      # a reader could not tell: keep the entry-level verdict
    return grade, False                  # unaffected / narrowed / reattributed: review, not refutation


def _claim_corrections(entry: dict) -> dict[int, dict]:
    """Per-claim correction verdicts, indexed by claim. Empty when the dive recorded none."""
    out: dict[int, dict] = {}
    for rec in entry.get("claim_corrections") or []:
        if isinstance(rec, dict) and isinstance(rec.get("claim_index"), int):
            out[rec["claim_index"]] = rec
    return out


def _frames_for_entry(entry: dict, as_of: str) -> list[dict]:
    """Build the frame set for one index entry: one source, N claims, N support/oppose edges."""
    assertion_kinds = _validated_assertion_kinds(entry)
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
    claim_verdicts = _claim_corrections(entry)
    for i, text in enumerate(claims):
        if not isinstance(text, str):
            continue
        cid = _claim_id(entry_id, i)
        kind = assertion_kinds.get(i, {}).get("kind", "source_claim")
        if kind == "record_status":
            binding = assertion_kinds[i]
            out.append(make_frame(
                frame_type=FT_CLAIM,
                assertion={"claim_id": cid, "display_text": text, "source_id": src_id,
                           "assertion_kind": "record_status"},
                provenance={"method": ADAPTER_ID, "derived_from": src_id, "about": entry_id,
                            "current_claim_text_sha256": binding["current_claim_text_sha256"],
                            "assertion_kind_reason": binding["reason"]},
                actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
            ))
            # A record status is displayed and addressable, but asserts no source finding.
            continue
        anchor = anchors.get(i)
        source_verification = (
            verify_source_anchor(anchor, entry_url=entry.get("url"), claim=text) if anchor else None
        )
        grade, is_opposition = grade_for_entry(entry, anchor, source_verification, claim=text)
        # A per-claim verdict overrides the entry-level one. Without it, `dive-overturned` opposes
        # EVERY claim of the entry -- measured 2026-08-10 as 114 claims across 27 entries, most of
        # which no dive ever disputed. intake-896 is the case that motivated it: four claims, one
        # fabricated, all four opposed.
        grade, is_opposition = apply_claim_verdict(grade, is_opposition, claim_verdicts.get(i))
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
                "source_verification": (
                    "verified" if source_verification and source_verification[0] else "unknown"
                ),
                **({"source_artifact": dict(anchor["source_artifact"])}
                   if isinstance(anchor.get("source_artifact"), dict) else {}),
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
                    # Only the claims a dive actually implicated. Falls back to every claim
                    # when no per-claim record exists, because blanket doubt is the honest default
                    # for an unindexed prose correction -- but it is now a fallback, not the rule.
                    "claim_ids": (
                        [_claim_id(entry_id, i) for i in sorted(claim_verdicts)
                         if claim_verdicts[i].get("effect") != "unaffected"]
                        if claim_verdicts else
                        [_claim_id(entry_id, i) for i, c in enumerate(claims)
                         if isinstance(c, str)]
                    ),
                    "per_claim_effects": (
                        {_claim_id(entry_id, i): claim_verdicts[i].get("effect")
                         for i in sorted(claim_verdicts)} or None
                    ),
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


def _depends_frames(entry: dict, as_of: str) -> list[dict]:
    """`depends_on` -> claim_depends_on frames.

    Kept separate from `cross_references`, which is related reading and NOT a dependency: 18% of
    citation edges are evidential (measured 2026-08-10 over 60 dived-source edges), so promoting
    them wholesale would create roughly 550 false dependencies. Only the explicit, human-authored
    edge reaches the ledger.
    """
    from frames import make_frame  # noqa: PLC0415

    out: list[dict] = []
    entry_id = entry["id"]
    for dep in entry.get("depends_on") or []:
        if not isinstance(dep, dict):
            continue
        target = dep.get("entry")
        why = str(dep.get("why") or "").strip()
        if not isinstance(target, str) or not why:
            continue
        ci = dep.get("claim_index")
        dependents = (
            [_claim_id(entry_id, ci)]
            if isinstance(ci, int)
            else [_claim_id(entry_id, i) for i in range(len(entry.get("key_claims") or []))]
        )
        for cid in dependents:
            out.append(
                make_frame(
                    frame_type="epyc.vidya/frame/claim_depends_on/v1",
                    assertion={
                        "claim_id": cid,
                        "depends_on_source": _source_id({"id": target}),
                        "depends_on_entry": target,
                        "rationale": why,
                    },
                    provenance={
                        "about": cid,
                        "method": "research-intake/stage2-depends-on",
                        "authored_by": "human",
                    },
                    actor=ADAPTER_ID,
                    authority_scope="research-verification",
                    created_at=as_of,
                )
            )
    return out


def emit_read_depth_correction(
    ledger, *, index_path: Path, target_manifest: dict[str, Any],
    expected_index_sha256: str, expected_manifest_sha256: str, as_of: str,
) -> dict[str, Any]:
    """Retract exact native Verified targets and emit stage1 Hinted replacements."""
    return _emit_warrant_correction(
        ledger, index_path=index_path, target_manifest=target_manifest,
        expected_index_sha256=expected_index_sha256,
        expected_manifest_sha256=expected_manifest_sha256, as_of=as_of,
        withdraw_only=False,
    )


def emit_warrant_withdrawal(
    ledger, *, index_path: Path, target_manifest: dict[str, Any],
    expected_index_sha256: str, expected_manifest_sha256: str, as_of: str,
) -> dict[str, Any]:
    """Withdraw exact reviewed native support/opposition, emitting no replacement evidence.

    The filtered corrected index may retain dive-verified status for supported
    siblings. Only manifest targets are withdrawn; no per-claim quality is invented.
    Each target requires an explicit frame_type, reviewed scope reason, and SHA-256
    bindings to old assertion JSON and the current claim text. Historical refutations
    stay in dated index history; withdrawal repairs the current stable slot's scope.
    Index bytes, full canonical manifest JSON and timestamp must stay frozen on retry.
    """
    return _emit_warrant_correction(
        ledger, index_path=index_path, target_manifest=target_manifest,
        expected_index_sha256=expected_index_sha256,
        expected_manifest_sha256=expected_manifest_sha256, as_of=as_of,
        withdraw_only=True,
    )


def _emit_warrant_correction(
    ledger,
    *,
    index_path: Path,
    target_manifest: dict[str, Any],
    expected_index_sha256: str,
    expected_manifest_sha256: str,
    as_of: str,
    withdraw_only: bool,
) -> dict[str, Any]:
    """Prepare a pinned native correction before any append; optionally replace support.

    The caller pins SHA-256 of index bytes and canonical JSON of the entire manifest
    (sorted keys, compact separators). Manifest ``targets`` rows name ``entry_id``,
    ``claim_id`` and ``old_support_frame_id``. Keep those inputs and ``as_of`` frozen
    for retry: exact event IDs resume a partially fsynced append sequence. Requires
    the ordinary single-writer ledger ownership; Ledger has no batch transaction.
    """
    import hashlib  # noqa: PLC0415
    import json  # noqa: PLC0415
    from datetime import datetime  # noqa: PLC0415

    from fold import FT_RETRACT, fold  # noqa: PLC0415
    from frames import validate_frame  # noqa: PLC0415
    from ledger import _refuse_future_stamp  # noqa: PLC0415

    stamp = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("correction timestamp must include a timezone")
    raw = index_path.read_bytes()
    index_digest = hashlib.sha256(raw).hexdigest()
    manifest_digest = hashlib.sha256(json.dumps(
        target_manifest, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    if index_digest != expected_index_sha256:
        raise ValueError("corrected index digest does not match reviewed digest")
    if manifest_digest != expected_manifest_sha256:
        raise ValueError("target manifest digest does not match reviewed digest")
    entries = yaml.safe_load(raw)
    if not isinstance(entries, list) or not entries:
        raise ValueError("correction index must be a nonempty filtered entry list")
    entries_by_id = {}
    for entry in entries:
        if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                or not entry["id"]):
            raise ValueError("all correction entries must be identified records")
        if not withdraw_only and entry.get("verification") != "stage1-unverified":
            raise ValueError("all demotion entries must be stage1-unverified records")
        if entry["id"] in entries_by_id:
            raise ValueError("duplicate correction entry")
        entries_by_id[entry["id"]] = entry
    targets = target_manifest.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("manifest must name a nonempty target list")

    # Prepare through the existing emitter, with no new interpretation of Q or T.
    native = {entry_id: _frames_for_entry(entry, as_of)
              for entry_id, entry in entries_by_id.items()}
    claims = {entry_id: {f["assertion"]["claim_id"]: f for f in frames
                        if f["frame_type"] == FT_CLAIM}
              for entry_id, frames in native.items()}
    supports = {entry_id: {f["assertion"]["claim_id"]: f for f in frames
                          if f["frame_type"] == FT_SUPPORT}
                for entry_id, frames in native.items()}
    frames = [r.frame for r in ledger.read_all() if isinstance(r.frame, dict)]
    by_id = {f.get("frame_id"): f for f in frames}
    state = fold(frames, as_of=as_of)
    retracted = {fid for belief in state.beliefs.values() for fid in belief.retracted_support}
    method = "warrant-withdrawal/v1" if withdraw_only else "read-depth-correction/v1"
    provenance = {
        "correction_method": ADAPTER_ID + "/" + method,
        "corrected_index_sha256": index_digest,
        "target_manifest_sha256": manifest_digest,
    }
    planned = []
    seen_targets = set()
    represented_entries = set()
    replacement_ids = set()
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("manifest target must be a mapping")
        entry_id = target.get("entry_id")
        cid = target.get("claim_id")
        fid = target.get("old_frame_id") or target.get("old_support_frame_id")
        target_type = target.get("frame_type") if withdraw_only else FT_SUPPORT
        if target_type not in ((FT_SUPPORT, FT_OPPOSE) if withdraw_only else (FT_SUPPORT,)):
            raise ValueError("withdrawal must explicitly name a native support/opposition direction")
        if not isinstance(fid, str) or not fid or fid in seen_targets:
            raise ValueError("manifest has a missing or duplicate target frame ID")
        seen_targets.add(fid)
        if entry_id not in entries_by_id or cid not in claims[entry_id]:
            raise ValueError("manifest claim does not belong to its filtered native entry")
        represented_entries.add(entry_id)
        old = by_id.get(fid)
        if old is None:
            raise ValueError(f"missing target frame: {fid}")
        validate_frame(old)
        assertion = old["assertion"]
        if (old["frame_type"] != target_type or assertion.get("claim_id") != cid
                or assertion.get("source_id") != _source_id(entries_by_id[entry_id])
                or old["pubinfo"].get("actor") != ADAPTER_ID
                or old["pubinfo"].get("authority_scope") != AUTHORITY
                or assertion.get("grade", {}).get("Q") != "Verified"):
            raise ValueError(f"target is not this entry's native Verified {target_type}: {fid}")
        for key, actual in (("actor", ADAPTER_ID), ("authority_scope", AUTHORITY),
                            ("frame_type", target_type)):
            if key in target and target[key] != actual:
                raise ValueError(f"manifest {key} does not match native target")
        scope_binding = {}
        if withdraw_only:
            reason = target.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("withdrawal requires a nonempty reviewed old/current scope reason")
            scope_binding = {
                "old_assertion_sha256": hashlib.sha256(json.dumps(
                    assertion, sort_keys=True, separators=(",", ":"), allow_nan=False,
                ).encode()).hexdigest(),
                "current_claim_text_sha256": hashlib.sha256(
                    claims[entry_id][cid]["assertion"]["display_text"].encode(),
                ).hexdigest(),
            }
            if any(target.get(k) != v for k, v in scope_binding.items()):
                raise ValueError("withdrawal old/current assertion scope binding does not match")
        replacement = supports[entry_id].get(cid)
        if not withdraw_only and (replacement is None or replacement["assertion"]["grade"]["Q"] != "Hinted"):
            raise ValueError("target claim does not emit corrected Hinted support")
        reason = (
            target["reason"] if withdraw_only else
            f"Read-depth warrant correction for {entry_id}: the available record does not "
            "establish sufficient relevant raw-source read scope for the prior dive-verified "
            "warrant; this does not assert the claim false."
        )
        event = make_frame(
            frame_type=FT_RETRACT,
            assertion={
                "retracts": fid,
                "reason": reason,
            },
            provenance={**provenance, **scope_binding, "method": ADAPTER_ID, "about": fid,
                        "claim_id": cid, "entry_id": entry_id,
                        "derived_from": assertion["source_id"]},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
        )
        if fid in retracted and by_id.get(event["frame_id"]) != event:
            raise ValueError("target already effectively retracted outside this frozen correction")
        if event["frame_id"] in by_id and fid not in retracted:
            raise ValueError("existing correction event is not effective under fold semantics")
        planned.append(event)
        if withdraw_only:
            continue
        # Carry source identity and ordinary anchor provenance on the native support.
        replacement = make_frame(
            frame_type=FT_SUPPORT, assertion=replacement["assertion"],
            provenance={**replacement["provenance"], **provenance, "entry_id": entry_id},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
        )
        if replacement["frame_id"] not in replacement_ids:
            replacement_ids.add(replacement["frame_id"])
            planned.append(replacement)
    if represented_entries != set(entries_by_id):
        raise ValueError("filtered entries must exactly match manifest entry coverage")
    targeted_directions = {(t["claim_id"], t["frame_type"] if withdraw_only else FT_SUPPORT)
                           for t in targets}
    for existing in frames:
        if ((existing.get("assertion", {}).get("claim_id"), existing.get("frame_type"))
                in targeted_directions
                and existing.get("assertion", {}).get("grade", {}).get("Q") == "Verified"
                and existing.get("pubinfo", {}).get("actor") == ADAPTER_ID
                and existing.get("pubinfo", {}).get("authority_scope") == AUTHORITY
                and existing.get("frame_id") not in retracted
                and existing.get("frame_id") not in seen_targets):
            raise ValueError("manifest omits active native Verified evidence in a targeted direction")
    # Schema, stamp, content identity and effective-state preflight ALL precede append.
    for frame in planned:
        validate_frame(frame)
        _refuse_future_stamp(frame)
        if frame["frame_id"] in by_id and by_id[frame["frame_id"]] != frame:
            raise ValueError("existing correction frame does not match frozen event")
        if frame["frame_id"] in retracted:
            raise ValueError("a generated correction frame has itself been retracted")
    preview = fold(frames + [f for f in planned if f["frame_id"] not in by_id], as_of=as_of)
    effective = {fid for b in preview.beliefs.values() for fid in b.retracted_support}
    if not seen_targets <= effective:
        raise ValueError("planned retractions do not take effect under fold semantics")
    appended = []
    for frame in planned:
        if frame["frame_id"] not in by_id:
            ledger.append(frame)
            by_id[frame["frame_id"]] = frame
            appended.append(frame["frame_id"])
    return {
        "adapter": ADAPTER_ID, "as_of": as_of, "withdraw_only": withdraw_only,
        "entries_read": len(entries), "target_count": len(seen_targets),
        "corrected_index_sha256": index_digest, "target_manifest_sha256": manifest_digest,
        "planned_frame_ids": [f["frame_id"] for f in planned],
        "appended_frame_ids": appended,
        "already_present_count": len(planned) - len(appended),
    }


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

    # Validate every selected entry before any append, including a malformed late entry.
    # This is a projection precondition, not a grade or fold rule.
    for entry in entries:
        if isinstance(entry, dict) and "id" in entry:
            _validated_assertion_kinds(entry)

    # Frames are content-addressed, so re-ingesting an UNCHANGED entry produces byte-identical
    # frames with identical ids. Skipping ids already in the ledger makes re-ingest incremental and
    # keeps the ledger append-only across runs -- which matters because a rebuilt ledger silently
    # invalidates every prior checkpoint, making a legitimate regeneration indistinguishable from
    # tampering. Append-only across re-ingests keeps that distinction sharp.
    # Keyed on (frame_type, assertion), NOT on frame_id. `frame_id` hashes the whole envelope
    # including `created_at`, so re-ingesting the same index with a different `--as-of` produced a
    # complete duplicate corpus: 2026-08-10 measured a ledger going 9,599 -> 19,270 frames with
    # zero new information. What makes a frame redundant is that it asserts the same thing, not
    # that it was written at the same moment.
    existing_ids = {
        _dedup_key(rec.frame) for rec in ledger.read_all() if isinstance(rec.frame, dict)
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
        assertion_kinds = _validated_assertion_kinds(entry)
        for i, c in enumerate(entry.get("key_claims") or []):
            if not isinstance(c, str):
                continue
            n_claims += 1
            if assertion_kinds.get(i, {}).get("kind") == "record_status":
                continue
            anchor = anchors.get(i)
            source_verification = (
                verify_source_anchor(anchor, entry_url=entry.get("url"), claim=c) if anchor else None
            )
            grade, is_opposition = grade_for_entry(entry, anchor, source_verification, claim=c)
            # The SAME helper the frame emitter uses, not a second reading of it. These two drifted
            # before — the report said 112 opposition while the adapter emitted 106, a summary
            # misstating the run it summarizes, which is this program's own subject matter showing
            # up in its own reporting path.
            grade, is_opposition = apply_claim_verdict(
                grade, is_opposition, (_claim_corrections(entry) or {}).get(i))
            grade_counts[f"{grade}{' (opposition)' if is_opposition else ''}"] += 1
        claims_total += n_claims
        verification_counts[entry.get("verification", "<unset>")] += 1
        if not entry.get("ingested_date"):
            no_revision += 1

        anchored_claims += sum(1 for i in range(n_claims) if i in anchors)
        if isinstance(entry.get("dive_corrections"), str) and entry["dive_corrections"].strip():
            corrections_emitted += 1
        for frame in _frames_for_entry(entry, as_of) + _depends_frames(entry, as_of):
            key = _dedup_key(frame)
            if key in existing_ids:
                skipped += 1
                continue
            emitted += 1
            if not dry_run:
                ledger.append(frame)
                existing_ids.add(key)

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
            "Claims WITH an anchor exceed document-level traceability only when its retained original "
            "source bytes and normalized quote hash re-verify; a machine match remains capped at "
            "T2 MachineLocated and a human semantic assertion remains separate. Missing originals "
            "are unknown, never reconstructed or backfilled."
        ),
    }
