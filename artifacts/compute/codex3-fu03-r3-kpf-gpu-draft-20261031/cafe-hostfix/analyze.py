#!/usr/bin/env python3
"""Derive CAFE-1 rule from original one-grant native packet; no retrospective warrant."""
import hashlib,json,math,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 out=D/'run';t=json.loads((out/'TERMINAL.json').read_text());plan=json.loads((D/'PLAN.json').read_text());prompts={x['id']:x for x in json.loads((D/'PROMPTS.json').read_text())['prompts']}
 if t.get('mode')!='full' or t.get('state')!='complete_raw' or t.get('responses')!=75 or t.get('unknown')!=0:raise RuntimeError('incomplete or unknown native cohort')
 arms=['A0','P05','P075','P09','A0_repeat']; ps={'A0':0,'P05':.5,'P075':.75,'P09':.9,'A0_repeat':0};records={};grants=set()
 for b in range(5):
  for arm in arms:
   sid=f'{b}-{arm}';sp=out/(sid+'.server.json');dr=out/(sid+'.drain.json');log=out/(sid+'.server.log');s=json.loads(sp.read_text());z=json.loads(dr.read_text());
   if s.get('mode')!='full' or s.get('control_no_mtp') or s.get('block')!=b or s.get('arm')!=arm or s.get('p_min')!=ps[arm] or s.get('model_sha256')!=plan['target_sha256'] or s.get('plan_sha256')!=sha(D/'PLAN.json') or s.get('source_catalog_sha256')!=sha(D/'SOURCE-SHA256SUMS') or not s.get('grant_id') or not s.get('grant_text') or s.get('affinity')!=list(range(96)):raise RuntimeError('server envelope mismatch '+sid)
   proof=json.loads((out/(sid+'.residency.json')).read_text())
   if proof.get('pid')!=s['pid'] or proof.get('birth')!=s['birth'] or any('sha256' not in proof['evidence'].get(k,{}) or sha(out/proof['evidence'][k]['path'])!=proof['evidence'][k]['sha256'] for k in ('status','numa_maps','locks')):raise RuntimeError('placement proof unavailable '+sid)
   if not z.get('reaped') or z.get('pid')!=s['pid'] or z.get('birth')!=s['birth'] or z.get('server_log_sha256')!=sha(log):raise RuntimeError('server drain mismatch '+sid)
   if "adding speculative implementation 'draft-mtp'" not in log.read_text(errors='replace'):raise RuntimeError('MTP engagement unproven '+sid)
   grants.add((s['grant_id'],s['grant_text']))
   for kind in ('code','rag','prose'):
    ident=f'{kind}-{b}';base=out/(sid+'-'+ident);ep=pathlib.Path(str(base)+'.exposure.json');rp=pathlib.Path(str(base)+'.response.json');e=json.loads(ep.read_text());r=json.loads(rp.read_text());
    if e['prompt_id']!=ident or e['prompt_class']!=kind or e['prompt_sha256']!=prompts[ident]['prompt_sha256'] or e['server_record_sha256']!=sha(sp) or r['exposure_sha256']!=sha(ep) or r['http_status']!=200 or hashlib.sha256(r['raw'].encode()).hexdigest()!=r['raw_sha256']:raise RuntimeError('request identity mismatch '+str(base))
    body=r['parsed'];tim=body.get('timings',{});tokens=body.get('tokens');n=tim.get('predicted_n');ms=tim.get('predicted_ms');
    if not isinstance(tokens,list) or not tokens or not isinstance(n,(int,float)) or not isinstance(ms,(int,float)) or n<=0 or ms<=0 or not r.get('samples'):raise RuntimeError('native metrics or token/sampling proof missing '+str(base))
    records[(b,arm,kind)]={'n':n,'ms':ms,'tokens':tokens,'draft_n':tim.get('draft_n'),'formatted_prompt_sha256':e['formatted_prompt_sha256']}
 if len(grants)!=1:raise RuntimeError('multiple timing grants cannot supply a single-window decision')
 def rate(vals):return sum(x['n'] for x in vals)*1000/sum(x['ms'] for x in vals)
 def group(arm,kind=None):return [records[(b,arm,k)] for b in range(5) for k in ('code','rag','prose') if kind is None or kind==k]
 floors={}
 for kind in ('code','rag','prose','aggregate'):
  ks=('code','rag','prose') if kind=='aggregate' else (kind,);floors[kind]=max(abs(rate([records[(b,'A0_repeat',k)] for k in ks])/rate([records[(b,'A0',k)] for k in ks])-1)*100 for b in range(5))
 result={}
 for arm in ('P05','P075','P09'):
  identity=sum(records[(b,arm,k)]['tokens']==records[(b,'A0',k)]['tokens'] for b in range(5) for k in ('code','rag','prose'));format_identity=all(records[(b,arm,k)]['formatted_prompt_sha256']==records[(b,'A0',k)]['formatted_prompt_sha256'] for b in range(5) for k in ('code','rag','prose'))
  if not format_identity:raise RuntimeError('formatted paired prompt drift')
  gains={k:(rate(group(arm,None if k=='aggregate' else k))/rate(group('A0',None if k=='aggregate' else k))-1)*100 for k in ('code','rag','prose','aggregate')};keep=identity==15 and gains['aggregate']>=1+floors['aggregate'] and all(gains[k]>=-1-floors[k] for k in ('code','rag','prose'));result[arm]={'p_min':ps[arm],'matched_token_identity':identity,'matched_total':15,'gain_pct':gains,'decision':'KEEP' if keep else 'DECLINE','draft_count_presence':sum(records[(b,arm,k)]['draft_n'] is not None for b in range(5) for k in ('code','rag','prose'))}
 dest=out/'ANALYSIS.json';data={'schema':'cafe1.analysis.v1','plan_sha256':sha(D/'PLAN.json'),'prompt_manifest_sha256':sha(D/'PROMPTS.json'),'raw_terminal_sha256':sha(out/'TERMINAL.json'),'source_catalog_sha256':sha(D/'SOURCE-SHA256SUMS'),'grant_id':next(iter(grants))[0],'floors_pct':floors,'candidate_results':result,'scope':'single private full-target timing window; not a deployment'}
 with dest.open('x') as f:json.dump(data,f,sort_keys=True,indent=2);f.write('\n')
 print('analysis',sha(dest))
if __name__=='__main__':main()
