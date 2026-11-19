#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/canonical-judge-suite-revamp/ifbench-v3-cj6a-20261104
ID=codex-ifbench-cj6a-27b-v4-20261104
OWNER=codex-ifbench
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
cd "$D"
sha256sum -c --quiet V3-INPUTS.sha256
sha256sum -c --quiet SOURCE-SHA256SUMS
sha256sum -c --quiet KERNEL-INPUTS.sha256
sha256sum -c --quiet RUNTIME-INPUTS.sha256
sha256sum -c --quiet SCORE-RUNTIME.sha256
case ${1:-} in
 --job)
   if [ "${FILLER_SMOKE:-0}" = 1 ]; then
     export IFBENCH_MODE=smoke IFBENCH_OUT="${FILLER_DRYRUN_DIR:?}/ifbench-native"
   else
     export IFBENCH_MODE=full IFBENCH_OUT=run
   fi
   exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/worker.py" ;;
 --job-check)
   test -s "$D/source/data/IFBench_test.jsonl" -a -x "$D/venv/bin/python" -a -s "$D/nltk_data/tokenizers/punkt/english.pickle"
   test -x /mnt/raid0/llm/kernels/production/cpu/llama-server
   printf '%s  %s\n' 4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c /mnt/raid0/llm/kernels/production/cpu/llama-server | sha256sum -c --quiet
   /usr/bin/python3 -c 'import pathlib; d=pathlib.Path("'"$D"'"); assert sum(1 for _ in open(d/"source/data/IFBench_test.jsonl")) == 300; print("source/runtime paths present; 300 prompts")' ;;
 --engine)
   export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
   export FILLER_OWNER="$OWNER" FILLER_EST_WALL_S=14400
   exec /bin/bash "$ENGINE" --id "$ID" --class cpu --role bench --claim-cpus "${WS58_REGIONS:?}" --min-window 1800 --stop "$D/STOP" --workdir "$D" --complete-cmd 'test -s /mnt/raid0/llm/tmp/canonical-judge-suite-revamp/ifbench-v3-cj6a-20261104/run/TERMINAL.json -o -s "${FILLER_DRYRUN_DIR:-/nonexistent}/ifbench-native/TERMINAL.json"' --cmd 'if [ "${FILLER_SMOKE:-0}" = 1 ]; then export IFBENCH_MODE=smoke IFBENCH_OUT="$FILLER_DRYRUN_DIR/ifbench-native"; else export IFBENCH_MODE=full IFBENCH_OUT=run; fi; env -i PATH=/usr/bin:/bin LANG=C.UTF-8 RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1 IFBENCH_MODE="$IFBENCH_MODE" IFBENCH_OUT="$IFBENCH_OUT" FILLER_DRYRUN_RESULT_PATH="${FILLER_DRYRUN_RESULT_PATH:-}" FILLER_SMOKE="${FILLER_SMOKE:-0}" FILLER_DRYRUN_DIR="${FILLER_DRYRUN_DIR:-}" FILLER_ID="$FILLER_ID" FILLER_CPUS="$FILLER_CPUS" FILLER_NEEDGPU="$FILLER_NEEDGPU" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_END="$FILLER_END" FILLER_DEADLINE="$FILLER_DEADLINE" FILLER_GRANTS_DIR="$FILLER_GRANTS_DIR" FILLER_FLAGS_DIR="$FILLER_FLAGS_DIR" FILLER_OWNER="$FILLER_OWNER" FILLER_EST_WALL_S="$FILLER_EST_WALL_S" WS58_REGIONS="$WS58_REGIONS" /bin/bash /mnt/raid0/llm/tmp/canonical-judge-suite-revamp/ifbench-v3-cj6a-20261104/launch.sh --job' ;;
 '')
   exec > >(tee -a "$D/ws58-launcher.out") 2>&1
   exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS,FILLER_SMOKE,FILLER_DRYRUN,FILLER_DRYRUN_DIR,FILLER_DRYRUN_RESULT_PATH /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine ;;
 *) exit 64 ;;
esac
