import json,sys,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 r=json.loads((D/'out/RESULT.json').read_text())
 assert r['schema']=='kpf17.wrapper-stop-qualification.v1' and r['status']=='PASS' and r['synthetic'] is True and r['smoke'] is False
 assert len(r['observations'])==10 and all(x['safe'] is True and x['invalid_timeout'] is False and x['captured_pids_verified_dead'] is True for x in r['observations'])
 expected={(v,s,b) for v in ('patched','original') for s,b in [('startup',False),('startup',True),('postjob',False),('postjob',True),('postjob75',False)]}
 assert {(x['variant'],x['stage'],x['stop']) for x in r['observations']}==expected
 for x in r['observations']:
  assert x['complete']==(not x['stop'] and x['stage']!='postjob75' if x['variant']=='patched' else True)
 seal=json.loads((D/'qualification-seal.json').read_text())
 assert r['sources']==seal
 assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in seal['sha256'].items())
except (OSError,ValueError,KeyError,AssertionError,TypeError):sys.exit(1)
