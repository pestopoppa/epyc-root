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
    # Corrections recorded against this claim's source entry. These do NOT change the grade -- what
    # a correction did to an individual claim is prose, and guessing at it is the failure this
    # substrate exists to prevent. They mark the belief as needing review, which is a freshness
    # question, not a support question.
    corrections: list[str] = field(default_factory=list)

    @property
    def review_required(self) -> bool:
        return bool(self.corrections)

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
    retracted: set[str] = set()
    corrections_by_claim: dict[str, list[str]] = {}
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

    # Pass 2: interpret the surviving frames.
    for frame in frames:
        ftype = frame.get("frame_type")
        fid = frame.get("frame_id", "")

        if ftype == FT_RETRACT:
            continue

        if fid in retracted:
            claim_id = frame.get("assertion", {}).get("claim_id")
            if claim_id:
                claims.add(claim_id)
            continue

        if ftype == FT_CLAIM:
            claim_id = frame.get("assertion", {}).get("claim_id")
            if not claim_id:
                raise FoldError(f"claim frame {fid} has no assertion.claim_id")
            claims.add(claim_id)

        elif ftype in (FT_SUPPORT, FT_OPPOSE):
            assertion = frame.get("assertion", {})
            claim_id = assertion.get("claim_id")
            if not claim_id:
                raise FoldError(f"{ftype} frame {fid} has no assertion.claim_id")
            try:
                grade = parse_grade(assertion.get("grade"))
            except ValueError as exc:
                raise FoldError(f"{ftype} frame {fid}: {exc}") from exc
            claims.add(claim_id)
            label = assertion.get("evidence_id") or fid or f"<frame {len(support)}>"
            bucket = support if ftype == FT_SUPPORT else oppose
            bucket.setdefault(claim_id, []).append((label, grade))

        elif ftype == FT_CORRECTION:
            assertion = frame.get("assertion", {})
            for claim_id in assertion.get("claim_ids") or []:
                if isinstance(claim_id, str):
                    claims.add(claim_id)
                    corrections_by_claim.setdefault(claim_id, []).append(fid)

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
    )


def chain_grade(grades: Iterable[Grade]) -> Grade:
    """Joint support along a derivation chain: a chain is as strong as its weakest step, per axis."""
    return meet_all(grades)
