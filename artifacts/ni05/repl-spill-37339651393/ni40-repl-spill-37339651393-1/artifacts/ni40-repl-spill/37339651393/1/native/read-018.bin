"""Routing, delegation, and episodic memory tools for the REPL environment.

Provides mixin with: escalate, my_role, route_advice, delegate, recall.
"""

from __future__ import annotations

import json
import logging

from src.constants import TASK_IR_OBJECTIVE_LEN
from src.delegation_reports import load_report
from src.graph.helpers import _validate_final_answer
from src.structured_output.repair import parse_with_repair, primitives_completer
from src.task_ir import canonicalize_task_ir
from src.roles import Role

_MAX_SCHEMA_RETRIES = 2

logger = logging.getLogger(__name__)


def _recall_unavailable(reason: str) -> dict:
    """Explicit "recall is broken/unavailable" payload.

    Distinct from an empty-but-healthy result (``status == "ok"`` with
    ``results == []``) so callers can tell "no memories" from "recall broken".
    """
    return {
        "status": "unavailable",
        "results": [],
        "best_action": None,
        "confidence": None,
        "error": reason,
    }


def _render_delegate_schema_preamble(schema: dict) -> str:
    """Prompt prefix for schema-constrained delegate calls."""
    return (
        "Return only a JSON value matching this JSON Schema. Do not wrap it in markdown "
        "or add prose.\n```json\n"
        + json.dumps(schema, indent=2)
        + "\n```"
    )


def _render_delegate_schema_retry_prompt(
    original_prompt: str,
    schema: dict,
    err: str,
    rejected: str,
) -> str:
    rejected_trunc = rejected[:500]
    if len(rejected) > 500:
        rejected_trunc += f"...[truncated {len(rejected) - 500} chars]"
    return (
        f"{_render_delegate_schema_preamble(schema)}\n\n"
        "Your previous response failed schema validation.\n"
        f"Validation error: {err}\n"
        f"Rejected response: {rejected_trunc}\n\n"
        f"Original task:\n{original_prompt}"
    )


class _RoutingMixin:
    """Mixin providing routing and delegation tools (_recall, _escalate, _my_role, _route_advice, _delegate).

    Required attributes (provided by REPLEnvironment.__init__):
        config: REPLConfig — environment configuration
        context: str — full input context
        artifacts: dict — collected artifacts
        role: str — current agent role
        _exploration_calls: int — exploration call counter
        _exploration_log: ExplorationLog — exploration event history
        llm_primitives: Any | None — LLM primitives for delegation
        _retriever: TwoPhaseRetriever | None — episodic memory retriever (MemRL)
        _hybrid_router: HybridRouter | None — routing decision engine (MemRL)
    """

    def _recall(self, query: str, limit: int = 5) -> str:
        """Search episodic memory for similar past tasks with Q-values.

        Args:
            query: Natural language description of what you're looking for.
            limit: Maximum number of results to return (default 5).

        Returns:
            JSON string with similar past tasks and routing advice.
        """
        lock = getattr(self, "_state_lock", None)
        if lock:
            with lock:
                self._exploration_calls += 1
        else:
            self._exploration_calls += 1

        # Use retriever if available (reuses shared MemRL components)
        if self._retriever is not None:
            return self._recall_via_retriever(query, limit)

        # Legacy fallback: create fresh instances
        return self._recall_legacy(query, limit)

    def _recall_via_retriever(self, query: str, limit: int = 5) -> str:
        """Recall using shared TwoPhaseRetriever (fast, Q-value aware)."""
        import json

        try:
            results_raw = self._retriever.retrieve_for_exploration(
                query=query,
                context_preview=self.context[:500] if self.context else "",
            )

            results = []
            for r in results_raw[:limit]:
                ctx = r.memory.context or {}
                results.append(
                    {
                        "task": ctx.get("objective", r.memory.action)[:200],
                        "outcome": r.memory.outcome or "pending",
                        "action": r.memory.action[:100],
                        "q_value": round(r.q_value, 3),
                        "similarity": round(r.similarity, 3),
                        "combined_score": round(r.combined_score, 3),
                        "role_used": ctx.get("role", "unknown"),
                    }
                )

            # Get best action recommendation
            best = self._retriever.get_best_action(results_raw)
            # Handle both base (action, conf) and graph-enhanced (action, conf, warnings)
            if best is not None:
                best_action = best[0]
                best_conf = round(best[1], 3)
            else:
                best_action = None
                best_conf = None

            response = {
                "status": "ok",
                "results": results,
                "best_action": best_action,
                "confidence": best_conf,
            }

            self._exploration_log.add_event("recall", {"query": query}, response)

            if self.config.use_toon_encoding and len(results) >= 3:
                from src.services.toon_encoder import encode

                output = encode(response)
            else:
                output = json.dumps(response, indent=2)
            return self._maybe_wrap_tool_output(output)

        except Exception as e:
            logger.error("recall() via retriever FAILED: %s", e, exc_info=True)
            output = json.dumps(_recall_unavailable(f"{type(e).__name__}: {e}"))
            return self._maybe_wrap_tool_output(output)

    def _recall_legacy(self, query: str, limit: int = 5) -> str:
        """Fallback recall for REPLs built without a shared retriever.

        Opens a fresh EpisodicStore + TaskEmbedder and uses the real store API
        (``TaskEmbedder.embed_exploration`` + ``EpisodicStore.retrieve_by_similarity``,
        exploration memories only, matching ``TwoPhaseRetriever.retrieve_for_exploration``).
        Any failure is logged at ERROR and returned as an explicit
        ``status: "unavailable"`` payload — never as a silent empty result.
        """
        import json

        logger.warning(
            "recall() has no shared retriever; using legacy fallback "
            "(fresh EpisodicStore + TaskEmbedder)"
        )
        try:
            from orchestration.repl_memory.episodic_store import EpisodicStore
            from orchestration.repl_memory.embedder import TaskEmbedder
        except ImportError as e:
            logger.error("recall() legacy fallback: episodic memory not importable: %s", e)
            return json.dumps(_recall_unavailable(f"Episodic memory not available: {e}"))

        store = None
        embedder = None
        try:
            store = EpisodicStore()
            embedder = TaskEmbedder()

            context_preview = self.context[:500] if self.context else ""
            query_embedding = embedder.embed_exploration(query, context_preview)
            memories = store.retrieve_by_similarity(
                query_embedding,
                k=limit,
                action_type="exploration",
            )

            results = []
            for mem in memories[:limit]:
                ctx = mem.context or {}
                results.append(
                    {
                        "task": str(ctx.get("objective", mem.action))[:200],
                        "outcome": mem.outcome or "pending",
                        "action": mem.action[:100],
                        "q_value": round(mem.q_value, 3),
                        "similarity": round(mem.similarity_score, 3),
                        "combined_score": 0.0,
                        "role_used": ctx.get("role", "unknown"),
                    }
                )

            response = {
                "status": "ok",
                "results": results,
                "best_action": None,
                "confidence": None,
            }
            self._exploration_log.add_event("recall", {"query": query}, response)

            if self.config.use_toon_encoding and len(results) >= 3:
                from src.services.toon_encoder import encode

                output = encode(response)
            else:
                output = json.dumps(response, indent=2)
            return self._maybe_wrap_tool_output(output)

        except Exception as e:
            logger.error("recall() legacy fallback FAILED: %s", e, exc_info=True)
            output = json.dumps(_recall_unavailable(f"{type(e).__name__}: {e}"))
            return self._maybe_wrap_tool_output(output)
        finally:
            for resource in (embedder, store):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception:  # pragma: no cover - best-effort cleanup
                        logger.debug("recall() fallback cleanup failed", exc_info=True)

    def _escalate(self, reason: str, target_role: str | None = None) -> str:
        """Request escalation to a higher-tier or specific model.

        Args:
            reason: Why escalation is needed (be specific).
            target_role: Optional specific role to escalate to.

        Returns:
            Acknowledgment message.
        """
        self.artifacts["_escalation_requested"] = True
        self.artifacts["_escalation_reason"] = reason
        if target_role:
            # Resolve role aliases (e.g., "reviewer_agent" -> "architect_general")
            target_role = self._resolve_role_alias(target_role)
            self.artifacts["_escalation_target"] = target_role

        target_desc = target_role or "next-tier"
        return f"[ESCALATION REQUESTED -> {target_desc}]: {reason}"

    def _my_role(self) -> str:
        """Get information about the current model's role and capabilities.

        Returns:
            JSON string with role metadata.
        """
        import json
        from src.roles import get_tier, get_escalation_chain

        try:
            tier = get_tier(self.role)
            tier_val = tier.value
        except Exception:
            tier_val = "C"

        TIER_CAPABILITIES = {
            "A": ["chat", "routing", "intent_classification", "delegation"],
            "B": ["specialized_execution", "complex_reasoning", "delegation"],
            "C": ["parallel_execution", "file_level_tasks"],
            "D": ["draft_speculation"],
        }

        # Workers that Tier A/B can delegate to
        WORKER_ROLES = [
            str(Role.WORKER_GENERAL),
            str(Role.WORKER_MATH),
            str(Role.WORKER_SUMMARIZE),
            str(Role.WORKER_VISION),
        ]

        delegate_targets: list[str] = []
        if tier_val in ("A", "B"):
            delegate_targets = list(WORKER_ROLES)
            # Both Tier A and B can delegate to specialists
            delegate_targets.extend(["coder_escalation", "vision_escalation"])

        # Get escalation target
        chain = get_escalation_chain(self.role)
        escalation_target = str(chain[1]) if len(chain) > 1 else None

        result = {
            "role": self.role,
            "tier": tier_val,
            "capabilities": TIER_CAPABILITIES.get(tier_val, []),
            "escalates_to": escalation_target,
            "can_delegate_to": delegate_targets,
        }

        if self.config.use_toon_encoding:
            from src.services.toon_encoder import encode

            output = encode(result)
        else:
            output = json.dumps(result, indent=2)

        # Track tool output so it can be stripped from answer
        return self._maybe_wrap_tool_output(output)

    def _route_advice(self, task_description: str) -> str:
        """Get MemRL-informed routing advice for a task.

        Args:
            task_description: Description of the task to route.

        Returns:
            JSON string with routing recommendation.
        """
        self._exploration_calls += 1
        import json

        if self._hybrid_router is None:
            output = json.dumps(
                {
                    "recommended_role": None,
                    "confidence": 0.0,
                    "strategy": "unavailable",
                    "similar_tasks": [],
                    "warnings": ["MemRL routing not initialized"],
                }
            )
            return self._maybe_wrap_tool_output(output)

        try:
            task_ir = {
                "task_type": "chat",
                "objective": task_description[:TASK_IR_OBJECTIVE_LEN],
                "priority": "interactive",
            }
            task_ir = canonicalize_task_ir(task_ir)
            routing_decision, strategy = self._hybrid_router.route(task_ir)

            # Get raw retrieval results for transparency
            results = self._hybrid_router.retriever.retrieve_for_routing(task_ir)

            # Aggregate results by role
            role_stats: dict[str, dict] = {}
            for r in results:
                ctx = r.memory.context or {}
                role = ctx.get("role", r.memory.action)
                if role not in role_stats:
                    role_stats[role] = {"q_sum": 0.0, "count": 0}
                role_stats[role]["q_sum"] += r.q_value
                role_stats[role]["count"] += 1

            similar_tasks = []
            for role, stats in sorted(
                role_stats.items(),
                key=lambda x: x[1]["q_sum"] / max(x[1]["count"], 1),
                reverse=True,
            ):
                similar_tasks.append(
                    {
                        "role": role,
                        "q_value": round(stats["q_sum"] / max(stats["count"], 1), 3),
                        "count": stats["count"],
                    }
                )

            # Collect warnings from graph-enhanced results
            all_warnings: list[str] = []
            for r in results:
                if hasattr(r, "warnings") and r.warnings:
                    all_warnings.extend(r.warnings)

            # Confidence from best result
            confidence = round(results[0].combined_score, 3) if results else 0.0

            response = {
                "recommended_role": routing_decision[0] if routing_decision else None,
                "confidence": confidence,
                "strategy": strategy,
                "similar_tasks": similar_tasks[:5],
                "warnings": list(set(all_warnings))[:3],
            }

            self._exploration_log.add_event(
                "route_advice",
                {"task": task_description[:100]},
                response,
            )

            if self.config.use_toon_encoding:
                from src.services.toon_encoder import encode

                output = encode(response)
            else:
                output = json.dumps(response, indent=2)
            return self._maybe_wrap_tool_output(output)

        except Exception as e:
            output = json.dumps(
                {
                    "recommended_role": None,
                    "confidence": 0.0,
                    "strategy": "error",
                    "similar_tasks": [],
                    "warnings": [str(e)],
                }
            )
            return self._maybe_wrap_tool_output(output)

    # Role alias mapping: model-generated role names -> actual backend roles
    _ROLE_ALIASES: dict[str, str] = {
        "worker_coder": "coder_escalation",
        "worker_code": "coder_escalation",
    }

    def _resolve_role_alias(self, role: str) -> str:
        """Resolve a model-generated role alias to an actual backend role.

        Args:
            role: Role name (may be an alias like "researcher_agent").

        Returns:
            Resolved role name that exists in the backend config.
        """
        resolved = Role.from_string(role)
        if resolved is not None:
            return str(resolved)
        return self._ROLE_ALIASES.get(role, role)

    # Roles that can be delegation targets (any role can delegate to these)
    _DELEGATABLE_ROLES: frozenset[str] = frozenset({
        str(Role.WORKER_MATH),
        str(Role.WORKER_GENERAL),
        str(Role.WORKER_SUMMARIZE),
        str(Role.WORKER_VISION),
        "vision_escalation",
        str(Role.CODER_ESCALATION),
    })

    def _fetch_report(
        self,
        report_id: str,
        offset: int = 0,
        max_chars: int = 2400,
    ) -> str:
        """Fetch persisted delegation report chunk by report handle id."""
        self._exploration_calls += 1
        payload = load_report(report_id, offset=offset, max_chars=max_chars)
        output = json.dumps(payload, ensure_ascii=True)
        return self._maybe_wrap_tool_output(output)

    def _can_delegate_to(self, role: str) -> bool:
        """Check if a role can be a delegation target.

        Args:
            role: Target role to check.

        Returns:
            True if the role can receive delegations.
        """
        return role in self._DELEGATABLE_ROLES

    def _delegate(
        self,
        brief: str,
        to: str = "worker_general",
        parallel: bool = False,
        reason: str = "",
        persona: str = "",
        schema: dict | None = None,
        max_retries: int = 1,
    ) -> str | list[str]:
        """Delegate a subtask to another role.

        Available to ALL roles (no tier restrictions). Workers can delegate
        to other workers for parallel exploration and distributed work.

        Args:
            brief: What to do (becomes the worker's prompt).
            to: Target role (worker_general, worker_math, coder_escalation, etc.).
            parallel: If True, spawn multiple workers for list items in brief.
            reason: Why this role was chosen (helps MemRL learn).
            persona: Optional persona overlay.
            schema: Optional JSON Schema dict for validating a single delegate response.
            max_retries: Schema retry count, capped to 2.

        Returns:
            Worker's response (or list of responses if parallel).

        Examples:
            # Single delegation
            result = delegate("Summarize this file", to="worker_summarize")

            # Parallel delegation (brief should contain parseable work items)
            results = delegate(
                "Apply rename to these files: [a.py, b.py, c.py]",
                to="worker_general",
                parallel=True,
            )
        """
        self._exploration_calls += 1

        # Resolve role aliases (e.g., "researcher_agent" -> "worker_general")
        target_role = self._resolve_role_alias(to)

        # Check if target can receive delegations
        if not self._can_delegate_to(target_role):
            return f"[ERROR: Cannot delegate to '{target_role}'. Valid targets: {', '.join(sorted(self._DELEGATABLE_ROLES))}]"

        if self.llm_primitives is None:
            return "[ERROR: No LLM primitives available for delegation]"

        if schema is not None and not isinstance(schema, dict):
            return "[ERROR: schema must be a JSON Schema dict]"

        # Handle parallel delegation
        if parallel:
            if schema is not None:
                return "[ERROR: schema validation is only supported for single delegation]"
            return self._delegate_parallel(brief, target_role, reason, persona)

        return self._delegate_single(
            brief,
            target_role,
            reason,
            persona,
            schema=schema,
            max_retries=max_retries,
        )

    def _delegate_single(
        self,
        brief: str,
        target_role: str,
        reason: str = "",
        persona: str = "",
        schema: dict | None = None,
        max_retries: int = 1,
    ) -> str:
        """Execute a single delegation to one worker."""
        import time

        start = time.perf_counter()

        # Initialize delegation tracking list in artifacts
        if "_delegations" not in self.artifacts:
            self.artifacts["_delegations"] = []

        delegation_record: dict = {
            "from_role": self.role,
            "to_role": target_role,
            "reason": reason,
            "persona": persona,
            "prompt_preview": brief[:100],
            "timestamp": time.time(),
            "parallel": False,
        }

        # Build delegate prompt: include original task context so the
        # target model knows WHAT to solve, not just the brief instruction.
        # Without this, delegates only see terse briefs like "Implement X"
        # without problem constraints, examples, or method signatures.
        delegate_prompt = brief
        if hasattr(self, "context") and self.context:
            # Truncate context to avoid overwhelming small workers
            ctx_preview = self.context[:4000]
            if len(self.context) > 4000:
                ctx_preview += "\n... [truncated]"
            delegate_prompt = (
                f"{ctx_preview}\n\n"
                f"## Task\n{brief}"
            )

        query_prompt = (
            f"{_render_delegate_schema_preamble(schema)}\n\n{delegate_prompt}"
            if schema is not None
            else delegate_prompt
        )
        retry_budget = max(0, min(max_retries, _MAX_SCHEMA_RETRIES))
        attempts = 1
        retry_count = 0

        try:
            # TD-21.22 (typed-decision-plane.md): forward the schema on the
            # wire now that TD-21.0 landed (json_schema constrains BOTH the
            # /completion and /v1 lanes), instead of relying only on the
            # prose preamble above to get the model to comply.
            result = self.llm_primitives.llm_call(
                query_prompt,
                role=target_role,
                persona=persona or None,
                json_schema=schema,
            )

            parsed = None
            ok = True
            err = None
            if schema is not None:
                ok, err, parsed = _validate_final_answer(result, schema)
                if not ok:
                    # TD-21.22 residual: one repair turn (fish, then at most
                    # one constrained extraction call to the same server)
                    # before paying for a full re-call. With the schema now
                    # on the wire above, this residual should rarely fire.
                    repair = parse_with_repair(
                        result,
                        schema=schema,
                        complete=primitives_completer(self.llm_primitives, target_role),
                        site="repl_delegate",
                        # TD-21.34: `schema` is the tool caller's own structured
                        # answer contract for this delegate -- same fabrication
                        # risk as `repl_final`.
                        require_evidence=True,
                    )
                    if repair.status in ("parsed", "repaired"):
                        parsed = repair.value
                        result = json.dumps(parsed)
                        ok, err = True, None
                    else:
                        err = repair.reason or err
                while not ok and attempts <= retry_budget:
                    retry_count += 1
                    attempts += 1
                    retry_prompt = _render_delegate_schema_retry_prompt(
                        delegate_prompt,
                        schema,
                        err or "unknown validation error",
                        result,
                    )
                    result = self.llm_primitives.llm_call(
                        retry_prompt,
                        role=target_role,
                        persona=persona or None,
                        json_schema=schema,
                    )
                    ok, err, parsed = _validate_final_answer(result, schema)

            elapsed = time.perf_counter() - start

            delegation_record["success"] = True
            delegation_record["elapsed_sec"] = round(elapsed, 3)
            delegation_record["result_len"] = len(result)
            if schema is not None:
                delegation_record["schema_validation"] = True
                delegation_record["schema_valid"] = ok
                delegation_record["schema_attempts"] = attempts
                delegation_record["schema_retry_count"] = retry_count
            self.artifacts["_delegations"].append(delegation_record)

            self._exploration_log.add_event(
                "delegate",
                {
                    "target_role": target_role,
                    "reason": reason,
                    "schema": schema is not None,
                },
                {
                    "summary": f"[{len(result)} chars in {elapsed:.1f}s]",
                    "schema_valid": ok if schema is not None else None,
                    "retry_count": retry_count,
                },
            )

            if schema is not None:
                return json.dumps(
                    {
                        "operation": "delegate",
                        "target_role": target_role,
                        "schema_validation": True,
                        "valid": ok,
                        "response": parsed if ok else result,
                        "raw_response": result,
                        "error": None if ok else err,
                        "attempts": attempts,
                    },
                    indent=2,
                    default=str,
                )

            return result

        except Exception as e:
            elapsed = time.perf_counter() - start
            delegation_record["success"] = False
            delegation_record["error"] = str(e)
            delegation_record["elapsed_sec"] = round(elapsed, 3)
            self.artifacts["_delegations"].append(delegation_record)

            return f"[DELEGATION FAILED: {target_role} -> {e}]"

    def _delegate_parallel(
        self,
        brief: str,
        target_role: str,
        reason: str = "",
        persona: str = "",
    ) -> list[str]:
        """Execute parallel delegation to multiple workers.

        Parses the brief for work items (lists, file paths, etc.) and
        spawns concurrent workers for each item.

        Args:
            brief: Brief containing multiple work items.
            target_role: Role for all workers.
            reason: Why this delegation approach.
            persona: Optional persona overlay.

        Returns:
            List of worker responses (one per work item).
        """
        from src.concurrency import is_small_worker_role
        import concurrent.futures
        import time

        if not is_small_worker_role(target_role):
            # Large roles must never run concurrently; fall back to single.
            return [self._delegate_single(brief, target_role, reason, persona)]

        # Parse work items from brief
        # Look for: [a, b, c], numbered lists, file paths, etc.
        work_items = self._parse_parallel_work_items(brief)

        if len(work_items) <= 1:
            # Not enough items for parallel, fall back to single
            return [self._delegate_single(brief, target_role, reason, persona)]

        start = time.perf_counter()

        # Initialize delegation tracking
        if "_delegations" not in self.artifacts:
            self.artifacts["_delegations"] = []

        results: list[str] = []
        # Limit concurrent workers to prevent resource exhaustion
        max_workers = min(4, len(work_items))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all work items
            futures = {
                executor.submit(
                    self._delegate_single_item,
                    item,
                    target_role,
                    persona,
                ): item
                for item in work_items
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(f"[PARALLEL WORKER FAILED for '{item[:50]}': {e}]")

        elapsed = time.perf_counter() - start

        # Log parallel delegation summary
        self._exploration_log.add_event(
            "delegate_parallel",
            {
                "target_role": target_role,
                "reason": reason,
                "work_items": len(work_items),
            },
            f"[{len(results)} results in {elapsed:.1f}s]",
        )

        # Record parallel delegation in artifacts
        self.artifacts["_delegations"].append({
            "from_role": self.role,
            "to_role": target_role,
            "reason": reason,
            "parallel": True,
            "work_items": len(work_items),
            "success": True,
            "elapsed_sec": round(elapsed, 3),
            "timestamp": time.time(),
        })

        return results

    def _delegate_single_item(
        self,
        item: str,
        target_role: str,
        persona: str = "",
    ) -> str:
        """Execute a single parallel work item (called from thread pool)."""
        # Include original task context (same as _delegate_single)
        delegate_prompt = item
        if hasattr(self, "context") and self.context:
            ctx_preview = self.context[:4000]
            if len(self.context) > 4000:
                ctx_preview += "\n... [truncated]"
            delegate_prompt = f"{ctx_preview}\n\n## Task\n{item}"
        try:
            return self.llm_primitives.llm_call(
                delegate_prompt,
                role=target_role,
                persona=persona or None,
            )
        except Exception as e:
            return f"[ERROR: {e}]"

    def _parse_parallel_work_items(self, brief: str) -> list[str]:
        """Parse a brief into individual work items for parallel execution.

        Handles various formats:
        - Python lists: [a, b, c]
        - Numbered lists: 1. item, 2. item
        - Comma-separated: a, b, c
        - Newline-separated with markers

        Args:
            brief: The brief text to parse.

        Returns:
            List of individual work items. If parsing fails, returns [brief].
        """
        import re

        # Try Python list format: [a, b, c] or ["a", "b", "c"]
        list_match = re.search(r'\[([^\]]+)\]', brief)
        if list_match:
            items_str = list_match.group(1)
            # Split on comma, respecting quotes
            items = []
            current = ""
            in_quotes = False
            quote_char = None
            for char in items_str:
                if char in ('"', "'") and not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char and in_quotes:
                    in_quotes = False
                    quote_char = None
                elif char == ',' and not in_quotes:
                    if current.strip():
                        items.append(current.strip().strip('"\''))
                    current = ""
                    continue
                current += char
            if current.strip():
                items.append(current.strip().strip('"\''))
            if len(items) > 1:
                # Reconstruct full prompts with context from brief
                context = brief[:brief.find('[')].strip()
                return [f"{context}: {item}" if context else item for item in items]

        # Try numbered list format: 1. item\n2. item
        numbered = re.findall(r'^\d+[.)]\s*(.+)$', brief, re.MULTILINE)
        if len(numbered) > 1:
            return numbered

        # Fall back to single item
        return [brief]
