#!/bin/bash
# akx27_run.sh -- AKX-ALL-27b run driver (probe both gpu-20261021-{732389d6d,b0eb4fab4} HIP builds, width_dimension vs the parent).
# Runs INSIDE the exclusive GPU claim: armed as  filler_run2.sh --id akx-all-27b-run --class gpu --gpu-quiet exclusive --cmd 'bash .../akx27_run.sh --execute'
# usage: akx27_run.sh --dry-run|--execute [--stand-in]   (dry-run validates builds/linkage/route/commands/importability, launches nothing)
set -uo pipefail
D=/mnt/raid0/llm/tmp/fillers-3c4ca599/v11drv
case "${1:-}" in
  --dry-run|--execute) exec /usr/bin/python3 -I "$D/akx27_driver.py" "$@" ;;
  --selftest) exec /usr/bin/python3 -I "$D/akx27_driver.py" --selftest ;;
  *) sed -n '2,5p' "$0"; exit 64 ;;
esac
