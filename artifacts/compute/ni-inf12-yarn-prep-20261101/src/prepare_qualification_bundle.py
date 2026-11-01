#!/usr/bin/env python3
"""Pin YARN r2 request/recipe metadata without creating a READY or calibration claim."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "qualification"
MODEL = Path("/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf")
TEMPLATE = Path("/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja")
IMAGES = {
    "E1": ("9a3f1392a", Path("/mnt/raid0/llm/kernels/builds/gpu-20261004-9a3f1392a/bin")),
    "W": ("b0ba1d427", Path("/mnt/raid0/llm/kernels/builds/gpu-20261004-b0ba1d427/bin")),
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def edge_pin(path: Path) -> dict:
    size = path.stat().st_size
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        digest.update(stream.read(64 * 2**20))
        stream.seek(max(0, size - 64 * 2**20))
        digest.update(stream.read(64 * 2**20))
    digest.update(str(size).encode())
    return {"path": str(path), "size_bytes": size, "edge_sha256": digest.hexdigest()}


def main() -> int:
    metadata = json.loads((OUT / "REQUEST-METADATA.json").read_text())
    prompt = metadata["prompt"]
    prompt_max = max(x["token_count"] for x in metadata["planned_500k_prompts"])
    if prompt["token_count"] != prompt_max or not metadata["identity_audit"]["request_bytes_match_historical"]:
        raise SystemExit("metadata maximum or exact message/history join failed; refusing qualification pins")
    images = {}
    for name, (commit, bindir) in IMAGES.items():
        binary = bindir / "llama-server"
        dsos = sorted(path for path in bindir.glob("libggml*.so*") if path.is_file() and not path.is_symlink())
        if not binary.is_file() or len(dsos) != 4:
            raise SystemExit(f"incomplete pinned image: {name}")
        images[name] = {
            "source_commit": commit,
            "binary": {"path": str(binary), "sha256": sha(binary)},
            "ggml_dsos": [{"path": str(path), "sha256": sha(path)} for path in dsos],
            "argv": [str(binary), "-m", str(MODEL), "--host", "127.0.0.1", "--port", 18437,
                     "-np", 1, "-t", 8, "-ub", 2048, "--flash-attn", "on", "--jinja",
                     "-ctk", "q8_0", "-ctv", "q8_0", "--no-kv-unified", "--no-mmap",
                     "-ngl", "all", "--cache-ram", 0, "--chat-template-file", str(TEMPLATE),
                     "--device", "ROCm0", "--slot-save-path", "<cell>/slots", "--verbosity", 4,
                     "-c", 524288, "--rope-scaling", "yarn", "--rope-scale", 2,
                     "--yarn-orig-ctx", 262144, "--override-kv",
                     "qwen35.context_length=int:524288,qwen35.rope.scaling.type=str:yarn,"
                     "qwen35.rope.scaling.factor=float:2,qwen35.rope.scaling.original_context_length=int:262144"],
        }
    recipe = {
        "schema": "epyc.yarn-e1-production-recipe.v1",
        "status": "candidate-pinned-unqualified",
        "kv_cache_mode": "split",
        "images": images,
        "model": edge_pin(MODEL),
        "template": {"path": str(TEMPLATE), "sha256": sha(TEMPLATE)},
        "backend": {"device": "ROCm0", "ngl": "all", "flash_attention": "on",
                    "kv_types": ["q8_0", "q8_0"], "shim": str(HERE / "helper/libhipmalloc_trace.so"),
                    "shim_sha256": sha(HERE / "helper/libhipmalloc_trace.so"), "omp_threads": 1},
        "request": {"arm": "A1", "seed_stage": "400k", "first_request_stage": "500k",
                    "needle": prompt["needle"], "messages_sha256": prompt["messages_sha256"],
                    "rendered_prompt_sha256": prompt["rendered_sha256"],
                    "prompt_tokens_required": prompt["token_count"],
                    "template_sha256": sha(TEMPLATE)},
        "qualification_work_unit": f"one paired E1/W A1/high comparison: each image runs 400k cache seed then exact 500k {prompt['needle']} request",
        "kv_mode_basis": "explicit --no-kv-unified; native qualification must still prove kv_unified=false",
        "calibration": {"status": "missing-same-image-complete-work-unit-measurement",
                        "qualification_is_not_calibration": True},
    }
    recipe_path = OUT / "production_recipe.json"
    recipe_path.write_text(json.dumps(recipe, sort_keys=True, indent=2) + "\n")
    recipe_sha = sha(recipe_path)
    request = {
        "schema": "epyc.yarn-e1-request-manifest.v1",
        "id": "codex-ni-yarn-e1-mem-phase-r2-20261101",
        "science_cells": [["E1", "A0", "low"], ["W", "A0", "low"],
                          ["E1", "A1", "low"], ["W", "A1", "low"],
                          ["E1", "A1", "high"], ["W", "A1", "high"]],
        "science_cells_mutated": False,
        "decision_rule": {"metric": "own-PID KFD VRAM plus hipMalloc-shim phase series",
                          "direction": "lower VRAM is better", "historical_excess_gib": 15,
                          "e1_commit": IMAGES["E1"][0], "w_commit": IMAGES["W"][0],
                          "quality_or_champion_verdict": False},
        "input_manifest": {"path": str(HERE / "inputs/manifest.json"), "sha256": sha(HERE / "inputs/manifest.json")},
        "runner": {"path": str(HERE / "yarn_needle.py"), "sha256": sha(HERE / "yarn_needle.py")},
        "template": recipe["template"], "model": recipe["model"],
        "request_max": {"stage": "500k", "arm": "A1", "needle": prompt["needle"],
                        "messages_sha256": prompt["messages_sha256"],
                        "rendered_sha256": prompt["rendered_sha256"],
                        "prompt_tokens_required": prompt["token_count"]},
        "production_recipe": {"path": str(recipe_path), "sha256": recipe_sha},
        "metadata_only_tokenizer": {"path": str(OUT / "REQUEST-METADATA.json"),
                                    "sha256": sha(OUT / "REQUEST-METADATA.json"),
                                    "qualification_claim": False},
    }
    request_path = OUT / "request_manifest.json"
    request_path.write_text(json.dumps(request, sort_keys=True, indent=2) + "\n")
    request_sha = sha(request_path)
    fixture = {
        "schema": "epyc.yarn-e1-qual-fixture.v1", "items": 2,
        "qualification_claim": "keeper-issued native proof required; this fixture alone is not qualification",
        "normal_and_cutoff": {"same_entry": True, "work_unit": recipe["qualification_work_unit"],
                              "cutoff_after_native_first_event": True},
        "request": {"stage": "500k", "arm": "A1", "needle": prompt["needle"],
                    "messages_sha256": prompt["messages_sha256"],
                    "rendered_sha256": prompt["rendered_sha256"],
                    "prompt_tokens_required": prompt["token_count"],
                    "request_manifest_sha256": request_sha,
                    "production_recipe_sha256": recipe_sha},
        "required_capacity": {"total_context": 524288, "per_slot_context": 524288,
                              "parallel": 1, "kv_cache_mode": "split"},
        "science_cells": request["science_cells"],
    }
    fixture_path = OUT / "qual_fixture.json"
    fixture_path.write_text(json.dumps(fixture, sort_keys=True, indent=2) + "\n")
    calibration = {
        "schema": "epyc.yarn-work-unit-calibration.v1",
        "status": "MISSING", "reason": "no accepted same-image complete A1/high work-unit timing exists",
        "work_unit": recipe["qualification_work_unit"], "production_threads": 8,
        "production_recipe_sha256": recipe_sha, "observed_wall_s_per_unit": None,
        "planned_comparison_pairs": 3,
        "conservative_bound": {
            "status": "UNPROVEN",
            "requirement": "measured paired high-unit wall time must conservatively bound all three comparison pairs including both image loads, cache seeds, stage requests, probes, analysis, and cleanup",
            "items_times_wall_s_per_unit_must_fit_declared_window": True,
        },
        "historical_planning_only": {
            "image": "v10 gpu-20260921-ffc1bac82; not a calibration for this recipe",
            "e1_high_requests_and_local_probes_s": 2854.558,
            "paired_high_unit_lower_bound_s_before_loads": 5709.116,
            "three_pair_proxy_s_before_loads": 17127.348,
            "status": "planning estimate only; cannot qualify or establish current feasibility",
        },
        "evidence": [], "qualification_run_is_not_eligible": True,
        "ready_manifest_must_remain_unpublished": True,
    }
    (OUT / "WORK-UNIT-CALIBRATION-REQUIRED.json").write_text(json.dumps(calibration, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"request_manifest_sha256": request_sha, "production_recipe_sha256": recipe_sha,
                      "qual_fixture_sha256": sha(fixture_path), "prompt_tokens_required": prompt["token_count"],
                      "calibration_status": "MISSING; no READY"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
