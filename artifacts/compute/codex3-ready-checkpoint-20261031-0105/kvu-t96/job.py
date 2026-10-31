#!/usr/bin/python3
import datetime,hashlib,json,os,pathlib,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent
control=os.environ.get('RTG57_CONTROL')=='1'
root=D/('control-' if control else 'run-');root=pathlib.Path(str(root)+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+str(os.getpid()));root.mkdir()
env=dict(os.environ,RTG57_OUT=str(root/'out'),WATCH_RESULT=str(root/'watch-result.json'),FILLER_STOPFILE=str(D/'STOP'))
limit=8*1024**2 if control else 110*1024**2
with (root/'native.log').open('wb') as log:
 rc=subprocess.call([sys.executable,'-B',str(D/'resource_watch.py'),'--limit-kib',str(limit),sys.executable,'-B',str(D/('control.py' if control else 'driver.py'))],env=env,stdout=log,stderr=subprocess.STDOUT)
w=json.loads((root/'watch-result.json').read_text())
result={'rc':rc,'partial':rc==75 and w['partial'],'cleanup_verified':w['cleanup_verified'],'target_load_tested':not control,'watch':w}
(root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'path':str(root),**result}),flush=True)
if not w['cleanup_verified']: sys.exit(125)
sys.exit(rc)
