#!/bin/bash
# filler_run15.sh - canonical engine of the simplified row flow (ws58, operator ruling 2026-11-01: remove every gate
# that is not indispensable). = filler_run14.sh MINUS the keeper-qualification coupling (WS58_QUAL fixture branch,
# nonce/receipt verify at start and at grant, dryrun_check.py T1 admission and in-claim resource proof against the
# FILLERS.md 18-cell row, FILLERS.md COMPLETE sed, qualifier-mediated group/pidfile drain) PLUS:
#   FILLER_DRYRUN=1 FILLER_DRYRUN_DIR=DIR  the keeper's dry run: the SAME launcher, engine, region-lock claim and job on
#       the real lane under a real short grants/<id>.grant; .ended/.complete/stop file live in DIR so the real row id is
#       never consumed. The keeper stops the job via DIR/stop once the first unit of output is in result_path.
#   FILLER_OWNER / FILLER_EST_WALL_S (env, set by rowflow arm) replace the FILLERS.md owner/duration lookup in .ended.
#   --requires-tool / --qual-interpreter are accepted and ignored (v14 launchers keep working once repointed).
# Region-lock default is the host path (valid in every namespace); /workspace is a devcontainer-only symlink and a
# keeper-launched job never sees it (class-A launch failures 2026-11-01: `region-lock: No such file or directory`).
# --- original header (filler_run2.sh) ---
# filler_run2.sh = filler_run.sh + exclusive-GPU mode + precondition gate (2026-10-21, v11-drivers). filler_run.sh is left untouched (it is RUNNING).
#   NEW  --gpu-quiet shared|exclusive|none  claim mode of the region-lock wrapper. Default none for EVERY class (2026-11-03 session
#                                           review item 6: gpu-quiet is opt-in for decision-grade/quiet rows only; a gpu row left at
#                                           `none` runs on the MI210 beside other work under the 2026-10-22 co-residency policy).
#   NEW  --role ROLE                        region-lock --role (default build; timing items use bench).
#   NEW  --no-fold-siblings                 gpu class: claim gpu-quiet only, no CPU region (host threads tasksetted by the job); cpu class: region-lock --no-fold-siblings
#   NEW  --claim-cpus LIST                  region-lock --cpu-list override (default = grant cpus). Timing items: 0-95. With --gpu-quiet exclusive on a
#                                           gpu-class grant the default is 0-95 + role bench (the whole quiet host, as lib.sh/gpu_champion_ab require);
#                                           the JOB still sees FILLER_CPUS = the grant's host threads (184-191).
#   NEW  --precond-cmd 'CMD'                rc!=0 -> .ended rc=5 reason=build-missing:<first line of CMD stdout>; grant deleted, nothing launched.
#                                           Checked at grant time (after the window/port checks), so a poller can be armed before its builds exist.
# Generic grant-polling FILLER launcher (shell only, no LLM). Generalises ct18-run-20261021/filler_{worker,arch}.sh.
# Protocol: /workspace/docs/guides/agent-workflows/compute-fillers.md ; registry /mnt/raid0/llm/tmp/compute-flags/FILLERS.md
# Usage:
#   filler_run.sh --id ID --class cpu|gpu|cpu+gpu --cmd 'JOB COMMAND' --min-window SECONDS --stop STOPFILE
#                 [--complete-cmd 'CHECK (rc0 = all done)'] [--port P[,P2]] [--sched-port P[,P2]]
#                 [--excl-lock FILE] [--self-claim] [--gpu-threads 184-191] [--workdir DIR]
#   --port        ports the JOB's own servers will bind: launcher refuses (.ended rc=4) if any already LISTENs.
#   --sched-port  ports of the scheduled runner for the same results file: refuse rc=4 if listening.
#   --self-claim  the JOB takes its own region-lock claim (e.g. cs47 latency.sh): launcher adds NO region-lock/GPU claim;
#                 job sees FILLER_END_ISO (grant end) for its --deadline. Job rc (75 claim timeout, 124 end...) lands in .ended.
#   --excl-lock   per-arm runner lock of the scheduled runner: refuse rc=4 if it is held (flock -n probe).
# Grant regions: cpu -> qN list or cpu-list; gpu -> must name mi210_0, digits = host threads (default --gpu-threads);
#   cpu+gpu -> mi210_0 plus qN/cpu-list for the CPU part.
# Job contract (exported into the job): FILLER_ID FILLER_END(epoch hard end) FILLER_DEADLINE(epoch, END-90: start no new item)
#   FILLER_STOPFILE FILLER_CPUS FILLER_THREADS(physical cores) FILLER_PORTS FILLER_PIDFILE(append server PIDs we spawned)
#   FILLER_LIB (source it: fl_wait_own_port PORT PID [maxsecs] proves OUR pid owns the port + /health).
#   Job must be resumable and honour FILLER_STOPFILE / FILLER_DEADLINE between items.
# Mid-job STOP (2026-11-05, keeper-friction-review refinement 4): the launcher polls --stop every 3 s while the job runs;
#   on STOP it TERMs the job's setsid group (region-lock child, inner engine group and every member), KILLs after
#   --stop-grace S (default ${FILLER_STOP_GRACE_S:-60}; not in a dry run: the keeper's harness owns that stop and its
#   600 s truncation warning), verifies the groups are gone, writes .ended rc=75 reason=stopped (grant released; the region-lock dies
#   with its group, so its claim is released) and exits. A STOP present when a grant arrives writes a terminal
#   .ended rc=75 reason=stopped-before-start (it used to release the grant silently and be re-granted every tick, F4).
# Test overrides (env): FILLER_RL FILLER_GRANTS_DIR FILLER_FLAGS_DIR FILLERS_MD FILLER_POLL FILLER_STATE_DIR FILLER_STUB_CMD FILLER_GPU_LOCK
set -uo pipefail
HERE=$(dirname "$(readlink -f "$0")")
SELF=$(readlink -f "$0")
ID=""; CLASS=""; JOBCMD=""; MINWIN=0; STOPFILE=""; COMPLETE_CMD=""; PORTS=""; SCHED_PORTS=""; EXCL_LOCK=""; GPUTHR="184-191"; WORKDIR=/workspace; SELFCLAIM=0; GPUQ=""; ROLE=""; CLAIM_CPUS=""; PRECOND_CMD=""; STOP_GRACE=""; REPEAT=0; NOFOLD=0; REQUIRES_TOOLS=(); QUAL_INTERPRETER=""
if [ "${1:-}" = "--inner" ]; then INNER=1; shift; else INNER=0; fi
while [ $# -gt 0 ]; do
  case $1 in
    --id) ID=$2; shift 2;; --class) CLASS=$2; shift 2;; --cmd) JOBCMD=$2; shift 2;; --min-window) MINWIN=$2; shift 2;;
    --stop) STOPFILE=$2; shift 2;; --complete-cmd) COMPLETE_CMD=$2; shift 2;; --port) PORTS=$2; shift 2;;
    --sched-port) SCHED_PORTS=$2; shift 2;; --excl-lock) EXCL_LOCK=$2; shift 2;; --gpu-threads) GPUTHR=$2; shift 2;; --self-claim) SELFCLAIM=1; shift;;
    --workdir) WORKDIR=$2; shift 2;;
    --requires-tool) REQUIRES_TOOLS+=("$2"); shift 2;; --qual-interpreter) QUAL_INTERPRETER=$2; shift 2;;
    --gpu-quiet) GPUQ=$2; shift 2;; --role) ROLE=$2; shift 2;; --claim-cpus) CLAIM_CPUS=$2; shift 2;; --precond-cmd) PRECOND_CMD=$2; shift 2;; --stop-grace) STOP_GRACE=$2; shift 2;; --repeat) REPEAT=1; shift;; --no-fold-siblings) NOFOLD=1; shift;; *) echo "unknown arg $1" >&2; exit 64;;
  esac
done
[ -n "$ID" ] && [ -n "$JOBCMD" ] && [ -n "$STOPFILE" ] || { echo "need --id --cmd --stop" >&2; exit 64; }
# A missing completion predicate cannot consume a grant or become a false rc1.
[ "$INNER" = 1 ] || [ -n "$COMPLETE_CMD" ] || { echo "REFUSED: --complete-cmd required" >&2; exit 65; }
[ -d "$WORKDIR" ] || { echo "REFUSED: workdir $WORKDIR absent in exec namespace" >&2; exit 65; }
case $CLASS in cpu|gpu|cpu+gpu) ;; *) echo "bad --class" >&2; exit 64;; esac
case "$GPUQ" in ""|shared|exclusive|none) ;; *) echo "bad --gpu-quiet (shared|exclusive|none)" >&2; exit 64;; esac
# filler_run8 (2026-10-22): a CPU timing job that needs the GPU quiet is --class cpu --gpu-quiet exclusive --claim-cpus LIST.
# run7 refused it and the cpu+gpu workaround then refused workspace-58's CPU-only "0-95" grant (no mi210_0 token) -> slot lost 19:28Z.
[ "$GPUQ" = exclusive ] && [ "$CLASS" = cpu ] && [ -z "$CLAIM_CPUS" ] && { echo "--class cpu --gpu-quiet exclusive needs --claim-cpus LIST" >&2; exit 64; }
# filler_run7 (2026-10-22): a gpu-class exclusive claim used to silently default to a whole-host 0-95 CPU claim. Be explicit.
if [ "$CLASS" = gpu ] && [ "$GPUQ" = exclusive ] && [ -z "$CLAIM_CPUS" ] && [ $NOFOLD = 0 ]; then
  echo "filler_run7: --class gpu --gpu-quiet exclusive needs --claim-cpus LIST (whole-host timing jobs: --claim-cpus 0-95) or --no-fold-siblings (GPU-only claim, no CPU region); refusing to default to 0-95" >&2; exit 64
fi
[[ ${STOP_GRACE:-0} =~ ^[0-9]+$ ]] || { echo "bad --stop-grace (seconds)" >&2; exit 64; }
if [ -n "$CLAIM_CPUS" ] && ! [[ $CLAIM_CPUS =~ ^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$ ]]; then echo "bad --claim-cpus" >&2; exit 64; fi

FLAGS=${FILLER_FLAGS_DIR:-/mnt/raid0/llm/tmp/compute-flags}
GRANTS=${FILLER_GRANTS_DIR:-$FLAGS/grants}
FILLERS_MD=${FILLERS_MD:-$FLAGS/FILLERS.md}
POLL=${FILLER_POLL:-5}   # ws58 2026-11-02: a granted quarter starts within seconds, not 45 s
STATE=${FILLER_STATE_DIR:-$HERE/state}
GPU_LOCK=${FILLER_GPU_LOCK:-/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock}
RL=${FILLER_RL:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}
mkdir -p "$STATE"
LAUNCHER_LOCK=$STATE/$ID.launcher.lock
RUNNER_LOCK=$STATE/$ID.runner.lock
PIDFILE=$STATE/$ID.pids
GRANT=$GRANTS/$ID.grant; ENDED=$GRANTS/$ID.ended; COMPLETE=$GRANTS/$ID.complete
DRYRUN=${FILLER_DRYRUN:-0}
if [ "$DRYRUN" = 1 ]; then
  # keeper-hotfix 2026-11-05 (D10): a dry run derives its whole world from FILLER_DRYRUN_DIR (the one name that survives a
  # `sudo --preserve-env` list); it can never fall back to the MAIN grants dir and poll it forever.
  DR=${FILLER_DRYRUN_DIR:-}
  [ -n "$DR" ] || { echo "REFUSED: FILLER_DRYRUN=1 needs FILLER_DRYRUN_DIR (dryrun-env-incomplete)" >&2; exit 64; }
  GRANTS=$DR/grants; FLAGS=$(dirname "$(dirname "$DR")"); GRANT=$GRANTS/$ID.grant
  if [ ! -d "$GRANTS" ]; then
    printf 'rc=64 time=%s reason=dryrun-env-incomplete\n' "$(date -u +%FT%TZ)" > "$DR/ended" 2>/dev/null
    echo "REFUSED: dry-run grants dir $GRANTS absent (dryrun-env-incomplete)" >&2; exit 64
  fi
  mkdir -p "$DR/state"
  ENDED=$DR/ended; COMPLETE=$DR/complete; STOPFILE=$DR/stop; STATE=$DR/state; REPEAT=0
  LAUNCHER_LOCK=$STATE/$ID.launcher.lock; RUNNER_LOCK=$STATE/$ID.runner.lock; PIDFILE=$STATE/$ID.pids
  # allocator 2026-11-01: a multi-quarter row is dry-run on ONE quarter - the region-lock claim is the grant's own cpus
  # (gpu class: its host threads, folding onto q3), so a dry run never holds more than it needs.
  if [ "${FILLER_DRYRUN_ONE_QUARTER:-0}" = 1 ]; then if [ "$CLASS" = gpu ]; then CLAIM_CPUS=$GPUTHR; else CLAIM_CPUS=""; GPUQ=none; fi; fi  # quiet-host rows: plumbing only
  # ws58 2026-11-02: publish_row's smoke (FILLER_SMOKE=1) is always small and must NEVER wait on a held region (a real
  # whole-host run held q0 and every smoke blocked on its full 0-95 claim). Its claim is exactly the smoke's cpus
  # (WS58_REGIONS), taken by taskset, not region-lock; it never takes gpu-quiet exclusive (gpu rows: shared gpu lock only).
  SMOKE_NOLOCK=0
  if [ "${FILLER_SMOKE:-0}" = 1 ]; then
    SMOKE_NOLOCK=1; CLAIM_CPUS=${WS58_REGIONS:-$CLAIM_CPUS}; NOFOLD=0
    if [ "$CLASS" = gpu ]; then GPUQ=shared; else GPUQ=none; fi
  fi
fi
STOP_GRACE=${STOP_GRACE:-${FILLER_STOP_GRACE_S:-60}}
ts() { date -u +%FT%TZ; }
log() { echo "$(ts) [$ID] $*"; }

# ------------------------------------------------------------------ GPU fence (operator 2026-11-05 "fix it")
# A grant that does NOT hold the GPU token (no mi210_0 region, no gpu-quiet in holds=, no --gpu-quiet claim) runs its
# whole process tree fenced off the MI210: device-visibility env hides it from HIP/ROCr, and an LD_PRELOAD shim refuses
# open(/dev/kfd, /dev/dri/{renderD,card}*) - the env alone still opens KFD (measured: hipGetDeviceCount=0 yet a
# /sys/class/kfd/kfd/proc/<pid> entry with a per-device context). Origin: codex3-cs8-stt5 r3/r4 (lane cpu) ran the HIP
# whisper-cli every ~7 s from a Python job and wrecked the exclusive kvu16g2-ab twice; launcher argv cannot see that.
# HIP builds fall back to CPU (whisper-cli: "no GPU found" -> CPU; llama.cpp: "no ROCm-capable device", 0 GPU devices).
# Rows WITH the token are unchanged. The keeper's GPU-FENCE-BREACH sampler is the safety net for a bypassed fence.
FENCE_DIR=${FILLER_FENCE_DIR:-$HERE/state}
gpu_fence_so() { # prints the path of the compiled shim (cached by source hash); empty when no compiler is available
  local src h so tmp
  src=$(cat <<'CSRC'
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <string.h>
#include <sys/types.h>
static int fenced(const char *p){ return p && (!strcmp(p,"/dev/kfd") || !strncmp(p,"/dev/dri/renderD",16) || !strncmp(p,"/dev/dri/card",13)); }
#define W(N, PRE, CALL) int N PRE { static int (*r)(); if(!r) r=(int(*)())dlsym(RTLD_NEXT,#N); mode_t m=0; \
  if(f&(O_CREAT|O_TMPFILE)){va_list a; va_start(a,f); m=(mode_t)va_arg(a,int); va_end(a);} \
  if(fenced(p)){errno=EACCES; return -1;} return CALL; }
W(open, (const char *p, int f, ...), r(p,f,m))
W(open64, (const char *p, int f, ...), r(p,f,m))
W(openat, (int d, const char *p, int f, ...), r(d,p,f,m))
W(openat64, (int d, const char *p, int f, ...), r(d,p,f,m))
CSRC
)
  h=$(printf '%s' "$src" | sha256sum | cut -c1-12); so=$FENCE_DIR/gpu_fence-$h.so
  if [ ! -s "$so" ]; then
    command -v gcc >/dev/null 2>&1 || return 0
    mkdir -p "$FENCE_DIR"; tmp=$so.part.$$
    printf '%s\n' "$src" | gcc -x c -std=gnu99 -shared -fPIC -O2 -o "$tmp" - -ldl 2>/dev/null && mv -f "$tmp" "$so" || { rm -f "$tmp"; return 0; }
  fi
  echo "$so"
}
# GPU-FENCE-VACUOUS (operator 2026-11-05): under the fence `test-backend-ops -b ROCm0` finds no backend, prints
# "Backend 1/1: CPU / Skipping", "1/1 backends passed", OK and exits 0 - a pass that tested nothing. After a FENCED job the
# engine scans its output (tee'd copy + *.log/*.out/*.txt the job wrote under --workdir) for test-backend-ops' own markers
# (tests/test-backend-ops.cpp console printer): a "Testing N devices" run with no "  Backend <name>: OK|FAIL" status line,
# "Testing 0 devices", or "  0/0 tests passed". A hit fails the run with rc=$VACUOUS_RC (not 0, not 75).
VACUOUS_RC=78
gpu_vacuous_scan() { # files... ; prints the reason and returns 0 on a vacuous GPU test
  awk '{ gsub(/\033\[[0-9;]*m/, "") }
       /^Testing [0-9]+ devices/ { if (open && !st) { why = "test-backend-ops tested 0 backends (every backend skipped/not found)" }
                                   open = 1; st = 0; if ($2 == 0) why = "test-backend-ops: Testing 0 devices" ; next }
       open && /^  Backend [^ ]+: (OK|FAIL)/ { st++ }
       open && /^[0-9]+\/[0-9]+ backends passed/ { if (!st && why == "") why = "test-backend-ops tested 0 backends (every backend skipped/not found): " $0; open = 0 }
       /^ +0\/0 tests passed/ { if (why == "") why = "test-backend-ops ran 0 cases (0/0 tests passed)" }
       END { if (open && !st && why == "") why = "test-backend-ops tested 0 backends (run ended before any backend status)"
             if (why != "") { print why; exit 0 } exit 1 }' "$@" 2>/dev/null
}
gpu_vacuous_check() { # after a fenced job: 0 = vacuous (VAC_WHY set)
  [ "${FENCE_ON:-0}" = 1 ] || return 1
  local files=() f
  [ -s "$STATE/$ID.fenced-job.out" ] && files+=("$STATE/$ID.fenced-job.out")
  if [ -n "$WORKDIR" ] && [ "$WORKDIR" != /workspace ] && [ -n "${VAC_STAMP:-}" ]; then
    while IFS= read -r f; do files+=("$f"); done < <(find "$WORKDIR" -maxdepth 3 -type f \( -name '*.log' -o -name '*.out' -o -name '*.txt' \) \
        -newer "$VAC_STAMP" -size -64M 2>/dev/null | awk 'NR<=200')
  fi
  [ ${#files[@]} -gt 0 ] || return 1
  VAC_WHY=$(for f in "${files[@]}"; do gpu_vacuous_scan "$f" && { echo " [$f]"; break; }; done | tr -d '\n')
  [ -n "$VAC_WHY" ]
}
holds_gpu_token() { # $1 = grant file; NEEDGPU / GPUQ already set
  [ "${NEEDGPU:-0}" = 1 ] && return 0
  case ${GPUQ:-} in shared|exclusive) return 0;; esac
  local h; h=$(sed -n 's/.*holds=\([^ ]*\).*/\1/p' "$1" 2>/dev/null) || true
  [[ ",$h," == *",gpu-quiet,"* ]]
}
FENCE_ENV=()
set_gpu_fence() { # fills FENCE_ENV (an `env ...` prefix) for a grant without the GPU token; empty otherwise
  FENCE_ENV=()
  FENCE_ON=0
  if holds_gpu_token "$GRANT"; then export FILLER_GPU_FENCE=0; return; fi
  FENCE_ON=1; mkdir -p "$STATE"; rm -f "$STATE/$ID.fenced-job.out"; VAC_STAMP=$STATE/$ID.fenced-job.start; : > "$VAC_STAMP"
  local so pre; so=$(gpu_fence_so)
  FENCE_ENV=(env FILLER_GPU_FENCE=1 ROCR_VISIBLE_DEVICES= HIP_VISIBLE_DEVICES=-1 GPU_DEVICE_ORDINAL=-1 CUDA_VISIBLE_DEVICES=-1
             GGML_VK_VISIBLE_DEVICES=-1 HSA_ENABLE_SDMA=0)
  if [ -n "$so" ]; then pre="$so${LD_PRELOAD:+ $LD_PRELOAD}"; FENCE_ENV+=(LD_PRELOAD="$pre")
  else log "WARN gpu-fence: no compiler for the /dev/kfd shim; env fence only (keeper GPU-FENCE-BREACH sampler is the net)"; fi
  log "GPU-FENCE on: grant holds no GPU token (${so:-env-only})"
}
epoch() { date -u -d "$1" +%s 2>/dev/null; }
listening() { ss -ltn "sport = :$1" 2>/dev/null | grep LISTEN >/dev/null; }
any_listening() { local p; for p in ${1//,/ }; do listening "$p" && { echo "$p"; return 0; }; done; return 1; }

expand() { local t a b; IFS=, read -ra T <<<"$1"; for t in "${T[@]}"; do case $t in *-*) a=${t%-*}; b=${t#*-}; seq "$a" "$b";; *) echo "$t";; esac; done; }
valid_list() { [[ $1 =~ ^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$ ]] && ! expand "$1" | awk '$1>191{f=1} END{exit !f}'; }
phys_count() { expand "$1" | awk '{print $1%96}' | sort -un | wc -l; }

parse_regions() { # sets CPUS THREADS NEEDGPU
  local tok qs="" list="" gpu=0 n a b s e parts=""
  IFS=, read -ra TK <<<"${1//;/,}"
  for tok in "${TK[@]}"; do
    case $tok in mi210_0) gpu=1;; q[0-3]) qs="$qs ${tok#q}";; [0-9]*) list="${list:+$list,}$tok";; *) ;; esac
  done
  NEEDGPU=0; CPUS=""
  case $CLASS in
    cpu) [ $gpu = 0 ] || return 1
      if [ -n "$list" ]; then CPUS=$list
      elif [ -n "$qs" ]; then
        for n in $qs; do a=$((n*24)); b=$((a+23)); s=$((a+96)); e=$((s+15)); parts="${parts:+$parts,}$a-$b,$s-$e"; done; CPUS=$parts
      else return 1; fi;;
    gpu) [ $gpu = 1 ] || return 1; NEEDGPU=1; CPUS=${list:-$GPUTHR};;
    cpu+gpu) [ $gpu = 1 ] || return 1; NEEDGPU=1
      if [ -n "$list" ]; then CPUS=$list
      elif [ -n "$qs" ]; then
        for n in $qs; do a=$((n*24)); b=$((a+23)); s=$((a+96)); e=$((s+15)); parts="${parts:+$parts,}$a-$b,$s-$e"; done; CPUS=$parts
      else return 1; fi;;
  esac
  valid_list "$CPUS" || return 1
  if [ $CLASS = gpu ]; then THREADS=$(expand "$CPUS" | sort -un | wc -l); else THREADS=$(phys_count "$CPUS"); fi
}

# VB-CAL-OVERRUN-WRITE: snapshot native duration at launch; never substitute
# min-window/grant length. Composite/ranged/missing estimates stay unchecked.
snapshot_overrun() {  # v15: owner/estimate come from the row (rowflow arm exports them); no FILLERS.md lookup
  OV_OWNER=${FILLER_OWNER:-}; OV_EST=${FILLER_EST_WALL_S:-}; OV_REGIONS=$1
}

write_ended() { # rc reason
  LM_RESULT=$1
  local ov_started=${OV_STARTED:-} ov_owner=${OV_OWNER:-} ov_est=${OV_EST:-} ov_regions=${OV_REGIONS:-}
  # Consume before any I/O: a later TERM/unstarted repeat cannot reuse it.
  OV_STARTED=""; OV_OWNER=""; OV_EST=""; OV_REGIONS=""
  mkdir -p "$GRANTS"
  [ ! -e "$ENDED" ] || { log "REFUSED: .ended already exists; use a new row id"; return 66; }
  {
    printf 'rc=%s time=%s reason=%s\n' "$1" "$(ts)" "$2"
    if [ -n "$ov_started" ] && [ -n "$ov_est" ]; then
      printf 'job_id=%s\nowner=%s\nstep=job-run\nestimated_wall_s=%s\nstarted=%s\nregions=%s\n' \
        "$ID" "$ov_owner" "$ov_est" "$ov_started" "$ov_regions"
    fi
  } > "$ENDED.tmp"
  ln "$ENDED.tmp" "$ENDED" || { rm -f "$ENDED.tmp"; log "REFUSED: .ended race; use a new id"; return 66; }
  rm -f "$ENDED.tmp"
  rm -f "$GRANT"
  log "ended rc=$1 reason=$2 (grant deleted)"
  # 2026-11-07 (coordinator: a build row left a ROOT-owned mode-555 tree of ~42 GB that trash-sweep could not delete):
  # at row end the job dir must be reclaimable by the keeper's uid. Modes we own are repaired here (best effort, never
  # fatal); a foreign-uid residue is logged with the exact chown so the janitor's OWNER step and the operator see it.
  case "${WORKDIR:-}" in /mnt/raid0/llm/tmp/*) if [ -d "$WORKDIR" ]; then
    chmod -R u+rwX "$WORKDIR" 2>/dev/null || true
    foreign=$(find "$WORKDIR" -maxdepth 3 ! -user "$(id -un)" -print -quit 2>/dev/null || true)
    [ -z "$foreign" ] || log "OWNER-RESIDUE: $foreign is not owned by $(id -un); fix: sudo chown -R $(id -u):$(id -g) $WORKDIR"
  fi;; esac   # only a job dir under tmp/ (never the default /workspace)
  notify_end "$1" "$2"
}
# 2026-11-04 incident (disk-floor kill, nobody told for 3 h): push every terminal event to the row owner (session bus)
# and rowflow-alerts.jsonl. Idempotent, best effort, never changes the caller's rc. Dry runs report via rowflow FAIL.
notify_end() { # rc reason
  [ "$DRYRUN" = 1 ] && return 0
  [ -f "$HERE/notify.py" ] || { log "WARN: $HERE/notify.py missing; terminal event NOT pushed"; return 0; }
  local ef=()
  [ -e "$ENDED" ] && ef=(--ended-file "$ENDED")
  ROWFLOW_FLAGS="$FLAGS" timeout 60 python3 -I "$HERE/notify.py" --flags "$FLAGS" row-ended --id "$ID" \
    --rc "$1" --reason "$2" ${FILLER_OWNER:+--owner "$FILLER_OWNER"} "${ef[@]}" </dev/null 7>&- 8>&- || log "WARN: notify rc=$?"
  return 0
}
# keeper-hotfix 2026-11-05: liveness by ps//proc (kill -0 is blind in this sandbox); a zombie is dead
alive_pid() { local st; st=$(ps -o stat= -p "$1" 2>/dev/null) || return 1; [ -n "$st" ] && [[ $st != Z* ]]; }
group_pids() { [[ ${1:-} =~ ^[0-9]+$ ]] || return 0; ps -eo pid=,pgid=,sid=,stat= 2>/dev/null | awk -v g="$1" '($2==g || $3==g) && $4 !~ /^Z/ {print $1}'; }
gone() { [ -z "$(group_pids "$1")" ]; }
proc_birth() { sed 's/.*) //' "/proc/$1/stat" 2>/dev/null | awk '{print $20}'; }
kill_group() { # captured pgid + birth [grace s, default 20]: TERM, wait, KILL - only when the leader's birth still matches
  local g=$1 birth=$2 grace=${3:-20} i
  gone "$g" && return 0
  [ -n "$birth" ] || { log "REFUSED: live group $g has no captured birth"; return 1; }
  [ "$(proc_birth "$g")" = "$birth" ] || { log "group leader $g birth changed (pid reused); not signalling"; return 0; }
  kill -TERM -- "-$g" 2>/dev/null
  for i in $(seq "$grace"); do gone "$g" && { log "group $g ended after TERM"; return 0; }; sleep 1 7>&- 8>&-; done
  kill -KILL -- "-$g" 2>/dev/null; sleep 1
  gone "$g" && { log "group $g killed"; return 0; }
  log "REFUSED: group $g survives KILL"; return 1
}
INNERPG=$STATE/$ID.inner.pgid
descendants() { # every live descendant of the given pids (and the pids themselves), from one ps snapshot
  ps -eo pid=,ppid=,stat= 2>/dev/null | awk -v roots="$*" '
    BEGIN { n = split(roots, r, " "); for (i = 1; i <= n; i++) if (r[i] != "") want[r[i]] = 1 }
    $3 !~ /^Z/ { par[$1] = $2; all[++m] = $1 }
    END { do { ch = 0; for (i = 1; i <= m; i++) { p = all[i]; if (!(p in want) && (par[p] in want)) { want[p] = 1; ch = 1 } } } while (ch)
          for (p in want) if (p in par) print p }'
}
tagged_pids() { # orphans of THIS run (reparented away from the tree) still carry its FILLER_ID + FILLER_STOPFILE
  local f p e
  for f in /proc/[0-9]*/environ; do
    p=${f#/proc/}; p=${p%/environ}
    [ "$p" = $$ ] && continue
    e=$'\n'$(tr '\0' '\n' 2>/dev/null < "$f")$'\n' || continue   # 2> before < (a denied /proc/N/environ spammed ~2000 lines per run into job logs: yarn OUTPUT-PAUSE 2026-11-05); no pipes into grep -q
    [[ $e == *$'\n'"FILLER_ID=$ID"$'\n'* && $e == *$'\n'"FILLER_STOPFILE=$STOPFILE"$'\n'* ]] && echo "$p"
  done
}
job_pids() { # keeper-hotfix 2026-11-05: the launcher's setsid group, the inner engine's group, every descendant
  # (setsid/nohup grandchildren included) and orphans tagged with this run's env - never this launcher itself
  local roots="" g b
  [ -n "$CUR" ] && roots="$(group_pids "$CUR") $CUR"
  if [ -f "$INNERPG" ]; then read -r g b < "$INNERPG" || true; roots="$roots $(group_pids "${g:-}")"; fi
  roots="$roots $(tagged_pids)"
  [ -n "${roots// /}" ] || return 0
  descendants $roots | grep -vx "$$" | sort -un
}
kill_job() { # TERM the whole run, wait up to the grace, KILL, verify by ps; returns 1 if anything survives
  local grace=${1:-20} i pids
  pids=$(job_pids)
  [ -n "$pids" ] || { rm -f "$INNERPG"; return 0; }
  kill -CONT $pids 2>/dev/null   # disk-pause (2026-11-07): a SIGSTOPped group never handles TERM
  kill -TERM $pids 2>/dev/null
  for i in $(seq "$grace"); do
    pids=$(job_pids); [ -n "$pids" ] || { log "run ended after TERM"; rm -f "$INNERPG"; return 0; }
    kill -CONT $pids 2>/dev/null; kill -TERM $pids 2>/dev/null; sleep 1 7>&- 8>&-
  done
  kill -KILL $pids 2>/dev/null; sleep 1
  pids=$(job_pids); [ -n "$pids" ] || { log "run killed"; rm -f "$INNERPG"; return 0; }
  kill -KILL $pids 2>/dev/null; sleep 1
  pids=$(job_pids); [ -n "$pids" ] || { log "run killed"; rm -f "$INNERPG"; return 0; }
  log "REFUSED: pids survive KILL: $(echo $pids)"; return 1
}
kill_pidfile() { # pids the job registered (fl_register_pid); TERM then KILL; never a pid that is already gone
  local p
  [ -f "$PIDFILE" ] || return 0
  while read -r p _; do
    [[ $p =~ ^[0-9]+$ ]] || continue
    ps -o pid= -p "$p" >/dev/null 2>&1 || continue
    kill -TERM "$p" 2>/dev/null; sleep 2; ps -o pid= -p "$p" >/dev/null 2>&1 && kill -KILL "$p" 2>/dev/null
  done < "$PIDFILE"
  return 0
}
# operator 2026-11-06 "Yes, both" (ak-asm-t1-harness-r3-20261106-r2: a docker container started by the job survived the row's
# STOP, held 0.8 GB of MI210 VRAM and overlapped the next timing row). Containers started UNDER a row are labelled by a
# `docker` shim the job gets first on PATH (label epyc.filler.row=<ID>); on every end path the launcher stops and removes
# the containers carrying THAT label, and only those - never a container the row did not start.
DOCKER_LABEL="epyc.filler.row"
docker_bin() { [ -n "${FILLER_DOCKER_BIN:-}" ] && { echo "$FILLER_DOCKER_BIN"; return; }; command -v docker 2>/dev/null; }
DOCKER_USED="$STATE/$ID.dockershim/used"   # touched by the shim the first time the job runs/creates a container
row_containers() { local d; d=$(docker_bin) || return 0; [ -n "$d" ] || return 0
  timeout 20 "$d" ps -aq --no-trunc --filter "label=$DOCKER_LABEL=$ID" 2>/dev/null; }
kill_containers() { # stop (TERM, 10 s, then KILL) + rm the containers this row started; returns 1 if one survives
  local d ids c left; d=$(docker_bin) || return 0; [ -n "$d" ] || return 0
  [ -e "$DOCKER_USED" ] || return 0   # the job never ran `docker run|create`: do not even ask the daemon (it can hang)
  ids=$(row_containers); [ -n "$ids" ] || { rm -f "$DOCKER_USED"; return 0; }
  for c in $ids; do
    log "docker: stopping container ${c:0:12} started under $ID"
    timeout 60 "$d" stop -t 10 "$c" >/dev/null 2>&1
    timeout 60 "$d" rm -f "$c" >/dev/null 2>&1   # a --rm container is already gone: the failure is harmless
  done
  left=$(row_containers); [ -z "$left" ] && { rm -f "$DOCKER_USED"; log "docker: row containers stopped"; return 0; }
  log "REFUSED: row container(s) survive stop+rm: $(echo $left | cut -c1-80)"; return 1
}
install_docker_shim() { # inner: put a labelling `docker` first on PATH for the job (no real docker -> nothing)
  local real shim; real=$(docker_bin) || return 0; [ -n "$real" ] || return 0
  shim="$STATE/$ID.dockershim"; mkdir -p "$shim"
  cat > "$shim/docker" <<SHIM
#!/bin/bash
real=$(printf '%q' "$real")
a=("\$@"); n=0
[ "\${a[0]:-}" = container ] && n=1
case "\${a[\$n]:-}" in
  run|create) : > "$shim/used"; exec "\$real" "\${a[@]:0:\$((n+1))}" --label "$DOCKER_LABEL=$ID" "\${a[@]:\$((n+1))}";;
esac
exec "\$real" "\$@"
SHIM
  chmod 0755 "$shim/docker"; export PATH="$shim:$PATH"
}
is_complete() { [ -n "$COMPLETE_CMD" ] || return 1; ( cd "$WORKDIR" && bash -c "$COMPLETE_CMD" ) >/dev/null 2>&1; }
mark_complete() {
  kill_pidfile || { log "REFUSED: completion while native child unverified"; return 70; }
  mkdir -p "$GRANTS"
  write_ended 0 complete || return 70
  printf 'complete time=%s id=%s\n' "$(ts)" "$ID" > "$COMPLETE"
  log "ALL DONE: wrote $COMPLETE, row marked COMPLETE; exiting for good"
}

# ------------------------------------------------------------------ inner (inside the region-lock claim)
if [ $INNER = 1 ]; then
  END=$FILLER_END
  [ $(( END - $(date -u +%s) )) -le 120 ] && { echo "no time left"; exit 3; }
  if p=$(any_listening "$PORTS"); then echo "port $p already in use"; exit 4; fi
  if [ "${FILLER_NEEDGPU:-0}" = 1 ]; then
    exec 9>"$GPU_LOCK"
    flock -w $(( END - $(date -u +%s) - 60 )) 9 || { echo "GPU flock busy"; exit 9; }
    echo "$(ts) mi210_0 flock held"
  fi
  export FILLER_END_ISO=$(date -u -d "@$END" +%FT%TZ) FILLER_ID=$ID FILLER_DEADLINE=$(( END - 90 )) FILLER_STOPFILE=$STOPFILE FILLER_PORTS=$PORTS FILLER_PIDFILE=$PIDFILE FILLER_LIB=$HERE/filler_lib.sh
  mkdir -p "$STATE"; _pg=$(ps -o pgid= -p $$ | tr -d ' '); printf '%s %s\n' "$_pg" "$(proc_birth "$_pg")" > "$INNERPG"
  install_docker_shim
  cd "$WORKDIR" || exit 3
  # No `timeout` wrapper: it moves the job into its own process group, out of reach of the launcher's captured-group kill.
  # The hard end is enforced by the launcher (TERM, wait, KILL on the whole setsid group); the job also honours FILLER_DEADLINE.
  if [ "${FILLER_GPU_FENCE:-0}" = 1 ]; then   # GPU-FENCE-VACUOUS: keep a copy of the fenced job's output for the scan
    taskset -c "$FILLER_CPUS" bash -c "$JOBCMD" 8>&- 9>&- 2>&1 | tee -a "$STATE/$ID.fenced-job.out"
    rc=${PIPESTATUS[0]}
  else
    taskset -c "$FILLER_CPUS" bash -c "$JOBCMD" 8>&- 9>&-
    rc=$?
  fi
  echo "job rc=$rc"
  exit $rc
fi


# ------------------------------------------------------------------ launcher (poll loop; shell only)
mkdir -p "$GRANTS"
exec 7>"$LAUNCHER_LOCK"
flock -n 7 || { log "another launcher for $ID already running; exiting"; exit 0; }
CUR=""; CUR_BIRTH=""; STARTED_ONE=0
sleep_poll() { sleep "$1" 7>&- 8>&- & SLP=$!; wait $SLP 2>/dev/null; }
on_term() {
  log "launcher signalled"
  if [ -n "$CUR" ]; then
    kill_job && kill_pidfile && kill_containers || { log "REFUSED: signal cleanup incomplete; grant retained"; exit 70; }
  fi
  [ -e "$GRANT" ] && write_ended 143 launcher-signalled
  exit 143
}
trap on_term TERM INT

run_one() {
  local regions start end s e now rc reason p
  OV_STARTED=""; OV_OWNER=""; OV_EST=""; OV_REGIONS=""
  regions=$(sed -n 's/.*regions=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  start=$(sed -n 's/.*start=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  end=$(sed -n 's/.*end=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  s=$(epoch "$start"); e=$(epoch "$end")
  if [ -z "$regions" ] || [ -z "$s" ] || [ -z "$e" ] || [ "$s" -ge "$e" ]; then write_ended 2 "malformed-grant"; return; fi
  # CTC-Q-G: a running sibling (runner lock held elsewhere) owns this grant: never write .ended / delete it.
  if ! ( exec 5>>"$RUNNER_LOCK"; flock -n 5 ) 2>/dev/null; then
    log "runner lock held by a running sibling; leaving grant and .ended untouched"; GRANT_WAIT=$POLL; return 9
  fi
  now=$(date -u +%s)
  if [ "$now" -ge "$e" ]; then write_ended 3 "grant-expired-unrun"; return; fi
  if [ "$now" -lt "$s" ]; then GRANT_WAIT=$(( s - now )); return 9; fi
  # disk-pause (2026-11-07): no row STARTS while the host is paused for disk; the grant waits (logged once per pause)
  if [ "${FILLER_SMOKE:-0}" != 1 ] && [ -e "$FLAGS/disk-pause/PAUSED" ]; then
    [ "${_dp_wait:-0}" = 1 ] || { log "DISK-PAUSE: start deferred until free disk is back above the resume level"; _dp_wait=1; }
    GRANT_WAIT=$POLL; return 9
  fi
  _dp_wait=0
  [ ! -e "$ENDED" ] || { log "REFUSED: .ended exists; use new id"; return 66; }
  if ! parse_regions "$regions"; then write_ended 2 "regions-unusable-for-$ID($CLASS):$regions"; return; fi
  if [ $(( e - now )) -lt "$MINWIN" ]; then write_ended 3 "window-$(( e - now ))s-below-min-$MINWIN"; return; fi
  # 2026-11-03 session review item 7: a STOP file at grant time is RETRYABLE - the grant is released and the id stays
  # usable (the allocator shows the row as `held` and does not re-grant it while the STOP file exists); it used to write
  # .ended, which burned the id and left the poller spinning on "REFUSED: .ended exists" (85k lines).
  # 2026-11-05 (keeper-friction-review F4/refinement 4): that silent release was re-granted every tick (1,344 grants in
  # 16 h of one row whose stop path the keeper could not resolve). A STOP at grant time is now terminal and recorded.
  if [ -e "$STOPFILE" ]; then write_ended 75 stopped-before-start; log "STOP present before start ($STOPFILE): terminal; publish a new row id to run it"; return 21; fi
  if [ -n "$PRECOND_CMD" ]; then
    local pout prc; pout=$( cd "$WORKDIR" && bash -c "$PRECOND_CMD" 2>&1 ); prc=$?
    if [ $prc -ne 0 ]; then write_ended 5 "build-missing:$(printf '%s' "$pout" | head -n1 | tr -c '[:print:]' ' ' | cut -c1-160)"; return; fi
  fi
  if p=$(any_listening "$SCHED_PORTS"); then write_ended 4 "refused:scheduled-runner-port-$p-listening"; return; fi
  if p=$(any_listening "$PORTS"); then write_ended 4 "refused:own-port-$p-already-listening"; return; fi
  if [ -n "$EXCL_LOCK" ]; then
    ( exec 6>>"$EXCL_LOCK"; flock -n 6 ) || { write_ended 4 "refused:scheduled-runner-lock-held"; return; }
  fi
  exec 8>"$RUNNER_LOCK"
  if ! flock -n 8; then exec 8>&-; write_ended 4 "refused:runner-lock-held"; return; fi
  if is_complete; then
    exec 8>&-
    mark_complete || return 70
    return 20
  fi
  log "START regions=$regions cpus=$CPUS threads=$THREADS gpu=$NEEDGPU end=$end"
  export FILLER_END=$e FILLER_CPUS="$CPUS" FILLER_THREADS=$THREADS FILLER_NEEDGPU=$NEEDGPU
  rm -f "$PIDFILE"
  local rlargs
  local gq=$GPUQ cc=${CLAIM_CPUS:-} rl_role=${ROLE:-build}
  if [ "$gq" = exclusive ]; then
    [ -n "$cc" ] || cc=0-95
    [ -n "$ROLE" ] || rl_role=bench
  fi
  case $CLASS in
    cpu) rlargs=(--cpu-list "${cc:-$CPUS}"); [ -n "$gq" ] && [ "$gq" != none ] && rlargs+=(--gpu-quiet "$gq");;
    gpu) if [ "$gq" = exclusive ]; then rlargs=(--cpu-list "$cc" --gpu-quiet exclusive)
         elif [ -z "$gq" ] || [ "$gq" = none ]; then rlargs=()
         else rlargs=(--gpu-quiet "$gq"); [ -n "$cc" ] && rlargs=(--cpu-list "$cc" --gpu-quiet "$gq"); fi;;
    cpu+gpu) rlargs=(--cpu-list "${cc:-$CPUS}"); [ -n "$gq" ] && [ "$gq" != none ] && rlargs+=(--gpu-quiet "$gq");;
  esac
  # GRANT_CPUS (ws58 2026-11-02): a gpu-class grant locks ONLY the cpus the grant names (its cpus= field, else its
  # regions list): primary cpus (0-95) as an exact --cpu-list claim, SMT-sibling host threads (184-191) unlocked and
  # pinned by the inner taskset (FILLER_CPUS). --claim-cpus / --no-fold-siblings no longer widen a gpu claim: the
  # allocator booked gpu-quiet + exactly these cpus, so the GPU runs beside a whole-q3 / host row.
  local gcl="" gprim=""
  if [ "$CLASS" = gpu ]; then
    gcl=$(sed -n 's/.* cpus=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n'); valid_list "$gcl" || gcl=$CPUS
    gprim=$(expand "$gcl" | awk '$1<96' | sort -un | paste -sd, -)
    case $gq in exclusive|shared) rlargs=(--gpu-quiet "$gq");; *) rlargs=();; esac   # opt-in only (2026-11-03 item 6)
    [ -n "$gprim" ] && rlargs=(--cpu-list "$gprim" --no-fold-siblings "${rlargs[@]}")
  fi
  # CONTRACT_LOCK (keeper class fix 2026-11-05): a cpu / cpu+gpu grant carrying lock=LIST is the keeper's evidence
  # contract; the region-lock claim is exactly that list (it replaces --claim-cpus, which may name the whole host for a
  # 1-thread job). A grant without lock= keeps the claim above.
  local glk=""
  [ "$CLASS" != gpu ] && glk=$(sed -n 's/.* lock=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  if [ -n "$glk" ] && valid_list "$glk"; then
    rlargs=(--cpu-list "$glk"); [ -n "$gq" ] && [ "$gq" != none ] && rlargs+=(--gpu-quiet "$gq")
    CLAIM_CPUS=$glk; export FILLER_CPUS="$glk"
  fi
  # --no-fold-siblings (2026-10-22): a GPU job's host threads 184-191 must not fold into a whole-q3 claim (MI210 sat idle behind a q3 build)
  # filler_run6 (2026-10-22): region-lock REFUSES --no-fold-siblings for an SMT-only list ("maps to no regions"), so for a
  # GPU job --no-fold-siblings means: claim gpu-quiet ONLY (no CPU region) and let the job taskset its host threads (184-191).
  if [ $NOFOLD = 1 ] && [ "$CLASS" != gpu ]; then   # GRANT_CPUS: a gpu claim is the grant's cpus (above)
    if [ "$CLASS" = gpu ]; then
      _n=(); _skip=0; for a in "${rlargs[@]}"; do if [ $_skip = 1 ]; then _skip=0; continue; fi; [ "$a" = --cpu-list ] && { _skip=1; continue; }; _n+=("$a"); done
      rlargs=("${_n[@]}")   # 2026-11-03 item 6: no implicit --gpu-quiet shared
    elif [[ " ${rlargs[*]} " == *" --cpu-list "* ]]; then rlargs+=(--no-fold-siblings); fi
  fi
  if [ "${SMOKE_NOLOCK:-0}" = 1 ]; then
    if [ "$CLASS" = gpu ]; then rlargs=(--gpu-quiet shared); else rlargs=(); fi
  fi
  set_gpu_fence
  snapshot_overrun "$regions"
  if [ -n "${FILLER_STUB_CMD:-}" ]; then
    "${FENCE_ENV[@]}" setsid bash -c "$FILLER_STUB_CMD" 7>&- &
  elif [ "${SMOKE_NOLOCK:-0}" = 1 ] && [ ${#rlargs[@]} = 0 ]; then
    "${FENCE_ENV[@]}" setsid taskset -c "${CLAIM_CPUS:-$CPUS}" /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" 7>&- &
  elif [ $SELFCLAIM = 1 ] || [ ${#rlargs[@]} = 0 ]; then   # nothing to lock (gpu row, gpu-quiet none, host threads only): no region-lock call
    "${FENCE_ENV[@]}" setsid /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" 7>&- &
  else
    local rl_to=$(( e - $(date -u +%s) )); [ "$rl_to" -ge 1 ] || rl_to=1   # region-lock: 0 = wait forever; never that
    "${FENCE_ENV[@]}" setsid "$RL" run "${rlargs[@]}" --role "$rl_role" --timeout-s "$rl_to" --tag "filler-$ID" -- \
      /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" 7>&- &
  fi
  CUR=$!
  CUR_BIRTH=$(proc_birth "$CUR")
  lm_job_dispatched
  OV_STARTED=$(ts)
  [ "$(ps -o pgid= -p $CUR | tr -d ' ')" = "$CUR" ] || log "WARN: $CUR is not a group leader"
  reason=exited
  while alive_pid "$CUR"; do
    if [ "$DRYRUN" != 1 ] && [ -e "$STOPFILE" ]; then
      reason=stopped; log "STOP seen mid-run ($STOPFILE): TERM job group(s), KILL after ${STOP_GRACE}s"
      kill_job "$STOP_GRACE" || reason=cleanup-failed; break; fi
    if [ "$(date -u +%s)" -ge "$e" ]; then reason=hard-end; kill_job || reason=cleanup-failed; break; fi
    # operator 2026-11-07 "Pause with hysteresis": below the floor the row is PAUSED (SIGSTOP of its captured group by
    # diskpause.py, resumed at FILLER_DISK_RESUME_GIB) - never killed. Only below the EMERGENCY floor is it killed.
    # A smoke (FILLER_SMOKE=1, floor 20) keeps the single-threshold kill: it writes little and must not run the pause machine.
    _free=$(df -BG --output=avail /mnt/raid0 2>/dev/null | tail -1 | tr -dc 0-9)
    _floor=${FILLER_DISK_FLOOR_GIB:-150}; _emerg=${FILLER_DISK_EMERGENCY_GIB:-50}
    if [ "${FILLER_SMOKE:-0}" = 1 ] || [ "$_emerg" -gt "$_floor" ] 2>/dev/null; then _emerg=$_floor; fi
    if [ "$_free" -lt "$_emerg" ] 2>/dev/null; then
      log "DISK-EMERGENCY free=${_free}GiB < emergency floor ${_emerg}GiB: killing the row"
      reason=disk-floor; kill_job || reason=cleanup-failed; break; fi
    if [ "${FILLER_SMOKE:-0}" != 1 ] && [ $(( SECONDS - ${_dp_last:--999} )) -ge 15 ] \
       && { [ -e "$FLAGS/disk-pause/PAUSED" ] || [ "$_free" -lt "$_floor" ] 2>/dev/null; }; then
      _dp_last=$SECONDS
      python3 -I "$HERE/diskpause.py" tick --flags "$FLAGS" 7>&- 8>&- 2>&1 | sed "s/^/$(ts) [$ID] /" || true
    fi
    sleep 3 7>&- 8>&-
  done
  wait "$CUR" 2>/dev/null; rc=$?
  case $reason in hard-end|disk-floor|stopped) rc=75;; esac
  local cleanup_bad=0
  kill_job || cleanup_bad=1
  kill_pidfile || cleanup_bad=1
  kill_containers || cleanup_bad=1
  CUR=""
  CUR_BIRTH=""
  exec 8>&-
  if [ "$cleanup_bad" = 1 ] || [ "$reason" = cleanup-failed ]; then
    log "REFUSED: native cleanup incomplete; grant retained, no .ended or .complete"
    notify_end 70 cleanup-failed
    STARTED_ONE=1; return 70
  fi
  if [ "$reason" = exited ] && gpu_vacuous_check; then
    log "GPU-FENCE-VACUOUS $ID: fenced grant (no GPU token) ran a GPU test that tested nothing (job rc=$rc): $VAC_WHY"
    printf '{"id":"%s","at":"%s","reason":"gpu-fence-vacuous","job_rc":%s,"why":"%s"}\n' "$ID" "$(ts)" "$rc" \
      "$(printf '%s' "$VAC_WHY" | tr -d '"\\')" > "$STATE/$ID.gpu-fence-vacuous.json"
    [ "$DRYRUN" = 1 ] && cp -f "$STATE/$ID.gpu-fence-vacuous.json" "$DR/GPU-FENCE-VACUOUS.json" 2>/dev/null
    write_ended "$VACUOUS_RC" "gpu-fence-vacuous"
    STARTED_ONE=1; return 0
  fi
  if is_complete; then mark_complete || return 70; return 20; fi
  if [ "$rc" -eq 0 ]; then rc=75; reason=partial-native-incomplete; fi
  [ "$rc" -eq 75 ] || reason="job-rc-$rc:$reason"
  write_ended "$rc" "$reason"
  STARTED_ONE=1
  [ "$reason" = stopped ] && return 21
  return 0
}

# Disabled metadata has no new file dependency or EXIT trap.
lm_attempt_begin() { :; }
lm_attempt_end() { :; }
lm_job_dispatched() { :; }
if [ -n "${LOOP_METRICS_LEDGER:-}" ]; then
  if [ -n "$(trap -p EXIT)" ]; then
    printf '%s\n' 'loop metrics: existing EXIT trap preserved; coverage unavailable' >&2
  elif [ -r "${LOOP_METRICS_HOOK:-$(dirname "$SELF")/loop_metrics_hook.sh}" ]; then
    source "${LOOP_METRICS_HOOK:-$(dirname "$SELF")/loop_metrics_hook.sh}"
    lm_start
    trap lm_close EXIT
  else
    printf '%s\n' 'loop metrics: helper unavailable; coverage unavailable' >&2
  fi
fi
log "launcher up pid=$$ class=$CLASS poll=${POLL}s grants=$GRANTS stop=$STOPFILE minwin=${MINWIN}s ports=${PORTS:-none}${DRYRUN:+ dryrun=$DRYRUN}"
if is_complete; then mark_complete || exit 70; exit 0; fi
while :; do
  [ -e "$COMPLETE" ] && { log "complete marker present; exiting"; exit 0; }
  if [ ! -e "$GRANT" ]; then
    # keeper-hotfix 2026-11-05 (D13): STOP is honoured while WAITING for a grant too - terminal record, release, exit
    if [ -e "$STOPFILE" ]; then
      log "STOP seen while waiting for a grant ($STOPFILE): releasing claim, exiting"
      [ -e "$ENDED" ] || write_ended 75 stopped-while-waiting
      [ "$DRYRUN" = 1 ] && rm -f "$DR/RUNNING.json"
      exit 0
    fi
    sleep_poll "$POLL"; continue
  fi
  GRANT_WAIT=""
  lm_attempt_begin
  run_one; rc=$?
  lm_attempt_end "$rc"
  [ "$rc" = 70 ] && exit 70
  [ $rc = 20 ] && exit 0
  [ "$rc" = 21 ] && { log "row stopped (.ended reason=stopped*); poller exiting"; exit 0; }
  # 2026-11-03: rc=66 means the id is terminal (.ended exists); the grant can never be consumed - release it and exit
  # instead of re-reading it every poll (r3 poller: 85,235 REFUSED lines, ~10% of a core, grant shown as held).
  [ "$rc" = 66 ] && { rm -f "$GRANT"; log "terminal id (.ended exists): grant released, poller exiting; fix: publish a new row id"; exit 66; }
  if [ "${STARTED_ONE:-0}" = 1 ] && [ $REPEAT = 0 ]; then log "one window done; exiting (no --repeat)"; exit 0; fi
  if [ $rc = 9 ]; then w=$GRANT_WAIT; [ "$w" -gt "$POLL" ] && w=$POLL; sleep_poll "$w"; fi
done
