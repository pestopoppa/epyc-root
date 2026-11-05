import os,signal,sys,time
from pathlib import Path
root,case,stop=map(str,sys.argv[1:]);root=Path(root)
if case=='failure':raise SystemExit(9)
if case=='detached':
    pid=os.fork()
    if pid:
        (root/'detached.pid').write_text(str(pid));raise SystemExit(0)
    os.setsid();signal.signal(signal.SIGTERM,signal.SIG_IGN)
    while True:time.sleep(.02)
if case=='normal':
    (root/'payload').write_bytes(b'a'*4096);raise SystemExit(0)
if case=='stop':Path(stop).touch()
if case=='growth':
    with (root/'payload').open('wb',buffering=0) as f:
        while True:f.write(b'x'*8192);time.sleep(.003)
else:
    while True:time.sleep(.02)
