import json,os,pathlib,sys
b=pathlib.Path(__file__).resolve().parent
p=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(b/'out'/'RESULT.json')))
try:r=json.loads(p.read_text())
except (OSError,ValueError):sys.exit(1)
sys.exit(0 if r.get('processed_files')==(1 if os.environ.get('FILLER_SMOKE')=='1' else 16) and len(r.get('records',[]))==(5 if os.environ.get('FILLER_SMOKE')=='1' else 80) and r.get('status')=='INVENTORY_COMPLETE' and r.get('mode')==('smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full') else 1)
