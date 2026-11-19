#!/bin/bash
set -euo pipefail
job=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-phase-smoke-20261102
build_job=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-phase-build-20261102
build=/mnt/micron/rtg58-p3-phase-cpu-20261102
packet=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-phase-trial-20261102
belief=/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-p3-belief-20261102
server_pid=
cleanup() {
  local rc=$?
  trap - EXIT
  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill -TERM "$server_pid" || true
    for _ in {1..50}; do kill -0 "$server_pid" 2>/dev/null || break; sleep .1; done
    if kill -0 "$server_pid" 2>/dev/null; then kill -KILL "$server_pid" || true; fi
    wait "$server_pid" 2>/dev/null || true
    if kill -0 "$server_pid" 2>/dev/null; then rc=73; fi
  fi
  printf '%s\n' "$rc" > "$job/EXIT_CODE"; touch "$job/FINISHED"; exit "$rc"
}
trap cleanup EXIT
[[ -f "$build_job/FINISHED" && $(cat "$build_job/EXIT_CODE") = 0 ]]
sha256sum -c "$build_job/BINARIES.sha256"
LD_LIBRARY_PATH="$build/bin" bash /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$build/bin/llama-server" "$build/bin" > "$job/linkage.txt"
printf '%s\n' '{"prompt":"The scientific method begins with","n_predict":16,"temperature":0,"cache_prompt":false}' > "$job/request.json"
date -u +%FT%TZ > "$job/start.txt"
LLAMA_KPF30_MIXED_BLOCKS=1 LD_LIBRARY_PATH="$build/bin" taskset -c 80-81 "$build/bin/llama-server" -m /mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf --host 127.0.0.1 --port 19878 -c 512 -np 1 -b 128 -ub 128 -t 2 -tb 2 --no-mmap --device none --kv-unified -lv 4 --no-warmup > "$job/server.log" 2>&1 &
server_pid=$!
printf '%s\n' "$server_pid" > "$job/server.pid"
python3 - "$job" "$server_pid" <<'PY'
import json,pathlib,sys,time,urllib.error,urllib.request
job=pathlib.Path(sys.argv[1]); pid=sys.argv[2]; base='http://127.0.0.1:19878'
for _ in range(120):
    try:
        with urllib.request.urlopen(base+'/health',timeout=2) as r:
            if r.status==200: break
    except (OSError,urllib.error.URLError): pass
    time.sleep(.5)
else: raise RuntimeError('server never became ready')
(job/'argv.json').write_text(json.dumps([x for x in pathlib.Path('/proc',pid,'cmdline').read_bytes().decode().split('\0') if x]))
req=urllib.request.Request(base+'/completion',(job/'request.json').read_bytes(),{'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=120) as r:
    response=r.read(); assert r.status==200
(job/'response.json').write_bytes(response)
PY
kill -TERM "$server_pid"
set +e
wait "$server_pid"
server_rc=$?
set -e
if kill -0 "$server_pid" 2>/dev/null; then exit 73; fi
server_pid=
PYTHONPATH="$packet/runner" python3 - "$job" "$server_rc" <<'PY'
import hashlib,json,pathlib,socket,sys
from kpf30_phase_capture import write_phase_capture
p=pathlib.Path(sys.argv[1]); sha=lambda f:hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
m=dict(run_id='rtg58-p3-smoke',window_id='rtg58-p3-smoke',host=socket.gethostname(),binary_sha256=sha('/mnt/micron/rtg58-p3-phase-cpu-20261102/bin/llama-server'),prompt_set_sha256=sha(p/'request.json'),start_utc=(p/'start.txt').read_text().strip(),category='CANDIDATE',argv=json.loads((p/'argv.json').read_text()),fan_completed=True,process_reaped=True,server_returncode=int(sys.argv[2]))
r=write_phase_capture(p/'server.log',p/'phase-capture',m)
assert len(r)==1 and r[0]['phase']=='decode' and r[0]['n_rows']>0, r
print('PASS: live server phase writer; prestart excluded:',r[0]['excluded_prestart_rows'],'decode rows:',r[0]['n_rows'])
PY
PYTHONPATH="$belief/scripts/vidya" python3 - "$job/phase-capture/belief_measurements.jsonl" <<'PY'
import json,sys
from adapters.kv_prefix_fork import project
from claim_tuple import grade
p=sys.argv[1]; x=json.loads(open(p).readline()); claim=project({'row':x,'sidecar_path':p})
assert claim.attestation_verified and claim.extra['phase']=='decode'
print('PASS: shared adapter re-derived native phase and source log; grade:',grade(claim)[0])
PY
