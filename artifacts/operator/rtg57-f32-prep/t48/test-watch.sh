#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/packet
O="$TMPDIR/rtg57-watch"
mkdir -p "$O"
export FILLER_DEADLINE=$(( $(date +%s)+60 ))
run_watch() { /usr/bin/python3 -B -I - "$D/resource-watch.py" "$@" <<'PY'
import importlib.util,sys
p=sys.argv[1];s=importlib.util.spec_from_file_location('w',p);w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
w.MIN_FREE_BYTES=0
sys.argv=['watch']+sys.argv[2:]
raise SystemExit(w.main())
PY
}
run_watch /usr/bin/python3 -c pass > "$O/clean.log" 2>&1
if run_watch /usr/bin/python3 -c 'import os,sys,time; p=os.fork(); open(sys.argv[1],"w").write(str(p)) if p else time.sleep(15)' "$O/orphan.pid" > "$O/orphan.log" 2>&1; then exit 1; else rc=$?; fi
[ "$rc" = 125 ] && [ -s "$O/orphan.pid" ]
pid=$(cat "$O/orphan.pid")
! ps -p "$pid" >/dev/null
if run_watch --limit-kib 1 /usr/bin/python3 -c 'import time; time.sleep(15)' > "$O/rss.log" 2>&1; then exit 1; else rc=$?; fi
[ "$rc" = 125 ] && grep -q RSS_SAMPLE_LIMIT_EXCEEDED "$O/rss.log"
export FILLER_DEADLINE=1
if run_watch /usr/bin/python3 -c 'import time; time.sleep(15)' > "$O/deadline.log" 2>&1; then exit 1; else rc=$?; fi
[ "$rc" = 125 ] && grep -q FILLER_DEADLINE_EXCEEDED "$O/deadline.log"
echo 'resource watcher clean/orphan/RSS/deadline fixtures PASS; synthetic only'
