"""Species 0 — Seeder: per-role evaluation + Q-value reward injection.

Wraps the seed_specialist_routing.py pipeline as a callable species,
monitoring memory accumulation and Q-value convergence.

Phase 5 refactor: replaced 3-way eval (SELF:direct, SELF:repl, ARCHITECT)
with dynamic per-role eval that discovers active roles from model_registry.yaml
and tests each individually with natural mode selection.
"""

from __future__ import annotations

import logging
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("autopilot.seeder")

_orch_root = Path(__file__).resolve().parents[3]
_memory_db = _orch_root / "orchestration" / "repl_memory" / "sessions" / "episodic.db"
sys.path.insert(0, str(_orch_root / "scripts" / "benchmark"))

from seeding_eval import evaluate_question_per_role  # noqa: E402
from seeding_injection import _inject_per_role_rewards_http  # noqa: E402
from seeding_types import DEFAULT_TIMEOUT, discover_active_roles  # noqa: E402

# Import sample_unseen_questions from the main seeding script
from seed_specialist_routing import sample_unseen_questions  # noqa: E402

DEFAULT_URL = "http://localhost:8000"

# Convergence thresholds
TD_ERROR_EPSILON = 0.05  # Below this, Q-values are "converged"
CONVERGENCE_WINDOW = 5  # N consecutive batches with |TD| < epsilon


@dataclass
class SeederBatchResult:
    n_questions: int = 0
    n_correct: int = 0
    n_role_successes: int = 0
    n_errors: int = 0
    rewards_injected: int = 0
    rewards_delivery: list[dict[str, Any]] = field(default_factory=list)
    avg_td_error: float = 0.0
    memory_count: int = 0
    elapsed_s: float = 0.0
    per_action_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    results: list[dict[str, Any]] = field(default_factory=list)
    # 2026-05-23 exogenous-restart resilience (handoff Phase 4).
    # Aggregated from per-role RoleResult.exogenous_* across all questions
    # in the batch. The seed phase happens BEFORE tower.hybrid_eval; if any
    # role call in any question failed exogenously and stayed unrecovered,
    # _action_seed_batch merges these counts into the final trial EvalResult
    # so Phase 5's pre-gate classifier can tag the trial bug_corrupted.
    n_exogenous_recovered: int = 0
    n_exogenous_unrecovered: int = 0
    n_external_restart: int = 0
    exogenous_question_ids: list[str] = field(default_factory=list)
    exogenous_marker_log: list[dict] = field(default_factory=list)


# How often to re-discover active roles (in batches)
_ROLE_REFRESH_INTERVAL = 10


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int_like(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _tail_below_threshold(values: list[float], threshold: float) -> int:
    """Count consecutive trailing values below ``threshold``."""
    count = 0
    for value in reversed(values):
        if value < threshold:
            count += 1
        else:
            break
    return count


def _is_success_reward(value: Any) -> bool:
    try:
        return float(value) > 0.5
    except (TypeError, ValueError):
        return False


def _question_with_strategy_hints(
    question: dict[str, Any],
    strategy_hints: str | None,
) -> dict[str, Any]:
    """Deprecated no-op: planner hints must never enter eval prompts."""
    return question


class Seeder:
    """Species 0: per-role seeding with Q-value convergence monitoring."""

    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout: int = DEFAULT_TIMEOUT,
        batch_size: int = 10,
        suites: list[str] | None = None,
        dry_run: bool = False,
        on_question: "Callable[[str], None] | None" = None,
    ):
        self.url = url
        self.timeout = timeout
        self.batch_size = batch_size
        self.suites = suites or [
            "coder", "thinking", "math", "general", "simpleqa",
            "hotpotqa", "agentic", "instruction_precision",
        ]
        self.dry_run = dry_run
        self.on_question = on_question
        self._seen: set[str] = set()
        self._td_errors: list[tuple[int, float]] = []  # (batch_num, avg_td_error)
        self._question_results: list[dict[str, Any]] = []
        self._batch_count = 0
        self._consecutive_converged = 0
        self._active_roles: list[dict[str, Any]] = []
        self._refresh_roles()

    def _refresh_roles(self) -> None:
        """Discover active roles from model_registry.yaml."""
        self._active_roles = discover_active_roles()
        log.info(
            "Discovered %d active roles: %s",
            len(self._active_roles),
            [r["name"] for r in self._active_roles],
        )

    @property
    def td_errors(self) -> list[tuple[int, float]]:
        return list(self._td_errors)

    @property
    def is_converged(self) -> bool:
        return self._consecutive_converged >= CONVERGENCE_WINDOW

    def export_state(self) -> dict[str, Any]:
        """Serialize convergence state for autopilot_state persistence."""
        return {
            "td_errors": [err for _, err in self._td_errors],
            "batch_count": self._batch_count,
            "consecutive_converged": self._consecutive_converged,
            "seen_question_ids": sorted(self._seen),
            "question_results": list(self._question_results),
        }

    def restore_state(self, state: dict[str, Any] | None) -> None:
        """Restore convergence state from persisted autopilot state."""
        state = state or {}
        raw_td_errors = state.get("td_errors", [])
        if isinstance(raw_td_errors, list):
            td_errors = [float(err) for err in raw_td_errors if _is_number(err)]
        else:
            td_errors = []
        self._td_errors = list(enumerate(td_errors))

        batch_count = state.get("batch_count")
        if _is_int_like(batch_count):
            self._batch_count = max(int(batch_count), len(self._td_errors))
        else:
            self._batch_count = len(self._td_errors)

        consecutive = state.get("consecutive_converged")
        if _is_int_like(consecutive):
            self._consecutive_converged = max(0, int(consecutive))
        else:
            self._consecutive_converged = _tail_below_threshold(
                td_errors, TD_ERROR_EPSILON
            )

        raw_seen = state.get("seen_question_ids", state.get("seen", []))
        if isinstance(raw_seen, list):
            self._seen = {str(qid) for qid in raw_seen if qid}
        else:
            self._seen = set()

        raw_results = state.get("question_results", [])
        if isinstance(raw_results, list):
            self._question_results = [
                dict(row) for row in raw_results if isinstance(row, dict)
            ]
        else:
            self._question_results = []

    # ── main entry point ─────────────────────────────────────────

    def run_batch(
        self,
        n_questions: int | None = None,
        suites: list[str] | None = None,
        seed: int | None = None,
        watcher: "Any | None" = None,
        strategy_hints: str | None = None,
    ) -> SeederBatchResult:
        """Run a batch of per-role evaluations and inject rewards."""
        import httpx

        # Periodic role refresh to pick up stack changes
        if self._batch_count > 0 and self._batch_count % _ROLE_REFRESH_INTERVAL == 0:
            self._refresh_roles()

        if not self._active_roles:
            log.error("No active roles discovered — cannot seed")
            return SeederBatchResult()

        n = n_questions or self.batch_size
        suites = suites or self.suites
        seed = seed if seed is not None else int(time.time()) % 10000

        # Sample questions
        per_suite = max(1, n // len(suites))
        questions = sample_unseen_questions(
            suites=suites,
            sample_per_suite=per_suite,
            seen=self._seen,
            seed=seed,
            use_pool=True,
        )
        if not questions:
            log.warning("No unseen questions available")
            return SeederBatchResult()

        questions = questions[:n]
        if strategy_hints:
            log.warning(
                "Ignoring seed_batch strategy_hints for %d sampled question(s); "
                "planner hints are not answer-context and must not enter eval prompts.",
                len(questions),
            )
        log.info(
            "Seeding batch %d: %d questions × %d roles across %s",
            self._batch_count, len(questions), len(self._active_roles), suites,
        )

        start = time.time()
        batch_result = SeederBatchResult(n_questions=len(questions))
        td_errors_batch = []

        with httpx.Client(timeout=self.timeout) as client:
            for i, q in enumerate(questions):
                # Notify TUI of current question
                if self.on_question:
                    suite = q.get("suite", "unknown")
                    qid = q.get("id", q.get("question_id", f"q_{i}"))
                    prompt_text = q.get("prompt", "")
                    self.on_question(f"[{suite}] {qid}\n\n{prompt_text}")
                try:
                    role_results, rewards, metadata = evaluate_question_per_role(
                        prompt_info=q,
                        active_roles=self._active_roles,
                        url=self.url,
                        timeout=self.timeout,
                        client=client,
                        dry_run=self.dry_run,
                        watcher=watcher,
                    )

                    # 2026-05-23 Phase 4 — aggregate per-question exogenous
                    # signals into batch-level counters. metadata fields
                    # exogenous_*_roles are lists of role names; we count
                    # any-of-roles per question.
                    qid = q.get("id", q.get("question_id", f"q_{i}"))
                    exo_rec = bool(metadata.get("exogenous_recovered_roles"))
                    exo_unrec = bool(metadata.get("exogenous_unrecovered_roles"))
                    ext_restart = bool(metadata.get("external_restart_roles"))
                    if exo_rec:
                        batch_result.n_exogenous_recovered += 1
                    if exo_unrec:
                        batch_result.n_exogenous_unrecovered += 1
                    if ext_restart:
                        batch_result.n_external_restart += 1
                    if exo_rec or exo_unrec:
                        batch_result.exogenous_question_ids.append(qid)
                    for marker in (metadata.get("exogenous_marker_log") or []):
                        if marker:
                            batch_result.exogenous_marker_log.append(marker)

                    # Track per-role stats. `n_correct` is question-level for
                    # the batch summary denominator; per-role wins are tracked
                    # separately so N roles cannot produce >N-question "correct"
                    # counts.
                    question_has_success = False
                    for role_name, reward in rewards.items():
                        if role_name not in batch_result.per_action_stats:
                            batch_result.per_action_stats[role_name] = {
                                "total": 0, "correct": 0
                            }
                        batch_result.per_action_stats[role_name]["total"] += 1
                        if _is_success_reward(reward):
                            batch_result.per_action_stats[role_name]["correct"] += 1
                            batch_result.n_role_successes += 1
                            question_has_success = True
                    if question_has_success:
                        batch_result.n_correct += 1

                    # Inject rewards
                    delivery: dict[str, Any] = {}
                    if not self.dry_run:
                        qid = q.get("id", q.get("question_id", f"q_{i}"))
                        suite = q.get("suite", "unknown")
                        delivery = _inject_per_role_rewards_http(
                            prompt=q.get("prompt", ""),
                            suite=suite,
                            question_id=qid,
                            rewards=rewards,
                            metadata=metadata,
                            url=self.url,
                            client=client,
                        )
                        batch_result.rewards_delivery.append(delivery)
                        batch_result.rewards_injected += int(delivery.get("acknowledged", 0))
                        _failed = int(delivery.get("failed", 0))
                        if _failed > 0:
                            _reasons = delivery.get("failure_reasons", {})
                            log.warning(
                                "Reward delivery: %d acknowledged, %d failed for %s — %s",
                                int(delivery.get("acknowledged", 0)),
                                _failed, qid, _reasons,
                            )

                    # Track TD error from metadata
                    td = metadata.get("avg_td_error", 0.0)
                    if td > 0:
                        td_errors_batch.append(td)

                    # Mark as seen
                    qid = q.get("id", q.get("question_id", ""))
                    if qid:
                        self._seen.add(qid)

                    # Store result for logging and durable item analytics.
                    result_row = {
                        "batch_num": self._batch_count,
                        "seed": seed,
                        "suite": q.get("suite", "unknown"),
                        "question_id": qid,
                        "rewards": rewards,
                        "roles_tested": metadata.get("roles_tested", []),
                    }
                    if q.get("planner_hints_applied"):
                        result_row["planner_hints_applied"] = True
                    batch_result.results.append(result_row)
                    self._question_results.append(result_row)

                except Exception as e:
                    log.exception("Error on question %d: %s", i, e)
                    batch_result.n_errors += 1
                    qid = q.get("id", q.get("question_id", f"q_{i}"))
                    result_row = {
                        "batch_num": self._batch_count,
                        "seed": seed,
                        "suite": q.get("suite", "unknown"),
                        "question_id": qid,
                        "error": str(e),
                        "roles_tested": [],
                    }
                    batch_result.results.append(result_row)
                    self._question_results.append(result_row)

                if (i + 1) % 5 == 0:
                    log.info("  Seeding progress: %d/%d", i + 1, len(questions))

        batch_result.elapsed_s = time.time() - start

        # TD error tracking
        if td_errors_batch:
            avg_td = sum(td_errors_batch) / len(td_errors_batch)
        else:
            avg_td = 0.0
        batch_result.avg_td_error = avg_td
        self._td_errors.append((self._batch_count, avg_td))

        # Convergence tracking
        if avg_td < TD_ERROR_EPSILON:
            self._consecutive_converged += 1
        else:
            self._consecutive_converged = 0

        # Memory count
        batch_result.memory_count = self._get_memory_count()

        self._batch_count += 1
        log.info(
            "Seeder batch %d done: %d/%d questions with >=1 success, "
            "%d role successes, %d rewards, TD=%.4f, converged=%d/%d, "
            "memories=%d, roles=%d",
            self._batch_count - 1,
            batch_result.n_correct,
            batch_result.n_questions,
            batch_result.n_role_successes,
            batch_result.rewards_injected,
            avg_td,
            self._consecutive_converged,
            CONVERGENCE_WINDOW,
            batch_result.memory_count,
            len(self._active_roles),
        )
        return batch_result

    # ── memory monitoring ────────────────────────────────────────

    def _get_memory_count(self) -> int:
        """Get routing memory count from SQLite without importing ML deps."""
        try:
            if not _memory_db.exists():
                return 0
            with sqlite3.connect(_memory_db) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE action_type = ?",
                    ("routing",),
                ).fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            log.debug("Could not get memory count: %s", e)
            return 0

    def get_memory_count(self) -> int:
        return self._get_memory_count()

    def convergence_status(self) -> dict[str, Any]:
        """Status summary for controller consumption."""
        return {
            "batch_count": self._batch_count,
            "is_converged": self.is_converged,
            "consecutive_converged": self._consecutive_converged,
            "convergence_threshold": CONVERGENCE_WINDOW,
            "last_td_error": self._td_errors[-1][1] if self._td_errors else None,
            "td_epsilon": TD_ERROR_EPSILON,
            "memory_count": self._get_memory_count(),
        }
