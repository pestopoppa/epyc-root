import json, tempfile
from pathlib import Path
import enrollment
B=Path(__file__).resolve().parent
receipt=json.loads((B/'INSTALL-RECEIPT.json').read_text())
assert enrollment.verify(B/'INSTALL-RECEIPT.json',B/'SOURCE.sha256')==Path(receipt['installed_root'])
with tempfile.TemporaryDirectory(dir=B/'test-run/tmp') as tmp:
    p=Path(tmp)/'bad.json'
    for field in ('registry_sha256','producer_sha256','helper_sha256','adapter_sha256','carrier_sha256','runtime_source_seal_sha256','evidence_sha256','canary_sha256'):
        bad=dict(receipt); bad[field]='0'*64; p.write_text(json.dumps(bad))
        try: enrollment.verify(p,B/'SOURCE.sha256')
        except RuntimeError: pass
        else: raise AssertionError('tampered '+field+' accepted')
    bad=dict(receipt); bad['synthetic']=False; p.write_text(json.dumps(bad))
    try: enrollment.verify(p,B/'SOURCE.sha256')
    except RuntimeError: pass
    else: raise AssertionError('non-synthetic fixture receipt accepted')
print('PASS enrollment source, receipt, evidence and identity tamper controls')
