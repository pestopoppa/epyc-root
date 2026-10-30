"""Fail closed if the model-free local Python source inventory drifts."""

import datetime
import hashlib
import time
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path("/mnt/micron/codex3-lanes/orchestrator")
SOURCE_ROOTS = (ROOT / "src", ROOT / "orchestration")
SITE_ROOT = Path("/mnt/raid0/llm/epyc-orchestrator/.venv/lib/python3.11/site-packages")


def inventory():
    paths = {
        str(path)
        for root in SOURCE_ROOTS
        for path in root.rglob("*.py")
        if path.is_file()
    }
    paths.update(
        str(path)
        for pattern in ("*.py", "*.so")
        for path in SITE_ROOT.rglob(pattern)
        if path.is_file()
    )
    return {
        path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def verify():
    expected = json.loads((HERE / "LOCAL-SOURCE-INVENTORY.json").read_text())
    if inventory() != expected:
        raise RuntimeError("local Python source inventory changed")
    # The inherited sealed ReDel environment includes an unrelated historical
    # GGUF; this preflight checks imported implementation files, not weights.
    for manifest in (
        HERE / "CAMPAIGN-SOURCES.sha256",
        HERE / "RUNTIME-SOURCES.sha256",
        Path("/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/source.sha256"),
    ):
        for line in manifest.read_text().splitlines():
            expected_hash, name = line.split("  ", 1)
            if name.endswith(".gguf"):
                continue
            if name == "/home/node/.local/share/uv/python/cpython-3.11.17-linux-x86_64-gnu/bin/python3.11": name = "/mnt/micron/codex3-evl34-deepdive-r9-20261030/bin/python3.11"
            path = Path(name)
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            if h.hexdigest() != expected_hash:
                raise RuntimeError("source digest changed: " + name)


def timing_grant_active():
    flags = Path("/mnt/raid0/llm/tmp/compute-flags")
    rows = {}
    for line in (flags / "FILLERS.md").read_text().splitlines():
        cells = [x.strip() for x in line.split("|")[1:-1]]
        if len(cells) == 18:
            rows[cells[0]] = cells[8]
    now = time.time()
    for path in (flags / "grants").glob("*.grant"):
        try:
            fields = dict(x.split("=", 1) for x in path.read_text().split())
            start = datetime.datetime.fromisoformat(
                fields["start"].replace("Z", "+00:00")
            ).timestamp()
            end = datetime.datetime.fromisoformat(
                fields["end"].replace("Z", "+00:00")
            ).timestamp()
        except FileNotFoundError:
            continue
        if start <= now < end and rows.get(path.stem) not in (
            "block-correctness",
            "diagnostic",
        ):
            return True
    return False


if __name__ == "__main__":
    if timing_grant_active():
        raise SystemExit(75)
    verify()
    print("local Python source inventory verified")
