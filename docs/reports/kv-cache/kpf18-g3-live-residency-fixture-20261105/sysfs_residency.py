#!/usr/bin/env python3
"""MI210 PCI/KFD-bound high-frequency residency evidence for G3.

Read-only; this does not establish exclusive device ownership. KFD vram_<id>
is the captured PID's allocation and DRM mem_info_vram_used is device-wide.
"""
import os
import math
from pathlib import Path
import re
import time

BDF='0000:43:00.0'
VENDOR=0x1002
DEVICE=0x740f
UNIQUE=0xc6cb1cf088bd97ec


def discover(drm=Path('/sys/class/drm'), nodes=Path('/sys/class/kfd/kfd/topology/nodes')):
    cards=[]
    for card in Path(drm).iterdir():
        if not re.fullmatch(r'card[0-9]+', card.name): continue
        dev=card/'device'
        if dev.resolve(strict=True).name != BDF: continue
        if int((dev/'vendor').read_text(),0)!=VENDOR or int((dev/'device').read_text(),0)!=DEVICE or int((dev/'unique_id').read_text(),16)!=UNIQUE:
            raise ValueError('wrong PCI device identity')
        cards.append((card, dev.resolve(strict=True)))
    if len(cards)!=1: raise ValueError('MI210 card missing or ambiguous')
    card, device=cards[0]; found=[]
    for node in Path(nodes).iterdir():
        if not node.name.isdigit(): continue
        props={}
        for line in (node/'properties').read_text().splitlines():
            parts=line.split()
            if len(parts)!=2 or parts[0] in props: raise ValueError('bad KFD properties')
            props[parts[0]]=int(parts[1],0)
        if props.get('unique_id')!=UNIQUE: continue
        if any(props.get(k)!=v for k,v in {'vendor_id':VENDOR,'device_id':DEVICE,'location_id':0x4300,'domain':0}.items()):
            raise ValueError('KFD topology mismatch')
        gid=int((node/'gpu_id').read_text()); minor=props.get('drm_render_minor')
        if gid<=0 or type(minor) is not int or minor<128 or (Path(drm)/f'renderD{minor}'/'device').resolve(strict=True)!=device:
            raise ValueError('KFD render device mismatch')
        found.append(gid)
    if len(found)!=1: raise ValueError('MI210 KFD node missing or ambiguous')
    return {'bdf':BDF,'unique_id':UNIQUE,'gpu_id':found[0], 'card':card.name,
            'device_vram':str(card/'device/mem_info_vram_used'), 'drm':str(drm), 'nodes':str(nodes)}


def proc_birth(pid, proc_root=Path('/proc')):
    raw=(Path(proc_root)/str(pid)/'stat').read_text()
    return int(raw[raw.rfind(')')+2:].split()[19])


def read_sysfs_sample(*, pid, birth, device, backend, proc_root=Path('/proc'), kfd_root=Path('/sys/class/kfd/kfd/proc')):
    start=time.time(); mono_start=time.monotonic()
    proc=Path(proc_root)/str(pid)
    if proc_birth(pid,proc_root)!=birth: raise ValueError('process birth changed')
    backend=Path(backend).resolve(strict=True); st=backend.stat()
    expected=f'{os.major(st.st_dev):x}:{os.minor(st.st_dev):x}'
    mapped=False
    for line in (proc/'maps').read_text().splitlines():
        fields=line.split(maxsplit=5)
        if len(fields)==6:
            try:
                dev=':'.join(f'{int(part,16):x}' for part in fields[3].split(':'))
                if dev==expected and int(fields[4])==st.st_ino and fields[5]==str(backend): mapped=True
            except (ValueError,IndexError): pass
    ownpath=Path(kfd_root)/str(pid)/('vram_'+str(device['gpu_id']))
    own=int(ownpath.read_text()) if ownpath.is_file() else None
    total=int(Path(device['device_vram']).read_text())
    if proc_birth(pid,proc_root)!=birth: raise ValueError('process birth changed during sample')
    end=time.time(); mono_end=time.monotonic()
    if total<0 or (own is not None and own<0): raise ValueError('negative VRAM count')
    return {'observation_start':start,'observation_end':end,'monotonic_start':mono_start,'monotonic_end':mono_end,
            'pid':pid,'birth':birth,'gpu_id':device['gpu_id'],'hip_mapped':mapped,'own_vram_bytes':own,
            'device_vram_bytes':total,'kfd_pid_present':(Path(kfd_root)/str(pid)).is_dir()}


def correlate(*, calls, samples, pid, birth, gpu_id):
    out=[]
    for call in calls:
        a,t,b=call['native_begin'],call['native_dispatch'],call['native_end']
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (a,t,b)) or not a<t<b:
            raise ValueError('invalid native time window')
        valid=[s for s in samples if s.get('pid')==pid and s.get('birth')==birth and s.get('gpu_id')==gpu_id
               and s.get('hip_mapped') is True and s.get('kfd_pid_present') is True
               and type(s.get('own_vram_bytes')) is int and s['own_vram_bytes']>0
               and type(s.get('device_vram_bytes')) is int and s['device_vram_bytes']>0
               and all(type(s.get(k)) in (int,float) and math.isfinite(s[k]) for k in ('observation_start','observation_end'))
               and a <= s['observation_start'] <= s['observation_end'] <= b]
        distinct={(s['observation_start'],s['observation_end']) for s in valid}
        hit=[s for s in valid if s['observation_start']<=t<=s['observation_end']]
        out.append({'invocation':call['invocation'],'native_dispatch':t,
                    'status':'BOUNDED_OBSERVATION' if len(distinct)>=2 and hit else 'UNKNOWN',
                    'valid_sample_count':len(valid),'overlap_count':len(hit)})
    return out
