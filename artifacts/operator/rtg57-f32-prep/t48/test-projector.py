#!/usr/bin/python3
import hashlib,importlib.util,json,pathlib,tempfile
P=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('projector',P/'projector.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
hashb=lambda b:hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory(dir=P) as temp:
 root=pathlib.Path(temp); out=root/'packet'/'out';out.mkdir(parents=True); (root/'PROTOCOL.md').write_text('fixture rule')
 (out.parent/'SOURCES.sha256').write_text('fixture manifest'); (out.parent/'driver.py').write_text('fixture driver')
 source='c72ec82f5417bb2937310326120f149b665e8400'; recipe='a'*64
 (out/'identity.json').write_text(json.dumps({'source':source,'recipe_sha256':recipe,'threads':48,'cpus':'0-95'}))
 for n in ('linkage.txt','verdict.json'): (out/n).write_text('fixture')
 arms=['HYBRID','F32','F32','HYBRID','HYBRID','F32']; cells={}
 for i,arm in enumerate(arms,1):
  prefix=f'{i}-{arm}'; rate=101 if arm=='F32' else 100
  rows=[{'n_gen':1 if n==1 else 0,'n_prompt':0 if n==1 else n,'n_depth':d,'avg_ts':rate,'autokernel_hardened':False} for n,d in [(1,8192),(5,8192),(1,32768),(5,32768)]]
  (out/f'{prefix}.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
  for ext in ('err','process.json'): (out/f'{prefix}.{ext}').write_text('fixture')
  (out/f'{prefix}.maps').write_text('/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu/bin/libggml-cpu.so.0.16.0')
  (out/f'{prefix}.numa').write_text('PASS')
  env={'GGML_FA_SPLIT_KV':'0'}
  if arm=='F32': env['GGML_FA_VKQ_F32']='1'
  (out/f'{prefix}.env.json').write_text(json.dumps(env))
 for n,d in [(1,8192),(5,8192),(1,32768),(5,32768)]: cells[str((n,d))]={'effects':[.01,.01,.01],'median':.01}
 rec={'schema':'epyc.rtg57.vkq_comparison.native.v1','completed_utc':'2026-10-27T00:00:00+00:00','source_commit':source,'recipe_sha256':recipe,'predeclared_rule_sha256':hashb((root/'PROTOCOL.md').read_bytes()),'protocol_id':None,'n_process_pairs':3,'arm_order':arms,'cells':cells,'evidence_sha256':{p.name:hashb(p.read_bytes()) for p in out.iterdir()}}
 rec['source_manifest_sha256']=hashb((out.parent/'SOURCES.sha256').read_bytes()); rec['producer_script_sha256']=hashb((out.parent/'driver.py').read_bytes())
 rec['content_sha256']=hashb(json.dumps(rec,sort_keys=True,separators=(',',':'),allow_nan=False).encode()); path=out/'native-receipt.json';path.write_text(json.dumps(rec))
 claims=mod.project(path);assert len(claims)==4 and all(x['protocol_id']=='' for x in claims)
 (out/'1-HYBRID.jsonl').write_text('tampered')
 try: mod.project(path)
 except ValueError: pass
 else: raise AssertionError('tampered arm accepted')
print('projector four native claims and tamper refusal PASS; synthetic only')
