import json,pathlib
p=pathlib.Path(__file__).resolve().parent/'out/RESULT.json'
r=json.loads(p.read_text()) if p.exists() else {}
raise SystemExit(0 if r.get('row_id')=='kpf50-raw-maps-qual-20261105' and len(r.get('cases',[]))==20 and all(c.get('matched') is True for c in r.get('cases',[])) and r.get('status')=='SYNTHETIC_REFUSAL_QUALIFIED' and r.get('partial') is False and r.get('scan_complete') is True and r.get('cleanup_confirmed') is True else 1)
