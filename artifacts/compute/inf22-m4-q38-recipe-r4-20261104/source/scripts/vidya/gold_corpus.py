"""The P0 gold corpus, encoded as frames, with its expected impact sets.

Corpus definition: docs/design/vidya-pilot-corpus.md (ratified 2026-08-09).

Four documented real corrections plus a measurement family, 19 claims. Real corrections beat
synthetic mutations here for a reason worth restating: their ground truth is already written down
in `dive_corrections` and the incident log, so the gold labels cost nothing to produce, and they
are the exact failure modes the substrate claims to catch.

**Each family carries an `untouched` set, and that is the discriminating half.** An impact engine
that flags everything is as useless as one that flags nothing; three of the four families have a
neighbouring claim that a naive blast radius would have wrongly invalidated, and those are the
assertions that actually test something.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from frames import make_frame  # noqa: E402

__all__ = ["GoldClaim", "GoldFamily", "CORPUS", "corpus_frames", "MUTATION_ROUNDS"]

CORPUS_AS_OF = "2026-08-09T00:00:00Z"
ACTOR = "gold-corpus/p0"
AUTHORITY = "research-verification"


@dataclass(frozen=True)
class GoldClaim:
    claim_id: str
    description: str
    q: str
    t: str
    evidence_id: str
    polarity: str = "support"          # support | oppose
    # Expected behaviour when this family's mutation fires.
    expect: str = "unaffected"         # retracted | downgraded | unaffected | never_believed


@dataclass(frozen=True)
class GoldFamily:
    family_id: str
    title: str
    mutation: str                      # the EVIDENCE TOKEN the mutation retracts
    claims: tuple[GoldClaim, ...]
    round: int = 1
    note: str = ""


CORPUS: tuple[GoldFamily, ...] = (
    GoldFamily(
        family_id="E1",
        title="ngram drafter retraction (2026-07-30 -> 07-31)",
        mutation="e1-c1",
        round=1,
        note=(
            "The corpus's clearest over-propagation test. The real correction generalized into "
            "'do not deploy this path ANYWHERE', which contradicts a live operator decision -- so "
            "an engine that marks e1-c2/e1-c3 stale here reproduces a currently-open defect."
        ),
        claims=(
            GoldClaim("e1-c1", "the drafter delivers a large decode speedup on the composed path",
                      "Verified", "Anchored", "evd-e1-bench", expect="retracted"),
            GoldClaim("e1-c2", "the composed production recipe is the right default",
                      "Verified", "Anchored", "evd-e1-opdecision", expect="unaffected"),
            GoldClaim("e1-c3", "the ngram path is the only speculative path for the SSM-hybrid role",
                      "Verified", "Anchored", "evd-e1-arch", expect="unaffected"),
            GoldClaim("e1-c4", "the MONOTONE CLIMB flag indicates an invalid cell",
                      "Hinted", "Located", "evd-e1-flag", expect="never_believed"),
        ),
    ),
    GoldFamily(
        family_id="E2",
        title="quality-NULL scorer artifact (2026-07-24, n=533)",
        mutation="e2-c1",
        round=2,
        note=(
            "A scorer fix in code does not propagate to already-stored per-question files, so this "
            "is a projection-staleness event with a mechanical trigger. e2-c3 is the "
            "discrimination test: a naive 'all scorers are contaminated' blast radius would have "
            "wrongly invalidated an LLM-judge grader that does zero regex extraction."
        ),
        claims=(
            # BOTH rest on the same stale extractor's output. Giving them independent evidence
            # would model a world where one scorer fix could move one conclusion and not the
            # other, which is not what happened -- and the first run of this suite failed exactly
            # there, because the encoding was wrong rather than the engine.
            GoldClaim("e2-c1", "arms A1/A3 are significantly higher quality than A4",
                      "Verified", "Anchored", "evd-e2-stale-extractor", expect="retracted"),
            GoldClaim("e2-c2", "the parse-failure rate is a model property",
                      "Verified", "Anchored", "evd-e2-stale-extractor", expect="retracted"),
            GoldClaim("e2-c3", "AutoPilot eval-tower grading is affected by the same bug",
                      "Verified", "Anchored", "evd-e2-autopilot", expect="unaffected"),
            GoldClaim("e2-c4", "the separate math-scorer null result is affected",
                      "Verified", "Anchored", "evd-e2-math", expect="unaffected"),
        ),
    ),
    GoldFamily(
        family_id="E3",
        title="fabricated citations (2026-07-25) -- one still wrong at HEAD 15 days later",
        mutation="e3-c1",
        round=1,
        note=(
            "The sharpest case: three records asserted the fabrication was struck and the index "
            "kept serving it. e3-c2's host entry had independently OVERTURNED a claim in the "
            "opposite direction, so a crude quarantine would have destroyed a good result."
        ),
        claims=(
            GoldClaim("e3-c1", "the fabricated ablation figures",
                      "Verified", "Anchored", "evd-e3-ablation", expect="retracted"),
            GoldClaim("e3-c2", "the host entry's own independently-verified finding",
                      "Verified", "Anchored", "evd-e3-hostfinding", expect="unaffected"),
            GoldClaim("e3-c3", "the fabricated four-step tool behaviour",
                      "Hinted", "Located", "evd-e3-doctor", expect="never_believed"),
        ),
    ),
    GoldFamily(
        family_id="E4",
        title="renamed-kernel incident (2026-08-09)",
        mutation="e4-c1",
        round=2,
        note=(
            "The anchor-rot case and the best-propagated real correction. e4-c2 is the "
            "discrimination test: the four-stage decomposition is correct and load-bearing -- only "
            "the LABEL rotted, so a name-keyed invalidation that voided it would be wrong."
        ),
        claims=(
            GoldClaim("e4-c1", "the stage-2 kernel is named ..._kkt_solve_kernel",
                      "Verified", "Anchored", "evd-e4-symbol", expect="retracted"),
            GoldClaim("e4-c2", "the prefill decomposes into four separately-autotuned stages",
                      "Verified", "Anchored", "evd-e4-decomp", expect="unaffected"),
            GoldClaim("e4-c3", "the symbol is absent from upstream",
                      "Hinted", "Located", "evd-e4-absence", expect="never_believed"),
        ),
    ),
    GoldFamily(
        family_id="M",
        title="E8-era measurement family",
        mutation="m-c1",
        round=3,
        note=(
            "Exercises what the prose families cannot: era scoping, protocol grammar, and DERIVED "
            "claim propagation -- m-c5 is derived FROM m-c1, so retracting m-c1 must reach it."
        ),
        claims=(
            GoldClaim("m-c1", "frontdoor decode 40.22 tok/s with spec-dec on",
                      "Witnessed", "Attested", "evd-m-pbench1", expect="retracted"),
            GoldClaim("m-c2", "ingest-role decode 10.12 tok/s, category=OPTIMUM",
                      "Witnessed", "Attested", "evd-m-pbench2", expect="unaffected"),
            GoldClaim("m-c3", "two roles served at 46%/54% of canonical throughput",
                      "Witnessed", "Attested", "evd-m-placement", expect="unaffected"),
            GoldClaim("m-c4", "first-touch placement moved fleet decode 40.91 -> 52.13 tok/s",
                      "Witnessed", "Attested", "evd-m-firsttouch", expect="unaffected"),
            # m-c5's OWN warrant is Verified, not Witnessed: a derived prior is not itself a
            # protocol-admissible measurement (spec §4.2 -- Q4 means exactly "would be admissible
            # as a decision-gating claim"). It inherits Witnessed only through m-c1's measurement,
            # so retracting that measurement drops it to its own weaker warrant. The first run of
            # this suite scored 0 here because the gold had given it Witnessed outright, which
            # made a downgrade arithmetically impossible -- the expectation was wrong, not the fold.
            GoldClaim("m-c5", "corrected router throughput priors (24.3 -> 40.22)",
                      "Verified", "Anchored", "evd-m-priors", expect="downgraded"),
        ),
    ),
)

# Incremental introduction, per the corpus doc §7 -- not all classes at once, so the engine is
# never chasing several failure modes simultaneously.
MUTATION_ROUNDS = {
    1: ("source edit / retraction", ("E1", "E3")),
    2: ("correction narrowing scope / anchor rot", ("E2", "E4")),
    3: ("supersession + derived-claim propagation", ("E2", "M")),
    4: ("era boundary / expiry / conflicting source", ("M",)),
}


def _frame(claim: GoldClaim, family: GoldFamily) -> list[dict]:
    kind = ("evidence_opposes_claim" if claim.polarity == "oppose"
            else "evidence_supports_claim")
    out = [
        make_frame(
            frame_type="epyc.vidya/frame/claim_proposed/v1",
            assertion={"claim_id": claim.claim_id, "display_text": claim.description,
                       "family": family.family_id},
            provenance={"method": "gold-corpus", "about": family.family_id},
            actor=ACTOR, authority_scope=AUTHORITY, created_at=CORPUS_AS_OF),
        make_frame(
            frame_type=f"epyc.vidya/frame/{kind}/v1",
            assertion={"claim_id": claim.claim_id, "evidence_id": claim.evidence_id,
                       "grade": {"Q": claim.q, "T": claim.t}},
            provenance={"method": "gold-corpus", "anchor": f"anchor:{claim.evidence_id}",
                        "derived_from": family.family_id},
            actor=ACTOR, authority_scope=AUTHORITY, created_at=CORPUS_AS_OF),
    ]
    return out


def corpus_frames(families: tuple[str, ...] | None = None) -> list[dict]:
    """All frames for the corpus (or the named families).

    `m-c5` gets a second support path derived from `m-c1`'s evidence, because the corpus's stated
    purpose for it is testing DERIVED-claim propagation: retracting m-c1 must reach it.
    """
    out: list[dict] = []
    for fam in CORPUS:
        if families and fam.family_id not in families:
            continue
        for claim in fam.claims:
            out.extend(_frame(claim, fam))
        if fam.family_id == "M":
            out.append(
                make_frame(
                    frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
                    assertion={"claim_id": "m-c5", "evidence_id": "evd-m-pbench1",
                               "grade": {"Q": "Witnessed", "T": "Attested"}},
                    provenance={"method": "gold-corpus", "anchor": "anchor:evd-m-pbench1",
                                "derived_from": "m-c1"},
                    actor=ACTOR, authority_scope=AUTHORITY, created_at=CORPUS_AS_OF)
            )
    return out


def evidence_frame_id(frames_list: list[dict], evidence_id: str) -> str:
    """The frame id of a named evidence edge -- what a mutation retracts."""
    for f in frames_list:
        if f.get("assertion", {}).get("evidence_id") == evidence_id:
            return f["frame_id"]
    raise KeyError(evidence_id)
