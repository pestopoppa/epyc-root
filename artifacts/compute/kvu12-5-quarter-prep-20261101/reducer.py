#!/usr/bin/env python3
"""Unqualified KVU-12.5 quarter successor reducer: pure, no hardware access."""
from __future__ import annotations
import json, math, statistics, sys

ANCHOR={'sum':12.48,'stream':11.93,'ttft':0.51}

def reduce_pair(u,s,uw,sw,quality):
    def invalid(reason): return {'verdict':'INVALID','reason':reason}
    if not isinstance(quality,dict) or not all(quality.get(k) is True for k in ('same_binary','same_model','same_source','same_argv','gpu_idle_both','quarter_bound_both','both_complete','no_errors','same_clients','cleanup_verified','warrant_captured')):
        return invalid('missing provenance, isolation, completeness, or capture')
    if any(not isinstance(ws,list) or len(ws)!=4 for ws in (uw,sw)):
        return invalid('expected four waves in each arm')
    def series(ws,key):
        vals=[]
        for i,w in enumerate(ws):
            if not isinstance(w,dict) or w.get('wave') != i or w.get('n_ok') != 8 or w.get('n_err') != 0 or w.get('errors'):
                raise ValueError('incomplete wave')
            if i==0: continue
            if key=='sum': v=w.get('decode_tps_sum')
            else:
                rates=w.get('decode_tps_per_stream')
                if not isinstance(rates,list) or len(rates)!=8: raise ValueError('bad streams')
                if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in rates): raise ValueError('invalid stream values')
                v=statistics.median(rates)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0: raise ValueError('invalid wave value')
            vals.append(v)
        return vals
    try:
        ser={m:{'unified':series(uw,m),'split':series(sw,m)} for m in ('sum','stream')}
        metric_map={'sum':'decode_tps_sum_med','stream':'decode_tps_stream_med','ttft':'ttft_s_med'}
        gap={}
        for m,k in metric_map.items():
            a,b=u[k],s[k]
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (a,b)): raise ValueError('invalid summary metric')
            gap[m]=100*(a-b)/b
        ranges={m:{a:100*(max(v)-min(v))/statistics.median(v) for a,v in d.items()} for m,d in ser.items()}
        floor={m:max(ANCHOR[m],*ranges[m].values()) for m in ('sum','stream')};floor['ttft']=ANCHOR['ttft']
        thr={m:max(2*value,3) for m,value in floor.items()}
        if gap['sum']>thr['sum'] and gap['stream']>thr['stream'] and gap['ttft']<=thr['ttft']: verdict='UNIFIED_BETTER'
        elif gap['sum'] < -thr['sum'] and gap['stream'] < -thr['stream']: verdict='SPLIT_BETTER'
        elif abs(gap['sum'])<=thr['sum'] or abs(gap['stream'])<=thr['stream']: verdict='NO_DIFFERENCE'
        else: verdict='MIXED'
        return {'verdict':verdict,'gap_pct':gap,'threshold_pct':thr,'floor_pct':floor,'wave_range_pct':ranges,'wave_values':ser,'normalization':'100*(max-min)/median of three decode waves; stream=per-wave median of 8','ttft_floor_note':'wave-0 TTFT uses np4 anchor only; no independent within-launch TTFT range'}
    except (KeyError,TypeError,ValueError,ZeroDivisionError) as exc: return invalid(str(exc))

if __name__=='__main__':
    data=json.load(sys.stdin); print(json.dumps(reduce_pair(**data),indent=2,allow_nan=False))
