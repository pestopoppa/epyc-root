#!/usr/bin/env python3
"""Self-test for fold_row_guard.py (no GPU, no grant): python3 -I test_fold_row_guard.py"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, 'fold_row_guard.py')
sys.path.insert(0, HERE)
import fold_row_guard as fg  # noqa: E402


def sh(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)


def job(d, verdict, rc=0):
    p = os.path.join(d, 'job.py')
    open(p, 'w').write('import json,sys\njson.dump({"complete": True, "verdict": %r}, open(%r, "w"))\nsys.exit(%d)\n'
                       % (verdict, os.path.join(d, 'out', 'RESULT.json'), rc))
    return p


def main():
    fails = []
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(d + '/out')
        env = dict(os.environ, FILLER_ID='grant-test-1')
        env.pop('FILLER_SMOKE', None); env.pop('FILLER_DRYRUN', None)
        # 1. a stale terminal RESULT with no RUN.json never completes
        json.dump({'complete': True, 'verdict': 'PASS'}, open(d + '/out/RESULT.json', 'w'))
        if sh(sys.executable, G, 'check', '--dir', d).returncode == 0:
            fails.append('stale RESULT without RUN.json passed check')
        # 2. a guarded run moves the stale RESULT aside and binds its own
        r = sh(sys.executable, G, 'run', '--dir', d, '--', sys.executable, job(d, 'FAIL(x)'), env=env)
        run = json.load(open(d + '/out/RUN.json'))
        if r.returncode != 0 or run['run_id'] != 'grant-test-1' or not run['stale_moved_to']:
            fails.append('run did not record run id / stale move: %r %r' % (r.returncode, run))
        elif not os.path.exists(os.path.join(run['stale_moved_to'], 'RESULT.json')):
            fails.append('stale RESULT not moved')
        if sh(sys.executable, G, 'check', '--dir', d).returncode != 0:
            fails.append('fresh guarded RESULT did not pass check')
        # 3. a RESULT rewritten after the run (sha no longer bound) fails
        json.dump({'complete': True, 'verdict': 'PASS'}, open(d + '/out/RESULT.json', 'w'))
        if sh(sys.executable, G, 'check', '--dir', d).returncode == 0:
            fails.append('RESULT rewritten after the run passed check')
        # 4. rc != 0 fails even with a terminal RESULT
        sh(sys.executable, G, 'run', '--dir', d, '--', sys.executable, job(d, 'PASS', 3), env=env)
        if sh(sys.executable, G, 'check', '--dir', d).returncode == 0:
            fails.append('rc 3 run passed check')
        # 5. smoke passes straight through and never writes RUN.json
        os.remove(d + '/out/RUN.json')
        sh(sys.executable, G, 'run', '--dir', d, '--', sys.executable, job(d, 'PASS'), env=dict(env, FILLER_SMOKE='1'))
        if os.path.exists(d + '/out/RUN.json'):
            fails.append('smoke wrote RUN.json')
        # 6. install_guard wraps a fold-row launch.sh
        open(d + '/launch.sh', 'w').write('#!/bin/bash\nD=/x\nexec run.sh --id x --cmd "/usr/bin/python3 -I -B $D/job.py" \\\n'
                                          '  --complete-cmd "/usr/bin/python3 -I $D/check_complete.py" --stop "$D/STOP"\n')
        fg.install_guard(d, G)
        fg.install_guard(d, os.path.join(d, 'fold_row_guard.py'))   # re-install from the row's own copy: no SameFileError
        s = open(d + '/launch.sh').read()
        if 'fold_row_guard.py run --dir $D -- /usr/bin/python3 -I -B $D/job.py' not in s or 'fold_row_guard.py check --dir $D' not in s:
            fails.append('install_guard did not wrap launch.sh: ' + s)
    # 7. touched-libs maps sources to libraries
    with tempfile.TemporaryDirectory() as repo:
        g = lambda *a: sh('git', '-C', repo, *a)
        g('init', '-q'); g('config', 'user.email', 't@t'); g('config', 'user.name', 't')
        os.makedirs(repo + '/src'); os.makedirs(repo + '/ggml/src/ggml-cpu')
        open(repo + '/src/a.cpp', 'w').write('1'); g('add', '-A'); g('commit', '-qm', 'a')
        base = g('rev-parse', 'HEAD').stdout.strip()
        open(repo + '/ggml/src/ggml-cpu/v.h', 'w').write('2'); g('add', '-A'); g('commit', '-qm', 'b')
        tip = g('rev-parse', 'HEAD').stdout.strip()
        libs = fg.touched_libs(repo, base, tip)
        if set(libs) != {'libggml-cpu.so'}:
            fails.append('touched_libs wrong: %r' % libs)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for x, c in ((a, b'1'), (b, b'2')):
                open(x + '/libggml-cpu.so', 'wb').write(c); open(x + '/libllama.so', 'wb').write(b'same')
            if not fg.libs_differ(repo, base, tip, a, b)['ok']:
                fails.append('libs_differ missed a differing touched lib')
            open(b + '/libggml-cpu.so', 'wb').write(b'1')
            if fg.libs_differ(repo, base, tip, a, b)['ok']:
                fails.append('libs_differ passed with the touched lib identical')
    # 8. compound per-recipe verdicts are terminal; a compound with a non-terminal part is not
    if not fg.is_terminal('mtp:ATTRIBUTED_H15|np4mtp:NO_LOSS') or fg.is_terminal('mtp:ATTRIBUTED_H15|np4mtp:RUNNING'):
        fails.append('is_terminal wrong on compound verdicts')
    print('FAIL\n' + '\n'.join(fails) if fails else 'OK 8 checks')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())


def test_all() -> None:
    assert main() == 0
