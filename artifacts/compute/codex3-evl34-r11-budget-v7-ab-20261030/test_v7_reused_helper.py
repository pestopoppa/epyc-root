from native_projection import project_redel
root={'type':'kani_spawn','id':'r','depth':0,'parent':None};child={'type':'kani_spawn','id':'c','depth':1,'parent':'r'}
def delegated(p,c):return {'type':'kani_delegated','parent_id':'r','child_id':'c','parent_message_idx':p,'child_message_idx':c}
end=[{'type':'root_message','msg':{'role':'assistant','content':'fixture'}},{'type':'round_complete'}]
graph=[root,child,delegated(1,0),delegated(4,2),*end]
r=project_redel(graph,{'prompt_tokens':1,'completion_tokens':1},True);assert r['delegations']==2 and r['max_depth']==1
for bad in ([root,child,delegated(1,0),delegated(1,0),*end],[root,child,{'type':'kani_delegated','parent_id':'r','child_id':'c'},delegated(4,2),*end]):
 try:project_redel(bad,None,True)
 except ValueError:pass
 else:raise AssertionError('duplicate or unlocated edge accepted')
print('PASS: native reused helper edges with distinct coordinates accepted; duplicates and unlocated repeat refused')
