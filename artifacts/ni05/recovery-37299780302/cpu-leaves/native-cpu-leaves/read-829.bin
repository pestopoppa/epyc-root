"""Tests for StrategyStore — FAISS + SQLite strategy memory."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class MockEmbedder:
    """Deterministic hash-based embedder for testing (no model needed)."""

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def embed_text(self, text: str) -> np.ndarray:
        h = hashlib.sha256(text.encode()).digest()
        rng = np.random.RandomState(int.from_bytes(h[:4], "big"))
        vec = rng.randn(self.dim).astype(np.float32)
        vec /= np.linalg.norm(vec) + 1e-9
        return vec


@pytest.fixture
def store(tmp_path):
    from orchestration.repl_memory.strategy_store import StrategyStore
    s = StrategyStore(path=tmp_path / "strategies", embedding_dim=1024, embedder=MockEmbedder())
    yield s
    s.close()


class TestStrategyStore:

    def test_store_and_count(self, store):
        sid = store.store(
            description="Disable self-speculation for dense models",
            insight="HSD net-negative on hybrid",
            source_trial_id=1,
            species="config_tuner",
        )
        assert isinstance(sid, str)
        assert len(sid) == 36  # UUID
        assert store.count() == 1

    def test_store_multiple(self, store):
        for i in range(5):
            store.store(
                description=f"Strategy {i}",
                insight=f"Insight {i}",
                source_trial_id=i,
                species="explorer",
            )
        assert store.count() == 5

    def test_retrieve_returns_results(self, store):
        store.store("Enable caching for read-heavy workloads", "Cache hit rate 90%",
                     source_trial_id=1, species="perf_tuner")
        store.store("Increase batch size for throughput", "2x throughput at batch=8",
                     source_trial_id=2, species="perf_tuner")
        results = store.retrieve("caching performance", k=5)
        assert len(results) >= 1
        assert results[0].similarity_score > 0

    def test_retrieve_empty_store(self, store):
        results = store.retrieve("anything", k=5)
        assert results == []

    def test_retrieve_sees_external_strategy_seed_without_restart(self, tmp_path):
        from orchestration.repl_memory.strategy_store import StrategyStore

        strategy_path = tmp_path / "strategies"
        live_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        writer_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        try:
            assert live_store.retrieve("external planner hint", k=5) == []

            seeded_id = writer_store.store(
                "external planner hint",
                "planner should see this StrategyStore row without restart",
                source_trial_id=1104,
                species="seeder",
                entry_type="pattern",
                evidence_trial_ids=[1104],
            )

            results = live_store.retrieve(
                "external planner hint",
                k=5,
                species="seeder",
            )
            assert seeded_id in {entry.id for entry in results}
        finally:
            writer_store.close()
            live_store.close()

    def test_closing_stale_store_does_not_overwrite_external_faiss_seed(self, tmp_path):
        from orchestration.repl_memory.strategy_store import StrategyStore

        strategy_path = tmp_path / "strategies"
        stale_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        writer_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        try:
            seeded_id = writer_store.store(
                "persistent external planner hint",
                "stale StrategyStore close must not erase this row",
                source_trial_id=1105,
                species="seeder",
                entry_type="pattern",
                evidence_trial_ids=[1105],
            )
        finally:
            writer_store.close()
            stale_store.close()

        reopened_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        try:
            results = reopened_store.retrieve(
                "persistent external planner hint",
                k=5,
                species="seeder",
            )
            assert seeded_id in {entry.id for entry in results}
        finally:
            reopened_store.close()

    def test_stale_store_write_keeps_external_faiss_seed(self, tmp_path):
        from orchestration.repl_memory.strategy_store import StrategyStore

        strategy_path = tmp_path / "strategies"
        stale_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        writer_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        try:
            external_id = writer_store.store(
                "external planner hint",
                "newer StrategyStore writer must survive a stale writer",
                source_trial_id=1106,
                species="seeder",
                entry_type="pattern",
                evidence_trial_ids=[1106],
            )
            stale_id = stale_store.store(
                "stale writer planner hint",
                "stale StrategyStore instance reloads before adding its vector",
                source_trial_id=1107,
                species="seeder",
                entry_type="pattern",
                evidence_trial_ids=[1107],
            )
        finally:
            writer_store.close()
            stale_store.close()

        reopened_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        try:
            assert reopened_store._faiss.count == 2
            results = reopened_store.retrieve("planner hint StrategyStore", k=10)
            result_ids = {entry.id for entry in results}
            assert external_id in result_ids
            assert stale_id in result_ids
        finally:
            reopened_store.close()

    def test_retrieve_with_species_filter(self, store):
        store.store("Strategy A", "Insight A", source_trial_id=1, species="alpha")
        store.store("Strategy B", "Insight B", source_trial_id=2, species="beta")
        store.store("Strategy C", "Insight C", source_trial_id=3, species="alpha")

        results = store.retrieve("Strategy", k=10, species="alpha")
        assert all(r.species == "alpha" for r in results)

    def test_retrieve_excludes_source_trial_ids(self, store):
        store.store("Strategy A", "Insight A", source_trial_id=1, species="alpha")
        store.store("Strategy B", "Insight B", source_trial_id=2, species="alpha")

        results = store.retrieve("Strategy", k=10, excluded_trial_ids={2})

        assert results
        assert all(r.source_trial_id != 2 for r in results)

    def test_retrieve_excludes_any_evidence_trial_id(self, store):
        sid = store.store(
            "Strategy A",
            "Insight A",
            source_trial_id=99,
            species="alpha",
            evidence_trial_ids=[1, 2],
        )
        store.store("Strategy B", "Insight B", source_trial_id=3, species="alpha")

        results = store.retrieve("Strategy", k=10, excluded_trial_ids={2})

        assert results
        assert all(r.id != sid for r in results)
        assert any(r.source_trial_id == 3 for r in results)

    def test_retrieve_exclusion_falls_back_to_source_trial_id(self, store):
        store.store("Legacy evidence", "Insight", source_trial_id=5, species="alpha")
        store._conn.execute("UPDATE strategies SET evidence_trial_ids = '[]'")
        store._conn.commit()

        results = store.retrieve("Legacy evidence", k=10, excluded_trial_ids={5})

        assert results == []

    def test_store_frontier_journal_entry_is_idempotent(self, store):
        entry = SimpleNamespace(
            trial_id=7,
            timestamp="2026-06-19T00:00:00Z",
            species="prompt_forge",
            action_type="code_mutation",
            quality=1.2345,
            speed=42.25,
            pareto_status="frontier",
            hypothesis="repair parser",
            expected_mechanism="targeted_fix",
            outcome_status="ok",
            bug_corrupted_by="",
            eval_details={},
        )

        sid = store.store_frontier_journal_entry(entry)
        sid_again = store.store_frontier_journal_entry(entry)

        assert sid == "journal-frontier-trial-7"
        assert sid_again == sid
        assert store.count() == 1
        results = store.retrieve("repair parser", k=5)
        assert len(results) == 1
        assert results[0].id == sid
        assert results[0].source_trial_id == 7
        assert results[0].evidence_trial_ids == [7]
        assert results[0].metadata["generated_from"] == "journal_frontier"
        assert results[0].metadata["journal_trial_id"] == 7

    def test_store_frontier_journal_entry_skips_unsafe_rows(self, store):
        base = {
            "trial_id": 8,
            "timestamp": "2026-06-19T00:00:00Z",
            "species": "prompt_forge",
            "action_type": "code_mutation",
            "quality": 1.0,
            "speed": 10.0,
            "pareto_status": "frontier",
            "hypothesis": "repair parser",
            "expected_mechanism": "targeted_fix",
            "outcome_status": "ok",
            "bug_corrupted_by": "",
            "eval_details": {},
        }

        assert store.store_frontier_journal_entry(
            SimpleNamespace(**{**base, "pareto_status": "dominated"})
        ) is None
        assert store.store_frontier_journal_entry(
            SimpleNamespace(**{**base, "outcome_status": "skipped"})
        ) is None
        assert store.store_frontier_journal_entry(
            SimpleNamespace(**{**base, "bug_corrupted_by": "resource_contention"})
        ) is None
        assert store.store_frontier_journal_entry(
            SimpleNamespace(
                **{
                    **base,
                    "eval_details": {"learning_exclusion": {"by": "mad_noise"}},
                }
            )
        ) is None
        assert store.count() == 0

    def test_frontier_journal_projection_report_finds_missing_and_unexpected(self, store):
        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(
                        trial_id=1,
                        timestamp="2026-06-19T00:00:00Z",
                        species="prompt_forge",
                        action_type="code_mutation",
                        quality=1.2,
                        speed=40.0,
                        pareto_status="frontier",
                        hypothesis="repair parser",
                        expected_mechanism="targeted_fix",
                        outcome_status="ok",
                        bug_corrupted_by="",
                        eval_details={},
                    ),
                    SimpleNamespace(
                        trial_id=2,
                        timestamp="2026-06-19T00:00:00Z",
                        species="prompt_forge",
                        action_type="code_mutation",
                        quality=1.0,
                        speed=10.0,
                        pareto_status="frontier",
                        hypothesis="unsafe row",
                        expected_mechanism="targeted_fix",
                        outcome_status="ok",
                        bug_corrupted_by="resource_contention",
                        eval_details={},
                    ),
                ]

        store.store(
            "old unsafe projection",
            "q=1.000 s=10.0 mechanism=targeted_fix",
            source_trial_id=2,
            species="prompt_forge",
            metadata={"generated_from": "journal_frontier", "journal_trial_id": 2},
            evidence_trial_ids=[2],
            entry_id="journal-frontier-trial-2",
        )

        report = store.frontier_journal_projection_report(FakeJournal())

        assert report["ok"] is False
        assert report["expected_count"] == 1
        assert report["projected_count"] == 1
        assert report["missing"] == [
            {"trial_id": 1, "strategy_id": "journal-frontier-trial-1"}
        ]
        assert report["unexpected"] == [
            {"trial_id": 2, "strategy_id": "journal-frontier-trial-2"}
        ]

    def test_sync_frontier_journal_entries_inserts_missing_only(self, store):
        entry = SimpleNamespace(
            trial_id=9,
            timestamp="2026-06-19T00:00:00Z",
            species="prompt_forge",
            action_type="code_mutation",
            quality=1.2345,
            speed=42.25,
            pareto_status="frontier",
            hypothesis="repair parser",
            expected_mechanism="targeted_fix",
            outcome_status="ok",
            bug_corrupted_by="",
            eval_details={},
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [entry]

        dry = store.sync_frontier_journal_entries(FakeJournal(), dry_run=True)
        assert dry["ok"] is False
        assert dry["would_insert_count"] == 1
        assert dry["inserted_count"] == 0
        assert store.count() == 0

        written = store.sync_frontier_journal_entries(FakeJournal(), dry_run=False)
        assert written["ok"] is True
        assert written["would_insert_count"] == 1
        assert written["inserted_count"] == 1
        assert store.count() == 1

    def test_store_consult_gate_journal_entry_keeps_dominated_policy_evidence(self, store):
        entry = SimpleNamespace(
            trial_id=21,
            timestamp="2026-07-07T00:00:00Z",
            species="consult_gate",
            action_type="consult_gate_probe",
            tier=3,
            quality=2.4,
            speed=18.5,
            pareto_status="dominated",
            config_snapshot={"task_suite": "targeted", "turns": 10, "tier": 3},
            outcome_status="ok",
            bug_corrupted_by="",
            eval_details={
                "speed_metric_mode": "consult_gate_tasks_per_hour",
                "details": {
                    "kind": "consult_gate_probe",
                    "tier": 3,
                    "consult_calls": 4,
                    "consult_skips": 6,
                    "rerun_requests": 2,
                    "gate_reason_counts": {
                        "parser_data_contract": 3,
                        "plain_single_file_edit": 6,
                    },
                    "summary": {
                        "baseline": {"turns": 10, "quality": 0.7, "passes": 7},
                        "consult": {"turns": 10, "quality": 0.8, "passes": 8},
                        "gated": {
                            "turns": 10,
                            "quality": 0.8,
                            "passes": 8,
                            "consult_calls": 4,
                            "consult_skips": 6,
                            "rerun_requests": 2,
                            "gate_reason_counts": {
                                "parser_data_contract": 3,
                                "plain_single_file_edit": 6,
                            },
                        },
                        "gated_comparison": {"quality_delta_pp": 10.0},
                    },
                },
            },
        )

        sid = store.store_consult_gate_journal_entry(entry)
        sid_again = store.store_consult_gate_journal_entry(entry)

        assert sid == "journal-consult-gate-trial-21"
        assert sid_again == sid
        results = store.retrieve("consult parser data contract T3 targeted", k=5)
        stored = next(item for item in results if item.id == sid)
        assert stored.entry_type == "pattern"
        assert stored.species == "consult_gate"
        assert stored.evidence_trial_ids == [21]
        assert stored.metadata["generated_from"] == "journal_consult_gate"
        assert stored.metadata["consult_call_rate"] == 0.4
        assert stored.metadata["gate_reason_counts"]["parser_data_contract"] == 3
        assert "prefer targeted consult gate" in stored.generalized_content

    def test_store_consult_gate_journal_entry_skips_untrustworthy_rows(self, store):
        base = {
            "trial_id": 22,
            "timestamp": "2026-07-07T00:00:00Z",
            "species": "consult_gate",
            "action_type": "consult_gate_probe",
            "tier": 3,
            "quality": 1.0,
            "speed": 10.0,
            "pareto_status": "dominated",
            "config_snapshot": {"task_suite": "targeted", "tier": 3},
            "outcome_status": "ok",
            "bug_corrupted_by": "",
            "eval_details": {
                "details": {
                    "kind": "consult_gate_probe",
                    "summary": {"gated": {"turns": 3, "quality": 0.0}},
                }
            },
        }

        assert store.store_consult_gate_journal_entry(
            SimpleNamespace(**{**base, "outcome_status": "skipped"})
        ) is None
        assert store.store_consult_gate_journal_entry(
            SimpleNamespace(**{**base, "bug_corrupted_by": "mock_backend"})
        ) is None
        assert store.store_consult_gate_journal_entry(
            SimpleNamespace(
                **{
                    **base,
                    "eval_details": {
                        "learning_exclusion": {"by": "mad_noise"},
                        "details": {
                            "kind": "consult_gate_probe",
                            "summary": {"gated": {"turns": 3, "quality": 0.0}},
                        },
                    },
                }
            )
        ) is None
        assert store.count() == 0

    def test_sync_consult_gate_journal_entries_inserts_missing_only(self, store):
        entry = SimpleNamespace(
            trial_id=23,
            timestamp="2026-07-07T00:00:00Z",
            species="consult_gate",
            action_type="consult_gate_probe",
            tier=2,
            quality=2.1,
            speed=20.0,
            pareto_status="candidate",
            config_snapshot={"task_suite": "targeted", "turns": 5, "tier": 2},
            outcome_status="ok",
            bug_corrupted_by="",
            eval_details={
                "details": {
                    "kind": "consult_gate_probe",
                    "tier": 2,
                    "summary": {
                        "baseline": {"turns": 5, "quality": 0.4},
                        "gated": {"turns": 5, "quality": 0.6, "consult_calls": 2, "consult_skips": 3},
                    },
                }
            },
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [entry]

        dry = store.sync_consult_gate_journal_entries(FakeJournal(), dry_run=True)
        assert dry["ok"] is False
        assert dry["would_insert_count"] == 1
        assert store.count() == 0

        written = store.sync_consult_gate_journal_entries(FakeJournal(), dry_run=False)
        assert written["ok"] is True
        assert written["inserted"] == [
            {"trial_id": 23, "strategy_id": "journal-consult-gate-trial-23"}
        ]
        assert store.count() == 1

    def test_frontier_journal_projection_report_flags_mismatched_projection(self, store):
        entry = SimpleNamespace(
            trial_id=11,
            timestamp="2026-06-19T00:00:00Z",
            species="prompt_forge",
            action_type="code_mutation",
            quality=1.2345,
            speed=42.25,
            pareto_status="frontier",
            hypothesis="repair parser",
            expected_mechanism="targeted_fix",
            outcome_status="ok",
            bug_corrupted_by="",
            eval_details={},
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [entry]

        store.store(
            "projection with bad evidence",
            "q=1.000 s=10.0 mechanism=targeted_fix",
            source_trial_id=11,
            species="prompt_forge",
            metadata={"generated_from": "legacy"},
            evidence_trial_ids=[99],
            entry_id="journal-frontier-trial-11",
        )

        report = store.frontier_journal_projection_report(FakeJournal())

        assert report["ok"] is False
        assert report["missing_count"] == 0
        assert report["mismatch_count"] == 1
        assert report["mismatches"][0]["trial_id"] == 11
        assert set(report["mismatches"][0]["problems"]) == {
            "evidence_trial_ids",
            "metadata.generated_from",
            "metadata.journal_trial_id",
        }

    def test_retrieve_for_journal_applies_folded_evidence_exclusions(self, store):
        sid = store.store(
            "Strategy A",
            "Insight A",
            source_trial_id=99,
            species="alpha",
            evidence_trial_ids=[1, 2],
        )
        store.store("Strategy B", "Insight B", source_trial_id=3, species="alpha")

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=2, bug_corrupted_by="superseded"),
                ]

        results = store.retrieve_for_journal("Strategy", journal=FakeJournal(), k=10)

        assert results
        assert all(r.id != sid for r in results)
        assert any(r.source_trial_id == 3 for r in results)

    def test_retrieve_for_journal_keeps_operator_seeded_hints(self, store):
        operator_id = store.store(
            "tool use sentinel lane",
            "Use tool_helpfulness instead of raw tool-call count.",
            source_trial_id=1036,
            species="structural_lab",
            metadata={"seeded_by": "operator"},
            entry_type="pattern",
            evidence_trial_ids=[1036],
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=1036, bug_corrupted_by="superseded"),
                ]

        results = store.retrieve_for_journal(
            "tool use sentinel",
            journal=FakeJournal(),
            k=10,
            species="structural_lab",
        )

        assert operator_id in {entry.id for entry in results}

    def test_store_rejects_journal_absent_evidence_ids(self, store):
        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=1, bug_corrupted_by=""),
                ]

        with pytest.raises(ValueError, match="absent from journal"):
            store.store(
                "Fabricated evidence",
                "Should not be persisted",
                source_trial_id=99,
                species="structural_lab",
                evidence_trial_ids=[2],
                journal=FakeJournal(),
            )

        assert store.count() == 0

    def test_store_fails_closed_when_journal_validation_unavailable(self, store):
        class BrokenJournal:
            def entries_with_supersessions(self):
                raise RuntimeError("journal unavailable")

        with pytest.raises(ValueError, match="journal unavailable"):
            store.store(
                "Unvalidated evidence",
                "Should not silently become declared provenance.",
                source_trial_id=1,
                species="structural_lab",
                evidence_trial_ids=[1],
                journal=BrokenJournal(),
            )

        assert store.count() == 0

    def test_store_tags_explicit_empty_evidence_without_source_fallback(self, store):
        sid = store.store(
            "Ungrounded strategy",
            "No evidence was supplied.",
            source_trial_id=99,
            species="structural_lab",
            evidence_trial_ids=[],
        )

        row = store._conn.execute(
            "SELECT evidence_trial_ids, metadata_json, source_trial_id FROM strategies WHERE id=?",
            (sid,),
        ).fetchone()
        meta = json.loads(row["metadata_json"])

        assert json.loads(row["evidence_trial_ids"]) == []
        assert meta["provenance_status"] == "none"
        assert meta["provenance_evidence_count"] == 0
        assert store._evidence_trial_ids_for_row(row) == []

    def test_retrieve_for_journal_filters_non_operator_provenance_none(self, store):
        ungrounded_id = store.store(
            "tool use sentinel lane",
            "No evidence should keep this hidden from journal-aware planner reads.",
            source_trial_id=99,
            species="structural_lab",
            entry_type="pattern",
            evidence_trial_ids=[],
        )
        kept_id = store.store(
            "tool use sentinel lane",
            "Evidence-backed row remains planner-visible.",
            source_trial_id=3,
            species="structural_lab",
            entry_type="pattern",
            evidence_trial_ids=[3],
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=3, bug_corrupted_by=""),
                ]

        results = store.retrieve_for_journal(
            "tool use sentinel lane",
            journal=FakeJournal(),
            k=10,
            species="structural_lab",
        )

        result_ids = {entry.id for entry in results}
        assert ungrounded_id not in result_ids
        assert kept_id in result_ids

    def test_retrieve_for_journal_keeps_operator_seeded_provenance_none(self, store):
        operator_id = store.store(
            "operator tool-use hypothesis",
            "Curated operator hypotheses stay visible as hypotheses.",
            source_trial_id=1036,
            species="structural_lab",
            metadata={"seeded_by": "operator"},
            entry_type="pattern",
            evidence_trial_ids=[],
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return []

        results = store.retrieve_for_journal(
            "operator tool-use hypothesis",
            journal=FakeJournal(),
            k=10,
            species="structural_lab",
        )

        assert operator_id in {entry.id for entry in results}
        assert results[0].metadata["provenance_status"] == "operator_seeded"
        assert results[0].evidence_trial_ids == []

    def test_retrieve_conventions_filters_species_plus_global(self, store):
        prompt_id = store.store(
            "PromptForge guardrail",
            "Avoid prompt edits when route ownership is unclear",
            source_trial_id=1,
            species="prompt_forge",
            entry_type="convention",
        )
        global_id = store.store(
            "Global handoff hypothesis",
            "Prefer evidence-gated restarts after live policy changes",
            source_trial_id=2,
            species="all",
            entry_type="convention",
        )
        store.store(
            "Numeric-only guardrail",
            "Do not use qwen2-tokenized drafts for qwen3.5 bins",
            source_trial_id=3,
            species="numeric_swarm",
            entry_type="convention",
        )
        store.store(
            "Raw PromptForge row",
            "Not a convention",
            source_trial_id=4,
            species="prompt_forge",
        )

        results = store.retrieve_conventions(species="prompt_forge")

        result_ids = [entry.id for entry in results]
        assert result_ids == [prompt_id, global_id]
        assert all(entry.entry_type == "convention" for entry in results)
        assert all(entry.validity_score == 0.5 for entry in results)
        assert all(entry.staleness == 1.0 for entry in results)

    def test_retrieve_conventions_applies_folded_evidence_exclusions(self, store):
        excluded_id = store.store(
            "Excluded convention",
            "This should not appear through a folded journal",
            source_trial_id=99,
            species="structural_lab",
            entry_type="convention",
            evidence_trial_ids=[1, 2],
        )
        kept_id = store.store(
            "Kept convention",
            "This remains planner-visible",
            source_trial_id=3,
            species="structural_lab",
            entry_type="convention",
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=2, bug_corrupted_by="superseded"),
                ]

        results = store.retrieve_conventions(
            species="structural_lab",
            journal=FakeJournal(),
        )

        result_ids = {entry.id for entry in results}
        assert excluded_id not in result_ids
        assert kept_id in result_ids

    def test_retrieve_conventions_keeps_operator_seeded_hints(self, store):
        operator_id = store.store(
            "tool-use convention",
            "Keep native tool sentinels in a clean restart window.",
            source_trial_id=1036,
            species="structural_lab",
            metadata={"seeded_by": "operator"},
            entry_type="convention",
            evidence_trial_ids=[1036],
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=1036, bug_corrupted_by="superseded"),
                ]

        results = store.retrieve_conventions(
            species="structural_lab",
            journal=FakeJournal(),
        )

        assert operator_id in {entry.id for entry in results}

    def test_retrieve_conventions_honors_quarantine_and_min_validity(self, store):
        quarantined_id = store.store(
            "Quarantined convention",
            "Should be hidden by default",
            source_trial_id=1,
            species="seeder",
            entry_type="convention",
        )
        low_validity_id = store.store(
            "Low validity convention",
            "Visible unless min_validity excludes it",
            source_trial_id=2,
            species="seeder",
            entry_type="convention",
        )
        for _ in range(20):
            store.update_validity(quarantined_id, failure=True)
        store.update_validity(low_validity_id, failure=True)

        default_results = store.retrieve_conventions(species="seeder")
        strict_results = store.retrieve_conventions(species="seeder", min_validity=0.70)
        full_results = store.retrieve_conventions(
            species="seeder",
            include_quarantined=True,
        )

        assert all(entry.id != quarantined_id for entry in default_results)
        assert all(entry.id != low_validity_id for entry in strict_results)
        assert any(entry.id == quarantined_id for entry in full_results)

    def test_retrieve_conventions_reports_staleness(self, store):
        sid = store.store(
            "Stale convention",
            "Created in an older context epoch",
            source_trial_id=1,
            species="numeric_swarm",
            entry_type="convention",
        )

        fresh = store.retrieve_conventions(species="numeric_swarm")
        store.compute_context_hash = lambda *args, **kwargs: "DIFFERENTHASH0001"
        stale = store.retrieve_conventions(species="numeric_swarm")

        assert [entry.id for entry in fresh] == [sid]
        assert fresh[0].staleness == 1.0
        assert stale[0].staleness == 0.5

    def test_strategy_rows_for_compression_applies_folded_evidence_exclusions(self, store):
        excluded_id = store.store(
            "Strategy A",
            "Insight A",
            source_trial_id=99,
            species="alpha",
            evidence_trial_ids=[1, 2],
        )
        kept_id = store.store(
            "Strategy B",
            "Insight B",
            source_trial_id=3,
            species="alpha",
            evidence_trial_ids=[3],
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=2, bug_corrupted_by="superseded"),
                ]

        rows = store.strategy_rows_for_compression(journal=FakeJournal())

        row_ids = {row["id"] for row in rows}
        assert excluded_id not in row_ids
        assert kept_id in row_ids

    def test_strategy_rows_for_compression_window_counts_eligible_rows(self, store):
        for trial_id in range(1, 5):
            store.store(
                f"Strategy {trial_id}",
                f"Insight {trial_id}",
                source_trial_id=trial_id,
                species="alpha",
                evidence_trial_ids=[trial_id],
            )

        rows = store.strategy_rows_for_compression(
            window_trials=2,
            excluded_trial_ids={4},
        )

        assert [row["source_trial_id"] for row in rows] == [3, 2]

    def test_strategy_rows_for_staleness_scan_applies_folded_evidence_exclusions(self, store):
        excluded_id = store.store(
            "Strategy A",
            "Insight A",
            source_trial_id=99,
            species="alpha",
            evidence_trial_ids=[1, 2],
            metadata={"refs": ["prompt.md"]},
        )
        kept_id = store.store(
            "Strategy B",
            "Insight B",
            source_trial_id=3,
            species="alpha",
            evidence_trial_ids=[3],
            metadata={"refs": ["prompt.md"]},
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(
                        trial_id=2,
                        eval_details={"learning_exclusion": {"by": "seq_accumulating"}},
                    ),
                ]

        rows = store.strategy_rows_for_staleness_scan(journal=FakeJournal())

        row_ids = {row["id"] for row in rows}
        assert excluded_id not in row_ids
        assert kept_id in row_ids

    def test_strategy_entries_for_distillation_applies_folded_evidence_exclusions(self, store):
        excluded_id = store.store(
            "Strategy A",
            "Insight A",
            source_trial_id=99,
            species="alpha",
            evidence_trial_ids=[1, 2],
        )
        kept_id = store.store(
            "Strategy B",
            "Insight B",
            source_trial_id=3,
            species="alpha",
            evidence_trial_ids=[3],
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=2, bug_corrupted_by="superseded"),
                ]

        entries = store.strategy_entries_for_distillation("raw", journal=FakeJournal())

        entry_ids = {entry["id"] for entry in entries}
        assert excluded_id not in entry_ids
        assert kept_id in entry_ids

    def test_strategy_entries_for_distillation_filters_low_validity(self, store):
        kept_id = store.store("Keep", "Insight", source_trial_id=1, species="alpha")
        low_id = store.store("Drop", "Insight", source_trial_id=2, species="alpha")
        for _ in range(30):
            store.update_validity(low_id, failure=True)

        entries = store.strategy_entries_for_distillation("raw", min_validity=0.10)

        entry_ids = {entry["id"] for entry in entries}
        assert kept_id in entry_ids
        assert low_id not in entry_ids

    def test_excluded_strategy_evidence_trial_ids_prefers_folded_view(self):
        from orchestration.repl_memory.strategy_store import (
            excluded_strategy_evidence_trial_ids,
        )

        class FakeJournal:
            def all_entries(self):
                return [
                    SimpleNamespace(
                        trial_id=1,
                        bug_corrupted_by="raw_only",
                    )
                ]

            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=1, bug_corrupted_by=""),
                    SimpleNamespace(trial_id=2, bug_corrupted_by="resource_contention"),
                    SimpleNamespace(trial_id=3, outcome_status="error"),
                    SimpleNamespace(trial_id=4, keep_revert_decision="excluded"),
                    SimpleNamespace(
                        trial_id=5,
                        eval_details={"learning_exclusion": {"by": "seq_accumulating"}},
                    ),
                    SimpleNamespace(trial_id="not-an-int", bug_corrupted_by="bad-row"),
                ]

        assert excluded_strategy_evidence_trial_ids(FakeJournal()) == {2, 3, 4, 5}

    def test_excluded_strategy_evidence_trial_ids_falls_back_to_all_entries(self):
        from orchestration.repl_memory.strategy_store import (
            excluded_strategy_evidence_trial_ids,
        )

        class FakeJournal:
            def all_entries(self):
                return [
                    SimpleNamespace(trial_id=7, bug_corrupted_by="operator_scrub"),
                    SimpleNamespace(trial_id=8, bug_corrupted_by=""),
                ]

        assert excluded_strategy_evidence_trial_ids(FakeJournal()) == {7}

    def test_excluded_strategy_evidence_trial_ids_tolerates_load_errors(self):
        from orchestration.repl_memory.strategy_store import (
            excluded_strategy_evidence_trial_ids,
        )

        class BrokenJournal:
            def all_entries(self):
                raise RuntimeError("journal unavailable")

        assert excluded_strategy_evidence_trial_ids(BrokenJournal()) == set()

    def test_metadata_roundtrip(self, store):
        meta = {"key": "value", "nested": {"a": 1}}
        store.store("Test", "Test insight", source_trial_id=1, species="test",
                     metadata=meta)
        results = store.retrieve("Test", k=1)
        assert len(results) == 1
        assert results[0].metadata["key"] == "value"
        assert results[0].metadata["nested"] == {"a": 1}
        assert results[0].metadata["insight_format"]["title"] == "Test"

    def test_to_dict_serialization(self, store):
        store.store("Serialize me", "Check dict", source_trial_id=7, species="serializer")
        results = store.retrieve("Serialize me", k=1)
        d = results[0].to_dict()
        assert isinstance(d, dict)
        assert d["species"] == "serializer"
        assert d["source_trial_id"] == 7
        assert d["evidence_trial_ids"] == [7]
        assert "id" in d
        assert "created_at" in d

    def test_close_is_safe(self, store):
        store.close()
        # Double close should not raise
        store.close()


class TestAP32InsightFormat:
    """AP-32: task-agnostic insight format metadata."""

    def test_store_records_derived_insight_format_metadata(self, store):
        sid = store.store(
            "Disable brittle benchmark-specific prompt anchors.",
            "Patterns tied to one suite should stay local until cross-suite evidence exists.",
            source_trial_id=11,
            species="prompt_forge",
        )

        row = store._conn.execute(
            "SELECT metadata_json FROM strategies WHERE id=?", (sid,)
        ).fetchone()
        meta = json.loads(row["metadata_json"])
        fmt = meta["insight_format"]

        assert fmt["version"] == 1
        assert fmt["title"] == "Disable brittle benchmark-specific prompt anchors"
        assert fmt["description"] == "Disable brittle benchmark-specific prompt anchors."
        assert fmt["generalized_content"].startswith("Patterns tied to one suite")
        assert fmt["specificity_flags"] == []

        results = store.retrieve("benchmark-specific prompt anchors", k=1)
        assert results[0].title == fmt["title"]
        assert results[0].generalized_content == fmt["generalized_content"]
        assert results[0].specificity_flags == []

    def test_store_accepts_explicit_generalized_content(self, store):
        sid = store.store(
            "Prefer mutation evidence that crosses benchmark families.",
            "Changed a concrete file after one trial.",
            source_trial_id=123,
            species="structural_lab",
            title="Prefer cross-suite mechanisms before promotion",
            generalized_content=(
                "Promote a mutation pattern only after evidence spans more than one "
                "benchmark family."
            ),
        )

        row = store._conn.execute(
            "SELECT insight, metadata_json FROM strategies WHERE id=?", (sid,)
        ).fetchone()
        meta = json.loads(row["metadata_json"])
        fmt = meta["insight_format"]

        assert row["insight"] == fmt["generalized_content"]
        assert fmt["title"] == "Prefer cross-suite mechanisms before promotion"
        assert fmt["specificity_flags"] == []

    def test_audit_insight_specificity_flags_task_specific_entries(self, store):
        sid = store.store(
            "scripts/autopilot/foo.py improved trial #123",
            "Keep commit abc1234 behavior from /mnt/raid0/llm/example/path.",
            source_trial_id=123,
            species="structural_lab",
        )

        findings = store.audit_insight_specificity()

        assert len(findings) == 1
        assert findings[0]["id"] == sid
        assert findings[0]["source_trial_id"] == 123
        assert findings[0]["species"] == "structural_lab"
        assert findings[0]["specificity_flags"] == [
            "absolute_path",
            "commit_hash",
            "repo_path",
            "trial_reference",
        ]

    def test_audit_insight_specificity_skips_folded_journal_excluded_evidence(self, store):
        excluded_id = store.store(
            "scripts/autopilot/foo.py improved trial #123",
            "Keep commit abc1234 behavior from /mnt/raid0/llm/example/path.",
            source_trial_id=123,
            species="structural_lab",
            evidence_trial_ids=[123],
        )
        kept_id = store.store(
            "scripts/autopilot/bar.py improved trial #124",
            "Keep commit def5678 behavior from /mnt/raid0/llm/other/path.",
            source_trial_id=124,
            species="prompt_forge",
            evidence_trial_ids=[124],
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=123, bug_corrupted_by="superseded"),
                ]

        findings = store.audit_insight_specificity(journal=FakeJournal())

        finding_ids = {item["id"] for item in findings}
        assert excluded_id not in finding_ids
        assert kept_id in finding_ids

    def test_list_conventions_skips_folded_journal_excluded_evidence(self, store):
        excluded_id = store.add_convention(
            representative="excluded convention",
            member_ids=["a", "b"],
            compression_ratio=0.25,
            span_trials=(10, 11),
            evidence_trial_ids=[10, 11],
        )
        kept_id = store.add_convention(
            representative="kept convention",
            member_ids=["c", "d"],
            compression_ratio=0.30,
            span_trials=(12, 13),
            evidence_trial_ids=[12, 13],
        )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=11, bug_corrupted_by="superseded"),
                ]

        default_ids = {item["id"] for item in store.list_conventions()}
        filtered_ids = {
            item["id"]
            for item in store.list_conventions(journal=FakeJournal())
        }

        assert default_ids == {excluded_id, kept_id}
        assert filtered_ids == {kept_id}


class TestAP28HybridRetrieval:
    """AP-28: FTS5 + RRF fusion, content-hash staleness, validity weighting."""

    def test_fts5_index_present(self, store):
        # FTS5 virtual table should exist after _init_schema
        rows = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='strategies_fts'"
        ).fetchall()
        assert len(rows) == 1
        assert getattr(store, "_fts_enabled", False) is True

    def test_entry_type_default_raw(self, store):
        sid = store.store("desc", "insight", source_trial_id=1, species="alpha")
        row = store._conn.execute(
            "SELECT entry_type FROM strategies WHERE id=?", (sid,)
        ).fetchone()
        assert row["entry_type"] == "raw"

    def test_entry_type_explicit(self, store):
        sid = store.store(
            "desc", "insight", source_trial_id=1, species="alpha", entry_type="pattern"
        )
        row = store._conn.execute(
            "SELECT entry_type FROM strategies WHERE id=?", (sid,)
        ).fetchone()
        assert row["entry_type"] == "pattern"

    def test_context_hash_recorded(self, store):
        sid = store.store("desc", "insight", source_trial_id=1, species="alpha")
        row = store._conn.execute(
            "SELECT context_hash FROM strategies WHERE id=?", (sid,)
        ).fetchone()
        # context files may not exist in tests → hash of empty input is fine,
        # we just need a non-NULL string value (incl. empty).
        assert row["context_hash"] is not None

    def test_default_context_files_use_live_worker_prompt(self):
        from orchestration.repl_memory.strategy_store import DEFAULT_CONTEXT_FILES

        assert DEFAULT_CONTEXT_FILES[-1].name == "worker_general.md"
        assert all(path.name != "worker_explore.md" for path in DEFAULT_CONTEXT_FILES)

    def test_bm25_exact_term_match(self, store):
        # FAISS via MockEmbedder is hash-based and has zero semantic fidelity.
        # BM25 must surface the entry that contains the exact query term.
        store.store("Speculation tuning for Qwen3.5", "Disable HSD",
                     source_trial_id=1, species="config_tuner")
        store.store("Increase ubatch size", "Throughput +20%",
                     source_trial_id=2, species="config_tuner")
        store.store("Cache hit rate optimisation", "Use prefix cache",
                     source_trial_id=3, species="config_tuner")

        results = store.retrieve("Qwen3.5 speculation", k=1)
        assert len(results) == 1
        assert "Qwen3.5" in results[0].description

    def test_rrf_fuses_both_signals(self, store):
        # Even when FAISS+BM25 disagree, RRF should produce a deterministic
        # ordering and never error.
        for i in range(8):
            store.store(f"Strategy {i}", f"Insight {i}",
                        source_trial_id=i, species="explorer")
        results = store.retrieve("Strategy 3", k=3)
        assert 1 <= len(results) <= 3
        # All returned entries must carry the diagnostic fields.
        for r in results:
            assert r.entry_type == "raw"
            assert r.staleness == 1.0
            assert 0.0 <= r.validity_score <= 1.0

    def test_quarantined_entries_excluded(self, store):
        sid = store.store("Quarantine me", "should be hidden",
                          source_trial_id=1, species="alpha")
        # Force quarantine via repeated failures (NIB2-41 pathway)
        for _ in range(20):
            store.update_validity(sid, failure=True)
        results = store.retrieve("Quarantine", k=5)
        assert all(r.id != sid for r in results)
        # And re-includable when explicitly requested
        results_full = store.retrieve("Quarantine", k=5, include_quarantined=True)
        assert any(r.id == sid for r in results_full)

    def test_staleness_penalises_old_entries(self, store):
        # Insert with fixed hash, then pretend the world moved on by
        # rewriting compute_context_hash to return a different string.
        store.store("Old entry", "from epoch A", source_trial_id=1, species="alpha")
        # Confirm it's currently fresh
        results = store.retrieve("Old entry", k=1)
        assert results[0].staleness == 1.0
        # Force a different epoch by monkeypatching the helper
        store.compute_context_hash = lambda *a, **kw: "DIFFERENTHASH0001"
        results = store.retrieve("Old entry", k=1)
        assert results[0].staleness == 0.5

    def test_purge_strategy_campaign_removes_retrieval_mirrors(self, store):
        store.store("kept", "kept insight", source_trial_id=1, species="alpha")
        deleted_id = store.store(
            "expert_parallelism guardrail",
            "Do not toggle expert_parallelism",
            source_trial_id=2,
            species="structural_lab",
            metadata={"seed_campaign": "operator-handoff-distillation"},
            entry_type="convention",
            entry_id="opseed-guardrail-ep-needs-canonical",
        )

        report = store.purge_strategy_campaign("operator-handoff-distillation")

        assert report["deleted_count"] == 1
        assert report["deleted_ids"] == [deleted_id]
        assert report["indexes"]["sqlite_count"] == 1
        assert report["indexes"]["faiss_count"] == 1
        assert store.count() == 1
        fts_rows = store._conn.execute(
            "SELECT id FROM strategies_fts WHERE id = ?", (deleted_id,)
        ).fetchall()
        assert fts_rows == []
        results = store.retrieve(
            "expert_parallelism guardrail",
            k=5,
            include_quarantined=True,
        )
        assert all(result.id != deleted_id for result in results)

    def test_search_index_health_detects_sqlite_rows_missing_from_mirrors(self, store):
        store.store("kept", "kept insight", source_trial_id=1, species="alpha")
        store._conn.execute(
            "INSERT INTO strategies(id, description, insight, source_trial_id, species, "
            "created_at, metadata_json, entry_type, context_hash, evidence_trial_ids) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "sqlite-only",
                "sqlite only strategy",
                "missing from mirrors",
                2,
                "alpha",
                "now",
                "{}",
                "raw",
                "",
                "[2]",
            ),
        )
        store._conn.commit()

        health = store.search_index_health()

        assert not health["healthy"]
        assert health["sqlite_count"] == 2
        assert health["faiss_count"] == 1
        assert health["missing_faiss_count"] == 1
        assert health["missing_faiss_ids"] == ["sqlite-only"]
        if health["fts_enabled"]:
            assert health["missing_fts_count"] == 1

        rebuilt = store.rebuild_search_indexes()
        assert rebuilt["sqlite_count"] == 2
        assert rebuilt["faiss_count"] == 2
        assert store.search_index_health()["healthy"]

    def test_search_index_health_refreshes_external_faiss_writer(self, tmp_path):
        from orchestration.repl_memory.strategy_store import StrategyStore

        strategy_path = tmp_path / "strategies"
        live_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        writer_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        try:
            writer_store.store(
                "external search health row",
                "live store should refresh before reporting health",
                source_trial_id=4,
                species="alpha",
            )

            health = live_store.search_index_health()

            assert health["healthy"]
            assert health["sqlite_count"] == 1
            assert health["faiss_count"] == 1
            assert live_store._faiss.id_map
        finally:
            writer_store.close()
            live_store.close()

    def test_rebuild_search_indexes_retries_after_stale_save_and_rereads_sqlite(
        self,
        monkeypatch,
        store,
    ):
        from orchestration.repl_memory.faiss_store import StaleFAISSSaveError

        store.store("initial", "initial insight", source_trial_id=1, species="alpha")
        original_publish = store._publish_search_indexes_from_rows
        snapshots: list[list[str]] = []

        def fake_publish(rows):
            snapshots.append([str(row["id"]) for row in rows])
            if len(snapshots) == 1:
                with sqlite3.connect(store._db_path) as conn:
                    conn.execute(
                        "INSERT INTO strategies(id, description, insight, source_trial_id, "
                        "species, created_at, metadata_json, entry_type, context_hash, "
                        "evidence_trial_ids) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            "late-external",
                            "late external",
                            "must survive rebuild retry",
                            2,
                            "alpha",
                            "later",
                            "{}",
                            "raw",
                            "",
                            "[2]",
                        ),
                    )
                    conn.commit()
                raise StaleFAISSSaveError("simulated stale save")
            return original_publish(rows)

        monkeypatch.setattr(store, "_publish_search_indexes_from_rows", fake_publish)

        report = store.rebuild_search_indexes()

        assert len(snapshots) == 2
        assert "late-external" not in snapshots[0]
        assert "late-external" in snapshots[1]
        assert report["sqlite_count"] == 2
        assert report["faiss_count"] == 2
        assert store.search_index_health()["healthy"]

    def test_rebuild_search_indexes_abort_does_not_publish_partial_faiss(
        self,
        monkeypatch,
        tmp_path,
    ):
        from orchestration.repl_memory.strategy_store import StrategyStore

        strategy_path = tmp_path / "strategies"
        live_store = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        try:
            live_store.store("first", "first insight", source_trial_id=1, species="alpha")
            live_store.store("second", "second insight", source_trial_id=2, species="alpha")
            assert live_store.search_index_health()["healthy"]
            original_embed = live_store._embed
            calls = 0

            def fail_second_embed(text):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("simulated embed failure")
                return original_embed(text)

            monkeypatch.setattr(live_store, "_embed", fail_second_embed)

            with pytest.raises(RuntimeError, match="simulated embed failure"):
                live_store.rebuild_search_indexes()
        finally:
            live_store.close()

        reopened = StrategyStore(
            path=strategy_path,
            embedding_dim=1024,
            embedder=MockEmbedder(),
        )
        try:
            health = reopened.search_index_health()

            assert health["healthy"]
            assert health["sqlite_count"] == 2
            assert health["faiss_count"] == 2
            assert health["missing_faiss_count"] == 0
        finally:
            reopened.close()

    def test_retrieve_falls_back_to_fts_when_faiss_mirror_is_empty(self, store):
        if not getattr(store, "_fts_enabled", False):
            pytest.skip("FTS5 unavailable")
        store._conn.execute(
            "INSERT INTO strategies(id, description, insight, source_trial_id, species, "
            "created_at, metadata_json, entry_type, context_hash, evidence_trial_ids) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "fts-only",
                "unique bm25 fallback strategy",
                "served even when FAISS is empty",
                3,
                "alpha",
                "now",
                "{}",
                "raw",
                "",
                "[3]",
            ),
        )
        store._conn.execute(
            "INSERT INTO strategies_fts(id, description, insight, species) "
            "VALUES (?, ?, ?, ?)",
            (
                "fts-only",
                "unique bm25 fallback strategy",
                "served even when FAISS is empty",
                "alpha",
            ),
        )
        store._conn.commit()

        results = store.retrieve("unique bm25 fallback", k=1, species="alpha")

        assert [entry.id for entry in results] == ["fts-only"]

    def test_backfill_fts_idempotent(self, store):
        # Insert directly into ``strategies`` bypassing the store() FTS path,
        # then call backfill_fts to populate the index.
        store._conn.execute(
            "INSERT INTO strategies(id, description, insight, source_trial_id, species, "
            "created_at, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("legacy-1", "legacy desc", "legacy insight", 1, "old", "now", "{}"),
        )
        store._conn.commit()
        n1 = store.backfill_fts()
        assert n1 >= 1
        # Idempotent: second call should not double-insert.
        n2 = store.backfill_fts()
        assert n2 == 0

    def test_bm25_handles_punctuation_safely(self, store):
        # FTS5 MATCH chokes on raw punctuation; sanitiser must handle it.
        store.store("Mutation type=targeted_fix", "boost q",
                    source_trial_id=1, species="prompt_forge")
        # Punctuation-heavy query should not raise.
        results = store.retrieve("type=targeted_fix?!", k=2)
        assert isinstance(results, list)
