"""Verify in-window ggml mappings against a frozen binary inventory."""
import hashlib
import os
import re
from pathlib import Path

def snapshot(pid, expected_binary, inventory, require_hip, proc_root=Path('/proc')):
    proc=Path(proc_root)/str(pid)
    expected=Path(expected_binary).resolve(strict=True)
    def identity():
        stat=(proc/'stat').read_text(); close=stat.rfind(')')
        if close<0: raise ValueError('invalid process stat')
        return (proc/'exe').resolve(strict=True),int(stat[close+2:].split()[19])
    before=identity()
    if before[0]!=expected: raise ValueError('wrong process executable')
    allowed={str(Path(p).resolve(strict=True)):v for p,v in inventory.items()}
    rows={}
    raw=(proc/'maps').read_text()
    for line in raw.splitlines():
        fields=line.split(None,5)
        if len(fields)<6: continue
        path=fields[5]
        if not re.search(r'/lib(?:ggml|llama)[^/]*\.so(?:\.|$)',path): continue
        if path.endswith(' (deleted)'): raise ValueError('deleted library mapping')
        resolved=str(Path(path).resolve(strict=True))
        if resolved not in allowed: raise ValueError('mapped library absent from inventory')
        st=os.stat(resolved)
        major,minor=(int(x,16) for x in fields[3].split(':'))
        if (os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)!=(major,minor,int(fields[4])):
            raise ValueError('mapped library identity differs from file')
        if resolved not in rows:
            h=hashlib.sha256()
            with open(resolved,'rb') as f:
                for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
            if h.hexdigest()!=allowed[resolved]: raise ValueError('mapped library digest mismatch')
            rows[resolved]=h.hexdigest()
    names=[Path(x).name for x in rows]
    if not any(x.startswith('libggml-base.so') for x in names): raise ValueError('no mapped ggml base')
    if require_hip and not any(x.startswith('libggml-hip.so') for x in names): raise ValueError('no mapped HIP backend')
    if identity()!=before: raise ValueError('process changed during maps capture')
    return {'verifier':'pf1.maps_witness.v1','pid':pid,'start_ticks':before[1],
            'binary':str(expected),'libraries':rows,'maps':raw,'verdict':'pass'}
