"""Read actual nested OpenCode tool records and preserve ordering/content."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
UNITS=HERE.parent.parent/'ws58-a3b-frozen-revalidation-20261126/quality-runs/cache-safe-01/units'
NAMES=('gpu-DS41-W-66-off-common-on-sampling','gpu-DS41-W-66-off-recommended')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

def extract(name):
    unit=UNITS/name;path=unit/'OPEN-CODE-SESSION.json';export=json.loads(path.read_text());rows=[]
    for mi,message in enumerate(export['messages']):
        parts=message.get('content',[])
        if not isinstance(parts,list):continue
        for pi,part in enumerate(parts):
            if not isinstance(part,dict) or part.get('type')!='tool':continue
            state=part.get('state',{});inputs=state.get('input',{});content=state.get('content',[])
            text='\n'.join(p.get('text','') for p in content if isinstance(p,dict))
            if part.get('name') not in {'shell','edit','write','execute'}:continue
            rows.append({'message_index':mi,'part_index':pi,'message_id':message.get('id'),'tool_id':part.get('id'),
                         'name':part.get('name'),'time':part.get('time',{}),'status':state.get('status'),
                         'input':inputs,'content_text':text,'metadata':state.get('metadata'),
                         'pytest_failure':bool('FAILED ' in text or 'RunAborted' in text),
                         'pytest_pass':bool(' passed in ' in text or '1 passed' in text),
                         'tail_pipeline':'| tail' in str(inputs),'script_namespace':'scripts.kernel_rnd.autokernel.loop' in str(inputs),
                         'failure_namespace_autokernel':'autokernel.loop.loop.RunAborted' in text})
    result=json.loads((unit/'RESULT.json').read_text());edits=[r for r in rows if r['name'] in {'edit','write'}]
    final_edit=max((r['time'].get('completed',0) for r in edits),default=0)
    after=[{'tool_id':r['tool_id'],'completed_ms':r['time'].get('completed'),'pytest_pass':r['pytest_pass'],'pytest_failure':r['pytest_failure'],'command':r['input'].get('command')} for r in rows if r['name']=='shell' and r['time'].get('created',0)>final_edit]
    report={'unit':name,'export_sha256':sha(path),'raw_result_sha256':sha(unit/'RESULT.json'),
            'raw_status':result['status'],'raw_candidate_status':result.get('candidate_status'),'raw_oracle':result.get('oracle'),
            'final_edit_completed_ms':final_edit,'commands_after_final_edit':after,'tools':rows,
            'source_shape':'messages[].content[] tool.state.content[] text; tool time.created/ran/completed in ms',
            'model_calls':0}
    write(HERE/(name+'.TRACE.json'),report)
    return report

if __name__=='__main__':
    for name in NAMES:
        r=extract(name);print(name,r['final_edit_completed_ms'],r['commands_after_final_edit'])
