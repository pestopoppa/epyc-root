"""Pareto archive tier semantics.

Tier-0 is a fast-reject sentinel eval with 10-question granularity. It is useful
for quick screening and audit history, but it must not define the production
Pareto frontier or baseline archive-max guard.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from pareto_archive import (  # noqa: E402
    PARETO_STATUS_TIER_EXCLUDED,
    ParetoArchive,
    ParetoEntry,
    pareto_archive_from_journal_rows,
)


def _entry(
    trial_id: int,
    *,
    tier: int,
    q: float,
    speed: float = 50.0,
    cost: float = -0.5,
    reliability: float = 0.9,
    species: str = "",
    reasoning: str = "",
) -> ParetoEntry:
    return ParetoEntry(
        trial_id=trial_id,
        objectives=(q, speed, cost, reliability),
        eval_tier=tier,
        species=species,
        reasoning=reasoning,
    )


def test_t0_entry_is_audit_only_not_frontier(tmp_path: Path) -> None:
    archive = ParetoArchive(state_path=tmp_path / "state.json")

    status = archive.update(_entry(7, tier=0, q=2.4))

    assert status == PARETO_STATUS_TIER_EXCLUDED
    assert len(archive._all_entries) == 1
    assert archive.frontier() == []
    assert archive.hypervolume_trend() == []
    assert archive.summary()["frontier_size"] == 0


def test_t0_quality_does_not_dominate_t1_frontier(tmp_path: Path) -> None:
    archive = ParetoArchive(state_path=tmp_path / "state.json")

    t0_status = archive.update(_entry(7, tier=0, q=2.4, speed=80.0))
    t1_status = archive.update(_entry(118, tier=1, q=1.895, speed=71.0))

    assert t0_status == PARETO_STATUS_TIER_EXCLUDED
    assert t1_status == "frontier"
    assert [e.trial_id for e in archive.frontier()] == [118]
    assert archive.summary()["best_quality"] == 1.895


def test_load_rebuilds_frontier_without_legacy_t0_pollution(tmp_path: Path) -> None:
    """Existing state may have T1 entries in all_entries that were kept off the
    frontier only because saturated T0 entries dominated them. Loading must
    rebuild the frontier from all eligible T1/T2 entries, not merely filter the
    old frontier list.
    """
    state_path = tmp_path / "state.json"
    t0 = _entry(38, tier=0, q=2.4, speed=20.0).to_dict()
    t1 = _entry(118, tier=1, q=1.895, speed=71.0).to_dict()
    state_path.write_text(json.dumps({
        "trial_counter": 569,
        "pareto_archive": {
            "frontier": [t0],
            "all_entries": [t0, t1],
            "hypervolume_history": [[38, 10.0]],
        },
    }))

    archive = ParetoArchive(state_path=state_path)

    assert [e.trial_id for e in archive.frontier()] == [118]
    assert archive.summary()["best_quality"] == 1.895


def test_readonly_archive_from_journal_rows_matches_read_surface() -> None:
    rows = [
        {
            "trial_id": 1,
            "tier": 0,
            "quality": 2.4,
            "speed": 80.0,
            "cost": 0.5,
            "reliability": 1.0,
            "timestamp": "2026-06-14T00:00:01+00:00",
        },
        {
            "trial_id": 2,
            "tier": 1,
            "quality": 1.7,
            "speed": 40.0,
            "cost": 0.4,
            "reliability": 0.9,
            "timestamp": "2026-06-14T00:00:02+00:00",
            "species": "seed",
        },
        {
            "trial_id": 3,
            "tier": 1,
            "quality": 1.8,
            "speed": 45.0,
            "cost": 0.4,
            "reliability": 0.9,
            "timestamp": "2026-06-14T00:00:03+00:00",
            "species": "seed",
        },
    ]

    archive = pareto_archive_from_journal_rows(rows, current_run_only=False)

    assert archive is not None
    assert archive.read_only is True
    assert archive.frontier_size() == 1
    assert [entry.trial_id for entry in archive.frontier()] == [3]
    assert [trial_id for trial_id, _hv in archive.hypervolume_trend()] == [2, 3]
    assert "T1" in archive.summary_text()


def test_readonly_archive_refuses_mutation_methods() -> None:
    archive = ParetoArchive.from_archive_payload(
        {
            "all_entries": [
                _entry(2, tier=1, q=1.7).to_dict(),
            ],
        }
    )

    assert archive.read_only is True
    assert [entry.trial_id for entry in archive.frontier()] == [2]
    for mutate in (
        lambda: archive.update(_entry(3, tier=1, q=1.8)),
        lambda: archive.upsert_representative(
            "fp",
            1,
            (1.8, 40.0, -0.5, 0.9),
            trial_id=3,
        ),
        lambda: archive.mark_production_best(2),
        lambda: archive.load({"pareto_archive": {}}),
    ):
        try:
            mutate()
        except RuntimeError as exc:
            assert "read-only" in str(exc)
        else:
            raise AssertionError("read-only archive mutation unexpectedly succeeded")


def test_production_best_refuses_non_default_tier_frontier(tmp_path: Path) -> None:
    archive = ParetoArchive(state_path=tmp_path / "state.json")

    assert archive.update(_entry(20, tier=2, q=1.2)) == "frontier"
    assert archive.update(_entry(30, tier=3, q=0.4)) == "frontier"

    assert archive.mark_production_best(20) is False
    assert archive.mark_production_best(30) is False
    assert archive.production_best() is None

    assert archive.update(_entry(10, tier=1, q=1.8)) == "frontier"
    assert archive.mark_production_best(10) is True
    assert archive.production_best().trial_id == 10


def test_generic_raw_payload_loader_is_not_public_api() -> None:
    assert not hasattr(ParetoArchive, "load_archive_payload")


def test_stepping_stones_surface_dominated_diverse_near_misses(tmp_path: Path) -> None:
    archive = ParetoArchive(state_path=tmp_path / "state.json")

    assert archive.update(_entry(1, tier=1, q=2.0, speed=50.0, reliability=1.0)) == "frontier"
    assert archive.update(_entry(2, tier=1, q=1.8, speed=70.0, reliability=1.0)) == "frontier"
    assert archive.update(
        _entry(
            3,
            tier=1,
            q=1.7,
            speed=45.0,
            reliability=0.95,
            species="prompt_forge",
            reasoning='{"type": "prompt_mutation"}',
        )
    ) == "dominated"
    assert archive.update(
        _entry(
            4,
            tier=1,
            q=1.91,
            speed=49.0,
            reliability=0.99,
            species="prompt_forge",
            reasoning='{"type": "prompt_mutation"}',
        )
    ) == "dominated"
    assert archive.update(
        _entry(
            5,
            tier=1,
            q=1.72,
            speed=68.0,
            reliability=0.98,
            species="numeric_swarm",
            reasoning='{"type": "numeric_trial"}',
        )
    ) == "dominated"

    rows = archive.stepping_stones(limit=2)

    assert [row["trial_id"] for row in rows] == [4, 5]
    assert {(row["species"], row["action"]) for row in rows} == {
        ("prompt_forge", "prompt_mutation"),
        ("numeric_swarm", "numeric_trial"),
    }
    assert {entry.trial_id for entry in archive.frontier()} == {1, 2}


def test_stepping_stones_text_is_explicitly_observe_only(tmp_path: Path) -> None:
    archive = ParetoArchive(state_path=tmp_path / "state.json")
    archive.update(_entry(1, tier=1, q=2.0, speed=50.0, reliability=1.0))
    archive.update(
        _entry(
            2,
            tier=1,
            q=1.9,
            speed=45.0,
            reliability=0.95,
            species="structural_lab",
            reasoning='{"type": "structural_experiment"}',
        )
    )

    text = archive.stepping_stones_text()

    assert "Observe-only" in text
    assert "not replay authorization" in text
    assert "#2 [structural_lab:structural_experiment]" in text
