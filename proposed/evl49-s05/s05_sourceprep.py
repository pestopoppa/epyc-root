#!/usr/bin/env python3
"""Opt-in S-05 corrected-grid generator and per-cell receipt sealer.

Scratch PREP artifact. It never changes the canonical manifest generator or
server_numa_np_sweep.py. Generation imports the pinned canonical generator only
when explicitly requested; `--check` validates in memory and `--write` writes
only below an explicit output directory outside the Research checkout.
The receipt subcommand accepts raw owner-collected evidence and fails closed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

SOURCE_COMMIT = "3caaf22fa853daab5c5ae055ca46b67809e2c938"
GENERATOR_PATH = "scripts/benchmark/e5_cell_manifests.py"
GENERATOR_BLOB = "21d623581d31e235a719f0db1775b3321025dfa1"
RUNBOOK_PATH = "data/batched_decode/E5_STAGE_B_RUNBOOK.md"
RUNBOOK_BLOB = "9bee9121b1e0eac28523177511ba527bd2c44095"
SWEEP_HARNESS_PATH = "scripts/benchmark/server_numa_np_sweep.py"
SWEEP_HARNESS_BLOB = "ac4355855aa03bfc38a4133aa321648c9d3aa571"
SELF_PATH = Path(__file__).resolve()

# Current published v10 dry-only selection, restricted to the two remaining
# Stage-B model groups. The selected keys are verified against build_grid().
SELECTED = {
    "qwen36_q8_0": {
        "window": "W1",
        "cells": [("C1", 1), ("C1", 4), ("C1", 8), ("C1", 16), ("C1", 32),
                  ("C2", 8), ("C2", 16), ("C3", 1), ("C3", 2), ("C3", 4), ("C3", 8)],
    },
    "qwen3_next_80b": {
        "window": "W4",
        "cells": [("C1", 1), ("C1", 4), ("C1", 8), ("C1", 16), ("C1", 32),
                  ("C1b", 4), ("C1b", 8), ("C1b", 16),
                  ("C3", 1), ("C3", 2), ("C3", 4), ("C3", 8)],
    },
}
FULL_K = {"qwen36_q8_0": (1, 4, 8, 16, 32), "qwen3_next_80b": (1, 4, 8, 16, 32)}
STRADDLING_CONFIGS = {"C1", "C1b"}
CONTROL_NOTE = (
    "S-05 defect-replication control: legacy straddling half cpuset with "
    "taskset-only policy retained for comparison; not corrected placement."
)
FULL_NOTE = (
    "S-05 corrected-placement arm: full machine cpu_list=0-95 with "
    "numactl_policy=interleave=all; paired against retained legacy "
    "straddling C1 defect-replication control."
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _run_git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.stdout.strip()


def _load_generator(root: Path):
    """Load only the pinned source bytes and fail if the working file differs."""
    generator = root / GENERATOR_PATH
    runbook = root / RUNBOOK_PATH
    harness = root / SWEEP_HARNESS_PATH
    for rel, expected in ((GENERATOR_PATH, GENERATOR_BLOB),
                          (RUNBOOK_PATH, RUNBOOK_BLOB),
                          (SWEEP_HARNESS_PATH, SWEEP_HARNESS_BLOB)):
        tree_blob = _run_git(root, "rev-parse", f"{SOURCE_COMMIT}:{rel}")
        work_blob = _run_git(root, "hash-object", str(root / rel))
        if tree_blob != expected or work_blob != expected:
            raise ValueError(f"source pin mismatch for {rel}: tree={tree_blob}, worktree={work_blob}")
    spec = importlib.util.spec_from_file_location("s05_pinned_e5_cell_manifests", generator)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned generator {generator}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _note(cell: dict, text: str) -> None:
    old = str(cell.get("notes") or "").strip()
    if text not in old:
        cell["notes"] = "; ".join(p for p in (old, text) if p)


def build_roster(generator) -> list[dict]:
    """Build selected current Stage-B cells plus full C1 siblings in memory."""
    output: list[dict] = []
    for model, spec in SELECTED.items():
        window = spec["window"]
        for config, np in spec["cells"]:
            if np not in generator.STAGE_B_K[model][config]:
                raise ValueError(f"selected current-runbook cell is outside pinned Stage-B K set: {(model, config, np, window)}")
            is_control = config in STRADDLING_CONFIGS
            cell = generator.make_cell(
                model, config, np, window,
                decision_grade_intent=True,
                n_predict=generator.N_PREDICT_STAGE_B,
                extra_notes=CONTROL_NOTE if is_control else "",
                stage_b_families=generator._stage_b_families(model, config, np),
            )
            if is_control and any(i.get("numactl_policy") != "none" for i in cell.get("instances", [])):
                raise ValueError(f"unexpected control policy: {cell['cell_id']}")
            output.append(cell)
        for np in FULL_K[model]:
            full = generator.make_cell(
                model, "C1", np, window,
                decision_grade_intent=True,
                n_predict=generator.N_PREDICT_STAGE_B,
                full_variant=True,
                cell_id_suffix="-full",
                extra_notes=FULL_NOTE,
                stage_b_families=[],
            )
            full["s05_shape_variant"] = "full_machine_corrected"
            output.append(full)
    ids = [c["cell_id"] for c in output]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate roster contains duplicate cell IDs")
    for cell in output:
        errors = generator.validate_cell_manifest(cell)
        if errors:
            raise ValueError(f"generator validator rejected {cell['cell_id']}: {errors}")
        for inst in cell["instances"]:
            cpus = generator.parse_cpulist(inst["cpu_list"])
            if cpus is None:
                raise ValueError(f"invalid cpu_list in {cell['cell_id']}")
            if cpus in (generator.parse_cpulist(generator.CPUSET_HALF0), generator.parse_cpulist(generator.CPUSET_HALF1)):
                if cell["config_id"] in STRADDLING_CONFIGS and CONTROL_NOTE not in cell.get("notes", ""):
                    raise ValueError(f"unmarked straddling control: {cell['cell_id']}")
            if cpus == set(range(96)) and inst["numactl_policy"] != "interleave=all":
                raise ValueError(f"full-machine cell missing interleave: {cell['cell_id']}")
    return output


def generate(args) -> int:
    root = Path(args.research_root).resolve()
    out = Path(args.output_dir).resolve()
    if out == root or root in out.parents:
        raise ValueError("output directory must be outside the Research checkout")
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"refusing nonempty output directory: {out}")
    gen = _load_generator(root)
    cells = build_roster(gen)
    print(f"validated candidate cells: {len(cells)} (W1=11 + W4=12 + full arms=10)")
    print(f"source HEAD: {_run_git(root, 'rev-parse', 'HEAD')}; pinned tree commit: {SOURCE_COMMIT}")
    print(f"source generator blob: {GENERATOR_BLOB}; harness blob: {SWEEP_HARNESS_BLOB} (unchanged)")
    if not args.write:
        print("no files written; pass --write to materialize under the explicit scratch output directory")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for cell in cells:
        path = out / cell["model_key"] / (cell["cell_id"] + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(cell, indent=2, ensure_ascii=False).encode() + b"\n"
        path.write_bytes(body)
        rows.append({"path": path.relative_to(out).as_posix(), "cell_id": cell["cell_id"],
                     "sha256": _sha256(body), "bytes": len(body)})
    roster = {
        "schema": "evl49-s05-candidate-roster/1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_commit": SOURCE_COMMIT,
        "generator_blob": GENERATOR_BLOB,
        "runbook_blob": RUNBOOK_BLOB,
        "sweep_harness_blob_unchanged": SWEEP_HARNESS_BLOB,
        "candidate_cell_count": len(rows),
        "scope": "current v10 W1/W4 dry selection plus 10 current-generator full-machine siblings; candidate only, not an execution claim",
        "cells": rows,
    }
    (out / "ROSTER-MANIFEST.json").write_text(json.dumps(roster, indent=2) + "\n")
    print(f"wrote {len(cells)} manifests below {out}")
    return 0


def _normalize_cpu_list(raw: str) -> set[int]:
    cpus: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            raise ValueError("empty cpulist segment")
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            if lo < 0 or hi < lo:
                raise ValueError(f"invalid cpulist range {part}")
            cpus.update(range(lo, hi + 1))
        else:
            value = int(part)
            if value < 0:
                raise ValueError(f"invalid CPU id {part}")
            cpus.add(value)
    return cpus


def _numa_policy_from_maps(raw: str) -> str:
    policies = set()
    for line in raw.splitlines():
        for token in line.split():
            if token == "interleave" or token.startswith("interleave:"):
                policies.add("interleave")
            elif token == "default" or token.startswith("default:"):
                policies.add("default")
            elif token.startswith(("bind:", "preferred:", "local:", "prefer:", "static:", "relative:")):
                policies.add("other")
    if not policies:
        return "unknown"
    if "other" in policies:
        return "conflict"
    if len(policies) != 1:
        return "mixed"
    return next(iter(policies))


def _pages_by_node_from_maps(raw: str) -> dict[str, int]:
    pages: dict[str, int] = {}
    for line in raw.splitlines():
        for token in line.split():
            if len(token) > 3 and token[0] == "N" and "=" in token:
                node, count = token.split("=", 1)
                if node[1:].isdigit() and count.isdigit():
                    key = f"N{int(node[1:])}"
                    pages[key] = pages.get(key, 0) + int(count)
    return pages


def validate_evidence(manifest: dict, evidence: dict, manifest_sha256: str | None = None) -> None:
    """Validate owner-collected observations; missing or contradictory is fatal."""
    expected_manifest_hash = manifest_sha256 or _sha256(_canonical_json(manifest))
    if evidence.get("manifest_sha256") != expected_manifest_hash:
        raise ValueError("manifest_sha256 mismatch")
    provenance = evidence.get("provenance") or {}
    for key, expected in (("research_commit", SOURCE_COMMIT), ("generator_blob", GENERATOR_BLOB),
                          ("runbook_blob", RUNBOOK_BLOB), ("harness_blob", SWEEP_HARNESS_BLOB)):
        if provenance.get(key) != expected:
            raise ValueError(f"provenance pin missing/mismatched: {key}")
    for key in ("binary_sha256", "model_sha256", "input_sha256", "recipe_sha256", "admission_artifact_sha256"):
        if not _valid_sha256(provenance.get(key)):
            raise ValueError(f"provenance digest missing: {key}")
    if provenance.get("owner_window_admitted") is not True:
        raise ValueError("owner window was not admitted")
    def timestamp(value):
        if not isinstance(value, str):
            raise ValueError("missing observation timestamp")
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("observation timestamp lacks timezone")
        return parsed
    measurement = evidence.get("measurement_window") or {}
    start, end = timestamp(measurement.get("start_utc")), timestamp(measurement.get("end_utc"))
    if start >= end:
        raise ValueError("invalid measurement window")
    cache = evidence.get("cache_drop") or {}
    if cache.get("exit_status") != 0 or not cache.get("argv") or not cache.get("start_utc") or not cache.get("end_utc"):
        raise ValueError("cache-drop receipt missing/failed")
    if "drop_caches" not in " ".join(str(x) for x in cache["argv"]):
        raise ValueError("cache-drop argv does not identify drop_caches")
    if not timestamp(cache["start_utc"]) <= timestamp(cache["end_utc"]) <= start:
        raise ValueError("cache-drop window does not precede measurement")
    for k in ("cached_kib_before", "cached_kib_after"):
        if not isinstance(cache.get(k), int) or cache[k] < 0:
            raise ValueError(f"cache-drop receipt lacks integer {k}")
    outputs = evidence.get("harness") or {}
    if (outputs.get("exit_status") != 0 or not _valid_sha256(outputs.get("stdout_sha256"))
            or not _valid_sha256(outputs.get("stderr_sha256"))
            or not _valid_sha256(outputs.get("cell_result_sha256"))
            or outputs.get("cell_result_cell_id") != manifest.get("cell_id")):
        raise ValueError("harness outcome/raw stream pins missing or failed")
    observed = evidence.get("instances")
    expected_instances = manifest.get("instances") or []
    if not isinstance(observed, list) or len(observed) != len(expected_instances):
        raise ValueError("instance evidence count differs from manifest")
    for expected, seen in zip(expected_instances, observed):
        label = str(expected.get("port"))
        pid = seen.get("pid")
        if not isinstance(pid, int) or pid <= 0 or not isinstance(seen.get("start_ticks"), int) or seen["start_ticks"] <= 0:
            raise ValueError(f"instance {label}: process identity missing")
        requested = _normalize_cpu_list(expected["cpu_list"])
        if _normalize_cpu_list(seen.get("cpus_allowed_list", "")) != requested:
            raise ValueError(f"instance {label}: observed affinity differs from manifest")
        gate = seen.get("affinity_preflight") or {}
        if (gate.get("exit_status") != 0 or gate.get("live_affinity_verified") is not True
                or not _valid_sha256(gate.get("artifact_sha256"))):
            raise ValueError(f"instance {label}: existing affinity-preflight gate did not pass")
        if _normalize_cpu_list(gate.get("observed_cpu_list", "")) != requested:
            raise ValueError(f"instance {label}: preflight cpuset differs from manifest")
        argv = seen.get("launch_argv") or []
        expected_taskset = ["-c", expected["cpu_list"]]
        if not argv or "taskset" not in argv or not any(argv[i:i + 2] == expected_taskset for i in range(len(argv) - 1)):
            raise ValueError(f"instance {label}: actual launch argv missing taskset")
        policy = expected.get("numactl_policy")
        if requested == set(range(96)) and policy != "interleave=all":
            raise ValueError(f"instance {label}: full-machine cell missing interleave")
        if policy == "interleave=all":
            if "numactl" not in argv or "--interleave=all" not in argv or requested != set(range(96)):
                raise ValueError(f"instance {label}: full-machine argv/policy mismatch")
            wanted_maps = "interleave"
        elif policy == "none":
            if "numactl" in argv:
                raise ValueError(f"instance {label}: unexpected numactl argv for taskset-only control")
            if expected.get("cpu_list") in ("0-47,96-143", "48-95,144-191") and CONTROL_NOTE not in str(manifest.get("notes") or ""):
                raise ValueError(f"instance {label}: straddling half lacks defect-replication annotation")
            wanted_maps = "default"
        else:
            raise ValueError(f"instance {label}: unsupported manifest policy {policy!r}")
        observed_times = seen.get("observation_times") or {}
        if not timestamp(observed_times.get("ready")) <= start < timestamp(observed_times.get("during_cell")) < end <= timestamp(observed_times.get("after_cell")):
            raise ValueError(f"instance {label}: observations do not bracket/overlap measurement")
        for phase in ("ready", "during_cell", "after_cell"):
            maps = seen.get(f"numa_maps_{phase}")
            numastat = seen.get(f"numastat_{phase}")
            counts = seen.get(f"pages_by_node_{phase}")
            if not isinstance(maps, str) or not maps.strip():
                raise ValueError(f"instance {label}: missing raw numa_maps_{phase}")
            if not isinstance(numastat, str) or not numastat.strip():
                raise ValueError(f"instance {label}: missing raw numastat_{phase}")
            actual_map_policy = _numa_policy_from_maps(maps)
            # A process can have unrelated default-policy VMAs (executable,
            # shared libraries) while its newly allocated working set is
            # interleaved. Require positive evidence of the requested policy
            # and reject contradictory explicit policies; do not require every
            # VMA to share one policy.
            if wanted_maps == "interleave" and actual_map_policy not in ("interleave", "mixed"):
                raise ValueError(f"instance {label}: numa_maps_{phase} lacks interleave evidence")
            if wanted_maps == "default" and actual_map_policy not in ("default",):
                raise ValueError(f"instance {label}: numa_maps_{phase} policy disagrees with manifest")
            if not isinstance(counts, dict) or not counts or any(not isinstance(v, int) or v < 0 for v in counts.values()):
                raise ValueError(f"instance {label}: pages_by_node_{phase} missing/invalid")
            parsed_pages = _pages_by_node_from_maps(maps)
            if parsed_pages != counts:
                raise ValueError(f"instance {label}: pages_by_node_{phase} differs from raw numa_maps")
    if evidence.get("teardown", {}).get("all_pids_dead") is not True:
        raise ValueError("teardown does not verify all instance processes exited")


def seal_receipt(manifest_path: Path, evidence_path: Path, output_path: Path) -> dict:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    evidence = json.loads(evidence_path.read_text())
    manifest_digest = _sha256(manifest_bytes)
    validate_evidence(manifest, evidence, manifest_digest)
    receipt = {
        "schema": "evl49-s05-submitted-evidence-envelope/1",
        "verification_scope": "structural consistency only; not native observation, warrant, grade, or owner admission verification",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {"research_commit": SOURCE_COMMIT, "generator_blob": GENERATOR_BLOB,
                   "sweep_harness_blob_unchanged": SWEEP_HARNESS_BLOB,
                   "receipt_writer_sha256": _sha256(SELF_PATH.read_bytes())},
        "cell_id": manifest["cell_id"],
        "manifest_sha256": manifest_digest,
        "evidence": evidence,
    }
    receipt["seal_sha256"] = _sha256(_canonical_json(receipt))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite receipt {output_path}")
    output_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    return receipt


def verify_receipt(path: Path, manifest_path: Path) -> dict:
    receipt = json.loads(path.read_text())
    seal = receipt.pop("seal_sha256", None)
    if not isinstance(seal, str) or seal != _sha256(_canonical_json(receipt)):
        raise ValueError("receipt seal mismatch")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if receipt.get("manifest_sha256") != _sha256(manifest_bytes):
        raise ValueError("archived manifest byte digest differs from receipt")
    if receipt.get("cell_id") != manifest.get("cell_id"):
        raise ValueError("receipt cell_id differs from archived manifest")
    validate_evidence(manifest, receipt["evidence"], _sha256(manifest_bytes))
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    pgen = sub.add_parser("generate", help="validate candidate roster; optional explicit scratch write")
    pgen.add_argument("--research-root", required=True)
    pgen.add_argument("--output-dir", required=True)
    pgen.add_argument("--write", action="store_true", help="materialize under output-dir; absent means in-memory check only")
    pgen.set_defaults(func=generate)
    prec = sub.add_parser("seal-receipt", help="validate and seal one owner-collected cell evidence file")
    prec.add_argument("--manifest", required=True, type=Path)
    prec.add_argument("--evidence", required=True, type=Path)
    prec.add_argument("--output", required=True, type=Path)
    prec.set_defaults(func=lambda a: (seal_receipt(a.manifest, a.evidence, a.output) and 0))
    pver = sub.add_parser("verify-receipt", help="verify receipt envelope hash")
    pver.add_argument("--receipt", required=True, type=Path)
    pver.add_argument("--manifest", required=True, type=Path)
    pver.set_defaults(func=lambda a: (verify_receipt(a.receipt, a.manifest) and 0))
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
