#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf623-tokenizer-roundtrip-20261105
printf '%s  %s\n' 68eba3b13afa4975b064a272738a46bd55d795cf124b3b9889bc2c1b42eb5569 "$D/SHA256SUMS" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SHA256SUMS)
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf623-tokenizer-roundtrip-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd 'sha256sum -c SHA256SUMS' --complete-cmd "python3 -B '$D/worker.py' complete" --cmd "python3 -B '$D/worker.py'"
