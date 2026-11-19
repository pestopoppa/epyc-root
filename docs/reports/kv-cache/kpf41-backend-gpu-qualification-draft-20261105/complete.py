import json,os,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
smoke=os.environ.get('FILLER_DRYRUN')=='1'
p=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
try:
 r=json.loads(p.read_text());assert r['status']==('SMOKE_PASS' if smoke else 'QUALIFICATION_PASS');assert r['progress']==1
except (OSError,KeyError,ValueError,AssertionError):sys.exit(1)
