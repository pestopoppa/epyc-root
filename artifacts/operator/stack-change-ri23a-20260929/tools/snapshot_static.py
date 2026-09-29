#!/usr/bin/env python3
"""RI-23a static snapshot of an orchestrator TREE: operative URLs + per-role request-side
thinking facts. Read-only; run with cwd = the tree.

Sections (tab-separated, one fact per line, sorted):
  url      <server_urls field>            <url>
  ctk      <server_mode role>             <chat_template_kwargs as sorted JSON, or null>
  priors   <live role>                    enable_thinking=<descriptor-derived> jinja=<bool>
  lane     thinking_chat_lane_roles       <sorted list>   (the RI-23 admission set; flag-independent)

URLs use ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS=1 (the live host's runtime-facts manifest
must not mask what the tree resolves to), exactly as ARCHSWAP's url_snapshot_static.py.
The ctk rows are what registry_loader.chat_template_kwargs_for_role() returns for each
server_mode row of THIS tree's lean registry: the value the backend puts in the POST body.
usage: (cd <tree> && python snapshot_static.py) > out.tsv
"""
import dataclasses
import json
import os
import sys

os.environ["ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS"] = "1"
os.environ.setdefault("ORCHESTRATOR_STACK_NUMA_MODE", "both")
sys.path.insert(0, os.getcwd())

import yaml  # noqa: E402

from src.config import get_config  # noqa: E402
from src.registry.registry_loader import RegistryLoader  # noqa: E402

su = get_config().server_urls
for f in sorted(x.name for x in dataclasses.fields(su)):
    print(f"url\t{f}\t{getattr(su, f)}")

lean = os.path.join(os.getcwd(), "orchestration/model_registry.yaml")
loader = RegistryLoader(registry_path=lean, validate_paths=False)
with open(lean, encoding="utf-8") as fh:
    sm = (yaml.safe_load(fh) or {}).get("server_mode") or {}
for role in sorted(sm):
    ctk = loader.get_role_chat_template_kwargs(role)
    print(f"ctk\t{role}\t{json.dumps(ctk, sort_keys=True)}")

with open(os.path.join(os.getcwd(), "orchestration/derived/stack_priors.yaml"), encoding="utf-8") as fh:
    pri = yaml.safe_load(fh) or {}
roles = pri.get("roles") or {}
for role in sorted(roles):
    rec = roles[role] or {}
    if rec.get("deployment_status") != "live_stack":
        continue
    acc = rec.get("acceleration") or {}
    flags = (((rec.get("serving") or {}).get("launch") or {}).get("runtime") or {}).get("flags") or {}
    print(f"priors\t{role}\tenable_thinking={acc.get('enable_thinking')} jinja={flags.get('jinja')}")
lane = sorted(
    r for r, rec in roles.items()
    if (rec or {}).get("deployment_status") == "live_stack"
    and ((((rec.get("serving") or {}).get("launch") or {}).get("runtime") or {}).get("flags") or {}).get("jinja") is True
    and (rec.get("acceleration") or {}).get("enable_thinking") is True
)
print(f"lane\tthinking_chat_lane_roles\t{json.dumps(lane)}")
