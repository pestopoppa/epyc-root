#!/usr/bin/env python3
"""Preselection held-out scorer draft. Never opens test gold without frozen selection and complete native cohort."""
import collections,hashlib,json,pathlib,random,re,sys,unicodedata
D=pathlib.Path(__file__).resolve().parent;L=D.parent/'lex2';sys.path[:0]=[str(L),str(L/'research-scorer-snapshot')];import grid_job as g
from scripts.speech.stt_bakeoff import lexicon,align,stt_norm
def normal(s):return ' '.join(re.sub(r"[^\w\s']",' ',unicodedata.normalize('NFKC',s)).split())
def pct(xs,q):
 xs=sorted(xs);z=(len(xs)-1)*q;i=int(z);j=min(i+1,len(xs)-1);return xs[i]+(xs[j]-xs[i])*(z-i)
def main():
 sel=L/'DEV-SELECTION.json';plan=L/'HELDOUT-PLAN.json';terminal=D/'run/TERMINAL.json'
 if not sel.exists() or not plan.exists():raise SystemExit('HELD: actual dev selection absent')
 instance_path=D/'INSTANCE-PLAN.json'
 if not instance_path.is_file():raise SystemExit('HELD: pre-test instance absent')
 selected=json.loads(sel.read_text());held=json.loads(plan.read_text());instance=json.loads(instance_path.read_text())
 if instance.get('selection_sha256')!=g.digest(sel) or instance.get('base_heldout_plan_sha256')!=g.digest(plan) or instance.get('source_catalog_sha256')!=g.digest(D/'SOURCE-SHA256SUMS') or instance.get('native_attempts_planned')!=25095:raise RuntimeError('instance plan drift')
 if held['selection_sha256']!=g.digest(sel) or held['selection']!=selected['selection'] or selected.get('test_opened') is not False or selected.get('nonlist_noise_floor_state')!='known_lexical' or selected['raw_terminal_sha256']!=g.digest(L/'run/TERMINAL.json'):raise RuntimeError('selection or dev evidence drift')
 if not terminal.exists():raise SystemExit('HELD: original held-out native capture incomplete')
 t=json.loads(terminal.read_text())
 if t['state'] not in ('complete_raw','incomplete_raw') or t['counts']['unknown']!=0 or t['counts']['failure']+t['counts']['ok']!=25095 or t['selection_sha256']!=g.digest(sel):raise SystemExit('HELD: original denominator has exposure unknown or missing native results')
 test_manifest=pathlib.Path('/mnt/raid0/llm/data/contextual-earnings22-59d7f947/test-native/MANIFEST-V2.json')
 if g.digest(test_manifest)!='bf5a32fb1a74d6cac4950f8973abc2583c08ad4e71a1169399aa8eb443188fd7':raise RuntimeError('test manifest drift')
 data=json.loads(test_manifest.read_text());ctx=json.loads((D/'TEST-CONVERSATION-CONTEXTS.json').read_text());fp=json.loads((D/'FLEURS-CONTEXT-POLICY.json').read_text());alpha=selected['selection']['alpha'];scope=selected['selection']['scope'];domain=fp['global_context'];calls=ctx['calls'];rows={}
 for r in data['records']:
  if r['eligibility']=='heldout':rows[('contextual',r['file_id'])]={'wav':r['wav_path'],'wav_sha256':r['wav_sha256'],'annotation_path':r['annotations_path'],'annotation_sha256':r['annotations_sha256'],'duration':r['duration'],'call_id':r['call_id'],'local':calls[r['call_id']],'aa_overlap_status':r['aa_overlap_status']}
 for r in fp['rows']:rows[('fleurs',r['clip_id'])]={'wav':r['wav_path'],'wav_sha256':r['wav_sha256'],'duration':r['frames']/16000,'local':calls[r['assigned_call_id']],'language':r['language']}
 cells=[('nemo','none',0),('nemo','global',alpha),('nemo','local',alpha),('whisper','none',None),('whisper','global',None),('whisper','local',None)];auto_cells=[('whisper','none-auto',None),('whisper','global-auto',None),('whisper','local-auto',None)];expected={(c,i,e,s,a) for c,i in rows for e,s,a in (cells+auto_cells if c=='contextual' else cells)};seen={}
 for p in (D/'run').glob('*.result.json'):
  v=json.loads(p.read_text());b=v['binding'];k=(b['corpus'],b['clip_id'],b['engine'],b['scope'],b['alpha'])
  if k not in expected or k in seen:raise RuntimeError('duplicate or unexpected native attempt')
  row=rows[(k[0],k[1])];basekind=k[3].removesuffix('-auto');context=[] if basekind=='none' else domain if basekind=='global' else row['local'];context=sorted(set(x.strip() for x in context if x.strip()));chs=hashlib.sha256(json.dumps(context,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();stem=str(p).removesuffix('.result.json');ex=pathlib.Path(stem+'.exposure.json');so=pathlib.Path(stem+'.stdout');se=pathlib.Path(stem+'.stderr');samples=pathlib.Path(stem+'.samples.jsonl');e=json.loads(ex.read_text())
  cmd=g.make_recipe(k[2],k[4],row['wav'],context,str(min(8,len(b['affinity']))))
  if k[2]=='whisper' and (k[0]=='fleurs' or k[3].endswith('-auto')):cmd[cmd.index('-l')+1]='auto'
  model='a5c435f294eea8f88ce68dd27b8c3bfea7f777cb2fbba04fcd30eaa555f429ae' if k[2]=='nemo' else '1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69';runtime=g.digest(g.N if k[2]=='nemo' else g.WH);spm='ce3895e40806f02a26c3a225161b96ef682d6c0054bae32a245dec4258d7d291' if k[2]=='nemo' else None
  immutable={'instance_plan_sha256':g.digest(instance_path),'source_catalog_sha256':g.digest(D/'SOURCE-SHA256SUMS'),'recipe_sha256':g.recipe_sha(cmd),'model_sha256':model,'runtime_sha256':runtime,'spm_sha256':spm,'selection_sha256':g.digest(sel),'heldout_plan_sha256':g.digest(plan),'contexts_sha256':g.digest(D/'TEST-CONVERSATION-CONTEXTS.json'),'fleurs_policy_sha256':g.digest(D/'FLEURS-CONTEXT-POLICY.json'),'contract_sha256':g.digest(D/'HELDOUT-CONTRACT.md'),'wav_sha256':row['wav_sha256'],'context_sha256':chs,'context_count':len(context)};g.validate_cached_binding(b,immutable)
  if e['binding']!=b or e['argv']!=cmd or any(g.digest(path)!=v[field] for path,field in [(so,'stdout_sha256'),(se,'stderr_sha256'),(samples,'samples_sha256')]) or v['status'] not in ('ok','failure') or not v['reaped']:raise RuntimeError('native result mismatch')
  native=g.classify_native(k[2],k[4],len(context),v['rc'],so.read_bytes(),se.read_text(errors='replace'))
  if any(v.get(q)!=val for q,val in native.items()):raise RuntimeError('native status/trie mismatch')
  ss=[json.loads(line) for line in samples.read_text().splitlines()]
  raw=b.get('grant_text')
  if not raw or hashlib.sha256(raw.encode()).hexdigest()!=b.get('grant_sha256') or not b.get('grant_id'):raise RuntimeError('original exposure grant binding missing')
  if v['status']=='ok' and not any(x.get('sampled_while_child_live') and x.get('grant_id')==b.get('grant_id') and x.get('grant_sha256')==b.get('grant_sha256') and x.get('child_pid')==v.get('child_pid') and x.get('child_birth') is not None and x.get('child_birth')==v.get('child_birth') for x in ss):raise RuntimeError('original live grant sample absent')
  seen[k]=(so.read_text(errors='strict') if v['status']=='ok' else '',context,se.read_text(errors='replace'),v['status'])
 if set(seen)!=expected:raise RuntimeError('missing attempts')
 # Only now, after actual dev selection and all expected original native attempts, read test references.
 values={};unknown_v1=[]
 for (corpus,ident),row in rows.items():
  if corpus!='contextual':continue
  ann=pathlib.Path(row['annotation_path'])
  if g.digest(ann)!=row['annotation_sha256']:raise RuntimeError('annotation changed')
  a=json.loads(ann.read_text());ref=a['reference'];terms=[normal(x) for x in a['keywords'] if normal(x)]
  for e,s,al in cells:
   hyp,_,stderr,native_status=seen[(corpus,ident,e,s,al)];fold=lexicon.keyword_counts(normal(ref),normal(hyp),terms,False);sensitive=lexicon.keyword_counts(normal(ref),normal(hyp),terms,True);ts=lexicon._term_set(terms,str.casefold)
   def mask(text):
    toks=normal(text).split();drop={i for x,y in lexicon.term_spans(toks,ts,str.casefold) for i in range(x,y)};return [v.casefold() for i,v in enumerate(toks) if i not in drop]
   rr,hh=mask(ref),mask(hyp);rt=normal(ref).casefold().split();ht=normal(hyp).casefold().split();srt=normal(ref).split();sht=normal(hyp).split();sts=lexicon._term_set(terms,lambda x:x)
   def sensitive_mask(toks):
    drop={i for x,y in lexicon.term_spans(toks,sts,lambda x:x) for i in range(x,y)};return [v for i,v in enumerate(toks) if i not in drop]
   srr,shh=sensitive_mask(srt),sensitive_mask(sht);pairs=align.align(rt,ht).pairs;sensitive_pairs=align.align(srt,sht).pairs;rs=stt_norm.normalise_v1(ref,'en',side='reference');hs=stt_norm.normalise_v1(hyp,'en',side='hypothesis');rec={'call_id':row['call_id'],'native_status':native_status,'fold':fold,'sensitive':sensitive,'masked_errors':align.edit_distance(rr,hh),'masked_ref':len(rr),'lexical_errors':align.edit_distance(rt,ht),'lexical_ref':len(rt),'sensitive_masked_errors':align.edit_distance(srr,shh),'sensitive_masked_ref':len(srr),'sensitive_lexical_errors':align.edit_distance(srt,sht),'sensitive_lexical_ref':len(srt),'folded_alignment':[{'op':q.op,'ref_idx':q.ref_idx,'hyp_idx':q.hyp_idx} for q in pairs],'sensitive_alignment':[{'op':q.op,'ref_idx':q.ref_idx,'hyp_idx':q.hyp_idx} for q in sensitive_pairs],'hypothesis_sha256':hashlib.sha256(hyp.encode()).hexdigest(),'keyword_v1_statuses':[stt_norm.normalise_v1(w,'en',side='reference').status for w in a['keywords']],'reference_v1_status':rs.status,'hypothesis_v1_status':hs.status,'raw_token_unk':None,'aa_overlap_status':row['aa_overlap_status']};values[(ident,e,s,al)]=rec
   if rs.status!='ok' or hs.status!='ok':unknown_v1.append({'clip_id':ident,'cell':[e,s,al],'ref_status':rs.status,'hyp_status':hs.status})
 callids=sorted({r['call_id'] for (c,i),r in rows.items() if c=='contextual'});ids={c:[i for (co,i),r in rows.items() if co=='contextual' and r['call_id']==c] for c in callids}
 def aggregate(cell,case,draw):
  v=[values[(i,*cell)] for c in draw for i in ids[c]];n={k:sum(r[case][k] for r in v) for k in ('tp','fn','fp')};prefix='' if case=='fold' else 'sensitive_';den=sum(r[prefix+'masked_ref'] for r in v);rd=sum(r[prefix+'lexical_ref'] for r in v);return {'keyword':{**n,**lexicon._prf(**n)},'nonlist_wer':sum(r[prefix+'masked_errors'] for r in v)/den if den else None,'lexical_wer':sum(r[prefix+'lexical_errors'] for r in v)/rd if rd else None}
 baseline=('nemo','none',0);chosen=('nemo',scope,alpha);rnd=random.Random(42);draws=[[rnd.choice(callids) for _ in callids] for _ in range(2000)];deltas=[]
 for draw in draws:
  x=aggregate(chosen,'fold',draw)['keyword']['term_f'];y=aggregate(baseline,'fold',draw)['keyword']['term_f']
  if x is not None and y is not None:deltas.append(x-y)
 ci=[pct(deltas,.025),pct(deltas,.975)] if len(deltas)==2000 else None;summary={str(c):{'fold':aggregate(c,'fold',callids),'sensitive':aggregate(c,'sensitive',callids)} for c in cells};insertions_by_cell={};fleurs_per_item=[]
 for cell in cells:
  reference=baseline if cell[0]=='nemo' else ('whisper','none',None)
  for case in ('fold','sensitive'):
   x=summary[str(cell)][case]['lexical_wer'];y=summary[str(reference)][case]['lexical_wer'];summary[str(cell)][case]['lexical_wer_delta_vs_same_engine_baseline']=None if x is None or y is None else x-y
 for cell in cells:
  per_language={}
  for language in sorted(fp['counts']):
   n=0;seconds=0;unknown=0
   for (corpus,ident),row in rows.items():
    if corpus!='fleurs' or row['language']!=language:continue
    hyp,terms,_,status=seen[(corpus,ident,*cell)];seconds+=row['duration']
    if status!='ok':
     unknown+=1;fleurs_per_item.append({'clip_id':ident,'language':language,'cell':cell,'native_status':status,'duration_s':row['duration'],'term_spans':None});continue
    # Evaluate both no-context baselines against the selected study list; an empty
    # no-context request is not allowed to make insertion accounting vacuous.
    if cell[1]=='none':terms=seen[(corpus,ident,'nemo',scope,alpha)][1]
    ts=lexicon._term_set([normal(x) for x in terms],str.casefold);spans=len(lexicon.term_spans(normal(hyp).split(),ts,str.casefold));n+=spans;fleurs_per_item.append({'clip_id':ident,'language':language,'cell':cell,'native_status':status,'duration_s':row['duration'],'term_spans':spans,'hypothesis_sha256':hashlib.sha256(hyp.encode()).hexdigest()})
   per_language[language]={'term_spans_observed':n,'duration_s_all':seconds,'native_failure_unknown_n':unknown,'per_hour':n/(seconds/3600) if seconds and not unknown else None}
  seconds=sum(v['duration_s_all'] for v in per_language.values());rate=sum(v['term_spans_observed'] for v in per_language.values())/(seconds/3600) if seconds and not any(v['native_failure_unknown_n'] for v in per_language.values()) else None
  insertions_by_cell[str(cell)]={'languages':per_language,'total_per_hour':rate}
 insertion_rate=insertions_by_cell[str(chosen)]['total_per_hour'];selected_wer=summary[str(chosen)]['fold']['nonlist_wer'];baseline_wer=summary[str(baseline)]['fold']['nonlist_wer'];delta=None if selected_wer is None or baseline_wer is None else selected_wer-baseline_wer
 # Apply exactly the source's three numerical guards; separate anchor uncertainty and missing future CS-4 coverage from this predicate.
 guard=None if ci is None or insertion_rate is None or delta is None else bool(ci[0]>0 and insertion_rate<=1 and delta<=selected['nonlist_noise_floor'])
 comparator=[]
 for (corpus,ident),row in rows.items():
  for e,s,a in (cells+auto_cells if corpus=='contextual' else cells):
   if e!='whisper':continue
   hyp,_,stderr,status=seen[(corpus,ident,e,s,a)];tokens=normal(hyp).casefold().split();maxrun=run=0;previous=None
   for token in tokens:
    run=run+1 if token==previous else 1;maxrun=max(maxrun,run);previous=token
   m=re.search(r'auto.detected language\s*:\s*([a-z-]+)',stderr,re.I)
   comparator.append({'corpus':corpus,'clip_id':ident,'scope':s,'native_status':status,'max_identical_token_run':maxrun if status=='ok' else None,'repeated_token_loop_10plus':(maxrun>=10) if status=='ok' else None,'detected_language':m.group(1) if m else None,'language_flip':'unknown' if not m else m.group(1).lower()!=('en' if corpus=='contextual' else row['language'].split('_')[0])})
 comparator_counts={}
 for r in comparator:
  key=r['corpus']+'|'+r['scope'];bucket=comparator_counts.setdefault(key,{'total':0,'repeated_loop_10plus':0,'repeated_loop_unknown':0,'language_flips':0,'language_flip_unknown':0});bucket['total']+=1
  if r['repeated_token_loop_10plus'] is None:bucket['repeated_loop_unknown']+=1
  elif r['repeated_token_loop_10plus']:bucket['repeated_loop_10plus']+=1
  if r['language_flip']=='unknown':bucket['language_flip_unknown']+=1
  elif r['language_flip']:bucket['language_flips']+=1
 result={'schema':'cs8.lex2.heldout-score-draft.v1','selection_sha256':g.digest(sel),'heldout_terminal_sha256':g.digest(terminal),'scorer_predeclared_sha256':g.digest(L/'SCORER-PREDECLARED.json'),'metric_label':'LEX1 lexical reference agreement, not P-STT-1 v1 WER or speech release','candidate_n':755,'fleurs_n':3050,'native_failure_count':t['counts']['failure'],'aa_overlap_unknown_n':sum(r.get('aa_overlap_status')=='unknown' for r in rows.values()),'cs4_recorded':'unknown','summary':summary,'paired_keyword_f_delta_ci95':ci,'bootstrap_undefined_n':2000-len(deltas),'nonlist_wer_delta':delta,'frozen_dev_noise_floor':selected['nonlist_noise_floor'],'fleurs_per_item':fleurs_per_item,'fleurs_insertions_by_condition':insertions_by_cell,'fleurs_selected_insertions_per_hour':insertion_rate,'v1_status_unknowns':unknown_v1,'raw_token_unk':None,'m16_numerical_predicate':guard,'m16_predicate_definition':'paired keyword F 95% lower bound > 0, selected FLEURS term insertions <= 1/hour, and non-list lexical WER delta <= frozen dev floor; None if a required numeric input is undefined','anchor_membership':'19 AA flagged test clips remain UNKNOWN; original AA and contextual denominators unchanged','per_item':[{'clip_id':i,'engine':e,'scope':s,'alpha':a,**v} for (i,e,s,a),v in sorted(values.items(),key=lambda x:str(x[0]))],'whisper_loop_and_language_observations':comparator,'whisper_loop_and_language_counts':comparator_counts,'test_redraw':False}
 out=D/'HELDOUT-SCORE-DRAFT.json'
 with out.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 print('wrote draft',g.digest(out))
if __name__=='__main__':main()
