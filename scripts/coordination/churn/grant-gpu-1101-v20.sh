#!/bin/bash
# v20 (ws58-calendar-keeper 2026-11-01T03:01:44Z): waits for v19 (3072798 birth 155598676).
# v18 (ws58 2026-10-30): v17 + codex3 free_of head-of-line fix (one fail-closed status snapshot per candidate, no 600 s wait); waits for v17 (1950503) to EXIT.
# v19 (ws58 2026-10-31): v18 restarted by hand after the keeper v7b 06:00Z expiry (keeper refused succession: v18 already dead). Cap 2026-11-01T06:00Z.
# Revision v17b: succession-safe parameterized predecessor guard.
# PROPOSED ONLY: owner ws58 applies at safe boundary; never hot-edit v16.
# v16 (ws58-calendar-keeper 2026-10-30T03:02:02Z): v15 copied, cap 2026-11-02T06:00:00Z, waits for v15 (551766) to EXIT so only one GPU writer is live.
# v15 (ws58-calendar-keeper 2026-10-28T11:45:26Z): v14 copied, cap 2026-11-02T06:00:00Z, waits for v14 (3927496) to EXIT so only one GPU writer is live.
# v14 (ws58 10-28 03:4xZ): v13 copied, cap 10-29T06:00Z, waits for v13 (3135524) to EXIT so only one GPU writer is live.
# v13 (ws58 10-26 21:4xZ): v12 copied verbatim except: log/pid names, cap 2026-10-28T06:00Z (night-chain cap), and it waits for v12 (pid 1976503) to EXIT before doing anything, so only one GPU writer is ever live. v12 exits when < 2300 s remain to its 00:30Z cap.
# v12 (ws58 10-25, prepared by a subagent, NOT ARMED): replaces v11 (pid 1265567). Changes vs v11, per CALENDAR-PLAN.md section 0:
#  (a) the .wsg-granted-<id> stamp is touched INSIDE step() right after the .grant is written (GRANT time), not after step() returns. v11 stamped after
#      .ended appeared, so the stamp was always newer than .ended and the re-offer test [ ended_mtime -ge stamp_mtime ] never passed (hsf-5p-microbench).
#      An item that is skipped/refused/not ready is NOT stamped (v11 stamped refusals as granted).
#  (b) every `kill -0` liveness check is `ps -o pid= -p PID` (kill -0 is blind in this sandbox).
#  (c) cap 2026-10-27T00:30Z.
#  (d) queue-first order and the HOLD pause are kept: each loop pass offers ws58-gpu.queue items (re-offer on clean end rc 0/75/124, other rc -> HELD in
#      ws58-gpu.queue.held) before ufh14/yarn. The pause now honours ANY $F/HOLD_GPU_FOR_QUIET_* file (20261024 and 20261025 names).
#  Dropped vs v11: the fixed pre-loop sequence (pb-qcost-1-confirm-r, kpf17-4c-bisect, c4-gpu-correctness, c4-leak-check): all ended/complete before 10-25.
#  Added: on start, waits out any open GPU grant (a running yarn slice or queue item) so a swap never overlaps; refused items back off 600 s.
# One live GPU writer only: stop v11 (pid 1265567) BEFORE starting this (see README-v12-swap.txt).
set -u
F=/mnt/raid0/llm/tmp/compute-flags
G=$F/grants
LOG=$F/grant-gpu-1101-v20.log
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
echo $$ > $F/grant-gpu-1101-v20.pid
log() { echo "$(date -u +%FT%TZ) $*" >> $LOG; }
ts() { date -u -d @"$1" +%Y-%m-%dT%H:%MZ; }
alive() { ps -o pid= -p "$1" >/dev/null 2>&1; }
holdfile() { local h; for h in $F/HOLD_GPU_FOR_QUIET_*; do [ -e "$h" ] && { echo "$h"; return 0; }; done; return 1; }
free_of() { # $1 regex of status lines that must be free; one fail-closed snapshot
  local status matches rc
  status=$("$RL" status 2>/dev/null) || return 1
  # The native table must contain each atomic region and the GPU exactly once.
  # Queue details, when present, follow these rows and are not region status.
  printf '%s\n' "$status" | awk '
    /^queue \(FIFO,/ { queue=1; next }
    queue { next }
    {
      if ($1 !~ /^(q0|q1|q2|q3|gpu-quiet)$/ || seen[$1]++) exit 1
      if ($1 == "gpu-quiet") {
        if ($2 !~ /^(free|HELD|EXCL|SHRD)$/) exit 1
      } else if ($2 !~ /^(free|HELD)$/) exit 1
      count++
    }
    END { if (count != 5) exit 1 }
  ' || return 1
  matches=$(printf '%s\n' "$status" | grep -E "$1"); rc=$?
  [ "$rc" -eq 0 ] || return 1  # missing requested region or invalid regex
  printf '%s\n' "$matches" | grep -qE 'HELD|EXCL|SHARED|SHRD'
  rc=$?
  [ "$rc" -eq 1 ] # busy or grep error both fail closed
}
gq_ordered() {  # finite manifest rank; stable FIFO ties/legacy; never modifies queue
  python3 -I - "$F" "$GQ" <<'PYORDER'
import json, math, pathlib, sys
f, q = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out = []
for position, line in enumerate(q.read_text().splitlines()):
    if not line or line.startswith('#'): continue
    rid = line.split('|', 1)[0]; rank = math.inf; held = False
    for directory in ('ready', 'ready/armed'):
        path = f / directory / (rid + '.json')
        if not path.exists(): continue
        try:
            m = json.loads(path.read_text())
            if m.get('id') != rid or m.get('hold') is not None: held = True; break
            value = float(m['priority_rank'])
            if math.isfinite(value) and value > 0: rank = value
        except (OSError, ValueError, TypeError, KeyError): pass
        break
    if not held: out.append((rank, position, line))
for _, _, line in sorted(out): print(line)
PYORDER
}
launcher_birth() {  # existing native parser rejects zombies, inner engines and unrelated reused PIDs
  python3 -I - "$F" "$1" "$2" <<'PYBIRTH'
import json, pathlib, sys
sys.path.insert(0, sys.argv[1])
import grant_ok_launcher as gate
try:
    pid = int(sys.argv[3]); row = sys.argv[2]
    if not gate.alive('/proc', pid): raise ValueError('dead')
    options, engine, _ = gate.find_launcher('/proc', pid, row)
    if options is None: raise ValueError('no matching engine')
    stat = pathlib.Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
    minimum = options['min_window']
    if not isinstance(minimum, int) or minimum <= 0: raise ValueError('missing minimum')
    for directory in ('ready', 'ready/armed'):
        manifest = pathlib.Path(sys.argv[1]) / directory / (row + '.json')
        if not manifest.exists(): continue
        m = json.loads(manifest.read_text())
        if 'min_window_s' in m:
            declared = m['min_window_s']
            if isinstance(declared, bool) or not isinstance(declared, int) or declared <= 0: raise ValueError('invalid declared minimum')
            if minimum != declared: raise ValueError('declared and actual minima differ')
        break
    print('%s|%d' % (stat[19], minimum))
except (OSError, ValueError, gate.Refuse): sys.exit(1)
PYBIRTH
}
claim_regex() {  # use the SAME parser/claim derivation as grant_ok, then existing free_of
  python3 -I - "$F" "$1" "$2" "$3" <<'PYCLAIM'
import sys
sys.path.insert(0, sys.argv[1])
import grant_ok_launcher as gate
try:
    o, _, _ = gate.find_launcher('/proc', int(sys.argv[3]), sys.argv[2])
    if o is None or o['self_claim']: raise ValueError('unknown job-side claims')
    cpus = gate.parse_regions(sys.argv[4], o['class'], o['gpu_threads'])
    cl, gm = gate.claim_of(o, cpus)
    need = gate.cpu_regions(cl, not (o['nofold'] and o['class'] != 'gpu')) if cl else set()
    if gm: need.add('gpu-quiet')
    # This writer owns the MI210 bin even when a launcher suppresses its own lock.
    need.add('gpu-quiet')
    print('^ *(' + '|'.join(sorted(need)) + ') ')
except (OSError, ValueError, gate.Refuse): sys.exit(1)
PYCLAIM
}
step() {  # $1 id, $2 pid, $3 seconds, $4 min seconds, $5 GiB, $6 cap epoch, $7 free-regex, $8 regions
  local st en r birth after minwin claims
  [ -e $G/$1.complete ] && { log "$1 skipped: complete"; return 2; }
  birth=$(launcher_birth "$1" "$2") || { log "$1 skipped: launcher $2 dead/reused/unrecognised"; return 2; }
  minwin=${birth#*|}  # actual parsed launcher minimum; old queues may contain invented window-300
  claims=$(claim_regex "$1" "$2" "${8:-mi210_0,184-191}") || { log "$1 skipped: cannot derive native claim"; return 2; }
  free_of "$claims" || { log "$1 skipped: claims still held"; return 1; }
  st=$(date -u +%s); en=$(( st + $3 )); [ $en -gt $6 ] && en=$6
  [ $(( en - st )) -lt $(( minwin + 300 )) ] && { log "$1 skipped: window $(( en - st )) s < min $minwin + 300"; return 1; }
  r=$("$F/grant_ok.sh" "$1" "$5" --window-s "$((en-st))" --regions "${8:-mi210_0,184-191}" --pid "$2") || { case "$r" in *"not ready"*) log "$1 not ready: ${r:0:120}"; return 1;; esac; log "$1 refused: $r"; return 2; }
  after=$(launcher_birth "$1" "$2") || return 2
  [ "$birth" = "$after" ] || { log "$1 skipped: launcher PID birth changed during admission"; return 2; }
  printf 'regions=%s start=%s end=%s\n' "${8:-mi210_0,184-191}" "$(ts $st)" "$(ts $en)" > $G/$1.grant
  touch $F/.wsg-granted-$1          # (a) stamp at GRANT time: any later .ended is newer than the stamp
  log "$r; granted $1: $(cat $G/$1.grant)"
  while :; do
    if [ -e $G/$1.ended ] && [ "$(stat -c %Y $G/$1.ended)" -ge $st ]; then log "$1 ended: $(head -1 $G/$1.ended)"; return 0; fi
    [ "$(date -u +%s)" -ge $(( en + 300 )) ] && { log "$1: no .ended by end + 5 min"; return 0; }
    sleep 30
  done
}
GPUQ='^ *gpu-quiet'
UFH=$F/FIXED_ufh14-lb7-1-probes
P3=$(date -u -d '2026-11-02T06:00:00Z' +%s)      # (c) cap
ufh_ready() {  # fixed, not complete, launcher alive, and not already run since the FIXED flag was written
  [ -e $UFH ] && [ ! -e $G/ufh14-lb7-1-probes.complete ] && alive 2562628 || return 1
  [ -e $G/ufh14-lb7-1-probes.ended ] && [ "$(stat -c %Y $G/ufh14-lb7-1-probes.ended)" -ge "$(stat -c %Y $UFH)" ] && return 1
  return 0
}
predecessor_alive() {  # PID + captured birth are arguments, rewritten together by keeper
  python3 -I - "$1" "$2" <<'PYPREV'
import pathlib, sys
try:
    root=pathlib.Path('/proc') / sys.argv[1]
    fields=(root/'stat').read_text().rsplit(')',1)[1].split()
    ok=fields[0] not in ('Z','X','x') and fields[19] == sys.argv[2]
except FileNotFoundError: ok=False
except (OSError, ValueError, IndexError): ok=True  # uncertainty blocks, never starts a second writer
sys.exit(0 if ok else 1)
PYPREV
}
while ps -o pid= -p 3072798 >/dev/null 2>&1 && predecessor_alive 3072798 155598676; do sleep 30; done
# ps can fail under /proc visibility errors: the authoritative identity check must still refuse.
if predecessor_alive 3072798 155598676; then log "predecessor identity uncertain or still live; refusing startup"; exit 1; fi
log "v19 (3072798) gone; v20 starting"
log "armed v20 (stamp at grant, ps liveness, cap $(ts $P3)); adopting any open queue grant, then waiting it out"
GQ=$F/ws58-gpu.queue
for gf in $G/*.grant; do   # swap from v11: an item v11 granted but never stamped (stamp-after-step bug) gets the stamp it should have had: the .grant's own mtime
  [ -e "$gf" ] || continue; gid=$(basename "$gf" .grant)
  if grep -qE "^$gid\|" $GQ 2>/dev/null && grep -q 'mi210_0' "$gf"; then touch -r "$gf" $F/.wsg-granted-$gid; log "adopted open grant $gid: stamp := .grant mtime"; fi
done
while ls $G/*.grant >/dev/null 2>&1 && grep -l 'mi210_0' $G/*.grant >/dev/null 2>&1 && [ "$(date -u +%s)" -lt $P3 ]; do sleep 30; done
log "no open GPU grant; entering the loop"
declare -A REFUSED
gq_next() {  # grant the first ready item of ws58-gpu.queue (id|pid|win|min|gib|free-regex|regions); 0 = something was granted and ended, 1 = nothing ran
  local id lp win mn gib rx rg erc src now
  while IFS='|' read -r id lp win mn gib rx rg; do
    case "$id" in ''|\#*) continue;; esac
    [ -e $G/$id.complete ] && continue; [ -e $G/$id.grant ] && continue; alive "$lp" || continue
    grep -qx "$id" $F/ws58-gpu.queue.held 2>/dev/null && continue
    now=$(date -u +%s); [ "${REFUSED[$id]:-0}" -gt "$now" ] && continue
    if [ -e $F/.wsg-granted-$id ]; then
      [ -e $G/$id.ended ] && [ "$(stat -c %Y $G/$id.ended)" -ge "$(stat -c %Y $F/.wsg-granted-$id)" ] || continue
      erc=$(head -1 $G/$id.ended | sed -n 's/^rc=\([0-9]*\).*/\1/p')
      case "$erc" in 0|75|124) ;; *) echo "$id" >> $F/ws58-gpu.queue.held; log "$id HELD: last end rc=$erc"; continue;; esac
    fi
    step "$id" "$lp" "$win" "$mn" "$gib" $P3 "${rx:-$GPUQ}" "${rg:-mi210_0,184-191}"; src=$?
    [ $src = 1 ] && continue                                   # not ready / claims held: try the next item
    [ $src = 2 ] && { REFUSED[$id]=$(( now + 600 )); continue; }   # refused / complete / launcher gone: back off, no stamp
    return 0
  done < <(gq_ordered)
  return 1
}
log "loop: queue items first, then ufh14 when re-fixed, else yarn slices; paused while any HOLD_GPU_FOR_QUIET_* exists"
YARN_DONE=0
while [ $(( P3 - $(date -u +%s) )) -ge 2300 ]; do
  if h=$(holdfile); then sleep 60; continue; fi
  if [ -e $GQ ] && gq_next; then continue; fi
  if ufh_ready; then step ufh14-lb7-1-probes 2562628 6000 1920 48 $P3 '^ *(q3|gpu-quiet) '; [ $? = 1 ] && sleep 120; continue; fi
  if [ $YARN_DONE = 1 ] || [ $(( P3 - $(date -u +%s) )) -lt 7500 ]; then sleep 120; continue; fi
  step yarn-extension-arms 1198715 7800 7200 64 $P3 "$GPUQ"; rc=$?
  [ $rc = 2 ] && { YARN_DONE=1; log "yarn done/refused; loop keeps waiting for queue items/ufh14"; }
  [ $rc = 1 ] && sleep 120
done
log "done"
