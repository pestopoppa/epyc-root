"""Meta-optimizer budget credit should follow realized information gain."""

from __future__ import annotations

import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

experiment_journal = importlib.import_module("experiment_journal")
meta_optimizer = importlib.import_module("meta_optimizer")

ExperimentJournal = experiment_journal.ExperimentJournal
JournalEntry = experiment_journal.JournalEntry
MetaOptimizer = meta_optimizer.MetaOptimizer


def _entry(trial_id: int, species: str, **kw) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        species=species,
        action_type="seed_batch",
        tier=kw.pop("tier", 1),
        quality=kw.pop("quality", 1.0),
        speed=10.0,
        cost=0.1,
        reliability=1.0,
        pareto_status=kw.pop("pareto_status", "dominated"),
        surprise_score=kw.pop("surprise_score", None),
        bug_corrupted_by=kw.pop("bug_corrupted_by", ""),
        outcome_status=kw.pop("outcome_status", "ok"),
        **kw,
    )


def test_species_effectiveness_prefers_peaf_information_for_budget_rate(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1, "seeder", surprise_score=0.8))
    journal.record(_entry(2, "seeder", surprise_score=0.2))
    journal.record(_entry(3, "prompt_forge", pareto_status="frontier"))

    stats = journal.species_effectiveness()

    assert stats["seeder"]["rate"] == 0.0
    assert stats["seeder"]["information_rate"] == 0.5
    assert stats["seeder"]["budget_rate"] == 0.5
    assert stats["prompt_forge"]["rate"] == 1.0
    assert stats["prompt_forge"]["information_count"] == 0
    assert stats["prompt_forge"]["budget_rate"] == 1.0


def test_species_effectiveness_excludes_untrusted_surprise_from_budget_rate(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1, "seeder", surprise_score=0.9))
    journal.record(_entry(2, "seeder", surprise_score=1.0, bug_corrupted_by="badc0de"))
    journal.record(_entry(3, "seeder", surprise_score=1.0, outcome_status="invalid"))

    stats = journal.species_effectiveness()

    assert stats["seeder"]["information_count"] == 1
    assert stats["seeder"]["information_rate"] == 0.9
    assert stats["seeder"]["budget_rate"] == 0.9


def test_species_effectiveness_adds_clipped_higher_tier_quality_credit(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1, "structural_lab", tier=3, quality=2.4))
    journal.record(_entry(2, "numeric_swarm", pareto_status="frontier"))

    stats = journal.species_effectiveness()

    assert stats["structural_lab"]["rate"] == 0.0
    assert stats["structural_lab"]["higher_tier_quality_count"] == 1
    assert stats["structural_lab"]["higher_tier_quality_rate"] == pytest.approx(0.8)
    assert stats["structural_lab"]["budget_rate"] == pytest.approx(0.12)
    assert stats["numeric_swarm"]["budget_rate"] == 1.0


def test_species_effectiveness_excludes_failed_higher_tier_quality_credit(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            1,
            "seeder",
            tier=3,
            quality=2.4,
            failure_analysis="Quality floor violation",
        )
    )

    stats = journal.species_effectiveness()

    assert stats["seeder"]["higher_tier_quality_count"] == 0
    assert stats["seeder"]["higher_tier_quality_rate"] == 0.0
    assert stats["seeder"]["budget_rate"] == 0.0


def test_rebalance_uses_budget_rate_instead_of_frontier_rate() -> None:
    optimizer = MetaOptimizer()

    budget = optimizer.rebalance(
        species_effectiveness={
            "numeric_swarm": {
                "total": 10,
                "pareto": 0,
                "rate": 0.0,
                "budget_rate": 0.5,
            },
            "prompt_forge": {
                "total": 10,
                "pareto": 10,
                "rate": 1.0,
                "budget_rate": 0.0,
            },
        },
        hv_slope=0.01,
        memory_count=600,
        is_converged=False,
    )

    assert budget.numeric_swarm > budget.prompt_forge


# ── AP-37 diversity-stall detector: DELETED 2026-08-01 ────────────────────────
# The detector was fully built and never once invoked. Its trigger is a
# conjunction of distinct-2 collapse AND semantic-embedding-agreement collapse
# AND a failed Verbalized Sampling recovery probe, held 10 consecutive trials.
# Two of the three signals and both baselines needed inference machinery that was
# never built, so every observation it ever recorded read status="signal_missing"
# while it persisted a growing all-null blob into autopilot_state.json. The tests
# below are the removal regression: they assert the API and the persisted state
# key are gone, so the dead capability cannot silently return.


def test_diversity_stall_api_is_removed_from_meta_optimizer() -> None:
    optimizer = MetaOptimizer()
    for attr in (
        "observe_diversity",
        "diversity_rebalance_due",
        "restore_diversity_state",
        "export_diversity_state",
        "diversity_stall_state",
        "_default_diversity_stall_state",
    ):
        assert not hasattr(optimizer, attr), f"AP-37 leftover on MetaOptimizer: {attr}"
    for const in (
        "DIVERSITY_STALL_STREAK_MIN",
        "DIVERSITY_DISTINCT2_RATIO_THRESHOLD",
        "DIVERSITY_SEMANTIC_DROP_THRESHOLD",
        "DIVERSITY_VS_RECOVERY_THRESHOLD",
        "DIVERSITY_HISTORY_LIMIT",
    ):
        assert not hasattr(meta_optimizer, const), f"AP-37 leftover constant: {const}"
    assert "diversity_stall" not in MetaOptimizer().summary()


def test_rebalance_rejects_diversity_stall_argument() -> None:
    with pytest.raises(TypeError):
        MetaOptimizer().rebalance(
            species_effectiveness={},
            hv_slope=0.01,
            memory_count=600,
            is_converged=False,
            diversity_stall={"rebalance_recommended": True},
        )


def test_autopilot_default_state_has_no_diversity_stall_key() -> None:
    autopilot = importlib.import_module("autopilot")
    assert "diversity_stall_state" not in autopilot._default_state()
    assert not hasattr(autopilot, "_load_ap37_diversity_baseline")
    assert not hasattr(autopilot, "_ap37_finite_float")


def test_normalize_state_before_save_drops_legacy_diversity_stall_state() -> None:
    """A pre-existing autopilot_state.json must shed the dead key, not keep it.

    state_store.load_state returns the on-disk JSON verbatim (it does NOT merge
    _default_state), so dropping the key from the default alone would leave the
    live file reporting an all-null guardrail forever.
    """
    autopilot = importlib.import_module("autopilot")
    state = {
        "trial_counter": 1460,
        "paused": False,
        "diversity_stall_state": {
            "schema_version": "ap37_diversity_stall.v1",
            "distinct2_baseline": None,
            "semantic_embedding_agreement_baseline": None,
            "distinct2_history": [{"trial_id": 1460, "status": "signal_missing"}],
            "consecutive_trigger_count": 0,
            "rebalance_recommended": False,
            "last_status": "signal_missing",
        },
    }
    autopilot._normalize_state_before_save(state)
    assert "diversity_stall_state" not in state
    assert state["trial_counter"] == 1460
    # Idempotent on already-migrated / fresh state.
    autopilot._normalize_state_before_save(state)
    assert "diversity_stall_state" not in state
