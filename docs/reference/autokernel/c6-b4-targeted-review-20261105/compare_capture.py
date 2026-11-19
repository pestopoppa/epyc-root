#!/usr/bin/env python3
"""Compare captured tensor bytes; equality is descriptive, never a gate verdict."""
import hashlib
import json
from pathlib import Path
import re
import sys

NAMES=('candidate_weight','candidate_activation','sibling_weight','sibling_activation','candidate_output','sibling_output')
PAT=re.compile(r'^C6_CAPTURE (\S+) type=(\d+) ne=([0-9,]+) nb=([0-9,]+) bytes=(\d+)$')

def load(root):
    root=Path(root)
    rows={}
    for line in (root/'stderr.log').read_text().splitlines():
        m=PAT.fullmatch(line)
        if not m: continue
        name, typ, ne, nb, size=m.groups()
        if name not in NAMES or name in rows: raise ValueError('unexpected or duplicate capture')
        if len(ne.split(',')) != 4 or len(nb.split(',')) != 4: raise ValueError('invalid dimensions')
        p=root/(name+'.bin')
        if p.is_symlink() or not p.is_file(): raise ValueError('missing or symlink capture')
        data=p.read_bytes()
        if len(data)!=int(size) or not data: raise ValueError('invalid length')
        rows[name]={'type':int(typ),'ne':ne,'nb':nb,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    if set(rows)!=set(NAMES): raise ValueError('incomplete capture')
    return rows

def compare(a,b):
    x,y=load(a),load(b)
    for n in NAMES:
        if any(x[n][k]!=y[n][k] for k in ('type','ne','nb','bytes')): raise ValueError('capture metadata mismatch: '+n)
    for image in (x,y):
        for suffix in ('weight','activation'):
            if image['candidate_'+suffix] != image['sibling_'+suffix]: raise ValueError('intra-image inputs mismatch: '+suffix)
    return {'schema':'c6.capture_comparison.v1','input_bytes_equal':all(x['candidate_'+n]['sha256']==y['candidate_'+n]['sha256'] for n in ('weight','activation')),'logical_blocks_exclude_padding':True,'outputs_equal':x['candidate_output']['sha256']==y['candidate_output']['sha256'],'images':[x,y],'gate_pass':None}

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: compare_capture.py C5_DIR C6_DIR')
    print(json.dumps(compare(*sys.argv[1:]),indent=2,sort_keys=True))
