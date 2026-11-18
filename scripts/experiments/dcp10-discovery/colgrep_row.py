"""Run the sealed three-task DCP-10 native ColGREP allocator row."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import tempfile
import time
from hashlib import sha256
from math import isclose
from pathlib import Path
from statistics import mean
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))

import colgrep_compare as comparator
import colgrep_native as native
import pilot

ROW = "dcp10-colgrep-native-20261118"
SCHEMA = "epyc.dcp10.colgrep-native-preparation.v1"
MAX_SECONDS = 1800
SMOKE_SECONDS = 120
PACKET_SOURCES = ("colgrep_row.py", "colgrep_compare.py", "colgrep_native.py", "pilot.py")
FIXTURE_FILE = "alpine.py"
FIXTURE_SOURCE = "def connect_alpine_sensor():\n    \"\"\"Connect the alpine atmospheric telemetry sensor.\"\"\"\n    return 'alpine telemetry'\n"
FIXTURE_QUERY = "Where is the alpine atmospheric telemetry sensor connected?"


class RowStopped(Exception):
    """Signal or allocator boundary stops further attempts."""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def jsonl(data):
    return [json.loads(line) for line in data.splitlines()]


def save(path, record):
    """Publish a fixed checkpoint atomically and refuse to replace an earlier result."""
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(pilot.encode(record).encode())
            handle.flush()
            os.fsync(handle.fileno())
            temporary.chmod(0o400)
            os.link(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def original_inputs(work):
    request = json.loads(comparator.read_sealed(work / "packet/request.json", comparator.ORIGINAL_REQUEST_SHA))
    require(
        (request["app_revision"], request["arm"], request["limit"], request["max_files"], request["budgets"])
        == (pilot.APP_REV, pilot.ARM, comparator.LIMIT, comparator.MAX_FILES, list(comparator.BUDGETS)),
        "original lexical protocol drift",
    )
    baseline = comparator.read_sealed(work / "pilot/predictions.jsonl", comparator.LEXICAL_PREDICTIONS_SHA)
    app = work / "app"
    require(app.resolve(strict=True) == app, "unexpected application checkout path")
    pilot.check_worktree(app, pilot.APP_REV)
    app_sources = {name: comparator.read_sealed(app / name, expected)
                   for name, expected in request["source_hashes"].items()}
    packet = {name: comparator.read_sealed(work / "packet" / name, expected)
              for name, expected in request["packet_hashes"].items()}
    included = {row["task_id"] for row in json.loads(packet["dispositions.json"])["tasks"]
                if row["disposition"] == "include"}
    tasks = [task for task in request["selected"] if task["task_id"] in included]
    require([task["language"] for task in tasks] == ["python", "c", "cpp"]
            and {task["task_id"] for task in tasks} == included
            and {row["task_id"] for row in jsonl(baseline)} == included, "fixed cohort drift")
    return request, comparator.Admission({}, tasks, app_sources, baseline, packet["tasks.jsonl"],
                                         packet["dispositions.json"])


def base_tree(root, task):
    require(root.resolve(strict=True) == root, f"noncanonical checkout: {root}")
    pilot.check_worktree(root, task["base_commit"])
    pilot.check_read_scope(root)
    require(not pilot.git(root, "ls-files", "--others", "--ignored", "--exclude-standard"),
            f"ignored checkout contents: {root}")
    require(all(record.startswith("H ") for record in pilot.git(root, "ls-files", "-vz").split("\0") if record),
            f"hidden Git index entries: {root}")
    return pilot.git(root, "rev-parse", "HEAD^{tree}")


def model_stat(model):
    require(model.resolve(strict=True) == model and model.is_dir()
            and model.stat().st_uid == os.geteuid() and model.stat().st_mode & 0o777 == 0o500,
            "model directory is missing or writable")
    records = {}
    for path in sorted(model.iterdir()):
        file = comparator.regular_path(path).stat()
        require(file.st_uid == os.geteuid() and file.st_mode & 0o777 == 0o400,
                f"model file is missing or writable: {path}")
        records[path.name] = [file.st_dev, file.st_ino, file.st_size, file.st_mtime_ns, file.st_ctime_ns]
    require(records, "model directory is empty")
    return records


def load_preparation(root, expected):
    packet, assets = root / "packet", root / "assets"
    for path in (root, assets, packet):
        require(path.resolve(strict=True) == path and path.is_dir() and path.stat().st_uid == os.geteuid()
                and path.stat().st_mode & 0o077 == 0, f"expected an owned private directory: {path}")
    receipt = json.loads(comparator.read_sealed(packet / "preparation.json", expected))
    require((receipt["schema"], receipt["row"], receipt["scratch"]) == (SCHEMA, ROW, str(root)),
            "unexpected preparation receipt")
    require(set(receipt["source_hashes"]) == set(PACKET_SOURCES), "incomplete packet source seal")
    for name, sealed in receipt["source_hashes"].items():
        comparator.read_sealed(packet / name, sealed)
    for path, sealed in ((assets / "bin/colgrep", receipt["binary_sha256"]),
                         (assets / "runtime" / native.RUNTIME_NAME, receipt["runtime_sha256"])):
        comparator.regular_path(path)
        comparator.verify_hash(path, sealed)
    require(model_stat(assets / "model") == receipt["model"]["file_stat"],
            "staged model identity differs from preparation")
    work = Path(receipt["work"])
    request, admitted = original_inputs(work)
    require(receipt["request_sha256"] == comparator.ORIGINAL_REQUEST_SHA
            and receipt["baseline_sha256"] == comparator.LEXICAL_PREDICTIONS_SHA
            and receipt["app_revision"] == pilot.APP_REV
            and receipt["app_sources"] == request["source_hashes"]
            and receipt["packet_hashes"] == request["packet_hashes"],
            "original input identities differ from preparation")
    require(set(receipt["tasks"]) == {task["task_id"] for task in admitted.tasks}, "task binding drift")
    return receipt, admitted


def span_pairs(spans):
    return {(span["file"], line) for span in spans
            for line in range(span["start_line"], span["end_line"] + 1)}


def count_overlap(predicted, gold):
    return {"tp": len(predicted & gold), "fp": len(predicted - gold), "fn": len(gold - predicted)}


def metric_values(kind, counts):
    tp, fp, fn = (counts[key] for key in ("tp", "fp", "fn"))
    return {f"{kind}_precision": tp / (tp + fp) if tp + fp else 0.0,
            f"{kind}_recall": tp / (tp + fn) if tp + fn else 0.0,
            f"{kind}_f1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0}


def accounted(arm, checkpoints, gold, expected_budgets):
    """Check every explicit task, rendered file/line scope, and macro aggregate."""
    task_index = {item["task_id"]: item for item in checkpoints}
    require([scope["budget_tokens"] for scope in arm["scopes"]] == expected_budgets, "score scope drift")
    actual = []
    for scope in arm["scopes"]:
        budget = scope["budget_tokens"]
        require({item["task_id"] for item in scope["per_task"]} == set(task_index)
                and len(scope["per_task"]) == len(task_index), "score denominator drift")
        per_task = []
        for scored in scope["per_task"]:
            task_id = scored["task_id"]
            checkpoint = task_index[task_id]
            prediction, evidence = checkpoint["prediction"], checkpoint["evidence"]
            require(scored["status"] == prediction["status"], f"score status drift: {task_id}")
            predicted_files, predicted_lines = set(), set()
            if budget is None:
                predicted_files = set(prediction["pred_files"])
                predicted_lines = span_pairs(prediction["pred_spans"])
            elif prediction["status"] != "error":
                plans = evidence["pack_plans"]
                require([plan["budget_tokens"] for plan in plans] == expected_budgets[1:],
                        f"render scope drift: {task_id}")
                plan = next(plan for plan in plans if plan["budget_tokens"] == budget)
                entries = plan["entries"]
                require(len({entry["path"] for entry in entries}) == len(entries), "duplicate render entry")
                require(plan["estimated_packed_tokens"] == sum(entry["estimated_tokens"] for entry in entries)
                        <= budget, "render budget drift")
                require(all(entry["rendered_mode"] in {"full", "slices", "codemap_only", "excluded"}
                            and (bool(entry["pred_spans"]) == (entry["rendered_mode"] in {"full", "slices"}))
                            for entry in entries), "render mode and line evidence disagree")
                predicted_files = {entry["path"] for entry in entries if entry["rendered_mode"] != "excluded"}
                require(predicted_files == set(plan["pred_files"]), "rendered file coverage drift")
                predicted_lines = {(entry["path"], line) for entry in entries
                                   for lo, hi in entry["pred_spans"] for line in range(lo, hi + 1)}
            if prediction["status"] != "ok":
                require(not predicted_files and not predicted_lines, "failed or empty retrieval claimed coverage")
            counts = {
                "file": count_overlap(predicted_files, {span["file"] for span in gold[task_id]}),
                "line": count_overlap(predicted_lines, span_pairs(gold[task_id])),
            }
            require(counts == scored["counts"], f"score and actual render counts disagree: {task_id}/{budget}")
            values = {name: value for kind, count in counts.items()
                      for name, value in metric_values(kind, count).items()}
            require(values == scored["metrics"], f"task metrics disagree: {task_id}/{budget}")
            per_task.append({"task_id": task_id, "status": prediction["status"], "counts": counts, "metrics": values})
        macro = {name: mean(row["metrics"][name] for row in per_task) for name in scope["metrics"]}
        require(all(isclose(value, scope["metrics"][name]["value"], rel_tol=1e-15)
                    for name, value in macro.items()), f"macro metrics disagree: {budget}")
        actual.append({"budget_tokens": budget, "metrics": macro, "per_task": per_task})
    return actual


def run_clock(max_seconds):
    require(os.environ.get("FILLER_ID") == ROW, "native execution requires the filler row context")
    deadline = int(os.environ["FILLER_DEADLINE"])
    stopfile = Path(os.environ["FILLER_STOPFILE"])
    end = min(time.monotonic() + deadline - time.time(), time.monotonic() + max_seconds)

    def remaining(cap=MAX_SECONDS):
        duration = min(cap, end - time.monotonic())
        if stopfile.exists() or duration <= 0:
            raise RowStopped("allocator STOP or deadline")
        return duration

    return remaining


def error_prediction(task_id):
    return {"task_id": task_id, "arm": comparator.ARM, "status": "error",
            "pred_files": [], "pred_spans": [], "pack_candidates": []}


def attempt(root, receipt, task, remaining, output, discovery, assembly, *, build, search):
    assets = root / "assets"
    work, task_id = Path(receipt["work"]), task["task_id"]
    source = work / "bases" / task["language"]
    data_home = assets / "bases" / source.name
    binding = receipt["tasks"][task_id]
    require(binding["root"] == str(source) and binding["base_commit"] == task["base_commit"]
            and binding["base_tree"] == base_tree(source, task)
            and binding["query_sha256"] == digest(task["query"].encode()),
            f"pre-build base or query identity drift: {task_id}")
    remaining()
    data_home.mkdir(mode=0o700, parents=True)
    try:
        build(assets, source, data_home, remaining())
    except native.NativeError as exc:
        require(base_tree(source, task) == binding["base_tree"], "source changed during index build")
        return error_prediction(task_id), {"task_id": task_id, "stage": "build", "error": str(exc)}
    remaining()
    index_sha = comparator.directory_digest(data_home)
    sealed = {**binding, "index_data_sha256": index_sha}
    config = {"tasks": {task_id: sealed}, "model": receipt["model"], "app_revision": receipt["app_revision"]}
    comparator.admit_task(work, assets, config, task)
    save(output / f"{source.name}-binding.json", {"task_id": task_id, "binding": sealed})

    def search_bound(query, limit):
        timeout = remaining(comparator.TIMEOUT_S)
        return search(comparator.search_command(assets, source, query, limit), source, data_home, timeout)

    try:
        prediction, evidence = comparator.predict(task, source, search_bound, discovery, assembly)
    except native.IsolationError:
        raise
    except comparator.ERRORS as exc:
        prediction, evidence = error_prediction(task_id), {
            "task_id": task_id, "stage": "retrieval", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        require(base_tree(source, task) == binding["base_tree"], "source changed during retrieval")
        require(comparator.directory_digest(data_home) == index_sha, "sealed index changed during retrieval")
    evidence["binding"] = sealed
    return prediction, evidence


def run_official(root, receipt, admitted, remaining, *, build, search):
    output = root / "native"
    output.mkdir(mode=0o700)
    checkpoints = []
    stop_reason = None
    try:
        with comparator.load_app(Path(receipt["work"]) / "app", admitted.app_sources) as (assembly, discovery, scorer):
            for task in admitted.tasks:
                prediction, evidence = attempt(root, receipt, task, remaining, output, discovery, assembly,
                                               build=build, search=search)
                checkpoint = {"unit": task["task_id"], "task_id": task["task_id"],
                              "prediction": prediction, "evidence": evidence}
                save(output / f"{task['language']}-attempt.json", checkpoint)
                checkpoints.append(checkpoint)
            remaining()
            combined = admitted.baseline + "".join(pilot.encode(item["prediction"]) for item in checkpoints).encode()
            scores = scorer.score_contextbench_bytes(admitted.task_bytes, combined, admitted.dispositions,
                                                     declared_arms=[pilot.ARM, comparator.ARM])
            gold = {item["instance_id"]: item["gold_context"] for item in jsonl(admitted.task_bytes)}
            actual = accounted(scores["arms"][1], checkpoints, gold, [None, *comparator.BUDGETS])
            save(output / "score.json", scores)
            save(output / "actual-colgrep-scopes.json", actual)
    except (RowStopped, *comparator.ERRORS) as exc:
        stop_reason = f"{type(exc).__name__}: {exc}"
    except SystemExit as exc:
        if exc.code != 143:
            raise
        stop_reason = "isolated child cleanup on allocator stop signal"
    finished = {item["task_id"] for item in checkpoints}
    unresolved = [task["task_id"] for task in admitted.tasks if task["task_id"] not in finished]
    result = {
        "row": ROW, "completed": len(checkpoints), "reconciled": stop_reason is None,
        "comparison_valid": stop_reason is None and all(item["prediction"]["status"] != "error"
                                                       for item in checkpoints),
        "observed": [{"task_id": item["task_id"], "status": item["prediction"]["status"]} for item in checkpoints],
        "unknown": unresolved, "stop_reason": stop_reason,
        "outputs_sha256": {path.name: comparator.hash_file(path) for path in sorted(output.iterdir())},
    }
    save(output / "RESULT.json", result)
    return 0 if stop_reason is None else 1


def smoke_path():
    require(os.environ.get("FILLER_SMOKE") == "1" and os.environ.get("FILLER_DRYRUN") == "1",
            "publisher smoke context is required")
    dryrun = Path(os.environ["FILLER_DRYRUN_DIR"])
    smoke_dir = dryrun / ROW
    require(smoke_dir.is_absolute() and smoke_dir.resolve() == smoke_dir, "smoke root must be canonical")
    t0 = os.environ["FILLER_SMOKE_T0"]
    require(re.fullmatch(r"[0-9]{10}", t0) is not None, "invalid publisher smoke time")
    return smoke_dir, t0


def run_smoke(root, remaining, *, build, search):
    assets = root / "assets"
    smoke_dir, t0 = smoke_path()
    smoke_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    marker = smoke_dir / f"smoke-{t0}.json"
    require(not marker.exists(), "publisher smoke marker already exists")
    nonce = uuid4().hex
    fixture = smoke_dir / f"fixture-{t0}-{nonce}"
    fixture.mkdir(mode=0o700)
    path = fixture / FIXTURE_FILE
    path.write_text(FIXTURE_SOURCE)
    path.chmod(0o400)
    fixture.chmod(0o500)
    fixture_sha = comparator.directory_digest(fixture)
    data_home = assets / "bases" / fixture.name
    data_home.mkdir(mode=0o700, parents=True)
    build(assets, fixture, data_home, remaining())
    index_sha = comparator.directory_digest(data_home)
    raw = json.loads(search(comparator.search_command(assets, fixture, FIXTURE_QUERY, comparator.LIMIT),
                            fixture, data_home, remaining(comparator.TIMEOUT_S)))
    hits = comparator.normalize_hits(raw, fixture, comparator.LIMIT, {FIXTURE_FILE})
    require(hits and all(hit["end_line"] <= len(FIXTURE_SOURCE.splitlines()) for hit in hits),
            "publisher smoke did not return a fixture source span")
    require(comparator.directory_digest(data_home) == index_sha
            and comparator.directory_digest(fixture) == fixture_sha,
            "publisher smoke changed the sealed index or fixture")
    save(marker, {"row": ROW, "nonce": nonce, "t0": t0, "fixture": fixture.name, "fixture_sha256": fixture_sha,
                  "index_sha256": index_sha, "hits": hits})


def smoke_completed():
    smoke_dir, t0 = smoke_path()
    marker = smoke_dir / f"smoke-{t0}.json"
    if not marker.is_file():
        return False
    value = json.loads(comparator.regular_path(marker).read_bytes())
    nonce = value.get("nonce", "")
    return (value.get("row") == ROW and value.get("t0") == t0 and re.fullmatch(r"[0-9a-f]{32}", nonce)
            and value.get("fixture") == f"fixture-{t0}-{nonce}"
            and (smoke_dir / value["fixture"] / FIXTURE_FILE).is_file() and bool(value.get("hits")))


def completed(root):
    marker = root / "native/RESULT.json"
    if not marker.is_file():
        return False
    value = json.loads(comparator.regular_path(marker).read_bytes())
    return (value["row"] == ROW and value["completed"] == 3 and value["reconciled"]
            and not value["unknown"] and not value["stop_reason"]
            and {"score.json", "actual-colgrep-scopes.json"}.issubset(value["outputs_sha256"])
            and all(comparator.hash_file(marker.parent / name) == expected
                    for name, expected in value["outputs_sha256"].items()))


def stop_signal(_signum, _frame):
    raise RowStopped("allocator stop signal")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--receipt-sha")
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode in ("precondition", "run", "complete", "smoke"):
        modes.add_parser(mode)
    args = parser.parse_args()
    root = args.root.absolute()
    if args.mode == "smoke":
        return 0 if smoke_completed() else 1
    if args.mode == "complete":
        return 0 if completed(root) else 1
    if (root / "native").exists():
        raise ValueError("official output directory already exists; this row does not retry")
    smoke = os.environ.get("FILLER_SMOKE") == "1"
    if args.mode == "run":
        signal.signal(signal.SIGTERM, stop_signal)
        remaining = run_clock(SMOKE_SECONDS if smoke else MAX_SECONDS)
        remaining()
    require(args.receipt_sha is not None, "expected the prospective preparation receipt SHA-256")
    receipt, admitted = load_preparation(root, args.receipt_sha)
    if args.mode == "precondition":
        return 0
    if smoke:
        run_smoke(root, remaining, build=native.build_index, search=native.search)
        return 0
    return run_official(root, receipt, admitted, remaining, build=native.build_index, search=native.search)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RowStopped, *comparator.ERRORS) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
