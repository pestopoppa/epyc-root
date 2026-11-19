"""Linux owner-bound marker receiver. Does not validate a request or prove a trace.

Caller creates the connected SOCK_SEQPACKET pair and passes its sending endpoint
only to its trusted request-owner. Never accept an owner-provided PID as identity.
"""
import json
import math
import os
from pathlib import Path
import secrets
import select
import socket
import struct
import time

MAX_PACKET=4096
CREDENTIAL_SIZE=struct.calcsize('3i')

def identity(pid):
    root=Path('/proc')/str(pid)
    raw=(root/'stat').read_text(); prefix,sep,tail=raw.rpartition(') ')
    if not sep or prefix.split(' (',1)[0]!=str(pid): raise ValueError('malformed process identity')
    start=int(tail.split()[19]); boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if start<0 or not boot: raise ValueError('invalid process identity')
    return start,boot

def _object(pairs):
    result={}
    for k,v in pairs:
        if k in result: raise ValueError('duplicate field')
        result[k]=v
    return result

class Receiver:
    def __init__(self, sock, *, pid, uid, max_age_ns=1_000_000_000, receive_timeout_s=5.0):
        if sock.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET: raise ValueError('SOCK_SEQPACKET required')
        if type(pid) is not int or pid<=0 or type(uid) is not int or uid<0 or type(max_age_ns) is not int or max_age_ns<=0: raise ValueError('invalid identity or age')
        if isinstance(receive_timeout_s,bool) or not isinstance(receive_timeout_s,(int,float)) or not math.isfinite(receive_timeout_s) or not 0 < receive_timeout_s <= 3600: raise ValueError('invalid receive timeout')
        self.sock=sock;self.pid=pid;self.uid=uid;self.max_age_ns=max_age_ns;self.receive_timeout_s=receive_timeout_s
        self.fd=None;self.failed=False;self.sequence=0;self.markers=[]
        self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
        before=identity(pid)
        fd=os.pidfd_open(pid,0)
        try:
            if identity(pid)!=before or self._dead(fd): raise ValueError('owner changed or exited during attach')
        except BaseException:
            os.close(fd);raise
        self.fd=fd;self.start_ticks,self.boot_id=before
        self.nonce=secrets.token_hex(32)
    @staticmethod
    def _dead(fd):
        p=select.poll();p.register(fd,select.POLLIN|select.POLLHUP|select.POLLERR)
        return bool(p.poll(0))
    def _live(self):
        if self.fd is None or self._dead(self.fd) or identity(self.pid)!=(self.start_ticks,self.boot_id): raise ValueError('owner identity unavailable or changed')
    def receive(self):
        if self.failed or self.fd is None or self.sequence>=2: raise ValueError('receiver closed or request complete')
        try:
            self._live()
            deadline=time.monotonic()+self.receive_timeout_s
            poller=select.poll();poller.register(self.sock.fileno(),select.POLLIN|select.POLLHUP|select.POLLERR);poller.register(self.fd,select.POLLIN|select.POLLHUP|select.POLLERR)
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0: raise TimeoutError('request marker receive timeout')
                ready=poller.poll(max(1,math.ceil(remaining*1000)))
                if not ready: continue
                if any(fd==self.fd for fd,_ in ready): raise ValueError('owner exited while waiting')
                if any(fd==self.sock.fileno() and event & select.POLLNVAL for fd,event in ready): raise ValueError('marker socket closed')
                if any(fd==self.sock.fileno() and event & (select.POLLIN|select.POLLHUP|select.POLLERR) for fd,event in ready): break
            self._live()
            data,anc,flags,_=self.sock.recvmsg(MAX_PACKET, socket.CMSG_SPACE(CREDENTIAL_SIZE),socket.MSG_DONTWAIT)
            received=time.monotonic_ns()
            if not data or flags & (socket.MSG_TRUNC|socket.MSG_CTRUNC): raise ValueError('EOF or truncated packet')
            creds=[struct.unpack('3i',v) for lev,typ,v in anc if lev==socket.SOL_SOCKET and typ==socket.SCM_CREDENTIALS and len(v)==CREDENTIAL_SIZE]
            if len(creds)!=1 or creds[0][:2]!=(self.pid,self.uid): raise ValueError('owner credentials mismatch')
            self._live()
            obj=json.loads(data.decode('utf8'),object_pairs_hook=_object)
            if not isinstance(obj,dict) or set(obj)!={'kind','seq','nonce','timestamp_ns'}: raise ValueError('marker schema')
            seq=self.sequence+1; stamp=obj['timestamp_ns']
            if type(obj['seq']) is not int or obj['seq']!=seq or obj['kind']!=('begin' if seq==1 else 'end'): raise ValueError('marker sequence')
            if not isinstance(obj['nonce'],str) or not secrets.compare_digest(obj['nonce'],self.nonce): raise ValueError('marker nonce mismatch')
            if type(stamp) is not int or stamp<=0 or stamp>received or received-stamp>self.max_age_ns: raise ValueError('marker timestamp invalid or stale')
            if self.markers and stamp<=self.markers[-1]['timestamp_ns']: raise ValueError('nonmonotonic marker time')
            marker={'kind':obj['kind'],'seq':seq,'timestamp_ns':stamp,'received_ns':received,'pid':self.pid,'uid':self.uid,'start_ticks':self.start_ticks,'boot_id':self.boot_id}
            self.sequence=seq;self.markers.append(marker);return marker
        except BaseException:
            self.failed=True;raise
    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None
