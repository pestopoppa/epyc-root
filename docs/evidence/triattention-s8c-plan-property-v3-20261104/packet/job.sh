#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/triattention-s8c-plan-property-v3-20261104
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
python3 - "$R/input-pins.json" <<'PY2'
import hashlib,json,pathlib,sys
x=json.load(open(sys.argv[1]));assert x['base_commit']=='ffc1bac82eeca6f9099e1ccd9ba49703c460a115' and x['patch_sha256']=='7612c84004793847a77237d8881830a8f17041625be28bd409591289f62298dc'
for name,h in x['files'].items():assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==h,name
PY2
mkdir -p "$R/output"
/usr/bin/g++ --version > "$R/output/compiler.txt"
/usr/bin/g++ -std=c++17 -O2 -I "$R/include" "$R/packet/property.cpp" -o "$R/output/property"
exec python3 "$R/packet/driver.py"
