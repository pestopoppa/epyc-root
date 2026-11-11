"""Generate per-role OpenAI `tools` arrays from the PRODUCTION enforcement path (AFC v3c).

Supersedes gen_architect_tools.py, which filtered tool_registry.yaml by the category table
orchestration/tools/executor.py ROLE_PERMISSIONS -- a legacy table not used on the serving path.
Here the allowed set is whatever the orchestrator's own registry says:

    r = src.registry.production.build_tool_registry(SimpleNamespace(tools=True))
    allowed = sorted(n for n in r._tools if r.can_use_tool(role, n))

Run with the orchestrator venv:
    /workspace/repos/epyc-orchestrator/.venv/bin/python gen_role_tools.py [role ...]
Outputs next to this file: tools_<role>_prod.json and tools_<role>_prod.meta.json
(orchestrator git HEAD, model_registry.yaml / tool_registry.yaml sha256, count, names).
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import sys
import types
from pathlib import Path

ORCH = Path("/workspace/repos/epyc-orchestrator")
DEFAULT_ROLES = ("worker_general", "architect_general")
HERE = Path(__file__).resolve().parent


def resolve_allowed(role: str, orch: Path = ORCH):
    """Return (allowed_tool_objects sorted by name) for `role` via the production registry."""
    if str(orch) not in sys.path:
        sys.path.insert(0, str(orch))
    logging.disable(logging.CRITICAL)
    from src.registry.production import build_tool_registry

    r = build_tool_registry(types.SimpleNamespace(tools=True))
    return [r._tools[n] for n in sorted(r._tools) if r.can_use_tool(role, n)]


def tool_to_openai(tool) -> dict:
    """Tool(name, description, parameters, category) -> OpenAI function tool.

    `parameters` is either {pname: {type, description, required}} (YAML/builtin shorthand)
    or an already-formed JSON schema {"type": "object", "properties": ...}.
    """
    params = tool.parameters or {}
    if params.get("type") == "object" and isinstance(params.get("properties"), dict):
        schema = json.loads(json.dumps(params))
    else:
        props, required = {}, []
        for pname, p in params.items():
            p = dict(p) if isinstance(p, dict) else {"type": str(p)}
            if p.pop("required", False):
                required.append(pname)
            prop = {"type": p.get("type", "string")}
            if "description" in p:
                prop["description"] = p["description"]
            for k in ("enum", "default"):
                if k in p:
                    prop[k] = p[k]
            if prop["type"] == "array":
                prop["items"] = p.get("items", {})
            props[pname] = prop
        schema = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
    return {"type": "function", "function": {"name": tool.name, "description": tool.description or "", "parameters": schema}}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def generate(role: str, out_dir: Path = HERE, orch: Path = ORCH) -> tuple[Path, Path]:
    tools = resolve_allowed(role, orch)
    arr = [tool_to_openai(t) for t in tools]
    names = [t.name for t in tools]
    head = subprocess.run(["git", "-C", str(orch), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    meta = {
        "role": role,
        "orchestrator_head": head,
        "model_registry_yaml_sha256": _sha(orch / "orchestration" / "model_registry.yaml"),
        "tool_registry_yaml_sha256": _sha(orch / "orchestration" / "tool_registry.yaml"),
        "count": len(names),
        "names": names,
    }
    jp, mp = out_dir / f"tools_{role}_prod.json", out_dir / f"tools_{role}_prod.meta.json"
    jp.write_text(json.dumps(arr, indent=1) + "\n")
    mp.write_text(json.dumps(meta, indent=1) + "\n")
    return jp, mp


if __name__ == "__main__":
    for role in sys.argv[1:] or DEFAULT_ROLES:
        jp, mp = generate(role)
        print(f"{role}: {json.loads(mp.read_text())['count']} tools -> {jp}")
