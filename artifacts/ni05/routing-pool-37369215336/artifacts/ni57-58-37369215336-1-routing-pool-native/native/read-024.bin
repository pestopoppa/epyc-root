"""3-Way evaluation logic: _eval_single_config, evaluate_question_3way, ThreeWayResult.

Contains the core eval loop and the deduped ``_build_role_result`` helper
that replaces the previously copy-pasted RoleResult construction in
``_eval_single_config``'s first-attempt and retry paths.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from seeding_types import (
    ACTION_ARCHITECT,
    ACTION_SELF_DIRECT,
    ACTION_SELF_REPL,
    DEFAULT_TIMEOUT,
    HEAVY_PORTS,
    ROLE_PORT,
    RoleResult,
    VISION_ROLES,
    state,
)
from seeding_scoring import (
    _adaptive_timeout_s,
    _bump_timeout_from_observed,
    _classify_error,
    _forced_role_serving_mismatch,
    _inband_error_text,
    _is_coding_task,
    infra_failure_reason,
    score_answer_or_error,
)
from seeding_orchestrator import (
    _busy_heavy_ports,
    _call_orchestrator_with_slot_poll,
    _erase_slots,
    _force_erase_and_verify,
    _recover_heavy_ports_if_stuck,
)
from seeding_infra import _wait_for_heavy_models_idle
from seeding_rewards import (
    compute_tool_value,
    extract_web_research_telemetry,
    compute_web_research_rewards,
    compute_scratchpad_rewards,
    score_delegation_chain,
    score_query_strategy,
    stack_prior_architect_reward_roles,
    success_reward,
)
from seeding_telemetry import (
    lock_pressure_too_high as _telemetry_lock_pressure,
    recommended_timeout as _telemetry_timeout,
    record_outcome as _telemetry_record,
    should_skip as _telemetry_should_skip,
)

__all__ = [
    "ThreeWayResult",
    "_build_role_result",
    "_compute_3way_metadata",
    "_eval_single_config",
    "evaluate_question_3way",
    # Phase 5: dynamic per-role evaluation
    "evaluate_question_per_role",
]

logger = logging.getLogger("seed_specialist_routing")

if TYPE_CHECKING:
    import httpx

_TAP_PATH = "/mnt/raid0/llm/tmp/inference_tap.log"
_REPL_TAP_PATH = "/mnt/raid0/llm/tmp/repl_tap.log"
_NON_VL_ARCHITECT_FALLBACK = ("architect_general",)


def _non_vl_architect_roles_to_eval() -> list[str]:
    """Return live text architect roles for 3-way evaluation."""
    roles = stack_prior_architect_reward_roles()
    non_vl = sorted(role for role in roles if role.startswith("architect_"))
    return non_vl or list(_NON_VL_ARCHITECT_FALLBACK)


def _architect_result_order(available_roles: Any) -> list[str]:
    """Order architect results with live stack-prior roles first."""
    available = [str(role) for role in available_roles]
    available_set = set(available)
    live_order = [role for role in _non_vl_architect_roles_to_eval() if role in available_set]
    return live_order or available


def _heuristic_architect_role(prompt: str, available_roles: Any) -> str:
    """Pick the architect role implied by the coding/general heuristic."""
    ordered = _architect_result_order(available_roles)
    if not ordered:
        return ""
    if _is_coding_task(prompt):
        for role in ordered:
            if "code" in role.lower():
                return role
    if "architect_general" in ordered:
        return "architect_general"
    return ordered[0]


def _seed_role_concurrency_limit(n_roles: int) -> int:
    raw = os.environ.get("AUTOPILOT_SEED_ROLE_CONCURRENCY", "auto").strip().lower()
    if raw in {"", "auto", "0"}:
        return max(1, n_roles)
    try:
        return max(1, min(n_roles, int(raw)))
    except ValueError:
        logger.warning("invalid AUTOPILOT_SEED_ROLE_CONCURRENCY=%r; using auto", raw)
        return max(1, n_roles)


def _can_add_role_to_seed_wave(role_name: str, wave_roles: list[str]) -> bool:
    if not wave_roles:
        return True

    role_port = ROLE_PORT.get(role_name, 0)
    if role_port and any(ROLE_PORT.get(r, 0) == role_port for r in wave_roles):
        return False

    # _eval_single_config still contains a legacy all-heavy-port idle barrier.
    # Keep at most one heavy-port role per wave so the new fan-out does not
    # race that preflight or erase another heavy request's slots.
    if role_port in HEAVY_PORTS and any(ROLE_PORT.get(r, 0) in HEAVY_PORTS for r in wave_roles):
        return False

    # B wiring note (shape-keyed-contention-gating): this stays on the legacy
    # role-keyed pair_policy/nway_policy path DELIBERATELY. The placement-aware
    # seam (`seam_admit`) needs a CANDIDATE INSTANCE/placement, but wave packing
    # happens before any instance is chosen for these roles — there is no
    # placement to key on here. Shape-aware admission belongs at dispatch time
    # (the gate's `evaluate(..., candidate_topology_idx=...)` path), not at
    # wave-pack time. Do not call seam_admit here with a fabricated placement.
    try:
        from src.scheduling.contention import PairDecision, TrafficClass, nway_policy, pair_policy
        for active_role in wave_roles:
            if pair_policy(role_name, active_role, TrafficClass.BACKGROUND) != PairDecision.ALLOW:
                return False
        if nway_policy([*wave_roles, role_name], TrafficClass.BACKGROUND) != PairDecision.ALLOW:
            return False
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "seed concurrency matrix check failed for %s+%s: %s",
            role_name,
            wave_roles,
            exc,
        )
        return False

    return True


def _seed_role_waves(eval_roles: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    limit = _seed_role_concurrency_limit(len(eval_roles))
    if limit <= 1:
        return [[r] for r in eval_roles]

    waves: list[list[dict[str, Any]]] = []
    wave_names: list[list[str]] = []
    for role_info in eval_roles:
        role_name = role_info["name"]
        placed = False
        for idx, names in enumerate(wave_names):
            if len(names) >= limit:
                continue
            if _can_add_role_to_seed_wave(role_name, names):
                waves[idx].append(role_info)
                names.append(role_name)
                placed = True
                break
        if not placed:
            waves.append([role_info])
            wave_names.append([role_name])
    return waves


def _seed_queue_allowance_s() -> int:
    try:
        return max(0, int(os.environ.get("AUTOPILOT_SEED_QUEUE_ALLOWANCE_S", "90")))
    except (TypeError, ValueError):
        return 90


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _seed_request_timeout_s(inference_timeout_s: int) -> int:
    """Total client wait budget for a background seed request.

    The shared /chat contract clamps actual role execution to registry role
    timeout, so adding queue allowance here gives background requests room to
    sit at admission gates without changing API behavior.
    """
    return min(600, max(1, int(inference_timeout_s) + _seed_queue_allowance_s()))


def _role_base_timeout_s(role_info: dict[str, Any], fallback_timeout_s: int) -> int:
    raw = role_info.get("timeout_s") or fallback_timeout_s or DEFAULT_TIMEOUT
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return max(1, int(fallback_timeout_s or DEFAULT_TIMEOUT))


def _seed_telemetry_mode(mode: str) -> str:
    return mode or "natural"


def _is_timeout_result(rr: RoleResult, request_timeout_s: int) -> bool:
    err = (rr.error or "").lower()
    if "timeout" in err or "timed out" in err or "readtimeout" in err:
        return True
    return bool(
        rr.error_type == "infrastructure"
        and rr.elapsed_seconds >= max(request_timeout_s - 15, 5)
    )


def _log_delegation_diag(log_label: str, diag: dict[str, Any]) -> None:
    if not diag:
        return
    loops = diag.get("loops", "")
    break_reason = diag.get("break_reason", "")
    cap_reached = diag.get("cap_reached", False)
    repeated_edges = diag.get("repeated_edges", {}) or {}
    repeated_roles = diag.get("repeated_roles", {}) or {}
    infer_hops = diag.get("delegation_inference_hops")
    avg_prompt_ms = diag.get("avg_prompt_ms")
    avg_gen_ms = diag.get("avg_gen_ms")
    report_handles_count = diag.get("report_handles_count")
    report_handles = diag.get("report_handles", []) or []
    report_ids = [
        str(h.get("id", ""))
        for h in report_handles
        if isinstance(h, dict) and h.get("id")
    ]
    logger.info(
        "    [%s diag] loops=%s cap=%s break_reason=%s repeated_edges=%d repeated_roles=%d "
        "infer_hops=%s avg_prompt_ms=%s avg_gen_ms=%s report_handles=%s ids=%s",
        log_label,
        loops,
        cap_reached,
        break_reason or "none",
        len(repeated_edges),
        len(repeated_roles),
        infer_hops if infer_hops is not None else "n/a",
        avg_prompt_ms if avg_prompt_ms is not None else "n/a",
        avg_gen_ms if avg_gen_ms is not None else "n/a",
        report_handles_count if report_handles_count is not None else "n/a",
        ",".join(report_ids[:3]) if report_ids else "none",
    )


def _tap_size() -> int:
    """Current byte size of inference tap file (0 if missing)."""
    try:
        return os.path.getsize(_TAP_PATH)
    except OSError:
        return 0


def _repl_tap_size() -> int:
    """Current byte size of REPL tap file (0 if missing)."""
    try:
        return os.path.getsize(_REPL_TAP_PATH)
    except OSError:
        return 0


# ── ThreeWayResult dataclass ─────────────────────────────────────────


@dataclass
class ThreeWayResult:
    """Result from 3-way routing evaluation."""

    suite: str
    question_id: str
    prompt: str
    expected: str
    reference: str = ""
    timestamp: str = ""
    role_results: dict[str, RoleResult] = field(default_factory=dict)
    rewards: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    rewards_injected: int = 0
    rewards_delivery: dict[str, Any] = field(default_factory=dict)


# ── RoleResult builder (dedup helper) ────────────────────────────────


def _build_role_result(
    *,
    role: str,
    mode: str,
    resp: dict[str, Any],
    elapsed: float,
    expected: str,
    scoring_method: str,
    scoring_config: dict[str, Any],
    allow_delegation: bool | None = None,
) -> tuple[RoleResult, str]:
    """Build a RoleResult from orchestrator response, scoring the answer.

    Applies the REL-1 eval-honesty guards (mirroring eval_tower.py) so a
    failed/mis-served/unscoreable call becomes an EXCLUDED infrastructure row
    rather than a WRONG answer that injects a 0.0 reward into MemRL and poisons
    the learned router:

    * Guard 1 (in-band ``[ERROR: ...]`` answer with ``error=None``) is applied
      upstream in ``seeding_orchestrator._surface_inband_error`` (surfaced into
      ``resp["error"]``) and classified INFRASTRUCTURE by ``_classify_error``.
    * Guard 2 (forced-role serving mismatch) is applied here, gated on
      ``allow_delegation is False`` — the seeding ARCHITECT config runs with
      delegation ENABLED where ``routed_to != role`` is expected, so the guard
      MUST NOT fire there. See ``_forced_role_serving_mismatch``.
    * Scorer-unavailability (``ScoringUnavailableError`` / unknown method) is
      caught via ``score_answer_or_error`` and converted to an excluded row
      instead of crashing the seed run or silently dropping the question.

    Returns:
        (role_result, error_type) tuple.  error_type is one of
        "none", "infrastructure", or "task_failure".
    """
    answer = resp.get("answer", "")
    error = resp.get("error")

    # ── REL-1 Guard 1: in-band "[ERROR: ...]" answer with error=None ──
    # Normally surfaced upstream by seeding_orchestrator._surface_inband_error;
    # repeated here so _build_role_result is self-contained — any resp that
    # reaches scoring with an in-band banner is EXCLUDED as infrastructure,
    # never scored as a WRONG answer that would inject a 0.0 MemRL reward.
    if not error:
        inband = _inband_error_text(answer)
        if inband is not None:
            error = inband
            logger.error(
                "REL-1 in-band error surfaced as answer (role=%s): %s",
                role, inband[:200],
            )

    # ── REL-1 Guard 2: forced-role serving mismatch (delegation OFF only) ──
    if not error and allow_delegation is False:
        served_by = _forced_role_serving_mismatch(role, resp)
        if served_by is not None:
            error = f"forced_role_fallback: forced={role} served_by={served_by}"
            logger.error(
                "REL-1 forced-role integrity violation (role=%s served_by=%s) — "
                "excluding cross-role measurement (delegation disabled)",
                role, served_by,
            )

    # STRUCTURAL classification (2026-08-03 incident). `resp` is passed so the
    # shared classifier can read the transport facts recorded at the call site
    # — failure_reason / failure_provenance.class / _meta.reason / the HTTP
    # status / an empty non-error reply — instead of substring-matching the
    # error prose. Without `resp`, an HTTP 400 (per-slot context overflow), an
    # empty-message ReadTimeout and an unparseable body all classified as
    # `task_failure` and were scored as WRONG ANSWERS: absence reported as
    # failure. See src/autopilot_core/measurement_guards.py.
    error_type = _classify_error(error, resp)

    if error_type == "infrastructure":
        passed = None
        # An empty-message transport failure leaves `error` falsy, which would
        # otherwise sail through every `if error:` guard downstream. Give the
        # row a non-empty, self-describing error so it can never be mistaken
        # for a clean generation.
        if not str(error or "").strip():
            # ETR-3: measurement path — see seeding_scoring._classify_error.
            reason = (
                infra_failure_reason(resp, error=error, require_generation_evidence=True)
                or "infra_failed"
            )
            error = f"infra_failed: {reason} (role={role})"
            logger.error(
                "REL-1 infra failure with no error text (role=%s reason=%s) — "
                "excluding row rather than scoring an absent answer",
                role, reason,
            )
    elif error:
        passed = False
    else:
        # ── REL-1: scorer-unavailability → excluded row, never crash/drop ──
        passed, score_err = score_answer_or_error(
            answer, expected, scoring_method, scoring_config
        )
        if passed is None:
            error = score_err
            error_type = "infrastructure"
            logger.warning(
                "REL-1 scorer unavailable (role=%s method=%s): %s — excluding row",
                role, scoring_method, score_err,
            )

    rr = RoleResult(
        role=role,
        mode=mode,
        answer=answer or "",
        passed=bool(passed) if passed is not None else False,
        elapsed_seconds=elapsed,
        error=error,
        error_type=error_type,
        tokens_generated=resp.get("tokens_generated", 0),
        prompt_tokens=resp.get("tokens_used", 0) or resp.get("prompt_tokens", 0),
        tool_output_tokens=resp.get("tool_output_tokens", 0),
        tools_used=resp.get("tools_used", 0),
        tools_called=resp.get("tools_called", []),
        tool_chains=resp.get("tool_chains", []),
        delegation_events=resp.get("delegation_events", []),
        delegation_diagnostics=resp.get("delegation_diagnostics", {}),
        tools_success=resp.get("tools_success"),
        delegation_success=resp.get("delegation_success"),
        routed_to=resp.get("routed_to", ""),
        role_history=resp.get("role_history", []),
        predicted_tps=resp.get("predicted_tps", 0.0),
        generation_ms=resp.get("generation_ms", 0.0),
        tokens_generated_estimate=resp.get("tokens_generated_estimate", 0),
        backend_task_id=resp.get("backend_task_id", 0),
        slot_progress_source=resp.get("slot_progress_source", ""),
        # Orchestrator intelligence diagnostics
        cost_dimensions=resp.get("cost_dimensions", {}),
        think_harder_attempted=resp.get("think_harder_attempted", False),
        think_harder_succeeded=resp.get("think_harder_succeeded"),
        cheap_first_attempted=resp.get("cheap_first_attempted", False),
        cheap_first_passed=resp.get("cheap_first_passed"),
        grammar_enforced=resp.get("grammar_enforced", False),
        parallel_tools_used=resp.get("parallel_tools_used", False),
        cache_affinity_bonus=resp.get("cache_affinity_bonus", 0.0),
        # SkillBank integration
        skills_retrieved=resp.get("skills_retrieved", 0),
        skill_ids=resp.get("skill_ids", []),
        # Timing fields
        cache_stats=resp.get("cache_stats"),
        prompt_eval_ms=resp.get("prompt_eval_ms", 0.0),
        http_overhead_ms=resp.get("http_overhead_ms", 0.0),
        # Context window management (C1/C3) and budget tracking (R1)
        budget_diagnostics=resp.get("budget_diagnostics", {}),
        session_persistence=resp.get("session_persistence", {}),
        tool_results_cleared=resp.get("tool_results_cleared", 0),
        compaction_triggered=resp.get("compaction_triggered", False),
        compaction_tokens_saved=resp.get("compaction_tokens_saved", 0),
        compression_metrics=resp.get("compression_metrics", {}),
        think_harder_expected_roi=resp.get("think_harder_expected_roi", 0.0),
        # Web research telemetry (Search-R1)
        web_research_results=resp.get("web_research_results", []),
        # Scratchpad insights (Search-R1 Step 5)
        scratchpad_insights=resp.get("scratchpad_insights", []),
        # Factual-risk shadow telemetry (NIB2-35, routing-intelligence Phase 5)
        factual_risk_score=float(resp.get("factual_risk_score", 0.0) or 0.0),
        factual_risk_band=str(resp.get("factual_risk_band", "") or ""),
        # Difficulty signal shadow telemetry (NIB2-35, reasoning-compression Action 3)
        difficulty_score=float(resp.get("difficulty_score", 0.0) or 0.0),
        difficulty_band=str(resp.get("difficulty_band", "") or ""),
        # 2026-05-23 Phase 4 — exogenous-restart resilience.
        # resp["_meta"] is set by call_orchestrator_forced when a watcher is
        # active; absent when the legacy code path ran (no autopilot watcher).
        exogenous_recovered=bool((resp.get("_meta") or {}).get("exogenous_recovered", False)),
        exogenous_unrecovered=bool((resp.get("_meta") or {}).get("exogenous_unrecovered", False)),
        external_restart=bool((resp.get("_meta") or {}).get("external_restart", False)),
        retry_count=int((resp.get("_meta") or {}).get("retry_count", 0)),
        resilient_meta=dict(resp.get("_meta") or {}),
    )
    return rr, error_type


# ── Core eval function ───────────────────────────────────────────────


def _eval_single_config(
    prompt: str,
    expected: str,
    scoring_method: str,
    scoring_config: dict,
    role: str,
    mode: str,
    url: str,
    timeout: int,
    client: "httpx.Client",
    allow_delegation: bool,
    image_path: str = "",
    log_label: str = "",
    format_fn=None,
    watcher: Any | None = None,
) -> tuple[RoleResult, dict]:
    """Call the orchestrator, score, build RoleResult, and handle infra errors.

    Returns:
        (role_result, raw_response_dict) tuple.
    """
    port = ROLE_PORT.get(role, 0)
    did_recover_precheck = False

    # Proactive slot erase: clear ALL slots (including idle ones) to flush
    # stale KV cache from previous questions and prevent cross-question
    # context contamination (e.g. USACO text leaking into GPQA answers).
    if port > 0:
        _erase_slots(port, all_slots=True)

    if port in HEAVY_PORTS:
        idle_wait_cap = max(30, min(120, int(timeout // 2) if timeout else 120))
        _wait_for_heavy_models_idle(max_wait=idle_wait_cap)

        busy_ports = _busy_heavy_ports(timeout_s=2.0)
        if busy_ports:
            for bp in busy_ports:
                _erase_slots(bp)
            time.sleep(1.0)
            still_busy = _busy_heavy_ports(timeout_s=2.0)
            if still_busy:
                did_recover_precheck = _recover_heavy_ports_if_stuck(url, still_busy)

    logger.info(f"  → {log_label} ({role}:{mode}, timeout={timeout}s)...")
    tap_before = _tap_size()
    repl_tap_before = _repl_tap_size()
    resp, elapsed, slot_progress = _call_orchestrator_with_slot_poll(
        prompt=prompt,
        force_role=role,
        force_mode=mode,
        url=url,
        timeout=timeout,
        image_path=image_path,
        cache_prompt=False,
        client=client,
        allow_delegation=allow_delegation,
        log_label=log_label,
        poll_port=port,
        session_id=state.session_id,
        scoring_method=scoring_method,
        watcher=watcher,
    )

    # Merge slot progress into response
    max_decoded = int(slot_progress.get("max_decoded", 0) or 0)
    if max_decoded > 0:
        resp["tokens_generated_estimate"] = max_decoded
    resp["backend_task_id"] = int(slot_progress.get("task_id", 0) or 0)
    resp["slot_progress_source"] = str(slot_progress.get("source", "") or "")

    rr, error_type = _build_role_result(
        role=role, mode=mode, resp=resp, elapsed=elapsed,
        expected=expected, scoring_method=scoring_method,
        scoring_config=scoring_config,
        allow_delegation=allow_delegation,
    )
    _log_delegation_diag(log_label, rr.delegation_diagnostics)
    tap_after = _tap_size()
    rr.tap_offset_bytes = tap_before
    rr.tap_length_bytes = tap_after - tap_before
    repl_tap_after = _repl_tap_size()
    rr.repl_tap_offset_bytes = repl_tap_before
    rr.repl_tap_length_bytes = repl_tap_after - repl_tap_before

    # Retry logic for zero-token infra failures on heavy paths
    if error_type == "infrastructure" and resp.get("tokens_generated", 0) == 0:
        error_msg = (resp.get("error") or "").lower()
        # Distinguish client socket timeouts (httpx ReadTimeout/ConnectTimeout)
        # from HTTP 5xx status errors (504 Gateway Timeout, 503 Service Unavailable).
        # HTTP 5xx are server-side decisions — the backend may have been temporarily
        # overloaded, and a retry after slot recovery can succeed.
        # Client timeouts mean the model was genuinely too slow; retrying wastes budget.
        is_http_status_error = "server error '" in error_msg  # httpx.HTTPStatusError
        is_client_timeout = not is_http_status_error and (
            "timed out" in error_msg or "readtimeout" in error_msg or "connecttimeout" in error_msg
        )
        target_port = ROLE_PORT.get(role, 0)
        if target_port:
            _force_erase_and_verify(target_port)
        if is_client_timeout:
            # True client socket timeout — server was processing but too slow;
            # retrying with the same budget just doubles elapsed time.
            logger.info(f"  [skip-retry] {log_label} client timeout — not retrying")
        elif port in HEAVY_PORTS and not did_recover_precheck:
            busy_now = _busy_heavy_ports(timeout_s=2.0)
            if _recover_heavy_ports_if_stuck(url, busy_now):
                logger.info(f"  [retry] {log_label} retry after recovery")
                resp2, elapsed2, slot_progress2 = _call_orchestrator_with_slot_poll(
                    prompt=prompt,
                    force_role=role,
                    force_mode=mode,
                    url=url,
                    timeout=timeout,
                    image_path=image_path,
                    cache_prompt=False,
                    client=client,
                    allow_delegation=allow_delegation,
                    log_label=log_label,
                    poll_port=port,
                    session_id=state.session_id,
                    scoring_method=scoring_method,
                    watcher=watcher,
                )
                max_decoded2 = int(slot_progress2.get("max_decoded", 0) or 0)
                max_decoded = max(max_decoded, max_decoded2)
                if max_decoded > 0:
                    resp2["tokens_generated_estimate"] = max_decoded
                resp2["backend_task_id"] = int(slot_progress2.get("task_id", 0) or 0) or int(
                    slot_progress.get("task_id", 0) or 0
                )
                resp2["slot_progress_source"] = (
                    str(slot_progress2.get("source", "") or "")
                    or str(slot_progress.get("source", "") or "")
                )

                rr, error_type = _build_role_result(
                    role=role, mode=mode, resp=resp2,
                    elapsed=elapsed + elapsed2,
                    expected=expected, scoring_method=scoring_method,
                    scoring_config=scoring_config,
                    allow_delegation=allow_delegation,
                )
                _log_delegation_diag(f"{log_label}:retry", rr.delegation_diagnostics)
                tap_after = _tap_size()
                rr.tap_offset_bytes = tap_before
                rr.tap_length_bytes = tap_after - tap_before
                repl_tap_after = _repl_tap_size()
                rr.repl_tap_offset_bytes = repl_tap_before
                rr.repl_tap_length_bytes = repl_tap_after - repl_tap_before
                resp = resp2

    if format_fn is not None:
        final_error = rr.error
        final_passed = rr.passed
        for line in format_fn(log_label, final_passed, final_error, rr.elapsed_seconds, resp,
                              infra=(error_type == "infrastructure")):
            logger.info(line)

    return rr, resp


# ── 3-Way metadata computation ───────────────────────────────────────


def _compute_3way_metadata(
    role_results: dict[str, RoleResult],
    arch_results: dict[str, dict[str, Any]],
    prompt: str,
    suite: str,
    passed_direct: bool,
    passed_repl: bool,
    self_role: str,
    self_direct_mode: str,
    self_repl_mode: str,
    arch_mode: str,
) -> dict[str, Any]:
    """Compute metadata dict (tool value, cost metrics, architect eval)."""
    metadata = compute_tool_value(passed_direct, passed_repl)
    metadata["suite"] = suite
    metadata["cache_disabled"] = True

    # Determine best architect (prefer generation_ms over elapsed)
    best_arch = None
    arch_result_order = _architect_result_order(arch_results.keys())
    for ar in arch_result_order:
        res = arch_results[ar]
        if res["passed"] is True:
            if best_arch is None:
                best_arch = ar
            else:
                cur_time = res.get("generation_ms") or (res["elapsed_seconds"] * 1000)
                best_time = arch_results[best_arch].get("generation_ms") or (
                    arch_results[best_arch]["elapsed_seconds"] * 1000
                )
                if cur_time < best_time:
                    best_arch = ar
    if best_arch is None:
        for ar in arch_result_order:
            res = arch_results[ar]
            if res["passed"] is not None:
                best_arch = ar
                break

    metadata["architect_eval"] = {
        "by_role": {role: arch_results[role] for role in arch_result_order},
        "general": arch_results.get("architect_general"),
        "best": best_arch,
        "heuristic_would_pick": _heuristic_architect_role(prompt, arch_result_order),
    }
    metadata["architect_role"] = best_arch or ""

    direct_key = f"{self_role}:{self_direct_mode}"
    repl_key = f"{self_role}:{self_repl_mode}"
    metadata["cost_metrics"] = {
        ACTION_SELF_DIRECT: {
            "elapsed_seconds": role_results[direct_key].elapsed_seconds,
            "tokens_generated": role_results[direct_key].tokens_generated,
            "tokens_generated_estimate": role_results[direct_key].tokens_generated_estimate,
            "predicted_tps": role_results[direct_key].predicted_tps,
            "prompt_eval_ms": role_results[direct_key].prompt_eval_ms,
            "generation_ms": role_results[direct_key].generation_ms,
            "backend_task_id": role_results[direct_key].backend_task_id,
            "slot_progress_source": role_results[direct_key].slot_progress_source,
        },
        ACTION_SELF_REPL: {
            "elapsed_seconds": role_results[repl_key].elapsed_seconds,
            "tokens_generated": role_results[repl_key].tokens_generated,
            "tokens_generated_estimate": role_results[repl_key].tokens_generated_estimate,
            "predicted_tps": role_results[repl_key].predicted_tps,
            "prompt_eval_ms": role_results[repl_key].prompt_eval_ms,
            "generation_ms": role_results[repl_key].generation_ms,
            "tools_used": role_results[repl_key].tools_used,
            "backend_task_id": role_results[repl_key].backend_task_id,
            "slot_progress_source": role_results[repl_key].slot_progress_source,
        },
    }
    if best_arch:
        arch_key = f"{best_arch}:{arch_mode}"
        metadata["cost_metrics"][ACTION_ARCHITECT] = {
            "elapsed_seconds": arch_results[best_arch]["elapsed_seconds"],
            "tokens_generated": role_results[arch_key].tokens_generated,
            "tokens_generated_estimate": role_results[arch_key].tokens_generated_estimate,
            "predicted_tps": role_results[arch_key].predicted_tps,
            "prompt_eval_ms": role_results[arch_key].prompt_eval_ms,
            "generation_ms": role_results[arch_key].generation_ms,
            "role_history": role_results[arch_key].role_history,
            "backend_task_id": role_results[arch_key].backend_task_id,
            "slot_progress_source": role_results[arch_key].slot_progress_source,
        }

    infra_flags = [
        rr.error_type == "infrastructure"
        for rr in role_results.values()
        if rr is not None
    ]
    metadata["all_infra"] = bool(infra_flags) and all(infra_flags)

    # ── Step 0: Web research baseline metrics ──
    wr_configs_using: list[str] = []
    wr_total_calls = 0
    for config_key, rr in role_results.items():
        if rr is None:
            continue
        wr_count = sum(1 for t in rr.tools_called if t == "web_research")
        if wr_count > 0:
            wr_configs_using.append(config_key)
            wr_total_calls += wr_count
    metadata["web_research_baseline"] = {
        "triggered": wr_total_calls > 0,
        "call_count": wr_total_calls,
        "configs_using": wr_configs_using,
    }

    # ── Step 2c: Web research rewards and telemetry per config ──
    wr_rewards: dict[str, dict] = {}
    wr_telemetry: dict[str, dict] = {}
    wr_strategy: dict[str, dict] = {}
    for config_key, rr in role_results.items():
        if rr is None or not rr.web_research_results:
            continue
        telemetry = extract_web_research_telemetry(rr.web_research_results)
        if telemetry.call_count == 0:
            continue
        dim_rewards = compute_web_research_rewards(telemetry, rr.passed)
        strategy = score_query_strategy(rr.web_research_results)
        wr_rewards[config_key] = dim_rewards
        wr_telemetry[config_key] = {
            "call_count": telemetry.call_count,
            "total_pages_fetched": telemetry.total_pages_fetched,
            "total_pages_synthesized": telemetry.total_pages_synthesized,
            "total_elapsed_ms": telemetry.total_elapsed_ms,
            "unique_domains": telemetry.unique_domains,
            "queries": telemetry.queries,
        }
        wr_strategy[config_key] = strategy
    if wr_rewards:
        metadata["web_research_rewards"] = wr_rewards
    if wr_telemetry:
        metadata["web_research_telemetry"] = wr_telemetry
    if wr_strategy:
        metadata["web_research_strategy"] = wr_strategy

    # ── Step 5: Scratchpad insight rewards ──
    sp_rewards: dict[str, dict] = {}
    for config_key, rr in role_results.items():
        if rr is None:
            continue
        if not rr.scratchpad_insights and not rr.web_research_results:
            continue
        sp = compute_scratchpad_rewards(
            rr.scratchpad_insights, rr.web_research_results, rr.answer, rr.passed,
        )
        if sp:
            sp_rewards[config_key] = sp
    if sp_rewards:
        metadata["scratchpad_rewards"] = sp_rewards

    return metadata


# ── 3-Way evaluation ─────────────────────────────────────────────────


def evaluate_question_3way(
    prompt_info: dict,
    url: str,
    timeout: int,
    client: "httpx.Client",
    dry_run: bool = False,
    cooldown_s: float = 0.0,
) -> tuple[dict[str, RoleResult], dict[str, float], dict[str, Any]]:
    """Evaluate one question across the 3-way routing matrix.

    Test configurations:
    1. SELF:direct - Frontdoor without tools (direct mode)
    2. SELF:repl - Frontdoor with tools, delegation disabled
    3. ARCHITECT - Architect with full delegation freedom

    WORKER is scored indirectly via delegation chains.
    """
    prompt = prompt_info["prompt"]
    expected = prompt_info.get("expected", "")
    scoring_method = prompt_info.get("scoring_method", "exact_match")
    scoring_config = prompt_info.get("scoring_config", {})
    suite = prompt_info["suite"]
    image_path = prompt_info.get("image_path", "")
    is_vl = bool(image_path)

    role_results: dict[str, RoleResult] = {}

    # Flush KV cache from ALL model servers between questions to prevent
    # cross-question context contamination.  Without this, idle slots
    # retain stale KV state from the previous question (e.g. USACO text
    # leaking into GPQA organic chemistry answers).
    for _port in set(ROLE_PORT.values()):
        if _port > 0:
            _erase_slots(_port, all_slots=True)

    from eval_log_format import (
        format_self_direct, format_self_repl, format_architect_result,
        format_reward_skip, format_all_infra_skip,
    )

    # ── VL-aware role mapping ──
    if is_vl:
        self_role = "worker_vision"
        self_direct_mode = "direct"
        self_repl_mode = "repl"
        arch_role = "vision_escalation"
    else:
        self_role = "frontdoor"
        self_direct_mode = "direct"
        self_repl_mode = "repl"
        arch_role = None

    # ── Configuration 1: SELF:direct ──
    timeout_direct = _adaptive_timeout_s(
        role=self_role,
        mode=self_direct_mode,
        prompt=prompt,
        is_vl=is_vl,
        hard_timeout_s=timeout,
    )
    rr_direct, _ = _eval_single_config(
        prompt, expected, scoring_method, scoring_config,
        role=self_role, mode=self_direct_mode,
        url=url, timeout=timeout_direct, client=client,
        allow_delegation=False, image_path=image_path,
        log_label=ACTION_SELF_DIRECT, format_fn=format_self_direct,
    )
    role_results[f"{self_role}:{self_direct_mode}"] = rr_direct
    if cooldown_s > 0:
        time.sleep(cooldown_s)

    # ── Cleanup + retry: ensure port is idle before next strategy ──
    # If SELF:direct hit an infra error, attempt one retry after recovery.
    # This gives frontdoor:direct the same retry parity that architect configs
    # get inside _eval_single_config (which only retries non-timeout errors).
    if rr_direct.error_type == "infrastructure" or rr_direct.error:
        direct_port = ROLE_PORT.get(self_role, 0)
        if direct_port in HEAVY_PORTS:
            _force_erase_and_verify(direct_port)
            # Retry once if the error was an HTTP 5xx (not client socket timeout)
            direct_error_msg = (rr_direct.error or "").lower()
            is_http_5xx = "server error '" in direct_error_msg
            if is_http_5xx:
                busy_now = _busy_heavy_ports(timeout_s=2.0)
                if not busy_now or _recover_heavy_ports_if_stuck(url, busy_now):
                    logger.info(f"  [retry] {ACTION_SELF_DIRECT} retry after 5xx recovery")
                    rr_direct_retry, _ = _eval_single_config(
                        prompt, expected, scoring_method, scoring_config,
                        role=self_role, mode=self_direct_mode,
                        url=url, timeout=timeout_direct, client=client,
                        allow_delegation=False, image_path=image_path,
                        log_label=f"{ACTION_SELF_DIRECT}:retry",
                        format_fn=format_self_direct,
                    )
                    if rr_direct_retry.error_type != "infrastructure":
                        rr_direct = rr_direct_retry
                        role_results[f"{self_role}:{self_direct_mode}"] = rr_direct
                        logger.info(f"  [retry] {ACTION_SELF_DIRECT} retry succeeded")

    # ── Configuration 2: SELF:repl ──
    timeout_repl = _adaptive_timeout_s(
        role=self_role,
        mode=self_repl_mode,
        prompt=prompt,
        is_vl=is_vl,
        hard_timeout_s=timeout,
    )
    if rr_direct.error_type != "infrastructure":
        timeout_repl = _bump_timeout_from_observed(
            current_s=timeout_repl,
            observed_s=rr_direct.elapsed_seconds,
            factor=2.2 if not is_vl else 1.8,
            slack_s=30,
            hard_timeout_s=timeout,
            role_cap_s=300 if not is_vl else 260,
        )
    rr_repl, _ = _eval_single_config(
        prompt, expected, scoring_method, scoring_config,
        role=self_role, mode=self_repl_mode,
        url=url, timeout=timeout_repl, client=client,
        allow_delegation=False, image_path=image_path,
        log_label=ACTION_SELF_REPL, format_fn=format_self_repl,
    )
    role_results[f"{self_role}:{self_repl_mode}"] = rr_repl
    if cooldown_s > 0:
        time.sleep(cooldown_s)

    # ── Configuration 3: ARCHITECT (dual evaluation) ──
    if is_vl:
        arch_roles_to_eval = [arch_role]
    else:
        arch_roles_to_eval = _non_vl_architect_roles_to_eval()

    arch_results: dict[str, dict[str, Any]] = {}
    arch_mode = "direct" if is_vl else "delegated"

    for ar in arch_roles_to_eval:
        timeout_arch = _adaptive_timeout_s(
            role=ar,
            mode=arch_mode,
            prompt=prompt,
            is_vl=is_vl,
            hard_timeout_s=timeout,
        )
        observed_base = rr_direct.elapsed_seconds
        if rr_repl.error_type != "infrastructure" and rr_repl.elapsed_seconds > observed_base:
            observed_base = rr_repl.elapsed_seconds
        timeout_arch = _bump_timeout_from_observed(
            current_s=timeout_arch,
            observed_s=observed_base,
            factor=4.0 if not is_vl else 2.5,
            slack_s=60 if not is_vl else 40,
            hard_timeout_s=timeout,
            role_cap_s=max(540, int(timeout)) if not is_vl else 360,
        )
        rr_arch, resp_arch = _eval_single_config(
            prompt, expected, scoring_method, scoring_config,
            role=ar, mode=arch_mode,
            url=url, timeout=timeout_arch, client=client,
            allow_delegation=not is_vl, image_path=image_path,
            log_label=ACTION_ARCHITECT,
            format_fn=lambda label, passed, error, elapsed, resp, infra=False: format_architect_result(label, passed, error, elapsed, resp),
        )
        role_results[f"{ar}:{arch_mode}"] = rr_arch
        if cooldown_s > 0:
            time.sleep(cooldown_s)

        passed_arch = None if rr_arch.error_type == "infrastructure" else rr_arch.passed
        arch_results[ar] = {
            "passed": passed_arch,
            "elapsed_seconds": rr_arch.elapsed_seconds,
            "tokens_generated": rr_arch.tokens_generated,
            "predicted_tps": rr_arch.predicted_tps,
            "generation_ms": rr_arch.generation_ms,
            "tools_used": rr_arch.tools_used,
            "tools_called": rr_arch.tools_called,
            "role_history": rr_arch.role_history,
            "error": rr_arch.error,
            "error_type": rr_arch.error_type,
        }

    # ── Compute 3-way rewards (binary for faithful P(success)) ──
    passed_direct = rr_direct.passed
    passed_repl = rr_repl.passed
    error_type_direct = rr_direct.error_type
    error_type_repl = rr_repl.error_type

    rewards: dict[str, float] = {}

    if error_type_direct == "infrastructure":
        for line in format_reward_skip(ACTION_SELF_DIRECT):
            logger.info(line)
    else:
        rewards[ACTION_SELF_DIRECT] = success_reward(passed_direct)

    if error_type_repl == "infrastructure":
        for line in format_reward_skip(ACTION_SELF_REPL):
            logger.info(line)
    else:
        rewards[ACTION_SELF_REPL] = success_reward(passed_repl)

    valid_results = {k: v for k, v in arch_results.items() if v["passed"] is not None}
    if valid_results:
        passed_arch_any = any(v["passed"] for v in valid_results.values())
        rewards[ACTION_ARCHITECT] = success_reward(passed_arch_any)
    else:
        for line in format_all_infra_skip(ACTION_ARCHITECT):
            logger.info(line)

    worker_rewards = score_delegation_chain(role_results)
    rewards.update(worker_rewards)

    # ── Metadata ──
    metadata = _compute_3way_metadata(
        role_results, arch_results, prompt, suite,
        passed_direct, passed_repl,
        self_role, self_direct_mode, self_repl_mode, arch_mode,
    )

    # ── REL-1 offline re-scoring context ──
    # The per-role raw ``answer`` is already persisted via asdict(RoleResult)
    # into the checkpoint JSONL, but the ThreeWayResult truncates ``expected``
    # to 200 chars and the scoring method/config were not stored at all —
    # without them a completed seed run cannot be re-scored offline when the
    # scorer is fixed or a parse-failure is suspected (the exact capability the
    # architect bench has via architect_bench_rescore). Persist the untruncated
    # scoring context so seed artifacts are re-scorable without re-inference.
    metadata["scoring_context"] = {
        "expected": expected,
        "scoring_method": scoring_method,
        "scoring_config": scoring_config,
    }

    for action, reward in sorted(rewards.items()):
        logger.info(f"    reward[{action}] = {reward:.1f}")

    return role_results, rewards, metadata


# ── Phase 5: Dynamic per-role evaluation ─────────────────────────────


def _interleave_roles(roles: list[dict]) -> list[dict]:
    """Interleave heavy and light roles to reduce heavy-model contention.

    Also separates roles that share the same port (e.g., worker_general
    and worker_math both on 8082) to avoid back-to-back slot conflicts.
    """
    heavy = [r for r in roles if r["is_heavy"]]
    light = [r for r in roles if not r["is_heavy"]]
    result: list[dict] = []
    hi, li = 0, 0
    while hi < len(heavy) or li < len(light):
        if hi < len(heavy):
            result.append(heavy[hi])
            hi += 1
        if li < len(light):
            result.append(light[li])
            li += 1
    return result


def evaluate_question_per_role(
    prompt_info: dict,
    active_roles: list[dict],
    url: str,
    timeout: int,
    client: "httpx.Client",
    dry_run: bool = False,
    watcher: Any | None = None,
) -> tuple[dict[str, RoleResult], dict[str, float], dict[str, Any]]:
    """Evaluate one question across all active roles dynamically.

    Each role is tested with force_role=role_name and force_mode=""
    (natural mode — the orchestrator's _select_mode() chooses direct
    or repl based on question characteristics).  All roles can
    delegate/escalate freely (allow_delegation=True).

    Returns:
        (role_results, rewards, metadata) where:
        - role_results: {role_name: RoleResult} for each tested role
        - rewards: {role_name: 0.0|1.0} binary per-role rewards
        - metadata: {suite, cost_metrics, ...}
    """
    prompt = prompt_info["prompt"]
    expected = prompt_info.get("expected", "")
    scoring_method = prompt_info.get("scoring_method", "exact_match")
    scoring_config = prompt_info.get("scoring_config", {})
    suite = prompt_info["suite"]
    image_path = prompt_info.get("image_path", "")
    is_vl = bool(image_path)

    role_results: dict[str, RoleResult] = {}
    rewards: dict[str, float] = {}
    cost_metrics: dict[str, dict] = {}
    skipped_roles: dict[str, str] = {}

    # Filter roles for VL capability
    if is_vl:
        eval_roles = [r for r in active_roles if r["name"] in VISION_ROLES]
    else:
        eval_roles = [r for r in active_roles if r["name"] not in VISION_ROLES]

    if not eval_roles:
        logger.warning("No eligible roles for suite=%s is_vl=%s", suite, is_vl)
        return role_results, rewards, {"suite": suite, "all_infra": True}

    # Interleave heavy/light to reduce contention
    eval_roles = _interleave_roles(eval_roles)

    logger.info(
        "  Per-role eval: %d roles [%s]",
        len(eval_roles),
        ", ".join(r["name"] for r in eval_roles),
    )

    waves = _seed_role_waves(eval_roles)
    if len(waves) > 1 or any(len(w) > 1 for w in waves):
        logger.info(
            "  Seed role waves: %s",
            " | ".join("+".join(r["name"] for r in wave) for wave in waves),
        )

    question_start = time.perf_counter()
    per_question_budget_s = _env_float("SEEDING_PER_QUESTION_BUDGET_S", 600.0)
    roles_started = 0

    def _run_role(
        role_info: dict[str, Any],
        role_client: "httpx.Client",
    ) -> tuple[str, RoleResult, dict, int, int, str]:
        role_name = role_info["name"]
        telemetry_mode = _seed_telemetry_mode("")

        base_timeout = _role_base_timeout_s(role_info, timeout)
        # Adaptive timeout per role. Base comes from model_registry.yaml;
        # telemetry may raise it if observed P95 needs more headroom.
        role_timeout = _telemetry_timeout(role_name, telemetry_mode, base_timeout)
        role_timeout = _adaptive_timeout_s(
            role=role_name,
            mode="repl",  # Conservative default for timeout estimation
            prompt=prompt,
            is_vl=is_vl,
            hard_timeout_s=role_timeout,
        )
        request_timeout = _seed_request_timeout_s(role_timeout)
        if request_timeout != role_timeout:
            logger.info(
                "  → %s timeout budget: inference=%ss total_with_queue=%ss",
                role_name,
                role_timeout,
                request_timeout,
            )

        rr, resp = _eval_single_config(
            prompt=prompt,
            expected=expected,
            scoring_method=scoring_method,
            scoring_config=scoring_config,
            role=role_name,
            mode="",                  # Natural mode — orchestrator decides
            url=url,
            timeout=request_timeout,
            client=role_client,
            allow_delegation=True,    # All roles can delegate/escalate
            image_path=image_path,
            log_label=role_name,
            watcher=watcher,
        )

        return role_name, rr, resp, role_timeout, request_timeout, telemetry_mode

    for wave in waves:
        if state.shutdown:
            break

        if roles_started > 0 and per_question_budget_s > 0:
            spent = time.perf_counter() - question_start
            if spent >= per_question_budget_s:
                for role_info in wave:
                    skipped_roles[role_info["name"]] = (
                        f"question budget exhausted ({spent:.0f}s >= {per_question_budget_s:.0f}s)"
                    )
                logger.info(
                    "  → remaining seed roles SKIPPED — question budget exhausted "
                    "(%.0fs >= %.0fs)",
                    spent,
                    per_question_budget_s,
                )
                continue

        runnable_wave: list[dict[str, Any]] = []
        for role_info in wave:
            role_name = role_info["name"]
            telemetry_mode = _seed_telemetry_mode("")
            skip, reason = _telemetry_should_skip(role_name, telemetry_mode)
            if skip:
                skipped_roles[role_name] = reason
                logger.info("  → %s SKIPPED — %s", role_name, reason)
                continue

            port = ROLE_PORT.get(role_name, 0)
            if port in HEAVY_PORTS and roles_started > 0:
                pressure, why = _telemetry_lock_pressure(min_holder_age_s=60.0)
                if pressure:
                    skipped_roles[role_name] = f"heavy lock pressure: {why}"
                    logger.info(
                        "  → %s SKIPPED — heavy lock under pressure (%s)",
                        role_name,
                        why,
                    )
                    continue

            runnable_wave.append(role_info)

        if not runnable_wave:
            continue

        wave_outputs: dict[str, tuple[RoleResult, dict, int, int, str]] = {}
        if len(runnable_wave) <= 1:
            role_name, rr, resp, role_timeout, request_timeout, telemetry_mode = _run_role(
                runnable_wave[0],
                client,
            )
            wave_outputs[role_name] = (rr, resp, role_timeout, request_timeout, telemetry_mode)
            roles_started += 1
        else:
            max_workers = min(len(runnable_wave), _seed_role_concurrency_limit(len(eval_roles)))
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="seed-role",
            ) as ex:
                futs: dict[
                    concurrent.futures.Future[tuple[str, RoleResult, dict, int, int, str]],
                    str,
                ] = {}
                for role_info in runnable_wave:
                    role_name = role_info["name"]

                    def _worker(
                        ri: dict[str, Any],
                    ) -> tuple[str, RoleResult, dict, int, int, str]:
                        import httpx

                        with httpx.Client(timeout=max(timeout, DEFAULT_TIMEOUT)) as role_client:
                            return _run_role(ri, role_client)

                    futs[ex.submit(_worker, role_info)] = role_name
                for fut in concurrent.futures.as_completed(futs):
                    role_name, rr, resp, role_timeout, request_timeout, telemetry_mode = (
                        fut.result()
                    )
                    wave_outputs[role_name] = (
                        rr,
                        resp,
                        role_timeout,
                        request_timeout,
                        telemetry_mode,
                    )
                    roles_started += 1

        for role_info in runnable_wave:
            role_name = role_info["name"]
            rr, resp, role_timeout, request_timeout, telemetry_mode = wave_outputs[role_name]
            role_results[role_name] = rr
            _telemetry_record(
                role_name,
                telemetry_mode,
                rr.elapsed_seconds,
                _is_timeout_result(rr, request_timeout),
            )

            # Cost metrics for this role
            cost_metrics[role_name] = {
                "elapsed_seconds": rr.elapsed_seconds,
                "tokens_generated": rr.tokens_generated,
                "predicted_tps": rr.predicted_tps,
                "prompt_eval_ms": rr.prompt_eval_ms,
                "generation_ms": rr.generation_ms,
                "tools_used": rr.tools_used,
                "inference_timeout_s": role_timeout,
                "request_timeout_s": request_timeout,
            }

            # Binary reward (skip infrastructure errors)
            if rr.error_type == "infrastructure":
                logger.info(
                    "    [INFRA_SKIP] %s error=%r elapsed=%.1fs task=%s "
                    "decoded=%s source=%s",
                    role_name,
                    rr.error,
                    rr.elapsed_seconds,
                    rr.backend_task_id,
                    rr.tokens_generated_estimate,
                    rr.slot_progress_source or "none",
                )
            else:
                rewards[role_name] = success_reward(rr.passed)

    # Metadata
    metadata: dict[str, Any] = {
        "suite": suite,
        "cost_metrics": cost_metrics,
        "all_infra": all(
            rr.error_type == "infrastructure" for rr in role_results.values()
        ),
        "roles_tested": list(role_results.keys()),
        "roles_skipped": skipped_roles,
    }

    # 2026-05-23 Phase 4 — surface aggregated exogenous-restart info so
    # Seeder.run_batch can roll up SeederBatchResult counters.
    metadata["exogenous_recovered_roles"] = [
        n for n, rr in role_results.items() if rr.exogenous_recovered
    ]
    metadata["exogenous_unrecovered_roles"] = [
        n for n, rr in role_results.items() if rr.exogenous_unrecovered
    ]
    metadata["external_restart_roles"] = [
        n for n, rr in role_results.items() if rr.external_restart
    ]
    metadata["exogenous_marker_log"] = [
        rr.resilient_meta.get("marker_changes", {})
        for rr in role_results.values()
        if (rr.exogenous_recovered or rr.exogenous_unrecovered) and rr.resilient_meta.get("marker_changes")
    ]

    for role_name, reward in sorted(rewards.items()):
        logger.info("    reward[%s] = %.1f", role_name, reward)

    return role_results, rewards, metadata
