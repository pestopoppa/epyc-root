"""Characterization tests for src/features.py.

Tests the Features dataclass, validation logic, singleton accessor,
environment variable parsing, and get_features() factory function.
"""

from __future__ import annotations

import pytest

from src.features import (
    Features,
    _feature_flag_bool,
    features,
    get_features,
    reset_features,
)


@pytest.fixture(autouse=True)
def _clean_singleton():
    """Reset the features singleton before and after every test."""
    reset_features()
    yield
    reset_features()


# ---------------------------------------------------------------------------
# 1. Features defaults (dataclass field defaults)
# ---------------------------------------------------------------------------
class TestFeaturesDefaults:
    def test_dataclass_defaults(self):
        """Features() with no args should produce the field-level defaults."""
        f = Features()
        # Explicitly False by default
        assert f.memrl is False
        assert f.scripts is False
        assert f.streaming is False
        assert f.openai_compat is False
        assert f.react_mode is False
        assert f.output_formalizer is False
        assert f.deferred_tool_results is False
        assert f.restricted_python is False
        assert f.specialist_routing is False
        assert f.plan_review is False
        assert f.architect_delegation is False
        assert f.parallel_execution is False
        assert f.personas is False
        assert f.staged_rewards is False
        assert f.skillbank is False
        assert f.input_formalizer is False
        assert f.unified_streaming is False
        assert f.side_effect_tracking is False
        assert f.structured_tool_output is False
        assert f.model_fallback is False
        assert f.content_cache is False
        assert f.session_compaction is False
        assert f.depth_model_overrides is False
        assert f.resume_tokens is False
        assert f.approval_gates is False
        assert f.binding_routing is False
        assert f.eval_batch_serving is False
        assert f.review_before_commit_consult is False
        assert f.review_before_commit_targeted_gate is False

        # Explicitly True by default
        assert f.tools is True
        assert f.repl is True
        assert f.caching is True
        assert f.structured_delimiters is True
        assert f.semantic_classifiers is True
        assert f.generation_monitor is True
        assert f.mock_mode is True


# ---------------------------------------------------------------------------
# 2-6. Features.validate() dependency checks
# ---------------------------------------------------------------------------
class TestFeaturesValidate:
    def test_scripts_without_tools_error(self):
        """scripts=True without tools=True is a dependency violation."""
        f = Features(scripts=True, tools=False)
        errors = f.validate()
        assert any("scripts" in e and "tools" in e for e in errors)

    def test_specialist_routing_without_memrl_error(self):
        """specialist_routing requires memrl."""
        f = Features(specialist_routing=True, memrl=False)
        errors = f.validate()
        assert any("specialist_routing" in e and "memrl" in e for e in errors)

    def test_graph_router_without_specialist_routing_error(self):
        """graph_router requires specialist_routing."""
        f = Features(graph_router=True, specialist_routing=False, memrl=True)
        errors = f.validate()
        assert any("graph_router" in e and "specialist_routing" in e for e in errors)

    def test_plan_review_without_memrl_error(self):
        """plan_review requires memrl."""
        f = Features(plan_review=True, memrl=False)
        errors = f.validate()
        assert any("plan_review" in e and "memrl" in e for e in errors)

    def test_approval_gates_without_resume_tokens_error(self):
        """approval_gates requires resume_tokens."""
        f = Features(approval_gates=True, resume_tokens=False)
        errors = f.validate()
        assert any("approval_gates" in e and "resume_tokens" in e for e in errors)

    def test_approval_gates_without_side_effect_tracking_error(self):
        """approval_gates also requires side_effect_tracking."""
        f = Features(approval_gates=True, side_effect_tracking=False)
        errors = f.validate()
        assert any("approval_gates" in e and "side_effect_tracking" in e for e in errors)

    def test_valid_config_no_errors(self):
        """A fully-satisfied dependency set should produce zero errors."""
        f = Features(
            memrl=True,
            tools=True,
            scripts=True,
            specialist_routing=True,
            plan_review=True,
            architect_delegation=True,
            parallel_execution=True,
            personas=True,
            staged_rewards=True,
            skillbank=True,
            resume_tokens=True,
            side_effect_tracking=True,
            approval_gates=True,
            restricted_python=False,  # skip library check
        )
        errors = f.validate()
        assert errors == []

    def test_architect_delegation_without_memrl_error(self):
        """architect_delegation requires memrl."""
        f = Features(architect_delegation=True, memrl=False)
        errors = f.validate()
        assert any("architect_delegation" in e and "memrl" in e for e in errors)

    def test_parallel_execution_without_architect_delegation_error(self):
        """parallel_execution requires architect_delegation."""
        f = Features(parallel_execution=True, architect_delegation=False)
        errors = f.validate()
        assert any("parallel_execution" in e and "architect_delegation" in e for e in errors)

    def test_personas_without_memrl_error(self):
        """personas requires memrl."""
        f = Features(personas=True, memrl=False)
        errors = f.validate()
        assert any("personas" in e and "memrl" in e for e in errors)

    def test_staged_rewards_without_memrl_error(self):
        """staged_rewards requires memrl."""
        f = Features(staged_rewards=True, memrl=False)
        errors = f.validate()
        assert any("staged_rewards" in e and "memrl" in e for e in errors)

    def test_skillbank_without_memrl_error(self):
        """skillbank requires memrl."""
        f = Features(skillbank=True, memrl=False)
        errors = f.validate()
        assert any("skillbank" in e and "memrl" in e for e in errors)

    def test_dcp_for_consult_requires_dcp_pre_assembly(self):
        """consult DCP reuse requires the base DCP pre-assembly flag."""
        f = Features(dcp_for_consult=True, dcp_pre_assembly=False)
        errors = f.validate()
        assert any("dcp_for_consult" in e and "dcp_pre_assembly" in e for e in errors)

    def test_dcp_for_consult_dependency_satisfied(self):
        """dcp_for_consult is valid when dcp_pre_assembly is also enabled."""
        f = Features(dcp_for_consult=True, dcp_pre_assembly=True)
        errors = f.validate()
        assert not any("dcp_for_consult" in e for e in errors)

    def test_review_before_commit_consult_has_no_flag_dependency(self):
        """The edit-transaction consult seam is independently default-off."""
        f = Features(review_before_commit_consult=True)
        errors = f.validate()
        assert not any("review_before_commit_consult" in e for e in errors)


# ---------------------------------------------------------------------------
# 7. Features.summary()
# ---------------------------------------------------------------------------
class TestFeaturesSummary:
    def test_summary_returns_dict_with_all_keys(self):
        """summary() must return a dict covering every registry entry."""
        from src.features import _FEATURE_REGISTRY

        f = Features()
        s = f.summary()
        expected_keys = {spec.name for spec in _FEATURE_REGISTRY}
        assert set(s.keys()) == expected_keys

    def test_summary_values_match_fields(self):
        """summary() values must agree with the instance attributes."""
        f = Features(memrl=True, tools=False, streaming=True)
        s = f.summary()
        assert s["memrl"] is True
        assert s["tools"] is False
        assert s["streaming"] is True


# ---------------------------------------------------------------------------
# 8. Features.enabled_features()
# ---------------------------------------------------------------------------
class TestEnabledFeatures:
    def test_enabled_features_returns_only_true(self):
        """enabled_features() should list exactly the flags that are True."""
        f = Features(memrl=True, tools=True, scripts=False, streaming=False,
                     repl=False, caching=False, structured_delimiters=False,
                     semantic_classifiers=False, generation_monitor=False,
                     mock_mode=False)
        enabled = f.enabled_features()
        assert "memrl" in enabled
        assert "tools" in enabled
        assert "scripts" not in enabled
        assert "streaming" not in enabled

    def test_all_false_returns_empty(self):
        """If every flag is False, enabled_features() should be empty."""
        kwargs = {name: False for name in Features().summary()}
        f = Features(**kwargs)
        assert f.enabled_features() == []


# ---------------------------------------------------------------------------
# 9-10. get_features() test-mode vs production defaults
# ---------------------------------------------------------------------------
class TestGetFeatures:
    def test_test_mode_defaults(self, monkeypatch, tmp_path):
        """get_features() in test mode: mock_mode=True, repl=True, tools=False."""
        monkeypatch.setenv(
            "ORCHESTRATOR_RUNTIME_FLAGS_PATH",
            str(tmp_path / "missing-runtime-flags.json"),
        )
        f = get_features(production=False)
        assert f.mock_mode is True
        assert f.repl is True
        assert f.tools is False
        assert f.memrl is False
        assert f.streaming is False

    def test_production_defaults(self, monkeypatch):
        """get_features(production=True): mock_mode=False, tools=True, memrl=True."""
        monkeypatch.setenv("ORCHESTRATOR_MOCK_MODE", "0")
        f = get_features(production=True)
        assert f.mock_mode is False
        assert f.tools is True
        assert f.memrl is True
        assert f.streaming is True
        assert f.scripts is True
        assert f.openai_compat is True
        assert f.repl is True
        assert f.session_compaction is True
        assert f.depth_model_overrides is True

    def test_logit_probe_defaults_off_and_env_enables(self, monkeypatch):
        """The routing logit probe is default-off and explicitly env-gated."""
        assert get_features(production=True).logit_probe is False
        monkeypatch.setenv("ORCHESTRATOR_LOGIT_PROBE", "1")
        assert get_features(production=True).logit_probe is True

    def test_eval_batch_serving_defaults_off_and_env_enables(self, monkeypatch):
        """The P-BENCH-3 eval-batch serving hook is default-off."""
        assert get_features(production=True).eval_batch_serving is False
        monkeypatch.setenv("ORCHESTRATOR_EVAL_BATCH_SERVING", "1")
        assert get_features(production=True).eval_batch_serving is True

    def test_override_applies(self):
        """Explicit override dict takes precedence over defaults."""
        f = get_features(override={"memrl": True})
        assert f.memrl is True

    def test_override_can_disable_production_default(self):
        """Override can turn off a production-default-on flag."""
        f = get_features(production=True, override={"tools": False})
        assert f.tools is False


# ---------------------------------------------------------------------------
# 12. _feature_flag_bool reads from ORCHESTRATOR_ prefix
# ---------------------------------------------------------------------------
class TestEnvBool:
    @pytest.mark.parametrize("val,expected", [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
    ])
    def test_truthy_falsy_values(self, monkeypatch, val, expected):
        """_feature_flag_bool should parse various truthy/falsy strings."""
        monkeypatch.setenv("ORCHESTRATOR_TEST_FLAG", val)
        assert _feature_flag_bool("TEST_FLAG", default=not expected) is expected

    def test_missing_env_uses_default(self, monkeypatch):
        """Missing env var returns the default."""
        monkeypatch.delenv("ORCHESTRATOR_MISSING", raising=False)
        assert _feature_flag_bool("MISSING", default=True) is True
        assert _feature_flag_bool("MISSING", default=False) is False

    def test_unrecognized_value_uses_default(self, monkeypatch):
        """Unrecognized string falls back to default."""
        monkeypatch.setenv("ORCHESTRATOR_WEIRD", "maybe")
        assert _feature_flag_bool("WEIRD", default=True) is True
        assert _feature_flag_bool("WEIRD", default=False) is False

    def test_prefix_is_applied(self, monkeypatch):
        """_feature_flag_bool('MEMRL') reads ORCHESTRATOR_MEMRL."""
        monkeypatch.setenv("ORCHESTRATOR_MEMRL", "1")
        assert _feature_flag_bool("MEMRL") is True


# ---------------------------------------------------------------------------
# 13-14. Singleton: features() and reset_features()
# ---------------------------------------------------------------------------
class TestSingleton:
    def test_features_returns_same_instance(self):
        """features() should return the same object on repeated calls."""
        a = features()
        b = features()
        assert a is b

    def test_reset_features_clears_singleton(self):
        """After reset_features(), a new instance should be created."""
        a = features()
        reset_features()
        b = features()
        assert a is not b


# ---------------------------------------------------------------------------
# 15. Environment variable override of feature flags via get_features()
# ---------------------------------------------------------------------------
class TestEnvVarOverride:
    def test_env_var_overrides_test_default(self, monkeypatch):
        """Setting ORCHESTRATOR_MEMRL=1 should override the test default (False)."""
        monkeypatch.setenv("ORCHESTRATOR_MEMRL", "1")
        f = get_features(production=False)
        assert f.memrl is True

    def test_env_var_overrides_production_default(self, monkeypatch):
        """Setting ORCHESTRATOR_TOOLS=0 should override the production default (True)."""
        monkeypatch.setenv("ORCHESTRATOR_TOOLS", "0")
        f = get_features(production=True)
        assert f.tools is False

    def test_singleton_reads_env_at_creation(self, monkeypatch):
        """The singleton should reflect env vars present at first call."""
        monkeypatch.setenv("ORCHESTRATOR_STREAMING", "1")
        reset_features()
        f = features()
        assert f.streaming is True


# ── Registry Consistency ─────────────────────────────────────────────────


class TestRegistryConsistency:
    """Validate that the FeatureSpec registry stays in sync with the Features dataclass."""

    @staticmethod
    def _isolate_flag_env(monkeypatch) -> None:
        """Strip every per-flag env override before asserting about DEFAULTS.

        `_compute_feature_flags` lets `ORCHESTRATOR_<env_var>` /
        `ORCHESTRATOR_FEATURE_<env_var>` beat the registry default — correct for
        a flag override, wrong input for a test whose whole claim is about the
        defaults. Ambient values leak in: tests/unit/test_odl_structured.py sets
        `ORCHESTRATOR_MOCK_MODE=1` at MODULE IMPORT time with no teardown, so
        merely COLLECTING the suite poisoned this process and
        `get_features(production=True).mock_mode` came back True against
        `default_prod=False`. Same remedy as conftest.py's
        `_pin_runtime_feature_flags`, which pins the runtime flag FILE for the
        identical reproducibility reason. The assertion loops are untouched and
        gain strength: they can no longer be satisfied OR broken by ambient env.
        """
        from src.features import ENV_PREFIX, FEATURE_ENV_PREFIX, _FEATURE_REGISTRY

        for spec in _FEATURE_REGISTRY:
            monkeypatch.delenv(f"{ENV_PREFIX}{spec.env_var}", raising=False)
            monkeypatch.delenv(f"{FEATURE_ENV_PREFIX}{spec.env_var}", raising=False)

    def test_registry_matches_dataclass_fields(self):
        """Every registry entry must have a matching dataclass field and vice versa."""
        import dataclasses
        from src.features import _FEATURE_REGISTRY

        dc_fields = {f.name for f in dataclasses.fields(Features)}
        reg_names = {spec.name for spec in _FEATURE_REGISTRY}
        missing_in_registry = dc_fields - reg_names
        missing_in_dataclass = reg_names - dc_fields
        assert not missing_in_registry, f"Dataclass fields not in registry: {missing_in_registry}"
        assert not missing_in_dataclass, f"Registry entries not in dataclass: {missing_in_dataclass}"

    def test_registry_test_defaults_match_get_features(self, monkeypatch, tmp_path):
        """Registry default_test must match get_features(production=False) output."""
        from src.features import _FEATURE_REGISTRY

        monkeypatch.setenv(
            "ORCHESTRATOR_RUNTIME_FLAGS_PATH",
            str(tmp_path / "missing-runtime-flags.json"),
        )
        self._isolate_flag_env(monkeypatch)
        f = get_features(production=False)
        for spec in _FEATURE_REGISTRY:
            actual = getattr(f, spec.name)
            assert actual == spec.default_test, (
                f"{spec.name}: get_features(production=False)={actual} "
                f"!= registry default_test={spec.default_test}"
            )

    def test_registry_prod_defaults_match_get_features(self, monkeypatch, tmp_path):
        """Registry default_prod must match get_features(production=True) output."""
        from src.features import _FEATURE_REGISTRY

        monkeypatch.setenv(
            "ORCHESTRATOR_RUNTIME_FLAGS_PATH",
            str(tmp_path / "missing-runtime-flags.json"),
        )
        self._isolate_flag_env(monkeypatch)
        f = get_features(production=True)
        for spec in _FEATURE_REGISTRY:
            actual = getattr(f, spec.name)
            assert actual == spec.default_prod, (
                f"{spec.name}: get_features(production=True)={actual} "
                f"!= registry default_prod={spec.default_prod}"
            )

    def test_registry_env_vars_are_unique(self):
        """Each registry entry must have a unique env_var."""
        from src.features import _FEATURE_REGISTRY

        env_vars = [spec.env_var for spec in _FEATURE_REGISTRY]
        assert len(env_vars) == len(set(env_vars)), f"Duplicate env_vars: {[v for v in env_vars if env_vars.count(v) > 1]}"

    def test_registry_names_are_unique(self):
        """Each registry entry must have a unique name."""
        from src.features import _FEATURE_REGISTRY

        names = [spec.name for spec in _FEATURE_REGISTRY]
        assert len(names) == len(set(names)), f"Duplicate names: {[n for n in names if names.count(n) > 1]}"
