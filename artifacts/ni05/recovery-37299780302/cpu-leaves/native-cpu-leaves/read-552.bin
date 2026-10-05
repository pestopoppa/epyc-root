"""Tests for offline reward verifier NPZ extraction."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.graph_router import build_offline_reward_verifier_npz as mod


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _source(path: Path) -> Path:
    return _write_json(
        path,
        [
            {
                "suite": "math",
                "question_id": "q1",
                "prompt": "What is 2+2?",
                "expected": "4",
                "role_results": {
                    "frontdoor": {"answer": "4", "passed": True},
                    "coder_primary": {"answer": "four", "passed": True},
                },
            },
        ],
    )


def _manifest_row(
    source_path: Path,
    *,
    role_key: str,
    label: int,
    score: float,
) -> dict:
    return {
        "schema_version": "offline_reward_feature_input.v1",
        "item_id": f"source:1:{role_key}",
        "join_key": f"{source_path}:0:{role_key}:source:1:{role_key}",
        "question_id": "q1",
        "suite": "math",
        "role_key": role_key,
        "source_path": str(source_path),
        "source_record_index": 1,
        "source_record_offset": 0,
        "source_record_index_base": "one_based",
        "source_record_count": 1,
        "source_role": role_key,
        "source_passed": True,
        "source_elapsed_seconds": 1.0,
        "source_error_present": False,
        "prompt_sha256": "p",
        "expected_sha256": "e",
        "answer_sha256": "a",
        "prompt_chars": len("What is 2+2?"),
        "expected_chars": 1,
        "answer_chars": 1,
        "feature_context": {
            "task_type": "general",
            "task_type_onehot": [0.0, 0.0, 0.0, 0.0, 1.0],
            "source_family": "other",
            "source_family_onehot": [0.0, 0.0, 0.0, 1.0],
            "context_length_chars": len("What is 2+2?"),
            "has_images": False,
            "expected_classifier_feature_dim_without_embedding": 11,
        },
        "oracle_binary_label": label,
        "oracle_score": score,
        "oracle_threshold": 0.86,
        "oracle_score_source": "reference_token_coverage",
        "target_binary_label": label,
        "target_source": "answer_equivalence_final_label",
        "label_source": "reference_token_coverage@0.86",
        "label_status": "oracle_labeled",
    }


def test_build_verifier_npz_emits_compatible_contract_and_aliases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_architect_coding = "architect_coding:delegated"  # stack-change-guard: allow retired-role remap fixture
    monkeypatch.setattr(
        mod,
        "load_live_canonical_actions",
        lambda: ["frontdoor", "architect_general", "coder_escalation"],
    )
    source_path = _source(tmp_path / "source.json")
    manifest_path = _write_jsonl(
        tmp_path / "manifest.jsonl",
        [
            _manifest_row(source_path, role_key="frontdoor:direct", label=1, score=1.0),
            _manifest_row(source_path, role_key="coder_primary", label=0, score=0.0),
            _manifest_row(
                source_path,
                role_key="architect_general:delegated",
                label=1,
                score=0.9,
            ),
            _manifest_row(
                source_path,
                role_key=legacy_architect_coding,
                label=0,
                score=0.2,
            ),
        ],
    )
    out_npz = tmp_path / "verifier.npz"
    summary_json = tmp_path / "summary.json"
    calls: list[str] = []

    def fake_embed(text: str) -> np.ndarray:
        calls.append(text)
        return np.ones(1024, dtype=np.float32)

    summary = mod.build_verifier_npz(
        manifest_path,
        out_npz,
        summary_json=summary_json,
        embed_fn=fake_embed,
    )
    data = np.load(out_npz, allow_pickle=True)

    assert summary["rows"] == 4
    assert summary["unique_source_records_embedded"] == 1
    assert summary["feature_contract"]["name"] == "prompt_only"
    assert summary["feature_contract"]["engineered_feature_dim"] == 7
    assert summary["feature_contract"]["classifier_feature_dim"] == 1031
    assert summary["conflict_policy"]["name"] == "keep"
    assert summary["conflict_policy"]["dropped_conflicting_rows"] == 0
    diagnostics = summary["model_input_group_diagnostics"]
    assert diagnostics["unique_model_input_groups"] == 3
    assert diagnostics["duplicate_model_input_groups"] == 1
    assert diagnostics["duplicate_model_input_rows"] == 2
    assert diagnostics["conflicting_model_input_groups"] == 1
    assert diagnostics["conflicting_model_input_rows"] == 2
    assert calls == ["What is 2+2?"]
    assert data["Z"].shape == (4, 1031 + 3)
    assert data["Z"].dtype == np.float32
    assert data["correct"].astype(np.float32).tolist() == [1.0, 0.0, 1.0, 0.0]
    assert data["actions"].astype(np.int64).tolist() == [0, 2, 1, 1]
    np.testing.assert_allclose(data["q_weights"].astype(np.float32), [1.0, 0.01, 0.9, 0.2])
    assert int(data["feature_dim"]) == 1031
    assert int(data["classifier_feature_dim"]) == 1031
    assert int(data["n_actions"]) == 3
    assert [str(row[1]) for row in data["label_map"]] == [
        "frontdoor",
        "architect_general",
        "coder_escalation",
    ]
    metadata = data["metadata"].tolist()
    assert "prompt" not in metadata[0]
    assert "answer" not in metadata[0]
    assert metadata[0]["source_record_index_base"] == "one_based"
    assert metadata[0]["oracle_threshold"] == 0.86
    assert metadata[2]["canonical_action"] == "architect_general"
    assert metadata[3]["canonical_action"] == "architect_general"
    summary_payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert summary_payload["n_neg"] == 2
    assert summary_payload["canonical_action_counts"]["architect_general"] == 2


def test_build_verifier_npz_can_drop_conflicting_model_input_groups(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_architect_coding = "architect_coding:delegated"  # stack-change-guard: allow retired-role remap fixture
    monkeypatch.setattr(
        mod,
        "load_live_canonical_actions",
        lambda: ["frontdoor", "architect_general", "coder_escalation"],
    )
    source_path = _source(tmp_path / "source.json")
    manifest_path = _write_jsonl(
        tmp_path / "manifest.jsonl",
        [
            _manifest_row(source_path, role_key="frontdoor:direct", label=1, score=1.0),
            _manifest_row(source_path, role_key="coder_primary", label=0, score=0.0),
            _manifest_row(
                source_path,
                role_key="architect_general:delegated",
                label=1,
                score=0.9,
            ),
            _manifest_row(
                source_path,
                role_key=legacy_architect_coding,
                label=0,
                score=0.2,
            ),
        ],
    )
    out_npz = tmp_path / "verifier.npz"

    summary = mod.build_verifier_npz(
        manifest_path,
        out_npz,
        embed_fn=lambda _text: np.ones(1024, dtype=np.float32),
        conflict_policy="drop_conflicting_model_inputs",
    )
    data = np.load(out_npz, allow_pickle=True)

    assert summary["rows"] == 2
    assert summary["conflict_policy"]["name"] == "drop_conflicting_model_inputs"
    assert summary["conflict_policy"]["rows_before_filter"] == 4
    assert summary["conflict_policy"]["rows_after_filter"] == 2
    assert summary["conflict_policy"]["dropped_conflicting_rows"] == 2
    pre_filter = summary["conflict_policy"]["pre_filter_model_input_group_diagnostics"]
    assert pre_filter["conflicting_model_input_groups"] == 1
    assert summary["model_input_group_diagnostics"]["conflicting_model_input_groups"] == 0
    assert data["correct"].astype(np.float32).tolist() == [1.0, 0.0]
    assert data["actions"].astype(np.int64).tolist() == [0, 2]
    assert summary["canonical_action_counts"] == {
        "coder_escalation": 1,
        "frontdoor": 1,
    }
    assert summary["pre_filter_canonical_action_counts"]["architect_general"] == 2


def test_build_verifier_npz_response_telemetry_contract_adds_prompt_free_features(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mod,
        "load_live_canonical_actions",
        lambda: ["frontdoor", "architect_general", "coder_escalation"],
    )
    source_path = _source(tmp_path / "source.json")
    manifest_path = _write_jsonl(
        tmp_path / "manifest.jsonl",
        [
            _manifest_row(source_path, role_key="frontdoor", label=1, score=1.0),
            {
                **_manifest_row(source_path, role_key="frontdoor", label=0, score=0.0),
                "answer_chars": 42,
                "source_elapsed_seconds": 9.5,
            },
        ],
    )
    out_npz = tmp_path / "verifier.npz"

    summary = mod.build_verifier_npz(
        manifest_path,
        out_npz,
        embed_fn=lambda _text: np.ones(1024, dtype=np.float32),
        feature_contract="response_telemetry",
    )
    data = np.load(out_npz, allow_pickle=True)

    assert summary["feature_contract"]["name"] == "response_telemetry"
    assert summary["feature_contract"]["engineered_feature_dim"] == 11
    assert int(data["feature_dim"]) == 1035
    assert int(data["classifier_feature_dim"]) == 1031
    assert data["Z"].shape == (2, 1035 + 3)
    diagnostics = summary["model_input_group_diagnostics"]
    assert diagnostics["duplicate_model_input_groups"] == 0
    assert diagnostics["conflicting_model_input_groups"] == 0


def test_build_verifier_npz_source_family_response_telemetry_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mod,
        "load_live_canonical_actions",
        lambda: ["frontdoor", "architect_general", "coder_escalation"],
    )
    source_path = _source(tmp_path / "source.json")
    manifest_path = _write_jsonl(
        tmp_path / "manifest.jsonl",
        [
            {
                **_manifest_row(source_path, role_key="frontdoor", label=1, score=1.0),
                "feature_context": {
                    **_manifest_row(
                        source_path,
                        role_key="frontdoor",
                        label=1,
                        score=1.0,
                    )["feature_context"],
                    "source_family": "seeding_eval",
                    "source_family_onehot": [0.0, 1.0, 0.0, 0.0],
                },
            },
            {
                **_manifest_row(source_path, role_key="coder_primary", label=0, score=0.0),
                "feature_context": {
                    **_manifest_row(
                        source_path,
                        role_key="coder_primary",
                        label=0,
                        score=0.0,
                    )["feature_context"],
                    "source_family": "three_way_eval",
                    "source_family_onehot": [0.0, 0.0, 1.0, 0.0],
                },
            },
        ],
    )
    out_npz = tmp_path / "verifier.npz"

    summary = mod.build_verifier_npz(
        manifest_path,
        out_npz,
        embed_fn=lambda _text: np.ones(1024, dtype=np.float32),
        feature_contract="source_family_response_telemetry",
    )
    data = np.load(out_npz, allow_pickle=True)

    assert summary["feature_contract"]["name"] == "source_family_response_telemetry"
    assert summary["feature_contract"]["engineered_feature_dim"] == 15
    assert "source_family_onehot[4]" in summary["feature_contract"]["engineered_features"]
    assert int(data["feature_dim"]) == 1039
    assert int(data["classifier_feature_dim"]) == 1031
    assert data["Z"].shape == (2, 1039 + 3)


def test_build_verifier_npz_source_action_response_telemetry_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mod,
        "load_live_canonical_actions",
        lambda: ["frontdoor", "architect_general", "coder_escalation"],
    )
    source_path = _source(tmp_path / "source.json")
    frontdoor_row = _manifest_row(source_path, role_key="frontdoor", label=1, score=1.0)
    coder_row = _manifest_row(source_path, role_key="coder_primary", label=0, score=0.0)
    manifest_path = _write_jsonl(
        tmp_path / "manifest.jsonl",
        [
            {
                **frontdoor_row,
                "feature_context": {
                    **frontdoor_row["feature_context"],
                    "source_family": "seeding_eval",
                    "source_family_onehot": [0.0, 1.0, 0.0, 0.0],
                },
            },
            {
                **coder_row,
                "feature_context": {
                    **coder_row["feature_context"],
                    "source_family": "three_way_eval",
                    "source_family_onehot": [0.0, 0.0, 1.0, 0.0],
                },
            },
        ],
    )
    out_npz = tmp_path / "verifier.npz"

    summary = mod.build_verifier_npz(
        manifest_path,
        out_npz,
        embed_fn=lambda _text: np.ones(1024, dtype=np.float32),
        feature_contract="source_action_response_telemetry",
    )
    data = np.load(out_npz, allow_pickle=True)

    assert summary["feature_contract"]["name"] == "source_action_response_telemetry"
    assert summary["feature_contract"]["engineered_feature_dim"] == 27
    assert "source_family_onehot[4]" in summary["feature_contract"]["engineered_features"]
    assert "source_family_x_action_onehot[12]" in summary["feature_contract"]["engineered_features"]
    assert int(data["feature_dim"]) == 1051
    assert int(data["classifier_feature_dim"]) == 1031
    assert data["Z"].shape == (2, 1051 + 3)
    # Engineered layout after 1024-d embedding:
    # task[5], source_family[4], context_length, has_images, interaction[12], telemetry[4].
    engineered = data["Z"][:, 1024:1051]
    frontdoor_interaction = engineered[0, 11:23]
    coder_interaction = engineered[1, 11:23]
    np.testing.assert_allclose(frontdoor_interaction.reshape(4, 3)[1], [1.0, 0.0, 0.0])
    np.testing.assert_allclose(coder_interaction.reshape(4, 3)[2], [0.0, 0.0, 1.0])


def test_build_verifier_npz_rejects_unmapped_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mod, "load_live_canonical_actions", lambda: ["frontdoor"])
    source_path = _source(tmp_path / "source.json")
    manifest_path = _write_jsonl(
        tmp_path / "manifest.jsonl",
        [_manifest_row(source_path, role_key="unknown_role", label=1, score=1.0)],
    )

    with pytest.raises(mod.OfflineRewardVerifierNpzError, match="cannot map role_key"):
        mod.build_verifier_npz(
            manifest_path,
            tmp_path / "verifier.npz",
            embed_fn=lambda _text: np.ones(1024, dtype=np.float32),
        )
