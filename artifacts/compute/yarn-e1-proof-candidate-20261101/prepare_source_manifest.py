#!/usr/bin/env python3
"""Build the proposal's exact source dependency list; it does not publish a READY row."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUTS = Path("/mnt/raid0/llm/tmp/yarn-e1-20261004/inputs")
ROOT = Path("/mnt/raid0/llm")
ENGINE = Path("/mnt/raid0/llm/tmp/codex-ni-hard-qual-gate-20261101/src/scripts/coordination")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    paths = [
        HERE / "launch.sh", HERE / "run.py", HERE / "yarn_needle.py", HERE / "yarn_proof.py", HERE / "analyze_phase.py",
        HERE / "prepare_500k_request_metadata.py", HERE / "prepare_qualification_bundle.py",
        HERE / "prepare_source_manifest.py", HERE / "test_qualification_contract.py",
        HERE / "helper/check_complete.py", HERE / "helper/validate_launch_window.py", HERE / "helper/kfd_sampler.py",
        HERE / "helper/libhipmalloc_trace.so", HERE / "qualification/REQUEST-METADATA.json",
        HERE / "qualification/request_manifest.json", HERE / "qualification/production_recipe.json",
        HERE / "qualification/qual_fixture.json",
        HERE / "qualification/WORK-UNIT-CALIBRATION-REQUIRED.json",
        Path("/mnt/raid0/llm/tmp/codex-ni-hard-qual-gate-20261101/src/scripts/coordination/filler_run14.sh"),
        ENGINE / "dryrun_check.py", ENGINE / "dryrun_disk_policy.json",
        ENGINE / "filler_lib.sh", ENGINE / "qualify_launcher.py", ENGINE / "keeper_qual_gate.py",
        ENGINE / "ready_manifest.schema.json",
        Path("/mnt/raid0/llm/kernels/builds/gpu-20261004-9a3f1392a/bin/llama-server"),
        Path("/mnt/raid0/llm/kernels/builds/gpu-20261004-b0ba1d427/bin/llama-server"),
        Path("/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja"),
        Path("/mnt/raid0/llm/kernels/builds/gpu-20261004-9a3f1392a/bin/llama-tokenize"),
    ]
    recipe = json.loads((HERE / "qualification/production_recipe.json").read_text())
    for image in recipe["images"].values():
        paths.extend(Path(item["path"]) for item in image["ggml_dsos"])
    inputs_manifest = json.loads((INPUTS / "manifest.json").read_text())
    paths.append(INPUTS / "manifest.json")
    paths.extend(INPUTS / name for name in inputs_manifest["files"])
    paths.extend(HERE / "qualification" / f"a1-500k-n{n}.rendered.txt" for n in range(15, 20))
    unique = sorted({path.resolve() for path in paths})
    bad = [str(path) for path in unique if not path.is_file() or not str(path).startswith("/mnt/raid0/llm/")]
    if bad:
        raise SystemExit("source dependency missing or outside keeper hash scope: " + ", ".join(bad))
    manifest = HERE / "SOURCE.sha256"
    manifest.write_text("".join(f"{sha(path)}  {path}\n" for path in unique))
    print(json.dumps({"path": str(manifest), "sha256": sha(manifest), "entries": len(unique),
                      "candidate_engine_path": str(ENGINE / "filler_run14.sh"),
                      "canonical_deployment_binding": "NOT PRESENT; candidate-only"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
