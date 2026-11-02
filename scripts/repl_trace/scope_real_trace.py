#!/usr/bin/env python3
"""Select one v2 session from a native trace and retain selection provenance.

The input log and receipt are not proof of real use or authorized custody. Keep
both the complete native input and the selection receipt for later review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{16}', args.session):
        parser.error('session must be a 16-character lowercase hexadecimal id')
    if args.output.resolve() == args.receipt.resolve():
        parser.error('output and receipt must be distinct')
    for parent in {args.output.parent, args.receipt.parent}:
        info = parent.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            parser.error('output and receipt directories must be owner-only')
    sys.path.insert(0, str(args.app_root.resolve()))
    from src.repl_environment.trace_capture import pii_scan

    raw = args.trace.read_bytes()
    selected, versions, total = [], {}, 0
    for number, line in enumerate(raw.splitlines(), 1):
        try:
            record = json.loads(line)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f'invalid JSON at line {number}') from exc
        if not isinstance(record, dict) or pii_scan(record):
            raise ValueError(f'invalid native record at line {number}')
        total += 1
        version = str(record['v'])
        versions[version] = versions.get(version, 0) + 1
        if record['session'] == args.session:
            if record['v'] != 2:
                raise ValueError('selected session contains legacy v1 records')
            selected.append(line + b'\n')
    if not selected:
        raise ValueError('selected session has no v2 records')
    output = b''.join(selected)
    receipt = {'schema': 'epyc.repl_trace_selection.v1',
               'source_path': str(args.trace.resolve()), 'source_sha256': hashlib.sha256(raw).hexdigest(),
               'source_records': total, 'source_versions': versions, 'session': args.session,
               'selected_records': len(selected), 'excluded_records': total - len(selected),
               'selection': 'v2 records matching session, original order',
               'output_sha256': hashlib.sha256(output).hexdigest(),
               'warrant': 'file selection only; no real-session or custody attestation'}
    created = []
    try:
        for path, content in ((args.output, output), (args.receipt, (json.dumps(receipt, sort_keys=True) + '\n').encode())):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    print(f'selected {len(selected)} of {total} records')


if __name__ == '__main__':
    main()
