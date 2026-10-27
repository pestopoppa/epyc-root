#!/usr/bin/env python3
"""Temporary synthetic admission only; no canonical grant or live row write."""
import datetime, os, pathlib, signal, subprocess, time
B = pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep')
I = 'codex-ni-df2-row-exact-build-20261027'
D = B / 'final-admit'; D.mkdir(exist_ok=True); (D / 'grants').mkdir(exist_ok=True)
assert not pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants', I + '.grant').exists()
def run(name, args, env=None):
    with (D / name).open('wb') as f:
        r = subprocess.run([str(x) for x in args], stdout=f, stderr=subprocess.STDOUT, env=env, timeout=30)
    if r.returncode:
        raise RuntimeError((name, r.returncode, (D / name).read_text()[-1200:]))
env = os.environ.copy(); env.update(FILLER_PREFLIGHT='1', FILLER_GRANTS_DIR=str(D/'grants'), FILLER_STATE_DIR=str(D/'state'))
f = (D / 'poller.log').open('wb')
p = subprocess.Popen(['/bin/bash', str(B/'build-poller.sh')], env=env, start_new_session=True, stdout=f, stderr=subprocess.STDOUT)
try:
    for _ in range(100):
        assert p.poll() is None
        if b'filler_run12.sh' in pathlib.Path(f'/proc/{p.pid}/cmdline').read_bytes(): break
        time.sleep(.03)
    else: raise RuntimeError('engine not entered')
    a = [x.strip() for x in (B/'ROW-BACKLOG.md').read_text().strip().strip('|').split('|')]; assert len(a) == 18
    a[2] = str(B/'build-poller.sh') + f'; pid={p.pid}; synthetic admission only'; a[7] = 'ARMED'; a[12] = 'y'
    h = next(x for x in pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/FILLERS.md').read_text().splitlines() if x.startswith('| filler-id |'))
    row = D/'ROW-TEMP.md'; row.write_text(h+'\n|'+'|'.join(['---']*18)+'|\n| '+' | '.join(a)+' |\n')
    run('validator.log', ['/usr/bin/python3','-I','-B','/mnt/raid0/llm/tmp/compute-flags/validate_fillers.py','--file',row,'--row',I,'--for-grant'])
    e = os.environ.copy(); e['GRANT_OK_TEST_FILLERS'] = str(row)
    run('grant-ok.log', ['/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh',I,'24','--window-s','3600','--regions','48-71','--pid',str(p.pid)], e)
    now = datetime.datetime.now(datetime.timezone.utc).replace(second=0,microsecond=0); end = now + datetime.timedelta(seconds=3600)
    g = D/'normal.grant'; g.write_text(f'regions=48-71 start={now:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n')
    run('normal-admit.log', ['/usr/bin/python3','-B',B/'deps/dryrun_check.py','admit','--id',I,'--row-file',row,'--grant',g,'--min-window-s','3300','--require-proof','--engine',B/'deps/filler_run12.sh'])
    print('NORMAL_ADMISSION_VALIDATION_PASS')
finally:
    if p.poll() is None: os.killpg(p.pid, signal.SIGTERM)
    try: p.wait(timeout=10)
    except subprocess.TimeoutExpired: os.killpg(p.pid, signal.SIGKILL); p.wait(timeout=10)
    f.close()
    print(f'temporary poller reaped rc={p.returncode}')
