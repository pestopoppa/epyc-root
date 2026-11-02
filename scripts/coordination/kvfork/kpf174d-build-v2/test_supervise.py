#!/usr/bin/env python3
"""Exercise the cooperative STOP path against a TERM-resistant process tree."""
import pathlib
import subprocess
import sys
import tempfile
import threading
import time


SUP = pathlib.Path(__file__).with_name('supervise.py')


def test_cooperative_stop_terminates_and_reaps_descendants():
    # Keep the fixture on the same scratch filesystem as the build workflow.
    with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvfork') as d:
        stop, marker = pathlib.Path(d) / 'stop', pathlib.Path(d) / 'children'
        child = '''import os,signal,subprocess,sys,time
signal.signal(signal.SIGTERM,signal.SIG_IGN)
p=subprocess.Popen([sys.executable,"-c","import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"])
open(sys.argv[1],"w").write(f"{os.getpid()} {p.pid}\\n")
time.sleep(60)
'''

        def trigger():
            for _ in range(30):
                if marker.exists():
                    stop.touch()
                    return
                time.sleep(0.1)

        t = threading.Thread(target=trigger)
        t.start()
        try:
            proc = subprocess.run(
                [sys.executable, str(SUP), str(stop), str(int(time.time()) + 30),
                 sys.executable, '-c', child, str(marker)],
                timeout=10,
            )
        finally:
            t.join(timeout=5)

        assert not t.is_alive(), 'STOP trigger did not finish'
        assert proc.returncode == 75, proc.returncode
        assert marker.exists(), 'fixture did not record its child PIDs'
        for pid in marker.read_text().split():
            stat = pathlib.Path('/proc') / pid / 'stat'
            if stat.exists():
                state = stat.read_text().split(') ', 1)[1].split()[0]
                assert state == 'Z', (pid, state)
