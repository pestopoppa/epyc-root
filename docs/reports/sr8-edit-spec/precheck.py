#!/usr/bin/env python3
import hashlib,json,os
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr8-edit-spec')
p=json.loads((D/'preflight.json').read_text())
assert p['schema']=='epyc.sr8.preflight.v1'
for m in p['models']:
 s=os.stat(m['path']); assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(m['dev'],m['ino'],m['size'],m['mtime_ns'])
b=Path('/mnt/raid0/llm/kernels/production/gpu/llama-server').resolve(strict=True)
assert str(b)==p['kernel'] and hashlib.sha256(b.read_bytes()).hexdigest()==p['kernel_sha256']
assert (D/'linkage-preflight.txt').read_text().find('PASS:')>=0
