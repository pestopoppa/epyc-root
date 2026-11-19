#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-spec-guard-20261104-packet/probe-compile
P=${D%/probe-compile}
S=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-spec-guard-20261104
OUT=$P/out
export ROWFLOW_REPO=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root
if [[ "${FILLER_SMOKE:-0}" == 1 ]]; then
    python3 "$D/preflight.py" "$D/smoke-preflight.json" --smoke
    exit 0
fi
python3 "$D/preflight.py" "$D/input-preflight.json"
export LD_LIBRARY_PATH="$OUT/bin:/opt/rocm/lib"
python3 "$P/guarded_exec.py" "$D/compile.log" /usr/bin/g++ -O2 -std=c++17 \
    -I"$S/include" -I"$S/src" -I"$S/ggml/include" "$P/guard-probe.cpp" \
    -L"$OUT/bin" -Wl,-rpath,"$OUT/bin" -lllama -o "$P/guard-probe"
python3 "$P/guarded_exec.py" "$D/linkage.log" \
    /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$P/guard-probe" "$OUT"
python3 - "$D" "$P" <<'PY'
import hashlib, json, pathlib, re, subprocess, sys
d, p = map(pathlib.Path, sys.argv[1:]); h = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
build = json.loads((p / 'build-receipt.json').read_text())
probe = p / 'guard-probe'
out = subprocess.check_output(['ldd', str(probe)], text=True)
(d / 'ldd.log').write_text(out)
linked = {}
for line in out.splitlines():
    match = re.match(r'\s*(lib(?:llama|ggml)[^\s]*)\s+=>\s+(/\S+)', line)
    if not match: continue
    path = pathlib.Path(match.group(2)).resolve(strict=True)
    assert str(path) in build['dsos'] and h(path) == build['dsos'][str(path)], line
    linked[str(path)] = h(path)
assert any('libllama.so' in path for path in linked)
assert any('libggml-base.so' in path for path in linked)
receipt = {'source_commit': build['source_commit'], 'build_receipt_sha256': h(p / 'build-receipt.json'),
           'probe_source_sha256': h(p / 'guard-probe.cpp'), 'probe_sha256': h(probe),
           'linked_candidate_dsos': linked, 'compiler_sha256': h(pathlib.Path('/usr/bin/g++').resolve()),
           'compile_log_sha256': h(d / 'compile.log'), 'linkage_log_sha256': h(d / 'linkage.log'),
           'ldd_log_sha256': h(d / 'ldd.log'), 'model_loaded': False, 'gpu_used': False}
(p / 'probe-build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
with (d / 'results.jsonl').open('a') as f:
    f.write(json.dumps({'unit': 'guard-probe-compiled-and-linked', 'probe_sha256': receipt['probe_sha256'],
                        'linked_candidate_dsos': len(linked), 'model_loaded': False, 'gpu_used': False}) + '\n')
(d / 'complete').touch()
PY
