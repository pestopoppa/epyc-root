"""Verify peers with their issuer version, retaining the full native checks."""
import json
from pathlib import Path
import subprocess

V1=Path('/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/qualify_launcher.py')

def verify(manifest, flags, current):
    # Unknown kinds fail closed. Never select from receipt-supplied paths.
    p=Path(manifest)
    if p.is_symlink() or not p.is_file(): raise current.Refused('manifest missing or symlink')
    original=p.read_bytes();m=json.loads(original)
    if 'qualifier_version' in m:
        if m['qualifier_version']!='epyc.qual-v2-row': raise current.Refused('unknown qualifier version')
        llm=m.get('llm',{})
        if not isinstance(llm,dict):raise current.Refused('malformed llm selector')
        if llm.get('backend','server') not in ('server','native-batched-bench'):raise current.Refused('unknown qualifier backend')
        return current.verify(p,flags,True)
    receipt=Path(m['qualification']['receipt'])
    if receipt.is_symlink() or not receipt.is_file():raise current.Refused('receipt missing')
    before=receipt.read_bytes()
    cp=subprocess.run(['/usr/bin/python3','-I',str(V1),'verify','--manifest',str(p),'--flags',str(flags)],capture_output=True,text=True,timeout=60)
    if cp.returncode or p.read_bytes()!=original or receipt.read_bytes()!=before:
        raise current.Refused('v1 peer verification failed or changed')
    proof=json.loads(before)
    if not isinstance(proof,dict):raise current.Refused('v1 peer proof malformed')
    return proof
