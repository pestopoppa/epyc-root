#!/usr/bin/env python3
"""Frozen dev-only scorer; refuses missing/unknown, never opens or scores the test set."""
import collections,hashlib,json,math,os,pathlib,random,re,sys,unicodedata
D=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(D/'research-scorer-snapshot'));from scripts.speech.stt_bakeoff import lexicon,stt_norm,align
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
 manifest=json.loads(DATA.read_text());rows={x['file_id']:x for x in manifest['records']}; expected={(e,s,a,k) for k in rows for e,s,a in ([('nemo',s,a) for s in ('global','local') for a in (0,0.5,1,2,3,5)]+[('whisper',s,None) for s in ('none','global','local')])}; records={}
 for p in (D/'run').glob('*.result.json'):
  d=json.loads(p.read_text());b=d['binding'];key=(b['engine'],b['scope'],b['configured_alpha'],b['clip_id'])
  if key not in expected or key in records:raise RuntimeError('unexpected or duplicate attempt')
  exposure=p.with_name(p.name.replace('.result.json','.exposure.json'));x=json.loads(exposure.read_text());
  if x['binding']!=b or b['plan_sha256']!=spec['grid_plan_sha256'] or b['corpus_manifest_sha256']!=spec['dev_manifest_sha256']:raise RuntimeError('binding mismatch')
  out=p.with_name(p.name.replace('.result.json','.stdout'));err=p.with_name(p.name.replace('.result.json','.stderr'));sample=p.with_name(p.name.replace('.result.json','.samples.jsonl'))
  if sha(out)!=d['stdout_sha256'] or sha(err)!=d['stderr_sha256'] or sha(sample)!=d['samples_sha256'] or not d['reaped']:raise RuntimeError('native evidence drift')
  if d['status'] not in ('ok','failure'):raise RuntimeError('unknown native status')
  samples=[json.loads(line) for line in sample.read_text().splitlines()]
  if not any(x.get('sampled_while_child_live') for x in samples):raise RuntimeError('missing in-window sample')
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
  if rn.status!='ok' or hn.status!='ok':unknown.append({'cell':[engine,scope,alpha,ident],'reference_status':rn.status,'hypothesis_status':hn.status});continue
  termnorm=[stt_norm.normalise_v1(w,'en',side='reference') for w in words]
  if any(t.status!='ok' for t in termnorm):unknown.append({'cell':[engine,scope,alpha,ident],'keyword_normalization':'unknown'});continue
  terms=[t.text for t in termnorm if t.text];fold=lexicon.keyword_counts(rn.text,hn.text,terms,False);rawterms=[case_raw(w) for w in words];sensitive=lexicon.keyword_counts(case_raw(ref),case_raw(hyp),rawterms,True)
  ts=lexicon._term_set(terms,str.casefold)
  def mask(text):
   toks=text.split();drop={i for a,b in lexicon.term_spans(toks,ts,str.casefold) for i in range(a,b)};return [t.casefold() for i,t in enumerate(toks) if i not in drop]
  a,b=mask(rn.text),mask(hn.text); value={'call_id':r['call_id'],'fold':fold,'sensitive':sensitive,'masked_errors':align.edit_distance(a,b),'masked_ref':len(a),'wer_errors':align.edit_distance(rn.tokens,hn.tokens),'wer_ref':len(rn.tokens),'native_status':native['status']};per[(engine,scope,alpha,ident)]=value
 if unknown:
  (D/'DEV-SCORE-UNKNOWN.json').write_text(json.dumps({'schema':'cs8.lex2.dev-score-unknown.v1','unknown':unknown,'n':len(unknown),'selection':None},sort_keys=True)+'\n');raise RuntimeError('normalization unknowns; no selection')
 cells=sorted({(e,s,a) for e,s,a,k in expected},key=lambda x:(x[0],x[1],-1 if x[2] is None else x[2]));calls=sorted({r['call_id'] for r in rows.values()}); ids_by_call={c:[k for k,r in rows.items() if r['call_id']==c] for c in calls}
 def aggregate(cell,which,callseq):
  allrows=[per[(*cell,i)] for c in callseq for i in ids_by_call[c]];counts={k:sum(r[which][k] for r in allrows) for k in ('tp','fn','fp')};den=sum(r['masked_ref'] for r in allrows);return {'f':fscore(**counts),'counts':counts,'non_list_wer':sum(r['masked_errors'] for r in allrows)/den if den else None}
 summary={};samples=random.Random(42);draws=[[samples.choice(calls) for _ in calls] for _ in range(2000)]
 for c in cells:
  key='|'.join(map(str,c));base=aggregate(c,'fold',calls);sensitive=aggregate(c,'sensitive',calls);fs=[v for seq in draws if (v:=aggregate(c,'fold',seq)['f']) is not None];summary[key]={'folded':base,'sensitive':sensitive,'f_ci95':[pct(fs,.025),pct(fs,.975)],'n':100}
 candidates=[(c,summary['|'.join(map(str,c))]['folded']['f']) for c in cells if c[0]=='nemo' and summary['|'.join(map(str,c))]['folded']['f'] is not None]
 if len(candidates)!=12:raise RuntimeError('undefined candidate F; no selection')
 best=sorted(candidates,key=lambda x:(-x[1],x[0][2],0 if x[0][1]=='global' else 1))[0];a=('nemo','global',0);b=('nemo','local',0);deltas=[]
 for seq in draws:
  x=aggregate(a,'fold',seq)['non_list_wer'];y=aggregate(b,'fold',seq)['non_list_wer']
  if x is not None and y is not None:deltas.append(x-y)
 if len(deltas)!=len(draws):raise RuntimeError('undefined paired noise floor')
 ci=[pct(deltas,.025),pct(deltas,.975)];result={'schema':'cs8.lex2.dev-selection.v1','grid_plan_sha256':spec['grid_plan_sha256'],'scorer_predeclared_sha256':sha(D/'SCORER-PREDECLARED.json'),'dev_manifest_sha256':sha(DATA),'raw_terminal_sha256':sha(D/'run/TERMINAL.json'),'seed':42,'bootstrap_resamples':2000,'cells':summary,'selection':{'engine':best[0][0],'scope':best[0][1],'alpha':best[0][2],'folded_keyword_f':best[1]},'paired_zero_nonlist_delta_ci95':ci,'nonlist_noise_floor':max(map(abs,ci)),'test_opened':False,'quality_verdict':None}
 out=D/'DEV-SELECTION.json'
 with out.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 fd=os.open(D,os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 print('selection frozen',sha(out))
if __name__=='__main__':main()
