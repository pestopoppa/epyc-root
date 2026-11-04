"""Open known system-wide perf tracepoints and retain the requested FD attributes.

Opening the FD in the capture owner binds the exact bytes passed to the syscall
and its returned event ID, provided this Python process and kernel are trusted.
This is not independent kernel readback or proof of host coverage/losslessness.
"""
import ctypes
import hashlib
import os
import platform
import re
import struct
from pathlib import Path
from kernel_counter import READ_FORMAT
from perf_mmap import Session

EVENT_DIR = {'sched_switch': 'sched/sched_switch', 'irq_handler_entry': 'irq/irq_handler_entry',
             'irq_handler_exit': 'irq/irq_handler_exit', 'softirq_entry': 'irq/softirq_entry',
             'softirq_exit': 'irq/softirq_exit'}
SAMPLE_TYPE = (1<<0)|(1<<1)|(1<<2)|(1<<7)|(1<<8)|(1<<10)|(1<<16)


def attr_bytes(config):
    if type(config) is not int or not 0 < config <= 65535: raise ValueError('invalid tracepoint ID')
    attr = bytearray(128)
    struct.pack_into('=IIQQQQQ', attr, 0, 2, 128, config, 1, SAMPLE_TYPE, READ_FORMAT, (1<<0)|(1<<18)|(1<<25))
    struct.pack_into('=i', attr, 92, 1)  # CLOCK_MONOTONIC
    return bytes(attr)


def trace_metadata(root, name):
    if name not in EVENT_DIR: raise ValueError('unapproved event')
    directory = Path(root) / EVENT_DIR[name]
    raw_id = (directory / 'id').read_text().strip()
    if not raw_id.isascii() or not raw_id.isdecimal(): raise ValueError('invalid tracepoint ID')
    config = int(raw_id); attr_bytes(config)
    fmt = (directory / 'format').read_bytes()
    text = fmt.decode('ascii')
    if not re.search(r'^name:\s*' + re.escape(name) + r'\s*$', text, re.M) or not re.search(r'^ID:\s*' + str(config) + r'\s*$', text, re.M):
        raise ValueError('tracepoint format identity mismatch')
    return config, fmt


def _syscall(attr, cpu):
    number = {'x86_64': 298, 'aarch64': 241}.get(platform.machine())
    if number is None: raise OSError('unsupported architecture')
    buf = ctypes.create_string_buffer(attr, len(attr))
    fd = ctypes.CDLL(None, use_errno=True).syscall(ctypes.c_long(number), ctypes.byref(buf),
             ctypes.c_int(-1), ctypes.c_int(cpu), ctypes.c_int(-1), ctypes.c_ulong(8)) # PERF_FLAG_FD_CLOEXEC
    if fd < 0:
        err = ctypes.get_errno(); raise OSError(err, os.strerror(err))
    return fd


def open_source(name, cpu, *, trace_root='/sys/kernel/tracing/events',
                syscall=_syscall, session_builder=Session, close=os.close):
    if type(cpu) is not int or cpu < 0: raise ValueError('invalid CPU')
    config, fmt = trace_metadata(trace_root, name)
    attr = attr_bytes(config)
    fd = syscall(attr, cpu)
    if type(fd) is not int or fd < 0: raise ValueError('invalid syscall FD')
    session = None
    try:
        session = session_builder(fd, cpu)
        if session.fd != fd or session.cpu != cpu or type(session.event_id) is not int or session.event_id <= 0:
            raise ValueError('session/FD identity mismatch')
        if trace_metadata(trace_root, name) != (config, fmt): raise ValueError('tracepoint changed during open')
        provenance = {'scope': 'owner-created system-wide CPU event', 'name': name, 'cpu': cpu,
                      'tracepoint_id': config, 'event_id': session.event_id,
                      'attr_hex': attr.hex(), 'attr_sha256': hashlib.sha256(attr).hexdigest(),
                      'format': fmt.decode('ascii'), 'format_sha256': hashlib.sha256(fmt).hexdigest(),
                      'pid_arg': -1, 'group_fd_arg': -1, 'flags_arg': 8,
                      'limitations': ['syscall arguments retained by owner; no independent kernel readback',
                                      'untrusted process could alter owner or evidence']}
        session.open_provenance = provenance
        return {'name': name, 'session': session}
    except BaseException:
        if session is not None: session.close()
        else: close(fd)
        raise


def validate_provenance(name, session):
    """Reject mismatched owner-created source receipts, without asserting trust."""
    try:
        p = session.open_provenance
        attr = bytes.fromhex(p['attr_hex'])
        fmt = p['format'].encode('ascii')
        if (p['name'] != name or p['cpu'] != session.cpu or p['event_id'] != session.event_id
                or p['pid_arg'] != -1 or p['group_fd_arg'] != -1 or p['flags_arg'] != 8
                or attr != attr_bytes(p['tracepoint_id'])
                or p['attr_sha256'] != hashlib.sha256(attr).hexdigest()
                or p['format_sha256'] != hashlib.sha256(fmt).hexdigest()
                or not re.search(r'^name:\s*' + re.escape(name) + r'\s*$', p['format'], re.M)
                or not re.search(r'^ID:\s*' + str(p['tracepoint_id']) + r'\s*$', p['format'], re.M)):
            raise ValueError('source provenance mismatch')
    except (AttributeError, KeyError, TypeError, UnicodeError, ValueError) as exc:
        raise ValueError('source provenance mismatch') from exc
    return dict(p)
