import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP = ROOT/'scripts/benchmark/m4_cpu_ownership'
OWNED_PATH = OWNERSHIP/"owned.py"
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


def _owned_module():
    spec = importlib.util.spec_from_file_location("m4_owned_env_test", OWNED_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ENV_PREFIX = ["env", "LD_LIBRARY_PATH=/x/bin", "GGML_FA_SPLIT_KV=0", "GGML_IQK=1", "ROCR_VISIBLE_DEVICES=-1",
               "CUDA_VISIBLE_DEVICES=", "OMP_NUM_THREADS=1"]
_TAIL = ["numactl", "--interleave=all", "--", "taskset", "-c", "0-95", "/x/bin/llama-server", "-m", "m.gguf"]


def test_env_wrapped_numactl_taskset_argv_resolves_to_usr_bin_env():
    # exact server_argv shape of inf22 recipe r1 (failed 'unbound bare executable' at spawn)
    out = _owned_module().resolve_argv(_ENV_PREFIX + _TAIL)
    assert out[0] == str(Path("/usr/bin/env").resolve()) and out[1:7] == _ENV_PREFIX[1:]
    assert Path(out[7]).name == "numactl" and out[-2:] == ["-m", "m.gguf"]


def test_env_wrapper_rejects_unreviewed_tokens():
    import pytest
    m = _owned_module()
    for bad in (["env", "PATH=/tmp"] + _TAIL, ["env", "LD_PRELOAD=/x.so"] + _TAIL, ["env", "-i"] + _TAIL,
                ["env", "-S", "x"] + _TAIL, ["env", "-u", "PATH"] + _TAIL, ["env", "GGML_IQK=1"],
                ["env", "GGML_IQK=1", "env", "numactl", "--", "taskset"], ["env", "GGML_IQK=1", "sh", "-c", "x"],
                ["env", "GGML_IQK=1", "./llama-server"]):
        with pytest.raises(ValueError):
            m.resolve_argv(bad)
    assert m.resolve_argv(["env", "-u", "GGML_X"] + _TAIL)[1:3] == ["-u", "GGML_X"]


def test_recipe_smoke_worker_spawns_through_real_owned_gate():
    src = (ROOT / "scripts/benchmark/m4_cpu_recipe_entry.py").read_text()
    body = src.split("def qualification_worker", 1)[1].split("def main", 1)[0]
    assert "m4_owned.spawn(" in body and "'env'" in body and "'numactl'" in body and "'taskset'" in body
    out = _owned_module().resolve_argv(["env", "LD_LIBRARY_PATH=/d", "GGML_IQK=1", "OMP_NUM_THREADS=1", "numactl",
                                        "--interleave=all", "--", "taskset", "-c", "72-75", sys.executable, "-B", "-c", "pass"])
    assert out[-3:] == ["-B", "-c", "pass"]
