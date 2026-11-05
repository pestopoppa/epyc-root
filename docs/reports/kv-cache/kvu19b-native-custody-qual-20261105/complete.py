import json,sys
from pathlib import Path
from output_path import result_path
try:
 r=json.loads(result_path(Path(__file__).resolve().parent).read_text());assert r['schema']=='kvu19b.native-custody.v1' and r['status']=='QUALIFIED' and r['progress']==3 and r['model'] is None
except (OSError,ValueError,KeyError,AssertionError):sys.exit(1)
