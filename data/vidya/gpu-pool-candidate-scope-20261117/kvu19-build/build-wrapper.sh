#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor
printf '%s\n' "$$" > "$D/wrapper.pid"
printf "\n[build attempt %s]\n" "$(date -u +%FT%TZ)" >> "$D/region-build.log"
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 48-51 --role build --timeout-s 1 --tag vidya-kvu19-successor -- /usr/bin/taskset -c 48-51 /bin/bash "$D/build.sh" >> "$D/region-build.log" 2>&1 &
lock_pid=$!
printf '%s\n' "$lock_pid" > "$D/region-lock.pid"
rc=0
wait "$lock_pid" || rc=$?
/usr/bin/python3 - "$rc" "$$" "$lock_pid" /mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor/build-terminal.json <<'PY'
import json,os,sys,tempfile,datetime
rc=int(sys.argv[1]); wrapper_pid=int(sys.argv[2]); lock_pid=int(sys.argv[3]); path=sys.argv[4]
r={'task':'kvu19-successor-build','state':'success' if rc==0 else 'failure','exit_code':rc,'wrapper_pid':wrapper_pid,'region_lock_pid':lock_pid,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'build_receipt':'/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor/build-receipt.json','log':'/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor/region-build.log','cpu_claim':'48-51','role':'build','root_code':'/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-root-code'}
fd,tmp=tempfile.mkstemp(dir=os.path.dirname(path),prefix='.kvu19-')
with os.fdopen(fd,'w') as f: json.dump(r,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
os.replace(tmp,path)
PY
exit "$rc"
