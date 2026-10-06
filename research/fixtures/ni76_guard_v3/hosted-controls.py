"""Disposable Linux runner ONLY. Real kernel flocks; no proc record fixtures."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import select
import sys
import time

SCOPE = Path(os.environ['NI76_SCOPE'])
CAPTURE = SCOPE / 'originals'
LOCKS = Path('/mnt/raid0/llm/tmp')
ENV = dict(os.environ, ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT='1')
QUADS = ['q0', 'q1', 'q2', 'q3']
JOURNAL = CAPTURE / 'downstream.jsonl'
ENV['NI76_JOURNAL'] = str(JOURNAL)
RESULTS = []
HANDLES = []


def snapshot():
    result = {}
    for root in [LOCKS, SCOPE / 'root', SCOPE / 'app']:
        for p in sorted(root.rglob('*')):
            st = p.lstat()
            if p.is_symlink():
                result[str(p)] = {'link': os.readlink(p), 'inode': st.st_ino}
            elif p.is_file():
                result[str(p)] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'inode': st.st_ino}
            else:
                result[str(p)] = {'mode': st.st_mode, 'inode': st.st_ino}
    for p in Path('/tmp').glob('gitnexus-*-analyze.lock'):
        st = p.lstat()
        result[str(p)] = {'mode': st.st_mode, 'inode': st.st_ino,
                          'link': os.readlink(p) if p.is_symlink() else None,
                          'sha256': hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() and not p.is_symlink() else None}
    return result


def run(label, argv, expected, *, cwd=None, env=None, denied=False):
    before = snapshot()
    journal_before = JOURNAL.read_bytes() if JOURNAL.exists() else b''
    (CAPTURE / f'{label}.proc-locks-before').write_text(Path('/proc/locks').read_text())
    (CAPTURE / f'{label}.owner-stat').write_text(Path(f'/proc/{os.getpid()}/stat').read_text())
    (CAPTURE / f'{label}.owner-status').write_text(Path(f'/proc/{os.getpid()}/status').read_text())
    result = subprocess.run(argv, cwd=cwd, env=env or ENV, capture_output=True, timeout=20)
    (CAPTURE / f'{label}.stdout').write_bytes(result.stdout)
    (CAPTURE / f'{label}.stderr').write_bytes(result.stderr)
    (CAPTURE / f'{label}.proc-locks-after').write_text(Path('/proc/locks').read_text())
    after = snapshot()
    record = {'label': label, 'argv': list(map(str, argv)), 'exit_code': result.returncode,
              'expected': expected, 'before': before, 'after': after,
              'owner_pid': os.getpid(), 'denial_no_mutation_required': denied}
    case_path = CAPTURE / f'{label}.case.json'
    with case_path.open('x') as case_file:
        json.dump(record, case_file, indent=2)
    RESULTS.append(case_path)
    assert result.returncode == expected, (label, result.returncode, result.stderr)
    if denied:
        assert before == after, ('mutated on refusal', label)
        assert journal_before == (JOURNAL.read_bytes() if JOURNAL.exists() else b''), ('child called on refusal', label)
    return result


def acquire():
    assert not HANDLES
    for role in ['GLOBAL', 'build']:
        for q in QUADS:
            p = LOCKS / f'cpu_region.{role}.{q}.lock'
            f = open(p, 'w+b')
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if role == 'build':
                f.write((json.dumps({'schema_version': 1, 'pid': os.getpid(), 'role': 'build',
                       'region': q, 'regions': QUADS, 'request_tag': 'ni76-disposable',
                       'started_at': time.time()}) + '\n').encode())
                f.flush()
            HANDLES.append(f)


def release():
    for f in HANDLES:
        f.close()
    HANDLES.clear()


def endpoints(repo):
    source = SCOPE / repo
    result = [('guard', ['/usr/bin/python3', '-I', str(source / 'scripts/gitnexus-guard.py'), '--repo', repo]),
              ('wrapper', ['/bin/bash', str(source / 'scripts/gitnexus-analyze.sh'), '--index-only'])]
    if repo == 'root':
        result.append(('direct-js', [os.environ['NI76_REAL_NODE'], str(source / 'scripts/gitnexus-patch.js')]))
    return result


def all_denied(label, env=None):
    for repo in ['root', 'app']:
        for kind, argv in endpoints(repo):
            run(f'{label}-{repo}-{kind}', argv, 64, cwd=SCOPE / repo, env=env, denied=True)


def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true", "hosted runner only"
    assert not Path("/workspace/repos").exists(), "canonical host paths forbidden"
    assert not LOCKS.exists() and not LOCKS.is_symlink(), 'disposable fixed root must be absent'
    LOCKS.mkdir(parents=True, mode=0o700)
    fake = SCOPE / 'fake-bin'
    fake.mkdir(mode=0o700)
    fake_cli = '''#!/usr/bin/python3
import json,os,sys,time
from pathlib import Path
if sys.argv[1:] == ['analyze','--help']:
    print('--skip-skills');sys.exit(0)
p=Path(os.environ['NI76_JOURNAL'])
with p.open('a') as f: f.write(json.dumps({'argv':sys.argv,'pid':os.getpid()})+'\\n')
repo=Path.cwd().name
lock=Path('/tmp')/('gitnexus-epyc-root-analyze.lock' if repo=='root' else 'gitnexus-app-analyze.lock')
st=lock.stat(); matches=[]
for fd in Path('/proc/self/fd').iterdir():
    try:
        s=os.fstat(int(fd.name))
        if (s.st_dev,s.st_ino)==(st.st_dev,st.st_ino):matches.append(int(fd.name))
    except OSError:pass
assert matches, 'writer FD not inherited'
if os.environ.get('NI76_HOLD_WRITER'):
    Path(os.environ['NI76_HOLD_WRITER']).write_text(str(os.getpid()))
    time.sleep(8)
'''
    (fake / 'gitnexus').write_text(fake_cli); (fake / 'gitnexus').chmod(0o700)
    # Real Node executes the unchanged independently guarded patcher; no global resolution
    # occurs because scratch target is an already-sentinel-patched fixture.
    ENV['PATH'] = str(fake) + ':' + os.environ['PATH']
    target = SCOPE / 'analyze.js'
    target.write_text('EPYC-NONTTY-PROGRESS-PATCH v1\n')
    ENV['GITNEXUS_DIST_ANALYZE'] = str(target)
    for repo in ['root', 'app']:
        subprocess.run(['git', 'init', '-q', str(SCOPE / repo)], check=True, timeout=10)
        writer = Path('/tmp') / ('gitnexus-epyc-root-analyze.lock' if repo == 'root' else 'gitnexus-app-analyze.lock')
        assert not writer.exists() and not writer.is_symlink()
        writer.write_bytes(b'writer-content-must-survive\n')
    all_denied('no-claim')
    all_denied('ci-without-claim', dict(ENV, CI='true'))
    acquire()
    for repo in ['root', 'app']:
        for kind, argv in endpoints(repo):
            run(f'positive-{repo}-{kind}', argv, 0, cwd=SCOPE / repo)
    for repo in ['root','app']:
        run('fifo-open-race-'+repo, ['/usr/bin/python3','-I',str(Path(__file__).with_name('race-controls.py')),
            str(SCOPE/repo/'scripts/gitnexus-guard.py')],64,cwd=SCOPE/repo,denied=True)
    for name in ['ORCHESTRATOR_TMP_DIR', 'ORCHESTRATOR_PATHS_TMP_DIR', 'TMP_DIR']:
        all_denied('wrong-root-' + name, dict(ENV, **{name: str(SCOPE)}))
    p = LOCKS / 'cpu_region.build.q0.lock'
    original = p.read_bytes()
    payload = json.loads(original)
    for field, value in [('pid', os.getpid()+123456), ('role', 'bench'), ('region', 'q3'), ('regions', ['q0'])]:
        bad = dict(payload, **{field: value}); p.write_text(json.dumps(bad))
        all_denied('payload-' + field)
        p.write_bytes(original)
    # The valid owner's real FLOCK remains held while attribution types are invalid.
    for label, field, value in [('schema-bool', 'schema_version', True),
                                ('pid-float', 'pid', float(os.getpid()))]:
        bad = dict(payload, **{field: value}); p.write_text(json.dumps(bad))
        all_denied('payload-' + label)
        p.write_bytes(original)
    # Keep real lock on prior inode while names point at a genuinely unlocked new inode.
    old = LOCKS / 'held-original'
    p.rename(old); p.write_bytes(original)
    all_denied('wrong-inode')
    p.unlink(); old.rename(p)
    p.rename(old); p.symlink_to(old)
    all_denied('claim-symlink')
    p.unlink(); os.mkfifo(p)
    all_denied('claim-fifo')
    p.unlink(); old.rename(p)
    for repo in ['root', 'app']:
        writer = Path('/tmp') / ('gitnexus-epyc-root-analyze.lock' if repo == 'root' else 'gitnexus-app-analyze.lock')
        saved = writer.read_bytes(); writer.unlink()
        writer.symlink_to(target)
        run('writer-symlink-' + repo, endpoints(repo)[1][1], 64, cwd=SCOPE/repo, denied=True)
        writer.unlink(); os.mkfifo(writer)
        run('writer-fifo-' + repo, endpoints(repo)[1][1], 64, cwd=SCOPE/repo, denied=True)
        writer.unlink(); os.link(target,writer)
        run('writer-hardlink-'+repo,endpoints(repo)[1][1],64,cwd=SCOPE/repo,denied=True)
        writer.unlink(); writer.write_bytes(saved)
        with writer.open('r+b') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run('writer-contention-' + repo, endpoints(repo)[1][1], 75, cwd=SCOPE/repo, denied=True)
        assert writer.read_bytes() == saved
        ready = CAPTURE / ('writer-ready-' + repo)
        child = subprocess.Popen(endpoints(repo)[1][1], cwd=SCOPE/repo, env=dict(ENV, NI76_HOLD_WRITER=str(ready)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            end = time.monotonic()+5
            while not ready.exists() and time.monotonic()<end: time.sleep(.05)
            assert ready.exists(), 'child did not reach inherited writer FD'
            run('writer-lifetime-contention-' + repo, endpoints(repo)[1][1], 75, cwd=SCOPE/repo, denied=True)
            out,err=child.communicate(timeout=15); assert child.returncode==0,(out,err)
        finally:
            if child.poll() is None:
                child.terminate(); child.wait(timeout=5)
    release()
    all_denied('unlocked-stale-payload')
    # A real same-UID sibling owner is not an ancestor: keep it alive until refusal captured.
    read_ready,write_ready=os.pipe(); read_stop,write_stop=os.pipe()
    child=os.fork()
    if child==0:
        os.close(read_ready);os.close(write_stop)
        acquire();os.write(write_ready,b'1');os.read(read_stop,1);release();os._exit(0)
    os.close(write_ready);os.close(read_stop)
    try:
        assert select.select([read_ready], [], [], 5)[0], 'owner readiness timeout'
        assert os.read(read_ready,1)==b'1'
        all_denied('wrong-owner')
    finally:
        os.write(write_stop,b'1');os.close(write_stop);os.close(read_ready)
        assert os.waitpid(child,0)[1]==0
    # Compatibility with the actual source producer, not only hand-created payloads.
    for fifo in ['0','1']:
        for repo in ['root','app']:
            label='native-cli-positive-fifo-'+fifo+'-'+repo
            run(label,
                ['/usr/bin/python3','-m','src.runtime.region_lock_cli','run','--role','build',
                 '--regions','q0,q1,q2,q3','--timeout-s','5','--no-preflight','--',
                 '/usr/bin/python3','-I',str(Path(__file__).with_name('native-child.py')),
                 str(SCOPE/repo/'scripts/gitnexus-guard.py'),repo,label],
                 0,cwd=SCOPE/'app',env=dict(ENV,EPYC_LOCK_FIFO=fifo))
    journal = [json.loads(line) for line in JOURNAL.read_text().splitlines()]
    assert journal and all(r['argv'][1:] == ['analyze','--skip-agents-md','--skip-skills','--index-only'] for r in journal)
    (CAPTURE/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULTS),
       'kernel_records':'real /proc/locks only','native_cli_preflight':'disabled only in disposable runner; actual GLOBAL/write locks still mandatory',
       'claim':'admission only; no continuous lifetime assurance'}))



def write_cases():
    """Aggregate actual immutable records on completion or Python failure."""
    with (CAPTURE / 'cases.json').open('x') as cases_file:
        cases_file.write('[\n')
        for position, case_path in enumerate(RESULTS):
            if position:
                cases_file.write(',\n')
            with case_path.open() as case_file:
                while chunk := case_file.read(1024 * 1024):
                    cases_file.write(chunk)
        cases_file.write('\n]\n')

if __name__ == '__main__':
    try:
        main()
    finally:
        write_cases()
