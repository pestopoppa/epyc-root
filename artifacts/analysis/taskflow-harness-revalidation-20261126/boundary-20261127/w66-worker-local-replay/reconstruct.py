from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
FROZEN=HERE.parent.parent/'ws58-a3b-frozen-revalidation-20261126'
TARGET='scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py'
sha=lambda x:hashlib.sha256(x.encode()).hexdigest()
records=[]
for f in sorted(HERE.glob('*.TRACE.json')):
    d=json.loads(f.read_text());text=(FROZEN/'quality-v4/packets/DS41-W-66/baseline'/TARGET).read_text();edits=[]
    for t in d['tools']:
        if t['name']=='edit' and t['status']=='completed' and t['input']['path']=='/case/'+TARGET:
            x=t['input'];assert text.count(x['oldString'])==1
            text=text.replace(x['oldString'],x['newString'],1)
            edits.append({'completed_ms':t['time']['completed'],'tool_id':t['tool_id'],'target_sha256':sha(text)})
    final=(FROZEN/'quality-runs/cache-safe-01/units'/d['unit']/'independent/work'/TARGET).read_text()
    assert text==final
    records.append({'unit':d['unit'],'edits':edits,'reconstruction_matches_final':True,'final_sha256':sha(final)})
(HERE/'EDIT-STATE.json').write_text(json.dumps(records,indent=2)+'\n')
