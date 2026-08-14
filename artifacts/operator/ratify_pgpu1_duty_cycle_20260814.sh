#!/bin/bash
# Human-only P-GPU-1 `duty_cycle` amendment (AK-OP-1 / master-index OP-10).
#
# Adds mandatory field 7 `duty_cycle: bursty | sustained` to
# measurement/protocols/gpu-cross-device.md and declares the canonical
# `fresh server per rep` recipe `bursty`. PURE LABELLING — invalidates nothing:
# every existing P-GPU-1 number stays valid and correctly labelled `bursty`.
#
# Why: P-GPU-1 field 4's "fresh server per rep" inserts a multi-second gap
# between reps, so it measures the BURSTY duty cycle while production serves
# the SUSTAINED one. Both regimes are legitimate; conflating them is not, and a
# protocol that does not name its duty cycle cannot be compared against one that
# does. Option (b) — authoring a sustained variant — is deferred until the first
# sustained-serving claim needs it (AK-OP-1 recommendation: (a) now, (b) later).
#
# Trust-boundary: human-amendment-only (MEASUREMENT.md + AK-D10). No session may
# self-apply this. Never runs inference. Whole-file sha256 pinned.
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-PGPU1-DUTY-CYCLE-20260814"
ROOT="/mnt/raid0/llm/epyc-root"
TARGET="$ROOT/measurement/protocols/gpu-cross-device.md"
RECEIPT="$ROOT/artifacts/operator/ratify_pgpu1_duty_cycle_20260814.json"
EXPECTED_SHA256="6eb9acc467ecc1fd4978ddd5061a42122bf3ce17e2bd7b303e7b5819aa341423"
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
    # Site 1: field 4 — name the bursty duty cycle of "fresh server per rep".
    ("warm-up policy; **fresh server per rep** unless resident-server mode",
     "warm-up policy; **fresh server per rep** (duty cycle `bursty` — see field 7) unless\n   resident-server mode"),
    # Site 2: insert mandatory field 7 after field 6 (Attestation).
    ("6. **Attestation** — `metric [P-GPU-1, n/reps, YYYY-MM-DD, attest <ref>]`.\n",
     "6. **Attestation** — `metric [P-GPU-1, n/reps, YYYY-MM-DD, attest <ref>]`.\n"
     "7. **Duty cycle** — `duty_cycle: bursty | sustained`, declared per claim. The canonical\n"
     "   recipe (`fresh server per rep`) is `bursty` by construction: a fresh server per repetition\n"
     "   inserts a multi-second gap between reps, so the protocol measures the bursty duty cycle\n"
     "   while production serves the sustained one. Both regimes are legitimate to measure;\n"
     "   conflating them is not, and a protocol that does not name its duty cycle cannot be compared\n"
     "   against one that does. Every existing P-GPU-1 number is valid and correctly labelled\n"
     "   `bursty`; a sustained-serving claim requires the not-yet-authored sustained variant\n"
     "   (deferred — see the amendment note below).\n"),
]
NOTE = (
    "\n<!-- AMENDED per RATIFY-PGPU1-DUTY-CYCLE-20260814 (AK-OP-1 / master-index OP-10): added\n"
    "     mandatory field 7 `duty_cycle: bursty | sustained` and declared the canonical\n"
    "     `fresh server per rep` recipe `bursty`. Pure labelling — invalidates nothing; every\n"
    "     existing P-GPU-1 number stays valid and correctly labelled `bursty`. A sustained variant\n"
    "     (option b) is deferred until the first sustained-serving claim needs it. -->\n"
)

candidate = original
for old, new in EDITS:
    n = candidate.count(old)
    if n != 1:
        raise SystemExit(f"edit-site text occurs {n} times, expected exactly 1; refuse: {old[:40]!r}")
    candidate = candidate.replace(old, new, 1)
candidate += NOTE

# Post-condition guards: exactly one field 7, no duplicated bursty clauses.
if candidate.count("7. **Duty cycle** — `duty_cycle: bursty | sustained`") != 1:
    raise SystemExit("field-7 duty_cycle declaration not unique; refuse")
if candidate.count("(duty cycle `bursty` — see field 7)") != 1:
    raise SystemExit("field-4 bursty cross-reference not unique; refuse")

print("site 1 (field 4 bursty label): OK")
print("site 2 (field 7 duty_cycle): OK")
print(f"candidate sha256: {hashlib.sha256(candidate.encode()).hexdigest()}")

if mode == "validate":
    print("preflight-valid")
    raise SystemExit(0)

fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".pgpu1-dc-")
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
    "schema": "epyc.operator_pgpu1_duty_cycle.v1",
    "status": "ratified",
    "human_attestation": token,
    "ratified_at": datetime.now(UTC).isoformat(),
    "target": target,
    "preimage_sha256": "6eb9acc467ecc1fd4978ddd5061a42122bf3ce17e2bd7b303e7b5819aa341423",
    "amended_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
    "amendment": "field 7 duty_cycle: bursty|sustained added; canonical recipe declared bursty (AK-OP-1 option a)",
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
