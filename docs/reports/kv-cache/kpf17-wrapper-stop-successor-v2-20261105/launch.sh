#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17-wrapper-stop-successor-v2-20261105
python3 - "$D" <<'VERIFY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);s=json.loads((p/"qualification-seal.json").read_text())
for n,h in s["sha256"].items():
 if hashlib.sha256((p/n).read_bytes()).hexdigest()!=h:raise SystemExit("sealed qualification input changed: "+n)
VERIFY
exec /bin/bash "$D/filler_run15.sh" --id kvfork17-wrapper-stop-successor-v2-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 '$D/row_complete.py'" --cmd "python3 '$D/qualify.py'"
