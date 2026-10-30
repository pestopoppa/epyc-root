import hashlib,json,tempfile
from pathlib import Path
from paired_journal import run,encoded,create
from partial_assessment import assess
D='a'*64
rows=[{'id':str(i),'question':'question '+str(i),'answer':'gold'} for i in range(3)]
manifest=[{'id':r['id'],'row_sha256':hashlib.sha256(encoded(r)).hexdigest(),'prompt_sha256':hashlib.sha256(r['question'].encode()).hexdigest()} for r in rows]
def events(matched):
 root={'type':'kani_spawn','id':'root','depth':0,'parent':None}
 out=[root]
 if matched:out += [{'type':'kani_message','id':'root','msg':{'role':'assistant','tool_calls':[{'function':{'name':'delegate'}}]}},{'type':'kani_spawn','id':'child','depth':1,'parent':'root'},{'type':'kani_delegated','parent_id':'root','child_id':'child'}]
 return out+[{'type':'root_message','msg':{'role':'assistant','content':'gold'}},{'type':'round_complete'}]
def native(matched=False):return {'status':'complete','flat_server_bound_attested':True,'answer':'gold','delegations':int(matched),'max_depth':int(matched),'native_events':events(matched),'wall_seconds':1.0,'server_usage':{'prompt_tokens':1,'completion_tokens':1}}
def key(r,arm):return hashlib.sha256(encoded({'campaign_sha256':D,'id':r['id'],'arm':arm})).hexdigest()
def start(j,r,arm):create(j/(key(r,arm)+'.start'),{'identity':{'campaign_sha256':D,'id':r['id'],'arm':arm,'prompt_sha256':hashlib.sha256(r['question'].encode()).hexdigest()},'exposure':'unknown'})
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);j=root/'j';j.mkdir();attempt=root/'attempt';attempt.mkdir();(attempt/'capture.json').write_text(json.dumps({'declaration_sha256':D}))
 for r in rows:run(j,D,{'id':r['id'],'prompt':r['question'],'gold':r['answer']},'production_repl',lambda _:native())
 run(j,D,{'id':rows[0]['id'],'prompt':rows[0]['question'],'gold':'gold'},'redel_delegate_wait',lambda _:native(True))
 for r in rows[1:]:start(j,r,'redel_delegate_wait')
 for i,matched in ((1,True),(2,False)):
  e=attempt/f'{i}-redel_delegate_wait/redel_delegate_wait/redel-log';e.mkdir(parents=True);(e/'events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in events(matched)))
 result=assess(j,attempt,D,rows,manifest)
 assert result['result']=='INCOMPLETE_DIAGNOSTIC' and result['arms']['redel_delegate_wait']['correct_bounds']==[1,3]
 assert result['matched_case_ids']==['0','1'] and result['delegation_unknown_case_ids']==['2'] and result['paired_complete']==1
 assert result['mechanism']=='DELEGATION_OBSERVED_EVALUATION_PENDING' and result['step3_gate_passed'] is False
 assert result['paired_em_difference_bounds']==[-2/3,0.0] and result['paired_complete_percentile_bootstrap_95ci'] is None
 assert result['completed_native_costs']['production_repl']['wall_seconds']==3.0
 # A later attempt must retain observations from the original exposure.
 attempt.rename(root/'campaign-pilot-earlier');attempt=root/'campaign-pilot-later';attempt.mkdir();(attempt/'capture.json').write_text(json.dumps({'declaration_sha256':D}))
 again=assess(j,attempt,D,rows,manifest);assert again['matched_case_ids']==['0','1'] and again['delegation_unknown_case_ids']==['2']
 # Tampering cannot turn a mismatched end into a grade.
 path=j/(key(rows[0],'redel_delegate_wait')+'.end');rec=json.loads(path.read_bytes());rec['correct']=False;path.write_bytes(encoded(rec))
 try:assess(j,attempt,D,rows,manifest)
 except ValueError:pass
 else:raise AssertionError('score tamper accepted')
print('PASS: partial bounds, native positive and incomplete absence, tamper refusal')
