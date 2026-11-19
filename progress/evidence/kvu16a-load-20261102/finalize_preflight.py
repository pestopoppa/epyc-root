#!/usr/bin/env python3
"""Finalize after the single completed external weight checksum, then pin launch."""
import hashlib,json,os
from pathlib import Path
from identity import stat_record
D=Path('/mnt/raid0/llm/tmp/kvu16a-load-20261102')
expected={
 '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf':'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348',
 '/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf':'7f1c9a31a6ed40044c69f6508b50fd63b87abd8e1fb7fe4290303df549153751'}
rows={}
for line in (D/'model.sha256').read_text().splitlines():
    digest,path=line.split('  ',1)
    if path in rows:raise ValueError('duplicate model')
    rows[path]=digest
if rows!=expected:raise ValueError('model checksum incomplete or mismatch')
data=(json.dumps({'schema':'kvu16a.preflight.v1','models':[{'path':p,'sha256':h,'stat':stat_record(p)} for p,h in expected.items()]},sort_keys=True)+'\n').encode()
receipt=D/'model-receipt.json'
fd=os.open(receipt,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o400)
with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
digest=hashlib.sha256(data).hexdigest()
launch=D/'launch.sh'
s=launch.read_text()
if s.count('MODEL_RECEIPT_SHA256_PLACEHOLDER')!=1:raise ValueError('missing unique launcher pin placeholder')
launch.write_text(s.replace('MODEL_RECEIPT_SHA256_PLACEHOLDER',digest))
print('preflight receipt pinned',digest)
