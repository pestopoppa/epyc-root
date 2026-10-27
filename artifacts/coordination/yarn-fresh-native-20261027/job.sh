#!/bin/bash
set -uo pipefail
S=/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch
( cd "$S" && sha256sum -c fresh/SOURCES.sha256 ) || exit 6
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
  exec /usr/bin/python3 -B "$S/deps/dryrun_check.py" boundary --job "$S/fresh/job.sh" --effect first-output-directory-write
fi
YG_ID=ni-yarn-fresh-native-cohort
YG_PLAN=native-gate-power
YG_OUT=$S/fresh/out
YG_PORT=18096
. "$S/owned-id.sh"
. "$S/yarn_gate_lib-owned.sh"
export HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0
# The legacy sampler and recycle loop also used kill -0; monitor only the
# captured server PID and stop on an absent or zombie process.
yg_alive() {
  [[ $1 == "${YG_OWN_PID:-}" ]] || return 1
  owned_match "$1" "$YG_OWN_BIRTH" "$YG_OWN_PGID"
}
yg_vram_bytes() {
  local pid=$1 v=0 k
  yg_alive "$pid" || return 1
  for k in "$YG_KFD/$pid"/vram_*; do
    yg_alive "$pid" || return 1
    [ -r "$k" ] && v=$((v + $(cat "$k" 2>/dev/null || echo 0)))
  done
  printf '%s\n' "$v"
}
yg_sampler() {
  local pid=$1 f=$2 v k
  while yg_alive "$pid"; do
    yg_alive "$pid" || return 1
    v=0
    for k in "$YG_KFD/$pid"/vram_*; do yg_alive "$pid" || return 1; [ -r "$k" ] && v=$((v + $(cat "$k" 2>/dev/null || echo 0))); done
    echo "$(date -u +%s) vram=$v $(grep -E '^(VmRSS|RssAnon|RssFile|VmHWM):' /proc/$pid/status 2>/dev/null | awk '{printf "%s%s ", $1, $2}')" >> "$f"
    sleep 5
  done
}
yg_recycle_watch() {
  local pid=$1 flag=$2 v base=""
  while yg_alive "$pid"; do
    if [ -n "${FILLER_STOPFILE:-}" ] && [ -e "$FILLER_STOPFILE" ]; then echo stop > "$flag"; return 0; fi
    yg_alive "$pid" || return 1
    v=$(yg_vram_bytes "$pid") || return 1
    [ -z "$base" ] && [ "$v" -gt 0 ] && base=$v
    if [ -n "$base" ] && [ "$v" -ge "$YG_RECYCLE_BYTES" ] && [ $((v-base)) -ge "$YG_RECYCLE_MIN_GROWTH" ]; then
      echo recycle > "$flag"
      echo "$(yg_ts) [$YG_ID] recycle requested: pid $pid own VRAM $((v / 1048576)) MiB" >> "$flag.log"
      return 0
    fi
    sleep "$YG_WATCH_S"
  done
}
# Override the legacy kill -0 probe, which is unreliable in this environment.
# The server PID is captured from our own setsid launch by yg_arm_once.
yg_stop() {
  local pid=$1 i state
  [[ $pid == "${YG_OWN_PID:-}" ]] || return 1
  if owned_read "$pid"; then
    [[ $OWN_BIRTH == "$YG_OWN_BIRTH" && $OWN_PGID == "$YG_OWN_PGID" ]] || { yg_log "identity mismatch; refusing signal"; return 1; }
    state=$OWN_STATE
  else
    state=''
  fi
  if [[ -z $state || $state == Z* ]]; then
    if ps -eo pgid=,stat= | awk -v g="$YG_OWN_PGID" '$1==g && $2 !~ /^Z/ {found=1} END {exit !found}'; then
      yg_log "dead server has undrained group"; return 1
    fi
    wait "$pid" 2>/dev/null || :
    ps -p "$pid" -o pid= >/dev/null && { yg_log "server remains unreaped"; return 1; }
    yg_log "captured server already dead and group drained"; return 0
  fi
  owned_match "$pid" "$YG_OWN_BIRTH" "$YG_OWN_PGID" || { yg_log "identity mismatch; refusing signal"; return 1; }
  kill -TERM -- "-$YG_OWN_PGID" 2>/dev/null || return 1
  for i in $(seq 1 60); do
    state=$(ps -p "$pid" -o stat= 2>/dev/null) || break
    [[ $state == Z* ]] && break
    sleep 1
  done
  state=$(ps -p "$pid" -o stat= 2>/dev/null) || state=''
  if [[ -n $state && $state != Z* ]]; then
    owned_match "$pid" "$YG_OWN_BIRTH" "$YG_OWN_PGID" || return 1
    kill -KILL -- "-$YG_OWN_PGID" 2>/dev/null || return 1
    for i in $(seq 1 10); do
      state=$(ps -p "$pid" -o stat= 2>/dev/null) || { state=''; break; }
      [[ $state == Z* ]] && break
      sleep 1
    done
    if [[ -n $state && $state != Z* ]]; then yg_log "server $pid remains alive"; return 1; fi
  fi
  wait "$pid" 2>/dev/null || :
  if ps -p "$pid" -o pid= >/dev/null; then yg_log "server $pid remains alive"; return 1; fi
  if ps -eo pgid=,stat= | awk -v g="$YG_OWN_PGID" '$1==g && $2 !~ /^Z/ {found=1} END {exit !found}'; then yg_log "captured group not drained"; return 1; fi
  yg_log "server $pid reaped and verified dead"
}
if [[ ! -d "$YG_OUT" ]]; then
  stage="$YG_OUT.tmp-$$"
  mkdir "$stage" || exit 6
  cp -a "$S/prospective-power-input/plan" "$stage/plan" || exit 6
  mv -T "$stage" "$YG_OUT" || exit 6
fi
for arm in A0 A1; do
  yg_server_argv "$arm" "$YG_PORT" "${FILLER_THREADS:?}" "$YG_OUT" > "$YG_OUT/$arm.recipe.tmp" || exit 6
  if [[ -e "$YG_OUT/$arm.recipe" ]]; then
    cmp -s "$YG_OUT/$arm.recipe.tmp" "$YG_OUT/$arm.recipe" || { echo 'REFUSED: recipe changed'; exit 6; }
    rm "$YG_OUT/$arm.recipe.tmp"
  else
    mv "$YG_OUT/$arm.recipe.tmp" "$YG_OUT/$arm.recipe" || exit 6
  fi
done
"$YG_PY" -B "$S/fresh/provenance.py" "$YG_OUT" || exit 6
yg_main || exit $?
if [[ -s "$YG_OUT/COMPLETE" ]]; then
  "$YG_PY" - "$YG_OUT/decision.json" <<'PY' || exit 6
import json,sys
d=json.load(open(sys.argv[1]))
if d['status'] != 'FINAL' or d['pooled_native']['n_pairs'] != 120 or d['excluded_from_gate']:
    raise SystemExit('REFUSED: cohort not 120 complete eligible pairs')
PY
  sha256sum "$YG_OUT/decision.json" > "$YG_OUT/VERIFIED_COMPLETE" || exit 6
fi
