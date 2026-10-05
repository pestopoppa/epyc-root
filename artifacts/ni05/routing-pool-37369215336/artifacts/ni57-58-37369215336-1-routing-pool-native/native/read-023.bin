"""Embedder precompute and reward injection via HTTP.

Handles reward injection using a background ThreadPoolExecutor, embedding
precomputation via the BGE pool, and delivery accounting for benchmark runs.
"""

from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from orchestration.repl_memory.memory_record import embedding_text_for

__all__ = [
    "EMBEDDER_PORTS",
    "RewardDeliverySummary",
    "_get_reward_executor",
    "_inject_3way_rewards_http",
    "_inject_per_role_rewards_http",
    "_inject_single_reward",
    "_precompute_embedding",
]

logger = logging.getLogger("seed_specialist_routing")

# Embedder server ports for precomputing embeddings
EMBEDDER_PORTS = [8090, 8091, 8092, 8093, 8094, 8095]

# Background executor for reward injection
_reward_executor: concurrent.futures.ThreadPoolExecutor | None = None
_REWARD_WAIT_TIMEOUT_S = 35.0


@dataclass
class RewardDeliverySummary:
    """Structured delivery accounting for reward injection."""

    submitted: int = 0
    acknowledged: int = 0
    failed: int = 0
    skipped: int = 0
    failure_reasons: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_reward_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Get or create the background executor for reward injection."""
    global _reward_executor
    if _reward_executor is None:
        _reward_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="reward_inject"
        )
    return _reward_executor


def _precompute_embedding(
    task_description: str,
    client: "httpx.Client",
    task_type: str | None = None,
) -> list[float] | None:
    """Precompute embedding for task_description using embedder servers.

    ``task_type`` MUST be the same value the injected row carries in its
    context, because that is what the API side derives the row's embedding text
    from (``q_scorer.score_external_result``: ``context["task_type"] or
    "chat"``). This used to hard-code ``type:chat`` for every suite, so a
    ``math``/``coder``/``hotpotqa`` row got a vector describing a convention
    its own stored context contradicted (EPD-3-R3). The text itself is built by
    the one canonical builder, never re-spelled here.

    ``task_description`` is expected pre-truncated by the caller to whatever it
    puts in the payload's ``task_description`` field, so the precomputed vector
    describes the text that is actually stored.
    """
    text = embedding_text_for(
        objective=task_description,
        task_type=task_type or "chat",
    )

    for port in EMBEDDER_PORTS:
        try:
            resp = client.post(
                f"http://127.0.0.1:{port}/embedding",
                json={"content": text},
                timeout=5.0,
            )
            if resp.status_code != 200:
                continue

            data = resp.json()
            if "embedding" in data:
                embedding_data = data["embedding"]
                if isinstance(embedding_data[0], list):
                    return embedding_data[0]
                return embedding_data
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0]["embedding"]
        except Exception:
            continue

    logger.debug("All embedder servers failed, will let API compute embedding")
    return None


def _inject_single_reward(
    url: str,
    payload: dict[str, Any],
    action_key: str,
    watcher: Any | None = None,
) -> tuple[bool, str]:
    """Inject a single reward (runs in background thread).

    When ``watcher`` is set, the POST uses resilient_post so an exogenous
    orchestrator/llama reload doesn't get logged as a real reward-injection
    failure. Bare /chat/reward POSTs (watcher=None) preserve the prior
    behavior exactly — non-autopilot callers (if any) unaffected.

    Reward injection runs in a background ThreadPoolExecutor; a per-call
    httpx.Client is created here to avoid sharing across threads.
    """
    if watcher is None:
        try:
            with httpx.Client() as client:
                resp = client.post(f"{url}/chat/reward", json=payload, timeout=30)
                if resp.status_code == 200:
                    return True, ""
                logger.warning("Reward injection failed for %s: HTTP %d", action_key, resp.status_code)
                return False, f"http_{resp.status_code}"
        except Exception as e:
            logger.warning("Reward injection error for %s: %s", action_key, e)
            return False, f"{type(e).__name__}: {e}"

    # Watcher path: use resilient_post for exogenous-reload detection.
    import sys
    from pathlib import Path
    _ap = Path(__file__).resolve().parents[1] / "autopilot"
    if str(_ap) not in sys.path:
        sys.path.insert(0, str(_ap))
    from resilient_http import resilient_post  # type: ignore

    try:
        with httpx.Client() as client:
            data, meta = resilient_post(
                f"{url}/chat/reward",
                json=payload,
                timeout=30,
                client=client,
                watcher=watcher,
                llama_role=payload.get("role") if isinstance(payload, dict) else None,
            )
            if not data.get("error"):
                return True, ""
            # When the failure was exogenous + unrecovered, log differently
            # so it's visible in the seeder's stats but doesn't get flagged as
            # a real failure mode.
            if meta.get("exogenous_unrecovered"):
                logger.info("Reward injection skipped for %s: exogenous reload unrecovered", action_key)
                return False, "exogenous_unrecovered"
            err = data.get("error", "")
            logger.warning("Reward injection failed for %s: %s", action_key, err)
            return False, err
    except Exception as e:
        logger.warning("Reward injection error for %s: %s", action_key, e)
        return False, f"{type(e).__name__}: {e}"


def _inject_3way_rewards_http(
    prompt: str,
    suite: str,
    question_id: str,
    rewards: dict[str, float],
    metadata: dict[str, Any],
    url: str,
    client: "httpx.Client",
) -> dict[str, Any]:
    """Inject 3-way rewards via HTTP API with delivery accounting."""
    cost_metrics = metadata.get("cost_metrics", {})
    summary = RewardDeliverySummary(skipped=0 if rewards else 0)

    if not rewards:
        return summary.to_dict()

    embedding = _precompute_embedding(prompt[:200], client, task_type=suite)

    executor = _get_reward_executor()
    futures: dict[concurrent.futures.Future[tuple[bool, str]], str] = {}

    for action_key, reward in rewards.items():
        action_cost = cost_metrics.get(action_key, {})
        tokens_generated = int(action_cost.get("tokens_generated", 0) or 0)
        tokens_estimate = int(action_cost.get("tokens_generated_estimate", 0) or 0)

        context = {
            "task_type": suite,
            "source": "3way_eval",
            "question_id": question_id,
            "action_type": "routing",
            "tools_helped": metadata.get("tools_helped", False),
            "tools_neutral": metadata.get("tools_neutral", False),
            "tools_hurt": metadata.get("tools_hurt", False),
            "tool_advantage": metadata.get("tool_advantage", 0),
            "elapsed_seconds": action_cost.get("elapsed_seconds", 0.0),
            "tokens_generated": tokens_generated,
            "tokens_generated_estimate": tokens_estimate,
            "tokens_generated_effective": (
                tokens_generated if tokens_generated > 0 else tokens_estimate
            ),
            "predicted_tps": action_cost.get("predicted_tps", 0.0),
            "prompt_eval_ms": action_cost.get("prompt_eval_ms", 0.0),
            "generation_ms": action_cost.get("generation_ms", 0.0),
            "tools_used": action_cost.get("tools_used", 0),
            "backend_task_id": action_cost.get("backend_task_id", 0),
            "slot_progress_source": action_cost.get("slot_progress_source", ""),
        }

        if wr_rewards := metadata.get("web_research_rewards", {}).get(action_key):
            context.update(wr_rewards)
        if sp_rewards := metadata.get("scratchpad_rewards", {}).get(action_key):
            context.update(sp_rewards)

        payload = {
            "task_description": prompt[:200],
            "action": action_key,
            "reward": reward,
            "context": context,
        }
        if embedding is not None:
            payload["embedding"] = embedding

        futures[executor.submit(_inject_single_reward, url, payload, action_key)] = action_key
        summary.submitted += 1

    done, not_done = concurrent.futures.wait(
        futures.keys(),
        timeout=_REWARD_WAIT_TIMEOUT_S,
    )
    for future in done:
        action_key = futures[future]
        try:
            ok, reason = future.result()
        except Exception as exc:
            ok = False
            reason = f"{type(exc).__name__}: {exc}"
        if ok:
            summary.acknowledged += 1
        else:
            summary.failed += 1
            summary.failure_reasons[action_key] = reason

    for future in not_done:
        action_key = futures[future]
        future.cancel()
        summary.failed += 1
        summary.failure_reasons[action_key] = "wait_timeout"

    return summary.to_dict()


def _inject_per_role_rewards_http(
    prompt: str,
    suite: str,
    question_id: str,
    rewards: dict[str, float],
    metadata: dict[str, Any],
    url: str,
    client: "httpx.Client",
) -> dict[str, Any]:
    """Inject per-role rewards via HTTP API with delivery accounting.

    Same mechanism as _inject_3way_rewards_http but with:
    - Action keys are role names (e.g., "frontdoor", "architect_general")
    - source: "per_role_eval"
    - No tool comparison fields (tools_helped, etc.)
    """
    cost_metrics = metadata.get("cost_metrics", {})
    summary = RewardDeliverySummary()

    if not rewards:
        return summary.to_dict()

    embedding = _precompute_embedding(prompt[:200], client, task_type=suite)

    executor = _get_reward_executor()
    futures: dict[concurrent.futures.Future[tuple[bool, str]], str] = {}

    for role_name, reward in rewards.items():
        action_cost = cost_metrics.get(role_name, {})
        tokens_generated = int(action_cost.get("tokens_generated", 0) or 0)

        context = {
            "task_type": suite,
            "source": "per_role_eval",
            "question_id": question_id,
            "action_type": "routing",
            "elapsed_seconds": action_cost.get("elapsed_seconds", 0.0),
            "tokens_generated": tokens_generated,
            "predicted_tps": action_cost.get("predicted_tps", 0.0),
            "prompt_eval_ms": action_cost.get("prompt_eval_ms", 0.0),
            "generation_ms": action_cost.get("generation_ms", 0.0),
            "tools_used": action_cost.get("tools_used", 0),
        }

        payload = {
            "task_description": prompt[:200],
            "action": role_name,
            "reward": reward,
            "context": context,
        }
        if embedding is not None:
            payload["embedding"] = embedding

        futures[executor.submit(_inject_single_reward, url, payload, role_name)] = role_name
        summary.submitted += 1

    done, not_done = concurrent.futures.wait(
        futures.keys(),
        timeout=_REWARD_WAIT_TIMEOUT_S,
    )
    for future in done:
        role_name = futures[future]
        try:
            ok, reason = future.result()
        except Exception as exc:
            ok = False
            reason = f"{type(exc).__name__}: {exc}"
        if ok:
            summary.acknowledged += 1
        else:
            summary.failed += 1
            summary.failure_reasons[role_name] = reason

    for future in not_done:
        role_name = futures[future]
        future.cancel()
        summary.failed += 1
        summary.failure_reasons[role_name] = "wait_timeout"

    return summary.to_dict()
