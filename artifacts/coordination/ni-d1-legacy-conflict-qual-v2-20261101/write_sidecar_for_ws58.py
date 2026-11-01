#!/usr/bin/env python3
"""ws58 only: bind an authoritative legacy declaration to a live grant/launcher."""
import argparse
import json
import os
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'qual-v2'))
import keeper_qual_gate as gate

def main():
    p=argparse.ArgumentParser()
    p.add_argument('id');p.add_argument('--ports',required=True,
                   help='all listening ports, comma separated; explicit empty string allowed')
    p.add_argument('--shared-state',required=True,
                   help='all shared-state names, comma separated; explicit empty string allowed')
    p.add_argument('--exclusive-class',required=True,
                   help='class name or literal none')
    p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    if not gate.re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]+',a.id):p.error('bad id')
    f=gate.ROOT;grant=f/'grants'/(a.id+'.grant')
    state,_=gate.grant_status(grant)
    if state!='active':raise SystemExit('REFUSED: grant not active')
    if (f/'grants'/(a.id+'.ended')).exists() or (f/'grants'/(a.id+'.complete')).exists():
        raise SystemExit('REFUSED: grant ended')
    pid,birth=gate._owned_launcher(a.id,f)
    ports=[int(v) for v in a.ports.split(',') if v]
    if any(not 1 <= v <= 65535 for v in ports) or len(set(ports))!=len(ports):
        raise SystemExit('REFUSED: bad/duplicate port')
    shared=[v for v in a.shared_state.split(',') if v]
    obj={'schema':'epyc.legacy-declaration.v2','id':a.id,
         'grant_sha256':gate.q.sha(grant),'launcher_pid':pid,'launcher_birth_ticks':birth,
         'ports':ports,'shared_state':shared,
         'exclusive_class':None if a.exclusive_class=='none' else a.exclusive_class}
    path=f/'ws58-keeper-state/legacy-declarations-v2'/(a.id+'.json')
    if not a.apply:
        print(json.dumps({'mode':'dry-run','path':str(path),'declaration':obj},indent=2,sort_keys=True));return
    if os.environ.get('WS58_OWNER_BOUNDARY')!='1':raise SystemExit('REFUSED: ws58 owner boundary marker required')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.exists() or path.is_symlink():raise SystemExit('REFUSED: sidecar exists; no overwrite')
    if gate.q.sha(grant)!=obj['grant_sha256'] or gate._birth(pid)!=birth:
        raise SystemExit('REFUSED: grant/launcher changed')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as out:json.dump(obj,out,sort_keys=True);out.write('\n')
    print(json.dumps({'applied':str(path),'sha256':gate.q.sha(path)}))

if __name__=='__main__':main()
