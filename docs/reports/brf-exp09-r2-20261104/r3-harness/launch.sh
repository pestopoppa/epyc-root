#!/bin/bash
# EXP-09 expanded R3 runner; blocked until separately produced corpus manifest is installed and pinned.
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp09-expand-r3
PY=/mnt/raid0/llm/tmp/brf-exp09/pyenv/venv/bin/python
KERNEL_BIN=/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin
VERIFY=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
mkdir -p "$D/out"
export LD_LIBRARY_PATH="$KERNEL_BIN"
if ! "$VERIFY" "$KERNEL_BIN/llama-server" "$KERNEL_BIN" > "$D/out/ggml-linkage-preflight.txt" 2>&1; then
  cat "$D/out/ggml-linkage-preflight.txt" >&2
  exit 1
fi
printf '%s  %s\n' 378f73d3c0d9a250540f504628b08dd166210a8dff57d562d6e1f3917ee6ef1b "$D/job.py" | sha256sum -c --quiet -
printf '%s  %s\n' ff62697b6ce529f9fd07530cfc522f6b2ad6981b711f47d878572b660f581f09 "$D/identity.json" | sha256sum -c --quiet -
printf '%s  %s\n' a49cbb3fccf9772cd407c6a4598d80290767f95eb786e80ba5d554e8b05eada3 "$D/summary_flags.py" | sha256sum -c --quiet -
if grep -q PENDING "$D/identity.json"; then echo "R3 corpus not finalized" >&2; exit 2; fi
printf '%s  %s\n' 19be7cafdefdb2360e478ace9a5b28a0981bdf6de0c64d024bb820b781b47dce "$D/corpus/MANIFEST.json" | sha256sum -c --quiet -
export EXP09_CAP_S=2700
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp09-expanded-r3-20261104 --class cpu --role build --gpu-quiet none --port 18429 --min-window 2700 --stop "$D/STOP" --workdir "$D" --precond-cmd "$PY $D/job.py --check" --cmd "exec $PY $D/job.py" --complete-cmd "test -s $D/out/COMPLETE"
