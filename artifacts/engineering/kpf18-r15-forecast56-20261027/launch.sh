#!/bin/bash
set -euo pipefail
source /mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/config.sh
WATCH=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-forecast56
hold_guard;source_guard
[[ -s "$WATCH/MAIN-APPROVAL.txt" && -s "$WATCH/SOURCE.sha256" ]] || refuse 'forecast watcher not reviewed'
(cd "$WATCH" && sha256sum --quiet -c SOURCE.sha256) || refuse 'forecast watcher source drift'
grep -Fx "source-seal-sha256=$(sha256sum "$WATCH/SOURCE.sha256" | cut -d' ' -f1)" "$WATCH/MAIN-APPROVAL.txt" >/dev/null || refuse 'forecast watcher approval seal mismatch'
export KPF18_WATCH_RECEIPT="$WATCH/RESOURCE-ABORT.json"
[[ ! -e "$KPF18_WATCH_RECEIPT" && ! -L "$KPF18_WATCH_RECEIPT" ]] || refuse 'prior watcher abort exists'
hard_kib=$(ulimit -Hv)
[[ $hard_kib == unlimited ]] || { [[ $hard_kib =~ ^[0-9]+$ ]] && ((hard_kib>=192*1024*1024)); } || refuse 'native parent address-space limit'
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]];then
 [[ ${DRYRUN_NONCE:-} =~ ^[a-f0-9]{48}$ && ${FILLER_GRANTS_DIR:-} == "$BASE/dryrun/$DRYRUN_NONCE/grants" ]] || refuse 'isolated PF nonce'
 export FILLER_GPU_LOCK=$BASE/dryrun/$DRYRUN_NONCE/gpu-device.synthetic.lock
 printf 'PF_PRIVATE_GPU_LOCK=%s; no real device lock\n' "$FILLER_GPU_LOCK"
 CLAIM_CPUS=$PF_CPUS
 SCHED_ARGS=() # Route-only PF uses private GPU lock and ends before model load.
 export FILLERS_MD=$WATCH/ROW-56.md
else
 [[ -s $BASE/DATA-VALIDATION-ACCEPTED.json && -s $BASE/INTEGRATION-REPLAY-ACCEPTED.json && -s $BASE/BK-ENROLLMENT-APPLIED.json ]] || refuse 'actual accepted components or canonical enrollment missing'
 unset FILLER_GRANTS_DIR FILLER_FLAGS_DIR FILLER_RL FILLER_STUB_CMD FILLER_GPU_LOCK FILLER_POLL
 export FILLER_STATE_DIR=$BASE/state FILLERS_MD=$WATCH/ROW-ARMED.md
 CLAIM_CPUS=184-191
 SCHED_ARGS=(--sched-port 8083) # Normal serving exclusion remains mandatory.
fi
exec /bin/bash "$ENGINE" --id "$ID" --class gpu --gpu-quiet exclusive --claim-cpus "$CLAIM_CPUS" --no-fold-siblings --role build --min-window 8700 \
 --port "$PORT" "${SCHED_ARGS[@]}" --stop "$BASE/STOP" --workdir "$BASE" --cmd "$PY -I -B $WATCH/resource-watch.py /bin/bash $BASE/job.sh" \
 --precond-cmd "/bin/bash $WATCH/precondition.sh" --complete-cmd "test -s $BASE/DIAGNOSTIC-COMPLETE"
