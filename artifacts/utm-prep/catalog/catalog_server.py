#!/usr/bin/env python3
"""Opt-in isolated baseline/candidate server and catalog capture for UTM-B1.

Run with the orchestrator environment, from a separate process per arm. Never
changes the default server source or the shared running API.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace


def private_db(root: Path, db: Path) -> Path:
    root = root.resolve(strict=True)
    db = db.resolve(strict=True)
    if not root.is_dir() or root not in db.parents or not db.is_file():
        raise ValueError('DB must be an existing file below the private directory')
    for path in (root, db):
        info = path.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('private root and DB must be owner-only and owned by caller')
    if db.stat().st_mode & 0o222:
        raise ValueError('candidate DB must have no filesystem write bits')
    return db


def build_server(app_root: Path, arm: str, root: Path | None, db: Path | None):
    sys.path.insert(0, str(app_root.resolve(strict=True)))
    from src import mcp_server
    mcp_server._get_plugin_loader()  # Match the standard server's stdio startup.
    if arm == 'candidate':
        if root is None or db is None:
            raise ValueError('candidate needs --private-root and --db')
        path = private_db(root, db)
        from src.trace import navigation
        from src.trace.mcp_tools import register_trace_navigation_tools
        nav = SimpleNamespace(
            search_records=lambda text: navigation.search_records(text, db_path=path),
            get_records=lambda ids: navigation.get_records(ids, db_path=path),
        )
        register_trace_navigation_tools(mcp_server.mcp, navigation=nav)
    return mcp_server.mcp


async def inventory(server):
    from fastmcp import Client
    async with Client(server) as client:
        tools = await client.list_tools()
    return {t.name: t.model_dump(mode='json', exclude_none=True) for t in tools}


def compare(base, candidate):
    expected = {'ms.search', 'ms.expand'}
    added = set(candidate) - set(base)
    removed = set(base) - set(candidate)
    changed = {name for name in base.keys() & candidate.keys() if base[name] != candidate[name]}
    errors = []
    if added != expected or removed or changed:
        errors.append('catalog delta differs from exactly two additions with unchanged existing tools')
    for name, required in [('ms.search', 'text'), ('ms.expand', 'event_ids')]:
        schema = candidate.get(name, {}).get('inputSchema', {})
        props = schema.get('properties', {})
        if (schema.get('required') != [required]
                or props.get('session_id', {}).get('default') != ''
                or props.get('session_id', {}).get('type') != 'string'):
            errors.append(f'{name}: required input or optional session_id differs')
        expected_type = {'ms.search': 'string', 'ms.expand': 'array'}[name]
        if props.get(required, {}).get('type') != expected_type:
            errors.append(f'{name}: wrong input type')
        if name == 'ms.expand' and props.get(required, {}).get('items') != {'type': 'integer'}:
            errors.append(f'{name}: IDs must be integers')
        if set(props) != {required, 'session_id'} or schema.get('additionalProperties') is not False:
            errors.append(f'{name}: unexpected input surface')
    return {'ok': not errors, 'added': sorted(added), 'removed': sorted(removed),
            'changed': sorted(changed), 'errors': errors}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('serve', 'inventory'):
        p = sub.add_parser(name)
        p.add_argument('--app-root', type=Path, required=True)
        p.add_argument('--arm', choices=['baseline', 'candidate'], required=True)
        p.add_argument('--private-root', type=Path)
        p.add_argument('--db', type=Path)
    p = sub.add_parser('compare')
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'compare':
        result = compare(json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text()))
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result['ok'] else 1
    server = build_server(args.app_root, args.arm, args.private_root, args.db)
    if args.command == 'serve':
        server.run(transport='stdio')
    else:
        print(json.dumps(asyncio.run(inventory(server)), sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
