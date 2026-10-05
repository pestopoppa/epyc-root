"""Regression tests for the one-use deterministic E8 terminal bridge."""
# NIB2-75 (2026-09-23): tests that needed the retired E8 sealed bundles were removed per OP-19.
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/benchmark/terminalize_e8_quality_baseline_v5_partial_r2_successor.py"
SPEC = importlib.util.spec_from_file_location("e8_terminalizer_test", PATH)
assert SPEC and SPEC.loader
TERMINALIZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TERMINALIZER)

def test_copy_tree_rejects_a_source_mutation(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    item = source / "immutable.txt"
    item.write_text("before")
    manifest = TERMINALIZER.RACE.source_hashes(source)
    item.write_text("after")

    with pytest.raises(ValueError, match="changed while copying"):
        TERMINALIZER._copy_tree(source, destination, manifest)


def test_publish_never_replaces_a_concurrent_destination(tmp_path: Path) -> None:
    source, destination = tmp_path / "staging", tmp_path / "published"
    source.mkdir()
    destination.mkdir()

    with pytest.raises(FileExistsError):
        TERMINALIZER._rename_noreplace(source, destination)


def test_restart_surface_predicate_requires_an_affirmative_warm_state() -> None:
    sidecars = {
        0: (0, {"result": {"host_covariates": {"cache_warm_state": "warm"}}}),
        1: (1, {"result": {"host_covariates": {"cache_warm_state": "cold"}}}),
        2: (2, {"result": {}}),
    }
    predicate = TERMINALIZER.MIXED._restart_surface_eligibility(sidecars, [0, 1, 2])
    assert predicate == {
        "predicate": "all_result_host_covariates_cache_warm_state_eq_warm.v1",
        "covered_generation_ordinals": [0, 1, 2],
        "cache_warm_state_counts": {"cold": 1, "missing": 1, "warm": 1},
        "eligible": False,
    }


