#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-forecast56
O="$TMPDIR/kpf18-56-watch-fixture"
mkdir -p "$O"
export FILLER_DEADLINE=$(( $(date +%s) + 60 ))
/usr/bin/python3 -I -B "$B/test-resource-unit.py"
KPF18_WATCH_RECEIPT="$O/success.json" /usr/bin/python3 -I -B "$B/resource-watch.py" /usr/bin/python3 -c pass > "$O/success.log" 2>&1
[[ ! -e "$O/success.json" ]]
if KPF18_WATCH_RECEIPT="$O/orphan.json" /usr/bin/python3 -I -B "$B/resource-watch.py" /usr/bin/python3 -c 'import os,sys,time; p=os.fork(); open(sys.argv[1],"w").write(str(p)) if p else time.sleep(15)' "$O/orphan.pid" > "$O/orphan.log" 2>&1; then exit 1; else [[ $? == 125 ]]; fi
pid=$(cat "$O/orphan.pid")
[[ $pid =~ ^[0-9]+$ ]] && ! ps -p "$pid" >/dev/null
rg -q 'INCONCLUSIVE' "$O/orphan.json"
if KPF18_WATCH_RECEIPT="$O/rss.json" /usr/bin/python3 -I -B "$B/resource-watch.py" --limit-kib 1 /usr/bin/python3 -c 'import time; time.sleep(15)' > "$O/rss.log" 2>&1; then exit 1; else [[ $? == 125 ]]; fi
rg -q RSS_SAMPLE_LIMIT_EXCEEDED "$O/rss.json"
touch "$O/STOP"
if FILLER_STOPFILE="$O/STOP" KPF18_WATCH_RECEIPT="$O/stop.json" /usr/bin/python3 -I -B "$B/resource-watch.py" /usr/bin/python3 -c 'import time; time.sleep(15)' > "$O/stop.log" 2>&1; then exit 1; else [[ $? == 125 ]]; fi
rg -q HOLD_OR_STOP_DETECTED "$O/stop.json"
if FILLER_DEADLINE=1 KPF18_WATCH_RECEIPT="$O/deadline.json" /usr/bin/python3 -I -B "$B/resource-watch.py" /usr/bin/python3 -c 'import pathlib,sys; pathlib.Path(sys.argv[1]).touch()' "$O/deadline-child-started" > "$O/deadline.log" 2>&1; then exit 1; else [[ $? == 125 ]]; fi
rg -q GRANT_DEADLINE_REACHED "$O/deadline.json"
[[ ! -e "$O/deadline-child-started" ]]
if KPF18_WATCH_RECEIPT="$O/disk.json" /usr/bin/python3 -I -B - "$B/resource-watch.py" <<'PY' > "$O/disk.log" 2>&1
import importlib.util,sys
spec=importlib.util.spec_from_file_location('watch',sys.argv[1]); w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
w.MIN_FREE_BYTES=1<<100
sys.argv=['watch',sys.executable,'-c','import time; time.sleep(15)']
raise SystemExit(w.main())
PY
then exit 1; else [[ $? == 125 ]]; fi
rg -q DISK_FLOOR_BREACHED "$O/disk.json"
printf 'WATCH_FIXTURES_PASS\n'
