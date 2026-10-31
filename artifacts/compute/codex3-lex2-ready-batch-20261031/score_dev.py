#!/usr/bin/env python3
"""Frozen dev-only scorer; refuses missing/unknown, never opens or scores the test set."""
import collections,hashlib,json,math,os,pathlib,random,re,sys,unicodedata
D=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(D/'research-scorer-snapshot'));from scripts.speech.stt_bakeoff import lexicon,stt_norm,align
import grid_job as grid
DATA=pathlib.Path('/mnt/raid0/llm/data/contextual-earnings22-59d7f947/dev-native/MANIFEST-V2.json')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def case_raw(s):return ' '.join(re.sub(r"[^\w\s']",' ',unicodedata.normalize('NFKC',s)).split())
def fscore(tp,fn,fp):
 return lexicon._prf(tp,fn,fp)['term_f']
def pct(xs,q):
 if not xs:return None
 xs=sorted(xs);z=(len(xs)-1)*q;i=int(z);j=min(i+1,len(xs)-1);return xs[i]+(xs[j]-xs[i])*(z-i)
def main():
 spec=json.loads((D/'SCORER-PREDECLARED.json').read_text())
 for rel,digest in spec['source_sha256'].items():
  if sha(D/rel)!=digest:raise RuntimeError('scorer source drift: '+rel)
 if sha(DATA)!=spec['dev_manifest_sha256']:raise RuntimeError('dev manifest drift')
 term=json.loads((D/'run/TERMINAL.json').read_text())
 if term['state'] not in ('complete_raw','incomplete_raw') or term['counts']['unknown'] != 0 or term['mode']!='full' or term['original_clips']!=100 or term['cells']!=15:raise RuntimeError('raw cohort incomplete or unknown')
 manifest=json.loads(DATA.read_text());rows={x['file_id']:x for x in manifest['records']};contexts=json.loads((D/'CONVERSATION-CONTEXTS.json').read_text());domain=json.loads((D/'DOMAIN-LEXICON-PROPOSAL.json').read_text())['phrases']['en'];
 if contexts['dev_manifest_sha256']!=sha(DATA):raise RuntimeError('conversation context input drift')
 expected={(e,s,a,k) for k in rows for e,s,a in ([('nemo',s,a) for s in ('global','local') for a in (0,0.5,1,2,3,5)]+[('whisper',s,None) for s in ('none','global','local')])}; records={}
 for p in (D/'run').glob('*.result.json'):
  d=json.loads(p.read_text());b=d['binding'];key=(b['engine'],b['scope'],b['configured_alpha'],b['clip_id'])
  if key not in expected or key in records:raise RuntimeError('unexpected or duplicate attempt')
  exposure=p.with_name(p.name.replace('.result.json','.exposure.json'));x=json.loads(exposure.read_text());
  r=rows[b['clip_id']];context=contexts['calls'][r['call_id']] if b['scope']=='local' else domain if b['scope']=='global' else [];context=sorted(set(str(v).strip() for v in context if str(v).strip()));ch=hashlib.sha256(json.dumps(context,ensure_ascii=False,separators=(',',':')).encode()).hexdigest();cmd=grid.make_recipe(b['engine'],b['configured_alpha'],r['wav_path'],context,'8');expected_model='a5c435f294eea8f88ce68dd27b8c3bfea7f777cb2fbba04fcd30eaa555f429ae' if b['engine']=='nemo' else '1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69';expected_runtime=sha(grid.N if b['engine']=='nemo' else grid.WH);expected_spm='ce3895e40806f02a26c3a225161b96ef682d6c0054bae32a245dec4258d7d291' if b['engine']=='nemo' else None
  expected_binding={'schema':'cs8.lex2.native_attempt.v1','plan_sha256':spec['grid_plan_sha256'],'source_catalog_sha256':sha(D/'SOURCE-SHA256SUMS'),'corpus_manifest_sha256':spec['dev_manifest_sha256'],'clip_id':r['file_id'],'wav_sha256':r['wav_sha256'],'annotation_sha256':r['annotations_sha256'],'engine':b['engine'],'scope':b['scope'],'configured_alpha':b['configured_alpha'],'context_sha256':ch,'context_count':len(context),'recipe_sha256':grid.recipe_sha(cmd),'model_sha256':expected_model,'runtime_sha256':expected_runtime,'spm_sha256':expected_spm}
  grid.validate_cached_binding(b,expected_binding)
  if x['binding']!=b or x['argv']!=cmd or sha(r['wav_path'])!=r['wav_sha256']:raise RuntimeError('binding or recipe mismatch')
  out=p.with_name(p.name.replace('.result.json','.stdout'));err=p.with_name(p.name.replace('.result.json','.stderr'));sample=p.with_name(p.name.replace('.result.json','.samples.jsonl'))
  if sha(out)!=d['stdout_sha256'] or sha(err)!=d['stderr_sha256'] or sha(sample)!=d['samples_sha256'] or not d['reaped']:raise RuntimeError('native evidence drift')
  if d['status'] not in ('ok','failure'):raise RuntimeError('unknown native status')
  classified=grid.classify_native(b['engine'],b['configured_alpha'],b['context_count'],d['rc'],out.read_bytes(),err.read_text(errors='replace'))
  if any(d.get(k)!=v for k,v in classified.items()):raise RuntimeError('native status or trace mismatch')
  samples=[json.loads(line) for line in sample.read_text().splitlines()]
  if not any(x.get('sampled_while_child_live') and x.get('grant_id')==b.get('grant_id') and x.get('grant_sha256') for x in samples):raise RuntimeError('missing in-window grant sample')
  if d['status']=='ok' and b['engine']=='nemo' and b['configured_alpha'] and b['context_count']:
   log=err.read_text(errors='strict'); required=f"effective_alpha={b['configured_alpha']:.6f}"
   if 'RNNT word boosting active' not in log or required not in log:raise RuntimeError('missing native active-trie proof')
  records[key]=(d,out.read_text(errors='strict') if d['status']=='ok' else '')
 if set(records)!=expected:raise RuntimeError('missing/unknown exposed attempt')
 per={};unknown=[]
 for (engine,scope,alpha,ident),(native,hyp) in records.items():
  r=rows[ident];ann=pathlib.Path(r['annotations_path']);
  if sha(ann)!=r['annotations_sha256']:raise RuntimeError('reference drift')
  x=json.loads(ann.read_text());ref=x['reference'];words=x['keywords']; rn=stt_norm.normalise_v1(ref,'en',side='reference');hn=stt_norm.normalise_v1(hyp,'en',side='hypothesis')
  rawterms=[case_raw(w) for w in words if case_raw(w)]
  # One predeclared lexical normalization for all rows; this metric is separate
  # from P-STT-1 WER and never repairs a flagged v1 normalization.
  fold=lexicon.keyword_counts(case_raw(ref),case_raw(hyp),rawterms,False)
  sensitive=lexicon.keyword_counts(case_raw(ref),case_raw(hyp),rawterms,True)
  termnorm=[stt_norm.normalise_v1(w,'en',side='reference') for w in words]
  norm_bad=rn.status!='ok' or hn.status!='ok' or any(t.status!='ok' for t in termnorm)
  # LEX1 lexical reference agreement, same case-folded tokenization as keyword F.
  # P-STT-1 status is retained separately and is never replaced or inferred.
  terms=rawterms;ts=lexicon._term_set(terms,str.casefold)
  def mask(text):
   toks=case_raw(text).split();drop={i for a,b in lexicon.term_spans(toks,ts,str.casefold) for i in range(a,b)};return [t.casefold() for i,t in enumerate(toks) if i not in drop]
  a,b=mask(ref),mask(hyp);rt=case_raw(ref).casefold().split();ht=case_raw(hyp).casefold().split()
  def alignment(ref_tokens,hyp_tokens):
   return [{'op':p.op,'ref_idx':p.ref_idx,'hyp_idx':p.hyp_idx} for p in align.align(ref_tokens,hyp_tokens).pairs]
  folded_alignment=alignment(rt,ht);sensitive_alignment=alignment(case_raw(ref).split(),case_raw(hyp).split())
  value={'call_id':r['call_id'],'fold':fold,'sensitive':sensitive,'masked_errors':align.edit_distance(a,b),'masked_ref':len(a),'lexical_errors':align.edit_distance(rt,ht),'lexical_ref':len(rt),'native_status':native['status'],'folded_alignment':folded_alignment,'sensitive_alignment':sensitive_alignment,'normalizer_ref_status':rn.status,'normalizer_hyp_status':hn.status,'keyword_normalizer_unknown':any(t.status!='ok' for t in termnorm),'keyword_v1_status_counts':dict(collections.Counter(t.status for t in termnorm)),'text_v1_reference_unk_count':rn.unk_count,'text_v1_hypothesis_unk_count':hn.unk_count,'raw_token_unk_count':None}
  if norm_bad:unknown.append({'cell':[engine,scope,alpha,ident],'reference_status':rn.status,'hypothesis_status':hn.status,'keyword_normalization_unknown':value['keyword_normalizer_unknown']})
  per[(engine,scope,alpha,ident)]=value
 cells=sorted({(e,s,a) for e,s,a,k in expected},key=lambda x:(x[0],x[1],-1 if x[2] is None else x[2]));calls=sorted({r['call_id'] for r in rows.values()}); ids_by_call={c:[k for k,r in rows.items() if r['call_id']==c] for c in calls}
 def aggregate(cell,which,callseq):
  allrows=[per[(*cell,i)] for c in callseq for i in ids_by_call[c]];counts={k:sum(r[which][k] for r in allrows) for k in ('tp','fn','fp')};den=sum(r['masked_ref'] for r in allrows);n_v1_unknown=sum(r['normalizer_ref_status']!='ok' or r['normalizer_hyp_status']!='ok' or r['keyword_normalizer_unknown'] for r in allrows);return {'f':fscore(**counts),'counts':counts,'non_list_wer':sum(r['masked_errors'] for r in allrows)/den if den else None,'v1_normalizer_unknown_n':n_v1_unknown}
 summary={};samples=random.Random(42);draws=[[samples.choice(calls) for _ in calls] for _ in range(2000)]
 for c in cells:
  key='|'.join(map(str,c));base=aggregate(c,'fold',calls);sensitive=aggregate(c,'sensitive',calls);fs=[aggregate(c,'fold',seq)['f'] for seq in draws];undefined=sum(v is None for v in fs);summary[key]={'folded':base,'sensitive':sensitive,'f_ci95':None if undefined else [pct(fs,.025),pct(fs,.975)],'bootstrap_undefined_n':undefined,'n':100}
 candidates=[(c,summary['|'.join(map(str,c))]['folded']['f']) for c in cells if c[0]=='nemo' and summary['|'.join(map(str,c))]['folded']['f'] is not None]
 if len(candidates)!=12:raise RuntimeError('undefined candidate F; no selection')
 best=sorted(candidates,key=lambda x:(-x[1],x[0][2],0 if x[0][1]=='global' else 1))[0];a=('nemo','global',0);b=('nemo','local',0);deltas=[]
 for seq in draws:
  x=aggregate(a,'fold',seq)['non_list_wer'];y=aggregate(b,'fold',seq)['non_list_wer']
  if x is not None and y is not None:deltas.append(x-y)
 ci=[pct(deltas,.025),pct(deltas,.975)] if len(deltas)==len(draws) else None;result={'schema':'cs8.lex2.dev-selection.v1','grid_plan_sha256':spec['grid_plan_sha256'],'scorer_predeclared_sha256':sha(D/'SCORER-PREDECLARED.json'),'dev_manifest_sha256':sha(DATA),'raw_terminal_sha256':sha(D/'run/TERMINAL.json'),'seed':42,'bootstrap_resamples':2000,'cells':summary,'selection':{'engine':best[0][0],'scope':best[0][1],'alpha':best[0][2],'folded_keyword_f':best[1]},'paired_zero_nonlist_delta_ci95':ci,'nonlist_noise_floor':max(map(abs,ci)) if ci else None,'nonlist_noise_floor_state':'known_lexical' if ci else 'unknown_lexical_denominator','v1_normalization_unknowns':unknown,'per_item':[{'engine':e,'scope':s,'alpha':a,'clip_id':i,**v} for (e,s,a,i),v in sorted(per.items(),key=lambda x:str(x[0]))],'raw_token_unk_count':None,'metric_label':'LEX1 lexical reference agreement; not P-STT-1 v1 WER or speech release claim','test_opened':False,'quality_verdict':None}
 out=D/'DEV-SELECTION.json'
 with out.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(D,os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 print('selection frozen',sha(out))
if __name__=='__main__':main()
