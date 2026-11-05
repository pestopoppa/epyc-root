import ctypes,json,os,pathlib,sys
# Leaf only: no subprocesses, threads, shell or model runtime.
lib=ctypes.CDLL(sys.argv[1])
if sys.argv[3]=='denied':
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(4,0,0,0,0)!=0: raise OSError(ctypes.get_errno(),'PR_SET_DUMPABLE')
pathlib.Path(sys.argv[2]).write_text(json.dumps({'pid':os.getpid(),'mapped':sys.argv[1],'mode':sys.argv[3]}))
sys.stdin.buffer.read(1)
