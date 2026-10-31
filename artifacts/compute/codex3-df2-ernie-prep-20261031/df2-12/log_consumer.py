#!/usr/bin/env python3
import json,pathlib,sys
d=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent/"run"
for p in sorted(d.glob("*.response.json")):
 x=json.loads(p.read_text()).get("native_response",{}); print(json.dumps({"file":p.name,"tokens_cached":x.get("tokens_cached"),"timings":x.get("timings"),"tokens_present":isinstance(x.get("tokens"),list)}))
for n in ("PARTIAL.json","TERMINAL.json","FAILURE.json"):
 p=d/n
 if p.exists():print(n,p.read_text().strip())
