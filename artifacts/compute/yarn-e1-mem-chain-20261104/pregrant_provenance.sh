#!/bin/bash
# Run once before requesting a grant. Local HF-tokenizer checks and provenance occur outside the grant.
set -euo pipefail
D=/mnt/raid0/llm/tmp/yarn-e1-mem-chain-20261104
cd "$D"
MODEL=/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
IMAGE=/mnt/raid0/llm/kernels/builds/gpu-20261004-9a3f1392a/bin
sha256sum -c "$D/image.sha256" >/dev/null
sha256sum -c "$D/SOURCE.sha256" >/dev/null
[ "$(stat -c %s "$MODEL")" = 29047086048 ]
[ -f "$D/model-pregrant.json" ] || { echo "model-pregrant snapshot missing" >&2; exit 2; }
mkdir -p "$D/pregrant"
LD_LIBRARY_PATH="$IMAGE:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib" "$IMAGE/llama-server" --version > "$D/pregrant/image-version.txt" 2>&1
grep -Fx 'version: 10325 (9a3f1392a)' "$D/pregrant/image-version.txt" >/dev/null
YARN_E1_RESULTS="$D/pregrant/results" YARN_E1_GATE="$D/pregrant/gate" \
  /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B "$D/yarn_needle.py" --dry-run > "$D/pregrant/yarn-dry-run.log" 2>&1
/usr/bin/python3 - "$D" "$MODEL" <<'PY'
import hashlib,json,sys,time
from pathlib import Path
d=Path(sys.argv[1]); model=Path(sys.argv[2]); log=(d/'pregrant/yarn-dry-run.log').read_text(errors='replace'); snap=json.loads((d/'model-pregrant.json').read_text())
if 'DRY-RUN OK' not in log: raise SystemExit('pregrant yarn_needle dry-run did not pass')
version=(d/'pregrant/image-version.txt').read_text().splitlines()[0].strip()
if version!='version: 10325 (9a3f1392a)': raise SystemExit('unexpected E1 image source/version')
st=model.stat();
if snap.get('path')!=str(model) or snap.get('size')!=st.st_size or snap.get('inode')!=st.st_ino or snap.get('mtime_ns')!=st.st_mtime_ns: raise SystemExit('model-pregrant snapshot does not match current file stat')
if len(snap.get('sha256',''))!=64 or any(c not in '0123456789abcdef' for c in snap['sha256']): raise SystemExit('model-pregrant snapshot lacks the sealed SHA-256')
obj={'schema':'yarn-e1-mem-chain-pregrant-provenance/v1','status':'PASS','captured_epoch':time.time(),'model_path':str(model),'model_size_bytes':st.st_size,'model_pregrant_snapshot':snap,'image_version':version,'image_version_output':str(d/'pregrant/image-version.txt'),'image_version_output_sha256':hashlib.sha256((d/'pregrant/image-version.txt').read_bytes()).hexdigest(),'image_manifest_sha256':hashlib.sha256((d/'image.sha256').read_bytes()).hexdigest(),'source_manifest_sha256':hashlib.sha256((d/'SOURCE.sha256').read_bytes()).hexdigest(),'segment_token_counts_sha256':hashlib.sha256((d/'stage-token-counts.json').read_bytes()).hexdigest(),'yarn_dry_run_log':str(d/'pregrant/yarn-dry-run.log')}
(d/'pregrant-provenance.json').write_text(json.dumps(obj,indent=2)+'\n')
PY
