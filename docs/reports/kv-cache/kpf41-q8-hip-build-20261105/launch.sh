#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf41-q8-build-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf41-q8-hip-build-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "cd '$D' && printf '%s  %s\n' 23568b9f2919e076ee26586f37d7bfeceb77ec87a60febd75bf4c1f7afbb5ce3 runtime.sha256 | sha256sum -c && sha256sum -c runtime.sha256 && python3 '$D/check.py' && test -x /opt/rocm/lib/llvm/bin/clang++" --cmd "bash '$D/job.sh'" --complete-cmd "python3 '$D/complete.py'"
