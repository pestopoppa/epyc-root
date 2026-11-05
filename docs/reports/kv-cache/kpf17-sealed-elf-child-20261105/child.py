#!/usr/bin/env python3
import errno,json,os,sys
fd=int(sys.argv[1]); action=sys.argv[2]; parent=int(sys.argv[3])
if os.getppid()!=parent or os.geteuid()!=os.stat('/proc/%d' % parent).st_uid: raise RuntimeError('identity')
try:
 if action=='write': os.pwrite(fd,b'X',0)
 elif action=='shrink': os.ftruncate(fd,1)
 else: raise RuntimeError('action')
 result='success'
except OSError as e:
 if e.errno!=errno.EPERM: raise
 result='EPERM'
print(json.dumps({'pid':os.getpid(),'ppid':os.getppid(),'uid':os.geteuid(),'inode':os.fstat(fd).st_ino,'action':action,'result':result}))
