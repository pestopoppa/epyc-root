"""W3e — objective consumers read axes by NAME, not by position.

The regression half replays two archives reconstructed from the stored autopilot journal
(legacy ``legacy_4d_v1`` and post-flip ``task_rate_4d_v1``) and asserts every
dominance-derived read matches the golden values captured with the PRE-W3e positional
code (``tests/fixtures/w3e_dominance_replay.json``; provenance in its ``_provenance``).

The forward half proves the point of W3e: a tier whose declared axes omit ``neg_cost``
is read correctly instead of shifting reliability into the cost slot.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.autopilot import safety_gate  # noqa: E402
from scripts.autopilot.pareto_archive import ParetoArchive, ParetoEntry  # noqa: E402
from src.autopilot_core import tier_specs  # noqa: E402
from src.autopilot_core.pareto_math import dominates  # noqa: E402
from src.autopilot_core.tier_specs import (  # noqa: E402
    OBJECTIVE_AXES_4D,
    OBJECTIVE_AXIS_NEG_COST,
    OBJECTIVE_AXIS_QUALITY,
    OBJECTIVE_AXIS_RATE,
    OBJECTIVE_AXIS_RELIABILITY,
    ObjectiveShapeError,
    TierSpec,
    has_objective_axis,
    objective_axes,
    objective_axis_index,
    objective_value,
    objectives_match_axes,
)

FIXTURE = ROOT / "tests" / "fixtures" / "w3e_dominance_replay.json"
_DATA = json.loads(FIXTURE.read_text())
POLICIES = sorted(_DATA["archives"])


def _norm(value):
    return json.loads(json.dumps(value))


def _replay(policy: str) -> tuple[ParetoArchive, dict]:
    archive = ParetoArchive.from_archive_payload(_DATA["archives"][policy])
    return archive, _DATA["golden"][policy]


def test_fixture_covers_both_policies_and_real_frontiers() -> None:
    assert POLICIES == ["legacy_4d_v1", "task_rate_4d_v1"]
    for policy in POLICIES:
        archive, golden = _replay(policy)
        assert len(archive._all_entries) > 300
        assert set(golden["tiers"]) == {"1", "2"}
        assert all(golden["tiers"][t]["frontier_ids"] for t in golden["tiers"])


@pytest.mark.parametrize("policy", POLICIES)
def test_tier_overview_identical(policy: str) -> None:
    archive, golden = _replay(policy)
    assert archive.tier_overview() == golden["tier_overview"]


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("tier", [1, 2])
def test_dominance_and_frontier_identical(policy: str, tier: int) -> None:
    archive, golden = _replay(policy)
    expected = golden["tiers"][str(tier)]
    assert sorted(e.trial_id for e in archive.frontier(tier)) == expected["frontier_ids"]
    entries = [e for e in archive._all_entries if int(e.eval_tier) == tier]
    pairs = sorted(
        (a.trial_id, b.trial_id)
        for a in entries
        for b in entries
        if a is not b and dominates(a.objectives, b.objectives)
    )
    assert len(pairs) == expected["dominance_pairs_count"]
    assert hashlib.sha256(json.dumps(pairs).encode()).hexdigest() == expected["dominance_pairs_sha256"]


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("tier", [1, 2])
@pytest.mark.parametrize(
    "reader",
    [
        "summary",
        "summary_text",
        "stepping_stones",
        "stepping_stones_text",
        "geometry",
        "geometry_text",
        "bt_tiebreak_topk",
        "parent_utility_ranking",
    ],
)
def test_archive_reads_identical(policy: str, tier: int, reader: str) -> None:
    archive, golden = _replay(policy)
    if reader == "bt_tiebreak_topk":
        actual = archive.bt_tiebreak_topk(k=5, tier=tier)
    else:
        actual = getattr(archive, reader)(tier)
    assert _norm(actual) == golden["tiers"][str(tier)][reader]


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("tier", [1, 2])
def test_summary_key_order_unchanged(policy: str, tier: int) -> None:
    # The fixture is key-sorted, so the pre-W3e literal order is pinned here.
    archive, _golden = _replay(policy)
    assert list(archive.summary(tier)) == [
        "tier",
        "frontier_size",
        "total_entries",
        "hypervolume",
        "best_quality",
        "best_speed",
        "best_neg_cost",
        "hv_slope_50",
    ]


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("tier", [1, 2])
def test_safety_gate_named_reads_identical(policy: str, tier: int, monkeypatch) -> None:
    archive, golden = _replay(policy)
    expected = golden["tiers"][str(tier)]
    monkeypatch.setattr(safety_gate, "_pareto_archive_for_safety_guard", lambda: archive)

    best_q, ids = safety_gate._pareto_frontier_context(tier=tier)
    assert best_q == expected["best_quality"]
    assert sorted(ids) == expected["frontier_ids"]

    for entry in archive.frontier(tier):
        fields = safety_gate.promotion_fields_from_objectives(
            tuple(float(x) for x in entry.objectives), tier
        )
        assert fields == expected["promotion_fields"][str(entry.trial_id)]


# ---------------------------------------------------------------------------
# Axis-name API
# ---------------------------------------------------------------------------


def test_declared_axes_match_the_constructed_vector_order() -> None:
    assert OBJECTIVE_AXES_4D == ("quality", "rate", "neg_cost", "reliability")
    for tier in (0, 1, 2, 3, 99):
        assert objective_axes(tier) == OBJECTIVE_AXES_4D
    row = {
        "quality": 2.0,
        "speed": 14.0,
        "cost": 0.5,
        "reliability": 0.8,
    }
    vector = tier_specs.legacy_objectives_from_row(row)
    assert objective_value(vector, OBJECTIVE_AXIS_QUALITY, 1) == 2.0
    assert objective_value(vector, OBJECTIVE_AXIS_RATE, 1) == 14.0
    assert objective_value(vector, OBJECTIVE_AXIS_NEG_COST, 1) == -0.5
    assert objective_value(vector, OBJECTIVE_AXIS_RELIABILITY, 1) == 0.8


def test_shape_mismatch_raises_instead_of_reading_the_wrong_axis() -> None:
    with pytest.raises(ObjectiveShapeError):
        objective_value((2.0, 14.0, 0.8), OBJECTIVE_AXIS_RELIABILITY, 1)
    with pytest.raises(ObjectiveShapeError):
        objective_value((2.0, 14.0, -0.5, 0.8, 9.9), OBJECTIVE_AXIS_QUALITY, 1)
    with pytest.raises(KeyError):
        objective_axis_index("tokens", 1)
    assert objectives_match_axes((1, 2, 3, 4), 1)
    assert not objectives_match_axes((1, 2, 3), 1)


@pytest.mark.parametrize("objectives", [(), (2.0, 14.0, -0.5), (2.0, 14.0, -0.5, 0.8, 1.0)])
def test_promotion_refuses_a_tuple_that_does_not_match_the_axes(objectives) -> None:
    assert safety_gate.promotion_fields_from_objectives(objectives, 1) is None


# ---------------------------------------------------------------------------
# Forward: a tier that retires the cost axis
# ---------------------------------------------------------------------------

_NO_COST_TIER = 7
_NO_COST_AXES = (OBJECTIVE_AXIS_QUALITY, OBJECTIVE_AXIS_RATE, OBJECTIVE_AXIS_RELIABILITY)


@pytest.fixture
def no_cost_tier(monkeypatch):
    monkeypatch.setitem(
        tier_specs.TIER_SPECS,
        _NO_COST_TIER,
        TierSpec(
            _NO_COST_TIER,
            "T7 (test: cost axis retired)",
            reference_point=(0.0, 0.0, 0.0),
            axes=_NO_COST_AXES,
        ),
    )
    return _NO_COST_TIER


def test_three_axis_tier_reads_reliability_from_its_own_slot(no_cost_tier: int) -> None:
    objectives = (2.5, 60.0, 0.9)
    assert not has_objective_axis(OBJECTIVE_AXIS_NEG_COST, no_cost_tier)
    assert objective_value(objectives, OBJECTIVE_AXIS_RELIABILITY, no_cost_tier) == 0.9
    fields = safety_gate.promotion_fields_from_objectives(objectives, no_cost_tier)
    assert fields == {"quality": 2.5, "speed": 60.0, "reliability": 0.9}


def test_three_axis_tier_archive_renders_without_cost(no_cost_tier: int) -> None:
    archive = ParetoArchive.from_archive_payload(
        {
            "all_entries": [
                ParetoEntry(
                    trial_id=1, objectives=(2.0, 80.0, 0.9), eval_tier=no_cost_tier, species="a"
                ).to_dict(),
                ParetoEntry(
                    trial_id=2, objectives=(2.5, 60.0, 0.7), eval_tier=no_cost_tier, species="b"
                ).to_dict(),
            ]
        }
    )
    summary = archive.summary(no_cost_tier)
    assert "best_neg_cost" not in summary
    assert summary["best_quality"] == 2.5 and summary["best_speed"] == 80.0
    text = archive.summary_text(no_cost_tier)
    assert "#2 [b] q=2.500 s=60.0 r=0.70" in text
    assert "c=" not in text
    geometry = archive.geometry(no_cost_tier)
    assert geometry["blocking_quality"]["trial_id"] == 2
    assert geometry["blocking_speed"]["trial_id"] == 1
