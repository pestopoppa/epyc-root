#!/bin/bash
set -euo pipefail
S=/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch
source "$S/owned-id.sh"
yg_log() { printf '%s\n' "$*"; }
source <(sed -n '/^yg_stop() {/,/^}/p' "$S/fresh/job.sh")
setsid bash -c 'sleep .2; exit 7' & pid=$!
read -r YG_OWN_PID YG_OWN_BIRTH YG_OWN_PGID < <(owned_capture_group "$pid")
sleep .4
rc=7
yg_stop "$pid" || rc=8
[[ $rc == 7 ]]
ps -p "$pid" -o pid= >/dev/null && exit 1
echo 'already exited server: cleanup preserves rc7 retry PASS'
