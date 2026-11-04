"""Self-owned Linux perf counter experiment, not a trace coverage warrant.

Only current thread, any CPU, user-space software task-clock. The ioctl call
boundaries conservatively bracket transitions; they are not exact kernel times.
"""
import ctypes,fcntl,os,platform,struct,time

TYPE_SOFTWARE=1;TASK_CLOCK=1
FORMAT_TOTAL_TIME_ENABLED=1;FORMAT_TOTAL_TIME_RUNNING=2;FORMAT_ID=4;FORMAT_LOST=16
READ_FORMAT=FORMAT_TOTAL_TIME_ENABLED|FORMAT_TOTAL_TIME_RUNNING|FORMAT_ID|FORMAT_LOST
IOC_ENABLE=0x2400;IOC_DISABLE=0x2401
ATTR_SIZE=128

def open_self():
    arch=platform.machine(); numbers={'x86_64':298,'aarch64':241}
    if arch not in numbers:raise OSError('unsupported architecture')
    attr=bytearray(ATTR_SIZE)
    struct.pack_into('=IIQQQQQ',attr,0,TYPE_SOFTWARE,ATTR_SIZE,TASK_CLOCK,0,0,READ_FORMAT,(1<<0)|(1<<5)|(1<<6))
    buf=(ctypes.c_ubyte*ATTR_SIZE).from_buffer(attr)
    libc=ctypes.CDLL(None,use_errno=True)
    fd=libc.syscall(ctypes.c_long(numbers[arch]),ctypes.byref(buf),ctypes.c_int(0),ctypes.c_int(-1),ctypes.c_int(-1),ctypes.c_ulong(0))
    if fd<0:
        err=ctypes.get_errno();raise OSError(err,os.strerror(err))
    return fd

class Counter:
    def __init__(self,*,opener=open_self,ioctl=fcntl.ioctl,read=os.read,close=os.close,clock=time.monotonic_ns):
        self.opener=opener;self.ioctl=ioctl;self.read=read;self.closefd=close;self.clock=clock;self.fd=None;self.state='new';self.enable=None
    def start(self):
        if self.state!='new':raise ValueError('counter already started')
        self.fd=self.opener()
        try:
            before=self.clock();self.ioctl(self.fd,IOC_ENABLE,0);after=self.clock()
            if after<before:raise ValueError('clock regressed')
            self.enable=(before,after);self.state='running'
        except BaseException:
            self.state='failed';self.closefd(self.fd);self.fd=None;raise
    def stop(self):
        if self.state!='running':raise ValueError('counter not running')
        try:
            before=self.clock();self.ioctl(self.fd,IOC_DISABLE,0);after=self.clock()
            if after<before or before<self.enable[1]:raise ValueError('invalid transition brackets')
            raw=self.read(self.fd,40)
            if len(raw)!=40:raise ValueError('short perf counter read')
            value,enabled,running,event_id,lost=struct.unpack('=5Q',raw)
            if running>enabled or not event_id:raise ValueError('invalid perf counter values')
        except BaseException:
            self.state='failed';raise
        finally:
            self.closefd(self.fd);self.fd=None
        self.state='stopped'
        errors=[]
        if not enabled or running!=enabled:errors.append('disabled, multiplexed or throttled counter')
        if lost:errors.append('kernel event lost counter nonzero')
        return {'status':'unproven','coverage':'unknown','loss':'unknown','scope':'current-thread any-cpu task-clock',
                'enable_before_ns':self.enable[0],'enable_after_ns':self.enable[1],
                'disable_before_ns':before,'disable_after_ns':after,'event_id':event_id,'value':value,
                'time_enabled':enabled,'time_running':running,'lost_samples':lost,'errors':errors,
                'limitations':['this single software counter does not measure per-CPU scheduler rings',
                'ioctl brackets bound transitions but are not exact kernel timestamps',
                'PERF_FORMAT_LOST for this event is not proof of losslessness of other rings']}
