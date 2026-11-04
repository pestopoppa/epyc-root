#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/ch26-observer-overhead-20261104
cd "$D"
sha256sum --strict --quiet -c SOURCE.sha256
exec sudo -n --preserve-env=FILLER_ID,FILLER_CPUS,FILLER_DEADLINE,FILLER_STOPFILE,FILLER_DRYRUN,FILLER_DRYRUN_RESULT_PATH,FILLER_SMOKE,FILLER_SMOKE_UNITS /usr/bin/chroot /proc/1/root /usr/bin/python3 -B "$D/job.py"
