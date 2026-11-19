#!/usr/bin/env python3
"""Seal the model-swap candidate using receipted weights and the fixed r2 controls."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly")
SCRATCH = BASE / "cmp3-evalqual-r3"
R2_PACKET = BASE / "cmp3-evalqual-r2/packet"
R2_SEAL = "3b5f60ee62cac1ec4b89b8b683a9c65a5cc79f7befece41b1c90123e7e9faec8"
CF3C_PACKET = BASE / "cf3c/packet"
CF3C_INPUTS_SHA = "69a3375b7b37ff0a6c5253a58160e5516912395b235baac292e27540962a574a"
ROWFLOW_DRYRUN = Path("/mnt/raid0/llm/tmp/compute-flags/dryrun")
R2_SMOKE = ROWFLOW_DRYRUN / "toc-cmp-3-evalqual-20261118-r2/cmp3-evalqual-r2-native"
R2_SMOKE_SHA256 = {
    "PARTIAL.json": "dfe01e508f2aabbefc9eba4521b6557892e37c5dcc22b06e6b0c5517142f1c59",
    "attempt-01/request.json": "ba9b340e835d1acaf15ee62fab67e447b8596ca5693a53d6d55d295718489f09",
    "attempt-01/response.json": "9e5c36c5e8544129fd5ef611bf1c1cf697f31640c9451596720f3d63feadb9f3",
    "attempt-01/VERDICT.json": "d85f11e1349963d2bcd38c3c848fe6b0dc73de916c3044a13e0180deda2d1755",
    "attempt-02/request.json": "229e014fd83182cecf67777405c07de354d59f5faf00b89d295f9fd021218d28",
    "attempt-02/response.json": "5ffebf2049da14d5528e3645d66e06ff55a48e2cbc11729c2ef830f8e1e20c28",
    "attempt-02/VERDICT.json": "a24a9013bf464ddb90cb86d6aa0fbad434ce84d8039b6df18c3b73a8e4903fb3",
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_bound(path, expected):
    data = path.read_bytes()
    if digest(data) != expected:
        raise ValueError(f"SHA-256 custody mismatch for {path}")
    return data


def model_receipt(pilot, previous):
    model_path = Path(pilot["model_path"])
    device, inode, size, mtime_ns, ctime_ns = pilot["model_stat"]
    identity = {"path": str(model_path.resolve()), "device": device, "inode": inode, "size": size,
                "mtime_ns": mtime_ns, "ctime_ns": ctime_ns}
    bin_dir = Path(previous["bin_dir"])
    expected_builds = {str(bin_dir / name): sha for name, sha in previous["build_sha256"].items()}
    if pilot["build_sha256"] != expected_builds:
        raise ValueError("CF3C evaluator pilot build differs from the pinned v10 CPU build")
    return {"path": str(model_path), "sha256": pilot["model_sha256"], "stat_at_hash": identity}


def prepare():
    packet = SCRATCH / "packet"
    if packet.exists():
        raise ValueError("qualification packet already exists; preserve its custody")
    parent = json.loads((R2_PACKET / "inputs.json").read_bytes())
    if parent.pop("sha256") != R2_SEAL or digest(canonical(parent)) != R2_SEAL:
        raise ValueError("r2 input seal mismatch")
    pilot_bytes = read_bound(CF3C_PACKET / "inputs.json", CF3C_INPUTS_SHA)
    pilot = json.loads(pilot_bytes)
    weight_receipt = read_bound(CF3C_PACKET / "prior-model-receipt.json", pilot["cmp4_weight_receipt_sha256"])
    weight = json.loads(weight_receipt)
    if any(pilot[key] != weight[key] for key in (
            "model_path", "model_sha256", "model_stat", "build_sha256", "template_sha256")):
        raise ValueError("CF3C pilot and original weight receipt disagree")
    model = model_receipt(pilot, parent)
    template_sha = pilot["template_sha256"]
    template_source = Path(model["path"]).parent / "chat-templates/sha256" / f"{template_sha}.jinja"
    template = read_bound(template_source, template_sha)

    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="staging-", dir=SCRATCH) as temp:
        staged = Path(temp) / "packet"
        staged.mkdir()
        for name in ("runner.py", "launcher.sh", "spec.json", "README.md"):
            shutil.copy2(HERE / name, staged / name)
        prior_digests = parent["packet_sha256"]
        for name in ("rubric.py", "controls.py"):
            (staged / name).write_bytes(read_bound(HERE / name, prior_digests[name]))
        reused = ["semantic.py", "cmp2_runner.py", "verify_ggml_linkage.sh", "cases.json"]
        reused.extend(name for name in prior_digests if name.startswith("r1-smoke-"))
        for name in reused:
            (staged / name).write_bytes(read_bound(R2_PACKET / name, prior_digests[name]))
        for name, expected in R2_SMOKE_SHA256.items():
            archive_name = f"r2-smoke-{name.replace('/', '-')}"
            (staged / archive_name).write_bytes(read_bound(R2_SMOKE / name, expected))
        (staged / "cf3c-inputs.json").write_bytes(pilot_bytes)
        (staged / "prior-model-receipt.json").write_bytes(weight_receipt)
        (staged / "chat-template.jinja").write_bytes(template)
        (staged / "cf3c-cmp4-runner.py").write_bytes(
            read_bound(CF3C_PACKET / "cmp4_runner.py", pilot["packet_sha256"]["cmp4_runner.py"]))

        manifest = {key: parent[key] for key in (
            "bin_dir", "build_commit", "build_version", "build_sha256", "build_manifest_sha256",
        )}
        manifest.update(prior_manifest_sha256=R2_SEAL, model=model, template_sha256=template_sha,
                        packet_sha256={path.name: digest(path.read_bytes()) for path in sorted(staged.iterdir())})
        (staged / "inputs.json").write_bytes(canonical({**manifest, "sha256": digest(canonical(manifest))}) + b"\n")
        subprocess.run([sys.executable, "-B", str(staged / "runner.py"), "verify"], check=True)
        archive = SCRATCH / "native/prepared"
        archive.mkdir(parents=True, exist_ok=True)
        for source in staged.iterdir():
            target = archive / source.name
            data = source.read_bytes()
            if target.exists():
                read_bound(target, digest(data))
            else:
                with target.open("xb") as sink:
                    sink.write(data)
        staged.rename(packet)
    return packet / "spec.json"


if __name__ == "__main__":
    print(prepare())
