#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp09-resume-r5
PY=/mnt/raid0/llm/tmp/brf-exp09/pyenv/venv/bin/python
KERNEL_BIN=/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin
VERIFY=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
mkdir -p "$D/out"
# Pin copied task inputs and the immutable R3 control seed.
sha256sum -c <<'PINS'
9d01cb1c38f52303ea002281062a9b000a2aa1d2bf2cbf4d3a3ef0caf01929f7  /mnt/raid0/llm/tmp/brf-exp09-resume-r5/job.py
a49cbb3fccf9772cd407c6a4598d80290767f95eb786e80ba5d554e8b05eada3  /mnt/raid0/llm/tmp/brf-exp09-resume-r5/summary_flags.py
6a1838a9f8f38851f503cbef7972685edf33262ba9f3d29599d87bd234da4158  /mnt/raid0/llm/tmp/brf-exp09-resume-r5/identity.json
a626b9f76be65aeb7b230fbfaf82861177eda8c00b0ecffb26bbc14a6d1dfbf0  /mnt/raid0/llm/tmp/brf-exp09-resume-r5/smoke_predicate.py
0f633a4f2ec6d134ef957dbdbbfdabad3be787918353862d1a5938f5d36dd421  /mnt/raid0/llm/tmp/brf-exp09-resume-r5/out/seed-pins.json
59b4358cfdb709bf3b14a0781803d6595080b3045c8c0133b830b3e836ba7266  /mnt/raid0/llm/tmp/brf-exp09-resume-r5/out/results.r3-native.jsonl
076446cce8d4f0ba14ab1a450eeb4b93e861383367db031d0354465cec12e2cd  /mnt/raid0/llm/tmp/brf-exp09-resume-r5/corpus/MANIFEST.json
PINS
export LD_LIBRARY_PATH="$KERNEL_BIN"
if ! "$VERIFY" "$KERNEL_BIN/llama-server" "$KERNEL_BIN" > "$D/out/ggml-linkage-preflight.r5.txt" 2>&1; then
  cat "$D/out/ggml-linkage-preflight.r5.txt" >&2; exit 1
fi
export EXP09_WORKDIR="$D"
export EXP09_CAP_S=2700
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp09-resume-r5-20261104 --class cpu --role build --gpu-quiet none --port 18441 --min-window 2700 --stop "$D/STOP" --workdir "$D" --precond-cmd "$PY $D/job.py --check" --cmd "exec $PY $D/job.py" --complete-cmd "test -s $D/out/COMPLETE"
