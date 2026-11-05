import json,os,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
p=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_DRYRUN')=='1' else D/'out/RESULT.json'
try:
 r=json.loads(p.read_text());assert r['status']==('SMOKE_INPUTS_PINNED' if os.environ.get('FILLER_DRYRUN')=='1' else 'PARITY_PASS')
except (OSError,KeyError,ValueError,AssertionError):sys.exit(1)
