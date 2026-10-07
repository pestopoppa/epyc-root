#!/usr/bin/env python3
"""Capture an ungraded, read-only registry projection diagnostic on a hosted runner.

The top-level runner uses only the Python standard library. PyYAML is imported
only in the compare subcommand, inside a disposable venv installed from all
wheel hashes locked for the required package. This file imports no project code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import tomllib
import traceback

APP_SHA = "87ecbf18bc3d3793271d0eaf183e19900ad9726a"
RESEARCH_SHA = "c49729505b6b85bcc2ef68255168014b4ae6a84d"
EXPECTED_WHEEL_SHA = "0f29edc409a6392443abf94b9cf89ce99889a1dd5376d94316ae5145dfedd5d6"
ROLES = (
    "architect_critic", "architect_general", "coder_escalation", "embedder",
    "embedder_1", "embedder_2", "embedder_3", "embedder_4", "embedder_5",
    "embedder_bge_m3", "embedder_granite_97m_r2", "embedder_multilingual_e5_base",
    "frontdoor", "ingest_long_context", "toolrunner", "vision_escalation", "worker",
    "worker_explore", "worker_fast", "worker_general", "worker_math",
    "worker_summarize", "worker_vision",
)
EXPECTED_DIFF = "speculative_decoding_policy.retired_fields.ngram_candidate_spec_type"
REMOTE_URLS = {
    "root": "https://github.com/pestopoppa/epyc-root.git",
    "app": "https://github.com/pestopoppa/epyc-orchestrator.git",
    "research": "https://github.com/pestopoppa/epyc-inference-research.git",
}
SOURCE_PATHS = {
    "root": (
        ("handoffs/active/speculative-decoding-mtp-refresh.md", "SR5 source context"),
        ("handoffs/active/vidya-belief-substrate-program.md", "VB enrollment"),
        ("scripts/vidya/adapters/README.md", "source-table enrollment"),
        (".github/workflows/inf50-registry-compiler-projection.yml", "recipe"),
        ("scripts/ci/inf50_registry_projection.py", "runner"),
    ),
    "app": (
        ("src/__init__.py", "executed import closure"),
        ("src/registry/__init__.py", "executed import closure"),
        ("src/registry/registry_compiler.py", "executed CLI/projection"),
        ("src/registry/drafter_selection.py", "executed projection dependency"),
        ("scripts/server/stack_manifest.py", "static role-list derivation only"),
        ("orchestration/launch_manifest.yaml", "role-list input"),
        ("orchestration/stack_topology.yaml", "projection input"),
        ("orchestration/model_registry.yaml", "current generated baseline"),
        ("pyproject.toml", "dependency provenance"),
        ("uv.lock", "dependency/wheel provenance"),
    ),
    "research": (
        ("orchestration/model_registry.yaml", "master projection input"),
    ),
}
WHEEL_REQUIREMENTS = "PyYAML==6.0.3 \\\n  --hash=sha256:44edc647873928551a01e7a563d7452ccdebee747728c1080d881d68af7b997e \\\n  --hash=sha256:652cb6edd41e718550aad172851962662ff2681490a8a711af6a4d288dd96824 \\\n  --hash=sha256:10892704fc220243f5305762e276552a0395f7beb4dbf9b14ec8fd43b57f126c \\\n  --hash=sha256:850774a7879607d3a6f50d36d04f00ee69e7fc816450e5f7e58d7f17f1ae5c00 \\\n  --hash=sha256:b8bb0864c5a28024fac8a632c443c87c5aa6f215c0b126c449ae1a150412f31d \\\n  --hash=sha256:1d37d57ad971609cf3c53ba6a7e365e40660e3be0e5175fa9f2365a379d6095a \\\n  --hash=sha256:37503bfbfc9d2c40b344d06b2199cf0e96e97957ab1c1b546fd4f87e53e5d3e4 \\\n  --hash=sha256:8098f252adfa6c80ab48096053f512f2321f0b998f98150cea9bd23d83e1467b \\\n  --hash=sha256:9f3bfb4965eb874431221a3ff3fdcddc7e74e3b07799e0e84ca4a0f867d449bf \\\n  --hash=sha256:7f047e29dcae44602496db43be01ad42fc6f1cc0d8cd6c83d342306c32270196 \\\n  --hash=sha256:fc09d0aa354569bc501d4e787133afc08552722d3ab34836a80547331bb5d4a0 \\\n  --hash=sha256:9149cad251584d5fb4981be1ecde53a1ca46c891a79788c0df828d2f166bda28 \\\n  --hash=sha256:5fdec68f91a0c6739b380c83b951e2c72ac0197ace422360e6d5a959d8d97b2c \\\n  --hash=sha256:ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc \\\n  --hash=sha256:8dc52c23056b9ddd46818a57b78404882310fb473d63f17b07d5c40421e47f8e \\\n  --hash=sha256:41715c910c881bc081f1e8872880d3c650acf13dfa8214bad49ed4cede7c34ea \\\n  --hash=sha256:96b533f0e99f6579b3d4d4995707cf36df9100d67e0c8303a0c55b27b5f99bc5 \\\n  --hash=sha256:5fcd34e47f6e0b794d17de1b4ff496c00986e1c83f7ab2fb8fcfe9616ff7477b \\\n  --hash=sha256:64386e5e707d03a7e172c0701abfb7e10f0fb753ee1d773128192742712a98fd \\\n  --hash=sha256:8da9669d359f02c0b91ccc01cac4a67f16afec0dac22c2ad09f46bee0697eba8 \\\n  --hash=sha256:2283a07e2c21a2aa78d9c4442724ec1eb15f5e42a723b99cb3d822d48f5f7ad1 \\\n  --hash=sha256:ee2922902c45ae8ccada2c5b501ab86c36525b883eff4255313a253a3160861c \\\n  --hash=sha256:a33284e20b78bd4a18c8c2282d549d10bc8408a2a7ff57653c0cf0b9be0afce5 \\\n  --hash=sha256:0f29edc409a6392443abf94b9cf89ce99889a1dd5376d94316ae5145dfedd5d6 \\\n  --hash=sha256:f7057c9a337546edc7973c0d3ba84ddcdf0daa14533c2065749c9075001090e6 \\\n  --hash=sha256:eda16858a3cab07b80edaf74336ece1f986ba330fdb8ee0d6c0d68fe82bc96be \\\n  --hash=sha256:d0eae10f8159e8fdad514efdc92d74fd8d682c933a6dd088030f3834bc8e6b26 \\\n  --hash=sha256:79005a0d97d5ddabfeeea4cf676af11e647e41d81c9a7722a193022accdb6b7c \\\n  --hash=sha256:5498cd1645aa724a7c71c8f378eb29ebe23da2fc0d7a08071d89469bf1d2defb \\\n  --hash=sha256:8d1fab6bb153a416f9aeb4b8763bc0f22a5586065f86f7664fc23339fc1c1fac \\\n  --hash=sha256:34d5fcd24b8445fadc33f9cf348c1047101756fd760b4dacb5c3e99755703310 \\\n  --hash=sha256:501a031947e3a9025ed4405a168e6ef5ae3126c59f90ce0cd6f2bfc477be31b7 \\\n  --hash=sha256:b3bc83488de33889877a0f2543ade9f70c67d66d9ebb4ac959502e12de895788 \\\n  --hash=sha256:c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5 \\\n  --hash=sha256:7c6610def4f163542a622a73fb39f534f8c101d690126992300bf3207eab9764 \\\n  --hash=sha256:5190d403f121660ce8d1d2c1bb2ef1bd05b5f68533fc5c2ea899bd15f4399b35 \\\n  --hash=sha256:4a2e8cebe2ff6ab7d1050ecd59c25d4c8bd7e6f400f5f82b96557ac0abafd0ac \\\n  --hash=sha256:93dda82c9c22deb0a405ea4dc5f2d0cda384168e466364dec6255b293923b2f3 \\\n  --hash=sha256:02893d100e99e03eda1c8fd5c441d8c60103fd175728e23e431db1b589cf5ab3 \\\n  --hash=sha256:c1ff362665ae507275af2853520967820d9124984e0f7466736aea23d8611fba \\\n  --hash=sha256:6adc77889b628398debc7b65c073bcb99c4a0237b248cacaf3fe8a557563ef6c \\\n  --hash=sha256:a80cb027f6b349846a3bf6d73b5e95e782175e52f22108cfa17876aaeff93702 \\\n  --hash=sha256:00c4bdeba853cc34e7dd471f16b4114f4162dc03e6b7afcc2128711f0eca823c \\\n  --hash=sha256:66e1674c3ef6f541c35191caae2d429b967b99e02040f5ba928632d9a7f0f065 \\\n  --hash=sha256:16249ee61e95f858e83976573de0f5b2893b3677ba71c9dd36b9cf8be9ac6d65 \\\n  --hash=sha256:4ad1906908f2f5ae4e5a8ddfce73c320c2a1429ec52eafd27138b7f1cbe341c9 \\\n  --hash=sha256:ebc55a14a21cb14062aa4162f906cd962b28e2e9ea38f9b4391244cd8de4ae0b\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def put(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(data)
    finally:
        os.close(fd)


def replace_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def put_json(path: Path, value) -> None:
    replace_bytes(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def safe_regular(path: Path) -> tuple[bytes, int]:
    """Read a regular leaf through no-follow directory descriptors."""
    path = Path(os.path.abspath(path))
    if not path.parts or path.name in {"", ".", ".."}:
        raise ValueError(f"source path has no ordinary leaf: {path}")
    parent_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:-1]:
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"source is not a regular file: {path}")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                data = handle.read()
            return data, stat.S_IMODE(info.st_mode)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def normalized_origin(value: str) -> str:
    value = value.rstrip("/")
    return value[:-4] if value.endswith(".git") else value


def run(argv, *, cwd: Path, env=None, timeout=None):
    try:
        return subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        completed = subprocess.CompletedProcess(argv, 124, exc.stdout or b"", exc.stderr or b"")
        completed.timed_out = True
        completed.timeout_seconds = timeout
        return completed


def write_command(custody: Path, label: str, argv, cwd: Path, result, extra=None):
    out = custody / "result" / "commands" / label
    put(out / "stdout.bin", result.stdout or b"")
    put(out / "stderr.bin", result.stderr or b"")
    report = {"argv": [str(x) for x in argv], "cwd": str(cwd),
              "exit_code": result.returncode,
              "timed_out": bool(getattr(result, "timed_out", False)),
              "timeout_seconds": getattr(result, "timeout_seconds", None)}
    if extra:
        report.update(extra)
    put_json(out / "command.json", report)


def source_inventory(repos: dict[str, Path], expected_root: str, custody: Path, phase: str):
    """Bind checkout heads, origins, full Git blobs/modes, and exact source bytes."""
    entries = []
    repo_ids = {}
    clean = {}
    for key in ("root", "app", "research"):
        repo = repos[key].resolve(strict=True)
        argv = ["git", "rev-parse", "HEAD"]
        head = run(argv, cwd=repo)
        write_command(custody, f"{phase}-git-{key}-head", argv, repo, head)
        if head.returncode:
            raise RuntimeError(f"could not read {key} HEAD: {head.stderr.decode(errors='replace')}")
        commit = head.stdout.decode().strip()
        expected = expected_root if key == "root" else APP_SHA if key == "app" else RESEARCH_SHA
        if commit != expected:
            raise ValueError(f"{key} commit mismatch: {commit} != {expected}")
        argv = ["git", "remote", "get-url", "origin"]
        remote = run(argv, cwd=repo)
        write_command(custody, f"{phase}-git-{key}-remote", argv, repo, remote)
        remote_value = remote.stdout.decode().strip()
        if remote.returncode or normalized_origin(remote_value) != normalized_origin(REMOTE_URLS[key]):
            raise ValueError(f"{key} origin mismatch: {remote_value!r}")
        argv = ["git", "status", "--porcelain=v1", "--untracked-files=all"]
        status = run(argv, cwd=repo)
        write_command(custody, f"{phase}-git-{key}-status", argv, repo, status)
        status_text = status.stdout.decode(errors="replace")
        clean[key] = status.returncode == 0 and not status.stdout
        if not clean[key]:
            raise ValueError(f"{key} checkout is not clean: {status_text}")
        repo_ids[key] = {"commit": commit, "origin": remote_value, "clean": True}
    index = 0
    for key in ("root", "app", "research"):
        repo = repos[key].resolve(strict=True)
        for relative, role in SOURCE_PATHS[key]:
            argv = ["git", "ls-tree", "HEAD", "--", relative]
            tree = run(argv, cwd=repo)
            write_command(custody, f"{phase}-tree-{index:03d}", argv, repo, tree)
            if tree.returncode:
                raise RuntimeError(f"git ls-tree failed for {key}:{relative}")
            rows = tree.stdout.decode().splitlines()
            if len(rows) != 1 or "\t" not in rows[0]:
                raise ValueError(f"missing or ambiguous Git source path {key}:{relative}")
            mode_type, git_path = rows[0].split("\t", 1)
            mode, kind, blob = mode_type.split()
            if kind != "blob" or git_path != relative:
                raise ValueError(f"source is not one regular Git blob: {key}:{relative}")
            argv = ["git", "cat-file", "blob", blob]
            cat = run(argv, cwd=repo)
            write_command(custody, f"{phase}-blob-{index:03d}", argv, repo, cat,
                          {"repo": key, "path": relative, "blob": blob})
            if cat.returncode:
                raise RuntimeError(f"git cat-file failed for {key}:{relative}")
            working, file_mode = safe_regular(repo / relative)
            if working != cat.stdout:
                raise ValueError(f"working bytes differ from pinned Git blob: {key}:{relative}")
            expected_mode = 0o755 if mode == "100755" else 0o644 if mode == "100644" else None
            if expected_mode is None or file_mode != expected_mode:
                raise ValueError(f"mode mismatch for {key}:{relative}: Git {mode}, filesystem {file_mode:o}")
            artifact_rel = f"inputs/{index:03d}.bin"
            if phase == "before":
                put(custody / "result" / artifact_rel, working)
            entries.append({"repo": key, "path": relative, "role": role, "git_mode": mode,
                            "fs_mode": file_mode, "git_blob": blob, "bytes": len(working),
                            "sha256": sha(working), "artifact": artifact_rel})
            index += 1
    return {"repositories": repo_ids, "clean": clean, "files": entries}


def opaque_state(path: Path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"state": "absent"}
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return {"state": "symlink", "mode": mode, "target": os.readlink(path)}
    if stat.S_ISREG(info.st_mode):
        data, _ = safe_regular(path)
        return {"state": "regular", "mode": mode, "bytes": len(data), "sha256": sha(data)}
    if stat.S_ISDIR(info.st_mode):
        return {"state": "directory", "mode": mode}
    return {"state": "special", "mode": mode, "file_type": stat.S_IFMT(info.st_mode)}


def tree_inventory(root: Path):
    """Record every result path/mode/byte hash, empty directory, and opaque symlink."""
    rows = []
    def walk(directory: Path, rel: PurePosixPath):
        children = sorted(os.scandir(directory), key=lambda item: item.name)
        if not children and rel.parts:
            rows.append({"path": rel.as_posix(), "type": "empty_directory"})
        for item in children:
            child_rel = rel / item.name
            info = item.stat(follow_symlinks=False)
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                rows.append({"path": child_rel.as_posix(), "type": "symlink", "mode": mode,
                             "target": os.readlink(item.path)})
            elif stat.S_ISDIR(info.st_mode):
                rows.append({"path": child_rel.as_posix(), "type": "directory", "mode": mode})
                walk(Path(item.path), child_rel)
            elif stat.S_ISREG(info.st_mode):
                data, actual_mode = safe_regular(Path(item.path))
                rows.append({"path": child_rel.as_posix(), "type": "file", "mode": actual_mode,
                             "bytes": len(data), "sha256": sha(data)})
            else:
                rows.append({"path": child_rel.as_posix(), "type": "special", "mode": mode,
                             "file_type": stat.S_IFMT(info.st_mode)})
    walk(root, PurePosixPath())
    return rows


def validate_lock(app: Path, result: Path):
    lock_path = app / "uv.lock"
    lock_bytes, _ = safe_regular(lock_path)
    parsed = tomllib.loads(lock_bytes.decode("utf-8"))
    package = next((row for row in parsed.get("package", []) if row.get("name", "").lower() == "pyyaml"), None)
    if not package or package.get("version") != "6.0.3" or package.get("dependencies", []):
        raise ValueError("APP lock does not bind the expected zero-dependency PyYAML 6.0.3 package")
    locked = {wheel.get("hash") for wheel in package.get("wheels", [])}
    required = set()
    for line in WHEEL_REQUIREMENTS.splitlines()[1:]:
        value = line.strip()
        if value.endswith("\\"):
            value = value[:-1].rstrip()
        if not value.startswith("--hash=sha256:"):
            raise ValueError("malformed wheel-hash line in bound requirement set")
        required.add("sha256:" + value.split("sha256:", 1)[1])
    if len(package.get("wheels", [])) != 47 or len(locked) != 47 or len(required) != 47 or locked != required:
        raise ValueError("embedded requirements do not equal all 47 APP uv.lock PyYAML wheel hashes")
    selected = [row for row in package["wheels"] if EXPECTED_WHEEL_SHA in row.get("hash", "")
                and "cp313-cp313-manylinux2014_x86_64" in row.get("url", "")]
    if len(selected) != 1:
        raise ValueError("APP lock lacks exactly one expected CPython 3.13 Linux x86_64 PyYAML wheel")
    put(result / "requirements.lock.txt", WHEEL_REQUIREMENTS.encode("utf-8"))
    put(result / "uv.lock", lock_bytes)
    put_json(result / "dependency-lock-check.json", {
        "app_uv_lock_sha256": sha(lock_bytes), "package_count": len(parsed.get("package", [])),
        "pyyaml_locked_wheel_hashes": len(locked), "requirement_hashes": len(required),
        "all_hashes_equal": locked == required, "selected_runner_wheel": selected[0],
        "full_lock_wheel_map": "uv.lock artifact contains all package wheel and sdist metadata",
    })


def environment_record() -> dict:
    info = {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "system": platform.system(),
            "machine": platform.machine(), "executable": sys.executable}
    if info["python"] != "3.13.15" or info["system"] != "Linux" or info["machine"] != "x86_64":
        raise ValueError(f"runner environment differs from frozen target: {info}")
    return info


def compare_mode(args) -> int:
    import yaml
    candidate = yaml.safe_load(Path(args.candidate).read_text(encoding="utf-8"))
    baseline = yaml.safe_load(Path(args.baseline).read_text(encoding="utf-8"))
    master = yaml.safe_load(Path(args.master).read_text(encoding="utf-8"))
    if not all(isinstance(item, dict) for item in (candidate, baseline, master)):
        raise ValueError("native candidate, APP baseline, and Research master must be YAML mappings")
    def get_path(root, dotted):
        value = root
        for part in dotted.split("."):
            if not isinstance(value, dict) or part not in value:
                raise KeyError(dotted)
            value = value[part]
        return value
    expected = get_path(master, EXPECTED_DIFF)
    actual = get_path(candidate, EXPECTED_DIFF)
    diffs = []
    seen = set()
    def walk(old, new, prefix=""):
        pair = (id(old), id(new))
        if pair in seen:
            return
        seen.add(pair)
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(set(old) | set(new), key=str):
                path = f"{prefix}.{key}" if prefix else str(key)
                if key not in old or key not in new:
                    diffs.append(path)
                else:
                    walk(old[key], new[key], path)
        elif isinstance(old, list) and isinstance(new, list):
            if old != new:
                diffs.append(prefix)
        elif old != new:
            diffs.append(prefix)
    walk(baseline, candidate)
    report = {"record_kind": "semantic_projection_diagnostic", "expected_path": EXPECTED_DIFF,
              "actual_diff_paths": sorted(diffs), "candidate_value_matches_research_master": actual == expected,
              "candidate_value": actual, "expected_value": expected,
              "ungraded": True, "native_receipt": None, "junit": None, "claim": None}
    Path(args.report).write_bytes(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    sys.stdout.buffer.write(canonical(report) + b"\n")
    return 0 if diffs == [EXPECTED_DIFF] and actual == expected else 1


def set_state(meta: Path, state: dict):
    put_json(meta / "run-state.json", state)


def fail(custody: Path, state: dict, phase: str, exc: BaseException) -> None:
    error = {"phase": phase, "exception_type": type(exc).__name__, "message": str(exc)}
    state["phases"][phase] = "error"
    state["error"] = error
    state["ended_utc"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    put_json(custody / "meta" / "failure.json", error)
    put(custody / "meta" / "failure.traceback.txt", traceback.format_exc().encode("utf-8", "replace"))
    set_state(custody / "meta", state)


def capture(args) -> int:
    root, app, research = (Path(args.root).resolve(strict=True), Path(args.app).resolve(strict=True),
                           Path(args.research).resolve(strict=True))
    custody = Path(args.custody).resolve(strict=True)
    result, meta = custody / "result", custody / "meta"
    if not result.is_dir() or not meta.is_dir():
        raise ValueError("workflow must pre-create result and metadata custody directories")
    state = {"record_kind": "ungraded_native_projection_diagnostic", "schema": "epyc.inf50.projection.v1",
             "classification": "UN-GRADED_DIAGNOSTIC", "native_conformance_receipt": None,
             "junit": None, "claim_tuple": None,
             "phases": {"environment": "not_started", "source_before": "not_started",
                        "dependency_setup": "not_started", "compiler": "not_started",
                        "semantic_compare": "not_started", "source_after": "not_started",
                        "result_tree": "not_started"}}
    set_state(meta, state)
    put_json(meta / "result-tree-before.json", tree_inventory(result))
    repos = {"root": root, "app": app, "research": research}
    before_sources = None
    before_cache = None
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    try:
        state["runner"] = {"run_id": os.environ.get("GITHUB_RUN_ID", ""),
                           "job": os.environ.get("GITHUB_JOB", ""),
                           "attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
                           "environment": environment_record()}
        state["phases"]["environment"] = "captured"
        set_state(meta, state)
        expected_root = os.environ.get("EXPECTED_ROOT_SHA", "")
        if len(expected_root) != 40 or any(char not in "0123456789abcdef" for char in expected_root):
            raise ValueError("EXPECTED_ROOT_SHA is missing or malformed")
        before_sources = source_inventory(repos, expected_root, custody, "before")
        put_json(result / "source-map-before.json", before_sources)
        before_cache = opaque_state(app / "orchestration" / ".lean_cache_key")
        put_json(result / "cache-key-before.json", before_cache)
        state["phases"]["source_before"] = "captured_and_git_clean"
        set_state(meta, state)

        validate_lock(app, result)
        venv = Path(os.environ["RUNNER_TEMP"]) / "inf50-projection-venv"
        create_argv = [sys.executable, "-m", "venv", str(venv)]
        create = run(create_argv, cwd=root, timeout=120)
        write_command(custody, "venv-create", create_argv, root, create)
        if create.returncode:
            raise RuntimeError(f"venv setup exited {create.returncode}")
        vpy = venv / "bin" / "python"
        install_argv = [str(vpy), "-m", "pip", "install", "--disable-pip-version-check",
                        "--no-input", "--no-deps", "--require-hashes", "--only-binary=:all:",
                        "--report", str(result / "dependency-install-report.json"),
                        "-r", str(result / "requirements.lock.txt")]
        install = run(install_argv, cwd=root, env=env, timeout=300)
        write_command(custody, "dependency-install", install_argv, root, install)
        if install.returncode:
            raise RuntimeError(f"pinned PyYAML installation exited {install.returncode}")
        report = json.loads((result / "dependency-install-report.json").read_text(encoding="utf-8"))
        installs = report.get("install", [])
        if len(installs) != 1:
            raise ValueError(f"expected exactly one installed distribution; got {len(installs)}")
        installed = installs[0]
        wheel_hash = installed.get("download_info", {}).get("archive_info", {}).get("hashes", {}).get("sha256")
        version = installed.get("metadata", {}).get("version")
        name = installed.get("metadata", {}).get("name", "").lower()
        if name != "pyyaml" or version != "6.0.3" or wheel_hash != EXPECTED_WHEEL_SHA:
            raise ValueError("installed package identity/hash differs from locked runner wheel")
        check_argv = [str(vpy), "-c", "import yaml; print(yaml.__version__)"]
        check = run(check_argv, cwd=root, env=env, timeout=30)
        write_command(custody, "dependency-import-check", check_argv, root, check)
        if check.returncode or check.stdout.strip() != b"6.0.3":
            raise ValueError("locked PyYAML import check did not report 6.0.3")
        put_json(result / "installed-dependency.json", {
            "name": name, "version": version, "wheel_sha256": wheel_hash,
            "wheel_url": installed.get("download_info", {}).get("url"),
            "classification": "sole external dependency for actual CLI closure",
        })
        state["phases"]["dependency_setup"] = "one_locked_wheel_installed_and_verified"
        set_state(meta, state)

        compiler_argv = [str(vpy), "-m", "src.registry.registry_compiler",
                         "--master", str(research / "orchestration" / "model_registry.yaml"),
                         "--topology", str(app / "orchestration" / "stack_topology.yaml"),
                         "--roles", *ROLES, "--dry-run"]
        compiler = run(compiler_argv, cwd=app, env={**env, "PYTHONPATH": str(app)}, timeout=600)
        put(result / "compiler.stdout.yaml", compiler.stdout or b"")
        put(result / "compiler.stderr.bin", compiler.stderr or b"")
        put_json(result / "compiler.command.json", {"argv": compiler_argv, "cwd": str(app),
                                                      "exit_code": compiler.returncode,
                                                      "timed_out": bool(getattr(compiler, "timed_out", False)),
                                                      "timeout_seconds": getattr(compiler, "timeout_seconds", None)})
        state["phases"]["compiler"] = "exit_" + str(compiler.returncode)
        set_state(meta, state)
        predicate = {"compiler_exit": compiler.returncode, "semantic_compare_exit": None,
                     "source_unchanged": None, "cache_key_unchanged": None, "result": "pending",
                     "ungraded": True, "native_conformance_receipt": None, "junit": None, "claim_tuple": None}
        put_json(result / "projection-predicate.json", predicate)
        compare_argv = [str(vpy), str(Path(__file__).resolve()), "compare",
                        "--candidate", str(result / "compiler.stdout.yaml"),
                        "--baseline", str(app / "orchestration" / "model_registry.yaml"),
                        "--master", str(research / "orchestration" / "model_registry.yaml"),
                        "--report", str(result / "semantic-diff.json")]
        compare = run(compare_argv, cwd=app, env=env, timeout=120)
        write_command(custody, "semantic-compare", compare_argv, app, compare)
        predicate["semantic_compare_exit"] = compare.returncode
        state["phases"]["semantic_compare"] = "exit_" + str(compare.returncode)
        set_state(meta, state)

        after_sources = source_inventory(repos, expected_root, custody, "after")
        put_json(result / "source-map-after.json", after_sources)
        after_cache = opaque_state(app / "orchestration" / ".lean_cache_key")
        put_json(result / "cache-key-after.json", after_cache)
        source_same = canonical(before_sources) == canonical(after_sources)
        cache_same = before_cache == after_cache
        predicate["source_unchanged"] = source_same
        predicate["cache_key_unchanged"] = cache_same
        predicate["result"] = "pass" if (
            compiler.returncode == 0 and compare.returncode == 0 and source_same and cache_same
        ) else "fail"
        put_json(result / "projection-predicate.json", predicate)
        state["phases"]["source_after"] = "unchanged" if source_same else "changed"
        state["diagnostic_result"] = predicate["result"]
        state["ended_utc"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        set_state(meta, state)
        put_json(meta / "result-tree-after.json", tree_inventory(result))
        state["phases"]["result_tree"] = "captured"
        set_state(meta, state)
        return 0 if predicate["result"] == "pass" else 1
    except Exception as exc:
        fail(custody, state, "capture", exc)
        try:
            if before_sources is not None:
                after = source_inventory(repos, os.environ.get("EXPECTED_ROOT_SHA", ""), custody, "error-after")
                put_json(result / "source-map-error-after.json", after)
                state["source_after_error_unchanged"] = canonical(before_sources) == canonical(after)
            if before_cache is not None:
                state["cache_key_after_error"] = opaque_state(app / "orchestration" / ".lean_cache_key")
            put_json(meta / "result-tree-after-error.json", tree_inventory(result))
            put_json(meta / "run-state.json", state)
        except Exception as custody_exc:
            put_json(meta / "custody-error.json", {"exception_type": type(custody_exc).__name__,
                      "message": str(custody_exc), "traceback": traceback.format_exc()})
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--root", required=True)
    capture_parser.add_argument("--app", required=True)
    capture_parser.add_argument("--research", required=True)
    capture_parser.add_argument("--custody", required=True)
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--candidate", required=True)
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--master", required=True)
    compare_parser.add_argument("--report", required=True)
    args = parser.parse_args()
    if args.mode == "compare":
        return compare_mode(args)
    return capture(args)


if __name__ == "__main__":
    raise SystemExit(main())
