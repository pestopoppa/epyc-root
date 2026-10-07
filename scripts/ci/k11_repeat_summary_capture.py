#!/usr/bin/env python3
"""Actual whole K11 source controls; no live sampler/model/determinism warrant."""
from collections import Counter
import ast, hashlib, importlib.metadata, json, os, platform, stat, subprocess, sys, tomllib
from pathlib import Path, PurePosixPath
SOURCE_PIN = '507848f57f3fdefdc216463660668095324e2821'
CONTEXT_PIN = 'd71676281bfbbec7383a84292add3be214e8b9e9'
LOCK_PIN = '70096b763939a43409a1f1827ab633d62425a6c1'
LOCKED_PACKAGES = {'iniconfig': '2.3.0', 'packaging': '26.0', 'pluggy': '1.6.0', 'pygments': '2.20.0', 'pytest': '9.0.3'}
INPUTS = {'carrier': {'scripts/ci/native_conformance.py': '2b8c63121e1472d10849224911ee8f4035b7f758ce1aefca7c766e2de263aa0e', 'scripts/vidya/adapters/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'scripts/vidya/adapters/ci_conformance.py': 'aceba149c1b3386e2edd0f8ce5b0bd6bb1d4489d0fe3b3275f8984050aeeb19c', 'scripts/vidya/claim_tuple.py': '058749d2a1ce3487672e85cc5a18fd352b6f17e741a47d7f48bb55be278f4bfe', 'scripts/vidya/lattice.py': 'a889442eecf1887f5d5a4a1193dc0d7760efb668cf31cda21e1d226ec8b24da2', 'scripts/vidya/frames.py': 'f47f148218ae99d54c51b322bf4f3b0632d4458e49572843f5ed4aa424d15749', 'scripts/vidya/canonical.py': 'cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434'}, 'source': {'scripts/benchmark/k11_gemma4_determinism_runner.py': '5da2e7e1797da2505571ccfbddb757fb7559c9b6b96d1b8a089e5d60921b29ef', 'scripts/benchmark/test_k11_gemma4_determinism_runner.py': 'f04082d84575045e79c36fd2535f8956eb5a7f9a8cefb652ad74e6c70b180742', 'pyproject.toml': 'd20fbd0942498e78b94839f4e6b32bd5dfd07911a23339f1d89cec13ae53c140', 'uv.lock': 'e83f418fae20b8585a3200f270ed25b3d621ebeb4c0fcae0ed19de60ed05302d'}, 'lock-source': {'uv.lock': '7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3'}, 'context': {'handoffs/active/gemma-challenge-kernel-techniques-v7.md': 'fb76ec625e06de5e145185a076424aa53ba44942ba355f0216115a262f602510', 'handoffs/active/vidya-belief-substrate-program.md': '062c5b8d6171290fba8b66ad5e70b90c57298abd861cd7b5026b29f96b49d508', 'scripts/vidya/adapters/README.md': 'dc2f400c51bb4fd2f78a5da3da9c75f82b16e54b309a24945bcbbbfae8184ea1'}}
CONTEXT_MARKERS = {'handoffs/active/gemma-challenge-kernel-techniques-v7.md': ['K11-REPEAT-SUMMARY-SOURCE', 'VB-K11-REPEAT-SUMMARY-CONFORMANCE'], 'handoffs/active/vidya-belief-substrate-program.md': ['VB-K11-REPEAT-SUMMARY-CONFORMANCE'], 'scripts/vidya/adapters/README.md': ['VB-K11-REPEAT-SUMMARY-CONFORMANCE']}
EXPECTED_CASES = [{'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_server_argv_pins_experimental_v7_build'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_server_argv_supports_no_spec_control'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_server_argv_can_disable_flash_attention'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_server_argv_supports_cpu_no_spec_control'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_server_argv_can_disable_draft_backend_sampling'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_server_argv_records_extra_server_env'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_server_env_requires_assignment'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_apply_request_sampler_mode_explicit_greedy'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_apply_request_sampler_mode_cpu_top_k'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_score_word_task'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_schema_task_builds_word_array_schema'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_score_schema_task'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_query_chat_parses_semantic_response'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_query_chat_sends_stop_strings'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_query_chat_sends_json_schema'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_query_chat_can_request_token_trace_metadata'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_query_chat_can_send_explicit_greedy_payload'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_token_trace_compacts_chat_logprobs'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_token_trace_prefers_returned_token_ids'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_build_token_divergence_summary_reports_first_divergent_token'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_run_execute_writes_token_traces_and_summary_without_server'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_summary_producer_refuses_pass_from_only_successful_requested_repeat'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_summary_producer_accepts_complete_two_repeat_task_success'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_summary_producer_preserves_absent_task_oracle_as_unknown'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_terminate_server_stops_process_group'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_dry_run_writes_plan_and_commands'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestK11Gemma4DeterminismRunner', 'name': 'test_dry_run_records_token_trace_plan'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestCompleteTaskDenominator', 'name': 'test_empty_or_negative_repeat_count_is_refused_before_server_launch'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestCompleteTaskDenominator', 'name': 'test_failed_or_missing_repeat_cannot_inherit_successful_task_verdict'}, {'classname': 'scripts.benchmark.test_k11_gemma4_determinism_runner.TestCompleteTaskDenominator', 'name': 'test_complete_success_and_absent_task_oracle_remain_distinct'}]
TEST_PATH = 'scripts/benchmark/test_k11_gemma4_determinism_runner.py'
TEST_AST_SHA256 = '664eb23aab9bbb042fd3764766515ae20d342b856976744e8288a397ddc3af30'
LITERAL_BRANCH = 'codex/ni08-k11-repeat-summary-native-20261007'
ENVIRONMENT = {'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTEST_ADDOPTS': '', 'PYTEST_PLUGINS': '', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0', 'PYTHONUNBUFFERED': '1'}

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
    if hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()!=TEST_AST_SHA256:
        raise RuntimeError('whole original K11 module AST differs')
    return [{'classname':'scripts.benchmark.test_k11_gemma4_determinism_runner.'+c.name,'name':f.name}
            for c in tree.body if isinstance(c,ast.ClassDef) for f in c.body
            if isinstance(f,ast.FunctionDef) and f.name.startswith('test_')]

def main():
    workspace=Path(os.environ['GITHUB_WORKSPACE']).resolve()
    run=Path(os.environ['RUNNER_TEMP']).resolve()/'k11-summary'
    status_path=run/'status.json';status={'state':'preparing','native_metric':None}
    try:
        if run.is_symlink() or not run.is_dir() or status_path.is_symlink() or not status_path.is_file():raise RuntimeError('original setup layout missing')
        if platform.python_version()!='3.13.15' or platform.system()!='Linux' or platform.machine().lower() not in {'x86_64','amd64'}:raise RuntimeError('reviewed Python/Linux runtime differs')
        if Path(sys.prefix).resolve()!=Path(os.environ['RUNNER_TEMP']).resolve()/'k11-summary-venv' or sys.prefix==sys.base_prefix:raise RuntimeError('isolated venv differs')
        for key,value in ENVIRONMENT.items():
            if os.environ.get(key)!=value:raise RuntimeError('pytest environment differs: '+key)
        repos={name:workspace/name for name in ('recipe','source','lock-source','context')}
        expected={'recipe':os.environ['GITHUB_SHA'],'source':SOURCE_PIN,'lock-source':LOCK_PIN,'context':CONTEXT_PIN}
        if {name:require_clean(repo,name) for name,repo in repos.items()}!=expected:raise RuntimeError('actual checkout pins differ')
        if os.environ.get('GITHUB_REF')!='refs/heads/'+LITERAL_BRANCH or os.environ.get('GITHUB_EVENT_NAME')!='push':raise RuntimeError('literal reviewed branch push only')
        git(repos['recipe'],'merge-base','--is-ancestor',CONTEXT_PIN,'HEAD')
        git(repos['source'],'merge-base','--is-ancestor','f770a52514f3193db44268d61da86f1235122a20','HEAD')
        reads=[]
        for label,entries in INPUTS.items():
            repo=repos['recipe'] if label=='carrier' else repos[label]
            for relative,digest in entries.items():
                path=tracked_file(repo,relative)
                if hash_regular(path)!=digest:raise RuntimeError('source bytes differ: '+label+'/'+relative)
                if label=='context' and any(marker not in path.read_text() for marker in CONTEXT_MARKERS[relative]):raise RuntimeError('MAIN source/native enrollment missing')
                reads.append(path)
        recipe_files=('.github/workflows/k11-repeat-summary-native.yml','scripts/ci/k11_repeat_summary_capture.py','scripts/ci/k11_repeat_summary_requirements.txt')
        reads.extend(tracked_file(repos['recipe'],p) for p in recipe_files)
        verify_requirements((repos['recipe']/recipe_files[2]).read_bytes(),(repos['lock-source']/'uv.lock').read_bytes())
        if {p.lower():importlib.metadata.version(p) for p in LOCKED_PACKAGES}!={p.lower():v for p,v in LOCKED_PACKAGES.items()}:raise RuntimeError('actual installed dependency versions differ')
        source=repos['source'];test=tracked_file(source,TEST_PATH)
        if actual_cases(test.read_bytes())!=EXPECTED_CASES:raise RuntimeError('actual full module case identities differ')
        tool_paths={Path(sys.executable).resolve()}
        tool_records={}
        for command,version_args in [('git',['--version']),('bash',['--version']),('sleep',['--version'])]:
            path=Path(subprocess.check_output(['which',command],text=True).strip()).resolve()
            tool_paths.add(path);ldd=subprocess.check_output(['ldd',str(path)],text=True)
            for line in ldd.splitlines():
                for token in line.split():
                    if token.startswith('/') and Path(token).is_file():tool_paths.add(Path(token).resolve())
            tool_records[command]={'path':str(path),'original_version_stdout':subprocess.check_output([str(path),*version_args],text=True),'original_ldd_stdout':ldd}
        reads.extend(sorted(tool_paths))
        versions=run/'tool-versions.json';versions.write_text(json.dumps({'python':sys.version,'tools':tool_records,'original_native_binary_sha256':{str(p):hash_regular(p) for p in sorted(tool_paths)}},indent=2)+'\n')
        environment=run/'environment.json';environment.write_text(json.dumps({'env':{k:os.environ.get(k) for k in [*ENVIRONMENT,'PATH','LD_LIBRARY_PATH','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_REF','ImageOS','ImageVersion']},'source_proposition':'complete requested task repeat denominator; zero/negative repeat refusal; original whole K11 unit controls','controls':'existing actual owned-Popen sleep/terminate process-group control retained; fake-server seam is original actual run_execute producer control','excluded_warrants':['live natural-prose Gemma determinism','actual sampler/stop correctness','model/runtime/performance acceptance']},indent=2)+'\n')
        freeze=run/'pip-freeze.txt';freeze.write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze','--all']))
        install=run/'dependency-install.log'
        if not install.is_file() or install.is_symlink() or not install.stat().st_size:raise RuntimeError('original installation log missing')
        reads.extend([versions,environment,freeze,install]);before={str(p):hash_regular(p) for p in reads};before_tree=inventory(run,omit_root_status=True)
        result=run/'result';result.mkdir()
        argv=[sys.executable,'-m','pytest','--noconftest','-c','/dev/null','--import-mode=importlib','--rootdir='+str(source),'-o','addopts=','-p','no:cacheprovider','-q',str(test),'--basetemp='+str(result/'actual-test-worlds'),'--junitxml='+str(result/'original-junit.xml')]
        env=dict(os.environ);env['PYTHONPATH']=str(source)
        producer=[sys.executable,str(repos['recipe']/'scripts/ci/native_conformance.py'),'--cwd',str(source),'--junit',str(result/'original-junit.xml'),'--output',str(result/'native')]
        for label,repo in repos.items():producer.extend(['--repo',label+'='+str(repo)])
        for path in reads:producer.extend(['--read-path',str(path)])
        for case in EXPECTED_CASES:producer.extend(['--select',str(test)+'::'+case['classname'].rsplit('.',1)[-1]+'::'+case['name']])
        code=subprocess.call([*producer,'--',*argv],cwd=source,env=env)
        receipt_path=result/'native/receipt.json';receipt=json.loads(receipt_path.read_bytes());counts=receipt.get('summary',{}).get('counts',{});actual=receipt.get('summary',{}).get('cases',[])
        exact=len(actual)==len(EXPECTED_CASES) and Counter((c.get('classname'),c.get('name')) for c in actual)==Counter((c['classname'],c['name']) for c in EXPECTED_CASES)
        pregrade=inventory(run,omit_root_status=True);before_grade={str(p):hash_regular(p) for p in reads}
        sys.path.insert(0,str(repos['recipe']));sys.path.insert(0,str(repos['recipe']/'scripts/vidya'))
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
        status.update(state='capture_failed',error=type(exc).__name__+': '+str(exc),exit_code=1);return 1
    finally:status_path.write_text(json.dumps(status,sort_keys=True)+'\n')

if __name__=='__main__':raise SystemExit(main())
