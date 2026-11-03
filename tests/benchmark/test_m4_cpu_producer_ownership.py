import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP = ROOT/'scripts/benchmark/m4_cpu_ownership'
RUNNER = ROOT/'scripts/benchmark/m4_cpu_producer/native/k35_stack_context_matrix_runner.py'
DISPATCH = ROOT/'scripts/benchmark/m4_cpu_producer/dispatch.py'
spec=importlib.util.spec_from_file_location('m4_cgroup_guard',OWNERSHIP/'m4_cgroup_guard.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)


def test_successor_has_no_numeric_pid_registry_or_termination():
    source=RUNNER.read_text(); dispatch=DISPATCH.read_text()
    assert 'FILLER_PIDFILE' not in source
    assert 'proc.kill()' not in source and 'proc.send_signal(' not in source
    assert 'child.kill()' not in dispatch and 'child.terminate()' not in dispatch
    assert 'm4_owned.spawn(' in source and 'm4_owned.spawn(' in dispatch


def test_actual_runner_pidfd_cleanup_in_real_cgroup(tmp_path):
    out=tmp_path/'watch';out.mkdir()
    grant=tmp_path/'grant';grant.write_text('fixture')
    hold=tmp_path/'hold';hold.mkdir()
    receipt=tmp_path/'receipt.json'
    script=tmp_path/'worker.py'
    script.write_text('''import importlib.util,json,os,subprocess,sys\nfrom pathlib import Path\np=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('k35_owned_test',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)\nc,fd,b=m.m4_owned.spawn([sys.executable,'-c','import time;time.sleep(60)'],env=os.environ.copy(),registry=os.environ['M4_SERVER_PID_REGISTRY'])\nPath(sys.argv[2]).write_text(json.dumps(m.terminate(c,fd,b)))\n''')
    entry=tmp_path/'entry.py'
    entry.write_text('''import os,sys,time,watch\nenv=dict(os.environ,M4_DELEGATED_CGROUP_PARENT='/sys/fs/cgroup',M4_OUTER_OWNER_PID=sys.argv[1],M4_OUTER_OWNER_BIRTH=sys.argv[2])\nraise SystemExit(watch.run([sys.executable,sys.argv[3],sys.argv[4],sys.argv[5]],sys.argv[6],sys.argv[7],sys.argv[8],time.time()+20,sys.argv[9],env))\n''')
    cmd=[sys.executable,str(entry),str(os.getpid()),str(guard.birth(os.getpid())),str(script),str(RUNNER),str(receipt),str(grant),str(tmp_path/'stop'),str(hold),str(out)]
    result=subprocess.run(cmd,env=dict(os.environ,PYTHONPATH=str(OWNERSHIP)),capture_output=True,text=True,timeout=20)
    assert result.returncode==0, result.stderr
    proof=json.loads(receipt.read_text())
    assert proof['completed'] and proof['dead'] and proof['birth'] > 0
    assert json.loads((out/'watch-result.json').read_text())['containment_empty']


spec_owned=importlib.util.spec_from_file_location('m4_owned_test',OWNERSHIP/'owned.py')
owned=importlib.util.module_from_spec(spec_owned);spec_owned.loader.exec_module(owned)


def test_spawn_accepts_env_prefixed_argv_without_owned_cgroup(tmp_path):
    # The sealed plan emits `env NAME=VALUE ... <cmd>`; a bare run has no M4_OWNED_CGROUP.
    env={k:v for k,v in os.environ.items() if k!='M4_OWNED_CGROUP'}
    registry=tmp_path/'server-pids.txt'
    argv=['env','-u','M4_UNSET_ME','M4_ENV_PROBE=1','GGML_FA_SPLIT_KV=0',sys.executable,'-c',
          'import os,sys; sys.exit(0 if os.environ.get("M4_ENV_PROBE")=="1" and "M4_UNSET_ME" not in os.environ else 3)']
    child,fd,stamp=owned.spawn(argv,env=dict(env,M4_UNSET_ME='x'),registry=registry)
    try:
        assert child.wait(timeout=20)==0
        assert registry.read_text().split()==[str(child.pid),str(stamp)]
    finally:
        owned.stop(child,fd,stamp); os.close(fd)


def test_spawn_stop_by_pidfd(tmp_path):
    child,fd,stamp=owned.spawn([sys.executable,'-c','import time;time.sleep(60)'],env=dict(os.environ))
    try:
        owned.stop(child,fd,stamp)
        assert owned.exited(fd) and child.returncode is not None
    finally:
        os.close(fd)
