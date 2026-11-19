"""Stage the private DCP-10 native packet without constructing indexes or searching."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import colgrep_compare as comparator
import colgrep_native as native
import pilot
from colgrep_row import (
    MAX_SECONDS,
    PACKET_SOURCES,
    ROW,
    SCHEMA,
    base_tree,
    digest,
    launch_policy,
    model_stat,
    original_inputs,
    require,
    save,
)

DEFAULT_ROOT = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly")
ORIGINAL_BINARY = Path("/mnt/raid0/llm/UTILS/bin/colgrep-1.2.0")
MODEL_SNAPSHOT = Path("/mnt/raid0/llm/hf-home/hub/models--lightonai--LateOn-Code-edge/snapshots") / comparator.MODEL_REVISION
RUNTIME_SHA = "b0ef55d282792a762a346db77ce79519f72b238092a3d8b8944b831d42eda564"
ORIGINAL_ROW = "dcp10-colgrep-native-20261118"
ORIGINAL_ROOT = DEFAULT_ROOT / "dcp10-colgrep-native"
ORIGINAL_PREPARATION_SHA = "66b9f45fc59be61c1f58a3082977718240e0f0f173aac943c2c7f5752ad20950"
ORIGINAL_RESULT_SHA = "f4ba555150a489036d8b79de3f26dc8b92f9074ec60efdddd82204ec1d8fc0e6"

def copy_asset(source, target, mode):
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(mode)


def smoke_predicate(packet, receipt_sha):
    return f"/usr/bin/python3 -I -B {packet}/colgrep_row.py --receipt-sha {receipt_sha} smoke"


def source_manifest(source_hashes):
    return "".join(f"{source_hashes[name]}  {name}\n" for name in PACKET_SOURCES).encode()


def source_controls(root, source, receipt):
    receipt_bytes = pilot.encode(receipt).encode()
    receipt_sha = digest(receipt_bytes)
    manifest = source_manifest(receipt["source_hashes"])
    launcher = (source / "colgrep_row_launcher.sh").read_text()
    launcher = (launcher.replace("__SCRATCH_ROOT__", str(root)).replace("__RECEIPT_SHA__", receipt_sha)
                .replace("__SOURCE_SHA__", digest(manifest)).replace("__ROW_ID__", receipt["row"])).encode()
    return receipt_sha, {"preparation.json": receipt_bytes, "SOURCE.sha256": manifest, "launcher.sh": launcher}


def write_sources(destination, files):
    for name, content in files.items():
        path = destination / name
        path.write_bytes(content)
        path.chmod(0o500 if name == "launcher.sh" else 0o400)


def original_run(prior_root, work):
    receipt = json.loads(comparator.read_sealed(prior_root / "packet/preparation.json", ORIGINAL_PREPARATION_SHA))
    result_path = prior_root / "native/RESULT.json"
    result = json.loads(comparator.read_sealed(result_path, ORIGINAL_RESULT_SHA))
    require((receipt["row"], receipt["scratch"], receipt["work"]) == (ORIGINAL_ROW, str(prior_root), str(work))
            and result["row"] == ORIGINAL_ROW and result["completed"] == 3 and result["reconciled"]
            and not result["comparison_valid"] and not result["unknown"]
            and len(result["observed"]) == 3
            and all(item["status"] == "error" for item in result["observed"]),
            "unexpected predecessor run")
    for name, sealed in result["outputs_sha256"].items():
        comparator.read_sealed(result_path.parent / name, sealed)
    lineage = {"revision": 2, "reason": "qualification after native thread limit fix",
               "prior_row": ORIGINAL_ROW, "prior_preparation_sha256": ORIGINAL_PREPARATION_SHA,
               "prior_result_path": str(result_path), "prior_result_sha256": ORIGINAL_RESULT_SHA}
    return receipt, lineage


def prepare(root, work, runtime, *, prior_root=None):
    source = Path(__file__).resolve().parent
    require(root == root.resolve() and root.parent.is_dir(), "expected a canonical new scratch root")
    require(re.fullmatch(r"/[A-Za-z0-9/_.-]+", str(root)), "unsupported scratch path for launcher")
    require(runtime.name == native.RUNTIME_NAME and runtime.is_file(), "expected the ColGREP runtime library")
    request, admitted = original_inputs(work)
    prior, lineage = original_run(prior_root, work) if prior_root else (None, None)
    model_source = prior_root / "assets/model" if prior_root else MODEL_SNAPSHOT
    if prior:
        require(model_stat(model_source) == prior["model"]["file_stat"], "original staged model drift")
    root.mkdir(mode=0o700)
    packet, assets = root / "packet", root / "assets"
    packet.mkdir(mode=0o700)
    assets.mkdir(mode=0o700)
    for name in PACKET_SOURCES:
        copy_asset(source / name, packet / name, 0o400)
    binary = assets / "bin/colgrep"
    copy_asset(ORIGINAL_BINARY, binary, 0o500)
    comparator.verify_hash(binary, comparator.BINARY_SHA)
    library = assets / "runtime" / native.RUNTIME_NAME
    copy_asset(runtime, library, 0o400)
    comparator.verify_hash(library, RUNTIME_SHA)
    model = assets / "model"
    model.mkdir(mode=0o700)
    for item in sorted(model_source.iterdir()):
        copy_asset(item, model / item.name, 0o400)
    model.chmod(0o500)
    if prior:
        require(model_stat(model_source) == prior["model"]["file_stat"], "original staged model changed during copy")
    model_sha = prior["model"]["directory_sha256"] if prior else comparator.directory_digest(model)
    model_identity = {
        "id": comparator.MODEL_ID,
        "revision": comparator.MODEL_REVISION,
        "directory_sha256": model_sha,
        "file_stat": model_stat(model),
    }
    bindings = {}
    for task in admitted.tasks:
        base = work / "bases" / task["language"]
        bindings[task["task_id"]] = {
            "base_commit": task["base_commit"], "base_tree": base_tree(base, task), "root": str(base),
            "query_sha256": digest(task["query"].encode()), "app_revision": pilot.APP_REV,
            "binary_sha256": comparator.BINARY_SHA, "model_revision": comparator.MODEL_REVISION,
            "model_directory_sha256": model_identity["directory_sha256"],
        }
    receipt = {
        "schema": SCHEMA, "row": ROW, "work": str(work), "scratch": str(root),
        "request_sha256": comparator.ORIGINAL_REQUEST_SHA,
        "baseline_sha256": comparator.LEXICAL_PREDICTIONS_SHA,
        "app_revision": pilot.APP_REV, "app_sources": request["source_hashes"],
        "packet_hashes": request["packet_hashes"],
        "binary_sha256": comparator.BINARY_SHA, "runtime_sha256": RUNTIME_SHA,
        "model": model_identity, "tasks": bindings,
        "source_hashes": {name: comparator.hash_file(packet / name) for name in PACKET_SOURCES},
        "launch": launch_policy(),
    }
    if prior:
        require(all(receipt[field] == prior[field] for field in (
            "request_sha256", "baseline_sha256", "app_revision", "app_sources", "packet_hashes",
            "binary_sha256", "runtime_sha256", "tasks",
        )) and prior["model"]["id"] == comparator.MODEL_ID
            and prior["model"]["revision"] == comparator.MODEL_REVISION,
            "predecessor input identity differs from requalification")
        receipt["lineage"] = lineage
    receipt_sha, controls = source_controls(root, source, receipt)
    write_sources(packet, controls)
    launcher = packet / "launcher.sh"
    spec = {
        "id": ROW, "owner": "h-delegation-context-preassembly", "kind": "compute", "lane": "cpu",
        "regions": "0-3", "priority_rank": 57, "admission_class": "diagnostic",
        "launcher": str(launcher), "scratch_root": str(root),
        "result_path": str(root / "native/RESULT.json"), "result_format": "json",
        "ram_gib": 10, "budget_gib": 3, "estimate_s": MAX_SECONDS, "min_window_s": 1500,
        "max_window_s": 2400, "resumable": False, "first_progress_s": 150, "unit_key": "unit",
        "smoke_predicate": smoke_predicate(packet, receipt_sha),
        "decision_rule": "completed == 3 and comparison_valid == 1",
        "handoff_task": "context-and-token-economy.md:DCP-10-COLGREP-THREADS",
        "keep": ["native/*", "packet/preparation.json"],
        "notes": "Revision 2 qualifies the CPU thread fix on the fixed cohort. Hard 1800s cap. Publisher smoke uses a fresh fixture.",
    }
    save(root / "spec.json", spec)
    return receipt_sha


def refresh_sources(root):
    """Reseal staged source and leave the originally prepared asset proofs intact."""
    source = Path(__file__).resolve().parent
    packet = root / "packet"
    for path in (root, packet):
        require(path.resolve(strict=True) == path and path.is_dir() and path.stat().st_uid == os.geteuid()
                and path.stat().st_mode & 0o077 == 0, f"expected an owned private directory: {path}")
    require(re.fullmatch(r"/[A-Za-z0-9/_.-]+", str(root)), "unsupported scratch path for launcher")
    prior_receipt = comparator.regular_path(packet / "preparation.json").read_bytes()
    prior_sha = digest(prior_receipt)
    receipt = json.loads(prior_receipt)
    require((receipt["schema"], receipt["row"], receipt["scratch"]) == (SCHEMA, ROW, str(root)),
            "unexpected preparation receipt")
    require(set(receipt["source_hashes"]) == set(PACKET_SOURCES), "unexpected prepared source paths")
    prior_manifest = comparator.regular_path(packet / "SOURCE.sha256").read_bytes()
    require(prior_manifest == source_manifest(receipt["source_hashes"]), "prior source manifest drift")
    prior_launcher = comparator.regular_path(packet / "launcher.sh").read_bytes()
    require(prior_sha.encode() in prior_launcher and digest(prior_manifest).encode() in prior_launcher,
            "prior launcher does not bind the preparation receipt and source manifest")
    prior_sources = {name: comparator.read_sealed(packet / name, expected)
                     for name, expected in receipt["source_hashes"].items()}
    spec_path = comparator.regular_path(root / "spec.json")
    prior_spec = spec_path.read_bytes()
    spec = json.loads(prior_spec)
    require((spec["id"], spec["scratch_root"], spec["launcher"], spec["smoke_predicate"])
            == (ROW, str(root), str(packet / "launcher.sh"), smoke_predicate(packet, prior_sha)),
            "prior spec does not bind the staged row and receipt")

    files = {name: comparator.regular_path(source / name).read_bytes() for name in PACKET_SOURCES}
    receipt["source_hashes"] = {name: digest(content) for name, content in files.items()}
    receipt_sha, controls = source_controls(root, source, receipt)
    if receipt_sha == prior_sha and controls["launcher.sh"] == prior_launcher:
        return receipt_sha
    spec["smoke_predicate"] = smoke_predicate(packet, receipt_sha)
    history = packet / "source-history"
    history.mkdir(mode=0o700, exist_ok=True)
    require(history.resolve(strict=True) == history and history.is_dir(), "unexpected source history path")
    previous = history / digest(prior_launcher)
    previous.mkdir(mode=0o700, exist_ok=True)
    require(previous.resolve(strict=True) == previous and previous.is_dir(), "unexpected prior source record")
    for name, content in {**prior_sources, "preparation.json": prior_receipt, "launcher.sh": prior_launcher,
                          "SOURCE.sha256": prior_manifest, "spec.json": prior_spec}.items():
        old_path = previous / name
        if old_path.exists():
            comparator.read_sealed(old_path, digest(content))
        else:
            with old_path.open("xb") as output:
                output.write(content)
            old_path.chmod(0o400)

    # Stage complete replacements first. The old launcher fails closed on intermediate source drift.
    with tempfile.TemporaryDirectory(dir=packet) as directory:
        pending = Path(directory)
        write_sources(pending, {**files, **controls, "spec.json": pilot.encode(spec).encode()})
        for name in (*PACKET_SOURCES, "preparation.json", "SOURCE.sha256"):
            os.replace(pending / name, packet / name)
        os.replace(pending / "spec.json", spec_path)
        os.replace(pending / "launcher.sh", packet / "launcher.sh")
    return receipt_sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT / "dcp10-colgrep-native-r2")
    parser.add_argument("--work", type=Path, default=DEFAULT_ROOT / "dcp10")
    parser.add_argument("--runtime", type=Path,
                        default=DEFAULT_ROOT / "native-colgrep-ort-source" / native.RUNTIME_NAME)
    parser.add_argument("--requalify-from", type=Path, default=ORIGINAL_ROOT,
                        help="reuse the sealed asset proof and retain lineage from the failed original run")
    parser.add_argument("--refresh-sources", action="store_true",
                        help="refresh sources and seals in an existing staged packet only")
    args = parser.parse_args()
    root = args.root.absolute()
    print(refresh_sources(root) if args.refresh_sources else prepare(
        root, args.work.absolute(), args.runtime.absolute(), prior_root=args.requalify_from.absolute()))


if __name__ == "__main__":
    main()
