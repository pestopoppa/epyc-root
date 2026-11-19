#!/bin/bash
set -euo pipefail
D=$(cd -- "$(dirname -- "$0")" && pwd -P)
SRC="$D/inputs/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf"
URL=https://huggingface.co/bartowski/Qwen_Qwen3.6-35B-A3B-GGUF/resolve/d98fa7286daa6544d050929df95e436741ee739b/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf
SHA=afddb074d3ce9ec8a3f64bfe7288a6c33f0d3a629be3caf4b5de1386a582dbd5
exec 9>"$D/inputs/.recovery.lock"
flock -n 9
if [[ -f "$D/inputs/Q8-VERIFIED.json" && -f "$SRC" ]]; then
    echo 'Q8_0 prep already has a receipt. Use the row preflight to verify its exact file identity.'
    exit 0
fi
child=
signal_exit() {
    local code=$1
    if [[ -n $child ]]; then
        kill -TERM "$child" 2>/dev/null || true
    fi
    exit "$code"
}
finish() {
    local rc=$?
    python3 - "$D/inputs" "$rc" <<'PY_EVENT'
import json, os, sys, time
from pathlib import Path
root, rc = Path(sys.argv[1]), int(sys.argv[2])
temp = root / 'Q8-RECOVERY-TERMINAL.tmp'
with temp.open('w') as stream:
    json.dump({'state': 'verified' if rc == 0 else 'failed', 'rc': rc, 'ended_at': time.time()}, stream)
    stream.write('\n')
    stream.flush()
    os.fsync(stream.fileno())
temp.replace(root / 'Q8-RECOVERY-TERMINAL.json')
PY_EVENT
}
trap finish EXIT
trap 'signal_exit 143' TERM
trap 'signal_exit 130' INT
trap 'signal_exit 129' HUP
python3 - "$D/inputs" "$$" <<'PY_OWNER'
import json, os, sys, time
from pathlib import Path

root, pid = Path(sys.argv[1]), int(sys.argv[2])
proc = Path('/proc') / str(pid)
start_ticks = int((proc / 'stat').read_text().rsplit(')', 1)[1].split()[19])
argv = [field.decode() for field in (proc / 'cmdline').read_bytes().split(b'\0') if field]
boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
owner = dict(pid=pid, boot_id=boot_id, proc_start_ticks=start_ticks, argv=argv,
             recorded_at=time.time(), lock=str(root / '.recovery.lock'))
temp = root / 'Q8-RECOVERY-OWNER.tmp'
with temp.open('w') as stream:
    json.dump(owner, stream, sort_keys=True)
    stream.write('\n')
    stream.flush()
    os.fsync(stream.fileno())
temp.replace(root / 'Q8-RECOVERY-OWNER.json')
PY_OWNER
if [[ ! -f "$SRC" ]]; then
    python3 "$D/fetch_ranges.py" "$SRC" "$URL" &
    child=$!
    wait "$child"
    child=
fi
python3 - "$SRC" "$SHA" "$URL" <<'PY' &
import hashlib
import json
import os
import sys
from pathlib import Path

src, expected, url = sys.argv[1:]
p = Path(src)
with p.open('rb') as f:
    before = os.fstat(f.fileno())
    digest = hashlib.file_digest(f, 'sha256').hexdigest()
    after = os.fstat(f.fileno())
fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
if (digest != expected or after.st_size != 36914690368
        or any(getattr(before, field) != getattr(after, field) for field in fields)
        or any(getattr(after, field) != getattr(p.stat(), field) for field in fields)):
    raise SystemExit('Q8_0 bytes or stat identity differ; receipt absent')
receipt = p.parent / 'Q8-VERIFIED.json'
record = dict(path=src, url=url, sha256=digest, **{field: getattr(after, field) for field in fields})
with receipt.with_suffix('.tmp').open('x') as f:
    json.dump(record, f, sort_keys=True)
    f.write('\n')
    f.flush()
    os.fsync(f.fileno())
os.replace(receipt.with_suffix('.tmp'), receipt)
print(f'Verified exact {after.st_size}-byte Q8_0 source: {digest}')
PY
child=$!
wait "$child"
child=
