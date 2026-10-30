#!/usr/bin/env python3
import collections,json,math,random,statistics,sys
from pathlib import Path
D=Path(__file__).resolve().parent
cases={x['case_id']:x for x in map(json.loads,(D/'crops.jsonl').read_text().splitlines())}
def read(model):
 result={}
 for p in sorted((D/'results'/model).glob('worker-*.jsonl')):
  for x in map(json.loads,p.read_text().splitlines()):
   if x['event']=='outcome':
    assert x['case_id'] not in result and x['case_id'] in cases
    result[x['case_id']]=x
 return result
def wilson(k,n):
 z=1.959963984540054; q=k/n; den=1+z*z/n; c=(q+z*z/(2*n))/den; d=z*math.sqrt(q*(1-q)/n+z*z/(4*n*n))/den;return [c-d,c+d]
def pct(a,p):
 a=sorted(a);i=(len(a)-1)*p;l=int(i);u=min(l+1,len(a)-1);return a[l]+(a[u]-a[l])*(i-l)
def score(model):
 o=read(model);out={'model':model,'cases_expected':len(cases),'known':len(o),'unknown_or_unexposed':len(cases)-len(o),'groups':{}}
 for sec in (1,2,3):
  for lang in ('en','it','de','fr'):
   rows=[x for x in cases.values() if x['duration_requested_s']==sec and x['language']==lang]; known=[(x,o[x['case_id']]) for x in rows if x['case_id'] in o];ok=sum(y.get('status')=='ok' and y.get('prediction')==lang for x,y in known);conf=collections.Counter((y.get('prediction') if y.get('status')=='ok' else 'failure') for x,y in known); lat=[y['latency_ns']/1e9 for x,y in known if y.get('status')=='ok'];out['groups'][f'{lang}:{sec}']={'expected':len(rows),'known':len(known),'correct':ok,'accuracy_known':ok/len(known) if known else None,'ci95_wilson_known':wilson(ok,len(known)) if known else None,'confusion':dict(conf),'short_clips':sum(x['pad_frames']>0 for x in rows),'known_short_clips':sum(x['pad_frames']>0 for x,y in known),'short_correct':sum(x['pad_frames']>0 and y.get('status')=='ok' and y.get('prediction')==lang for x,y in known),'latency_s_median':statistics.median(lat) if lat else None,'latency_s_p95':pct(lat,.95) if lat else None}
 return out
out={'arms':[score(m) for m in sys.argv[1:]],'paired':{},'seed':146064415,'bootstrap_replicates':4000}
if len(sys.argv)>2:
 base=read(sys.argv[1])
 for model in sys.argv[2:]:
  candidate=read(model); intervals={}
  for sec in (1,2):
   groups={lang:[x for x in cases.values() if x['duration_requested_s']==sec and x['language']==lang] for lang in ('en','it','de','fr')}
   if any(x['case_id'] not in base or x['case_id'] not in candidate for g in groups.values() for x in g):intervals[str(sec)]={'unknown':True};continue
   diffs={lang:[int(candidate[x['case_id']].get('status')=='ok' and candidate[x['case_id']].get('prediction')==lang)-int(base[x['case_id']].get('status')=='ok' and base[x['case_id']].get('prediction')==lang) for x in g] for lang,g in groups.items()}
   rng=random.Random(146064415); n=sum(map(len,diffs.values()));s=[]
   for _ in range(4000):s.append(sum(sum(rng.choice(g) for _ in g) for g in diffs.values())/n)
   intervals[str(sec)]={'difference':sum(map(sum,diffs.values()))/n,'ci95':[pct(s,.025),pct(s,.975)]}
  enbase=score(sys.argv[1])['groups'];ennew=score(model)['groups']; intervals['english_recall_no_worse']=all(ennew[f'en:{sec}']['known']==ennew[f'en:{sec}']['expected'] and enbase[f'en:{sec}']['known']==enbase[f'en:{sec}']['expected'] and ennew[f'en:{sec}']['accuracy_known']>=enbase[f'en:{sec}']['accuracy_known'] for sec in (1,2));out['paired'][model]=intervals
print(json.dumps(out,indent=2))
