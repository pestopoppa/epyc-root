import json,hashlib,os
from pathlib import Path
import sealed_journal as s
from prompt_projection import project
p=Path(__file__).parent
# Synthetic sealed manifests test admission, and cannot affect the frozen source declarations.
r=p/('sealed-journal-fixture-'+str(os.getpid()));r.mkdir()
row={'id':'fixture','question':'question','context':{'title':['t'],'sentences':[['body']]},'answer':'gold'}
prompt=project(row);raw=json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode();item={'id':'fixture','row_sha256':hashlib.sha256(raw).hexdigest(),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
dec={'pilot':[item],'independent_smoke_control':{'id':'other','row_sha256':'b'*64}}
decb=json.dumps(dec).encode();decl=hashlib.sha256(decb).hexdigest();(r/'PREDECLARATION-FROZEN.json').write_bytes(decb)
manifest={'declaration_sha256':decl,'pilot':[item],'control':{'id':'other','row_sha256':'b'*64,'prompt_sha256':'c'*64}}
mb=json.dumps(manifest).encode();(r/'FROZEN-PROMPT-MANIFEST.json').write_bytes(mb)
s.BASE=r;s.DECL=decl;s.MANIFEST=hashlib.sha256(mb).hexdigest();calls=[]
def call(q):calls.append(q);return {'answer':'gold','delegations':0,'status':'complete','flat_server_bound_attested':True,'max_depth':0}
assert s.invoke_cell(r/'journal',row,'production_repl','pilot',call)['correct']
assert s.invoke_cell(r/'journal',row,'production_repl','pilot',call)['correct'] and len(calls)==1
for bad,cohort in [(row|{'question':'changed'},'pilot'),(row,'control'),(row|{'id':'other'},'pilot')]:
 try:s.invoke_cell(r/'journal',bad,'redel_delegate_wait',cohort,call)
 except ValueError:pass
 else:raise AssertionError('unsealed exposure allowed')
try:s.invoke_cell(r/'journal',row,'redel_delegate_wait','pilot',lambda _:(_ for _ in ()).throw(TimeoutError()))
except TimeoutError:pass
else:raise AssertionError('cutoff accepted')
try:s.invoke_cell(r/'journal',row,'redel_delegate_wait','pilot',call)
except RuntimeError:pass
else:raise AssertionError('unknown exposure replayed')
assert len(calls)==1
print('sealed population/prompt gate, completed reopen and unknown-cell replay refusal passed')
for i,invalid in enumerate(({'answer':'[ERROR: backend]','delegations':0,'status':'complete','flat_server_bound_attested':True,'max_depth':0},{'answer':'gold','delegations':0,'status':'complete','flat_server_bound_attested':False,'max_depth':0},{'answer':'gold','delegations':0,'status':'complete','flat_server_bound_attested':True,'max_depth':'unknown'})):
 store=r/('reject-'+str(i))
 try:s.invoke_cell(store,row,'production_repl','pilot',lambda _:invalid)
 except ValueError:pass
 else:raise AssertionError('invalid native result accepted')
 try:s.invoke_cell(store,row,'production_repl','pilot',call)
 except RuntimeError:pass
 else:raise AssertionError('refused exposed result silently replayed')
print('in-band error, coverage missing and unknown depth preserve unknown exposure')
