#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
EXPECTED_CUSTODY_SHA256='ab6d10e509d7483963a39b0da2caccab4ac8b85ee33a9e0b117107601d8d8702'
EXPECTED_BINDING_SHA256='5b56f806a39f24a2f68dafe147b5b56295a2975fea3914bca2a388e571b16b82'
ROW_ID='kvu-kpf17-map-revalidation-r3-20261104'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
 r=json.loads((D/'out/RESULT.json').read_text());s=json.loads((D/'input_seal.json').read_text());b=json.loads((D/'binding.json').read_text());c=json.loads((D/'out/attempt.json').read_text())
 assert r.get('schema')=='kpf17.alt17-custody-race.v1' and r.get('status')=='PASS' and r.get('sealed') is True and r.get('result_kind')=='full'
 assert r.get('case_count')==1 and r.get('unit_key')=='case_count'
 assert r.get('attempt_id')==ROW_ID==c.get('attempt_id') and c.get('row_id')==ROW_ID and r.get('attempt_nonce')==c.get('nonce') and len(c.get('nonce',''))==48
 assert c.get('result_path')==str(D/'out/RESULT.json') and r.get('attempt_context_sha256')==sha(D/'out/attempt.json')
 assert c.get('input_seal_sha256')==sha(D/'input_seal.json') and c.get('runner_sha256')==sha(D/'qualify.py')
 assert r.get('input_seal_sha256')==sha(D/'input_seal.json')
 assert r.get('custody_source_sha256')==s.get('custody_source_sha256')==EXPECTED_CUSTODY_SHA256==sha(D/'custody.py')
 assert b['runner_files']['custody.py']==EXPECTED_CUSTODY_SHA256 and sha(D/'binding.json')==s.get('source_binding_sha256')==EXPECTED_BINDING_SHA256
 assert r.get('tested_function')=='custody.validate_maps' and r.get('baseline')=='ACCEPTED_COMPLETE_FIVE_DSO_FIXTURE'
 assert r.get('case',{}).get('revalidation')=='REFUSED' and r['case'].get('barrier')=='PASS'
except Exception:sys.exit(1)
