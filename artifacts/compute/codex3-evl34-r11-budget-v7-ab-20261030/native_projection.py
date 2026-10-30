"""Conservative separation of REPL graph events from tracked sub-LM calls.

A child-provided depth is evidence of its report, not an independent depth
attestation. Missing whole-route coverage yields unknown, never no delegation.
"""
def project_repl(response,broker_events,coverage_attested=False):
 if not isinstance(response,dict) or response.get('mode')!='repl' or not isinstance(response.get('answer'),str):raise ValueError('native REPL response required')
 graph=response.get('delegation_events')
 if not isinstance(graph,list):raise ValueError('graph event list required')
 if not isinstance(broker_events,list):raise ValueError('broker event list required')
 tracked=[]
 for event in broker_events:
  if not isinstance(event,dict) or event.get('source')!='child_reported_repl_depth' or type(event.get('depth')) is not int or event['depth'] not in (0,1):raise ValueError('invalid trace event')
  if event['depth']==1:tracked.append(event)
 if type(coverage_attested) is not bool:raise ValueError('invalid coverage')
 return {'answer':response['answer'],'native_graph_delegation_events':len(graph),'reported_tracked_sub_lm_calls':len(tracked),'max_reported_depth':max((x['depth'] for x in broker_events),default=None),'whole_route_delegation':'unknown' if not coverage_attested else 'not established by this projection','depth_attestation':'child-reported, not independent','native_response':response,'broker_events':broker_events}

def project_redel(events,server_usage,flat_server_bound_attested):
 if type(flat_server_bound_attested) is not bool:raise ValueError('invalid server-bound evidence')
 if not isinstance(events,list) or not events:raise ValueError('native event list required')
 spawns={};delegated=[];answer=None;rounds=0
 for e in events:
  if not isinstance(e,dict) or not isinstance(e.get('type'),str):raise ValueError('invalid native event')
  typ=e['type']
  if typ=='error':raise ValueError('native ReDel error')
  if typ=='kani_spawn':
   ident=e.get('id');depth=e.get('depth')
   if not isinstance(ident,str) or not ident or ident in spawns or type(depth) is not int or depth not in (0,1):raise ValueError('invalid spawn/depth')
   spawns[ident]=e
  elif typ=='kani_delegated':delegated.append(e)
  elif typ=='root_message':
   msg=e.get('msg')
   if not isinstance(msg,dict):raise ValueError('invalid root message')
   if msg.get('role')=='assistant' and isinstance(msg.get('content'),str) and msg['content']:answer=msg['content']
  elif typ=='round_complete':rounds+=1
 if rounds!=1 or answer is None or sum(x['depth']==0 for x in spawns.values())!=1:raise ValueError('incomplete ReDel result')
 for e in delegated:
  parent=spawns.get(e.get('parent_id'));child=spawns.get(e.get('child_id'))
  if parent is None or child is None or parent['depth']!=0 or child['depth']!=1 or child.get('parent')!=parent['id']:raise ValueError('unmatched delegation')
 # DelegateAndWait can legitimately reuse an existing helper across rounds.
 # Repeated child ids require distinct native parent/child message coordinates;
 # repeated or unlocated edges are not trustworthy.
 seen={}
 for e in delegated:
  child=e['child_id'];coords=(e.get('parent_message_idx'),e.get('child_message_idx'))
  prior=seen.setdefault(child,[])
  if prior and (any(type(x) is not int or x<0 for x in coords) or any(any(type(x) is not int or x<0 for x in p) for p in prior) or coords in prior):raise ValueError('duplicate or unlocated delegation')
  prior.append(coords)
 if server_usage is not None and (not isinstance(server_usage,dict) or any(type(server_usage.get(k)) is not int or server_usage[k]<0 for k in ('prompt_tokens','completion_tokens'))):raise ValueError('bad server usage')
 return {'status':'complete','answer':answer,'delegations':len(delegated),'max_depth':max(x['depth'] for x in spawns.values()),'server_usage':server_usage,'flat_server_bound_attested':flat_server_bound_attested,'native_events':events}
