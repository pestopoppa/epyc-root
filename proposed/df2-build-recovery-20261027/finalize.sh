#!/bin/bash
# Source-only; caller passes both actual statuses and explicit paths.
recovery_fresh() {
 local work=$1 done=$2
 [[ ! -e $work && ! -L $work && ! -e $done && ! -L $done ]]
}
finalize_recovery() {
 local work_rc=$1 drain_rc=$2 work=$3 build_marker=$4 recovery_marker=$5
 ((work_rc==0)) || return "$work_rc"
 ((drain_rc==0)) || return "$drain_rc"
 [[ -s $work && ! -e $build_marker && ! -L $build_marker && ! -e $recovery_marker && ! -L $recovery_marker ]] || return 70
 ( set -o noclobber; cat "$work" > "$recovery_marker" ) || return 70
 if ! ln "$recovery_marker" "$build_marker"; then rm -f "$recovery_marker"; return 70; fi
}
