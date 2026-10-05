"""Unit tests for registry_loader module."""

from pathlib import Path

import pytest
import yaml

from src.registry_loader import (
    DEFAULT_LEAN_REGISTRY_PATH,
    PerformanceMetrics,
    RegistryError,
    RegistryLoader,
    ResolvedTps,
    format_tps,
    resolve_tps_prior,
)

_RETIRED_ARCHITECT_ROLE = "architect_coding"


# Test fixtures
@pytest.fixture
def minimal_registry(tmp_path: Path) -> Path:
    """Create a minimal valid registry file."""
    registry = {
        "runtime_defaults": {
            "model_base_path": str(tmp_path),
            "threads": 96,
            "context_length": 8192,
        },
        "roles": {
            "test_role": {
                "tier": "C",
                "description": "Test role",
                "model": {
                    "name": "test-model",
                    "path": "test-model.gguf",
                    "quant": "Q4_K_M",
                    "size_gb": 1.0,
                },
                "acceleration": {
                    "type": "none",
                },
                "performance": {
                    "baseline_tps": 10.0,
                },
                "memory": {
                    "residency": "hot",
                },
            },
        },
        "routing_hints": [
            {"if": "task_type == 'code'", "use": ["test_role"]},
        ],
        "command_templates": {
            "baseline": "llama-cli -m {model_path} -t {threads}",
        },
    }

    # Create dummy model file
    (tmp_path / "test-model.gguf").touch()

    registry_path = tmp_path / "registry.yaml"
    with registry_path.open("w") as f:
        yaml.dump(registry, f)

    return registry_path


@pytest.fixture
def speculative_registry(tmp_path: Path) -> Path:
    """Create a registry with speculative decoding configuration."""
    registry = {
        "runtime_defaults": {
            "model_base_path": str(tmp_path),
            "threads": 96,
            "context_length": 8192,
        },
        "roles": {
            "target": {
                "tier": "B",
                "description": "Target model",
                "model": {
                    "name": "target-model",
                    "path": "target.gguf",
                    "quant": "Q4_K_M",
                    "size_gb": 10.0,
                },
                "acceleration": {
                    "type": "speculative_decoding",
                    "draft_role": "draft",
                    "k": 16,
                },
                "performance": {"baseline_tps": 5.0, "optimized_tps": 30.0},
                "memory": {"residency": "hot"},
            },
            "draft": {
                "tier": "D",
                "description": "Draft model",
                "model": {
                    "name": "draft-model",
                    "path": "draft.gguf",
                    "quant": "Q8_0",
                    "size_gb": 0.5,
                },
                "acceleration": {"type": "none"},
                "performance": {"raw_tps": 85},
                "memory": {"residency": "hot"},
            },
        },
        "command_templates": {
            "speculative_decoding": "llama-spec -m {model_path} -md {draft_path} --draft-max {k}",
            "baseline": "llama-cli -m {model_path}",
        },
    }

    (tmp_path / "target.gguf").touch()
    (tmp_path / "draft.gguf").touch()

    registry_path = tmp_path / "registry.yaml"
    with registry_path.open("w") as f:
        yaml.dump(registry, f)

    return registry_path


class TestRegistryLoaderBasic:
    """Basic loading tests."""

    def test_load_minimal_registry(self, minimal_registry: Path):
        """Test loading a minimal valid registry."""
        loader = RegistryLoader(minimal_registry, validate_paths=True)

        assert len(loader.roles) == 1
        assert "test_role" in loader.roles
        assert loader.missing_models == []

    def test_load_nonexistent_file(self, tmp_path: Path):
        """Test loading a nonexistent file raises error."""
        with pytest.raises(RegistryError, match="Registry not found"):
            RegistryLoader(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml(self, tmp_path: Path):
        """Test loading invalid YAML raises error."""
        registry_path = tmp_path / "invalid.yaml"
        registry_path.write_text("not: valid: yaml: {{")

        with pytest.raises(RegistryError, match="Invalid YAML"):
            RegistryLoader(registry_path)

    def test_load_empty_file(self, tmp_path: Path):
        """Test loading empty file raises error."""
        registry_path = tmp_path / "empty.yaml"
        registry_path.write_text("")

        with pytest.raises(RegistryError, match="Empty registry"):
            RegistryLoader(registry_path)

    def test_load_no_roles(self, tmp_path: Path):
        """Test loading registry without roles raises error."""
        registry_path = tmp_path / "no_roles.yaml"
        registry_path.write_text("runtime_defaults:\n  threads: 96\n")

        with pytest.raises(RegistryError, match="No roles defined"):
            RegistryLoader(registry_path)

    def test_committed_lean_registry_excludes_retired_architect_role(self):
        """Lean registry routes code escalation to the live coder role.

        2026-08-01: repointed from the hand-maintained
        `orchestration/model_registry_lean.yaml` (deleted — a second, drifted role
        table dated 2026-06-13) to the compiled lean artifact that
        `src/registry/registry_compiler.py` regenerates from the master registry.
        """
        registry_path = DEFAULT_LEAN_REGISTRY_PATH

        loader = RegistryLoader(registry_path, validate_paths=False)

        assert _RETIRED_ARCHITECT_ROLE not in loader.roles
        assert loader.get_timeout(_RETIRED_ARCHITECT_ROLE) == loader.get_timeout("default")
        assert loader.get_escalation_chain("coder").chain == [
            "frontdoor",
            "coder_escalation",
        ]
        assert all(_RETIRED_ARCHITECT_ROLE not in hint.use for hint in loader.routing_hints)


class TestRoleAccess:
    """Tests for role access methods."""

    def test_get_role(self, minimal_registry: Path):
        """Test getting a specific role."""
        loader = RegistryLoader(minimal_registry)
        role = loader.get_role("test_role")

        assert role.name == "test_role"
        assert role.tier == "C"
        assert role.model.name == "test-model"

    def test_get_nonexistent_role(self, minimal_registry: Path):
        """Test getting nonexistent role raises KeyError."""
        loader = RegistryLoader(minimal_registry)

        with pytest.raises(KeyError, match="Role not found"):
            loader.get_role("nonexistent")

    def test_get_roles_by_tier(self, minimal_registry: Path):
        """Test filtering roles by tier."""
        loader = RegistryLoader(minimal_registry)

        tier_c = loader.get_roles_by_tier("C")
        tier_a = loader.get_roles_by_tier("A")

        assert len(tier_c) == 1
        assert tier_c[0].name == "test_role"
        assert len(tier_a) == 0


class TestSpeculativeDecoding:
    """Tests for speculative decoding configuration."""

    def test_get_draft_for_role(self, speculative_registry: Path):
        """Test getting draft model for speculative decoding."""
        loader = RegistryLoader(speculative_registry)
        draft = loader.get_draft_for_role("target")

        assert draft is not None
        assert draft.name == "draft"
        assert draft.model.name == "draft-model"

    def test_get_draft_for_non_speculative(self, minimal_registry: Path):
        """Test getting draft for non-speculative role returns None."""
        loader = RegistryLoader(minimal_registry)
        draft = loader.get_draft_for_role("test_role")

        assert draft is None


class TestCommandGeneration:
    """Tests for command generation."""

    def test_generate_baseline_command(self, minimal_registry: Path):
        """Test generating baseline command."""
        loader = RegistryLoader(minimal_registry)
        cmd = loader.generate_command("test_role", prompt="Hello", n_tokens=32)

        assert "llama-cli" in cmd
        assert "-m" in cmd
        assert "test-model.gguf" in cmd
        assert "-t 96" in cmd
        assert "'Hello'" in cmd
        assert "-n 32" in cmd

    def test_generate_speculative_command(self, speculative_registry: Path):
        """Test generating speculative decoding command."""
        loader = RegistryLoader(speculative_registry)
        cmd = loader.generate_command("target", prompt="Code", n_tokens=64)

        assert "llama-spec" in cmd
        assert "target.gguf" in cmd
        assert "draft.gguf" in cmd
        assert "--draft-max 16" in cmd

    def test_generate_command_with_file(self, minimal_registry: Path):
        """Test generating command with prompt file."""
        loader = RegistryLoader(minimal_registry)
        cmd = loader.generate_command("test_role", prompt_file="/tmp/prompt.txt")

        assert "-f /tmp/prompt.txt" in cmd
        assert "-p" not in cmd.split("-f")[0]  # No inline prompt


class TestRouting:
    """Tests for task routing."""

    def test_route_code_task(self, minimal_registry: Path):
        """Test routing a code task."""
        loader = RegistryLoader(minimal_registry)

        task_ir = {
            "task_type": "code",
            "priority": "interactive",
            "objective": "Write a function",
            "constraints": [],
            "inputs": [],
            "escalation": {},
        }

        roles = loader.route_task(task_ir)
        assert roles == ["test_role"]

    def test_route_unknown_task(self, minimal_registry: Path):
        """Test routing unknown task defaults to frontdoor."""
        loader = RegistryLoader(minimal_registry)

        task_ir = {
            "task_type": "unknown",
            "priority": "batch",
            "objective": "Something",
            "constraints": [],
            "inputs": [],
            "escalation": {},
        }

        roles = loader.route_task(task_ir)
        assert roles == ["frontdoor"]


class TestResolvedTps:
    """NIB2-57a: the t/s prior must resolve with its provenance, never as a
    bare float that could be an optimized measurement, an unoptimized
    baseline standing in for a missing optimized, or nothing at all."""

    def test_optimized_wins_when_present(self):
        prior = resolve_tps_prior(PerformanceMetrics(optimized_tps=40.22, baseline_tps=24.3))
        assert prior == ResolvedTps(value=40.22, source="optimized")
        assert prior.measured is True

    def test_baseline_only_is_named_baseline_not_optimized(self):
        # NIB2-57 shape: a role with ONLY an unoptimized baseline must not
        # read as a measured optimized speed at the decision/display site.
        prior = resolve_tps_prior(PerformanceMetrics(baseline_tps=24.3))
        assert prior == ResolvedTps(value=24.3, source="baseline")
        assert prior.measured is True

    def test_neither_field_is_unmeasured_not_a_fabricated_number(self):
        prior = resolve_tps_prior(PerformanceMetrics())
        assert prior == ResolvedTps(value=None, source="unmeasured")
        assert prior.measured is False

    def test_format_tps_measured_optimized_is_unchanged(self):
        # Report-only rendering must stay byte-identical for the measured case.
        assert format_tps(PerformanceMetrics(optimized_tps=33.0, baseline_tps=3.0)) == "33.0 t/s"

    def test_format_tps_baseline_substitution_is_loud(self):
        assert (
            format_tps(PerformanceMetrics(baseline_tps=10.12))
            == "10.12 t/s (baseline, not optimized)"
        )

    def test_format_tps_unmeasured_says_unmeasured(self):
        assert format_tps(PerformanceMetrics()) == "unmeasured"


class TestValidation:
    """Tests for path validation."""

    def test_missing_model_detected(self, tmp_path: Path):
        """Test that missing model files are detected."""
        registry = {
            "runtime_defaults": {"model_base_path": str(tmp_path)},
            "roles": {
                "missing": {
                    "tier": "C",
                    "description": "Missing model",
                    "model": {
                        "name": "missing",
                        "path": "does-not-exist.gguf",
                        "quant": "Q4_K_M",
                        "size_gb": 1.0,
                    },
                    "acceleration": {"type": "none"},
                    "performance": {},
                    "memory": {"residency": "hot"},
                },
            },
        }

        registry_path = tmp_path / "registry.yaml"
        with registry_path.open("w") as f:
            yaml.dump(registry, f)

        loader = RegistryLoader(registry_path, validate_paths=True)

        assert len(loader.missing_models) == 1
        assert "missing" in loader.missing_models[0]

    def test_skip_validation(self, tmp_path: Path):
        """Test skipping path validation."""
        registry = {
            "runtime_defaults": {"model_base_path": str(tmp_path)},
            "roles": {
                "missing": {
                    "tier": "C",
                    "description": "Missing model",
                    "model": {
                        "name": "missing",
                        "path": "does-not-exist.gguf",
                        "quant": "Q4_K_M",
                        "size_gb": 1.0,
                    },
                    "acceleration": {"type": "none"},
                    "performance": {},
                    "memory": {"residency": "hot"},
                },
            },
        }

        registry_path = tmp_path / "registry.yaml"
        with registry_path.open("w") as f:
            yaml.dump(registry, f)

        loader = RegistryLoader(registry_path, validate_paths=False)

        assert len(loader.missing_models) == 0


def _is_ci() -> bool:
    """Check if running in CI environment."""
    import os

    return os.environ.get("CI") == "true" or os.environ.get("ORCHESTRATOR_MOCK_MODE") == "true"


@pytest.mark.skipif(_is_ci(), reason="Production registry tests require local paths")
class TestProductionRegistry:
    """Tests against the production registry."""

    def test_load_production_registry(self):
        """Test loading the actual production registry."""
        loader = RegistryLoader(validate_paths=True)

        # Should have all expected tiers
        assert len(loader.get_roles_by_tier("A")) >= 1
        assert len(loader.get_roles_by_tier("B")) >= 1
        assert len(loader.get_roles_by_tier("C")) >= 1
        assert len(loader.get_roles_by_tier("D")) >= 1

        # Key roles should exist
        assert "frontdoor" in loader.roles
        assert "coder_escalation" in loader.roles

    def test_production_coder_uses_current_baseline_acceleration(self):
        """Test coder_escalation matches the current shared-frontdoor baseline."""
        loader = RegistryLoader(validate_paths=True)

        role = loader.get_role("coder_escalation")
        assert role.acceleration is not None
        assert role.acceleration.type == "none"
        assert role.acceleration.lookup is False
        assert role.acceleration.corpus_retrieval is True

    def test_production_frontdoor_corpus_retrieval_matches_server_mode(self):
        """Prompt-builder role config should keep the live corpus path enabled."""
        loader = RegistryLoader(validate_paths=True)

        role = loader.get_role("frontdoor")
        assert role.acceleration is not None
        assert role.acceleration.lookup is False
        assert role.acceleration.corpus_retrieval is True

        corpus_config = loader.get_corpus_config()
        assert corpus_config["enabled"] is True
        assert corpus_config["min_score"] == 0.0
