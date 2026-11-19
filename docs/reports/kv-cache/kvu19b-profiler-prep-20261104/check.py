#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
for name,digest in json.loads((D/'inputs.json').read_text()).items():
 p=Path(name) if name.startswith('/') else D/name
 if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise SystemExit('input digest changed: '+name)

a=json.loads((D/'predecessor-assets.json').read_text())
if a['source_commit']!='1bceceb0514d423ad220888313eafcddc30e485e':raise SystemExit('wrong predecessor source')
if hashlib.sha256((D/'p3batch-original.cpp').read_bytes()).hexdigest()!=a['compile']['harness_source_sha256']:raise SystemExit('original source mismatch')
for name,digest in a['libraries'].items():
 if hashlib.sha256((D/'bin'/name).read_bytes()).hexdigest()!=digest:raise SystemExit('predecessor library mismatch: '+name)
for name,digest in a['compile']['included_header_catalog'].items():
 if hashlib.sha256((D/name).read_bytes()).hexdigest()!=digest:raise SystemExit('predecessor header mismatch: '+name)
