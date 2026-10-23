# Grant writer pattern

A grant writer is a versioned `#!/bin/bash` script, one per region set, that turns a plan into
`grants/<id>.grant` files at the right moments. The reference implementations are workspace-58's
`compute-flags/grant-afternoon-20261023.sh` (parallel lanes), `grant-gpu-long-20261023-v2.sh`
(GPU chain with a quiet phase), `grant-block-20261023-v4.sh` (whole-CPU block with an END flag)
and `grant-freedq-20261022.sh` (freed-quarter gap filler). All live under
`/mnt/raid0/llm/tmp/compute-flags/`; the live tooling there is read-only for everyone except the
calendar owner.

## Skeleton

```bash
#!/bin/bash
# <owner>: <what this writer does, which writer version it replaces and why>
set -u
F=/mnt/raid0/llm/tmp/compute-flags; G=$F/grants; LOG=$F/grant-<name>.log
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
echo $$ > $F/grant-<name>.pid
log() { echo "$(date -u +%FT%TZ) [$LANE] $*" >> $LOG; }
ts()  { date -u -d @"$1" +%Y-%m-%dT%H:%MZ; }
rowpid() { grep "^| $1 |" $F/FILLERS.md | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2; }
# wait (bounded) until no claim matching $1 is HELD/EXCL/SHARED -- ONLY the regions this grant needs
free_of() { local u=$(( $(date -u +%s) + 900 ))
  while $RL status 2>/dev/null | grep -E "$1" | grep -qE 'HELD|EXCL|SHARED'; do
    [ "$(date -u +%s)" -ge $u ] && return 1; sleep 10; done; }
# step id pid seconds minsec GiB regions free-regex [cap-epoch] [ram-mode]
step() {
  local id=$1 pid=$2 sec=$3 min=$4 gib=$5 reg=$6 rx=$7 cap=${8:-0} mode=${9:-} st en r
  [ -e $G/$id.complete ] && { log "$id skipped: complete"; return 2; }
  [ -n "$pid" ] && kill -0 $pid 2>/dev/null || { log "$id skipped: launcher '$pid' not running"; return 2; }
  free_of "$rx" || { log "$id skipped: claims ($rx) held 15 min"; return 1; }
  st=$(date -u +%s); en=$(( st + sec )); [ $cap -gt 0 ] && [ $en -gt $cap ] && en=$cap
  [ $(( en - st )) -lt $(( min + 300 )) ] && { log "$id skipped: window $(( en - st )) s < min $min + 300"; return 1; }
  r=$($F/grant_ok.sh $id $gib $mode) || { log "$id refused: $r"; return 2; }
  printf 'regions=%s start=%s end=%s\n' "$reg" "$(ts $st)" "$(ts $en)" > $G/$id.grant
  log "$r; granted $id: $(cat $G/$id.grant)"
  while :; do   # wait for an .ended NEWER than our start (old .ended files linger)
    if [ -e $G/$id.ended ] && [ "$(stat -c %Y $G/$id.ended)" -ge $st ]; then log "$id ended: $(head -1 $G/$id.ended)"; return 0; fi
    [ "$(date -u +%s)" -ge $(( en + 300 )) ] && { log "$id: no .ended by end + 5 min"; return 0; }
    sleep 30
  done
}
CPU='^ *q[0-3] '; GPUQ='^ *gpu-quiet'; ALL='^ *(q[0-3]|gpu-quiet) '
```

Return codes of `step`: 0 ran (or timed out waiting for `.ended`), 1 could not place now (retry
later is legitimate), 2 never place again in this writer (complete, dead launcher, refused).

## Lanes

Independent region sets run as background subshells and `wait`:

```bash
( LANE=B; trap 'echo "time=$(date -u +%FT%TZ) by=<owner>" > $F/GPU_CHAIN_ENDED_<date>' EXIT
  for s in "id1 pid1 2100 1800 13" "id2 ROW 2400 1800 48"; do set -- $s; p=$2; [ "$p" = ROW ] && p=$(rowpid $1)
    step $1 "$p" $3 $4 $5 mi210_0,184-191 '^ *(q3|gpu-quiet) '; done ) &
( LANE=C; step build-x 1715017 1500 900 24 q0 '^ *q0 '; step test-x 2014096 3000 1800 50 q0 '^ *q0 ' $E5 ) &
wait
```

Rules the skeleton encodes, and why:

| Line | Why |
|---|---|
| `free_of` on a lane-specific regex | a whole-status wait stalled the 10-23 CPU block behind a co-running GPU-only claim; a folded GPU lane waits on `q3|gpu-quiet`, a no-fold GPU lane on `gpu-quiet` only |
| `.complete` and `kill -0 pid` first | never grant a done id or a dead launcher; a stale poller would take a re-written grant |
| `min + 300` | poll lag (45 s) made three exactly-equal windows refuse `rc=3` |
| `grant_ok.sh` immediately before the write | row validity (`--for-grant`) and RAM admission at grant time, not at planning time |
| `.ended` newer than `st` | `.ended` files from earlier windows stay on disk |
| `trap ... EXIT` for the END flag | downstream writers wait on it; this is also why a superseded writer is stopped with **SIGKILL**, so the trap cannot fire early |
| the `--precond-cmd` build step before the test step in the same lane | a GPU test that needs a build sits on q2's lane right after the build; the launcher re-checks the precondition at grant time |
| a cap epoch on the last step | book to the end of the night, but never past the next fixed booking |

## Swapping a writer (vN → vN+1)

1. Write vN+1 as a new file; `bash -n` it; dry-read the ids' `pid=` tokens and `.complete` state.
2. List every other live writer whose steps can grant the same regions (grep the `grant-*.sh`
   whose `.pid` is alive), including conditional early-trigger branches. Retire them too, or the
   double grant of 10-22 16:47Z repeats.
3. `kill -KILL <vN pid>` (captured from its `.pid` file; never a name pattern), `ps -p` to verify.
4. Start vN+1 detached; confirm its `.pid` file and first `armed` log line; append a calendar
   REVISION line naming the replaced pid and the reason.

## Filler launcher flags vs the grant line it will receive

| Job | `filler_run8.sh` flags | Grant `regions=` |
|---|---|---|
| CPU correctness on a quarter | `--class cpu` | `q2` or `48-71` |
| whole-CPU correctness | `--class cpu --claim-cpus 0-95 --role build` | `0-95` |
| CPU timing needing the GPU quiet | `--class cpu --gpu-quiet exclusive --claim-cpus 0-95 --role bench` | `0-95` |
| GPU-only, co-runs with CPU work | `--class gpu --no-fold-siblings` (claims gpu-quiet only; job tasksets 184-191) | `mi210_0,184-191` |
| GPU, folded (needs q3 empty) | `--class gpu` (claims q3 via the fold) | `mi210_0,184-191` |
| whole-host quiet GPU timing | `--class gpu --gpu-quiet exclusive --claim-cpus 0-95 --role bench` | `mi210_0,184-191` (writer waits on ALL claims) |

`--class cpu+gpu` needs an `mi210_0` token and refuses a plain `0-95` grant. `.ended` codes: 124
hard end, 4 refused (port/lock busy), 2 unusable grant, 3 window below min, 5 precondition
missing, 75 inner claim timeout, 143 launcher signalled. A job's inner `region-lock` claim must
not exceed what its row books, or it times out (`rc=75`) behind other holders while its grant
burns.
