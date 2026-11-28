#!/usr/bin/env python3
"""Replay the V5I opcode census from immutable historical store artifacts."""

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

RESEARCH = Path("/mnt/raid0/llm/epyc-inference-research")
KERNEL = Path("/mnt/raid0/llm/llama.cpp")
LLM = Path("/mnt/raid0/llm")
sys.path.insert(0, str(RESEARCH / "scripts/kernel_rnd"))
sys.dont_write_bytecode = True
import gfx90a_isa_audit as isa

V5 = "_ZL13q8mf6_mul_matILi2ELi2EEvPKcjS1_jiiiiPfl"
I8PC = "_ZL12q8pc_mul_matILi2ELi2EEvPKcjPKfS1_jiiiiPfl"
V5_HASH = "62a9267aca1923209bbbae7105cd2405e45293db3756bc57e60ae40a7f51d7e8"
I8PC_HASH = "9a1f3760239fe4bd2de1466d7d49ee79976a5be52016aa784ed3f6709a5aab75"
STORES = (
    ("gpu-20261124-5d85e7e73-servedperf", "test-backend-ops"),
    ("gpu-20261125-59cc19096-q8wt", "test-backend-ops"),
    ("gpu-20261125-13b59e593-q8wpip", "llama-server"),
    ("gpu-20261124-6aedfd2ac-c22i8pc", "llama-server"),
)
KNEE = LLM / "tmp/ak-q8-hbm-knee-map-gpu-20261125/out"
SERVED = LLM / "tmp/ak-27b-served-decode-profile-gpu-20261125/out"
DIAG = LLM / "tmp/ak-c22-q8wt-op-diag-gpu-20261125/out"
PC_GATE = LLM / "tmp/ak-c22-i8pc-gate-gpu-20261124-r6/out"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def symbol_objects(path, names):
    data = path.read_bytes()
    remaining = set(names)
    for index, blob in enumerate(isa.load_code_objects(path)):
        sections = isa.elf_sections(blob)
        symbols = isa.elf_symbols(blob, sections)
        for name, addr, size, info, section_idx in symbols:
            if name not in names:
                continue
            require(name in remaining and info & 15 == 2, "ambiguous function symbol")
            remaining.remove(name)
            section = sections[section_idx]
            offset = section.offset + addr - section.addr
            descriptor = next(sym for sym in symbols if sym[0] == name + ".kd")
            kd_section = sections[descriptor[4]]
            kd_offset = kd_section.offset + descriptor[1] - kd_section.addr
            yield name, blob, {
                "code_object_index": index,
                "library_offset": hex(data.index(blob)),
                "code_object_sha256": sha(blob),
                "code_object_bytes": len(blob),
                "symbol_address": hex(addr),
                "symbol_sha256": sha(blob[offset:offset + size]),
                "symbol_bytes": size,
                "descriptor_address": hex(descriptor[1]),
                "descriptor_sha256": sha(blob[kd_offset:kd_offset + descriptor[2]]),
            }
    require(not remaining, f"missing symbols {remaining}")


def static_census(name, blob, identity, ranges):
    with tempfile.TemporaryDirectory(prefix="convcore-", dir=Path(__file__).parent) as folder:
        obj = Path(folder) / "kernel.amdgpu"
        obj.write_bytes(blob)
        note = command(str(isa.LLVM_BIN / "llvm-readelf"), "-n", str(obj))
        dis = command(str(isa.LLVM_BIN / "llvm-objdump"), "-d", "--no-show-raw-insn",
                      f"--disassemble-symbols={name}", str(obj))
    insts = isa.split_disassembly(dis, {name})[name]
    base = int(identity["symbol_address"], 16)
    by_address = {inst.addr: inst for inst in insts}
    require(by_address[base + ranges[0][1]].target == (name, ranges[1][0]),
            "first nonflush branch changed")
    require(by_address[base + ranges[1][1]].target == (name, ranges[0][0]),
            "second nonflush branch changed")
    units = []
    for start, stop in ranges:
        body = (inst.op for inst in insts if base + start <= inst.addr <= base + stop)
        counts = Counter(body)
        units.append({
            "start_offset": hex(start),
            "latch_offset": hex(stop),
            "total_instructions": sum(counts.values()),
            "non_mfma_valu": sum(v for k, v in counts.items()
                                 if k.startswith("v_") and not k.startswith("v_mfma")),
            "opcode_counts": dict(sorted(counts.items())),
        })
    stable_dis = dis.replace(str(obj), name)
    return {"metadata": isa.parse_notes_text(note)[name], "units": units}, stable_dis


def trace_summary(path, symbol):
    dispatches = 0
    seen_resources = set()
    family_names = set()
    with path.open() as handle:
        for row in csv.DictReader(handle):
            name = row["Kernel_Name"]
            if "q8mf" in name and "mul_mat" in name:
                family_names.add(name)
            if name != symbol + ".kd":
                continue
            dispatches += 1
            seen_resources.add(tuple(int(row[key]) for key in (
                "Private_Segment_Size", "Group_Segment_Size", "Workgroup_Size_X", "Grid_Size_X")))
    require(dispatches > 0, f"missing trace symbol in {path}")
    return {"path": str(path), "sha256": isa.file_sha256(path), "matched_dispatches": dispatches,
            "seen_resources_private_lds_wg_grid": sorted(seen_resources), "v5_family_names": sorted(family_names)}


def main():
    out = Path(__file__).parent
    identities = {}
    static = {}
    for store, entry in STORES:
        folder = LLM / "kernels/builds" / store
        library = folder / "bin/libggml-hip.so"
        manifest = json.loads((folder / "BUILD-IDENTITY.json").read_text())
        commit = manifest["source_sha"]
        require(command("git", "-C", KERNEL, "rev-parse", f"{commit}^{{tree}}").strip()
                == manifest["source_tree"], f"source tree mismatch: {store}")
        command("sha256sum", "-c", "--status", "SHA256SUMS", cwd=folder)
        identities[store] = {
            "source_commit": commit, "source_tree": manifest["source_tree"],
            "loader_sha256": isa.file_sha256(folder / "bin" / entry),
            "library_sha256": isa.file_sha256(library), "symbols": {},
        }
        names = (V5, I8PC) if store.endswith("c22i8pc") else (V5,)
        for name, blob, info in symbol_objects(library, names):
            require(info["symbol_sha256"] == (V5_HASH if name == V5 else I8PC_HASH),
                    f"symbol bytes changed in {store}")
            identities[store]["symbols"][name] = info
            if store.endswith("servedperf") or name == I8PC:
                key = "v5i" if name == V5 else "i8pc"
                offsets = ((0xA20, 0xD68), (0xF40, 0x1270)) if name == V5 else (
                    (0x9E0, 0xC58), (0xE64, 0x10D4))
                static[key], dis = static_census(name, blob, info, offsets)
                (out / f"{key}-gfx90a.isa").write_text(dis)
    knee = trace_summary(KNEE / "prof/v-attn_q-w8-g416-r1/v-attn_q-w8-g416-r1_kernel_trace.csv", V5)
    served = trace_summary(SERVED / "prof/t-off/OFF_kernel_trace.csv", V5)
    recorded_counters = json.loads((DIAG / "RESULT.json").read_text())["summary"]["signatures"]
    gate = json.loads((PC_GATE / "RESULT.json").read_text())
    summary = {
        "stores": identities, "static": static, "trace": {"knee_op": knee, "served_off": served},
        "published_op_signatures": {key: recorded_counters[key] for key in ("v5i", "S16", "S64")},
        "i8pc_gate": {key: gate[key] for key in (
            "verdict", "op_geomean", "op_ratio_by_n", "served_ratio", "served_ci95", "kld_on")},
    }
    (out / "audit.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
