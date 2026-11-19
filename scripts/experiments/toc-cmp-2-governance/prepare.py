#!/usr/bin/env python3
"""Stage the row packet and bind a previously computed model digest. No inference."""

import argparse
import re
import shutil
import subprocess
from pathlib import Path

from runner import HERE, SCRATCH, atomic_json, digest, file_identity, sealed

ROOT = HERE.parents[2]
BIN = Path("/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin")
BUILD = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
MODEL = Path("/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507-GGUF/Qwen3-4B-Instruct-2507-Q8_0.gguf")
LINKAGE = Path("/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
RUNTIME = (
    "llama-server", "libllama-server-impl.so", "libllama-common.so.0.0.10303",
    "libllama.so.0.0.10303", "libggml.so.0.16.0", "libggml-base.so.0.16.0",
    "libggml-cpu.so.0.16.0",
)


def prepare(model_digest_path):
    fields = model_digest_path.read_text().strip().split(maxsplit=1)
    if len(fields) != 2 or not re.fullmatch("[a-f0-9]{64}", fields[0]) or Path(fields[1]) != MODEL:
        raise ValueError("provide an original sha256sum receipt for the pinned model")
    if (Path("/mnt/raid0/llm/kernels/production/cpu").resolve() != BIN
            or model_digest_path.stat().st_mtime_ns < MODEL.stat().st_ctime_ns):
        raise ValueError("production build identity changed or the pre-grant weight digest is stale")
    recorded = {}
    build_manifest = BIN.parent / "SHA256SUMS"
    for line in build_manifest.read_text().splitlines():
        sha, rel_path = line.split(maxsplit=1)
        if rel_path.startswith("bin/"):
            recorded[rel_path.removeprefix("bin/")] = sha
    build_digests = {name: recorded[name] for name in RUNTIME}
    for name, expected in build_digests.items():
        if digest((BIN / name).read_bytes()) != expected:
            raise ValueError(f"approved runtime artifact differs: {name}")

    packet = SCRATCH / "packet"
    packet.mkdir(parents=True, exist_ok=True)
    (SCRATCH / "native").mkdir(exist_ok=True)
    files = [HERE / name for name in ("cases.json", "runner.py", "launcher.sh", "spec.json", "README.md")]
    files += [ROOT / "docs/reference/governance/rule_registry.json", LINKAGE]
    packet_digests = {}
    for src in files:
        staged = packet / src.name
        shutil.copy2(src, staged)
        packet_digests[src.name] = digest(staged.read_bytes())
    manifest = {
        "packet_sha256": packet_digests,
        "source_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "build_commit": BUILD,
        "build_version": 10303,
        "bin_dir": str(BIN),
        "build_sha256": build_digests,
        "build_manifest_sha256": digest(build_manifest.read_bytes()),
        "linkage_verifier": str(packet / LINKAGE.name),
        "model": {"path": str(MODEL), "sha256": fields[0], "stat_at_hash": file_identity(MODEL),
                  "sha256_receipt": model_digest_path.read_text().strip()},
    }
    atomic_json(packet / "input-manifest.json", sealed(manifest))
    return packet / "spec.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-digest", required=True, type=Path)
    opts = parser.parse_args()
    print(prepare(opts.model_digest))
