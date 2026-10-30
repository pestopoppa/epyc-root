"""Trusted synthetic descendant fixture; does not run a model."""
import os,sys,time
from pathlib import Path
root=Path(sys.argv[1]);pid=os.fork()
if pid==0:
 (root/'descendant.pid').write_text(str(os.getpid()))
 time.sleep(30)
 os._exit(0)
(root/'parent.pid').write_text(str(os.getpid()))
time.sleep(30)
