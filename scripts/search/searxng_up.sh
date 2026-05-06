#!/bin/bash
set -euo pipefail
# SearxNG standalone launcher.
#
# Imports the canonical service definition from orchestrator_stack.py
# (DOCKER_SERVICES list) and calls start_docker_container() to bring up
# just SearxNG — not the full LLM stack. Use this when:
#   - Working in a Claude Code session that only needs web search
#   - Verifying the bash bridge in scripts/search/searx.sh
#   - Smoke-testing config changes to config/searxng/settings.yml
#
# Per `feedback_stack_managed_services` (memory): SearxNG remains a
# first-class member of orchestrator_stack.py — this wrapper does NOT
# duplicate the config; it imports the same dict.
#
# Usage: bash scripts/search/searxng_up.sh
#
# Exit codes:
#   0 — container running and health check passed
#   1 — docker not available
#   2 — container failed to start
#   3 — config import failed (orchestrator_stack.py path issue)

ORCHESTRATOR_REPO="${ORCHESTRATOR_REPO:-/workspace/repos/epyc-orchestrator}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found in PATH. Install docker or run on the production EPYC host." >&2
  exit 1
fi

if [[ ! -f "${ORCHESTRATOR_REPO}/scripts/server/orchestrator_stack.py" ]]; then
  echo "ERROR: orchestrator_stack.py not found at ${ORCHESTRATOR_REPO}. Set ORCHESTRATOR_REPO env." >&2
  exit 3
fi

# Defer to orchestrator_stack.py for the actual launch — single source of truth.
PYTHON="${ORCHESTRATOR_REPO}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

cd "$ORCHESTRATOR_REPO"
"$PYTHON" - <<'PYEOF'
"""Bring up only the searxng service from DOCKER_SERVICES."""
import sys
from pathlib import Path

# Make the orchestrator's scripts/ importable.
repo = Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
sys.path.insert(0, str(Path.cwd() / "scripts" / "server"))

from orchestrator_stack import (  # type: ignore[import-not-found]
    DOCKER_SERVICES,
    docker_container_running,
    start_docker_container,
)

target = next((s for s in DOCKER_SERVICES if s["name"] == "searxng"), None)
if target is None:
    print("ERROR: searxng not in DOCKER_SERVICES", file=sys.stderr)
    sys.exit(2)

if docker_container_running("searxng"):
    print(f"  searxng already running on port {target['port']}")
    sys.exit(0)

info = start_docker_container(target)
if info is None:
    print("ERROR: start_docker_container returned None", file=sys.stderr)
    sys.exit(2)

print(f"  searxng up on port {info.port} (container managed by docker)")
sys.exit(0)
PYEOF
