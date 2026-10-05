"""Tests for NIB2-41 StructuralLab mutation primitives.

Covers ``mdl_compress_strategies`` and ``staleness_invalidate_strategies``
plus the underlying ``StrategyStore`` schema extensions (conventions,
validity, content_hashes) and the cascade step that flags
``routing_classifier_meta.json`` as stale.
"""

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
    s = StrategyStore(path=tmp_path / "strategies", embedding_dim=1024,
                      embedder=MockEmbedder())
    yield s
    s.close()


@pytest.fixture
def lab():
    from scripts.autopilot.species.structural_lab import StructuralLab
    return StructuralLab(orchestrator_url="http://unused-test:0")


# ── M1: MDL compression ─────────────────────────────────────────────

def test_mdl_compresses_near_duplicate_cluster(store, lab):
    """3 near-identical insights should promote to one convention with ratio > 0.20."""
    base = "Disable self-speculation for dense models because HSD overhead dominates on CPU"
    for i in range(3):
        store.store(
            description=f"try-{i}",
            insight=base + f" variant detail {i}",
            source_trial_id=i,
            species="config_tuner",
            evidence_trial_ids=[10 + i, 20 + i],
        )

    result = lab.mdl_compress_strategies(
        strategy_store=store,
        min_cluster_size=3,
        jaccard_threshold=0.50,
        compression_threshold=0.10,
    )

    assert result["status"] == "ok"
    assert result["conventions_promoted"] >= 1
    assert result["total_compression_saved_bytes"] > 0
    conventions = store.list_conventions()
    assert len(conventions) >= 1
    assert len(conventions[0]["member_ids"]) >= 3
    assert conventions[0]["compression_ratio"] >= 0.10
    assert conventions[0]["evidence_trial_ids"] == [10, 11, 12, 20, 21, 22]


def test_mdl_longest_overgeneralization_cannot_become_live_binding(store, lab):
    common = "Disable self speculation when dense CPU decode overhead dominates"
    rows = [
        (common, "success", {"device": "cpu", "shape": "full"}),
        (common + " for measured full shape", "success", {"device": "cpu", "shape": "full"}),
        (
            common + " on every model including all GPU deployments without exception",
            "failure",
            {"device": "gpu", "shape": "all"},
        ),
    ]
    for index, (insight, outcome, qualifiers) in enumerate(rows):
        store.store(
            description=f"commitment-{index}",
            insight=insight,
            source_trial_id=200 + index,
            species="structural_lab",
            evidence_trial_ids=[200 + index],
            metadata={
                "bind_status": "live",
                "bind_identifiers": ["self_speculation"],
                "qualifiers": qualifiers,
                "support_outcome": outcome,
            },
        )

    result = lab.mdl_compress_strategies(
        strategy_store=store,
        min_cluster_size=3,
        jaccard_threshold=0.40,
        compression_threshold=0.0,
    )

    assert result["conventions_promoted"] == 1
    convention = store.list_conventions()[0]
    assert convention["representative"] == common
    assert convention["metadata"]["binding_mode"] == "advisory_only"
    assert convention["metadata"]["bind_status"] == "context"
    assert convention["metadata"]["bind_identifiers"] == []
    assert "supporting_trials_disagree" in convention["metadata"]["failure_reasons"]
    assert any(
        "every" in delta["claims"]["insight"]
        for delta in convention["metadata"]["advisory_member_claims"]
    )


def test_mdl_compress_skips_folded_journal_excluded_evidence(store, lab):
    """Convention promotion must not aggregate evidence quarantined by journal view."""
    base = "Disable self-speculation for dense models because HSD overhead dominates on CPU"
    for i in range(3):
        store.store(
            description=f"try-{i}",
            insight=base + f" variant detail {i}",
            source_trial_id=i,
            species="config_tuner",
            evidence_trial_ids=[10 + i],
        )

    class FakeJournal:
        def entries_with_supersessions(self):
            return [
                SimpleNamespace(trial_id=11, bug_corrupted_by="superseded"),
            ]

    result = lab.mdl_compress_strategies(
        strategy_store=store,
        journal=FakeJournal(),
        min_cluster_size=3,
        jaccard_threshold=0.50,
        compression_threshold=0.10,
    )

    assert result["status"] == "ok"
    assert result["conventions_promoted"] == 0
    assert store.list_conventions() == []


def test_mdl_fails_closed_without_journal_aware_store_api(lab):
    class LegacyStore:
        _conn = object()

    class FakeJournal:
        def entries_with_supersessions(self):
            return []

    with pytest.raises(RuntimeError, match="strategy_rows_for_compression"):
        lab.mdl_compress_strategies(
            strategy_store=LegacyStore(),
            journal=FakeJournal(),
        )


def test_mdl_does_not_compress_below_threshold(store, lab):
    """Dissimilar insights (low Jaccard or high MDL_after) should NOT promote."""
    insights = [
        "Reduce draft_max from 16 to 4 on worker role",
        "Switch coder quant from Q4KM to Q6K when context > 32k",
        "Enable frontdoor batch mode for cold-start reranker queries",
    ]
    for i, ins in enumerate(insights):
        store.store(
            description=f"diverse-{i}", insight=ins,
            source_trial_id=i, species="config_tuner",
        )
    result = lab.mdl_compress_strategies(
        strategy_store=store,
        min_cluster_size=2,
        jaccard_threshold=0.60,
        compression_threshold=0.20,
    )
    assert result["status"] == "ok"
    assert result["conventions_promoted"] == 0


def test_mdl_noop_on_empty_store(store, lab):
    result = lab.mdl_compress_strategies(strategy_store=store)
    assert result["status"] == "ok"
    assert result["clusters_examined"] == 0
    assert result["conventions_promoted"] == 0


# ── M2: staleness invalidation ──────────────────────────────────────

def test_staleness_increments_validity_failure_on_hash_change(store, lab, tmp_path):
    """When a scanned file's hash changes, referring strategies lose validity."""
    prompt = tmp_path / "my_prompt.md"
    prompt.write_text("# Original content\nfoo bar")
    sid = store.store(
        description="references my_prompt",
        insight="uses my_prompt for routing",
        source_trial_id=1,
        species="config_tuner",
        metadata={"refs": [str(prompt)]},
    )

    # First scan: records baseline hash, no failure fires.
    r1 = lab.staleness_invalidate_strategies(
        strategy_store=store, scan_targets=[str(prompt)],
    )
    assert r1["status"] == "ok"
    assert r1["hashes_changed"] == 0

    # Mutate file, rescan: hash changes → referring strategy gets a failure.
    prompt.write_text("# Modified content\nfoo baz\nextra line")
    r2 = lab.staleness_invalidate_strategies(
        strategy_store=store, scan_targets=[str(prompt)],
    )
    assert r2["hashes_changed"] == 1
    assert r2["strategies_touched"] == 1
    assert r2["quarantined"] + r2["suspected"] >= 0  # first failure may not quarantine yet

    row = store._conn.execute(
        "SELECT beta_fail FROM strategy_validity WHERE strategy_id = ?", (sid,),
    ).fetchone()
    assert row["beta_fail"] == 1


def test_staleness_skips_folded_journal_excluded_evidence(store, lab, tmp_path):
    """Refuted strategy evidence must not drive staleness side effects."""
    prompt = tmp_path / "my_prompt.md"
    prompt.write_text("# Original content\nfoo bar")
    sid = store.store(
        description="references my_prompt",
        insight="uses my_prompt for routing",
        source_trial_id=1,
        species="config_tuner",
        metadata={"refs": [str(prompt)]},
        evidence_trial_ids=[11],
    )

    class FakeJournal:
        def entries_with_supersessions(self):
            return [
                SimpleNamespace(
                    trial_id=11,
                    eval_details={"learning_exclusion": {"by": "seq_accumulating"}},
                ),
            ]

    # First scan records baseline hash. The exclusion affects strategy rows, not
    # target hash tracking.
    lab.staleness_invalidate_strategies(
        strategy_store=store,
        journal=FakeJournal(),
        scan_targets=[str(prompt)],
    )

    prompt.write_text("# Modified content\nfoo baz\nextra line")
    result = lab.staleness_invalidate_strategies(
        strategy_store=store,
        journal=FakeJournal(),
        scan_targets=[str(prompt)],
    )

    assert result["hashes_changed"] == 1
    assert result["strategies_checked"] == 0
    assert result["strategies_touched"] == 0
    row = store._conn.execute(
        "SELECT beta_fail FROM strategy_validity WHERE strategy_id = ?", (sid,),
    ).fetchone()
    assert row is None or row["beta_fail"] == 0


def test_staleness_fails_closed_without_journal_aware_store_api(lab):
    class LegacyStore:
        _conn = object()

    class FakeJournal:
        def entries_with_supersessions(self):
            return []

    with pytest.raises(RuntimeError, match="strategy_rows_for_staleness_scan"):
        lab.staleness_invalidate_strategies(
            strategy_store=LegacyStore(),
            journal=FakeJournal(),
            scan_targets=[],
        )


def test_staleness_quarantines_below_threshold(store, lab, tmp_path):
    """Enough failures push validity < 0.40 and flip the quarantine flag."""
    prompt = tmp_path / "my_prompt.md"
    prompt.write_text("# initial")
    sid = store.store(
        description="references my_prompt",
        insight="uses my_prompt for routing",
        source_trial_id=1,
        species="config_tuner",
        metadata={"refs": [str(prompt)]},
    )
    # Seed baseline hash.
    lab.staleness_invalidate_strategies(strategy_store=store, scan_targets=[str(prompt)])

    # α starts at 2; quarantine_threshold 0.40 means β_fail ≥ 4 → 2/(2+4)=0.33 < 0.40.
    # Mutate + rescan 5 times to guarantee threshold crossed.
    for i in range(5):
        prompt.write_text(f"mutation {i}")
        lab.staleness_invalidate_strategies(
            strategy_store=store, scan_targets=[str(prompt)],
            quarantine_threshold=0.40,
        )

    quarantined_ids = store.quarantined_ids()
    assert sid in quarantined_ids

    # Quarantined strategies are omitted from default retrieve().
    entries = store.retrieve("routing", k=5)
    assert all(e.id != sid for e in entries)
    # include_quarantined=True surfaces them again.
    entries_all = store.retrieve("routing", k=5, include_quarantined=True)
    assert any(e.id == sid for e in entries_all)


def test_cascade_invalidates_routing_classifier_checkpoint(store, lab, tmp_path, monkeypatch):
    """Quarantined strategy that trained the routing classifier → meta.stale=True."""
    # Redirect ORCH_ROOT so the cascade writes into tmp_path.
    from scripts.autopilot.species import structural_lab as sl_mod

    classifier_meta = tmp_path / "orchestration" / "repl_memory" / "routing_classifier_meta.json"
    classifier_meta.parent.mkdir(parents=True, exist_ok=True)

    prompt = tmp_path / "p.md"
    prompt.write_text("v1")
    sid = store.store(
        description="classifier training signal",
        insight="used by routing MLP",
        source_trial_id=1,
        species="config_tuner",
        metadata={"refs": [str(prompt)]},
    )

    classifier_meta.write_text(json.dumps({
        "training_strategy_ids": [sid],
        "trained_at": "2026-04-01T00:00:00Z",
    }))

    monkeypatch.setattr(sl_mod, "ORCH_ROOT", tmp_path)

    lab.staleness_invalidate_strategies(
        strategy_store=store, scan_targets=[str(prompt)],
    )
    for i in range(6):
        prompt.write_text(f"mutation {i}")
        lab.staleness_invalidate_strategies(
            strategy_store=store, scan_targets=[str(prompt)],
            quarantine_threshold=0.40,
        )

    assert sid in store.quarantined_ids()
    meta_now = json.loads(classifier_meta.read_text())
    assert meta_now.get("stale") is True
    assert "stale_at" in meta_now


def test_structural_lab_memory_count_reads_sqlite_without_episodic_store_import(tmp_path, monkeypatch):
    from scripts.autopilot.species import structural_lab as sl_mod

    db_path = tmp_path / "episodic.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE memories (id TEXT PRIMARY KEY, action_type TEXT NOT NULL)"
        )
        conn.executemany(
            "INSERT INTO memories (id, action_type) VALUES (?, ?)",
            [("a", "routing"), ("b", "routing"), ("c", "exploration")],
        )
        conn.commit()

    monkeypatch.setattr(sl_mod, "EPISODIC_DB", db_path)
    lab = sl_mod.StructuralLab(orchestrator_url="http://unused-test:0")
    assert lab.summary()["memory_count"] == 2


def test_checkpoint_state_snapshots_ap22_and_strategy_store(tmp_path, monkeypatch):
    from scripts.autopilot.species import structural_lab as sl_mod

    checkpoint_dir = tmp_path / "checkpoints"
    ap22_memory = tmp_path / "orchestration" / "autopilot_short_term_memory.md"
    strategy_dir = tmp_path / "orchestration" / "repl_memory" / "strategies"
    ap22_memory.parent.mkdir(parents=True, exist_ok=True)
    strategy_dir.mkdir(parents=True, exist_ok=True)
    ap22_memory.write_text("checkpoint memory")
    (strategy_dir / "strategies.db").write_text("checkpoint strategy db")

    monkeypatch.setattr(sl_mod, "CHECKPOINT_DIR", checkpoint_dir)
    monkeypatch.setattr(sl_mod, "CHECKPOINT_FILES", {})
    monkeypatch.setattr(sl_mod, "PROMPTS_DIR", tmp_path / "missing-prompts")
    monkeypatch.setattr(sl_mod, "CLASSIFIER_CONFIG", tmp_path / "missing.yaml")
    monkeypatch.setattr(sl_mod, "AP22_MEMORY", ap22_memory)
    monkeypatch.setattr(sl_mod, "STRATEGY_STORE_DIR", strategy_dir)

    lab = sl_mod.StructuralLab(orchestrator_url="http://unused-test:0")
    monkeypatch.setattr(lab, "_get_memory_count", lambda: 0)

    checkpoint = lab.checkpoint_state(trial_id=123)

    assert (checkpoint / "autopilot_short_term_memory.md").read_text() == "checkpoint memory"
    assert (checkpoint / "strategy_store" / "strategies.db").read_text() == (
        "checkpoint strategy db"
    )


def test_restore_checkpoint_rewinds_ap22_and_strategy_store(tmp_path, monkeypatch):
    from scripts.autopilot.species import structural_lab as sl_mod

    checkpoint = tmp_path / "checkpoints" / "cp1"
    checkpoint.mkdir(parents=True)
    (checkpoint / "autopilot_short_term_memory.md").write_text("restored memory")
    strategy_cp = checkpoint / "strategy_store"
    strategy_cp.mkdir()
    (strategy_cp / "strategies.db").write_text("restored strategy db")

    ap22_memory = tmp_path / "orchestration" / "autopilot_short_term_memory.md"
    strategy_dir = tmp_path / "orchestration" / "repl_memory" / "strategies"
    ap22_memory.parent.mkdir(parents=True, exist_ok=True)
    strategy_dir.mkdir(parents=True, exist_ok=True)
    ap22_memory.write_text("stale memory")
    (strategy_dir / "strategies.db").write_text("stale strategy db")
    (strategy_dir / "stale.faiss").write_text("must be removed")

    monkeypatch.setattr(sl_mod, "CHECKPOINT_FILES", {})
    monkeypatch.setattr(sl_mod, "PROMPTS_DIR", tmp_path / "missing-prompts")
    monkeypatch.setattr(sl_mod, "CLASSIFIER_CONFIG", tmp_path / "missing.yaml")
    monkeypatch.setattr(sl_mod, "AP22_MEMORY", ap22_memory)
    monkeypatch.setattr(sl_mod, "STRATEGY_STORE_DIR", strategy_dir)

    lab = sl_mod.StructuralLab(orchestrator_url="http://unused-test:0")
    result = lab.restore_checkpoint(checkpoint)

    assert result["status"] == "ok"
    assert ap22_memory.read_text() == "restored memory"
    assert (strategy_dir / "strategies.db").read_text() == "restored strategy db"
    assert not (strategy_dir / "stale.faiss").exists()
    assert "autopilot_short_term_memory.md" in result["restored"]
    assert "strategy_store/" in result["restored"]


def test_restore_old_checkpoint_clears_uncheckpointed_planner_memory(
    tmp_path, monkeypatch
):
    from scripts.autopilot.species import structural_lab as sl_mod

    checkpoint = tmp_path / "checkpoints" / "old"
    checkpoint.mkdir(parents=True)
    ap22_memory = tmp_path / "orchestration" / "autopilot_short_term_memory.md"
    strategy_dir = tmp_path / "orchestration" / "repl_memory" / "strategies"
    ap22_memory.parent.mkdir(parents=True, exist_ok=True)
    strategy_dir.mkdir(parents=True, exist_ok=True)
    ap22_memory.write_text("post-checkpoint memory")
    (strategy_dir / "strategies.db").write_text("post-checkpoint strategy db")

    monkeypatch.setattr(sl_mod, "CHECKPOINT_FILES", {})
    monkeypatch.setattr(sl_mod, "PROMPTS_DIR", tmp_path / "missing-prompts")
    monkeypatch.setattr(sl_mod, "CLASSIFIER_CONFIG", tmp_path / "missing.yaml")
    monkeypatch.setattr(sl_mod, "AP22_MEMORY", ap22_memory)
    monkeypatch.setattr(sl_mod, "STRATEGY_STORE_DIR", strategy_dir)

    lab = sl_mod.StructuralLab(orchestrator_url="http://unused-test:0")
    result = lab.restore_checkpoint(checkpoint)

    assert result["status"] == "ok"
    assert not ap22_memory.exists()
    assert not strategy_dir.exists()
    assert "autopilot_short_term_memory.md:cleared" in result["restored"]
    assert "strategy_store/:cleared" in result["restored"]


def _lab_with_flags(monkeypatch, current):
    from scripts.autopilot.species import structural_lab as sl_mod
    lab = sl_mod.StructuralLab(orchestrator_url="http://unused-test:0")
    monkeypatch.setattr(lab, "current_flags", lambda: dict(current))
    return lab


def test_propose_flag_validates_merged_live_state_single_dependency(monkeypatch):
    """Enabling a dependent flag one-at-a-time validates against the merged live
    config, not the partial patch (the High blocker fix)."""
    # memrl is live-ON → enabling specialist_routing alone is valid.
    lab = _lab_with_flags(monkeypatch, {"memrl": True, "specialist_routing": False})
    assert lab.propose_flag_experiment({"specialist_routing": True})["status"] == "valid"

    # specialist_routing live-ON → enabling graph_router alone is valid.
    lab = _lab_with_flags(
        monkeypatch, {"memrl": True, "specialist_routing": True, "graph_router": False}
    )
    assert lab.propose_flag_experiment({"graph_router": True})["status"] == "valid"


def test_propose_flag_still_rejects_when_merged_dependency_unmet(monkeypatch):
    """A genuine dependency violation against KNOWN live state stays 'invalid'
    (blacklist-eligible)."""
    # memrl live-OFF → graph_router can't be enabled (needs specialist_routing→memrl).
    lab = _lab_with_flags(monkeypatch, {"memrl": False, "specialist_routing": False})
    result = lab.propose_flag_experiment({"graph_router": True})
    assert result["status"] == "invalid"
    assert any("specialist_routing" in e for e in result["errors"])


def test_propose_flag_unreadable_live_state_is_error_not_invalid(monkeypatch):
    """When live flags can't be read, a dependency failure is NOT trustworthy →
    status 'error' (non-blacklisting), not 'invalid' (the Medium fix)."""
    lab = _lab_with_flags(monkeypatch, {})  # orchestrator unreachable
    result = lab.propose_flag_experiment({"graph_router": True})
    assert result["status"] == "error"
    assert "unavailable" in result["error"]


def test_propose_flag_unknown_name_is_invalid_regardless_of_live_state(monkeypatch):
    lab = _lab_with_flags(monkeypatch, {})
    result = lab.propose_flag_experiment({"not_a_real_flag": True})
    assert result["status"] == "invalid"
    assert "Unknown flags" in result["errors"][0]


def test_train_routing_models_spawns_venv_interpreter_not_bare_python(tmp_path, monkeypatch):
    """Regression: the three routing-model trainers must be launched with the
    current venv interpreter (sys.executable), never a bare 'python'.

    The autopilot daemon runs under .venv/bin/python in a runtime where 'python'
    is not on PATH; bare-'python' spawns failed with FileNotFoundError, silently
    turning every train_routing_models trial into three error results.
    """
    from scripts.autopilot.species import structural_lab as sl_mod

    captured: list[list[str]] = []

    class _FakeCompleted:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kwargs):
        captured.append(cmd)
        return _FakeCompleted()

    # Capture argv instead of actually launching the trainers.
    monkeypatch.setattr(sl_mod.subprocess, "run", _fake_run)

    lab = sl_mod.StructuralLab(orchestrator_url="http://unused-test:0")
    # Clear the memory gate so all three trainer stages dispatch.
    monkeypatch.setattr(lab, "_get_memory_count", lambda: 10_000)

    results = lab.train_routing_models(min_memories=500)

    # extraction + classifier + graph_router all dispatched (scripts exist in-repo).
    assert len(captured) == 3, captured
    for cmd in captured:
        assert cmd[0] == sys.executable
        assert cmd[0] != "python"
    assert all(results[k]["status"] == "ok" for k in ("extraction", "classifier", "graph_router"))
    assert results["memory_count"] == 10_000
