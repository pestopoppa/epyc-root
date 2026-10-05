"""BaseJudge — transcribed verbatim from the DTAP upstream tree
(dt_arena/src/types/judge.py @ commit e0323a521ba4ef88f8e14c1eccf68d0a3d19a458,
Apache-2.0). Import prologue rewritten; logic byte-identical.

Only `llm_check` differs from upstream: the disposable runner performs zero
inference, so a judge that reaches `llm_check` fails with a typed JUDGE
failure instead of calling an LLM. No judge in the imported subset calls it
(verified at import time: 0 of 6682 judges use llm_check).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from .outcomes import JudgeFailure


class BaseJudge(ABC):
    """Base class for judges that evaluate agent behavior."""

    def __init__(self, domain: str, judge_model: str = "gpt-5.4"):
        self.domain = domain
        self.judge_model = judge_model
        self.trajectory: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

    def _find_calls(self, env: str, tool: str, **arg_filters: Any) -> List[Dict[str, Any]]:
        """Return every trajectory step matching (env, tool) and arg filters, in order.

        Each match is {"args": call.arguments, "response": parsed MCP result,
        "step": int index in self.trajectory}. Returns [] when nothing matches.
        """

        def _match(actual: Any, expected: Any) -> bool:
            if isinstance(actual, list):
                # Either the bare value is in the list, or — for string
                # expecteds — a case-insensitive membership check (gmail
                # recipients are not case-sensitive).
                if expected in actual:
                    return True
                if isinstance(expected, str):
                    return any(
                        isinstance(a, str) and a.strip().lower() == expected.strip().lower()
                        for a in actual
                    )
                return False
            if isinstance(actual, str) and isinstance(expected, str) and "," in actual:
                parts = [p.strip().lower() for p in actual.split(",") if p.strip()]
                return expected.strip().lower() in parts
            return actual == expected

        out: List[Dict[str, Any]] = []
        for i, (call, response) in enumerate(self.trajectory):
            if call.get("env") != env or call.get("tool") != tool:
                continue
            args = call.get("arguments") or {}
            if all(_match(args.get(k), v) for k, v in arg_filters.items()):
                out.append({"args": args, "response": response, "step": i})
        return out

    def _find_call(
        self,
        env: str,
        tool: str,
        which: Union[str, int] = "last",
        **arg_filters: Any,
    ) -> Optional[Dict[str, Any]]:
        """Convenience over `_find_calls`: return ONE matching step or None.

            which="last"   (default) — most recent matching step in trajectory
            which="first"  — earliest matching step
            which=int      — Nth match (supports negative indexing); None if OOB

        Returns the same {"args", "response", "step"} dict as `_find_calls`.
        """
        matches = self._find_calls(env, tool, **arg_filters)
        if not matches:
            return None
        if which == "last":
            return matches[-1]
        if which == "first":
            return matches[0]
        if isinstance(which, int):
            try:
                return matches[which]
            except IndexError:
                return None
        raise ValueError(f"which must be 'last', 'first', or int; got {which!r}")

    def llm_check(self, text: str, criterion: str, *, context: str = "", model: Optional[str] = None) -> bool:
        """Semantic-level checker; NOT supported in the disposable zero-inference runner."""
        raise JudgeFailure(
            "llm_check() is not supported by the disposable zero-inference runner; "
            "select a deterministic state-based judge instead.",
            detail={"criterion": criterion},
        )

    @abstractmethod
    def eval_task(self, agent_responses: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate whether the agent successfully completed the task."""
        pass

    @abstractmethod
    def eval_attack(self, agent_responses: List[str]) -> Optional[Tuple[bool, Dict[str, Any]]]:
        """Evaluate whether an attack was successful against the agent.

        Returns (success, metadata) for adversarial tasks, or None for benign
        tasks where no attack evaluation is needed.
        """
        pass
