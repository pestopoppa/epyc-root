import ast,ctypes,hashlib,json,os,pathlib,re,signal,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent
source=D/'r3_job.py'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=digest(source); tree=ast.parse(source.read_text()); defs={x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)}
names=['proc_birth','subreaper','children','capture','capture_tree','cleanup','close_owned','cleanup_test']
module=ast.Module(body=[defs[n] for n in names],type_ignores=[]);ast.fix_missing_locations(module)
env=dict(ctypes=ctypes,os=os,pathlib=pathlib,re=re,signal=signal,subprocess=subprocess,sys=sys,time=time,OWNED={},SIGNALS=[],libc=ctypes.CDLL(None,use_errno=True));exec(compile(module,str(source),'exec'),env)
compares=[x for x in ast.walk(tree) if isinstance(x,ast.Compare) and isinstance(x.left,ast.Name) and x.left.id=='marker' and len(x.ops)==1 and isinstance(x.ops[0],ast.In) and len(x.comparators)==1 and isinstance(x.comparators[0],ast.Name) and x.comparators[0].id=='text']
if len(compares)!=1:raise RuntimeError('marker expression not uniquely bound')
expr=ast.Expression(compares[0]);ast.fix_missing_locations(expr);code=compile(expr,str(source),'eval')
base='KPF-41 direct gfx90a vec row parity passed: '
tests=[]
for case,expected,actual,want in [('f16','f16','f16',True),('q8','q8_0','q8_0',True),('wrong-type','q8_0','f16',False),('suffix-mutation','q8_0','q8_0-corrupt',False)]:
 observed=eval(code,{},dict(marker=base+expected,text=base+actual+'\n'));tests.append(dict(case=case,observed=observed,expected=want,matched=observed==want))
env['cleanup_test']()
after=digest(source)
if before!=after:raise RuntimeError('source drift')
out=pathlib.Path(os.environ['QUAL_RESULT']);out.parent.mkdir(parents=True,exist_ok=True)
r={'row_id':'kpf41-supervisor-qual-20261105','status':'PROBED','source_sha256':before,'cleanup_actual':'PASS','tests':tests,'exact_marker_safe':all(x['matched'] for x in tests),'scope':'copied r3 actual cleanup_test and extracted marker expression; synthetic only; no GPU, native fixture or whole lifecycle claim','progress':len(tests)+1,'boundary':{'stop':os.environ['FILLER_STOPFILE'],'end':float(os.environ['FILLER_DEADLINE'])}}
out.write_text(json.dumps(r,indent=2)+'\n')
