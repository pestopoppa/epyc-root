"""Prospective KPF-30 observer-stream capture for a run owner.

Create before starting the observer, call feed() as each actual output line arrives,
then finish() with the child exit status. Interrupted captures keep raw rows but do
not publish a complete sidecar. A later reader must never synthesize these records.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "epyc.kpf30.observation.v1"
_FIELDS = ("row", "seq", "n_tokens", "n_seqs", "swa", "causal", "n_kv", "blocks", "live", "mixed",
           "unknown", "live_unknown", "invalid_mask")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_PAIR = re.compile(r"([a-z_]+)=(-?\d+)(?:\s|$)")


def _utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_observer(line):
    """Return native counters or None for unrelated output; malformed KPF30 fails closed."""
    pos = line.find("KPF30 row=")
    if pos < 0:
        if "KPF30 " in line:
            raise ValueError("malformed KPF30 line")
        return None
    text = line[pos + len("KPF30 "):].strip()
    pairs = _PAIR.findall(text)
    if len(pairs) != len(_FIELDS) or tuple(k for k, _ in pairs) != _FIELDS:
        raise ValueError("unexpected KPF30 fields")
    row = {k: int(v) for k, v in pairs}
    if any(v < 0 for v in row.values()) or row["mixed"] > row["live"] or row["live"] > row["blocks"] \
            or row["live_unknown"] > row["live"] or row["live_unknown"] > row["unknown"] \
            or row["unknown"] > row["blocks"] or row["swa"] not in (0, 1) or row["causal"] not in (0, 1):
        raise ValueError("invalid KPF30 counters")
    return row


class Capture:
    """A single, non-resumable run capture: instantiate before launching the measured child."""

    def __init__(self, directory, *, run_id, window_id, host, binary_sha256, prompt_set_sha256, argv, category):
        for name, value in (("run_id", run_id), ("window_id", window_id), ("host", host)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"missing {name}")
        if not _HEX.fullmatch(binary_sha256 or "") or not _HEX.fullmatch(prompt_set_sha256 or ""):
            raise ValueError("binary and prompt-set digests must be sha256")
        if category not in ("BASELINE", "CANDIDATE", "OPTIMUM"):
            raise ValueError("category must be a declared measurement label")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError("argv must be a nonempty string list")
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.rows_path = self.dir / 'kpf30_rows.jsonl'
        self.sidecar = self.dir / 'belief_measurements.jsonl'
        if self.sidecar.exists():
            raise FileExistsError(self.sidecar)
        self.stream = self.rows_path.open('x', encoding='utf-8')
        self.metadata = {"schema": SCHEMA, "run_id": run_id, "window_id": window_id, "host": host,
                         "binary_sha256": binary_sha256, "prompt_set_sha256": prompt_set_sha256,
                         "argv": list(argv), "start_utc": _utc(), "category": category}
        self.totals = {k: 0 for k in ("blocks", "live", "mixed", "unknown", "live_unknown", "invalid_mask")}
        self.n_rows = 0
        self.poisoned = False

    def feed(self, line):
        if self.stream.closed:
            raise ValueError("capture is closed")
        try:
            counters = parse_observer(line)
        except ValueError:
            self.poisoned = True
            raise
        if counters is None:
            return False
        self.stream.write(json.dumps(counters, sort_keys=True, separators=(",", ":")) + '\n')
        self.stream.flush()
        self.n_rows += 1
        for key in self.totals:
            self.totals[key] += counters[key]
        return True

    def finish(self, exit_code):
        self.stream.close()
        if type(exit_code) is not int or exit_code != 0 or self.n_rows == 0 or self.poisoned:
            raise ValueError("incomplete observer capture: no claim published")
        data = self.rows_path.read_bytes()
        row = dict(self.metadata, end_utc=_utc(), n_rows=self.n_rows, counts=self.totals,
                   rows=str(self.rows_path.resolve()), rows_sha256=hashlib.sha256(data).hexdigest(),
                   exit_code=exit_code)
        row['record_sha256'] = _digest(row)
        with self.sidecar.open('x', encoding='utf-8') as out:
            out.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + '\n')
        return row


def main(argv=None):
    """Wrap one owner-launched program; this does not acquire compute or schedule work."""
    import argparse
    import os
    import shutil
    import subprocess
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--window-id', required=True)
    parser.add_argument('--prompt-manifest', required=True)
    parser.add_argument('--category', required=True, choices=('BASELINE', 'CANDIDATE', 'OPTIMUM'))
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    cmd = args.command
    if cmd and cmd[0] == '--':
        cmd = cmd[1:]
    if not cmd:
        parser.error('a child command is required after --')
    path = shutil.which(cmd[0])
    if not path or not Path(path).is_file():
        parser.error('child executable must resolve to a file')
    # Hash exactly the executable the wrapper will exec, before launching it.
    binary = str(Path(path).resolve())
    binary_sha = hashlib.sha256(Path(binary).read_bytes()).hexdigest()
    prompt_sha = hashlib.sha256(Path(args.prompt_manifest).read_bytes()).hexdigest()
    cmd[0] = binary
    writer = Capture(args.output, run_id=args.run_id, window_id=args.window_id,
                     host=os.uname().nodename, binary_sha256=binary_sha,
                     prompt_set_sha256=prompt_sha, argv=cmd, category=args.category)
    env = os.environ.copy()
    env['LLAMA_KPF30_MIXED_BLOCKS'] = '1'
    child = None
    try:
        child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding='utf-8', errors='replace', env=env, bufsize=1)
        assert child.stdout is not None
        for line in child.stdout:
            sys.stdout.write(line)
            writer.feed(line)
        status = child.wait()
        writer.finish(status)
        return status
    except BaseException:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait()
        if not writer.stream.closed:
            writer.stream.close()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
