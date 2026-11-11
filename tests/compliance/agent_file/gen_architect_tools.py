"""Generate the OpenAI-style `tools` array offered to architect_general (AFC-P5.E3 r6).

Source of truth (read-only, epyc-orchestrator):
  orchestration/tool_registry.yaml            -- tool specs
  orchestration/tools/executor.py ToolRegistry.ROLE_PERMISSIONS["architect_general"]
      == {"web", "data", "llm"}                -- category filter; list_tools(role) keeps those categories
Output: tools_architect_general.json next to this file (committed with the row so the run is self-contained).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ARCHITECT_GENERAL_CATEGORIES = {"web", "data", "llm"}  # executor.py ROLE_PERMISSIONS["architect_general"]
WORKER_GENERAL_CATEGORIES = {"web", "data", "math", "llm"}  # ROLE_PERMISSIONS["worker_general"] (v3 q36 rows; usage: gen_architect_tools.py [registry.yaml] worker_general)


def spec_to_openai_tool(name: str, spec: dict) -> dict:
    props, required = {}, []
    for pname, p in (spec.get("parameters") or {}).items():
        p = dict(p or {})
        if p.pop("required", False):
            required.append(pname)
        prop = {"type": p.get("type", "string")}
        if "description" in p:
            prop["description"] = p["description"]
        if prop["type"] == "array":
            prop["items"] = {}
        props[pname] = prop
    params = {"type": "object", "properties": props}
    if required:
        params["required"] = required
    return {"type": "function", "function": {"name": name, "description": spec.get("description", ""), "parameters": params}}


def build_tools(registry_yaml: Path) -> list[dict]:
    data = yaml.safe_load(registry_yaml.read_text())
    return [spec_to_openai_tool(n, s) for n, s in data["tools"].items() if s.get("category", "") in ARCHITECT_GENERAL_CATEGORIES]


if __name__ == "__main__":
    reg = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/repos/epyc-orchestrator/orchestration/tool_registry.yaml")
    role = sys.argv[2] if len(sys.argv) > 2 else "architect_general"
    if role == "worker_general":
        ARCHITECT_GENERAL_CATEGORIES = WORKER_GENERAL_CATEGORIES
    out = Path(__file__).with_name(f"tools_{role}.json")
    tools = build_tools(reg)
    out.write_text(json.dumps(tools, indent=1) + "\n")
    print(f"{len(tools)} tools -> {out}")
