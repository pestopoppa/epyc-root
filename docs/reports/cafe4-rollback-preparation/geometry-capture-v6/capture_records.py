"""Project V6 native case logs into separately hashed arm records, without grading.

The caller must supply the actual captured grant, compiler/build/model identity,
process and mapped-library observations. Missing metadata or incomplete native
arms raises CaptureError; preserve the raw log and mark the case UNKNOWN.
"""
import hashlib
import re


class CaptureError(ValueError):
    pass


def parse_native_arms(raw):
    if not isinstance(raw, bytes):
        raise CaptureError('native log must be bytes')
    lines = raw.decode('utf-8', 'strict').splitlines(keepends=True)
    arms, active = {}, None
    for line in lines:
        m = re.fullmatch(r'CAFE4_CAPTURE mode=([012]) phase=begin\n', line)
        if m:
            mode = int(m.group(1))
            if active is not None or mode in arms or mode != len(arms):
                raise CaptureError('nested, duplicate or out-of-order arm')
            active = {'mode': mode, 'raw': [line], 'fields': {}}
            continue
        if active is None:
            continue
        active['raw'].append(line)
        m = re.fullmatch(r'CAFE4_CAPTURE mode=([012]) field=(prompt|draft) count=(\d+) tokens=([0-9,]+)\n', line)
        if m:
            mode, key, count, values = int(m.group(1)), m.group(2), int(m.group(3)), [int(x) for x in m.group(4).split(',')]
            if mode != active['mode'] or key in active['fields'] or len(values) != count or not values:
                raise CaptureError('invalid token capture')
            active['fields'][key] = values
            continue
        m = re.fullmatch(r'CAFE4_CAPTURE mode=([012]) field=boundary token=(\d+)\n', line)
        if m:
            mode, token = int(m.group(1)), int(m.group(2))
            if mode != active['mode'] or 'boundary' in active['fields']: raise CaptureError('invalid boundary')
            active['fields']['boundary'] = token
            continue
        m = re.fullmatch(r'CAFE4_CAPTURE mode=([012]) field=partial natural=(\d+) accepted=(\d+) width=(\d+) keep=(\d+) sampled=(\d+)\n', line)
        if m:
            mode, natural, accepted, width, keep, sampled = map(int,m.groups())
            if mode != active['mode'] or 'partial' in active['fields']: raise CaptureError('invalid partial')
            active['fields']['partial'] = dict(natural=natural,accepted=accepted,width=width,keep=keep,sampled=sampled)
            continue
        m = re.fullmatch(r'CAFE4_CAPTURE mode=([012]) field=seq_rm target=1 draft=1 keep=(\d+)\n', line)
        if m:
            mode, keep = map(int,m.groups())
            if mode != active['mode'] or 'seq_rm' in active['fields']: raise CaptureError('invalid removal')
            active['fields']['seq_rm'] = dict(target=True,draft=True,keep=keep)
            continue
        m = re.fullmatch(r'CAFE4_CAPTURE mode=([012]) field=replay token=(\d+) pos=(\d+) rc=0\n', line)
        if m:
            mode, token, pos = map(int,m.groups())
            if mode != active['mode'] or 'replay' in active['fields']: raise CaptureError('invalid replay')
            active['fields']['replay'] = dict(token=token,pos=pos,rc=0)
            continue
        m = re.fullmatch(r'CAFE4_CAPTURE mode=([012]) phase=complete selected=(\d+) faulted=(\d+)\n', line)
        if m:
            mode, selected, faulted = map(int,m.groups()); f=active['fields']
            if mode != active['mode'] or set(f) != {'prompt','draft','boundary','partial','seq_rm','replay'}: raise CaptureError('incomplete arm')
            x=f['partial']; rm=f['seq_rm']; replay=f['replay']
            if not (x['width']==len(f['draft']) and 0<x['accepted']<x['width'] and x['accepted']<=x['natural']<=x['width'] and x['keep']==len(f['prompt'])+1+x['accepted'] and rm['keep']==x['keep'] and replay['pos']==x['keep'] and replay['token']==x['sampled']): raise CaptureError('inconsistent verify/removal/replay')
            if not ((mode==0 and selected==0 and faulted==0) or (mode==1 and selected>0 and faulted==0) or (mode==2 and selected>0 and faulted>0)): raise CaptureError('missing target state witness')
            segment=''.join(active['raw']).encode('utf-8'); arms[mode]={'arm':('off','observe','fault')[mode],'expected':'nonfault' if mode<2 else 'injected-target-state-fault','tokens':f,'selected':selected,'faulted':faulted,'native_segment_sha256':hashlib.sha256(segment).hexdigest(),'native_segment':segment.decode('utf-8')};active=None
        elif line.startswith('CAFE4_CAPTURE '): raise CaptureError('unrecognized capture marker')
    if active is not None or set(arms)!={0,1,2}: raise CaptureError('missing or truncated arms')
    identity=lambda x:(x['tokens']['prompt'],x['tokens']['boundary'],x['tokens']['draft'],x['tokens']['partial'])
    if identity(arms[0])!=identity(arms[1]) or identity(arms[1])!=identity(arms[2]): raise CaptureError('arms use different token trajectories')
    return [arms[i] for i in range(3)]
