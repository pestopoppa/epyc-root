"""Producer-time native observation manifest; no invented protocol or grade."""
import datetime,hashlib,json,os
from pathlib import Path
SCHEMA='epyc.df2.row_exact.native.v1'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1<<20),b''): h.update(part)
    return h.hexdigest()
def emit(out,mode,verdicts,source_seal,build_seal,build_manifest,probe_manifest,case_manifest,producer_path):
    out=Path(out).resolve(); files=sorted(p for p in out.iterdir() if p.is_file() and p.name not in ('belief-native.json','CAPTURE-COMPLETE.json'))
    if mode not in ('output','byte') or not files or not verdicts: raise ValueError('empty/foreign producer data')
    identities={k:{'path':str(Path(p).resolve()),'sha256':sha(p)} for k,p in {'source_seal':source_seal,'build_seal':build_seal,'build_manifest':build_manifest,'probe_manifest':probe_manifest,'case_manifest':case_manifest,'producer':producer_path}.items()}
    rec={'schema':SCHEMA,'mode':mode,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),'verdicts':verdicts,'protocol_id':'','backend':'hip','gpu_identity':json.loads((out/'gpu-identity.json').read_text()),'identities':identities,'artifacts':[{'path':str(p),'sha256':sha(p)} for p in files]}
    target=out/'belief-native.json'; tmp=out/'belief-native.tmp'
    with tmp.open('x') as f: json.dump(rec,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,target); return target
