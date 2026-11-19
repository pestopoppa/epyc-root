#!/usr/bin/env python3
"""Offline diagnostic receipt validator. No target access; no performance verdict."""
import argparse, csv, hashlib, io, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent/'vendor'))
from select_step import first_step
from hsa_clock import offset_interval
from verify_clock_smoke import verify as verify_smoke

SOURCE='1e8a6d5da9836a27e8f1d2010a02e6cebd95abdc'
def need(x, why):
    if not x: raise ValueError(why)
def integer(x): return type(x) is int
def digest(x): return isinstance(x,str) and re.fullmatch('[0-9a-f]{64}',x) is not None
def validate(root, m, expected):
    # expected is a separately sealed, operator-reviewed identity policy, never inferred from receipt.
    need(m['schema']=='epyc.kpf50.native-window.v1','schema')
    need(type(m['synthetic']) is bool,'synthetic classification')
    need(expected['source_commit']==SOURCE,'candidate source')
    need(m['identity']==expected,'candidate/model/drafter/DSO/argv/prompt identity mismatch')
    for k in ('server_sha256','model_sha256','drafter_sha256','argv_sha256','prompt_sha256'):
        need(digest(expected[k]),'missing identity '+k)
    need(expected['dso_sha256'] and all(digest(x) for x in expected['dso_sha256'].values()),'DSO identities')
    need(any('hip' in x.lower() for x in expected['dso_sha256']),'HIP DSO missing')
    need(expected['drafter']=='DFlash2','drafter')
    need(m['window_index'] in range(4) and type(m['window_index']) is int,'window index')
    need(m['mode']==('full','mask','mask','full')[m['window_index']],'window order')
    need(m['complete'] is True and m['partial'] is False and m['fresh_model'] is True,'incomplete or nonfresh window')
    pid=m['pid']; birth=m['pid_birth']; need(integer(pid) and pid>0 and isinstance(birth,str) and birth,'PID identity')
    def raw(key):
        ref=m['artifacts'][key]; p=(root/ref['path']).resolve()
        need(p.is_relative_to(root.resolve()),'artifact escapes bundle')
        data=p.read_bytes(); need(hashlib.sha256(data).hexdigest()==ref['sha256'],'artifact digest '+key)
        return data.decode()
    def obj(key): return json.loads(raw(key))
    log=raw('server_log')
    # Existing selector is first-candidate conservative. Reject duplicate joined records it would overwrite.
    for marker in ('KPF30_PHASE','KPF50_INPUT'):
        keys=re.findall(marker+r' call=(\d+) index=(\d+)',log)
        need(len(keys)==len(set(keys)),'duplicate '+marker)
    s=first_step(log.splitlines(),int(m['mode']=='mask'))
    need(s['phase'] in ('decode','verify'),'mixed phase')
    need(all(kv>=80000 for _,kv,_,_ in s['masks']),'missing 80k physical mask extent')
    need(all(p==s['phase'] for p in s['iteration']['all_phases']),'mixed enclosing iteration')
    a,b=s['iteration']['start_ns'],s['iteration']['end_ns']
    start=m['attempt_start_ns']; need(integer(start) and start<a,'attempt marker must precede target')
    children=obj('children'); need(len(children)==4,'four child fork receipts')
    suffix=set(); seq=set()
    for c in children:
        need(c['role']=='child' and c['http']==200 and c['error'] is None,'child outcome')
        need(integer(c['suffix_index']) and c['suffix_index'] in range(4),'suffix')
        suffix.add(c['suffix_index']); seq.add(c['seq_id'])
        n=c['timings']['n_fork_tokens']; need(integer(n) and n>=60000,'fork under 60000')
        need(c['context_tokens']==80000 and c['trunk_tokens']==60000 and c['suffix_tokens']==20000,'80k shape')
    need(len(suffix)==4 and len(seq)==4 and seq=={i[0] for i in s['inputs']},'child/step sequence join')
    shape=obj('shape')
    need(shape==[{'seq_id':c['seq_id'],'context_tokens':80000,'trunk_tokens':60000,'suffix_tokens':20000} for c in children],'explicit native shape join')
    maps=obj('process_maps')
    need(maps['pid']==pid and maps['pid_birth']==birth and a<=maps['host_ns']<=b,'maps PID/time')
    need(maps['server_sha256']==expected['server_sha256'] and maps['model_sha256']==expected['model_sha256'] and maps['drafter_sha256']==expected['drafter_sha256'] and maps['dso_sha256']==expected['dso_sha256'],'mapped identities')
    samples=obj('residency'); good=[]
    for r in samples:
        need(r['pid']==pid and r['pid_birth']==birth,'residency PID')
        if s['start_ns']<=r['host_ns']<=s['end_ns']:
            need(r['kfd'] is True and integer(r['vram_bytes']) and r['vram_bytes']>0 and r['device']==expected['device'],'own-PID GPU residency')
            good.append(r)
    need(len({r['host_ns'] for r in good})>=2,'two during-step residency samples')
    before,after=obj('clock_before'),obj('clock_after'); lo,hi=offset_interval([before,after])
    need(max(r['host_after_ns'] for r in before['samples'])<=a and min(r['host_before_ns'] for r in after['samples'])>=b,'clock bracketing')
    smoke=verify_smoke(obj('smoke_before'),obj('smoke_after'),raw('smoke_log'),list(csv.DictReader(io.StringIO(raw('smoke_csv')))))
    need(smoke['verified'] is True,'clock witness')
    rows=list(csv.DictReader(io.StringIO(raw('dispatch_csv')))); dispatch=[]
    for r in rows:
        x,y=int(r['BeginNs']),int(r['EndNs']); need(0<=x<y,'dispatch interval')
        if x<b-lo and y>a-hi:
            need(a<=x+lo and y+hi<=b,'ambiguous iteration boundary')
        if x<s['end_ns']-lo and y>s['start_ns']-hi:
            need(s['start_ns']<=x+lo and y+hi<=s['end_ns'],'ambiguous step boundary')
            need(r['KernelName'] in expected['dispatch_families'],'unknown dispatch family')
            dispatch.append((x,y,r['KernelName'],expected['dispatch_families'][r['KernelName']]))
    need(dispatch,'no target dispatch')
    dispatch.sort(); need(all(x[1]<=y[0] for x,y in zip(dispatch,dispatch[1:])),'overlapping dispatches')
    need(any(x[3]=='attention' for x in dispatch),'no attention dispatch')
    return {'schema':'epyc.kpf50.validated-window.v1','valid':m['synthetic'], 'status':'SYNTHETIC_CONTROL_ONLY' if m['synthetic'] else 'UNKNOWN', 'native_binding':'UNPROVED: raw physical process/map/shape provenance parser unavailable', 'synthetic':m['synthetic'], 'window_index':m['window_index'],'identity':expected,'step':s,'dispatch_families':[x[2:] for x in dispatch], 'clock_bounds':[lo,hi],'gate_verdict':'UNRESOLVED','kv_value_identity':'unproved'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('bundle',type=Path);ap.add_argument('--expected',type=Path,required=True);ap.add_argument('--expected-sha256',required=True);a=ap.parse_args()
    try:
        data=a.expected.read_bytes();need(hashlib.sha256(data).hexdigest()==a.expected_sha256,'policy seal')
        result=validate(a.bundle,json.loads((a.bundle/'window.json').read_text()),json.loads(data));print(json.dumps(result,sort_keys=True))
        if result['status']=='UNKNOWN': return 3
    except (KeyError,TypeError,ValueError,OSError,OverflowError) as e:
        print(json.dumps({'valid':False,'reason':str(e),'gate_verdict':'UNRESOLVED'}));return 2
    return 0
if __name__=='__main__':sys.exit(main())
