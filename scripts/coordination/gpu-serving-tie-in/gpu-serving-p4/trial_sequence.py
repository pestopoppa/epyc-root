"""Isolated, default-disabled trial sequencing; no production operations."""
from dataclasses import dataclass
from typing import Any

from trial_response import TrialResponse, classify_response


@dataclass(frozen=True)
class TrialSequence:
    succeeded: bool
    reason: str
    responses: tuple[tuple[str, TrialResponse], ...] = ()


def run_trial(required_steps: Any = None, operations: Any = None, *,
              enabled: bool = False) -> TrialSequence:
    """Run explicitly ordered injected operations, stopping on first refusal.

    Each operation returns a dict containing status and optionally evidence and
    error. This helper does not authorize promotion or provide rollback.
    """
    if enabled is not True:
        return TrialSequence(False, "disabled")
    if (not isinstance(required_steps, tuple) or not required_steps
            or not all(isinstance(s, str) and s.strip() for s in required_steps)
            or len(set(required_steps)) != len(required_steps)
            or not isinstance(operations, dict)
            or set(operations) != set(required_steps)
            or not all(callable(operations[s]) for s in required_steps)):
        return TrialSequence(False, "invalid_steps")

    responses: list[tuple[str, TrialResponse]] = []
    for step in required_steps:
        try:
            result = operations[step]()
            if (not isinstance(result, dict) or "status" not in result
                    or not set(result) <= {"status", "evidence", "error"}):
                response = classify_response(evidence=result)
            else:
                response = classify_response(**result)
        except Exception as exc:
            response = classify_response(error=exc)
        responses.append((step, response))
        if not response.succeeded:
            return TrialSequence(False, "step_failed", tuple(responses))
    return TrialSequence(True, "completed", tuple(responses))
