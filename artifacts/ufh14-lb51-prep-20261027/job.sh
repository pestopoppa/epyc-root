#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh14-lb51-template
[[ ${FILLER_ID:-} == ufh14-lb51-live-template-20261027 ]] || exit 70
(cd "$B" && sha256sum --quiet -c SOURCE.SHA256SUMS)
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 exec /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$B/job.sh" --effect server-start
fi
[[ -s "$B/MAIN-ACCEPTANCE.txt" && ! -L "$B/MAIN-ACCEPTANCE.txt" ]] || exit 70
[[ $(cat "$B/MAIN-ACCEPTANCE.txt") == "source-seal-sha256=$(sha256sum "$B/SOURCE.SHA256SUMS" | cut -d' ' -f1)" ]] || exit 70
for f in PASS.json CANDIDATE.json ERROR.json result.json server.log audit.log model.sha256 maps.txt server-identity.json linkage.log; do
 [[ ! -e "$B/$f" && ! -L "$B/$f" ]] || { printf 'refusing existing attempt output: %s\n' "$f" >&2; exit 70; }
done
if /usr/bin/python3 -B "$B/resource-watch.py" /usr/bin/python3 -B "$B/server_job.py"; then :; else
 rc=$?
 [[ -e "$B/ERROR.json" ]] || printf '{"status":"incomplete","error":"resource monitor or job exited before recording details","exit_code":%s}\n' "$rc" > "$B/ERROR.json"
 exit "$rc"
fi
[[ -s "$B/CANDIDATE.json" ]] || exit 70
mv "$B/CANDIDATE.json" "$B/PASS.json"
