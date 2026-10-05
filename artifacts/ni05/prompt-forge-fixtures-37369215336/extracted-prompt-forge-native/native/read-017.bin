"""Constants, dataclasses, and shared state for the seeding evaluation suite.

Generated stack priors are the primary source for live role metadata, with the
model registry kept as the degraded/offline fallback. Project imports are kept
local so this module remains usable from benchmark entrypoints with minimal
startup coupling.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

__all__ = [
    "ARCHITECT_MODES", "ARCHITECT_ROLES", "ComparativeResult",
    "DEBUG_PROMPTS_DIR", "DEFAULT_MODES", "DEFAULT_ORCHESTRATOR_URL",
    "DEFAULT_ROLES", "DEFAULT_SUITES", "DEFAULT_TIMEOUT",
    "ESCALATION_REWARD", "EVAL_DIR", "HEAVY_PORTS",
    "HealthCheckError", "MODEL_PORTS", "PROJECT_ROOT",
    "ROLE_COST_TIER", "ROLE_PORT", "RoleResult",
    "SEEN_FILE", "STACK_SCRIPT",
    "VISION_MODES", "VISION_ROLES", "WebResearchTelemetry", "state",
    # Phase 4: 3-way routing action keys
    "ACTION_SELF_DIRECT", "ACTION_SELF_REPL", "ACTION_ARCHITECT", "ACTION_WORKER",
    "THREE_WAY_ACTIONS", "THREE_WAY_COST_TIER",
    # Phase 5: dynamic per-role discovery
    "SEEDING_EXCLUDED_ROLES", "discover_active_roles",
]


# ── Path constants ────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.parent
RESEARCH_ROOT = Path(os.environ.get(
    "EPYC_RESEARCH_ROOT", "/mnt/raid0/llm/epyc-inference-research"
))
STACK_PRIORS_PATH = PROJECT_ROOT / "orchestration" / "derived" / "stack_priors.yaml"
STACK_PRIOR_SEEDING_EXCLUDED_ROLES = frozenset({
    "toolrunner", "worker_math", "worker_summarize",
})
SEEDING_EXCLUDED_ROLES = frozenset({
    "voice_server", "document_formalizer",
    "nextplaid_code", "nextplaid_docs",
    "dev", "reap_25b",
})
HEAVY_MODEL_MEM_GB_THRESHOLD = 18.0
_COST_TIER_1_MAX_MEM_GB = 18.0
_COST_TIER_2_MAX_MEM_GB = 40.0

EVAL_DIR = RESEARCH_ROOT / "benchmarks" / "results" / "eval"
SEEN_FILE = EVAL_DIR / "seen_questions.jsonl"
DEBUG_PROMPTS_DIR = RESEARCH_ROOT / "benchmarks" / "prompts" / "debug"


# ── Registry timeout reader (no project imports) ──────────────────────

def _read_registry_timeout(category: str, key: str, fallback: int) -> int:
    """Read timeout from model_registry.yaml without project imports."""
    registry_path = PROJECT_ROOT / "orchestration" / "model_registry.yaml"
    try:
        with registry_path.open() as f:
            data = yaml.safe_load(f)
        timeouts = data.get("runtime_defaults", {}).get("timeouts", {})
        cat_data = timeouts.get(category, {})
        return cat_data.get(key, timeouts.get("default", fallback))
    except Exception:
        return fallback


def _load_live_stack_prior_roles(
    stack_priors_path: Path = STACK_PRIORS_PATH,
) -> dict[str, dict[str, Any]]:
    """Return live stack-prior role records keyed by role name."""
    try:
        from src.registry.stack_priors import live_stack_role_records
    except ImportError:
        return {}

    return dict(sorted(live_stack_role_records(stack_priors_path).items()))


def _read_stack_prior_default_roles(
    stack_priors_path: Path = STACK_PRIORS_PATH,
) -> list[str]:
    """Read live seeding defaults from generated stack priors.

    This module intentionally avoids project imports, so the generated YAML is
    the lightest safe interface for keeping CLI defaults aligned with stack
    changes.
    """
    active: list[str] = []
    for role_name, record in _load_live_stack_prior_roles(stack_priors_path).items():
        if role_name in STACK_PRIOR_SEEDING_EXCLUDED_ROLES:
            continue
        serving = record.get("serving")
        if not isinstance(serving, dict) or not serving.get("endpoint"):
            continue
        active.append(str(role_name))
    return active


def _cost_tier_from_stack_priors(role_name: str, record: dict[str, Any]) -> int:
    role_name = _canonical_role_name(role_name)
    model = record.get("model")
    mem_gb = model.get("mem_gb") if isinstance(model, dict) else None
    model_mem_tier = _cost_tier_from_model_mem(mem_gb)
    if model_mem_tier is not None:
        return model_mem_tier

    priors = record.get("priors")
    memory_cost = priors.get("memory_cost") if isinstance(priors, dict) else None
    try:
        cost = float(memory_cost)
    except (TypeError, ValueError):
        return ROLE_COST_TIER.get(role_name, 3)
    if cost <= 1.0:
        return ROLE_COST_TIER.get(role_name, 2)
    if cost <= 2.0:
        return 3
    return 4


def _cost_tier_from_model_mem(mem_gb: Any) -> int | None:
    try:
        mem = float(mem_gb)
    except (TypeError, ValueError):
        return None
    if mem <= _COST_TIER_1_MAX_MEM_GB:
        return 1
    if mem <= _COST_TIER_2_MAX_MEM_GB:
        return 2
    return 4


def _read_stack_prior_active_roles(
    stack_priors_path: Path = STACK_PRIORS_PATH,
) -> list[dict[str, Any]]:
    """Read active seeding role metadata from generated stack priors."""
    active: list[dict[str, Any]] = []
    for role_name, record in _load_live_stack_prior_roles(stack_priors_path).items():
        if (
            role_name in STACK_PRIOR_SEEDING_EXCLUDED_ROLES
            or role_name in SEEDING_EXCLUDED_ROLES
        ):
            continue
        serving = record.get("serving")
        if not isinstance(serving, dict) or not serving.get("endpoint"):
            continue
        ports = serving.get("ports")
        port = None
        if isinstance(ports, list):
            for candidate in ports:
                if isinstance(candidate, int):
                    port = candidate
                    break
        if port is None:
            raw_port = serving.get("port") or serving.get("primary_port")
            if isinstance(raw_port, int):
                port = raw_port
        if port is None:
            continue

        # Heaviness is a property of the model this record declares, not of a
        # port number: shared runtimes re-alias ports between lineups. Derive it
        # from the record we just read (same rule as _read_stack_prior_topology)
        # and only fall back to the module-level HEAVY_PORTS snapshot when the
        # record carries no model memory footprint.
        model = record.get("model")
        mem_gb = model.get("mem_gb") if isinstance(model, dict) else None
        try:
            is_heavy = float(mem_gb) >= HEAVY_MODEL_MEM_GB_THRESHOLD
        except (TypeError, ValueError):
            is_heavy = port in HEAVY_PORTS

        canonical_role_name = _canonical_role_name(str(role_name))
        active.append({
            "name": canonical_role_name,
            "registry_key": str(serving.get("server_role") or role_name),
            "model_role": canonical_role_name,
            "port": port,
            "is_heavy": is_heavy,
            "cost_tier": _cost_tier_from_stack_priors(canonical_role_name, record),
            "timeout_s": _read_registry_timeout("roles", canonical_role_name, DEFAULT_TIMEOUT),
        })

    active.sort(key=lambda r: r["cost_tier"])
    return active


def _primary_port_from_serving(serving: dict[str, Any]) -> int | None:
    endpoint = serving.get("endpoint")
    if isinstance(endpoint, str):
        port = urlparse(endpoint).port
        if port is not None:
            return port

    launch = serving.get("launch")
    entries = launch.get("entries") if isinstance(launch, dict) else None
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("alias"):
                continue
            port = entry.get("port")
            if isinstance(port, int):
                return port

    ports = serving.get("ports")
    if isinstance(ports, list):
        for port in ports:
            if isinstance(port, int):
                return port
    return None


# Map registry keys to the role names the orchestrator accepts for force_role.
# Most keys match directly; add entries here only for mismatches.
# When renaming roles, update this mapping.
_REGISTRY_KEY_TO_ROLE = {
    "worker": "worker_general",
}


def _canonical_role_name(role_name: str) -> str:
    try:
        from src.roles import Role
    except ImportError:
        return role_name
    canonical = Role.from_string(role_name)
    return canonical.value if canonical is not None else role_name


def _read_stack_prior_topology(
    stack_priors_path: Path = STACK_PRIORS_PATH,
) -> dict[str, Any]:
    """Read benchmark topology constants from generated stack priors."""
    role_port: dict[str, int] = {}
    model_ports: set[int] = set()
    heavy_ports: set[int] = set()
    for role_name, record in _load_live_stack_prior_roles(stack_priors_path).items():
        serving = record.get("serving")
        if not isinstance(serving, dict):
            continue
        port = _primary_port_from_serving(serving)
        if port is None:
            continue
        role_port[role_name] = port
        model_ports.add(port)

        model = record.get("model")
        mem_gb = model.get("mem_gb") if isinstance(model, dict) else None
        try:
            is_heavy = float(mem_gb) >= HEAVY_MODEL_MEM_GB_THRESHOLD
        except (TypeError, ValueError):
            is_heavy = False
        if is_heavy:
            heavy_ports.add(port)

    if not role_port:
        return {}
    return {
        "role_port": role_port,
        "heavy_ports": heavy_ports,
        "model_ports": sorted(model_ports),
    }


def _read_registry_topology(
    registry_path: Path | None = None,
) -> dict[str, Any]:
    """Read degraded benchmark topology from the lean model registry.

    Generated stack priors remain primary. This fallback exists for broken or
    unavailable generated artifacts and avoids preserving a separate role/port
    table in the benchmark harness.
    """
    registry_path = registry_path or PROJECT_ROOT / "orchestration" / "model_registry.yaml"
    try:
        with registry_path.open() as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return {}

    roles_section = data.get("server_mode", {})
    if not isinstance(roles_section, dict):
        return {}

    role_port: dict[str, int] = {}
    role_cost_tier: dict[str, int] = {}
    model_ports: set[int] = set()
    heavy_ports: set[int] = set()

    for role_key, role_def in roles_section.items():
        if not isinstance(role_key, str) or not isinstance(role_def, dict):
            continue
        if role_key in SEEDING_EXCLUDED_ROLES:
            continue
        if "model" not in role_def and "model_type" not in role_def:
            continue
        model_type = role_def.get("model_type", "gguf")
        if model_type not in ("gguf", "gguf_vlm"):
            continue

        role_name = _canonical_role_name(_REGISTRY_KEY_TO_ROLE.get(role_key, role_key))
        port = role_def.get("port")
        if not isinstance(port, int):
            continue

        role_port[role_name] = port
        model_ports.add(port)

        mem_gb = role_def.get("memory_gb")
        try:
            if float(mem_gb) >= HEAVY_MODEL_MEM_GB_THRESHOLD:
                heavy_ports.add(port)
        except (TypeError, ValueError):
            pass

        tier = _cost_tier_from_model_mem(mem_gb)
        if tier is not None:
            role_cost_tier[role_name] = tier

    if not role_port:
        return {}
    return {
        "role_port": role_port,
        "role_cost_tier": role_cost_tier,
        "heavy_ports": heavy_ports,
        "model_ports": sorted(model_ports),
    }


# ── Orchestrator defaults ─────────────────────────────────────────────

DEFAULT_ORCHESTRATOR_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = _read_registry_timeout("benchmark", "seeding_default", 600)
DEFAULT_SUITES = [
    # Hard benchmarks first (most routing signal, biggest mode differences)
    "gpqa", "usaco", "livecodebench", "debugbench",
    "mode_advantage_hard", "math",
    # Medium difficulty
    "hotpotqa", "simpleqa", "agentic", "skill_transfer", "coder",
    "long_context", "mode_advantage",
    # Easier / format-focused suites last
    "thinking", "general", "instruction_precision",
    "vl", "tool_compliance",
]
_EMERGENCY_DEFAULT_ROLES_FALLBACK = ["frontdoor"]


def _discover_default_roles_fallback() -> list[str]:
    """Return a non-blank default role order when stack priors are missing."""
    discovered = discover_active_roles()
    if discovered:
        roles: list[str] = []
        for role in discovered:
            name = str(role.get("name") or "")
            if not name or name in STACK_PRIOR_SEEDING_EXCLUDED_ROLES:
                continue
            roles.append(name)
        if roles:
            return roles
    return list(_EMERGENCY_DEFAULT_ROLES_FALLBACK)


DEFAULT_ROLES = _read_stack_prior_default_roles() or _discover_default_roles_fallback()
# NOTE: React mode has been unified into REPL with structured_mode=True.
# "react" is no longer a separate mode - REPL is the universal superset.
DEFAULT_MODES = ["direct", "repl"]


# ── Role / mode constraints ──────────────────────────────────────────

ARCHITECT_ROLES = {role for role in DEFAULT_ROLES if role.startswith("architect_")} or {"architect_general"}
ARCHITECT_MODES = {"direct", "delegated"}
# INF-78 scoped exception (operator 2026-09-25): REPL is allowed for the architect only
# on task-scoped requests (task_root set). Seeding requests are never task-scoped.
ARCHITECT_MODES_TASK_SCOPED = ARCHITECT_MODES | {"repl"}


def architect_modes(task_scoped: bool = False) -> set[str]:
    return set(ARCHITECT_MODES_TASK_SCOPED if task_scoped else ARCHITECT_MODES)

VISION_ROLES = {"worker_vision", "vision_escalation"}
VISION_MODES: dict[str, set[str]] = {
    # React has been unified into repl (structured REPL path).
    "worker_vision": {"direct", "repl"},
    "vision_escalation": {"direct"},
}

# ── Cost / escalation constants ──────────────────────────────────────

ROLE_COST_TIER: dict[str, int] = {
    "worker_explore": 1,
    "worker_general": 1,
    "worker_math": 1,
    "worker_vision": 1,
    "frontdoor": 2,
    "coder_escalation": 3,
    "toolrunner": 3,
    "worker_summarize": 3,
    "vision_escalation": 3,
    "architect_general": 4,
    "ingest_long_context": 4,
}

ESCALATION_REWARD = 0.8


# ── Phase 4: 3-way routing action keys ───────────────────────────────
# Simplified action vocabulary for faithful probability estimation.
# Q-values converge to P(success|action), cost applied at routing time.

ACTION_SELF_DIRECT = "SELF:direct"  # Frontdoor without tools
ACTION_SELF_REPL = "SELF:repl"      # Frontdoor with tools, no delegation
ACTION_ARCHITECT = "ARCHITECT"       # Architect with full delegation freedom
ACTION_WORKER = "WORKER"             # Worker models (scored via delegation chain)

THREE_WAY_ACTIONS = [ACTION_SELF_DIRECT, ACTION_SELF_REPL, ACTION_ARCHITECT, ACTION_WORKER]

# Cost tiers for 3-way routing (applied at decision time, not during learning)
THREE_WAY_COST_TIER: dict[str, int] = {
    ACTION_SELF_DIRECT: 2,  # Frontdoor, low cost
    ACTION_SELF_REPL: 2,    # Same model, just with tools
    ACTION_ARCHITECT: 4,    # Expensive architect models
    ACTION_WORKER: 1,       # Cheapest, small worker models
}


# ── Server topology ──────────────────────────────────────────────────
# Generated stack priors are preferred. Registry-derived topology is the
# degraded/offline fallback for historical fixtures and broken generated
# artifacts; empty sets preserve fail-closed behavior if both sources are gone.

_STACK_PRIOR_TOPOLOGY = _read_stack_prior_topology()
_REGISTRY_TOPOLOGY = _read_registry_topology()
ROLE_PORT: dict[str, int] = dict(
    _STACK_PRIOR_TOPOLOGY.get("role_port") or _REGISTRY_TOPOLOGY.get("role_port") or {}
)
ROLE_COST_TIER.update(_REGISTRY_TOPOLOGY.get("role_cost_tier") or {})
HEAVY_PORTS = set(
    _STACK_PRIOR_TOPOLOGY.get("heavy_ports") or _REGISTRY_TOPOLOGY.get("heavy_ports") or set()
)
MODEL_PORTS = list(
    _STACK_PRIOR_TOPOLOGY.get("model_ports") or _REGISTRY_TOPOLOGY.get("model_ports") or []
)

STACK_SCRIPT = PROJECT_ROOT / "scripts" / "server" / "orchestrator_stack.py"


# ── Phase 5: Dynamic role discovery ─────────────────────────────────
# Roles excluded from seeding evaluation (non-LLM infrastructure).
# When changing the stack, update this set for new non-LLM services.
# See adaptation surface docs in wiki/autopilot-seeder-roles.md.


def discover_active_roles(
    registry_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Discover active LLM inference roles from model_registry.yaml.

    Parses the production roles section and returns metadata for each
    active role suitable for seeding evaluation.

    Adaptation surface:
        - Add non-LLM services to SEEDING_EXCLUDED_ROLES
        - Port mappings read from ROLE_PORT (update when roles are renamed)
        - Heavy port classification from HEAVY_PORTS

    Returns:
        List of dicts: [{name, port, is_heavy, cost_tier, model_role}, ...]
        Sorted by cost_tier (cheapest first for interleaving).
    """
    if registry_path is None:
        stack_prior_roles = _read_stack_prior_active_roles()
        if stack_prior_roles:
            return stack_prior_roles
        registry_path = PROJECT_ROOT / "orchestration" / "model_registry.yaml"

    try:
        with registry_path.open() as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return []

    # Production roles live under server_mode (not roles, which has quant variants)
    roles_section = data.get("server_mode", {})
    if not roles_section:
        return []

    active: list[dict[str, Any]] = []

    for role_key, role_def in roles_section.items():
        if not isinstance(role_def, dict):
            continue

        # Skip excluded roles
        if role_key in SEEDING_EXCLUDED_ROLES:
            continue

        # Skip non-LLM services (no model field)
        if "model" not in role_def and "model_type" not in role_def:
            continue

        # Skip non-GGUF model types (whisper, onnx, docker, etc.)
        model_type = role_def.get("model_type", "gguf")
        if model_type not in ("gguf", "gguf_vlm"):
            continue

        # Resolve the role name the orchestrator accepts for force_role
        role_name = _canonical_role_name(_REGISTRY_KEY_TO_ROLE.get(role_key, role_key))
        model_role = role_def.get("model_role", role_name)

        # Get port from role definition or ROLE_PORT fallback
        port = role_def.get("port", ROLE_PORT.get(role_key, ROLE_PORT.get(role_name, 0)))
        if port == 0:
            continue  # No port → can't evaluate

        timeouts = data.get("runtime_defaults", {}).get("timeouts", {})
        role_timeouts = timeouts.get("roles", {})
        default_timeout = timeouts.get("default", DEFAULT_TIMEOUT)
        timeout_s = role_timeouts.get(
            role_name,
            role_timeouts.get(role_key, default_timeout),
        )

        active.append({
            "name": role_name,       # Use for force_role
            "registry_key": role_key,  # Original key in model_registry.yaml
            "model_role": model_role,
            "port": port,
            "is_heavy": port in HEAVY_PORTS,
            "cost_tier": ROLE_COST_TIER.get(role_name, ROLE_COST_TIER.get(role_key, 3)),
            "timeout_s": int(timeout_s),
        })

    # Sort by cost tier (cheapest first) for interleaving
    active.sort(key=lambda r: r["cost_tier"])
    return active


# ── Exceptions ────────────────────────────────────────────────────────


class HealthCheckError(Exception):
    """Raised when the orchestrator API is unreachable."""

    pass


# ── Data structures ──────────────────────────────────────────────────


@dataclass
class RoleResult:
    """Result of running a question through a specific role+mode."""

    role: str
    mode: str
    answer: str
    passed: bool
    elapsed_seconds: float
    error: str | None = None
    error_type: str = "none"
    tokens_generated: int = 0
    tool_output_tokens: int = 0  # Estimated tokens from tool outputs (~len/4)
    # Slot-observed decoded token estimate for timed-out infra calls where
    # payload-derived tokens are unavailable (kept separate from tokens_generated).
    tokens_generated_estimate: int = 0
    backend_task_id: int = 0
    slot_progress_source: str = ""
    tools_used: int = 0
    tools_called: list[str] = field(default_factory=list)
    tool_chains: list[dict[str, Any]] = field(default_factory=list)
    delegation_events: list[dict] = field(default_factory=list)
    delegation_diagnostics: dict[str, Any] = field(default_factory=dict)
    tools_success: bool | None = None
    delegation_success: bool | None = None
    routed_to: str = ""
    role_history: list[str] = field(default_factory=list)
    routing_strategy: str = ""
    turns: int = 0
    tokens_used: int = 0
    prompt_tokens: int = 0  # Input/context tokens (for compression-vs-quality analysis)
    formalization_applied: bool = False
    cache_stats: dict[str, Any] | None = None
    # Clean timing data from llama.cpp (excludes prompt eval overhead)
    predicted_tps: float = 0.0
    generation_ms: float = 0.0
    prompt_eval_ms: float = 0.0
    http_overhead_ms: float = 0.0
    # Inference tap byte range for this call (0/0 = not captured)
    tap_offset_bytes: int = 0
    tap_length_bytes: int = 0
    # Trinity tri-role axis (TR-2.1 of tri-role-coordinator-architecture.md).
    # Per-call assignment {"thinker", "worker", "verifier"}, ORTHOGONAL to the
    # `role` field above (which is the model role like "frontdoor"/"worker_30b").
    # Naming: NOT named `role` to avoid colliding with the existing model-role
    # field. Default `"worker"` for backward compat. Logged in shadow mode
    # regardless of feature flag; only acted on when ROLE_AWARE_ROUTING=1.
    assigned_role: str = "worker"
    # REPL tap byte range (code execution output/errors)
    repl_tap_offset_bytes: int = 0
    repl_tap_length_bytes: int = 0
    # New tunable fields (orchestrator intelligence improvements)
    cost_dimensions: dict[str, float] = field(default_factory=dict)
    think_harder_attempted: bool = False
    think_harder_succeeded: bool | None = None
    cheap_first_attempted: bool = False
    cheap_first_passed: bool | None = None
    grammar_enforced: bool = False
    parallel_tools_used: bool = False
    cache_affinity_bonus: float = 0.0
    # SkillBank integration
    skills_retrieved: int = 0
    skill_ids: list[str] = field(default_factory=list)
    # Context window management (C1/C3) and budget tracking (R1)
    budget_diagnostics: dict[str, Any] = field(default_factory=dict)
    session_persistence: dict[str, Any] = field(default_factory=dict)
    tool_results_cleared: int = 0
    compaction_triggered: bool = False
    compaction_tokens_saved: int = 0
    think_harder_expected_roi: float = 0.0
    # Tool output compression metrics
    compression_metrics: dict[str, Any] = field(default_factory=dict)
    # Web research telemetry (Search-R1 reward design)
    web_research_results: list[dict] = field(default_factory=list)
    # Scratchpad insights (Search-R1 Step 5)
    scratchpad_insights: list[dict] = field(default_factory=list)
    # Factual-risk scoring (routing-intelligence Phase 5)
    factual_risk_score: float = 0.0
    factual_risk_adjusted: float = 0.0
    factual_risk_band: str = ""
    factual_risk_features: dict[str, float] = field(default_factory=dict)
    # Difficulty signal (reasoning-compression Action 3 / NIB2-35)
    # Populated from routing_meta so NIB2-32 re-validation has queryable data.
    difficulty_score: float = 0.0
    difficulty_band: str = ""
    # 2026-05-23 exogenous-restart resilience (handoff Phase 4).
    # Populated from resilient_post `_meta` dict via _eval_single_config.
    # See QuestionResult.exogenous_* fields for the same semantics — these
    # are the per-role-call counterpart on the seeding side.
    exogenous_recovered: bool = False
    exogenous_unrecovered: bool = False
    external_restart: bool = False
    retry_count: int = 0
    resilient_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class WebResearchTelemetry:
    """Aggregated telemetry from web_research tool invocations."""

    call_count: int = 0
    total_pages_fetched: int = 0
    total_pages_synthesized: int = 0
    total_pages_irrelevant: int = 0
    total_elapsed_ms: float = 0.0
    unique_domains: int = 0
    queries: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)


@dataclass
class ComparativeResult:
    """Comparative result across roles for a single question."""

    suite: str
    question_id: str
    prompt: str
    expected: str
    reference: str = ""
    dataset_source: str = "yaml"
    prompt_hash: str = ""
    timestamp: str = ""
    role_results: dict[str, RoleResult] = field(default_factory=dict)
    rewards: dict[str, float] = field(default_factory=dict)
    rewards_injected: int = 0


# ── Shared mutable state ─────────────────────────────────────────────


class _State:
    """Process-wide mutable state shared across all seeding modules.

    Replaces module-level globals (_shutdown, _poll_client) with an
    explicit singleton so signal handlers and infra code can coordinate.
    """

    def __init__(self) -> None:
        self.shutdown: bool = False
        self.session_id: str = ""  # Set by main() for cross-request persistence
        self._poll_client: "Any" = None  # httpx.Client, lazily created

    def get_poll_client(self) -> "Any":
        """Get or create the connection-reusing httpx client for polling."""
        if self._poll_client is None:
            import httpx
            self._poll_client = httpx.Client(timeout=10)
        return self._poll_client

    def close_poll_client(self) -> None:
        """Close the polling client if open."""
        if self._poll_client is not None:
            try:
                self._poll_client.close()
            except Exception:
                pass
            self._poll_client = None


state = _State()
