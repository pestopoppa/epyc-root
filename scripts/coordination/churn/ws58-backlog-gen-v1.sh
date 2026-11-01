#!/bin/bash
# ws58 2026-11-01: zero-token generator of BACKLOG-<worker>.md (the ONE backlog per Codex worker) every 10 min.
# Replaces ws58-blocked-inference-feeder.sh (it still refreshes that WORK section with a pointer). Source of truth:
# /workspace scripts/coordination/backlog_gen.py (branch ws58-churn-flow-20261101); this is a byte copy, sha in the log.
set -euo pipefail
F=/mnt/raid0/llm/tmp/compute-flags
echo "$(date -u +%FT%TZ) backlog-gen start pid=$$ sha256=$(sha256sum $F/bin/backlog_gen.py | cut -c1-16)" >> $F/backlog-gen.log
echo $$ > $F/ws58-backlog-gen.pid
exec python3 -I $F/bin/backlog_gen.py --loop --interval 600 >> $F/backlog-gen.log 2>&1
