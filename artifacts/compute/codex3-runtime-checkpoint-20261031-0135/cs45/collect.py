#!/usr/bin/env python3
"""Derive per-tail selection/confirmation reports from completed, non-redrawn raw cells."""
import collections,hashlib,json,os,pathlib,subprocess,sys
D=pathlib.Path(__file__).resolve().parent; R=pathlib.Path(os.environ.get('CS45_RESULTS',str(D/'results'))); data=pathlib.Path('/mnt/raid0/llm/epyc-inference-research/data/turn-taking-cs45-1-tail-v1/manifest')
clips=[json.loads(x) for x in (data/'clips.jsonl').read_text().splitlines()]; pairs=[json.loads(x) for x in (data/'pairs.jsonl').read_text().splitlines()]; assert len(clips)==820
records={}
for path in sorted((R/'cells').glob('*.json')):
 if path.name.endswith('.exposure.json'): continue
 r=json.loads(path.read_text())
 if r.get('status')!='ok': raise SystemExit('cannot derive verdict: native failure recorded '+str(path))
 raw=R/'raw'/(path.stem+'.jsonl'); assert raw.is_file() and hashlib.sha256(raw.read_bytes()).hexdigest()==r['raw_sha256']; d=r['data']; assert json.loads(raw.read_text())==d; k=(d['clip'],d['arm'],d.get('variant','')); assert k not in records; records[k]=d
assert len(records)==8200, 'missing or unknown native cells'
for suffix in ('t0300','t0600','t1000','t3000','t4000'):
 root=R/'derived'/suffix; M=root/'manifest'; O=root/'out'; M.mkdir(parents=True,exist_ok=True); O.mkdir(exist_ok=True); cs=[c for c in clips if c['clip_id'].endswith('.'+suffix)]; ps=[p for p in pairs if p['pair_id'].endswith('.'+suffix)]; assert len(cs)==164 and len(ps)==82
 for name,rs in [('clips',cs),('pairs',ps)]: (M/(name+'.jsonl')).write_text(''.join(json.dumps(x)+'\n' for x in rs))
 buckets=collections.defaultdict(list)
 for c in cs:
  cid=c['clip_id']
  for (clip,arm,var),rec in records.items():
   if clip!=cid: continue
   prefix={'silero':'silero_all','smartturn':'st_all','parakeet':'pk_all'}[arm]; buckets[prefix].append(rec)
 for prefix,rs in buckets.items(): (O/(prefix+'.jsonl')).write_text(''.join(json.dumps(x)+'\n' for x in rs))
 assert len(buckets['silero_all'])==164 and len(buckets['st_all'])==164 and len(buckets['pk_all'])==1312
 env=os.environ.copy(); env.update(CS45_OUTPUT=str(root),CS45_MANIFEST=str(M),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
 for name,args in [('score.py',[str(root/'scores')]),('adaptive.py',[str(root/'adaptive.json')])]:
  subprocess.run([str(D.parent/'venv312/bin/python'),str(D/'source'/name),*args],env=env,check=True,stdout=subprocess.DEVNULL)
print('derived all five tails; synthetic pink room tone; backchannel INT-FPR n/a; no advancement')
