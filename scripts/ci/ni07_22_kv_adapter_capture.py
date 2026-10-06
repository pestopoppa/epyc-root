"""Capture pinned, synthetic Vidya adapter fixtures with native CI custody."""

from __future__ import annotations

import hashlib
import importlib.util
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys

CARRIER_PIN = "02f12d02ef40b28a141fb7ceaedba3897000a328"
CARRIER_READER_SHA256 = "2b8c63121e1472d10849224911ee8f4035b7f758ce1aefca7c766e2de263aa0e"
RESEARCH_PIN = "bed81e59f5a4d9f9cdb246b4b1eebe1d3e400762"
RESEARCH_SOURCES = {
    "scripts/benchmark/kv_quant_27b_v10_sweep.py": "b268e3067fb576f05915310b0df1b29ca0507442c87d6e3fb0a2be209c390cb5",
    "scripts/benchmark/laguna_pgpu1_dflash_runner.py": "5ee8265d2416799c5e41724cf02cb45dc0404a8b26730da3e8f0b7b7e402f6e5",
    "scripts/kernel_rnd/exl3/evidence.py": "8caeb33dbb12986fadc385afe25d22bd791b036253c736f9527e67a55f85e268",
    "scripts/validate/check_evidence_durability.py": "c46aa7f76064782f03b0db388bef220f301f6ff6d7d397c2e2274eac84eadc10",
}
SELECTION = [
    "tests/vidya/test_kv_quant_27b_v10_adapter.py",
    "tests/vidya/test_exl3_adapter.py",
    "tests/vidya/test_evidence_durability_adapter.py",
]
EXPECTED_CASES = 29
GENERIC_RESEARCH_CHECKOUT = ".ci-research-producers"
ROOT_INTAKE_INDEX_PATH = "research/intake_index.yaml"
ROOT_INTAKE_INDEX_BLOB = "cb1e77f0eff60101a280b509b757b88fb370ab93"
CONFIG_NAMES = {"pytest.ini", "setup.cfg", "tox.ini", "pyproject.toml", "uv.lock"}
CONFIG_SUFFIXES = {".ini", ".cfg", ".toml", ".yaml", ".yml"}
INSTALL_COMMAND = (
    "python -m pip install pytest==9.0.3 iniconfig==2.3.0 packaging==26.0 "
    "pluggy==1.6.0 Pygments==2.20.0 PyYAML==6.0.3"
)
PACKAGE_PINS = {
    "pytest": "9.0.3",
    "iniconfig": "2.3.0",
    "packaging": "26.0",
    "pluggy": "1.6.0",
    "Pygments": "2.20.0",
    "PyYAML": "6.0.3",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(f"source is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(fd)


def assert_clean_tracked(repo: Path, label: str, expected_pin: str) -> str:
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError(f"{label} checkout has tracked changes")
    pin = git(repo, "rev-parse", "HEAD")
    if pin != expected_pin:
        raise ValueError(f"{label} checkout differs from its exact pin")
    return pin


def is_source_path(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        path.suffix == ".py"
        or path.suffix in CONFIG_SUFFIXES
        or path.name in CONFIG_NAMES
    )


def tracked_source_entries(repo: Path, pin: str):
    raw = subprocess.check_output(
        ["git", "-C", str(repo), "ls-tree", "-r", "-z", pin]
    )
    regular: dict[str, tuple[str, str]] = {}
    symlinks: dict[str, tuple[str, str]] = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, path_bytes = entry.split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split(" ")
        name = path_bytes.decode("utf-8")
        if not is_source_path(name):
            continue
        if mode in {"100644", "100755"} and object_type == "blob":
            regular[name] = (mode, oid)
        elif mode == "120000" and object_type == "blob":
            symlinks[name] = (mode, oid)
        else:
            raise ValueError(f"unsupported tracked source entry: {name}")
    return regular, symlinks


def verify_root_sources(repo: Path, pin: str):
    regular, symlinks = tracked_source_entries(repo, pin)
    paths: list[Path] = []
    for name, (mode, oid) in sorted(regular.items()):
        path = repo / name
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"tracked source is not a regular file: {name}")
        expected = subprocess.check_output(
            ["git", "-C", str(repo), "cat-file", "blob", oid]
        )
        actual = read_regular(path)
        if sha256(actual) != sha256(expected):
            raise ValueError(f"tracked source differs from its Git blob: {name}")
        if git(repo, "rev-parse", f"{pin}:{name}") != oid:
            raise ValueError(f"tracked source blob identity changed: {name}")
        paths.append(path.resolve())

    symlink_facts = []
    for name, (mode, oid) in sorted(symlinks.items()):
        path = repo / name
        target = subprocess.check_output(
            ["git", "-C", str(repo), "cat-file", "blob", oid]
        )
        if not path.is_symlink() or os.readlink(os.fsencode(path)) != target:
            raise ValueError(f"tracked symlink metadata differs from its Git blob: {name}")
        symlink_facts.append(
            {"path": name, "mode": mode, "git_blob": oid, "target_sha256": sha256(target)}
        )
    return paths, symlink_facts


def verify_generic_research_checkout_isolated(repo: Path, pin: str) -> None:
    raw = subprocess.check_output(
        ["git", "-C", str(repo), "ls-tree", "-r", "-z", pin]
    )
    tracked: set[str] = set()
    intake_index_oid = None
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, path_bytes = entry.split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split(" ")
        name = path_bytes.decode("utf-8")
        tracked.add(name)
        if name == ROOT_INTAKE_INDEX_PATH:
            if mode not in {"100644", "100755"} or object_type != "blob":
                raise ValueError("ROOT intake index is not a tracked regular blob")
            intake_index_oid = oid

    if intake_index_oid != ROOT_INTAKE_INDEX_BLOB:
        raise ValueError("candidate ROOT intake index differs from reviewed tracked source")
    destination = PurePosixPath(GENERIC_RESEARCH_CHECKOUT)
    for name in tracked:
        tracked_path = PurePosixPath(name)
        if (
            tracked_path == destination
            or tracked_path.is_relative_to(destination)
            or destination.is_relative_to(tracked_path)
        ):
            raise ValueError("generic research checkout destination shadows tracked ROOT content")

    workflow = read_regular(repo / ".github/workflows/tests.yml").decode("utf-8")
    required = {
        "path: .ci-research-producers",
        "KV_QUANT_TEST_RESEARCH_ROOT: ${{ github.workspace }}/.ci-research-producers",
        "EXL3_TEST_PRODUCER: ${{ github.workspace }}/.ci-research-producers/scripts/kernel_rnd/exl3/evidence.py",
        "EVIDENCE_DURABILITY_PRODUCER: ${{ github.workspace }}/.ci-research-producers/scripts/validate/check_evidence_durability.py",
    }
    if not required.issubset({line.strip() for line in workflow.splitlines()}):
        raise ValueError("generic test workflow does not use the isolated pinned producer checkout")


def verify_research_sources(repo: Path, pin: str) -> list[Path]:
    paths = []
    for name, expected_sha in sorted(RESEARCH_SOURCES.items()):
        oid = git(repo, "rev-parse", f"{pin}:{name}")
        mode = git(repo, "ls-tree", pin, "--", name).split()[0]
        if mode not in {"100644", "100755"}:
            raise ValueError(f"pinned research source is not a regular blob: {name}")
        path = repo / name
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f"pinned research source is not a regular file: {name}")
        actual = read_regular(path)
        if sha256(actual) != expected_sha:
            raise ValueError(f"pinned research source hash differs: {name}")
        pinned = subprocess.check_output(
            ["git", "-C", str(repo), "cat-file", "blob", oid]
        )
        if actual != pinned:
            raise ValueError(f"pinned research source differs from its Git blob: {name}")
        paths.append(path.resolve())
    return paths


def load_native_carrier(path: Path):
    if sha256(read_regular(path)) != CARRIER_READER_SHA256:
        raise ValueError("native carrier reader differs from its pinned source hash")
    spec = importlib.util.spec_from_file_location("ni07_native_conformance", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load the pinned native carrier reader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    root, carrier, research = workspace / "root", workspace / "carrier", workspace / "research"
    output_root = temp / "ni07-22-kv-adapter" / "result"
    status_path = output_root / "status.json"
    status: dict[str, object] = {
        "schema": "ni07-22-kv-adapter-ci-status.v1",
        "state": "preparing",
        "exit_code": None,
    }
    try:
        if not output_root.is_dir() or {path.name for path in output_root.iterdir()} != {"status.json"}:
            raise ValueError("capture output directory is missing or already contains artifacts")
        root_pin = assert_clean_tracked(root, "ROOT candidate and recipe", os.environ["GITHUB_SHA"])
        if root_pin != os.environ.get("GITHUB_SHA"):
            raise ValueError("candidate and recipe checkout differ from triggering commit")
        if os.environ.get("NI22_RESEARCH_PIN") != RESEARCH_PIN:
            raise ValueError("workflow research pin differs from reviewed producer pin")
        research_pin = assert_clean_tracked(research, "research", RESEARCH_PIN)
        carrier_pin = assert_clean_tracked(carrier, "native carrier", CARRIER_PIN)
        if os.environ.get("NI22_CARRIER_PIN") != CARRIER_PIN:
            raise ValueError("workflow carrier pin differs from reviewed carrier pin")

        expected_env_paths = {
            "KV_QUANT_TEST_RESEARCH_ROOT": research,
            "EXL3_TEST_PRODUCER": research / "scripts/kernel_rnd/exl3/evidence.py",
            "EVIDENCE_DURABILITY_PRODUCER": research / "scripts/validate/check_evidence_durability.py",
        }
        for key, expected in expected_env_paths.items():
            observed = os.environ.get(key)
            if observed is None or Path(observed).resolve() != expected.resolve():
                raise ValueError(f"workflow producer path does not resolve inside pinned research checkout: {key}")

        if sys.version_info[:3] != (3, 13, 15):
            raise ValueError("runner Python version differs from reviewed 3.13.15 pin")
        installed = {name: metadata.version(name) for name in PACKAGE_PINS}
        if installed != PACKAGE_PINS:
            raise ValueError("installed fixture dependency versions differ from reviewed pins")

        root_paths, symlink_facts = verify_root_sources(root, root_pin)
        verify_generic_research_checkout_isolated(root, root_pin)
        carrier_paths, carrier_symlink_facts = verify_root_sources(carrier, carrier_pin)
        research_paths = verify_research_sources(research, research_pin)
        source_counts = {
            "root_regular_python_config": len(root_paths),
            "root_symlink_metadata_only": len(symlink_facts),
            "carrier_regular_python_config": len(carrier_paths),
            "carrier_symlink_metadata_only": len(carrier_symlink_facts),
            "research_exact_regular_sources": len(research_paths),
        }
        context_path = output_root / "context.json"
        freeze_path = output_root / "pip-freeze.txt"
        environment_keys = (
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONUNBUFFERED",
            "KV_QUANT_TEST_RESEARCH_ROOT",
            "EXL3_TEST_PRODUCER",
            "EVIDENCE_DURABILITY_PRODUCER",
            "NI22_CARRIER_PIN",
            "NI22_RESEARCH_PIN",
        )
        context = {
            "python": sys.version,
            "platform": platform.platform(),
            "install_command": INSTALL_COMMAND,
            "required_package_versions": PACKAGE_PINS,
            "observed_package_versions": installed,
            "repositories": {
                "root_candidate": root_pin,
                "recipe": root_pin,
                "carrier": carrier_pin,
                "research": research_pin,
            },
            "selection": SELECTION,
            "expected_case_count": EXPECTED_CASES,
            "generic_research_checkout": GENERIC_RESEARCH_CHECKOUT,
            "generic_checkout_isolation_asserted": True,
            "source_counts": source_counts,
            "symlink_facts_metadata_only": symlink_facts,
            "carrier_symlink_facts_metadata_only": carrier_symlink_facts,
            "environment": {key: os.environ.get(key) for key in environment_keys},
        }
        context_path.write_text(json.dumps(context, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        freeze_path.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))

        junit_path = output_root / "adapter-modules.junit.xml"
        native_output = output_root / "native"
        if junit_path.exists() or native_output.exists():
            raise ValueError("capture output already exists; refusing to overwrite a prior run")
        pytest_argv = [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "--noconftest",
            "-p",
            "no:cacheprovider",
            "-q",
            *SELECTION,
            f"--junitxml={junit_path}",
        ]
        carrier_reader = carrier / "scripts/ci/native_conformance.py"
        if sha256(read_regular(carrier_reader)) != CARRIER_READER_SHA256:
            raise ValueError("carrier reader source hash differs from pin")
        native = load_native_carrier(carrier_reader)
        read_paths = [*root_paths, *carrier_paths, *research_paths, context_path, freeze_path]
        status.update(state="running", selection=SELECTION, source_counts=source_counts)
        status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        record = native.capture_fixture_execution(
            argv=pytest_argv,
            cwd=root,
            junit=junit_path,
            output=native_output,
            repositories={
                "root_candidate": root,
                "recipe": root,
                "carrier": carrier,
                "research": research,
            },
            read_paths=read_paths,
            selections=SELECTION,
        )
        receipt, receipt_file_sha256 = native.read_receipt(native_output / "receipt.json")
        counts = receipt.get("summary", {}).get("counts", {})
        status.update(
            state="passed" if record["fixture_execution_conformant"] is True else "failed",
            exit_code=record["exit_code"],
            fixture_execution_conformant=record["fixture_execution_conformant"],
            receipt_file_sha256=receipt_file_sha256,
            receipt_self_hash=receipt.get("receipt_sha256"),
            junit_counts=counts,
        )
        if (
            record["exit_code"] != 0
            or record["fixture_execution_conformant"] is not True
            or counts.get("collected") != EXPECTED_CASES
            or counts.get("passed") != EXPECTED_CASES
            or counts.get("skipped") != 0
            or counts.get("failure") != 0
            or counts.get("error") != 0
        ):
            status["state"] = "failed"
            status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            return 1
        status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return 0
    except Exception as exc:  # noqa: BLE001 - preserve bounded capture diagnostics
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if output_root.exists():
            status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
