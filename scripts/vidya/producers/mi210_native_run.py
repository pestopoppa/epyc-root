"""Native writer integration only. Does not attest protocols or infer missing warrant."""
import os
import re
import uuid
from pathlib import Path

from scripts.vidya.producers import mi210_paired_capture as raw


def identity(path):
    path = Path(path)
    try:
        return {"path": str(path), "sha256": raw.carrier.file_sha256(path), "error": None}
    except OSError as error:
        return {"path": str(path), "sha256": None, "error": repr(error)}


def grant():
    """Capture only an explicitly supplied grant artifact; absent remains unknown."""
    path = os.environ.get("MI210_BELIEF_GRANT")
    return identity(path) if path else None


def build_identity(directory):
    directory = Path(directory)
    return {"source_commit": None, "files": [identity(p) for p in
            [directory / "llama-server", *sorted(directory.glob("libggml*.so*")),
             *sorted(directory.glob("libllama*.so*"))]]}


def model_identities(path):
    """Enumerate declared GGUF shard count, including explicitly missing shards."""
    path = Path(path)
    match = re.fullmatch(r"(.+-)(\d{5})(-of-)(\d{5})(\.gguf)", path.name)
    if not match:
        return [identity(path)]
    count = int(match[4])
    if not 1 <= count <= 1024:
        raise ValueError("bounded GGUF shard count required")
    return [identity(path.with_name(f"{match[1]}{i:05d}{match[3]}{match[4]}{match[5]}"))
            for i in range(1, count + 1)]


class NativeRun:
    def __init__(self, out, declaration):
        self.root = Path(out) / ("belief-" + uuid.uuid4().hex)
        self.root.mkdir()
        raw.begin(self.root, declaration)
        self.active = None
        self.closed = False
        self.stop = None

    def __enter__(self):
        return self

    def start(self, pair, arm):
        if self.active is not None:
            raise ValueError("previous launch not recorded")
        self.active = {"pair": pair, "arm": arm, "state": "partial", "requests": [],
                       "actual_placement": None, "residency_linkage": None,
                       "grant": grant(), "stop": None, "errors": None, "release": None}

    def update(self, **fields):
        if self.active is None:
            raise ValueError("no active native launch")
        self.active.update(fields)

    def record(self, state):
        self.update(state=state)
        raw.record(self.root, self.active)
        self.active = None

    def complete(self):
        raw.finish(self.root, "complete")
        self.closed = True

    def __exit__(self, kind, error, traceback):
        if self.closed:
            return False
        state = "stopped" if self.stop is not None or isinstance(error, (KeyboardInterrupt, SystemExit)) else "failed" if error else "partial"
        errors = [repr(error)] if error else None
        if self.active is not None:
            self.update(stop=self.stop, errors=(self.active.get("errors") or []) + (errors or []))
            self.record(state)
        if state == "partial" and any(x["native"]["state"] == "failed" for x in raw.read(self.root)["attempts"]):
            state = "failed"
        raw.finish(self.root, state, stop=self.stop, errors=errors)
        self.closed = True
        return False
