import sys,json,hashlib,importlib.util,dataclasses,copy
from pathlib import Path
from unittest.mock import patch
D=Path(__file__).resolve().parent
OLD=Path('/mnt/raid0/llm/tmp/refactor-c6-gpu-property-diag-20261031')
OUT=OLD/'runs/20261031T075837Z-3073572/native'
sys.path.insert(0,str(OLD))
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inputs={str(p):sha(p) for p in OUT.iterdir() if p.is_file()}
old=module('original_diag',OLD/'diag_validate.py')
try:old.validate_native(OUT,0)
except AssertionError: original_refused=True
else:raise AssertionError('original defect not reproduced')
new=module('fixed_diag',D/'diag_validate_fixed.py')
result=new.validate_native(OUT,0)
real=new.read_complete
negative=[]
def corrupt(text,rc):
 cases=real(text,rc);cases[0]=dataclasses.replace(cases[0],params=cases[0].params+' CORRUPTED');return cases
with patch.object(new,'read_complete',corrupt):
 try:new.validate_native(OUT,0)
 except AssertionError:negative.append('parsed case field corruption refused')
 else:raise AssertionError('corrupt case accepted')
assert inputs=={str(p):sha(p) for p in OUT.iterdir() if p.is_file()}
receipt={'schema':'c6.retained_json_replay.v1','original_validator_refused':original_refused,'fixed_validator_pass':True,'fixed_validator_sha256':sha(D/'diag_validate_fixed.py'),'original_validator_sha256':sha(OLD/'diag_validate.py'),'original_inputs_unchanged':True,'native_files':inputs,'negative_controls':negative,'native':result,'scope':'post-run diagnostic readback only; original wrapper failure preserved; no GPU rerun, new measurement warrant, input-byte pairing or GAK pass'}
(D/'REPLAY-RESULT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'original_refused':True,'fixed_pass':True,'negative':negative,'cohorts':[{'name':x['name'],'counts':x['status_counts']} for x in result['phases']],'full_gak_pass':result['full_gak_pass']}))
