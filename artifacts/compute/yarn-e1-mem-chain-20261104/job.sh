#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/yarn-e1-mem-chain-20261104
cd "$D"
sha256sum -c SOURCE.sha256 >/dev/null
sha256sum -c image.sha256 >/dev/null
if [ "${FILLER_DRYRUN:-0}" = 1 ]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?dryrun result path required}"
  : "${FILLER_DRYRUN_DIR:?dryrun directory required}"
  /usr/bin/python3 - "$D/pregrant-provenance.json" "$D/model-pregrant.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); snap=Path(sys.argv[2]); assert p.is_file() and snap.is_file(), 'pregrant provenance/model snapshot gate missing'
d=json.loads(p.read_text()); m=json.loads(snap.read_text()); assert d.get('status')=='PASS', 'pregrant validation not PASS'
assert m.get('path')=='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf' and m.get('size')==29047086048, 'pregrant model snapshot mismatch'
assert d.get('model_size_bytes')==m.get('size'), 'pregrant model size mismatch'
assert d.get('image_version')=='version: 10325 (9a3f1392a)', 'pinned E1 version/source mismatch'
PY
  exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/run_chain.py" --smoke
fi
exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/run_chain.py"
