#!/usr/bin/env python3
"""Export an authorized, scoped v2 trace using exact originals in a private manifest.

Run with the orchestrator Python environment. Manifest format: {"queries": {sha256:
text}, "sessions": {session: {"bundle": id, "sections": {original_path: text}}}}.
The manifest and output contain sensitive raw text; choose their custody separately.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--originals', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    info = args.originals.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        parser.error('originals must be an owner-only regular file owned by the current user')
    data = json.loads(args.originals.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) != {'queries', 'sessions'} or not all(
        isinstance(data[k], dict) for k in ('queries', 'sessions')
    ):
        parser.error('originals must contain exactly queries and sessions mappings')
    sys.path.insert(0, str(args.app_root.resolve()))
    from src.repl_environment.trace_capture import load_real_trace_rows, write_real_trace_queries

    query = data['queries'].get
    bundle = data['sessions'].get
    rows = load_real_trace_rows(args.trace, query, bundle)
    if not rows or not any(row.get('gold') and row.get('opened') for row in rows):
        raise ValueError('no opened, scoreable real-trace row in scoped input')
    # Exclusive owner-only creation prevents overwriting another export and limits exposure.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        count = write_real_trace_queries(args.output, args.trace, text_resolver=query, bundle_resolver=bundle)
    except BaseException:
        args.output.unlink(missing_ok=True)
        raise
    print(f'exported {count} rows; freeze must verify corpus custody')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
