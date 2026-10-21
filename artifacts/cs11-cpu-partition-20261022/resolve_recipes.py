#!/usr/bin/env python3
"""CS-11: resolve the codified launch recipes for frontdoor(:8070) and architect_general(:8074) from the
orchestrator's own builders (registry + compiled stack priors). READ-ONLY: no server is started, no dirs created.
Run with: /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python resolve_recipes.py OUT.json"""
import json, os, sys
ORCH = "/mnt/raid0/llm/epyc-orchestrator"
sys.path.insert(0, ORCH); os.chdir(ORCH)
os.environ["ORCHESTRATOR_STACK_REEXEC"] = "1"
from scripts.server import orchestrator_stack as S
from src.registry_loader import RegistryLoader
reg = RegistryLoader()
out = {"orch_head": os.popen(f"git -C {ORCH} rev-parse --short HEAD").read().strip(), "roles": {}}
for role, port in (("frontdoor", 8070), ("architect_general", 8074)):
    rc = reg.get_role(role)
    cmd = S.build_server_command(rc, port, numa_instance=0, prepare_runtime_dirs=False)
    prefix = S._numa_prefix(role, 0)
    env = S.build_launch_env(role, {})
    bo, ld = S._stack_prior_runtime_overrides(role)
    out["roles"][role] = {"port": port, "cmd": cmd, "numa_prefix": prefix, "declared_env": env,
                          "binary_override": bo, "ld_paths": ld, "model": rc.model.full_path,
                          "numa_cfg": S.NUMA_CONFIG.get(role)}
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)
print(json.dumps({r: {"cmd": v["cmd"], "prefix": v["numa_prefix"]} for r, v in out["roles"].items()}, indent=1))
