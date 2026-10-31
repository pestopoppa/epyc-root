import hashlib,itertools,json,os,pathlib,subprocess
D=pathlib.Path(__file__).resolve().parent; F=D/'fixture'; (F/'cells').mkdir(parents=True,exist_ok=True); (F/'raw').mkdir(exist_ok=True); orig=D/'smoke-result/cells'; clips='/mnt/raid0/llm/epyc-inference-research/data/turn-taking-cs45-1-tail-v1/manifest/clips.jsonl'; rows=[json.loads(x) for x in open(clips)]
samples=[json.loads(p.read_text()) for p in orig.glob('*.json') if not p.name.endswith('.exposure.json')]; assert len(samples)==10 and all(x['status']=='ok' for x in samples)
for i,c in enumerate(rows):
 for j,s in enumerate(samples):
  r=json.loads(json.dumps(s)); r['data']['clip']=c['clip_id']; raw=json.dumps(r['data'])+'\n'; (F/'raw'/f'{i:03d}-{j:02d}.jsonl').write_text(raw); r['raw_sha256']=hashlib.sha256(raw.encode()).hexdigest(); (F/'cells'/f'{i:03d}-{j:02d}.json').write_text(json.dumps(r))
env=os.environ.copy(); env['CS45_RESULTS']=str(F); subprocess.run([str(D.parent/'venv312/bin/python'),str(D/'collect.py')],env=env,check=True)
for suffix in ('t0300','t0600','t1000','t3000','t4000'):
 r=json.loads((F/'derived'/suffix/'scores/results.json').read_text()); assert all(x['int_fpr'] is None for x in r['selection'].values()); a=json.loads((F/'derived'/suffix/'adaptive.json').read_text()); assert all(x['sel']['int_fpr'] is None for x in a)
print('8200-cell writer fixture PASS; per-tail, no backchannel INT-FPR, synthetic only')
