#!/bin/bash
# Human-only Annex G currency amendment. Updates the two P-GPU-1 kernel-currency
# parentheticals in measurement/protocols/gpu-cross-device.md from v8 (67a433bf4)
# to v9 (0db32c06e) and appends a dated amendment note. Changes NOTHING else:
# the provenance rule, evidence fields, and every other clause are byte-identical.
# Never runs inference. Whole-file sha256 pinned — this annex is human-only and
# low-churn, so a file pin is appropriate here (unlike instrument_eras.yaml).
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-ANNEXG-V9-CURRENCY-20260811"
ROOT="/mnt/raid0/llm/epyc-root"
TARGET="$ROOT/measurement/protocols/gpu-cross-device.md"
RECEIPT="$ROOT/artifacts/operator/ratify_annexg_v9_currency_20260811.json"
EXPECTED_SHA256="ca47e4e6432b7de426c69bb86557b29ae0d6e32d7d1adbcfb8d632eab59b3a83"
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
[[ -f "$TARGET" ]] || fail "annex file is missing: $TARGET"
[[ "$MODE" != "attest" || ! -e "$RECEIPT" ]] || fail "receipt already exists (token is SPENT): $RECEIPT"
[[ "$MODE" != "attest" || ! -e "$ROOT/artifacts/operator/receipts/$TOKEN.json" ]] || fail "receipt index already exists (token is SPENT): receipts/$TOKEN.json"
[[ "$(sha256sum -- "$TARGET" | awk '{print $1}')" == "$EXPECTED_SHA256" ]] ||
    fail "annex preimage sha256 differs from the pinned ratified text; re-present, do not force"
if [[ "$MODE" == "attest" ]]; then
    git -C "$ROOT" diff --quiet -- measurement/protocols/gpu-cross-device.md || fail "annex has unstaged changes"
    git -C "$ROOT" diff --cached --quiet -- measurement/protocols/gpu-cross-device.md || fail "annex has staged changes"
fi

mkdir -p -- "$(dirname -- "$TRUST_LOCK")"
exec 8<>"$TRUST_LOCK"
/usr/bin/flock -n 8 || fail "measurement trust-boundary lock is already held"

"$PYTHON" - "$MODE" "$TARGET" "$RECEIPT" "$TOKEN" <<'PY'
import hashlib, json, os, sys, tempfile
from datetime import UTC, datetime

mode, target, receipt, token = sys.argv[1:]
original = open(target, "r", encoding="utf-8").read()

EDITS = [
    # Site 1: P-GPU-1 kernel-provenance rule parenthetical (lines ~17-18).
    ("; currently v8\n`67a433bf4`). Measurements",
     "; currently v9\n`0db32c06e`). Measurements"),
    # Site 2: P-SHED decision-grade requirements parenthetical (lines ~167-168).
    ("(currently\nv8 `67a433bf4`) per the P-GPU-1 provenance rule",
     "(currently\nv9 `0db32c06e`) per the P-GPU-1 provenance rule"),
]
NOTE = (
    "\n<!-- AMENDED per RATIFY-ANNEXG-V9-CURRENCY-20260811: the two P-GPU-1\n"
    "     kernel-currency parentheticals track the CURRENT production kernel and moved\n"
    "     v8 (67a433bf4, binary 10107) -> v9 (0db32c06e, binary 10125) at the\n"
    "     2026-08-10T23:59:00Z cutover (ratify_v9_final_freeze_20260811.json, ratified\n"
    "     2026-08-11T01:16:00Z). Decision-grade claims produced on v8 while v8 was the\n"
    "     production kernel remain decision-grade for their era; from the cutover, new\n"
    "     P-GPU-1 decision-grade claims require production-consolidated-v9. No other\n"
    "     clause of this annex is changed by this amendment. -->\n"
)

candidate = original
for old, new in EDITS:
    n = candidate.count(old)
    if n != 1:
        raise SystemExit(f"edit-site text occurs {n} times, expected exactly 1; refuse: {old[:40]!r}")
    candidate = candidate.replace(old, new, 1)
candidate += NOTE
if candidate.count("67a433bf4") != 1:
    # the sole survivor is the historical reference inside the amendment note
    raise SystemExit("unexpected residual v8-currency references; refuse")
if "currently v8" in candidate:
    raise SystemExit("a currently-v8 clause survived; refuse")

print("site 1 (P-GPU-1 provenance parenthetical): OK")
print("site 2 (decision-grade requirements parenthetical): OK")
print(f"candidate sha256: {hashlib.sha256(candidate.encode()).hexdigest()}")

if mode == "validate":
    print("preflight-valid")
    raise SystemExit(0)

fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".annexg-")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(candidate)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)
except BaseException:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise
dfd = os.open(os.path.dirname(target), os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(dfd)
finally:
    os.close(dfd)

payload = {
    "schema": "epyc.operator_annexg_v9_currency.v1",
    "status": "ratified",
    "human_attestation": token,
    "ratified_at": datetime.now(UTC).isoformat(),
    "target": target,
    "preimage_sha256": "ca47e4e6432b7de426c69bb86557b29ae0d6e32d7d1adbcfb8d632eab59b3a83",
    "amended_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
# Keyed receipt-index pointer (C39 contract): the daemon's spent-gate check stats
# exactly artifacts/operator/receipts/<GATE_ID>.json, so write it at signing time.
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
