"""Tests for the extracted autopilot.state_store module."""

from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

state_store = importlib.import_module("state_store")


# ----- load_state / save_state -----


def test_load_state_returns_default_when_file_missing(tmp_path) -> None:
    out = state_store.load_state(tmp_path / "no_such.json", lambda: {"trial_counter": 0})
    assert out == {"trial_counter": 0}


def test_load_state_reads_existing_json(tmp_path) -> None:
    f = tmp_path / "state.json"
    f.write_text(json.dumps({"trial_counter": 42, "paused": True}))
    out = state_store.load_state(f, lambda: {"trial_counter": 0})
    assert out == {"trial_counter": 42, "paused": True}


def test_save_state_writes_json_and_creates_parent(tmp_path) -> None:
    f = tmp_path / "nested" / "dir" / "state.json"
    state_store.save_state(f, {"trial_counter": 5})
    assert f.exists()
    assert json.loads(f.read_text()) == {"trial_counter": 5}


# ----- blacklist -----


def test_load_blacklist_returns_empty_when_missing(tmp_path) -> None:
    assert state_store.load_blacklist(tmp_path / "no_such.yaml") == []


def test_load_blacklist_parses_yaml(tmp_path) -> None:
    f = tmp_path / "bl.yaml"
    f.write_text(yaml.dump({"blacklist": [
        {"pattern": {"type": "prompt_mutation"}, "reason": "regression"},
    ]}))
    out = state_store.load_blacklist(f)
    assert len(out) == 1
    assert out[0]["reason"] == "regression"


def test_load_blacklist_filters_observational_deep_eval_entries(tmp_path) -> None:
    f = tmp_path / "bl.yaml"
    f.write_text(yaml.dump({"blacklist": [
        {"pattern": {"type": "deep_eval", "tier": 3}, "reason": "hard tier failed"},
        {"pattern": {"type": "seed_batch", "n_questions": 24}, "reason": "bad n"},
    ]}))
    out = state_store.load_blacklist(f)
    assert [entry["pattern"] for entry in out] == [
        {"type": "seed_batch", "n_questions": 24},
    ]


def test_load_blacklist_filters_unscoped_numeric_surface_entries(tmp_path) -> None:
    f = tmp_path / "bl.yaml"
    f.write_text(yaml.dump({"blacklist": [
        {
            "pattern": {"type": "numeric_trial", "surface": "memrl_retrieval"},
            "reason": "legacy broad ban",
        },
        {
            "pattern": {
                "type": "numeric_trial",
                "surface": "chat_pipeline",
                "params": {},
            },
            "reason": "empty sampler ban",
        },
        {
            "pattern": {
                "type": "numeric_trial",
                "surface": "repl_executor",
                "params": {"repl.turn_token_cap": 768},
            },
            "reason": "exact params failed",
        },
        {
            "pattern": {"type": "numeric_trial", "surface": "monitor"},
            "reason": "operator surface ban",
            "scope": "surface",
        },
    ]}))
    out = state_store.load_blacklist(f)
    assert [entry["reason"] for entry in out] == [
        "exact params failed",
        "operator surface ban",
    ]


def test_load_blacklist_filters_expired_auto_entries(tmp_path) -> None:
    f = tmp_path / "bl.yaml"
    old_added = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    f.write_text(yaml.dump({"blacklist": [
        {
            "pattern": {"type": "structural_experiment", "flags": {"x": True}},
            "reason": "Auto-blacklisted: 2× critic-rejected — stale",
            "added": old_added,
            "source_trial": 10,
        },
        {
            "pattern": {"type": "structural_experiment", "flags": {"y": True}},
            "reason": "Auto-blacklisted: 2× critic-rejected — explicit stale",
            "added": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            "source_trial": 11,
        },
        {
            "pattern": {"type": "prompt_mutation", "file": "frontdoor.md"},
            "reason": "MANUAL FREEZE: corruption recovery",
            "severity": "corruption",
            "added": old_added,
            "source_trial": -1,
        },
    ]}))

    out = state_store.load_blacklist(f)
    assert [entry["pattern"] for entry in out] == [
        {"type": "prompt_mutation", "file": "frontdoor.md"},
    ]


def test_load_blacklist_handles_malformed_yaml(tmp_path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text("not: valid: yaml: {{{")
    assert state_store.load_blacklist(f) == []


def test_check_blacklist_matches_full_pattern() -> None:
    bl = [{"pattern": {"type": "x", "file": "a.md"}, "reason": "no"}]
    assert state_store.check_blacklist(
        {"type": "x", "file": "a.md", "extra": 1}, bl
    ) == "no"


def test_check_blacklist_prefers_latest_duplicate_pattern() -> None:
    bl = [
        {"pattern": {"type": "x"}, "reason": "first"},
        {"pattern": {"type": "x"}, "reason": "latest"},
    ]
    assert state_store.check_blacklist({"type": "x"}, bl) == "latest"


def test_check_blacklist_no_match_returns_none() -> None:
    bl = [{"pattern": {"type": "x"}, "reason": "no"}]
    assert state_store.check_blacklist({"type": "y"}, bl) is None


def test_check_blacklist_skips_empty_pattern() -> None:
    bl = [{"pattern": {}, "reason": "no"}]
    assert state_store.check_blacklist({"type": "x"}, bl) is None


def test_check_blacklist_non_dict_action_returns_none() -> None:
    assert state_store.check_blacklist(None, [{"pattern": {"type": "x"}, "reason": "no"}]) is None


def test_check_blacklist_ignores_unscoped_numeric_surface_entry() -> None:
    bl = [
        {
            "pattern": {"type": "numeric_trial", "surface": "memrl_retrieval"},
            "reason": "legacy broad ban",
        }
    ]
    action = {"type": "numeric_trial", "surface": "memrl_retrieval", "params": {}}
    assert state_store.check_blacklist(action, bl) is None


def test_check_blacklist_honors_explicit_numeric_surface_scope() -> None:
    bl = [
        {
            "pattern": {"type": "numeric_trial", "surface": "memrl_retrieval"},
            "reason": "operator surface ban",
            "scope": "surface",
        }
    ]
    action = {"type": "numeric_trial", "surface": "memrl_retrieval", "params": {}}
    assert state_store.check_blacklist(action, bl) == "operator surface ban"


def test_check_blacklist_honors_numeric_param_pattern() -> None:
    bl = [
        {
            "pattern": {
                "type": "numeric_trial",
                "surface": "memrl_retrieval",
                "params": {"memrl_retrieval.semantic_k": 28},
            },
            "reason": "exact params failed",
        }
    ]
    assert state_store.check_blacklist(
        {
            "type": "numeric_trial",
            "surface": "memrl_retrieval",
            "params": {"memrl_retrieval.semantic_k": 28},
        },
        bl,
    ) == "exact params failed"
    assert state_store.check_blacklist(
        {
            "type": "numeric_trial",
            "surface": "memrl_retrieval",
            "params": {"memrl_retrieval.semantic_k": 32},
        },
        bl,
    ) is None


def test_check_blacklist_ignores_expired_auto_entries() -> None:
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    bl = [
        {
            "pattern": {"type": "structural_experiment", "flags": {"x": True}},
            "reason": "Auto-blacklisted: 2× critic-rejected — stale",
            "reason_class": "critic_rejected",
            "expires_at": expired,
        }
    ]
    assert state_store.check_blacklist(
        {"type": "structural_experiment", "flags": {"x": True}},
        bl,
    ) is None


def test_append_blacklist_creates_new_file(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {"type": "prompt_mutation", "file": "x.md"}, trial_id=1, reason="bad",
        blacklist_path=bl_path,
    )
    data = yaml.safe_load(bl_path.read_text())
    assert len(data["blacklist"]) == 1
    assert data["blacklist"][0]["pattern"] == {"type": "prompt_mutation", "file": "x.md"}
    assert data["blacklist"][0]["reason"] == "bad"


def test_append_blacklist_appends_to_existing(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    bl_path.write_text(yaml.dump({"blacklist": [
        {"pattern": {"type": "x"}, "reason": "first"},
    ]}))
    state_store.append_blacklist(
        {"type": "y"}, trial_id=2, reason="second", blacklist_path=bl_path,
    )
    data = yaml.safe_load(bl_path.read_text())
    assert len(data["blacklist"]) == 2
    assert data["blacklist"][1]["reason"] == "second"


def test_append_blacklist_updates_duplicate_pattern(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    bl_path.write_text(yaml.dump({"blacklist": [
        {"pattern": {"type": "x"}, "reason": "first", "source_trial": 1},
        {"pattern": {"type": "y"}, "reason": "second", "source_trial": 2},
        {"pattern": {"type": "x"}, "reason": "older duplicate", "source_trial": 3},
    ]}))
    state_store.append_blacklist(
        {"type": "x"}, trial_id=4, reason="latest", blacklist_path=bl_path,
    )
    data = yaml.safe_load(bl_path.read_text())
    assert len(data["blacklist"]) == 2
    assert [entry["pattern"] for entry in data["blacklist"]] == [
        {"type": "y"},
        {"type": "x"},
    ]
    assert data["blacklist"][1]["reason"] == "latest"
    assert data["blacklist"][1]["source_trial"] == 4


def test_append_blacklist_skips_type_only_low_risk_action(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {"type": "deep_eval"}, trial_id=2, reason="second", blacklist_path=bl_path,
    )
    assert not bl_path.exists()


def test_append_blacklist_keeps_specific_seed_pattern(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {"type": "seed_batch", "n_questions": 24}, trial_id=2, reason="second",
        blacklist_path=bl_path,
    )
    data = yaml.safe_load(bl_path.read_text())
    assert data["blacklist"][0]["pattern"] == {
        "type": "seed_batch",
        "n_questions": 24,
    }


def test_append_blacklist_skips_broad_numeric_surface_pattern(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {"type": "numeric_trial", "surface": "memrl_retrieval"},
        trial_id=1100,
        reason="critic loop",
        blacklist_path=bl_path,
    )
    assert not bl_path.exists()


def test_append_blacklist_keeps_numeric_params_pattern(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {
            "type": "numeric_trial",
            "surface": "memrl_retrieval",
            "params": {"memrl_retrieval.semantic_k": 28},
        },
        trial_id=1060,
        reason="safety revert",
        blacklist_path=bl_path,
    )
    data = yaml.safe_load(bl_path.read_text())
    assert data["blacklist"][0]["pattern"] == {
        "type": "numeric_trial",
        "surface": "memrl_retrieval",
        "params": {"memrl_retrieval.semantic_k": 28},
    }


def test_append_blacklist_tags_auto_expiry_metadata(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {"type": "structural_experiment", "flags": {"graph_router": True}},
        trial_id=1064,
        reason="Auto-blacklisted: 2× critic-rejected — stale draft",
        blacklist_path=bl_path,
        reason_class="critic_rejected",
    )
    entry = yaml.safe_load(bl_path.read_text())["blacklist"][0]
    assert entry["reason_class"] == "critic_rejected"
    assert entry["ttl_days"] == 14
    added = datetime.fromisoformat(entry["added"])
    expires_at = datetime.fromisoformat(entry["expires_at"])
    assert timedelta(days=13, hours=23) < expires_at - added < timedelta(days=14, minutes=1)


def test_append_blacklist_skips_observational_deep_eval_tier(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {"type": "deep_eval", "tier": 2}, trial_id=2, reason="second",
        blacklist_path=bl_path,
    )
    assert not bl_path.exists()


def test_append_blacklist_keeps_specific_distill_knowledge_window(tmp_path) -> None:
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {"type": "distill_knowledge", "last_n": 30},
        trial_id=1111,
        reason="critic loop",
        blacklist_path=bl_path,
    )
    data = yaml.safe_load(bl_path.read_text())
    assert data["blacklist"][0]["pattern"] == {
        "type": "distill_knowledge",
        "last_n": 30,
    }


def test_append_blacklist_skips_unpatternable_actions(tmp_path) -> None:
    """If no patternable fields are in the action, no entry is written."""
    bl_path = tmp_path / "bl.yaml"
    state_store.append_blacklist(
        {"unrelated": "key"}, trial_id=1, reason="bad", blacklist_path=bl_path,
    )
    assert not bl_path.exists()


# ----- model signatures -----


def test_load_model_signatures_raises_when_no_descriptor_path_given(tmp_path) -> None:
    """No descriptor path is an honest refusal, not an empty dict (2026-08-01)."""
    with pytest.raises(state_store.ModelSignaturesUnavailableError) as excinfo:
        state_store.load_model_signatures(tmp_path / "legacy.yaml")
    assert "orchestration/model_descriptors.yaml" in str(excinfo.value)


def test_load_model_signatures_raises_when_descriptors_missing_on_disk(tmp_path) -> None:
    with pytest.raises(state_store.ModelSignaturesUnavailableError) as excinfo:
        state_store.load_model_signatures(
            tmp_path / "legacy.yaml", descriptors_path=tmp_path / "no-descriptors.yaml"
        )
    assert "orchestration/model_descriptors.yaml" in str(excinfo.value)
    assert "no-descriptors.yaml" in str(excinfo.value)


def test_load_model_signatures_raises_when_descriptors_unparseable(tmp_path) -> None:
    descriptors = tmp_path / "model_descriptors.yaml"
    descriptors.write_text("models: [\n  - unterminated\n")
    with pytest.raises(state_store.ModelSignaturesUnavailableError) as excinfo:
        state_store.load_model_signatures(None, descriptors_path=descriptors)
    assert "orchestration/model_descriptors.yaml" in str(excinfo.value)


def test_load_model_signatures_raises_when_descriptors_empty(tmp_path) -> None:
    descriptors = tmp_path / "model_descriptors.yaml"
    descriptors.write_text(yaml.dump({"descriptor_version": 3, "models": []}))
    with pytest.raises(state_store.ModelSignaturesUnavailableError) as excinfo:
        state_store.load_model_signatures(None, descriptors_path=descriptors)
    assert "carries no model descriptors" in str(excinfo.value)


def test_load_model_signatures_never_falls_back_to_a_legacy_signature_file(tmp_path) -> None:
    """A readable legacy YAML must NOT rescue an unreadable descriptor artifact."""
    legacy = tmp_path / "model_quality_signatures.yaml"
    legacy.write_text(yaml.dump({"models": {
        "retired-fleet-model": {"role": "frontdoor", "max_throughput_tps": 12.7},
    }}))
    with pytest.raises(state_store.ModelSignaturesUnavailableError):
        state_store.load_model_signatures(
            legacy, descriptors_path=tmp_path / "no-descriptors.yaml"
        )


def test_load_model_signatures_prefers_model_descriptors(tmp_path) -> None:
    legacy = tmp_path / "sigs.yaml"
    legacy.write_text(yaml.dump({"models": {
        "legacy": {"role": "old", "max_throughput_tps": 1.0},
    }}))
    descriptors = tmp_path / "model_descriptors.yaml"
    descriptors.write_text(yaml.dump({
        "descriptor_version": 3,
        "compiled_at": "2026-06-12T20:24:22Z",
        "models": [
            {
                "model_id": "qwen3.6-35b-a3b-q8_0",
                "display_name": "Qwen3.6 35B",
                "role_bindings": {"roles": ["frontdoor", "coder_escalation"]},
                "quality": {"suite_vector": {"coder": 0.97, "math": 0.84}},
                "speed": {"solo_96t_tps": 24.3, "quarter_48t_tps": 60.7},
                "known_gaps": ["ctx_max is missing"],
            },
        ],
    }))

    out = state_store.load_model_signatures(legacy, descriptors_path=descriptors)

    assert "legacy" not in out
    assert out["__metadata__"]["compiled_at"] == "2026-06-12T20:24:22Z"
    sig = out["Qwen3.6 35B"]
    assert sig["model_id"] == "qwen3.6-35b-a3b-q8_0"
    assert sig["role"] == "frontdoor, coder_escalation"
    assert sig["max_throughput_tps"] == 60.7
    assert sig["per_suite"]["coder"] == "97%"
    assert sig["known_gaps"] == ["ctx_max is missing"]


def test_format_model_signatures_empty_dict_message() -> None:
    out = state_store.format_model_signatures({})
    assert "no model signatures available" in out


def test_format_model_signatures_table_format() -> None:
    sigs = {
        "gemma-4-26B": {
            "role": "worker",
            "max_throughput_tps": 76.5,
            "per_suite": {"coder": "96%", "math": "84%", "general": "78%"},
        },
    }
    out = state_store.format_model_signatures(sigs)
    assert "| Model | Role |" in out
    assert "gemma-4-26B" in out
    assert "worker" in out
    # Top suite should be coder (96%), bottom should be general (78%)
    assert "coder (96%)" in out
    assert "general (78%)" in out


def test_format_model_signatures_includes_descriptor_metadata_and_gaps() -> None:
    sigs = {
        "__metadata__": {
            "source": "orchestration/model_descriptors.yaml",
            "compiled_at": "2026-06-12T20:24:22Z",
            "descriptor_version": 3,
        },
        "Qwen3.6 35B": {
            "model_id": "qwen3.6-35b-a3b-q8_0",
            "role": "frontdoor",
            "max_throughput_tps": 24.3,
            "per_suite": {"coder": "97%"},
            "known_gaps": ["ctx_max is missing"],
        },
    }
    out = state_store.format_model_signatures(sigs)
    assert "compiled_at=2026-06-12T20:24:22Z" in out
    assert "descriptor_version=3" in out
    assert "qwen3.6-35b-a3b-q8_0" in out
    assert "coder (97%)" in out
    assert "ctx_max is missing" in out
