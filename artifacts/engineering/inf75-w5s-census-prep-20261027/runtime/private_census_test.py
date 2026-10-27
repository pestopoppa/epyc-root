from pathlib import Path
from unittest.mock import patch
import private_census as c
from autokernel.controller.workload_contract import WorkloadCensus
from flash_next_census import NAMES
model=Path('/fake')/NAMES[0]
weights=WorkloadCensus(str(model),'qwen4exp',2560,{'Q8_0':1224})
ident={'model':{'shards':['a','b','c'],'head':'d'}}
def probe(binary,model,shape,**kwargs):
 return {'state':c.OBSERVED,'nodes_total':1001,'shape':shape.to_dict()}
with patch.object(c,'read_flash_next_weights',return_value=weights) as read:
 r=c.produce_census(workload_id='fixture',workload_signature='fixture',model=model,identity=ident,shapes=[c.Shape('prefill',2048),c.Shape('decode',1),c.Shape('verify',5)],binary=Path('/fake/server'),probe=probe)
 assert read.call_args.args[0]==[model.parent/name for name in NAMES]
 assert r['weights']['tensor_types']=={'Q8_0':1224} and r['identity']['model']==ident['model'] and r['validity']['state']==c.OBSERVED
 r['graph']['per_shape'].pop();assert c.census_state(r)==c.UNKNOWN
 try:c.produce_census(workload_id='fixture',workload_signature='fixture',model=model.parent/NAMES[1],identity=ident,shapes=[],binary=Path('/fake/server'),probe=probe)
 except ValueError:pass
 else:raise AssertionError('non-first model accepted')
print('PASS: private producer preserves all identities and aggregated weights, refuses partial shapes and wrong first shard')
