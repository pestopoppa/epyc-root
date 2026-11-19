#!/usr/bin/env python3
"""Seal the CF-3c task-level diagnostic without opening the model weights."""

import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-task")
SOURCE = SCRATCH / "source"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
PYTHON = ORCH / ".venv/bin/python"
BASE = "12afe2858f9dbd4691447926d6cf1864de64348c"
HARNESS_REF = "ed0496bf38d9228bd8420f5b8c3fde238097de9f"
WEIGHT_RECEIPT_SHA = "3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff"
PROTOCOL = HERE.parents[2] / "docs/design/cf3c-task-level-protocol-20261118.md"
FILES = (
    "prepare.py",
    "runner.py",
    "policies.py",
    "environment.py",
    "test_task_level.py",
    "launcher.sh",
    "spec.json",
    "README.md",
    "protocol.md",
)
COPIED = (
    "cmp4_runner.py",
    "analysis.py",
    "verify_ggml_linkage.sh",
    "prior-model-receipt.json",
    "cases.json",
)
SERVING = (
    "model_path",
    "model_sha256",
    "model_stat",
    "template_sha256",
    "build_sha256",
)
CASE_PLAN = (
    ("archive-tail", "tool-tail", 2, "OR-351", 923741),
    ("archive-head", "tool-head", 3, "OR-629", 392847),
    ("archive-reasoning", "assistant-reasoning", 4, "OR-814", 620539),
)


def checkout_file(name):
    return PROTOCOL if name == "protocol.md" else HERE / name


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(packet):
    subprocess.run(
        [str(PYTHON), "-I", "-B", str(packet / "runner.py"), "verify"], check=True
    )


def seal(staged):
    for name in FILES:
        shutil.copy2(checkout_file(name), staged / name)
    for name, relative in (
        ("cmp4_runner.py", "runner.py"),
        ("analysis.py", "analysis.py"),
    ):
        (staged / name).write_bytes(
            subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(HERE),
                    "show",
                    f"{HARNESS_REF}:scripts/experiments/toc-cmp-4-live/{relative}",
                ]
            )
        )
    receipt_path = SCRATCH.parent / "cmp4-r2/packet/inputs.json"
    if digest(receipt_path) != WEIGHT_RECEIPT_SHA:
        raise ValueError("retained weight receipt hash changed")
    shutil.copy2(receipt_path, staged / "prior-model-receipt.json")
    receipt = json.loads((staged / "prior-model-receipt.json").read_text())
    if receipt["source"] != BASE:
        raise ValueError("retained receipt identifies a different source")
    linkage = Path(
        "/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh"
    )
    if (
        digest(linkage)
        != "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33"
    ):
        raise ValueError("linkage script differs from the original pinned receipt")
    shutil.copy2(linkage, staged / "verify_ggml_linkage.sh")

    fixture = SCRATCH / "fixture-cases.json"
    if not fixture.exists():
        cases = [
            {
                "id": case_id,
                "location": location,
                "desk": desk,
                "order": order,
                "seed": seed,
                "receipt": secrets.token_hex(6),
                "challenge": secrets.token_hex(4),
                "confirmation": secrets.token_hex(6),
            }
            for case_id, location, desk, order, seed in CASE_PLAN
        ]
        write_json(staged / "cases.json", cases)
        (staged / "cases.json").chmod(0o400)
        os.link(staged / "cases.json", fixture)
    else:
        shutil.copyfile(fixture, staged / "cases.json")
    write_json(
        staged / "inputs.json",
        {
            "source": BASE,
            "cmp4_harness_ref": HARNESS_REF,
            "cmp4_weight_receipt_sha256": WEIGHT_RECEIPT_SHA,
            **{name: receipt[name] for name in SERVING},
            "packet_sha256": {
                name: digest(staged / name) for name in sorted(FILES + COPIED)
            },
        },
    )
    check(staged)


def prepare():
    SCRATCH.mkdir(mode=0o700, parents=True, exist_ok=True)
    packet = SCRATCH / "packet"
    if packet.exists():
        check(packet)
        for name in FILES:
            if checkout_file(name).read_bytes() != (packet / name).read_bytes():
                raise ValueError(f"sealed packet differs from checkout: {name}")
        return packet / "spec.json"
    if not SOURCE.exists():
        subprocess.run(
            [
                "git",
                "-C",
                str(ORCH),
                "worktree",
                "add",
                "--quiet",
                "--detach",
                str(SOURCE),
                BASE,
            ],
            check=True,
        )

    with tempfile.TemporaryDirectory(prefix=".seal-", dir=SCRATCH) as temporary:
        staged = Path(temporary) / "packet"
        staged.mkdir(mode=0o700)
        seal(staged)
        for path in staged.iterdir():
            path.chmod(0o500 if os.access(path, os.X_OK) else 0o400)
        staged.rename(packet)
        packet.chmod(0o500)
    return packet / "spec.json"


if __name__ == "__main__":
    print(prepare())
