#!/bin/bash
# Human-only E8 quality-fence transaction. It opens a rebaseline hold; it does
# not seed new baseline values or change the production model lineup.
set -euo pipefail

ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
ORCH="${EPYC_ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
PROD="${EPYC_PROD:-/mnt/raid0/llm/llama.cpp}"
PYTHON="$ORCH/.venv/bin/python"
ERAS="$ORCH/orchestration/instrument_eras.yaml"
STATE="$ORCH/orchestration/autopilot_state.json"
SCRIPT_REL="artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh"
BOUNDARY_ISO="2026-07-25T18:38:43Z"
BOUNDARY_EPOCH="1785004723.0"
TOKEN="RATIFY-E8-AUTOPILOT-QUALITY-FENCE"
OUTPUT="$ROOT/artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.json"
TXN_DIR="$ROOT/artifacts/operator/e8-autopilot-quality-fence-20260726"
LOCK="$ROOT/artifacts/operator/.e8-autopilot-quality-fence.lock"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha256() { sha256sum -- "$1" | awk '{print $1}'; }

autopilot_running() {
    pgrep -f '[s]cripts/autopilot/autopilot.py start' >/dev/null ||
        pgrep -f '[s]cripts/autopilot/autopilot_supervisor.py' >/dev/null
}

validate_live_stack() {
    local health
    health="$(curl -fsS --max-time 10 http://127.0.0.1:8000/health)" || fail 'orchestrator API health request failed'
    jq -e '.status == "ok" and .models_loaded == 6 and (.backend_probes | type == "object") and ([.backend_probes[] | select(.ok == true)] | length == 6) and ([.backend_probes[]] | length == 6)' <<<"$health" >/dev/null || fail 'current both-mode API is not healthy 6/6'
}

validate_production() {
    [[ "$(git -C "$PROD" branch --show-current)" == "production-consolidated-v8" ]] || fail 'production tree is not on production-consolidated-v8'
    [[ "$(git -C "$PROD" rev-parse HEAD)" == "67a433bf45a8a091d83b4ea0b32ff0735fd51800" ]] || fail 'production tree is not at frozen v8 tip'
    git -C "$PROD" diff --quiet || fail 'production tree has tracked modifications'
    git -C "$PROD" diff --cached --quiet || fail 'production index has staged modifications'
}

validate_pre_state() {
    [[ -x "$PYTHON" && -f "$ERAS" && -f "$STATE" ]] || fail 'orchestrator venv, era registry, or AutoPilot state is missing'
    git -C "$ROOT" ls-files --error-unmatch -- "$SCRIPT_REL" >/dev/null || fail 'operator script must be committed before ratification'
    git -C "$ROOT" diff --quiet -- "$SCRIPT_REL" || fail 'operator script has unstaged changes'
    git -C "$ROOT" diff --cached --quiet -- "$SCRIPT_REL" || fail 'operator script has staged changes'
    git -C "$ORCH" diff --quiet -- orchestration/instrument_eras.yaml || fail 'instrument era registry has unstaged changes'
    git -C "$ORCH" diff --cached --quiet -- orchestration/instrument_eras.yaml || fail 'instrument era registry has staged changes'
    autopilot_running && fail 'AutoPilot is running; stop it before opening the quality fence'
    jq -e --arg epoch "$BOUNDARY_EPOCH" '.active_instrument_eras.autopilot_speed == "E8-autopilot-speed" and (.active_instrument_eras.eval_quality // "") != "E8" and .baseline_state.eval_quality_era == "E7-eval-instrument" and (.frontier_rerun_required.required == true) and (.pareto_exclude_before_ts == ($epoch | tonumber))' "$STATE" >/dev/null || fail 'state does not match the expected pre-E8-quality-fence posture'
    "$PYTHON" - "$ERAS" <<'PY'
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
try:
    registry = yaml.safe_load(path.read_text())
except yaml.YAMLError as exc:
    raise SystemExit(f"instrument-era registry is invalid YAML: {exc}")
if not isinstance(registry, dict) or not isinstance(registry.get("eras"), list):
    raise SystemExit("instrument-era registry must contain a top-level eras list")
if any(
    isinstance(row, dict)
    and row.get("id") == "E8"
    and row.get("scope") == "eval_quality"
    for row in registry["eras"]
):
    raise SystemExit("E8 eval-quality row already exists; use --status or inspect the prior transaction")
PY
}

validate_post_state() {
    AUTOPILOT_INSTRUMENT_ERAS_PATH="$ERAS" "$PYTHON" - "$STATE" <<'PY'
from scripts.autopilot.autopilot import _quality_epoch_params_from_state
from src.autopilot_core.instrument_era_guard import active_eval_quality_era
import json
from pathlib import Path
import sys

state = json.loads(Path(sys.argv[1]).read_text())
era, boundary = _quality_epoch_params_from_state(state)
guard = active_eval_quality_era()
assert era == 'E8', era
assert boundary == 1785004723.0, boundary
assert guard['ok'] and guard['era_id'] == 'E8', guard
assert state['baseline_state']['eval_quality_era'] == 'E7-eval-instrument'
PY
}

plan() {
    cat <<EOF
E8 quality-fence transaction plan
- append human-owned eval_quality era: E8 from $BOUNDARY_ISO
- set active_instrument_eras.eval_quality=E8
- set quality_epoch_ts=quality_exclude_before_ts=$BOUNDARY_EPOCH
- preserve E7 baseline values and quality histories as historical priors
- open the existing fail-closed rebaseline hold; no baseline value is seeded
- required E8 re-arm environment: AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES=kv_compaction
EOF
}

write_era() {
    "$PYTHON" - "$ERAS" "$BOUNDARY_ISO" <<'PY'
import os
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
boundary = sys.argv[2]
source = path.read_text()
try:
    registry = yaml.safe_load(source)
except yaml.YAMLError as exc:
    raise SystemExit(f"instrument-era registry is invalid YAML: {exc}")
if not isinstance(registry, dict) or not isinstance(registry.get("eras"), list):
    raise SystemExit("instrument-era registry must contain a top-level eras list")
if any(
    isinstance(row, dict)
    and row.get("id") == "E8"
    and row.get("scope") == "eval_quality"
    for row in registry["eras"]
):
    raise SystemExit("E8 eval-quality row already exists")

lines = source.splitlines(keepends=True)
try:
    insert_at = next(
        index
        for index, line in enumerate(lines)
        if line.rstrip("\n") == "known_dead_instrument_items:"
    )
except StopIteration as exc:
    raise SystemExit("instrument-era registry lacks known_dead_instrument_items anchor") from exc

entry = (
    "  - id: E8\n"
    f"    from: \"{boundary}\"\n"
    "    scope: eval_quality\n"
    "    note: >\n"
    "      v8 production quality-boundary. This opens a fail-closed E8 AutoPilot rebaseline hold:\n"
    "      pre-v8/E7 baseline and MAD observations are historical priors until an operator-ratified\n"
    "      E8 quality-baseline reseed writes fresh values and windows. No model-lineup or model-registry change.\n\n"
)
candidate = "".join(lines[:insert_at]) + entry + "".join(lines[insert_at:])
try:
    updated = yaml.safe_load(candidate)
except yaml.YAMLError as exc:
    raise SystemExit(f"E8 insertion would produce invalid YAML: {exc}") from exc
rows = updated.get("eras") if isinstance(updated, dict) else None
matches = [
    row for row in rows or []
    if isinstance(row, dict) and row.get("id") == "E8" and row.get("scope") == "eval_quality"
]
if len(matches) != 1 or matches[0].get("from") != boundary:
    raise SystemExit("E8 insertion did not create exactly one top-level eval_quality era")

tmp = path.with_suffix(path.suffix + ".e8-quality.tmp")
tmp.write_text(candidate)
os.chmod(tmp, path.stat().st_mode)
os.replace(tmp, path)
PY
}

write_state() {
    "$PYTHON" - "$STATE" "$BOUNDARY_EPOCH" <<'PY'
import json
import os
from pathlib import Path
import sys
path = Path(sys.argv[1]); epoch = float(sys.argv[2])
state = json.loads(path.read_text())
eras = state.setdefault('active_instrument_eras', {})
if eras.get('eval_quality') not in (None, '', 'E8'):
    raise SystemExit(f"refusing to replace active eval_quality era {eras['eval_quality']!r}")
eras['eval_quality'] = 'E8'
state['quality_epoch_ts'] = epoch
state['quality_exclude_before_ts'] = epoch
state['e8_quality_rebaseline'] = {'boundary': '2026-07-25T18:38:43Z', 'status': 'hold_open', 'required_next_action': 'human-only E8 baseline value reseed after fresh evidence'}
tmp = path.with_suffix(path.suffix + '.e8-quality.tmp')
tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + '\n')
os.chmod(tmp, path.stat().st_mode)
os.replace(tmp, path)
PY
}

write_attestation() {
    local ts script_sha eras_sha state_sha root_head orch_head
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"; script_sha="$(sha256 "$ROOT/$SCRIPT_REL")"; eras_sha="$(sha256 "$ERAS")"; state_sha="$(sha256 "$STATE")"
    root_head="$(git -C "$ROOT" rev-parse HEAD)"; orch_head="$(git -C "$ORCH" rev-parse HEAD)"
    "$PYTHON" - "$OUTPUT" "$ts" "$script_sha" "$eras_sha" "$state_sha" "$root_head" "$orch_head" <<'PY'
import json
from pathlib import Path
import sys
payload = {
  'schema': 'epyc.operator_e8_autopilot_quality_fence.v1', 'decision': 'RATIFY-E8-AUTOPILOT-QUALITY-FENCE', 'ratified_at': sys.argv[2],
  'production': {'branch': 'production-consolidated-v8', 'head': '67a433bf45a8a091d83b4ea0b32ff0735fd51800'},
  'quality_era': {'id': 'E8', 'scope': 'eval_quality', 'from': '2026-07-25T18:38:43Z'},
  'state_delta': {'active_instrument_eras.eval_quality': 'E8', 'quality_epoch_ts': 1785004723.0, 'quality_exclude_before_ts': 1785004723.0, 'baseline_state.eval_quality_era': 'preserved E7-eval-instrument until later E8 reseed'},
  'rebaseline_hold': True, 'required_autopilot_env': {'AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES': 'kv_compaction'},
  'next_human_action': 'ratify E8 baseline values and MAD windows after fresh E8 evidence',
  'repository_heads': {'epyc_root': sys.argv[6], 'epyc_orchestrator': sys.argv[7]},
  'sha256': {'operator_script': sys.argv[3], 'instrument_eras': sys.argv[4], 'autopilot_state': sys.argv[5]},
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
PY
}

transaction_started=0
rollback_on_exit() {
    local status=$?
    trap - EXIT
    if (( status != 0 && transaction_started == 1 )); then
        printf 'ERROR: transaction failed; restoring E8 quality-fence preimages.\n' >&2
        cp -p -- "$TXN_DIR/instrument_eras.yaml.before" "$ERAS"
        cp -p -- "$TXN_DIR/autopilot_state.json.before" "$STATE"
        rm -f -- "$OUTPUT"
        mv -- "$TXN_DIR" "${TXN_DIR}.rolled-back.$(date -u +%Y%m%dT%H%M%SZ)"
    fi
    exit "$status"
}

main() {
    case "${1:-}" in
        --plan) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--status|--attest TOKEN'; plan; return ;;
        --status) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--status|--attest TOKEN'; [[ -f "$OUTPUT" ]] && jq . "$OUTPUT" || printf 'No E8 quality-fence attestation exists.\n'; return ;;
        --validate-only) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--status|--attest TOKEN'; validate_production; validate_live_stack; validate_pre_state; printf 'E8 quality-fence preflight passed; no files changed.\n'; return ;;
        --attest) [[ $# -eq 2 && "$2" == "$TOKEN" ]] || fail "usage: $0 --attest $TOKEN" ;;
        *) fail "usage: $0 --plan|--validate-only|--status|--attest $TOKEN" ;;
    esac
    [[ ! -e "$OUTPUT" && ! -e "$TXN_DIR" ]] || fail 'prior E8 quality-fence transaction exists; inspect --status'
    validate_production; validate_live_stack; validate_pre_state
    exec 9>>"$LOCK"; flock -n 9 || fail 'another E8 quality-fence transaction is active'
    exec 8>>"$ORCH/orchestration/.autopilot.lock"; flock -n 8 || fail 'AutoPilot lifecycle lock is held'
    exec 7>>"$STATE.lock"; flock -n 7 || fail 'AutoPilot state lock is held'
    validate_live_stack; validate_pre_state
    mkdir "$TXN_DIR"
    cp -p -- "$ERAS" "$TXN_DIR/instrument_eras.yaml.before"
    cp -p -- "$STATE" "$TXN_DIR/autopilot_state.json.before"
    transaction_started=1
    trap rollback_on_exit EXIT
    write_era
    write_state
    ( cd "$ORCH"; "$PYTHON" -m pytest -q tests/unit/test_instrument_era_guard_eval_quality.py tests/unit/test_safety_gate_eval_quality_era.py tests/unit/test_autopilot_creativity.py; validate_post_state )
    write_attestation
    printf 'E8 quality-fence attestation created:\n%s\n' "$OUTPUT"
    sha256sum "$OUTPUT"
    printf 'The rebaseline hold is open. Restart AutoPilot only with AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES=kv_compaction.\n'
}

main "$@"
