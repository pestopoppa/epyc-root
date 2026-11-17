#!/bin/bash
set -uo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor
R=/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate/handoff-sessions/vidya-belief-substrate/awaiting/kvu19-build-20261117.json
printf '%s\n' "$$" > "$D/wrapper.pid"
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 48-51 --role build --timeout-s 1 --tag vidya-kvu19-successor -- /usr/bin/taskset -c 48-51 /bin/bash "$D/build.sh" > "$D/region-build.log" 2>&1
rc=$?
/usr/bin/python3 - "$rc" /mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor/build-terminal.json <<'PY'
import json,os,sys,tempfile,datetime
rc=int(sys.argv[1]); path=sys.argv[2]
r={'task':'kvu19-successor-build','state':'success' if rc==0 else 'failure','exit_code':rc,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'build_receipt':'/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor/build-receipt.json','log':'/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor/region-build.log','cpu_claim':'48-51','role':'build','root_code':'/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-root-code'}
fd,tmp=tempfile.mkstemp(dir=os.path.dirname(path),prefix='.kvu19-')
with os.fdopen(fd,'w') as f: json.dump(r,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
os.replace(tmp,path)
PY
exit "$rc"
