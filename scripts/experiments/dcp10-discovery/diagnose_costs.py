#!/usr/bin/env python3
"""Replay candidate costing and rendering for the three retained DCP-10 lexical shards."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

from pilot import APP_REV, ARM, BUDGETS, LIMIT, MAX_FILES, check_worktree, digest, git, read, read_rows

SHARDS = ("dcp10", "dcp10-shard2", "dcp10-shard3")


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def intervals(ranges):
    return [[span.start, span.end] for span in ranges]


def explain_slice(path, source, hits, planned, costs_equal):
    """Explain the pinned slicer's result, including which hit lines lack statements."""
    if not hits:
        return {"reason": "missing_hit_ranges"}
    if not path.endswith(".py"):
        return {"reason": "non_python"}
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError, ValueError) as error:
        return {"reason": "ast_parse_failure", "error_type": type(error).__name__,
                "error_line": getattr(error, "lineno", None)}
    line_count = len(source.splitlines())
    if planned:
        if planned == [[1, line_count]]:
            return {"reason": "whole_file_ast_span"}
        return {"reason": "ast_slice_equal_estimate" if costs_equal else "ast_slice_distinct_estimate"}
    if not line_count or any(start < 1 or end > line_count or end < start for start, end in hits):
        return {"reason": "hit_range_out_of_bounds"}
    statement_spans = [
        (min([node.lineno, *(decorator.lineno for decorator in getattr(node, "decorator_list", ()))]),
         node.end_lineno or node.lineno)
        for node in ast.walk(tree) if isinstance(node, ast.stmt) and not isinstance(node, ast.ClassDef)
    ]
    hit_lines = sorted({line for start, end in hits for line in range(start, end + 1)})
    uncovered = [line for line in hit_lines if not any(a <= line <= b for a, b in statement_spans)]
    require(uncovered, f"slice rejection has no known cause for {path}")
    return {"reason": "unresolved_ast_hit_lines", "hit_lines_without_ast_statement": uncovered}


def cost_and_render(hits, bodies):
    from src.context_assembly import BundleEntry, ContextBundle, InclusionMode, conservative_char_estimator
    from src.context_discovery import cost_candidates, render_bundle

    def trace_estimator(text):
        separator = text.index("\n")
        cost_texts[text[:separator]] = text
        return conservative_char_estimator(text)

    cost_texts = {}
    candidates = cost_candidates(hits, file_reader_fn=bodies.__getitem__, token_estimator=trace_estimator)
    checks = {}
    for candidate in candidates:
        rendered_modes = {}
        for mode in (InclusionMode.FULL, InclusionMode.SLICES, InclusionMode.CODEMAP_ONLY):
            cost_text = cost_texts.get(f"### {candidate.path} ({mode})")
            if cost_text is None:
                require(candidate.cost_for(mode) == candidate.cost_full,
                        f"fallback estimate differs from full: {candidate.path}/{mode}")
                continue
            entry = BundleEntry(path=candidate.path, mode=mode, source=candidate.source,
                                line_ranges=candidate.line_ranges, content_sha256=candidate.content_sha256,
                                render_ranges_verbatim=candidate.render_ranges_verbatim)
            text = render_bundle(ContextBundle(budget=0, entries=[entry]), file_reader_fn=bodies.__getitem__)
            require(entry.mode == mode and text + "\n\n" == cost_text,
                    f"cost and render texts differ: {candidate.path}/{mode}")
            rendered_modes[mode] = sha256(text.encode()).hexdigest()
        checks[candidate.path] = rendered_modes
    return candidates, checks


def replay_task(root, task, gold, prediction, discovery):
    from src.context_assembly import InclusionMode, _ladder_from, pack_to_budget
    from src.context_discovery import discover_candidates, render_bundle

    task_id = task["task_id"]
    check_worktree(root, task["base_commit"])
    require(prediction["status"] == "ok" and prediction["arm"] == ARM
            and not discovery["unreadable_hits"], f"unexpected discovery status: {task_id}")
    hits = discover_candidates("", code_search_fn=lambda _query, _limit: json.dumps(discovery["raw_search"]),
                               limit=LIMIT, max_files=MAX_FILES)
    require([hit.path for hit in hits] == prediction["pred_files"] and len(hits) == MAX_FILES,
            f"discovered files differ: {task_id}")
    require([{"file": hit.path, "start_line": r.start, "end_line": r.end}
             for hit in hits for r in hit.line_ranges] == prediction["pred_spans"],
            f"discovered spans differ: {task_id}")
    tracked = set(git(root, "ls-tree", "-rz", "--name-only", "HEAD").split("\0"))
    bodies = {}
    for hit in hits:
        source_path = (root / hit.path).resolve(strict=True)
        require(hit.path in tracked and source_path.is_relative_to(root), f"unbound source: {hit.path}")
        bodies[hit.path] = source_path.read_text(encoding="utf-8")
    candidates, hashes = cost_and_render(hits, bodies)

    expected_costs = []
    details = {}
    for hit, candidate in zip(hits, candidates, strict=True):
        require(hit.path == candidate.path, f"unexpected candidate order: {task_id}")
        path = candidate.path
        ranges = intervals(candidate.line_ranges)
        expected_costs.append({
            "path": path, "priority": candidate.priority, "cost_full": candidate.cost_full,
            "cost_slices": candidate.cost_slices, "cost_codemap": candidate.cost_codemap,
            "desired_mode": candidate.desired_mode, "total_lines": len(bodies[path].splitlines()),
            "line_ranges": ranges,
        })
        renderable = hashes[path]
        equal_cost = candidate.cost_full == candidate.cost_slices
        details[path] = {
            **expected_costs[-1],
            "source_text_sha256": candidate.content_sha256,
            "gold_file": any(span["file"] == path for span in gold),
            "hit_ranges": intervals(hit.line_ranges),
            "ast_ranges": ranges if candidate.render_ranges_verbatim else [],
            "full_slice_estimates_equal": equal_cost,
            "slice_provenance": explain_slice(path, bodies[path], intervals(hit.line_ranges),
                                              ranges if candidate.render_ranges_verbatim else [], equal_cost),
            "rendered_block_sha256_by_mode": renderable,
            "codemap_blocked_for_hit_ranges": bool(candidate.line_ranges),
            "budget_eligibility": {},
        }
    require(expected_costs == prediction["pack_candidates"], f"retained candidate costs differ: {task_id}")
    require([plan["budget_tokens"] for plan in discovery["pack_plans"]] == list(BUDGETS),
            f"retained budgets differ: {task_id}")

    budget_checks = {}
    by_path = {candidate.path: candidate for candidate in candidates}
    for plan in discovery["pack_plans"]:
        budget = plan["budget_tokens"]
        key = str(budget)
        bundle = pack_to_budget(candidates, budget)
        original_modes = {entry.path: entry.mode for entry in bundle.entries}
        rendered = render_bundle(bundle, file_reader_fn=bodies.__getitem__)
        rendered_hash = sha256(rendered.encode()).hexdigest()
        remaining = budget
        predicted_files = []
        gold_hits = []
        require(len(plan["entries"]) == len(candidates), f"retained entry count differs: {task_id}/{budget}")
        for entry, recorded in zip(bundle.entries, plan["entries"], strict=True):
            path = entry.path
            candidate = by_path[path]
            detail = details[path]
            mode = original_modes[path]
            spans = []
            if mode == InclusionMode.FULL and detail["total_lines"]:
                spans = [[1, detail["total_lines"]]]
            elif mode == InclusionMode.SLICES:
                spans = intervals(entry.line_ranges)
            observed = {"path": path, "packer_mode": mode, "rendered_mode": entry.mode,
                        "pred_spans": spans, "estimated_tokens": entry.estimated_tokens,
                        "content_sha256": entry.content_sha256, "reason": entry.reason_downgraded_or_excluded}
            require(observed == recorded, f"retained entry differs: {task_id}/{path}/{budget}")
            ladder = [choice for choice in _ladder_from(candidate.desired_mode)
                      if choice != InclusionMode.CODEMAP_ONLY or not candidate.line_ranges]
            fits_remaining = [choice for choice in ladder if candidate.cost_for(choice) <= remaining]
            require(mode == next(iter(fits_remaining), InclusionMode.EXCLUDED),
                    f"eligibility differs from selected mode: {task_id}/{path}/{budget}")
            detail["budget_eligibility"][key] = {
                "remaining_before": remaining,
                "packer_modes_fitting_total": [choice for choice in ladder if candidate.cost_for(choice) <= budget],
                "packer_modes_fitting_remaining": fits_remaining,
                "codemap_estimate_fits_remaining": candidate.cost_codemap <= remaining,
                "packer_mode": mode, "rendered_mode": entry.mode,
            }
            remaining -= entry.estimated_tokens
            if mode != InclusionMode.EXCLUDED:
                predicted_files.append(path)
                if detail["gold_file"]:
                    gold_hits.append(path)
        require(predicted_files == plan["pred_files"] and rendered_hash == plan["rendered_sha256"]
                and 0 <= budget - remaining == plan["estimated_packed_tokens"] <= budget,
                f"retained plan differs: {task_id}/{budget}")
        budget_checks[key] = {"rendered_sha256": rendered_hash, "included_files": predicted_files,
                              "included_gold_files": gold_hits, "estimated_packed_tokens": budget - remaining}

    return {"task_id": task_id, "language": task["language"], "base_commit": task["base_commit"],
            "repo_url": task["repo_url"], "budgets": budget_checks, "candidates": list(details.values())}


def load_shard(root, runtime, prior_request, rank):
    packet, run_dir = root / "packet", root / "pilot"
    request_hash = digest(packet / "request.json")
    request = read(packet / "request.json")
    run = read(run_dir / "run.json")
    require(run["request_sha256"] == request_hash and request.get("previous_request_sha256") == prior_request
            and request.get("selection_rank", 1) == rank, f"retained request chain differs: {root}")
    require((request["app_revision"], request["arm"], request["limit"], request["max_files"], request["budgets"])
            == (APP_REV, ARM, LIMIT, MAX_FILES, list(BUDGETS)), f"retained configuration differs: {root}")
    check_worktree(root / "app", APP_REV)
    for base, hashes in ((packet, request["packet_hashes"]), (run_dir, run["output_sha256"]),
                         (runtime, request["source_hashes"]), (root / "app", request["source_hashes"])):
        for filename, expected in hashes.items():
            require(digest(base / filename) == expected, f"sealed bytes differ: {base / filename}")
    gold = {row["instance_id"]: row["gold_context"] for row in read_rows(packet / "tasks.jsonl")}
    predictions = read_rows(run_dir / "predictions.jsonl")
    discovery = read_rows(run_dir / "discovery.jsonl")
    selected = request["selected"]
    require(len(selected) == len(predictions) == len(discovery) == len(gold) == 3,
            f"expected exactly three retained tasks: {root}")
    tasks = []
    for task, prediction, evidence in zip(selected, predictions, discovery, strict=True):
        task_id = task["task_id"]
        require(task_id == prediction["task_id"] == evidence["task_id"], f"task identity differs: {root}")
        tasks.append(replay_task((root / "bases" / task["language"]).resolve(), task, gold[task_id],
                                 prediction, evidence))
    return {"shard": root.name, "request_sha256": request_hash, "source_hashes": request["source_hashes"],
            "retained_pilot_producer_sha256": request["producer_sha256"],
            "predictions_sha256": run["output_sha256"]["predictions.jsonl"],
            "discovery_sha256": run["output_sha256"]["discovery.jsonl"], "tasks": tasks}


def summarize(tasks):
    candidates = [candidate for task in tasks for candidate in task["candidates"]]
    budget_totals = {}
    for budget in map(str, BUDGETS):
        eligibility = [(candidate, candidate["budget_eligibility"][budget]) for candidate in candidates]
        budget_totals[budget] = {
            "included_files": sum(len(task["budgets"][budget]["included_files"]) for task in tasks),
            "included_gold_files": sum(len(task["budgets"][budget]["included_gold_files"]) for task in tasks),
            "gold_files_with_no_mode_fitting_total": sum(
                candidate["gold_file"] and not row["packer_modes_fitting_total"] for candidate, row in eligibility),
            "candidates_excluded_after_earlier_consumption": sum(
                bool(row["packer_modes_fitting_total"]) and not row["packer_modes_fitting_remaining"]
                for _, row in eligibility),
            "excluded_candidates_with_blocked_fitting_codemap": sum(
                candidate["codemap_blocked_for_hit_ranges"] and row["codemap_estimate_fits_remaining"]
                and row["packer_mode"] == "excluded" for candidate, row in eligibility),
        }
    return {
        "tasks": len(tasks), "candidates": len(candidates),
        "replayed_plans": sum(len(task["budgets"]) for task in tasks),
        "replayed_entries": sum(len(candidate["budget_eligibility"]) for candidate in candidates),
        "slice_provenance_counts": dict(Counter(c["slice_provenance"]["reason"] for c in candidates)),
        "rendered_block_checks_by_mode": dict(Counter(mode for c in candidates
                                                      for mode in c["rendered_block_sha256_by_mode"])),
        "equal_full_slice_estimates": sum(c["full_slice_estimates_equal"] for c in candidates),
        "discovered_gold_files": sum(c["gold_file"] for c in candidates),
        "budget_totals": budget_totals,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch_parent", type=Path, help="directory containing the three retained shard directories")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    scratch = args.scratch_parent.resolve(strict=True)
    runtime = scratch / SHARDS[0] / "app"
    if any(args.output.resolve().is_relative_to(scratch / name) for name in SHARDS):
        parser.error("output must be outside the retained shard directories")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(runtime))
    shards = []
    for rank, name in enumerate(SHARDS, start=1):
        prior = shards[-1]["request_sha256"] if shards else None
        shards.append(load_shard(scratch / name, runtime, prior, rank))
    tasks = [task for shard in shards for task in shard["tasks"]]
    report = {
        "schema": "epyc.dcp10.cost-provenance.diagnostic.v1",
        "scope": "Offline replay of retained lexical hits and sealed local evidence. No score receipt or inference.",
        "custody_limit": "Original writable-ancestor capture refusal and trusted packer identity mismatch still apply.",
        "producer_sha256": digest(Path(__file__)),
        "pilot_helpers_sha256": digest(Path(__file__).with_name("pilot.py")),
        "app_revision": APP_REV,
        "python_version": ".".join(str(item) for item in sys.version_info[:3]),
        "python_executable_sha256": digest(Path(sys.executable)),
        "summary": summarize(tasks),
        "shards": shards,
    }
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")


if __name__ == "__main__":
    main()
