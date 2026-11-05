#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf623-census-r2-20261105
printf '%s  %s\n' 145a94ee7655356711e9a7d32fc5d146c2a4117c316d13c2505259ee354482d2 "$D/SHA256SUMS" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SHA256SUMS)
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf623-census-r2-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd 'sha256sum -c SHA256SUMS' --complete-cmd "python3 -B '$D/worker.py' complete" --cmd "python3 -B '$D/worker.py'"
