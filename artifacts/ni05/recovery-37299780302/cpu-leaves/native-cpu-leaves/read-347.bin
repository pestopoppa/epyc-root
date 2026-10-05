"""EvolutionManager must not distill legacy corrupt-baseline text."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from experiment_journal import JournalEntry  # noqa: E402
from species.evolution_manager import EvolutionManager  # noqa: E402


class CapturingEvolutionManager(EvolutionManager):
    def __init__(self) -> None:
        super().__init__()
        self.prompt = ""

    def _invoke_llm(self, prompt: str) -> str:
        self.prompt = prompt
        return """```json:insights
[
  {
    "description": "Still says baseline 9.900",
    "insight": "Suite 'coder' regression: -6.900",
    "species": "seeder",
    "confidence": "high",
    "evidence_trial_ids": [28, 43]
  }
]
```"""


class FakeStrategyStore:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def store(self, **kwargs):
        self.rows.append(kwargs)
        return "stored"


def test_distill_scrubs_legacy_scale_input_and_output() -> None:
    manager = CapturingEvolutionManager()
    store = FakeStrategyStore()
    entry = JournalEntry(
        trial_id=28,
        timestamp="2026-05-31T00:00:00Z",
        species="seeder",
        action_type="seed_batch",
        tier=1,
        quality=0.0,
        speed=1.0,
        cost=0.5,
        reliability=0.0,
        pareto_status="dominated",
        failure_analysis=(
            "Quality regression: 0.000 vs baseline 9.900 (-100.0%); "
            "Suite 'coder' regression: -9.900"
        ),
    )

    result = manager.distill([entry], store, last_n=1, trial_id=183)

    assert result["status"] == "success"
    assert "evidence_trial_ids" in manager.prompt
    assert "baseline 9.900" not in manager.prompt
    assert "-9.900" not in manager.prompt
    assert "legacy-scale failure_analysis omitted" in manager.prompt
    assert len(store.rows) == 1
    stored = store.rows[0]
    assert "9.900" not in stored["description"]
    assert "-6.900" not in stored["insight"]
    assert "legacy-scale" in stored["description"]
    assert "legacy-scale" in stored["insight"]
    assert stored["evidence_trial_ids"] == [28]


def test_distill_filters_corrupt_and_learning_excluded_rows() -> None:
    manager = CapturingEvolutionManager()
    store = FakeStrategyStore()
    corrupt = JournalEntry(
        trial_id=41,
        timestamp="2026-06-01T00:00:00Z",
        species="seeder",
        action_type="seed_batch",
        tier=1,
        quality=0.0,
        speed=0.0,
        cost=0.5,
        reliability=0.0,
        pareto_status="dominated",
        hypothesis="CORRUPT_SHOULD_NOT_APPEAR",
        bug_corrupted_by="exogenous_operator_reload",
    )
    excluded = JournalEntry(
        trial_id=42,
        timestamp="2026-06-01T00:01:00Z",
        species="seeder",
        action_type="seed_batch",
        tier=1,
        quality=1.7,
        speed=50.0,
        cost=0.2,
        reliability=0.98,
        pareto_status="frontier",
        hypothesis="EXCLUDED_SHOULD_NOT_APPEAR",
        keep_revert_decision="excluded",
        eval_details={"learning_exclusion": {"by": "mad_noise"}},
    )
    clean_failure = JournalEntry(
        trial_id=43,
        timestamp="2026-06-01T00:02:00Z",
        species="numeric_swarm",
        action_type="numeric_trial",
        tier=1,
        quality=1.1,
        speed=40.0,
        cost=0.2,
        reliability=0.98,
        pareto_status="dominated",
        hypothesis="CLEAN_FAILURE_SHOULD_APPEAR",
        failure_analysis="valid regression to analyze",
    )

    result = manager.distill([corrupt, excluded, clean_failure], store, last_n=3, trial_id=200)

    assert result["status"] == "success"
    assert result["trials_analyzed"] == 1
    assert result["entries_filtered"] == 2
    assert "CLEAN_FAILURE_SHOULD_APPEAR" in manager.prompt
    assert "CORRUPT_SHOULD_NOT_APPEAR" not in manager.prompt
    assert "EXCLUDED_SHOULD_NOT_APPEAR" not in manager.prompt
    assert store.rows[0]["evidence_trial_ids"] == [43]


def test_distill_skips_multitrial_insight_without_evidence_ids() -> None:
    class UngroundedEvolutionManager(CapturingEvolutionManager):
        def _invoke_llm(self, prompt: str) -> str:
            self.prompt = prompt
            return """```json:insights
[
  {
    "description": "Generic pattern with no support",
    "insight": "Do a broad thing",
    "species": "all",
    "confidence": "medium"
  }
]
```"""

    manager = UngroundedEvolutionManager()
    store = FakeStrategyStore()
    first = JournalEntry(
        trial_id=51,
        timestamp="2026-06-01T00:00:00Z",
        species="seeder",
        action_type="seed_batch",
        tier=1,
        quality=1.0,
        speed=40.0,
        cost=0.2,
        reliability=0.98,
        pareto_status="dominated",
    )
    second = JournalEntry(
        trial_id=52,
        timestamp="2026-06-01T00:01:00Z",
        species="numeric_swarm",
        action_type="numeric_trial",
        tier=1,
        quality=1.2,
        speed=41.0,
        cost=0.2,
        reliability=0.98,
        pareto_status="frontier",
    )

    result = manager.distill([first, second], store, last_n=2, trial_id=201)

    assert result == {
        "status": "skipped",
        "reason": "no grounded insights extracted",
        "insights_total": 1,
        "insights_stored": 0,
        "ungrounded_insights_skipped": 1,
        "trials_analyzed": 2,
        "entries_filtered": 0,
        # TD-21.25: dropped-evidence-id counter (see TRIAL_ID_COERCION_COUNTS)
        # -- 0 here since this insight's evidence_trial_ids key is absent
        # entirely, never a malformed token.
        "evidence_ids_dropped": 0,
    }
    assert store.rows == []
