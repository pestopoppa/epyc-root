"""Utils shim — transcribed from dt_arena/utils/utils/__init__.py
(@ e0323a521ba4ef88f8e14c1eccf68d0a3d19a458, Apache-2.0).

`load_task_config` is registry-backed instead of YAML-file-backed: the harness
transcribes upstream config.yaml into cases.json, and the transcribed judges
call load_task_config(_task_dir) where _task_dir resolves to the unique case id
(the transcribed judge's directory name). The upstream mcp.yaml fallback is not
mirrored — there is no global environment config in the disposable runner, so
get_mcp_env_var returns None for anything not in the task config or os.environ,
which is what upstream does when mcp.yaml has no entry.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional


class Registry:
    """Lazily-loaded case registry (cases.json) keyed by case id."""

    _cases: Optional[Dict[str, dict]] = None

    @classmethod
    def cases(cls) -> Dict[str, dict]:
        if cls._cases is None:
            from harness import REGISTRY_PATH  # noqa: PLC0415

            import json  # noqa: PLC0415

            with open(REGISTRY_PATH, encoding="utf-8") as fh:
                cls._cases = json.load(fh)["cases"]
        return cls._cases

    @classmethod
    def config_for(cls, task_dir: Path) -> Dict[str, Any]:
        case_id = Path(task_dir).resolve().name
        case = cls.cases().get(case_id)
        if case is None:
            return {}
        return case.get("config") or {}


def _resolve_template(value: str) -> str:
    """Resolve ${VAR} placeholders using os.environ (upstream semantics)."""

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(r"\$\{(\w+)\}", replacer, value)


def normalize_amounts(text: str) -> str:
    """Remove commas from numbers in text for flexible comparison (upstream)."""
    return re.sub(r"(\d),(\d)", r"\1\2", text)


def load_task_config(task_dir: Path) -> Dict[str, Any]:
    """Return the transcribed task config for the case owning `task_dir`."""
    return Registry.config_for(task_dir)


def _search_mcp_servers_recursive(agent_cfg: Dict[str, Any], mcp_name: str, var_name: str) -> Optional[str]:
    """Recursively search for MCP server env var in agent config and subagents (upstream)."""
    mcp_servers = agent_cfg.get("mcp_servers", [])
    for srv in mcp_servers:
        if srv.get("name", "").lower() == mcp_name.lower():
            env_vars = srv.get("env_vars", {})
            if var_name in env_vars:
                value = env_vars.get(var_name)
                if value:
                    return _resolve_template(str(value))
    for sub_agent in agent_cfg.get("sub_agents", []):
        result = _search_mcp_servers_recursive(sub_agent, mcp_name, var_name)
        if result:
            return result
    return None


def get_mcp_env_var(config: Dict[str, Any], mcp_name: str, var_name: str) -> Optional[str]:
    """Get an environment variable from MCP server config (upstream resolution order)."""
    env_value = os.environ.get(var_name)
    if env_value:
        return env_value
    agent_cfg = config.get("Agent", {})
    result = _search_mcp_servers_recursive(agent_cfg, mcp_name, var_name)
    if result:
        return result
    return None
