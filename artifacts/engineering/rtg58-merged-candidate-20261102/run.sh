#!/bin/bash
set -euo pipefail
src=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-integrated-p4-g3-cascade-20261102
out=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-integrated-merge-validation-20261102
build=/mnt/micron/rtg58-integrated-p4-g3-cascade-cpu-20261102
trap 'rc=$?; printf "%s\n" "$rc" > "$out/EXIT_CODE"; touch "$out/FINISHED"' EXIT
[ "$(git -C "$src" rev-parse HEAD)" = 3ec14227a0e293bfc223c9026ed761ea3bdda9bb ]
[ -z "$(git -C "$src" status --porcelain)" ]
sudo nsenter -t 1 -m -- setpriv --reuid 1000 --regid 1000 --init-groups taskset -c 24-29 cmake -S "$src" -B "$build" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=OFF -DGGML_CCACHE=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TOOLS=OFF
sudo nsenter -t 1 -m -- setpriv --reuid 1000 --regid 1000 --init-groups taskset -c 24-29 cmake --build "$build" -j 6 --target test-kv-rows-op test-cascade-attention-reference test-chunk-kv-g3 test-backend-ops
sudo nsenter -t 1 -m -- setpriv --reuid 1000 --regid 1000 --init-groups env LD_LIBRARY_PATH="$build/bin" taskset -c 24-29 "$build/bin/test-kv-rows-op"
sudo nsenter -t 1 -m -- setpriv --reuid 1000 --regid 1000 --init-groups env LD_LIBRARY_PATH="$build/bin" taskset -c 24-29 "$build/bin/test-cascade-attention-reference"
sudo nsenter -t 1 -m -- setpriv --reuid 1000 --regid 1000 --init-groups sha256sum "$build/bin/test-kv-rows-op" "$build/bin/test-cascade-attention-reference" "$build/bin/test-chunk-kv-g3" "$build/bin/test-backend-ops" "$build/bin/libllama.so" > "$out/BINARIES.sha256"
mkdir -p "$out/g3-tiny"
sudo nsenter -t 1 -m -- setpriv --reuid 1000 --regid 1000 --init-groups env LD_LIBRARY_PATH="$build/bin" taskset -c 24-29 "$build/bin/test-chunk-kv-g3" -m /mnt/raid0/llm/tmp/kpf-p1-20261004/smoke-20261004T073455Z/test-models/qwen3-dense.gguf -ngl 0 -t 4 -tb 4 -b 512 -ub 512 -ctk f32 -ctv f32 --g3-self-test --g3-out "$out/g3-tiny" --g3-modes all-inject --g3-outcome-mode all-inject --g3-outcome-tokens 4
python3 - "$out/g3-tiny/outcomes.jsonl" <<'PY'
import json, sys
rows = [json.loads(x) for x in open(sys.argv[1])]
assert len(rows) == 8, len(rows)
for i in range(0, len(rows), 2):
    a,b=rows[i:i+2]
    assert a['id']==b['id'] and a['arm']=='full' and b['arm']=='reuse'
    assert a['output_tokens']==b['output_tokens'] and a['output_text']==b['output_text']
    assert a['complete']==b['complete'] and a['finish_reason']==b['finish_reason']
    assert a['finish_reason'] in ('eog','length') and a['complete']==(a['finish_reason']=='eog')
print('PASS: four paired all-inject outputs equal, finish semantics valid')
PY
