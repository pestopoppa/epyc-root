#!/bin/bash
set -u
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-nemotron-tc-r2-20261030
P=/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/prep
for attempt in $(seq 1 120); do
 for cpus in 30,31 54,55 78,79 6,7 126,127; do
  if taskset -c "$cpus" python3 -c 'import sys,os;sys.path.insert(0,sys.argv[1]);import prep_admission;prep_admission.live(os.sched_getaffinity(0))' "$P" >/dev/null 2>&1; then
   sudo -n --preserve-env=HOME /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/30-31.lock /usr/bin/taskset -c "$cpus" /usr/bin/env OMP_NUM_THREADS=1 /usr/bin/python3 "$P/prep_supervisor.py" 300 -- /usr/bin/python3 "$D/build_source_catalog.py"
   rc=$?
   if [ "$rc" -eq 0 ]; then exit 0; fi
   break
  fi
 done
 sleep 15
done
exit 1
