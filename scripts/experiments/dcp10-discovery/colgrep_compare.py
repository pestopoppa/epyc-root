#!/usr/bin/env python3
"""Admit sealed DCP-10 ColGREP inputs and prepare the paired scoring path."""
from __future__ import annotations

import argparse
import json
import math
import os
import stat
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from hashlib import file_digest, sha256
from pathlib import Path
from types import ModuleType

# Keep local imports available when invoked with python -I -B.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot

ARM = "task-root-colgrep"
SCHEMA = "epyc.dcp10.colgrep-comparison.v1"
ORIGINAL_REQUEST_SHA = "5a42163d7262dcbe1fa6e7ff6daf870c74070b58b9d7fc4da684981f292a37db"
LEXICAL_PREDICTIONS_SHA = "64088e7ac17ea1f8228f69aa68465b48c171037311f1b4a14ec535b93f1d077a"
BINARY_SHA = "833e52aa6c40d090142fa132e3c75d3e792a4707474682a2496e3471f646f956"
MODEL_ID = "lightonai/LateOn-Code-edge"
MODEL_REVISION = "07ef20f406c86badca122464808f4cac2f6e4b25"
LIMIT, MAX_FILES, BUDGETS = pilot.LIMIT, pilot.MAX_FILES, pilot.BUDGETS
ALPHA = "0.95"
TIMEOUT_S = 10
ERRORS = (OSError, ValueError, OverflowError, RuntimeError, subprocess.SubprocessError)
APP_MODULES = ("context_assembly", "context_discovery", "contextbench_score")


@dataclass(frozen=True)
class Admission:
    config: dict
    tasks: list
    app_sources: dict
    baseline: bytes
    task_bytes: bytes
    dispositions: bytes


def hash_file(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f"expected a regular file: {path}")
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def verify_hash(path, expected):
    if hash_file(path) != expected:
        raise ValueError(f"sealed input drift: {path}")


def regular_path(path):
    if path.resolve(strict=True) != path or not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f"expected a canonical regular file: {path}")
    return path


def read_sealed(path, expected):
    content = regular_path(path).read_bytes()
    if sha256(content).hexdigest() != expected:
        raise ValueError(f"sealed input drift: {path}")
    return content


def directory_digest(root):
    """Hash relative names and bytes, including hidden files, in a private payload."""
    if root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError(f"expected a canonical directory: {root}")
    files = {}
    for directory, dirs, names in os.walk(root, onerror=fail_walk):
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"payload contains a symlink: {path}")
            files[path.relative_to(root).as_posix() + "/"] = None
        for name in names:
            path = Path(directory) / name
            files[path.relative_to(root).as_posix()] = hash_file(path)
    if not any(value is not None for value in files.values()):
        raise ValueError(f"payload has no files: {root}")
    return sha256(pilot.encode(files).encode()).hexdigest()


def fail_walk(error):
    raise error


def require_fields(record, expected, label):
    if not isinstance(record, dict) or set(record) != expected:
        raise ValueError(f"invalid fields in {label}")


def admit(work, assets, config_path, config_sha):
    """Verify the fixed cohort and common inputs before any backend is supplied."""
    if work.resolve(strict=True) != work or not work.is_dir():
        raise ValueError("expected a canonical pilot directory")
    if (assets.resolve(strict=True) != assets or not assets.is_dir() or assets.is_relative_to(work)
            or work.is_relative_to(assets) or assets.stat().st_uid != os.geteuid()
            or stat.S_IMODE(assets.stat().st_mode) & 0o077):
        raise ValueError("assets must be an owned private directory separate from the pilot")
    if config_path != assets / "config.json":
        raise ValueError("expected config.json directly inside the private assets directory")
    config = json.loads(read_sealed(config_path, config_sha))
    require_fields(config, {"schema", "arm", "pilot_request_sha256", "lexical_predictions_sha256",
                            "app_revision", "runner_sha256", "pilot_helpers_sha256", "binary_sha256",
                            "model", "limit", "max_files", "budgets", "alpha", "timeout_s", "tasks"},
                   "comparator config")
    pins = {"schema": SCHEMA, "arm": ARM, "pilot_request_sha256": ORIGINAL_REQUEST_SHA,
            "lexical_predictions_sha256": LEXICAL_PREDICTIONS_SHA, "app_revision": pilot.APP_REV,
            "binary_sha256": BINARY_SHA, "limit": LIMIT, "max_files": MAX_FILES,
            "budgets": list(BUDGETS), "alpha": ALPHA, "timeout_s": TIMEOUT_S}
    if any(config[key] != value for key, value in pins.items()):
        raise ValueError("comparator config differs from the fixed protocol")
    verify_hash(Path(__file__).resolve(), config["runner_sha256"])
    verify_hash(Path(pilot.__file__).resolve(), config["pilot_helpers_sha256"])

    packet, app = work / "packet", work / "app"
    request = json.loads(read_sealed(packet / "request.json", ORIGINAL_REQUEST_SHA))
    baseline = read_sealed(work / "pilot/predictions.jsonl", LEXICAL_PREDICTIONS_SHA)
    if (request["app_revision"], request["arm"], request["limit"], request["max_files"],
            request["budgets"]) != (pilot.APP_REV, pilot.ARM, LIMIT, MAX_FILES, list(BUDGETS)):
        raise ValueError("sealed request differs from the fixed protocol")
    if app.resolve(strict=True) != app:
        raise ValueError("expected a canonical application checkout")
    pilot.check_worktree(app, pilot.APP_REV)
    packet_bytes = {path: read_sealed(packet / path, expected)
                    for path, expected in request["packet_hashes"].items()}
    app_sources = {path: read_sealed(app / path, expected)
                   for path, expected in request["source_hashes"].items()}

    binary = assets / "bin/colgrep"
    if binary.resolve(strict=True) != binary or not os.access(binary, os.X_OK):
        raise ValueError("expected an executable ColGREP staged under the private assets directory")
    verify_hash(binary, BINARY_SHA)
    model = config["model"]
    require_fields(model, {"id", "revision", "directory_sha256"}, "local model identity")
    if model["id"] != MODEL_ID or model["revision"] != MODEL_REVISION:
        raise ValueError("expected an exact local LateOn-Code-edge model revision")
    if directory_digest(assets / "model") != model["directory_sha256"]:
        raise ValueError("sealed local model directory drift")

    dispositions = packet_bytes["dispositions.json"]
    decisions = {item["task_id"]: item["disposition"]
                 for item in json.loads(dispositions)["tasks"]}
    tasks = [task for task in request["selected"] if decisions[task["task_id"]] == "include"]
    require_fields(config["tasks"], {task["task_id"] for task in tasks}, "fixed cohort bindings")
    return Admission(config, tasks, app_sources, baseline, packet_bytes["tasks.jsonl"], dispositions)


def admit_base(work, assets, task, binding):
    task_id = task["task_id"]
    root = work / "bases" / task["language"]
    data_home = assets / "bases" / task["language"]
    require_fields(binding, {"base_commit", "base_tree", "root", "query_sha256", "app_revision",
                             "binary_sha256", "model_revision", "model_directory_sha256",
                             "index_data_sha256"}, f"index binding for {task_id}")
    if (root.resolve(strict=True) != root or binding["root"] != str(root)
            or binding["base_commit"] != task["base_commit"]
            or binding["query_sha256"] != sha256(task["query"].encode()).hexdigest()):
        raise ValueError(f"wrong base or query binding: {task_id}")
    pilot.check_worktree(root, task["base_commit"])
    pilot.check_read_scope(root)
    # Ignored source files can affect native index freshness too.
    if pilot.git(root, "ls-files", "--others", "--ignored", "--exclude-standard"):
        raise ValueError(f"unexpected ignored checkout files: {task_id}")
    git_files = pilot.git(root, "ls-files", "-vz")
    if any(record[0] != "H" for record in git_files.split("\0") if record):
        raise ValueError(f"checkout has hidden or unmerged Git index entries: {task_id}")
    if binding["base_tree"] != pilot.git(root, "rev-parse", "HEAD^{tree}"):
        raise ValueError(f"wrong base tree: {task_id}")

    if directory_digest(data_home) != binding["index_data_sha256"]:
        raise ValueError(f"stale index bytes: {task_id}")
    projects = list((data_home / "colgrep/indices").iterdir())
    if len(projects) != 1 or not projects[0].is_dir():
        raise ValueError(f"expected a single native project index: {task_id}")
    project = projects[0]
    project_config = pilot.read(project / "project.json")
    if not isinstance(project_config, dict) or project_config.get("project_path") != str(root):
        raise ValueError(f"native index belongs to a different root: {task_id}")
    for path in (project / "state.json", project / "index/metadata.json"):
        state = pilot.read(path)
        if not isinstance(state, dict) or not state:
            raise ValueError(f"missing native index state: {path}")
    if not any(path.is_file() and path.name != "metadata.json" for path in (project / "index").rglob("*")):
        raise ValueError(f"native index has no payload: {task_id}")
    return root, data_home


def admit_task(work, assets, config, task):
    binding = config["tasks"][task["task_id"]]
    if (not isinstance(binding, dict) or binding.get("app_revision") != config["app_revision"]
            or binding.get("binary_sha256") != BINARY_SHA
            or binding.get("model_revision") != config["model"]["revision"]
            or binding.get("model_directory_sha256") != config["model"]["directory_sha256"]):
        raise ValueError(f"index application, binary or model differs: {task['task_id']}")
    return admit_base(work, assets, task, binding)


def search_command(assets, root, query, limit):
    """Prepare argv for a future qualified isolated native-launch adapter."""
    return [str(assets / "bin/colgrep"), "search", "-k", str(limit), "--alpha", ALPHA,
            "--model", str(assets / "model"), "--force-cpu", "--json", "--", query, str(root)]


def invoke_mock(search, assets, root, data_home, query, limit):
    return search(search_command(assets, root, query, limit), root, data_home, TIMEOUT_S)


def read_path(root, name, tracked_files):
    path = root / name
    if ".." in path.parts or not path.is_relative_to(root):
        raise ValueError(f"result path escapes checkout: {name}")
    relative = path.relative_to(root).as_posix()
    if relative not in tracked_files:
        raise ValueError(f"result does not name a tracked regular source file: {name}")
    regular_path(path)
    return relative


def normalize_hits(raw, root, limit, tracked_files):
    if not isinstance(raw, list) or len(raw) > limit:
        raise ValueError("expected a native ColGREP JSON list within the declared limit")
    hits = []
    for item in raw:
        unit = item.get("unit") if isinstance(item, dict) else None
        if not isinstance(unit, dict) or not isinstance(unit.get("file"), str) or not unit["file"]:
            raise ValueError("native ColGREP result lacks a source file")
        score, start, end = item.get("score"), unit.get("line"), unit.get("end_line")
        if (type(score) not in (int, float) or not math.isfinite(score)
                or type(start) is not int or type(end) is not int or not 1 <= start <= end):
            raise ValueError("native ColGREP result has an invalid score or line range")
        hits.append({"file": read_path(root, unit["file"], tracked_files), "score": score,
                     "start_line": start, "end_line": end})
    return hits


def predict(task, root, search, discovery, assembly):
    task_id, query = task["task_id"], task["query"]
    if not isinstance(query, str) or not query.strip():
        raise ValueError("source issue statement is empty")
    tracked_files = set()
    for record in pilot.git(root, "ls-tree", "-rz", "--full-tree", "HEAD").split("\0"):
        if record.startswith(("100644 blob ", "100755 blob ")):
            tracked_files.add(record.split("\t", 1)[1])
    raw_search = None

    def search_and_record(actual_query, limit):
        nonlocal raw_search
        if raw_search is not None:
            raise ValueError("discovery called search more than once")
        if actual_query != query or limit != LIMIT:
            raise ValueError("discovery changed the sealed query or retrieval limit")
        payload = search(actual_query, limit)
        if not isinstance(payload, (str, bytes)):
            raise ValueError("expected a JSON text payload from the search adapter")  # noqa: TRY004
        raw = json.loads(payload)
        hits = normalize_hits(raw, root, limit, tracked_files)
        raw_search = raw
        return hits

    hits = discovery.discover_candidates(query, code_search_fn=search_and_record,
                                         limit=LIMIT, max_files=MAX_FILES)
    if raw_search is None or len(hits) > MAX_FILES:
        raise ValueError("discovery ignored the sealed retrieval call or file cap")
    sources = {}
    line_counts = {}
    for hit in hits:
        name = read_path(root, hit.path, tracked_files)
        body = (root / name).read_text(encoding="utf-8")
        line_count = len(body.splitlines())
        if any(span.end > line_count for span in hit.line_ranges):
            raise ValueError(f"result spans past the end of the pinned source file: {name}")
        sources[name] = body
        line_counts[name] = line_count
    candidates = discovery.cost_candidates(hits, file_reader_fn=sources.__getitem__)
    prediction = {
        "task_id": task_id, "arm": ARM, "status": "ok" if hits else "no_context_extracted",
        "pred_files": [hit.path for hit in hits],
        "pred_spans": [{"file": hit.path, "start_line": span.start, "end_line": span.end}
                       for hit in hits for span in hit.line_ranges],
        "pack_candidates": [{
            "path": item.path, "priority": item.priority, "cost_full": item.cost_full,
            "cost_slices": item.cost_slices, "cost_codemap": item.cost_codemap,
            "desired_mode": item.desired_mode, "total_lines": line_counts[item.path],
            "line_ranges": [[span.start, span.end] for span in item.line_ranges],
        } for item in candidates],
    }
    plans = []
    for budget in BUDGETS:
        bundle = assembly.pack_to_budget(candidates, budget)
        modes = {entry.path: entry.mode for entry in bundle.entries}
        rendered = discovery.render_bundle(bundle, file_reader_fn=sources.__getitem__)
        entries = []
        for entry in bundle.entries:
            spans = []
            if entry.mode == assembly.InclusionMode.FULL:
                spans = [[1, line_counts[entry.path]]]
            elif entry.mode == assembly.InclusionMode.SLICES:
                spans = [[span.start, span.end] for span in entry.line_ranges]
            entries.append({"path": entry.path, "packer_mode": modes[entry.path],
                            "rendered_mode": entry.mode, "estimated_tokens": entry.estimated_tokens,
                            "content_sha256": entry.content_sha256, "pred_spans": spans,
                            "reason": entry.reason_downgraded_or_excluded})
        plans.append({"budget_tokens": budget, "rendered_sha256": sha256(rendered.encode()).hexdigest(),
                      "entries": entries,
                      "estimated_packed_tokens": sum(entry["estimated_tokens"] for entry in entries),
                      "pred_files": [entry["path"] for entry in entries
                                     if entry["rendered_mode"] != assembly.InclusionMode.EXCLUDED]})
    return prediction, {"task_id": task_id, "raw_search": raw_search, "pack_plans": plans}


@contextmanager
def load_app(app, app_sources):
    """Load just the verified app modules and bypass ambient imports and bytecode."""
    names = ["src", *(f"src.{name}" for name in APP_MODULES)]
    if any(name in sys.modules for name in names):
        raise ValueError("run the comparator in a fresh process without preloaded app modules")
    sys.modules["src"] = ModuleType("src")
    sys.modules["src"].__path__ = []
    try:
        for module_name, name in zip(names[1:], APP_MODULES, strict=True):
            relative = f"src/{name}.py"
            module = ModuleType(module_name)
            module.__file__ = str(app / relative)
            sys.modules[module_name] = module
            exec(compile(app_sources[relative], module.__file__, "exec"), module.__dict__)  # noqa: S102
        yield tuple(sys.modules[name] for name in names[1:])
    finally:
        for name in reversed(names):
            sys.modules.pop(name, None)


def compare(work, assets, config_sha, *, search):
    """Score the admitted cohort with an explicitly injected mock search callback."""
    admitted = admit(work, assets, assets / "config.json", config_sha)
    with load_app(work / "app", admitted.app_sources) as (assembly, discovery, scorer):
        return _compare_admitted(work, assets, admitted, config_sha, search, discovery, assembly, scorer)


def _compare_admitted(work, assets, admitted, config_sha, search, discovery, assembly, scorer):
    predictions, evidence = [], []
    for task in admitted.tasks:
        task_id = task["task_id"]
        try:
            root, data_home = admit_task(work, assets, admitted.config, task)

            bound_search = partial(invoke_mock, search, assets, root, data_home)
            prediction, entry = predict(task, root, bound_search, discovery, assembly)
        except ERRORS as exc:
            prediction = {"task_id": task_id, "arm": ARM, "status": "error",
                          "pred_files": [], "pred_spans": [], "pack_candidates": []}
            entry = {"task_id": task_id, "error": f"{type(exc).__name__}: {exc}"}
        predictions.append(prediction)
        entry["binding"] = admitted.config["tasks"][task_id]
        entry["config_sha256"] = config_sha
        evidence.append(entry)
    combined = admitted.baseline + "".join(pilot.encode(row) for row in predictions).encode()
    scored = scorer.score_contextbench_bytes(admitted.task_bytes, combined, admitted.dispositions,
                                             declared_arms=[pilot.ARM, ARM])
    return predictions, evidence, scored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path, help="original pilot directory")
    parser.add_argument("assets", type=Path, help="private comparison directory")
    parser.add_argument("--config-sha", required=True, help="prospective SHA-256 of assets/config.json")
    args = parser.parse_args()
    work, assets = args.work.absolute(), args.assets.absolute()
    try:
        admitted = admit(work, assets, assets / "config.json", args.config_sha)
    except ERRORS as exc:
        parser.exit(1, f"ColGREP admission failed: {exc}\n")
    checks = {}
    for task in admitted.tasks:
        try:
            admit_task(work, assets, admitted.config, task)
            checks[task["task_id"]] = {"status": "admitted"}
        except ERRORS as exc:
            checks[task["task_id"]] = {"status": "error", "reason": str(exc)}
    print(pilot.encode({"config_sha256": args.config_sha, "native_execution": "disabled",
                        "tasks": checks}), end="")
    return 1 if any(item["status"] == "error" for item in checks.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
