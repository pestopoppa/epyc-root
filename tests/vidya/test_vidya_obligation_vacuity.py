"""SC71 — an obligation with an empty required-set is REFUSED, never reported satisfied.

`derive_obligations` evaluated `all: []` as vacuous truth, so an obligation whose satisfaction
condition required nothing was reported SATISFIED — "nothing to check" read identically to
"everything checked". That fills an absence the pilot spec says must be recorded, never filled
(§4.7), and it is the same fail-open shape as `blocked = 0` in the fan-out corpus: an empty set
under `all` manufactures a clean bill of health out of the absence of any requirement.

The condition language is deliberately capped and anything that does not fit "routes to explicit
human review rather than growing the language" (spec §10) — an empty combinator set is malformed in
both truth positions: `all: []` manufactures satisfaction from nothing, and `any: []` declares an
obligation that can never fire, which is a noiseless dead requirement. Both are definitional
errors, refused the same way an unknown predicate is refused.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import lattice as lat  # noqa: E402
from fold import fold  # noqa: E402
from impact import Obligation, derive_obligations  # noqa: E402

NOW = "2026-09-07T12:00:00Z"
FLOOR = lat.parse_grade("Verified/Anchored")


def _ob(**kw):
    base = dict(
        obligation_id="obl-1", title="Revise the section",
        activation={"belief_state_in": {"claim_id": "c", "states": ["Opposed", "Unknown"]}},
        satisfaction={"review_status": "accepted"},
        authority_frame="frm-approval",
    )
    base.update(kw)
    return Obligation(**base)


def _res():
    return fold([], as_of=NOW)


def test_an_empty_all_set_in_satisfaction_is_refused_not_satisfied():
    """CATCHES the vacuous report: an obligation with an empty required-set graded SATISFIED —
    the exact shape the audit found."""
    with pytest.raises(ValueError, match="empty"):
        derive_obligations([_ob(satisfaction={"all": []})], _res(), floor=FLOOR)


def test_an_empty_all_set_in_activation_is_refused_not_open():
    """The same vacuous truth on the other side: `all: []` activation would OPEN an obligation
    with no conditions — the system granting itself work on the strength of an absence."""
    with pytest.raises(ValueError, match="empty"):
        derive_obligations([_ob(activation={"all": []})], _res(), floor=FLOOR)


def test_an_empty_any_set_is_refused_as_a_dead_requirement():
    """CATCHES the sibling defect: `any: []` can never fire, so an obligation carrying it can
    never be satisfied or reopened — a noiseless dead requirement is a definitional error too."""
    with pytest.raises(ValueError, match="empty"):
        derive_obligations([_ob(satisfaction={"any": []})], _res(), floor=FLOOR)


def test_refusals_do_not_swallow_the_nesting_cap():
    """Nested combinators were already refused by the one-level cap before SC71; the empty-set
    guard must not change that boundary."""
    with pytest.raises(ValueError, match="nesting is capped"):
        derive_obligations(
            [_ob(activation={"any": [{"all": [{"review_status": "accepted"}]}]})],
            _res(), floor=FLOOR)


def test_non_empty_combinators_still_evaluate():
    """MUTATION for the refusals above: the guard must bite on the empty set, not on the
    combinators themselves."""
    out = derive_obligations(
        [_ob(satisfaction={"all": [{"review_status": "accepted"}]})], _res(), floor=FLOOR,
        context={"review_status": "accepted"})
    assert out[0].state == "satisfied"
