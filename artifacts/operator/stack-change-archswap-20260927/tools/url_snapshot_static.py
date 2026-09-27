#!/usr/bin/env python3
"""Operative-URL snapshot of an orchestrator TREE from its static sources only.

Same field enumeration as change-role/scripts/url_snapshot.sh, but with
ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS=1 so the live host's runtime-facts manifest
(which describes the CURRENT fleet labels) cannot mask what the tree's own config
resolves to. Run with cwd = the tree. Read-only.
usage: (cd <tree> && python url_snapshot_static.py) > out.tsv
"""
import dataclasses
import os
import sys

os.environ["ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS"] = "1"
os.environ.setdefault("ORCHESTRATOR_STACK_NUMA_MODE", "both")
sys.path.insert(0, os.getcwd())
from src.config import get_config  # noqa: E402

su = get_config().server_urls
for f in sorted(x.name for x in dataclasses.fields(su)):
    print(f"{f}\t{getattr(su, f)}")
