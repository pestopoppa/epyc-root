#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/lsa-native-capacity-9216-20261104/packet
R=/mnt/raid0/llm/tmp/lsa-native-capacity-9216-20261104
B=/mnt/raid0/llm/tmp/lsa-native-capacity-9216-20261104/pinned-build
S=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/ward-fix-088
MAP=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/native-map-validation-r2/pca.lsamap
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
printf '%s  %s\n' 2dcae5f36b153fd3af74497576795c1ad679812fddc963c83206eb77d4fb84a1 "$S/source-manifest.json" 7d381796426e282fa22ff8a3a79538698c91231d7506180402cb977f61c1519e "$B/out/bin/libllama.so.0.0.0" d26f2caecdbfdd12e492828465d6bbb61187f41854021d4fab92e4081fef1f0d "$B/out/bin/libggml-base.so.0.16.0" | sha256sum -c -
python3 - "$S" "$D/map-proof.json" <<'PY2'
import hashlib,json,pathlib,sys
s=pathlib.Path(sys.argv[1]); m=json.load(open(s/'source-manifest.json'))
for name in ('src/llama-lsa-map.h','src/llama-lsa-runtime.h','src/llama-lsa-native-hip.h','src/llama-lsa-native.h','ggml/include/ggml.h'):
 p=s/'source'/name; assert hashlib.sha256(p.read_bytes()).hexdigest()==m['files'][name]['sha256'],name
proof=json.load(open(sys.argv[2])); st=pathlib.Path(proof['path']).stat(); assert (st.st_size,st.st_ino,st.st_dev)==(proof['size'],proof['inode'],proof['device'])
PY2
unset LD_PRELOAD GGML_BACKEND_PATH
export LD_LIBRARY_PATH="$B/out/bin:/opt/rocm/lib"
mkdir -p "$R/output"
/usr/bin/g++ -std=c++17 -O2 -I "$S/source/src" -I "$S/source/ggml/include" "$D/capacity.cpp" -L "$B/out/bin" -Wl,-rpath,"$B/out/bin" -lllama -lggml-base -o "$R/output/capacity-check"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$R/output/capacity-check" "$B/out" > "$R/output/linkage.txt"
[[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
"$R/output/capacity-check" "$MAP" > "$R/output/native.txt"
python3 - "$R" <<'PY'
import hashlib,json,pathlib,re,sys
r=pathlib.Path(sys.argv[1]); text=(r/'output/native.txt').read_text().strip();pairs=dict(re.findall(r'(\w+)=(\d+)',text))
required=['host_valid','layers','per_layer_device_bytes','shared_scratch_bytes','aggregate_device_bytes','cap_bytes']
assert all(k in pairs for k in required) and int(pairs['host_valid'])==1 and int(pairs['layers'])==16
assert 0<int(pairs['aggregate_device_bytes'])<=int(pairs['cap_bytes'])==2147483648
result={'unit':'capacity-9216','status':'pass','source_commit':'088a77bd6ce5fac1ad3bf397912d884ae62b909e','max_keys':9216,'max_new_tokens':2048,'geometry':[24,4,256,64],'map_sha256_preverified':'8f280922d41ea2f8209cc6b800b827f1e2d82785d1989c9a55e0ce0c276856b7','metrics':{k:int(v) for k,v in pairs.items()},'scope':'host admission arithmetic only; no GPU allocation, model inference, quality, speed, or modification of any reviewed native manifest','binary_sha256':hashlib.sha256((r/'output/capacity-check').read_bytes()).hexdigest(),'linkage_sha256':hashlib.sha256((r/'output/linkage.txt').read_bytes()).hexdigest()}
with (r/'results.jsonl').open('a') as f:f.write(json.dumps(result,sort_keys=True)+'\n')
(r/'complete').touch()
PY
