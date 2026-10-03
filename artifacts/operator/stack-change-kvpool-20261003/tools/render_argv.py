#!/usr/bin/env python3
"""Render the launcher argv for a role from a tree's COMPILED priors + lean (starts nothing).

usage: render_argv.py <orch-tree> <role> <port>
Also applies the topology's numactl/taskset prefix the way `start` does, when exposed.
"""
import json
import sys
from pathlib import Path

tree, role, port = Path(sys.argv[1]).resolve(), sys.argv[2], int(sys.argv[3])
sys.path.insert(0, str(tree))
import yaml  # noqa: E402

from scripts.server import orchestrator_stack as ostack  # noqa: E402
from src.registry.registry_loader import RegistryLoader  # noqa: E402

priors = yaml.safe_load((tree / "orchestration/derived/stack_priors.yaml").read_text())


def _find(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == role and isinstance(v, dict) and "serving" in v:
                return v
            r = _find(v)
            if r is not None:
                return r
    return None


rec = _find(priors)
launch = rec["serving"]["launch"]
flags = launch["runtime"]["flags"]
print("compiled requirements:", json.dumps(launch.get("requirements")))
print("compiled spec:", json.dumps(flags.get("spec")))
print("compiled device:", flags.get("device"), "| binary:", launch["runtime"].get("binary_path"))
reg = RegistryLoader(registry_path=tree / "orchestration/model_registry.yaml")
cmd = ostack.build_server_command(reg.get_role(role), port, prepare_runtime_dirs=False)
print(f"rendered :{port} argv:")
print("  " + " ".join(cmd))
