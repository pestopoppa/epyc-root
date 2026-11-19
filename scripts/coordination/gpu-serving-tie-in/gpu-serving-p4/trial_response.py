"""Pure response classification for the isolated P4 prototype.

This module neither invokes an operation nor authorizes promotion.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TrialResponse:
    succeeded: bool
    reason: str
    status: Any
    evidence: Any
    error: Any


def classify_response(*, status: Any = None, evidence: Any = None,
                      error: Any = None) -> TrialResponse:
    """Classify one operation, retaining its inputs even on refusal.

    Only an explicit integer HTTP 2xx status with no error succeeds. The caller
    must classify every operation and separately enforce the trial lifecycle.
    """
    if error is not None:
        reason = "operation_error"
    elif type(status) is not int or not 100 <= status <= 599:
        reason = "missing_or_malformed_status"
    elif not 200 <= status <= 299:
        reason = "non_success_status"
    else:
        return TrialResponse(True, "success", status, evidence, error)
    return TrialResponse(False, reason, status, evidence, error)
