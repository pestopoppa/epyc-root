#!/usr/bin/env python3
import hashlib,json,os
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr8-fresh-edit-20261105')
p=json.loads((D/'preflight.json').read_text())
assert p['schema']=='epyc.sr8.preflight.v1'
for m in p['models']:
 s=os.stat(m['path']); assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(m['dev'],m['ino'],m['size'],m['mtime_ns'],m['ctime_ns'])
b=Path('/mnt/raid0/llm/kernels/production/gpu/llama-server').resolve(strict=True)
assert str(b)==p['kernel'] and hashlib.sha256(b.read_bytes()).hexdigest()==p['kernel_sha256']
assert (D/'linkage-preflight.txt').read_text().find('PASS:')>=0

binding=json.loads((D/'store-binding.json').read_text())
assert binding['commit']=='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
manifest={name:digest for digest,name in (line.split() for line in (D/'store-SHA256SUMS').read_text().splitlines())}
assert 'commit `ffc1bac82`' in (D/'store-provenance.md').read_text()
for item in binding['files']:
    f=Path(item['path']); assert manifest['bin/'+f.name]==item['sha256']
    assert hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
assert next(x['sha256'] for x in binding['files'] if x['path'].endswith('/llama-server')) == p['kernel_sha256']

plan=json.loads((D/'candidate-plan.json').read_text())
assert hashlib.sha256((D/'corpus.json').read_bytes()).hexdigest()==plan['corpus_sha256']
