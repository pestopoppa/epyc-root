#!/usr/bin/env bash
set -euo pipefail
ROOT=/mnt/raid0/llm/tmp/codex-ni-ap-legacy-status-wrap-20261030
RESEARCH=/mnt/raid0/llm/worktrees/mains/codex-ni-research-code
OUT="$ROOT/artifacts/compute/r24-8-alarms-20261031"
LOCKDIR=/mnt/raid0/llm/tmp/compute-flags/prep-locks
PAIR=
for candidate in 32-33 34-35 36-37; do
  if exec 9>"$LOCKDIR/$candidate.lock" && flock -n 9; then PAIR=$candidate; break; fi
  exec 9>&-
done
if [[ -z "$PAIR" ]]; then echo 'no R6 pair lock available' >&2; exit 75; fi
case "$PAIR" in
  32-33) CPUS=32,33,128,129 ;;
  34-35) CPUS=34,35,130,131 ;;
  36-37) CPUS=36,37,132,133 ;;
esac
ulimit -v 8388608
export OMP_NUM_THREADS=1
printf 'R6_PAIR=%s LOCK=%s/%s.lock AFFINITY=%s SMT_PAIRS=%s↔%s,%s↔%s VMEM_KIB=%s OMP_NUM_THREADS=%s\n' \
  "$PAIR" "$LOCKDIR" "$PAIR" "$CPUS" "${PAIR%-*}" "$(( ${PAIR%-*} + 96 ))" \
  "${PAIR#*-}" "$(( ${PAIR#*-} + 96 ))" "$(ulimit -v)" "$OMP_NUM_THREADS" | tee "$OUT/r6-controls.log"
run_case() {
  local name=$1 limit=$2 workdir=$3 py_path=$4; shift 4
  local log="$OUT/$name.log"
  (cd "$workdir" && timeout --foreground --kill-after=5s "${limit}s" taskset -c "$CPUS" \
    env OMP_NUM_THREADS=1 PYTHONPATH="$py_path" python3 "$@") >"$log" 2>&1 &
  local wrapper=$! child= birth= rss= comm= tries=0 rc=0
  while (( tries < 100 )); do
    child=$(ps -o pid= --ppid "$wrapper" | awk 'NR==1 {print $1}')
    if [[ -n "$child" ]]; then
      comm=$(ps -o comm= -p "$child" 2>/dev/null | tr -d ' ' || true)
      if [[ "$comm" == python3 ]]; then break; fi
    fi
    sleep 0.05; tries=$((tries+1))
  done
  if [[ -z "$child" ]]; then echo "could not capture child PID for $name" >&2; wait "$wrapper" || true; exit 1; fi
  birth=$(ps -o lstart= -p "$child" | sed 's/^ *//')
  rss=$(ps -o rss=,vsz= -p "$child" | awk '{$1=$1; print}')
  printf 'START name=%s wrapper_pid=%s test_pid=%s birth=%s rss_vsz_kib=%s comm=%s\n' \
    "$name" "$wrapper" "$child" "$birth" "$rss" "$comm" | tee -a "$OUT/r6-controls.log"
  set +e; wait "$wrapper"; rc=$?; set -e
  if [[ -e "/proc/$child" ]]; then printf 'ABSENCE name=%s pid=%s still-present\n' "$name" "$child" | tee -a "$OUT/r6-controls.log"; ps -o pid,ppid,stat,lstart,rss,vsz,comm -p "$child"; exit 1; fi
  printf 'ABSENCE name=%s pid=%s confirmed\nEXIT name=%s rc=%s\n' "$name" "$child" "$name" "$rc" | tee -a "$OUT/r6-controls.log"
  cat "$log" >> "$OUT/r6-controls.log"
  if (( rc != 0 )); then exit "$rc"; fi
}
run_case research-controls 400 "$RESEARCH" "$RESEARCH/scripts/kernel_rnd" \
  -m unittest autokernel.loop.test_status autokernel.loop.test_loop.OutcomeAttempt \
    autokernel.loop.test_actors.ContextBundle
run_case root-render-controls 400 "$ROOT" "$ROOT" tests/test_dashboard_loop_surface.py
