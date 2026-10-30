#!/bin/bash
set -euo pipefail
P=/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/prep
S=/mnt/raid0/llm/tmp/codex3-hil15b-r9-failure-audit-20261030
exec 9>/mnt/raid0/llm/tmp/compute-flags/prep-locks/26-27.lock
flock -n 9
pair=$(/usr/bin/python3 - "$P" <<'PY'
import sys
sys.path.insert(0,sys.argv[1]);import prep_admission
for p in [(26,27),(50,51),(74,75),(2,3),(122,123)]:
 try:prep_admission.live(p)
 except Exception:continue
 print(','.join(map(str,p)));break
else:raise SystemExit('no admitted R6 pair')
PY
)
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/mnt/raid0/llm/epyc-orchestrator/.venv/lib/python3.11/site-packages
exec taskset -c "$pair" /usr/bin/python3 "$P/prep_supervisor.py" 900 -- /home/daniele/.local/share/uv/python/cpython-3.11.17-linux-x86_64-gnu/bin/python3.11 -S "$S/audit_native.py"
