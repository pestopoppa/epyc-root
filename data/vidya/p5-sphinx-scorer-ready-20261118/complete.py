import json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent

def validate_native(x,case):
 assert x['schema']=='p5.gold-control.v1' and x['status']=='COMPLETE'
 assert set(x['arms'])=={'negative','gold'} and x.get('owned_containers_removed') is True
 assert not x.get('error') and not x.get('cleanup_error')
 for arm in x['arms'].values():
  assert type(arm['resolved']) is bool
  for field in ['FAIL_TO_PASS','PASS_TO_PASS']:
   assert set(arm[field])==set(json.loads(case[field]))
   assert all(v in ('PASSED','FAILED') for v in arm[field].values())
 gold=x['arms']['gold'];negative=x['arms']['negative']
 passed=(gold['resolved'] and all(v=='PASSED' for v in gold['FAIL_TO_PASS'].values()) and all(v=='PASSED' for v in gold['PASS_TO_PASS'].values()) and not negative['resolved'] and any(v=='FAILED' for v in negative['FAIL_TO_PASS'].values()) and all(v=='PASSED' for v in negative['PASS_TO_PASS'].values()))
 assert x['decision']==('PASS' if passed else 'FAIL')
 return x['decision']

if __name__=='__main__':
 x=json.loads((D/'RESULT.json').read_text());case=json.loads((D/'case.json').read_text())
 validate_native(x,case)
 for name,key in [('SOURCE.sha256','producer_source_manifest_sha256'),('launch.sh','producer_launcher_sha256')]:
  assert x[key]==hashlib.sha256((D/name).read_bytes()).hexdigest()
