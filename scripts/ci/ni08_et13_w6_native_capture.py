"""Capture bounded native outcomes for the complete ET13/W6 related test modules."""
from __future__ import annotations
import ast, hashlib, importlib.metadata, importlib.util, json, os, platform, re, stat, subprocess, sys, tomllib
from pathlib import Path
import xml.etree.ElementTree as ET

W6_PIN = "ce48ed2c386c2f69d23ad87289e384d7942ee7a5"
BASE_PIN = W6_PIN  # fresh candidate source remains descended from the reviewed W6 base
SOURCE_PIN = "14a2c3a1469cd44a7f7a9017c7f3a44c361b1464"
ROOT_PIN = "72a0d06a251667fe6dc1cdf05ab19313e03f9736"
ROOT_CONTEXT_FILES = ["scripts/ci/native_conformance.py", "scripts/vidya/adapters/__init__.py", "scripts/vidya/adapters/ci_conformance.py", "scripts/vidya/claim_tuple.py", "scripts/vidya/ingest_sources.py", "scripts/vidya/adapters/README.md", "handoffs/active/vidya-belief-substrate-program.md", "tests/vidya/test_ci_conformance.py", "scripts/vidya/lattice.py", "scripts/vidya/frames.py", "scripts/vidya/canonical.py", "handoffs/active/eval-tower-architecture-audit-2026-07-20.md"]
PY_PIN = "3.13.15"
REQUIREMENT_SEEDS = ["httpx", "jsonschema", "math-verify", "pydantic", "pydantic-settings", "pytest", "pyyaml"]
ENV = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1", "PYTHONDONTWRITEBYTECODE":"1", "PYTHONHASHSEED":"0",
       "PYTHONUNBUFFERED":"1", "PYTEST_ADDOPTS":"", "PYTEST_PLUGINS":"", "ORCHESTRATOR_MOCK_MODE":"1",
       "ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS":"1"}

def sha_info(p: Path):
    absolute=os.path.abspath(os.fspath(p))
    parts=Path(absolute).parts[1:]
    if not parts: raise RuntimeError(f"not a regular-file path: {p}")
    parent_parts=parts[:-1]; leaf=parts[-1]
    dirs=[os.open(os.sep,os.O_RDONLY|os.O_DIRECTORY)]
    try:
        for component in parent_parts:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dirs[-1])
            opened=os.fstat(child); named=os.stat(component,dir_fd=dirs[-1],follow_symlinks=False)
            if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(named.st_dev,named.st_ino):
                os.close(child); raise RuntimeError(f"parent path rebound while hashing: {p}")
            dirs.append(child)
        fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dirs[-1])
        try:
            a=os.fstat(fd)
            if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1: raise RuntimeError(f"not a single-link regular file: {p}")
            h=hashlib.sha256()
            for b in iter(lambda:os.read(fd,1<<20),b''): h.update(b)
            z=os.fstat(fd); named=os.stat(leaf,dir_fd=dirs[-1],follow_symlinks=False)
            if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns): raise RuntimeError(f"changed while hashing: {p}")
            if (z.st_dev,z.st_ino,z.st_size)!=(named.st_dev,named.st_ino,named.st_size): raise RuntimeError(f"path rebound while hashing: {p}")
            for i,component in enumerate(parent_parts):
                opened=os.fstat(dirs[i+1]); named_parent=os.stat(component,dir_fd=dirs[i],follow_symlinks=False)
                if (opened.st_dev,opened.st_ino)!=(named_parent.st_dev,named_parent.st_ino): raise RuntimeError(f"parent path rebound while hashing: {p}")
            return h.hexdigest(),z.st_size
        finally: os.close(fd)
    finally:
        for directory_fd in reversed(dirs): os.close(directory_fd)

def sha(p: Path) -> str:
    return sha_info(p)[0]

def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def snapshot(root:Path):
    absolute=os.path.abspath(os.fspath(root)); parts=Path(absolute).parts[1:]
    dirs=[os.open(os.sep,os.O_RDONLY|os.O_DIRECTORY)]
    out={'.':'directory'}
    try:
        for component in parts:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dirs[-1])
            opened=os.fstat(child); named=os.stat(component,dir_fd=dirs[-1],follow_symlinks=False)
            if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(named.st_dev,named.st_ino):
                os.close(child); raise RuntimeError(f"snapshot parent path rebound: {root}")
            dirs.append(child)
        def walk(directory_fd,prefix):
            start=os.fstat(directory_fd)
            names=sorted(os.listdir(directory_fd))
            for name in names:
                rel=f'{prefix}/{name}' if prefix else name
                if not prefix and name=='run-root-inventory.json':
                    continue
                info=os.stat(name,dir_fd=directory_fd,follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    target=os.readlink(name,dir_fd=directory_fd)
                    check=os.stat(name,dir_fd=directory_fd,follow_symlinks=False)
                    if (info.st_dev,info.st_ino)!=(check.st_dev,check.st_ino): raise RuntimeError(f"snapshot symlink rebound: {rel}")
                    out[rel]='symlink:'+target
                elif stat.S_ISDIR(info.st_mode):
                    child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory_fd)
                    try:
                        opened=os.fstat(child)
                        if (info.st_dev,info.st_ino)!=(opened.st_dev,opened.st_ino): raise RuntimeError(f"snapshot directory rebound: {rel}")
                        out[rel+'/']='directory'; walk(child,rel)
                        check=os.stat(name,dir_fd=directory_fd,follow_symlinks=False)
                        if (opened.st_dev,opened.st_ino)!=(check.st_dev,check.st_ino): raise RuntimeError(f"snapshot directory rebound: {rel}")
                    finally: os.close(child)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink==1:
                    out[rel]=_sha_at(directory_fd,name,rel)
                else: raise RuntimeError(f'unsupported result object: {rel}')
            end=os.fstat(directory_fd)
            if (start.st_dev,start.st_ino,start.st_mtime_ns,start.st_ctime_ns)!=(end.st_dev,end.st_ino,end.st_mtime_ns,end.st_ctime_ns):
                raise RuntimeError(f"snapshot directory changed during inventory: {prefix or '.'}")
        walk(dirs[-1],'')
        for i,component in enumerate(parts):
            opened=os.fstat(dirs[i+1]); named=os.stat(component,dir_fd=dirs[i],follow_symlinks=False)
            if (opened.st_dev,opened.st_ino)!=(named.st_dev,named.st_ino): raise RuntimeError(f"snapshot parent path rebound: {root}")
    finally:
        for directory_fd in reversed(dirs): os.close(directory_fd)
    return dict(sorted(out.items()))

def _sha_at(parent_fd,name,label):
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent_fd)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1: raise RuntimeError(f"not a single-link regular file: {label}")
        digest=hashlib.sha256()
        for block in iter(lambda:os.read(fd,1<<20),b''): digest.update(block)
        after=os.fstat(fd); named=os.stat(name,dir_fd=parent_fd,follow_symlinks=False)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns): raise RuntimeError(f"changed while hashing: {label}")
        if (after.st_dev,after.st_ino,after.st_size)!=(named.st_dev,named.st_ino,named.st_size): raise RuntimeError(f"path rebound while hashing: {label}")
        return digest.hexdigest()
    finally: os.close(fd)

def read_regular_bytes(p: Path) -> bytes:
    absolute=os.path.abspath(os.fspath(p)); parts=Path(absolute).parts[1:]
    if not parts: raise RuntimeError(f"not a regular-file path: {p}")
    parent_parts=parts[:-1]; leaf=parts[-1]; dirs=[os.open(os.sep,os.O_RDONLY|os.O_DIRECTORY)]
    try:
        for component in parent_parts:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dirs[-1])
            opened=os.fstat(child); named=os.stat(component,dir_fd=dirs[-1],follow_symlinks=False)
            if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(named.st_dev,named.st_ino):
                os.close(child); raise RuntimeError(f"parent path rebound while reading: {p}")
            dirs.append(child)
        fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dirs[-1])
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1: raise RuntimeError(f"not a single-link regular file: {p}")
            chunks=[]
            for block in iter(lambda:os.read(fd,1<<20),b''): chunks.append(block)
            after=os.fstat(fd); named=os.stat(leaf,dir_fd=dirs[-1],follow_symlinks=False)
            if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns): raise RuntimeError(f"changed while reading: {p}")
            if (after.st_dev,after.st_ino,after.st_size)!=(named.st_dev,named.st_ino,named.st_size): raise RuntimeError(f"path rebound while reading: {p}")
            for i,component in enumerate(parent_parts):
                opened=os.fstat(dirs[i+1]); named_parent=os.stat(component,dir_fd=dirs[i],follow_symlinks=False)
                if (opened.st_dev,opened.st_ino)!=(named_parent.st_dev,named_parent.st_ino): raise RuntimeError(f"parent path rebound while reading: {p}")
            return b''.join(chunks)
        finally: os.close(fd)
    finally:
        for directory_fd in reversed(dirs): os.close(directory_fd)

def tracked(repo,rel):
    p=repo/rel; info=p.lstat(); ent=git(repo,'ls-tree','HEAD','--',rel).split()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or len(ent)<3 or ent[1]!='blob' or ent[0] not in ('100644','100755'): raise RuntimeError(f'untracked/nonregular input {rel}')
    return p,ent[0],ent[2]
def _marker(node, env):
    if isinstance(node,ast.Expression): return _marker(node.body,env)
    if isinstance(node,ast.Name): return env[node.id]
    if isinstance(node,ast.Constant): return node.value
    if isinstance(node,ast.BoolOp): return all(_marker(x,env) for x in node.values) if isinstance(node.op,ast.And) else any(_marker(x,env) for x in node.values)
    if isinstance(node,ast.Compare):
        left=_marker(node.left,env)
        for op,right_node in zip(node.ops,node.comparators):
            right=_marker(right_node,env)
            ok=(left==right if isinstance(op,ast.Eq) else left!=right if isinstance(op,ast.NotEq) else left<right if isinstance(op,ast.Lt) else left<=right if isinstance(op,ast.LtE) else left>right if isinstance(op,ast.Gt) else left>=right if isinstance(op,ast.GtE) else False)
            if not ok:return False
            left=right
        return True
    raise RuntimeError('unsupported marker grammar')
def closure(lock, seeds):
    packages={x['name'].lower().replace('_','-'):x for x in lock['package']}
    env={'implementation_name':'cpython','platform_python_implementation':'CPython','platform_machine':'x86_64','sys_platform':'linux','python_full_version':'3.13.15','python_version':'3.13'}
    start=[x.lower().replace('_','-') for x in seeds]
    seen=set(); todo=list(start)
    while todo:
        n=todo.pop()
        if n in seen: continue
        if n not in packages: raise RuntimeError('lock missing dependency '+n)
        seen.add(n)
        for d in packages[n].get('dependencies',[]):
            if isinstance(d,str): todo.append(re.split(r'[<>=!~; ]',d,1)[0].lower().replace('_','-'))
            elif isinstance(d,dict) and d.get('name') and (not d.get('marker') or _marker(ast.parse(d['marker'],mode='eval'),env)):
                todo.append(d['name'].lower().replace('_','-'))
    return packages,seen

def parse_pinned_requirements(text):
    packages={}; current=None; inside_hash_block=False
    for number,line in enumerate(text.splitlines(),1):
        if not line or line.startswith('#'):
            if inside_hash_block: raise RuntimeError(f'incomplete continued requirement before line {number}')
            continue
        if inside_hash_block:
            continued=line.endswith(' \\')
            body=line[:-2] if continued else line
            match=re.fullmatch(r'    --hash=sha256:([0-9a-f]{64})',body)
            if not match: raise RuntimeError(f'malformed locked hash line {number}')
            if match.group(1) in packages[current]['hashes']: raise RuntimeError(f'duplicate wheel hash on line {number}')
            packages[current]['hashes'].add(match.group(1))
            inside_hash_block=continued
            if not continued: current=None
            continue
        continued=line.endswith(' \\')
        body=line[:-2] if continued else line
        match=re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s]+)',body)
        if not match or not continued: raise RuntimeError(f'malformed or unterminated package header on line {number}')
        current=match.group(1).lower().replace('_','-')
        if current in packages: raise RuntimeError(f'duplicate locked package requirement {current}')
        packages[current]={'version':match.group(2),'hashes':set()}
        inside_hash_block=True
    if inside_hash_block or current is not None: raise RuntimeError('unterminated exact package/hash list')
    if any(not value['hashes'] for value in packages.values()): raise RuntimeError('locked package has no wheel hashes')
    return packages

def main():
    app=Path(os.environ['GITHUB_WORKSPACE'])/'app'; carrier=Path(os.environ['GITHUB_WORKSPACE'])/'carrier'
    result=Path(os.environ['RUNNER_TEMP'])/'ni08-et13-w6'/'result'; status_path=result/'status.json'
    status={'state':'preparing','fixture_execution_conformant':None,'native_outcome_kind':'not_captured','shared_grade_state':'not_started','promotion_or_release_acceptance':None}
    receipt=None; stage='setup'; before_capture=None; after_capture=None; before_grade=None; after_grade=None
    inputs=[]; root_inputs=[]; case_count=None; source_manifest_sha256=None; app_commit=None; carrier_commit=None
    capture_started=False; grade_started=False; inventory=None
    status_path.write_text(json.dumps(status,sort_keys=True)+'\n')
    try:
        if platform.python_version()!=PY_PIN or sys.platform!='linux' or platform.machine()!='x86_64' or sys.prefix==sys.base_prefix: raise RuntimeError('runner/Python/venv differs from declared hosted context')
        for k,v in ENV.items():
            if os.environ.get(k)!=v: raise RuntimeError('environment mismatch '+k)
        if any(k in os.environ for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','PYTHONPATH')): raise RuntimeError('ambient loader/Python path is present')
        if os.environ.get('EPYC_ORCH_ROOT')!=str(app) or os.environ.get('VIDYA_ORCH_WRITER_ROOT')!=str(app): raise RuntimeError('writer root is not the reviewed APP checkout')
        absent=[os.environ.get(k,'') for k in ('ORCHESTRATOR_PATHS_LLAMA_CPP_BIN','ORCHESTRATOR_PATHS_LLAMA_MTMD','ORCHESTRATOR_PATHS_LLAMA_SERVER')]
        if not all(x.startswith('/absent/') and not Path(x).exists() for x in absent): raise RuntimeError('serving binaries are not absent')
        llm=Path(os.environ.get('ORCHESTRATOR_PATHS_LLM_ROOT',''))
        if not llm.is_dir() or any(llm.iterdir()): raise RuntimeError('isolated model directory is not empty')
        if os.environ.get('GITHUB_REF')!='refs/heads/codex/ni08-et13-w6-ci-20261007' or os.environ.get('GITHUB_EVENT_NAME')!='push': raise RuntimeError('unexpected workflow event/ref')
        if os.environ.get('ROOT_CARRIER_PIN')!=ROOT_PIN: raise RuntimeError('ROOT context environment pin mismatch')
        if git(app,'status','--porcelain','--untracked-files=all') or git(carrier,'status','--porcelain','--untracked-files=all'): raise RuntimeError('checkout is not clean, including untracked files')
        if git(carrier,'rev-parse','HEAD')!=ROOT_PIN: raise RuntimeError('native carrier pin mismatch')
        if git(app,'rev-parse','HEAD')!=os.environ.get('GITHUB_SHA'): raise RuntimeError('APP checkout differs from triggering source SHA')
        cases_p,_,_=tracked(app,'scripts/ci/ni08_et13_w6_native_cases.json'); cases=json.loads(cases_p.read_text())
        case_count=cases.get('case_count')
        if cases.get('base_commit')!=BASE_PIN or cases.get('w6_commit')!=W6_PIN or cases.get('source_commit')!=SOURCE_PIN or len(cases['cases'])!=case_count: raise RuntimeError('case/source manifest pin/count mismatch')
        if cases.get('root_carrier')!=ROOT_PIN or cases.get('root_context_files')!=ROOT_CONTEXT_FILES: raise RuntimeError('ROOT context identity mismatch')
        binding=cases.get('prospective_source_binding',{})
        if binding.get('vidya_task')!='VB-ET13-ROUTING-CONFORMANCE' or binding.get('parent_task')!='ET-13 honest routing buckets (E5 remaining LOWs sweep), handoffs/active/eval-tower-architecture-audit-2026-07-20.md': raise RuntimeError('ET13 owning task binding mismatch')
        if binding.get('current_table_row_status')!='actual ET13 task/source row is published and bound in the exact ROOT context; carrier registry remains the existing ci-fixture-conformance source': raise RuntimeError('ET13 prospective source-table approval gate missing')
        if git(app,'rev-parse',BASE_PIN+'^{tree}')!=cases.get('base_tree') or subprocess.run(['git','-C',str(app),'merge-base','--is-ancestor',BASE_PIN,'HEAD']).returncode!=0: raise RuntimeError('tested APP is not descended from exact reviewed W6 source')
        if git(app,'rev-parse',SOURCE_PIN+'^{tree}')!=cases.get('source_tree') or subprocess.run(['git','-C',str(app),'merge-base','--is-ancestor',SOURCE_PIN,'HEAD']).returncode!=0: raise RuntimeError('tested APP is not descended from exact reviewed ET13 source')
        inputs=[]
        declared=['.github/workflows/ni08-et13-w6-native.yml','scripts/ci/ni08_et13_w6_native_capture.py','scripts/ci/ni08_et13_w6_native_cases.json','scripts/ci/ni08_et13_w6_native_requirements.txt','pyproject.toml','uv.lock']
        for rel in declared:
            p,mode,oid=tracked(app,rel); digest,size=sha_info(p); inputs.append({'repo':'app','path':rel,'mode':mode,'blob':oid,'sha256':digest,'size_bytes':size})
        root_inputs=[]
        expected_root={row['path']:row for row in cases.get('root_context',[])}
        if set(expected_root)!=set(ROOT_CONTEXT_FILES): raise RuntimeError('ROOT source closure is incomplete')
        for rel in ROOT_CONTEXT_FILES:
            p,mode,oid=tracked(carrier,rel); digest,size=sha_info(p); row={'repo':'root','path':rel,'mode':mode,'blob':oid,'sha256':digest,'size_bytes':size}; pin=expected_root[rel]
            if mode!=pin['git_mode'] or oid!=pin['git_blob'] or row['sha256']!=pin['sha256'] or row['size_bytes']!=pin['size_bytes']: raise RuntimeError('ROOT bound source mismatch '+rel)
            root_inputs.append(row); inputs.append(row)
        for row in cases['bound_files']:
            p,mode,oid=tracked(app,row['path'])
            digest,size=sha_info(p)
            if mode!=row['git_mode'] or oid!=row['git_blob'] or digest!=row['sha256'] or size!=row['size_bytes']: raise RuntimeError('bound source/data mismatch '+row['path'])
            inputs.append({'repo':'app','path':row['path'],'mode':mode,'blob':oid,'sha256':digest,'size_bytes':size})
        lock=tomllib.loads((app/'uv.lock').read_text()); pkgs,names=closure(lock,REQUIREMENT_SEEDS)
        req=(app/'scripts/ci/ni08_et13_w6_native_requirements.txt').read_text()
        got=parse_pinned_requirements(req)
        if len(got)!=len(names) or set(got)!=names: raise RuntimeError('requirement package set differs from exact uv.lock closure')
        for n in names:
            pkg=pkgs[n]; expected={h['hash'].split(':',1)[1] for h in pkg.get('wheels',[]) if h.get('hash','').startswith('sha256:')}
            if not expected or got[n]['version']!=pkg['version'] or got[n]['hashes']!=expected: raise RuntimeError('version or full wheel-hash set mismatch '+n)
            try: installed=importlib.metadata.version(pkg['name'])
            except importlib.metadata.PackageNotFoundError: raise RuntimeError('locked package missing '+n)
            if installed!=pkg['version']: raise RuntimeError('installed version mismatch '+n)
        manifest=result/'source-manifest.json'
        manifest.write_text(json.dumps({'schema':'epyc.ni08.et13_w6.source_manifest.v1','base_commit':BASE_PIN,'source_commit':SOURCE_PIN,'app_combined_sha':git(app,'rev-parse','HEAD'),'app_tree':git(app,'rev-parse','HEAD^{tree}'),'root_carrier':ROOT_PIN,'root_context_files':root_inputs,'uv_lock_blob':git(app,'ls-tree','HEAD','uv.lock').split()[2],'test_modules':cases['whole_test_modules'],'case_count':case_count,'bound_inputs':inputs,'runtime_data':cases['runtime_data'],'native_outcome_acceptance':None},sort_keys=True,indent=2)+'\n')
        pre_status=result/'pre-status.json'
        pre_status.write_text(json.dumps({'state':'setup_complete','fixture_execution_conformant':None,'promotion_or_release_acceptance':None},sort_keys=True)+'\n')
        environment=result/'environment.json'
        environment.write_text(json.dumps({'python_version':platform.python_version(),'python_executable':sys.executable,'venv_prefix':sys.prefix,'base_prefix':sys.base_prefix,'platform':platform.platform(),'arch':platform.machine(),'python_pin':PY_PIN,'workflow_ref':os.environ['GITHUB_REF'],'event':os.environ['GITHUB_EVENT_NAME'],'launch_mode':'env-i','path':os.environ.get('PATH'),'home':os.environ.get('HOME'),'tmpdir':os.environ.get('TMPDIR'),'inherited_pythonpath':False,'loader_environment_absent':True,'plugin_autoload':'disabled','environment':ENV,'decision_acceptance':None},sort_keys=True,indent=2)+'\n')
        context=[app/'scripts/ci/ni08_et13_w6_native_requirements.txt',app/'uv.lock',manifest,app/'scripts/ci/ni08_et13_w6_native_cases.json',app/'.github/workflows/ni08-et13-w6-native.yml',app/'scripts/ci/ni08_et13_w6_native_capture.py',pre_status,environment,result/'pip-install.log',result/'pip-freeze.txt']
        for row in cases['bound_files']: context.append(app/row['path'])
        for rel in ROOT_CONTEXT_FILES: context.append(carrier/rel)
        for p in (result/'status.json',result/'pip-install.log',result/'pip-freeze.txt',manifest,pre_status,environment): sha(p)
        input_custody={'schema':'epyc.ni08_et13_w6.input_custody.v1','state':'pre_capture','app_commit':git(app,'rev-parse','HEAD'),'carrier_commit':git(carrier,'rev-parse','HEAD'),'source_manifest_sha256':sha(manifest),'declared_input_count':len(inputs),'declared_inputs':inputs,'result_files_before_capture':snapshot(result),'native_outcome_kind':'not_captured','fixture_execution_conformant':None,'shared_grade_state':'not_started','journal_record_grade':'not_in_scope','promotion_or_release_acceptance':None}
        custody_path=result/'input-custody.json'
        custody_path.write_text(json.dumps(input_custody,sort_keys=True,indent=2)+'\n')
        context.append(custody_path)
        app_commit=git(app,'rev-parse','HEAD'); carrier_commit=git(carrier,'rev-parse','HEAD'); source_manifest_sha256=sha(manifest)
        before_capture=snapshot(result)
        spec=importlib.util.spec_from_file_location('pinned_native_conformance',carrier/'scripts/ci/native_conformance.py'); api=importlib.util.module_from_spec(spec); sys.modules[spec.name]=api; spec.loader.exec_module(api)
        selections=[x['nodeid'] for x in cases['cases']]
        junit=result/'original-junit.xml'; temp=result/'pytest-tmp'; temp.mkdir()
        argv=[sys.executable,'-m','pytest','-c','/dev/null','--noconftest','--rootdir',str(app),'--import-mode=importlib','-p','no:cacheprovider','-o','addopts=','-q',*cases['whole_test_modules'],f'--basetemp={temp}',f'--junitxml={junit}']
        os.environ['PYTHONPATH']=str(app)
        stage='outer_native_capture'
        status.update(state='running',case_count=case_count,fixture_execution_conformant=None,native_outcome_kind='not_captured',shared_grade_state='not_started'); status_path.write_text(json.dumps(status,sort_keys=True)+'\n')
        capture_started=True
        receipt=api.capture_fixture_execution(argv=argv,cwd=app,junit=junit,output=result/'native',repositories={'app':app,'carrier':carrier},read_paths=context,selections=selections)
        stage='native_outcome_custody'
        after_capture=snapshot(result)
        if git(app,'status','--porcelain','--untracked-files=all') or git(carrier,'status','--porcelain','--untracked-files=all'): raise RuntimeError('APP or ROOT checkout changed during selected-module capture')
        if not isinstance(receipt,dict): raise RuntimeError('native capture returned no typed receipt object')
        outcome=receipt.get('fixture_execution_conformant')
        if outcome is not None and type(outcome) is not bool: raise RuntimeError('outer conformance result is not TRUE/FALSE/NULL')
        outcome_kind='true' if outcome is True else 'false' if outcome is False else 'null'
        native_receipt=result/'native'/'receipt.json'
        receipt_present=os.path.lexists(native_receipt)
        receipt_sha256=sha(native_receipt) if receipt_present else None
        junit_path=result/'native'/'original-junit.xml'; junit_present=os.path.lexists(junit_path)
        actual=None
        if junit_present:
            jr=ET.fromstring(read_regular_bytes(junit_path))
            actual={(x.get('classname',''),x.get('name','')) for x in jr.iter('testcase')}
        summary=receipt.get('summary')
        if summary is not None and not isinstance(summary,dict): raise RuntimeError('native receipt summary is not a mapping or NULL')
        counts=None if summary is None else summary.get('counts')
        if counts is not None and not isinstance(counts,dict): raise RuntimeError('native receipt summary counts are not a mapping or NULL')
        counts=counts or {}
        expected={(x['classname'],x['name']) for x in cases['cases']}
        exact_case_set=None if actual is None else actual==expected and len(actual)==case_count and counts.get('collected')==case_count
        junit_all_passed=None if not counts else counts.get('executed')==case_count and counts.get('passed')==case_count and counts.get('skipped')==0 and counts.get('failure')==0 and counts.get('error')==0
        all_passed=None if outcome is None or exact_case_set is None or junit_all_passed is None else exact_case_set and junit_all_passed
        inventory={'schema':'epyc.ni08_et13_w6.run_root_inventory.v2','before_capture':before_capture,'after_capture':after_capture,'before_shared_grade':None,'after_shared_grade':None,'after_error':None,'after_error_inventory_error':None,'inventory_self_excluded_from_snapshots':True,'native_receipt_present':receipt_present,'native_receipt_sha256':receipt_sha256,'junit_present':junit_present,'shared_grade_applicable':outcome is not None and exact_case_set is True and receipt_present,'selected_case_count':case_count,'junit_counts':counts,'original_outcome':outcome,'native_outcome_kind':outcome_kind,'exact_case_set':exact_case_set,'junit_all_passed':junit_all_passed,'all_passed':all_passed,'promotion_or_release_acceptance':None}
        (result/'run-root-inventory.json').write_text(json.dumps(inventory,sort_keys=True,indent=2)+'\n')
        grade_source_hashes={row['path']:row['sha256'] for row in root_inputs}
        hashes_before_grade={row['path']:sha(carrier/row['path']) for row in root_inputs}
        if hashes_before_grade!=grade_source_hashes: raise RuntimeError('ROOT grader/readset changed after capture and before shared grading')
        grade_request_state='declined_null' if outcome is None else 'pending' if receipt_present and exact_case_set is True else 'not_started'
        pregrade={'schema':'epyc.ni08_et13_w6.shared_grade_request.v2','outer_receipt_path':'native/receipt.json' if receipt_present else None,'outer_receipt_sha256':receipt_sha256,'outer_receipt_present':receipt_present,'outer_outcome_kind':outcome_kind,'fixture_execution_conformant':outcome,'selected_case_count':case_count,'junit_present':junit_present,'junit_counts':counts,'exact_case_set':exact_case_set,'all_passed':all_passed,'root_carrier':ROOT_PIN,'source_manifest_sha256':source_manifest_sha256,'declared_input_count':len(inputs),'declared_input_hashes':inputs,'grader_source_hashes':grade_source_hashes,'verified_source_hashes_before_grade':hashes_before_grade,'result_files_before_grade':snapshot(result),'adapter_id':'vidya.adapters.ci_conformance/v1','registry_source':'ci-fixture-conformance','registry_task':'VB-CI-CONFORMANCE','shared_grade_state':grade_request_state,'journal_record_grade':'not_in_scope','promotion_or_release_acceptance':None}
        pregrade_path=result/'pregrade-custody.json'
        pregrade_path.write_text(json.dumps(pregrade,sort_keys=True,indent=2)+'\n')
        before_grade=snapshot(result); inventory['before_shared_grade']=before_grade
        (result/'run-root-inventory.json').write_text(json.dumps(inventory,sort_keys=True,indent=2)+'\n')
        grade_result={'state':'declined_null','native_outcome_kind':outcome_kind,'fixture_execution_conformant':outcome,'reason':'existing ci_conformance.native_rows emits no tuple for a NULL proposition','journal_record_grade':'not_in_scope','promotion_or_release_acceptance':None}
        if outcome is not None and not receipt_present:
            grade_result={'state':'not_graded_receipt_missing','native_outcome_kind':outcome_kind,'fixture_execution_conformant':outcome,'reason':'native receipt artifact is absent; no tuple projected','journal_record_grade':'not_in_scope','promotion_or_release_acceptance':None}
        elif outcome is not None and exact_case_set is not True:
            grade_result={'state':'not_graded_case_set_mismatch','native_outcome_kind':outcome_kind,'fixture_execution_conformant':outcome,'reason':'outer receipt did not contain the exact 140 selected case identities','journal_record_grade':'not_in_scope','promotion_or_release_acceptance':None}
        if outcome is not None and receipt_present and exact_case_set is True:
            stage='shared_ci_conformance_projection'
            grade_started=True
            sys.path.insert(0,str(carrier)); sys.path.insert(0,str(carrier/'scripts'/'vidya'))
            import scripts.vidya.ingest_sources as registry_module
            from claim_tuple import grade as shared_grade
            import claim_tuple as claim_tuple_module
            if Path(registry_module.__file__).resolve()!=(carrier/'scripts/vidya/ingest_sources.py').resolve(): raise RuntimeError('ROOT source registry import escaped pinned carrier')
            source=registry_module.SOURCES.get('ci-fixture-conformance')
            if source is None or source.task!='VB-CI-CONFORMANCE' or source.module!='ci_conformance' or source.natives!='native_rows' or source.project!='project_ci_conformance': raise RuntimeError('ROOT CI-conformance registry row differs from the bound VB source')
            if binding['current_carrier_row']!={'name':source.name,'module':source.module,'natives':source.natives,'project':source.project,'task':source.task}: raise RuntimeError('actual ROOT carrier row differs from prebound source-table context')
            adapter=source.load()
            native_reader=getattr(adapter,source.natives); projector=getattr(adapter,source.project)
            if Path(adapter.__file__).resolve()!=(carrier/'scripts/vidya/adapters/ci_conformance.py').resolve() or Path(claim_tuple_module.__file__).resolve()!=(carrier/'scripts/vidya/claim_tuple.py').resolve(): raise RuntimeError('shared grader import escaped pinned ROOT carrier')
            if shared_grade is not claim_tuple_module.grade: raise RuntimeError('grader function identity mismatch')
            rows=native_reader(native_receipt)
            if len(rows)!=1: raise RuntimeError('TRUE/FALSE outer receipt did not yield exactly one existing ci_conformance native row')
            tuple_value=projector(rows[0])
            stage='shared_claim_tuple_grade'
            quality,traceability,reasons=shared_grade(tuple_value)
            hashes_after={row['path']:sha(carrier/row['path']) for row in root_inputs}
            if hashes_after!=grade_source_hashes: raise RuntimeError('ROOT grader/readset changed during shared grading')
            if git(app,'status','--porcelain','--untracked-files=all') or git(carrier,'status','--porcelain','--untracked-files=all'): raise RuntimeError('APP or ROOT checkout changed during shared grading')
            grade_result={'state':'graded','native_outcome_kind':outcome_kind,'fixture_execution_conformant':outcome,'adapter_id':'vidya.adapters.ci_conformance/v1','registry_source':'ci-fixture-conformance','registry_task':'VB-CI-CONFORMANCE','measurement_id':tuple_value.measurement_id,'metric':tuple_value.metric,'value':tuple_value.value,'claim':tuple_value.claim,'quality':quality,'traceability':traceability,'reasons':reasons,'expected_ceiling_match':(quality,traceability)==('Judged','Located'),'shared_grade_source_hashes':hashes_after,'journal_record_grade':'not_in_scope','promotion_or_release_acceptance':None}
        (result/'shared-grade-custody.json').write_text(json.dumps(grade_result,sort_keys=True,indent=2)+'\n')
        after_grade=snapshot(result); inventory['after_shared_grade']=after_grade
        (result/'run-root-inventory.json').write_text(json.dumps(inventory,sort_keys=True,indent=2)+'\n')
        grade_ok=grade_result['state']=='graded' and grade_result.get('expected_ceiling_match') is True
        status.update(state='complete' if exact_case_set is True and all_passed is True and outcome is True and grade_ok else 'native_outcome_retained',fixture_execution_conformant=outcome,native_outcome_kind=outcome_kind,shared_grade_state=grade_result['state'],junit_exact_case_set=exact_case_set,junit_all_passed=junit_all_passed,native_receipt='native/receipt.json' if receipt_present else None,shared_grade='shared-grade-custody.json',promotion_or_release_acceptance=None)
        status_path.write_text(json.dumps(status,sort_keys=True)+'\n')
        return 0 if exact_case_set is True and all_passed is True and outcome is True and grade_ok else 1
    except Exception as exc:
        outer_value=receipt.get('fixture_execution_conformant') if isinstance(receipt,dict) else None
        outer_kind=('true' if outer_value is True else 'false' if outer_value is False else 'null' if outer_value is None else 'invalid') if isinstance(receipt,dict) else ('exception' if capture_started else 'not_captured')
        native_receipt_path=result/'native'/'receipt.json'; receipt_present=os.path.lexists(native_receipt_path); receipt_sha256=None; receipt_hash_error=None
        if receipt_present:
            try: receipt_sha256=sha(native_receipt_path)
            except Exception as hash_exc: receipt_hash_error={'type':type(hash_exc).__name__,'diagnostic':str(hash_exc)}
        if capture_started and after_capture is None:
            try: after_capture=snapshot(result)
            except Exception: pass
        shared_state='exception' if grade_started else 'not_started'
        error_record={'schema':'epyc.ni08_et13_w6.error_custody.v2','failed_stage':stage,'capture_started':capture_started,'native_receipt_object_returned':isinstance(receipt,dict),'outer_native_outcome_kind':outer_kind,'fixture_execution_conformant':outer_value,'native_receipt_artifact_present':receipt_present,'native_receipt_sha256':receipt_sha256,'native_receipt_hash_error':receipt_hash_error,'processing_outcome_kind':'exception','exception_type':type(exc).__name__,'diagnostic':str(exc),'shared_grade_state':shared_state,'source_pins':{'app_commit':app_commit,'carrier_commit':carrier_commit,'source_manifest_sha256':source_manifest_sha256,'declared_inputs':inputs,'carrier_source_hashes':{row['path']:row['sha256'] for row in root_inputs}},'result_files_before_capture':before_capture,'result_files_after_capture':after_capture,'result_files_before_grade':before_grade,'journal_record_grade':'not_in_scope','promotion_or_release_acceptance':None}
        (result/'shared-grade-error-custody.json').write_text(json.dumps(error_record,sort_keys=True,indent=2)+'\n')
        failure_state='processing_error' if isinstance(receipt,dict) else 'native_capture_error' if capture_started else 'setup_failure'
        status.update(state=failure_state,diagnostic=f'{type(exc).__name__}: {exc}',fixture_execution_conformant=outer_value,native_outcome_kind=outer_kind,shared_grade_state=shared_state,promotion_or_release_acceptance=None)
        status_path.write_text(json.dumps(status,sort_keys=True)+'\n')
        after_error=None; after_error_inventory_error=None
        try: after_error=snapshot(result)
        except Exception as snapshot_exc: after_error_inventory_error={'type':type(snapshot_exc).__name__,'diagnostic':str(snapshot_exc)}
        if inventory is None:
            inventory={'schema':'epyc.ni08_et13_w6.run_root_inventory.v2','before_capture':before_capture,'after_capture':after_capture,'before_shared_grade':before_grade,'after_shared_grade':after_grade,'native_receipt_present':receipt_present,'native_receipt_sha256':receipt_sha256,'original_outcome':outer_value,'native_outcome_kind':outer_kind,'shared_grade_applicable':False,'selected_case_count':case_count,'exact_case_set':None,'junit_all_passed':None,'all_passed':None,'promotion_or_release_acceptance':None}
        inventory['after_error']=after_error; inventory['after_error_inventory_error']=after_error_inventory_error; inventory['inventory_self_excluded_from_snapshots']=True
        try: (result/'run-root-inventory.json').write_text(json.dumps(inventory,sort_keys=True,indent=2)+'\n')
        except Exception: pass
        return 1
if __name__=='__main__': raise SystemExit(main())
