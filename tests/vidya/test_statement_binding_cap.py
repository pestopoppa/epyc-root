"""SC56 — a verifier result may outrank `Judged` only when it is BOUND to the claim it supports.

Spec: docs/design/vidya-pilot-spec.md §4.5 (the status-to-grade table, which already caps a
deterministic verifier result at `Q3` — "a verifier confirms, it does not measure" — and names
protocol-admissible measurement as the only route to `Q4`) and §4.7 (project, never grade).

SC57 made a verifier adapter record WHAT its check decided. It deliberately stopped there. This
file is the other half: nothing yet binds that decided proposition to the claim someone cites the
check for, and an unbound verdict is an observation about a different sentence. `intake-1307#05` —
the certificate "does not certify individual mathematical truth"; `intake-1307#00` — in one real
pipeline an automated check labelled 73.6% of proved artifacts non-trivial-and-correct where a
manual audit put faithfulness far lower (a reweighted projection from a 45-example
single-annotator audit: admissible as an existence proof that the gap is large, never as a rate).

Three properties this file exists to defend, each of which was a live way to get SC56 wrong:

  * **The cap is scoped to `source_class == "verifier"`,** not to "carries a decided_proposition"
    and not to every class. `test_a_decided_proposition_alone_never_caps_a_measurement_tuple` and
    `test_the_measurement_ladder_is_bit_for_bit_what_it_was` are the tests that fail if the scope
    widens.
  * **T is untouched.** Traceability is a different axis from warrant quality, and the tempting
    implementation — an early return inside the ladder, copying the shape of the existing
    `no protocol` branch — silently returns `Located`/`T0` and destroys it.
    `test_the_cap_preserves_the_traceability_axis_exactly` is that test.
  * **A MISSING binding grades down; a FALSE binding is refused.** Asserting `identity` between
    two different statements is not a hole in the record, it is a wrong claim about a structural
    fact, and letting it decay into a downgrade would record it at a defensible-looking grade.

Every positive is paired with a mutation that makes the same call come out the other way, because
a cap test that would also pass against a grader which capped EVERYTHING proves nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402

CLAIM = "the sort routine returns a sorted permutation of its input"
# The identity case: the checker decided exactly the sentence being claimed.
SAME = CLAIM
# The ordinary case: a real theorem statement that is NOT the claim it gets cited for. This is the
# shape the whole SC56 gap is about — plausible, adjacent, and not the same proposition.
OTHER = "for every list xs of int, sorted_permutation(sort(xs), xs) holds"


def tup(**over):
    """A FULL tuple — protocol, reps, date, hashed artifact present on disk — so the measurement
    ladder reaches `Witnessed`/`Attested` on its own. Starting from the top is what lets each test
    show the cap doing work rather than agreeing with an already-low grade."""
    base = dict(measurement_id="sc56", metric="obligations_discharged", value=1,
                date="2026-09-07", category="CANDIDATE", claim=CLAIM,
                protocol_id="P-verifier-1", reps=3, attestation_path="MEASUREMENT.md",
                attestation_sha256="a" * 64)
    base.update(over)
    return ct.ClaimTuple(**base)


def verifier(**over):
    over.setdefault("decided_proposition", OTHER)
    return tup(source_class=ct.VERIFIER_CLASS, **over)


# --- the unbound cap ------------------------------------------------------------------------

def test_an_unbound_verifier_result_caps_at_judged():
    """CATCHES: a verifier receipt with a perfect measurement tuple riding to `Witnessed` on the
    strength of a check that decided some OTHER proposition — the entire SC56 gap.

    `Judged` and not lower: the check really ran and really decided something, which is exactly
    what an observation is. Grading it below that would be a claim that no check happened.
    """
    q, t, reasons = ct.grade(verifier())
    assert q == "Judged"
    assert any("not bound to the claim" in r for r in reasons)


def test_the_bound_mutation_reaches_the_normal_level():
    """MUTATION for the test above. Without it, that test would also pass against a grader that
    capped every verifier tuple at `Judged` unconditionally, which would make the binding — the
    only thing SC56 is about — carry no weight at all."""
    assert ct.grade(verifier(decided_proposition=SAME, binding_kind="identity"))[0] == "Verified"


def test_the_cap_preserves_the_traceability_axis_exactly():
    """CATCHES the near-miss implementation: an early return inside the ladder.

    The existing `no protocol` branch returns `("Judged", "Located"|"T0")`, and copying that shape
    to implement the cap destroys T. It must not: an unbound receipt can be perfectly located,
    hashed and present on disk — nobody recording which claim it decided says nothing whatever
    about where the receipt is. So the SAME tuple graded as a measurement and as an unbound
    verifier must differ on Q and agree on T.
    """
    _, measurement_t, _ = ct.grade(tup(decided_proposition=OTHER))
    capped_q, capped_t, _ = ct.grade(verifier())
    assert measurement_t == capped_t == "Attested"
    assert capped_q == "Judged" != ct.grade(tup(decided_proposition=OTHER))[0]


@pytest.mark.parametrize("over, expected_t", [
    (dict(), "Attested"),
    (dict(attestation_sha256=""), "Anchored"),
    (dict(attestation_path="", attestation_locator=""), "Located"),
    (dict(protocol_id="", attestation_path="", attestation_locator=""), "T0"),
])
def test_t_survives_the_cap_at_every_level_of_the_t_axis(over, expected_t):
    """CATCHES a cap that collapses T only for SOME inputs — a single-point T check would pass
    against an implementation that pinned T to whatever the one probe happened to produce."""
    assert ct.grade(verifier(**over))[:2] == ("Judged", expected_t)


def test_the_reason_names_the_decided_proposition_verbatim():
    """CATCHES a reason string that reports a gap instead of showing it.

    "the binding is missing" tells a reader something they must then go and investigate. Printing
    the sentence the checker actually decided, next to the claim, lets them see the distance for
    themselves — which for the real cases is the whole finding.
    """
    _, _, reasons = ct.grade(verifier())
    joined = " ".join(reasons)
    assert OTHER in joined and CLAIM in joined


def test_a_verifier_that_recorded_no_proposition_at_all_says_so():
    """MUTATION for the test above: the verbatim quote must not be the only thing the reason can
    say, or a tuple with an empty proposition would report an empty pair of quotes as though a
    proposition had been recorded."""
    _, _, reasons = ct.grade(verifier(decided_proposition=""))
    assert any("recorded no decided proposition" in r for r in reasons)


# --- the ratified Q3 ceiling ----------------------------------------------------------------

def test_a_bound_verifier_still_cannot_reach_witnessed():
    """CATCHES: the binding being read as a licence to measure. Spec §4.5 caps a deterministic
    verifier result at `Q3` — a verifier confirms, it does not measure — and makes
    protocol-admissible measurement the only route to `Q4`. Binding fixes WHICH claim the check
    decided; it does not turn the check into a measurement of it."""
    q, t, reasons = ct.grade(verifier(decided_proposition=SAME, binding_kind="identity"))
    assert (q, t) == ("Verified", "Attested")
    assert any("does not measure" in r for r in reasons)


def test_the_identical_tuple_as_a_measurement_does_reach_witnessed():
    """MUTATION for the test above, and the proof the ceiling is the CLASS's and not the tuple's:
    one field changes, and the same content grades a full level higher."""
    assert ct.grade(tup(decided_proposition=SAME))[:2] == ("Witnessed", "Attested")


def test_the_ceiling_never_promotes_a_low_verifier_grade():
    """CATCHES a cap written as an assignment instead of a minimum — `Q = Verified` would PROMOTE
    a bound verifier tuple that cited no protocol, inventing warrant out of a cap."""
    weak = verifier(decided_proposition=SAME, binding_kind="identity",
                    protocol_id="", attestation_path="", attestation_sha256="")
    assert ct.grade(weak)[0] == "Judged"


# --- a FALSE binding is refused, never downgraded --------------------------------------------

def test_a_false_identity_binding_is_refused_not_downgraded():
    """CATCHES the single most damaging way to be lenient here.

    `identity` asserts a structural fact: the checker decided THIS sentence. When the two strings
    differ, that assertion is false, and a false assertion is not a missing element. Letting it
    degrade into a downgrade would record a wrong claim at a grade that looks considered — the
    behaviour `category` has been refusing since this module was written.
    """
    with pytest.raises(ct.ProjectionError, match="identity"):
        verifier(decided_proposition=OTHER, binding_kind="identity")


def test_a_true_identity_binding_is_accepted():
    """MUTATION for the test above: the refusal must fire on inequality, not on the kind."""
    assert verifier(decided_proposition=SAME, binding_kind="identity").binding_kind == "identity"


@pytest.mark.parametrize("variant", [
    "The Sort Routine Returns A Sorted Permutation Of Its Input",      # casefold
    "the sort   routine returns a\tsorted\npermutation of its input",  # whitespace collapse
    "the sort routine returns a sorted permutation of its input.",     # trailing punctuation
    "  THE SORT ROUTINE returns a sorted permutation of its input!!  ",  # all three
])
def test_identity_tolerates_exactly_three_normalizations(variant):
    """The accepted half of the normalizer contract: case, internal whitespace, trailing sentence
    punctuation. These are typography, not meaning."""
    assert ct.propositions_are_identical(variant, CLAIM)


@pytest.mark.parametrize("variant", [
    "the sort routines return sorted permutations of their inputs",   # stemming would match
    "the sorting function yields an ordered rearrangement of its input",  # synonyms would match
    "sort routine returns sorted permutation input",                  # stopword removal
    "of its input a sorted permutation returns the sort routine",     # token-set overlap
    "the sort routine returns a sorted permutation of its input in O(n log n) time",  # superset
    "the sort routine returns a sorted permutation of its input, assuming a total order",
])
def test_identity_refuses_everything_looser(variant):
    """CATCHES the normalizer drifting toward similarity.

    Each of these is matched by SOME popular normalization — a stemmer, a synonym table, stopword
    removal, a token-set ratio, a prefix test. Every one of them would let two DIFFERENT statements
    be declared identical, and the only load-bearing property of `identity` is that a machine can
    decide it with no judgment involved. A claim that genuinely follows from the proposition
    without being the same sentence is real and common — it is `attested`, a human judgment with a
    reference, and never a looser rule here.
    """
    assert not ct.propositions_are_identical(variant, CLAIM)
    with pytest.raises(ct.ProjectionError, match="paraphrase detection"):
        verifier(decided_proposition=variant, binding_kind="identity")


def test_two_empty_statements_are_not_identical():
    """CATCHES the normalizer's degenerate fixed point: "" == "" is True as string equality, so a
    proposition-less tuple would acquire an identity binding for free. (`__post_init__` refuses
    that case for a second reason, which is why this asserts on the predicate directly.)"""
    assert not ct.propositions_are_identical("", "")


# --- `attested`: validated here, produced by SC61 ---------------------------------------------

def test_attested_without_a_binding_ref_is_refused():
    """CATCHES an attested binding that points at no judgment. `attested` IS a human judgment;
    one nobody can retrieve is indistinguishable from no binding at all, except that it grades
    like a binding."""
    with pytest.raises(ct.ProjectionError, match="requires `binding_ref`"):
        verifier(binding_kind="attested")


def test_attested_with_a_binding_ref_is_accepted_and_capped_at_verified():
    """MUTATION for the test above. SC61 owns the PRODUCER of these references
    (`claim_statement_binding/v1`: the frame type, the review worksheet and the fold pass), so
    nothing in this repo mints one yet — the kind is accepted and validated, and unreachable in
    practice until that lands. This test is what pins the contract SC61 must satisfy."""
    t = verifier(binding_kind="attested", binding_ref="frm_binding_0001")
    assert ct.grade(t)[:2] == ("Verified", "Attested")


def test_attested_does_not_require_the_statements_to_match():
    """The reason `attested` exists at all: it binds a claim that FOLLOWS FROM the proposition
    without being it. If this ever starts raising, someone applied the identity rule to both
    kinds and deleted the useful half."""
    assert verifier(decided_proposition=OTHER, binding_kind="attested",
                    binding_ref="frm_binding_0002").binding_ref == "frm_binding_0002"


@pytest.mark.parametrize("kind", ["identity", "attested"])
def test_a_binding_with_nothing_on_the_other_end_is_refused(kind):
    """CATCHES a binding declared over an absent proposition — a claim bound to nothing, which
    would grade above `Judged` while recording strictly less than an unbound tuple does."""
    with pytest.raises(ct.ProjectionError, match="no `decided_proposition`"):
        verifier(decided_proposition="", binding_kind=kind, binding_ref="frm_x")


def test_an_unknown_binding_kind_is_refused():
    with pytest.raises(ct.ProjectionError, match="binding_kind must be one of"):
        verifier(binding_kind="probably")


def test_an_unknown_source_class_on_the_tuple_is_refused():
    """CATCHES a class arriving by typo. A tuple whose class is misspelled would silently be
    graded... by nothing, since the cap keys on an exact match."""
    with pytest.raises(ct.ProjectionError, match="source_class must be one of"):
        tup(source_class="verifiers")


def test_the_default_class_is_measurement():
    """MUTATION for the test above, and the back-compat pin: every adapter in this repo
    constructs `ClaimTuple` without naming a class, and must keep landing in the same one."""
    assert tup().source_class == ct.MEASUREMENT_CLASS


# --- nothing else moved ----------------------------------------------------------------------

def test_a_decided_proposition_alone_never_caps_a_measurement_tuple():
    """CATCHES the scoping mistake that looks most natural: capping on "has a decided_proposition"
    rather than on the declared class.

    Several existing adapters could legitimately record what a check decided while remaining
    measurement-class, and scoping the cap on the field would re-grade all of them. The class is
    a deliberate registration; the field is data.
    """
    assert ct.grade(tup()) == ct.grade(tup(decided_proposition=OTHER))


@pytest.mark.parametrize("over, expected", [
    (dict(protocol_id="", reps=None, date="", attestation_path="", attestation_sha256=""),
     ("Judged", "T0")),
    (dict(protocol_id="", reps=None, attestation_path="", attestation_sha256="",
          attestation_locator="run-7#trial-3"), ("Judged", "Located")),
    (dict(attestation_path="", attestation_sha256=""), ("Verified", "Located")),
    (dict(attestation_sha256=""), ("Witnessed", "Anchored")),
    (dict(attestation_path="nope/x.json"), ("Witnessed", "Anchored")),
    (dict(), ("Witnessed", "Attested")),
])
def test_the_measurement_ladder_is_bit_for_bit_what_it_was(over, expected):
    """CATCHES the post-step leaking onto the class that carries the whole existing corpus. Every
    rung of the ladder, re-asserted at the value it had before SC56 existed."""
    q, t, reasons = ct.grade(tup(**over))
    assert (q, t) == expected
    assert not any("SC56" in r or "verifier" in r for r in reasons)


def test_the_literature_ladder_is_unchanged():
    """CATCHES the cap being applied by class NAME comparison gone wrong, or the post-step being
    hung on the wrong side of the ladder registry. Literature caps at `Verified` for its own,
    structural reason and owes nothing to SC56."""
    from adapters.research_intake import grade_for_entry

    for verification in ("stage1-unverified", "dive-verified", "dive-overturned", None):
        g, _ = grade_for_entry({"verification": verification, "url": "https://x"})
        assert g.q_name != "Witnessed"
    assert grade_for_entry({"verification": "dive-verified", "url": "https://x"})[0].q_name == \
        "Verified"


def test_the_cap_is_a_post_step_and_not_a_second_ladder():
    """CATCHES SC56 growing into a verifier ladder. §4.7's invariant — each source class has
    exactly one ladder — must survive this change untouched, and the verifier class is still
    graded by the measurement ladder with a cap applied after it."""
    import adapters.research_intake  # noqa: F401  (registers the literature ladder)

    assert ct.VERIFIER_CLASS not in ct.ladders()
    assert set(ct.ladders()) == {"measurement", "literature"}
    with pytest.raises(ct.ProjectionError, match="already has a ladder"):
        ct.register_ladder("measurement", "sc56/elsewhere.py")(lambda *a: ("Judged", "T0", []))


# --- integrity, not presence: the class cannot be dodged at projection time -------------------

def test_a_verifier_adapter_cannot_emit_measurement_class_tuples():
    """CATCHES the cap being present, tested, and inert — which is worse than absent, because it
    reads as enforced.

    `source_class` is what the cap keys on. A verifier adapter whose projection left the field at
    its default would emit tuples graded by the uncapped ladder, and every verifier adapter in the
    repo today does exactly that. The registration is the authoritative statement of class, so the
    guard stamps it.
    """
    @ct.register("sc56-unstamped", source_class=ct.VERIFIER_CLASS,
                 decided_proposition_field="theorem_statement")
    def _p(native):
        return tup(decided_proposition=native["theorem_statement"])

    out = ct.registered()["sc56-unstamped"]({"theorem_statement": OTHER})
    assert out.source_class == ct.VERIFIER_CLASS
    assert ct.grade(out)[0] == "Judged"


def test_the_same_projection_unregistered_keeps_the_measurement_class():
    """MUTATION for the test above: the stamp must come from the REGISTRATION, not from anything
    about the tuple, or the guard would be indistinguishable from a rule that made every tuple
    carrying a proposition verifier-class."""
    def _p(native):
        return tup(decided_proposition=native["theorem_statement"])

    assert _p({"theorem_statement": OTHER}).source_class == ct.MEASUREMENT_CLASS


def test_the_stamp_survives_a_list_returning_projection():
    """CATCHES the stamp being applied to a single return value only — several adapters here
    project a list of rows per native record, and one unstamped row is one uncapped grade."""
    @ct.register("sc56-list", source_class=ct.VERIFIER_CLASS,
                 decided_proposition_field="theorem_statement")
    def _p(native):
        return [tup(measurement_id="a", decided_proposition=OTHER),
                tup(measurement_id="b", decided_proposition=OTHER)]

    out = ct.registered()["sc56-list"]({})
    assert [t.source_class for t in out] == [ct.VERIFIER_CLASS, ct.VERIFIER_CLASS]


def test_a_measurement_projection_is_still_stored_unwrapped():
    """CATCHES the stamping guard leaking onto the classes that must not carry it."""
    def _p(native):
        return tup()

    ct.register("sc56-measurement")(_p)
    assert ct.registered()["sc56-measurement"] is _p


def test_an_already_verifier_class_tuple_is_returned_unchanged():
    """MUTATION for the stamping tests: an adapter that DOES declare the class must not have its
    tuple rebuilt behind its back (rebuilding drops nothing today, and this is what notices if a
    future field makes that untrue)."""
    made = verifier()

    @ct.register("sc56-declared", source_class=ct.VERIFIER_CLASS,
                 decided_proposition_field="theorem_statement")
    def _p(native):
        return made

    assert ct.registered()["sc56-declared"]({}) is made


# --- the binding reaches the ledger ----------------------------------------------------------

def test_the_binding_rides_in_the_claim_frame_beside_the_proposition():
    """CATCHES the binding being validated and then dropped. Adjacency is the point: a reader of
    the claim frame sees what was decided AND what licenses reading it as this claim."""
    frames = ct.to_frames(verifier(decided_proposition=SAME, binding_kind="identity"),
                          as_of="t", adapter_id="probe/v1")
    claim = next(f for f in frames if f["frame_type"].endswith("claim_proposed/v1"))
    assert claim["assertion"]["binding_kind"] == "identity"
    assert claim["assertion"]["decided_proposition"] == SAME


def test_an_attested_binding_carries_its_reference_into_the_frame():
    """CATCHES a binding recorded without the judgment it rests on — unresolvable on read, which
    is the same hole `decided_proposition` exists to close one level down."""
    frames = ct.to_frames(verifier(binding_kind="attested", binding_ref="frm_binding_0003"),
                          as_of="t", adapter_id="probe/v1")
    claim = next(f for f in frames if f["frame_type"].endswith("claim_proposed/v1"))
    assert claim["assertion"]["binding_ref"] == "frm_binding_0003"


def test_a_tuple_without_a_binding_emits_the_byte_identical_assertion():
    """The back-compat pin. Adding either key unconditionally would move the frame_id of every
    claim frame in a 12,479-frame ledger to record the absence of a field nobody wrote."""
    frames = ct.to_frames(tup(), as_of="t", adapter_id="probe/v1")
    claim = next(f for f in frames if f["frame_type"].endswith("claim_proposed/v1"))
    assert set(claim["assertion"]) == {"claim_id", "display_text", "source_id"}


def test_the_capped_grade_is_what_reaches_the_evidence_frame():
    """CATCHES a cap applied in `grade()` but bypassed on the path that actually writes the
    ledger — the grade a consumer reads is the one in the frame, not the one a test called."""
    frames = ct.to_frames(verifier(), as_of="t", adapter_id="probe/v1")
    sup = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assert sup["assertion"]["grade"] == {"Q": "Judged", "T": "Attested"}
    assert any("not bound to the claim" in r for r in sup["provenance"]["grade_reasons"])
