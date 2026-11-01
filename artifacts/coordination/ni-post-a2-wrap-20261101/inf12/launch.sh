#!/bin/bash
set -euo pipefail
ROOT=/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/inf12
ID=codex-ni-inf12-gate2-triton36-v3-20261101
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/filler_run14.sh
[[ "$(sha256sum "$ENGINE" | awk '{print $1}')" == 6fe168333738d15e5988d5af42e2b4c348194d722bac11c32368183ae89cd3ef ]] || { echo 'REFUSED: canonical engine14 drift' >&2; exit 70; }
(cd "$ROOT" && sha256sum --check SOURCE-SHA256SUMS >/dev/null) || { echo 'REFUSED: source pin drift' >&2; exit 70; }
G2_PIN_FINGERPRINT=$(python3 - "$ROOT/MODEL-SHA256SUMS" "$ROOT/DATA-SHA256SUMS" "$ROOT/SOURCE-SHA256SUMS" <<'PYS'
import hashlib,pathlib,sys
h=hashlib.sha256()
for name in sys.argv[1:]:
 p=pathlib.Path(name);h.update(p.name.encode()+b'\0');h.update(p.read_bytes());h.update(b'\0')
print(h.hexdigest())
PYS
)
export G2_PIN_FINGERPRINT
if [[ "${WS58_FINGERPRINT_ONLY:-0}" != 1 ]]; then : "${WS58_REGIONS:?keeper must provide actual region claim}"; fi
if [[ "${WS58_REGIONS:-}" == mi210_0,* ]]; then
  CPU_CLAIM=${WS58_REGIONS#mi210_0,}
elif [[ "${WS58_QUAL:-0}" == 1 || "${WS58_FINGERPRINT_ONLY:-0}" == 1 ]]; then
  CPU_CLAIM=${WS58_REGIONS:-}
else
  echo 'REFUSED: production GPU claim must include mi210_0 and numeric CPUs' >&2; exit 64
fi
[[ -z "$CPU_CLAIM" || "$CPU_CLAIM" =~ ^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$ ]] || { echo 'REFUSED: CPU claim not numeric' >&2; exit 64; }
exec /bin/bash "$ENGINE" --id "$ID" --class gpu --role inference \
  --claim-cpus "$CPU_CLAIM" --min-window 1200 --stop "$ROOT/STOP" --workdir "$ROOT" \
  --gpu-quiet exclusive --no-fold-siblings \
  --cmd "exec taskset -c \"\$FILLER_CPUS\" /bin/bash $ROOT/job.sh" \
  --complete-cmd "/bin/bash $ROOT/job.sh --complete"
