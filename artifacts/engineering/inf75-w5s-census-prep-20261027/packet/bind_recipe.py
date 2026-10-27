import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
p=json.loads((D/'recipes.json').read_text())['workloads'][0]
if p['prefill_fixture']['tokens']!=4096:raise ValueError('wrong frozen prompt length')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
binding={'canonical_source_target':'architect_general@8074','scope':p['scope'],
 'recipes_sha256':sha(D/'recipes.json'),'native_builder_sha256':sha(D/'native-builder.json'),
 'not_complete_obligated_P0d_set':True,'retained_author_obligation':'open',
 'prefill_fixture':p['prefill_fixture'],'verify':'width 5 = sampled token plus four actual drafts; same-call tensor and API witness',
 'startup':'40 GiB free target each claimed node; full-byte native touch, 120s per node',
 'foreign':'two full snapshot intervals inside actual request window per phase'}
(D/'OWNER-RECIPE-BOUND.json').write_text(json.dumps(binding,sort_keys=True)+'\n')
