"""Persistent MCP tool registry with health checks (NIB2-44 AW-1).

JSONL-backed — one record per tool. Entries carry provenance, endpoint
metadata, and a rolling health signal. The registry is append-only
except for health-field updates; deletions are logical (``active=False``)
to preserve the discovery trail.

Health check strategy is intentionally pluggable: the caller provides an
async ``check`` callback. For HTTP MCP tools that would typically be a
HEAD / JSON-RPC probe; for local tools it could be a subprocess ping.
The registry only tracks results and rate-limits checks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Optional

log = logging.getLogger("autopilot.env_synth.mcp_tool_registry")

HealthCheck = Callable[["MCPToolEntry"], Awaitable[bool]]


@dataclass
class MCPToolEntry:
    """One record in the persistent MCP tool registry."""

    tool_id: str                       # stable id (provenance key)
    name: str
    description: str
    endpoint: str                      # URL or `stdio://<binary>` for local tools
    discovered_via: str                # "etd_web" | "etd_github" | "manual" | ...
    environment_id: str = ""
    schema: dict[str, Any] = field(default_factory=dict)  # MCP tool schema (args, returns)
    active: bool = True
    discovered_at: str = ""
    last_health_check: str = ""
    last_health_ok: Optional[bool] = None  # None until first check
    consecutive_failures: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "MCPToolEntry":
        return cls(**json.loads(raw))


class MCPToolRegistry:
    """Append-only JSONL registry for discovered MCP tools."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, MCPToolEntry] = {}
        self._load()

    # ── persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = MCPToolEntry.from_json(line)
            except json.JSONDecodeError:
                log.warning("Skipping malformed registry line: %s", line[:120])
                continue
            self._index[entry.tool_id] = entry

    def _append(self, entry: MCPToolEntry) -> None:
        with self.path.open("a") as f:
            f.write(entry.to_json() + "\n")

    def _rewrite(self) -> None:
        """Rewrite the registry with the current in-memory index.

        Used when health fields mutate — keeps JSONL canonical.
        """
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w") as f:
            for e in self._index.values():
                f.write(e.to_json() + "\n")
        tmp.replace(self.path)

    # ── public API ─────────────────────────────────────────────────

    def register(self, entry: MCPToolEntry) -> None:
        """Add a new tool. Overwrites an existing entry with the same id."""
        if not entry.discovered_at:
            entry.discovered_at = datetime.now(timezone.utc).isoformat()
        is_new = entry.tool_id not in self._index
        self._index[entry.tool_id] = entry
        if is_new:
            self._append(entry)
        else:
            self._rewrite()

    def deactivate(self, tool_id: str) -> None:
        entry = self._index.get(tool_id)
        if entry is None or not entry.active:
            return
        entry.active = False
        self._rewrite()

    def get(self, tool_id: str) -> Optional[MCPToolEntry]:
        return self._index.get(tool_id)

    def all(self) -> list[MCPToolEntry]:
        return list(self._index.values())

    def active(self) -> list[MCPToolEntry]:
        return [e for e in self._index.values() if e.active]

    def by_environment(self, environment_id: str) -> list[MCPToolEntry]:
        return [e for e in self._index.values() if e.environment_id == environment_id]

    # ── health check loop ─────────────────────────────────────────

    async def run_health_checks(
        self,
        check: HealthCheck,
        *,
        max_parallel: int = 4,
        deactivate_after: int = 3,
        targets: Optional[Iterable[MCPToolEntry]] = None,
    ) -> dict[str, Any]:
        """Run ``check`` against each active tool; update health fields.

        Tools failing ``deactivate_after`` consecutive checks are flipped
        to ``active=False`` (caller can re-register manually to re-add).
        """
        targets = list(targets) if targets is not None else self.active()
        sem = asyncio.Semaphore(max(1, max_parallel))
        deactivated: list[str] = []
        ok_count = 0
        fail_count = 0

        async def _one(entry: MCPToolEntry) -> None:
            nonlocal ok_count, fail_count
            async with sem:
                try:
                    ok = await check(entry)
                except Exception as e:
                    log.debug("health check for %s raised: %s", entry.tool_id, e)
                    ok = False
                entry.last_health_check = datetime.now(timezone.utc).isoformat()
                entry.last_health_ok = ok
                if ok:
                    entry.consecutive_failures = 0
                    ok_count += 1
                else:
                    entry.consecutive_failures += 1
                    fail_count += 1
                    if entry.consecutive_failures >= deactivate_after:
                        entry.active = False
                        deactivated.append(entry.tool_id)

        await asyncio.gather(*[_one(e) for e in targets])
        self._rewrite()

        return {
            "checked": len(targets),
            "ok": ok_count,
            "failed": fail_count,
            "deactivated": deactivated,
        }
