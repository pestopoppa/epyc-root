#!/bin/bash
# Terminal countersignature for four ratifications the operator approved in chat on
# 2026-09-26/27 but that the agent (session workspace-8d) executed, or that recorded no
# person as operator. Record: artifacts/operator/countersign/COUNTERSIGN-20260927.md.
#
# The OPERATOR runs this, from a terminal. An agent must never run it: the whole point
# is a human-typed step. It writes ONE file,
#   artifacts/operator/countersign/COUNTERSIGN-20260927.signed.json
# with the typed name, the UTC time, the uid, the record's sha256 and the four gate ids.
# It re-runs no ratification and edits nothing else. With --commit it also commits that
# one file (pathspec-limited; no push).
#
# Usage:  bash scripts/operator/countersign_20260927.sh [--commit]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REC_REL="artifacts/operator/countersign/COUNTERSIGN-20260927.md"
OUT_REL="artifacts/operator/countersign/COUNTERSIGN-20260927.signed.json"
GATES=(
  "RATIFY-P-SERVE-SEL-1-20260926|3573028b"
  "RATIFY-OP63-REGION-LOCK-SCOPE-20260926|cdf8232f"
  "RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926|2850fa8c"
  "RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926|bf610d36"
)

DO_COMMIT=0
case "${1:-}" in
  "") ;;
  --commit) DO_COMMIT=1 ;;
  *) echo "usage: $0 [--commit]" >&2; exit 64 ;;
esac

die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }

[ -t 0 ] && [ -t 1 ] || die "run this from an interactive terminal; the typed step is the proof of a human."
[ -f "$ROOT/$REC_REL" ] || die "$REC_REL not found under $ROOT"
[ ! -e "$ROOT/$OUT_REL" ] || die "$OUT_REL already exists: the countersignature is already recorded."
for g in "${GATES[@]}"; do
  commit="${g#*|}"
  git -C "$ROOT" cat-file -e "$commit^{commit}" 2>/dev/null || die "commit $commit (${g%%|*}) is not in $ROOT"
done

echo "You are countersigning four ratifications that you approved in chat on 2026-09-26/27"
echo "and that the agent (session workspace-8d) executed:"
for g in "${GATES[@]}"; do printf '  - %s  (root %s)\n' "${g%%|*}" "${g#*|}"; done
echo "Record: $REC_REL"
echo

read -r -p "Your name (as you sign it, not the login account): " NAME
# Same rule as every ratifier: no system account, no login account, no agent id.
# shellcheck source=lib/ratify_operator.sh
source "$SCRIPT_DIR/lib/ratify_operator.sh"
ratify_require_operator "$NAME"
NAME="$RATIFY_OPERATOR"

read -r -p "Type COUNTERSIGN to record it: " WORD
[ "$WORD" = "COUNTERSIGN" ] || die "you typed '$WORD', not COUNTERSIGN. Nothing written."

python3 - "$ROOT" "$REC_REL" "$OUT_REL" "$NAME" "${GATES[@]}" <<'PYEOF'
import hashlib, json, os, sys, tempfile
from datetime import datetime, timezone
root, rec_rel, out_rel, name, *gates = sys.argv[1:]
rec = os.path.join(root, rec_rel)
doc = {
    "schema": "epyc.operator_countersign.v1",
    "record": {"path": rec_rel, "sha256": hashlib.sha256(open(rec, "rb").read()).hexdigest()},
    "countersigned_by": name,
    "countersigned_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "uid": os.getuid(),
    "typed": "COUNTERSIGN",
    "gates": [{"gate_id": g.split("|")[0], "landed_in": g.split("|")[1]} for g in gates],
    "state": "COUNTERSIGNED",
    "note": "chat approval 2026-09-26/27 (https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ); "
            "executed by the agent (workspace-8d); countersigned here by a human at a terminal",
}
out = os.path.join(root, out_rel)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(out), prefix=".countersign.")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
os.replace(tmp, out)
print(f"written {out_rel}: {name} at {doc['countersigned_at_utc']}")
PYEOF

if [ "$DO_COMMIT" -eq 1 ]; then
  git -C "$ROOT" add -- "$OUT_REL"
  git -C "$ROOT" commit -q -m "operator: countersign four chat-approved ratifications (COUNTERSIGN-20260927)" -- "$OUT_REL"
  echo "committed $(git -C "$ROOT" rev-parse --short HEAD) (not pushed)."
else
  echo "Not committed. To commit only this file: git -C $ROOT commit -m 'operator: countersign (COUNTERSIGN-20260927)' -- $OUT_REL"
fi
