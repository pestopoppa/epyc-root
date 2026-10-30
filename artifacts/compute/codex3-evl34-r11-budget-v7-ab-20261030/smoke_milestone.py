"""Prospective smoke milestone, independent of pilot outcome adjudication."""
def inspect(events):
 if not isinstance(events,list) or any(not isinstance(e,dict) for e in events):raise ValueError('invalid events')
 roots=[e for e in events if e.get('type')=='kani_spawn' and e.get('depth')==0 and e.get('parent') is None and isinstance(e.get('id'),str)]
 if len(roots)!=1:return {'qualified':False,'reason':'root_missing'}
 if any(e.get('type')=='kani_spawn' and (type(e.get('depth')) is not int or e['depth'] not in (0,1)) for e in events):return {'qualified':False,'reason':'invalid_depth'}
 root=roots[0]['id']; spawns={}; delegates=[]; calls=[]
 for i,e in enumerate(events):
  if e.get('type')=='kani_spawn' and e.get('depth')==1 and e.get('parent')==root and isinstance(e.get('id'),str):spawns[e['id']]=(i,e.get('name'))
  if e.get('type')=='kani_delegated' and e.get('parent_id')==root:delegates.append((i,e.get('child_id')))
  if e.get('type')=='kani_message' and e.get('id')==root:
   m=e.get('msg') or {}
   if m.get('role')=='assistant' and any((c.get('function') or {}).get('name')=='delegate' for c in (m.get('tool_calls') or []) if isinstance(c,dict)):calls.append(i)
 for decision,child in delegates:
  info=spawns.get(child)
  if info is None:continue
  spawn,name=info
  if not isinstance(name,str) or not name or not any(call<spawn<=decision for call in calls):continue
  content=[i for i,e in enumerate(events) if e.get('type')=='kani_message' and e.get('id')==child and (e.get('msg') or {}).get('role')=='assistant' and isinstance((e.get('msg') or {}).get('content'),str) and (e.get('msg') or {}).get('content')]
  stopped=[i for i,e in enumerate(events) if e.get('type')=='kani_state_change' and e.get('id')==child and e.get('state')=='stopped']
  usage=[i for i,e in enumerate(events) if e.get('type')=='tokens_used' and e.get('id')==child and type(e.get('completion_tokens')) is int and e['completion_tokens']>0]
  waits=[i for i,e in enumerate(events) if e.get('type')=='kani_message' and e.get('id')==root and (e.get('msg') or {}).get('role')=='function' and (e.get('msg') or {}).get('name')=='wait' and (e.get('msg') or {}).get('is_tool_call_error') is False and isinstance((e.get('msg') or {}).get('content'),str) and (e.get('msg') or {}).get('content','').startswith(name+':\n') and 'encountered an exception:' not in (e.get('msg') or {}).get('content','')]
  if any(decision<c<s<w and any(decision<u<=s for u in usage) for c in content for s in stopped for w in waits):return {'qualified':True,'reason':'linked_child_response_and_wait','child_id':child,'max_depth':1}
 return {'qualified':False,'reason':'linked_child_wait_not_observed'}
