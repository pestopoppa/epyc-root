#!/bin/bash
# Arms the grant-polling fillers for V11-052/050/051 (GPU, exclusive), V11-086 (CPU, bench claim 0-95, gpu-quiet shared) and AKX-ALL-27b run.
# Each poller is filler_run2.sh (new copy; the running filler_run.sh is untouched). A poller whose arm build is absent refuses with .ended rc=5
# 'build-missing' (precond-cmd) and keeps polling. Idempotent: a second launcher for the same id exits (launcher flock).
D=/mnt/raid0/llm/tmp/fillers-3c4ca599
V=$D/v11drv
RUNS=/mnt/raid0/llm/tmp/v11-runs
PY=/usr/bin/python3
arm() {
  local id=$1; shift
  setsid nohup "$D/filler_run2.sh" --id "$id" --stop "$D/STOP_$id" "$@" > "$D/logs/$id.out" 2>&1 < /dev/null &
  echo "$id launcher pid $!"
}
for it in 052 050 051; do
  case $it in 052) w=7200; pt=18183,8197;; 050) w=5400; pt=18183,8197;; 051) w=5400; pt=18183;; esac
  arm v11-$it-gpu --class gpu --gpu-quiet exclusive --min-window $w --port $pt \
    --precond-cmd "$PY -I $V/v11_driver.py $it --check-builds" \
    --complete-cmd "ls $RUNS/$it/20*/COMPLETE" \
    --cmd "$PY -I $V/v11_driver.py $it --execute"
done
arm v11-086-cpu --class cpu --role bench --claim-cpus 0-95 --gpu-quiet shared --min-window 7200 --port 18641,18651,18761 \
  --precond-cmd "$PY -I $V/v11_driver.py 086 --check-builds" \
  --complete-cmd "ls $RUNS/086/20*/COMPLETE" \
  --cmd "$PY -I $V/v11_driver.py 086 --execute"
arm akx-all-27b-run --class gpu --gpu-quiet exclusive --min-window 1500 \
  --precond-cmd "test -e /mnt/raid0/llm/kernels/builds/gpu-20261021-732389d6d/SHA256SUMS && test -e /mnt/raid0/llm/kernels/builds/gpu-20261021-b0eb4fab4/SHA256SUMS || { echo 'akx-all-27b-builds output absent'; exit 5; }" \
  --complete-cmd "$PY -I $V/akx27_driver.py --is-done" \
  --cmd "bash $D/akx27_run.sh --execute"
