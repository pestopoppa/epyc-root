"""URE-2 live escalation writes into the shared trace store.

An escalation permits one re-answer or a role transition, never arbitrary
edits. System approval is not human review. Missing quality/uncertainty
evidence stays NULL; a decision-time signature is explicitly partial.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from src.trace.harness_schema import (
    ApprovalRecord,
    BehaviorSignature,
    insert_approval_record,
    insert_behavior_signature,
)
from src.trace.store import DEFAULT_DB_PATH, ensure_schema

log = logging.getLogger(__name__)


class _Transaction:
    """Keep the legacy insert helpers' commits inside our pair transaction."""

    def __init__(self, conn):
        self.execute = conn.execute

    def commit(self):
        pass


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def call_escalation(
    primitives,
    prompt,
    *,
    from_role,
    to_role,
    request_id,
    reason,
    alternatives,
    **kwargs,
):
    """One live re-answer attempt; preserve the backend's return/exception."""
    answer = None
    outcome = "failed"
    try:
        result = primitives.llm_call(prompt, role=to_role, **kwargs)
        answer = result if isinstance(result, str) else None
        outcome = (
            "in_band_error"
            if answer and answer.strip().startswith("[ERROR")
            else "returned"
            if answer and answer.strip()
            else "empty"
        )
        return result
    except Exception as exc:
        outcome = f"raised:{type(exc).__name__}"
        raise
    finally:
        record_live_escalation(
            request_id=request_id,
            prompt=prompt,
            from_role=from_role,
            to_role=to_role,
            reason=reason,
            primitives=primitives,
            outcome=outcome,
            answer=answer,
            alternatives=alternatives,
            boundary="re-answer this request once with the selected role",
        )


def record_live_escalation(
    *,
    request_id: str | None,
    prompt: str | None,
    from_role: str,
    to_role: str,
    reason: str,
    primitives=None,
    outcome: str = "selected_pending_execution",
    answer: str | None = None,
    alternatives: list[str] | None = None,
    boundary: str = "continue this request with the selected role",
    db_path: Path | str | None = None,
) -> int | None:
    """Write one linked pair atomically. A failed writer cannot break serving.

    Called at the owning transition/attempt, never at response rendering, so
    two same-role attempts in one request remain two distinct decisions.
    Outcomes describe this attempt, not inferred task success. No raw prompt
    or answer is retained. Callers must not invoke this for shadow decisions.
    """
    conn = None
    try:
        model = None
        getter = getattr(getattr(primitives, "registry", None), "get_role", None)
        if callable(getter):
            try:
                name = getattr(getattr(getter(to_role), "model", None), "name", None)
                model = name if isinstance(name, str) and name else None
            except Exception as exc:
                log.debug(
                    "URE-2 model identity unavailable: %s",
                    type(exc).__name__,
                    exc_info=True,
                )
        task_signature = _hash(prompt) if isinstance(prompt, str) else None
        path_hash = _hash([from_role, to_role])
        conn = ensure_schema(db_path if db_path is not None else DEFAULT_DB_PATH)
        with conn:
            transaction = _Transaction(conn)
            signature_id = insert_behavior_signature(
                transaction,
                BehaviorSignature(
                    answer_hash=_hash(answer) if answer is not None else None,
                    route_path_hash=path_hash,
                    escalation_path_hash=path_hash,
                    signature_hash=_hash([task_signature, path_hash, outcome, model]),
                    signature_confidence="partial",
                ),
            )
            return insert_approval_record(
                transaction,
                ApprovalRecord(
                    request_id=request_id,
                    task_signature=task_signature,
                    selected_role=to_role,
                    selected_model=model,
                    alternatives=alternatives
                    if alternatives is not None
                    else [from_role],
                    trigger_reason=reason,
                    approval_boundary=boundary,
                    actor="system",
                    downstream_outcome=outcome,
                    behavior_signature_id=signature_id,
                ),
            )
    except Exception:
        log.warning("URE-2 live escalation persistence failed", exc_info=True)
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                log.warning("URE-2 trace connection close failed", exc_info=True)
