#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/ward-fix-088/build
ROOT=${D%/ward-fix-088/build}
OLD=$ROOT/reason-build-d2c5/out
SRC=$ROOT/ward-fix-088/source
NEW=$D/out
python3 - "$D/approved.json" <<'PY'
import json,hashlib,pathlib,sys
x=json.load(open(sys.argv[1]));assert x['reviewed'] and x['source_commit']=='088a77bd6ce5fac1ad3bf397912d884ae62b909e'
for p,h in x['pins'].items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
m=json.load(open(x['source_manifest'])); root=pathlib.Path(x['source_manifest']).parent/'source'
for n,v in m['files'].items():
 p=root/n
 if 'sha256' in v: assert hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'],n
 else: assert p.is_symlink() and str(p.readlink())==v['symlink'],n
for v in json.load(open(x['compiler_receipt'])).values(): assert hashlib.sha256(pathlib.Path(v['path']).read_bytes()).hexdigest()==v['sha256']
PY
sha256sum -c "$D/prior-objects.sha256" >/dev/null
sha256sum -c "$ROOT/openssl-dev/dependency.sha256" >/dev/null
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
source "$D/cmake-args.sh"
if [[ ! -f $D/base-unit.json ]]; then
 cmake -S "$SRC" -B "$NEW" "${args[@]}"
 python3 - "$OLD" "$NEW" "$D" <<'PY'
import hashlib,json,pathlib,shutil,sys,os,time
old,new,d=map(pathlib.Path,sys.argv[1:]); excluded={'llama-lsa-native.cpp.o','llama-lsa-native-hip.hip.o','test-lsa-native.cpp.o','test-lsa-native-hip.cpp.o'}; entries=[]
for p in old.rglob('*.o'):
 rel=p.relative_to(old); dest=new/rel
 if p.name in excluded:continue
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);os.utime(dest,None)
 h=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==h
 entries.append({'relative':str(rel),'sha256':h})
assert len(entries)>300
(d/'seeded-objects.json').write_text(json.dumps(entries,indent=2)+'\n')
PY
 make -C "$NEW/src" llama-lsa-native-hip.hip.o -j "${FILLER_THREADS:-4}"
 sha256sum "$NEW/src/CMakeFiles/llama.dir/llama-lsa-native-hip.hip.o" > "$D/hip-object.sha256"
 python3 - "$D" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); files=[p/'hip-object.sha256',p/'seeded-objects.json',p/'out/CMakeCache.txt',p/'out/compile_commands.json'];(p/'base-unit.json').write_text(json.dumps({str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in files},indent=2)+'\n')
PY
 printf '{"unit":"ward-hip-object"}\n' >> "$D/results.jsonl"
 exit 75
fi
python3 - "$D/base-unit.json" <<'PY'
import json,hashlib,pathlib,sys
for p,h in json.load(open(sys.argv[1])).items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
PY
[[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
cmake --build "$NEW" --target llama llama-server test-lsa-native-live test-lsa-native-hip-live --parallel "${FILLER_THREADS:-4}"
sha256sum -c "$D/hip-object.sha256"
find "$NEW" -type f \( -name 'libggml*.so*' -o -name 'libllama*.so*' -o -name 'llama-server' -o -name 'test-lsa-graph-integration' \) -exec sha256sum {} + > "$D/artifact-sha256.txt"
printf '{"unit":"ward-build-complete"}\n' >> "$D/results.jsonl"
touch "$D/complete"
