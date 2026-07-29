#!/bin/bash
# Human-only E8 bootstrap transaction. It admits an intentionally empty E8
# frontier for the first fresh trials; it does not alter a baseline or era fence.
set -euo pipefail

ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
ORCH="${EPYC_ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
PYTHON="${EPYC_PYTHON:-$ORCH/.venv/bin/python}"
STATE="$ORCH/orchestration/autopilot_state.json"
ERAS="$ORCH/orchestration/instrument_eras.yaml"
JOURNAL="$ORCH/orchestration/autopilot_journal.jsonl"
E8_RECEIPT="$ROOT/artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.json"
E8_RECEIPT_SHA256="313a8129336ec4ad6149bfb04541cb5a2bacd79568e0ce06efdba9718b43437c"
# This is the reviewed recovery fix. The subsequent rearm receipt makes this
# immutable launch authority rather than trusting whatever happens to be HEAD.
REVIEWED_ORCHESTRATOR_HEAD="f3ba7e9d13891de368db0e3100d2357d18122aee"
SCRIPT_REL="artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.sh"
TOKEN="RATIFY-E8-EMPTY-FRONTIER-BOOTSTRAP"
OUTPUT="$ROOT/artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.json"
TXN_DIR="$ROOT/artifacts/operator/e8-empty-frontier-bootstrap-20260726"
LOCK="$ROOT/artifacts/operator/.e8-empty-frontier-bootstrap.lock"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha256() { sha256sum -- "$1" | awk '{print $1}'; }

autopilot_running() {
    pgrep -f '[s]cripts/autopilot/autopilot.py start' >/dev/null ||
        pgrep -f '[s]cripts/autopilot/autopilot_supervisor.py' >/dev/null
}

validate_current_era_replay_empty() {
    ( cd "$ORCH"; "$PYTHON" - "$STATE" "$JOURNAL" <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, "scripts/autopilot")
from src.autopilot_core.journal_reconstruction import reconstruct_archive_from_journal_rows

state_path, journal_path = map(Path, sys.argv[1:])
state = json.loads(state_path.read_text())
rows = [json.loads(line) for line in journal_path.read_text().splitlines() if line.strip()]
archive = reconstruct_archive_from_journal_rows(
    rows,
    None,
    current_run_only=False,
    deinflate_before_ts=state.get("pareto_epoch_ts"),
    deinflate_factor=state.get("pareto_pre_epoch_speed_factor", 0.5),
    exclude_before_ts=state.get("pareto_exclude_before_ts"),
)
if archive is not None:
    raise SystemExit("current-era journal replay is non-empty; empty-frontier bootstrap is unsafe")
PY
    )
}

validate_pre_state() {
    [[ -x "$PYTHON" && -f "$STATE" && -f "$ERAS" && -f "$JOURNAL" ]] || fail 'orchestrator prerequisites are missing'
    git -C "$ROOT" ls-files --error-unmatch -- "$SCRIPT_REL" >/dev/null || fail 'operator script must be committed before ratification'
    git -C "$ROOT" diff --quiet -- "$SCRIPT_REL" || fail 'operator script has unstaged changes'
    git -C "$ROOT" diff --cached --quiet -- "$SCRIPT_REL" || fail 'operator script has staged changes'
    autopilot_running && fail 'AutoPilot is running; stop it before opening the bootstrap'
    [[ -f "$E8_RECEIPT" ]] || fail 'E8 quality-fence receipt is absent'
    [[ "$(sha256 "$E8_RECEIPT")" == "$E8_RECEIPT_SHA256" ]] || fail 'E8 quality-fence receipt hash is not the ratified original'
    [[ "$(git -C "$ORCH" rev-parse HEAD)" == "$REVIEWED_ORCHESTRATOR_HEAD" ]] ||
        fail "orchestrator HEAD is not reviewed bootstrap authority $REVIEWED_ORCHESTRATOR_HEAD"
    # The E8 registry row is a human-attested, intentionally uncommitted delta.
    # No other tracked orchestrator source may vary from the reviewed authority.
    git -C "$ORCH" diff --quiet -- . ':(exclude)orchestration/instrument_eras.yaml' ||
        fail 'orchestrator tree has tracked modifications outside the attested era registry'
    git -C "$ORCH" diff --cached --quiet -- . ':(exclude)orchestration/instrument_eras.yaml' ||
        fail 'orchestrator index has staged modifications outside the attested era registry'
    jq -e --arg eras "$(sha256 "$ERAS")" --arg state "$(sha256 "$STATE")" '
        .decision == "RATIFY-E8-AUTOPILOT-QUALITY-FENCE" and
        .quality_era.id == "E8" and .sha256.instrument_eras == $eras and .sha256.autopilot_state == $state
    ' "$E8_RECEIPT" >/dev/null || fail 'E8 receipt does not bind the current state and registry'
    jq -e '
        .active_instrument_eras.autopilot_speed == "E8-autopilot-speed" and
        .active_instrument_eras.eval_quality == "E8" and
        .pareto_epoch_ts == 1785004723.0 and .pareto_exclude_before_ts == 1785004723.0 and
        (.frontier_rerun_required.required == true) and
        (.frontier_rerun_required.completed_numeric_trials == 0) and
        (.frontier_rerun_required.min_numeric_trials == 16) and
        (._allow_empty_frontier_rebase // false) == false
    ' "$STATE" >/dev/null || fail 'state is not the exact unbootstrapped E8 posture'
    validate_current_era_replay_empty
}

write_state() {
    "$PYTHON" - "$STATE" <<'PY'
import json
import os
from pathlib import Path
import sys

path = Path(sys.argv[1])
state = json.loads(path.read_text())
if state.get("_allow_empty_frontier_rebase"):
    raise SystemExit("empty-frontier bootstrap is already active")
state["_allow_empty_frontier_rebase"] = True
state["e8_empty_frontier_bootstrap"] = {
    "status": "active",
    "reason": "E8 current-era replay intentionally empty; permit fresh frontier bootstrap",
    "required_clear_condition": (
        "next AutoPilot startup observes at least one current-era Pareto point"
    ),
}
tmp = path.with_suffix(path.suffix + ".e8-empty-frontier.tmp")
tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
os.chmod(tmp, path.stat().st_mode)
os.replace(tmp, path)
PY
}

validate_post_state() {
    "$PYTHON" - "$STATE" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "scripts/autopilot")
from pareto_archive import ParetoArchive
import json

state = json.loads(Path(sys.argv[1]).read_text())
assert state["_allow_empty_frontier_rebase"] is True
assert state["e8_empty_frontier_bootstrap"]["status"] == "active"
archive = ParetoArchive(state_path=Path(sys.argv[1]))
assert archive.frontier_size() == 0
PY
}

write_attestation() {
    "$PYTHON" - "$OUTPUT" "$E8_RECEIPT" "$STATE" "$ERAS" "$ROOT" "$ORCH" "$REVIEWED_ORCHESTRATOR_HEAD" <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

out, receipt, state, eras, root, orch, reviewed_head = sys.argv[1:]
out, receipt, state, eras, root, orch = map(Path, (out, receipt, state, eras, root, orch))
actual_head = __import__("subprocess").check_output(
    ["git", "-C", str(orch), "rev-parse", "HEAD"], text=True
).strip()
if actual_head != reviewed_head:
    raise SystemExit("orchestrator HEAD changed while writing bootstrap receipt")
state_payload = json.loads(state.read_text())
payload = {
    "schema": "epyc.operator_e8_empty_frontier_bootstrap.v1",
    "decision": "RATIFY-E8-EMPTY-FRONTIER-BOOTSTRAP",
    "ratified_at": datetime.now(timezone.utc).isoformat(),
    "parent_e8_quality_fence_sha256": __import__("hashlib").sha256(receipt.read_bytes()).hexdigest(),
    "reviewed_orchestrator_head": reviewed_head,
    "state_delta": {
        "_allow_empty_frontier_rebase": state_payload["_allow_empty_frontier_rebase"],
        "e8_empty_frontier_bootstrap": state_payload["e8_empty_frontier_bootstrap"],
    },
    "clear_condition": (
        "next AutoPilot startup observes at least one current-era Pareto point"
    ),
    "sha256": {
        "autopilot_state": __import__("hashlib").sha256(state.read_bytes()).hexdigest(),
        "instrument_eras": __import__("hashlib").sha256(eras.read_bytes()).hexdigest(),
    },
    "repository_heads": {
        "epyc_root": __import__("subprocess").check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "epyc_orchestrator": actual_head,
    },
}
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
}

transaction_started=0
rollback_on_exit() {
    local status=$?
    trap - EXIT
    if (( status != 0 && transaction_started == 1 )); then
        cp -p -- "$TXN_DIR/autopilot_state.json.before" "$STATE"
        rm -f -- "$OUTPUT"
        mv -- "$TXN_DIR" "${TXN_DIR}.rolled-back.$(date -u +%Y%m%dT%H%M%SZ)"
        printf 'ERROR: E8 bootstrap failed; state preimage restored.\n' >&2
    fi
    exit "$status"
}

plan() {
    cat <<EOF
E8 empty-frontier bootstrap transaction plan
- require the current E8 quality-fence receipt and its exact state/era hashes
- require reviewed recovery authority at $REVIEWED_ORCHESTRATOR_HEAD with no source drift
- require zero completed E8 numeric trials and an empty E8-only journal replay
- atomically set _allow_empty_frontier_rebase=true
- leave all era, quality, baseline, and frontier-rerun values unchanged
- retire the bypass at the next AutoPilot startup after a current-era Pareto point exists
EOF
}

main() {
    case "${1:-}" in
        --plan) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--status|--attest TOKEN'; plan; return ;;
        --status) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--status|--attest TOKEN'; [[ -f "$OUTPUT" ]] && jq . "$OUTPUT" || printf 'No E8 bootstrap attestation exists.\n'; return ;;
        --validate-only) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--status|--attest TOKEN'; validate_pre_state; printf 'E8 empty-frontier bootstrap preflight passed; no files changed.\n'; return ;;
        --attest) [[ $# -eq 2 && "$2" == "$TOKEN" ]] || fail "usage: $0 --attest $TOKEN" ;;
        *) fail "usage: $0 --plan|--validate-only|--status|--attest $TOKEN" ;;
    esac
    [[ ! -e "$OUTPUT" && ! -e "$TXN_DIR" ]] || fail 'prior bootstrap transaction exists; inspect --status'
    validate_pre_state
    exec 9>>"$LOCK"; flock -n 9 || fail 'another E8 bootstrap transaction is active'
    exec 8>>"$ORCH/orchestration/.autopilot.lock"; flock -n 8 || fail 'AutoPilot lifecycle lock is held'
    exec 7>>"$STATE.lock"; flock -n 7 || fail 'AutoPilot state lock is held'
    validate_pre_state
    mkdir "$TXN_DIR"
    cp -p -- "$STATE" "$TXN_DIR/autopilot_state.json.before"
    transaction_started=1
    trap rollback_on_exit EXIT
    write_state
    ( cd "$ORCH"; validate_post_state )
    write_attestation
    printf 'E8 empty-frontier bootstrap attestation created:\n%s\n' "$OUTPUT"
    sha256sum "$OUTPUT"
}

main "$@"
