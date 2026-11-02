#!/usr/bin/env python3
"""One-shot native SR-6 readiness witness, not complete launch authority.

The caller must authenticate inputs and independently ensure containment,
placement, model identity and continuous admission. Recheck admission and
listener ownership before every request; a snapshot cannot establish either.
"""
import http.client
import json
from pathlib import Path

from native_worker import ARMS, exclusive_json
from process_linkage import verify_process_linkage
from verified_post import process_starttime, verify_owned_loopback_listener


def verify_ready_server(*, process, arm, expected_argv, library_dir, build_root,
                        port, admission_check, record_path, timeout_s=2):
    """Capture and seal a one-shot health, command, listener and linkage witness."""
    pid = getattr(process, 'pid', None)
    if (type(pid) is not int or pid <= 0 or process.poll() is not None or arm not in ARMS
            or not isinstance(expected_argv, list) or not expected_argv
            or any(not isinstance(x, str) or not x or '\0' in x for x in expected_argv)
            or not isinstance(library_dir, str) or not library_dir.startswith('/')
            or not isinstance(build_root, Path) or not build_root.is_absolute()
            or type(port) is not int or not 1 <= port <= 65535
            or not callable(admission_check) or not isinstance(record_path, Path)
            or not 0 < timeout_s <= 10):
        raise ValueError('invalid readiness inputs')
    if admission_check() is not True:
        raise ValueError('admission unavailable')
    birth = process_starttime(pid)
    try:
        cmd = Path(f'/proc/{pid}/cmdline').read_bytes()
        env = Path(f'/proc/{pid}/environ').read_bytes()
        if not cmd.endswith(b'\0') or cmd[:-1].split(b'\0') != [x.encode() for x in expected_argv]:
            raise ValueError('server argv mismatch')
        entries = [entry for entry in env.split(b'\0') if entry.startswith(b'LD_LIBRARY_PATH=')]
        if entries != [b'LD_LIBRARY_PATH=' + library_dir.encode()]:
            raise ValueError('server library path mismatch')
        verify_owned_loopback_listener(pid, birth, port)
        linkage = verify_process_linkage(pid, birth, build_root)
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout_s)
        try:
            conn.request('GET', '/health', headers={'Connection': 'close'})
            response = conn.getresponse()
            body = response.read(4097)
            if (response.status != 200 or len(body) > 4096 or
                    (response.length is not None and response.length != 0) or
                    json.loads(body) != {'status': 'ok'}):
                raise ValueError('server health not ready')
        finally:
            conn.close()
        if (process.poll() is not None or process_starttime(pid) != birth or
                admission_check() is not True):
            raise ValueError('identity or admission changed')
        verify_owned_loopback_listener(pid, birth, port)
        record = {'schema': 'sr6.server-ready.v1', 'pid': pid, 'arm': arm,
                  'starttime_ticks': birth, 'argv': expected_argv,
                  'library_dir': library_dir, 'port': port, 'linkage': linkage,
                  'health': {'status': 200, 'body': {'status': 'ok'}},
                  'limitations': ['point-in-time witness; launch provenance, model, placement, '
                                  'continuous admission and containment require independent proof']}
        record_sha = exclusive_json(record_path, record)
        return {'server_record_sha256': record_sha, 'starttime_ticks': birth}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('server readiness unavailable') from exc
