#!/bin/bash
# Grant-only entry point. All child fixtures are synthetic; no servers or network.
set -euo pipefail
D=$(cd -- "$(dirname -- "$0")" && pwd)
exec /usr/bin/python3 -I "$D/bundle_gate_verdict_c5_regression.py"
