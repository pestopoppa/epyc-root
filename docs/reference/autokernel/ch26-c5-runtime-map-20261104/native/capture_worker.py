"""Dedicated CH-26 worker entrypoint; diagnostic evidence only.

The owner passes a connected control socket and a separate connected marker
socket. This process opens every perf FD itself, binds owner and target with
pidfds and persists raw snapshots before acknowledging completion. No floor or
admissibility claim is made. Use only in isolated experimental scratch.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import socket
import sys
import uuid

# Isolated mode omits the script directory; use only this sealed worker's own path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from owned_capture import Capture, EVENTS
from ring_archive import RingArchive
from owner_marker import Receiver
from target_identity import Target
from trace_open import open_source
from worker_protocol import serve, _send
from worker_signals import WorkerSignals


def _encode(value):
    if isinstance(value, bytes):
        return {'encoding': 'base64', 'data': base64.b64encode(value).decode('ascii')}
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value): raise ValueError('non-string evidence key')
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)): return [_encode(item) for item in value]
    if value is None or type(value) in (str, int, float, bool): return value
    raise ValueError('unsupported evidence value')


def persist(result, destination):
    """Exclusively publish complete JSON; never replace an existing receipt."""
    dest = Path(destination)
    if not dest.is_absolute() or dest.name in ('', '.', '..'): raise ValueError('absolute output file required')
    if not isinstance(result, dict) or result.get('measurement_admission') != 'none' or result.get('errors') != []:
        raise ValueError('incomplete diagnostic evidence')
    payload = (json.dumps(_encode(result), sort_keys=True, allow_nan=False, separators=(',', ':')) + '\n').encode()
    if len(payload) > 512 * 1024 * 1024: raise ValueError('evidence size bound exceeded')
    temp = dest.parent / ('.' + dest.name + '.' + uuid.uuid4().hex + '.tmp')
    fd = None
    linked = False
    owned_inode = None
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as f:
            fd = None
            f.write(payload); f.flush(); os.fsync(f.fileno())
        st = os.stat(temp, follow_symlinks=False)
        owned_inode = (st.st_dev, st.st_ino)
        os.link(temp, dest, follow_symlinks=False)
        linked = True
        dfd = os.open(dest.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    except BaseException:
        if linked:
            try:
                current = os.stat(dest, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == owned_inode:
                    dest.unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        if fd is not None: os.close(fd)
        try: temp.unlink()
        except FileNotFoundError: pass


def build_capture(marker, *, owner_pid, owner_uid, target_pid, cpus, trace_root, archive):
    receiver = target = None
    sources = []
    try:
        receiver = Receiver(marker, pid=owner_pid, uid=owner_uid, receive_timeout_s=3600)
        target = Target(target_pid)
        for cpu in sorted(cpus):
            for name in sorted(EVENTS):
                sources.append(open_source(name, cpu, trace_root=trace_root))
        return Capture(receiver, target, sources, cpus, archive=archive)
    except BaseException:
        for item in reversed(sources):
            try: item['session'].close()
            except Exception: pass
        if target is not None: target.close()
        if receiver is not None: receiver.close()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--control-fd', type=int, required=True)
    parser.add_argument('--marker-fd', type=int, required=True)
    parser.add_argument('--owner-pid', type=int, required=True)
    parser.add_argument('--owner-uid', type=int, required=True)
    parser.add_argument('--target-pid', type=int, required=True)
    parser.add_argument('--cpus', required=True, help='comma separated exact CPU ids')
    parser.add_argument('--output', required=True)
    parser.add_argument('--trace-root', default='/sys/kernel/tracing/events')
    args = parser.parse_args(argv)
    if args.control_fd < 3 or args.marker_fd < 3 or args.control_fd == args.marker_fd: raise ValueError('distinct explicit FDs required')
    parts = args.cpus.split(',')
    if not parts or any(not x.isascii() or not x.isdecimal() for x in parts): raise ValueError('invalid CPU list')
    cpus = {int(x) for x in parts}
    if len(cpus) != len(parts): raise ValueError('duplicate CPUs')
    control = marker = capture = archive = None
    persisted = False
    try:
        control = socket.socket(fileno=args.control_fd)
        marker = socket.socket(fileno=args.marker_fd)
        archive = RingArchive(str(Path(args.output)) + '.rings', max_bytes=256 * 1024 * 1024)
        with WorkerSignals():
            capture = build_capture(marker, owner_pid=args.owner_pid, owner_uid=args.owner_uid,
                                    target_pid=args.target_pid, cpus=cpus, trace_root=args.trace_root, archive=archive)
            _send(control, {'state': 'created', 'marker_nonce': capture.receiver.nonce,
                            'measurement_admission': 'none'})
            def finalize(result):
                nonlocal persisted
                persist(result, args.output)
                persisted = True
            serve(control, capture, timeout_s=3600, finalize=finalize)
    finally:
        try:
            if capture is not None: capture.abort()
        finally:
            try:
                drain_alive = (capture is not None and getattr(capture, 'thread', None) is not None
                               and capture.thread.is_alive())
                if archive is not None and not drain_alive:
                    try:
                        archive.abort()
                    finally:
                        if not persisted:
                            try: archive.path.unlink()
                            except FileNotFoundError: pass
            finally:
                try:
                    if control is not None: control.close()
                finally:
                    if marker is not None: marker.close()

if __name__ == '__main__': main()
