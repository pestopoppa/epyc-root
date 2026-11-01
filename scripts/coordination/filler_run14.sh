#!/bin/bash
# Canonical LOOP-49 entry. The allowlist binds this file AND runtime support.
set -euo pipefail
exec python3 -B "$(dirname "$(readlink -f "$0")")/filler_engine14.py" "$@"
