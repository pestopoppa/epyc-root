#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 [[ ${FILLER_ID:-} == kpf62-native-g1-fixed-capture-20261027 && ${FILLER_CPUS:-} == 72,73 ]] || exit 70
 [[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 72-73 ]] || exit 70
 sha256sum --quiet -c "$B/CAPTURE-SOURCE.sha256"
 /usr/bin/python3 -I -B - "$B" <<'PY'
import ast,sys
from pathlib import Path
b=Path(sys.argv[1])
for p in (b/'job.py',b/'finalize.py',b/'native_refusal_controls.py',b/'deps/finalizer_v2.py'):ast.parse(p.read_text(),filename=str(p))
assert 'build-receipt.json' in (b/'job.py').read_text()
assert 'llama_chunk_kv_read_f32' in (b/'draft/tests/test-chunk-kv.cpp').read_text()
PY
 /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$B/capture-body.sh" --effect generated-tiny-capture
 exit 0
fi
bash "$B/check-complete.sh"
[[ -s "$B/build-receipt.json" && ! -L "$B/build-receipt.json" && -s "$B/CAPTURE-APPROVAL.txt" && ! -L "$B/CAPTURE-APPROVAL.txt" ]] || exit 70
sha256sum --quiet -c "$B/CAPTURE-SOURCE.sha256"
grep -Fx 'capture=MAIN-approved' "$B/CAPTURE-APPROVAL.txt" >/dev/null
grep -Fx "reviewed-build-sha256=$(sha256sum "$B/build-receipt.json" | cut -d' ' -f1)" "$B/CAPTURE-APPROVAL.txt" >/dev/null
grep -Fx "capture-source-sha256=$(sha256sum "$B/CAPTURE-SOURCE.sha256" | cut -d' ' -f1)" "$B/CAPTURE-APPROVAL.txt" >/dev/null
exec /bin/bash "$B/owner-capture.sh"
