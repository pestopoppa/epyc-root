#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp09-resume-r4
PY=/mnt/raid0/llm/tmp/brf-exp09/pyenv/venv/bin/python
KERNEL_BIN=/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin
VERIFY=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
mkdir -p "$D/out"
# Content pins for the copied job, identity, seed, and corpus.
sha256sum -c <<'PINS'
5015cede8f3501e5c45a6f1709129adf1842751127f56862a9aba3c7de6f7a4e  /mnt/raid0/llm/tmp/brf-exp09-resume-r4/job.py
a49cbb3fccf9772cd407c6a4598d80290767f95eb786e80ba5d554e8b05eada3  /mnt/raid0/llm/tmp/brf-exp09-resume-r4/summary_flags.py
d713bb082be97ae1f47d97664388b781a0f6d008ba5aee65a5ae0b139ba196e3  /mnt/raid0/llm/tmp/brf-exp09-resume-r4/identity.json
389715383d90e7e16472aebf896f743e23fe3a826023efd6b6ecd075416f8981  /mnt/raid0/llm/tmp/brf-exp09-resume-r4/smoke_predicate.py
0f633a4f2ec6d134ef957dbdbbfdabad3be787918353862d1a5938f5d36dd421  /mnt/raid0/llm/tmp/brf-exp09-resume-r4/out/seed-pins.json
076446cce8d4f0ba14ab1a450eeb4b93e861383367db031d0354465cec12e2cd  /mnt/raid0/llm/tmp/brf-exp09-resume-r4/corpus/MANIFEST.json
PINS
export LD_LIBRARY_PATH="$KERNEL_BIN"
if ! "$VERIFY" "$KERNEL_BIN/llama-server" "$KERNEL_BIN" > "$D/out/ggml-linkage-preflight.r4.txt" 2>&1; then
  cat "$D/out/ggml-linkage-preflight.r4.txt" >&2; exit 1
fi
export EXP09_WORKDIR="$D"
export EXP09_CAP_S=2700
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp09-resume-r4-20261104 --class cpu --role build --gpu-quiet none --port 18431 --min-window 2700 --stop "$D/STOP" --workdir "$D" --precond-cmd "$PY $D/job.py --check" --cmd "exec $PY $D/job.py" --complete-cmd "test -s $D/out/COMPLETE"
