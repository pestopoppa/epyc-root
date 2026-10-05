"""PayPal helpers shim — same function surface as dt_arena/utils/paypal/helpers.py
(@ e0323a521ba4ef88f8e14c1eccf68d0a3d19a458, Apache-2.0), backed by the
in-memory StateStore ("paypal" -> {"invoices": [...], "payouts": [...]}).
"""
from __future__ import annotations

from typing import Any

_store: Any = None


def _set_store(store: Any) -> None:
    global _store
    _store = store


def list_invoices(access_token: str, status: str = None) -> list:
    invoices = _store.data["paypal"].get("invoices", [])
    if status:
        invoices = [i for i in invoices if (i.get("status") or "") == status]
    return list(invoices)


def list_payouts(access_token: str = "", token: str = "", status: str = None) -> list:
    payouts = _store.data["paypal"].get("payouts", [])
    if status:
        payouts = [p for p in payouts if (p.get("status") or "") == status]
    return list(payouts)
