import json,pathlib
p=pathlib.Path(__file__).resolve().parent/'out/RESULT.json'
r=json.loads(p.read_text()) if p.exists() else {}
raise SystemExit(0 if r.get('id')=='kpf50-raw-residency-qual-20261105' and r.get('status')=='SYNTHETIC_RESIDENCY_QUALIFIED' and r.get('partial') is False and r.get('scan_complete') is True and r.get('cleanup_confirmed') is True and len(r.get('cases',[]))==10 and all(c.get('matched') is True for c in r['cases']) else 1)
