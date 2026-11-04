#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row
exec bash "$D/filler_run15.sh" --id kvfork17-partial-20261102 --class cpu --role build --gpu-quiet none --min-window 1200 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 93edca3088046b16b5abb0a07f5ccdf33bbb51c739f236247dec4da4929fb363 '$D/runtime.sha256' | sha256sum -c && sha256sum -c '$D/runtime.sha256' && python3 '$D/check.py'" --complete-cmd "test -s '$D/out/RESULT.json'" --cmd "bash '$D/job.sh'"
