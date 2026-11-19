#!/bin/bash
# DF2-EXL3 codec gate on real target blocks (CPU lane; HIP harness compiled only). filler_run15 engine.
set -euo pipefail
S=/mnt/raid0/llm/tmp/df2-exl3-gate-20261107
cd "$S"
ulimit -c 0
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id df2-exl3-codec-gate-real-blocks-r1-20261107 \
  --class cpu --role build --claim-cpus 24-47 --min-window 1800 \
  --cmd "/usr/bin/python3 -B $S/job.py" \
  --complete-cmd "/usr/bin/python3 -I -B $S/check_complete.py" \
  --stop "$S/STOP" --workdir "$S"
