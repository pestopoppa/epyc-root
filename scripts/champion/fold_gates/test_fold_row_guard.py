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


def test_move_stale_covers_out_smoke(tmp_path) -> None:
    d = str(tmp_path)
    os.makedirs(d + '/out-smoke/stale-old'); os.makedirs(d + '/out')
    for p in ('/out-smoke/RESULT.json', '/out-smoke/log.txt', '/out/TERMINAL-smoke.json', '/out/RESULT.json'):
        open(d + p, 'w').write('{}')
    dst = fg.move_stale(d + '/out-smoke', smoke=True)
    assert sorted(os.listdir(d + '/out-smoke')) == sorted(['stale-old', os.path.basename(dst)])
    assert sorted(os.listdir(dst)) == ['RESULT.json', 'log.txt', 'out.TERMINAL-smoke.json']
    assert os.path.exists(d + '/out/RESULT.json')          # the real RESULT is not a smoke file
    assert fg.move_stale(d + '/out-smoke', smoke=True) is None


def test_kld_floor_header() -> None:
    saved = dict(fg.KLD_FLOOR)
    fg.KLD_FLOOR.update({'gpu': None, 'cpu': None})
    try:
        h = fg.kld_floor_header('gpu', 0.0012, floor=None)
    finally:
        fg.KLD_FLOOR.update(saved)
    assert h['kld_floor'] is None and h['candidate_kld_over_floor'] is None and 'UNMEASURED' in h['kld_floor_status']
    h = fg.kld_floor_header('cpu', 0.0012, floor=(0.0003, 'row-x'))
    assert abs(h['candidate_kld_over_floor'] - 4.0) < 1e-9 and abs(h['kld_gate_over_floor'] - 10.0) < 1e-9 and h['kld_floor_source'] == 'row-x'
    h = fg.kld_floor_header('gpu', 0.0, floor=0.0)
    assert h['kld_floor_status'] == 'MEASURED_ZERO' and h['candidate_kld_over_floor'] is None


def test_kld_floor_table_matches_filed_results() -> None:
    for dev, rid in (('gpu', 'fold-kld-floor-gpu-20261124-r2'), ('cpu', 'fold-kld-floor-cpu-20261124')):
        floor, row, sha = fg.KLD_FLOOR[dev]
        assert row.startswith(rid) and len(sha) == 64
        p = '/mnt/raid0/llm/tmp/%s/out/RESULT.json' % rid
        if os.path.exists(p):
            assert abs(json.load(open(p))['detail']['floor_kld'] - floor) < 1e-12 and fg.sha256(p) == sha


def test_kld_gpu_absolute_zero_floor() -> None:
    assert fg.KLD_GATE_MODE == {'gpu': 'absolute', 'cpu': 'relative'}
    h = fg.kld_floor_header('gpu', 0.001)
    assert h['kld_floor'] == 0.0 and h['candidate_kld_over_floor'] is None and h['kld_gate_over_floor'] is None
    assert fg.kld_gate_verdict('gpu', 0.0029)[0] and not fg.kld_gate_verdict('gpu', 0.0031)[0]
    assert fg.kld_gate_verdict('gpu', 0.0029)[1]['kld_gate_effective'] == fg.KLD_GATE


def test_kld_cpu_relative() -> None:
    fl = fg.KLD_FLOOR['cpu'][0]
    assert fg.kld_gate_verdict('cpu', fl)[0]                  # at the floor passes (absolute 0.003 would fail)
    assert fg.kld_gate_verdict('cpu', fl * 1.5)[0]
    assert not fg.kld_gate_verdict('cpu', fl * 3)[0]          # well above the floor fails
    assert not fg.kld_gate_verdict('cpu', 0.2)[0]
    assert abs(fg.kld_gate_verdict('cpu', fl)[1]['kld_gate_effective'] - fl * 1.5) < 1e-12


def test_kld_missing_floor_fails_closed() -> None:
    saved = dict(fg.KLD_FLOOR)
    fg.KLD_FLOOR['cpu'] = None
    try:
        ok, d = fg.kld_gate_verdict('cpu', 0.0)
        assert not ok and 'fail closed' in d['reason']
    finally:
        fg.KLD_FLOOR.update(saved)
    assert not fg.kld_gate_verdict('npu', 0.0)[0]
    assert not fg.kld_gate_verdict('cpu', None)[0]
