import hashlib,json,os,sys
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 smoke=os.environ.get('FILLER_DRYRUN')=='1'
 if smoke:
  result=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
  r=json.loads(result.read_text())
  o=Path(r['attempt']).resolve()
 else:
  o=Path((D/'COMPLETE_ATTEMPT').read_text().strip()).resolve()
  r=json.loads((o/'RESULT.json').read_text())
  assert json.loads((D/'out/RESULT.json').read_text())==r
 assert o.parent == (D/'attempts').resolve()
 assert r['status']=='PASS' and r['smoke'] is smoke and r['attempt']==str(o)
 names=('checked_counter.hpp','test_checked_counter.cpp','test_checked_counter','compile.log','test.log','compile.receipt.json','test.receipt.json')
 assert set(r['sha256'])==set(names)
 for n,h in r['sha256'].items(): assert hashlib.sha256((o/n).read_bytes()).hexdigest()==h
 for n in ('compile','test'):
  x=json.loads((o/(n+'.receipt.json')).read_text()); assert x['command_exit']==0 and x['supervisor_exit']==0 and x['cleanup_verified'] and x['child_absent'] and not x['cleanup_killed'] and not x['interrupted'] and x['birth_ticks']
except (OSError,KeyError,ValueError,TypeError,AssertionError): sys.exit(1)
