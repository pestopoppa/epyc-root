"""Tests for KnowledgeDistiller — L1->L2->L3 strategy memory consolidation (AP-29)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class ClusterableEmbedder:
    """Embedder that produces tightly-clustered vectors for entries that share
    a substring tag.

    Each entry embeds to a base vector (one of the registered tags) plus a
    small per-entry noise vector. The cosine similarity between entries
    sharing a tag is far higher than the 0.75 cluster threshold, while
    entries with different tags are roughly orthogonal.
    """

    def __init__(self, dim: int = 32, tags: tuple[str, ...] = ("alpha", "beta", "gamma", "delta")):
        self.dim = dim
        rng = np.random.RandomState(0)
        self._base = {t: rng.randn(dim).astype(np.float32) for t in tags}
        for k, v in self._base.items():
            self._base[k] = v / (np.linalg.norm(v) + 1e-9)

    def embed_text(self, text: str) -> np.ndarray:
        # Pick the first registered tag that appears in the text.
        for tag, base in self._base.items():
            if tag in text:
                # Tiny per-text noise so different entries with the same tag
                # are not literally identical, while still > 0.99 cosine.
                rng = np.random.RandomState(
                    int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big")
                )
                noise = 0.01 * rng.randn(self.dim).astype(np.float32)
                v = base + noise
                return v / (np.linalg.norm(v) + 1e-9)
        # Fallback for unseen tags
        rng = np.random.RandomState(
            int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big")
        )
        v = rng.randn(self.dim).astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-9)


@pytest.fixture
def store(tmp_path):
    from orchestration.repl_memory.strategy_store import StrategyStore

    s = StrategyStore(
        path=tmp_path / "strategies",
        embedding_dim=32,
        embedder=ClusterableEmbedder(dim=32),
    )
    yield s
    s.close()


@pytest.fixture
def distiller(store):
    from orchestration.repl_memory.knowledge_distiller import KnowledgeDistiller

    return KnowledgeDistiller(store)


class TestKnowledgeDistiller:
    def test_no_action_below_mdl(self, store, distiller):
        # Below MDL_MIN_CLUSTER_SIZE — nothing should promote.
        store.store("alpha tag entry one", "rich detailed insight one",
                     source_trial_id=1, species="prompt_forge")
        store.store("alpha tag entry two", "rich detailed insight two",
                     source_trial_id=2, species="prompt_forge")
        stats = distiller.distill(trial_id=10)
        assert stats.patterns_created == 0
        assert stats.conventions_created == 0

    def test_l1_to_l2_pattern_promotion(self, store, distiller):
        # Three+ similar entries within a species → one pattern.
        for i in range(4):
            store.store(
                description=f"alpha tag detailed strategy entry index {i} long version",
                insight=f"alpha tag insight entry {i} with extra explanatory detail",
                source_trial_id=i,
                species="prompt_forge",
                evidence_trial_ids=[100 + i],
            )
        stats = distiller.distill(trial_id=20)
        assert stats.patterns_created == 1
        assert stats.raw_entries_consolidated == 4

        # Source rows must be quarantined → retrieve() should not return them.
        results = store.retrieve("alpha", k=10)
        # The pattern is the only thing left visible.
        types = [r.entry_type for r in results]
        assert "pattern" in types
        assert "raw" not in types

        pattern_row = store._conn.execute(
            "SELECT * FROM strategies WHERE entry_type = 'pattern'"
        ).fetchone()
        assert store._evidence_trial_ids_for_row(pattern_row) == [100, 101, 102, 103]
        convention_rows = store.list_conventions()
        assert len(convention_rows) == 1
        assert convention_rows[0]["evidence_trial_ids"] == [100, 101, 102, 103]
        assert store.retrieve("alpha", k=10, excluded_trial_ids={102}) == []

    def test_longest_member_overgeneralization_is_advisory_delta(self, store, distiller):
        common_description = "alpha tag disable speculation on measured dense CPU full shape"
        common_insight = "alpha tag overhead exceeded the measured decode benefit"
        for index in range(4):
            overgeneralized = index == 3
            store.store(
                description=(
                    common_description
                    + (" across every model GPU and workload without exception" if overgeneralized else "")
                ),
                insight=(
                    common_insight
                    + (" therefore always disable it globally" if overgeneralized else "")
                ),
                source_trial_id=300 + index,
                species="structural_lab",
                evidence_trial_ids=[300 + index],
                metadata={
                    "bind_status": "live",
                    "bind_identifiers": ["self_speculation"],
                    "qualifiers": (
                        {"device": "gpu", "scope": "all"}
                        if overgeneralized
                        else {"device": "cpu", "shape": "full"}
                    ),
                    "support_outcome": "failure" if overgeneralized else "success",
                },
            )

        stats = distiller.distill(trial_id=399)

        assert stats.patterns_created == 1
        row = store._conn.execute(
            "SELECT * FROM strategies WHERE entry_type = 'pattern'"
        ).fetchone()
        metadata = json.loads(row["metadata_json"])
        assert row["description"].startswith("[PATTERN][ADVISORY ONLY]")
        assert "every model" not in row["description"]
        assert metadata["binding_mode"] == "advisory_only"
        assert metadata["bind_identifiers"] == []
        assert len(metadata["source_members"]) == 4
        assert sorted(metadata["source_members"][0]) == [
            "bind_identifiers",
            "bind_status",
            "evidence_trial_ids",
            "id",
            "qualifiers",
            "source_trial_id",
        ]
        assert any(
            "every" in delta["claims"].get("description", "")
            for delta in metadata["advisory_member_claims"]
        )

    def test_binding_recoding_change_fails_closed(self):
        from orchestration.repl_memory.commitment_contract import (
            derive_commitment_contract,
        )

        entries = [
            {
                "id": f"s{index}",
                "description": "same harmless paraphrase",
                "insight": "same claim",
                "source_trial_id": index,
                "evidence_trial_ids": [index],
                "metadata": {
                    "bind_status": "live",
                    "bind_identifiers": ["kv_compaction"],
                    "qualifiers": {"role": "frontdoor"},
                    "binding_recodings": [
                        {
                            "bind_status": "live",
                            "bind_identifiers": ["different_surface"],
                            "qualifiers": {"role": "frontdoor"},
                        }
                    ],
                },
            }
            for index in range(3)
        ]

        contract = derive_commitment_contract(entries)

        assert contract["binding_mode"] == "advisory_only"
        assert contract["recoding_stable"] is False
        assert "binding_changes_under_recoding" in contract["failure_reasons"]

    def test_distill_skips_folded_journal_excluded_raw_evidence(self, store, distiller):
        excluded_id = store.store(
            description="alpha tag detailed strategy excluded long version",
            insight="alpha tag insight excluded with extra explanatory detail",
            source_trial_id=99,
            species="prompt_forge",
            evidence_trial_ids=[2],
        )
        for i in range(2):
            store.store(
                description=f"alpha tag detailed strategy kept index {i} long version",
                insight=f"alpha tag insight kept {i} with extra explanatory detail",
                source_trial_id=i,
                species="prompt_forge",
                evidence_trial_ids=[100 + i],
            )

        class FakeJournal:
            def entries_with_supersessions(self):
                return [
                    SimpleNamespace(trial_id=2, bug_corrupted_by="superseded"),
                ]

        stats = distiller.distill(trial_id=21, journal=FakeJournal())

        assert stats.patterns_created == 0
        assert stats.raw_entries_consolidated == 0
        row = store._conn.execute(
            "SELECT entry_type FROM strategies WHERE id = ?", (excluded_id,)
        ).fetchone()
        assert row["entry_type"] == "raw"

    def test_distill_fails_closed_without_journal_aware_store_api(self, distiller):
        class LegacyStore:
            _conn = object()

        distiller.store = LegacyStore()

        class FakeJournal:
            def entries_with_supersessions(self):
                return []

        with pytest.raises(RuntimeError, match="strategy_entries_for_distillation"):
            distiller._fetch_entries_by_type("raw", journal=FakeJournal())

    def test_pattern_skipped_when_not_compressible(self, store, distiller):
        # Cluster has one large seed and two tiny entries; the pattern row
        # would be larger than the cluster total → MDL check skips it.
        store.store(
            description="alpha tag " + ("very long detailed text " * 30),
            insight="alpha tag " + ("explanatory paragraph " * 30),
            source_trial_id=1,
            species="prompt_forge",
        )
        for i in range(2, 4):
            store.store(
                description=f"alpha {i}",
                insight="a",
                source_trial_id=i,
                species="prompt_forge",
            )
        stats = distiller.distill(trial_id=30)
        assert stats.patterns_created == 0
        assert stats.skipped_below_mdl >= 1

    def test_l2_to_l3_convention_cross_species(self, store, distiller):
        # Three species each with three+ similar raw entries → three patterns
        # → cross-species convention.
        for species in ("prompt_forge", "numeric_swarm", "structural_lab"):
            for i in range(3):
                source_trial_id = len(species) * 10 + i
                store.store(
                    description=f"alpha tag long shared description for {species} run {i}",
                    insight=f"alpha tag matching insight describing {species} trial {i}",
                    source_trial_id=i,
                    species=species,
                    evidence_trial_ids=[source_trial_id],
                    metadata={"test_source_trial_id": source_trial_id},
                )
        stats = distiller.distill(trial_id=40)
        assert stats.patterns_created >= 3
        assert stats.conventions_created >= 1

        # Convention must be stored under species='all'
        rows = store._conn.execute(
            "SELECT id, species FROM strategies WHERE entry_type = 'convention'"
        ).fetchall()
        assert len(rows) >= 1
        assert all(r["species"] == "all" for r in rows)

        convention = store._conn.execute(
            "SELECT * FROM strategies WHERE entry_type = 'convention' LIMIT 1"
        ).fetchone()
        convention_evidence = store._evidence_trial_ids_for_row(convention)
        source_pattern_ids = json.loads(convention["metadata_json"])["source_pattern_ids"]
        pattern_rows = store._conn.execute(
            "SELECT * FROM strategies WHERE id IN (%s)"
            % ",".join("?" for _ in source_pattern_ids),
            tuple(source_pattern_ids),
        ).fetchall()
        expected_evidence = sorted({
            trial_id
            for row in pattern_rows
            for trial_id in store._evidence_trial_ids_for_row(row)
        })
        assert sorted(convention_evidence) == expected_evidence

        excluded_trial = convention_evidence[0]
        visible = store.retrieve("alpha", k=20, excluded_trial_ids={excluded_trial})
        assert all(entry.id != convention["id"] for entry in visible)

    def test_idempotent(self, store, distiller):
        # Running distill twice must not double-promote.
        for i in range(4):
            store.store(
                description=f"beta tag detailed strategy entry index {i} long version",
                insight=f"beta tag insight entry {i} with extra explanatory detail",
                source_trial_id=i,
                species="seeder",
            )
        stats_a = distiller.distill(trial_id=50)
        stats_b = distiller.distill(trial_id=51)
        assert stats_a.patterns_created == 1
        assert stats_b.patterns_created == 0

    def test_distillation_stats_to_dict(self):
        from orchestration.repl_memory.knowledge_distiller import DistillationStats

        s = DistillationStats(patterns_created=2, conventions_created=1)
        d = s.to_dict()
        assert d["patterns_created"] == 2
        assert d["conventions_created"] == 1
        assert d["raw_entries_consolidated"] == 0
        assert d["notes"] == []
