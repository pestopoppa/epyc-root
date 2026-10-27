#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-c5-api-port
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 [[ ${FILLER_ID:-} == kpf62-native-g1-build-20261027 && ${FILLER_CPUS:-} == 0,1 ]] || exit 70
 [[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 0-1 ]] || exit 70
 (cd "$B" && sha256sum --quiet -c SOURCE.SHA256SUMS && sha256sum --quiet -c NATIVE-SOURCES.sha256)
 for f in "$B"/launch.sh "$B"/guard.sh "$B"/build-body.sh "$B"/build-poller.sh; do bash -n "$f"; done
 /usr/bin/python3 -I -B - "$B" <<'PY'
import ast,sys
from pathlib import Path
b=Path(sys.argv[1])
for p in (b/'job.py',b/'prepare_candidate.py',b/'finalize.py',b/'resource-watch.py'):ast.parse(p.read_text(),filename=str(p))
PY
 git -C /mnt/raid0/llm/llama.cpp cat-file -e c72ec82f5417bb2937310326120f149b665e8400^{commit}
 git -C /workspace cat-file -e 297b166dbd27a88f14dc4de8f8858c07bf17b137^{commit}
 /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$B/build-body.sh" --effect source-build
 exit 0
fi
exec /bin/bash "$B/owner-build.sh"
