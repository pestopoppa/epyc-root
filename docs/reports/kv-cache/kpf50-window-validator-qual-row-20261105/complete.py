import json,pathlib
p=pathlib.Path(__file__).resolve().parent/'out/RESULT.json'
r=json.loads(p.read_text()) if p.exists() else {}
raise SystemExit(0 if r.get('status')=='SYNTHETIC_REFUSAL_QUALIFIED' and r.get('partial') is False and r.get('scan_complete') is True and r.get('cleanup_confirmed') is True else 1)
