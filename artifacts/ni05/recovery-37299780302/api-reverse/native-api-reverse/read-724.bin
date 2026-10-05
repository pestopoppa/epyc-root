"""Guards for the tracked runtime-flag spec.

The live overlay (``orchestration/runtime_flags.json``) is gitignored runtime
state, so the only thing keeping a fresh clone able to reproduce production
behaviour is ``orchestration/runtime_flags.spec.yaml``. These tests exist so
that spec cannot silently rot: flag names are derived from code, and every
derived layer the spec leans on is pinned to what the stack actually launches.

Nothing here reads the live flag file — ``tests/conftest.py`` pins
``ORCHESTRATOR_RUNTIME_FLAGS_PATH`` to an empty fixture on purpose, and drift
cases below supply their own temp file.
"""

from __future__ import annotations

import json

import pytest

from src import runtime_flag_spec as rfs
from src.runtime_flag_spec import (
    Spec,
    SpecEntry,
    SpecError,
    baseline_posture,
    compute_drift,
    flag_metadata,
    load_spec,
    referenced_flag_names,
    registry_flag_names,
    render_spec,
    spec_coverage,
    sync_spec,
)


def _write_live(tmp_path, flags: dict[str, object]):
    path = tmp_path / "runtime_flags.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "flags": {
                    name: {"value": value, "set_by": "unit-test", "ts": "2026-08-03T00:00:00+00:00"}
                    for name, value in flags.items()
                },
            }
        )
    )
    return path


# ── Coverage: the spec must not rot ────────────────────────────────────────


def test_every_flag_in_code_is_declared_in_the_spec():
    """A flag added to _FEATURE_REGISTRY without a spec entry fails here.

    This is the whole point of the spec: a clone must be able to see the
    intended production posture of EVERY flag, not just the ones somebody
    remembered to write down.
    """
    missing, _unknown = spec_coverage()
    assert not missing, (
        f"{len(missing)} flag(s) exist in src/features.py but not in "
        f"{rfs.SPEC_PATH.name}: {missing}. "
        "Run: python scripts/validate/runtime_flags_drift.py --sync-spec"
    )


def test_spec_has_no_entries_for_flags_that_left_the_code():
    _missing, unknown = spec_coverage()
    assert not unknown, (
        f"spec declares flags no longer in the registry: {unknown}. "
        "Run: python scripts/validate/runtime_flags_drift.py --sync-spec"
    )


def test_coverage_check_actually_detects_a_missing_flag(monkeypatch):
    """The guard must FAIL on a gap, not just pass on the compliant tree."""
    from src.features import FeatureSpec, _FEATURE_REGISTRY

    extra = FeatureSpec("brand_new_unspecced_flag", False, False, "BRAND_NEW_UNSPECCED_FLAG", "x")
    monkeypatch.setattr("src.features._FEATURE_REGISTRY", _FEATURE_REGISTRY + (extra,))

    missing, unknown = spec_coverage()
    assert missing == ["brand_new_unspecced_flag"]
    assert not unknown


def test_spec_loads_and_declares_only_known_flags():
    spec = load_spec()
    assert spec.flags
    assert set(spec.flags) == set(registry_flag_names())


def test_every_flag_read_off_a_features_object_is_registered():
    """A flag consumed in code but never registered would be invisible to the spec."""
    unregistered = referenced_flag_names() - set(registry_flag_names())
    assert not unregistered, (
        f"attributes read off a Features object with no FeatureSpec: {sorted(unregistered)}"
    )


def test_reference_scan_finds_real_flags():
    """Sanity-check the scanner itself; an always-empty scan would pass vacuously."""
    found = referenced_flag_names()
    assert len(found) >= 10
    assert found <= set(registry_flag_names())


# ── The derived baseline must match what the stack actually launches ───────


def test_baseline_matches_the_stack_production_feature_env():
    """`baseline` in the spec means the stack's launch posture — prove it.

    If orchestrator_stack stopped honouring the registry (or the wave overrides
    moved), every `baseline` entry in the spec would quietly mean something
    else. This pins the two together.
    """
    from scripts.server.orchestrator_stack import _production_feature_env

    env = _production_feature_env()
    meta = flag_metadata()
    values, _sources = baseline_posture()

    for name, expected in values.items():
        env_name = meta[name]["env_var"]
        assert env_name in env, f"{name}: {env_name} missing from the launch env block"
        assert env[env_name] == ("1" if expected else "0"), (
            f"{name}: spec baseline={expected} but stack launches {env_name}={env[env_name]}"
        )


def test_wave_overrides_only_name_registered_flags():
    values, sources = baseline_posture()
    wave = {name for name, source in sources.items() if source == "stack:wave_override"}
    assert wave <= set(values)
    assert wave, "expected at least one wave-gated flag"


# ── Spec grammar ───────────────────────────────────────────────────────────


def test_pin_without_a_reason_is_rejected(tmp_path):
    path = tmp_path / "spec.yaml"
    path.write_text("version: 1\nflags:\n  memrl:\n    expected: off\n")
    with pytest.raises(SpecError, match="reason"):
        load_spec(path)


def test_unknown_flag_in_spec_is_rejected(tmp_path):
    path = tmp_path / "spec.yaml"
    path.write_text("version: 1\nflags:\n  no_such_flag: baseline\n")
    with pytest.raises(SpecError, match="not a known feature flag"):
        load_spec(path)


def test_bad_expected_value_is_rejected(tmp_path):
    path = tmp_path / "spec.yaml"
    path.write_text('version: 1\nflags:\n  memrl:\n    expected: maybe\n    reason: "x"\n')
    with pytest.raises(SpecError, match="on/off/baseline"):
        load_spec(path)


def test_render_round_trips(tmp_path):
    spec = load_spec()
    path = tmp_path / "spec.yaml"
    path.write_text(render_spec(spec))
    reloaded = load_spec(path)
    assert {n: (e.expected, e.reason) for n, e in reloaded.flags.items()} == {
        n: (e.expected, e.reason) for n, e in spec.flags.items()
    }
    assert render_spec(reloaded) == render_spec(spec)


def test_sync_adopts_new_flags_as_baseline_and_drops_retired_ones(monkeypatch):
    from src.features import FeatureSpec, _FEATURE_REGISTRY

    extra = FeatureSpec("freshly_added_flag", False, True, "FRESHLY_ADDED_FLAG", "x")
    monkeypatch.setattr("src.features._FEATURE_REGISTRY", _FEATURE_REGISTRY + (extra,))

    stale = Spec(
        flags={
            "memrl": SpecEntry("memrl"),
            "retired_flag": SpecEntry("retired_flag", expected=True, reason="old"),
        }
    )
    synced, added, removed = sync_spec(stale)

    assert "freshly_added_flag" in added
    assert removed == ["retired_flag"]
    assert synced.flags["freshly_added_flag"].follows_baseline
    assert "retired_flag" not in synced.flags


def test_sync_can_read_a_spec_that_still_names_a_retired_flag(tmp_path):
    """The strict loader rejects retired names and tells you to --sync-spec.

    So sync must be able to parse exactly what the strict loader rejects, or the
    guard forbids its own remedy and the file becomes unrepairable by the tool.
    """
    path = tmp_path / "spec.yaml"
    path.write_text("version: 1\nflags:\n  langgraph_architect_coding: baseline\n  memrl: baseline\n")

    with pytest.raises(SpecError, match="not a known feature flag"):
        load_spec(path)

    tolerant = load_spec(path, tolerant=True)
    synced, _added, removed = sync_spec(tolerant)

    assert removed == ["langgraph_architect_coding"]
    path.write_text(render_spec(synced))
    assert set(load_spec(path).flags) == set(registry_flag_names())


def test_sync_preserves_hand_written_pins(monkeypatch):
    stale = Spec(flags={"memrl": SpecEntry("memrl", expected=False, reason="kept", since="2026-01-01")})
    synced, _added, _removed = sync_spec(stale)
    assert synced.flags["memrl"].expected is False
    assert synced.flags["memrl"].reason == "kept"


# ── Drift ──────────────────────────────────────────────────────────────────


def _all_baseline_spec() -> Spec:
    return Spec(flags={name: SpecEntry(name) for name in registry_flag_names()})


def test_undeclared_override_is_reported(tmp_path):
    values, _ = baseline_posture()
    flag = "session_compaction"
    live = _write_live(tmp_path, {flag: not values[flag]})

    drifts = {d.flag: d for d in compute_drift(_all_baseline_spec(), live)}

    assert drifts[flag].kind == "undeclared_override"
    assert drifts[flag].effective is (not values[flag])
    assert drifts[flag].expected is values[flag]
    assert drifts[flag].set_by == "unit-test"


def test_pinned_expectation_suppresses_the_drift(tmp_path):
    values, _ = baseline_posture()
    flag = "session_compaction"
    live = _write_live(tmp_path, {flag: not values[flag]})
    spec = _all_baseline_spec()
    spec.flags[flag] = SpecEntry(flag, expected=not values[flag], reason="declared")

    drifts = {d.flag: d.kind for d in compute_drift(spec, live)}

    assert flag not in drifts


def test_pin_the_live_file_does_not_carry_is_reported(tmp_path):
    values, _ = baseline_posture()
    flag = "session_compaction"
    live = _write_live(tmp_path, {})
    spec = _all_baseline_spec()
    spec.flags[flag] = SpecEntry(flag, expected=not values[flag], reason="declared")

    drifts = {d.flag: d for d in compute_drift(spec, live)}

    assert drifts[flag].kind == "contradicts_spec"
    assert drifts[flag].live_present is False


def test_redundant_override_is_reported_but_not_blocking(tmp_path):
    values, _ = baseline_posture()
    flag = "session_compaction"
    live = _write_live(tmp_path, {flag: values[flag]})

    drift = next(d for d in compute_drift(_all_baseline_spec(), live) if d.flag == flag)

    assert drift.kind == "redundant_override"
    assert drift.kind not in rfs.BLOCKING_KINDS


def test_retired_flag_left_in_the_live_file_is_surfaced(tmp_path):
    """src.features silently drops unknown names; that must not hide dead config."""
    live = _write_live(tmp_path, {"langgraph_architect_coding": True})

    drift = next(
        d for d in compute_drift(_all_baseline_spec(), live) if d.flag == "langgraph_architect_coding"
    )

    assert drift.kind == "unknown_flag_in_live"


def test_dependency_violation_in_the_effective_posture_is_reported(tmp_path):
    live = _write_live(tmp_path, {"plan_review": True, "memrl": False})

    kinds = {d.kind for d in compute_drift(_all_baseline_spec(), live)}

    assert "dependency_violation" in kinds


def test_clean_live_file_produces_no_drift(tmp_path):
    live = _write_live(tmp_path, {})

    drifts = compute_drift(_all_baseline_spec(), live)

    assert drifts == [], [d.as_dict() for d in drifts]
