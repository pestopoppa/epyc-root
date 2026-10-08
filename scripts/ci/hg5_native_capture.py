"""Private HG5 recipe draft. Hosted native run only after owner review and trigger."""
from __future__ import annotations
import ast, collections, hashlib, itertools, json, os, platform, subprocess, sys, time, xml.etree.ElementTree as ET
from pathlib import Path

RECIPE=Path(__file__).resolve().parents[2]
RESULT=Path(os.environ['RUNNER_TEMP'])/'hg5-native'/ 'result'
APP=Path(os.environ['GITHUB_WORKSPACE'])/'app'
ROOT=Path(os.environ['GITHUB_WORKSPACE'])/'recipe'
CARRIER=Path(os.environ['GITHUB_WORKSPACE'])/'carrier'
APP_PIN='c12c9c5e49e28fa69b5da30c646ecb967f616c58'
ROOT_PIN='152fb52cd0489b8756a69999c38e7d0e0afa9488'
CARRIER_PIN='4c0c653baf1654c8c25c66433cf39c8faefd8e52'
TESTS=['tests/unit/test_v1_escalation.py', 'tests/unit/test_v1_escalation_off_golden.py', 'tests/unit/test_openai_compat_default_golden.py', 'tests/unit/test_stages.py']
RECIPE_DATA=RECIPE/'scripts/ci/hg5_native'

def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def raw(path):
    if path.is_symlink() or not path.is_file(): raise RuntimeError('source is absent, nonregular, or symlink: '+str(path))
    return path.read_bytes()
def typed_tree(root):
    rows={'.':{'kind':'directory'}}
    if not root.exists(): return rows
    for base,dirs,files in os.walk(root,followlinks=False):
        bp=Path(base)
        for name in sorted(dirs+files):
            p=bp/name; rel=p.relative_to(root).as_posix(); st=p.lstat()
            import stat
            if stat.S_ISLNK(st.st_mode): rows[rel]={'kind':'opaque_symlink','mode':stat.S_IMODE(st.st_mode),'target_sha256':digest(os.readlink(p).encode())}
            elif stat.S_ISDIR(st.st_mode): rows[rel+'/']={'kind':'directory','mode':stat.S_IMODE(st.st_mode)}
            elif stat.S_ISREG(st.st_mode): rows[rel]={'kind':'regular','mode':stat.S_IMODE(st.st_mode),'bytes':st.st_size,'sha256':digest(raw(p))}
            else: raise RuntimeError('special result artifact: '+rel)
    return rows
def app_source_path(relative): return APP/relative
def inventory(path,source):
    """Portable names/literal parameters only; source identity is pinned by raw Git blobs."""
    tree=ast.parse(source.decode('utf-8'),filename=path);module=path[:-3].replace('/','.');definitions=[];cases=[]
    case_keys={};fixtures={}
    for top in tree.body:
        if isinstance(top,(ast.Assign,ast.AnnAssign)):
            targets=top.targets if isinstance(top,ast.Assign) else [top.target]
            if any(isinstance(t,ast.Name) and t.id=='CASES' for t in targets):
                if not isinstance(top.value,ast.Dict):raise RuntimeError('CASES must be literal dict')
                case_keys['CASES']=sorted(ast.literal_eval(key) for key in top.value.keys)
        if isinstance(top,(ast.FunctionDef,ast.AsyncFunctionDef)):
            for dec in top.decorator_list:
                if isinstance(dec,ast.Call) and ast.unparse(dec.func).endswith('fixture'):
                    params=next((k.value for k in dec.keywords if k.arg=='params'),None)
                    if params is not None:
                        if any(k.arg=='ids' for k in dec.keywords):raise RuntimeError('explicit fixture IDs require reviewed derivation')
                        fixtures[top.name]=ast.literal_eval(params)
    def param_id(value,name,index):
        if isinstance(value,str):return value.encode('unicode_escape').decode('ascii')
        if value is None or isinstance(value,(int,float,bool)):return str(value)
        if isinstance(value,dict):return name+str(index)
        raise RuntimeError('unreviewed parameter ID type')
    for top in tree.body:
        if isinstance(top,ast.ClassDef):cls=top.name;sequence=top.body
        elif isinstance(top,(ast.FunctionDef,ast.AsyncFunctionDef)):cls=None;sequence=[top]
        else:continue
        for fn in sequence:
            if not isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)) or not fn.name.startswith('test_'):continue
            dims=[]
            # Fixture parameters precede function parameters in the pytest callspec.
            for arg in fn.args.args:
                if arg.arg in fixtures:
                    values=fixtures[arg.arg];dims.append({'names':[arg.arg],'values':[[v] for v in values],'ids':[param_id(v,arg.arg,i) for i,v in enumerate(values)],'origin':'fixture'})
            for dec in reversed(fn.decorator_list):
                if isinstance(dec,ast.Call) and ast.unparse(dec.func).endswith('parametrize'):
                    if len(dec.args)!=2 or dec.keywords:raise RuntimeError('unreviewed parametrization options')
                    names=ast.literal_eval(dec.args[0]);names=[n.strip() for n in names.split(',')] if isinstance(names,str) else list(names)
                    expr=dec.args[1]
                    if isinstance(expr,ast.Call) and isinstance(expr.func,ast.Name) and expr.func.id=='sorted' and len(expr.args)==1 and isinstance(expr.args[0],ast.Name):values=case_keys[expr.args[0].id]
                    else:values=ast.literal_eval(expr)
                    rows=[[v] if len(names)==1 else list(v) for v in values]
                    if any(len(row)!=len(names) for row in rows):raise RuntimeError('parameter arity')
                    ids=['-'.join(param_id(v,n,i) for n,v in zip(names,row)) for i,row in enumerate(rows)]
                    if len(set(ids))!=len(ids):raise RuntimeError('parameter ID collision')
                    dims.append({'names':names,'values':rows,'ids':ids,'origin':'parametrize'})
            definition=(cls+'.' if cls else '')+fn.name
            definitions.append({'source_path':path,'definition':definition,'module':module,'class':cls,'function':fn.name,'param_dimensions':dims})
            products=itertools.product(*(range(len(dim['values'])) for dim in dims)) if dims else [()]
            for indexes in products:
                parameters={};parts=[]
                for dim,i in zip(dims,indexes):parameters.update(zip(dim['names'],dim['values'][i]));parts.append(dim['ids'][i])
                cases.append({'classname':module+('.'+cls if cls else ''),'name':fn.name+('['+'-'.join(parts)+']' if dims else ''),'source_path':path,'definition':definition,'parameters':parameters})
    identities=[(r['classname'],r['name']) for r in cases]
    if len(set(identities))!=len(identities):raise RuntimeError('duplicate derived identities')
    return definitions,cases

def verify_ast_manifest(manifest):
    definitions=[];derived=[]
    for path in TESTS:
        r=manifest['test_file_source_records'][path];b=raw(APP/path)
        if len(b)!=r['bytes'] or digest(b)!=r['sha256'] or hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=r['blob']:
            raise RuntimeError('pinned raw Git test source differs: '+path)
        ds,cs=inventory(path,b);definitions+=ds;derived+=cs
    if definitions!=manifest['ast_definitions'] or derived!=manifest['case_identities']:
        raise RuntimeError('portable AST names/parameter inventory differs')
    pairs=[(r['classname'],r['name']) for r in derived]
    if len(set(pairs))!=len(pairs):raise RuntimeError('duplicate expected JUnit identity')
    return derived
def source_snapshot(paths): return {str(p):digest(raw(p)) for p in paths}
def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(json.dumps(obj,sort_keys=True,indent=2).encode()+b'\n'); f.flush(); os.fsync(f.fileno())

def main():
    status={'state':'capture_started','capture_started':False,'native_receipt_state':'no_receipt','native_metric_value':None,'proposition_invented':False}
    boundary='initialization'; native_record=None; source_paths=[]
    try:
        if not RESULT.is_dir() or RESULT.is_symlink(): raise RuntimeError('workflow result directory missing or unsafe')
        entries={p.name for p in RESULT.iterdir()}
        if entries!={'status.json','dependency-install.log','pip-freeze.txt'}: raise RuntimeError('result directory entries differ from the exact workflow setup outputs')
        import stat
        for name in ('status.json','dependency-install.log','pip-freeze.txt'):
            path=RESULT/name; item=path.lstat()
            if not stat.S_ISREG(item.st_mode) or item.st_nlink!=1: raise RuntimeError('workflow setup output is not a singly-linked regular file: '+name)
            raw(path)
        status_path=RESULT/'status.json'; initial_status=json.loads(raw(status_path))
        if initial_status.get('state')!='setup_pending' or initial_status.get('capture_started') is not False: raise RuntimeError('workflow initial status does not show capture pending')
        status.update(capture_started=True,setup_outputs={name:digest(raw(RESULT/name)) for name in ('dependency-install.log','pip-freeze.txt')})
        status_path.write_text(json.dumps(status,sort_keys=True)+'\n')
        sm=json.loads(raw(RECIPE_DATA/'source-map.json')); cm=json.loads(raw(RECIPE_DATA/'expected-cases.json'))
        req=raw(RECIPE_DATA/'requirements-linux-py311.txt')
        if sm['status']!='PRIVATE_UNEXECUTED_RECIPE_DRAFT' or cm['status']!='STATIC_PROPOSAL_AWAITING_JUNIT_CONFIRMATION': raise RuntimeError('draft input status mismatch')
        if sm['app']['commit']!=APP_PIN or sm['root_context']['commit']!=ROOT_PIN or sm['native_carrier']['commit']!=CARRIER_PIN: raise RuntimeError('reviewed pins mismatch')
        if cm['ast_test_definition_count']!=56 or cm['ast_derived_expected_junit_case_count']!=87 or len(cm['case_identities'])!=87: raise RuntimeError('static identity proposal malformed')
        derived_cases=verify_ast_manifest(cm)
        if sm['dependency_lock']['requirements_sha256']!=digest(req) or sm['dependency_lock']['package_count']!=64 or sm['dependency_lock']['wheel_hash_count']!=905: raise RuntimeError('dependency lock closure differs from static review')
        if sm['test_identity']['case_manifest_sha256']!=digest(raw(RECIPE_DATA/'expected-cases.json')): raise RuntimeError('case manifest hash differs from source map')
        if git(APP,'rev-parse','HEAD')!=APP_PIN or git(APP,'rev-list','--parents','-n','1',APP_PIN).split()!=[APP_PIN,*sm['app']['parents']] or git(APP,'rev-parse',APP_PIN+'^{tree}')!=sm['app']['tree']: raise RuntimeError('APP pin, complete parent list, or tree differs')
        if git(ROOT,'rev-parse','HEAD')!=os.environ.get('GITHUB_SHA'): raise RuntimeError('ROOT recipe event pin differs from workflow SHA')
        git(ROOT,'cat-file','-e',ROOT_PIN+'^{commit}')
        if git(CARRIER,'rev-parse','HEAD')!=CARRIER_PIN: raise RuntimeError('carrier pin differs')
        for name,repo in [('APP',APP),('ROOT',ROOT),('CARRIER',CARRIER)]:
            if git(repo,'status','--porcelain','--untracked-files=all'): raise RuntimeError(name+' checkout is not clean')
        boundary='source_inventory'
        source_paths=[]
        for row in sm['app_source_config_envelope']['files']:
            p=app_source_path(row['path'])
            if row['mode']=='120000':
                if not p.is_symlink() or digest(os.readlink(p).encode('utf-8','surrogateescape'))!=row['sha256']: raise RuntimeError('symlink envelope mismatch: '+row['path'])
            else:
                data=raw(p)
                if len(data)!=row['bytes'] or digest(data)!=row['sha256'] or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=row['blob'] or stat.S_IMODE(p.lstat().st_mode)!=(0o755 if row['mode']=='100755' else 0o644): raise RuntimeError('APP source envelope raw Git blob/mode mismatch: '+row['path'])
                source_paths.append(p)
        for group,repo in [('root_context',ROOT),('native_carrier',CARRIER)]:
            for row in sm[group]['files']:
                p=repo/row['path']; data=raw(p)
                if len(data)!=row['bytes'] or digest(data)!=row['sha256'] or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=row['blob']: raise RuntimeError(group+' source pin mismatch: '+row['path'])
                if group=='root_context' and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=row['blob']: raise RuntimeError('historical enrolled ROOT blob differs: '+row['path'])
                source_paths.append(p)
        source_paths += [RECIPE/'scripts/ci/hg5_native_capture.py',RECIPE_DATA/'source-map.json',RECIPE_DATA/'expected-cases.json',RECIPE_DATA/'requirements-linux-py311.txt']
        source_paths=list(dict.fromkeys(source_paths))
        before=source_snapshot(source_paths)
        boundary='original_native_execution'
        junit=RESULT/'original-junit.xml'; native_out=RESULT/'native'
        test_command=[sys.executable,'-m','pytest','-c','pyproject.toml','-o','addopts=','-p','no:cacheprovider','-p','asyncio','-q','--junitxml='+str(junit),*TESTS]
        env=dict(os.environ); env.update({'PYTHONPATH':str(APP),'CI':'true','ORCHESTRATOR_MOCK_MODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTEST_ADDOPTS':'','PYTEST_PLUGINS':'','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','PYTHONNOUSERSITE':'1','PYTHONUNBUFFERED':'1'})
        carrier_argv=[sys.executable,str(CARRIER/'scripts/ci/native_conformance.py'),'--cwd',str(APP),'--junit',str(junit),'--output',str(native_out),'--repo','app='+str(APP),'--repo','root_recipe='+str(ROOT),'--repo','carrier='+str(CARRIER)]
        for p in source_paths: carrier_argv += ['--read-path',str(p)]
        for test in TESTS: carrier_argv += ['--select',test]
        carrier_argv += ['--',*test_command]
        request={'carrier_argv':carrier_argv,'pytest_argv':test_command,'cwd':str(APP),'env_controls':{k:env[k] for k in ('CI','ORCHESTRATOR_MOCK_MODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTEST_ADDOPTS','PYTEST_PLUGINS','PYTHONDONTWRITEBYTECODE','PYTHONHASHSEED','PYTHONNOUSERSITE')},'selection':TESTS,'source_before_capture':before,'repositories':{'app':APP_PIN,'root_recipe_event':os.environ.get('GITHUB_SHA'),'enrolled_root_context':ROOT_PIN,'carrier':CARRIER_PIN},'ast_definition_count':56,'proposed_junit_identities':87,'native_case_count_claim':None}
        write_json(RESULT/'execution-request.json',request)
        typed_result_before_capture=typed_tree(RESULT)
        write_json(RESULT/'pre-capture-custody.json',{'phase':'immediately_before_original_native_capture','source_snapshot':before,'execution_request_sha256':digest(raw(RESULT/'execution-request.json')),'typed_result_tree_before_this_custody_record':typed_result_before_capture,'status_included':True,'self_excluded':True})
        run=subprocess.run(carrier_argv,cwd=APP,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
        (RESULT/'carrier-command.log').write_bytes(run.stdout); (RESULT/'carrier-command.exit').write_text(str(run.returncode)+'\n')
        receipt_path=native_out/'receipt.json'
        native_record=json.loads(raw(receipt_path))
        status.update(native_receipt_state=('native_true' if native_record.get('fixture_execution_conformant') is True else 'native_false' if native_record.get('fixture_execution_conformant') is False else 'native_null'),native_metric_value=native_record.get('fixture_execution_conformant'))
        junit_error=None; junit_counts=None; actual=[]; expected=[(x['classname'],x['name']) for x in cm['case_identities']]
        try:
            junit_bytes=raw(junit); root=ET.fromstring(junit_bytes)
            junit_rows=list(root.iter('testcase'))
            actual=[(x.get('classname',''),x.get('name','')) for x in junit_rows]
            junit_counts={'collected':len(junit_rows),'passed':sum(not any(x.find(t) is not None for t in ('failure','error','skipped')) for x in junit_rows),'failure':sum(x.find('failure') is not None for x in junit_rows),'error':sum(x.find('error') is not None for x in junit_rows),'skipped':sum(x.find('skipped') is not None for x in junit_rows)}
        except Exception as junit_exc:
            junit_error={'type':type(junit_exc).__name__,'message':str(junit_exc)}
        actual_duplicate_free=len(set(actual))==len(actual)
        expected_duplicate_free=len(set(expected))==len(expected)
        exact_order=actual==expected  # diagnostic only; native JUnit ordering is preserved, not graded
        exact_multiset=actual_duplicate_free and expected_duplicate_free and collections.Counter(actual)==collections.Counter(expected)
        source_after_capture=source_snapshot(source_paths)
        source_stable=before==source_after_capture
        write_json(RESULT/'pre-grade-custody.json',{'phase':'native_receipt_and_original_junit_before_existing_shared_grade','source_before_capture':before,'source_after_capture_before_grade':source_after_capture,'source_stable':source_stable,'expected_junit_identity_count':len(expected),'actual_junit_identity_count':len(actual),'junit_status_counts':junit_counts,'junit_inspection_error':junit_error,'junit_original_order_preserved':actual,'order_matches_ast_diagnostic_only':exact_order,'actual_identity_duplicate_free':actual_duplicate_free,'expected_identity_duplicate_free':expected_duplicate_free,'exact_duplicate_free_identity_multiset':exact_multiset,'canonical_sorted_identity_sha256':digest(canonical(sorted(expected))),'native_receipt':native_record,'carrier_invocation_exit':run.returncode,'typed_result_tree_after_capture':typed_tree(RESULT),'no_new_grade_authored':True})
        boundary='existing_shared_grade'
        source_before_grade=source_snapshot(source_paths); result_before_grade=typed_tree(RESULT)
        sys.path.insert(0,str(CARRIER)); sys.path.insert(0,str(CARRIER/'scripts/vidya'))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        grades=[]
        for row in native_rows(receipt_path):
            claim=project_ci_conformance(row); q,t,reasons=grade(claim)
            grades.append({'measurement_id':claim.measurement_id,'Q':q,'T':t,'reasons':reasons})
        source_after_grade=source_snapshot(source_paths); result_after_grade=typed_tree(RESULT)
        write_json(RESULT/'shared-grade-custody.json',{'phase':'existing_native_adapter_and_shared_claim_tuple_grade_only','source_before_capture':before,'source_before_grade':source_before_grade,'source_after_grade':source_after_grade,'source_stable':before==source_before_grade==source_after_grade,'typed_result_tree_before_shared_grade':result_before_grade,'typed_result_tree_after_shared_grade_before_this_record':result_after_grade,'result_tree_stable_across_shared_grade':result_before_grade==result_after_grade,'native_boolean_preserved_by_receipt':native_record.get('fixture_execution_conformant'),'projected_rows':len(grades),'grades':grades,'new_grade_authored':False,'native_null_projects_zero_rows':native_record.get('fixture_execution_conformant') is None and not grades})
        if not source_stable: raise RuntimeError('pinned source changed across native capture or grade')
        if junit_error is not None or not exact_multiset: raise RuntimeError('original JUnit absent, duplicated, or differs from the duplicate-free canonical case multiset; native value preserved')
        if run.returncode!=0 or native_record.get('fixture_execution_conformant') is not True: raise RuntimeError('carrier command or native receipt reports nonconformance; native value preserved')
        if junit_counts!={'collected':87,'passed':87,'failure':0,'error':0,'skipped':0}: raise RuntimeError('original JUnit did not report exactly 87 passed cases: '+repr(junit_counts))
        if not source_stable or before!=source_after_grade or result_before_grade!=result_after_grade: raise RuntimeError('source/result custody changed across capture or grade')
        for name,repo in [('APP',APP),('ROOT',ROOT),('CARRIER',CARRIER)]:
            if git(repo,'status','--porcelain','--untracked-files=all'): raise RuntimeError(name+' checkout changed during native capture or grade')
        status.update(state='captured',carrier_invocation_exit=run.returncode,junit_identity_count=len(actual),junit_exact_duplicate_free_multiset=True,junit_order_matches_manifest_diagnostic_only=exact_order,native_receipt_state='native_true',native_metric_value=True,projected_rows=len(grades),proposition_invented=False)
        return 0
    except Exception as exc:
        status.update(state='capture_error',failure_stage=boundary,error_type=type(exc).__name__,error_message=str(exc),proposition_invented=False)
        # Preserve the original native value, including None, if a receipt was made.
        if native_record is not None:
            status['native_metric_value']=native_record.get('fixture_execution_conformant')
            status['native_receipt_state']='native_true' if status['native_metric_value'] is True else 'native_false' if status['native_metric_value'] is False else 'native_null'
        try:
            write_json(RESULT/'error-custody.json',{'phase':boundary,'error_type':type(exc).__name__,'error_message':str(exc),'native_receipt':native_record,'source_snapshot':source_snapshot(source_paths) if source_paths else None,'typed_result_tree_before_error_record':typed_tree(RESULT),'proposition_invented':False,'status_and_self_excluded':True})
        except Exception: pass
        return 1
    finally:
        if RESULT.is_dir() and not RESULT.is_symlink() and (RESULT/'status.json').is_file() and not (RESULT/'status.json').is_symlink():
            tmp=RESULT/'status.json.tmp'; tmp.write_text(json.dumps(status,sort_keys=True)+'\n'); os.replace(tmp,RESULT/'status.json')

if __name__=='__main__': sys.exit(main())
