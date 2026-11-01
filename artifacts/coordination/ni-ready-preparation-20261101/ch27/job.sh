#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-v2-ch27-20261101
mode=${1:-normal}
cd "$D"
sha256sum --quiet -c SOURCE.sha256
if [[ "${WS58_QUAL:-0}" == 1 ]]; then
  case "${FILLER_QUAL_PHASE:-}" in
    normal|cutoff) exec /usr/bin/python3 -I "$D/qualification_entry.py" "$FILLER_QUAL_PHASE" ;;
    *) echo "REFUSED: missing canonical qualification phase" >&2; exit 70 ;;
  esac
fi
[[ "$mode" == normal && $# -le 1 ]] || { echo "REFUSED: production entry accepts only normal mode" >&2; exit 64; }
[[ ! -e "$D/STOP" ]] || exit 70
out="$D/calibration-attempts/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$D/calibration-attempts"
[[ $(df --output=avail -BG "$D" | tail -1 | tr -dc 0-9) -ge 151 ]] || exit 70
[[ "${FILLER_DEADLINE:-}" =~ ^[0-9]+$ ]] || exit 70
seconds=$((FILLER_DEADLINE-$(date +%s)-15)); ((seconds > 0)) || exit 75
set +e
python3 "$D/native_runner.py" "$out" "$seconds" /bin/bash "$D/calibration_body.sh" "$out" > "$out.supervisor.log" 2>&1
rc=$?
set -e
[[ -s "$out/CLEANUP.json" ]] || exit 70
python3 "$D/write_state.py" "$out" "$rc" normal
if [[ "$rc" != 0 ]]; then /mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/release_failed_claim.py" "$out"; fi
exit "$rc"
