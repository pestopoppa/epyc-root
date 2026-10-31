#!/usr/bin/env python3
import hashlib,json,pathlib
import grid_job as g
D=pathlib.Path(__file__).resolve().parent
assert not g.enough_time(100,730,600) and g.enough_time(100,731,600)
base={'plan_sha256':'plan','source_catalog_sha256':'source','corpus_manifest_sha256':'corpus','clip_id':'clip','wav_sha256':'wav','annotation_sha256':'annotation','engine':'nemo','scope':'local','configured_alpha':.5,'context_sha256':'context','context_count':2,'recipe_sha256':'recipe','model_sha256':'model','runtime_sha256':'runtime','spm_sha256':'spm'}
g.validate_cached_binding({**base,'grant_id':'old-grant','affinity':[0,1]},base)
for k in base:
 t={**base,k:'tampered'}
 try:g.validate_cached_binding(t,base)
 except RuntimeError:pass
 else:raise AssertionError('unrefused drift: '+k)
c=json.loads((D/'CONVERSATION-CONTEXTS.json').read_text());m=json.loads(g.DATA.read_text());assert len(m['records'])==100 and len(c['calls'])==9
for r in m['records']:
 raw=pathlib.Path(r['annotations_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['annotations_sha256'];supplied=json.loads(raw)['dictionary'];assert set(x.strip() for x in supplied if x.strip())<=set(c['calls'][r['call_id']])
a=g.make_recipe('nemo',0,'/x',['alpha'],'8');b=g.make_recipe('nemo',.5,'/x',['alpha'],'8');c2=g.make_recipe('nemo',.5,'/x',['beta'],'8');assert '--speech-context' not in a and '--speech-context' in b and g.recipe_sha(b)!=g.recipe_sha(c2)
print('reserve boundary, all immutable-field drift refusals, original grant tolerance, 100 dictionary-subset and recipe context fixtures pass')
assert g.classify_native('nemo',.5,1,0,b'text','RNNT word boosting active phrases=1 effective_alpha=0.500000')['status']=='ok'
assert g.classify_native('nemo',.5,1,0,b'text','no trace')['status']=='failure'
assert g.classify_native('nemo',0,1,0,b'text','RNNT word boosting active phrases=1 effective_alpha=1.000000')['status']=='failure'
assert g.classify_native('nemo',0,1,0,b'text','')['status']=='ok'
print('native classification and zero-alpha anti-vacuity fixtures pass')
