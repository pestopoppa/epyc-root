#!/usr/bin/env python3
"""Produce one prospective FM-4 acceptance record for a real dispatch, by hand.

Pure composition of `run_gate.py` (executes the caller's pre-registered gate)
and `task_acceptance.py` (identity-bound record, digest-verified evidence and,
optionally, transcript snapshots). The record lands at a deterministic path:

    <root>/<task_id with "/" -> "__">/<dispatch_tool_use_id>.json

and is re-validated from disk before its path is printed. Exit 0 = record
written and valid; exit 1 = no record (gate timeout/launch error/signal, bad
identity, existing output, or post-write validation failure).

The caller chooses the gate BEFORE the dispatch runs and supplies the task ID
from its own dispatch context; neither is inferred here. No hook, no daemon.
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_gate  # noqa: E402
from task_acceptance import IDENTIFIER, IDENTITIES, _unique_object, validate_record  # noqa: E402


def record_path(root, task_id, dispatch_tool_use_id):
    for name, value in (("task_id", task_id), ("dispatch_tool_use_id", dispatch_tool_use_id)):
        if (not isinstance(value, str) or not IDENTIFIER.fullmatch(value)
                or any(part in (".", "..") for part in value.split("/"))):
            raise ValueError(f"invalid {name}")
    if "/" in dispatch_tool_use_id:
        raise ValueError("invalid dispatch_tool_use_id")
    return Path(root) / task_id.replace("/", "__") / (dispatch_tool_use_id + ".json")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    separator = argv.index("--") if "--" in argv else len(argv)
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--timeout-s", required=True)
    for name in IDENTITIES:
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    parser.add_argument("--child-transcript", type=Path)
    parser.add_argument("--parent-transcript", type=Path)
    args = parser.parse_args(argv[:separator])
    gate = argv[separator + 1:]
    if not gate:
        parser.error("supply a gate executable and its arguments after --")
    try:
        out = record_path(args.root, args.task_id, args.dispatch_tool_use_id)
        out.parent.mkdir(parents=True, exist_ok=True)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    forwarded = ["--out", str(out), "--cwd", args.cwd, "--timeout-s", args.timeout_s]
    for name in IDENTITIES:
        forwarded += ["--" + name.replace("_", "-"), getattr(args, name)]
    for role in ("child", "parent"):
        source = getattr(args, role + "_transcript")
        if source is not None:
            forwarded += [f"--{role}-transcript", str(source)]
    saved = sys.stdout
    sys.stdout = sys.stderr  # keep stdout to the single record path
    try:
        rc = run_gate.main(forwarded + ["--"] + gate)
    finally:
        sys.stdout = saved
    if rc != 0:
        return rc
    try:
        validate_record(json.loads(out.read_text(), object_pairs_hook=_unique_object))
    except (ValueError, OSError) as exc:
        print(f"written record failed validation: {exc}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
