#!/bin/bash
# FM-2 launcher (shape of inf86-reprefill-rate-20261110/launch.sh): NO grant, no run - filler_run15.sh polls the grant.
# Do not run by hand; publish_row.py snapshots this directory. Env exports below are the row's pinned inputs; the
# <...> values are filled at publish time and are deliberately not guessed here.
set -euo pipefail
D=/mnt/raid0/llm/tmp/fm2-adamast-20261110
cd "$D"
/usr/bin/sha256sum --check --status SOURCE.sha256
export FM2_RUN_DIR="$D"
export FM2_ADAMAST_SRC="${FM2_ADAMAST_SRC:?pinned upstream 3c83d81c8 + providers_base_url.patch}"
export FM2_MODEL_GGUF="${FM2_MODEL_GGUF:?judge model; operator/registry choice}"
export FM2_SERVER_BIN="${FM2_SERVER_BIN:?production-store cpu llama-server}"
export FM2_NORMALIZER="$D/adamast_normalize.py"
export FM2_PORT="${FM2_PORT:-18711}"
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id fm2-adamast-20261110 \
  --class cpu --gpu-quiet none --role build --min-window 3600 --port "$FM2_PORT" \
  --cmd "/bin/bash $D/job.sh" \
  --complete-cmd "/usr/bin/python3 -I $D/check_complete.py" \
  --stop "$D/STOP" --workdir "$D"
