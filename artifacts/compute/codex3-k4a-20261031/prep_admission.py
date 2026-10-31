#!/usr/bin/env python3
"""Read-only R6 admission; fixtures inject strings, never write grant files."""
import datetime
from pathlib import Path
import re
import time

FLAGS=Path('/mnt/raid0/llm/tmp/compute-flags')
CLASSES={'filler','block-correctness','block-timing-pairable','block-timing-quiet'}

def regions(raw):
    cpus=set()
    for token in raw.split(','):
        if re.fullmatch(r'mi210_\d+',token): continue
        if re.fullmatch(r'q[0-3]',token):
            start=int(token[1])*24; cpus.update(range(start,start+24)); continue
        m=re.fullmatch(r'(\d+)(?:-(\d+))?',token)
        if not m: raise ValueError('unparseable grant region')
        lo=int(m.group(1));hi=int(m.group(2) or lo)
        if lo>hi or hi>191: raise ValueError('invalid cpu range')
        cpus.update(range(lo,hi+1))
    return cpus

def queue_classes(text):
    result={}
    for line in text.splitlines():
        if not line.lstrip().startswith('|'): continue
        cells=[x.strip().strip('`') for x in line.split('|')[1:-1]]
        if len(cells)!=18 or cells[0].lower() in ('filler-id','---'): continue
        if cells[0] in result: raise ValueError('duplicate queue row')
        result[cells[0]]=cells[8]
    if not result: raise ValueError('no valid queue rows')
    return result

def check(pair, rows, records, now):
    if len(pair)!=2: raise ValueError('R6 requires exactly two CPUs')
    busy=[]
    for ident,raw in records:
        cls=rows.get(ident)
        if cls not in CLASSES: raise ValueError('unclassified grant')
        m=re.fullmatch(r'regions=(\S+) start=(\S+) end=(\S+)\s*',raw)
        if not m: raise ValueError('malformed grant')
        def ts(x):
            d=datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
            if d.tzinfo is None or d.utcoffset() is None: raise ValueError('naive grant time')
            return d.timestamp()
        start,end=ts(m.group(2)),ts(m.group(3))
        if end<=start: raise ValueError('invalid grant window')
        if start<=now<end:
            cpu=regions(m.group(1));busy.append(cpu)
            if cls.startswith('block-timing'): raise ValueError('timing grant active')
            if pair & cpu: raise ValueError('grant overlaps prep CPUs')
    # SMT fallback is justified only when every physical quarter has a live grant.
    if min(pair)>=96:
        physical=set().union(*busy) if busy else set()
        if any(not (physical & set(range(q*24,(q+1)*24))) for q in range(4)):
            raise ValueError('SMT fallback requires all quarters granted')
    return True

def live(pair):
    rows=queue_classes((FLAGS/'FILLERS.md').read_text())
    records=[]
    for p in (FLAGS/'grants').glob('*.grant'):
        if p.is_symlink() or not p.is_file(): raise ValueError('unsafe grant file')
        try: raw=p.read_text()
        except FileNotFoundError: raise ValueError('grant changed while reading')
        records.append((p.name[:-6],raw))
    return check(set(pair),rows,records,time.time())
