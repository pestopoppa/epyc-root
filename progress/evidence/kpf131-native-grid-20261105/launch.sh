#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/native-grid-20261105
/usr/bin/python3 -I - "$D" <<'VERIFY'
import hashlib,json,sys
from pathlib import Path
d=Path(sys.argv[1]);s=d/'seal.json'
if hashlib.sha256(s.read_bytes()).hexdigest()!='26c5413af87379c83c5032548fe00dea3519caed55aee6d6a57b09d56cbb3f26':raise SystemExit('seal digest drift')
for p,h in json.loads(s.read_text()).items():
 if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise SystemExit('seal mismatch: '+p)
VERIFY
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf131-native-grid-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "/usr/bin/python3 -E -s -B '$D/complete.py'" --cmd "/usr/bin/python3 -E -s -B '$D/run.py'"
