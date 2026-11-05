import json,sys
from pathlib import Path
from output_path import result_path
try:
 r=json.loads(result_path(Path(__file__).resolve().parent).read_text())
 assert r['schema']=='kvu19b.synthetic-trace-qual.v1' and r['status']=='QUALIFIED_SYNTHETIC' and r['tests']==2 and r['mutation_cases']==14 and r['model'] is None
except (ValueError,KeyError,OSError,AssertionError): sys.exit(1)
