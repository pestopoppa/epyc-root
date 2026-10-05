"""Bounded, per-module native custody for the full tests/unit selection.

This driver never grades tests. Each selected module is executed once under a
synthetic off-host capacity bootstrap and captured by the existing native CI
receipt producer. The status sidecar records only selection/capture coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


APP_BASE_SHA = "6714c72ff42cd7b4216182bbf3431444b0a91846"
BOOTSTRAP_PATH = "tests/fixtures/offhost_unit_bootstrap.py"
BOOTSTRAP_SHA256 = "9b1758788336d7d42d55171dbd463762f0a160a0efeb382db701194a3e0d7cda"
EXPECTED_MODULES = 895
SHARD_COUNT = 32
SCHEMA = "ni18.unit_module_manifest.v1"
STATUS_SCHEMA = "ni18.unit_module_capture_status.v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(app: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(app), *args], text=True).strip()


def write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)


def key_value(value: str) -> tuple[str, str]:
    name, separator, path = value.partition("=")
    if not separator or not name or not path:
        raise argparse.ArgumentTypeError("expected NAME=ABSENT_PATH")
    return name, path


def manifest_for(app: Path, synthetic_sha: str, shard_count: int,
                 root_producer_sha: str, root_workflow_sha: str) -> dict[str, Any]:
    if shard_count != SHARD_COUNT:
        raise ValueError(f"reviewed shard count is fixed at {SHARD_COUNT}")
    if git(app, "rev-parse", "HEAD") != synthetic_sha:
        raise ValueError("synthetic app checkout differs from its immutable pin")
    if git(app, "rev-parse", "HEAD^") != APP_BASE_SHA:
        raise ValueError("synthetic app parent differs from accepted app main")
    changed = git(app, "diff", "--name-only", APP_BASE_SHA, synthetic_sha).splitlines()
    if changed != [BOOTSTRAP_PATH]:
        raise ValueError(f"synthetic app delta is not the single approved bootstrap: {changed!r}")
    bootstrap = app / BOOTSTRAP_PATH
    bootstrap_sha = digest(bootstrap.read_bytes())
    if bootstrap_sha != BOOTSTRAP_SHA256:
        raise ValueError("synthetic bootstrap differs from previously reviewed bytes")
    listed = git(app, "ls-tree", "-r", "--name-only", synthetic_sha, "--", "tests/unit").splitlines()
    modules = sorted(
        path for path in listed
        if Path(path).name.startswith("test_") and Path(path).suffix == ".py"
    )
    if len(modules) != EXPECTED_MODULES:
        raise ValueError(f"expected {EXPECTED_MODULES} tracked unit modules, found {len(modules)}")
    items = []
    for index, relative in enumerate(modules):
        source = app / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"tracked test module is missing or not a regular file: {relative}")
        items.append({"ordinal": index, "path": relative,
                      "sha256": digest(source.read_bytes()), "shard": index % shard_count})
    return {
        "schema": SCHEMA,
        "app_base_sha": APP_BASE_SHA,
        "app_synthetic_sha": synthetic_sha,
        "root_producer_sha": root_producer_sha,
        "root_workflow_sha": root_workflow_sha,
        "bootstrap_path": BOOTSTRAP_PATH,
        "bootstrap_sha256": bootstrap_sha,
        "module_count": len(items),
        "shard_count": shard_count,
        "assignment": "lexicographic module path order; ordinal modulo shard_count",
        "modules": items,
        "scope": "all tracked Python test_*.py modules recursively under tests/unit; every module selected once",
        "exclusions": ["unselected test trees", "inference", "performance", "host corpus",
                       "undeclared dependency completeness"],
    }


def prepare(args: argparse.Namespace) -> None:
    app = Path(args.app).resolve()
    expected_overrides = {
        "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN",
        "ORCHESTRATOR_PATHS_LLAMA_MTMD",
        "ORCHESTRATOR_PATHS_LLAMA_SERVER",
    }
    overrides = dict(args.path_override)
    if set(overrides) != expected_overrides:
        raise ValueError("all three reviewed unavailable binary path overrides are required")
    for name, value in overrides.items():
        path = Path(value)
        if not path.is_absolute() or os.path.lexists(path):
            raise ValueError(f"{name} must be an absolute path that remains absent: {value}")
    if not 0 <= args.shard < args.shard_count:
        raise ValueError("shard id is outside the declared shard count")
    manifest = manifest_for(app, args.app_synthetic_sha, args.shard_count,
                            args.root_producer_sha, args.root_workflow_sha)
    manifest_path = Path(args.manifest)
    write_exclusive(manifest_path, canonical(manifest) + b"\n")
    context = {
        "schema": "ni18.unit_module_context.v1",
        "app_base_sha": APP_BASE_SHA,
        "app_synthetic_sha": args.app_synthetic_sha,
        "root_producer_sha": args.root_producer_sha,
        "root_workflow_sha": args.root_workflow_sha,
        "module_count": manifest["module_count"],
        "shard_count": manifest["shard_count"],
        "shard_id": args.shard,
        "shard_selection_count": sum(item["shard"] == args.shard for item in manifest["modules"]),
        "assignment": manifest["assignment"],
        "synthetic_host_ram_gib": 1024.0,
        "synthetic_ram_scope": "existing test-process-only bootstrap; production validator unchanged",
        "path_overrides": {
            name: {"value": value, "must_remain_absent": True}
            for name, value in sorted(overrides.items())
        },
        "actual_runner_capacity_guard": "separate ordinary-runner capture; not covered by synthetic result",
        "inference": "none",
        "claim_scope": "named per-module pytest cases and statuses only; no suite-wide inference",
    }
    context_path = Path(args.context)
    write_exclusive(context_path, canonical(context) + b"\n")
    comparison = {
        "schema": "ni18.unit_module_source_comparison.v1",
        "app_base_sha": APP_BASE_SHA,
        "app_synthetic_sha": args.app_synthetic_sha,
        "synthetic_parent_sha": APP_BASE_SHA,
        "synthetic_only_changed_path": BOOTSTRAP_PATH,
        "bootstrap_sha256": BOOTSTRAP_SHA256,
        "module_count": manifest["module_count"],
        "module_manifest_sha256": digest(canonical(manifest) + b"\n"),
        "ordinary_runner_capacity_phase_separate": True,
        "production_validator_changed": False,
    }
    write_exclusive(Path(args.comparison), canonical(comparison) + b"\n")


def import_reader(producer_checkout: Path):
    sys.path.insert(0, str(producer_checkout.resolve()))
    from scripts.ci.native_conformance import read_receipt  # type: ignore[import-not-found]
    return read_receipt


def run_shard(args: argparse.Namespace) -> int:
    app = Path(args.app).resolve()
    control = Path(args.control).resolve()
    producer = Path(args.producer_checkout).resolve()
    manifest_path = Path(args.manifest).resolve()
    context_path = Path(args.context).resolve()
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get("schema") != SCHEMA or manifest.get("app_synthetic_sha") != args.app_synthetic_sha:
        raise ValueError("module manifest does not match immutable run pins")
    if not 0 <= args.shard < SHARD_COUNT or manifest.get("shard_count") != SHARD_COUNT:
        raise ValueError("invalid shard identity")
    if git(app, "rev-parse", "HEAD") != args.app_synthetic_sha:
        raise ValueError("app checkout moved after manifest preparation")
    expected = [item for item in manifest["modules"] if item["shard"] == args.shard]
    if not expected:
        raise ValueError("shard has no selected modules")
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if (output_root / "shard-status.json").exists() or (output_root / "driver.log").exists():
        raise ValueError("refusing to overwrite an existing shard capture")
    status_path = output_root / "shard-status.json"
    driver_path = output_root / "driver.log"
    read_receipt = import_reader(producer)
    statuses: list[dict[str, Any]] = []
    any_failure = False
    native_script = producer / "scripts/ci/native_conformance.py"
    timeout = ["timeout", "--verbose", "--signal=TERM", "--kill-after=15s"]
    pyenv = os.environ.get("UV_PROJECT_ENVIRONMENT")
    if not pyenv:
        raise ValueError("locked uv environment path was not declared")
    python = str(Path(pyenv) / "bin/python")

    def persist_status() -> None:
        status = {
            "schema": STATUS_SCHEMA,
            "shard_id": args.shard,
            "shard_count": SHARD_COUNT,
            "manifest_sha256": digest(manifest_path.read_bytes()),
            "expected_modules": [item["path"] for item in expected],
            "completed_count": len(statuses),
            "receipt_reader_accepted_count": sum(
                item["receipt_reader_accepted"] for item in statuses
            ),
            "module_captures": statuses,
            "decision": "capture coverage only; module pass/failure/timeout remains in each original native receipt",
        }
        temporary = status_path.with_suffix(".json.tmp")
        with temporary.open("xb") as output:
            output.write(canonical(status) + b"\n")
        os.replace(temporary, status_path)

    persist_status()
    with driver_path.open("x", encoding="utf-8") as driver:
        for item in expected:
            relative = item["path"]
            if digest((app / relative).read_bytes()) != item["sha256"]:
                raise ValueError(f"test module changed after manifest: {relative}")
            index = int(item["ordinal"])
            stem = f"module-{index:04d}"
            local_root = Path(args.local_output_root) / f"shard-{args.shard}"
            junit_rel = local_root / "junit" / f"{stem}.xml"
            log_rel = local_root / "pytest-logs" / f"{stem}.log"
            (app / junit_rel).parent.mkdir(parents=True, exist_ok=True)
            (app / log_rel).parent.mkdir(parents=True, exist_ok=True)
            native_dir = output_root / "native" / stem
            native_dir.parent.mkdir(parents=True, exist_ok=True)
            if native_dir.exists() or (app / junit_rel).exists() or (app / log_rel).exists():
                raise ValueError(f"refusing to overwrite existing capture for {relative}")
            command = [
                python, str(native_script),
                "--cwd", str(app),
                "--junit", str(junit_rel),
                "--output", str(native_dir),
                "--repo", f"root_workflow={control}",
                "--repo", f"root_producer={producer}",
                "--repo", f"orchestrator_synthetic={app}",
                "--read-path", str(control / ".github/workflows/ni18-unit-sweep.yml"),
                "--read-path", str(control / "scripts/ci/ni18_unit_sweep.py"),
                "--read-path", str(Path(args.comparison).resolve()),
                "--read-path", str(manifest_path),
                "--read-path", str(context_path),
                "--read-path", str(native_script),
                "--read-path", str(producer / "scripts/vidya/adapters/ci_conformance.py"),
                "--read-path", str(producer / "scripts/vidya/claim_tuple.py"),
                "--read-path", str(app / "src/config/models.py"),
                "--read-path", str(app / "scripts/server/stack_paths.py"),
                "--read-path", str(app / "src/registry/kernel_paths.py"),
                "--read-path", str(app / "scripts/server/stack_manifest.py"),
                "--read-path", str(app / "orchestration/stack_topology.yaml"),
                "--read-path", str(app / "orchestration/model_registry.yaml"),
                "--read-path", str(app / BOOTSTRAP_PATH),
                "--read-path", str(app / "tests/conftest.py"),
                "--read-path", str(app / "tests/unit/conftest.py"),
                "--read-path", str(app / "pyproject.toml"),
                "--read-path", str(app / "uv.lock"),
                "--read-path", str(app / relative),
                "--generated-output", str(log_rel),
                "--select", relative,
                "--", *timeout, "120s", python,
                str(app / BOOTSTRAP_PATH), "-q", "--tb=short",
                "--rootdir", str(app), "--junit-prefix=ni18-unit-sweep", relative,
                f"--junitxml={junit_rel}", f"--log-file={log_rel}",
            ]
            driver.write(f"\n=== module {index + 1}/{len(manifest['modules'])}: {relative} ===\n")
            driver.flush()
            try:
                completed = subprocess.run(
                    [*timeout, "165s", *command], cwd=app,
                    stdout=driver, stderr=subprocess.STDOUT, check=False,
                )
                outer_exit = completed.returncode
            except OSError as exc:
                outer_exit = 127
                driver.write(f"capture launch error: {exc}\n")
            receipt_path = native_dir / "receipt.json"
            receipt_digest = ""
            reader_ok = False
            diagnostic = ""
            if receipt_path.is_file():
                try:
                    record, receipt_digest = read_receipt(receipt_path)
                    if record.get("selections") != [relative]:
                        raise ValueError("receipt selection differs from manifest module")
                    if record.get("repositories", {}).get("orchestrator_synthetic") != args.app_synthetic_sha:
                        raise ValueError("receipt app repository identity differs from pin")
                    reader_ok = True
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    diagnostic = str(exc)
            else:
                diagnostic = "native receipt absent (bounded capture did not complete)"
            row = {"ordinal": index, "module": relative, "module_sha256": item["sha256"],
                   "outer_exit_code": outer_exit, "receipt_path": str(receipt_path.relative_to(output_root)),
                   "receipt_sha256": receipt_digest, "receipt_reader_accepted": reader_ok,
                   "diagnostic": diagnostic}
            statuses.append(row)
            if outer_exit != 0 or not reader_ok:
                any_failure = True
            persist_status()
    print(json.dumps({"shard": args.shard, "expected": len(expected),
                      "completed": len(statuses),
                      "reader_accepted": sum(item["receipt_reader_accepted"] for item in statuses),
                      "any_capture_or_test_command_nonzero": any_failure}, sort_keys=True))
    return 1 if any_failure or len(statuses) != len(expected) else 0


def audit(args: argparse.Namespace) -> int:
    artifacts = Path(args.artifacts_dir).resolve()
    read_receipt = import_reader(Path(args.producer_checkout))
    status_files = sorted(artifacts.rglob("shard-status.json"))
    if len(status_files) != SHARD_COUNT:
        raise ValueError(f"expected {SHARD_COUNT} shard status files, found {len(status_files)}")
    seen_shards: set[int] = set()
    seen_modules: dict[str, int] = {}
    expected_manifest = None
    accepted_receipts = 0
    for status_path in status_files:
        status = json.loads(status_path.read_bytes())
        if status.get("schema") != STATUS_SCHEMA or status.get("shard_count") != SHARD_COUNT:
            raise ValueError(f"unexpected shard status: {status_path}")
        shard = status.get("shard_id")
        if type(shard) is not int or not 0 <= shard < SHARD_COUNT or shard in seen_shards:
            raise ValueError(f"duplicate or invalid shard id: {shard!r}")
        seen_shards.add(shard)
        manifest_path = status_path.parent / "module-manifest.json"
        if not manifest_path.is_file() or digest(manifest_path.read_bytes()) != status.get("manifest_sha256"):
            raise ValueError(f"missing or changed module manifest for shard {shard}")
        manifest = json.loads(manifest_path.read_bytes())
        if (manifest.get("schema") != SCHEMA or manifest.get("module_count") != EXPECTED_MODULES
                or len(manifest.get("modules", [])) != EXPECTED_MODULES):
            raise ValueError(f"unexpected complete module manifest: {manifest_path}")
        if expected_manifest is None:
            expected_manifest = manifest
        elif canonical(manifest) != canonical(expected_manifest):
            raise ValueError("shard manifests disagree")
        expected_for_shard = [item["path"] for item in manifest["modules"] if item["shard"] == shard]
        if status.get("expected_modules") != expected_for_shard:
            raise ValueError(f"shard {shard} selection differs from deterministic manifest")
        if status.get("completed_count") != len(status.get("module_captures", [])):
            raise ValueError(f"shard {shard} status count mismatch")
        for row in status["module_captures"]:
            module = row.get("module")
            if module not in expected_for_shard or module in seen_modules:
                raise ValueError(f"duplicate or foreign module selection: {module!r}")
            seen_modules[module] = shard
            receipt_path = status_path.parent / row["receipt_path"]
            if not receipt_path.is_file() or row.get("receipt_reader_accepted") is not True:
                raise ValueError(f"module capture incomplete: {module}")
            record, receipt_sha = read_receipt(receipt_path)
            if (receipt_sha != row.get("receipt_sha256") or record.get("selections") != [module]
                    or record.get("repositories", {}).get("orchestrator_synthetic")
                    != manifest.get("app_synthetic_sha")
                    or record.get("repositories", {}).get("root_producer")
                    != manifest.get("root_producer_sha")
                    or record.get("repositories", {}).get("root_workflow")
                    != manifest.get("root_workflow_sha")):
                raise ValueError(f"native receipt identity mismatch for {module}")
            accepted_receipts += 1
    if expected_manifest is None or len(seen_shards) != SHARD_COUNT:
        raise ValueError("missing one or more shard manifests")
    all_modules = [item["path"] for item in expected_manifest["modules"]]
    if len(all_modules) != EXPECTED_MODULES or set(seen_modules) != set(all_modules):
        raise ValueError("shard receipts do not account for every manifest module exactly once")
    print(json.dumps({"shards": len(seen_shards), "manifest_modules": len(all_modules),
                      "unique_module_capture_receipts": accepted_receipts,
                      "scope": "coverage/integrity only; native per-module results remain authoritative"},
                     sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--app", required=True)
    p.add_argument("--app-synthetic-sha", required=True)
    p.add_argument("--root-producer-sha", required=True)
    p.add_argument("--root-workflow-sha", required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shard-count", type=int, default=SHARD_COUNT)
    p.add_argument("--manifest", required=True)
    p.add_argument("--context", required=True)
    p.add_argument("--comparison", required=True)
    p.add_argument("--path-override", action="append", type=key_value, default=[], metavar="NAME=ABSENT_PATH")
    p.set_defaults(func=prepare)
    r = sub.add_parser("run-shard")
    r.add_argument("--app", required=True)
    r.add_argument("--control", required=True)
    r.add_argument("--producer-checkout", required=True)
    r.add_argument("--app-synthetic-sha", required=True)
    r.add_argument("--shard", type=int, required=True)
    r.add_argument("--manifest", required=True)
    r.add_argument("--context", required=True)
    r.add_argument("--comparison", required=True)
    r.add_argument("--output-root", required=True)
    r.add_argument("--local-output-root", required=True)
    r.set_defaults(func=run_shard)
    v = sub.add_parser("audit")
    v.add_argument("--artifacts-dir", required=True)
    v.add_argument("--producer-checkout", required=True)
    v.set_defaults(func=audit)
    args = parser.parse_args()
    try:
        result = args.func(args)
        return result if type(result) is int else 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ni18 unit sweep refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
