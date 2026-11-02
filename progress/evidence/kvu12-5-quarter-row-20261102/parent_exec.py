#!/usr/bin/env python3
"""Native server shares engine process group and dies with its smoke worker."""
import ctypes,os,signal,sys
parent=int(sys.argv[1])
if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise OSError(ctypes.get_errno(),'prctl')
if os.getppid()!=parent:sys.exit(70)
os.execv(sys.argv[2],sys.argv[2:])
