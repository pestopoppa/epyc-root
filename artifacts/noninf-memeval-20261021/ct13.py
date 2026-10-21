import json,collections as C
F='/mnt/raid0/llm/tmp/inference_tap_events.jsonl'
R={}
for l in open(F):
    e=json.loads(l); rid=e.get('request_id')
    if not rid: continue
    r=R.setdefault(rid,{'role':e['role'],'port':e['port'],'t0':None,'t1':None,'txt':0,'tokens':None,'resp':0,'start':False})
    if e['event']=='start': r['t0']=e['ts_epoch'];r['start']=True
    elif e['event']=='end': r['t1']=e['ts_epoch']
    elif e['event']=='chunk': r['txt']+=len((e.get('text') or '').strip())
    elif e['event']=='response': r['resp']+=len((e.get('text') or '').strip())
    elif e['event']=='timings': r['tokens']=e.get('tokens')
def rep(name,sel):
    rows=[r for r in R.values() if r['start'] and sel(r)]
    n=len(rows); done=[r for r in rows if r['t1'] and r['t0']]
    blank=[r for r in done if r['txt']+r['resp']==0]
    blank30=[r for r in blank if r['t1']-r['t0']>=30]
    noend=n-len(done)
    print('%-34s turns=%d with_end=%d no_end=%d blank=%d blank>=30s=%d  share_blank>=30s=%.4f share_blank=%.4f'%(name,n,len(done),noend,len(blank),len(blank30),len(blank30)/max(1,len(done)),len(blank)/max(1,len(done))))
rep('port 8083 (all roles)',lambda r:r['port']==8083)
for role in ['architect_general','coder_escalation','architect_critic','ingest_long_context']:
    rep('8083 '+role,lambda r,role=role:r['port']==8083 and r['role']==role)
rep('all roles',lambda r:True)
for p in sorted({r['port'] for r in R.values()}):
    rep('port %s'%p,lambda r,p=p:r['port']==p)
import statistics as st
b=[r for r in R.values() if r['start'] and r['port']==8083 and r['role']=='architect_general' and r['t1'] and r['txt']+r['resp']==0]
nb=[r for r in R.values() if r['start'] and r['port']==8083 and r['role']=='architect_general' and r['t1'] and r['txt']+r['resp']>0]
f=lambda L,k:[float(r[k]) for r in L if r[k] is not None]
print('blank dur med/max',st.median([r['t1']-r['t0'] for r in b]),max(r['t1']-r['t0'] for r in b),'tokens med',st.median(f(b,'tokens')) if f(b,'tokens') else None, 'n tokens',len(f(b,'tokens')))
print('nonblank dur med',st.median([r['t1']-r['t0'] for r in nb]),'tokens med',st.median(f(nb,'tokens')))
print('blank tokens>0:',sum(1 for r in b if r['tokens'] and float(r['tokens'])>0),'of',len(b))
