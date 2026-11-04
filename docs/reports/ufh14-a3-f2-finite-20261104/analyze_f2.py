#!/usr/bin/env python3
"""Project F2 SSE arrival gaps without assigning a keep verdict."""
import json, math, pathlib, statistics, sys
import client_ttft

LEGS=('cold1','all4warm1','all4warm2','cold2')
DELTA_TYPES=client_ttft.OUTPUT_TYPES

def verified_generated_arrivals(member):
    proof=client_ttft.project(member)
    raw=[]
    for line in pathlib.Path(member['raw']).read_text().splitlines():
        if line.startswith('data:'):
            payload=line[5:].strip()
            if payload!='[DONE]':raw.append(json.loads(payload))
    assert len(raw)==proof['event_count']
    return [float(captured['t']) for event,captured in zip(raw,member['events'])
            if event.get('type') in DELTA_TYPES and event.get('delta')]

def quantile(values,p):
    x=sorted(values); i=(len(x)-1)*p; lo=int(i); hi=min(lo+1,len(x)-1)
    return x[lo]+(x[hi]-x[lo])*(i-lo)

def project(root):
    result={'scope':'UFH14-A3A-F2 descriptive paired decode-stall proxy; no keep threshold',
            'order':list(LEGS),'lower_gap_is_better':True,'legs':{}}
    for leg in LEGS:
        base=root/leg
        group=json.loads((base/'group/native-group.json').read_text())
        bindings=json.loads((base/'group/timing-bindings.json').read_text())
        quiet=json.loads((base/'q3-kfd-samples.summary.json').read_text())
        expected_warm=not leg.startswith('cold')
        if len(group['warm_requests'])!=(4 if expected_warm else 0) or len(group['members'])!=2:
            raise ValueError(f'{leg}: wrong request count')
        requests=group['warm_requests']+group['members']
        if len(bindings)!=len(requests) or not quiet['q3_quiet']:
            raise ValueError(f'{leg}: timing/quiet proof missing')
        request_ids=[x.get('request_sha256') for x in requests]
        binding_ids=[x.get('request_sha256') for x in bindings]
        if any(not x for x in request_ids+binding_ids) or len(set(request_ids))!=len(requests) or len(set(binding_ids))!=len(bindings) or set(request_ids)!=set(binding_ids):
            raise ValueError(f'{leg}: missing, duplicate or mismatched timing request join')
        by_id={x['request_sha256']:x for x in bindings}
        if expected_warm and any(not x['native_slot_binding_ok'] for x in group['warm_requests']):
            raise ValueError(f'{leg}: native warm-slot binding failed')
        member_rows=[]
        for i,member in enumerate(group['members']):
            stamps=verified_generated_arrivals(member)
            if len(stamps)<3 or stamps!=sorted(stamps):raise ValueError(f'{leg} member{i}: missing/unsorted generated SSE')
            gaps=[b-a for a,b in zip(stamps,stamps[1:])]
            bins=[0,0,0,0,0]
            for gap in gaps:
                bins[0 if gap<.01 else 1 if gap<.1 else 2 if gap<1 else 3 if gap<5 else 4]+=1
            timing=by_id[member['request_sha256']]['timings']
            for field in ('predicted_n', 'predicted_ms', 'cache_n', 'prompt_n'):
                value=timing[field]
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                    raise ValueError(f'{leg} member{i}: invalid native {field}')
            if timing['predicted_n']<=0 or timing['predicted_ms']<=0:raise ValueError(f'{leg} member{i}: no native decode timing')
            member_rows.append({'member':i,'delta_events':len(stamps),'gaps':len(gaps),
                                'gap_median_s':statistics.median(gaps),'gap_p95_s':quantile(gaps,.95),
                                'gap_p99_s':quantile(gaps,.99),'gap_max_s':max(gaps),
                                'gap_histogram_bins_s':['<0.01','0.01-0.1','0.1-1','1-5','>=5'],
                                'gap_histogram_counts':bins,'native_predicted_n':timing['predicted_n'],
                                'native_predicted_ms':timing['predicted_ms'],
                                'native_decode_tok_s':1000*timing['predicted_n']/timing['predicted_ms'],
                                'cache_n':timing['cache_n'],'prompt_n':timing['prompt_n'],
                                'raw_sse':member['raw']})
        if expected_warm and any(x['cache_n']<=0 for x in member_rows):
            raise ValueError(f'{leg}: member cache miss; warm comparison invalid')
        result['legs'][leg]={'members':member_rows,'quiet':quiet,
                             'member_gap_p95_median_s':statistics.median(x['gap_p95_s'] for x in member_rows)}
    result['adjacent_pairs']=[{'cold':c,'warm':w,'warm_minus_cold_member_gap_p95_median_s':
                               result['legs'][w]['member_gap_p95_median_s']-result['legs'][c]['member_gap_p95_median_s']}
                              for c,w in (('cold1','all4warm1'),('cold2','all4warm2'))]
    result['status']='COMPLETE_DESCRIPTIVE'
    return result

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: analyze_f2.py ATTEMPT_DIR')
    root=pathlib.Path(sys.argv[1]); out=root/'F2-RESULT.json'
    out.write_text(json.dumps(project(root),indent=2)+'\n')
    print(out)
