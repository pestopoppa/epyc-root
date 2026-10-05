"""FinanceEnvClient shim — same method surface as dt_arena/utils/finance/helpers.py
(@ e0323a521ba4ef88f8e14c1eccf68d0a3d19a458, Apache-2.0), backed by the
in-memory StateStore instead of the simulated finance HTTP service.

The action log is populated by the runner as the stub executes the fixture
script's tool calls (one agent step + one tool step per call), so judges that
inspect tool calls (`has_called_tool`, `get_tool_call_params`, ...) observe the
executed trace.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_store: Any = None


def _set_store(store: Any) -> None:
    global _store
    _store = store


def _finance() -> Dict[str, Any]:
    return _store.data["finance"]


class FinanceEnvClient:
    """In-memory client for the simulated Finance environment state."""

    def __init__(self, host: Optional[str] = None, port: Optional[str] = None):
        self.host = host
        self.port = port

    # ===== Action Log APIs =====

    def get_action_log(self) -> List[Dict[str, Any]]:
        return list(_finance().get("action_log", []))

    def get_tool_calls(self) -> List[Dict[str, Any]]:
        return [s for s in self.get_action_log() if s.get("role") == "agent"]

    def get_tool_results(self) -> List[Dict[str, Any]]:
        return [s for s in self.get_action_log() if s.get("role") == "tool"]

    def has_called_tool(self, tool_name: str, **params) -> bool:
        for call in self.get_tool_calls():
            meta = call.get("metadata", {})
            if meta.get("tool_name") != tool_name:
                continue
            if not params:
                return True
            tp = meta.get("tool_params", {})
            if all(
                str(tp.get(k, "")).strip().lower() == str(v).strip().lower()
                for k, v in params.items()
            ):
                return True
        return False

    def get_tool_call_params(self, tool_name: str) -> List[Dict[str, Any]]:
        results = []
        for call in self.get_tool_calls():
            meta = call.get("metadata", {})
            if meta.get("tool_name") == tool_name:
                results.append(meta.get("tool_params", {}))
        return results

    def get_tool_call_with_results(self, tool_name: str = None) -> List[Dict[str, Any]]:
        steps = self.get_action_log()
        paired = []
        for i, step in enumerate(steps):
            if step.get("role") != "agent":
                continue
            meta = step.get("metadata", {})
            name = meta.get("tool_name", "")
            if not name:
                continue
            if tool_name and name != tool_name:
                continue
            result = ""
            for j in range(i + 1, min(i + 3, len(steps))):
                if steps[j].get("role") == "tool":
                    result = steps[j].get("state", steps[j].get("content", ""))
                    break
            paired.append({"tool_name": name, "params": meta.get("tool_params", {}), "result": str(result) if result else ""})
        return paired

    # ===== Portfolio APIs =====

    def get_portfolio(self) -> Dict[str, Any]:
        return dict(_finance().get("portfolio", {}))

    def get_transactions(self) -> List[Dict[str, Any]]:
        return list(_finance().get("transactions", []))

    def get_account_transactions(self, account_name: str) -> List[Dict[str, Any]]:
        return [
            t for t in self.get_transactions()
            if str(t.get("account", "")).strip().lower() == str(account_name).strip().lower()
        ]

    def get_comments(self) -> Dict[str, List[Dict[str, Any]]]:
        return {k: list(v) for k, v in (_finance().get("comments", {}) or {}).items()}

    def get_option_positions(self) -> List[Dict[str, Any]]:
        return list(_finance().get("options", []))

    # ===== Order APIs =====

    def get_cancelled_orders(self) -> List[Dict[str, Any]]:
        return list(_finance().get("cancelled_orders", []))

    # ===== Stock Data APIs =====

    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        return dict(_finance().get("quotes", {}).get(str(symbol).upper(), {}))

    # ===== Environment Control APIs =====

    def reset(self) -> bool:
        return True
