#!/bin/bash
set -uo pipefail
S=/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030
P=/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/prep
arm=$1; n=$2; epoch=$3; pair=$4
/usr/bin/python3 -c 'import sys;sys.path.insert(0,sys.argv[1]);import prep_admission;prep_admission.live(tuple(map(int,sys.argv[2].split(","))))' "$P" "$pair" || exit 98
d=$(/usr/bin/python3 "$S/epoch_watch.py" prepare "$arm" "$n" "$epoch") || exit 97
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=/mnt/raid0/llm/omnidocbench/.venv/lib/python3.11/site-packages taskset -c "$pair" /usr/bin/python3 "$P/prep_supervisor.py" 900 -- /home/daniele/.local/share/uv/python/cpython-3.11.17-linux-x86_64-gnu/bin/python3.11 -S "$d/run_one.py" "$n" >"$d/run.log" 2>&1
rc=$?
/usr/bin/python3 - "$d" "$rc" <<'PY'
import json,sys,datetime
from pathlib import Path
p=Path(sys.argv[1]);rc=int(sys.argv[2]);rec={'returncode':rc,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'receipt_present':bool(list(p.glob('*.score-receipt.json')))}
with (p/'execution-status.json').open('x') as f:json.dump(rec,f,sort_keys=True);f.write('\n')
PY
if [[ "$arm" == paddle && "$rc" -eq 0 ]]; then /usr/bin/python3 "$S/render_running.py" >>"$d/run.log" 2>&1 || echo "renderer failed for $d"; fi
exit "$rc"
