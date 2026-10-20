#!/bin/bash
# Phase 2: induced contention (own spinner PIDs) + perf samples. Runs inside a region claim on q1 (cpus 24-47).
set -uo pipefail
D=/mnt/raid0/llm/tmp/qwentts-threads-20261020
source $D/sweep.sh --source-only
SP=$D/spinner_pids.txt
: > $SP
spin() { # cpulist -> starts one spinner per cpu, records pids
  for c in $(echo "$1" | tr ',' ' '); do
    taskset -c $c bash -c 'while :; do :; done' &
    echo $! >> $SP
  done
}
unspin() {
  for p in $(cat $SP); do kill $p 2>/dev/null; done
  sleep 1
  for p in $(cat $SP); do kill -0 $p 2>/dev/null && kill -9 $p 2>/dev/null; done
  sleep 1
  for p in $(cat $SP); do kill -0 $p 2>/dev/null && echo "SPINNER $p STILL ALIVE" >> $D/phase2.err; done
  : > $SP
}
trap unspin EXIT
allcpus() { seq -s, $1 $2; }

# (c) 1 thread sharing its core with 1 spinner
spin 24;                      run_leg c_1T_shared1 1 24 3 ; unspin
# (b) 8 threads pinned 24-31, one spinner on cpu 24 (one thread descheduled half the time)
spin 24;                      run_leg b_8T_pinned_1spin 8 24-31 3 ; unspin
# (a) 8 threads pinned 24-31, spinner on every one of those cpus
spin $(allcpus 24 31);        run_leg a_8T_pinned_8spin 8 24-31 3 ; unspin
# (d) 8 threads free over 24-47 with 24 spinners (whole region oversubscribed 1:1 + our 8)
spin $(allcpus 24 47);        run_leg d_8T_free_24spin 8 24-47 3 ; unspin
# (e) 1 thread free over 24-47 with 24 spinners
spin $(allcpus 24 47);        run_leg e_1T_free_24spin 1 24-47 3 ; unspin
# (f) 2 threads pinned 24-25, spinners on both
spin 24,25;                   run_leg f_2T_pinned_2spin 2 24-25 3 ; unspin

# perf samples, own PID only: quiet 8T free, and 8T pinned w/ 8 spinners
Q=/mnt/raid0/llm/qwentts.cpp/build; M=/mnt/raid0/llm/models/Qwen3-TTS-qwentts
REF=/mnt/raid0/llm/data/asr-eval/librispeech-test-clean-strat300/wav/3729-6852-0044.wav
perf_leg() { # label cpuset threads
  echo "Would you like me to book that table for Friday evening?" | env -u LD_PRELOAD HIP_VISIBLE_DEVICES=-1 GGML_BACKEND=CPU LD_LIBRARY_PATH=$Q:/opt/rocm/lib LD_PRELOAD=/mnt/raid0/llm/tmp/cs45/nprocs_shim.so SHIM_NPROCS=$((2*$3)) \
    perf record -F 499 -o $D/perf_$1.data -- taskset -c $2 $Q/qwen-tts --model $M/qwen-talker-0.6b-base-Q8_0.gguf --codec $M/qwen-tokenizer-12hz-Q8_0.gguf --lang English --seed 1234 --greedy --max-new 24 --ref-wav $REF -o $D/out.wav > $D/logs/perf_$1.log 2>&1 &
  local pid=$!; echo $pid >> $D/pids_started.txt; wait $pid
  perf report -i $D/perf_$1.data --sort dso,sym --stdio 2>/dev/null | grep -v '^#' | grep -v '^$' | head -25 > $D/perf_$1.txt
}
perf_leg quiet8 24-47 8
spin $(allcpus 24 31); perf_leg spin8 24-31 8; unspin
echo PHASE2_DONE > $D/phase2.done
