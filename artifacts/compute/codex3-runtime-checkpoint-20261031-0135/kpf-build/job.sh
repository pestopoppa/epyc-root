#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-kpf183-e332-build-r2-20261030
S=/mnt/micron/codex3-lanes/kpf-e332-src
B=/mnt/micron/codex3-lanes/kpf-e332-build
[[ $(sha256sum "$D/source-files.sha256" | cut -d' ' -f1) == 86e34ae3450420e3afc07f56e692b81d8cc8ebba5fdb74fd6e942297e6dc509b ]]
(cd "$S"; sha256sum --quiet -c "$D/source-files.sha256"; test "$(find . -type f | wc -l)" = "$(wc -l < "$D/source-files.sha256")")
export CCACHE_DISABLE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PATH=/usr/bin:/bin
ulimit -c 0
: "${FILLER_DEADLINE:?}" "${BUILD_MODE:?}"
exec /usr/bin/python3 -B "$D/build-guard.py" "$S" "$B" "$D" "$FILLER_DEADLINE" "$BUILD_MODE"
