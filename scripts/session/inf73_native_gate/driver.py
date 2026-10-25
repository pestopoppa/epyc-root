#!/usr/bin/env python3
"""PROPOSED original-wait recorder inside official owner; no nested scheduling."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runner import digest, proc_identity, write_json

def main():
    own=Path(__file__).resolve().parent
    approval=own/"MAIN-APPROVED-NATIVE-LAUNCH.json"
    expected=(own/"MAIN-NATIVE-LAUNCH.sha256").read_text().strip().removeprefix("approval_sha256=")
    if digest(approval)!=expected: return 78
    if (own/"DRIVER_ORIGINAL_WAIT.json").exists(): return 78
    context=own/"NATIVE_OWNER_LIVE.json"
    # Capture shim creates context immediately after spawn; native admission waits boundedly.
    import time
    until=time.monotonic()+5
    while (not context.exists() or context.stat().st_size==0) and time.monotonic()<until: time.sleep(.01)
    if not context.exists() or context.stat().st_size==0: return 78
    command=[sys.executable,"-I","-S","-B","-c",
        'import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=sys.argv[2:];runpy.run_path(sys.argv[0],run_name="__main__")',
        str(own),str(own/"runner.py"),"--approval",str(approval),"--sha",expected,
        "--results",str(own/"native-results-current")]
    child=subprocess.Popen(command)
    identity=proc_identity(child.pid)
    seen=[]
    def cancel(number,frame):
        seen.append(number)
        current=proc_identity(child.pid)
        if identity and current and current[0]==identity[0] and current[2]!="Z": child.send_signal(number)
    for number in (signal.SIGTERM,signal.SIGINT):signal.signal(number,cancel)
    wait=child.wait()
    write_json(own/"DRIVER_ORIGINAL_WAIT.json",{"popen_wait_returncode":wait,
        "source":"original current runner Popen.wait","approval_sha256":expected,
        "signals":seen,"captured_runner_identity":identity[0] if identity else None})
    return 128+seen[0] if seen else wait
if __name__=="__main__":raise SystemExit(main())
