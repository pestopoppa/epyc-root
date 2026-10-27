#!/usr/bin/env python3
"""Check installed UFH-12 G-S source and synthetic planning-canary receipt."""
import hashlib, importlib, json, sys
from pathlib import Path

def sha(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink(): raise RuntimeError('missing or symlink source: '+str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(receipt_path,seal):
    rp=Path(receipt_path)
    if not rp.is_file() or rp.is_symlink(): raise RuntimeError('missing enrollment receipt')
    r=json.loads(rp.read_text()); root=Path(r['installed_root'])
    if not root.is_absolute() or root.resolve(strict=True)!=root or not root.is_dir(): raise RuntimeError('unresolved installed root')
    if r.get('source_family')!='VB-UFH12-GS' or r.get('status')!='passed' or r.get('planning_context')!='visible' or r.get('synthetic') is not True: raise RuntimeError('canary did not prove planning visibility')
    files={'adapter_sha256':root/'scripts/vidya/adapters/ufh12_gs_coverage.py','helper_sha256':root/'scripts/vidya/producers/ufh12_gs_diagnostic.py','producer_sha256':root/'scripts/vidya/producers/ufh12_gs_capture.py','registry_sha256':root/'scripts/vidya/ingest_sources.py','carrier_sha256':root/'scripts/vidya/adapters/_native_sidecar.py','canary_sha256':root/'scripts/vidya/ufh12_gs_canary.py','runtime_source_seal_sha256':Path(seal),'evidence_sha256':Path(r['evidence_path'])}
    pins=json.loads(Path(__file__).with_name('INSTALLED-PINS.json').read_text())
    for field in ('adapter_sha256','helper_sha256','producer_sha256','carrier_sha256','canary_sha256'):
        if pins.get(field)!=r.get(field): raise RuntimeError('installed file differs from reviewed source: '+field)
    for field,path in files.items():
        if r.get(field)!=sha(path): raise RuntimeError('enrollment drift: '+field)
    evidence=json.loads(Path(r['evidence_path']).read_text())
    claims=[x for x in evidence.get('planning_evidence',{}).get('claims',[]) if x.get('source_kind')=='ufh12-gs-coverage']
    if evidence.get('synthetic') is not True or evidence.get('planning_status')!='ready' or len(claims)!=2 or any(x.get('value')!=1 or x.get('unit')!='records' or x.get('model_file')!='synthetic-fixture.gguf' for x in claims) or len(evidence.get('reports',[]))!=2 or any(x.get('rows_projected')!=1 or x.get('refused') for x in evidence['reports']): raise RuntimeError('canary evidence invalid')
    sys.path.insert(0,str(root/'scripts/vidya'))
    try:
        reg=importlib.import_module('ingest_sources')
        if Path(reg.__file__).resolve()!=files['registry_sha256'] or Path(reg.SOURCES['ufh12-gs-coverage'].load().__file__).resolve()!=files['adapter_sha256']: raise RuntimeError('foreign registry or adapter')
    finally: sys.path.pop(0)
    return root
if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: enrollment.py RECEIPT SOURCE.sha256')
    print(verify(sys.argv[1],sys.argv[2]))
