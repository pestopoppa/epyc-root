#!/usr/bin/env python3
"""Whole future keep-claim decisive propagation controls; no historical row/runtime warrant."""
from collections import Counter
import ast, hashlib, importlib.metadata, json, os, platform, stat, subprocess, sys, tomllib
from pathlib import Path, PurePosixPath
SOURCE_PIN = '188087701c963d57eb622ff8279081fae55f8049'
CONTEXT_PIN = '09c7b2df444beb70fc97e0ee6feefbc6f36fd9af'
LOCK_PIN = '70096b763939a43409a1f1827ab633d62425a6c1'
LOCKED_PACKAGES = {'jsonschema': '4.26.0', 'rpds-py': '0.30.0', 'referencing': '0.37.0', 'typing-extensions': '4.15.0', 'attrs': '26.1.0', 'jsonschema-specifications': '2025.9.1', 'pytest': '9.0.3', 'pygments': '2.20.0', 'pluggy': '1.6.0', 'packaging': '26.0', 'iniconfig': '2.3.0'}
INPUTS = {'carrier': {'scripts/ci/native_conformance.py': '2b8c63121e1472d10849224911ee8f4035b7f758ce1aefca7c766e2de263aa0e', 'scripts/vidya/adapters/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'scripts/vidya/adapters/ci_conformance.py': 'aceba149c1b3386e2edd0f8ce5b0bd6bb1d4489d0fe3b3275f8984050aeeb19c', 'scripts/vidya/claim_tuple.py': '058749d2a1ce3487672e85cc5a18fd352b6f17e741a47d7f48bb55be278f4bfe', 'scripts/vidya/lattice.py': 'a889442eecf1887f5d5a4a1193dc0d7760efb668cf31cda21e1d226ec8b24da2', 'scripts/vidya/frames.py': 'f47f148218ae99d54c51b322bf4f3b0632d4458e49572843f5ed4aa424d15749', 'scripts/vidya/canonical.py': 'cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434'}, 'source': {'scripts/kernel_rnd/autokernel/loop/test_claims.py': 'c3ac560f9dd311578d62ecae7dc944f384a7a7ef0bc0f997af48cee0d8dfc304', 'scripts/kernel_rnd/autokernel/loop/__init__.py': 'a004ca9cd70d052369046a8c5bc6981316a4c9c4182724035e3a6a007994a992', 'scripts/kernel_rnd/autokernel/__init__.py': 'b94859500275b1c19c6ec12cb357f2dd0f44ccd118fc95dc6ecfbb358ae37543', 'scripts/kernel_rnd/autokernel/loop/loop.py': '535c0915f30a20e8b4a2daf9375a11d8bbbaa70bb325396ea452881653dfc69d', 'scripts/kernel_rnd/autokernel/loop/runtime_identity.py': 'a8a961d451d218932ee05c0b5b1d090154a777cd9b487081b19835a45595be4c', 'scripts/kernel_rnd/autokernel/loop/integrity.py': 'a69043456e7ea0b40cf636fac983645dc975399d2eb17609c762411aa1733a9a', 'scripts/kernel_rnd/autokernel/execution/reward_hack_scan.py': 'cb6bd63ab8e6a870ae78fed7874da3bfc2034332f5b09f4a37d71ae28ac1d356', 'scripts/kernel_rnd/autokernel/execution/__init__.py': 'f168d3dca9c6f4036242d435d36c2c456ac1293470381c8981a1a84890123ba5', 'scripts/kernel_rnd/autokernel/loop/gates.py': '21248734050ae1e36af7cd79256f28896ca7c0f637b195410aed94d2f70513b8', 'scripts/kernel_rnd/autokernel/loop/residency.py': '7040d7029ef3099684870271eb7f6fa1d3523f583aff0f689ac2739f37040723', 'scripts/kernel_rnd/autokernel/loop/census.py': 'dfd46b7275aeb335d62627a270b79ede27867b4ca1c89416d6638bdf135f9152', 'scripts/kernel_rnd/autokernel/controller/workload_contract.py': '64f8220a3bf343c8e7c27706152584b06a9b0379353ded9e5d9e6d9d76229cbb', 'scripts/kernel_rnd/autokernel/controller/__init__.py': '7b886cb86f5bdd63cca362f81f8adf319f2584a46af35f266d7add5bc1a3a0f0', 'scripts/kernel_rnd/autokernel/controller/hypotheses.py': '425c1dc97ba9d2f4085cb49f6433badc007f7af14efcc7a30a2d43ae98fedf75', 'scripts/kernel_rnd/autokernel/controller/shared.py': 'd0e7cf87e24ea9301b8da59e7537be3ef45806ab007fa53765a8b833cbf1e3ed', 'scripts/kernel_rnd/autokernel/schemas.py': '4dd07e2492a534029654b4bad5a2fb1062d66ddf5582bbd3bda8b7f17ea88644', 'scripts/kernel_rnd/autokernel/resource/device_claim.py': 'ed079e49946a869399b905e2149f6b0a3c76c1c19d1acbb1bfd39766e4d861d7', 'scripts/kernel_rnd/autokernel/resource/__init__.py': '86556de74e577691e7b10b724e4443e3f763efe940dcbf20574d4b062880ded3', 'scripts/kernel_rnd/autokernel/journal.py': 'c73cc8d7e4f6ec9e4a36de1396a72daa412d4d79cc026940bd785aa49fe83a2a', 'scripts/kernel_rnd/autokernel/controller/do_not_repeat.py': '66c32876760b2f61c1064e0e6767c3ce3b5c22ae4878ee558439e188e7e6aec3', 'scripts/kernel_rnd/autokernel/evaluator/api.py': 'bf7a729fb84c2a4b7a7f44c9872a7647680ee129bc07a74aa28db963c767a956', 'scripts/kernel_rnd/autokernel/evaluator/__init__.py': '78741f051d83ea3d84ea60440226630889053d93b49790d12b57d7ab1b099630', 'scripts/kernel_rnd/autokernel/evaluator/devices.py': 'af8ee4813a4a80535f2628604bd53257259ef1aad5173c96863db68b1e990c3b', 'scripts/kernel_rnd/autokernel/loop/bench.py': '95c97fb3ffb410ef5858820384d8713767fd7d2f61c9889688a39a70521eccc2', 'scripts/kernel_rnd/autokernel/execution/microbench.py': '2be83412522813faa14bd63719db94b68649959b3de7dffc58d5a0db0a953a09', 'scripts/kernel_rnd/autokernel/execution/sandbox.py': '014061ab210cf3b3cef3b1df7cdd6f299e67271ae920aa3e244031968fc02ac6', 'scripts/kernel_rnd/autokernel/execution/physical_bounds.py': 'b5b3df8d4c4cf8b769ad6766c188c6c0e1600aee7d52a3ddb0b5632868ce1724', 'scripts/kernel_rnd/autokernel/execution/instrument_integrity.py': 'bbc1013e988cdbfb86b6adf7b7267cc1e8cccefc71769fd6d3ea0033e2872bee', 'scripts/kernel_rnd/autokernel/execution/device_sampler.py': '13f86ed2854d095241b609290e21318e426bd2a3e6b21ea56fb8a74e21c768f0', 'scripts/kernel_rnd/autokernel/evaluator/statistics.py': '19620e357ccc3f3b32b1b9a1a88f979922135c585176af814c6dff1633a94140', 'scripts/kernel_rnd/autokernel/evaluator/recipes.py': 'ba7e2e76602c04f6a012b0609963215f21aff2faa735d5ea3990a6bac8d6f5e2', 'scripts/kernel_rnd/autokernel/storage.py': '7d1426ebb47d2f0926f5128ccc2bebc2fd6d7239a1ce5708815ef1287e7557a9', 'scripts/kernel_rnd/autokernel/evaluator/integrity.py': 'dfc6dbc719aab525d4ddedd53ca087b00e1e632ed8147967175676884f415f1f', 'scripts/kernel_rnd/autokernel/evaluator/surface.py': 'a8576e98dc6c0292bab6b4bdc08f3cc22ca6d1e1f9fdb9805d0e3bad775a7cf6', 'scripts/kernel_rnd/autokernel/evaluator/correctness.py': 'd03b9949d72694c679a61af7ca5b64d0aca3666ad8eb97e32aefccc036e61fbd', 'scripts/kernel_rnd/autokernel/loop/claims.py': '510322ffc500da257b2185d6dd3bddd2d88a6873a4a2974eec141d25b9feee9f', 'scripts/kernel_rnd/autokernel/loop/actors.py': '70ebe0584c3e34cf8158c9d982686a3a8a1ed846c5e3250154a255a66803663c', 'scripts/kernel_rnd/autokernel/loop/scratch.py': 'a0e2155d0e10f2c92d417388b631baec8cfa493e0cbe167f20b6cd4d637b02e4', 'scripts/kernel_rnd/autokernel/loop/procguard.py': 'ba76df114d3feef6df5555b98849d6f9339745889bcedb660ab4b2c5eecb34be', 'scripts/kernel_rnd/autokernel/loop/belief_context.py': 'dd5cb696087499d4109903aa65b070c6c30e69f53b8b599ef31b28373f572f81', 'scripts/kernel_rnd/autokernel/loop/actor_metrics.py': '7407d7d8bd331871a603ecb52483cdfa63e7f29a01f519e540b867c0b43859bf', 'scripts/kernel_rnd/autokernel/controller/experiments.py': 'e444a540cdb8ce4a21b820cbaf7db8ef94015f18d5670b00e635b706bee91d47', 'scripts/lib/canonical_recipe.py': '3d71f755e9b537df46fee99fa3869bcd4dff6d2884e7600cb86a44d203a726de', 'scripts/lib/__init__.py': '61b591cd8f067aba6550dbfa242ce673e1f5e3666e738dfa03c70f0315bb92f2', 'pyproject.toml': 'd20fbd0942498e78b94839f4e6b32bd5dfd07911a23339f1d89cec13ae53c140', 'uv.lock': 'e83f418fae20b8585a3200f270ed25b3d621ebeb4c0fcae0ed19de60ed05302d'}, 'lock': {'uv.lock': '7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3'}, 'context': {'handoffs/active/deepseek-v41-flash-evaluation.md': '4ffc37dda8db50ceda52b78661711d8b3613f2c27a71cf5f922a0a0c18fdb8ab', 'handoffs/active/vidya-belief-substrate-program.md': 'd792f53cb358bdf7e64bdf7e0a9014da31dff4087c6f09781f5722594c8d6b14', 'scripts/vidya/adapters/README.md': 'd2c939ca8f6a7369974316b8a223ff7c8d6a2edfeda12ec7ccf7dfb890d38172'}}
CONTEXT_MARKERS = {'handoffs/active/deepseek-v41-flash-evaluation.md': ['DS41-C104-FUTURE-WRITER-SOURCE'], 'handoffs/active/vidya-belief-substrate-program.md': ['VB-DS41-C104-FUTURE-WRITER-CONFORMANCE'], 'scripts/vidya/adapters/README.md': ['DS41-C104-FUTURE-WRITER-SOURCE', 'VB-DS41-C104-FUTURE-WRITER-CONFORMANCE']}
EXPECTED_CASES = [{'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': 'test_keep_splits_verified_effect_from_hypothesis_mechanism'}, {'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': 'test_effect_and_mechanism_verification_fail_closed'}, {'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': 'test_explicit_evidenced_ablation_verifies_mechanism'}, {'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': 'test_non_keep_has_no_keep_claims'}, {'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': 'test_outcome_serialization_and_recall_preserve_the_split'}, {'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': 'test_planner_does_not_characterise_hypothesis_mechanisms'}, {'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': 'test_effect_requires_explicit_decisive_boolean_without_mutating_comparison'}, {'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': 'test_actual_outcome_serialization_preserves_native_decisive_effect_boundary'}]
TEST_PATH = 'scripts/kernel_rnd/autokernel/loop/test_claims.py'
TEST_AST_SHA256 = '24b8782f708514467849fa466c6ed05ad005e3863d4f719ccabb4b96f535acac'
LITERAL_BRANCH = 'codex/ni08-ds41-c104-native-20261007'
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
    return [{'classname': 'scripts.kernel_rnd.autokernel.loop.test_claims', 'name': f.name} for f in tree.body if isinstance(f, ast.FunctionDef) and f.name.startswith('test_')]

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
    run=Path(os.environ['RUNNER_TEMP']).resolve()/'ds41-c104'
    status_path=run/'status.json';status={'state':'preparing','native_metric':None};reads=[];boundary='setup'
    try:
        if run.is_symlink() or not run.is_dir() or status_path.is_symlink() or not status_path.is_file():raise RuntimeError('original setup layout missing')
        if platform.python_version()!='3.13.15' or platform.system()!='Linux' or platform.machine().lower() not in {'x86_64','amd64'}:raise RuntimeError('reviewed Python/Linux runtime differs')
        if Path(sys.prefix).resolve()!=Path(os.environ['RUNNER_TEMP']).resolve()/'ds41-c104-venv' or sys.prefix==sys.base_prefix:raise RuntimeError('isolated venv differs')
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
        git(repos['recipe'],'merge-base','--is-ancestor',CONTEXT_PIN,'HEAD')
        git(repos['source'],'merge-base','--is-ancestor','c49729505b6b85bcc2ef68255168014b4ae6a84d','HEAD')
        reads=[]
        for label,entries in INPUTS.items():
            repo=repos[label]
            for relative,digest in entries.items():
                path=tracked_file(repo,relative)
                if hash_regular(path)!=digest:raise RuntimeError('source bytes differ: '+label+'/'+relative)
                if label=='context' and any(marker not in path.read_text() for marker in CONTEXT_MARKERS[relative]):raise RuntimeError('MAIN source/native enrollment missing')
                reads.append(path)
        recipe_files=('.github/workflows/ds41-c104-native.yml','scripts/ci/ds41_c104_capture.py','scripts/ci/ds41_c104_requirements.txt')
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
        environment=run/'environment.json';environment.write_text(json.dumps({'env':{k:os.environ.get(k) for k in [*ENVIRONMENT,'HOME','TMPDIR','PYTHONPATH','PYTHONHOME','LD_PRELOAD','PATH','LD_LIBRARY_PATH','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_REF','ImageOS','ImageVersion']},'source_proposition':'Future keep-claim decisive propagation; whole actual8 writer/producer/store/render controls','controls':'real Comparison/Outcome, temporary SQLite record/recall and planner rendering; no actor/CLI/model/build/native process launch','excluded_warrants':['historical14-row reprojection','keep admission policy change','actor/model/build/runtime/performance acceptance']},indent=2)+'\n')
        actor_paths=[run/'home/.codex/packages/app-server-daemon/current/bin/codex',Path('/usr/local/share/npm-global/bin/codex'),Path('/home/node/.local/bin/claude')]
        if any(os.path.lexists(path) for path in actor_paths):raise RuntimeError('declared synthetic actor binary context must be absent before source imports')
        actor_context=run/'actor-binary-absence.json';actor_context.write_text(json.dumps({'paths':[str(p) for p in actor_paths],'all_absent':True,'scope':'actual actors source constants/context; no actor invoked'},indent=2)+'\n')
        reads.append(actor_context)
        freeze=run/'pip-freeze.txt';freeze.write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze','--all']))
        install=run/'dependency-install.log'
        if not install.is_file() or install.is_symlink() or not install.stat().st_size:raise RuntimeError('original installation log missing')
        reads.extend([versions,environment,freeze,install]);before={str(p):hash_regular(p) for p in reads};before_tree=inventory(run,omit_root_status=True)
        result=run/'result';result.mkdir()
        argv=[sys.executable,'-m','pytest','--noconftest','-c','/dev/null','--import-mode=importlib','--rootdir='+str(source),'-o','addopts=','-p','no:cacheprovider','-q',str(test),'--basetemp='+str(result/'actual-test-worlds'),'--junitxml='+str(result/'original-junit.xml')]
        env=dict(os.environ);env['PYTHONPATH']=str(source/'scripts/kernel_rnd')+os.pathsep+str(source)
        producer=[sys.executable,str(repos['carrier']/'scripts/ci/native_conformance.py'),'--cwd',str(source),'--junit',str(result/'original-junit.xml'),'--output',str(result/'native')]
        for label,repo in repos.items():producer.extend(['--repo',label+'='+str(repo)])
        for path in reads:producer.extend(['--read-path',str(path)])
        for case in EXPECTED_CASES:producer.extend(['--select',str(test)+'::'+case['name']])
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
        if any(os.path.lexists(path) for path in actor_paths):raise RuntimeError('declared actor binary absence context changed')
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
