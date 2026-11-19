#!/usr/bin/env python3
import json
from pathlib import Path
import sys
try:
    result=json.loads(Path(sys.argv[1]).read_text())
    ok=result.get('status')=='ok' and result.get('native_units')==2
    if result.get('mode')=='full':ok=ok and result.get('full_rc')==0 and len(result.get('rows',[]))==20
    elif result.get('mode')!='qualification':ok=False
except (OSError,ValueError,IndexError):ok=False
raise SystemExit(0 if ok else 1)
