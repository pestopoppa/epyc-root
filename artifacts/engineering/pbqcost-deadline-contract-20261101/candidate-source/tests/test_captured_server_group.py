"""Nonmodel proof of the pinned KPF subprocess group/drain helper in an isolated real import."""
import os
from pathlib import Path
import subprocess
import sys

D = Path(__file__).resolve().parents[1]
CODE = r'''
import json, os, signal, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import pb_hol_1 as H
p = H.K.captured_process_popen([sys.executable, "-c", "import time; time.sleep(30)"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
pid = p.pid
try:
    assert os.getpgid(pid) == os.getpgrp()
    birth = int(Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()[19])
    os.kill(pid, signal.SIGTERM)
    p.wait(timeout=5)
    assert not Path(f"/proc/{pid}").exists()
    print(json.dumps({"pid":pid,"birth_ticks":birth,"pgid":os.getpgid(os.getpid()),"drained":True}))
finally:
    if p.poll() is None:
        os.kill(pid, signal.SIGTERM)
        p.wait(timeout=5)
'''

def test_captured_process_inherits_launcher_group_and_drains_owned_pid():
    p = subprocess.run([sys.executable, "-c", CODE, str(D)], text=True, capture_output=True, timeout=10)
    assert p.returncode == 0, p.stderr
    assert '"drained": true' in p.stdout.lower()
