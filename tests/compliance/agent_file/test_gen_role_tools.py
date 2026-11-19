"""Committed *_prod.json name lists must equal what the production registry resolves (skip if orchestrator not importable)."""
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
VENV_PY = Path("/workspace/repos/epyc-orchestrator/.venv/bin/python")
PROBE = (
    "import sys,logging,types,json;sys.path.insert(0,'/workspace/repos/epyc-orchestrator');logging.disable(logging.CRITICAL)\n"
    "from src.registry.production import build_tool_registry\n"
    "r=build_tool_registry(types.SimpleNamespace(tools=True))\n"
    "print(json.dumps({k:sorted(n for n in r._tools if r.can_use_tool(k,n)) for k in ('worker_general','architect_general')}))\n"
)


def _resolve():
    if not VENV_PY.exists():
        pytest.skip("orchestrator venv unavailable")
    p = subprocess.run([str(VENV_PY), "-c", PROBE], capture_output=True, text=True)
    if p.returncode != 0:
        pytest.skip("orchestrator not importable")
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("role", ["worker_general", "architect_general"])
def test_committed_names_match_production(role):
    resolved = _resolve()[role]
    meta = json.loads((HERE / f"tools_{role}_prod.meta.json").read_text())
    arr = json.loads((HERE / f"tools_{role}_prod.json").read_text())
    assert meta["names"] == resolved
    assert [t["function"]["name"] for t in arr] == resolved
    assert meta["count"] == len(resolved)
