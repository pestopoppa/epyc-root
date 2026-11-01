#!/usr/bin/env python3
"""Keeper-owned, fixed-version routing; never grants or issues qualification."""
import json
import os
from pathlib import Path
import sys

BASE=Path('/mnt/raid0/llm/tmp/compute-flags/bin')
V1=BASE/'qual-v1'
V2=BASE/'qual-v2-row'

def version(manifest):
    p=Path(manifest)
    if p.is_symlink() or not p.is_file(): raise ValueError('manifest missing or symlink')
    m=json.loads(p.read_text())
    if not isinstance(m,dict): raise ValueError('manifest not an object')
    if 'qualifier_version' not in m: return V1
    if m['qualifier_version']!='epyc.qual-v2-row': raise ValueError('unknown qualifier version')
    llm=m.get('llm',{})
    if not isinstance(llm,dict): raise ValueError('malformed llm selector')
    backend=llm.get('backend','server')
    if backend not in ('server','native-batched-bench'): raise ValueError('unknown qualifier backend')
    return V2

def main(argv):
    if not argv: raise ValueError('command required')
    command=argv[0];rest=argv[1:]
    if command=='reconcile-failures':
        if '--manifest' in rest: raise ValueError('unexpected manifest')
        target=V2/'keeper_qual_gate.py'
    else:
        if command not in ('check','conflict','qualify-pending','select','canonical-row','bootstrap-row'): raise ValueError('unknown command')
        if rest.count('--manifest')!=1: raise ValueError('exactly one --manifest required')
        i=rest.index('--manifest')
        if i+1>=len(rest):raise ValueError('manifest path missing')
        selected=version(rest[i+1])
        if command=='select':
            if len(rest)!=2: raise ValueError('unexpected selector arguments')
            print(selected/'qualify_launcher.py');return 0
        if command=='bootstrap-row' and selected==V1:
            # V1 has no draft bootstrap; its own qualify-pending validates the
            # existing canonical row before issuing anything. Do not write it.
            print('ok\tlegacy v1: defer canonical checks to v1 qualifier');return 0
        if command=='canonical-row' and selected==V1:
            command='check'  # v1 verify already requires its canonical row
        # The shared v2 conflict check verifies each booked peer with its own
        # version; otherwise a v1/v2 cross-version reservation can disappear.
        target=(V2 if command in ('conflict','bootstrap-row') else selected)/'keeper_qual_gate.py'
    os.execv('/usr/bin/python3',['/usr/bin/python3','-I',str(target),command,*rest])
    raise AssertionError('unreachable')
if __name__=='__main__':
    try: raise SystemExit(main(sys.argv[1:]))
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as e:
        print('bad\tqualifier route: '+str(e));raise SystemExit(2)
