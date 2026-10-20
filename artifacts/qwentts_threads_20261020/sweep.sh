#!/bin/bash
# runs inside the region claim; sequential; writes jsonl
set -uo pipefail
D=/mnt/raid0/llm/tmp/qwentts-threads-20261020
Q=/mnt/raid0/llm/qwentts.cpp/build
M=/mnt/raid0/llm/models/Qwen3-TTS-qwentts
REF=/mnt/raid0/llm/data/asr-eval/librispeech-test-clean-strat300/wav/3729-6852-0044.wav
SHIM=/mnt/raid0/llm/tmp/cs45/nprocs_shim.so
TXT="Would you like me to book that table for Friday evening?"
OUT=$D/results.jsonl
cpus_busy() { awk '/^cpu(2[4-9]|3[0-9]|4[0-7]|12[0-9]|13[0-9]|14[0-3]) /{b+=$2+$3+$4+$7+$8; t+=$2+$3+$4+$5+$6+$7+$8} END{print b, t}' /proc/stat; }
run_leg() { # label threads cpuset reps [extra env VAR=val ...]
  local label=$1 th=$2 cs=$3 reps=$4; shift 4
  for r in $(seq 1 $reps); do
    local log=$D/logs/${label}_t${th}_r${r}.log
    local la0=$(cut -d' ' -f1 /proc/loadavg) b0 t0 b1 t1
    read b0 t0 < <(cpus_busy)
    echo "$TXT" | env -u LD_PRELOAD HIP_VISIBLE_DEVICES=-1 GGML_BACKEND=CPU LD_LIBRARY_PATH=$Q:/opt/rocm/lib LD_PRELOAD=$SHIM SHIM_NPROCS=$((2*th)) "$@" \
      taskset -c "$cs" $Q/qwen-tts --model $M/qwen-talker-0.6b-base-Q8_0.gguf --codec $M/qwen-tokenizer-12hz-Q8_0.gguf --lang English --seed 1234 --greedy --max-new 24 --ref-wav $REF -o $D/out.wav >$log 2>&1 &
    local pid=$!; echo $pid >> $D/pids_started.txt
    wait $pid; local rc=$?
    read b1 t1 < <(cpus_busy)
    local la1=$(cut -d' ' -f1 /proc/loadavg)
    python3 - "$label" "$th" "$cs" "$r" "$rc" "$log" "$la0" "$la1" "$b0" "$t0" "$b1" "$t1" "$*" >> $OUT <<'P'
import sys,re,json
label,th,cs,r,rc,log,la0,la1,b0,t0,b1,t1,env=sys.argv[1:]
s=open(log).read()
m=re.search(r'TalkerDecode ([\d.]+) ms \((\d+) frames, ([\d.]+) ms/frame\)',s)
c=re.search(r'CodePredictor ([\d.]+) ms \(([\d.]+) ms/frame\)',s)
t=re.search(r'Total ([\d.]+) ms \((\d+) frames, ([\d.]+) ms/frame AR',s)
th_log=re.search(r'CPU threads: (\d+)',s)
d=dict(label=label,threads=int(th),cpuset=cs,rep=int(r),rc=int(rc),env=env,load1_before=float(la0),load1_after=float(la1),
 region_busy_frac=(int(b1)-int(b0))/max(1,int(t1)-int(t0)),
 log_threads=int(th_log.group(1)) if th_log else None,
 frames=int(t.group(2)) if t else None,
 talker_ms_frame=float(m.group(3)) if m else None, predictor_ms_frame=float(c.group(2)) if c else None,
 total_ms_frame=float(t.group(3)) if t else None)
print(json.dumps(d))
P
  done
}
[ "${1:-}" = "--source-only" ] && return 0 2>/dev/null
REGION=24-47
for th in 1 2 4 8 16; do
  pin=24-$((23+th)); [ $th -eq 1 ] && pin=24
  run_leg pinned $th $pin 5
  run_leg free   $th $REGION 5
done
# negative control: OMP env at 8 threads (OpenMP not compiled in -> expect no effect)
run_leg omp_env_pinned 8 24-31 3 OMP_PROC_BIND=close OMP_PLACES=cores OMP_WAIT_POLICY=passive
run_leg omp_env_free 8 $REGION 3 OMP_PROC_BIND=close OMP_PLACES=cores OMP_WAIT_POLICY=passive
echo SWEEP_DONE >> $D/sweep.done
