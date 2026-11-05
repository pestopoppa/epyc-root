import json
from job import result_path,ID
try:
 r=json.loads(result_path().read_text())
 assert r['row_id']==ID and r['status'] in ('CENSUS_COMPLETE','UNKNOWN') and r['serializer_source']=='UNKNOWN' and r['binary_source_equivalence']=='UNKNOWN' and r['profiler_gpu_id_to_bdf']=='UNKNOWN' and r['model'] is None and r['gpu_work'] is False
except (OSError,ValueError,KeyError,AssertionError): raise SystemExit(1)
