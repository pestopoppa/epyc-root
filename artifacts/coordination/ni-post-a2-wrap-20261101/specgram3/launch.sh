#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/specgram3
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/filler_run14.sh
validate_claim() {
  if [ "${WS58_QUAL:-0}" = 1 ] || [ "${WS58_R11_CALIBRATION:-0}" = 1 ]; then python3 -I "$D/cpu_claim.py" qual "$1" >/dev/null
  else python3 -I "$D/cpu_claim.py" quarter "$1" >/dev/null; fi
}
case ${1:-} in
  --validate-claim)
    [ "$#" = 2 ] || { echo "usage: $0 --validate-claim NUMERIC_CPUS" >&2; exit 64; }
    validate_claim "$2"
    python3 -I "$D/cpu_claim.py" "$(if [ "${WS58_QUAL:-0}" = 1 ] || [ "${WS58_R11_CALIBRATION:-0}" = 1 ]; then echo qual; else echo quarter; fi)" "$2" ;;
  --job)
    : "${FILLER_CPUS:?canonical engine must supply its actual CPUs}" "${FILLER_THREADS:?}" "${FILLER_DEADLINE:?}"
    validate_claim "$FILLER_CPUS"
    [ "$FILLER_THREADS" = 24 ] || { echo "REFUSED: production recipe requires 24 threads" >&2; exit 64; }
    [ "${WS58_REGIONS:-}" = "$FILLER_CPUS" ] || { echo "REFUSED: FILLER_CPUS differs from granted WS58_REGIONS" >&2; exit 64; }
    exec taskset -c "$FILLER_CPUS" python3 -I -B "$D/job.py" full ;;
  '')
    if [ "${WS58_FINGERPRINT_ONLY:-0}" != 1 ]; then
      : "${WS58_REGIONS:?keeper must provide actual numeric granted CPUs}"
      validate_claim "$WS58_REGIONS"
    fi
    mkdir -p "$D/state"
    exec /bin/bash "$ENGINE" --id codex-ni-specgram3-llg101-cpu-r3-20261101 --class cpu --role build \
      --claim-cpus "${WS58_REGIONS:-}" --min-window 1200 --stop "$D/STOP" --workdir "$D" \
      --cmd "env FILLER_THREADS=24 /bin/bash $D/launch.sh --job" \
      --complete-cmd "python3 -I $D/job.py complete" ;;
  *) echo "usage: $0 [--job]" >&2; exit 64 ;;
esac
