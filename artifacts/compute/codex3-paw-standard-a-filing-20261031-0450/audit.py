#!/usr/bin/env python3
"""Recheck saved checkpoint identities; bundle hashing is opt-in due to cost."""
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('--rehash-bundles',action='store_true');args=p.parse_args()
d=pathlib.Path('/mnt/raid0/llm/tmp/codex3-paw-hsf-t1-20261030/A');s=d/'epoch/state.json';raw=s.read_bytes();x=json.loads(raw)
r=d/'results/real-1793419509204324996/job-result.json';j=json.loads(r.read_text());programs={}
for key,v in x['programs'].items():
 path=pathlib.Path(v['path']);row={'path':str(path),'recorded_sha256':v['sha256'],'exists':path.is_file()}
 if args.rehash_bundles and path.is_file():
  h=hashlib.sha256()
  with path.open('rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  row['hash_matches']=h.hexdigest()==v['sha256']
 programs[key]=row
print(json.dumps({'checkpoint_path':str(s),'checkpoint_sha256':hashlib.sha256(raw).hexdigest(),'declaration_sha256':x['declaration_sha256'],'source_manifest_sha256':x['source_manifest_sha256'],'programs':programs,'case_disposition_counts':{k:sum(y['disposition']==k for y in j['case_dispositions']) for k in sorted({y['disposition'] for y in j['case_dispositions']})},'reason':j['reason'],'wall_s':j['wall_s'],'children_drained':j['children_drained'],'grant_writer_record':'2026-10-31T04:03:56Z granted 48-71 start=04:03Z end=06:00Z','launcher_end':'2026-10-31T04:45:26Z rc=1; grant deleted after terminal','predicate':'UNKNOWN: guard did not record individual predicate outcomes'},indent=2))
