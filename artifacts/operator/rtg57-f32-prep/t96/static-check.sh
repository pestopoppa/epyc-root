#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/t96/packet
bash -n "$D/launch.sh" "$D/job.sh"
/usr/bin/python3 -B -I - "$D/driver.py" <<'PY'
import runpy, sys
m=runpy.run_path(sys.argv[1], run_name='inspection')
r=m['recipe']; c=m['canonical']
assert r.THREADS == 48
assert "'-t','96'" in __import__('pathlib').Path(sys.argv[1]).read_text()
assert __import__('pathlib').Path(r.TRUNK_GGUF) == m['MODEL']
assert r.KV_CACHE_FLAGS == ['-ctk','f16','-ctv','f16']
assert r.SERVE_PREFIX == ['taskset','-c','0-95','numactl','--interleave=all']
assert r.CHAMPION_GGML_ENV['GGML_FA_SPLIT_KV'] == '0'
assert all(c.CANONICAL_OMP_ENV[k] == v for k,v in r.CANONICAL_OMP_ENV.items())
assert m['starttime'](__import__('os').getpid()).isdigit()
grade=m['grade']
def cells(values): return [{(1,8192):v} for v in values]
assert grade(cells([100, 98, 98, 100, 100, 98]))[0] == 'COSTS'
assert grade(cells([100, 101, 101, 100, 100, 101]))[0] == 'NO_COST'
assert grade(cells([100, 98, 101, 100, 100, 98]))[0] == 'INCONCLUSIVE'
import subprocess
p=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
fn=m['cleanup']; fn.__globals__['active']=p; fn.__globals__['birth']=m['starttime'](p.pid)
fn()
assert p.poll() is not None and fn.__globals__['active'] is None
import tempfile, pathlib, time, os
with tempfile.TemporaryDirectory() as temp:
    marker=pathlib.Path(temp)/'child.pid'
    p=subprocess.Popen([sys.executable, '-c', 'import os,sys,time; p=os.fork(); open(sys.argv[1],"w").write(str(p)) if p else time.sleep(30)', str(marker)],start_new_session=True)
    birth=m['starttime'](p.pid); p.wait(timeout=5)
    for _ in range(50):
        if marker.exists(): break
        time.sleep(.02)
    assert marker.exists()
    orphan=int(marker.read_text()); fn.__globals__['active']=p; fn.__globals__['birth']=birth
    try: fn()
    except RuntimeError as e: assert 'descendants' in str(e)
    else: raise AssertionError('early parent exit with orphan was accepted')
    assert not pathlib.Path('/proc',str(orphan)).exists()
print('pinned recipe import, T48 shape, env, process birth and owned-child drain PASS; no model executed')
PY
/usr/bin/python3 -B -I "$D/test-projector.py"
if /usr/bin/python3 -B -I "$D/approval-check.py" >/dev/null 2>&1; then echo 'missing seals unexpectedly accepted' >&2; exit 1; fi
echo 'missing owner/main seal refusal PASS'
bash "$D/test-watch.sh"
if FILLER_ID=rtg57-c5-vkq-t96 bash "$D/job.sh" >/dev/null 2>&1; then echo 'default STOP failed' >&2; exit 1; fi
echo 'normal path default STOP refusal PASS'
