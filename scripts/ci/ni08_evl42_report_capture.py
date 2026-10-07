#!/usr/bin/env python3
"""Private prospective actual pin-report attachment controls; no pin-health warrant."""
from __future__ import annotations
from collections import Counter
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import tomllib

SOURCE_PIN = '112217d1422a74b6b4a13dbc8354381a0bf058d1'
RESEARCH_PIN = 'cb801b9b7bb4ad3555ffc4be5a6d879cc6ae7875'
LOCK_PIN = '70096b763939a43409a1f1827ab633d62425a6c1'
LOCK_BLOB = 'ef2306018773ff9a1e80389970d92f66fcf8d5b7'
LOCK_SHA256 = '7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3'
LOCKED_PACKAGES = {'iniconfig': '2.3.0', 'packaging': '26.0', 'pluggy': '1.6.0', 'Pygments': '2.20.0', 'pytest': '9.0.3'}
SOURCE_INPUTS = {'scripts/ci/pin_report_fixture.py': 'ce91371a13cfd2288e43e91e4b8b895de362160bccc0f1bf43081645e920eb03', 'tests/ci/test_pin_report_fixture.py': '6d507b95f954c565497961aae080e1982872f67afaa39475dca068e24b610d05', 'tests/__init__.py': '10c16231f06d380ad96987c164ecf0560eba68aea5f265eebb8d90fa2993c528', 'scripts/ci/native_conformance.py': '2b8c63121e1472d10849224911ee8f4035b7f758ce1aefca7c766e2de263aa0e', 'scripts/vidya/adapters/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'scripts/vidya/adapters/ci_conformance.py': 'aceba149c1b3386e2edd0f8ce5b0bd6bb1d4489d0fe3b3275f8984050aeeb19c', 'scripts/vidya/claim_tuple.py': '058749d2a1ce3487672e85cc5a18fd352b6f17e741a47d7f48bb55be278f4bfe', 'scripts/vidya/lattice.py': 'a889442eecf1887f5d5a4a1193dc0d7760efb668cf31cda21e1d226ec8b24da2', 'scripts/vidya/frames.py': 'f47f148218ae99d54c51b322bf4f3b0632d4458e49572843f5ed4aa424d15749', 'scripts/vidya/canonical.py': 'cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434'}
EXPECTED_CASES = [{'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_roundtrip_preserves_current_stale_and_unknown[current]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_roundtrip_preserves_current_stale_and_unknown[stale]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_roundtrip_preserves_current_stale_and_unknown[missing]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_roundtrip_preserves_current_stale_and_unknown[unresolved]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[count]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[complete]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[git_stable]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[checker_match]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[boolean_count]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[scope]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[dirty_count]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[unread_source]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_report_metadata_drift_is_refused[path_normalization]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_original_report_hash_and_duplicate_json_fields_are_refused'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_report_writer_refuses_overwrite_and_symlink_parents'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_missing_scanned_checker_remains_incomplete_without_tuple_upgrade'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_failed_file_or_directory_fsync_removes_only_owned_report_for_retry[file]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_failed_file_or_directory_fsync_removes_only_owned_report_for_retry[directory]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_native_attachment_projection_preserves_true_false_null[current_TRUE]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_native_attachment_projection_preserves_true_false_null[stale_TRUE]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_native_attachment_projection_preserves_true_false_null[missing_TRUE]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_native_attachment_projection_preserves_true_false_null[unresolved_TRUE]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_native_attachment_projection_preserves_true_false_null[current_FALSE]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_native_attachment_projection_preserves_true_false_null[current_NULL]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_original_attachment_refuses_absent_tampered_or_mixed_receipts[absent]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_original_attachment_refuses_absent_tampered_or_mixed_receipts[tampered]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_actual_original_attachment_refuses_absent_tampered_or_mixed_receipts[mixed]'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_partial_write_is_removed_without_deleting_unrelated_output'}, {'classname': 'tests.ci.test_pin_report_fixture', 'name': 'test_failure_cleanup_refuses_to_unlink_replaced_exclusive_name'}]
TEST_PATH = 'tests/ci/test_pin_report_fixture.py'
CHECKER_PATH = 'scripts/benchmark/check_pin_staleness.py'
CHECKER_SHA256 = '2fc0680f070cc2f051bd8d74b66748a1c00e09f3d8d8f229ab46b9167152e666'
CONTEXT_PIN = '7981a9acf2b8e2c328b9add8e21a68656c99c1d6'
CONTEXT_INPUTS = {'handoffs/active/scoring-infra-standardization.md': '56541ec5134bec43fe888fd3977c2ce20b40677436ab80c5d28ee524a28daa25', 'handoffs/active/vidya-belief-substrate-program.md': 'b18435c0b2e0f0aa3d37dc23892aaebb63235f328bffda5dc9084ae324e95cb1', 'scripts/vidya/adapters/README.md': '32633774ffb96d17c97b357b55f8c18de4b3ac1d9b2c7f9846620c021a6d229d'}
REQUIREMENTS_SHA256 = 'e10bd23d53c73d76ae3fdd231dfd28b177d777e8107f6f56762299002711512a'
TEST_AST_SHA256 = '50fa33618644c75a54e8d0d8ff425ded0d2c29ed4f52c07a034ff932bcce40d6'
LITERAL_BRANCH = 'codex/ni08-evl42-report-native-20261007'
CONTEXT_MARKERS = {'handoffs/active/scoring-infra-standardization.md': 'SC-EVL42-PIN-REPORT-WIRING', 'handoffs/active/vidya-belief-substrate-program.md': 'SC-EVL42-PIN-REPORT-WIRING', 'scripts/vidya/adapters/README.md': 'SC-EVL42-PIN-REPORT-WIRING'}
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


def expanded_test_cases(source: bytes):
    """Enumerate literal actual parameterizations without importing source code."""
    import itertools
    tree=ast.parse(source,filename=TEST_PATH)
    if hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()!=TEST_AST_SHA256:
        raise RuntimeError('actual whole-module test AST differs')
    found=[]
    for node in tree.body:
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) or not node.name.startswith('test_'):
            continue
        suffixes=[[]]
        for decorator in reversed(node.decorator_list):
            if not isinstance(decorator,ast.Call) or not isinstance(decorator.func,ast.Attribute) or decorator.func.attr!='parametrize':
                raise RuntimeError('unexpected actual test decorator')
            if len(decorator.args)!=2:
                raise RuntimeError('nonliteral parameterization shape')
            values=ast.literal_eval(decorator.args[1])
            options={k.arg:ast.literal_eval(k.value) for k in decorator.keywords}
            if set(options)-{'ids'}:
                raise RuntimeError('unreviewed parameterization options')
            ids=options.get('ids')
            if ids is None:
                if any(not isinstance(value,(str,int)) or type(value) is bool for value in values):
                    raise RuntimeError('default parameter IDs are not explicit scalar literals')
                ids=[str(value) for value in values]
            if len(ids)!=len(values) or len(set(ids))!=len(ids) or any(not isinstance(x,str) for x in ids):
                raise RuntimeError('invalid literal parameter IDs')
            suffixes=[[*prefix,value] for prefix,value in itertools.product(suffixes,ids)]
        for parts in suffixes:
            found.append({'classname':'tests.ci.test_pin_report_fixture',
                          'name':node.name+('['+'-'.join(parts)+']' if parts else '')})
    if len(found)!=29 or len({(r['classname'],r['name']) for r in found})!=29:
        raise RuntimeError('actual expanded case count differs')
    return found


def main():
    workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    run = Path(os.environ['RUNNER_TEMP']).resolve() / 'evl42-report'
    status_path = run / 'status.json'
    status = {'state': 'preparing', 'native_metric': None}
    if run.is_symlink() or not run.is_dir() or status_path.is_symlink() or not status_path.is_file():
        raise RuntimeError('workflow private capture layout missing')
    try:
        if len(CONTEXT_PIN) != 40 or not CONTEXT_INPUTS:
            raise RuntimeError('prospective MAIN enrollment is not bound; capture forbidden')
        if (platform.python_version() != '3.13.15' or platform.system() != 'Linux'
                or platform.machine().lower() not in {'x86_64', 'amd64'}):
            raise RuntimeError('reviewed Python/Linux runtime differs')
        if Path(sys.prefix).resolve() != Path(os.environ['RUNNER_TEMP']).resolve() / 'evl42-report-venv' or sys.prefix == sys.base_prefix:
            raise RuntimeError('isolated venv differs')
        for name, expected in ENVIRONMENT.items():
            if os.environ.get(name) != expected:
                raise RuntimeError('pytest environment differs: ' + name)
        repos = {name: workspace/name for name in ('recipe', 'source', 'research', 'lock-source', 'context')}
        expected = {'recipe':os.environ['GITHUB_SHA'], 'source':SOURCE_PIN, 'research':RESEARCH_PIN,
                    'lock-source':LOCK_PIN, 'context':CONTEXT_PIN}
        if {name:require_clean(repo,name) for name,repo in repos.items()} != expected:
            raise RuntimeError('actual checkout pins differ')
        source = repos['source']
        if os.environ.get('GITHUB_REF') != 'refs/heads/' + LITERAL_BRANCH or os.environ.get('GITHUB_EVENT_NAME') != 'push':
            raise RuntimeError('only exact reviewed literal push branch is eligible')
        git(repos['recipe'], 'merge-base', '--is-ancestor', SOURCE_PIN, 'HEAD')
        if set(CONTEXT_INPUTS) != set(CONTEXT_MARKERS):
            raise RuntimeError('all three prospective enrollment files must be bound')
        reads = []
        for rel, digest in SOURCE_INPUTS.items():
            path = tracked_file(source,rel)
            if hash_regular(path) != digest:
                raise RuntimeError('source bytes differ: '+rel)
            reads.append(path)
        for rel,digest in CONTEXT_INPUTS.items():
            path=tracked_file(repos['context'],rel)
            if hash_regular(path)!=digest:
                raise RuntimeError('MAIN enrollment bytes differ')
            if CONTEXT_MARKERS[rel] not in path.read_text(encoding='utf-8'):
                raise RuntimeError('prospective MAIN enrollment marker missing')
            reads.append(path)
        checker=tracked_file(repos['research'],CHECKER_PATH)
        if hash_regular(checker)!=CHECKER_SHA256:
            raise RuntimeError('actual unchanged Research checker differs')
        reads.append(checker)
        for rel in ('pyproject.toml','uv.lock'):
            reads.append(tracked_file(repos['research'],rel))
        lock=tracked_file(repos['lock-source'],'uv.lock')
        if git(repos['lock-source'],'rev-parse','HEAD:uv.lock')!=LOCK_BLOB or hash_regular(lock)!=LOCK_SHA256:
            raise RuntimeError('explicit dependency lock differs')
        req=tracked_file(repos['recipe'],'scripts/ci/ni08_evl42_report_requirements.txt')
        verify_requirements(req.read_bytes(),lock.read_bytes())
        if hash_regular(req) != REQUIREMENTS_SHA256:
            raise RuntimeError('requirements bytes differ')
        if {name:importlib.metadata.version(name) for name in LOCKED_PACKAGES}!=LOCKED_PACKAGES:
            raise RuntimeError('installed dependency versions differ')
        reads.extend([lock,req,tracked_file(repos['recipe'],'scripts/ci/ni08_evl42_report_capture.py'),
                      tracked_file(repos['recipe'],'.github/workflows/ni08-evl42-report-native.yml')])
        environment=run/'environment.json'
        environment.write_text(json.dumps({'pins':expected,'environment':ENVIRONMENT,'python':sys.version,
            'platform':platform.platform(),'cases':EXPECTED_CASES,'source_import_closure':SOURCE_INPUTS,
            'pytest_argv_isolation':['--noconftest','-c /dev/null','--import-mode=importlib','-o addopts=','-p no:cacheprovider'],
            'dependency_versions':LOCKED_PACKAGES,'artifact_custody':'regular bytes, directory membership and links without following; root status.json alone is mutable/excluded','scope':'29 outer synthetic controls; original nested TRUE/FALSE/NULL retained; no actual Research scan or pin-health warrant'},sort_keys=True,indent=2)+'\n')
        freeze=run/'pip-freeze.txt'
        freeze.write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze','--all']))
        versions=run/'tool-versions.json'
        versions.write_text(json.dumps({'git':subprocess.check_output(['git','--version'],text=True).strip(),
            'bash':subprocess.check_output(['bash','--version'],text=True).splitlines()[0],
            'python':sys.version},sort_keys=True)+'\n')
        install=run/'dependency-install.log'
        if not install.is_file() or install.is_symlink() or not install.stat().st_size:
            raise RuntimeError('original installation log missing')
        reads.extend([environment,freeze,versions,install])
        before={str(p):hash_regular(p) for p in reads}
        result=run/'result';result.mkdir()
        tree_before_capture=inventory(run,omit_root_status=True)
        test=tracked_file(source,TEST_PATH)
        if expanded_test_cases(test.read_bytes()) != EXPECTED_CASES:
            raise RuntimeError('complete expanded AST case identity differs')
        argv=[sys.executable,'-m','pytest','--noconftest','-c','/dev/null','--import-mode=importlib',
              '--rootdir='+str(source),'-o','addopts=','-p','no:cacheprovider','-q',str(test),
              '--basetemp='+str(result/'actual-test-worlds'),'--junitxml='+str(result/'original-junit.xml')]
        env=dict(os.environ);env.update(ENVIRONMENT)
        env['EPYC_INFERENCE_RESEARCH_REPO']=str(repos['research'])
        env['PYTHONPATH']=str(source)
        producer=[sys.executable,str(source/'scripts/ci/native_conformance.py'),'--cwd',str(source),
                  '--junit',str(result/'original-junit.xml'),'--output',str(result/'native')]
        for name,repo in repos.items():producer.extend(['--repo',name+'='+str(repo)])
        for path in reads:producer.extend(['--read-path',str(path)])
        for case in EXPECTED_CASES:producer.extend(['--select',str(test)+'::'+case['name']])
        code=subprocess.call([*producer,'--',*argv],cwd=source,env=env)
        receipt_path=result/'native/receipt.json'
        receipt=json.loads(receipt_path.read_bytes())
        summary=receipt.get('summary') or {};counts=summary.get('counts') or {}
        actual=[(c.get('classname'),c.get('name')) for c in summary.get('cases') or []]
        exact=Counter(actual)==Counter((c['classname'],c['name']) for c in EXPECTED_CASES) and len(actual)==29
        tree_before=inventory(run,omit_root_status=True);before_grade={str(p):hash_regular(p) for p in reads}
        sys.path.insert(0,str(source));sys.path.insert(0,str(source/'scripts/vidya'))
        from scripts.vidya.adapters.ci_conformance import native_rows,project_ci_conformance
        from claim_tuple import grade
        rows=native_rows(receipt_path)
        grades=[]
        for row in rows:
            claim=project_ci_conformance(row);quality,trust,reasons=grade(claim)
            grades.append({'measurement_id':claim.measurement_id,'Q':quality,'T':trust,'reasons':reasons})
        tree_after=inventory(run,omit_root_status=True);after_grade={str(p):hash_regular(p) for p in reads}
        if tree_before!=tree_after or before!=before_grade or before_grade!=after_grade:
            raise RuntimeError('original source/result custody changed')
        custody={'full_result_tree_before_capture':tree_before_capture,
                 'full_result_tree_after_capture_before_grade':tree_before,'full_result_tree_after_grade':tree_after,
                 'only_mutable_exclusion':'root status.json', 'source_before_capture':before,
                 'source_before_grade':before_grade,'source_after_grade':after_grade,'grades':grades,'new_grade_authored':False}
        with (run/'shared-grade-custody.json').open('x') as handle:json.dump(custody,handle,indent=2,sort_keys=True)
        metric=receipt.get('fixture_execution_conformant')
        passed=code==0 and metric is True and exact and counts.get('collected')==29 and counts.get('executed')==29 and counts.get('passed')==29 and all(counts.get(k)==0 for k in ('failure','error','skipped')) and len(grades)==1 and (grades[0]['Q'],grades[0]['T'])==('Judged','Located')
        status.update(full_result_tree_after_analysis=inventory(run,omit_root_status=True),
                      state='passed' if passed else 'failed',native_metric=metric,junit_counts=counts,exact_cases=exact,grades=grades,exit_code=0 if passed else code or 1)
        return status['exit_code']
    except Exception as exc:
        status.update(state='capture_failed',error=type(exc).__name__+': '+str(exc),exit_code=1)
        return 1
    finally:
        status_path.write_text(json.dumps(status,sort_keys=True)+'\n')

if __name__=='__main__':
    raise SystemExit(main())
