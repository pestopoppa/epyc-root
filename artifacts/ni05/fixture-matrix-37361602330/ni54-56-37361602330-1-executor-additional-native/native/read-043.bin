#!/usr/bin/env python3
"""Load and validate the model registry for hierarchical orchestration.

This module provides typed access to model configurations, acceleration
strategies, and command generation for llama.cpp inference.

Usage:
    from src.registry_loader import RegistryLoader

    registry = RegistryLoader()
    role = registry.get_role("coder_escalation")
    cmd = registry.generate_command("coder_escalation", prompt="Write a function...")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default registry locations (static fallback; config preferred in __init__).
#
# 2026-08-01: both constants used to resolve to `src/orchestration/model_registry*.yaml`
# — `parent.parent` from `src/registry/` is `src/`, which is a Python package with no
# `orchestration/` directory. Neither file has ever existed, so
# `ORCHESTRATOR_REGISTRY_MODE=lean` raised RegistryError on every start.
#
# The real artifacts, and the single source of truth for their locations, live in
# `src/registry/model_descriptors.py` (also imported by
# `scripts/registry/stack_change_pipeline.py`):
#   * DEFAULT_RESEARCH_REGISTRY — the MASTER registry in epyc-inference-research.
#   * DEFAULT_LEAN_REGISTRY     — `<repo>/orchestration/model_registry.yaml`, the
#     lean runtime view that `src/registry/registry_compiler.py` compiles from the
#     master at every stack start.
# Re-exported here rather than restated so there is no fourth copy to drift.
from src.registry.model_descriptors import (  # noqa: E402
    DEFAULT_LEAN_REGISTRY as DEFAULT_LEAN_REGISTRY_PATH,
    DEFAULT_RESEARCH_REGISTRY as DEFAULT_REGISTRY_PATH,
)


@dataclass
class ModelConfig:
    """Model file configuration."""

    name: str
    path: str  # Relative to model_base_path
    quant: str
    size_gb: float
    full_path: str = ""  # Resolved absolute path
    architecture: str | None = None
    split_count: int | None = None
    mmproj_path: str | None = None


@dataclass
class AccelerationConfig:
    """Acceleration strategy configuration."""

    type: str  # speculative_decoding, moe_expert_reduction, prompt_lookup, self_speculation, hierarchical_speculation, none
    draft_role: str | None = None
    k: int | None = None  # Draft tokens for speculative
    experts: int | None = None  # Expert count for MoE reduction
    override_key: str | None = None
    ngram_min: int | None = None  # For prompt lookup
    lookup: bool = False  # Enable --lookup (prompt n-gram fallback)
    temperature: float | None = None
    corpus_retrieval: bool = False  # Enable corpus-augmented prompt stuffing
    n_layer_exit_draft: int | None = None  # Layer exit depth for self-speculation draft
    hierarchical_spec: bool = False  # Enable hierarchical intermediate verification
    n_layer_exit_intermediate: int | None = None  # Intermediate depth for HiSpec (0 = auto N/4)
    p_split: float | None = None  # Tree speculation branching threshold (--draft-p-split)


@dataclass
class PerformanceMetrics:
    """Performance metrics from benchmarks."""

    baseline_tps: float | None = None
    optimized_tps: float | None = None
    speedup: str | None = None
    acceptance_rate: str | None = None
    raw_tps: float | None = None


@dataclass(frozen=True)
class ResolvedTps:
    """A role's t/s prior with its provenance stated, not implied.

    NIB2-57a: the old read idiom ``performance.optimized_tps or
    performance.baseline_tps`` handed callers a bare float that could be the
    optimized measurement, an UNOPTIMIZED baseline standing in for a missing
    optimized_tps, or nothing at all — indistinguishable at the read site.
    That indistinguishability is what let four unmeasured priors drive the
    router for weeks (NIB2-57). This resolves the same numeric preference
    (optimized wins when present) but says which case held.
    """

    value: float | None
    source: str  # "optimized" | "baseline" | "unmeasured"

    @property
    def measured(self) -> bool:
        """True when a number exists at all (either measurement)."""
        return self.value is not None


def resolve_tps_prior(performance: PerformanceMetrics) -> ResolvedTps:
    """Resolve ``performance`` to its t/s prior with provenance.

    Numeric preference is identical to the historical ``optimized_tps or
    baseline_tps`` idiom; only the provenance is new. A role that has ONLY a
    baseline_tps now says so explicitly instead of being indistinguishable
    from one whose optimized_tps was measured, and a role with neither field
    resolves to ``source="unmeasured"`` — never to a fabricated number.

    Decision sites (routing, placement, prior selection) MUST check
    ``source`` before using the value; report-only consumers may read
    ``value`` directly.
    """
    if performance.optimized_tps is not None:
        return ResolvedTps(value=float(performance.optimized_tps), source="optimized")
    if performance.baseline_tps is not None:
        return ResolvedTps(value=float(performance.baseline_tps), source="baseline")
    return ResolvedTps(value=None, source="unmeasured")


def format_tps(performance: PerformanceMetrics) -> str:
    """Human-readable t/s for display sites (report-only consumers).

    A measured-optimized role renders exactly as before (``33.0 t/s``). A
    role whose only number is an unoptimized baseline_tps says so — that
    figure is NOT its achievable speed, and printing it bare is how the
    unmeasured-prior case stayed quiet. A role with no t/s prior renders
    ``unmeasured``, never a fabricated figure.
    """
    prior = resolve_tps_prior(performance)
    if prior.value is None:
        return "unmeasured"
    if prior.source == "baseline":
        return f"{prior.value} t/s (baseline, not optimized)"
    return f"{prior.value} t/s"


@dataclass
class MemoryConfig:
    """Memory residency configuration."""

    residency: str  # hot, warm
    pinned: bool = False
    max_instances: int = 1


@dataclass
class GenerationDefaults:
    """Default generation parameters for a role."""

    n_tokens: int = 512
    temperature: float | None = None  # None = use global default
    context_length: int | None = None


@dataclass
class Constraints:
    """Acceleration constraints for a role."""

    forbid: list[str] = field(default_factory=list)
    reason: str | None = None


@dataclass
class BackendConfig:
    """Backend routing configuration for a role.

    Supports routing to different inference backends:
    - local: llama.cpp (default for all existing roles)
    - anthropic: Anthropic Claude API
    - openai: OpenAI API (or compatible endpoints)
    """

    backend_type: str = "local"  # local, anthropic, openai
    api_model: str | None = None  # Model name for API backends (e.g., "claude-3-5-sonnet-20241022")
    fallback_role: str | None = None  # Local role to fall back to if API unavailable


@dataclass
class RoleConfig:
    """Complete configuration for an agent role."""

    name: str
    tier: str
    description: str
    model: ModelConfig
    acceleration: AccelerationConfig
    performance: PerformanceMetrics
    memory: MemoryConfig
    constraints: Constraints | None = None
    compatible_targets: list[str] = field(default_factory=list)
    notes: str | None = None
    generation_defaults: GenerationDefaults | None = None
    system_prompt_suffix: str | None = None
    backend_config: BackendConfig = field(default_factory=BackendConfig)


@dataclass
class RoutingHint:
    """Deterministic routing rule."""

    condition: str
    use: list[str]


@dataclass
class EscalationChain:
    """Escalation chain configuration."""

    name: str
    description: str
    chain: list[str]  # Ordered list of role names
    triggers: list[dict[str, Any]] = field(default_factory=list)
    max_escalations: int = 2

    def get_next_role(self, current_role: str) -> str | None:
        """Get the next role in the escalation chain.

        Args:
            current_role: The role that failed/needs escalation.

        Returns:
            The next role in the chain, or None if at end.
        """
        try:
            idx = self.chain.index(current_role)
            if idx < len(self.chain) - 1:
                return self.chain[idx + 1]
        except ValueError:
            pass
        return None

    def get_chain_for_role(self, role: str) -> list[str] | None:
        """Get the remaining chain starting from a role.

        Args:
            role: The starting role.

        Returns:
            List of roles from this point forward, or None if not in chain.
        """
        try:
            idx = self.chain.index(role)
            return self.chain[idx:]
        except ValueError:
            return None


class RegistryError(Exception):
    """Error loading or validating the registry."""

    pass


class RegistryLoader:
    """Load and provide access to the model registry."""

    def __init__(
        self,
        registry_path: Path | str | None = None,
        validate_paths: bool = True,
        allow_missing: bool = False,
    ):
        """Initialize the registry loader.

        Args:
            registry_path: Path to model_registry.yaml. Uses default if None.
            validate_paths: If True, verify model files exist on disk.
            allow_missing: If True, don't error if registry file doesn't exist.
        """
        self._allow_missing = allow_missing
        if registry_path is not None:
            self.registry_path = Path(registry_path)
        else:
            import os

            registry_mode = os.environ.get("ORCHESTRATOR_REGISTRY_MODE", "full")
            if registry_mode == "lean":
                self.registry_path = DEFAULT_LEAN_REGISTRY_PATH
                logger.info("Using lean registry: %s", self.registry_path)
            else:
                try:
                    from src.config import get_config

                    self.registry_path = get_config().paths.registry_path
                except Exception as e:
                    logger.debug("Config unavailable, using default registry path: %s", e)
                    self.registry_path = DEFAULT_REGISTRY_PATH
        self._raw: dict[str, Any] = {}
        self._roles: dict[str, RoleConfig] = {}
        self._routing_hints: list[RoutingHint] = []
        self._command_templates: dict[str, str] = {}
        self._escalation_chains: dict[str, EscalationChain] = {}
        try:
            from src.config import get_config

            self._model_base_path: Path = get_config().paths.model_base
        except Exception as e:
            logger.debug("Config unavailable, using default model base path: %s", e)
            self._model_base_path: Path = Path("/mnt/raid0/llm/models")
        self._runtime_defaults: dict[str, Any] = {}
        self._missing_models: list[str] = []

        self._load(validate_paths)

    def _load(self, validate_paths: bool) -> None:
        """Load and parse the registry YAML."""
        if not self.registry_path.exists():
            if self._allow_missing:
                # Return empty registry without error (for testing/CI)
                return
            raise RegistryError(f"Registry not found: {self.registry_path}")

        try:
            with self.registry_path.open("r", encoding="utf-8") as f:
                self._raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise RegistryError(f"Invalid YAML in registry: {e}") from e

        if not self._raw:
            raise RegistryError("Empty registry file")

        # Load runtime defaults
        self._runtime_defaults = self._raw.get("runtime_defaults", {})
        base_path = self._runtime_defaults.get("model_base_path")
        if base_path:
            self._model_base_path = Path(base_path)

        # Load roles
        roles_data = self._raw.get("roles", {})
        if not roles_data:
            raise RegistryError("No roles defined in registry")

        for role_name, role_data in roles_data.items():
            try:
                role_config = self._parse_role(role_name, role_data)
                if validate_paths:
                    self._validate_model_path(role_config)
                self._roles[role_name] = role_config
            except Exception as e:
                raise RegistryError(f"Error parsing role '{role_name}': {e}") from e

        # Load routing hints
        hints_data = self._raw.get("routing_hints", [])
        for hint in hints_data:
            self._routing_hints.append(
                RoutingHint(
                    condition=hint.get("if", ""),
                    use=hint.get("use", []),
                )
            )

        # Load command templates
        self._command_templates = self._raw.get("command_templates", {})

        # Load escalation chains
        chains_data = self._raw.get("escalation_chains", {})
        for chain_name, chain_data in chains_data.items():
            self._escalation_chains[chain_name] = EscalationChain(
                name=chain_name,
                description=chain_data.get("description", ""),
                chain=chain_data.get("chain", []),
                triggers=chain_data.get("triggers", []),
                max_escalations=chain_data.get("max_escalations", 2),
            )

    def _parse_role(self, name: str, data: dict[str, Any]) -> RoleConfig:
        """Parse a role configuration from YAML data."""
        model_data = data.get("model", {})
        accel_data = data.get("acceleration", {})
        perf_data = data.get("performance", {})
        mem_data = data.get("memory", {})
        constraints_data = data.get("constraints")

        # Build model config
        model = ModelConfig(
            name=model_data.get("name", ""),
            path=model_data.get("path", ""),
            quant=model_data.get("quant", "Q4_K_M"),
            size_gb=model_data.get("size_gb", 0.0),
            architecture=model_data.get("architecture"),
            split_count=model_data.get("split_count"),
            mmproj_path=model_data.get("mmproj_path"),
        )

        # Resolve full path
        if model.path:
            model.full_path = str(self._model_base_path / model.path)

        # Build acceleration config
        # Support MoE + spec decode combo: if moe_expert_reduction has a
        # speculative_decoding sub-config, populate draft_role and k from it
        draft_role = accel_data.get("draft_role")
        draft_k = accel_data.get("k")
        spec_sub = accel_data.get("speculative_decoding", {})
        if spec_sub:
            draft_role = draft_role or spec_sub.get("draft_role")
            draft_k = draft_k or spec_sub.get("k")
        # Resolve lookup flag: check spec_sub first, then top-level
        lookup = spec_sub.get("lookup", accel_data.get("lookup", False))
        # Resolve corpus_retrieval: check runtime_defaults, then accel_data
        corpus_rt = self._runtime_defaults.get("corpus_retrieval", {})
        corpus_enabled = accel_data.get(
            "corpus_retrieval",
            corpus_rt.get("enabled", False) if bool(lookup) else False,
        )
        acceleration = AccelerationConfig(
            type=accel_data.get("type", "none"),
            draft_role=draft_role,
            k=draft_k,
            experts=accel_data.get("experts"),
            override_key=accel_data.get("override_key"),
            ngram_min=accel_data.get("ngram_min", 3),
            lookup=bool(lookup),
            temperature=accel_data.get("temperature"),
            corpus_retrieval=bool(corpus_enabled),
            p_split=accel_data.get("p_split"),
        )

        # Build performance metrics
        performance = PerformanceMetrics(
            baseline_tps=perf_data.get("baseline_tps"),
            optimized_tps=perf_data.get("optimized_tps"),
            speedup=perf_data.get("speedup"),
            acceptance_rate=perf_data.get("acceptance_rate"),
            raw_tps=perf_data.get("raw_tps"),
        )

        # Build memory config
        memory = MemoryConfig(
            residency=mem_data.get("residency", "warm"),
            pinned=mem_data.get("pinned", False),
            max_instances=mem_data.get("max_instances", 1),
        )

        # Build constraints
        constraints = None
        if constraints_data:
            constraints = Constraints(
                forbid=constraints_data.get("forbid", []),
                reason=constraints_data.get("reason"),
            )

        # Build generation defaults
        gen_defaults = None
        gen_data = data.get("generation_defaults")
        if gen_data:
            gen_defaults = GenerationDefaults(
                n_tokens=gen_data.get("n_tokens", 512),
                temperature=gen_data.get("temperature"),
                context_length=gen_data.get("context_length"),
            )

        # Build backend config
        backend_data = data.get("backend", {})
        backend_config = BackendConfig(
            backend_type=backend_data.get("type", "local"),
            api_model=backend_data.get("api_model"),
            fallback_role=backend_data.get("fallback_role"),
        )

        return RoleConfig(
            name=name,
            tier=data.get("tier", "C"),
            description=data.get("description", ""),
            model=model,
            acceleration=acceleration,
            performance=performance,
            memory=memory,
            constraints=constraints,
            compatible_targets=data.get("compatible_targets", []),
            notes=data.get("notes"),
            generation_defaults=gen_defaults,
            system_prompt_suffix=data.get("system_prompt_suffix"),
            backend_config=backend_config,
        )

    def _validate_model_path(self, role: RoleConfig) -> None:
        """Check if model file exists, record missing models."""
        if not role.model.full_path:
            return
        path = Path(role.model.full_path)
        if not path.exists():
            self._missing_models.append(f"{role.name}: {role.model.full_path}")

    @property
    def roles(self) -> dict[str, RoleConfig]:
        """All loaded role configurations."""
        return self._roles

    @property
    def routing_hints(self) -> list[RoutingHint]:
        """Deterministic routing rules."""
        return self._routing_hints

    @property
    def missing_models(self) -> list[str]:
        """List of roles with missing model files."""
        return self._missing_models

    @property
    def model_base_path(self) -> Path:
        """Base path for model files."""
        return self._model_base_path

    def get_role(self, name: str) -> RoleConfig:
        """Get configuration for a specific role.

        Raises:
            KeyError: If role not found.
        """
        if name not in self._roles:
            raise KeyError(f"Role not found: {name}. Available: {list(self._roles.keys())}")
        return self._roles[name]

    def get_roles_by_tier(self, tier: str) -> list[RoleConfig]:
        """Get all roles in a specific tier (A, B, C, D)."""
        return [r for r in self._roles.values() if r.tier == tier]

    def get_draft_for_role(self, role_name: str) -> RoleConfig | None:
        """Get the draft model configuration for a role using speculative decoding.

        Supports both pure spec decode roles and MoE+spec combo roles
        (e.g., 480B with expert reduction + jukofyork draft).
        """
        role = self.get_role(role_name)
        draft_role = role.acceleration.draft_role
        if draft_role and draft_role in self._roles:
            return self._roles[draft_role]
        return None

    def get_role_defaults(self, role_name: str) -> tuple[int, float | None, str | None]:
        """Get generation defaults for a role.

        Args:
            role_name: The role to get defaults for.

        Returns:
            Tuple of (n_tokens, temperature, system_prompt_suffix).
            Falls back to (-1, None, None) if role not found (-1 = unlimited).
        """
        try:
            role = self.get_role(role_name)
            if role.generation_defaults:
                return (
                    role.generation_defaults.n_tokens,
                    role.generation_defaults.temperature,
                    role.system_prompt_suffix,
                )
            return (-1, None, role.system_prompt_suffix)
        except KeyError:
            return (-1, None, None)

    def get_role_chat_template_kwargs(self, role_name: str) -> dict[str, Any] | None:
        """Per-role Jinja chat-template kwargs (e.g. {enable_thinking: False}), or
        None if the role declares none. Read from the `server_mode.<role>` block
        (where the deployment-time chat-template config lives), NOT the `roles`
        section. Backends auto-inject this into request.extra["chat_template_kwargs"]
        when the caller hasn't set it explicitly (J12)."""
        sm = (self._raw.get("server_mode") or {}).get(role_name)
        if isinstance(sm, dict):
            ctk = sm.get("chat_template_kwargs")
            if isinstance(ctk, dict) and ctk:
                return ctk
        return None

    @property
    def escalation_chains(self) -> dict[str, EscalationChain]:
        """Get all escalation chains."""
        return self._escalation_chains

    def get_escalation_chain(self, name: str) -> EscalationChain | None:
        """Get an escalation chain by name."""
        return self._escalation_chains.get(name)

    def get_chain_for_role(self, role_name: str) -> EscalationChain | None:
        """Find the escalation chain that contains a role.

        Args:
            role_name: The role to look up.

        Returns:
            The escalation chain containing this role, or None.
        """
        for chain in self._escalation_chains.values():
            if role_name in chain.chain:
                return chain
        return None

    def get_escalation_target(self, role_name: str) -> str | None:
        """Get the next escalation target for a role.

        Args:
            role_name: The current role.

        Returns:
            The next role in the escalation chain, or None if at end or not in chain.
        """
        chain = self.get_chain_for_role(role_name)
        if chain:
            return chain.get_next_role(role_name)
        return None

    def get_roles_by_backend(self, backend_type: str) -> list[RoleConfig]:
        """Get all roles using a specific backend type.

        Args:
            backend_type: The backend type (local, anthropic, openai).

        Returns:
            List of roles configured for that backend.
        """
        return [r for r in self._roles.values() if r.backend_config.backend_type == backend_type]

    def get_local_roles(self) -> list[RoleConfig]:
        """Get all roles using local llama.cpp inference."""
        return self.get_roles_by_backend("local")

    def get_external_roles(self) -> list[RoleConfig]:
        """Get all roles using external API backends (anthropic, openai)."""
        return [
            r
            for r in self._roles.values()
            if r.backend_config.backend_type in ("anthropic", "openai")
        ]

    def get_fallback_role(self, role_name: str) -> RoleConfig | None:
        """Get the local fallback role for an external API role.

        Args:
            role_name: The role to get fallback for.

        Returns:
            The fallback RoleConfig, or None if no fallback configured.
        """
        role = self.get_role(role_name)
        fallback_name = role.backend_config.fallback_role
        if fallback_name and fallback_name in self._roles:
            return self._roles[fallback_name]
        return None

    def get_timeout(
        self,
        key: str,
        category: str = "roles",
    ) -> int | float:
        """Get a timeout value from the registry.

        Single source of truth for all timeouts in the system.

        Args:
            key: The timeout key (e.g., "architect_general", "request", "warm_keepalive").
            category: The timeout category: "roles", "server", "services", "pools", "benchmark".
                     Default is "roles" for per-role inference timeouts.

        Returns:
            Timeout value in seconds. Falls back to runtime_defaults.timeouts.default (600).

        Examples:
            registry.get_timeout("architect_general")  # Role timeout
            registry.get_timeout("request", "server")  # Server request timeout
            registry.get_timeout("warm_keepalive", "pools")  # Pool timeout
        """
        timeouts = self._runtime_defaults.get("timeouts", {})
        default = timeouts.get("default", 600)

        # Look up in specified category
        category_timeouts = timeouts.get(category, {})
        if key in category_timeouts:
            return category_timeouts[key]

        # Fall back to default
        return default

    def generate_command(
        self,
        role_name: str,
        prompt: str | None = None,
        prompt_file: str | None = None,
        n_tokens: int = 128,
        extra_args: dict[str, Any] | None = None,
    ) -> str:
        """Generate a llama.cpp command for a role.

        Args:
            role_name: The role to generate a command for.
            prompt: Inline prompt text.
            prompt_file: Path to prompt file (overrides prompt).
            n_tokens: Number of tokens to generate.
            extra_args: Additional arguments to append.

        Returns:
            Shell command string.
        """
        role = self.get_role(role_name)
        accel_type = role.acceleration.type

        # Get template
        template_name = accel_type if accel_type != "none" else "baseline"
        if template_name not in self._command_templates:
            template_name = "baseline"
        template = self._command_templates.get(template_name, "")

        # Build substitution dict
        defaults = self._runtime_defaults
        subs = {
            "model_path": role.model.full_path,
            "threads": defaults.get("threads", 96),
            "context_length": defaults.get("context_length", 8192),
        }

        # Add acceleration-specific params
        if accel_type == "speculative_decoding":
            draft = self.get_draft_for_role(role_name)
            if draft:
                subs["draft_path"] = draft.model.full_path
            subs["k"] = role.acceleration.k or 16

        elif accel_type == "moe_expert_reduction":
            subs["override_key"] = role.acceleration.override_key or "moe_n_expert"
            subs["experts"] = role.acceleration.experts or 4

        elif accel_type == "prompt_lookup":
            subs["ngram_min"] = role.acceleration.ngram_min or 3

        # Vision model
        if role.model.mmproj_path:
            subs["mmproj_path"] = str(self._model_base_path / role.model.mmproj_path)
            template_name = "vision"
            template = self._command_templates.get("vision", template)

        # Apply substitutions
        cmd = template.strip()
        for key, value in subs.items():
            cmd = cmd.replace(f"{{{key}}}", str(value))

        # Add prompt
        if prompt_file:
            cmd += f" \\\n      -f {prompt_file}"
        elif prompt:
            # Escape for shell
            safe_prompt = prompt.replace("'", "'\\''")
            cmd += f" \\\n      -p '{safe_prompt}'"

        # Add token count and common flags
        cmd += f" \\\n      -n {n_tokens}"
        cmd += " \\\n      --no-display-prompt"
        cmd += " \\\n      --simple-io"

        # Add extra args
        if extra_args:
            for k, v in extra_args.items():
                cmd += f" \\\n      --{k} {v}"

        return cmd

    def route_task(self, task_ir: dict[str, Any]) -> list[str]:
        """Determine which roles to use based on TaskIR.

        Uses the routing_hints from the registry to match task properties.
        Supports backend_preference to filter by backend type.

        Args:
            task_ir: Parsed TaskIR JSON. May include:
                - backend_preference: "local", "anthropic", or "openai"
                  to filter roles by backend type

        Returns:
            List of role names to use.
        """
        # Extract relevant fields for matching
        task_type = task_ir.get("task_type", "")
        priority = task_ir.get("priority", "batch")
        objective = task_ir.get("objective", "").lower()
        constraints = [c.lower() for c in task_ir.get("constraints", [])]
        inputs = task_ir.get("inputs", [])
        input_types = [i.get("type", "") for i in inputs]
        escalation = task_ir.get("escalation", {})
        backend_preference = task_ir.get("backend_preference")

        # Check each routing hint
        matched_roles: list[str] = []
        for hint in self._routing_hints:
            condition = hint.condition

            # Simple condition evaluation (not a full expression parser)
            # Supports: task_type == 'x', priority == 'x', 'x' in objective, etc.
            try:
                # Build evaluation context
                ctx = {
                    "task_type": task_type,
                    "priority": priority,
                    "objective": objective,
                    "constraints": constraints,
                    "inputs": input_types,
                    "escalation": escalation,
                }

                # Evaluate condition (limited, safe subset)
                if self._eval_condition(condition, ctx):
                    matched_roles = hint.use
                    break
            except Exception as e:
                logger.debug("Routing condition eval failed for '%s': %s", condition, e)
                continue

        # Default: frontdoor only
        if not matched_roles:
            matched_roles = ["frontdoor"]

        # Filter by backend preference if specified
        if backend_preference:
            filtered = [
                role_name
                for role_name in matched_roles
                if role_name in self._roles
                and self._roles[role_name].backend_config.backend_type == backend_preference
            ]
            # Fall back to matched roles if no backend match
            if filtered:
                return filtered

        return matched_roles

    def _eval_condition(self, condition: str, ctx: dict[str, Any]) -> bool:
        """Safely evaluate a routing condition.

        Supports limited expressions like:
        - task_type == 'code'
        - 'refactor' in objective
        - priority == 'interactive' and task_type == 'chat'
        """
        # Handle 'and' by splitting
        if " and " in condition:
            parts = condition.split(" and ")
            return all(self._eval_condition(p.strip(), ctx) for p in parts)

        # Handle 'or'
        if " or " in condition:
            parts = condition.split(" or ")
            return any(self._eval_condition(p.strip(), ctx) for p in parts)

        # Handle equality: x == 'y'
        eq_match = re.match(r"(\w+(?:\.\w+)?)\s*==\s*['\"]([^'\"]+)['\"]", condition)
        if eq_match:
            key, value = eq_match.groups()
            actual = self._get_nested(ctx, key)
            return actual == value

        # Handle 'x' in y
        in_match = re.match(r"['\"]([^'\"]+)['\"]\s+in\s+(\w+)", condition)
        if in_match:
            needle, key = in_match.groups()
            haystack = ctx.get(key, "")
            if isinstance(haystack, str):
                return needle in haystack
            if isinstance(haystack, list):
                return needle in haystack
            return False

        return False

    def _get_nested(self, ctx: dict[str, Any], key: str) -> Any:
        """Get a potentially nested value from context (e.g., 'escalation.max_level')."""
        parts = key.split(".")
        value = ctx
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def get_corpus_config(self) -> dict[str, Any]:
        """Get corpus retrieval config from runtime_defaults.

        Returns dict with keys: enabled, index_path, max_snippets, max_chars,
        rag_enabled, rag_roles.
        """
        return dict(self._runtime_defaults.get("corpus_retrieval", {}))

    def summary(self) -> str:
        """Return a summary of loaded roles."""
        lines = [
            f"Registry: {self.registry_path}",
            f"Base path: {self._model_base_path}",
            f"Roles loaded: {len(self._roles)}",
            "",
        ]

        for tier in ["A", "B", "C", "D"]:
            tier_roles = self.get_roles_by_tier(tier)
            if tier_roles:
                lines.append(f"Tier {tier}:")
                for r in tier_roles:
                    status = (
                        "OK"
                        if r.model.full_path and Path(r.model.full_path).exists()
                        else "MISSING"
                    )
                    lines.append(f"  {r.name}: {r.model.name} [{status}]")
                lines.append("")

        if self._missing_models:
            lines.append("Missing models:")
            for m in self._missing_models:
                lines.append(f"  {m}")

        return "\n".join(lines)


def main() -> int:
    """CLI entry point for testing."""
    import sys

    try:
        loader = RegistryLoader(validate_paths=True)
        print(loader.summary())

        if loader.missing_models:
            print(f"\nWarning: {len(loader.missing_models)} model(s) not found on disk")
            return 1

        print("\nAll models validated successfully.")
        return 0

    except RegistryError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


# ── Cached module-level accessor (J12) ───────────────────────────────
# Lets a backend auto-inject per-role chat_template_kwargs without threading a
# RegistryLoader handle through every call site. Lazily loads the default
# registry once (validate_paths=False — read-only metadata lookup).
_CTK_LOADER: "RegistryLoader | None" = None


def chat_template_kwargs_for_role(role_name: str) -> dict[str, Any] | None:
    """Per-role chat_template_kwargs from the default registry, or None.

    Cached + fail-soft: any load/lookup error returns None (no injection),
    so a missing/invalid registry never breaks inference.
    """
    global _CTK_LOADER
    if _CTK_LOADER is None:
        try:
            _CTK_LOADER = RegistryLoader(validate_paths=False)
        except Exception:
            return None
    try:
        return _CTK_LOADER.get_role_chat_template_kwargs(role_name)
    except Exception:
        return None


# ── Serving-host resolution (server_mode) ────────────────────────────
# A role either owns a llama-server process (a `server_mode` row without
# `alias_of`) or rides one: it is listed in a host row's `shared_with`, or it
# is an `alias_of` row. After the operator-signed 2026-09-22 lineup cutover
# most roles ride another role's process, so any per-role fact that is really a
# per-PROCESS fact (model, layer count, tier, fallback target) must be resolved
# through this map instead of restated per role.


def load_server_mode(registry_path: Path | str | None = None) -> dict[str, Any]:
    """The ``server_mode`` section of the runtime registry.

    Defaults to the configured registry path (the lean runtime view,
    ``orchestration/model_registry.yaml``), falling back to
    ``DEFAULT_LEAN_REGISTRY_PATH`` when config is unavailable. Raises
    ``RegistryError`` if the file is missing or has no usable section.
    """
    if registry_path is None:
        try:
            from src.config import get_config

            registry_path = get_config().paths.registry_path
        except Exception:
            registry_path = DEFAULT_LEAN_REGISTRY_PATH
    path = Path(registry_path)
    if not path.exists():
        raise RegistryError(f"Registry not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    server_mode = raw.get("server_mode") if isinstance(raw, dict) else None
    if not isinstance(server_mode, dict) or not server_mode:
        raise RegistryError(f"registry {path} has no usable server_mode section")
    return server_mode


def serving_host_rows(server_mode: dict[str, Any]) -> list[str]:
    """``server_mode`` rows that own a process of their own, in declaration order."""
    return [
        name
        for name, row in server_mode.items()
        if isinstance(row, dict) and not row.get("alias_of")
    ]


def serving_host_by_role(server_mode: dict[str, Any]) -> dict[str, str]:
    """Map every role the registry binds to the host row whose process serves it.

    Hosts map to themselves; ``shared_with`` members and ``alias_of`` rows map
    to their host (``alias_of`` chains are followed). A role the registry does
    not mention is absent from the result.
    """
    hosts = serving_host_rows(server_mode)
    out: dict[str, str] = {host: host for host in hosts}
    for host in hosts:
        for member in server_mode[host].get("shared_with") or []:
            out.setdefault(str(member), host)
    for name, row in server_mode.items():
        if not isinstance(row, dict) or not row.get("alias_of"):
            continue
        target, seen = str(row["alias_of"]), {name}
        while target not in out and target not in seen:
            seen.add(target)
            nxt = server_mode.get(target)
            if not isinstance(nxt, dict) or not nxt.get("alias_of"):
                break
            target = str(nxt["alias_of"])
        if target in out:
            out.setdefault(name, out[target])
    return out


if __name__ == "__main__":
    import sys

    sys.exit(main())
