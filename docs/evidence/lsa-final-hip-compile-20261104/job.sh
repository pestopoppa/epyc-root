#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/final-hip
approval="$D/approved.json"
sha256sum -c "/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/openssl-dev/dependency.sha256"
snapshot=$(python3 - "$approval" <<'PY'
import hashlib,json,pathlib,sys
a=json.load(open(sys.argv[1])); assert a['reviewed'] is True
for name,digest in a['helper_sha256'].items(): assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==digest,name
p=pathlib.Path(a['snapshot']).resolve(); m=p/'source-manifest.json'
assert hashlib.sha256(m.read_bytes()).hexdigest()==a['manifest_sha256']
x=json.loads(m.read_text()); assert x['head']==a['source_commit'] and x['tracked_clean'] is True; s=p/'source'
for rel,v in x['files'].items():
 q=s/rel
 if 'sha256' in v: assert q.is_file() and not q.is_symlink() and hashlib.sha256(q.read_bytes()).hexdigest()==v['sha256'] and q.stat().st_mode & 0o777==v['mode'],rel
 else: assert q.is_symlink() and q.readlink().as_posix()==v['symlink'],rel
assert {str(q.relative_to(s)) for q in s.rglob('*') if q.is_file() or q.is_symlink()}==set(x['files'])
print(p)
PY
)
run="$D/out"
unset LD_PRELOAD LD_LIBRARY_PATH GGML_BACKEND_PATH
args=(-DOPENSSL_INCLUDE_DIR=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/openssl-dev/root/usr/include -DOPENSSL_CRYPTO_LIBRARY=/usr/lib/x86_64-linux-gnu/libcrypto.so.3 -DOPENSSL_SSL_LIBRARY=/usr/lib/x86_64-linux-gnu/libssl.so.3 -DCMAKE_C_FLAGS=-I/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/openssl-dev/root/usr/include/x86_64-linux-gnu -DCMAKE_CXX_FLAGS=-I/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/openssl-dev/root/usr/include/x86_64-linux-gnu -DCMAKE_BUILD_TYPE=Release -DLLAMA_LSA_NATIVE=ON -DGGML_NATIVE=ON -DGGML_OPENMP=ON -DGGML_BLAS=OFF -DBUILD_SHARED_LIBS=ON -DLLAMA_BUILD_TESTS=ON -DLLAMA_USE_PREBUILT_UI=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=/usr/bin/cc -DCMAKE_CXX_COMPILER=/usr/bin/c++ -DGGML_HIP=ON -DGGML_HIP_MMQ_MFMA=ON -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_HIP_NO_VMM=ON -DAMDGPU_TARGETS=gfx90a -DCMAKE_HIP_COMPILER=/opt/rocm/lib/llvm/bin/clang++ -DCMAKE_PREFIX_PATH=/opt/rocm)
printf '%q ' cmake -S "$snapshot/source" -B "$run" "${args[@]}" > "$D/configure-command.txt"
printf '\n' >> "$D/configure-command.txt"
cmake --version > "$D/compiler-versions.txt"
/usr/bin/gcc-15 --version >> "$D/compiler-versions.txt"
/usr/bin/g++-15 --version >> "$D/compiler-versions.txt"
/opt/rocm/lib/llvm/bin/clang++ --version >> "$D/compiler-versions.txt"
if [[ ! -f "$D/base-unit.json" ]]; then
 cmake -S "$snapshot/source" -B "$run" "${args[@]}"
fi
python3 - "$run/CMakeCache.txt" <<'PY'
import hashlib,json,pathlib,re,sys
p=pathlib.Path('/workspace/artifacts/compute/vidya-c6-order-repair-20261101/C5-RECIPES.json')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='854fcfdc1142f568dd4ba84dfff75a62709aff803f8a41690221d1f4f81aa4a9'
ref=json.loads(p.read_text())['gpu']['definitions']; cache={}
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
 m=re.match(r'([^#/:][^:=]*):[^=]*=(.*)',line)
 if m: cache[m[1]]=m[2]
ignore={'LLAMA_SERVER_DEBUG_TIMINGS','GGML_IQK_FLASH_ATTENTION','LLAMA_LB7_PROBES'}
diff=[(k,v['value'],cache.get(k)) for k,v in ref.items() if k.startswith(('GGML_','LLAMA_','AMDGPU_')) and not (k in ignore and v['value']=='OFF' and k not in cache) and cache.get(k)!=v['value']]
assert not diff,diff
assert cache.get('LLAMA_LSA_NATIVE')=='ON'
import subprocess
compilers={}
for k in ('CMAKE_C_COMPILER','CMAKE_CXX_COMPILER','CMAKE_HIP_COMPILER'):
 if k in cache and cache[k]:
  p=pathlib.Path(cache[k]).resolve(strict=True)
  compilers[k]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'version':subprocess.check_output([str(p),'--version'],text=True).splitlines()[0]}
assert 'CMAKE_C_COMPILER' in compilers and 'CMAKE_CXX_COMPILER' in compilers
pathlib.Path(sys.argv[1]).parent.parent.joinpath('actual-compilers.json').write_text(json.dumps(compilers,indent=2)+'\n')
PY
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
if [[ ! -f "$D/base-unit.json" ]]; then
 cmake --build "$run" --target ggml-base --parallel "${FILLER_THREADS:-4}"
 python3 - "$D" "$snapshot" <<'PY'
import hashlib,json,pathlib,sys
d=pathlib.Path(sys.argv[1]); s=pathlib.Path(sys.argv[2]); libs=[p for p in (d/'out').rglob('libggml-base.so.*') if p.is_file() and not p.is_symlink()]; assert len(libs)==1
paths=[s/'source-manifest.json',d/'out/CMakeCache.txt',d/'out/compile_commands.json',libs[0]]
t=d/'base-unit.tmp'; t.write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n'); t.replace(d/'base-unit.json')
PY
 printf '{"unit":"ggml-base"}\n' >> "$D/results.jsonl"
 exit 75
fi
python3 - "$D/base-unit.json" <<'PY'
import hashlib,json,pathlib,sys
for p,h in json.load(open(sys.argv[1])).items(): assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
PY
[[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
cmake --build "$run" --target ggml-cpu ggml-hip llama llama-server test-lsa-graph-integration test-lsa-native-hip-live test-lsa-runtime-hip-live --parallel "${FILLER_THREADS:-4}"
find "$run" -type f \( -name 'libggml*.so*' -o -name 'libllama*.so*' -o -name 'test-lsa-graph-integration' -o -name 'test-lsa-*-live' -o -name 'llama-server' \) -exec sha256sum {} + > "$D/artifact-sha256.txt"
printf '{"unit":"graph-cpu-wip-compile-complete"}\n' >> "$D/results.jsonl"
touch "$D/complete"
