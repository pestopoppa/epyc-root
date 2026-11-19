import json,sys,hashlib,os
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 smoke=os.environ.get('FILLER_DRYRUN')=='1'
 target=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
 if smoke:
  assert target.resolve()!= (D/'out/RESULT.json').resolve()
  assert target.stat().st_mtime >= int(os.environ['FILLER_SMOKE_T0'])
 r=json.loads(target.read_text())
 assert r['schema']=='kpf17.wrapper-stop-qualification.v1' and r['status']=='PASS' and r['synthetic'] is True and r['smoke'] is smoke
 assert type(r['case_count']) is int and r['case_count']==10
 assert len(r['observations'])==r['case_count'] and all(x['safe'] is True and x['invalid_timeout'] is False and x['captured_pids_verified_dead'] is True for x in r['observations'])
 expected={(v,s,b) for v in ('patched','original') for s,b in [('startup',False),('startup',True),('postjob',False),('postjob',True),('postjob75',False)]}
 assert {(x['variant'],x['stage'],x['stop']) for x in r['observations']}==expected
 for x in r['observations']:
  assert x['complete']==(not x['stop'] and x['stage']!='postjob75' if x['variant']=='patched' else True)
 seal=json.loads((D/'qualification-seal.json').read_text())
 assert r['sources']==seal
 assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in seal['sha256'].items())
except (OSError,ValueError,KeyError,AssertionError,TypeError):sys.exit(1)
