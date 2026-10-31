#!/usr/bin/env python3
"""SPQ-03 simple normalized corpus WER/CER; primary and repeated seed remain separate."""
import json, pathlib, random, sys
D=pathlib.Path(sys.argv[1]); manifest=json.loads(pathlib.Path(sys.argv[2]).read_text()); cells=manifest['cells']; records={}
for c in cells:
 p=D/'cells'/(c['id']+'.json')
 if not p.is_file(): raise SystemExit('unobserved or unknown cell '+c['id'])
 records[c['id']]=json.loads(p.read_text())
def stats(rows, mode):
 dat=[r['modes'][mode] for r in rows]; n=sum(x['ref_words'] for x in dat); err=sum(x['word_errors'] for x in dat); chars=sum(x['ref_chars'] for x in dat)
 if not n or not chars: raise ValueError('empty denominator')
 rng=random.Random(8675309); samples=[]
 for _ in range(10000):
  boot=[dat[rng.randrange(len(dat))] for _ in dat]; den=sum(x['ref_words'] for x in boot)
  samples.append(sum(x['word_errors'] for x in boot)/den if den else 0)
 samples.sort()
 return {'n':len(dat),'words':n,'errors':err,'wer':err/n,'cer':sum(x['char_errors'] for x in dat)/chars,'bootstrap_95':[samples[249],samples[9749]]}
out={}
for arm in ('tts_rt','stt'):
 for mode in ('forced','auto'):
  for lang in ('en','it','de','fr'):
   selected=[records[c['id']] for c in cells if c['arm']==arm and c['lang']==lang and (arm=='stt' or c.get('primary'))]
   if len(selected)!=60: raise ValueError('wrong primary denominator')
   out[f'{arm}|{mode}|{lang}']=stats(selected,mode)
  if arm=='tts_rt':
   for lang in ('en','it','de','fr'):
    selected=[records[c['id']] for c in cells if c['arm']==arm and c['lang']==lang and c.get('primary') is False]
    if len(selected)!=10: raise ValueError('wrong repeat denominator')
    out[f'repeated_seed|{mode}|{lang}']=stats(selected,mode)
  if arm=='tts_rt':
   en=out[f'{arm}|{mode}|en']
   for lang in ('it','de','fr'):
    s=out[f'{arm}|{mode}|{lang}']; s['automated_m17_trigger']=s['wer']>2*en['wer'] and (s['bootstrap_95'][0]>en['bootstrap_95'][1] or en['bootstrap_95'][0]>s['bootstrap_95'][1]); s['english_same_run_wer']=en['wer']
json.dump({'summary':out,'normalizer':'SPQ-03 NFKC lower punctuation separator; not P-STT-1','native_listener':'NOT_ASSESSED','ci':'10000 utterance bootstrap, fixed seed 8675309, percentile 95%', 'note':'repeated seed not pooled with primary'},open(D/'summary.json','w'),indent=2)
