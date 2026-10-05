"""Reward computation, escalation chain detection, and reward injection.

Keep module imports light for benchmark scripts; stack-prior artifact loading is
lazy so the shared runtime fail-closed loader can be reused without changing
seeding script bootstrap order.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from urllib.parse import urlparse

import yaml

from src.roles import Role

from seeding_types import (
    ACTION_ARCHITECT,
    ACTION_SELF_DIRECT,
    ACTION_SELF_REPL,
    ACTION_WORKER,
    ComparativeResult,
    ESCALATION_REWARD,
    ROLE_COST_TIER,
    RoleResult,
    STACK_PRIORS_PATH,
    WebResearchTelemetry,
)

DEFAULT_MODEL_DESCRIPTORS_PATH = (
    Path(__file__).resolve().parents[2] / "orchestration" / "model_descriptors.yaml"
)

__all__ = [
    "FALLBACK_THROUGHPUT_BY_ROLE",
    "compute_comparative_rewards",
    "detect_escalation_chains",
    "stack_prior_architect_reward_roles",
    "stack_prior_throughput_by_role",
    "throughput_prior_provenance",
    # Phase 4: Binary rewards for faithful probability estimation
    "success_reward",
    "compute_3way_rewards",
    "score_delegation_chain",
    "compute_tool_value",
    # Search-R1: Web research quality rewards
    "extract_web_research_telemetry",
    "compute_web_research_rewards",
    "aggregate_web_research_reward",
    "score_query_strategy",
    # Search-R1 Step 5: Scratchpad insight rewards
    "compute_scratchpad_rewards",
]

# Explicit degraded/offline values. Live seeding reads stack_priors.yaml.
FALLBACK_THROUGHPUT_BY_ROLE: dict[str, float] = {
    "frontdoor": 24.3,
    "coder_escalation": 24.3,
    "worker_summarize": 24.3,
    "architect_general": 12.19,
    "ingest_long_context": 20.8,
    "toolrunner": 38.46,
    "worker_general": 38.46,
    "worker_math": 38.46,
    "worker_vision": 20.0,
    "vision_escalation": 27.6,
}
FALLBACK_ARCHITECT_REWARD_ROLES = frozenset({"architect_general", "vision_escalation"})
THROUGHPUT_CONFIG_KEY = "throughput_by_role"
LEGACY_THROUGHPUT_CONFIG_KEY = "baseline_" + "tps_by_role"
STACK_PRIORS_CONFIG_KEY = "stack_priors_path"
MODEL_DESCRIPTORS_CONFIG_KEY = "model_descriptors_path"
ALLOW_DEGRADED_CONFIG_KEY = "allow_degraded_fallback"
PRIOR_SOURCE_CONFIG_OVERRIDE = "config_override"
PRIOR_SOURCE_LEGACY_CONFIG_OVERRIDE = "legacy_config_override"
PRIOR_SOURCE_STACK_PRIORS = "stack_priors"
PRIOR_SOURCE_MODEL_DESCRIPTORS = "model_descriptors"
PRIOR_SOURCE_DEGRADED_FALLBACK = "degraded_fallback"
PRIOR_SOURCE_MISSING = "missing"


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _clean_throughput_mapping(values: Any) -> dict[str, float]:
    if not isinstance(values, dict):
        return {}
    cleaned: dict[str, float] = {}
    for role, value in values.items():
        number = _positive_float(value)
        if number is not None:
            cleaned[_canonical_role_name(str(role))] = number
    return cleaned


def _canonical_role_name(role: str) -> str:
    canonical = Role.from_string(role)
    return canonical.value if canonical is not None else role


def _live_stack_role_records(path: Path | None = None) -> dict[str, dict[str, Any]]:
    stack_priors_path = path or STACK_PRIORS_PATH
    try:
        from src.registry.stack_priors import live_stack_role_records
    except ImportError:
        return {}
    return live_stack_role_records(stack_priors_path)


def stack_prior_throughput_by_role(path: Path | None = None) -> dict[str, float]:
    """Read live per-role throughput from generated stack priors."""
    throughput: dict[str, float] = {}
    for role, record in _live_stack_role_records(path).items():
        priors = record.get("priors")
        if not isinstance(priors, dict):
            continue
        value = _positive_float(priors.get("throughput_tps"))
        if value is not None:
            throughput[str(role)] = value
    return throughput


def stack_prior_architect_reward_roles(path: Path | None = None) -> set[str]:
    """Return live roles that map onto the 3-way ARCHITECT action."""
    architect_roles: set[str] = set()
    for role, record in _live_stack_role_records(path).items():
        role_name = str(role)
        if role_name.startswith("architect_") or role_name == "vision_escalation":
            architect_roles.add(role_name)
    return architect_roles


def _load_model_descriptors(path: Path = DEFAULT_MODEL_DESCRIPTORS_PATH) -> list[dict[str, Any]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    models = data.get("models")
    if not isinstance(models, list):
        return []
    return [model for model in models if isinstance(model, dict)]


def _descriptor_speed_tps(descriptor: dict[str, Any]) -> float | None:
    speed = descriptor.get("speed")
    if not isinstance(speed, dict):
        return None
    for key in (
        "optimized_tps",
        "quarter_48t_tps",
        "solo_96t_tps",
        "prefill_tps",
        "generation_tps_range",
    ):
        value = _positive_float(speed.get(key))
        if value is not None:
            return value
    return None


def descriptor_throughput_by_role(
    path: Path = DEFAULT_MODEL_DESCRIPTORS_PATH,
) -> dict[str, float]:
    """Read degraded per-role throughput from generated model descriptors."""
    throughput: dict[str, float] = {}
    for descriptor in _load_model_descriptors(path):
        tps = _descriptor_speed_tps(descriptor)
        if tps is None:
            continue
        bindings = descriptor.get("role_bindings")
        roles = bindings.get("roles") if isinstance(bindings, dict) else None
        if not isinstance(roles, list):
            continue
        for role in roles:
            if not isinstance(role, str):
                continue
            throughput[_canonical_role_name(role)] = tps
    return throughput


def _throughput_provenance(
    source: str,
    throughput: dict[str, float],
    *,
    stack_priors_path: Path | None = None,
    model_descriptors_path: Path | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "roles": sorted(throughput),
        "role_count": len(throughput),
        "stack_priors_path": str(stack_priors_path) if stack_priors_path else None,
        "model_descriptors_path": (
            str(model_descriptors_path) if model_descriptors_path else None
        ),
        "uses_degraded_fallback": source in {
            PRIOR_SOURCE_MODEL_DESCRIPTORS,
            PRIOR_SOURCE_DEGRADED_FALLBACK,
        },
        "reason": reason,
    }


def _resolve_throughput_by_role(
    cost_config: dict[str, Any],
) -> tuple[dict[str, float], dict[str, Any]]:
    override = cost_config.get(THROUGHPUT_CONFIG_KEY)
    override_source = PRIOR_SOURCE_CONFIG_OVERRIDE
    if override is None:
        override = cost_config.get(LEGACY_THROUGHPUT_CONFIG_KEY)
        override_source = PRIOR_SOURCE_LEGACY_CONFIG_OVERRIDE
    cleaned_override = _clean_throughput_mapping(override)
    if cleaned_override:
        return cleaned_override, _throughput_provenance(override_source, cleaned_override)

    path_value = cost_config.get(STACK_PRIORS_CONFIG_KEY)
    stack_priors_path = Path(path_value) if path_value else None
    live_throughput = stack_prior_throughput_by_role(stack_priors_path)
    if live_throughput:
        return live_throughput, _throughput_provenance(
            PRIOR_SOURCE_STACK_PRIORS,
            live_throughput,
            stack_priors_path=stack_priors_path or STACK_PRIORS_PATH,
        )
    if cost_config.get(ALLOW_DEGRADED_CONFIG_KEY):
        descriptor_value = cost_config.get(MODEL_DESCRIPTORS_CONFIG_KEY)
        descriptor_path = Path(descriptor_value) if descriptor_value else DEFAULT_MODEL_DESCRIPTORS_PATH
        descriptor_throughput = descriptor_throughput_by_role(descriptor_path)
        if descriptor_throughput:
            return descriptor_throughput, _throughput_provenance(
                PRIOR_SOURCE_MODEL_DESCRIPTORS,
                descriptor_throughput,
                stack_priors_path=stack_priors_path or STACK_PRIORS_PATH,
                model_descriptors_path=descriptor_path,
                reason="stack_priors_missing_or_no_live_throughput",
            )
        fallback = dict(FALLBACK_THROUGHPUT_BY_ROLE)
        return fallback, _throughput_provenance(
            PRIOR_SOURCE_DEGRADED_FALLBACK,
            fallback,
            stack_priors_path=stack_priors_path or STACK_PRIORS_PATH,
            reason="stack_priors_missing_or_no_live_throughput",
        )
    return {}, _throughput_provenance(
        PRIOR_SOURCE_MISSING,
        {},
        stack_priors_path=stack_priors_path or STACK_PRIORS_PATH,
        reason="no_override_and_no_live_stack_priors",
    )


def _throughput_by_role(cost_config: dict[str, Any]) -> dict[str, float]:
    throughput, _provenance = _resolve_throughput_by_role(cost_config)
    return throughput


def throughput_prior_provenance(cost_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Describe the throughput-prior source used by comparative rewards."""
    _throughput, provenance = _resolve_throughput_by_role(cost_config or {})
    return provenance


def _architect_reward_roles() -> set[str]:
    return stack_prior_architect_reward_roles() or set(FALLBACK_ARCHITECT_REWARD_ROLES)


def _architect_result_keys(results: dict[str, RoleResult]) -> list[str]:
    architect_roles = _architect_reward_roles()
    return [
        key for key, result in results.items()
        if result.role in architect_roles or key.split(":", 1)[0] in architect_roles
    ]


def compute_comparative_rewards(
    role_results: dict[str, RoleResult],
    baseline_key: str = "frontdoor:direct",
    cost_config: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Compute comparative rewards relative to the baseline.

    Reward scheme (xRouter-style, correctness-gated cost penalty):
      specialist correct & baseline wrong -> +1.0 (clear specialist win)
      specialist wrong & baseline right   -> -0.5 (specialist worse)
      both correct -> 0.5 - lambda * max(0, cost_ratio - 1.0)  (cost-aware)
      both wrong   -> -0.3 (neither helps)
    """
    cost_config = cost_config or {}
    lam = cost_config.get("lambda", 0.15)
    throughput_by_role = _throughput_by_role(cost_config)

    rewards: dict[str, float] = {}
    baseline = role_results.get(baseline_key)
    if baseline is None:
        for key, result in role_results.items():
            rewards[key] = 1.0 if result.passed else 0.0
        return rewards

    baseline_passed = baseline.passed

    for key, result in role_results.items():
        if key == baseline_key:
            rewards[key] = 1.0 if result.passed else 0.0
        elif result.passed and not baseline_passed:
            rewards[key] = 1.0
        elif not result.passed and baseline_passed:
            rewards[key] = -0.5
        elif result.passed and baseline_passed:
            base = 0.5
            role_tps = throughput_by_role.get(_canonical_role_name(result.role), 0)
            gen_elapsed = result.generation_ms / 1000.0 if result.generation_ms > 0 else 0
            actual_elapsed = gen_elapsed if gen_elapsed > 0 else result.elapsed_seconds
            if (role_tps > 0 and result.tokens_generated > 0
                    and actual_elapsed > 0):
                expected = result.tokens_generated / role_tps
                cost_ratio = actual_elapsed / expected
                cost_penalty = lam * max(0.0, cost_ratio - 1.0)
                rewards[key] = max(0.1, base - cost_penalty)
            else:
                rewards[key] = 0.3
        else:
            rewards[key] = -0.3

    return rewards


def detect_escalation_chains(
    role_results: dict[str, RoleResult],
) -> list[dict[str, Any]]:
    """Detect cases where a cheap model fails but a more expensive one passes.

    Returns list of escalation chain dicts:
      {"from_role": "worker_general", "from_mode": "direct",
       "to_role": "coder_escalation", "to_mode": "direct",
       "action": "escalate:worker_general->coder_escalation",
       "reward": 0.8}
    """
    chains: list[dict[str, Any]] = []
    entries = []
    for key, rr in role_results.items():
        role, mode = key.split(":", 1)
        role = _canonical_role_name(role)
        tier = ROLE_COST_TIER.get(role, 99)
        entries.append((tier, role, mode, rr))

    entries.sort(key=lambda x: x[0])

    # For each failed cheap role, find the cheapest passing expensive role
    for i, (tier_i, role_i, mode_i, rr_i) in enumerate(entries):
        if rr_i.passed or rr_i.error:
            continue  # Only look at failures (not errors)
        for j in range(i + 1, len(entries)):
            tier_j, role_j, mode_j, rr_j = entries[j]
            if tier_j <= tier_i:
                continue
            if rr_j.passed:
                chains.append({
                    "from_role": role_i,
                    "from_mode": mode_i,
                    "to_role": role_j,
                    "to_mode": mode_j,
                    "action": f"escalate:{role_i}->{role_j}",
                    "reward": ESCALATION_REWARD,
                })
                break  # Only the cheapest passing escalation target

    return chains


def _inject_escalation_chains_http(
    comp: ComparativeResult,
    chains: list[dict[str, Any]],
    url: str,
    client: "Any",
) -> int:
    """Inject escalation chain rewards via HTTP API.

    Returns number of rewards successfully injected.
    """
    injected = 0
    for chain in chains:
        try:
            resp = client.post(
                f"{url}/chat/reward",
                json={
                    "task_description": comp.prompt[:200],
                    "action": chain["action"],
                    "reward": chain["reward"],
                    "context": {
                        "task_type": comp.suite,
                        "source": "escalation_chain",
                        "question_id": comp.question_id,
                        "action_type": "escalation",
                        "from_role": chain["from_role"],
                        "to_role": chain["to_role"],
                    },
                },
                timeout=10,
            )
            if resp.status_code == 200:
                injected += 1
        except Exception:
            continue
    return injected


def _inject_rewards_http(
    comp: ComparativeResult,
    url: str,
    client: "Any",
) -> int:
    """Inject comparative rewards for one question via HTTP API.

    Returns number of rewards successfully injected.
    """
    injected = 0
    for action_key, reward in comp.rewards.items():
        try:
            resp = client.post(
                f"{url}/chat/reward",
                json={
                    "task_description": comp.prompt[:200],
                    "action": action_key,
                    "reward": reward,
                    "context": {
                        "task_type": comp.suite,
                        "source": "comparative_seeding",
                        "question_id": comp.question_id,
                        "comparative": True,
                    },
                },
                timeout=10,
            )
            if resp.status_code == 200:
                injected += 1
        except Exception:
            continue
    return injected


# ── Phase 4: Binary rewards for faithful probability estimation ──────


def success_reward(passed: bool) -> float:
    """Binary reward for faithful probability estimation.

    Q-values should converge to P(success|action).
    With binary rewards and TD learning (α=0.1):
        new_q = old_q + α(reward - old_q)
    converges to empirical success rate.

    Args:
        passed: Whether the task succeeded.

    Returns:
        1.0 for success, 0.0 for failure.
    """
    return 1.0 if passed else 0.0


def compute_3way_rewards(
    results: dict[str, RoleResult],
) -> dict[str, float]:
    """Compute binary rewards for 3-way routing evaluation.

    Maps role results to 3-way action categories and computes
    binary rewards. Cost is NOT included — Q-values represent
    pure P(success).

    Args:
        results: Dict mapping action_key (e.g. "frontdoor:direct") to RoleResult.

    Returns:
        Dict mapping 3-way action key to binary reward.
    """
    rewards: dict[str, float] = {}

    # SELF:direct — frontdoor/worker_vision without tools
    direct_keys = [k for k in results if k in ("frontdoor:direct", "worker_vision:direct")]
    if direct_keys:
        rewards[ACTION_SELF_DIRECT] = success_reward(results[direct_keys[0]].passed)

    # SELF:repl — frontdoor/worker_vision with tools (no delegation)
    # Backward-compatible: older sessions may still have worker_vision:react.
    repl_keys = [k for k in results if k in ("frontdoor:repl", "worker_vision:repl", "worker_vision:react")]
    if repl_keys:
        rewards[ACTION_SELF_REPL] = success_reward(results[repl_keys[0]].passed)

    # ARCHITECT — live architect-like roles from stack priors.
    architect_keys = _architect_result_keys(results)
    if architect_keys:
        # Take best architect result (they have delegation freedom)
        best_architect = max(architect_keys, key=lambda k: int(results[k].passed))
        rewards[ACTION_ARCHITECT] = success_reward(results[best_architect].passed)

    return rewards


def score_delegation_chain(
    results: dict[str, RoleResult],
) -> dict[str, float]:
    """Score WORKER based on delegation chain outcomes.

    Workers are "glorified tools" — they're triggered by SELF:repl or ARCHITECT
    delegation. When delegation occurs, we also inject a WORKER reward.

    Args:
        results: Dict mapping action_key to RoleResult.

    Returns:
        Dict with WORKER reward if delegation occurred.
    """
    rewards: dict[str, float] = {}

    # Check SELF:repl for delegation (frontdoor:repl for text, worker_vision:repl for VL).
    # Keep worker_vision:react for backward compatibility with older logs.
    repl_keys = [k for k in results if k in ("frontdoor:repl", "worker_vision:repl", "worker_vision:react")]
    for key in repl_keys:
        rr = results[key]
        if getattr(rr, "error_type", "none") == "infrastructure":
            continue
        if _has_delegation(rr):
            if rr.delegation_success is not None:
                rewards[ACTION_WORKER] = success_reward(rr.delegation_success)
            else:
                rewards[ACTION_WORKER] = success_reward(rr.passed)

    # Check ARCHITECT for delegation
    architect_keys = _architect_result_keys(results)
    for key in architect_keys:
        rr = results[key]
        if getattr(rr, "error_type", "none") == "infrastructure":
            continue
        if _has_delegation(rr):
            score = (
                success_reward(rr.delegation_success)
                if rr.delegation_success is not None
                else success_reward(rr.passed)
            )
            if ACTION_WORKER in rewards:
                rewards[ACTION_WORKER] = max(rewards[ACTION_WORKER], score)
            else:
                rewards[ACTION_WORKER] = score

    return rewards


def _has_delegation(rr: RoleResult) -> bool:
    """Check if a RoleResult involved delegation to a worker."""
    if getattr(rr, "error_type", "none") == "infrastructure":
        return False
    if getattr(rr, "delegation_events", None):
        return True
    # Check tools_called for delegation indicators
    if rr.tools_called:
        delegation_tools = {"delegate", "delegate_to_worker", "spawn_worker"}
        for tool in rr.tools_called:
            if any(dt in tool.lower() for dt in delegation_tools):
                return True

    # Check role_history for worker involvement
    if rr.role_history and len(rr.role_history) > 1:
        worker_roles = {
            Role.WORKER_GENERAL.value,
            Role.WORKER_MATH.value,
            Role.WORKER_VISION.value,
            Role.WORKER_SUMMARIZE.value,
        }
        for role in rr.role_history:
            if _canonical_role_name(role) in worker_roles:
                return True

    return False


def compute_tool_value(
    direct_passed: bool,
    repl_passed: bool,
) -> dict[str, Any]:
    """Compute tool value signal comparing SELF:direct vs SELF:repl.

    This is stored as metadata, not separate rewards.

    Args:
        direct_passed: Whether SELF:direct succeeded.
        repl_passed: Whether SELF:repl succeeded.

    Returns:
        Dict with tool value analysis.
    """
    return {
        "tools_helped": repl_passed and not direct_passed,
        "tools_neutral": repl_passed == direct_passed,
        "tools_hurt": direct_passed and not repl_passed,
        "tool_advantage": int(repl_passed) - int(direct_passed),
    }


# ── Search-R1: Web research quality rewards ──────────────────────────

_WEB_RESEARCH_IRRELEVANCE_REWARD_THRESHOLD = 0.20


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _is_relevant_source(source: dict[str, Any]) -> bool:
    """Return True when source relevance is not explicitly negated."""
    return source.get("relevant") is not False


def _web_research_relevance_scale(
    *,
    total_pages_synthesized: int,
    total_pages_irrelevant: int,
) -> float:
    """Downweight reward when synthesized pages are mostly irrelevant."""
    if total_pages_synthesized <= 0:
        return 1.0
    if total_pages_irrelevant >= total_pages_synthesized:
        return 0.0

    irrelevant_rate = total_pages_irrelevant / total_pages_synthesized
    if irrelevant_rate >= _WEB_RESEARCH_IRRELEVANCE_REWARD_THRESHOLD:
        return max(0.0, 1.0 - irrelevant_rate)
    return 1.0


def _source_relevance_counts(sources: Any) -> tuple[int, int]:
    """Return explicit source relevance metadata as (total, irrelevant)."""
    if not isinstance(sources, list):
        return 0, 0
    total = 0
    irrelevant = 0
    for src in sources:
        if not isinstance(src, dict) or "relevant" not in src:
            continue
        total += 1
        if src.get("relevant") is False:
            irrelevant += 1
    return total, irrelevant


def _web_research_relevance_counts(result: dict[str, Any]) -> tuple[int, int]:
    """Merge page counters with source-level relevance flags."""
    sources = result.get("sources", [])
    source_total, source_irrelevant = _source_relevance_counts(sources)
    total_pages_synthesized = max(
        _nonnegative_int(result.get("pages_synthesized")),
        source_total,
    )
    total_pages_irrelevant = max(
        _nonnegative_int(result.get("pages_irrelevant")),
        source_irrelevant,
    )
    return total_pages_synthesized, total_pages_irrelevant


def _web_research_results_relevance_scale(web_research_results: list[dict]) -> float:
    total_pages_synthesized = 0
    total_pages_irrelevant = 0
    valid_results = 0
    for wr in web_research_results:
        if not isinstance(wr, dict):
            continue
        if wr.get("success") is False:
            continue
        valid_results += 1
        pages_synthesized, pages_irrelevant = _web_research_relevance_counts(wr)
        total_pages_synthesized += pages_synthesized
        total_pages_irrelevant += pages_irrelevant
    if web_research_results and valid_results == 0:
        return 0.0
    return _web_research_relevance_scale(
        total_pages_synthesized=total_pages_synthesized,
        total_pages_irrelevant=total_pages_irrelevant,
    )


def _relevant_source_urls(sources: Any) -> list[str]:
    relevant_urls: list[str] = []
    if not isinstance(sources, list):
        return relevant_urls
    for src in sources:
        if not isinstance(src, dict):
            continue
        if not _is_relevant_source(src):
            continue
        url = src.get("url", "")
        if url:
            relevant_urls.append(url)
    return relevant_urls


def extract_web_research_telemetry(
    tool_results: list[dict],
) -> WebResearchTelemetry:
    """Aggregate telemetry from web_research tool result dicts.

    Args:
        tool_results: List of web_research return dicts (from ToolInvocation.result).

    Returns:
        Aggregated WebResearchTelemetry.
    """
    if not tool_results:
        return WebResearchTelemetry()

    total_pages_fetched = 0
    total_pages_synthesized = 0
    total_pages_irrelevant = 0
    total_elapsed_ms = 0.0
    queries: list[str] = []
    source_urls: list[str] = []
    relevant_source_urls: list[str] = []
    valid_call_count = 0

    for wr in tool_results:
        if not isinstance(wr, dict):
            continue
        if wr.get("success") is False:
            continue
        valid_call_count += 1
        total_pages_fetched += _nonnegative_int(wr.get("pages_fetched"))
        pages_synthesized, pages_irrelevant = _web_research_relevance_counts(wr)
        total_pages_synthesized += pages_synthesized
        total_pages_irrelevant += pages_irrelevant
        total_elapsed_ms += float(wr.get("total_elapsed_ms", 0.0) or 0.0)
        q = wr.get("query", "")
        if q:
            queries.append(q)
        sources = wr.get("sources", [])
        relevant_source_urls.extend(_relevant_source_urls(sources))
        source_urls.extend(_relevant_source_urls(sources))

    # Compute unique domains
    domains: set[str] = set()
    for url in relevant_source_urls:
        try:
            parsed = urlparse(url)
            if parsed.hostname:
                domains.add(parsed.hostname)
        except Exception:
            pass

    return WebResearchTelemetry(
        call_count=valid_call_count,
        total_pages_fetched=total_pages_fetched,
        total_pages_synthesized=total_pages_synthesized,
        total_pages_irrelevant=total_pages_irrelevant,
        total_elapsed_ms=total_elapsed_ms,
        unique_domains=len(domains),
        queries=queries,
        source_urls=source_urls,
    )


def compute_web_research_rewards(
    telemetry: WebResearchTelemetry,
    passed: bool,
    f1_score: float = 0.0,
) -> dict[str, float]:
    """Compute multi-dimensional web research quality rewards.

    Returns empty dict if no web_research calls were made.

    Dimensions:
        wr_accuracy: 1.0 if passed, else 0.0
        wr_source_diversity: unique_domains / pages_fetched (0–1)
        wr_efficiency: 1/pages_fetched for correct answers only (0–1)
        wr_completeness: f1_score passthrough

    Args:
        telemetry: Aggregated web research telemetry.
        passed: Whether the overall task passed.
        f1_score: F1 score (0–1) if available.

    Returns:
        Dict of reward dimension name -> value.
    """
    if telemetry.call_count == 0:
        return {}

    rewards: dict[str, float] = {}
    relevance_scale = _web_research_relevance_scale(
        total_pages_synthesized=telemetry.total_pages_synthesized,
        total_pages_irrelevant=telemetry.total_pages_irrelevant,
    )
    rewards["wr_accuracy"] = (1.0 if passed else 0.0) * relevance_scale
    rewards["wr_completeness"] = max(0.0, min(1.0, f1_score)) * relevance_scale

    if telemetry.total_pages_fetched > 0:
        rewards["wr_source_diversity"] = (
            min(1.0, telemetry.unique_domains / telemetry.total_pages_fetched)
            * relevance_scale
        )
        # Efficiency: fewer pages for a correct answer = better
        if passed:
            rewards["wr_efficiency"] = (
                min(1.0, 1.0 / telemetry.total_pages_fetched) * relevance_scale
            )
        else:
            rewards["wr_efficiency"] = 0.0
    else:
        rewards["wr_source_diversity"] = 0.0
        rewards["wr_efficiency"] = 0.0

    return rewards


_DEFAULT_WR_WEIGHTS: dict[str, float] = {
    "wr_accuracy": 0.5,
    "wr_completeness": 0.3,
    "wr_source_diversity": 0.1,
    "wr_efficiency": 0.1,
}


def aggregate_web_research_reward(
    dimension_rewards: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Aggregate multi-dimensional web research rewards into a single scalar.

    Args:
        dimension_rewards: Per-dimension reward values.
        weights: Optional weight overrides (default: accuracy=0.5, completeness=0.3,
                 diversity=0.1, efficiency=0.1).

    Returns:
        Weighted average reward (0–1). Returns 0.0 if no dimensions present.
    """
    if not dimension_rewards:
        return 0.0

    w = weights or _DEFAULT_WR_WEIGHTS
    total_weight = 0.0
    weighted_sum = 0.0

    for dim, val in dimension_rewards.items():
        dim_weight = w.get(dim, 0.0)
        weighted_sum += dim_weight * val
        total_weight += dim_weight

    if total_weight == 0.0:
        return 0.0
    return weighted_sum / total_weight


def score_query_strategy(
    web_research_results: list[dict],
) -> dict[str, float]:
    """Score the root LM's query decomposition strategy.

    Evaluates how well the model breaks complex questions into
    sub-queries across multiple web_research calls.

    Dimensions:
        query_count: Number of web_research calls
        query_diversity: Jaccard distance between consecutive queries
        source_yield: unique domains / total calls

    Args:
        web_research_results: List of web_research return dicts.

    Returns:
        Dict of strategy metric name -> value.
    """
    if not web_research_results:
        return {}

    queries: list[str] = []
    all_domains: set[str] = set()
    total_pages_synthesized = 0
    total_pages_irrelevant = 0
    for wr in web_research_results:
        if not isinstance(wr, dict):
            continue
        if wr.get("success") is False:
            continue
        pages_synthesized, pages_irrelevant = _web_research_relevance_counts(wr)
        total_pages_synthesized += pages_synthesized
        total_pages_irrelevant += pages_irrelevant
        q = wr.get("query", "")
        if q:
            queries.append(q)
        for url in _relevant_source_urls(wr.get("sources", [])):
            try:
                parsed = urlparse(url)
                if parsed.hostname:
                    all_domains.add(parsed.hostname)
            except Exception:
                pass

    n_calls = len(web_research_results)
    strategy: dict[str, float] = {
        "query_count": float(n_calls),
    }

    # Query diversity: average Jaccard distance between consecutive queries
    if len(queries) >= 2:
        distances: list[float] = []
        for i in range(1, len(queries)):
            tokens_a = set(queries[i - 1].lower().split())
            tokens_b = set(queries[i].lower().split())
            union = tokens_a | tokens_b
            if union:
                jaccard = len(tokens_a & tokens_b) / len(union)
                distances.append(1.0 - jaccard)  # distance = 1 - similarity
        strategy["query_diversity"] = sum(distances) / len(distances) if distances else 0.0
    else:
        strategy["query_diversity"] = 0.0

    # Source yield: unique domains per call
    strategy["source_yield"] = (
        len(all_domains) / n_calls if n_calls > 0 else 0.0
    ) * _web_research_relevance_scale(
        total_pages_synthesized=total_pages_synthesized,
        total_pages_irrelevant=total_pages_irrelevant,
    )

    return strategy


# ── Search-R1 Step 5: Scratchpad insight rewards ─────────────────────


_WEB_INSIGHT_KEYWORDS = frozenset(
    ["search", "found", "source", "website", "page", "url", "article"]
)


def compute_scratchpad_rewards(
    scratchpad_insights: list[dict],
    web_research_results: list[dict],
    answer: str,
    passed: bool,
) -> dict[str, float]:
    """Compute reward dimensions from scratchpad insights.

    Dimensions:
        sp_insight_count: Raw count of insights (float).
        sp_web_insight_ratio: Fraction of insights mentioning web-related
            keywords. Only computed when web_research was used.
        sp_answer_containment: Fraction of insight keywords that appear
            in the final answer. Measures whether the model actually USED
            its extracted insights.

    Returns empty dict if both scratchpad_insights and web_research_results
    are empty.
    """
    if not scratchpad_insights and not web_research_results:
        return {}

    rewards: dict[str, float] = {}

    insights = [e for e in scratchpad_insights if isinstance(e, dict)]
    rewards["sp_insight_count"] = float(len(insights))
    web_relevance_scale = _web_research_results_relevance_scale(web_research_results)

    # sp_web_insight_ratio: only meaningful when web_research was used
    if web_research_results and insights:
        web_related = 0
        for entry in insights:
            text = str(entry.get("insight", "")).lower()
            if any(kw in text for kw in _WEB_INSIGHT_KEYWORDS):
                web_related += 1
        rewards["sp_web_insight_ratio"] = (web_related / len(insights)) * web_relevance_scale
    elif web_research_results:
        # Web research used but no insights extracted
        rewards["sp_web_insight_ratio"] = 0.0

    # sp_answer_containment: do insight keywords appear in the answer?
    if insights and answer:
        answer_lower = answer.lower()
        # Collect meaningful keywords from all insights (length >= 4 to skip noise)
        insight_keywords: set[str] = set()
        for entry in insights:
            text = str(entry.get("insight", ""))
            for word in text.lower().split():
                cleaned = word.strip(".,;:!?\"'()-")
                if len(cleaned) >= 4:
                    insight_keywords.add(cleaned)

        if insight_keywords:
            matched = sum(1 for kw in insight_keywords if kw in answer_lower)
            rewards["sp_answer_containment"] = matched / len(insight_keywords)
        else:
            rewards["sp_answer_containment"] = 0.0
    elif insights:
        rewards["sp_answer_containment"] = 0.0

    return rewards
