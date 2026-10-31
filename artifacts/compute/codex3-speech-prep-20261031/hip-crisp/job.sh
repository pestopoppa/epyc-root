#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt4-crisp-20261031
S=/mnt/micron/codex3-cs8-stt2-crisp-20261030/src
[[ $(git -C "$S" rev-parse HEAD) == 2aa8d7669fcaa18d98d61a4bc8a077464e6b9919 ]]
[[ -z $(git -C "$S" status --porcelain --untracked-files=no) ]]
export CCACHE_DISABLE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PATH=/opt/rocm/bin:/usr/bin:/bin
ulimit -c 0
: "${FILLER_DEADLINE:?}" "${BUILD_MODE:?}"
exec /usr/bin/nice -n 19 /usr/bin/python3 -B "$D/build-guard.py" "$S" "$D/build" "$D" "$FILLER_DEADLINE" "$BUILD_MODE"
