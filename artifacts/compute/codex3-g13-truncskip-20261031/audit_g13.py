import json,hashlib,math,collections
from pathlib import Path
b=Path('/mnt/raid0/llm/tmp/codex-ni-kbrag-g13-truncskip-20261030'); result=json.loads((b/'results/RESULT.json').read_text()); truths=json.loads((b/'k7_cert_cases.json').read_text())['cases']; truth={x['id']:x for x in truths}; assert len(truth)==70
arms={}; ids=set(truth)
for folder in sorted((b/'results/cases').iterdir()):
 if not folder.is_dir():continue
 vals=[]; files=list(folder.glob('*.json'));assert len(files)==70
 for f in files:
  x=json.loads(f.read_text());t=truth[x['id']]; assert x['source_manifest_sha256']==result['source_manifest_sha256'];assert x['evidence_files']==t['evidence_files']; ranked=[z['file'] for z in x['results'][:10]]; assert ranked==x['metrics']['ranked_files']; val=len(set(t['evidence_files']) & set(ranked))/len(set(t['evidence_files'])); assert math.isclose(val,x['metrics']['recall@10'],abs_tol=1e-12);vals.append(val)
 assert {json.loads(f.read_text())['id'] for f in files}==ids
 avg=sum(vals)/len(vals);assert math.isclose(avg,result['recall_at10'][folder.name],abs_tol=1e-12);arms[folder.name]=avg
base=arms['4000_256_plain']
for a,v in arms.items():
 if a=='canonical_stored':continue
 assert math.isclose(v-base,result['matched_delta'][a],abs_tol=1e-12)
 assert (v-base>0.02)==result['descriptive_gt2pp'][a]
pins=json.loads((b/'CORPUS-PINS.json').read_text()); assert len(pins['files'])==1522
for row in pins['files']:
 p=Path(row['snapshot']);assert p.stat().st_size==row['raw_bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],p
print('490 case metrics, truth IDs, source manifest, and all 1522 source snapshot hashes pass')
print('chunk equivalence',collections.Counter(x.get('chunk_multiset_exact','changed') for x in pins['files']),'changed',pins['changed_snapshot_files'])
print('recall@10',arms,'matched deltas', {k:round(v-base,9) for k,v in arms.items() if k!='canonical_stored'})
workers=result['worker_counts']['records'];assert len(workers)==8 and all(w['exit_rc']==0 and w['invocation']==result['invocation'] and w['source_manifest_sha256']==result['source_manifest_sha256'] for w in workers)
for field in ('native_new_encodes','cache_skips','cache_loads'): assert sum(w[field] for w in workers)==result['worker_counts'][field]
print('8 worker records aggregate validated', {k:result['worker_counts'][k] for k in ('native_new_encodes','cache_skips','cache_loads')})
