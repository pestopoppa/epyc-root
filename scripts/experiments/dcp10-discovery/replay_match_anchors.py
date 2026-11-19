#!/usr/bin/env python3
"""Seal and compare the original and match-anchor DCP-10 lexical replays."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from statistics import mean

SCRIPT = Path(__file__).resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT.parent))

from diagnose_costs import SHARDS, cost_and_render, require
from pilot import (
    APP_REV,
    ARM,
    BUDGETS,
    LIMIT,
    MAX_FILES,
    check_worktree,
    digest,
    get_predictions,
    git,
    read,
    read_rows,
    write,
)

ROOT = SCRIPT.parents[3]
EVIDENCE = ROOT / "docs/research"
CANDIDATE = EVIDENCE / "dcp10-lexical-match-anchors-candidate-20261118.json"
DIAGNOSTIC = EVIDENCE / "dcp10-cost-diagnostic-20261118.json"
ORIGINALS = (
    "dcp10-lexical-pilot-results-20261118.json",
    "dcp10-lexical-shard2-results-20261118.json",
    "dcp10-lexical-shard3-results-20261118.json",
    "dcp10-packer-custody-review-20261118.json",
)


def check_hashes(root, hashes):
    for name, expected in hashes.items():
        require(digest(root / name) == expected, f"sealed bytes differ: {root / name}")


def snapshot(scratch, candidate):
    metadata = read(CANDIDATE)
    diagnostic = read(DIAGNOSTIC)
    patch = ROOT / metadata["patch"]
    require(metadata["base_revision"] == APP_REV == diagnostic["app_revision"], "wrong app revision")
    require(digest(patch) == metadata["patch_sha256"], "wrong patch bytes")

    patches = metadata["patched_files"]
    expected_diff = {f" M {path}" for path in patches}
    require(git(candidate, "rev-parse", "HEAD") == APP_REV
            and git(candidate, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
            and git(candidate, "rev-parse", "--show-toplevel") == str(candidate)
            and (candidate / ".git").is_file(), "candidate must be a detached linked worktree")
    status = git(candidate, "status", "--porcelain", "--untracked-files=all")
    require(set((" " + status).splitlines()) == expected_diff, "candidate changed paths differ")
    git(candidate, "apply", "--reverse", "--check", str(patch))

    shards = []
    previous = None
    for rank, witness in enumerate(diagnostic["shards"], 1):
        name = witness["shard"]
        require(name == SHARDS[rank - 1], "retained shard order differs")
        root = scratch / name
        packet, pilot = root / "packet", root / "pilot"
        request, run = read(packet / "request.json"), read(pilot / "run.json")
        request_hash = digest(packet / "request.json")
        source_hashes = request["source_hashes"]
        require(request_hash == run["request_sha256"] == witness["request_sha256"]
                and request.get("previous_request_sha256") == previous
                and request.get("selection_rank", 1) == rank
                and request["producer_sha256"] == witness["retained_pilot_producer_sha256"]
                and source_hashes == witness["source_hashes"], f"retained request differs: {name}")
        require((request["app_revision"], request["arm"], request["limit"], request["max_files"],
                 request["budgets"]) == (APP_REV, ARM, LIMIT, MAX_FILES, list(BUDGETS)),
                f"retained configuration differs: {name}")
        require(run["output_sha256"]["discovery.jsonl"] == witness["discovery_sha256"]
                and run["output_sha256"]["predictions.jsonl"] == witness["predictions_sha256"],
                f"retained outcomes differ: {name}")
        check_hashes(packet, request["packet_hashes"])
        check_hashes(pilot, run["output_sha256"])
        check_worktree(root / "app", APP_REV)
        check_hashes(root / "app", source_hashes | {p: v["base_sha256"] for p, v in patches.items()})
        check_hashes(candidate, source_hashes | {p: v["candidate_sha256"] for p, v in patches.items()})

        tasks = [{k: row[k] for k in ("task_id", "language", "base_commit")}
                 for row in request["selected"]]
        decisions = read(packet / "dispositions.json")["tasks"]
        require(len(tasks) == len(decisions) == len(witness["tasks"]) == 3
                and {row["task_id"]: row["disposition"] for row in decisions}
                == {row["task_id"]: "include" for row in tasks}, f"retained cohort differs: {name}")
        for task, prior_task in zip(tasks, witness["tasks"], strict=True):
            require(all(prior_task[key] == value for key, value in task.items()),
                    f"retained task differs: {task['task_id']}")
            check_worktree(root / "bases" / task["language"], task["base_commit"])
        shards.append({"shard": name, "request_sha256": request_hash,
                       "run_sha256": digest(pilot / "run.json"), "packet_hashes": request["packet_hashes"],
                       "outputs": run["output_sha256"], "source_hashes": source_hashes, "tasks": tasks})
        previous = request_hash

    require(len(shards) == len(SHARDS) and len({t["task_id"] for s in shards for t in s["tasks"]}) == 9,
            "expected nine unique retained tasks")
    require(digest(Path(sys.executable)) == diagnostic["python_executable_sha256"],
            "interpreter differs from original cost replay")
    return {
        "schema": "epyc.dcp10.lexical-match-anchors.replay-request.v1",
        "question": "On the same nine tasks, do explicit lexical anchors restore actual packed "
                    "gold spans when previews, ranking, full costs and codemap policy are held fixed?",
        "expected_effect": "Some Python slices may become packable. First matches are lexical "
                           "evidence, so overlap with gold is uncertain. C and C++ plans should match exactly.",
        "stop_rule": "Run exactly the retained nine tasks and three budgets per arm. Stop after "
                     "the comparison; any failed invariant invalidates that execution.",
        "comparison": ["raw hit scores and previews", "candidate modes and range/cost deltas",
                       "actual packed spans, estimates and rendered hashes", "gold file and line overlap"],
        "scope": "Fixed-cohort deterministic offline comparison with no sampling-error estimate.",
        "custody_limit": diagnostic["custody_limit"],
        "execution": {"app_revision": APP_REV, "arm": ARM, "limit": LIMIT, "max_files": MAX_FILES,
                      "budgets": list(BUDGETS), "python_version": sys.version.split()[0],
                      "python_executable_sha256": digest(Path(sys.executable)),
                      "patch_sha256": metadata["patch_sha256"], "patched_files": patches,
                      "producer_sha256": digest(SCRIPT),
                      "pilot_helpers_sha256": digest(SCRIPT.with_name("pilot.py")),
                      "cost_render_helpers_sha256": digest(SCRIPT.with_name("diagnose_costs.py"))},
        "evidence_sha256": {path.name: digest(path) for path in
                            (CANDIDATE, DIAGNOSTIC, *(EVIDENCE / name for name in ORIGINALS))},
        "shards": shards,
    }


def run_shard(scratch, runtime, name):
    import importlib

    sys.path.insert(0, str(runtime))
    request = read(scratch / name / "packet/request.json")
    for module_path in request["source_hashes"]:
        name_parts = Path(module_path).with_suffix("").parts
        module = importlib.import_module(".".join(name_parts))
        require(Path(module.__file__).resolve() == runtime / module_path,
                f"unexpected module origin: {module_path}")

    rows = []
    for task in request["selected"]:
        root = scratch / name / "bases" / task["language"]
        prediction, evidence = get_predictions(root, task["task_id"], task["query"])
        from src.context_discovery import discover_candidates

        hits = discover_candidates("", code_search_fn=lambda _q, _n, raw=evidence["raw_search"]: raw,
                                   limit=LIMIT, max_files=MAX_FILES)
        bodies = {hit.path: (root / hit.path).read_text(encoding="utf-8") for hit in hits}
        costs, rendered_hashes = cost_and_render(hits, bodies)
        require(len(costs) == MAX_FILES and not evidence["unreadable_hits"],
                f"incomplete candidates: {task['task_id']}")
        for cost, recorded in zip(costs, prediction["pack_candidates"], strict=True):
            require(cost.path == recorded["path"] and cost.cost_slices == recorded["cost_slices"],
                    f"standalone costing differs: {cost.path}")
        rows.append({"prediction": prediction, "evidence": evidence, "rendered_blocks": rendered_hashes})
    return rows


def line_set(spans):
    return {(path, line) for path, start, end in spans for line in range(start, end + 1)}


def overlap(files, spans, gold):
    gold_files = {span["file"] for span in gold}
    gold_lines = line_set((s["file"], s["start_line"], s["end_line"]) for s in gold)
    counts = {}
    metrics = {}
    for kind, predicted, expected in (("file", set(files), gold_files), ("line", line_set(spans), gold_lines)):
        tp, fp, fn = len(predicted & expected), len(predicted - expected), len(expected - predicted)
        counts[kind] = {"tp": tp, "fp": fp, "fn": fn}
        metrics.update({f"{kind}_precision": tp / (tp + fp) if tp + fp else 0,
                        f"{kind}_recall": tp / (tp + fn) if tp + fn else 0,
                        f"{kind}_f1": 2 * tp / (2 * tp + fp + fn) if tp else 0})
    return {"counts": counts, "metrics": metrics}


def summarize_plan(plan, gold):
    included = []
    for entry in plan["entries"]:
        require(entry["packer_mode"] == entry["rendered_mode"],
                f"render mode differs: {entry['path']}")
        if entry["rendered_mode"] != "excluded":
            included.append({k: entry[k] for k in ("path", "rendered_mode", "pred_spans",
                                                   "estimated_tokens", "content_sha256")})
    files = [entry["path"] for entry in included]
    require(files == plan["pred_files"] and 0 <= plan["estimated_packed_tokens"]
            == sum(entry["estimated_tokens"] for entry in included) <= plan["budget_tokens"],
            "rendered pack accounting differs")
    spans = [(e["path"], a, b) for e in included for a, b in e["pred_spans"]]
    return {"included": included, "estimated_packed_tokens": plan["estimated_packed_tokens"],
            "rendered_sha256": plan["rendered_sha256"], **overlap(files, spans, gold)}


def compare_task(task, baseline, patched, original_prediction, original_evidence, gold, scores):
    task_id = task["task_id"]
    old, new = baseline["prediction"], patched["prediction"]
    old_evidence, new_evidence = baseline["evidence"], patched["evidence"]
    require(old == original_prediction and old_evidence == original_evidence,
            f"baseline failed to reproduce retained outcomes: {task_id}")
    raw_new = new_evidence["raw_search"]
    previews = [{k: v for k, v in row.items() if k != "lexical_match_lines"} for row in raw_new]
    require(previews == old_evidence["raw_search"]
            and all("lexical_match_lines" in row for row in raw_new), f"search preview drift: {task_id}")
    unchanged = ("status", "arm", "task_id", "pred_files", "pred_spans")
    require(all(old[k] == new[k] for k in unchanged), f"discovery drift: {task_id}")
    anchors = {row["path"]: row["lexical_match_lines"] for row in raw_new}
    changes = []
    for before, after in zip(old["pack_candidates"], new["pack_candidates"], strict=True):
        path = before["path"]
        fixed = ("path", "priority", "cost_full", "cost_codemap", "total_lines")
        require(all(before[k] == after[k] for k in fixed), f"fixed candidate data drift: {task_id}/{path}")
        original_blocks = baseline["rendered_blocks"][path]
        patched_blocks = patched["rendered_blocks"][path]
        require(original_blocks == {mode: block for mode, block in patched_blocks.items() if mode != "slices"},
                f"full or codemap rendered text drift: {task_id}/{path}")
        if before != after:
            require(path.endswith(".py") and after["desired_mode"] == "slices" and "slices" in patched_blocks,
                    f"unexpected candidate change: {task_id}/{path}")
            keys = ("cost_slices", "desired_mode", "line_ranges")
            changes.append({"path": path, "gold_file": any(s["file"] == path for s in gold),
                            "lexical_match_lines": anchors[path], "cost_full": before["cost_full"],
                            "cost_codemap": before["cost_codemap"], "slice_block_sha256": patched_blocks["slices"],
                            "original": {k: before[k] for k in keys}, "patched": {k: after[k] for k in keys}})
    budgets = {}
    for budget, before, after in zip(BUDGETS, old_evidence["pack_plans"], new_evidence["pack_plans"], strict=True):
        require(before["budget_tokens"] == after["budget_tokens"] == budget, f"budget drift: {task_id}")
        if task["language"] != "python":
            require(before == after, f"non-Python plan drift: {task_id}/{budget}")
        original = summarize_plan(before, gold)
        candidate = summarize_plan(after, gold)
        require(all(original[k] == scores[budget][k] for k in ("counts", "metrics")),
                f"original score cross-check differs: {task_id}/{budget}")
        budgets[str(budget)] = {"original": original, "patched": candidate}
    return {**task, "candidate_count": len(old["pack_candidates"]), "candidate_changes": changes,
            "budgets": budgets}


def summarize(tasks):
    totals = {}
    for budget in map(str, BUDGETS):
        totals[budget] = {}
        for arm in ("original", "patched"):
            rows = [task["budgets"][budget][arm] for task in tasks]
            totals[budget][arm] = {
                "included_files": sum(len(row["included"]) for row in rows),
                "included_gold_files": sum(row["counts"]["file"]["tp"] for row in rows),
                "included_gold_lines": sum(row["counts"]["line"]["tp"] for row in rows),
                "estimated_packed_tokens": sum(row["estimated_packed_tokens"] for row in rows),
                "macro_metrics": {k: mean(row["metrics"][k] for row in rows) for k in rows[0]["metrics"]},
            }
        totals[budget]["changed_rendered_prompts"] = sum(
            task["budgets"][budget]["original"]["rendered_sha256"]
            != task["budgets"][budget]["patched"]["rendered_sha256"] for task in tasks
        )
    return {"tasks": len(tasks), "candidates_per_arm": sum(row["candidate_count"] for row in tasks),
            "plans_per_arm": len(tasks) * len(BUDGETS),
            "changed_candidates": sum(len(task["candidate_changes"]) for task in tasks),
            "budgets": totals}


def launch(scratch, runtime, name):
    environment = {**os.environ, "ORCHESTRATOR_MOCK_MODE": "1", "ORCHESTRATOR_REGISTRY_MODE": "lean"}
    return json.loads(subprocess.check_output(
        [sys.executable, "-I", "-B", str(SCRIPT), str(scratch), "worker", str(runtime), name],
        cwd=runtime, env=environment, timeout=90,
    ))


def replay(scratch, candidate, request_path, seal):
    require(digest(request_path) == seal, "prospective request hash differs")
    request = read(request_path)
    require(snapshot(scratch, candidate) == request, "replay inputs differ from the prospective request")
    tasks = []
    for shard in request["shards"]:
        name = shard["shard"]
        packet, pilot = scratch / name / "packet", scratch / name / "pilot"
        original_predictions = read_rows(pilot / "predictions.jsonl")
        original_discovery = read_rows(pilot / "discovery.jsonl")
        gold = {row["instance_id"]: row["gold_context"] for row in read_rows(packet / "tasks.jsonl")}
        scores = {scope["budget_tokens"]: {row["task_id"]: row for row in scope["per_task"]}
                  for scope in read(pilot / "scored-output.json")["arms"][0]["scopes"]}
        baseline = launch(scratch, scratch / name / "app", name)
        patched = launch(scratch, candidate, name)
        for task, before, after, prediction, evidence in zip(
            shard["tasks"], baseline, patched, original_predictions, original_discovery, strict=True,
        ):
            task_id = task["task_id"]
            require(task_id == prediction["task_id"] == evidence["task_id"], "retained task order drift")
            tasks.append(compare_task(task, before, after, prediction, evidence, gold[task_id],
                                      {budget: scores[budget][task_id] for budget in BUDGETS}))
    require(snapshot(scratch, candidate) == request and digest(request_path) == seal,
            "sealed inputs changed during replay")
    return {"schema": "epyc.dcp10.lexical-match-anchors.replay.v1", "request_sha256": seal,
            "scope": request["scope"], "custody_limit": request["custody_limit"],
            "summary": summarize(tasks), "tasks": tasks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch", type=Path, help="parent of the three retained shard directories")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("seal", "run"):
        sub = commands.add_parser(command)
        sub.add_argument("candidate", type=Path)
        sub.add_argument("request", type=Path)
        if command == "run":
            sub.add_argument("--request-sha", required=True)
            sub.add_argument("--output", required=True, type=Path)
    worker = commands.add_parser("worker", help=argparse.SUPPRESS)
    worker.add_argument("runtime", type=Path)
    worker.add_argument("shard", choices=SHARDS)
    args = parser.parse_args()
    scratch = args.scratch.resolve(strict=True)
    if args.command == "worker":
        print(json.dumps(run_shard(scratch, args.runtime, args.shard), allow_nan=False))
        return

    candidate = args.candidate.resolve(strict=True)
    protected = [scratch / name for name in SHARDS]
    paths = [candidate, args.request.resolve()]
    if args.command == "run":
        paths.append(args.output.resolve())
    require(all(path.is_relative_to(scratch) and not any(path.is_relative_to(root) for root in protected)
                for path in paths), "candidate and output paths must be scratch outside retained shards")
    if args.command == "seal":
        write(args.request, snapshot(scratch, candidate))
        print(digest(args.request))
    else:
        report = replay(scratch, candidate, args.request, args.request_sha)
        write(args.output, report)


if __name__ == "__main__":
    main()
