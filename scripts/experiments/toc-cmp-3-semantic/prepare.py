#!/usr/bin/env python3
"""Seal the judge rubric, controls, native wire evidence, and runtime custody."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import controls
from semantic import canonical, digest, read_bound, sealed_cases, strict_json

HERE = Path(__file__).resolve().parent
BASE = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly")
SCRATCH = BASE / "cmp3-semantic"
PRIOR_PACKET = BASE / "cmp3-r2/packet"
PRIOR_MANIFEST_SEAL = "3f3b9647edd28ac5152cc8a73afa1b77c7f5f5a91e92146199ece1e126276f2f"
LEDGER = BASE / "cmp3-live-r3/native/RESULT.json"
LEDGER_SHA = "6c566398cd6e36790c5f81bbd6b58e0321f3686869ddebafca27123aca4d6f08"
EXPECTED_UNITS = {
    f"{task}/contract_{arm}"
    for task in ("amber-ticket", "teal-ticket")
    for arm in ("summary_only", "verbatim_manifest")
}


def prepare():
    packet = SCRATCH / "packet"
    if packet.exists():
        raise ValueError("semantic packet already exists; preserve prior custody")
    parent = strict_json((PRIOR_PACKET / "input-manifest.json").read_bytes())
    if parent.pop("sha256") != PRIOR_MANIFEST_SEAL or digest(canonical(parent)) != PRIOR_MANIFEST_SEAL:
        raise ValueError("prior model/runtime input seal mismatch")
    cases = list(sealed_cases(LEDGER, LEDGER_SHA))
    if (len(cases) != len(EXPECTED_UNITS) or {case["unit"] for case in cases} != EXPECTED_UNITS
            or any("request_id" not in case or case["literal_delivered"] is not True for case in cases)):
        raise ValueError("missing or incomplete sealed semantic replay cases")
    schedule = controls.cases() + [{"case": case, "expected": None} for case in cases]
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="staging-", dir=SCRATCH) as temp:
        staged = Path(temp) / "packet"
        staged.mkdir()
        for name in ("semantic.py", "runner.py", "launcher.sh", "spec.json", "README.md"):
            shutil.copy2(HERE / name, staged / name)
        for name in ("cmp2_runner.py", "verify_ggml_linkage.sh"):
            (staged / name).write_bytes(read_bound(PRIOR_PACKET / name, parent["packet_sha256"][name]))
        (staged / "cases.json").write_bytes(canonical(schedule) + b"\n")
        (staged / "source-ledger.json").write_bytes(read_bound(LEDGER, LEDGER_SHA))
        manifest = {key: parent[key] for key in (
            "bin_dir", "build_commit", "build_version", "build_sha256", "build_manifest_sha256", "model",
        )}
        manifest.update(prior_manifest_sha256=PRIOR_MANIFEST_SEAL, source_ledger_sha256=LEDGER_SHA,
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
