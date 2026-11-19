#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/gpu-serving-tie-in/p5-candidate-pii-row
ID=codex-gpu-serving-p5-candidate-pii-20261104
if [[ ${1:-} == --job ]]; then
  cd "$D"
  printf '%s  %s\n' '79576d38dddab6fbadbb8efe24df9ba204ee2bdf4b8577ff55b11d0cb6ed3944' SOURCE.sha256 | sha256sum -c >/dev/null
  sha256sum -c SOURCE.sha256 >/dev/null
  export TMPDIR="$D/control-tmp"
  export PYTHONDONTWRITEBYTECODE=1
  mkdir -p "$TMPDIR"
  exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/job.py"
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 300 --stop "$D/STOP" --workdir "$D" --cmd "bash $D/launch.sh --job" --complete-cmd "/usr/bin/python3 -B $D/complete.py"
