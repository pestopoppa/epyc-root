#!/bin/bash
set -euo pipefail
root=/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase
p="$root/stage2-packet-r2"; id=codex-ni-gnx-split-resolve-r2-20261027
test ! -e "/mnt/raid0/llm/tmp/compute-flags/grants/$id.grant"
test ! -e "$p/MAIN-APPROVAL.txt"
test ! -e "$root/source-view/.gitnexus/lbug"
/usr/bin/python3 -I -B - "$id" <<'PY'
import os,pathlib,sys
for p in pathlib.Path('/proc').iterdir():
    if not p.name.isdecimal() or int(p.name)==os.getpid(): continue
    try: args=(p/'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError,PermissionError,ProcessLookupError): continue
    if b'--id' in args and sys.argv[1].encode() in args:
        raise SystemExit('successor launcher already exists')
PY
mkdir -p "$p/normal-guard-fixture/grants"
cleanup() {
  if [[ -f "$p/MAIN-APPROVAL.txt" ]]; then mv "$p/MAIN-APPROVAL.txt" "$p/normal-guard-fixture/approval.fixture-only.used"; fi
  [[ ! -e "$p/MAIN-APPROVAL.txt" ]] || exit 1
  printf 'FIXTURE_APPROVAL_REMOVED\n'
}
trap cleanup EXIT
seal=$(sha256sum "$p/PACKET.sha256"); seal=${seal%% *}
( set -o noclobber; printf 'approved-stage=resolve\npacket-sha256=%s\nfixture-only=true\n' "$seal" > "$p/MAIN-APPROVAL.txt" )
end=$((EPOCHSECONDS+3000)); start_iso=$(date -u +%FT%TZ); end_iso=$(date -u -d "@$end" +%FT%TZ)
export FILLER_ID="$id" FILLER_STOPFILE="$root/STOP" FILLER_GRANTS_DIR="$p/normal-guard-fixture/grants"
export FILLER_END="$end" FILLER_DEADLINE=$((end-90)) FILLER_THREADS=2 FILLER_PREFLIGHT=0
grant="$FILLER_GRANTS_DIR/$id.grant"
try_guard() { printf 'regions=%s start=%s end=%s\n' "$1" "$start_iso" "$end_iso" > "$grant"; FILLER_CPUS="$2" bash "$p/guard.sh"; }
try_guard 72-73 72-73
try_guard 72,73 72,73
try_guard 72-73 72,73
try_guard 72,73 72-73
if try_guard 72-74 72-73; then exit 1; fi
if try_guard 72-73 72-74; then exit 1; fi
if try_guard 72-73 72; then exit 1; fi
if try_guard 72 72-73; then exit 1; fi
test ! -e "/mnt/raid0/llm/tmp/compute-flags/grants/$id.grant"
test ! -e "$root/stage2-results-r2"
test ! -e "$root/source-view/.gitnexus/lbug"
printf 'NORMAL_GUARD_FIXTURE_PASS\n'
