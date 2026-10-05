"""In-memory environment state store + arm fixtures for the disposable runner.

The deterministic final-state judges are transcribed verbatim from DTAP; they
read environment state through the harness shims (harness/shims/*.py). The
state store below is what those shims read and write.

Arm fixtures (fixtures/<case_id>.<arm>.json) carry:
  * "initial_state"  - pre-seeded environment content (inbox, CRM records, ...).
  * "script"         - the stub agent's scripted tool calls; each call applies
                       a JSON-merge "state_delta" to the store. The executed
                       calls also populate the finance action log so judges that
                       inspect tool calls (has_called_tool etc.) work.
  * "agent_responses"- the final agent text responses (judge-visible).

`@now+<days>d` placeholder: a value of the string form "@now+7d" is materialized
as the ISO date `today + 7 days` at load time. This keeps day-relative judges
(e.g. CRM due-date windows) deterministic; the materialized value is what gets
recorded in the immutable trace, so replay is exact.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from .outcomes import InfrastructureFailure

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

NOW_RE = re.compile(r"^@now([+-]\d+)d$")


def default_store() -> Dict[str, Any]:
    return {
        "finance": {
            "transactions": [],
            "comments": {},
            "quotes": {},
            "portfolio": {},
            "options": [],
            "cancelled_orders": [],
            "action_log": [],
        },
        "gmail": {"messages": []},
        "slack": {"channels": {}},
        "salesforce": {"Leads": [], "Accounts": [], "Cases": [], "Notes": [], "Tasks": [], "Opportunities": []},
        "paypal": {"invoices": [], "payouts": []},
    }


def _materialize(value: Any, today: date) -> Any:
    if isinstance(value, str):
        m = NOW_RE.match(value)
        if m:
            return (today + timedelta(days=int(m.group(1)))).isoformat()
        return value
    if isinstance(value, dict):
        return {k: _materialize(v, today) for k, v in value.items()}
    if isinstance(value, list):
        return [_materialize(v, today) for v in value]
    return value


def materialize_fixture(data: Dict[str, Any], today: Optional[date] = None) -> Dict[str, Any]:
    return _materialize(data, today or date.today())


class StateStore:
    """The environment state that judges inspect, plus a JSON-merge patcher."""

    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        self.data = self._merged(default_store(), initial or {})

    def apply_merge_patch(self, patch: Dict[str, Any]) -> None:
        """Apply a scripted tool call's state delta (see `_merged` for the
        append-for-lists deviation from strict RFC 7386)."""
        self.data = self._merged(self.data, patch)

    def load_fixture(self, case_id: str, arm: str) -> Dict[str, Any]:
        """Load and materialize an arm fixture; raise InfrastructureFailure on any problem."""
        path = FIXTURES_DIR / f"{case_id}.{arm}.json"
        if not path.exists():
            raise InfrastructureFailure(f"fixture not found: {path.name}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InfrastructureFailure(f"fixture {path.name} is not valid JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise InfrastructureFailure(f"fixture {path.name} must be a JSON object")
        if "initial_state" not in raw:
            raise InfrastructureFailure(f"fixture {path.name} missing 'initial_state'")
        if "script" not in raw:
            raise InfrastructureFailure(f"fixture {path.name} missing 'script'")
        return materialize_fixture(raw)

    def reset(self, initial: Optional[Dict[str, Any]] = None) -> None:
        """Reset to the default store structure overlaid with `initial` (partial
        fixture states are merged over the canonical shape so later scripted
        deltas can always reach e.g. finance.action_log)."""
        self.data = self._merged(default_store(), initial or {})

    @staticmethod
    def _merged(target: Any, patch: Any) -> Any:
        if isinstance(patch, dict) and set(patch) == {"$set"}:
            return copy.deepcopy(patch["$set"])
        if isinstance(target, list) and isinstance(patch, list):
            return copy.deepcopy(list(target) + patch)
        if not isinstance(patch, dict):
            return copy.deepcopy(patch)
        if not isinstance(target, dict):
            target = {}
        for key, value in patch.items():
            if value is None:
                target.pop(key, None)
            else:
                target[key] = StateStore._merged(target.get(key), value)
        return target
