"""Check resident CPU model weights before opening an OpenCode model route."""
from __future__ import annotations

import os
from pathlib import Path
import re


def _affinity_nodes(process, node_root):
    affinity = set()
    for thread in (process / "task").iterdir():
        if thread.name.isdecimal():
            try:
                affinity.update(os.sched_getaffinity(int(thread.name)))
            except ProcessLookupError:
                continue  # A short-lived thread can exit during enumeration.
    covered, nodes = set(), set()
    for entry in node_root.glob("node[0-9]*"):
        cpus = set()
        for item in (entry / "cpulist").read_text().strip().split(","):
            if item:
                first, _, last = item.partition("-")
                cpus.update(range(int(first), int(last or first) + 1))
        local = affinity & cpus
        if local:
            if covered & local:
                raise ValueError("CPU affinity maps to overlapping NUMA nodes")
            covered.update(local)
            nodes.add(int(entry.name[4:]))
    if not affinity or covered != affinity:
        raise ValueError("NUMA topology does not cover the live thread affinity")
    return nodes


def _weight_residency(lines, model, model_bytes):
    large = []
    for line in lines:
        fields = dict(field.split("=", 1) for field in line.split()[2:] if "=" in field)
        if "file" in fields:
            # Linux escapes spaces and other delimiters in /proc path fields.
            path = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields["file"])
            if path == str(model):
                raise ValueError("live process still has a file-backed mapping of the GGUF model")
            continue
        if "anon" not in fields or "kernelpagesize_kB" not in fields:
            continue
        page_bytes = int(fields["kernelpagesize_kB"]) * 1024
        nodes = {int(key[1:]): int(value) * page_bytes for key, value in fields.items()
                 if re.fullmatch(r"N[0-9]+", key) and int(value) > 0}
        resident = sum(nodes.values())
        # A model-scale VMA is required. Aggregating smaller mappings can
        # mistake balanced KV and scratch buffers for split or skewed weights.
        if resident * 4 >= model_bytes * 3:
            if resident != int(fields["anon"]) * page_bytes:
                raise ValueError("model-scale mapping has incomplete anonymous residency evidence")
            large.append(nodes)
    if len(large) != 1:
        raise ValueError(f"expected one anonymous mapping with at least 75% of GGUF bytes resident, found {len(large)}; split allocations are unsupported")
    return large[0]


def require_cpu_placement(pid, cmdline, model, *, proc_root=Path("/proc"), node_root=Path("/sys/devices/system/node")):
    """Require observed model-scale anonymous residency on the affinity's nodes."""
    if b"--no-mmap" not in cmdline:
        raise ValueError("CPU NUMA preflight requires a live server launched with --no-mmap")
    process = proc_root / str(pid)
    try:
        model_bytes = model.stat().st_size
        if model_bytes <= 0:
            raise ValueError("GGUF size is unavailable")
        intended = _affinity_nodes(process, node_root)
        with (process / "numa_maps").open(errors="surrogateescape") as maps:
            resident = _weight_residency(maps, model, model_bytes)
        total = sum(resident.values())
        fractions = {node: size / total for node, size in sorted(resident.items())}
        # The field-verified bounds are 15–35% for four participating nodes.
        # Express them relative to equal interleaving for other affinity widths.
        if resident.keys() != intended or any(not 0.6 <= portion * len(intended) <= 1.4
                                                for portion in fractions.values()):
            raise ValueError(f"unbalanced anonymous weight residency {fractions}; expected nodes {sorted(intended)}")
    except (OSError, ValueError) as error:
        raise ValueError(f"CPU NUMA preflight could not verify balanced weights: {error}") from error
