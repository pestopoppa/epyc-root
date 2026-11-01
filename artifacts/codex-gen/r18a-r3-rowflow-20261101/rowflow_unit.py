#!/usr/bin/env python3
"""Bounded CPU compilation proof and rowflow-safe result writers for R18-A."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import time
import uuid
from pathlib import Path

UNIT_SCHEMA = "epyc.r18a.cpu_compile_unit.v1"
FULL_RESULT_SCHEMA = "epyc.r18a.full_build_result.v2"
FULL_TERMINAL_SCHEMA = "epyc.r18a.full_comparison_terminal.v1"
CPU_SOURCE_REL = Path("ggml/src/gguf.cpp")
CPU_OBJECT_REL = Path("ggml/src/CMakeFiles/ggml-base.dir/gguf.cpp.o")
CPU_MAKEFILE_REL = Path("ggml/src/CMakeFiles/ggml-base.dir/build.make")
CPU_FLAGS_REL = Path("ggml/src/CMakeFiles/ggml-base.dir/flags.make")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_cache(path: Path) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith(("#", "//")) or ":" not in line or "=" not in line:
            continue
        key, rest = line.split(":", 1)
        kind, value = rest.split("=", 1)
        out[key] = (kind, value)
    return out


def cpu_compile_record(*, source: Path, build: Path, scratch_root: Path,
                       recipe_path: Path, source_commit: str, source_tree: str,
                       compiler_path: Path, started_ns: int, command: list[str],
                       command_returncode: int, output_removed_before: bool) -> dict:
    """Accept only the exact generated make rule after a successful fresh object compile."""
    source = source.resolve(strict=True)
    build = build.resolve(strict=True)
    scratch_root = scratch_root.resolve(strict=True)
    recipe_path = recipe_path.resolve(strict=True)
    compiler_config_path = Path(os.path.abspath(compiler_path))
    compiler_real_path = compiler_config_path.resolve(strict=True)
    if not build.is_relative_to(scratch_root):
        raise ValueError("CPU build path escaped the private scratch root")
    if command_returncode != 0 or not output_removed_before:
        raise ValueError("CPU compile did not have a successful command and fresh-output precondition")

    expected_command = ["/usr/bin/gmake", "-C", str(build), "-f",
                        str(CPU_MAKEFILE_REL), str(CPU_OBJECT_REL), "-j1"]
    if command != expected_command:
        raise ValueError("CPU compile command differs from the pinned single-object make rule")

    cache = build / "CMakeCache.txt"
    cache_st = cache.lstat()
    if not stat.S_ISREG(cache_st.st_mode) or cache_st.st_size == 0:
        raise ValueError("CPU CMake cache is missing, empty, or not a regular file")
    values = parse_cache(cache)
    recipe = json.loads(recipe_path.read_text())
    defs = recipe["cpu"]["configure_definitions"]
    expected_values = {k: str(v["value"]) for k, v in defs.items()}
    expected_types = {k: str(v["type"]) for k, v in defs.items()}
    expected_values.update({
        "CMAKE_HOME_DIRECTORY": str(source),
        "CMAKE_GENERATOR": "Unix Makefiles",
        "CMAKE_C_COMPILER": "/usr/bin/cc",
        "CMAKE_CXX_COMPILER": str(compiler_config_path),
        "CMAKE_C_COMPILER_AR": "/usr/bin/gcc-ar-15",
        "CMAKE_CXX_COMPILER_AR": "/usr/bin/gcc-ar-15",
        "CMAKE_C_COMPILER_RANLIB": "/usr/bin/gcc-ranlib-15",
        "CMAKE_CXX_COMPILER_RANLIB": "/usr/bin/gcc-ranlib-15",
    })
    mismatches = {k: (values.get(k, (None, None)), expected_types.get(k), want)
                  for k, want in expected_values.items()
                  if values.get(k, (None, None))[1] != want
                  or (k in expected_types and values.get(k, (None, None))[0] != expected_types[k])}
    if mismatches:
        raise ValueError(f"CPU CMake cache differs from pinned recipe/toolchain: {mismatches}")

    source_file = source / CPU_SOURCE_REL
    source_st = source_file.lstat()
    if not stat.S_ISREG(source_st.st_mode):
        raise ValueError("pinned CPU source is not a regular file")
    makefile = build / CPU_MAKEFILE_REL
    make_st = makefile.lstat()
    if not stat.S_ISREG(make_st.st_mode):
        raise ValueError("generated CPU make rule is missing or unsafe")
    make_text = makefile.read_text(errors="strict")
    rule_prefix = str(CPU_OBJECT_REL) + ":"
    rule_lines = [line for line in make_text.splitlines() if line.startswith(rule_prefix)]
    if not rule_lines or str(source_file) not in rule_lines[0]:
        raise ValueError("generated CPU object rule does not bind the pinned gguf.cpp source")
    compile_recipes = [line.strip() for line in make_text.splitlines()
                       if line.startswith("\t") and str(compiler_config_path) in line
                       and f"-o {CPU_OBJECT_REL}" in line and f"-c {source_file}" in line]
    if len(compile_recipes) != 1:
        raise ValueError("generated CPU rule does not have one pinned compiler invocation for the exact object/source")
    flags = build / CPU_FLAGS_REL
    flags_st = flags.lstat()
    if not stat.S_ISREG(flags_st.st_mode):
        raise ValueError("generated CPU flags file is missing or unsafe")
    if not re.search(r"(?m)^CXX_COMPILER\s*=\s*" + re.escape(str(compiler_config_path)) + r"\s*$", flags.read_text()):
        raise ValueError("generated CPU flags do not name the pinned C++ compiler")

    obj = build / CPU_OBJECT_REL
    obj_st = obj.lstat()
    if not stat.S_ISREG(obj_st.st_mode) or obj_st.st_size < 64 or obj_st.st_mtime_ns < started_ns:
        raise ValueError("CPU object is missing, empty, unsafe, or not fresh for this compile")
    elf_header = subprocess.check_output(["/usr/bin/readelf", "-h", str(obj)], text=True)
    if not re.search(r"(?m)^\s*Type:\s+REL\b", elf_header):
        raise ValueError("fresh CPU output is not an ELF relocatable object")
    compiler_st = compiler_real_path.stat()
    if not stat.S_ISREG(compiler_st.st_mode):
        raise ValueError("pinned C++ compiler is not a regular file")

    return {
        "schema": UNIT_SCHEMA,
        "unit_id": uuid.uuid4().hex,
        "kind": "cpu_translation_unit_compiled",
        "scope": "one_exact_source_object_no_symbol_identity_verdict",
        "source_root": str(source), "source_commit": source_commit, "source_tree": source_tree,
        "source_path": str(source_file), "source_sha256": sha256(source_file),
        "recipe_path": str(recipe_path), "recipe_sha256": sha256(recipe_path),
        "build_dir": str(build), "cmake_cache_sha256": sha256(cache),
        "makefile_path": str(makefile), "makefile_sha256": sha256(makefile),
        "generated_compile_recipe": compile_recipes[0],
        "flags_path": str(flags), "flags_sha256": sha256(flags),
        "build_command": command, "command_returncode": command_returncode,
        "object_path": str(obj), "object_size_bytes": obj_st.st_size,
        "object_mtime_ns": obj_st.st_mtime_ns, "object_sha256": sha256(obj),
        "object_elf_type": "REL", "readelf_header_sha256": hashlib.sha256(elf_header.encode()).hexdigest(),
        "compiler_path": str(compiler_config_path), "compiler_real_path": str(compiler_real_path),
        "compiler_sha256": sha256(compiler_real_path),
        "compile_started_ns": started_ns, "observed_at_ns": time.time_ns(),
        "full_symbol_identity_complete": False,
    }


def comparison_outcome(path: Path, started_ns: int | None, returncode: int | None) -> dict:
    """Classify this run's comparator output; stale or absent files never become a verdict."""
    if started_ns is None:
        return {"state": "not_run", "returncode": None, "path": str(path), "sha256": None, "record": None}
    try:
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_mtime_ns < started_ns:
            raise ValueError("missing, unsafe, or stale comparator output")
        record = json.loads(path.read_text())
        if not isinstance(record, dict) or record.get("schema") != "r18a.independent_symbol_identity.v1":
            raise ValueError("comparator output schema differs")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"state": "invalid", "returncode": returncode, "path": str(path), "sha256": None,
                "record": None, "error": str(exc)}
    if record.get("error"):
        state = "invalid"
    elif record.get("symbol_identity_pass") is True and returncode == 0:
        state = "pass"
    elif record.get("symbol_identity_pass") is False and returncode == 1:
        state = "fail"
    else:
        state = "invalid"
    return {"state": state, "returncode": returncode, "path": str(path),
            "sha256": sha256(path), "record": record}


def completion_eligible(*, exit_code: int, partial: bool, comparison: dict) -> bool:
    return not partial and exit_code == 0 and comparison.get("state") == "pass"


def write_json_atomic(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
    data = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if os.write(fd, data) != len(data):
            raise OSError("short atomic JSON write")
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp, path)
    dirfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("JSONL destination is not a regular file")
        if os.write(fd, data) != len(data):
            raise OSError("short JSONL write")
        os.fsync(fd)
    finally:
        os.close(fd)
