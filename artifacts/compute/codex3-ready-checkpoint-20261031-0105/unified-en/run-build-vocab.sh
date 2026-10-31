#!/bin/bash
set -u
P=/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/prep
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-unified-en-20261031
for attempt in $(seq 1 120); do
 for cpus in 30,31 54,55 78,79 6,7 126,127; do
  if taskset -c "$cpus" python3 -c 'import sys,os;sys.path.insert(0,sys.argv[1]);import prep_admission;prep_admission.live(os.sched_getaffinity(0))' "$P" >/dev/null 2>&1; then
   if flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/30-31.lock taskset -c "$cpus" env OMP_NUM_THREADS=1 python3 "$P/prep_supervisor.py" 180 -- python3 "$D/build_vocab.py"; then exit 0; fi
   break
  fi
 done
 sleep 15
done
exit 1
