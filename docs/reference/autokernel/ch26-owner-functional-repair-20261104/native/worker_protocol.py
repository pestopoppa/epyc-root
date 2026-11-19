"""Fail-closed IPC lifecycle for one dedicated CH-26 capture worker.

The caller constructs Capture inside the child, including all perf FDs. The
control socket conveys lifecycle commands only; authenticated owner markers
remain a separate channel. This module does not establish request validity,
trace coverage, contention, or measurement admission.
"""
import json
import math
import socket

MAX_PACKET = 4096


def _pairs(items):
    obj = {}
    for key, value in items:
        if key in obj:
            raise ValueError('duplicate field')
        obj[key] = value
    return obj


def _recv(sock):
    data, _, flags, _ = sock.recvmsg(MAX_PACKET)
    if not data or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        raise ValueError('EOF or truncated IPC packet')
    value = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs)
    if not isinstance(value, dict):
        raise ValueError('IPC object required')
    return value


def _send(sock, value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(data) > MAX_PACKET or sock.send(data) != len(data):
        raise ValueError('IPC response too large or short')


def serve(sock, capture, *, timeout_s=30, finalize=None):
    """Execute start/begin/finish once, returning native evidence only to child.

    Capture.abort() runs even if peer dies, sends invalid traffic, or times out.
    The child caller must persist the returned evidence; only lifecycle state is
    acknowledged to the parent. A peer can never request a second capture.
    """
    if sock.family != socket.AF_UNIX or sock.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET:
        raise ValueError('connected UNIX SOCK_SEQPACKET required')
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 3600:
        raise ValueError('bounded timeout required')
    sock.settimeout(timeout_s)
    try:
        for seq, command in enumerate(('start', 'begin', 'finish'), 1):
            request = _recv(sock)
            if set(request) != {'seq', 'command'} or type(request['seq']) is not int or request != {'seq': seq, 'command': command}:
                raise ValueError('unexpected IPC command')
            result = getattr(capture, command)()
            if command == 'finish':
                if not isinstance(result, dict) or result.get('measurement_admission') != 'none' or result.get('errors') != []:
                    raise ValueError('capture failed or admission not explicitly withheld')
                if finalize is not None:
                    finalize(result)
            _send(sock, {'seq': seq, 'state': command, 'measurement_admission': 'none'})
        return result
    finally:
        capture.abort()
        sock.close()


def command(sock, seq, name, *, timeout_s=30):
    """Parent side: verify a matching bounded acknowledgement; errors propagate."""
    if (type(seq) is not int or (seq, name) not in ((1, 'start'), (2, 'begin'), (3, 'finish')) or
        isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 3600):
        raise ValueError('invalid IPC command or timeout')
    sock.settimeout(timeout_s)
    _send(sock, {'seq': seq, 'command': name})
    reply = _recv(sock)
    if reply != {'seq': seq, 'state': name, 'measurement_admission': 'none'}:
        raise ValueError('invalid worker acknowledgement')
    return reply
