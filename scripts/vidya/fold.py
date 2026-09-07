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

# SC58 — the statement-binding half of judge discipline, and it is a DIGEST, never a label.
#
# Until 2026-09-07 `_check_judgment` asked only whether `read_set` and `tool_output_hash` were
# PRESENT. `read_set: ["a"]` folded cleanly, and so did `tool_output_hash: "sha256:aa"`. That is a
# contract on the NAME of a field, not on its content, so a judgment could testify about a version
# of an artifact that no longer exists -- indefinitely and undetectably, because nothing anywhere
# re-checked the label against anything. `intake-1308#03`: "a read-back of an older version of the
# code is worse than none, because it testifies about the wrong artifact", and the platform that
# finding came from enforces the rule only as prose and stores no hash of the audited text -- which
# is exactly why it cannot detect its own violation. We were in the identical position.
#
# So `read_set` entries are in-toto SUBJECTS: `{"name": <artifact>, "digest": {"sha256": <hex>}}`.
# The name is not decoration -- a digest with no name is pinned but anonymous, and a move in an
# anonymous artifact is undetectable, which would leave the second half of the property (going
# dirty when the digest MOVES) unimplementable. This is a fail-closed, prospective requirement:
# the live ledger contains zero judgment frames, so nothing existing is invalidated by it.
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_PREFIXED_DIGEST_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def _digest_of(value: object) -> str | None:
    """Normalize a content digest to `sha256:<hex>`, or None when it is not one."""
    if isinstance(value, str):
        v = value.strip().lower()
        if _PREFIXED_DIGEST_RE.match(v):
            return v if v.startswith("sha256:") else f"sha256:{v}"
        return None
    if isinstance(value, dict) and len(value) == 1:
        (alg, hexdigest), = value.items()
        if (isinstance(alg, str) and isinstance(hexdigest, str)
                and alg.strip().lower() == "sha256"
                and _DIGEST_RE.match(hexdigest.strip().lower())):
            return f"sha256:{hexdigest.strip().lower()}"
    return None


def _judged_subjects(frame: dict) -> list[tuple[str, str]]:
    """(artifact name, digest) pairs a judgment frame pinned itself to."""
    key = frame.get("provenance", {}).get("replay_key")
    if not isinstance(key, dict):
        return []
    out: list[tuple[str, str]] = []
    for entry in key.get("read_set") or []:
        if isinstance(entry, dict):
            name, digest = entry.get("name"), _digest_of(entry.get("digest"))
            if isinstance(name, str) and name and digest:
                out.append((name, digest))
    return out


def _pinned_subjects(frame: dict) -> list[tuple[str, str]]:
    """Every (artifact, digest) this frame OBSERVES, from either pinning slot.

    Two slots, because two kinds of frame legitimately observe an artifact: the in-toto `subjects`
    list any frame may carry (`frames.validate_frame` already validates its shape and had no
    producer), and a judgment's own `read_set`. Ledger order decides which observation is current;
    that is well-defined because `fold` requires its input in ledger order.
    """
    out = list(_judged_subjects(frame))
    for subj in frame.get("subjects") or []:
        if not isinstance(subj, dict):
            continue
        name, digest = subj.get("name"), _digest_of(subj.get("digest"))
        if isinstance(name, str) and name and digest:
            out.append((name, digest))
    return out


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
    # SC59. Free-text reasons recorded ON the frames that superseded or retracted this claim's
    # frames -- "why the ground moved", in the author's own words. Deliberately INERT: no grade, no
    # witness, no verdict, and not part of `review_required`. It exists because a citer who is told
    # only THAT a frame was superseded re-walks the rejected reasoning at full price, and the person
    # who superseded it already knew why. Same rule as `corrections`, for the same reason: we know
    # the ground shifted, not by how much, and guessing the magnitude is the failure mode.
    supersession_reasons: list[str] = field(default_factory=list)
    # SC58. Artifacts a judgment on this claim was pinned to whose digest has since MOVED, with no
    # later judgment having seen the current one. This is the spec §7.2 `dirty` state -- "a
    # registered input changed and recomputation has not completed" -- and it maps to `aging` in
    # THE ONE CLASSIFIER (§8.1), not to `stale`. Kept apart from `corrections` and
    # `dependency_alerts` for the reason those two are kept apart from each other: "its own source
    # was corrected", "something it rests on was withdrawn" and "the artifact it was judged against
    # is no longer that artifact" are three different problems and get cleared by three different
    # people. It is NOT a one-way ratchet: a later judgment that saw the current digest clears it.
    dirty_inputs: list[str] = field(default_factory=list)

    @property
    def dirty(self) -> bool:
        """Spec §7.2 `dirty` -> §8.1 `aging`. Beliefs go dirty; projections go stale."""
        return bool(self.dirty_inputs)

    @property
    def review_required(self) -> bool:
        return bool(self.corrections or self.dependency_alerts or self.dirty_inputs)

    @property
    def flagged(self) -> bool:
        """Alias for readability inside the discharge rule; same condition, different question."""
        return self.review_required

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
        # Included only when present. The determinism anchor (`FoldResult.state_hash`) is pinned by
        # a golden fixture, and an always-present empty list would move every hash in the corpus to
        # record the absence of a field nobody wrote. Deterministic either way: the key is a pure
        # function of the folded frames.
        if self.supersession_reasons:
            out["supersession_reasons"] = self.supersession_reasons
        if self.dirty_inputs:
            out["dirty_inputs"] = self.dirty_inputs
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
    # R1b negation stratum: entries whose transitive dependents are all clear, and those still
    # holding at least one flagged claim. An entry appears in exactly one of the two.
    discharged: dict[str, list[str]] = field(default_factory=dict)
    undischarged: dict[str, list[str]] = field(default_factory=dict)

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
    fid = frame.get("frame_id", "<unsaved>")
    # SC58a: the read set must be DIGESTS OF NAMED ARTIFACTS, not labels for them.
    read_set = key["read_set"]
    if not isinstance(read_set, list) or not read_set:
        raise FoldError(
            f"judgment frame {fid} replay_key.read_set must be a non-empty list -- a judgment that "
            "read nothing has nothing to be replayed against")
    for i, entry in enumerate(read_set):
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) \
                or not entry.get("name"):
            raise FoldError(
                f"judgment frame {fid} replay_key.read_set[{i}] is not a named artifact: expected "
                '{"name": <artifact>, "digest": {"sha256": <hex>}}. A bare label testifies about '
                "whatever that name happens to mean later, which is the defect this pins")
        if _digest_of(entry.get("digest")) is None:
            raise FoldError(
                f"judgment frame {fid} replay_key.read_set[{i}] ({entry.get('name')!r}) carries no "
                'sha256 content digest: expected {"sha256": <64 hex>}. A judgment pinned to a name '
                "instead of a digest cannot detect that it now testifies about the wrong artifact")
    if _digest_of(key.get("tool_output_hash")) is None:
        raise FoldError(
            f"judgment frame {fid} replay_key.tool_output_hash is not a sha256 content digest "
            f"({key.get('tool_output_hash')!r}) -- a field named 'hash' that holds a label is a "
            "contract on the name of the field, not on its content")
    # SC58b: and it must say WHOSE belief it judged, or a dirty judgment has no surface to appear
    # on. Judgments were previously folded into a vote tally that nothing joined to a claim.
    if not isinstance(frame.get("assertion", {}).get("claim_id"), str) \
            or not frame["assertion"]["claim_id"]:
        raise FoldError(
            f"judgment frame {fid} has no assertion.claim_id: a judgment nothing can attribute to "
            "a belief can never be reported stale on that belief's review path")


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
    claim_source: dict[str, str] = {}                # claim_id -> the source that proposed it
    # Claims whose supports must NOT be counted as independent of each other, because a
    # human said the two records are one source or one derived from the other.
    dependent_group: dict[str, str] = {}   # claim_id -> group key
    judgment_votes: dict[str, str] = {}   # replay-key hash -> first frame_id that voted
    # (claim_id, artifact) -> every digest a COUNTED judgment on that claim actually saw. The set,
    # not the latest: a re-judgement at the current digest is what clears `dirty`, and keeping only
    # the newest would make the state depend on which judgment happened to be last rather than on
    # whether the current artifact has been judged at all.
    judgment_reads: dict[tuple[str, str], set[str]] = {}
    superseded_judgments: list[str] = []
    ignored: dict[str, int] = {}

    # Pass 1: collect retractions first, so a retracted support frame never enters the fold at
    # all. Zero-substitution on this carrier is exactly "the token is not there".
    # The frame -> claim index is built in the same walk: a retraction names the FRAME it removes,
    # so without it there is no way to say WHICH belief a retraction reason belongs to when the
    # retraction does not repeat the claim id itself (SC59).
    frame_claim: dict[str, str] = {}
    # SC58: the CURRENT digest of every named artifact anything in this ledger pinned itself to.
    # Last observation in ledger order wins -- `fold` requires its input in ledger order, so this
    # is total and deterministic, and the fold still reads no file and no clock to compute it.
    artifact_digest: dict[str, str] = {}
    for frame in frames:
        for _name, _digest in _pinned_subjects(frame):
            artifact_digest[_name] = _digest
    for frame in frames:
        assertion = frame.get("assertion")
        fid = frame.get("frame_id")
        if isinstance(assertion, dict) and isinstance(fid, str):
            cid = assertion.get("claim_id")
            if isinstance(cid, str) and cid:
                frame_claim.setdefault(fid, cid)
        if frame.get("frame_type") == FT_RETRACT:
            target = frame.get("assertion", {}).get("retracts")
            # The non-emptiness test is load-bearing, not defensive. `fid` below defaults to ""
            # for a frame carrying no frame_id (legal per frames.validate_frame, which only binds
            # frame_id to content when the key is present), so an empty `retracts` matched EVERY
            # such frame: one retraction naming "" silently dropped every id-less support in the
            # ledger and reported it as retracted_support [""]. A retraction must name exactly one
            # frame; naming nothing retracts nothing.
            if isinstance(target, str) and target:
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
            assertion = frame.get("assertion", {})
            claim_id = assertion.get("claim_id")
            if not claim_id:
                raise FoldError(f"claim frame {fid} has no assertion.claim_id")
            claim_id = _canonical(claim_id)
            claims.add(claim_id)
            if assertion.get("source_id"):
                claim_source[claim_id] = assertion["source_id"]

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
            judged_claim = frame["assertion"]["claim_id"]
            for name, digest in _judged_subjects(frame):
                judgment_reads.setdefault(
                    (_canonical(judged_claim), name), set()).add(digest)

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

    # SC58 STRATUM: a judgment is dirty when the artifact it was pinned to has moved and NO
    # judgment on that claim has yet seen the artifact's current digest. Computed after the frames
    # are read, from digests alone -- the fold never opens the artifact, so this stays a pure
    # function of the ledger. The "no judgment has seen the current digest" form is what keeps this
    # from becoming the one-way ratchet the correction rule already had to be rescued from (spec
    # risk §19.7): re-judge against the new artifact and the belief clears itself.
    dirty_inputs: dict[str, list[str]] = {}
    for (cid, name), seen in sorted(judgment_reads.items()):
        current = artifact_digest.get(name)
        if current is not None and current not in seen and cid in claims:
            dirty_inputs.setdefault(cid, []).append(
                f"{name}: judged at {', '.join(sorted(seen))}, now {current}")
    for v in dirty_inputs.values():
        v.sort()

    # SC59: WHY the ground moved, carried from the frame that moved it to the belief a citer reads.
    #
    # Two carriers, one rule. A retraction is a first-class claim frame, so its reason is part of
    # what it ASSERTS (`assertion.reason`); a supersession is a statement about the superseding
    # frame, so its reason rides in `pubinfo.supersedes_reason` beside `supersedes` (spec §3.5).
    #
    # The reason is INERT by construction and this is the whole point of the field. It is collected
    # AFTER the support/oppose buckets are closed, it is never a witness, it never enters
    # `pro`/`con`/`pro_paths`/`con_paths`, it is not part of `review_required`, and the gate may
    # only append it to what a refusal SAYS -- never to what a refusal DECIDES. Same rule as
    # corrections, for the same reason: we know the ground shifted, not by how much, and a system
    # that guessed the magnitude from prose would be manufacturing exactly the confidence this
    # substrate exists to refuse.
    supersession_reasons: dict[str, list[str]] = {}
    for frame in frames:
        assertion = frame.get("assertion") if isinstance(frame.get("assertion"), dict) else {}
        pubinfo = frame.get("pubinfo") if isinstance(frame.get("pubinfo"), dict) else {}
        moves: list[tuple[str, object, object]] = []
        if frame.get("frame_type") == FT_RETRACT:
            moves.append(("retraction of", assertion.get("retracts"), assertion.get("reason")))
        if pubinfo.get("supersedes"):
            moves.append(("supersession of", pubinfo.get("supersedes"),
                          pubinfo.get("supersedes_reason")))
        for verb, target, text in moves:
            if not isinstance(text, str) or not text.strip():
                continue   # absence is recorded as absence; a reason is never invented on read
            raw = assertion.get("claim_id")
            if not isinstance(raw, str) or not raw:
                raw = frame_claim.get(target) if isinstance(target, str) else None
            if not isinstance(raw, str) or not raw:
                continue
            cid = _canonical(raw)
            if cid not in claims:
                continue   # a reason never CREATES a belief -- it only annotates one that exists
            supersession_reasons.setdefault(cid, []).append(
                f"{verb} {target}: {text.strip()}")
    for v in supersession_reasons.values():
        v.sort()

    iterations = 0
    while True:
        changed = False
        for claim_id in sorted(claims):
            # Sort on the LABEL only. A bare `sorted()` on (label, Grade) pairs falls through to
            # comparing Grades whenever two labels tie, and Grade is not orderable -- a latent
            # crash that needs duplicate evidence ids to reach. The duplicate ingest of 2026-08-10
            # produced exactly that, so the fold raised TypeError on the live ledger while every
            # test still passed. Determinism is unaffected: equal labels are interchangeable.
            pro_paths = sorted(support.get(claim_id, []), key=lambda t: t[0])
            con_paths = sorted(oppose.get(claim_id, []), key=lambda t: t[0])
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
                or prev.supersession_reasons != supersession_reasons.get(claim_id, [])
                or prev.dirty_inputs != dirty_inputs.get(claim_id, [])
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
                    supersession_reasons=list(supersession_reasons.get(claim_id, [])),
                    dirty_inputs=list(dirty_inputs.get(claim_id, [])),
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

    # ---------------------------------------------------------------- discharge (R1b)
    #
    # STRATUM 2. Everything above is the positive fixpoint; this is the one rule whose body needs
    # the ABSENCE of a derived fact. Computed after the fixpoint closes, which is exactly what
    # stratification licenses: a negated stratum reads a lower stratum that is already complete.
    #
    # `depends_on` composes, so the dependents of a correction are its transitive closure — a claim
    # three edges away still inherits the doubt, and discharging on direct dependents only would
    # declare a correction finished while its reach was still flagged.
    # Keyed by SOURCE, not by entry name. The first version walked `claim -> what it depends on`,
    # which is the wrong direction: to continue a chain you need `claim -> what it BELONGS to`, so
    # you can find whatever depends on that. Keying everything by source_id makes both directions
    # available without the fold having to know the adapter's entry-naming convention.
    dependents_of_source: dict[str, set[str]] = {}
    entry_of_source: dict[str, str] = {}
    for claim_id, src, entry in depends_edges:
        dependents_of_source.setdefault(src, set()).add(claim_id)
        entry_of_source[src] = entry

    def _closure(source_id: str) -> set[str]:
        """Every claim reachable from this source through `depends_on`, transitively."""
        seen: set[str] = set()
        stack = list(dependents_of_source.get(source_id, ()))
        while stack:
            cid = stack.pop()
            if cid in seen:
                continue
            seen.add(cid)
            # continue through the source this dependent itself belongs to
            own_source = claim_source.get(cid)
            if own_source:
                stack.extend(dependents_of_source.get(own_source, ()))
        return seen

    discharged: dict[str, list[str]] = {}
    undischarged: dict[str, list[str]] = {}
    for source_id in sorted(dependents_of_source):
        label = entry_of_source.get(source_id, source_id)
        reach = sorted(_closure(source_id))
        still_flagged = [c for c in reach
                         if c in beliefs and beliefs[c].review_required]
        (undischarged if still_flagged else discharged)[label] = still_flagged or reach

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
        discharged=discharged,
        undischarged=undischarged,
    )


def chain_grade(grades: Iterable[Grade]) -> Grade:
    """Joint support along a derivation chain: a chain is as strong as its weakest step, per axis."""
    return meet_all(grades)
