import json,os,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
p=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(D/'out/RESULT.json')))
try:
 d=json.loads(p.read_text()); assert (d.get('status')=='compiled-object' and d.get('object_size_bytes',0)>0) or (d.get('status')=='BUILD_PASS' and len(d.get('files',{}))>=4)
except (OSError,ValueError,AssertionError): sys.exit(1)
