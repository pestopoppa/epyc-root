#!/usr/bin/env python3
"""SC75 / VB-WIRE-2: the launch identity the INF-70 serving-arm capture needs.

The SC75 writer (``scripts/vidya/adapters/inf70_serving_arm_capture.py``) refuses to emit a
belief row unless the producer supplies the launch identity. This helper writes that
``launch.json`` ONCE per launch, from what the running server actually is, and checks it at
arm end. It never computes anything that would disturb a measurement:

* ``launch_recipe.env`` / ``.args`` come from ``/proc/<pid>/environ`` and ``/proc/<pid>/cmdline``
  of the live server, never from the arm script's own intentions.
* ``gguf_sha256`` is NEVER computed here. Hashing a 50+ GB GGUF would refill the page cache
  that the arm's targeted eviction just emptied. It comes from ``$GGUF_SHA256`` or from a
  ``<model>.sha256`` sidecar. If neither exists the field is left out, and the capture fails
  loudly at arm end. The measurement itself still runs.
* ``kernel_commit`` is parsed from the ``llama-server --version`` line the arm already records,
  or taken from ``$KERNEL_COMMIT``.

  sc75_launch.py write --out F --launch-id ID --pid PID --model M --version-line V
                       --pinning P --bench-cpus C
  sc75_launch.py arm   --session F --out F2 --knobs "K=V,K=V"   per-arm copy (hot server)
  sc75_launch.py check F                                         exit 3 + names missing fields

``$SC75_PROC`` (default ``/proc``) lets the test point the reader at a fixture tree.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

#: The fields the SC75 writer requires (``write_arm_measurement`` docstring + SC75 evidence in
#: handoffs/active/vidya-belief-substrate-program.md). Order is the documented order.
REQUIRED = ("launch_id", "model_path", "gguf_sha256", "kernel_commit", "binary_version",
            "launch_recipe", "pinning", "bench_cpus")
ENV_PREFIXES = ("GGML_", "OMP_", "LLAMA_")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_IN_VERSION = re.compile(r"\(([0-9a-f]{7,40})\)")


def _proc() -> Path:
    return Path(os.environ.get("SC75_PROC", "/proc"))


def _read_environ(pid: str) -> dict[str, str]:
    raw = (_proc() / pid / "environ").read_bytes()
    env = {}
    for item in raw.split(b"\0"):
        if b"=" not in item:
            continue
        key, _, value = item.decode(errors="replace").partition("=")
        if key.startswith(ENV_PREFIXES):
            env[key] = value
    return dict(sorted(env.items()))


def _read_args(pid: str) -> list[str]:
    raw = (_proc() / pid / "cmdline").read_bytes()
    parts = [p.decode(errors="replace") for p in raw.split(b"\0") if p]
    return parts[1:]


def _gguf_sha256(model: str) -> str | None:
    value = os.environ.get("GGUF_SHA256", "").strip().lower()
    if not value:
        sidecar = Path(model + ".sha256")
        if sidecar.is_file():
            tokens = sidecar.read_text().split()
            value = tokens[0].lower() if tokens else ""
    return value if _SHA256.match(value) else None


def _kernel_commit(version_line: str) -> str | None:
    value = os.environ.get("KERNEL_COMMIT", "").strip().lower()
    if value:
        return value
    match = _COMMIT_IN_VERSION.search(version_line)
    return match.group(1) if match else None


def build_launch(*, launch_id: str, pid: str, model: str, version_line: str, pinning: str,
                 bench_cpus: str) -> dict:
    launch = {
        "launch_id": launch_id,
        "model_path": model,
        "gguf_sha256": _gguf_sha256(model),
        "kernel_commit": _kernel_commit(version_line),
        "binary_version": version_line.strip() or None,
        "launch_recipe": {"env": _read_environ(pid), "args": _read_args(pid), "server_pid": int(pid)},
        "pinning": pinning,
        "bench_cpus": bench_cpus,
    }
    return {k: v for k, v in launch.items() if v is not None}


def missing_fields(launch: dict) -> list[str]:
    out = []
    for key in REQUIRED:
        value = launch.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            out.append(key)
    recipe = launch.get("launch_recipe")
    if "launch_recipe" not in out and not (
            isinstance(recipe, dict) and isinstance(recipe.get("env"), dict)
            and isinstance(recipe.get("args"), list)):
        out.append("launch_recipe{env,args}")
    return out


def _atomic_write(path: Path, payload: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    for flag in ("--out", "--launch-id", "--pid", "--model", "--version-line", "--pinning",
                 "--bench-cpus"):
        w.add_argument(flag, required=True)
    a = sub.add_parser("arm")
    a.add_argument("--session", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--knobs", default="")
    c = sub.add_parser("check")
    c.add_argument("path")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "write":
            launch = build_launch(launch_id=args.launch_id, pid=args.pid, model=args.model,
                                  version_line=args.version_line, pinning=args.pinning,
                                  bench_cpus=args.bench_cpus)
            _atomic_write(Path(args.out), launch)
            gaps = missing_fields(launch)
            print(f"launch.json {args.out}" + (f" MISSING {','.join(gaps)}" if gaps else " complete"))
            return 0
        if args.cmd == "arm":
            launch = json.loads(Path(args.session).read_text())
            recipe = dict(launch.get("launch_recipe") or {})
            # the hot server switches knobs through the live control page, not the process
            # environment, so the arm's own payload is part of what this arm measured
            recipe["knob_page_payload"] = [kv for kv in args.knobs.split(",") if kv]
            launch["launch_recipe"] = recipe
            _atomic_write(Path(args.out), launch)
            return 0
        launch = json.loads(Path(args.path).read_text())
        gaps = missing_fields(launch)
        if gaps:
            print(f"launch.json {args.path} is missing required field(s): {', '.join(gaps)}")
            return 3
        return 0
    except (OSError, ValueError) as exc:
        print(f"sc75_launch {args.cmd} failed: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
