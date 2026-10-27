#!/bin/bash
set -euo pipefail
source /mnt/raid0/llm/tmp/codex-ni-20261027-meta-build-recovery/owned-bootstrap.sh
active=''; bootstrap_start=''
cleanup() { if [[ -n $active && -n $bootstrap_start ]]; then bootstrap_drain || true; fi; }
trap cleanup EXIT
setsid sleep 120 &
active=$!
for _ in {1..100}; do bootstrap_capture && break; sleep 0.01; done
[[ -n $bootstrap_start ]]
bootstrap_scan
[[ ${#bootstrap_members[@]} -ge 1 ]]
old=$bootstrap_start; bootstrap_start=0
if bootstrap_scan; then echo 'incorrect identity accepted' >&2; exit 1; fi
bootstrap_start=$old
bootstrap_drain
active=''
echo 'PASS scan with foreign mixed UIDs; rejects wrong captured start; drains captured process'
