#!/usr/bin/env python3
"""Fail-closed completion predicate for YARN science and keeper qualification."""
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
ROW_ID = "codex-ni-yarn-e1-mem-phase-r2-20261101"
CELLS = [
    ["E1", "A0", "low"], ["W", "A0", "low"],
    ["E1", "A1", "low"], ["W", "A1", "low"],
    ["E1", "A1", "high"], ["W", "A1", "high"],
]
QUAL_CELLS = [["E1", "A1", "high"], ["W", "A1", "high"]]
root = Path(os.environ.get("FILLER_RESULTS_DIR", HERE / "out"))


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        return None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_first_event(event: dict, image: str, nonce: str, request: dict,
                      capacity: dict, request_sha: str, recipe_sha: str) -> bool:
    first = event.get("first_request") if isinstance(event, dict) else None
    if not isinstance(first, dict):
        return False
    return (
        event.get("id") == ROW_ID and event.get("nonce") == nonce and event.get("image") == image and
        event.get("phase") == "normal" and event.get("native_first_event") is True and
        type(event.get("native_pid")) is int and event["native_pid"] > 0 and
        type(event.get("native_birth_ticks")) is int and event["native_birth_ticks"] > 0 and
        first.get("ok") is True and first.get("scope") == "TARGET_SCRATCH_SERVER" and
        first.get("manifest_sha256") == request_sha and
        first.get("production_recipe_sha256") == recipe_sha and
        type(first.get("n_ctx_total")) is int and first["n_ctx_total"] >= capacity["total_context"] and
        type(first.get("n_ctx_per_slot")) is int and first["n_ctx_per_slot"] >= capacity["per_slot_context"] and
        type(first.get("total_slots")) is int and first["total_slots"] >= capacity["parallel"] and
        (first["n_ctx_total"] >= first["n_ctx_per_slot"] * first["total_slots"]
         if capacity["kv_cache_mode"] == "split" else
         first["n_ctx_total"] >= first["n_ctx_per_slot"]) and
        first.get("prompt_tokens") == request["prompt_tokens_required"] and
        first.get("prompt_tokens") <= first["n_ctx_per_slot"] and
        first.get("kv_cache_mode") == capacity["kv_cache_mode"] and
        first.get("native_pid") == event.get("native_pid") and
        first.get("native_birth_ticks") == event.get("native_birth_ticks") and
        first.get("request") == {
            "arm": "A1", "cache_seed_stage": "400k", "stage": "500k",
            "needle": request["needle"], "messages_sha256": request["messages_sha256"],
            "rendered_sha256": request["rendered_sha256"]}
    )


def valid_qual_cell(cell, image, request, capacity, request_sha, recipe_sha, nonce):
    base = root / f"{image}-A1-high"
    complete_path = base / "complete.json"
    complete = read_json(complete_path)
    if not isinstance(complete, dict):
        return None
    for key, value in (("status", "COMPLETE"), ("row_id", ROW_ID), ("image", image),
                       ("arm", "A1"), ("level", "high"),
                       ("request_manifest_sha256", request_sha),
                       ("production_recipe_sha256", recipe_sha)):
        if complete.get(key) != value:
            return None
    for key in ("kfd_samples", "shim_log", "phase_attribution"):
        if not Path(complete.get(key, "")).is_file():
            return None
    report_path = Path(complete.get("report", ""))
    report = read_json(report_path)
    if (not isinstance(report, dict) or report.get("arm") != "A1" or
            report.get("inputs_manifest_sha256") != request["input_manifest_sha256"] or
            report.get("needle", {}).get("500k", {}).get("n") != 5):
        return None
    rows_path = Path(report.get("out", "")) / "needle_500k.jsonl"
    try:
        rows = [json.loads(line) for line in rows_path.read_text().splitlines() if line.strip()]
    except (OSError, ValueError):
        return None
    matches = [row for row in rows if row.get("id") == request["needle"]]
    if (len(matches) != 1 or matches[0].get("stage") != "500k" or
            matches[0].get("arm") != "A1" or
            matches[0].get("prompt_sha256") != request["messages_sha256"] or
            matches[0].get("http_ok") is not True):
        return None
    event_path = Path(complete.get("native_event_path", ""))
    event = read_json(event_path)
    if (not isinstance(event, dict) or complete.get("native_event_sha256") != sha(event_path) or
            not valid_first_event(event, image, nonce, request, capacity, request_sha, recipe_sha)):
        return None
    runtime = read_json(Path(complete.get("runtime_proof_path", "")))
    first = event["first_request"]
    if (not isinstance(runtime, dict) or runtime.get("image") != image or
            runtime.get("arm") != "A1" or runtime.get("level") != "high" or
            runtime.get("pid") != event.get("native_pid") or
            runtime.get("birth_ticks") != event.get("native_birth_ticks") or
            complete.get("native_pid") != event.get("native_pid") or
            complete.get("native_birth_ticks") != event.get("native_birth_ticks")):
        return None
    expected_prefix = Path(json.loads((HERE / "qualification/production_recipe.json").read_text())
                           ["images"][image]["binary"]["path"]).parent
    if not runtime.get("ggml_paths") or any(not str(Path(path)).startswith(str(expected_prefix))
                                             for path in runtime["ggml_paths"]):
        return None
    return (event["native_pid"], event["native_birth_ticks"])


result = read_json(root / "RESULT.json")
if not isinstance(result, dict):
    raise SystemExit(1)
if result.get("status") != "COMPLETE" or result.get("partial") is True or result.get("row_id") != ROW_ID:
    raise SystemExit(1)

if result.get("qualification_only") is True:
    if (result.get("steps") != QUAL_CELLS or type(result.get("work_unit_wall_s")) not in (int, float) or
            result["work_unit_wall_s"] <= 0 or not isinstance(result.get("nonce"), str) or
            not result["nonce"]):
        raise SystemExit(1)
    request_manifest = read_json(HERE / "qualification/request_manifest.json")
    recipe = read_json(HERE / "qualification/production_recipe.json")
    fixture = read_json(HERE / "qualification/qual_fixture.json")
    if not isinstance(request_manifest, dict) or not isinstance(recipe, dict) or not isinstance(fixture, dict):
        raise SystemExit(1)
    request_sha = sha(HERE / "qualification/request_manifest.json")
    recipe_sha = sha(HERE / "qualification/production_recipe.json")
    request = request_manifest.get("request_max", {})
    request["input_manifest_sha256"] = request_manifest.get("input_manifest", {}).get("sha256")
    capacity = fixture.get("required_capacity", {})
    if (request_manifest.get("id") != ROW_ID or
            result.get("request_manifest_sha256") != request_sha or
            result.get("production_recipe_sha256") != recipe_sha or
            result.get("work_unit") != recipe.get("qualification_work_unit") or
            result.get("native_first_event_sha256") != sha(root / "E1-A1-high/native-first-event.json")):
        raise SystemExit(1)
    identities = [valid_qual_cell(cell, cell[0], request, capacity, request_sha, recipe_sha, result["nonce"])
                  for cell in QUAL_CELLS]
    if any(identity is None for identity in identities) or identities[0] == identities[1]:
        raise SystemExit(1)
    raise SystemExit(0)

if (result.get("diagnostic") is not True or result.get("historical_comparison") is not True or
        result.get("request_manifest_sha256") != sha(HERE / "qualification/request_manifest.json") or
        result.get("production_recipe_sha256") != sha(HERE / "qualification/production_recipe.json") or
        result.get("steps") != CELLS):
    raise SystemExit(1)
if set(result.get("comparison", {})) != {"A0:128k", "A0:240k", "A1:128k", "A1:240k", "A1:400k", "A1:500k"}:
    raise SystemExit(1)
for image, arm, level in CELLS:
    complete = read_json(root / f"{image}-{arm}-{level}" / "complete.json")
    if (not isinstance(complete, dict) or complete.get("status") != "COMPLETE" or
            complete.get("image") != image or complete.get("arm") != arm or complete.get("level") != level):
        raise SystemExit(1)
    for key in ("kfd_samples", "shim_log", "phase_attribution"):
        if not Path(complete.get(key, "")).is_file():
            raise SystemExit(1)
raise SystemExit(0)
