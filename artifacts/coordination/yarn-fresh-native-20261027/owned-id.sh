#!/bin/bash
# Source-only helpers. Capture child identity at spawn; reject PID reuse.
owned_read() {
  local pid=$1 raw tail
  [[ $pid =~ ^[0-9]+$ ]] || return 1
  IFS= read -r raw < "/proc/$pid/stat" || return 1
  tail=${raw##*) }
  read -r -a OWN_FIELDS <<< "$tail"
  [[ ${#OWN_FIELDS[@]} -ge 20 && ${OWN_FIELDS[2]} =~ ^[0-9]+$ && ${OWN_FIELDS[19]} =~ ^[0-9]+$ ]] || return 1
  OWN_STATE=${OWN_FIELDS[0]} OWN_PGID=${OWN_FIELDS[2]} OWN_BIRTH=${OWN_FIELDS[19]}
}
owned_match() {
  local pid=$1 birth=$2 pgid=$3
  owned_read "$pid" || return 1
  [[ $OWN_STATE != Z && $OWN_BIRTH == "$birth" && $OWN_PGID == "$pgid" ]]
}
owned_capture_group() {
  local pid=$1 i birth
  owned_read "$pid" || return 1
  birth=$OWN_BIRTH
  for i in {1..100}; do
    owned_read "$pid" || return 1
    [[ $OWN_BIRTH == "$birth" && $OWN_STATE != Z ]] || return 1
    if [[ $OWN_PGID == "$pid" ]]; then
      printf '%s %s %s\n' "$pid" "$birth" "$OWN_PGID"
      return 0
    fi
    sleep .01
  done
  return 1
}
