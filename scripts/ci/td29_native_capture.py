"""Private TD29 recipe draft. Hosted native run only after owner review and trigger."""
from __future__ import annotations
import ast, collections, hashlib, itertools, json, os, platform, stat, subprocess, sys, time, xml.etree.ElementTree as ET
from pathlib import Path

RECIPE=Path(__file__).resolve().parents[2]
RESULT=Path(os.environ['RUNNER_TEMP'])/'td29-native'/ 'result'
APP=Path(os.environ['GITHUB_WORKSPACE'])/'app'
ROOT=Path(os.environ['GITHUB_WORKSPACE'])/'recipe'
CARRIER=Path(os.environ['GITHUB_WORKSPACE'])/'carrier'
APP_PIN='130a394e38a5b0cf1b199e33c267070dc7087bd6'
ROOT_PIN='c986a107fde2c6e7cd6bd8e05ff7cf7243207034'
CARRIER_PIN='4c0c653baf1654c8c25c66433cf39c8faefd8e52'
TESTS=['tests/unit/test_llama_server.py','tests/unit/test_inference_mixin.py','tests/unit/test_typed_decisions_call_recorder.py']
RECIPE_DATA=RECIPE/'scripts/ci/td29_native'

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
def identity_payload(rows):
    interpreter_fields={'definition_ast_sha256','body_ast_sha256'}
    return [{key:value for key,value in row.items() if key not in interpreter_fields} for row in rows]
def verify_ast_manifest(manifest):
    definitions=[]; derived=[]
    for path in TESTS:
        source_record=manifest['test_file_source_records'][path]
        source_bytes=raw(APP/path)
        if len(source_bytes)!=source_record['bytes'] or digest(source_bytes)!=source_record['sha256']:
            raise RuntimeError('pinned test-module raw source bytes differ: '+path)
        tree_row=git(APP,'ls-tree','-r','-l',APP_PIN,'--',path)
        parts=tree_row.split('\t',1); meta=parts[0].split() if parts else []
        if len(parts)!=2 or parts[1]!=path or len(meta)!=4 or (meta[0],meta[1],meta[2],int(meta[3]))!=(source_record['mode'],'blob',source_record['blob'],source_record['bytes']):
            raise RuntimeError('pinned test-module Git mode/blob/size differs: '+path)
        # AST dump spelling changes across CPython minors; full raw bytes and Git blob pin source identity.
        # AST parsing below derives names/parameters only; version-specific AST digests are review metadata.
        parsed=ast.parse(source_bytes.decode('utf-8'),filename=path)
        module=path[:-3].replace('/','.')
        for top in parsed.body:
            if isinstance(top,ast.ClassDef): cls=top.name; sequence=top.body
            elif isinstance(top,(ast.FunctionDef,ast.AsyncFunctionDef)): cls=None; sequence=[top]
            else: continue
            for fn in sequence:
                if not isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)) or not fn.name.startswith('test_'): continue
                dims=[]
                for dec in reversed(fn.decorator_list):
                    if isinstance(dec,ast.Call) and ast.unparse(dec.func).endswith('parametrize'):
                        names=ast.literal_eval(dec.args[0]); names=[names] if isinstance(names,str) else list(names)
                        raw_values=ast.literal_eval(dec.args[1]); values=[[v] if len(names)==1 else list(v) for v in raw_values]
                        if any(len(row)!=len(names) for row in values): raise RuntimeError('parameter arity differs from static manifest')
                        dims.append({'names':names,'values':values})
                definition=((cls+'.') if cls else '')+fn.name
                row={'source_path':path,'definition':definition,'previous_function_sha256':next((old['previous_function_sha256'] for old in manifest['original_119_ast_definitions'] if old['source_path']==path and old['definition']==definition),None),'module':module,'class':cls,'function':fn.name,'param_dimensions':dims}
                definitions.append(row)
                products=itertools.product(*(dim['values'] for dim in dims)) if dims else [()]
                for product in products:
                    params={}; parts=[]
                    for dim,values in zip(dims,product):
                        for value in values:
                            if not isinstance(value,str): raise RuntimeError('this static ID rule is restricted to literal string parameters')
                        params.update(zip(dim['names'],values)); parts.extend(str(value) for value in values)
                    case={'classname':module+('.'+cls if cls else ''),'name':fn.name+('['+'-'.join(parts)+']' if dims else ''),'source_path':path,'definition':definition,'parameters':params,'previous_function_sha256':row['previous_function_sha256']}
                    derived.append(case)
    if len(definitions)!=119 or identity_payload(definitions)!=identity_payload(manifest['original_119_ast_definitions']):
        raise RuntimeError('AST definition inventory or portable test identities differ from pinned manifest')
    if len(derived)!=122 or identity_payload(derived)!=identity_payload(manifest['case_identities']):
        raise RuntimeError('literal AST parameter expansion differs from pinned canonical case identities')
    identity_pairs=[(row['classname'],row['name']) for row in derived]
    if len(set(identity_pairs))!=len(identity_pairs): raise RuntimeError('static case manifest contains duplicate identities')
    for nodeid in manifest['required_legacy_nodeids']:
        source_path,tail=nodeid.split('::',1); expected_path=source_path[:-3].replace('/','.')
        cls_name,fn_name=tail.rsplit('::',1) if '::' in tail else ('',tail)
        classname=expected_path+('.'+cls_name if cls_name else '')
        if (classname,fn_name) not in identity_pairs: raise RuntimeError('legacy source-control identity missing from canonical manifest: '+nodeid)
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
        if cm['ast_test_definition_count']!=119 or cm['ast_derived_expected_junit_case_count']!=122 or len(cm['case_identities'])!=122: raise RuntimeError('static identity proposal malformed')
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
                if len(data)!=row['bytes'] or digest(data)!=row['sha256']: raise RuntimeError('APP source envelope mismatch: '+row['path'])
                source_paths.append(p)
        for group,repo in [('root_context',ROOT),('native_carrier',CARRIER)]:
            for row in sm[group]['files']:
                p=repo/row['path']; data=raw(p)
                if len(data)!=row['bytes'] or digest(data)!=row['sha256'] or git(repo,'rev-parse','HEAD:'+row['path'])!=row['blob']: raise RuntimeError(group+' source pin mismatch: '+row['path'])
                if group=='root_context' and git(ROOT,'rev-parse',ROOT_PIN+':'+row['path'])!=row['blob']: raise RuntimeError('historical enrolled ROOT blob differs: '+row['path'])
                source_paths.append(p)
        source_paths += [RECIPE/'scripts/ci/td29_native_capture.py',RECIPE_DATA/'source-map.json',RECIPE_DATA/'expected-cases.json',RECIPE_DATA/'requirements-linux-py311.txt']
        source_paths=list(dict.fromkeys(source_paths))
        before=source_snapshot(source_paths)
        boundary='original_native_execution'
        junit=RESULT/'original-junit.xml'; native_out=RESULT/'native'
        test_command=[sys.executable,'-m','pytest','-c','pyproject.toml','-o','addopts=','-p','no:cacheprovider','-p','asyncio','-q','--junitxml='+str(junit),*TESTS]
        env=dict(os.environ); env.update({'PYTHONPATH':str(APP),'CI':'true','ORCHESTRATOR_MOCK_MODE':'1','ORCHESTRATOR_PATHS_LLAMA_CPP_BIN':os.environ['ORCHESTRATOR_PATHS_LLAMA_CPP_BIN'],'ORCHESTRATOR_PATHS_LLAMA_MTMD':os.environ['ORCHESTRATOR_PATHS_LLAMA_MTMD'],'ORCHESTRATOR_PATHS_LLAMA_SERVER':os.environ['ORCHESTRATOR_PATHS_LLAMA_SERVER'],'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTEST_ADDOPTS':'','PYTEST_PLUGINS':'','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','PYTHONNOUSERSITE':'1','PYTHONUNBUFFERED':'1'})
        kernel_fixtures={}
        fixture_suffixes={'ORCHESTRATOR_PATHS_LLAMA_CPP_BIN': 'empty-kernel-bin', 'ORCHESTRATOR_PATHS_LLAMA_MTMD': 'empty-llama-mtmd-path', 'ORCHESTRATOR_PATHS_LLAMA_SERVER': 'empty-llama-server-path'}
        for key,suffix in fixture_suffixes.items():
            kernel_path=Path(env[key]);kernel_stat=kernel_path.lstat()
            if kernel_path!=(Path(os.environ['RUNNER_TEMP'])/'td29-native'/suffix) or kernel_path.is_symlink() or not stat.S_ISDIR(kernel_stat.st_mode) or kernel_stat.st_uid!=os.geteuid() or stat.S_IMODE(kernel_stat.st_mode)!=0o700 or next(kernel_path.iterdir(),None) is not None:
                raise RuntimeError('external-kernel fixture '+key+' is not the owned, empty mode-0700 runner-temp directory')
            kernel_fixtures[key]={'path':str(kernel_path),'purpose':'empty runner-temp fixture avoids external kernel default during mocked controls; no binary/model/server','checked_before_pytest':True,'empty':True,'owner_uid':kernel_stat.st_uid,'owner_gid':kernel_stat.st_gid,'mode':format(stat.S_IMODE(kernel_stat.st_mode),'04o'),'device':kernel_stat.st_dev,'inode':kernel_stat.st_ino}
        carrier_argv=[sys.executable,str(CARRIER/'scripts/ci/native_conformance.py'),'--cwd',str(APP),'--junit',str(junit),'--output',str(native_out),'--repo','app='+str(APP),'--repo','root_recipe='+str(ROOT),'--repo','carrier='+str(CARRIER)]
        for p in source_paths: carrier_argv += ['--read-path',str(p)]
        for test in TESTS: carrier_argv += ['--select',test]
        carrier_argv += ['--',*test_command]
        request={'carrier_argv':carrier_argv,'pytest_argv':test_command,'cwd':str(APP),'env_controls':{k:env[k] for k in ('CI','ORCHESTRATOR_MOCK_MODE','ORCHESTRATOR_PATHS_LLAMA_CPP_BIN','ORCHESTRATOR_PATHS_LLAMA_MTMD','ORCHESTRATOR_PATHS_LLAMA_SERVER','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTEST_ADDOPTS','PYTEST_PLUGINS','PYTHONDONTWRITEBYTECODE','PYTHONHASHSEED','PYTHONNOUSERSITE')},'kernel_path_fixtures':kernel_fixtures,'selection':TESTS,'source_before_capture':before,'repositories':{'app':APP_PIN,'root_recipe_event':os.environ.get('GITHUB_SHA'),'enrolled_root_context':ROOT_PIN,'carrier':CARRIER_PIN},'ast_definition_count':119,'proposed_junit_identities':122,'native_case_count_claim':None}
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
        if junit_counts!={'collected':122,'passed':122,'failure':0,'error':0,'skipped':0}: raise RuntimeError('original JUnit did not report exactly 122 passed cases: '+repr(junit_counts))
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
