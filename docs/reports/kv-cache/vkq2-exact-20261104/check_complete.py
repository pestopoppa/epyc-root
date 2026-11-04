import json,pathlib
p=pathlib.Path(__file__).resolve().parent/'RESULT.json'
r=json.loads(p.read_text());assert r['complete'] is True and r['mode']=='full'
assert len(r['records'])==20 and set(r['cells'])=={'16384','65536'}
