import collections, hashlib, json, sys
from pathlib import Path
P=Path('/mnt/raid0/llm/tmp/codex3-evl34-deepdive-r11-budget-v6-20261030')
C=Path('/mnt/micron/codex3-evl34-deepdive-r11-budget-v6-20261030/pilot/campaign-pilot-1793397283007158126')
sys.path.insert(0,str(P))
from paired_journal import encoded
from sealed_journal import DECL, MANIFEST
from prompt_projection import project
from pair_contract import exact
from natural_qualification import event_qualification
def inspect_wire_capture(path):
 files=sorted(path.glob('*.json'))
 if not files: raise ValueError('no captured ReDel request')
 first=json.loads(files[0].read_bytes())
 names=[t.get('function',{}).get('name') for t in first.get('tools',[])]
 if names!=['delegate','wait'] or first.get('tool_choice') not in (None,'auto'): raise ValueError('tool serialization missing or forced')
 return {'first_wire_sha256':hashlib.sha256(files[0].read_bytes()).hexdigest()}
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((P/'PREDECLARATION-FROZEN.json').read_bytes())==DECL
assert sha((P/'FROZEN-PROMPT-MANIFEST.json').read_bytes())==MANIFEST
dec=json.loads((P/'PREDECLARATION-FROZEN.json').read_bytes()); m=json.loads((P/'FROZEN-PROMPT-MANIFEST.json').read_bytes())
private=json.loads((P/'PILOT-PRIVATE.json').read_bytes()); assert private['source_sha256']==dec['source_sha256']
j=C.parent/'pilot-journal'; aggregates={}; raw_matches=[]; cases=[]
for arm in ('production_repl','redel_delegate_wait'):
 correct=complete=0; wall=0.; tokens=collections.Counter()
 for idx,(row,entry,manifest) in enumerate(zip(private['rows'],dec['pilot'],m['pilot'],strict=True)):
  assert sha(encoded(row))==entry['row_sha256']==manifest['row_sha256'] and row['id']==entry['id']==manifest['id']
  promptsha=sha(project(row).encode()); assert promptsha==manifest['prompt_sha256']
  ident={'campaign_sha256':DECL,'id':row['id'],'arm':arm,'prompt_sha256':promptsha}; key=sha(encoded({'campaign_sha256':DECL,'id':row['id'],'arm':arm}))
  start=j/(key+'.start'); end=j/(key+'.end'); assert json.loads(start.read_bytes())['identity']==ident
  if end.exists():
   rec=json.loads(end.read_bytes()); assert rec['identity']==ident and rec['status']=='complete' and rec['start_sha256']==sha(start.read_bytes())
   n=rec['native']; assert n['status']=='complete' and n['flat_server_bound_attested'] is True and exact(n['answer'],row['answer'])==rec['correct']
   correct+=rec['correct']; complete+=1; wall+=n['wall_seconds']; tokens.update(n['server_usage'])
  if arm=='redel_delegate_wait':
   ev=C/f'{idx}-redel_delegate_wait/redel_delegate_wait/redel-log/events.jsonl'; events=[json.loads(x) for x in ev.read_text().splitlines()]
   matched=event_qualification(events)
   wire=inspect_wire_capture(C/f'{idx}-redel_delegate_wait/redel_delegate_wait/outbound-requests')
   if matched: raw_matches.append(idx+11)
   cases.append({'case':idx+11,'accuracy_status':'complete' if end.exists() else 'unknown','native_matched_delegation_observed':matched,'native_events_sha256':sha(ev.read_bytes()),'captured_unforced_first_request':True,'first_request_sha256':wire['first_wire_sha256']})
 aggregates[arm]={'complete':complete,'unknown':10-complete,'normalized_em_correct_known':correct,'original_denominator':10,'em_bounds':[correct,correct+10-complete],'completed_wall_seconds_sum':round(wall,6),'completed_server_tokens':dict(tokens)}
assert raw_matches==[11,12,13,14,15,16,19]
result={'schema':'evl34-r11-offline-partial-audit/v1','result':'INCOMPLETE_DIAGNOSTIC','pilot_assessment':'DELEGATION_OBSERVED_EVALUATION_PENDING','step3_gate_passed':False,'declaration_sha256':DECL,'source_manifest_sha256':sha((P/'CAMPAIGN-SOURCES.sha256').read_bytes()),'native_result_sha256':sha((C/'result.json').read_bytes()),'denominator_pairs':10,'all_20_start_identities_verified':True,'aggregates':aggregates,'cases':cases,'matched_delegation_definition':'frozen event_qualification: root assistant delegate call before linked depth-1 spawn and kani_delegated event','accuracy_notes':'unknowns are not wrong; bounds use original ten cases','raw_event_match_notes':'positive observations on incomplete routes establish presence only; no absence claim for incomplete case 20','failure_causes':{'11':'journal record exceeds 2 MiB bound','13-16':'native child logs aggregate reservation exhausted','20':'native child log invalid tool-call argument JSON'},'pilot_done':False,'server_drained':json.loads((C/'result.json').read_bytes())['server_drained']}
print(json.dumps(result,indent=2,sort_keys=True))
