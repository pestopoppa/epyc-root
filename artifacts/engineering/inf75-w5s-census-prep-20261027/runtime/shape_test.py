from private_census import Shape
from server_evidence_full import tensor_shape_observed,shape_evidence
s=Shape('verify',5,1)
def graph(n,w):return {'decode_id':1,'model':'m','ctx':'c','api_batch':{'tokens':n,'tokens_per_seq':{'0':n}},'dense_matmul_ne11':[w]}
assert tensor_shape_observed(s,{'graphs':[graph(5,5)]})
assert not tensor_shape_observed(s,{'graphs':[graph(4,4),graph(1,1)]})
assert not tensor_shape_observed(s,{'graphs':[graph(5,4),graph(4,5)]})
start='n_seq_max = 1 n_ubatch = 2048'
log='id 0 | task 1 | new prompt, task.n_tokens = 4\nid 0 | task 1 | accepted 1/ 4 draft tokens'
req=[{'speculative.n_max':4}]; res=[{'stop':True,'timings':{'predicted_n':1,'draft_n':4}}];samples=[{'phase':'requests','slots':[{'id':0,'is_processing':True}]}]
assert shape_evidence(s,start,log,req,res,samples)['observed']
req[0]['speculative.n_max']=5
assert not shape_evidence(s,start,log,req,res,samples)['observed']
print('PASS: width 5 same-call only, four drafted tokens; split/wrong budget refused')
from server_evidence_full import graph_evidence
full='CENSUS_MODEL model=m path=/m\n'
phase=('CENSUS_API_BEGIN id=1 ctx=c tokens=5 scope=api_batch seq_ids=0,0,0,0,0,\n'
       'CENSUS_GRAPH gid=2 id=1 ctx=c model=m nodes=1 rc=0\n'
       'CENSUS_NODE gid=2 id=1 ctx=c model=m node=0 op=MUL_MAT backend=CPU src1_ne=4,5,1,1\n'
       'CENSUS_API_END id=1 ctx=c rc=0\n')
assert tensor_shape_observed(s,graph_evidence(full,phase,'/m'))
assert not tensor_shape_observed(s,graph_evidence(full,phase.replace('END id=1 ctx=c','END id=1 ctx=x'),'/m'))
assert not tensor_shape_observed(s,graph_evidence(full,phase.replace('model=m nodes','model=x nodes'),'/m'))
try:graph_evidence(full,phase+phase,'/m')
except ValueError:pass
else:raise AssertionError('duplicate identity accepted')
print('PASS: graph, model, context and decode identity coupled; duplicate rejected')
