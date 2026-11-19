#!/usr/bin/env python3
"""Capture isolated live MCP catalogs without sending inference or calling tools.

Declared launch pins are checked around capture. This is not model-serving or
complete runtime dependency custody; those remain requirements of the live row.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.harness.hs4_p04_acceptance import load_mcp_launch_spec


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def catalog(tools):
    records = [tool.model_dump(mode="json", exclude_none=True) for tool in tools]
    names = [record["name"] for record in records]
    if not records or len(set(names)) != len(names):
        raise ValueError("empty catalog or duplicate tool names")
    return sorted(records, key=lambda record: record["name"])


def check_growth(baseline, candidate):
    before = {tool["name"]: tool for tool in baseline}
    after = {tool["name"]: tool for tool in candidate}
    if not before or len(before) != len(baseline) or len(after) != len(candidate):
        raise ValueError("empty baseline or duplicate tool names")
    for name, tool in before.items():
        if after.get(name) != tool:
            raise ValueError(f"baseline tool removed or changed: {name}")
    added = sorted(after.keys() - before.keys())
    if not added:
        raise ValueError("candidate must add at least one tool")
    return added


async def list_live(spec):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport
    transport = StdioTransport(
        command=spec["command"][0], args=spec["command"][1:],
        cwd=spec["cwd"], env=dict(os.environ), keep_alive=False,
    )
    async with Client(transport) as client:
        return catalog(await client.list_tools())


async def capture(baseline_path, candidate_path, out, *, timeout=30, reader=list_live):
    paths = {"baseline": Path(baseline_path), "candidate": Path(candidate_path)}
    originals = {arm: path.read_bytes() for arm, path in paths.items()}
    specs = {arm: load_mcp_launch_spec(path) for arm, path in paths.items()}
    snapshots = {}
    # Sequential startup avoids mutable module/server state across arms.
    for arm, spec in specs.items():
        snapshots[arm] = await asyncio.wait_for(reader(spec), timeout=timeout)
    added = check_growth(snapshots["baseline"], snapshots["candidate"])
    for arm, path in paths.items():
        if path.read_bytes() != originals[arm] or load_mcp_launch_spec(path) != specs[arm]:
            raise ValueError(f"launch declaration drift: {arm}")
    payloads = {f"{arm}-tools-list.json": encoded(snapshot)
                for arm, snapshot in snapshots.items()}
    receipt = {
        "schema": "hs4-p6-live-catalogs/v1", "added_tools": added,
        "catalogs": {arm: hashlib.sha256(payloads[f"{arm}-tools-list.json"]).hexdigest()
                     for arm in specs},
        "launch_specs": {arm: hashlib.sha256(raw).hexdigest()
                         for arm, raw in originals.items()},
        "scope": "live tools/list with declared file pins; no tool calls, inference, "
                 "model-serving custody or complete dependency-closure proof",
    }
    # An existing output is never overwritten, including a partial failed write.
    Path(out).mkdir(parents=True, exist_ok=False)
    for name, raw in payloads.items():
        with (Path(out) / name).open("xb") as stream:
            stream.write(raw)
    with (Path(out) / "receipt.json").open("xb") as stream:
        stream.write(encoded(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if not 0 < args.timeout <= 120:
        parser.error("timeout must be in (0, 120]")
    try:
        receipt = asyncio.run(capture(args.baseline, args.candidate, args.out,
                                      timeout=args.timeout))
    except Exception as exc:
        print(f"catalog capture refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
