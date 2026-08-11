#!/bin/bash
# Static conformance check for the C39 keyed-receipt contract over operator
# ratifier artifacts. READ-ONLY: writes nothing, repairs nothing — a check that
# silently repairs what it checks for cannot be trusted to report (mainD, C39).
#
# Contract: any script that can mint an operator signature (--attest) must write
# artifacts/operator/receipts/<GATE_ID>.json at signing time (pointer, schema
# session_bus.receipt_index.v1) and refuse if that index already exists.
# Runtime drift backstop: `session_bus_coordinator.py backfill-receipts --check`
# (bus-known gates). This check covers the AUTHORING side and the receipts
# already on disk, which the bus may not know about.
#
# Exit 1 if any signable script lacks the keyed write, or any on-disk ratified
# receipt lacks its index. Exit 0 clean.
set -euo pipefail
export PATH="/usr/bin:/bin"

OP="/mnt/raid0/llm/epyc-root/artifacts/operator"
fail=0

# Scope: TOKEN-bearing --attest signers — the kind whose gate string the daemon
# presents in token-queue.md. Dry-run/apply-generation vehicles (no token argv)
# never enter the queue and are out of contract scope by design.
printf '== signable token scripts missing the keyed-receipt write ==\n'
clean=1
for f in "$OP"/ratify_*.sh "$OP"/rearm_*.sh "$OP"/attest_*.sh; do
    [[ -f "$f" ]] || continue
    grep -q -- "--attest" "$f" || continue                      # not a token signer
    if grep -q "artifacts/operator/receipts/" "$f"; then continue; fi   # contract adopted
    tok=$(grep -m1 -oP 'TOKEN="\K[^"]+' "$f" || true)
    if [[ -n "$tok" && -f "$OP/receipts/$tok.json" ]]; then continue; fi  # spent via index
    # Spent via its own basename-receipt guard — but ONLY if that receipt actually says
    # ratified. A stray/garbage <script>.json would otherwise silently exempt a signable
    # script from this check (lens: the skip could be bought by creating an empty file).
    if [[ -f "${f%.sh}.json" ]] && grep -qE '"status": *"ratified"|"ratified_at"' "${f%.sh}.json"; then continue; fi  # modern or legacy receipt schema; a stray empty file has neither
    # Signable (or token not extractable = assume signable, fail closed).
    printf 'MISSING-WRITE: %s (token=%s)\n' "${f##*/}" "${tok:-UNPARSED}"
    fail=1; clean=0
done
[[ "$clean" == 1 ]] && printf '(none)\n'

printf '== on-disk ratified receipts lacking a keyed index ==\n'
found_gap=0
"${PYTHON:-/usr/bin/python3}" - "$OP" <<'PY' || found_gap=1
import json, os, sys
op = sys.argv[1]
gap = False
for name in sorted(os.listdir(op)):
    if not name.endswith(".json") or "/" in name:
        continue
    path = os.path.join(op, name)
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception:
        continue
    if not isinstance(doc, dict) or doc.get("status") != "ratified":
        continue
    gate = doc.get("human_attestation") or doc.get("reviewer") or doc.get("gate_id")
    if not isinstance(gate, str) or not gate.strip():
        print(f"UNKEYABLE: {name} is status=ratified but carries no recognisable gate id")
        gap = True
        continue
    if not os.path.isfile(os.path.join(op, "receipts", f"{gate}.json")):
        print(f"MISSING-INDEX: gate {gate} (receipt {name})")
        gap = True

# Receipts must be IN GIT, not merely on disk — an index asserting ratified over
# an untracked receipt loses its evidence on a fresh checkout (found 2026-08-11:
# three E8-FINAL-C1 receipts were exactly this). Filesystem presence is not
# provenance; a check passable by the file merely existing is fail-open.
import subprocess
idx_dir = os.path.join(op, "receipts")
if not os.path.isdir(idx_dir):
    # Lens: a deleted index dir must be a LOUD defect, not a silent zero-iteration pass —
    # the daemon's spent-gate check stats exactly this path.
    print(f"MISSING-DIR: {idx_dir} does not exist; every spent-gate check is blind")
    gap = True
for name in sorted(os.listdir(idx_dir)) if os.path.isdir(idx_dir) else []:
    if not name.endswith(".json"):
        continue
    try:
        ptr = json.load(open(os.path.join(idx_dir, name), encoding="utf-8"))
    except Exception:
        print(f"UNPARSEABLE-INDEX: receipts/{name}")
        gap = True
        continue
    target = ptr.get("receipt", "")
    for repo, prefix in (("/mnt/raid0/llm/epyc-root", "/mnt/raid0/llm/epyc-root/"),
                         ("/workspace", "/workspace/")):
        if target.startswith(prefix):
            rel = target[len(prefix):]
            rc = subprocess.run(["git", "-C", repo, "ls-files", "--error-unmatch", rel],
                                capture_output=True).returncode
            if rc != 0:
                print(f"UNTRACKED-EVIDENCE: receipts/{name} -> {rel} is not in git")
                gap = True
            break
    else:
        print(f"UNRESOLVED-TARGET: receipts/{name} -> {target}")
        gap = True
if not gap:
    print("(none)")
sys.exit(1 if gap else 0)
PY
[[ "$found_gap" == 0 ]] || fail=1

exit "$fail"
