#!/usr/bin/env python3
"""Seal the CF-3c active-evidence replay using the verified frontdoor receipt."""
import hashlib
import json
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-active")
SOURCE = SCRATCH / "source"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
BASE = "12afe2858f9dbd4691447926d6cf1864de64348c"
HARNESS_REF = "ed0496bf38d9228bd8420f5b8c3fde238097de9f"
WEIGHT_RECEIPT_SHA = "3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff"
FILES = ("prepare.py", "policies.py", "runner.py", "launcher.sh", "spec.json", "README.md", "protocol.md")
PYTHON = ORCH / ".venv/bin/python"
PROTOCOL = HERE.parents[2] / "docs/design/cf3c-active-evidence-protocol-20261118.md"


def prepare():
    SCRATCH.mkdir(mode=0o700, parents=True, exist_ok=True)
    packet = SCRATCH / "packet"
    def verify(folder):
        subprocess.run([str(PYTHON), "-I", "-B", str(folder / "runner.py"), "verify"], check=True)

    if packet.exists():
        verify(packet)
        for name in FILES:
            src = PROTOCOL if name == "protocol.md" else HERE / name
            if src.read_bytes() != (packet / name).read_bytes():
                raise ValueError(f"sealed packet differs from checkout: {name}")
        return packet / "spec.json"
    if not SOURCE.exists():
        subprocess.run(["git", "-C", str(ORCH), "worktree", "add", "--quiet", "--detach",
                        str(SOURCE), BASE], check=True)

    with tempfile.TemporaryDirectory(prefix=".seal-", dir=SCRATCH) as temporary:
        staged = Path(temporary) / "packet"
        staged.mkdir(mode=0o700)
        for name in FILES:
            shutil.copy2(PROTOCOL if name == "protocol.md" else HERE / name, staged / name)
        for name, relative in (("cmp4_runner.py", "runner.py"), ("analysis.py", "analysis.py")):
            (staged / name).write_bytes(subprocess.check_output([
                "git", "-C", str(HERE), "show", f"{HARNESS_REF}:scripts/experiments/toc-cmp-4-live/{relative}",
            ]))
        sys.path.insert(0, str(staged))
        import cmp4_runner as live

        receipt_bytes = (SCRATCH.parent / "cmp4-r2/packet/inputs.json").read_bytes()
        receipt = json.loads(receipt_bytes)
        if (hashlib.sha256(receipt_bytes).hexdigest() != WEIGHT_RECEIPT_SHA
                or receipt["source"] != BASE or receipt["model_path"] != str(live.MODEL)
                or receipt["model_sha256"] != live.MODEL_SHA or receipt["template_sha256"] != live.TEMPLATE_SHA
                or receipt["model_stat"] != live.file_identity(live.MODEL)):
            raise ValueError("verified weight receipt differs from the current model")
        (staged / "prior-model-receipt.json").write_bytes(receipt_bytes)
        shutil.copy2(live.LINKAGE, staged / "verify_ggml_linkage.sh")
        # The isolated interpreter imports the actual pinned compressor and
        # emits the case dimensions. No mutable source tree is put on PYTHONPATH.
        dimensions = json.loads(subprocess.check_output(
            [str(PYTHON), "-I", "-B", str(staged / "runner.py"), "dimensions"], text=True))
        fixture_dir = SCRATCH / "prepared"
        fixture_dir.mkdir(mode=0o700, exist_ok=True)
        fixture = fixture_dir / "cases.json"
        if not fixture.exists():
            rng = secrets.SystemRandom()
            seeds = rng.sample(range(1, 2**31), len(dimensions["cases"]))
            cases = []
            for case, seed in zip(dimensions["cases"], seeds, strict=True):
                values = [secrets.token_hex(8) for _ in range(case["steps"] + 1)]
                cases.append({**case, "seed": seed, "answer": values[0], "decoys": values[1:]})
            live.atomic_json(fixture, cases)
        shutil.copy2(fixture, staged / "cases.json")
        live.atomic_json(staged / "inputs.json", {
            "source": BASE, "cmp4_harness_ref": HARNESS_REF, "cmp4_weight_receipt_sha256": WEIGHT_RECEIPT_SHA,
            **{key: receipt[key] for key in ("model_path", "model_sha256", "model_stat",
                                             "template_sha256", "build_sha256")},
            "packet_sha256": {path.name: live.digest(path) for path in sorted(staged.iterdir()) if path.is_file()},
        })
        verify(staged)
        staged.rename(packet)
    return packet / "spec.json"


if __name__ == "__main__":
    print(prepare())
