#!/usr/bin/env python3
"""Deny socket syscalls using an inherited kernel seccomp filter, then exec."""
import ctypes,errno,os,socket,sys
L=ctypes.CDLL('libseccomp.so.2',use_errno=True);L.seccomp_init.argtypes=[ctypes.c_uint32];L.seccomp_init.restype=ctypes.c_void_p;L.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];L.seccomp_syscall_resolve_name.restype=ctypes.c_int;L.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint];L.seccomp_rule_add.restype=ctypes.c_int;L.seccomp_load.argtypes=[ctypes.c_void_p];L.seccomp_load.restype=ctypes.c_int
ctx=L.seccomp_init(0x7fff0000)
if not ctx:raise RuntimeError('seccomp_init')
for n in ('socket','socketpair','connect','sendto','sendmsg','sendmmsg','recvfrom','recvmsg','recvmmsg'):
 nr=L.seccomp_syscall_resolve_name(n.encode())
 if nr<0:raise RuntimeError('unknown syscall '+n)
 if L.seccomp_rule_add(ctx,0x00050000|errno.EPERM,nr,0)!=0:raise RuntimeError('seccomp rule '+n)
if L.seccomp_load(ctx)!=0:raise RuntimeError('seccomp_load')
try:socket.socket()
except PermissionError:print('KERNEL_NETWORK_DENY_CONFIRMED',flush=True)
else:raise RuntimeError('socket denial not enforced')
if len(sys.argv)<2:raise SystemExit('missing command')
os.execv(sys.argv[1],sys.argv[1:])
