import json,os,pathlib
D=pathlib.Path(__file__).resolve().parent
smoke=os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1'
p=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
r=json.loads(p.read_text());assert r.get('status')==('SOURCE_OBJECT_BUILT' if smoke else 'BUILD_PASS');assert r.get('object_size_bytes' if smoke else 'binary_size_bytes',0)>0
