import copy,csv,json,re,sys
from pathlib import Path
from hsa_clock import offset_interval

def check(before,after,log,rows):
    if type(before.get('frequency_hz')) is not int or not 0 < before['frequency_hz'] <= (1 << 64) - 1: raise ValueError('invalid HSA frequency')
    if len(before['samples'])<2 or len(after['samples'])<2: raise ValueError('insufficient brackets')
    lo,hi=offset_interval([before,after])
    if hi-lo>1000000: raise ValueError('offset uncertainty exceeds 1ms bound')
    m=re.search(r'^IDENTITY pid=(\d+) birth=(\d+) bdf=([0-9a-fA-F:.]+) device=(\d+)$',log,re.M)
    if not m: raise ValueError('missing process and device identity')
    pid,birth=int(m[1]),int(m[2]); bdf=m[3].lower()
    if pid<=0 or birth<=0: raise ValueError('bad process identity')
    device=Path('/sys/bus/pci/devices')/bdf
    if (device/'vendor').read_text().strip()!='0x1002' or (device/'device').read_text().strip()!='0x740f': raise ValueError('not selected MI210')
    host=re.findall(r'^WITNESS ([012]) (\d+) (\d+)$',log,re.M)
    if [int(r[0]) for r in host]!=[0,1,2]: raise ValueError('missing or duplicated host witnesses')
    spans=[(int(b),int(e)) for _,b,e in host]
    if any(b>=e for b,e in spans) or any(spans[i+1][0]-spans[i][1] not in range(4_000_000_000,6_000_000_001) for i in (0,1)): raise ValueError('bad witness spacing')
    if max(r['host_after_ns'] for r in before['samples'])>spans[0][0] or min(r['host_before_ns'] for r in after['samples'])<spans[-1][1]: raise ValueError('samples do not bracket witnesses')
    picked=[]
    for i,name in enumerate(('kvu19b_witness_a','kvu19b_witness_b','kvu19b_witness_c')):
        rr=[r for r in rows if name in r['KernelName']]
        if len(rr)!=1: raise ValueError('missing or duplicate profiler witness')
        r=rr[0]; begin,end=int(r['BeginNs']),int(r['EndNs'])
        if int(r['pid'])!=pid or not (0<begin<end) or not(spans[i][0]<=begin+lo<=begin+hi and end+lo<=end+hi<=spans[i][1]): raise ValueError('witness binding or containment failure')
        picked.append(r)
    if len({r['gpu-id'] for r in picked})!=1 or len({r['queue-id'] for r in picked})!=1: raise ValueError('changed profiler device or queue')
    target=re.findall(r'^TARGET (\d+) (\d+)$',log,re.M)
    if len(target)!=1: raise ValueError('missing or duplicated target host interval')
    tb,te=map(int,target[0])
    if not spans[1][0]<=tb<te<=spans[1][1]: raise ValueError('target host interval outside witness')
    rr=[r for r in rows if 'kvu19b_fixture_target' in r['KernelName']]
    if len(rr)!=1: raise ValueError('missing or duplicate target dispatch')
    t=rr[0]; begin,end=int(t['BeginNs']),int(t['EndNs'])
    if int(t['pid'])!=pid or t['gpu-id']!=picked[0]['gpu-id'] or t['queue-id']!=picked[0]['queue-id'] or not (0<begin<end): raise ValueError('target identity or time mismatch')
    # Conditional fixture test only: the endpoint intersection is not proof of interior drift.
    if not (tb<=begin+lo<=begin+hi and end+lo<=end+hi<=te): raise ValueError('conditional target containment failure')
    return {'target_classification':'CONDITIONAL_ON_CONSTANT_OFFSET; interior drift UNKNOWN','target_host_ns':[tb,te],'pid':pid,'birth_ticks':birth,'bdf':bdf,'profiler_gpu_id':picked[0]['gpu-id'],'queue_id':picked[0]['queue-id'],'offset_ns':[lo,hi],'max_gap_ns':6000000000,'uncertainty_bound_ns':1000000,'scope':'witness points only; no interpolation or continuous drift bound'}

def main(d):
    before=json.loads((d/'before.json').read_text());after=json.loads((d/'after.json').read_text());log=(d/'witness.log').read_text()
    with (d/'dispatch.csv').open(newline='') as f: rows=list(csv.DictReader(f))
    result=check(before,after,log,rows)
    tests=[]
    for label,mut in [('missing',lambda x:x.pop()),('duplicate',lambda x:x.append(dict(x[-1]))),('wrong_pid',lambda x:x[-1].update(pid='1')),('bad_time',lambda x:x[-1].update(BeginNs='-1'))]:
        selected=[copy.copy(r) for r in rows if 'kvu19b_witness_' in r['KernelName']]; target=[copy.copy(r) for r in rows if 'kvu19b_fixture_target' in r['KernelName']];mut(selected);selected+=target
        try: check(before,after,log,selected)
        except (ValueError,KeyError,TypeError): tests.append(label)
        else: raise ValueError('mutation was not detected: '+label)
    
    host=re.findall(r'^WITNESS ([012]) (\d+) (\d+)$',log,re.M)
    overlong=log.replace('WITNESS 1 '+host[1][1]+' '+host[1][2], 'WITNESS 1 '+str(int(host[0][2])+6_000_000_001)+' '+str(int(host[0][2])+6_000_000_100))
    try: check(before,after,overlong,rows)
    except ValueError: tests.append('spacing_over_6s')
    else: raise ValueError('spacing mutation not detected')
    for label,mut in [('target_missing',lambda x:x.pop()),('target_duplicate',lambda x:x.append(dict(x[-1]))),('target_pid',lambda x:x[-1].update(pid='1')),('target_queue',lambda x:x[-1].update(**{'queue-id':'-1'})),('target_gpu',lambda x:x[-1].update(**{'gpu-id':'-1'})),('target_time',lambda x:x[-1].update(BeginNs='-1'))]:
        selected=[copy.copy(r) for r in rows if 'kvu19b_witness_' in r['KernelName'] or 'kvu19b_fixture_target' in r['KernelName']]
        targets=[r for r in selected if 'kvu19b_fixture_target' in r['KernelName']]
        if len(targets)!=1: raise ValueError('fixture target count')
        # Make target last for mutation controls.
        selected.remove(targets[0]);selected.append(targets[0]);mut(selected)
        try: check(before,after,log,selected)
        except (ValueError,KeyError,TypeError): tests.append(label)
        else: raise ValueError('mutation was not detected: '+label)
    result['mutations_detected']=tests
    (d/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]))
