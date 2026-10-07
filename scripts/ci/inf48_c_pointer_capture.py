#!/usr/bin/env python3
"""Whole C-style pointer lexical controls; no arbitrary reward-hack/runtime warrant."""
from collections import Counter
import ast, hashlib, importlib.metadata, json, os, platform, stat, subprocess, sys, tomllib
from pathlib import Path, PurePosixPath
SOURCE_PIN = 'b2b44fedba3db5ce4c240d9aee0573b753103c53'
CONTEXT_PIN = '09c7b2df444beb70fc97e0ee6feefbc6f36fd9af'
LOCK_PIN = '70096b763939a43409a1f1827ab633d62425a6c1'
LOCKED_PACKAGES = {'pytest': '9.0.3', 'iniconfig': '2.3.0', 'packaging': '26.0', 'pluggy': '1.6.0', 'pygments': '2.20.0'}
INPUTS = {'carrier': {'scripts/ci/native_conformance.py': '2b8c63121e1472d10849224911ee8f4035b7f758ce1aefca7c766e2de263aa0e', 'scripts/vidya/adapters/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'scripts/vidya/adapters/ci_conformance.py': 'aceba149c1b3386e2edd0f8ce5b0bd6bb1d4489d0fe3b3275f8984050aeeb19c', 'scripts/vidya/claim_tuple.py': '058749d2a1ce3487672e85cc5a18fd352b6f17e741a47d7f48bb55be278f4bfe', 'scripts/vidya/lattice.py': 'a889442eecf1887f5d5a4a1193dc0d7760efb668cf31cda21e1d226ec8b24da2', 'scripts/vidya/frames.py': 'f47f148218ae99d54c51b322bf4f3b0632d4458e49572843f5ed4aa424d15749', 'scripts/vidya/canonical.py': 'cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434'}, 'source': {'scripts/kernel_rnd/autokernel/__init__.py': 'b94859500275b1c19c6ec12cb357f2dd0f44ccd118fc95dc6ecfbb358ae37543', 'scripts/kernel_rnd/autokernel/execution/__init__.py': 'f168d3dca9c6f4036242d435d36c2c456ac1293470381c8981a1a84890123ba5', 'scripts/kernel_rnd/autokernel/execution/reward_hack_scan.py': '6b71777a9b60e048f7e581362b461b397d93ca9d54e0abdb210a4e86cd300dbc', 'scripts/kernel_rnd/autokernel/execution/test_reward_hack_scan.py': 'ca01051f2e5f8565e417574e965cc42397665e91a792402b40c72f6e66b85a87', 'pyproject.toml': 'd20fbd0942498e78b94839f4e6b32bd5dfd07911a23339f1d89cec13ae53c140', 'uv.lock': 'e83f418fae20b8585a3200f270ed25b3d621ebeb4c0fcae0ed19de60ed05302d'}, 'lock': {'uv.lock': '7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3'}, 'context': {'handoffs/active/rocm-verify-profile-backend.md': '4264a3ca526555df72aec7d9e5cd0803b327db5234ec03d1b1d7db4d05f3dbdd', 'handoffs/active/vidya-belief-substrate-program.md': 'd792f53cb358bdf7e64bdf7e0a9014da31dff4087c6f09781f5722594c8d6b14', 'scripts/vidya/adapters/README.md': 'd2c939ca8f6a7369974316b8a223ff7c8d6a2edfeda12ec7ccf7dfb890d38172'}}
CONTEXT_MARKERS = {'handoffs/active/rocm-verify-profile-backend.md': ['RVP-C6-26-C-POINTER-SOURCE'], 'handoffs/active/vidya-belief-substrate-program.md': ['VB-RVP-C6-26-C-POINTER-CONFORMANCE'], 'scripts/vidya/adapters/README.md': ['RVP-C6-26-C-POINTER-SOURCE', 'VB-RVP-C6-26-C-POINTER-CONFORMANCE']}
EXPECTED_CASES = [{'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_c_style_pointer_memo_is_flagged_and_counted_by_existing_reporter'}, {'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_c_pointer_text_in_comments_or_literals_is_not_an_active_finding'}, {'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_planted_and_clean_corpus_has_stated_sensitivity_and_specificity'}, {'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_detector_receipt_ids_are_versioned'}, {'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_stream_and_async_escape_corpus'}, {'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_broad_c6_corpus_reports_sensitivity_specificity_and_fpr'}, {'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_broad_detector_ids_are_versioned'}, {'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_phase_detection_exploits_are_refused_without_indicting_normal_dispatch'}, {'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.TestRewardHackDetectors', 'name': 'test_compile_graph_and_content_specialization_exploits_are_refused'}]
TEST_PATH = 'scripts/kernel_rnd/autokernel/execution/test_reward_hack_scan.py'
TEST_AST_SHA256 = '2b37665df90479ee115f8ce445e0396f4c059195258c433293b5fa5a8bf720cd'
LITERAL_BRANCH = 'codex/ni08-inf48-c-pointer-native-20261007'
ENVIRONMENT = {'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTEST_ADDOPTS': '', 'PYTEST_PLUGINS': '', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0', 'PYTHONUNBUFFERED': '1', 'PYTHONNOUSERSITE': '1'}

def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def require_clean(repo: Path, label: str) -> str:
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError(f"{label} checkout is not clean")
    head = git(repo, "rev-parse", "HEAD")
    if len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise RuntimeError(f"{label} HEAD is not a full Git commit")
    return head

def tracked_file(repo: Path, relative: str) -> Path:
    path = repo
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared input traverses a symlink: {relative}")
    if not path.is_file():
        raise RuntimeError(f"declared input is missing or nonregular: {relative}")
    row = git(repo, "ls-tree", "HEAD", "--", relative).split("\t", 1)[0].split()
    if not row or row[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a tracked regular file: {relative}")
    return path.absolute()

def hash_regular(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(f"captured input is not a single-link regular file: {path}")
        digest = hashlib.sha256()
        total = 0
        while True:
            data = os.read(fd, 1024 * 1024)
            if not data:
                break
            digest.update(data)
            total += len(data)
        after = os.fstat(fd)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_mode, row.st_size,
                                row.st_nlink, row.st_mtime_ns, row.st_ctime_ns)
        if identity(before) != identity(after) or total != after.st_size:
            raise RuntimeError(f"captured input changed while hashing: {path}")
        named = path.lstat()
        if identity(after) != identity(named):
            raise RuntimeError(f"captured input path changed while hashing: {path}")
        return digest.hexdigest()
    finally:
        os.close(fd)

def inventory(root: Path, *, omit_root_status=False) -> dict:
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise RuntimeError("fresh result tree is not a real directory")
    found = {".": {"kind": "directory"}}

    def walk(directory: Path) -> None:
        for entry in sorted(os.scandir(directory), key=lambda row: row.name):
            path = Path(entry.path)
            mode = entry.stat(follow_symlinks=False).st_mode
            rel = path.relative_to(root).as_posix()
            if omit_root_status and rel == "status.json":
                continue
            if stat.S_ISLNK(mode):
                found[rel] = {"kind": "symlink", "target": os.readlink(path)}
                continue
            if stat.S_ISDIR(mode):
                found[rel + "/"] = {"kind": "directory"}
                walk(path)
            elif stat.S_ISREG(mode):
                found[rel] = {"kind": "regular", "bytes": path.stat().st_size, "sha256": hash_regular(path)}
            else:
                raise RuntimeError(f"result tree contains a special file: {rel}")

    walk(root)
    return found

def verify_requirements(data: bytes, lock_data: bytes) -> None:
    """Require the exact minimal closure and every wheel in the pinned APP lock."""
    import re
    versions: dict[str, str] = {}
    hashes: dict[str, set[str]] = {}
    pending = ""
    for raw in data.decode("utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        pending += " " + (line[:-1].rstrip() if continued else line)
        if continued:
            continue
        match = re.fullmatch(r"\s*([A-Za-z0-9_.-]+)==([^\s]+)\s+((?:--hash=sha256:[0-9a-f]{64}\s*)+)", pending)
        if not match:
            raise RuntimeError("malformed exact hash-locked requirement")
        name, version, wheel_tokens = match.groups()
        name = name.lower()
        if name in versions:
            raise RuntimeError("duplicate locked requirement")
        versions[name] = version
        hashes[name] = set(re.findall(r"--hash=sha256:([0-9a-f]{64})", wheel_tokens))
        pending = ""
    if pending:
        raise RuntimeError("dangling requirements continuation")
    expected_versions = {name.lower(): version for name, version in LOCKED_PACKAGES.items()}
    if versions != expected_versions:
        raise RuntimeError("dependency pins differ from reviewed minimal pytest closure")
    packages = {row["name"].lower(): row for row in tomllib.loads(lock_data.decode("utf-8"))["package"]}
    for name, version in expected_versions.items():
        package = packages.get(name)
        if not package or package.get("version") != version:
            raise RuntimeError(f"package/version absent from explicit lock source: {name}")
        expected_hashes = set()
        for wheel in package.get("wheels", []):
            value = wheel.get("hash", "")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
                raise RuntimeError("pinned lock wheel lacks exact SHA-256")
            expected_hashes.add(value.removeprefix("sha256:"))
        if not expected_hashes or hashes[name] != expected_hashes:
            raise RuntimeError(f"requirements differ from ALL pinned lock wheels: {name}")

def actual_cases(data):
    tree=ast.parse(data)
    if hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()!=TEST_AST_SHA256:raise RuntimeError('whole actual module AST differs')
    return [{'classname': 'scripts.kernel_rnd.autokernel.execution.test_reward_hack_scan.'+c.name,'name': f.name} for c in tree.body if isinstance(c,ast.ClassDef) for f in c.body if isinstance(f,ast.FunctionDef) and f.name.startswith('test_')]

def durable_custody(path, record):
    with path.open('xb') as handle:
        handle.write((json.dumps(record, sort_keys=True, indent=2)+'\n').encode())
        handle.flush(); os.fsync(handle.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def best_effort_error_custody(run, reads, boundary, error):
    record={'boundary':boundary,'error':type(error).__name__+': '+str(error),'source_snapshots':{},'snapshot_errors':{}}
    for path in reads:
        try: record['source_snapshots'][str(path)]=hash_regular(path)
        except Exception as exc: record['snapshot_errors'][str(path)]=type(exc).__name__+': '+str(exc)
    try: record['full_typed_result_tree']=inventory(run,omit_root_status=True)
    except Exception as exc: record['result_snapshot_error']=type(exc).__name__+': '+str(exc)
    durable_custody(run/'error-custody.json',record)

def main():
    workspace=Path(os.environ['GITHUB_WORKSPACE']).resolve()
    run=Path(os.environ['RUNNER_TEMP']).resolve()/'inf48-c-pointer'
    status_path=run/'status.json';status={'state':'preparing','native_metric':None};reads=[];boundary='setup'
    try:
        if run.is_symlink() or not run.is_dir() or status_path.is_symlink() or not status_path.is_file():raise RuntimeError('original setup layout missing')
        if platform.python_version()!='3.13.15' or platform.system()!='Linux' or platform.machine().lower() not in {'x86_64','amd64'}:raise RuntimeError('reviewed Python/Linux runtime differs')
        if Path(sys.prefix).resolve()!=Path(os.environ['RUNNER_TEMP']).resolve()/'inf48-c-pointer-venv' or sys.prefix==sys.base_prefix:raise RuntimeError('isolated venv differs')
        for key in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','PYTHONPATH'):
            os.environ.pop(key,None)
        os.environ['PYTHONNOUSERSITE']='1'
        for name in ('home','tmp'):
            path=run/name;path.mkdir();os.environ['HOME' if name=='home' else 'TMPDIR']=str(path)
        for key,value in ENVIRONMENT.items():
            if os.environ.get(key)!=value:raise RuntimeError('pytest environment differs: '+key)
        repos={name:workspace/name for name in ('recipe','source','context','carrier','lock')}
        expected={'recipe':os.environ['GITHUB_SHA'],'source':SOURCE_PIN,'context':CONTEXT_PIN,'carrier':'4c0c653baf1654c8c25c66433cf39c8faefd8e52','lock':LOCK_PIN}
        if {name:require_clean(repo,name) for name,repo in repos.items()}!=expected:raise RuntimeError('actual checkout pins differ')
        if os.environ.get('GITHUB_REF')!='refs/heads/'+LITERAL_BRANCH or os.environ.get('GITHUB_EVENT_NAME')!='push':raise RuntimeError('literal reviewed branch push only')
        git(repos['recipe'],'merge-base','--is-ancestor','f477761093e66cc257fb4561e1eb78432833d162','HEAD')
        git(repos['source'],'merge-base','--is-ancestor','9f415a7165dd2c22f7bbf1a52ac3035292c7f5e0','HEAD')
        reads=[]
        for label,entries in INPUTS.items():
            repo=repos[label]
            for relative,digest in entries.items():
                path=tracked_file(repo,relative)
                if hash_regular(path)!=digest:raise RuntimeError('source bytes differ: '+label+'/'+relative)
                if label=='context' and any(marker not in path.read_text() for marker in CONTEXT_MARKERS[relative]):raise RuntimeError('MAIN source/native enrollment missing')
                reads.append(path)
        recipe_files=('.github/workflows/inf48-c-pointer-native.yml','scripts/ci/inf48_c_pointer_capture.py','scripts/ci/inf48_c_pointer_requirements.txt')
        reads.extend(tracked_file(repos['recipe'],p) for p in recipe_files)
        verify_requirements((repos['recipe']/recipe_files[2]).read_bytes(),(repos['lock']/'uv.lock').read_bytes())
        if {p.lower():importlib.metadata.version(p) for p in LOCKED_PACKAGES}!={p.lower():v for p,v in LOCKED_PACKAGES.items()}:raise RuntimeError('actual installed dependency versions differ')
        source=repos['source'];test=tracked_file(source,TEST_PATH)
        if actual_cases(test.read_bytes())!=EXPECTED_CASES:raise RuntimeError('actual full module case identities differ')
        tool_paths={Path(sys.executable).resolve()}
        tool_records={}
        for command,version_args in [('git',['--version'])]:
            path=Path(subprocess.check_output(['which',command],text=True).strip()).resolve()
            tool_paths.add(path);ldd=subprocess.check_output(['ldd',str(path)],text=True)
            for line in ldd.splitlines():
                for token in line.split():
                    if token.startswith('/') and Path(token).is_file():tool_paths.add(Path(token).resolve())
            tool_records[command]={'path':str(path),'original_version_stdout':subprocess.check_output([str(path),*version_args],text=True),'original_ldd_stdout':ldd}
        reads.extend(sorted(tool_paths))
        versions=run/'tool-versions.json';versions.write_text(json.dumps({'python':sys.version,'tools':tool_records,'original_native_binary_sha256':{str(p):hash_regular(p) for p in sorted(tool_paths)}},indent=2)+'\n')
        environment=run/'environment.json';environment.write_text(json.dumps({'env':{k:os.environ.get(k) for k in [*ENVIRONMENT,'HOME','TMPDIR','PYTHONPATH','PYTHONHOME','LD_PRELOAD','PATH','LD_LIBRARY_PATH','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_REF','ImageOS','ImageVersion']},'source_proposition':'C-style pointer memo added-line detection; whole actual detector module','controls':'real static scan_unified_diff and broad_detected corpus controls; no kernel/process launch','excluded_warrants':['arbitrary reward-hack coverage','GPU twin-ranking policy','kernel correctness/runtime/performance acceptance']},indent=2)+'\n')
        freeze=run/'pip-freeze.txt';freeze.write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze','--all']))
        install=run/'dependency-install.log'
        if not install.is_file() or install.is_symlink() or not install.stat().st_size:raise RuntimeError('original installation log missing')
        reads.extend([versions,environment,freeze,install]);before={str(p):hash_regular(p) for p in reads};before_tree=inventory(run,omit_root_status=True)
        result=run/'result';result.mkdir()
        argv=[sys.executable,'-m','pytest','--noconftest','-c','/dev/null','--import-mode=importlib','--rootdir='+str(source),'-o','addopts=','-p','no:cacheprovider','-q',str(test),'--basetemp='+str(result/'actual-test-worlds'),'--junitxml='+str(result/'original-junit.xml')]
        env=dict(os.environ);env['PYTHONPATH']=str(source)
        producer=[sys.executable,str(repos['carrier']/'scripts/ci/native_conformance.py'),'--cwd',str(source),'--junit',str(result/'original-junit.xml'),'--output',str(result/'native')]
        for label,repo in repos.items():producer.extend(['--repo',label+'='+str(repo)])
        for path in reads:producer.extend(['--read-path',str(path)])
        for case in EXPECTED_CASES:producer.extend(['--select',str(test)+'::'+case['classname'].rsplit('.',1)[-1]+'::'+case['name']])
        boundary='capture'
        before_tree=inventory(run,omit_root_status=True)
        durable_custody(run/'pre-capture-custody.json',{'source_before_capture':before,'full_typed_result_tree_before_capture':before_tree,'capture_environment':{k:env.get(k) for k in [*ENVIRONMENT,'PATH','HOME','TMPDIR','PYTHONPATH','PYTHONHOME','LD_LIBRARY_PATH','LD_PRELOAD']},'scope':'original source and result snapshots frozen before native invocation'})
        code=subprocess.call([*producer,'--',*argv],cwd=source,env=env)
        receipt_path=result/'native/receipt.json';receipt=json.loads(receipt_path.read_bytes());summary=receipt.get('summary') or {};counts=summary.get('counts') or {};actual=summary.get('cases') or []
        exact=len(actual)==len(EXPECTED_CASES) and Counter((c.get('classname'),c.get('name')) for c in actual)==Counter((c['classname'],c['name']) for c in EXPECTED_CASES)
        pregrade=inventory(run,omit_root_status=True);before_grade={str(p):hash_regular(p) for p in reads}
        boundary='grade'
        durable_custody(run/'pre-grade-custody.json',{'source_before_capture':before,'source_after_capture_before_grade':before_grade,'full_typed_result_tree_after_capture_before_grade':pregrade,'native_receipt':receipt,'original_exit_code':code,'source_stable':before==before_grade})
        pregrade=inventory(run,omit_root_status=True)
        sys.path.insert(0,str(repos['carrier']));sys.path.insert(0,str(repos['carrier']/'scripts/vidya'))
        from scripts.vidya.adapters.ci_conformance import native_rows,project_ci_conformance
        from claim_tuple import grade
        grades=[]
        for row in native_rows(receipt_path):
            claim=project_ci_conformance(row);q,t,reasons=grade(claim);grades.append({'measurement_id':claim.measurement_id,'Q':q,'T':t,'reasons':reasons})
        postgrade=inventory(run,omit_root_status=True);after_grade={str(p):hash_regular(p) for p in reads}
        if before!=before_grade or before_grade!=after_grade or pregrade!=postgrade:raise RuntimeError('full source/result custody differs')
        for name,repo in repos.items():
            if require_clean(repo,name)!=expected[name]:raise RuntimeError('Git source checkout changed')
        with (run/'shared-grade-custody.json').open('x') as handle:
            json.dump({'full_result_tree_before_capture':before_tree,'full_result_tree_after_capture_before_grade':pregrade,'full_result_tree_after_grade':postgrade,'only_mutable_exclusion':'root status.json','source_before_capture':before,'source_before_grade':before_grade,'source_after_grade':after_grade,'grades':grades,'new_grade_authored':False},handle,indent=2)
        metric=receipt.get('fixture_execution_conformant');n=len(EXPECTED_CASES)
        passed=code==0 and metric is True and exact and counts.get('collected')==n and counts.get('executed')==n and counts.get('passed')==n and all(counts.get(k)==0 for k in ('failure','error','skipped')) and len(grades)==1 and (grades[0]['Q'],grades[0]['T'])==('Judged','Located')
        status.update(state='passed' if passed else 'failed',native_metric=metric,junit_counts=counts,exact_cases=exact,grades=grades,exit_code=0 if passed else code or 1,full_result_tree_after_analysis=inventory(run,omit_root_status=True));return status['exit_code']
    except Exception as exc:
        try: best_effort_error_custody(run,reads,boundary,exc)
        except Exception as custody_error: status['error_custody_error']=type(custody_error).__name__+': '+str(custody_error)
        status.update(state='capture_failed',error=type(exc).__name__+': '+str(exc),exit_code=1);return 1
    finally:status_path.write_text(json.dumps(status,sort_keys=True)+'\n')

if __name__=='__main__':raise SystemExit(main())
