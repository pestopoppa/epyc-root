#!/bin/bash
# ws58 2026-10-28 (operator: "results/verdicts/insights/followups need to be filed IMMEDIATELY after the run ends").
# Zero-token watcher: every grants/<id>.ended or .complete that is new since the last scan becomes one line in
# filing-due.jsonl (id, rc, ended_at, result_path from the ready/armed manifest). The owner session watches that file
# and dispatches a filing subagent per line; the filer writes filing-done/<id>.FILED (verdict line + commit) when done.
# Read-only on everything except its own state files. Kills nothing, deletes nothing.
set -euo pipefail
F=${FILING_WATCH_FLAGS_ROOT:-/mnt/raid0/llm/tmp/compute-flags}
BUS=${FILING_WATCH_BUS_ROOT:-/workspace/coordination/session-bus}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
ONCE=0
if [ "${1:-}" = --once ]; then ONCE=1; elif [ "$#" != 0 ]; then echo "usage: filing_watch.sh [--once]" >&2; exit 2; fi
DUE=$F/filing-due.jsonl
DONE=$F/filing-done
SEEN=$F/filing-watch.seen
mkdir -p "$DONE"
touch "$DUE" "$SEEN"
echo "$(date -u +%FT%TZ) filing-watch start pid=$$" >> $F/filing-watch.log
while :; do
  for f in $F/grants/*.ended $F/grants/*.complete; do
    [ -e "$f" ] || continue
    id=$(basename "$f"); id=${id%.ended}; id=${id%.complete}
    grep -qxF "$id" "$SEEN" && continue
    # only runs that ended after this watcher's epoch (older ends are the backlog, handled by verdict_count.py)
    [ "$(stat -c %Y "$f")" -ge 1793145600 ] || { echo "$id" >> "$SEEN"; continue; }
    python3 -I - "$id" "$f" "$DUE" <<'PY'
import json, os, sys, glob, datetime
rid, f, due = sys.argv[1:4]
first = open(f).readline().strip()
man = {}
for p in glob.glob(os.path.join(os.path.dirname(due), 'ready', '**', rid + '.json'), recursive=True) + \
         glob.glob(os.path.join(os.path.dirname(due), 'ready', rid + '.json')):
    try: man = json.load(open(p)); break
    except Exception: pass
rec = {'id': rid, 'ended_file': f, 'end_line': first[:300],
       'seen_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
       'result_path': man.get('result_path'), 'scratch_root': man.get('scratch_root'),
       'decision_rule': man.get('decision_rule'), 'class': man.get('class'), 'owner': man.get('owner')}
open(due, 'a').write(json.dumps(rec) + '\n')
PY
    echo "$id" >> "$SEEN"
  done
  alarm_rc=0
  # The bus uses installed PyYAML/jsonschema; -I suppresses required user-site dependencies.
  python3 "$ROOT/scripts/coordination/filing_takeover_alarm.py" --flags-root "$F" --bus-root "$BUS" || alarm_rc=$?
  if [ "$alarm_rc" != 0 ]; then echo "$(date -u +%FT%TZ) filing-alarm unknown rc=$alarm_rc" >> "$F/filing-watch.log"; fi
  [ "$ONCE" = 1 ] && exit "$alarm_rc"
  sleep 60
done
