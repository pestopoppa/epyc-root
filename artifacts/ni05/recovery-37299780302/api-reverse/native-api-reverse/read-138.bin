"""Unit tests for src.registry.capability_registry.

Tests:
  - Valid load of the repo's capability_registry.yaml
  - Schema validation: required fields, enum constraints, sub-field checks
  - Duplicate-id rejection
  - Malformed-entry rejection (non-mapping row, bad enum, missing sub-field)

Spec: fable5-findings-04-impl-plan.md §C.1
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.registry.capability_registry import (
    CapabilityRegistryError,
    build_action_availability_section,
    build_index_a_by_table,
    capability_index_rows,
    load_capability_registry,
)
from scripts.registry.compile_capability_registry import (
    _replace_marked_block,
    main as compile_capability_registry_main,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


def _minimal_entry(**overrides: object) -> dict:
    """Build a minimal valid capability entry, with optional field overrides."""
    base: dict = {
        "id": "test_lever",
        "kind": "env",
        "surface": "SOME_ENV_VAR",
        "applicator": "role_restart",
        "range": {"type": "int", "min": 0, "max": 64},
        "roles": ["frontdoor"],
        "evidence": {
            "measured": "some effect observed",
            "protocol": "none",
            "source": "some-handoff.md",
        },
        "risk": "medium",
        "actionable_by": "operator",
        "promotion_state": "placeholder",
        "trial_protocol": {
            "class": "batched_restart",
            "min_trials": 5,
            "restore_after_batch": True,
            "boundary_event": "role_restart_boundary",
            "smoke_check": "canned_completion",
            "require_explicit_affected_roles": True,
        },
    }
    base.update(overrides)
    return base


def _write_registry(tmp_path: Path, capabilities: list) -> Path:
    """Write a capability_registry.yaml with the given capabilities list."""
    path = tmp_path / "capability_registry.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "capability_registry_version": 1,
                "schema_status": "scaffold",
                "capabilities": capabilities,
            }
        ),
        encoding="utf-8",
    )
    return path


# ──────────────────────────────────────────────────────────────────────────────
# Valid load
# ──────────────────────────────────────────────────────────────────────────────


def test_load_repo_capability_registry() -> None:
    """The repo's own capability_registry.yaml loads and validates cleanly."""
    caps = load_capability_registry()
    assert isinstance(caps, list)
    assert len(caps) >= 1, "registry must have at least one capability entry"
    for cap in caps:
        assert isinstance(cap, dict)
        assert "id" in cap
        assert "promotion_state" in cap


def test_repo_registry_contains_first_cohort_members() -> None:
    """First-cohort capability ids declared in the spec are present."""
    caps = load_capability_registry()
    ids = {cap["id"] for cap in caps}
    expected_ids = {
        "moe_spec_budget",
        "per_role_enable_thinking",
        "ea_compaction_profiles",
        "draft_max_p_split",
        "edit_transaction_auto_routing",
    }
    assert expected_ids <= ids, (
        f"missing first-cohort ids: {expected_ids - ids}"
    )


def test_repo_registry_all_rows_are_placeholder() -> None:
    """All rows must be promotion_state=placeholder (no live/promoted rows)."""
    caps = load_capability_registry()
    non_placeholder = [
        cap["id"]
        for cap in caps
        if cap.get("promotion_state") != "placeholder"
    ]
    assert not non_placeholder, (
        f"rows must not be promoted until evidence-plane Phase 1: {non_placeholder}"
    )


def test_edit_transaction_auto_routing_is_operator_only_placeholder() -> None:
    """A2 routing stays operator-owned until clean-window evidence exists."""
    caps = load_capability_registry()
    edit_cap = next(
        cap for cap in caps if cap["id"] == "edit_transaction_auto_routing"
    )
    assert edit_cap["actionable_by"] == "operator"
    assert edit_cap["promotion_state"] == "placeholder"
    assert edit_cap["risk"] == "high"
    assert isinstance(edit_cap["kill_condition"], str)
    assert edit_cap["kill_condition"].strip()


def test_load_minimal_valid_registry(tmp_path: Path) -> None:
    """A minimal single-entry registry loads without error."""
    path = _write_registry(tmp_path, [_minimal_entry()])
    caps = load_capability_registry(path)
    assert len(caps) == 1
    assert caps[0]["id"] == "test_lever"


def test_load_multiple_entries(tmp_path: Path) -> None:
    """Multiple distinct entries load in declaration order."""
    entries = [
        _minimal_entry(id="lever_a"),
        _minimal_entry(id="lever_b"),
        _minimal_entry(
            id="lever_c",
            kind="flag",
            applicator="config_post",
            trial_protocol=None,
        ),
    ]
    path = _write_registry(tmp_path, entries)
    caps = load_capability_registry(path)
    assert [c["id"] for c in caps] == ["lever_a", "lever_b", "lever_c"]


def test_action_availability_section_is_generated_from_rows(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _minimal_entry(id="operator_lever", actionable_by="operator"),
            _minimal_entry(
                id="gated_lever",
                actionable_by="gated:evidence-plane",
                promotion_state="candidate",
            ),
            _minimal_entry(
                id="promoted_lever",
                actionable_by="autopilot",
                promotion_state="promoted",
                kill_condition="rollback if quality regresses",
            ),
        ],
    )
    caps = load_capability_registry(path)

    rendered = build_action_availability_section(caps)

    assert "`promoted_lever`" in rendered
    assert "Autopilot-actionable:" in rendered
    assert "`operator_lever`: operator-only" in rendered
    assert "`gated_lever`: gated on evidence-plane; candidate is not promoted" in rendered


def test_index_a_by_table_uses_same_registry_rows(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _minimal_entry(
                id="edit_transaction_auto_routing",
                actionable_by="operator",
                handoff="multi-file-coding-completion-capability.md",
            )
        ],
    )
    caps = load_capability_registry(path)

    rows = capability_index_rows(caps)
    table = build_index_a_by_table(caps)

    assert rows == [
        {
            "id": "edit_transaction_auto_routing",
            "a_by": "operator",
            "promotion_state": "placeholder",
            "risk": "medium",
            "reason": "operator-only",
            "handoff": "multi-file-coding-completion-capability.md",
        }
    ]
    assert "| `edit_transaction_auto_routing` | operator | placeholder |" in table


def test_replace_marked_block_updates_only_generated_region() -> None:
    text = "\n".join(
        [
            "prefix",
            "<!-- capability-registry:index-a-by:start -->",
            "old",
            "<!-- capability-registry:index-a-by:end -->",
            "suffix",
        ]
    )

    updated = _replace_marked_block(
        text, target="index-a-by", rendered="new\ncontent"
    )

    assert updated == "\n".join(
        [
            "prefix",
            "<!-- capability-registry:index-a-by:start -->",
            "new",
            "content",
            "<!-- capability-registry:index-a-by:end -->",
            "suffix",
        ]
    )


def test_replace_marked_block_requires_exactly_one_marker_pair() -> None:
    with pytest.raises(ValueError, match="expected exactly one"):
        _replace_marked_block("no markers", target="index-a-by", rendered="table")


def test_compile_capability_registry_check_block_fails_on_drift(tmp_path: Path) -> None:
    doc = tmp_path / "index.md"
    doc.write_text(
        "\n".join(
            [
                "<!-- capability-registry:index-a-by:start -->",
                "stale",
                "<!-- capability-registry:index-a-by:end -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    rc = compile_capability_registry_main(
        ["--target", "index-a-by", "--check-block", str(doc)]
    )

    assert rc == 1


def test_compile_capability_registry_replace_then_check_block(tmp_path: Path) -> None:
    doc = tmp_path / "index.md"
    doc.write_text(
        "\n".join(
            [
                "prefix",
                "<!-- capability-registry:index-a-by:start -->",
                "stale",
                "<!-- capability-registry:index-a-by:end -->",
                "suffix",
                "",
            ]
        ),
        encoding="utf-8",
    )

    replace_rc = compile_capability_registry_main(
        ["--target", "index-a-by", "--replace-block", str(doc)]
    )
    check_rc = compile_capability_registry_main(
        ["--target", "index-a-by", "--check-block", str(doc)]
    )

    assert replace_rc == 0
    assert check_rc == 0


# ──────────────────────────────────────────────────────────────────────────────
# Missing file / structural errors
# ──────────────────────────────────────────────────────────────────────────────


def test_missing_file_raises() -> None:
    with pytest.raises(CapabilityRegistryError, match="not found"):
        load_capability_registry("/nonexistent/capability_registry.yaml")


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "capability_registry.yaml"
    path.write_text("capabilities: [- bad: yaml: here\n  broken", encoding="utf-8")
    with pytest.raises(CapabilityRegistryError, match="not valid YAML"):
        load_capability_registry(path)


def test_non_mapping_top_level_raises(tmp_path: Path) -> None:
    path = tmp_path / "capability_registry.yaml"
    path.write_text("- just_a_list_item\n", encoding="utf-8")
    with pytest.raises(CapabilityRegistryError, match="must be a YAML mapping"):
        load_capability_registry(path)


def test_missing_capabilities_key_raises(tmp_path: Path) -> None:
    path = tmp_path / "capability_registry.yaml"
    path.write_text(yaml.safe_dump({"capability_registry_version": 1}), encoding="utf-8")
    with pytest.raises(CapabilityRegistryError, match="missing top-level 'capabilities' key"):
        load_capability_registry(path)


def test_capabilities_not_a_list_raises(tmp_path: Path) -> None:
    path = tmp_path / "capability_registry.yaml"
    path.write_text(
        yaml.safe_dump({"capabilities": {"id": "oops"}}), encoding="utf-8"
    )
    with pytest.raises(CapabilityRegistryError, match="must be a list"):
        load_capability_registry(path)


# ──────────────────────────────────────────────────────────────────────────────
# Duplicate id rejection
# ──────────────────────────────────────────────────────────────────────────────


def test_duplicate_id_raises(tmp_path: Path) -> None:
    """Two entries with the same id must be rejected."""
    entries = [
        _minimal_entry(id="same_id"),
        _minimal_entry(id="other_lever"),
        _minimal_entry(id="same_id"),  # duplicate
    ]
    path = _write_registry(tmp_path, entries)
    with pytest.raises(CapabilityRegistryError, match="duplicate capability id"):
        load_capability_registry(path)


def test_duplicate_id_error_names_both_indices(tmp_path: Path) -> None:
    entries = [_minimal_entry(id="dup"), _minimal_entry(id="dup")]
    path = _write_registry(tmp_path, entries)
    with pytest.raises(CapabilityRegistryError) as exc_info:
        load_capability_registry(path)
    msg = str(exc_info.value)
    assert "dup" in msg
    # Both first and duplicate index should appear
    assert "index 0" in msg
    assert "index 1" in msg


# ──────────────────────────────────────────────────────────────────────────────
# Required field validation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "missing_field",
    [
        "id",
        "kind",
        "surface",
        "applicator",
        "range",
        "roles",
        "evidence",
        "risk",
        "actionable_by",
        "promotion_state",
    ],
)
def test_missing_required_field_raises(tmp_path: Path, missing_field: str) -> None:
    entry = _minimal_entry()
    del entry[missing_field]
    path = _write_registry(tmp_path, [entry])
    with pytest.raises(CapabilityRegistryError, match=f"missing required field {missing_field!r}"):
        load_capability_registry(path)


# ──────────────────────────────────────────────────────────────────────────────
# Enum field validation
# ──────────────────────────────────────────────────────────────────────────────


def test_invalid_kind_raises(tmp_path: Path) -> None:
    path = _write_registry(tmp_path, [_minimal_entry(kind="not_a_valid_kind")])
    with pytest.raises(CapabilityRegistryError, match="invalid kind"):
        load_capability_registry(path)


def test_invalid_applicator_raises(tmp_path: Path) -> None:
    path = _write_registry(tmp_path, [_minimal_entry(applicator="instant_magic")])
    with pytest.raises(CapabilityRegistryError, match="invalid applicator"):
        load_capability_registry(path)


def test_invalid_risk_raises(tmp_path: Path) -> None:
    path = _write_registry(tmp_path, [_minimal_entry(risk="catastrophic")])
    with pytest.raises(CapabilityRegistryError, match="invalid risk"):
        load_capability_registry(path)


def test_invalid_actionable_by_raises(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [_minimal_entry(actionable_by="gated:   ")],
    )
    with pytest.raises(CapabilityRegistryError, match="invalid actionable_by"):
        load_capability_registry(path)


def test_invalid_promotion_state_raises(tmp_path: Path) -> None:
    path = _write_registry(tmp_path, [_minimal_entry(promotion_state="deployed")])
    with pytest.raises(CapabilityRegistryError, match="invalid promotion_state"):
        load_capability_registry(path)


def test_promoted_entry_requires_autopilot_and_kill_condition(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _minimal_entry(
                promotion_state="promoted",
                actionable_by="operator",
                kill_condition="rollback on regression",
            )
        ],
    )
    with pytest.raises(CapabilityRegistryError, match="promoted rows must set actionable_by"):
        load_capability_registry(path)


def test_promoted_entry_requires_text_kill_condition(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _minimal_entry(
                promotion_state="promoted",
                actionable_by="autopilot",
                kill_condition=["rollback on regression"],
            )
        ],
    )
    with pytest.raises(
        CapabilityRegistryError,
        match="promoted rows must define a non-empty string kill_condition",
    ):
        load_capability_registry(path)


def test_restart_applicator_requires_trial_protocol(tmp_path: Path) -> None:
    entry = _minimal_entry()
    del entry["trial_protocol"]
    path = _write_registry(tmp_path, [entry])
    with pytest.raises(
        CapabilityRegistryError,
        match="restart applicator rows must define trial_protocol mapping",
    ):
        load_capability_registry(path)


def test_restart_trial_protocol_requires_batched_restore_boundary(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _minimal_entry(
                trial_protocol={
                    "class": "single_restart",
                    "min_trials": 0,
                    "restore_after_batch": False,
                    "boundary_event": "",
                    "smoke_check": "",
                    "require_explicit_affected_roles": False,
                },
            )
        ],
    )
    with pytest.raises(CapabilityRegistryError) as exc_info:
        load_capability_registry(path)
    msg = str(exc_info.value)
    assert "trial_protocol.class must be 'batched_restart'" in msg
    assert "trial_protocol.min_trials must be an integer >= 1" in msg
    assert "trial_protocol.restore_after_batch must be true" in msg
    assert "trial_protocol.boundary_event must be a non-empty string" in msg
    assert "trial_protocol.smoke_check must be a non-empty string" in msg
    assert "trial_protocol.require_explicit_affected_roles must be true" in msg


def test_non_restart_applicator_does_not_require_trial_protocol(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _minimal_entry(
                kind="flag",
                applicator="config_post",
                trial_protocol=None,
            )
        ],
    )
    caps = load_capability_registry(path)
    assert caps[0]["applicator"] == "config_post"


@pytest.mark.parametrize("valid_kind", ["env", "flag", "numeric", "prompt", "registry-field", "restart-class"])
def test_all_valid_kinds_accepted(tmp_path: Path, valid_kind: str) -> None:
    path = _write_registry(tmp_path, [_minimal_entry(id=f"lever_{valid_kind.replace('-', '_')}", kind=valid_kind)])
    caps = load_capability_registry(path)
    assert caps[0]["kind"] == valid_kind


@pytest.mark.parametrize("valid_applicator", ["config_post", "env_hotswap", "role_restart", "stack_restart"])
def test_all_valid_applicators_accepted(tmp_path: Path, valid_applicator: str) -> None:
    trial_protocol = (
        {
            "class": "batched_restart",
            "min_trials": 5,
            "restore_after_batch": True,
            "boundary_event": "role_restart_boundary",
            "smoke_check": "canned_completion",
            "require_explicit_affected_roles": True,
        }
        if valid_applicator in {"role_restart", "stack_restart"}
        else None
    )
    path = _write_registry(
        tmp_path,
        [
            _minimal_entry(
                id=f"lever_{valid_applicator}",
                applicator=valid_applicator,
                trial_protocol=trial_protocol,
            )
        ],
    )
    caps = load_capability_registry(path)
    assert caps[0]["applicator"] == valid_applicator


# ──────────────────────────────────────────────────────────────────────────────
# Evidence sub-field validation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("missing_sub", ["measured", "protocol", "source"])
def test_missing_evidence_subfield_raises(tmp_path: Path, missing_sub: str) -> None:
    entry = _minimal_entry()
    del entry["evidence"][missing_sub]
    path = _write_registry(tmp_path, [entry])
    with pytest.raises(CapabilityRegistryError, match=f"evidence missing required sub-field {missing_sub!r}"):
        load_capability_registry(path)


def test_evidence_not_a_mapping_raises(tmp_path: Path) -> None:
    entry = _minimal_entry(evidence="just a string, not a map")
    path = _write_registry(tmp_path, [entry])
    with pytest.raises(CapabilityRegistryError, match="evidence must be a mapping"):
        load_capability_registry(path)


# ──────────────────────────────────────────────────────────────────────────────
# Structural validation
# ──────────────────────────────────────────────────────────────────────────────


def test_non_mapping_entry_raises(tmp_path: Path) -> None:
    """A list entry that is not a dict must be rejected."""
    path = _write_registry(tmp_path, ["not_a_dict"])
    with pytest.raises(CapabilityRegistryError, match="must be a mapping"):
        load_capability_registry(path)


def test_empty_roles_list_raises(tmp_path: Path) -> None:
    entry = _minimal_entry(roles=[])
    path = _write_registry(tmp_path, [entry])
    with pytest.raises(CapabilityRegistryError, match="roles must be a non-empty list"):
        load_capability_registry(path)


def test_roles_not_a_list_raises(tmp_path: Path) -> None:
    entry = _minimal_entry(roles="frontdoor")
    path = _write_registry(tmp_path, [entry])
    with pytest.raises(CapabilityRegistryError, match="roles must be a non-empty list"):
        load_capability_registry(path)


def test_range_not_a_mapping_raises(tmp_path: Path) -> None:
    entry = _minimal_entry(range="0..64")
    path = _write_registry(tmp_path, [entry])
    with pytest.raises(CapabilityRegistryError, match="range must be a mapping"):
        load_capability_registry(path)


# ──────────────────────────────────────────────────────────────────────────────
# Multiple errors reported together
# ──────────────────────────────────────────────────────────────────────────────


def test_multiple_errors_reported_in_single_raise(tmp_path: Path) -> None:
    """A single bad entry with multiple violations produces one exception that
    lists all errors, not just the first."""
    bad_entry = {
        "id": "bad_lever",
        "kind": "not_valid",
        "surface": "X",
        "applicator": "also_invalid",
        # missing: range, roles, evidence, risk, actionable_by, promotion_state
    }
    path = _write_registry(tmp_path, [bad_entry])
    with pytest.raises(CapabilityRegistryError) as exc_info:
        load_capability_registry(path)
    msg = str(exc_info.value)
    assert "invalid kind" in msg
    assert "invalid applicator" in msg
    # At least some missing required fields should appear
    assert "missing required field" in msg
