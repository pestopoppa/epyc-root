#!/bin/bash
set -euo pipefail
bash -n private/scripts/inf70/harness1/arm_cold.sh
bash -n private/scripts/inf70/harness1/arm_hot.sh
python3 - <<'PY'
from pathlib import Path
for kind in ('cold','hot'):
 old=Path(kind+'.base').read_text().splitlines()
 new=Path(f'private/scripts/inf70/harness1/arm_{kind}.sh').read_text().splitlines()
 removed=[x for x in old if x not in new]
 assert len(removed)==2 and all('/proc/loadavg' in x for x in removed)
 assert sum('cores_sampler' in x for x in old)==sum('cores_sampler' in x for x in new)>0
 assert not any('/proc/loadavg' in x for x in new)
 print(f'{kind}: syntax OK, in-window sampler retained; only pre-arm wait and log removed')
PY
