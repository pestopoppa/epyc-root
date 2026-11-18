#!/usr/bin/env python3
"""Replay fixture-only GitNexus append and rerank controls on original DCP-10 tasks."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import colgrep_compare as common
import pilot

SCHEMA = "epyc.dcp10.gitnexus-fixture.v1"
SEED_ARM = "fixture-colgrep"
APPENDED_ARM = "fixture-colgrep-gitnexus-appended"
RERANK_ARM = "fixture-colgrep-gitnexus-rerank-only"
SOURCE_ROOT = Path("/usr/local/share/npm-global/lib/node_modules/gitnexus")
SOURCE_FILES = {
    "package.json": "5c246850e33ab06f149d92c880557e8fad590c3c3679dab2fe50a272529a4e7c",
    "dist/mcp/local/local-backend.js": "756d29b6b81ef35495385a5d394d0f101def333f51a976d05a4d2472a2a9bc4a",
    "dist/core/lbug/schema.js": "2d91d17c6ed60fbaf6841a3c0dbbe0d713fe7c7cff2661a224c80a55b4f49dd9",
    "dist/core/lbug/pool-adapter.js": "d37f8605286d8eb63c40e6fe49675c750395bac32507d8ffc9c27cdcda5a4b24",
    "dist/core/run-analyze.js": "caf4c8b8b33578892ee2fbb458d1d04f3deb7da9ea49b64a882f3ac705226c2c",
    "dist/storage/repo-manager.js": "f57bbf8c027ac1eab62c065e1c7ff4dd52e1c50d89f6e0209ccd006ed87a40a2",
}
RELATIONS = (
    "CALLS", "IMPORTS", "EXTENDS", "IMPLEMENTS", "METHOD_OVERRIDES", "OVERRIDES", "METHOD_IMPLEMENTS",
)
CONFIDENCE = 0.9
GRAPH_QUERY = f"""MATCH (src)-[r:CodeRelation]->(dst)
WHERE (src.filePath IN $seed_paths OR dst.filePath IN $seed_paths)
  AND src.filePath <> dst.filePath
  AND r.type IN [{", ".join(repr(relation) for relation in RELATIONS)}]
  AND r.confidence >= {CONFIDENCE}
RETURN src.id AS source_id, src.filePath AS source_path,
       dst.id AS target_id, dst.filePath AS target_path,
       r.type AS relation, r.confidence AS confidence, 1 AS depth"""
GRAPH_QUERY_SHA = sha256(GRAPH_QUERY.encode()).hexdigest()
EDGE_FIELDS = {"source_id", "source_path", "target_id", "target_path", "relation", "confidence", "depth"}


def source_identity(source_root):
    """Verify the installed API, storage and index writer source bytes without running Node."""
    try:
        for name, digest in SOURCE_FILES.items():
            common.read_sealed(source_root / name, digest)
    except (OSError, ValueError) as exc:
        raise ValueError(f"GitNexus 1.6.1 source gate failed: {exc}") from exc
    return {"package": "gitnexus", "version": "1.6.1", "source_sha256": SOURCE_FILES.copy()}


def producer_identity():
    return {path.name: common.hash_file(path)
            for path in (Path(source).resolve() for source in (__file__, common.__file__, pilot.__file__))}


def strict_json(content):
    def unique_object(pairs):
        record = {}
        for key, value in pairs:
            if key in record:
                raise ValueError(f"duplicate fixture field: {key}")
            record[key] = value
        return record

    def reject_constant(value):
        raise ValueError(f"invalid JSON number: {value}")

    return json.loads(content, object_pairs_hook=unique_object, parse_constant=reject_constant)


def admit(work, capture_path, capture_sha, source_root):
    identity = source_identity(source_root)
    request = json.loads(common.read_sealed(work / "packet/request.json", common.ORIGINAL_REQUEST_SHA))
    common.read_sealed(work / "pilot/predictions.jsonl", common.LEXICAL_PREDICTIONS_SHA)
    packet = {name: common.read_sealed(work / "packet" / name, digest)
              for name, digest in request["packet_hashes"].items()}
    app_sources = {name: common.read_sealed(work / "app" / name, digest)
                   for name, digest in request["source_hashes"].items()}
    pilot.check_worktree(work / "app", pilot.APP_REV)
    included = [row["task_id"] for row in json.loads(packet["dispositions.json"])["tasks"]
                if row["disposition"] == "include"]
    selected = [task for task in request["selected"] if task["task_id"] in included]
    task_ids = [task["task_id"] for task in selected]
    fixture_root = capture_path.parent
    if (fixture_root.is_relative_to(work) or work.is_relative_to(fixture_root)
            or fixture_root.stat().st_uid != os.geteuid() or stat.S_IMODE(fixture_root.stat().st_mode) & 0o077):
        raise ValueError("the fixture directory must be owned, private and separate from the original pilot")
    capture = strict_json(common.read_sealed(capture_path, capture_sha))
    common.require_fields(capture, {"schema", "kind", "pilot_request_sha256", "lexical_predictions_sha256",
                                    "gitnexus_source", "graph_query_sha256", "producer_sha256", "tasks"},
                          "fixture capture")
    if capture["producer_sha256"] != producer_identity():
        raise ValueError("fixture producer source bytes drifted")
    if (capture["schema"], capture["kind"], capture["pilot_request_sha256"], capture["lexical_predictions_sha256"],
            capture["gitnexus_source"], capture["graph_query_sha256"]) != (
            SCHEMA, "synthetic", common.ORIGINAL_REQUEST_SHA, common.LEXICAL_PREDICTIONS_SHA, identity, GRAPH_QUERY_SHA):
        raise ValueError("fixture capture differs from the fixed source or protocol")
    common.require_fields(capture["tasks"], set(task_ids), "original three-task fixture bindings")
    return selected, packet, app_sources, capture


def bind_task(work, task, binding):
    root = work / "bases" / task["language"]
    common.require_fields(binding, {"root", "base_commit", "base_tree", "query_sha256"}, "base binding")
    if (binding["root"], binding["base_commit"], binding["query_sha256"]) != (
            str(root), task["base_commit"], sha256(task["query"].encode()).hexdigest()):
        raise ValueError("wrong task base or issue query binding")
    if root.resolve(strict=True) != root:
        raise ValueError("expected a canonical task root")
    pilot.check_worktree(root, task["base_commit"])
    pilot.check_read_scope(root)
    if pilot.git(root, "ls-files", "--others", "--ignored", "--exclude-standard"):
        raise ValueError("unexpected ignored checkout files")
    if any(record[0] != "H" for record in pilot.git(root, "ls-files", "-vz").split("\0") if record):
        raise ValueError("checkout has hidden or unmerged Git index entries")
    if binding["base_tree"] != pilot.git(root, "rev-parse", "HEAD^{tree}"):
        raise ValueError("wrong base tree")
    return root


def bind_fixture_index(index, binding, digest):
    if common.directory_digest(index) != digest:
        raise ValueError("fixture index bytes drifted")
    metadata = strict_json(common.regular_path(index / "meta.json").read_bytes())
    if (not isinstance(metadata, dict) or metadata.get("repoPath") != binding["root"]
            or metadata.get("lastCommit") != binding["base_commit"]):
        raise ValueError("fixture index metadata names a different root or commit")
    if common.regular_path(index / "lbug").stat().st_size == 0:
        raise ValueError("fixture index has no lbug payload")


def check_path(name, root, tracked):
    if (not isinstance(name, str) or not name or name.startswith("/") or "\\" in name or "\0" in name
            or any(part in ("", ".", "..") for part in name.split("/"))):
        raise ValueError(f"edge path must be canonical and relative: {name!r}")
    return common.read_path(root, name, tracked)


def ranked_paths(seeds, edges, *, root, tracked, excluded):
    """Return both rankings from a single validated set of stored direct edges."""
    if not isinstance(edges, list):
        raise ValueError("expected a list of stored direct edges")  # noqa: TRY004
    seed_rank = {path: rank for rank, path in enumerate(seeds)}
    append_support, rerank_support = {}, {}
    node_paths = {}
    for edge in edges:
        common.require_fields(edge, EDGE_FIELDS, "direct edge")
        if type(edge["depth"]) is not int or edge["depth"] != 1:
            raise ValueError("transitive graph evidence is ineligible")
        if edge["relation"] not in RELATIONS:
            raise ValueError("unknown graph relation")
        confidence = edge["confidence"]
        if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
            raise ValueError("invalid stored graph confidence")
        source = check_path(edge["source_path"], root, tracked)
        target = check_path(edge["target_path"], root, tracked)
        for endpoint, node in ((source, edge["source_id"]), (target, edge["target_id"])):
            if not isinstance(node, str) or not node.strip() or node_paths.setdefault(node, endpoint) != endpoint:
                raise ValueError("missing node identity or node associated with conflicting paths")
        if source not in seed_rank and target not in seed_rank:
            raise ValueError("direct edge does not touch an original seed")
        if source == target or confidence < CONFIDENCE:
            continue
        for seed, neighbor in ((source, target), (target, source)):
            if seed not in seed_rank:
                continue
            if neighbor in seed_rank:
                rerank_support[neighbor] = max(confidence, rerank_support.get(neighbor, 0))
            elif not excluded(neighbor):
                key = (-confidence, seed_rank[seed], neighbor)
                append_support[neighbor] = min(key, append_support.get(neighbor, key))
    available = pilot.MAX_FILES - len(seeds)
    new_paths = sorted(append_support, key=append_support.__getitem__)
    return (
        seeds + new_paths[:available],
        sorted(seeds, key=lambda path: (-rerank_support.get(path, 0), seed_rank[path])),
        {"append_capacity": available, "append_eligible": new_paths, "rerank_support": rerank_support},
    )


def make_prediction(task_id, arm, status="error"):
    return {"task_id": task_id, "arm": arm, "status": status, "pred_files": [], "pred_spans": [],
            "pack_candidates": []}


def graph_prediction(seed, paths, arm, root, discovery):
    sources = {}
    previous = {item["path"]: item for item in seed["pack_candidates"]}
    hits = []
    for path in paths:
        if path not in previous:
            sources[path] = (root / path).read_text(encoding="utf-8")
            hits.append(discovery.DiscoveredHit(path=path))
    for item in discovery.cost_candidates(hits, file_reader_fn=sources.__getitem__):
        previous[item.path] = {
            "path": item.path, "cost_full": item.cost_full, "cost_slices": item.cost_slices,
            "cost_codemap": item.cost_codemap, "desired_mode": item.desired_mode,
            "total_lines": len(sources[item.path].splitlines()), "line_ranges": [],
        }
    return {
        **make_prediction(seed["task_id"], arm, "ok" if paths else "no_context_extracted"),
        "pred_files": paths,
        "pred_spans": seed["pred_spans"],
        # The packer sorts by priority. Ordinals carry the graph ranking to that entry point.
        "pack_candidates": [{**previous[path], "priority": len(paths) - rank} for rank, path in enumerate(paths)],
    }


def process_task(work, capture_dir, task, row, assembly, discovery):
    task_id = task["task_id"]
    seed = make_prediction(task_id, SEED_ARM)
    evidence = {"task_id": task_id}
    try:
        common.require_fields(row, {"base", "mock_search", "graph"}, "task fixture row")
        root = bind_task(work, task, row["base"])
        evidence["base"] = row["base"]
        search = row["mock_search"]
        if isinstance(search, dict):
            common.require_fields(search, {"error"}, "fixture search failure")
            if not isinstance(search["error"], str) or not search["error"].strip():
                raise ValueError("fixture search failure requires a reason")
            raise RuntimeError(f"fixture ColGREP error: {search['error']}")  # noqa: TRY004
        seed_prediction, trace = common.predict(task, root, lambda *_: pilot.encode(search), discovery, assembly)
        seed = {**seed_prediction, "arm": SEED_ARM}
        evidence["seed_pack_plans"] = trace["pack_plans"]
    except common.ERRORS as exc:
        evidence.update(graph_status="upstream_error", error=f"{type(exc).__name__}: {exc}")
        return [seed, make_prediction(task_id, APPENDED_ARM), make_prediction(task_id, RERANK_ARM)], evidence

    try:
        graph = row["graph"]
        common.require_fields(graph, {"index_sha256", "seed_paths", "edges", "error"}, "graph edge fixture")
        seeds = seed["pred_files"]
        if graph["seed_paths"] != seeds:
            raise ValueError("graph query seed order differs from this task's admitted ColGREP fixture")
        bind_fixture_index(capture_dir / "indexes" / task["language"], row["base"], graph["index_sha256"])
        evidence.update(index_sha256=graph["index_sha256"], seed_paths=seeds)
        if graph["error"] is not None:
            if not isinstance(graph["error"], str) or not graph["error"].strip() or graph["edges"] != []:
                raise ValueError("graph failure requires a reason and an empty edge list")
            raise ValueError(f"fixture GitNexus error: {graph['error']}")
        tracked = {record.split("\t", 1)[1] for record in pilot.git(root, "ls-tree", "-rz", "HEAD").split("\0")
                   if record.startswith(("100644 blob ", "100755 blob "))}
        appended, reranked, ranks = ranked_paths(
            seeds, graph["edges"], root=root, tracked=tracked, excluded=assembly.default_exclusion_reason,
        )
        append = graph_prediction(seed, appended, APPENDED_ARM, root, discovery)
        rerank = graph_prediction(seed, reranked, RERANK_ARM, root, discovery)
        evidence.update(graph_status="ok" if graph["edges"] else "empty", direct_edges=graph["edges"], **ranks)
    except common.ERRORS as exc:
        append, rerank = make_prediction(task_id, APPENDED_ARM), make_prediction(task_id, RERANK_ARM)
        evidence.update(graph_status="error", error=f"{type(exc).__name__}: {exc}")
    return [seed, append, rerank], evidence


def compare(work, capture_path, capture_sha, source_root=SOURCE_ROOT):
    tasks, packet, app_sources, capture = admit(work, capture_path, capture_sha, source_root)
    predictions, outcomes = [], []
    with common.load_app(work / "app", app_sources) as (assembly, discovery, scorer):
        for task in tasks:
            rows, outcome = process_task(work, capture_path.parent, task, capture["tasks"][task["task_id"]],
                                         assembly, discovery)
            predictions.extend(rows)
            outcomes.append(outcome)
        combined = "".join(pilot.encode(row) for row in predictions).encode()
        score = scorer.score_contextbench_bytes(
            packet["tasks.jsonl"], combined, packet["dispositions.json"],
            declared_arms=[SEED_ARM, APPENDED_ARM, RERANK_ARM],
        )
    return {
        "schema": SCHEMA, "kind": "synthetic", "native_execution": "disabled",
        "capture_sha256": capture_sha, "gitnexus_source": capture["gitnexus_source"],
        "producer_sha256": capture["producer_sha256"],
        "graph_query_sha256": GRAPH_QUERY_SHA, "pilot_request_sha256": common.ORIGINAL_REQUEST_SHA,
        "lexical_predictions_sha256": common.LEXICAL_PREDICTIONS_SHA,
        "app_revision": pilot.APP_REV, "app_source_sha256": {name: sha256(data).hexdigest()
                                                           for name, data in app_sources.items()},
        "outcomes": outcomes, "predictions": predictions, "fixture_scores": score,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path, help="original sealed pilot directory")
    parser.add_argument("capture", type=Path, help="sealed JSON fixture in its private directory")
    parser.add_argument("--capture-sha", required=True)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--output", type=Path, required=True, help="new output file outside the original pilot")
    args = parser.parse_args()
    work = args.work.absolute()
    output = args.output.absolute()
    try:
        if output.resolve().is_relative_to(work.resolve()):
            raise ValueError("write results outside the original pilot")
        result = compare(work, args.capture.absolute(), args.capture_sha, args.source_root.absolute())
        pilot.write(output, result)
    except common.ERRORS as exc:
        parser.exit(1, f"GitNexus fixture admission failed: {exc}\n")


if __name__ == "__main__":
    main()
