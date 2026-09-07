"""SC57 — a verifier-class adapter must record WHAT the check decided, not only that it passed.

Spec: docs/design/vidya-pilot-spec.md §4.7 (the ingestion contract: project, never grade).

A machine-checked verdict certifies the proposition the checker decided, and nothing binds that
proposition to the claim someone later cites it for. `intake-1307#05`: the certificate "does not
certify individual mathematical truth". `intake-1307#00` is the existence proof that the resulting
gap is large — an automated check labelled 73.6% of proved artifacts non-trivial-and-correct where
a manual audit put faithfulness far lower (a reweighted projection from a 45-example
single-annotator audit: admissible that the gap exists, never as a rate).

So the registry refuses a verifier-class adapter that emits pass/fail alone. Two refusals, because
there are two ways to emit pass/fail alone: never declaring where the proposition comes from
(refused at import), and declaring it and then leaving it empty (refused at projection).

**Every positive here is paired with a mutation** that makes the same call succeed, because a
refusal test that would also pass against a function which refuses EVERYTHING proves nothing.

And the whole file exists under one prohibition: SC57 adds a projection rule, never a grading rule.
`test_grading_is_untouched_by_the_decided_proposition` and `test_the_verifier_class_registers_no_
ladder` are the tests that fail if someone later reaches for a second ladder.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402

PROPOSITION = "for every input list, sort(xs) is a sorted permutation of xs"


def tup(**over):
    base = dict(measurement_id="v1", metric="proof_obligations_discharged", value=1,
                date="2026-09-07", category="CANDIDATE", claim="the sort routine is correct")
    base.update(over)
    return ct.ClaimTuple(**base)


# --- registration-time refusal --------------------------------------------------------------

def test_a_verifier_that_names_no_proposition_field_is_refused_at_registration():
    """CATCHES: an adapter registering as a verifier while projecting only a boolean.

    The declaration is what makes the refusal happen at import time rather than after the first
    run has already been recorded — the retrofit that is never possible.
    """
    with pytest.raises(ct.ProjectionError, match="pass/fail alone"):
        ct.register("sc57-undeclared", source_class=ct.VERIFIER_CLASS)


def test_the_same_registration_succeeds_once_the_field_is_named():
    """MUTATION for the test above. Without this, that test would also pass against a registry
    that refused every verifier registration unconditionally."""

    @ct.register("sc57-declared", source_class=ct.VERIFIER_CLASS,
                 decided_proposition_field="theorem_statement")
    def _p(native):
        return tup(decided_proposition=PROPOSITION)

    assert "sc57-declared" in ct.registered()
    assert ct.source_classes()["sc57-declared"] == ct.VERIFIER_CLASS


def test_an_unknown_source_class_is_refused():
    """CATCHES: a new class of warrant arriving by typo rather than by decision (§4.7)."""
    with pytest.raises(ct.ProjectionError, match="unknown source_class"):
        ct.register("sc57-typo", source_class="verifiers")


def test_the_proposition_field_belongs_to_the_verifier_class_only():
    """CATCHES: a measurement adapter borrowing verifier vocabulary and quietly acquiring a second
    contract. MUTATION is `test_the_same_registration_succeeds_once_the_field_is_named`, where the
    identical kwarg is accepted for the class that owns it."""
    with pytest.raises(ct.ProjectionError, match="verifier class only"):
        ct.register("sc57-misplaced", decided_proposition_field="theorem_statement")


def test_a_duplicate_projection_name_is_still_refused_after_the_wrapping():
    """CATCHES: the `_ORIGINALS` refactor silently disabling duplicate detection — the registry
    now stores a wrapper for verifier classes, so comparing the STORED function to the incoming
    one would never match again."""

    @ct.register("sc57-dup", source_class=ct.VERIFIER_CLASS,
                 decided_proposition_field="theorem_statement")
    def _p(native):
        return tup(decided_proposition=PROPOSITION)

    with pytest.raises(ct.ProjectionError, match="already registered"):
        ct.register("sc57-dup", source_class=ct.VERIFIER_CLASS,
                    decided_proposition_field="theorem_statement")(lambda n: tup())


def test_re_registering_the_identical_function_is_idempotent():
    """MUTATION for the test above: duplicate detection must fire on a DIFFERENT function, not on
    a module being imported twice, or a re-import would refuse itself."""

    def _p(native):
        return tup(decided_proposition=PROPOSITION)

    ct.register("sc57-idem", source_class=ct.VERIFIER_CLASS,
                decided_proposition_field="theorem_statement")(_p)
    ct.register("sc57-idem", source_class=ct.VERIFIER_CLASS,
                decided_proposition_field="theorem_statement")(_p)   # must not raise


# --- projection-time refusal: declared, then left empty --------------------------------------

def test_a_declared_field_left_empty_is_refused_when_the_projection_runs():
    """CATCHES: the registration-time declaration being satisfiable by a comment. The guard is the
    backstop that makes the declaration mean something."""

    @ct.register("sc57-empty", source_class=ct.VERIFIER_CLASS,
                 decided_proposition_field="theorem_statement")
    def _p(native):
        return tup()          # boolean-shaped: the check passed, and that is all it says

    with pytest.raises(ct.ProjectionError, match="must carry `decided_proposition`"):
        ct.registered()["sc57-empty"]({"status": "pass"})


def test_the_same_projection_is_accepted_once_it_names_the_proposition():
    """MUTATION for the test above."""

    @ct.register("sc57-filled", source_class=ct.VERIFIER_CLASS,
                 decided_proposition_field="theorem_statement")
    def _p(native):
        return tup(decided_proposition=native["theorem_statement"])

    out = ct.registered()["sc57-filled"]({"theorem_statement": PROPOSITION, "status": "pass"})
    assert out.decided_proposition == PROPOSITION


@pytest.mark.parametrize("verdict", ["pass", "PASS", "failed", "true", "1", "ok", "unsat",
                                     "verified", "Valid."])
def test_a_bare_verdict_token_is_not_a_proposition(verdict):
    """CATCHES: the field being satisfied by moving the boolean into it. 'pass' is what the check
    ANSWERED; the contract is about what it ASSERTED."""
    with pytest.raises(ct.ProjectionError, match="bare verdict"):
        ct.check_decided_proposition(verdict, where="probe")


def test_a_real_proposition_containing_a_verdict_word_is_accepted():
    """MUTATION for the parametrized test: the check must be on the WHOLE value, not a substring
    scan, or every honest proposition mentioning 'valid' would be refused."""
    assert ct.check_decided_proposition(
        "every parsed manifest is valid under schema v2", where="probe")


def test_a_list_returning_verifier_projection_is_checked_element_by_element():
    """CATCHES: an adapter smuggling an unpinned tuple through by returning several at once —
    several adapters here project a list of rows per record."""

    @ct.register("sc57-list", source_class=ct.VERIFIER_CLASS,
                 decided_proposition_field="theorem_statement")
    def _p(native):
        return [tup(measurement_id="v1", decided_proposition=PROPOSITION),
                tup(measurement_id="v2")]

    with pytest.raises(ct.ProjectionError, match="must carry `decided_proposition`"):
        ct.registered()["sc57-list"]({})


# --- project, never grade: the invariant SC57 must not cross --------------------------------

def test_the_verifier_class_registers_no_ladder():
    """CATCHES: SC57 growing into a second grading rule. §4.7 — the carrier is shared, the ladder
    is not, and a verifier tuple is still graded by `claim_tuple.grade()`.

    The `measurement` assertion is the anti-vacuity half: without it this test would pass against
    an empty ladder registry, i.e. against a broken import.
    """
    assert "measurement" in ct.ladders()
    assert ct.VERIFIER_CLASS not in ct.ladders()


def test_grading_is_untouched_by_the_decided_proposition():
    """CATCHES: the proposition acquiring grade weight. SC56 — the statement-binding precondition
    that WOULD change grading semantics — is deliberately not implemented; if this test starts
    failing, something implemented it by accident."""
    plain = tup(protocol_id="P-1", reps=3, attestation_locator="proof:x")
    pinned = tup(protocol_id="P-1", reps=3, attestation_locator="proof:x",
                 decided_proposition=PROPOSITION)
    assert ct.grade(plain) == ct.grade(pinned)


def test_a_measurement_projection_is_stored_unwrapped():
    """CATCHES: the guard leaking onto classes that must not carry it — every existing adapter."""

    def _p(native):
        return tup()

    ct.register("sc57-measurement")(_p)
    assert ct.registered()["sc57-measurement"] is _p


# --- the proposition reaches the ledger, beside the claim ------------------------------------

def test_the_proposition_rides_in_the_claim_frame():
    """CATCHES: the field being validated and then dropped on the floor — recorded nowhere is
    identical to never captured, and retrofit is impossible."""
    emitted = ct.to_frames(tup(decided_proposition=PROPOSITION), as_of="t", adapter_id="probe/v1")
    claim = next(f for f in emitted if f["frame_type"].endswith("claim_proposed/v1"))
    assert claim["assertion"]["decided_proposition"] == PROPOSITION


def test_a_tuple_without_one_emits_the_byte_identical_frame_it_always_did():
    """MUTATION/regression pair for the test above, and the back-compat pin: adding the key
    unconditionally would move the frame_id of every measurement frame in a 12,479-frame ledger to
    record the absence of a field nobody wrote."""
    emitted = ct.to_frames(tup(), as_of="t", adapter_id="probe/v1")
    claim = next(f for f in emitted if f["frame_type"].endswith("claim_proposed/v1"))
    assert "decided_proposition" not in claim["assertion"]
    assert set(claim["assertion"]) == {"claim_id", "display_text", "source_id"}


def test_the_tuple_refuses_a_non_string_proposition():
    with pytest.raises(ct.ProjectionError, match="decided_proposition must be a string"):
        tup(decided_proposition=True)
