import os,sys,json,hashlib,time,subprocess
from pathlib import Path
out=Path(sys.argv[1]); i=int(sys.argv[2]); scenario=sys.argv[3]; mode=sys.argv[4]
if mode=='stop':
    child=subprocess.Popen([sys.executable,'-I','-B','-c','import time; time.sleep(120)'])
    (out/'stub-descendant.json').write_text(json.dumps({'pid':child.pid,'birth':Path(f'/proc/{child.pid}/stat').read_text().rsplit(')',1)[1].split()[19]}))
    time.sleep(120)
receipt={'window_index':i,'scenario':scenario,'row_id':os.environ['FILLER_ID'],'command_sha256':hashlib.sha256(json.dumps([sys.executable,'-I','-B',*sys.argv],separators=(',',':')).encode()).hexdigest(),'status':'VALID_FIRST_QUALIFYING_STEP','partial':False}
if mode=='badbinding': receipt['row_id']='wrong-row'
(out/'window-result.json').write_text(json.dumps(receipt))
