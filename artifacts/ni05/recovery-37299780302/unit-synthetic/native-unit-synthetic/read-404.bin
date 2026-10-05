"""Tests for GraphRouter action-space derivation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest
import yaml

from scripts.graph_router.action_space import (
    DEGRADED_CANONICAL_ACTIONS,
    action_index_for_raw_label,
    canonical_actions_from_label_map,
    load_live_canonical_actions,
    normalize_action,
)
from scripts.graph_router.extract_training_data import extract as extract_training_data
from scripts.graph_router.extract_verifier_training_data import extract as extract_verifier_data
from scripts.graph_router.extract_verifier_training_data_debiased import (
    extract as extract_debiased_verifier_data,
)

LEGACY_ARCHITECT_ROLE = "architect" "_coding"

EXPECTED_ACTION_ORDER = [
    "frontdoor",
    "architect_general",
    "coder_escalation",
    "worker_general",
    "worker_math",
    "worker_vision",
    "ingest_long_context",
    "worker_summarize",
    "toolrunner",
    "vision_escalation",
]


def _stack_prior_record(role: str, *, deployment_status: str = "live_stack") -> dict:
    return {
        "role": role,
        "deployment_status": deployment_status,
        "status": "compiled",
        "model_id": f"{role}-model",
        "display_name": role,
        "serving": {
            "endpoint": "http://localhost:9999",
            "server_role": role,
            "binding": "unit",
            "ports": [9999],
            "slots": 1,
            "tier": "hot",
            "binary": "llama.cpp",
            "binary_dir": None,
            "numa_policy": "unit",
            "shared_mmap": False,
        },
        "priors": {
            "throughput_tps": 1.0,
            "quality_overall": 0.5,
            "memory_cost": 1.0,
        },
        "acceleration": {},
        "model": {"mem_gb": 1.0, "modalities": ["text"]},
        "evidence": {},
        "known_gaps": [],
    }


def _write_stack_priors(path: Path, roles: dict[str, dict]) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "stack_priors_version": 1,
                "contract": {"schema": "epyc.stack_priors", "version": 1},
                "compiled_at": "2026-06-13T00:00:00Z",
                "status": "compiled",
                "coverage_scope": "unit",
                "precedence_spec": "unit",
                "source_artifacts": {},
                "roles": roles,
                "known_global_gaps": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _label_map(actions: list[str]) -> np.ndarray:
    return np.array(list(enumerate(actions)), dtype=object)


def test_live_actions_derive_from_stack_priors_and_normalize_legacy_labels(
    tmp_path: Path,
) -> None:
    retired_architect = "architect" + "_coding"
    legacy_worker = "worker" + "_explore"
    priors = _write_stack_priors(
        tmp_path / "stack_priors.yaml",
        {
            "worker_general": _stack_prior_record("worker_general"),
            "candidate": _stack_prior_record(
                "candidate",
                deployment_status="benchmark_or_candidate",
            ),
            "frontdoor": _stack_prior_record("frontdoor"),
            "coder_escalation": _stack_prior_record("coder_escalation"),
        },
    )

    actions = load_live_canonical_actions(priors)

    assert actions == ["frontdoor", "coder_escalation", "worker_general"]
    assert "candidate" not in actions
    assert retired_architect not in actions
    assert normalize_action(retired_architect) == "architect_general"
    assert normalize_action(legacy_worker) == "worker_general"
    assert normalize_action("frontdoor:direct") is None
    assert normalize_action("frontdoor:direct", include_seeded_frontdoor=True) == "frontdoor"


def test_normalize_action_canonicalizes_role_aliases_before_lookup() -> None:
    assert normalize_action("worker_explore") == "worker_general"
    assert normalize_action("worker_fast") == "worker_general"
    assert normalize_action("coder") == "coder_escalation"
    assert normalize_action(LEGACY_ARCHITECT_ROLE) == "architect_general"
    assert normalize_action(f"escalate:coder_escalation->{LEGACY_ARCHITECT_ROLE}") == (
        "architect_general"
    )


def test_degraded_actions_pin_serialized_classifier_order() -> None:
    assert DEGRADED_CANONICAL_ACTIONS == EXPECTED_ACTION_ORDER
    assert canonical_actions_from_label_map(_label_map(DEGRADED_CANONICAL_ACTIONS)) == (
        EXPECTED_ACTION_ORDER
    )


def test_saved_label_map_canonicalizes_without_renumbering() -> None:
    retired_architect = "architect" + "_coding"
    actions = canonical_actions_from_label_map(
        _label_map(["frontdoor", "worker_explore", retired_architect])
    )

    assert actions == ["frontdoor", "worker_general", "architect_general"]
    assert action_index_for_raw_label("worker_fast", actions) == 1
    assert action_index_for_raw_label(retired_architect, actions) == 2


def test_live_actions_keep_preferred_order_and_append_new_live_roles(tmp_path: Path) -> None:
    priors = _write_stack_priors(
        tmp_path / "stack_priors.yaml",
        {
            "unit_new_role": _stack_prior_record("unit_new_role"),
            "vision_escalation": _stack_prior_record("vision_escalation"),
            "worker_general": _stack_prior_record("worker_general"),
            "candidate": _stack_prior_record(
                "candidate",
                deployment_status="benchmark_or_candidate",
            ),
            "frontdoor": _stack_prior_record("frontdoor"),
            "architect_general": _stack_prior_record("architect_general"),
        },
    )

    assert load_live_canonical_actions(priors) == [
        "frontdoor",
        "architect_general",
        "worker_general",
        "vision_escalation",
        "unit_new_role",
    ]


def test_live_actions_fall_back_when_stack_prior_roles_are_malformed(tmp_path: Path) -> None:
    priors = tmp_path / "stack_priors.yaml"
    priors.write_text(
        yaml.safe_dump(
            {
                "stack_priors_version": 1,
                "contract": {"schema": "epyc.stack_priors", "version": 1},
                "status": "compiled",
                "roles": ["frontdoor", "worker_general"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert load_live_canonical_actions(priors) == DEGRADED_CANONICAL_ACTIONS


def test_extract_training_data_remaps_preembedded_legacy_actions(
    tmp_path: Path,
) -> None:
    retired_architect = "architect" + "_coding"
    legacy_worker = "worker" + "_explore"
    actions = ["frontdoor", "architect_general", "coder_escalation", "worker_general"]
    priors = _write_stack_priors(
        tmp_path / "stack_priors.yaml",
        {role: _stack_prior_record(role) for role in actions},
    )
    embeddings_path = tmp_path / "reembedded.npz"
    output_path = tmp_path / "training_data.npz"
    contexts = np.array(
        [json.dumps({"task_type": "code", "context_length": 10}) for _ in range(4)],
        dtype=object,
    )
    np.savez_compressed(
        embeddings_path,
        embeddings=np.ones((4, 1024), dtype=np.float32),
        actions=np.array([retired_architect, legacy_worker, "coder", "unknown"], dtype=object),
        q_values=np.array([0.9, 0.8, 0.7, 0.6], dtype=np.float32),
        contexts=contexts,
    )

    result = extract_training_data(
        db_path=tmp_path,
        output_path=output_path,
        embeddings_file=embeddings_path,
        stack_priors_path=priors,
    )
    out = np.load(output_path, allow_pickle=True)
    label_map = {int(row[0]): str(row[1]) for row in out["label_map"]}
    y = out["y"].astype(np.int64)
    stats = out["extraction_stats"].item()

    assert result["samples"] == 3
    assert result["actions_total"] == len(actions)
    assert list(label_map.values()) == actions
    assert stats["excluded"] == 1
    assert set(y.tolist()) == {
        actions.index("architect_general"),
        actions.index("worker_general"),
        actions.index("coder_escalation"),
    }


def test_verifier_extraction_infers_action_width_from_classifier_artifact(
    tmp_path: Path,
) -> None:
    classifier_path = tmp_path / "classifier.npz"
    output_path = tmp_path / "verifier.npz"
    actions = ["frontdoor", "architect_general", "worker_general"]
    np.savez_compressed(
        classifier_path,
        X=np.ones((2, 3), dtype=np.float32),
        y=np.array([0, 2], dtype=np.int64),
        q_weights=np.array([0.8, 0.2], dtype=np.float32),
        label_map=_label_map(actions),
        canonical_actions=np.array(actions, dtype=object),
    )

    result = extract_verifier_data(classifier_path, output_path)
    out = np.load(output_path, allow_pickle=True)

    assert result["n_actions"] == 3
    assert out["Z"].shape == (2, 6)
    assert int(out["n_actions"]) == 3
    assert [str(row[1]) for row in out["label_map"]] == actions


def test_verifier_extraction_rejects_undersized_action_width(tmp_path: Path) -> None:
    classifier_path = tmp_path / "classifier.npz"
    actions = ["frontdoor", "architect_general", "worker_general"]
    np.savez_compressed(
        classifier_path,
        X=np.ones((2, 3), dtype=np.float32),
        y=np.array([0, 2], dtype=np.int64),
        q_weights=np.array([0.8, 0.2], dtype=np.float32),
        label_map=_label_map(actions),
    )

    with pytest.raises(SystemExit, match="cannot encode max action label"):
        extract_verifier_data(classifier_path, tmp_path / "verifier.npz", n_actions=2)


def test_debiased_verifier_recomputes_actions_against_classifier_label_map(
    tmp_path: Path,
) -> None:
    retired_architect = "architect" + "_coding"
    legacy_worker = "worker" + "_explore"
    actions = ["frontdoor", "architect_general", "worker_general", "coder_escalation"]
    reembedded_path = tmp_path / "reembedded.npz"
    classifier_path = tmp_path / "classifier.npz"
    backup_db = tmp_path / "episodic.db"
    output_path = tmp_path / "verifier_debiased.npz"
    ids = np.array(["a", "b", "c"], dtype=object)
    np.savez_compressed(
        reembedded_path,
        ids=ids,
        embeddings=np.ones((3, 1, 1024), dtype=np.float32),
    )
    np.savez_compressed(
        classifier_path,
        X=np.ones((3, 4), dtype=np.float32),
        y=np.array([0, 1, 2], dtype=np.int64),
        q_weights=np.array([0.9, 0.1, 0.8], dtype=np.float32),
        label_map=_label_map(actions),
        canonical_actions=np.array(actions, dtype=object),
    )
    conn = sqlite3.connect(backup_db)
    conn.execute(
        "CREATE TABLE memories (id TEXT, outcome TEXT, action TEXT, action_type TEXT)"
    )
    conn.executemany(
        "INSERT INTO memories VALUES (?, ?, ?, ?)",
        [
            ("a", "success", retired_architect, "routing"),
            ("b", "failure", legacy_worker, "routing"),
            ("c", "success", "frontdoor:direct", "routing"),
        ],
    )
    conn.commit()
    conn.close()

    result = extract_debiased_verifier_data(
        reembedded_path=reembedded_path,
        backup_db_path=backup_db,
        classifier_data_path=classifier_path,
        out_path=output_path,
    )
    out = np.load(output_path, allow_pickle=True)

    assert result["N"] == 3
    assert int(out["n_actions"]) == len(actions)
    assert out["Z"].shape == (3, 4 + len(actions))
    assert out["actions"].astype(np.int64).tolist() == [
        actions.index("architect_general"),
        actions.index("worker_general"),
        actions.index("frontdoor"),
    ]
    assert [str(row[1]) for row in out["label_map"]] == actions
