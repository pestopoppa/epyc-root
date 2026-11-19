import json,sys
from pathlib import Path
from output_path import result_path
try:
 r=json.loads(result_path(Path(__file__).resolve().parent).read_text())
 assert r['status']=='QUALIFIED_SYNTHETIC' and r['tests']==2 and r['mutations']==10 and r['progress']==10
except (ValueError,KeyError,OSError,AssertionError): sys.exit(1)
