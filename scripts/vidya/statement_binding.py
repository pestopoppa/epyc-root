"""SC61 — the human-authored producer for SC56's `attested` binding.

SC56 caps a verifier-class tuple at `Judged` until its decided proposition is BOUND to the claim
it is cited for. Two binding kinds exist: `identity` (the proposition and the claim are the same
statement, machine-checkable by normalized string equality) and `attested` — a person's judgment
that the claim FOLLOWS FROM the proposition the checker decided, which is the common case an
identical sentence is not. Until this module existed `attested` had no producer, so only
`identity` was reachable and the more useful half was inert.

This module is the producer, built parallel to `claim_alias/v1`:

* **It does not decide anything.** The judgment that a claim follows from a proposition is
  exactly the semantic call the substrate keeps out of the deterministic path, so the output here
  is a review worksheet with every row `pending`, and only a human flipping a row to `follows`
  produces a `claim_statement_binding/v1` frame. The fold APPLIES such frames; it never derives
  them.
* **The frame is the record of the judgment.** `binding_ref` on a tuple names its
  `claim_statement_binding/v1` frame id, and the frame carries the claim and the proposition it
  was judged against, verbatim, so a reader can compare without chasing the source evidence.
* **The generator proposes candidates; the reviewer disposes.** Candidates are claims whose
  frames carry a `decided_proposition` and no binding yet. A pair the machine could bind by
  `identity` is never proposed — same hard-filter discipline as the alias generator, for the same
  reason: a human is not needed where the machine can decide, and a worksheet full of
  machine-decidable rows is a worksheet that will be rubber-stamped.
"""

from __future__ import annotations

from typing import Any, Iterable

__all__ = [
    "FT_STATEMENT_BINDING",
    "WORKSHEET_SCHEMA",
    "candidate_rows",
    "worksheet_from_candidates",
    "bindings_from_worksheet",
    "WorksheetError",
]

FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"
FT_STATEMENT_BINDING = "epyc.vidya/frame/claim_statement_binding/v1"
WORKSHEET_SCHEMA = "epyc.vidya/statement-binding-worksheet/v1"

_DECISIONS = frozenset({"pending", "follows", "does_not_follow"})


class WorksheetError(ValueError):
    """A review worksheet is malformed or carries an unrecognized decision."""


def candidate_rows(frames: Iterable[dict], *, limit: int | None = None) -> list[dict]:
    """Claims a human could bind by attestation: they carry the proposition a checker decided,
    and no binding yet.

    A claim the machine could bind by `identity` (normalized-string equality between proposition
    and claim) is never proposed — that judgment needs no human. `binding_kind` empty is the
    candidate state: an `identity`-bound claim is already reachable, and an `attested`-bound one
    already has its judgment.
    """
    from claim_tuple import propositions_are_identical

    rows: list[dict] = []
    for frame in frames:
        if frame.get("frame_type") != FT_CLAIM:
            continue
        assertion = frame.get("assertion") or {}
        cid = assertion.get("claim_id")
        claim = assertion.get("display_text")
        decided = assertion.get("decided_proposition")
        if not isinstance(cid, str) or not cid:
            continue
        if not isinstance(claim, str) or not claim.strip():
            continue
        if not isinstance(decided, str) or not decided.strip():
            continue
        if assertion.get("binding_kind"):
            continue
        if propositions_are_identical(decided, claim):
            continue
        rows.append({
            "claim_id": cid,
            "claim_text": claim,
            "decided_proposition": decided,
            "source_id": assertion.get("source_id") or "",
        })
        if limit is not None and len(rows) >= limit:
            break
    rows.sort(key=lambda r: (r["claim_id"], r["decided_proposition"]))
    return rows


def worksheet_from_candidates(rows: list[dict], *, generated_at: str) -> dict:
    """A review worksheet with every decision `pending` — the only legal initial value.

    `pending` emits nothing. A generator that pre-filled `follows` would be the machine making
    the judgment with extra steps; a generator that pre-filled `does_not_follow` would be the
    machine refusing to let a human look.
    """
    return {
        "schema": WORKSHEET_SCHEMA,
        "generated_at": generated_at,
        "generator": "vidya.statement_binding/candidate_rows",
        "rows": [
            {
                "claim_id": r["claim_id"],
                "claim_text": r["claim_text"],
                "decided_proposition": r["decided_proposition"],
                "decision": "pending",  # pending | follows | does_not_follow
                "reviewer": "",
                "note": "",
            }
            for r in rows
        ],
        "instructions": (
            "Set decision to 'follows' only if the claim genuinely FOLLOWS FROM the proposition "
            "the checker decided — the checker proved the proposition, and you are judging that "
            "the claim is licensed by it. Set 'does_not_follow' otherwise; leave 'pending' if "
            "you did not look. Fill 'reviewer'. Only 'follows' rows become "
            "claim_statement_binding frames, and the claim cited with binding_ref "
            "then caps at Verified instead of Judged (SC56). Rows where the proposition and "
            "the claim are the same statement never appear: that is 'identity', which needs no "
            "human judgment."
        ),
    }


def bindings_from_worksheet(worksheet: dict) -> list[dict]:
    """Collect `follows` rows into binding records.

    An approved `follows` row MUST name its reviewer — an unattributed human judgment is
    indistinguishable from one the machine made, the same rule the alias worksheet enforces.
    """
    if worksheet.get("schema") != WORKSHEET_SCHEMA:
        raise WorksheetError(f"unrecognized worksheet schema {worksheet.get('schema')!r}")
    rows = worksheet.get("rows")
    if not isinstance(rows, list):
        raise WorksheetError("worksheet.rows must be a list")

    out: list[dict] = []
    for i, row in enumerate(rows):
        decision = row.get("decision")
        if decision not in _DECISIONS:
            raise WorksheetError(
                f"rows[{i}]: decision must be one of {sorted(_DECISIONS)}, got {decision!r}")
        if decision != "follows":
            continue
        cid = row.get("claim_id")
        decided = row.get("decided_proposition")
        if not isinstance(cid, str) or not cid:
            raise WorksheetError(f"rows[{i}]: claim_id must be a non-empty string")
        if not isinstance(decided, str) or not decided.strip():
            raise WorksheetError(
                f"rows[{i}]: an approved binding must carry the decided proposition it was "
                "judged against, verbatim")
        reviewer = (row.get("reviewer") or "").strip()
        if not reviewer:
            raise WorksheetError(
                f"rows[{i}]: an approved binding must name its reviewer — an unattributed "
                "human judgment is indistinguishable from one the machine made")
        out.append({
            "claim_id": cid,
            "decided_proposition": decided,
            "reviewer": reviewer,
            "note": (row.get("note") or "").strip(),
        })
    return out


def frame_from_binding(binding: dict, *, actor: str, at: str, worksheet_digest: str) -> dict:
    """One content-addressed `claim_statement_binding/v1` frame for an approved row."""
    from frames import make_frame

    provenance: dict[str, Any] = {
        "method": "human-review/statement-binding-worksheet",
        "about": binding["claim_id"],
        "reviewers": [binding["reviewer"]],
        "worksheet_digest": worksheet_digest,
    }
    if binding.get("note"):
        provenance["notes"] = [binding["note"]]
    return make_frame(
        frame_type=FT_STATEMENT_BINDING,
        assertion={
            "claim_id": binding["claim_id"],
            "decided_proposition": binding["decided_proposition"],
        },
        provenance=provenance,
        actor=actor,
        authority_scope="statement-binding",
        created_at=at,
    )
