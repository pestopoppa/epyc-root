#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt4-transcribe-20261031
S=/mnt/raid0/llm/tmp/dive-transcribe-cpp/tc
[[ $(git -C "$S" rev-parse HEAD) == db678a031cf4c524bcab2c45a0dc6a7813106e4a ]]
[[ -z $(git -C "$S" status --porcelain --untracked-files=no) ]]
export CCACHE_DISABLE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PATH=/opt/rocm/bin:/usr/bin:/bin
ulimit -c 0
: "${FILLER_DEADLINE:?}" "${BUILD_MODE:?}"
exec /usr/bin/nice -n 19 /usr/bin/python3 -B "$D/build-guard.py" "$S" "$D/build" "$D" "$FILLER_DEADLINE" "$BUILD_MODE"
