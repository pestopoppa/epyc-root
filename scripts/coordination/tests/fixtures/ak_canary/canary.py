#!/usr/bin/env python3
"""Offline AK pipeline canary. Invoked by canary_ak_pipeline.sh."""
import contextlib
import io
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
FIX = Path(__file__).resolve().parent


class KnownFailure(Exception):
    pass


def tbo_semantics():
    def unit(name, rc):
        cases = H.tbo_cases((FIX / name).read_text())
        return dict(G.tbo_counts(cases), arm='ON', rc=rc)
    cfg = {'kind': 'tbo', 'min_cases': 1}
    good = unit('tbo-notsupported.log', 0)
    assert good['n_fail'] == 0 and good['n_skipped'] > 0 and G.tbo_pass(cfg, good), good
    bad = unit('tbo-fail.log', 0)
    assert not G.tbo_pass(cfg, bad), bad
    crash = unit('tbo-crash.log', 139)
    if G.tbo_pass(cfg, crash):
        raise KnownFailure('A5: nonzero return code accepted by default')


def server_env_knob():
    s = {'row_id': 'ak-canary', 'knobs': {'GGML_CANARY_KNOB': {'kind': 'env', 'marker': 'canary knob enabled'}},
         'arms': {'OFF': {}, 'ON': {'GGML_CANARY_KNOB': '1'}},
         'server': {'env': {'GGML_CANARY_KNOB': '1'}}}
    assert G.server_env_knob_errors(s), 'server-env knob was accepted'
    with tempfile.TemporaryDirectory(prefix='ak-canary-env-') as d:
        g = G.Gate.__new__(G.Gate)
        g.spec, g.env = s, {}
        assert 'GGML_CANARY_KNOB' not in g.proc_env('OFF')
        assert g.proc_env('ON')['GGML_CANARY_KNOB'] == '1'


def stop_park():
    import rowflow as rf
    import notify
    with fixture_environment() as e:
        rid = 'ak-canary-stop-gpu-20261125'
        rc, output = run_generator(declaration(e, rid))
        assert rc == 0, output
        rowdir = e['rows'] / rid
        spec = json.loads((rowdir / 'spec.json').read_text())
        flags = str(e['flags'])
        rf.publish(spec, flags)
        assert Path(rf.ready_path(flags, rid)).is_file()
        launcher = Path(spec['launcher'])
        stop = Path(spec['stop_file'])
        stop.write_text('owner stop\n')
        os.makedirs(os.path.dirname(rf.pass_path(flags, rid)), exist_ok=True)
        rf.atomic_json(rf.pass_path(flags, rid), {'launcher_sha256': rf.sha256(str(launcher))})
        (e['flags'] / 'grants' / (rid + '.ended')).write_text('rc=75 time=2026-11-23T10:00:00Z reason=stopped\n')
        old = rf.OWNER_STOP_REQUEUE
        rf.OWNER_STOP_REQUEUE = False
        try:
            assert rf.autorequeue_decision(flags, rid)[0] == 'stop-parked'
            rf.autorequeue(flags, log=lambda *_: None)
            assert Path(rf.ready_path(flags, rid)).exists(), 'parked row lost its ready record'
            inbox = Path(notify.inbox_path(flags))
            alerts = [json.loads(line) for line in inbox.read_text().splitlines()] if inbox.exists() else []
            if not any('stop-parked' in str(a) and 'autokernel' in str(a) for a in alerts):
                raise KnownFailure('R10: stop-parked owner alert missing')
        finally:
            rf.OWNER_STOP_REQUEUE = old


def family_no_strike():
    import publish_row as P
    import family_strikes as F
    import rowflow as rf
    with tempfile.TemporaryDirectory(prefix='ak-canary-family-') as d:
        root = Path(d)
        for sub in ('ready', 'grants', 'dryrun'):
            (root / sub).mkdir()
        base = 'ak-canary-family-gpu-20261125'
        for i in (1, 2):
            rid = f'{base}-r{i}'
            rf.atomic_json(rf.ready_path(d, rid), {'id': rid, 'owner': 'autokernel', 'lane': 'gpu'})
            p = root / 'dryrun' / rid / 'FAIL-1.json'
            p.parent.mkdir()
            p.write_text(json.dumps({'id': rid, 'failclass': {'side': 'harness'}, 'reason': 'synthetic harness error'}))
            P.record_family_outcome(d, rid, 'FAIL', 'synthetic harness error', f'failure-{i}')
        stem = F.stem_of(base)
        count = F.load(d, stem).get('count', 0)
        parked = F.park_reason(d, stem)
        for i in (3, 4):
            rid = f'{base}-r{i}'
            rf.atomic_json(rf.ready_path(d, rid), {'id': rid, 'owner': 'autokernel', 'lane': 'gpu'})
            p = root / 'dryrun' / rid / 'FAIL-1.json'
            p.parent.mkdir()
            p.write_text(json.dumps({'id': rid, 'failclass': {'side': 'candidate'}}))
            P.record_family_outcome(d, rid, 'FAIL', 'synthetic candidate error', f'failure-{i}')
        assert F.load(d, stem).get('count', 0) >= 2 and F.park_reason(d, stem), 'candidate control did not park'
        if count or parked:
            raise KnownFailure(f'P15: harness failures caused {count} family strikes')


def static_launch_faults():
    import publish_row as P
    import preflight as PF
    import rowflow as rf
    with tempfile.TemporaryDirectory(prefix='ak-canary-launch-') as d:
        root = Path(d)
        engine = root / 'filler_run15.sh'
        engine.write_text('#!/bin/sh\n')
        job = root / 'job.py'
        job.write_text(f"SERVER_ARGV = {[str(root / 'missing/llama-server'), '-t', '999']!r}\n")
        launch = root / 'launch.sh'
        launch.write_text(f'#!/bin/bash\n: "${{AK_CANARY_REQUIRED:?required}}"\n'
                          f'exec bash {engine} --id fixture --class cpu --min-window 300 '
                          f'--stop {root}/STOP --workdir {root} --complete-cmd "true" --cmd "python3 {job}"\n')
        spec = {'id': 'ak-canary-static-cpu-20261125', 'launcher': str(launch), 'owner': 'autokernel',
                'regions': '84-87', 'declared_threads': 999}
        lane_findings = PF.check_lane(PF.Row(spec), {'nodes': ({}, {})})
        assert any(code == 'THREADS-OVERSUB' for _, code, _ in lane_findings), lane_findings
        refused = False
        try:
            P.publish_rehearsal(spec, str(root / 'flags'))
        except rf.Refused as e:
            text = str(e)
            assert 'AK_CANARY_REQUIRED' in text and 'binary missing' in text, text
            refused = True
        if not refused:
            warnings = '\n'.join(spec.get('publish_warnings', []))
            assert 'AK_CANARY_REQUIRED' in warnings and 'binary missing' in warnings, warnings
        from unittest import mock
        flags = root / 'flags'
        for part in ('ready', 'grants', 'dryrun'):
            (flags / part).mkdir(parents=True)
        specfile = root / 'spec.json'
        specfile.write_text(json.dumps(spec))
        report = io.StringIO()
        with mock.patch.object(P, 'REPO', str(root / 'repo')), mock.patch.object(P, '_toolroot_banner'), \
             mock.patch.object(P, 'check_owner_roster'), contextlib.redirect_stdout(report), contextlib.redirect_stderr(report):
            P.main([str(specfile), '--rehearse', '--flags', str(flags)])
        text = report.getvalue()
        if refused:
            assert '[publish-rehearsal]' in text and 'AK_CANARY_REQUIRED' in text and 'binary missing' in text, text
        if PF.PREFLIGHT_ENFORCE.get('lane'):
            assert 'THREADS-OVERSUB' in text and '[preflight]' in text, text
        if not refused or not PF.PREFLIGHT_ENFORCE.get('lane'):
            raise KnownFailure('P1/P2: static launch and lane checks are not enforced')


def box_source():
    import publish_row as P
    import rowflow as rf
    with tempfile.TemporaryDirectory(prefix='ak-canary-view-') as d:
        root = Path(d)
        def git(*args):
            return subprocess.run(['git', '-C', d, *args], text=True, capture_output=True, check=True).stdout.strip()
        git('init', '-q')
        git('config', 'user.name', 'AK Canary')
        git('config', 'user.email', 'ak-canary@example.invalid')
        handoff = root / 'handoffs/active/handoff.md'
        handoff.parent.mkdir(parents=True)
        handoff.write_text('# stale view\n')
        git('add', 'handoffs/active/handoff.md')
        git('commit', '-qm', 'stale view')
        stale_sha = git('rev-parse', 'HEAD')
        handoff.write_text((FIX / 'handoff.md').read_text())
        git('commit', '-qam', 'origin box')
        git('update-ref', 'refs/remotes/origin/main', git('rev-parse', 'HEAD'))
        git('checkout', '-q', stale_sha)
        assert 'AK-CANARY-OK' not in handoff.read_text()
        origin = git('show', 'origin/main:handoffs/active/handoff.md')
        assert 'AK-CANARY-OK' in origin
        try:
            P.task_box({'handoff_task': 'handoff.md:AK-CANARY-OK'}, repo=d)
        except rf.Refused as e:
            msg = str(e)
            if 'VIEW-STALE' not in msg and stale_sha not in msg:
                if 'no checkbox' in msg:
                    raise KnownFailure('P3: stale view refusal omits the view SHA')
                raise AssertionError(msg)


def alert_routing():
    import rowflow as rf
    import notify
    with tempfile.TemporaryDirectory(prefix='ak-canary-alert-') as d:
        root = Path(d)
        (root / 'dryrun').mkdir()
        os.environ['ROWFLOW_AKLOOP_DIR'] = str(ROOT / 'scripts/coordination/akloop')
        row = {'owner': 'autokernel', 'launcher': {'path': str(root / 'none')}}
        rec = rf.record_fail(d, 'ak-canary-harness-gpu-20261125', row, 'no ended record', {})
        assert rec['failclass']['side'] == 'harness', rec
        entries = [json.loads(x) for x in Path(notify.inbox_path(d)).read_text().splitlines()]
        owners = {x.get('row_owner') or x.get('owner') for x in entries}
        assert {'autokernel', 'pipeline-mgmt'} <= owners, entries
        rec = rf.record_fail(d, 'ak-canary-unknown-gpu-20261125', row, 'unrecognised synthetic failure', {})
        assert rec['failclass']['side'] == 'unknown', rec
        entries = [json.loads(x) for x in Path(notify.inbox_path(d)).read_text().splitlines()
                   if 'ak-canary-unknown-gpu-20261125' in x]
        owners = {x.get('row_owner') or x.get('owner') for x in entries}
        pending = []
        if not {'autokernel', 'pipeline-mgmt'} <= owners:
            pending.append('R2 unknown classification routing')
        key = notify.event_key('ak-canary', 'fixture', 'stale')
        marker = notify._marker(d, key)
        Path(marker).parent.mkdir(parents=True, exist_ok=True)
        claim = marker + '.claim'
        Path(claim).write_text('stale')
        os.utime(claim, (1, 1))
        if not notify.emit(d, 'ak-canary', 'fixture', 'stale', 'test', 'warning', owner='autokernel'):
            pending.append('N2 stale claim')
        if pending:
            raise KnownFailure(', '.join(pending))


@contextlib.contextmanager
def fixture_environment():
    import mk_ak_row as M
    import publish_row as P
    import rowflow as R
    import shutil
    from unittest import mock
    with tempfile.TemporaryDirectory(prefix='ak-canary-row-') as d:
        root = Path(d)
        repo = root / 'repo'
        (repo / 'handoffs/active').mkdir(parents=True)
        (repo / 'handoffs/active/handoff.md').write_text((FIX / 'handoff.md').read_text())
        shutil.copytree(ROOT / 'scripts/handoffs', repo / 'scripts/handoffs',
                        ignore=shutil.ignore_patterns('tests', '__pycache__'))
        flags = root / 'flags'
        for part in ('ready', 'grants', 'dryrun'):
            (flags / part).mkdir(parents=True)
        rows = root / 'rows'
        rows.mkdir()
        store = root / 'kernels/builds/gpu-20261125-abcdef123-gate'
        shutil.copytree(FIX / 'fake-store', store, symlinks=False)
        # Fixture links resolve relative to their original location before copying.
        (store / 'BUILD-IDENTITY.json').write_text(json.dumps({'source_sha': 'abcdef1234567'}))
        (store / 'bin/libggml-hip.so').write_text('GGML_CANARY_KNOB\ncanary knob enabled\n')
        engine = root / 'filler_run15.sh'
        engine.write_text('#!/bin/sh\n# CONTRACT_LOCK\nexit 0\n')
        engine.chmod(0o755)
        model = root / 'Canary-Q8_0.gguf'
        model.write_bytes(b'GGUF')
        env = {'repo': repo, 'flags': flags, 'rows': rows, 'store': store, 'model': model, 'engine': engine}
        with mock.patch.object(P, 'REPO', str(repo)), mock.patch.object(R, 'TMP', str(root) + '/'), \
             mock.patch.object(P, 'check_owner_roster', lambda *a, **k: None), \
             mock.patch.object(M, 'FILLER', str(engine)), \
             mock.patch.dict(os.environ, {'ROWFLOW_NO_VIEW_REFRESH': '1', 'ROWFLOW_FLAGS': str(flags),
                                         'PREFLIGHT_CACHE': str(root / 'pfcache')}, clear=False):
            yield env


def declaration(e, rid, task='AK-CANARY-OK', extra=()):
    server = e['store'] / 'bin/llama-server'
    argv = [str(server), '-m', str(e['model']), '--port', '{PORT}', '-t', '8']
    return ['gate', 'new', '--id', rid, '--task', 'handoff.md:' + task, '--model', 'Canary-Q8_0',
            '--root', str(e['rows']), '--flags', str(e['flags']), '--knob', 'GGML_CANARY_KNOB:canary knob enabled::4',
            '--arm', 'OFF:', '--arm', 'OFF2:', '--arm', 'ON:GGML_CANARY_KNOB=1', '--metric', 'ms_per_round',
            '--keep-rule', 'ci_lower>1.01,n=8,look=4,aa=0.02', '--server-argv-json', json.dumps(argv),
            '--prompt', 'canary prompt', '--rank', '45', *extra]


def run_generator(args):
    import mk_ak_row as M
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            rc = M.main(args)
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 2
            if isinstance(exc.code, str):
                print(exc.code, file=out)
    return rc, out.getvalue()


def witness_scope():
    with fixture_environment() as e:
        tbo = [{'kind': 'tbo', 'witness': True, 'argv': [str(e['store'] / 'bin/test-backend-ops')],
                'arms': ['OFF', 'ON'], 'ops': {'OFF': 'MUL_MAT', 'ON': 'MUL_MAT'},
                'min_cases': {'OFF': 1, 'ON': 1}}]
        base = declaration(e, 'ak-canary-scope-gpu-20261125', extra=['--check-only', '--correctness', json.dumps(tbo)])
        # Current ak_gate exempts TBO unless the declaration opts into unit witness.
        rc, out = run_generator(base)
        assert rc == 0, out
        present = {'tbo': {'ON': {'GGML_CANARY_KNOB': 'present'}}}
        rc, out = run_generator(base + ['--expect-by-unit', json.dumps(present)])
        assert rc == 2 and 'witness scope' in out.lower(), out
        ignore = {'tbo': {'ON': {'GGML_CANARY_KNOB': 'ignore'}}}
        rc, out = run_generator(base + ['--expect-by-unit', json.dumps(ignore)])
        assert rc == 0, out


def generator_shape():
    with fixture_environment() as e:
        rid = 'ak-canary-shape-gpu-20261125'
        rc, out = run_generator(declaration(e, rid, extra=['--no-rehearse']))
        assert rc == 0, out
        row = e['rows'] / rid
        spec = json.loads((row / 'spec.json').read_text())
        assert spec['regions'] == 'mi210_0,88-95,184-191', spec
        assert spec['estimate_basis']['units'] > 0 and 'scratch_gb' in spec
        ns = {}
        # The generated job is a declaration; import it with its vendored modules.
        import importlib.util
        from unittest import mock
        with mock.patch.object(sys, 'path', [str(row)] + sys.path):
            sp = importlib.util.spec_from_file_location('ak_canary_job', row / 'job.py')
            job = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(job)
        assert job.SPEC['server']['env']['LD_LIBRARY_PATH'].split(':')[0] == str(e['store'] / 'bin')
        args = declaration(e, 'ak-canary-direction-gpu-20261125', extra=['--no-rehearse', '--lower-is-better'])
        args[args.index('ms_per_round')] = 'tok_s'
        rc, out = run_generator(args)
        assert rc == 2 and 'contradicts' in out, out


def all_refusals_once():
    with fixture_environment() as e:
        rid = 'ak-canary-refusals-gpu-20261125'
        path = e['repo'] / 'handoffs/active/handoff.md'
        lines = path.read_text().splitlines()
        path.write_text('\n'.join(line.replace('on model Canary-Q8_0, store canary;', ';')
                                  if 'AK-CANARY-TICKED' in line else line for line in lines) + '\n')
        args = declaration(e, rid, task='AK-CANARY-TICKED')
        index = args.index('--server-argv-json') + 1
        argv = json.loads(args[index])
        argv[argv.index('-t') + 1] = '999'
        args[index] = json.dumps(argv)
        rc, out = run_generator(args)
        assert rc == 2 and 'not open' in out and 'identity incomplete' in out, out
        assert not (e['rows'] / rid).exists(), out
        assert 'THREADS-OVERSUB' in out, out
        missing_threads = out.count('FIX:') < 3
        rc, clean = run_generator(declaration(e, 'ak-canary-clean-gpu-20261125'))
        assert rc == 0, clean
        if missing_threads:
            raise KnownFailure('P2: thread oversubscription is not enforced in the rehearsal')


def stub_smoke():
    import socket
    import time
    with fixture_environment() as e:
        rid = 'ak-canary-smoke-cpu-20261125'
        rc, out = run_generator(declaration(e, rid, extra=['--no-rehearse', '--lane', 'cpu', '--claim', '84-87']))
        assert rc == 0, out
        row = e['rows'] / rid
        spec = json.loads((row / 'spec.json').read_text())
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        t0 = str(int(time.time()))
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(row), 'FILLER_DRYRUN': '1', 'FILLER_SMOKE': '1',
               'FILLER_SMOKE_T0': t0, 'FILLER_PORTS': str(port), 'FILLER_CPUS': '84-87'}
        p = subprocess.run([sys.executable, '-I', '-B', str(row / 'job.py')], cwd=row, env=env,
                           capture_output=True, text=True, timeout=45)
        assert p.returncode == 0, p.stdout + p.stderr
        term = json.loads((row / 'out/TERMINAL-smoke.json').read_text())
        assert term['ok'] is True, term
        assert (row / 'out-smoke/smoke_measure.json').is_file()
        p = subprocess.run(['/bin/bash', '-c', spec['smoke_predicate']], cwd=row, env=env,
                           capture_output=True, text=True, timeout=10)
        assert p.returncode == 0, p.stdout + p.stderr


def manifest():
    result = []
    for line in (ROOT / 'scripts/coordination/INSTALL.manifest').read_text().splitlines():
        fields = line.split('#', 1)[0].split()
        if len(fields) >= 2:
            result.append((fields[0], fields[1]))
    return result


def deployed_parity():
    import hashlib
    entries = manifest()
    origin = os.environ.get('ORIGIN', 'origin/main')
    for dst, src in entries:
        blob = subprocess.run(['git', '-C', str(ROOT), 'show', f'{origin}:{src}'],
                              capture_output=True, check=True).stdout
        path = STAGE / dst
        assert path.is_file(), f'missing {dst}'
        assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(blob).digest(), f'drift {dst}'
    deployed = STAGE / 'bin/rowflow/DEPLOYED.json'
    if deployed.exists():
        actual = json.loads(deployed.read_text()).get('sha')
        expected = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', origin],
                                  text=True, capture_output=True, check=True).stdout.strip()
        assert actual == expected, f'DEPLOYED.json.sha {actual} != {expected}'
    rowflow = STAGE / 'bin/rowflow'
    expected = {p for p, _ in entries}
    extras = sorted(str(p.relative_to(STAGE)) for p in rowflow.iterdir()
                    if p.is_file() and str(p.relative_to(STAGE)) not in expected and p.name != 'DEPLOYED.json')
    if extras:
        return 'WARN extras: ' + ', '.join(extras)


def install_imports():
    import ast
    import py_compile
    import re
    names = {pub for pub, _ in manifest()}
    dirs = sorted({str(STAGE / Path(pub).parent) for pub, _ in manifest() if pub.endswith('.py')})
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(WORK), 'ROWFLOW_FLAGS': str(WORK / 'flags'),
           'ROWFLOW_TMP': str(WORK) + '/', 'PYTHONPATH': ''}
    missing, broken = [], []
    local_modules = {}
    for pub, src in manifest():
        if pub.endswith('.py'):
            local_modules.setdefault(Path(src).stem, set()).add(pub)
    for pub, src in manifest():
        if not pub.endswith('.py'):
            continue
        path = STAGE / pub
        source = path.read_text()
        try:
            tree = ast.parse(source, filename=pub)
            py_compile.compile(str(path), cfile=str(WORK / ('compile-' + str(len(local_modules)) + '.pyc')), doraise=True)
        except (SyntaxError, ValueError, py_compile.PyCompileError) as e:
            broken.append(f'{pub}: {e}')
            continue
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [a.name.split('.')[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules = [node.module.split('.')[0]]
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '__import__' \
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                modules = [node.args[0].value.split('.')[0]]
            for mod in modules:
                candidate = str(Path(pub).parent / (mod + '.py'))
                if mod in local_modules and candidate not in names:
                    missing.append(f'{pub}: {candidate}')
            if isinstance(node, ast.Call):
                call = ast.unparse(node.func)
                if call.endswith(('spec_from_file_location', 'subprocess.run', 'subprocess.Popen', 'subprocess.call',
                                  'subprocess.check_call', 'subprocess.check_output', 'os.system')):
                    for arg in ast.walk(node):
                        if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                            continue
                        ref = arg.value
                        if not re.search(r'\.(?:py|sh)$', ref):
                            continue
                        source_ref = Path(ref) if os.path.isabs(ref) else ROOT / Path(src).parent / ref
                        if str(source_ref).startswith('/workspace/'):
                            source_ref = ROOT / str(source_ref)[len('/workspace/'):]
                        if source_ref.is_file():
                            try:
                                source_rel = str(source_ref.resolve().relative_to(ROOT))
                            except ValueError:
                                continue
                            if source_rel not in {source for _, source in manifest()}:
                                missing.append(f'{pub}: uninstalled reference {source_rel}')
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'join' \
                    and len(node.args) >= 2 and isinstance(node.args[0], ast.Name) and node.args[0].id in ('HERE', '_HERE') \
                    and all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in node.args[1:]):
                parts = [x.value for x in node.args[1:]]
                candidate = Path(os.path.normpath(str(Path(pub).parent.joinpath(*parts))))
                src_candidate = ROOT / Path(src).parent.joinpath(*parts)
                if src_candidate.is_file() and str(candidate) not in names:
                    missing.append(f'{pub}: {candidate}')
        code = 'import sys;sys.path[:0]=' + repr([str(path.parent)]) + ';import ' + path.stem
        p = subprocess.run([sys.executable, '-I', '-B', '-c', code], env=env, capture_output=True, text=True, timeout=8)
        if p.returncode:
            reason = (p.stderr or p.stdout).strip().splitlines()[-1:]
            if reason and ('ModuleNotFoundError' in reason[0] or 'ImportError' in reason[0]):
                missing.append(f'{pub}: {reason[0]}')
            else:
                broken.append(f'{pub}: {reason}')
    # Shell entry points can source or execute a sibling script without a Python import.
    for pub, src in manifest():
        if not pub.endswith('.sh'):
            continue
        for ref in re.findall(r'(?m)(?:^|[;\s])(?:source|\.|bash|sh)\s+([A-Za-z0-9_./-]+\.sh)\b', (STAGE / pub).read_text()):
            source_ref = (ROOT / Path(src).parent / ref).resolve()
            if source_ref.is_file():
                try:
                    source_rel = str(source_ref.relative_to(ROOT))
                except ValueError:
                    continue
                if source_rel not in {source for _, source in manifest()}:
                    missing.append(f'{pub}: uninstalled reference {source_rel}')
    assert not broken, '; '.join(broken)
    if missing:
        raise KnownFailure('I2/I3: ' + '; '.join(missing[:4]))


def server_env_cli():
    server_env_knob()
    with fixture_environment() as e:
        rid = 'ak-canary-env-gpu-20261125'
        rc, out = run_generator(declaration(e, rid, extra=['--check-only', '--server-env', 'GGML_CANARY_KNOB=1']))
        assert rc == 2 and 'server-env knob' in out.lower(), out


def main():
    import shutil
    global WORK, STAGE, G, H
    with tempfile.TemporaryDirectory(prefix='ak-canary-') as tmp:
        WORK = Path(tmp)
        (WORK / 'flags').mkdir()
        os.environ.update(ROWFLOW_FLAGS=str(WORK / 'flags'), ROWFLOW_TMP=str(WORK) + '/',
                          ROWFLOW_NO_VIEW_REFRESH='1', PREFLIGHT_CACHE=str(WORK / 'cache'))
        stage = os.environ.get('STAGE')
        STAGE = Path(stage).resolve() if stage else WORK / 'stage'
        if not stage:
            for dst, src in manifest():
                target = STAGE / dst
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copyfile(ROOT / src, target)
                except OSError:
                    pass  # C0/C7 report missing files; still execute the other steps.
        sys.path[:0] = sorted({str(STAGE / Path(pub).parent) for pub, _ in manifest()})
        try:
            import ak_gate as G
            import ak_row_harness as H
        except Exception:
            G = H = None  # Individual steps report their own failures and continue.
        steps = [('C0 install-imports', install_imports), ('C1 witness-scope', witness_scope),
                 ('C2 tbo-semantics', tbo_semantics), ('C3 server-env-knob', server_env_cli),
                 ('C4 generator-shape', generator_shape), ('C5 all-refusals-once', all_refusals_once),
                 ('C6 box-source', box_source), ('C7 deployed-parity', deployed_parity),
                 ('C8 stop-park', stop_park), ('C9 alert-routing', alert_routing),
                 ('C10 static-launch-faults', static_launch_faults), ('C11 family-no-strike-on-harness', family_no_strike),
                 ('C12 stub-smoke', stub_smoke)]
        failed = False
        for name, fn in steps:
            output = io.StringIO()
            status, reason = 'PASS', ''
            try:
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    reason = fn() or ''
            except KnownFailure as e:
                status, reason = 'KNOWN-FAIL', str(e)
            except Exception as e:
                status, reason, failed = 'FAIL', f'{type(e).__name__}: {e}', True
            reason = ' '.join(str(reason).split())
            print(f'CANARY {name} {status}' + (f' {reason[:1200]}' if reason else ''), flush=True)
        return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
