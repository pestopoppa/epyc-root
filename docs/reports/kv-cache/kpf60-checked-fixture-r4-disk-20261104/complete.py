import hashlib,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 r=json.loads((D/'out/RESULT.json').read_text())
 if r['schema']!='kpf60.checked-fixture.v1' or r['status']!='PASS' or r['smoke'] is not False:raise ValueError('result')
 for key,p in (('source_sha256',D/'checked_counter.hpp'),('fixture_sha256',D/'test_checked_counter.cpp'),('binary_sha256',D/'out/test_checked_counter'),('compile_log_sha256',D/'out/compile.log'),('test_log_sha256',D/'out/test.log')):
  if hashlib.sha256(p.read_bytes()).hexdigest()!=r[key]:raise ValueError('digest')
except (OSError,KeyError,ValueError,TypeError):sys.exit(1)
