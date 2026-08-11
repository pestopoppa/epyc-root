#!/bin/bash
# Human-only single-field state advance: autopilot_state.json
# active_instrument_eras.cpu_bench  E8-cpu-kernel -> E9-cpu-kernel.
#
# Why this exists: the operator-signed consolidated era token (21:35:01Z) added the
# E9-cpu-kernel row to the REGISTRY, but nothing is wired to advance the STATE
# consumer — the v8 precedent (ratify_v8_era_fence_20260725.sh) wrote both in one
# transaction, and no v9 analogue existed. The v10 multitier seal already advanced
# autopilot_speed/eval_quality; ONLY cpu_bench lagged. Downstream readers of the
# stale field: dashboard Pareto endpoint (src/api/routes/dashboard.py:~5539).
#
# Deliberately NOT written by this script: scripts/autopilot/system_card.md — it is
# GENERATED (gen_system_card.py) and already stale on autopilot_speed too;
# regeneration belongs to the autopilot resume checklist, not a state fence.
#
# Edit mechanism: exact-substring replacement asserted to occur EXACTLY once, then
# full-JSON re-parse asserting the ONLY semantic change is this one field. No
# whole-file sha pin (autopilot state is live-mutable when autopilot runs); instead
# the semantic precondition cpu_bench==E8-cpu-kernel refuses on any drift, and the
# autopilot lock is held for the write.
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811"
ROOT="/mnt/raid0/llm/epyc-root"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
STATE="$ORCH/orchestration/autopilot_state.json"
ERAS="$ORCH/orchestration/instrument_eras.yaml"
SOURCE_RECEIPT="$ROOT/artifacts/operator/ratify_consolidated_era_rows_20260811.json"
RECEIPT="$ROOT/artifacts/operator/ratify_v9_cpu_bench_era_advance_20260811.json"
AUTOPILOT_LOCK="$ORCH/orchestration/.autopilot.lock"
TRUST_LOCK="/run/lock/epyc-measurement-trust-boundary.lock"
PYTHON="/usr/bin/python3"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() { printf 'usage: %s --validate-only | --attest %s\n' "$0" "$TOKEN" >&2; }
case "${1:-}" in
    --validate-only) [[ $# == 1 ]] || { usage; exit 2; }; MODE="validate" ;;
    --attest) [[ $# == 2 && "$2" == "$TOKEN" ]] || { usage; exit 2; }; MODE="attest" ;;
    *) usage; exit 2 ;;
esac

[[ -x "$PYTHON" ]] || fail "trusted interpreter unavailable"
[[ -f "$STATE" && -f "$ERAS" && -f "$SOURCE_RECEIPT" ]] || fail "required inputs missing"
[[ "$MODE" != "attest" || ! -e "$RECEIPT" ]] || fail "receipt already exists (token is SPENT): $RECEIPT"
[[ "$MODE" != "attest" || ! -e "$ROOT/artifacts/operator/receipts/$TOKEN.json" ]] || fail "receipt index already exists (token is SPENT)"
# No process-pattern probe (host rule: never pgrep by name) — the autopilot lock
# flock below IS the running-autopilot guard: a live autopilot holds it.
mkdir -p -- "$(dirname -- "$TRUST_LOCK")"
exec 8<>"$TRUST_LOCK"
/usr/bin/flock -n 8 || fail "measurement trust-boundary lock is already held"
exec 9<>"$AUTOPILOT_LOCK"
/usr/bin/flock -n 9 || fail "autopilot lock is already held"

"$PYTHON" - "$MODE" "$STATE" "$ERAS" "$SOURCE_RECEIPT" "$RECEIPT" "$TOKEN" <<'PY'
import hashlib, json, os, sys, tempfile
from datetime import UTC, datetime

mode, state_path, eras_path, source_receipt, receipt, token = sys.argv[1:]

src = json.load(open(source_receipt, encoding="utf-8"))
if src.get("status") != "ratified" or src.get("human_attestation") != "RATIFY-CONSOLIDATED-ERA-ROWS-20260811":
    raise SystemExit("source era-token receipt is not the ratified consolidated-era receipt; refuse")
if "E9-cpu-kernel" not in (src.get("applied_rows") or []):
    raise SystemExit("source receipt does not record E9-cpu-kernel as applied; refuse")

eras_text = open(eras_path, encoding="utf-8").read()
if "id: E9-cpu-kernel" not in eras_text:
    raise SystemExit("registry does not carry the E9-cpu-kernel row; refuse")

original = open(state_path, encoding="utf-8").read()
doc = json.loads(original)
active = doc.get("active_instrument_eras") or {}
if active.get("cpu_bench") != "E8-cpu-kernel":
    raise SystemExit(f"state cpu_bench is {active.get('cpu_bench')!r}, expected the exact E8-cpu-kernel predecessor; refuse")

OLD = '"cpu_bench": "E8-cpu-kernel"'
NEW = '"cpu_bench": "E9-cpu-kernel"'
n = original.count(OLD)
if n != 1:
    raise SystemExit(f"edit-site occurs {n} times, expected exactly 1; refuse")
candidate = original.replace(OLD, NEW, 1)

cand = json.loads(candidate)
if cand["active_instrument_eras"]["cpu_bench"] != "E9-cpu-kernel":
    raise SystemExit("candidate field did not advance; refuse")
cand["active_instrument_eras"]["cpu_bench"] = "E8-cpu-kernel"
if cand != doc:
    raise SystemExit("candidate changes MORE than the one field; refuse")

print("precondition: source receipt ratified, E9-cpu-kernel applied and present in registry")
print("edit: active_instrument_eras.cpu_bench E8-cpu-kernel -> E9-cpu-kernel (single site, sole semantic change)")
print(f"candidate state sha256: {hashlib.sha256(candidate.encode()).hexdigest()}")

if mode == "validate":
    print("preflight-valid")
    raise SystemExit(0)

fd, tmp = tempfile.mkstemp(dir=os.path.dirname(state_path), prefix=".era-advance-")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(candidate)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, state_path)
except BaseException:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise
dfd = os.open(os.path.dirname(state_path), os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(dfd)
finally:
    os.close(dfd)

payload = {
    "schema": "epyc.operator_v9_cpu_bench_era_advance.v1",
    "status": "ratified",
    "human_attestation": token,
    "ratified_at": datetime.now(UTC).isoformat(),
    "target": state_path,
    "field": "active_instrument_eras.cpu_bench",
    "from_value": "E8-cpu-kernel",
    "to_value": "E9-cpu-kernel",
    "source_era_receipt": {"path": source_receipt,
                           "human_attestation": "RATIFY-CONSOLIDATED-ERA-ROWS-20260811"},
    "state_sha256_after": hashlib.sha256(candidate.encode()).hexdigest(),
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
index_dir = os.path.join(os.path.dirname(receipt), "receipts")
os.makedirs(index_dir, exist_ok=True)
index_path = os.path.join(index_dir, f"{token}.json")
with open(index_path, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": token, "indexed_by": "attest", "receipt": receipt,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
print(f"ratified: {receipt}")
print(f"receipt index: {index_path}")
PY
