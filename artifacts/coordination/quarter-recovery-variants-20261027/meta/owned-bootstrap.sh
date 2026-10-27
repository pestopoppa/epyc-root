#!/bin/bash
# Source-only cleanup for the captured setsid bootstrap; no process-name signals.
bootstrap_identity() {
  local pid=$1 line rest uid a b c d
  [[ -r /proc/$pid/stat && -r /proc/$pid/status ]] || return 1
  IFS= read -r line < "/proc/$pid/stat" || return 1
  rest=${line##*) }
  # Fields after comm begin with state; starttime is field 20 here.
  read -r -a bi_fields <<< "$rest"
  (( ${#bi_fields[@]} >= 20 )) || return 1
  uid=''
  while read -r a b c d uid; do
    if [[ $a == Uid: ]]; then
      BI_UIDS_MATCH=0; [[ $b == "$c" && $b == "$d" && $b == "$uid" ]] && BI_UIDS_MATCH=1
      uid=$b; break
    fi
  done < "/proc/$pid/status"
  [[ $uid =~ ^[0-9]+$ ]] || return 1
  BI_STATE=${bi_fields[0]} BI_PGID=${bi_fields[2]} BI_SID=${bi_fields[3]} BI_START=${bi_fields[19]} BI_UID=$uid
}

bootstrap_capture() {
  bootstrap_identity "$active" || return 1
  [[ $BI_UIDS_MATCH == 1 && $BI_UID == "$EUID" && $BI_SID == "$active" && $BI_PGID == "$active" && $BI_STATE != Z ]] || return 1
  bootstrap_uid=$BI_UID bootstrap_sid=$BI_SID bootstrap_pgid=$BI_PGID bootstrap_start=$BI_START
}

# A complete scan is required before signalling and before declaring absence.
# A vanished /proc entry is harmless; an unreadable live entry fails closed.
bootstrap_scan() {
  local entry pid
  bootstrap_members=()
  for entry in /proc/[0-9]*; do
    pid=${entry##*/}
    if ! bootstrap_identity "$pid"; then
      [[ ! -e $entry ]] && continue
      return 1
    fi
    if [[ $pid == "$active" ]]; then
      [[ $BI_UIDS_MATCH == 1 && $BI_START == "$bootstrap_start" && $BI_UID == "$bootstrap_uid" && $BI_SID == "$bootstrap_sid" && $BI_PGID == "$bootstrap_pgid" ]] || return 1
    fi
    if [[ $BI_PGID == "$bootstrap_pgid" ]]; then
      [[ $BI_UIDS_MATCH == 1 && $BI_UID == "$bootstrap_uid" && $BI_SID == "$bootstrap_sid" ]] || return 1
      bootstrap_members+=("$pid:$BI_START:$BI_STATE")
    fi
  done
}

bootstrap_drain() {
  local phase member pid start state i
  [[ -n ${bootstrap_start:-} ]] || return 1
  for phase in TERM KILL; do
    for ((i=0; i<20; i++)); do
      bootstrap_scan || return 1
      if ((${#bootstrap_members[@]} == 0)); then wait "$active" 2>/dev/null || true; return 0; fi
      for member in "${bootstrap_members[@]}"; do
        IFS=: read -r pid start state <<< "$member"
        [[ $state == Z ]] && continue
        bootstrap_identity "$pid" || { [[ ! -e /proc/$pid ]] && continue; return 1; }
        [[ $BI_UIDS_MATCH == 1 && $BI_START == "$start" && $BI_UID == "$bootstrap_uid" && $BI_SID == "$bootstrap_sid" && $BI_PGID == "$bootstrap_pgid" ]] || return 1
        kill -s "$phase" -- "$pid" 2>/dev/null || { [[ ! -e /proc/$pid ]] || return 1; }
      done
      # wait is bounded: call it only for an absent or zombie direct child.
      if ! bootstrap_identity "$active" || [[ $BI_STATE == Z ]]; then wait "$active" 2>/dev/null || true; fi
      sleep 0.1
    done
  done
  bootstrap_scan || return 1
  ((${#bootstrap_members[@]} == 0))
}
