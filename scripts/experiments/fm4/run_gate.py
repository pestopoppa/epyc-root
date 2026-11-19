#!/usr/bin/env python3
"""Run a caller-selected FM-4 acceptance gate using direct argv after `--`.

The gate's exit code describes that gate alone. The caller supplies a suitable
gate and the actual dispatch identities. The timeout kills and reaps the direct
child only. Descendants can survive and may keep writing to their output files.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from task_acceptance import IDENTIFIER, IDENTITIES, write_record


SCHEMA = "fm4.gate_execution.v1"


def _require_new(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return
    raise ValueError(f"output already exists: {path}")


def _preflight(args, gate, identities):
    for name, value in identities.items():
        if (not IDENTIFIER.fullmatch(value)
                or any(part in (".", "..") for part in value.split("/"))):
            raise ValueError(f"invalid {name}")
    if not math.isfinite(args.timeout_s) or args.timeout_s <= 0:
        raise ValueError("--timeout-s must be finite and positive")
    if not gate[0] or any("\x00" in word for word in gate):
        raise ValueError("invalid gate argv")
    cwd = Path(args.cwd).resolve(strict=True)
    if str(cwd) != args.cwd or not cwd.is_dir():
        raise ValueError("--cwd must be a canonical absolute directory")

    parent = args.out.parent.resolve(strict=True)
    if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
        raise ValueError(f"output parent must be a writable directory: {parent}")
    output = parent / args.out.name
    store = parent / "evidence"
    if output == store:
        raise ValueError("--out conflicts with the evidence store")
    execution = output.with_name(output.name + ".execution.json")
    _require_new(output)
    _require_new(execution)
    for role in ("child", "parent"):
        source = getattr(args, role + "_transcript", None)
        if source is not None and (source.is_symlink() or not source.is_file()):
            raise ValueError(f"{role} transcript must be an existing regular file, not a symlink")
    if store.is_symlink() or (store.exists() and (
            not store.is_dir() or not os.access(store, os.W_OK | os.X_OK))):
        raise ValueError(f"evidence store must be a writable directory: {store}")
    return cwd, output, execution


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _write_execution(dest, metadata, stdout, stderr):
    # Snapshot the lengths and use positional reads so surviving descendants
    # cannot extend the capture or cause reads to move their output offsets.
    captures = [(name, stream.fileno(), os.fstat(stream.fileno()).st_size)
                for name, stream in (("stdout", stdout), ("stderr", stderr))]
    dest.write(json.dumps(metadata, sort_keys=True).encode()[:-1])
    for name, fd, length in captures:
        dest.write(f', "{name}_base64": "'.encode())
        offset = 0
        remainder = b""
        while offset < length:
            chunk = os.pread(fd, min(48 * 1024, length - offset), offset)
            if not chunk:
                raise OSError(f"{name} capture shortened while reading captured output")
            offset += len(chunk)
            data = remainder + chunk
            split = len(data) - len(data) % 3
            dest.write(base64.b64encode(data[:split]))
            remainder = data[split:]
        dest.write(base64.b64encode(remainder) + b'"')
    dest.write(b"}\n")


def _run_gate(gate, cwd, timeout_s, execution, identities):
    metadata = dict(schema=SCHEMA, argv=gate, cwd=str(cwd), timeout_s=timeout_s,
                    returncode=None, timed_out=False, launch_error=None, **identities)
    with (tempfile.TemporaryFile(dir=execution.parent) as stdout,
          tempfile.TemporaryFile(dir=execution.parent) as stderr,
          execution.open("xb") as evidence):
        metadata["started_at"] = _utc_now()
        try:
            result = subprocess.run(gate, cwd=cwd, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr, timeout=timeout_s,
                                    shell=False, check=False)
            metadata["returncode"] = result.returncode
        except subprocess.TimeoutExpired:
            metadata["timed_out"] = True
        except OSError as exc:
            metadata["launch_error"] = str(exc)
        metadata["ended_at"] = _utc_now()
        _write_execution(evidence, metadata, stdout, stderr)
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, allow_abbrev=False,
        epilog="Execution evidence is saved to OUT.execution.json. Exit 0 means an "
               "acceptance record was written. A timeout, launch error, or signal "
               "termination exits 1 with execution evidence only.",
    )
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--timeout-s", required=True, type=float)
    for name in IDENTITIES:
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    parser.add_argument("--child-transcript", type=Path,
                        help="snapshot this child transcript into the record (schema v1.1)")
    parser.add_argument("--parent-transcript", type=Path,
                        help="snapshot this parent transcript into the record (schema v1.1)")
    argv = list(sys.argv[1:] if argv is None else argv)
    separator = argv.index("--") if "--" in argv else len(argv)
    args = parser.parse_args(argv[:separator])
    gate = argv[separator + 1:]
    if not gate:
        parser.error("supply a gate executable and its arguments after --")
    identities = {name: getattr(args, name) for name in IDENTITIES}
    try:
        cwd, output, execution = _preflight(args, gate, identities)
        result = _run_gate(gate, cwd, args.timeout_s, execution, identities)
        if result["timed_out"]:
            raise ValueError(f"gate timed out after {args.timeout_s:g} s. Evidence saved at {execution}")
        if result["launch_error"] is not None:
            raise ValueError(f"gate launch failed: {result['launch_error']}. Evidence saved at {execution}")
        returncode = result["returncode"]
        if returncode < 0:
            raise ValueError(f"gate terminated by signal {-returncode}. Evidence saved at {execution}")
        with execution.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        record = write_record(
            output, **identities, gate_result="pass" if returncode == 0 else "fail",
            evidence_path=execution, evidence_sha256=digest,
            child_transcript=args.child_transcript, parent_transcript=args.parent_transcript,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
