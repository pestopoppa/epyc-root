"""The deterministic fold: frames in, graded beliefs out.

Spec: docs/design/vidya-pilot-spec.md §5, §7.

Three properties this module exists to guarantee, each of which is easy to lose by accident:

* **Purity.** The fold is a function of (frames, policy, as_of). No clock is read, no file is
  touched, no model is called. `as_of` is a required argument precisely so that time cannot sneak
  in as ambient state.
* **A bounded, asserted budget.** Least fixpoint is reached in exactly N applications on this
  carrier -- N being the number of derivable atoms -- because a product of finite chains is
  0-stable. So there is no convergence loop to tune: the iteration count is a constant, and
  exceeding it is an implementation bug that raises rather than a slow case that retries.
* **Independent pro and con.** Refutation never subtracts from support; it accumulates on its own
  side. A claim with strong evidence both ways is Conflicted, which is a served state, not a
  number that averages the disagreement away.

The judge-discipline rules (spec §6) are enforced structurally here: this module imports no model
client, and `fold` will refuse a judgment frame whose replay key is incomplete.
"""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from lattice import (
    BOTTOM,
    Grade,
    join_with_witnesses,
    meet_all,
    parse_grade,
    satisfies_conjunctive,
)

__all__ = ["Belief", "FoldResult", "fold", "FoldError", "Verdict"]

# Frame types the fold interprets. Anything else is carried in the ledger and ignored here --
# a frame the fold does not understand must never silently become support.
FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"
FT_SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"
FT_OPPOSE = "epyc.vidya/frame/evidence_opposes_claim/v1"
FT_RETRACT = "epyc.vidya/frame/retraction/v1"
FT_JUDGMENT = "epyc.vidya/frame/judgment_recorded/v1"
FT_CORRECTION = "epyc.vidya/frame/correction_recorded/v1"
FT_CORRECTION_REVIEWED = "epyc.vidya/frame/correction_reviewed/v1"
# R4b: a human-authored assertion that two claim ids denote the same proposition. The judgment is
# deliberately NOT made by the fold -- deciding two differently-worded claims are the same is
# exactly the semantic call the substrate keeps out of the deterministic path (spec §4.2 boundary).
# The fold only APPLIES an alias somebody else authored, and records that it did.
FT_ALIAS = "epyc.vidya/frame/claim_alias/v1"
FT_SOURCE = "epyc.vidya/frame/source_observed/v1"
FT_DEPENDS = "epyc.vidya/frame/claim_depends_on/v1"

# A judgment frame must be keyed by what the judge saw AND the full decoder tuple, or replay is
# provably inconsistent (spec §6). Greedy decoding does not exempt a frame from this: the
# nondeterminism space includes sampling state and hardware numerics.
_REQUIRED_DECODER_KEYS = {"prompt", "seed", "model_version", "temperature", "tool_output_hash"}


class FoldError(Exception):
    """The frame set cannot be folded deterministically."""


class Verdict:
    UNKNOWN = "Unknown"
    SUPPORTED = "Supported"
    OPPOSED = "Opposed"
    CONFLICTED = "Conflicted"


@dataclass
class Belief:
    """The derived state of one claim at a named frontier."""

    claim_id: str
    pro: Grade = BOTTOM
    con: Grade = BOTTOM
    pro_witnesses: list[str] = field(default_factory=list)
    con_witnesses: list[str] = field(default_factory=list)
    pro_paths: list[tuple[str, Grade]] = field(default_factory=list)
    con_paths: list[tuple[str, Grade]] = field(default_factory=list)
    retracted_support: list[str] = field(default_factory=list)
    # Distinct SOURCES behind the support edges, locator-normalized and collapsed for aliases the
    # author marked non-independent. `pro_paths` counts edges; this counts witnesses, and only the
    # second is a corroboration statistic.
    pro_sources: list[str] = field(default_factory=list)
    con_sources: list[str] = field(default_factory=list)
    # Corrections recorded against this claim's source entry. These do NOT change the grade -- what
    # a correction did to an individual claim is prose, and guessing at it is the failure this
    # substrate exists to prevent. They mark the belief as needing review, which is a freshness
    # question, not a support question.
    corrections: list[str] = field(default_factory=list)
    # Entries this claim declared a `depends_on` edge into whose source has lost all support.
    # Separate from `corrections` so the REASON a claim needs review stays legible -- "its own
    # source was corrected" and "something it rests on was withdrawn" are different problems and
    # get cleared by different people.
    dependency_alerts: list[str] = field(default_factory=list)

    @property
    def review_required(self) -> bool:
        return bool(self.corrections or self.dependency_alerts)

    def verdict(self, floor: Grade, *, conjunctive: bool = True) -> str:
        """Four-valued verdict against a policy floor.

        `conjunctive` is the authoritative default: it asks whether ONE path clears both axes,
        rather than whether the join does. Reading the join would answer a strictly weaker
        question while looking like an answer to this one.

        Note that an unreviewed correction does NOT change this verdict -- support is support. It
        is the freshness gate's job to refuse a `review_required` belief for authoritative use;
        collapsing the two would make a correction look like counter-evidence, which it is not.
        """
        if conjunctive:
            pro_ok, _ = satisfies_conjunctive(self.pro_paths, floor)
            con_ok, _ = satisfies_conjunctive(self.con_paths, floor)
        else:
            pro_ok = self.pro.dominates(floor)
            con_ok = self.con.dominates(floor)
        if pro_ok and con_ok:
            return Verdict.CONFLICTED
        if pro_ok:
            return Verdict.SUPPORTED
        if con_ok:
            return Verdict.OPPOSED
        return Verdict.UNKNOWN

    def as_dict(self, floor: Grade | None = None) -> dict:
        out = {
            "claim_id": self.claim_id,
            "pro": self.pro.as_dict(),
            "con": self.con.as_dict(),
            "pro_witnesses": self.pro_witnesses,
            "con_witnesses": self.con_witnesses,
            "retracted_support": self.retracted_support,
            "corrections": self.corrections,
            "review_required": self.review_required,
        }
        if floor is not None:
            out["verdict"] = self.verdict(floor)
        return out


@dataclass
class FoldResult:
    beliefs: dict[str, Belief]
    iterations: int
    frontier: int
    as_of: str
    ignored_frame_types: dict[str, int]
    # replay-key hash -> the frame_id of the FIRST judgment committed under that key. Exposed
    # rather than kept internal because a certificate needs to name which judgments it counted,
    # and because a rule that cannot be observed cannot be tested.
    counted_judgments: dict[str, str] = field(default_factory=dict)
    superseded_judgments: list[str] = field(default_factory=list)
    reviewed_corrections: list[str] = field(default_factory=list)
    applied_aliases: list[str] = field(default_factory=list)
    alias_map: dict[str, str] = field(default_factory=dict)

    def state_hash(self) -> str:
        """A content hash over the derived state -- the determinism-suite anchor."""
        from canonical import content_hash

        payload = {
            "as_of": self.as_of,
            "frontier": self.frontier,
            "beliefs": [
                self.beliefs[cid].as_dict() for cid in sorted(self.beliefs)
            ],
        }
        return content_hash(payload)


def _check_judgment(frame: dict) -> None:
    """A judgment frame must carry a complete replay key (spec §6.1)."""
    key = frame.get("provenance", {}).get("replay_key")
    if not isinstance(key, dict):
        raise FoldError(
            f"judgment frame {frame.get('frame_id', '<unsaved>')} has no provenance.replay_key: "
            "a judgment that does not record what the judge saw is not replayable"
        )
    missing = _REQUIRED_DECODER_KEYS - set(key)
    if missing:
        raise FoldError(
            f"judgment frame {frame.get('frame_id', '<unsaved>')} replay_key missing "
            f"{sorted(missing)} -- temperature-0 decoding does not exempt a frame from this"
        )
    if "read_set" not in key:
        raise FoldError(
            f"judgment frame {frame.get('frame_id', '<unsaved>')} replay_key missing 'read_set'"
        )


def _normalize_locator(url: str) -> str:
    """Fold the spellings of one source to one key.

    An arXiv id and an arXiv URL name the same paper; so do http/https, a trailing slash, and a
    version suffix. This is the same normalization the intake validator uses, and it exists here
    for the same reason: two records of one paper must not read as two witnesses.
    """
    u = url.strip().lower()
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9v.]+)", u)
    if m:
        return "arxiv:" + re.sub(r"v\d+$", "", m.group(1).removesuffix(".pdf"))
    return "url:" + re.sub(r"^https?://(www\.)?", "", u).rstrip("/")


def fold(
    frames: Sequence[dict],
    *,
    as_of: str,
    max_iterations: int | None = None,
) -> FoldResult:
    """Fold an ordered frame sequence into belief state.

    `frames` must be in ledger order. `as_of` is the explicit evaluation time -- required, never
    defaulted to now.
    """
    if not isinstance(as_of, str) or not as_of:
        raise FoldError("as_of must be an explicit non-empty timestamp string")

    claims: set[str] = set()
    support: dict[str, list[tuple[str, Grade]]] = {}
    oppose: dict[str, list[tuple[str, Grade]]] = {}
    pro_sources: dict[str, list[str]] = {}
    con_sources: dict[str, list[str]] = {}
    retracted: set[str] = set()
    corrections_by_claim: dict[str, list[str]] = {}
    reviewed_corrections: set[str] = set()
    alias_of: dict[str, str] = {}          # claim_id -> canonical claim_id
    applied_aliases: list[str] = []
    source_locator: dict[str, str] = {}    # source_id -> normalized locator
    depends_edges: list[tuple[str, str, str]] = []   # (claim_id, source_id, entry)
    supported_sources: set[str] = set()              # sources with surviving support
    # Claims whose supports must NOT be counted as independent of each other, because a
    # human said the two records are one source or one derived from the other.
    dependent_group: dict[str, str] = {}   # claim_id -> group key
    judgment_votes: dict[str, str] = {}   # replay-key hash -> first frame_id that voted
    superseded_judgments: list[str] = []
    ignored: dict[str, int] = {}

    # Pass 1: collect retractions first, so a retracted support frame never enters the fold at
    # all. Zero-substitution on this carrier is exactly "the token is not there".
    for frame in frames:
        if frame.get("frame_type") == FT_RETRACT:
            target = frame.get("assertion", {}).get("retracts")
            if isinstance(target, str):
                retracted.add(target)

    # Corrections are collected with retractions, before interpretation, so a correction that was
    # already reviewed never marks anything. Without this the review flag is a one-way ratchet: a
    # single `dive_corrections` field blocks every claim from its entry forever, and the gate
    # deadlocks the work it was meant to protect (spec risk §19.7).
    # Source locators, so support can be counted by SOURCE rather than by evidence label.
    # Evidence tokens are minted per claim, so counting labels counts edges, not witnesses:
    # two records of one paper produce two labels and would read as independent support.
    for frame in frames:
        if frame.get("frame_type") == FT_SOURCE:
            assertion = frame.get("assertion", {})
            sid, loc = assertion.get("source_id"), assertion.get("locator")
            if isinstance(sid, str) and isinstance(loc, str) and loc.strip():
                source_locator[sid] = _normalize_locator(loc)

    for frame in frames:
        if frame.get("frame_type") == FT_CORRECTION_REVIEWED:
            target = frame.get("assertion", {}).get("reviewed")
            if isinstance(target, str):
                reviewed_corrections.add(target)

    # Aliases resolve before interpretation so support from both members lands on one claim.
    # Union-find with path compression, ordered by canonical id so the choice of representative
    # does not depend on frame arrival order -- otherwise the same alias set could produce two
    # different state hashes.
    for frame in frames:
        if frame.get("frame_type") != FT_ALIAS:
            continue
        members = sorted(
            m for m in (frame.get("assertion", {}).get("claim_ids") or []) if isinstance(m, str)
        )
        if len(members) < 2:
            continue
        canonical = members[0]
        for member in members[1:]:
            alias_of[member] = canonical
        applied_aliases.append(frame.get("frame_id", ""))
        # `independent: false` means the human who authored the alias also said the two
        # records are not separate witnesses -- one source recorded twice, or one derived
        # from the other (a dataset card restating its own paper). Without this the merge
        # would CREATE the corroboration it was supposed to let us measure.
        if frame.get("assertion", {}).get("independent") is False:
            group = "alias:" + canonical
            for member in members:
                dependent_group[member] = group

    def _canonical(cid: str) -> str:
        seen: set[str] = set()
        while cid in alias_of and cid not in seen:
            seen.add(cid)
            cid = alias_of[cid]
        return cid

    # Pass 2: interpret the surviving frames.
    for frame in frames:
        ftype = frame.get("frame_type")
        fid = frame.get("frame_id", "")

        if ftype == FT_RETRACT:
            continue

        if fid in retracted:
            claim_id = frame.get("assertion", {}).get("claim_id")
            if claim_id:
                claims.add(_canonical(claim_id))
            continue

        if ftype == FT_CLAIM:
            claim_id = frame.get("assertion", {}).get("claim_id")
            if not claim_id:
                raise FoldError(f"claim frame {fid} has no assertion.claim_id")
            claims.add(_canonical(claim_id))

        elif ftype in (FT_SUPPORT, FT_OPPOSE):
            assertion = frame.get("assertion", {})
            claim_id = assertion.get("claim_id")
            if not claim_id:
                raise FoldError(f"{ftype} frame {fid} has no assertion.claim_id")
            try:
                grade = parse_grade(assertion.get("grade"))
            except ValueError as exc:
                raise FoldError(f"{ftype} frame {fid}: {exc}") from exc
            claim_id = _canonical(claim_id)
            claims.add(claim_id)
            label = assertion.get("evidence_id") or fid or f"<frame {len(support)}>"
            raw_claim = assertion.get("claim_id")
            source_key = (
                dependent_group.get(raw_claim)
                or source_locator.get(assertion.get("source_id") or "")
                or assertion.get("source_id")
                or label
            )
            bucket = support if ftype == FT_SUPPORT else oppose
            bucket.setdefault(claim_id, []).append((label, grade))
            (pro_sources if ftype == FT_SUPPORT else con_sources).setdefault(
                claim_id, []
            ).append(source_key)
            if ftype == FT_SUPPORT and assertion.get("source_id"):
                supported_sources.add(assertion["source_id"])

        elif ftype == FT_CORRECTION:
            assertion = frame.get("assertion", {})
            already_reviewed = fid in reviewed_corrections
            for claim_id in assertion.get("claim_ids") or []:
                if isinstance(claim_id, str):
                    claim_id = _canonical(claim_id)
                    claims.add(claim_id)
                    if not already_reviewed:
                        corrections_by_claim.setdefault(claim_id, []).append(fid)

        elif ftype == FT_DEPENDS:
            assertion = frame.get("assertion", {})
            cid = assertion.get("claim_id")
            src = assertion.get("depends_on_source")
            ent = assertion.get("depends_on_entry") or src or ""
            if isinstance(cid, str) and isinstance(src, str):
                depends_edges.append((_canonical(cid), src, ent))
            continue

        elif ftype in (FT_CORRECTION_REVIEWED, FT_ALIAS):
            continue

        elif ftype == FT_JUDGMENT:
            _check_judgment(frame)
            from canonical import content_hash

            key_hash = content_hash(frame["provenance"]["replay_key"])
            if key_hash in judgment_votes:
                # First-committed-vote-wins per key. A re-run judge is short-circuited by the
                # existing frame -- an append-only ledger permits both records, and it is the fold
                # that must refuse to count the second.
                superseded_judgments.append(fid)
                continue
            judgment_votes[key_hash] = fid

        else:
            ignored[str(ftype)] = ignored.get(str(ftype), 0) + 1

    # Derivation. With only direct evidence->claim edges the fixpoint is reached in one pass; the
    # loop and its assertion are kept because the budget is the invariant, not the current rule
    # set's shallowness. N is the number of derivable atoms.
    n_atoms = max(len(claims), 1)
    budget = max_iterations if max_iterations is not None else n_atoms
    beliefs: dict[str, Belief] = {}
    # `iterations` counts PRODUCTIVE applications of F -- passes that changed something. The final
    # pass that observes stability is not one of them, and must not be charged against the budget:
    # the theorem bounds how many times a value can strictly increase, not how many times you look.
    # (Same off-by-one as the spec's "N+1" = N Kleene steps plus the zero-init layer.)
    # OP-11 (operator-ratified 2026-08-10): a dependency whose source has lost all support marks
    # its dependents for review. No grade moves -- we know the ground shifted, not by how much,
    # and the correction rule already established that guessing the magnitude is the failure mode.
    dependency_alerts: dict[str, list[str]] = {}
    for claim_id, src, entry in depends_edges:
        if src not in supported_sources:
            dependency_alerts.setdefault(claim_id, []).append(entry)
    for v in dependency_alerts.values():
        v.sort()

    iterations = 0
    while True:
        changed = False
        for claim_id in sorted(claims):
            pro_paths = sorted(support.get(claim_id, []))
            con_paths = sorted(oppose.get(claim_id, []))
            pro, pro_w = join_with_witnesses(pro_paths)
            con, con_w = join_with_witnesses(con_paths)
            corrections = sorted(corrections_by_claim.get(claim_id, []))
            prev = beliefs.get(claim_id)
            if (
                prev is None
                or prev.pro != pro
                or prev.con != con
                or prev.corrections != corrections
                or prev.dependency_alerts != dependency_alerts.get(claim_id, [])
            ):
                beliefs[claim_id] = Belief(
                    claim_id=claim_id,
                    pro=pro,
                    con=con,
                    pro_witnesses=pro_w,
                    con_witnesses=con_w,
                    pro_paths=pro_paths,
                    con_paths=con_paths,
                    retracted_support=sorted(retracted),
                    corrections=corrections,
                    pro_sources=sorted(set(pro_sources.get(claim_id, []))),
                    con_sources=sorted(set(con_sources.get(claim_id, []))),
                    dependency_alerts=dependency_alerts.get(claim_id, []),
                )
                changed = True
        if not changed:
            break
        iterations += 1
        if iterations > budget:
            raise FoldError(
                f"fold exceeded its {budget}-iteration budget (N={n_atoms}). On a 0-stable "
                "carrier the least fixpoint is reached in at most N strictly-increasing steps, "
                "so this is an implementation bug, not a slow case."
            )

    return FoldResult(
        beliefs=beliefs,
        iterations=iterations,
        frontier=len(frames),
        as_of=as_of,
        ignored_frame_types=ignored,
        counted_judgments=judgment_votes,
        superseded_judgments=superseded_judgments,
        reviewed_corrections=sorted(reviewed_corrections),
        applied_aliases=sorted(a for a in applied_aliases if a),
        alias_map=dict(sorted(alias_of.items())),
    )


def chain_grade(grades: Iterable[Grade]) -> Grade:
    """Joint support along a derivation chain: a chain is as strong as its weakest step, per axis."""
    return meet_all(grades)
