#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105/v3
S=/mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf18-item4-raw-build-20261105 --class cpu --role build --min-window 2400 --stop "$S/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 52a842cc2f539138957164f76274bd7f4a924f55ffaaf9fd5dd83abcd5b7b16e $D/runtime.sha256 | sha256sum -c && sha256sum -c $D/runtime.sha256 && python3 $D/integrity.py" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
