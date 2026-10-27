from copy import deepcopy
from pathlib import Path
from flash_next_census import validate_parts,NAMES
p=[Path('/fake')/n for n in NAMES]
def part(i,n):
 return {'version':3,'count':n,'metadata':{'split.no':i,'split.count':3,'split.tensors.count':1224,**({'general.architecture':'qwen4exp','qwen4exp.embedding_length':2560} if i==0 else {})},'names':[f'{i}-{j}' for j in range(n)],'types':{8:n} if n else {}}
a=[part(0,0),part(1,373),part(2,851)]
assert validate_parts(p,a).tensor_types=={'Q8_0':1224}
def reject(paths,parts):
 try:validate_parts(paths,parts)
 except ValueError:return
 raise AssertionError('invalid accepted')
for paths in (p[:2],p[::-1],[p[0]]*3):reject(paths,a)
for field,value in [('split.no',2),('split.count',4),('split.tensors.count',1223),('general.architecture','bad')]:
 b=deepcopy(a);b[1]['metadata'][field]=value;reject(p,b)
b=deepcopy(a);b[2]['names'][0]=b[1]['names'][0];reject(p,b)
b=deepcopy(a);b[2]['count']-=1;reject(p,b)
print('PASS: exact ordered set, metadata, architecture, totals, duplicate names, type aggregation')
