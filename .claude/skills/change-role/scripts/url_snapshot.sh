#!/bin/bash
# The operative-URL snapshot, carried over from
# epyc-orchestrator/docs/runbooks/role-alias-change-runbook.md (verification chain
# steps 1 and 3). It is the ONLY check that asks what a plain-import consumer
# actually gets, rather than what a YAML says it should get.
#
#   url_snapshot.sh capture <outfile>
#   url_snapshot.sh diff <before> <after> [role ...]      # roles allowed to change
#
# exit 0  captured, or the diff changed only the roles you named
# exit 2  a role you did NOT name changed -- STOP
# exit 1  usage / the config could not be imported
#
# An alias membership change must alter ONLY the intended alias's URL. Anything
# else moving means the change reached further than the intent did, and the
# runbook's rule is: stop, do not reload.
#
# Read-only: it imports the orchestrator config and prints. It starts, stops and
# reloads nothing.
set -uo pipefail

ORCH="${EPYC_ORCHESTRATOR:-/mnt/raid0/llm/epyc-orchestrator}"
PY="$ORCH/.venv/bin/python"

capture() {
  [ -x "$PY" ] || { echo "FAIL: no orchestrator venv at $PY" >&2; exit 1; }
  # The field list is ENUMERATED from the dataclass, never typed out here. A
  # hand-kept list is one more restatement, and it goes stale the first time a
  # role is added -- which is exactly the change this script is used for.
  (cd "$ORCH" && "$PY" - <<'PYEOF'
import dataclasses, sys
try:
    from src.config import get_config
except Exception as exc:  # noqa: BLE001
    print(f"FAIL: cannot import the orchestrator config: {exc}", file=sys.stderr)
    raise SystemExit(1)
su = get_config().server_urls
for f in sorted(x.name for x in dataclasses.fields(su)):
    print(f"{f}\t{getattr(su, f)}")
PYEOF
  )
}

case "${1:-}" in
  capture)
    OUT="${2:?usage: url_snapshot.sh capture <outfile>}"
    capture > "$OUT" || exit 1
    [ -s "$OUT" ] || { echo "FAIL: empty snapshot -- a vacuous PASS is worse than a failure" >&2; exit 1; }
    echo "captured $(wc -l < "$OUT") operative URLs -> $OUT"
    cat "$OUT"
    ;;
  diff)
    B="${2:?usage: url_snapshot.sh diff <before> <after> [role ...]}"
    A="${3:?}"
    shift 3 || true
    ALLOWED=" $* "
    RC=0
    while IFS=$'\t' read -r role url; do
      new=$(awk -F'\t' -v r="$role" '$1==r{print $2}' "$A")
      if [ "$url" != "$new" ]; then
        case "$ALLOWED" in
          *" $role "*) echo "CHANGED (intended)  $role: $url -> $new" ;;
          *) echo "CHANGED (UNINTENDED) $role: $url -> $new"; RC=2 ;;
        esac
      fi
    done < "$B"
    while IFS=$'\t' read -r role url; do
      grep -q "^$role	" "$B" || { echo "NEW ROLE $role: $url"; case "$ALLOWED" in *" $role "*) ;; *) RC=2 ;; esac; }
    done < "$A"
    if [ "$RC" != 0 ]; then
      echo "REFUSED: a role you did not name moved. The change reached further than the intent." >&2
      echo "         Do not reload. Go back to the transform (stack-change phase 2)." >&2
      exit 2
    fi
    echo "PASS: only the named role(s) moved:${ALLOWED}"
    ;;
  *)
    echo "usage: url_snapshot.sh capture <outfile> | diff <before> <after> [role ...]" >&2
    exit 1 ;;
esac
