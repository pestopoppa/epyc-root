#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 a=json.loads((D/'out/RESULT.json').read_text())
 if not (a['schema']=='kvu19b.profiler-build.v1' and a['status']=='built' and not a['smoke']):raise ValueError('wrong result')
 for key,path in [('binary_sha256',Path(a['binary'])),('source_sha256',D/'p3batch-clock.cpp'),('linkage_sha256',D/'out/linkage.txt'),('predecessor_assets_sha256',D/'predecessor-assets.json')]:
  if hashlib.sha256(path.read_bytes()).hexdigest()!=a[key]:raise ValueError('digest mismatch '+key)
except Exception:sys.exit(1)
