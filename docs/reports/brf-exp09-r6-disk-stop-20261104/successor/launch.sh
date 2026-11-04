#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp09-resume-r7
PY=/mnt/raid0/llm/tmp/brf-exp09/pyenv/venv/bin/python
KERNEL_BIN=/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin
VERIFY=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
mkdir -p "$D/out"
# Content pins bind the R7 task, helper, identity, qualification predicate, seed, and corpus.
sha256sum -c <<'PINS'
963a400c1d79c685a2eaed4f887cdd02cf9fc868fcea3b0d7ce7f059fb9da83d  /mnt/raid0/llm/tmp/brf-exp09-resume-r7/job.py
a49cbb3fccf9772cd407c6a4598d80290767f95eb786e80ba5d554e8b05eada3  /mnt/raid0/llm/tmp/brf-exp09-resume-r7/summary_flags.py
e845f6bdff457087ad6304ac95b79f208df48edcff8eaae5b4ba66b7b1aba794  /mnt/raid0/llm/tmp/brf-exp09-resume-r7/identity.json
da352aeb797a278838493639de5c023dd90b8688330de79f2c5be8cd4dc85279  /mnt/raid0/llm/tmp/brf-exp09-resume-r7/smoke_predicate.py
0f633a4f2ec6d134ef957dbdbbfdabad3be787918353862d1a5938f5d36dd421  /mnt/raid0/llm/tmp/brf-exp09-resume-r7/out/seed-pins.json
59b4358cfdb709bf3b14a0781803d6595080b3045c8c0133b830b3e836ba7266  /mnt/raid0/llm/tmp/brf-exp09-resume-r7/out/results.r3-native.jsonl
076446cce8d4f0ba14ab1a450eeb4b93e861383367db031d0354465cec12e2cd  /mnt/raid0/llm/tmp/brf-exp09-resume-r7/corpus/MANIFEST.json
PINS
export LD_LIBRARY_PATH="$KERNEL_BIN"
if ! "$VERIFY" "$KERNEL_BIN/llama-server" "$KERNEL_BIN" > "$D/out/ggml-linkage-preflight.r7.txt" 2>&1; then
  cat "$D/out/ggml-linkage-preflight.r7.txt" >&2; exit 1
fi
export EXP09_WORKDIR="$D"
export EXP09_CAP_S=2700
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp09-resume-r7-20261104 --class cpu --role build --gpu-quiet none --port 18461 --min-window 2700 --stop "$D/STOP" --workdir "$D" --precond-cmd "$PY $D/job.py --check" --cmd "exec $PY $D/job.py" --complete-cmd "test -s $D/out/COMPLETE"
