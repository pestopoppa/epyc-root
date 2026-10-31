#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-g16a-build-prep-20261031/native
cd "$D"
# R7: GPU quiet only, host work pinned184-185; no CPU-quarter claim/folding.
# Acquisition is immediate-or-rc75. 295s plus a5s forced-drain bound is at most300s.
set +e
/usr/bin/timeout --signal=TERM --kill-after=5s 295s /bin/bash /workspace/repos/epyc-orchestrator/scripts/region-lock run --gpu-quiet exclusive --role bench-gpu --timeout-s 0 --tag codex-ni-g16a-native -- taskset -c 184-185 python3 -I -B "$D/native_job.py" > >(tee -a "$D/native-launcher.out") 2>&1
rc=$?
set -e
python3 -I -B - "$D" "$rc" <<'PY'
import json,pathlib,sys,datetime,os
D=pathlib.Path(sys.argv[1]);rc=int(sys.argv[2]);r={'launcher_rc':rc,'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native_result':str(D/'LATEST-RESULT.json'),'scope':'G16a eight shapes only; no greedy/keep/promotion','note':'rc75 can be admission unavailable or partial; consult native result timestamp and native-launcher.out'}
(D/'LAUNCH-TERMINAL.json').write_text(json.dumps(r,indent=2)+'\n');(D/'LAUNCH-TERMINAL.flag').touch()
if not (rc==75 and os.environ.get('G16A_ADMISSION_WATCH')=='1'):
 with open('/mnt/raid0/llm/tmp/compute-flags/codex-channels/codex3.md','a') as f:f.write('\n## NI G16a native public entry returned\n'+json.dumps(r)+'\n')
pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/codex-channels/NI-G16A-NATIVE-ENTRY-TERMINAL-20261031.flag').touch()
PY
exit "$rc"
