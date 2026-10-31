#!/usr/bin/env python3
"""Read native worker control logs and verify real control request evidence."""
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);partial='--partial' in sys.argv;r=json.loads(p.read_text());d=p.parent
if r.get('rc')!=(75 if partial else 0) or r.get('partial') is not partial or not r.get('server_dead') or not r.get('client_dead') or r.get('cleanup_errors') or (partial and not r.get('cutoff_triggered')) or r.get('gpu_samples',0)<2 or r.get('completed_rounds',0)<1:raise SystemExit('native summary incomplete')
e=json.loads((d/'ENVELOPE.json').read_text());eh=hashlib.sha256((d/'ENVELOPE.json').read_bytes()).hexdigest()
if not e.get('gpu_resident') or e.get('model_sha256')!='a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348':raise SystemExit('native model/residency mismatch')
rounds=sorted(d.glob('round-*'))
if not rounds:raise SystemExit('no completed public control')
r0=next((x for x in rounds if (x/'DONE.json').is_file()),None)
if r0 is None:raise SystemExit('no control writer')
for name in ('estimate','baseline','static','tale'):
 f=r0/'0000'/(name+'.json');o=json.loads(f.read_text());w=o.get('write_warrant',{})
 if o.get('status')!='complete' or w.get('envelope_sha256')!=eh or o.get('finish_reason') is None:raise SystemExit('request or warrant incomplete '+name)
 b={k:v for k,v in o.items() if k!='record_sha256'}
 if hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()!=o.get('record_sha256'):raise SystemExit('request hash mismatch')
print(json.dumps({'control':'cutoff' if partial else 'normal','server_pid':r.get('server_pid'),'gpu_samples':r['gpu_samples'],'mtp_log_evidence':e.get('mtp_log_evidence'),'server_log':str(d/'server.log'),'envelope':str(d/'ENVELOPE.json'),'control_round':str(r0)}))
