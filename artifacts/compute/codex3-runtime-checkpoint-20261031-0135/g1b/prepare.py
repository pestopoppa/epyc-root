#!/usr/bin/env python3
"""Freeze deterministic SPQ-03 test cohort and audio only; performs no inference."""
import hashlib, importlib.util, json, os, pathlib, tarfile
D=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('g1',D/'original-g1.py'); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
base='/mnt/raid0/llm/data/speech-testsets-20261020/fleurs/data'
extra='/mnt/raid0/llm/tmp/refactor-01a16fc3/inf79-speech-inference-ready/fleurs-evidence/data'
langs={'en':('en_us','English',base),'it':('it_it','Italian',base),'de':('de_de','German',extra),'fr':('fr_fr','French',extra)}
O=D/'inputs'; O.mkdir(exist_ok=True); cells=[]; sources={}
for lg,(fl,voice,root) in langs.items():
 p=pathlib.Path(root)/fl; g.FLEURS=root; g.LANGS={lg:(fl,voice,lg)}
 prompts=g.select_prompts(60)[lg]; assert len(prompts)==60
 tar=p/'audio/test.tar.gz'; sources[lg]={'tsv_sha256':sha(p/'test.tsv'),'tar_sha256':sha(tar),'split':'test'}
 wanted={x['audio'] for x in prompts}; raw=O/lg/'original'; raw.mkdir(parents=True,exist_ok=True); found={}; ref=None
 with tarfile.open(tar) as t:
  for m in t:
   b=os.path.basename(m.name)
   if not (m.isfile() and b.endswith('.wav')): continue
   if b in wanted or ref is None:
    if b in found: raise ValueError('duplicate archive basename '+b)
    dst=raw/b
    with t.extractfile(m) as src, open(dst,'wb') as dstf:
     while buf:=src.read(1<<20): dstf.write(buf)
    if b in wanted: found[b]=str(dst)
    elif ref is None: ref=str(dst)
 assert len(found)==60 and ref
 out=O/lg/'pcm'; out.mkdir(exist_ok=True)
 for i,r in enumerate(prompts):
  pcm=out/(r['id']+'.wav'); g.resample_16k(found[r['audio']],str(pcm)); common={'lang':lg,'tts_language':voice,'text':r['text'],'pcm':str(pcm),'pcm_sha256':sha(pcm),'voice_ref':ref,'voice_ref_sha256':sha(ref),'source_id':r['id']}
  cells.append(dict(common,id=r['id']+'-stt',arm='stt'))
  cells.append(dict(common,id=r['id']+'-tts-1234',arm='tts_rt',seed=1234,primary=True))
  if i<10: cells.append(dict(common,id=r['id']+'-tts-4321',arm='tts_rt',seed=4321,primary=False))
json.dump({'protocol':'SPQ-03 exact test split and normalizer; second seed 4321; no inference','cells':cells,'sources':sources},open(D/'cohort.json','w'),ensure_ascii=False,sort_keys=True,indent=1)
print('cells',len(cells),'tts',sum(c['arm']=='tts_rt' for c in cells),'stt',sum(c['arm']=='stt' for c in cells),'sha',sha(D/'cohort.json'))
