from native_projection import project_repl
r={'mode':'repl','answer':'fixture','delegation_events':[]}
a=project_repl(r,[{'source':'child_reported_repl_depth','depth':0},{'source':'child_reported_repl_depth','depth':1}])
assert a['native_graph_delegation_events']==0 and a['reported_tracked_sub_lm_calls']==1 and a['whole_route_delegation']=='unknown' and a['depth_attestation']=='child-reported, not independent'
assert project_repl(r,[])['whole_route_delegation']=='unknown'
try:project_repl(r,[{'source':'child_reported_repl_depth','depth':2}])
except ValueError:pass
else:raise AssertionError('depth overflow accepted')
print('native REPL graph and tracked sub-LM semantics separated; missing coverage remains unknown')
