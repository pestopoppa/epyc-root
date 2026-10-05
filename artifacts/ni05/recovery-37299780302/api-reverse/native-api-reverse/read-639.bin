from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "scripts/autopilot/operator_candidates/ratify_and_apply_multitier_baseline_v10.py"
)
SPEC = importlib.util.spec_from_file_location("ratify_multitier_v10", MODULE_PATH)
assert SPEC and SPEC.loader
ratifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ratifier)


def _evidence(tier: int, quality: float, started_at: str) -> dict:
    return {
        "started_at": started_at,
        "eval_result": {
            "quality": quality,
            "speed": 20.0 + tier,
            "cost": 0.5,
            "reliability": 1.0,
            "per_suite_quality": {"suite": quality},
            "per_suite_counts": {"suite": tier * 10},
        },
        "tier_baseline_evidence": {
            "schema_version": "multitier-tier-baseline.v1",
            "policy_version": ratifier.MULTITIER_POLICY,
            "tier": tier,
            "outcomes": {f"q{tier}": True},
        },
    }


def test_state_candidate_enables_matched_multitier_policy_and_preserves_pause():
    evidence = {
        1: _evidence(1, 1.5, "2026-08-10T19:30:52Z"),
        2: _evidence(2, 1.356, "2026-08-10T16:23:03Z"),
        3: _evidence(3, 1.275, "2026-08-10T16:23:52Z"),
    }
    original = {
        "paused": True,
        "in_flight_trial": None,
        "active_instrument_eras": {"cpu_bench": "E8-cpu-kernel"},
        "frontier_rerun_required": {"required": False},
    }

    candidate, boundary = ratifier.build_state_candidate(original, evidence)

    assert boundary == "2026-08-10T16:23:03Z"
    assert candidate["paused"] is True
    assert candidate["in_flight_trial"] is None
    assert candidate["baseline_state"]["baselines_by_tier"] == {
        "1": 1.5,
        "2": 1.356,
        "3": 1.275,
    }
    assert set(candidate["multitier_baseline_bundle"]["tiers"]) == {"1", "2", "3"}
    assert candidate["multitier_promotion_policy"]["enabled"] is True
    assert candidate["multitier_promotion_policy"]["required_tiers"] == [2, 3]
    assert candidate["active_instrument_eras"]["cpu_bench"] == "E8-cpu-kernel"
    assert candidate["frontier_rerun_required"]["previous_marker"] == {
        "required": False
    }


def test_append_eras_adds_complete_pair_and_is_idempotent():
    raw = b"eras:\n  - id: old\n    scope: eval_quality\n\nknown_dead_instrument_items: []\n"
    boundary = "2026-08-10T16:23:03Z"

    candidate = ratifier.append_eras(raw, boundary)
    parsed = yaml.safe_load(candidate)
    ids = {row["id"] for row in parsed["eras"]}

    assert ratifier.QUALITY_ERA in ids
    assert ratifier.SPEED_ERA in ids
    assert ratifier.append_eras(candidate, boundary) == candidate


def test_production_checkpoint_publish_and_restore_is_atomic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    checkpoint_root = tmp_path / "checkpoints"
    final = checkpoint_root / "multitier_v10_20260810"
    link = checkpoint_root / "production_best"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    episodic = source_root / "episodic.db"
    import sqlite3

    with sqlite3.connect(episodic) as conn:
        conn.execute("CREATE TABLE episodes (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO episodes DEFAULT VALUES")
    prompts = source_root / "prompts"
    prompts.mkdir()
    (prompts / "frontdoor.md").write_text("prompt")
    old = checkpoint_root / "old"
    old.mkdir(parents=True)
    link.symlink_to(old)

    monkeypatch.setattr(ratifier, "CHECKPOINT_ROOT", checkpoint_root)
    monkeypatch.setattr(ratifier, "CHECKPOINT_PATH", final)
    monkeypatch.setattr(ratifier, "PRODUCTION_BEST_LINK", link)
    monkeypatch.setattr(ratifier, "CHECKPOINT_FILES", {"episodic.db": episodic})
    monkeypatch.setattr(ratifier, "CHECKPOINT_OPTIONAL_FILES", {})
    monkeypatch.setattr(ratifier, "CHECKPOINT_DIRS", {"prompts": prompts})
    state_after = b'{"paused": true}\n'

    staging, meta = ratifier._prepare_production_checkpoint(
        state_after=state_after,
        state={"trial_counter": 1506},
        bundle_sha="bundle",
    )
    previous = ratifier._publish_production_checkpoint(staging)

    assert link.resolve() == final
    assert (final / "autopilot_state.json").read_bytes() == state_after
    assert json.loads((final / "checkpoint_meta.json").read_text())["memory_count"] == 1
    assert meta["is_production_best"] is True

    ratifier._restore_production_best(previous)
    assert link.resolve() == old
    assert not final.exists()


def test_applied_era_registry_is_the_only_allowed_dirty_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    eras = tmp_path / "orchestration/instrument_eras.yaml"
    eras.parent.mkdir(parents=True)
    eras.write_text("eras: [applied]\n")
    applied_sha = ratifier._sha_path(eras)
    evidence = {
        1: {
            "source_sha256": {
                "orchestration/instrument_eras.yaml": "pre-apply-sha"
            }
        }
    }

    def fake_run(command, **_kwargs):
        if command[1:3] == ["rev-parse", "HEAD"]:
            return SimpleNamespace(returncode=0, stdout="head\n")
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(ratifier, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ratifier, "AUDITED_POST_COLLECTION_HASHES", {})
    monkeypatch.setattr(ratifier.subprocess, "run", fake_run)

    assert (
        ratifier.validate_current_sources(
            evidence, applied_eras_sha256=applied_sha
        )
        == "head"
    )
    with pytest.raises(SystemExit, match="source identity mismatch"):
        ratifier.validate_current_sources(evidence)
