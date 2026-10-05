"""Slack helpers shim — same surface as dt_arena/utils/slack/helpers.py
(@ e0323a521ba4ef88f8e14c1eccf68d0a3d19a458, Apache-2.0), backed by the
in-memory StateStore ("slack" -> {"channels": {channel: [messages]}}).
"""
from __future__ import annotations

from typing import Any, Dict, List

_store: Any = None


def _set_store(store: Any) -> None:
    global _store
    _store = store


def get_channel_messages(
    channel: str,
    token: str,
    workspace_id: str = "W01",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return messages for a channel (list of {"text", ...} dicts)."""
    if not token:
        return []
    messages = _store.data["slack"]["channels"].get(channel, [])
    return list(messages)[:limit]


def channel_feed(
    channel: str,
    token: str,
    workspace_id: str = "W01",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Alias with the same semantics (kept for surface parity with upstream)."""
    return get_channel_messages(channel, token, workspace_id=workspace_id, limit=limit)
