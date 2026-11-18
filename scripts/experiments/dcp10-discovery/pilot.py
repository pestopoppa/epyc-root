#!/usr/bin/env python3
"""Prepare and run the finite DCP-10 task-root lexical pilot."""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import monotonic

HF_REV = "c2855792b006af41c67202d33883fb9d46362853"
UPSTREAM_REV = "1436c28a8eb95496da4ea69ad458b9f8a8eb7d61"
APP_REV = "072d1583b3ead7456731946cd4e4595da6a9877f"
DATASETS = {
    "full": ("full.parquet", "2f56535bdc73eb8a68bf4ebb49789d8e9cd4f219ea60df6290b85278aee61ca8", 1136),
    "lite": ("contextbench_verified.parquet", "e9dcfd504cbfb849ac815a79040c793d0d92f94eecc9b5a4ee3e1445a2f8a791", 500),
}
STRATA = {"python": "lite", "c": "full", "cpp": "full"}
ARM = "task-root-lexical"
LIMIT = 20
MAX_FILES = 8
BUDGETS = (2000, 4000, 8000)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def write(path, value, *, jsonl=False):
    with path.open("x", encoding="utf-8") as out:
        if jsonl:
            out.writelines(encode(item) for item in value)
        else:
            out.write(encode(value))
    path.chmod(0o400)


def read(path):
    return json.loads(path.read_bytes())


def read_rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, timeout=30,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0"},
    ).strip()


def check_worktree(root, revision):
    if git(root, "rev-parse", "HEAD") != revision:
        raise ValueError(f"wrong checkout revision: {root}")
    if git(root, "rev-parse", "--show-toplevel") != str(root):
        raise ValueError(f"wrong checkout root: {root}")
    if git(root, "rev-parse", "--abbrev-ref", "HEAD") != "HEAD" or not (root / ".git").is_file():
        raise ValueError(f"expected detached linked worktree: {root}")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(f"checkout has local modifications: {root}")


def check_read_scope(root):
    for path in root.rglob("*"):
        if path.is_symlink() and not path.resolve().is_relative_to(root):
            raise ValueError(f"checkout contains a symlink escaping the root: {path.relative_to(root)}")


def prepare(work):
    import pyarrow.parquet as pq
    from src.contextbench_score import ScoringInputError, normalize_relative_path

    upstream = work / "source/upstream"
    check_worktree(upstream, UPSTREAM_REV)
    check_worktree(work / "app", APP_REV)
    datasets = {}
    for name, (leaf, expected, count) in DATASETS.items():
        path = work / "source" / f"{name}.parquet"
        if digest(path) != expected or digest(upstream / "data" / leaf) != expected:
            raise ValueError(f"dataset bytes differ from pinned releases: {name}")
        rows = pq.read_table(path, columns=[
            "instance_id", "repo", "repo_url", "language", "base_commit",
            "gold_context", "problem_statement",
        ]).to_pylist()
        if len(rows) != count or len({row["instance_id"] for row in rows}) != count:
            raise ValueError(f"dataset ID count differs: {name}")
        datasets[name] = rows

    def raw_gold(row):
        return json.loads(row["gold_context"])

    def scratch_paths(row):
        return {item["file"] for item in raw_gold(row)
                if item["file"].startswith("/workspace/") and item["file"].count("/") == 2}

    full = datasets["full"]
    full_by_id = {r["instance_id"]: r for r in full}
    if any(full_by_id.get(r["instance_id"]) != r for r in datasets["lite"]):
        raise ValueError("Lite pilot inputs differ from their full-release rows")
    audit = {
        "empty_gold_ids": sorted(r["instance_id"] for r in full if not raw_gold(r)),
        "workspace_bare_paths_by_id": {
            r["instance_id"]: sorted(scratch_paths(r)) for r in full if scratch_paths(r)
        },
        "reported_unresolvable_tasks": 88,
        "reported_unresolvable_count_reverified": False,
    }
    selected, tasks, decisions = [], [], []
    for lang, dataset in STRATA.items():
        rows = [r for r in datasets[dataset] if r["language"] == lang]
        row = min(rows, key=lambda r: sha256(r["instance_id"].encode()).hexdigest())
        root = work / "bases" / lang
        check_worktree(root, row["base_commit"])
        repo = row["repo"]
        prefixes = (f"/workspace/{repo.split('/')[-1]}/", f"/workspace/{repo.replace('/', '__')}__0.1/")
        spans, absolute_unresolved = [], []
        bare = scratch_paths(row)
        for item in raw_gold(row):
            original = item["file"]
            path = original
            for prefix in prefixes:
                if path.startswith(prefix):
                    path = path.removeprefix(prefix)
                    break
            if original in bare:
                path = path.removeprefix("/workspace/")
            try:
                path = normalize_relative_path(path)
            except ScoringInputError:
                absolute_unresolved.append(original)
            spans.append({"file": path, "start_line": item["start_line"], "end_line": item["end_line"]})
        tracked = set(git(root, "ls-tree", "-rz", "--name-only", "HEAD").split("\0"))
        missing = sorted({item["file"] for item in spans} - tracked)
        task_id = row["instance_id"]
        disposition, paths = "include", []
        if not spans:
            disposition = "exclude_empty_gold"
        elif absolute_unresolved:
            disposition = "exclude_unresolvable_gold"
        elif bare:
            disposition = "exclude_scratch_gold"
            paths = sorted(normalize_relative_path(p.removeprefix("/workspace/")) for p in bare)
        tasks.append({"instance_id": task_id, "gold_context": spans})
        decisions.append({"task_id": task_id, "disposition": disposition, "evidence_paths": paths})
        selected.append({
            "task_id": task_id, "dataset": dataset, "stratum_size": len(rows),
            "language": lang, "repo_url": row["repo_url"], "base_commit": row["base_commit"],
            "query": row["problem_statement"], "missing_gold_paths": missing,
        })

    packet = work / "packet"
    packet.mkdir(mode=0o700)
    write(packet / "tasks.jsonl", tasks, jsonl=True)
    write(packet / "dispositions.json", {"schema": "epyc.contextbench_dispositions.v1", "tasks": decisions})
    write(packet / "dataset-audit.json", audit)
    write(packet / "request.json", {
        "schema": "epyc.dcp10.lexical-pilot.v1",
        "created_utc": datetime.now(UTC).isoformat(),
        "upstream_git_rev": UPSTREAM_REV, "hf_rev": HF_REV,
        "app_revision": APP_REV, "arm": ARM, "limit": LIMIT, "max_files": MAX_FILES,
        "budgets": BUDGETS, "dataset_hashes": {name: spec[1] for name, spec in DATASETS.items()},
        "source_hashes": {name: digest(work / "app" / name) for name in (
            "src/context_discovery.py", "src/context_assembly.py", "src/contextbench_score.py",
            "src/repl_environment/code_search.py", "src/repl_environment/task_root.py",
        )},
        "packet_hashes": {name: digest(packet / name) for name in (
            "tasks.jsonl", "dispositions.json", "dataset-audit.json",
        )},
        "producer_sha256": digest(Path(__file__)),
        "selected": selected,
    })


def get_predictions(root, task_id, query):
    from src.context_assembly import InclusionMode, pack_to_budget
    from src.context_discovery import (
        cost_candidates,
        discover_candidates,
        render_bundle,
    )
    from src.repl_environment.code_search import _CodeSearchMixin
    from src.repl_environment.task_root import get_task_root

    def read_source(name):
        path = (root / name).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError(f"source path escapes checkout: {name}")
        return path.read_text(encoding="utf-8")

    check_read_scope(root)
    os.environ["ORCHESTRATOR_EDIT_ROOT"] = str(root)
    if get_task_root() != root:
        raise ValueError("lexical search would use the wrong checkout")
    raw_search = []
    search = _CodeSearchMixin()._code_search

    def search_and_record(query, limit):
        raw = search(query, limit=limit)
        raw_search.extend(json.loads(raw))
        return raw

    hits = discover_candidates(query, code_search_fn=search_and_record, limit=LIMIT, max_files=MAX_FILES)
    candidates = cost_candidates(hits, file_reader_fn=read_source)
    line_counts = {candidate.path: len(read_source(candidate.path).splitlines()) for candidate in candidates}
    prediction = {
        "task_id": task_id, "arm": ARM, "status": "ok" if hits else "no_context_extracted",
        "pred_files": [hit.path for hit in hits],
        "pred_spans": [{"file": hit.path, "start_line": span.start, "end_line": span.end}
                       for hit in hits for span in hit.line_ranges],
        "pack_candidates": [{
            "path": candidate.path, "priority": candidate.priority, "cost_full": candidate.cost_full,
            "cost_slices": candidate.cost_slices, "cost_codemap": candidate.cost_codemap,
            "desired_mode": candidate.desired_mode, "total_lines": line_counts[candidate.path],
            "line_ranges": [[span.start, span.end] for span in candidate.line_ranges],
        } for candidate in candidates],
    }
    plans = []
    for budget in BUDGETS:
        bundle = pack_to_budget(candidates, budget)
        modes = {entry.path: entry.mode for entry in bundle.entries}
        entries = []
        rendered = render_bundle(bundle, file_reader_fn=read_source)
        for entry in bundle.entries:
            spans = []
            if modes[entry.path] == InclusionMode.FULL and line_counts[entry.path]:
                spans = [[1, line_counts[entry.path]]]
            elif modes[entry.path] == InclusionMode.SLICES:
                spans = [[span.start, span.end] for span in entry.line_ranges]
            entries.append({
                "path": entry.path, "packer_mode": modes[entry.path], "rendered_mode": entry.mode,
                "pred_spans": spans, "estimated_tokens": entry.estimated_tokens,
                "content_sha256": entry.content_sha256, "reason": entry.reason_downgraded_or_excluded,
            })
        plans.append({
            "budget_tokens": budget, "entries": entries,
            "estimated_packed_tokens": sum(e["estimated_tokens"] for e in entries),
            "pred_files": [entry["path"] for entry in entries if entry["packer_mode"] != InclusionMode.EXCLUDED],
            "rendered_sha256": sha256(rendered.encode()).hexdigest(),
        })
    return prediction, {
        "task_id": task_id, "raw_search": raw_search, "pack_plans": plans,
        "unreadable_hits": sorted(set(prediction["pred_files"]) - set(line_counts)),
    }


def run(work, request_sha, output):
    from src.contextbench_score import score_contextbench_bytes

    started = monotonic()
    packet = work / "packet"
    if digest(packet / "request.json") != request_sha:
        raise ValueError("prospective request hash differs")
    request = read(packet / "request.json")
    if request["producer_sha256"] != digest(Path(__file__)):
        raise ValueError("pilot source differs from prospective request")
    check_worktree(work / "app", APP_REV)
    for base, hashes in ((packet, request["packet_hashes"]), (work / "app", request["source_hashes"])):
        for path, expected in hashes.items():
            if digest(base / path) != expected:
                raise ValueError(f"sealed input drift: {path}")
    for name, expected in request["dataset_hashes"].items():
        if digest(work / "source" / f"{name}.parquet") != expected:
            raise ValueError(f"sealed dataset drift: {name}")

    decisions = {r["task_id"]: r["disposition"] for r in read(packet / "dispositions.json")["tasks"]}
    output.mkdir(mode=0o700)
    predictions, discovery = [], []
    for task in request["selected"]:
        task_id = task["task_id"]
        if decisions[task_id] != "include":
            continue
        root = work / "bases" / task["language"]
        try:
            check_worktree(root, task["base_commit"])
            if not task["query"] or not task["query"].strip():
                raise ValueError("source issue statement is empty")
            prediction, evidence = get_predictions(root, task_id, task["query"])
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            prediction = {"task_id": task_id, "arm": ARM, "status": "error",
                          "pred_files": [], "pred_spans": [], "pack_candidates": []}
            evidence = {"task_id": task_id, "error": f"{type(exc).__name__}: {exc}"}
        predictions.append(prediction)
        discovery.append(evidence)
        write(output / f"{task['language']}.json", {"prediction": prediction, "evidence": evidence})
    write(output / "predictions.jsonl", predictions, jsonl=True)
    write(output / "discovery.jsonl", discovery, jsonl=True)
    write(output / "score-request.json", {
        "app_revision": APP_REV, "source_hashes": request["source_hashes"],
        "pilot_request_sha256": request_sha,
        "tasks_sha256": digest(packet / "tasks.jsonl"),
        "dispositions_sha256": digest(packet / "dispositions.json"),
        "predictions_sha256": digest(output / "predictions.jsonl"),
        "discovery_sha256": digest(output / "discovery.jsonl"),
        "dataset_hashes": request["dataset_hashes"],
        "arms": [ARM], "budgets": BUDGETS,
        "started_utc": datetime.now(UTC).isoformat(),
    })
    score = score_contextbench_bytes(
        (packet / "tasks.jsonl").read_bytes(), (output / "predictions.jsonl").read_bytes(),
        (packet / "dispositions.json").read_bytes(), declared_arms=[ARM],
    )
    write(output / "scored-output.json", score)
    write(output / "run.json", {
        "request_sha256": request_sha, "elapsed_seconds": monotonic() - started,
        "ended_utc": datetime.now(UTC).isoformat(),
        "prediction_status_counts": dict(Counter(row["status"] for row in predictions)),
        "output_sha256": {p.name: digest(p) for p in sorted(output.iterdir())},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("prepare")
    execute = subcommands.add_parser("run")
    execute.add_argument("--request-sha", required=True)
    execute.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve(strict=True)
    parent = work.stat()
    if parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) & 0o077:
        raise ValueError("pilot work directory must be owned and private")
    sys.path.insert(0, str(work / "app"))
    if args.command == "prepare":
        prepare(work)
    else:
        output = args.output.resolve()
        if output.parent != work:
            raise ValueError("output must be a new directory directly inside the pilot work directory")
        run(work, args.request_sha, output)


if __name__ == "__main__":
    main()
