from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import progress_plots  # noqa: E402
from src.autopilot_core.tier_specs import DEFAULT_FRONTIER_TIER  # noqa: E402


@dataclass
class _Entry:
    trial_id: int
    tier: int
    quality: float
    speed: float = 10.0
    cost: float = 0.1
    reliability: float = 1.0
    species: str = "seeder"
    bug_corrupted_by: str = ""
    pareto_status: str = "dominated"
    eval_details: dict = field(default_factory=dict)


@dataclass
class _ArchiveEntry:
    trial_id: int
    eval_tier: int
    objectives: tuple[float, float, float, float]
    species: str = "seeder"

    def to_dict(self) -> dict:
        return {
            "trial_id": self.trial_id,
            "eval_tier": self.eval_tier,
            "objectives": list(self.objectives),
            "species": self.species,
        }


class _Archive:
    def __init__(self) -> None:
        self._frontiers = {
            DEFAULT_FRONTIER_TIER: [_ArchiveEntry(2, 1, (1.5, 20.0, -0.1, 1.0))],
            2: [_ArchiveEntry(4, 2, (2.2, 8.0, -0.1, 1.0))],
        }
        self._all_entries = [
            _ArchiveEntry(1, 0, (2.4, 30.0, -0.1, 1.0)),
            self._frontiers[DEFAULT_FRONTIER_TIER][0],
            _ArchiveEntry(3, 1, (1.0, 10.0, -0.1, 1.0)),
            self._frontiers[2][0],
        ]

    def hypervolume_trend(self, tier=None):
        assert tier in {DEFAULT_FRONTIER_TIER, 2}
        return {
            DEFAULT_FRONTIER_TIER: [(2, 1.0)],
            2: [(4, 2.0)],
        }[tier]

    def frontier(self, tier=None):
        assert tier in {DEFAULT_FRONTIER_TIER, 2}
        return list(self._frontiers[tier])

    def is_frontier_eligible(self, entry) -> bool:
        return entry.eval_tier > 0


class _Journal:
    def __init__(self) -> None:
        self._entries = [
            _Entry(
                1,
                0,
                2.4,
                pareto_status="frontier",
                eval_details={"per_suite_quality": {"sentinel": 2.4}},
            ),
            _Entry(
                2,
                1,
                1.5,
                pareto_status="frontier",
                eval_details={"per_suite_quality": {"t1": 1.5}},
            ),
            _Entry(
                3,
                1,
                2.4,
                bug_corrupted_by="ec9622d",
                pareto_status="frontier",
                eval_details={"per_suite_quality": {"stale": 2.4}},
            ),
            _Entry(
                99,
                1,
                2.2,
                pareto_status="frontier",
                eval_details={"per_suite_quality": {"pre_epoch": 2.2}},
            ),
        ]

    def all_entries(self):
        return list(self._entries)

    def species_effectiveness(self):
        return {}


def test_generate_all_plots_filters_t0_and_bug_corrupted_points(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        progress_plots,
        "plot_hypervolume_trend",
        lambda history, output_dir=None: captured.setdefault("hv", history) or tmp_path / "hv.png",
    )

    # `excluded_by_tier` was added to plot_pareto_frontier_2d after this double was
    # written. `generate_all_plots` catches the resulting TypeError and only logs
    # "Error generating plots", so the stale signature turned into an empty
    # `captured` dict rather than a visible failure — keep this stub in step with
    # the real signature.
    def _frontier(
        frontier,
        dominated,
        output_dir=None,
        *,
        frontiers_by_tier=None,
        dominated_by_tier=None,
        excluded_by_tier=None,
    ):
        captured["frontier"] = frontier
        captured["dominated"] = dominated
        captured["frontiers_by_tier"] = frontiers_by_tier
        captured["dominated_by_tier"] = dominated_by_tier
        captured["excluded_by_tier"] = excluded_by_tier
        return tmp_path / "frontier.png"

    monkeypatch.setattr(progress_plots, "plot_pareto_frontier_2d", _frontier)
    monkeypatch.setattr(
        progress_plots,
        "plot_species_effectiveness",
        lambda eff, output_dir=None: (
            captured.setdefault("species", eff) or tmp_path / "species.png"
        ),
    )

    def _suite(data, output_dir=None):
        captured["suite_data"] = data
        return tmp_path / "suite.png"

    monkeypatch.setattr(progress_plots, "plot_per_suite_quality", _suite)
    monkeypatch.setattr(
        progress_plots,
        "plot_memory_convergence",
        lambda td_errors, output_dir=None: tmp_path / "memory.png",
    )

    def _timeline(data, output_dir=None):
        captured["timeline"] = data
        return tmp_path / "timeline.png"

    monkeypatch.setattr(progress_plots, "plot_trial_timeline", _timeline)

    progress_plots.generate_all_plots(_Archive(), _Journal(), output_dir=tmp_path)

    assert captured["hv"] == {1: [(2, 1.0)], 2: [(4, 2.0)]}
    assert [p["trial_id"] for p in captured["frontier"]] == [2]
    assert [p["trial_id"] for p in captured["dominated"]] == [3]
    assert {
        tier: [p["trial_id"] for p in pts]
        for tier, pts in captured["frontiers_by_tier"].items()
    } == {1: [2], 2: [4]}
    assert {
        tier: [p["trial_id"] for p in pts]
        for tier, pts in captured["dominated_by_tier"].items()
    } == {1: [3], 2: []}
    assert captured["species"] == {"seeder": {"total": 1, "pareto": 1, "rate": 1.0}}
    assert [p["trial_id"] for p in captured["suite_data"]] == [2]
    assert [p["trial_id"] for p in captured["timeline"]] == [2]


def test_frontier_envelope_2d_keeps_2d_nondominated_sorted_by_speed() -> None:
    # objectives = (quality, speed, -cost, reliability); envelope maximizes
    # quality and speed. Returns (speed, quality) pairs sorted by speed.
    pts = [
        {"objectives": [1.0, 60.0, -0.1, 1.0]},  # fastest, low quality — on edge
        {"objectives": [2.0, 30.0, -0.1, 1.0]},  # best quality, slower — on edge
        {"objectives": [1.0, 20.0, -0.1, 1.0]},  # 2D-dominated by the first
        {"objectives": [1.5, 10.0, -0.1, 1.0]},  # 2D-dominated by the second
    ]
    assert progress_plots._frontier_envelope_2d(pts) == [(30.0, 2.0), (60.0, 1.0)]


def test_frontier_envelope_2d_degenerate_cases() -> None:
    # A single frontier member cannot form a line (len < 2) — this is the case
    # that historically rendered as "scatter but no frontier".
    assert progress_plots._frontier_envelope_2d(
        [{"objectives": [1.0, 2.0, -0.1, 1.0]}]
    ) == [(2.0, 1.0)]
    assert progress_plots._frontier_envelope_2d([]) == []


def test_plot_pareto_frontier_2d_renders_file_with_frontier_line(tmp_path: Path) -> None:
    # Exercises the real matplotlib path (envelope length 2 → ax.plot line drawn)
    # so the new frontier-line code can't raise on a normal frontier.
    frontier = [
        {"objectives": [2.0, 30.0, -0.1, 1.0], "species": "seeder"},
        {"objectives": [1.0, 60.0, -0.1, 1.0], "species": "structural_lab"},
    ]
    dominated = [{"objectives": [1.0, 20.0, -0.1, 1.0], "species": "seeder"}]
    out = progress_plots.plot_pareto_frontier_2d(frontier, dominated, tmp_path)
    assert out.exists() and out.stat().st_size > 0
