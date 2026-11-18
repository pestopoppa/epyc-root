#!/usr/bin/env python3
"""Seal the registered requests and retained DCP-12 serving custody."""

import fcntl
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/thinking-probe")
DCP12 = SCRATCH.parent / "dcp12"
PYTHON = Path("/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python")
ROW = "thinking-budget-semantics-20261118"
PORT = 19389
WINDOW_S = 1200
REQUEST_S = 100
STARTUP_S = 160
MAX_TOKENS = 128
BUDGET = 8
PROMPT = (
    "A bus has 42 passengers. At the first stop one third leave and 9 board. "
    "At the next stop 5 leave and twice that many board. How many passengers "
    "are on the bus now? Give the final number."
)
ARMS = ("budget-omitted", "budget-8", "thinking-disabled")
LOCAL_FILES = ("prepare.py", "runner.py", "launcher.sh", "spec.json", "README.md", "test_protocol.py")
DCP_PINS = {
    "inputs.json": "b8a03a2f9895acb9b16e7fe83590ef686458c1b982e89bbed51380091f534b83",
    "prior-model-receipt.json": "3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff",
    "cmp4_runner.py": "ccb3200093bf14136acdf4ac6de7feefd91485d4ca3607085c7c29c170f93e7a",
    "analysis.py": "4d59e79e57aa630ccf82335d44180cadd393c6899a1cde3f2a6b739b46722b4d",
    "verify_ggml_linkage.sh": "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33",
    "own_port_proof.py": "f6a410abddb7333a5bed8309443f6ecf12bf1eb5db70ed7186baa11e2f212baf",
}
KERNEL = Path("/mnt/raid0/llm/llama.cpp")
COMMIT = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
BUILD = Path("/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82")
BUILD_PINS = {
    "PROVENANCE.md": "a3dba6ae9cf8c2a49d76866d8b1dfef6890300743f3df96538d74c7a09bf6058",
    "SHA256SUMS": "ccfe57b18bc720e569c2e97e55454a27865d15dd928857d4ba3674874a1608a2",
}
SOURCES = {
    "tools/server/server-common.cpp": (1058, 1132),
    "tools/server/server-task.cpp": (444, 490),
}
SERVING = ("model_path", "model_sha256", "model_stat", "template_sha256", "build_sha256")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def check_digest(path, expected):
    if path.is_symlink() or digest(path) != expected:
        raise ValueError(f"source or receipt pin mismatch: {path}")


def requests(model):
    registered = []
    for arm in ARMS:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT}],
            "stream": False,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
            "top_k": 1,
            "seed": 20261118,
            "cache_prompt": False,
            "verbose": True,
            "return_tokens": True,
            "reasoning_format": "deepseek",
            "chat_template_kwargs": {"enable_thinking": arm != "thinking-disabled"},
        }
        if arm == "budget-8":
            body["thinking_budget_tokens"] = BUDGET
        registered.append({"unit": arm, "body": body})
    return registered


def retain_v10_source(staged):
    evidence = {"commit": COMMIT, "build": str(BUILD), "build_pins": BUILD_PINS, "snippets": {}}
    for path, (first, last) in SOURCES.items():
        blob = subprocess.check_output(["git", "-C", str(KERNEL), "show", f"{COMMIT}:{path}"])
        evidence["snippets"][path] = {
            "lines": [first, last],
            "git_blob_sha256": hashlib.sha256(blob).hexdigest(),
            "text": "\n".join(blob.decode().splitlines()[first - 1:last]),
        }
    (staged / "v10-source.json").write_text(json.dumps(evidence, indent=2) + "\n")


def verify_packet(packet):
    inputs = packet / "inputs.json"
    pins = packet / "sha256.json"
    if inputs.is_symlink() or pins.is_symlink():
        raise ValueError("packet manifest must be a regular file")
    hashes = read_json(pins)
    if set(hashes) != set((*LOCAL_FILES, *DCP_PINS, *BUILD_PINS, "requests.json", "v10-source.json")):
        raise ValueError("packet file set differs from registration")
    for name, sha in hashes.items():
        expected = (DCP_PINS | BUILD_PINS).get(name, sha)
        if sha != expected:
            raise ValueError(f"retained receipt pin differs: {name}")
        check_digest(packet / name, expected)
    inherited = read_json(inputs)
    prior = read_json(packet / "prior-model-receipt.json")
    if any(inherited[field] != prior[field] for field in SERVING):
        raise ValueError("DCP-12 serving identity differs from the earlier weight receipt")
    if read_json(packet / "requests.json") != requests(Path(inherited["model_path"]).name):
        raise ValueError("sealed native requests differ from registration")
    return {field: inherited[field] for field in SERVING}


def prepare():
    SCRATCH.mkdir(mode=0o700, parents=True, exist_ok=True)
    packet = SCRATCH / "packet"
    with (SCRATCH / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if packet.exists():
            verify_packet(packet)
            for name in LOCAL_FILES:
                check_digest(packet / name, digest(HERE / name))
            subprocess.run([str(PYTHON), "-I", "-B", str(packet / "runner.py"), "verify"], check=True)
            return packet / "spec.json"
        with tempfile.TemporaryDirectory(prefix=".seal-", dir=SCRATCH) as temporary:
            staged = Path(temporary) / "packet"
            staged.mkdir(mode=0o700)
            for name in LOCAL_FILES:
                shutil.copy2(HERE / name, staged / name)
            for name, sha in DCP_PINS.items():
                source = (DCP12 / "source/scripts/benchmark" if name == "own_port_proof.py"
                          else DCP12 / "packet") / name
                check_digest(source, sha)
                shutil.copy2(source, staged / name)
            for name, sha in BUILD_PINS.items():
                check_digest(BUILD / name, sha)
                shutil.copy2(BUILD / name, staged / name)
            retain_v10_source(staged)
            model = Path(read_json(staged / "inputs.json")["model_path"]).name
            (staged / "requests.json").write_text(json.dumps(requests(model), indent=2) + "\n")
            hashes = {path.name: digest(path) for path in sorted(staged.iterdir())}
            (staged / "sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
            subprocess.run([str(PYTHON), "-I", "-B", str(staged / "runner.py"), "verify"], check=True)
            for path in staged.iterdir():
                path.chmod(0o500 if path.stat().st_mode & 0o100 else 0o400)
            staged.rename(packet)
            packet.chmod(0o500)
    return packet / "spec.json"


if __name__ == "__main__":
    print(prepare())
