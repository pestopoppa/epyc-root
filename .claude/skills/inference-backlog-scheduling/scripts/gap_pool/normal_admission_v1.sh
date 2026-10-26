#!/bin/bash
# PROPOSED extracted native normal checks; only official owner grant calls this.
set -euo pipefail
F=$1; RL=$2; id=$3; gib=$4; W=$5; regs=$6
quarters() {
  local t a b c q
  for t in ${1//,/ }; do
    case "$t" in q[0-3]) echo "$t";;
      *) [[ $t =~ ^([0-9]+)(-([0-9]+))?$ ]] || return 6
         a=${BASH_REMATCH[1]}; b=${BASH_REMATCH[3]:-$a}
         ((a<=b && b<=191)) || return 6
         for ((c=a;c<=b;c++)); do q=$(((c%96)/24)); echo "q$q"; done;; esac
  done | sort -u
}
# Capture the producer rc before parsing: a dead/unreadable status is UNKNOWN.
claim_status=""; claim_rc=0
claim_status=$("$RL" status 2>&1) || claim_rc=$?
((claim_rc == 0)) || { echo "refuse: region-status-rc=$claim_rc" >&2; exit 6; }
# Native formatter: exactly one q0..q3 and gpu-quiet line, known states, optional
# native FIFO queue heading/tails. Missing/duplicate/unknown rows fail closed.
status_rows=$(printf '%s\n' "$claim_status" | awk '
  /^[[:space:]]*(q[0-3]|gpu-quiet)[[:space:]]/ {
    if (++seen[$1] != 1 || $2 !~ /^(free|HELD|EXCL|SHARED|SHRD)$/) bad=1
    print $1, $2; next
  }
  /^queue \(FIFO, EPYC_LOCK_FIFO=1 clients only\):$/ { if(queue++) bad=1; next }
  /^[[:space:]]*#[0-9]+[[:space:]]+age=/ { if(!queue) bad=1; next }
  { bad=1 }
  END { if(seen["q0"]!=1 || seen["q1"]!=1 || seen["q2"]!=1 || seen["q3"]!=1 || seen["gpu-quiet"]!=1 || bad) exit 6 }
') || { echo 'refuse: unknown-region-status-schema' >&2; exit 6; }
needed=$(quarters "$regs") || { echo 'refuse: unknown-requested-regions' >&2; exit 6; }
for q in $needed; do
  state=$(printf '%s\n' "$status_rows" | awk -v q="$q" '$1==q {print $2}')
  [[ $state == free ]] || { echo "refuse: $q=$state" >&2; exit 6; }
done
r=$("$F/grant_ok.sh" "$id" "$gib" --window-s "$W" --regions "$regs") || exit $?
# Native owner SMT rule retained; no timing beside GPU host threads184-191.
case " $(quarters "$regs" | tr '\n' ' ') " in *" q3 "*)
  shopt -s nullglob
  for grant in "$F"/grants/*.grant; do
    if grep -qE 'regions=[^ ]*184-191' "$grant"; then
      [[ $r == *class=block-correctness* ]] || exit 6
    fi
  done;;
esac
printf '%s\n' "$r"
