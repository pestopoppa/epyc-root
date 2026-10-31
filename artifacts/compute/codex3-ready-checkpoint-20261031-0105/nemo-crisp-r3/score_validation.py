#!/usr/bin/env python3
"""Derive selection-only WER from pinned native files and canonical P-STT-1."""
import hashlib,json,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
snapshot=pathlib.Path('/mnt/raid0/llm/tmp/codex3-cs8-stt3-transcribe-20261030')
catalog=snapshot/'SCORER-SHA256SUMS'
if hashlib.sha256(catalog.read_bytes()).hexdigest()!='74f4c45bacf0ea2da83d9869e5b0f0e33fa8a5a2d3043081c0da7d2f4c18b8a2':raise ValueError('scorer catalog drift')
for line in catalog.read_text().splitlines():
 digest,name=line.split('  ',1)
 if hashlib.sha256((snapshot/name).read_bytes()).hexdigest()!=digest:raise ValueError('scorer member drift '+name)
sys.path.insert(0,str(snapshot/'scorer-snapshot'))
from scripts.speech.stt_bakeoff.scorer import score_utterance,bootstrap_pooled_wer
from scripts.speech.stt_bakeoff import stt_norm
from scripts.kernel_rnd.autokernel.adapters import whisper_stt
from chunk_materialize import verify_record
from matched_tokens import parse as parse_tokens
from nemo_crisp_job import sha
MANIFEST=pathlib.Path('/mnt/raid0/llm/data/stt-cs8-public-20261030/fleurs-validation-pcm/manifest.json')
def native_unk_observed(value):
 if value is None:return 0
 if isinstance(value,list):return sum(native_unk_observed(x) for x in value)
 if isinstance(value,dict):return value['unk_count']
 raise ValueError('invalid token evidence')
source=sha(D/'SOURCE-SHA256SUMS');pins=json.loads((D/'INPUT-PINS.json').read_text());plan=pins['plan_sha256'];inp=pins['validation_sha256'];out=D/'validation-results'
if sha(MANIFEST)!=inp:raise ValueError('input drift')
records=json.loads(MANIFEST.read_text())['records'];report={'schema':'cs8-stt5-validation-score/v1','selection_only':True,'seed':146064415,'resamples':4000,'repetition_check':'COULD_NOT_CHECK: no validation-derived envelope supplied','weight_format_note':'same pinned transcribe Q8 GGUF; pointwise requantization disabled','unavailable_contexts':{'r1':'not present in pinned checkpoint training menu'},'cells':{}}
for model in ('r0','r3','r6','r13'):
 for mode in ('auto','forced'):
  allrows=[]
  for r in records:
   key=hashlib.sha256(r['clip_id'].encode()).hexdigest();p=out/'chunks'/(key+'.chunks.json')
   if not p.is_file():raise ValueError('unknown or missing chunk map '+r['clip_id'])
   chunk=json.loads(p.read_text());verify_record(chunk)
   if chunk['status']!='ok' or chunk['id']!=r['clip_id'] or chunk['original_pcm_sha256']!=r['pcm_sha256'] or chunk['original_wav_sha256']!=r['wav_sha256']:raise ValueError('invalid chunk map')
   texts=[];native_texts=[];token_evidence=[];failed=False
   for part in chunk['chunks']:
    k=hashlib.sha256((model+'|'+mode+'|'+r['clip_id']+'|'+str(part['index'])).encode()).hexdigest();ep=out/(k+'.exposure.json');rp=out/(k+'.result.json')
    if not ep.exists() or not rp.exists():raise ValueError('unknown exposure '+r['clip_id'])
    e=json.loads(ep.read_text());v=json.loads(rp.read_text());binding={'clip_id':r['clip_id'],'chunk_index':part['index'],'chunk_pcm_sha256':part['pcm_sha256'],'chunk_wav_sha256':part['wav_sha256'],'input_sha256':inp,'plan_sha256':plan,'source_sha256':source,'model_sha256':pins['models'][model],'binary_sha256':pins['runner_binary_sha256'][model],'library_set_sha256':pins['runner_library_set_sha256'][model],'mode':mode}
    if e['binding']!=binding or v['binding']!=binding or v.get('reaped') is not True or not isinstance(v.get('rc'),int):raise ValueError('native binding')
    for suffix in ('stdout','stderr','txt'):
     f=out/(k+'.'+suffix);h=v[suffix+'_sha256']
     if (h is None and f.exists()) or (h is not None and (not f.exists() or sha(f)!=h)):raise ValueError('native output drift')
    f=out/(k+'.txt');text=f.read_text() if f.exists() else ''
    native_texts.append(text)
    if v['rc']!=0:
     failed=True;token_evidence.append(None);texts.append('')
    else:
     try: evidence=parse_tokens((out/(k+'.stdout')).read_text(),text)
     except ValueError:
      if text.strip(): raise
      evidence=None
     token_evidence.append(evidence)
     hypothesis=evidence['hypothesis_with_unk'] if evidence is not None else ''
     texts.append(hypothesis)
     if not hypothesis.strip(): failed=True
   if failed:texts=['']*len(texts)
   allrows.append({'native_hypothesis_chunks':native_texts,'token_evidence':token_evidence,'unk_count_unknown':any(x is None for x in token_evidence),'utterance_id':r['clip_id'],'pcm_sha256':r['pcm_sha256'],'reference_raw':r['reference_raw'],'hypothesis_chunks':texts,'chunk_indices':list(range(len(texts))),'duration_s':r['frames']/16000,'language':r['language'].split('_')[0],'set_id':'fleurs-validation','reference_track':'standard','content_stratum':'clean_read','decode_status':'error' if failed else 'ok'})
  (out/f'raw-{model}-{mode}.json').write_text(json.dumps({'schema_version':'stt_bakeoff.raw_manifest/v1','corpus_id':'fleurs-validation','stratum':'selection','language_mode':mode,'segmentation_mode':'vad_30s','arm':{'arm_id':model,'arm_kind':'streaming_cache_aware','model_family':'nemotron-3.5','chunk_label':model,'algorithmic_delay_ms':80*(int(model[1:])+1),'att_context_right':int(model[1:]),'runner_id':'crispasr-private-traced','runner_commit':'2aa8d7669fcaa18d98d61a4bc8a077464e6b9919','ggml_version':'0.26.0','quant':'Q8_0','backend':'cpu','weights_sha256':pins['models'][model],'unk_ban':False,'decode_options':'greedy; complete emitted-ID witness'},'rows':allrows},ensure_ascii=False,sort_keys=True)+'\n')
  for norm in ('stt_norm/v1','stt_norm/v2'):
   contract=stt_norm.contract_check(norm)
   if norm=='stt_norm/v1' and contract.outcome!='PASS':raise ValueError('normalizer contract failure')
   texts=[(r['reference_raw'],r['language']) for r in allrows]+[(c,r['language']) for r in allrows for c in r['hypothesis_chunks']]
   props=stt_norm.check_properties(texts,norm)
   if props.check.outcome!='PASS':raise ValueError('normalizer properties failure')
   scored=[score_utterance(r,normaliser_id=norm,segmentation_mode='vad_30s',repetition_envelope=None) for r in allrows]
   for score,row in zip(scored,allrows):
    score['unk_count_unknown']=row.get('unk_count_unknown',False);score['native_unk_observed']=native_unk_observed(row.get('token_evidence'))
   (out/f'per-utterance-{model}-{mode}-{norm.rsplit("/",1)[-1]}.json').write_text(json.dumps(scored,sort_keys=True,ensure_ascii=False)+'\n')
   for lang in ('en','it','de','fr'):
    cases=[r for r in scored if r['language']==lang]
    if any(x['class']=='VOID' for x in cases):raise ValueError('canonical scorer VOID')
    taxonomy={c:sum(x['class']==c for x in cases) for c in whisper_stt.FAILURE_CLASSES}
    check=whisper_stt.check_failure_taxonomy(taxonomy,n_utterances=len(cases))
    if check.outcome!='PASS':raise ValueError('failure taxonomy invalid')
    errs=[x['errors'] for x in cases];refs=[x['reference_tokens'] for x in cases]
    report['cells'][f'{model}|{mode}|{norm}|{lang}']={'n':len(cases),'wer_percent':whisper_stt.pooled_corpus_wer(errs,refs),'ci95':bootstrap_pooled_wer(errs,refs,resamples=4000,seed=146064415),'unk_count':sum(x['native_unk_observed'] for x in cases),'unk_count_complete':not any(r['unk_count_unknown'] for r in allrows if r['language']==lang),'normalizer_route':'COULD_NOT_CHECK' if any(x['class'] in ('unknown_marker','numeral_uncovered') for x in cases) else 'CHECKED','classes':{c:sum(x['class']==c for x in cases) for c in sorted({x['class'] for x in cases})}}
(out/'validation-score.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print('validation-score complete',len(report['cells']))
