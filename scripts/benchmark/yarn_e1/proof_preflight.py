#!/usr/bin/env python3
"""Run the pinned E1 GPU preflight read-only, without starting a server.

Adopts the reviewed shared matcher directly from its git object. No historical
packet, model, server, or research checkout is modified. A zero exit requires
all live-host checks as well as log proofs; unavailable inspection fails closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import types

SOURCE_COMMIT = "0e4321f24bae29355333fcf2cb712a41ce080e2f"
SOURCE_ROOT = "scripts/benchmark/yarn_e1"
DEFAULT_REPO = "/mnt/raid0/llm/epyc-inference-research"


def load_runner(repo: str):
    """Import the two reviewed modules in memory, independent of checkout HEAD."""
    def source(name):
        return subprocess.check_output(
            ["git", "-C", repo, "show", f"{SOURCE_COMMIT}:{SOURCE_ROOT}/{name}.py"],
            stderr=subprocess.PIPE,
        )

    # Fetch both objects before executing anything, and restore the import table
    # so an embedding caller's yarn_proof module cannot be replaced accidentally.
    helper_source, runner_source = source("yarn_proof"), source("yarn_needle")
    helper = types.ModuleType("yarn_proof")
    helper.__file__ = f"git:{SOURCE_COMMIT}/{SOURCE_ROOT}/yarn_proof.py"
    runner = types.ModuleType("_pinned_yarn_needle")
    runner.__file__ = str(Path(repo) / SOURCE_ROOT / "yarn_needle.py")
    previous = sys.modules.get("yarn_proof")
    try:
        exec(compile(helper_source, helper.__file__, "exec"), helper.__dict__)
        sys.modules["yarn_proof"] = helper
        exec(compile(runner_source, runner.__file__, "exec"), runner.__dict__)
    finally:
        if previous is None:
            sys.modules.pop("yarn_proof", None)
        else:
            sys.modules["yarn_proof"] = previous
    return runner


def main(argv=None, *, loader=load_runner) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--arm", required=True, choices=["A0", "A0Q4", "A1", "A2"])
    parser.add_argument("--port", type=int, default=18083)
    parser.add_argument("--server-log", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    output = Path(args.output)
    log = Path(args.server_log)
    if output.resolve() == log.resolve() or output.exists():
        parser.error("output must be a new file distinct from the server log")
    result = {"source_commit": SOURCE_COMMIT, "arm": args.arm, "port": args.port,
              "server_log": str(log), "force_preflight": False}
    try:
        runner = loader(args.repo)
        # No stubs, force flag, launch, or completion endpoint in this path.
        result["preflight"] = runner.preflight(args, f"http://127.0.0.1:{args.port}")
        result["ok"] = not result["preflight"]["problems"]
    except Exception as exc:
        result.update(ok=False, error=f"{type(exc).__name__}: {exc}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"ok": result["ok"], "output": str(output)}))
    return 0 if result["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
