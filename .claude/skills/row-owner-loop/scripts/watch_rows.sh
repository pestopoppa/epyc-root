#!/bin/bash
# watch_rows.sh — the ONE owner watcher (row-owner-loop skill, step 3). Run with run_in_background.
# Prints one line per actionable event and exits 0 on the first one; re-arm after handling.
#   ENDED <id> rc= reason=        grants/<id>.ended owned by --owner, no filing-done/<id>.FILED
#   SMOKE-FAIL <id>               last launcher.out block of dryrun/<id> says FAIL (owner's ready/ rows)
#   QUEUED-DROPPED <id> <file>    dryrun/<id>/QUEUED-DROPPED-*.json
#   QUEUED-AGED <id> <age_s>      dryrun/<id>/*SMOKE-QUEUED.json older than --queued-max
#   IDLE-GRANT <id> gpu|cpu <pct> owner grant open, device/quarter busy < --idle-pct for --idle-n samples
# --gate-eval: on ENDED, also draft <rowdir>/verdict.json with the deterministic gate evaluator
#   (runend.py <id> --gate-eval, AKPL-P1) and append `gate=<verdict>` to the event line.
# Handled events are keyed in the state file; `--ack <key>` records one so it never fires again.
# No per-row exclusions in code. Usage:
#   watch_rows.sh --owner autokernel [--interval 60] [--queued-max 600] [--idle-pct 5] [--idle-n 3] [--once]
#   watch_rows.sh --owner autokernel --ack 'ENDED <id>'
set -euo pipefail
FLAGS=/mnt/raid0/llm/tmp/compute-flags
OWNER="" INTERVAL=60 QMAX=600 IDLE_PCT=5 IDLE_N=3 ONCE=0 ACK="" SINCE="" GATE_EVAL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --owner) OWNER=$2; shift 2;; --interval) INTERVAL=$2; shift 2;; --queued-max) QMAX=$2; shift 2;;
    --idle-pct) IDLE_PCT=$2; shift 2;; --idle-n) IDLE_N=$2; shift 2;; --once) ONCE=1; shift;;
    --ack) ACK=$2; shift 2;; --gate-eval) GATE_EVAL=1; shift;; --flags) FLAGS=$2; shift 2;; --since) SINCE=$2; shift 2;;
    *) echo "unknown arg $1" >&2; exit 2;;
  esac
done
[ -n "$OWNER" ] || { echo "--owner required" >&2; exit 2; }
STATE_DIR=${WATCH_ROWS_STATE:-/mnt/raid0/llm/tmp/row-owner-loop-state}
mkdir -p "$STATE_DIR"
STATE=$STATE_DIR/$OWNER.handled
MARK=$STATE_DIR/$OWNER.marker
IDLE=$STATE_DIR/$OWNER.idle
touch "$STATE" "$IDLE"
# The marker bounds ENDED to records newer than the first arm (or --since 'YYYY-MM-DD HH:MM').
if [ -n "$SINCE" ]; then touch -d "$SINCE" "$MARK"; elif [ ! -e "$MARK" ]; then touch "$MARK"; fi
if [ -n "$ACK" ]; then echo "$ACK" >> "$STATE"; echo "ACKED $ACK"; exit 0; fi

handled() { grep -qxF "$1" "$STATE"; }
emit() { handled "$1" && return 1; echo "$(date -u +%FT%TZ) $1${2:+ $2}"; return 0; }

owner_of_ready() { # prints ids of the owner's published rows
  for f in "$FLAGS"/ready/*.json; do
    [ -e "$f" ] || continue
    grep -q "\"owner\": *\"$OWNER\"" "$f" && basename "$f" .json
  done
  return 0
}

gpu_busy() { # integer GPU busy % of card 0, or empty
  /opt/rocm/bin/rocm-smi --showuse --json 2>/dev/null | python3 -c 'import json,sys
d=json.load(sys.stdin)
for k,v in d.items():
  for kk,vv in v.items():
    if "GPU use" in kk: print(int(float(vv))); raise SystemExit' 2>/dev/null || true
}

cpu_busy() { # busy % over a cpu list (e.g. 0-23) across a 2 s window
  python3 - "$1" <<'EOF'
import sys,time,re
def parse(s):
    out=set()
    for p in s.split(','):
        m=re.fullmatch(r'(\d+)-(\d+)',p.strip())
        if m: out|=set(range(int(m[1]),int(m[2])+1))
        elif p.strip().isdigit(): out.add(int(p))
    return out
want=parse(sys.argv[1])
def snap():
    r={}
    for l in open('/proc/stat'):
        m=re.match(r'cpu(\d+) (.*)',l)
        if m and int(m[1]) in want:
            v=list(map(int,m[2].split())); r[int(m[1])]=(sum(v),v[3]+v[4])
    return r
a=snap(); time.sleep(2); b=snap()
tot=sum(b[c][0]-a[c][0] for c in b); idle=sum(b[c][1]-a[c][1] for c in b)
print(int(100*(tot-idle)/tot) if tot else 0)
EOF
}

scan() {
  local f id rc reason age q last busy cnt regs gv
  # ENDED
  for f in "$FLAGS"/grants/*.ended; do
    [ -e "$f" ] || continue
    [ "$f" -nt "$MARK" ] || continue
    grep -q "^owner=$OWNER\$" "$f" || continue
    id=$(basename "$f" .ended)
    [ -e "$FLAGS/filing-done/$id.FILED" ] && continue
    rc=$(sed -n '0,/^rc=/s/^rc=\([^ ]*\).*/\1/p' "$f")
    reason=$(sed -n '0,/reason=/s/.*reason=\([^ ]*\).*/\1/p' "$f")
    if ! handled "ENDED $id" && [ "$GATE_EVAL" = 1 ]; then
      gv=$(python3 "$(dirname "$0")/runend.py" "$id" --gate-eval 2>&1 | tail -n 1 | cut -c1-160 || true)
      reason="$reason gate=[$gv]"
    fi
    emit "ENDED $id" "rc=$rc reason=$reason" && return 0
  done
  for id in $(owner_of_ready); do
    d=$FLAGS/dryrun/$id
    [ -d "$d" ] || continue
    # SMOKE-FAIL: last block only (lines after the last '==== ' header block start)
    if [ -f "$d/launcher.out" ]; then
      last=$(grep -E '^==== dry run (PASS|FAIL)' "$d/launcher.out" | tail -n 1 || true)
      case "$last" in *"dry run FAIL"*) emit "SMOKE-FAIL $id" "$(echo "$last" | cut -c1-160)" && return 0;; esac
    fi
    for q in "$d"/QUEUED-DROPPED-*.json; do
      [ -e "$q" ] || continue
      emit "QUEUED-DROPPED $id $(basename "$q")" && return 0
    done
    for q in "$d"/*SMOKE-QUEUED.json; do
      [ -e "$q" ] || continue
      age=$(( $(date +%s) - $(stat -c %Y "$q") ))
      [ "$age" -gt "$QMAX" ] && emit "QUEUED-AGED $id" "${age}s $(basename "$q")" && return 0
    done
  done
  # IDLE-GRANT: owner's open grants
  for f in "$FLAGS"/grants/*.grant; do
    [ -e "$f" ] || continue
    id=$(basename "$f" .grant)
    grep -q "\"owner\": *\"$OWNER\"" "$FLAGS/ready/$id.json" 2>/dev/null || continue
    regs=$(sed -n 's/^regions=\([^ ]*\).*/\1/p' "$f")
    if [[ "$regs" == *mi210* ]]; then busy=$(gpu_busy); kind=gpu
    else busy=$(cpu_busy "$regs"); kind=cpu; fi
    [ -n "$busy" ] || continue
    if [ "$busy" -lt "$IDLE_PCT" ]; then
      cnt=$(( $(grep -c "^$id " "$IDLE" || true) + 1 )); echo "$id $busy" >> "$IDLE"
      [ "$cnt" -ge "$IDLE_N" ] && emit "IDLE-GRANT $id" "$kind ${busy}% x$cnt" && return 0
    else
      grep -v "^$id " "$IDLE" > "$IDLE.tmp" || true; mv "$IDLE.tmp" "$IDLE"
    fi
  done
  return 1
}

while true; do
  if scan; then exit 0; fi
  [ "$ONCE" = 1 ] && { echo "$(date -u +%FT%TZ) NO-EVENT"; exit 1; }
  sleep "$INTERVAL"
done
