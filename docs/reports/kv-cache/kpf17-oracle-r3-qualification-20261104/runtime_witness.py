"""Independently revalidate witness samples against the sealed build and model."""
import hashlib
import os
from pathlib import Path

POINTS={(mode,point) for mode in (0,8) for point in ('decode_entry','restore_dst_1','restore_dst_2')}

def validate(witness,build,model,validate_maps):
    if witness.get('schema')!='kpf17.oracle-in-test-maps.v1' or witness.get('error'):
        raise ValueError('witness schema/error')
    pid=witness.get('pid');birth=witness.get('birth_ticks');initial=witness.get('initial_stop') or {}
    if not isinstance(pid,int) or pid<=0 or not isinstance(birth,int) or birth<=0:
        raise ValueError('inferior identity absent')
    if initial.get('pid')!=pid or initial.get('birth_ticks')!=birth or initial.get('exe')!=build['binary']:
        raise ValueError('initial inferior identity mismatch')
    samples=witness.get('samples',[])
    if len(samples)!=len(POINTS) or {(s.get('mode'),s.get('point')) for s in samples}!=POINTS:
        raise ValueError('incomplete or duplicate sample points')
    expected_model=str(Path(model['path']).resolve(strict=True));st=model['stat']
    for s in samples:
        if s.get('pid')!=pid or s.get('birth_ticks')!=birth:
            raise ValueError('sample identity mismatch')
        for sample_key,expected in [('source_commit',build['source_commit']),('patch_sha256',build['patch_sha256']),('receipt_sha256',build['receipt_sha256']),('model_sha256',model['sha256'])]:
            if s.get(sample_key)!=expected:raise ValueError('sample binding mismatch: '+sample_key)
        raw=s.get('maps_text')
        if not isinstance(raw,str) or hashlib.sha256(raw.encode()).hexdigest()!=s.get('maps_sha256'):
            raise ValueError('maps content/hash mismatch')
        actual=validate_maps(raw.splitlines(),build['libraries'])
        if actual!=s.get('libraries'):raise ValueError('mapped library set mismatch')
        found=False
        for line in raw.splitlines():
            fields=line.split(None,5)
            if len(fields)!=6 or fields[5]!=expected_model:continue
            major,minor=(int(x,16) for x in fields[3].split(':'))
            if (major,minor,int(fields[4]))!=(os.major(st['dev']),os.minor(st['dev']),st['ino']):
                raise ValueError('mapped model inode mismatch')
            found=True
        if not found:raise ValueError('model mapping absent')
    return True
