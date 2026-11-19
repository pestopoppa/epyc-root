"""Prepare bounded direct-edge capture from sealed DCP-10 GitNexus indexes."""
from __future__ import annotations

import math
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import time
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import gitnexus_compare as graph

common, pilot = graph.common, graph.pilot
SCHEMA = "epyc.dcp10.gitnexus-native-request.v1"
OUTPUT_SCHEMA = "epyc.dcp10.gitnexus-native-edges.v1"
INDEX_BUILD_SCHEMA = "epyc.dcp10.gitnexus-index-build.v1"
WORK = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10")
COLGREP_ROW = "dcp10-colgrep-native-20261118"
COLGREP_R2 = f"{COLGREP_ROW}-r2"
COLGREP_LINEAGE = {
    "revision": 2, "reason": "qualification after native thread limit fix", "prior_row": COLGREP_ROW,
    "prior_preparation_sha256": "66b9f45fc59be61c1f58a3082977718240e0f0f173aac943c2c7f5752ad20950",
    "prior_result_path": str(WORK.parent / "dcp10-colgrep-native/native/RESULT.json"),
    "prior_result_sha256": "f4ba555150a489036d8b79de3f26dc8b92f9074ec60efdddd82204ec1d8fc0e6",
}
WORKER = Path(__file__).with_name("gitnexus_native_worker.mjs").resolve()
IMAGE = "sha256:d9b8c34d61a9b9a3c44cab883d7d2f2619d674966ab520186f799cf32e3e0377"
NODE = Path("/usr/local/bin/node")
NODE_SHA = "94efd062ed066c1a0b332e18249859c905e920eeada5df55d24c99b919629a90"
SOURCE_WRITERS = {
    "dist/core/ingestion/parsing-processor.js": "2c2f9df97937757c2b28c286c5a0a65e6fd530487ca52d773f46c93088a1d006",
    "dist/core/lbug/csv-generator.js": "25b6096fcccaf40f727786c2f12f277407716076d50d7328114741f034c2ddb1",
    "dist/core/lbug/lbug-adapter.js": "36466a35a6fc77fae9329de3506f14e49aa206d5343e08e79371707bb53ad7c2",
    "dist/_shared/index.js": "70c0b3a8abacaeca42f759f32c009755867e0e2a8bec39c59d70372f90b952a3",
}
LADYBUG_FILES = {
    "package.json": "babb4ec62940fe80167c8582e61ce48577ab563b598697718d4b7096b5848239",
    "index.js": "7f01d0781f5bfef08e45d5b05a08deb0cf3b57598fea1123c473a7617f5ed3cb",
    "connection.js": "8cc703f478f55beec45ef628c4609d28eaf54d56d043d05dadad9b550aad2f26",
    "database.js": "95b826985a55ee114301300ae039c7b6818accbd8603e2e4d810ea686b1b83d0",
    "query_result.js": "4e378d17817092029db486719de44756416865af02f415747a87da26c9abff49",
    "prepared_statement.js": "59910c494bafe5162f5736922f4faa04bb91cdbd5875202387a3dbc14ef28999",
    "lbug_native.js": "bf028ed690e7ad6c6f44cf01c6301eb402835de479335ed59d5eb337c2cebdf4",
    "lbugjs.node": "4d2d045404f8e31cd6d5bd8aec0adac64ce5bef8c904ab79408a5a3dbc8dce56",
}
LADYBUG = graph.SOURCE_ROOT / "node_modules/@ladybugdb/core"
MAX_EDGES = 4096
MAX_OUTPUT = 4 * 1024**2
MAX_INDEX = 2 * 1024**3
TIMEOUT = 20
QUERY = f"{graph.GRAPH_QUERY}\nLIMIT {MAX_EDGES + 1}"
QUERY_SHA = sha256(QUERY.encode()).hexdigest()
BASE_FIELDS = {"root", "base_commit", "base_tree", "query_sha256"}


class IsolationError(RuntimeError):
    """Capture must stop because its launch confinement could not be established."""


class QueryError(RuntimeError):
    """The isolated query failed without producing usable graph evidence."""


def producer_identity():
    return {**graph.producer_identity(), Path(__file__).name: common.hash_file(Path(__file__).resolve()),
            WORKER.name: common.hash_file(WORKER)}


def seal_file(path, digest):
    if not isinstance(digest, str) or not re.fullmatch("[a-f0-9]{64}", digest):
        raise ValueError(f"missing SHA-256 pin for {path.name}")
    before = common.regular_path(path).stat()
    common.verify_hash(path, digest)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_ctime_ns):
        raise ValueError(f"sealed input changed while hashing: {path}")
    return (after.st_dev, after.st_ino, after.st_ctime_ns)


def writer_identity():
    verified = graph.source_identity(graph.SOURCE_ROOT)
    for name, digest in SOURCE_WRITERS.items():
        seal_file(graph.SOURCE_ROOT / name, digest)
    return {**verified, "source_sha256": {**verified["source_sha256"], **SOURCE_WRITERS}}


def runtime_identity():
    return {"image": IMAGE, "node_sha256": NODE_SHA, "ladybug_version": "0.15.4",
            "ladybug_sha256": LADYBUG_FILES.copy()}


def read_record(path, expected, max_bytes=64 * 1024):
    if common.regular_path(path).stat().st_size > max_bytes:
        raise ValueError(f"sealed JSON is too large: {path}")
    return graph.strict_json(common.read_sealed(path, expected))


def original_tasks():
    request = read_record(WORK / "packet/request.json", common.ORIGINAL_REQUEST_SHA)
    for name, digest in request["packet_hashes"].items():
        seal_file(WORK / "packet" / name, digest)
    seal_file(WORK / "pilot/predictions.jsonl", common.LEXICAL_PREDICTIONS_SHA)
    pilot.check_worktree(WORK / "app", pilot.APP_REV)
    for name, digest in request["source_hashes"].items():
        seal_file(WORK / "app" / name, digest)
    dispositions = read_record(WORK / "packet/dispositions.json", request["packet_hashes"]["dispositions.json"])
    included = {row["task_id"] for row in dispositions["tasks"] if row["disposition"] == "include"}
    return {task["task_id"]: task for task in request["selected"] if task["task_id"] in included}


def admit_upstream(upstream, row_id, result_sha, tasks):
    if row_id not in (COLGREP_ROW, COLGREP_R2):
        raise ValueError("request does not name an allowed official ColGREP row")
    result = read_record(upstream / "RESULT.json", result_sha)
    fields = {"row", "completed", "reconciled", "comparison_valid", "observed", "unknown", "stop_reason", "outputs_sha256"}
    common.require_fields(result, fields | ({"lineage"} if row_id == COLGREP_R2 else set()), "official ColGREP result")
    if row_id == COLGREP_R2 and result["lineage"] != COLGREP_LINEAGE:
        raise ValueError("ColGREP follow-up lineage differs from the fixed original result")
    if (result["row"] != row_id or type(result["completed"]) is not int
            or result["completed"] != len(tasks) or result["reconciled"] is not True
            or result["comparison_valid"] is not True or result["unknown"] != []
            or result["stop_reason"] is not None):
        raise ValueError("native graph capture requires an admitted complete official ColGREP comparison")
    observed = result["observed"]
    if not isinstance(observed, list) or len(observed) != len(tasks):
        raise ValueError("official ColGREP cohort drift")
    status_by_task = {}
    for task_id, row in zip(tasks, observed, strict=True):
        common.require_fields(row, {"task_id", "status"}, "official ColGREP outcome")
        if row["task_id"] != task_id or row["status"] not in ("ok", "no_context_extracted"):
            raise ValueError("official ColGREP cohort has a missing, reordered or failed attempt")
        status_by_task[task_id] = row["status"]
    outputs = result["outputs_sha256"]
    if not isinstance(outputs, dict):
        raise ValueError("missing official ColGREP output seals")  # noqa: TRY004 - malformed record value
    admitted = {}
    for task_id, task in tasks.items():
        filename = f"{task['language']}-attempt.json"
        attempt = read_record(upstream / filename, outputs.get(filename), max_bytes=512 * 1024)
        common.require_fields(attempt, {"unit", "task_id", "evidence", "prediction"}, "official ColGREP attempt")
        prediction, evidence = attempt["prediction"], attempt["evidence"]
        common.require_fields(prediction, {"task_id", "arm", "status", "pred_files", "pred_spans",
                                           "pack_candidates"}, "official ColGREP prediction")
        if (attempt["unit"] != task_id or attempt["task_id"] != task_id or prediction["task_id"] != task_id
                or prediction["arm"] != common.ARM or prediction["status"] != status_by_task[task_id]
                or not isinstance(evidence, dict) or evidence.get("task_id") != task_id
                or not isinstance(evidence.get("binding"), dict) or not BASE_FIELDS <= evidence["binding"].keys()):
            raise ValueError("official ColGREP task binding drift")
        seeds = prediction["pred_files"]
        if (not isinstance(seeds, list) or len(seeds) > pilot.MAX_FILES
                or any(not isinstance(path, str) or len(path.encode()) > 4096 for path in seeds)
                or len(set(seeds)) != len(seeds) or bool(seeds) != (prediction["status"] == "ok")):
            raise ValueError("invalid official ColGREP seed paths")
        admitted[task_id] = ({key: evidence["binding"][key] for key in BASE_FIELDS}, seeds, outputs[filename])
    return admitted


def index_identity(index, receipt, receipt_sha, *, task_id, base, writer):
    record = read_record(receipt, receipt_sha)
    common.require_fields(record, {"schema", "task_id", "base", "gitnexus_source", "files", "build_manifest_sha256"},
                          "GitNexus index build receipt")
    if (record["schema"] != INDEX_BUILD_SCHEMA or record["task_id"] != task_id
            or record["base"] != base or record["gitnexus_source"] != writer):
        raise ValueError("GitNexus index build receipt does not bind this task, base and source")
    seal_file(receipt.with_suffix(".manifest.json"), record["build_manifest_sha256"])
    files = record["files"]
    common.require_fields(files, {"meta.json", "lbug"}, "GitNexus index files")
    if index.resolve(strict=True) != index or {entry.name for entry in index.iterdir()} != set(files):
        raise ValueError("GitNexus index must contain only checkpointed metadata and database, with no sidecars")
    db = common.regular_path(index / "lbug")
    if not 0 < db.stat().st_size <= MAX_INDEX:
        raise ValueError("empty or oversized GitNexus database")
    metadata = read_record(index / "meta.json", files["meta.json"])
    stats = metadata.get("stats") if isinstance(metadata, dict) else None
    if (not isinstance(stats, dict) or metadata.get("repoPath") != base["root"]
            or metadata.get("lastCommit") != base["base_commit"]
            or any(type(stats.get(key)) is not int or stats[key] < 1 for key in ("files", "nodes"))
            or type(stats.get("edges")) is not int or stats["edges"] < 0
            or type(stats.get("embeddings")) is not int or stats["embeddings"] != 0):
        raise ValueError("GitNexus metadata does not describe this non-embedded base index")
    return {name: seal_file(index / name, digest) for name, digest in files.items()}


def tracked_files(root):
    return {row.split("\t", 1)[1] for row in pilot.git(root, "ls-tree", "-rz", "HEAD").split("\0")
            if row.startswith(("100644 blob ", "100755 blob "))}


def validate_edges(raw, seeds, root, tracked):
    if len(raw) > MAX_OUTPUT:
        raise QueryError("GitNexus output byte bound exceeded")
    try:
        edges = graph.strict_json(raw)
    except (ValueError, UnicodeError) as exc:
        raise QueryError("GitNexus query did not return valid raw edge JSON") from exc
    if not isinstance(edges, list) or len(edges) > MAX_EDGES:
        raise QueryError("GitNexus output row bound or schema violated")
    for edge in edges:
        common.require_fields(edge, graph.EDGE_FIELDS, "raw GitNexus direct edge")
        confidence = edge["confidence"]
        if (type(confidence) not in (int, float) or not graph.CONFIDENCE <= confidence <= 1
                or edge["source_path"] == edge["target_path"]):
            raise ValueError("raw edge does not satisfy the sealed cross-file confidence query")
    graph.ranked_paths(seeds, edges, root=root, tracked=tracked, excluded=lambda _: False)
    return edges


def check_custody(path):
    """Reject aliases, hard-linked files, and path components writable by peers."""
    if path.resolve(strict=True) != path:
        raise IsolationError(f"noncanonical isolated capture path: {path}")
    for component in (path, *path.parents):
        info = component.stat()
        if (info.st_uid not in (0, os.geteuid()) or info.st_mode & 0o022
                or (stat.S_ISREG(info.st_mode) and info.st_nlink != 1)):
            raise IsolationError(f"untrusted isolated capture path component: {component}")


def launch_config(docker, name, mounts, timeout):
    cpus = ",".join(map(str, sorted(os.sched_getaffinity(0))))
    command = [docker, "run", "--rm", "--interactive", "--pull=never", "--name", name, "--runtime=runc",
               "--network=none", "--read-only", "--cap-drop=ALL", "--log-driver=none",
               "--security-opt=no-new-privileges:true", "--pids-limit=64", "--memory=2g", "--memory-swap=2g",
               "--cpus=1", "--cpuset-cpus", cpus, "--user", f"{os.geteuid()}:{os.getegid()}",
               "--workdir=/", "--entrypoint=/usr/bin/timeout"]
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        command.extend(("--env", f"{key}=/dcp10/empty-home"))
    for key in ("NODE_OPTIONS", "NODE_PATH", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        command.extend(("--env", f"{key}="))
    for source, target in mounts:
        if re.search(r'[,\n\r"]', str(source)):
            raise IsolationError("unsupported character in an isolated capture mount")
        command.extend(("--mount", f"type=bind,src={source},dst={target},readonly,bind-recursive=readonly"))
    return [*command, IMAGE, "--foreground", "--signal=KILL", f"{timeout:.3f}s", "/dcp10/node", "/dcp10/worker.mjs"]


def remove_container(docker, name, env):
    try:
        result = subprocess.run([docker, "rm", "-f", name], env=env, capture_output=True, check=False, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        raise IsolationError("could not confirm isolated GitNexus container teardown") from exc
    if result.returncode and b"No such container" not in result.stderr:
        raise IsolationError("could not confirm isolated GitNexus container teardown")


def _stop_on_term(_signal, _frame):
    raise SystemExit(143)


def read_bounded(command, env, payload, timeout):
    deadline = time.monotonic() + timeout
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd="/", env=env) as process, selectors.DefaultSelector() as selector:
        limits = {process.stdout: MAX_OUTPUT, process.stderr: 64 * 1024}
        buffers = {stream: bytearray() for stream in limits}
        pending = memoryview(payload)
        try:
            for stream in (process.stdin, *limits):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_WRITE if stream is process.stdin else selectors.EVENT_READ)
            while selector.get_map():
                time_left = deadline - time.monotonic()
                if time_left <= 0 or not (ready := selector.select(time_left)):
                    raise subprocess.TimeoutExpired(command, timeout)
                for key, _ in ready:
                    stream = key.fileobj
                    if stream is process.stdin:
                        try:
                            pending = pending[os.write(key.fd, pending):]
                        except BrokenPipeError:
                            pending = pending[:0]
                        if pending:
                            continue
                    else:
                        buffer = buffers[stream]
                        chunk = os.read(key.fd, min(64 * 1024, limits[stream] - len(buffer) + 1))
                        if chunk:
                            buffer.extend(chunk)
                            if len(buffer) > limits[stream]:
                                raise QueryError("isolated GitNexus output exceeded the stream byte bound")
                            continue
                    selector.unregister(stream)
                    stream.close()
            status = process.wait(timeout=max(0, deadline - time.monotonic()))
        finally:
            if process.poll() is None:
                process.kill()
        return subprocess.CompletedProcess(command, status, bytes(buffers[process.stdout]), bytes(buffers[process.stderr]))


def launch(mounts, seeds, timeout):
    docker = shutil.which("docker")
    if docker is None or os.geteuid() == 0:
        raise IsolationError("isolated GitNexus requires a local Docker launcher and a non-root user")
    env = {"PATH": os.environ.get("PATH", os.defpath), "LANG": "C.UTF-8",
           "DOCKER_HOST": "unix:///var/run/docker.sock", "DOCKER_CONFIG": "/run/dcp10-no-docker-config"}
    env.update({key: os.environ[key] for key in ("FILLER_ID", "FILLER_STOPFILE") if key in os.environ})
    name = f"dcp10-gitnexus-{uuid4().hex}"
    payload = pilot.encode({"query": QUERY, "seed_paths": seeds, "max_edges": MAX_EDGES,
                            "max_bytes": MAX_OUTPUT, "query_timeout_ms": max(1, int(timeout * 900))}).encode()
    command = launch_config(docker, name, mounts, timeout)
    previous = signal.signal(signal.SIGTERM, _stop_on_term)
    try:
        result = read_bounded(command, env, payload, timeout)
    except (KeyboardInterrupt, SystemExit, QueryError, subprocess.TimeoutExpired) as exc:
        remove_container(docker, name, env)
        if isinstance(exc, subprocess.TimeoutExpired):
            raise QueryError("isolated GitNexus query timed out") from None
        raise
    except OSError as exc:
        remove_container(docker, name, env)
        raise IsolationError("could not start or read isolated GitNexus") from exc
    finally:
        signal.signal(signal.SIGTERM, previous)
    if result.returncode in (125, 126, 127) or result.returncode < 0:
        remove_container(docker, name, env)
        raise IsolationError(f"isolated GitNexus launch failed with exit {result.returncode}")
    if result.returncode:
        raise QueryError(f"isolated GitNexus exited {result.returncode}: {result.stderr[-2048:].decode(errors='replace')}")
    return result.stdout


def capture(assets, request_sha, task_id, remaining):
    """Run one prospective capture and return the record plus its raw stdout for archiving."""
    remaining(TIMEOUT)
    check_custody(assets / "request.json")
    if assets.stat().st_uid != os.geteuid() or assets.stat().st_mode & 0o077:
        raise IsolationError("GitNexus capture assets must live in an owned private directory")
    request = read_record(assets / "request.json", request_sha)
    common.require_fields(request, {"schema", "pilot_request_sha256", "lexical_predictions_sha256", "producer_sha256",
                                    "gitnexus_source", "runtime", "query_sha256", "output_schema", "colgrep_row",
                                    "colgrep_result_sha256", "tasks"}, "native graph request")
    producer, writer = producer_identity(), writer_identity()
    pins = {"schema": SCHEMA, "pilot_request_sha256": common.ORIGINAL_REQUEST_SHA,
            "lexical_predictions_sha256": common.LEXICAL_PREDICTIONS_SHA, "producer_sha256": producer,
            "gitnexus_source": writer, "runtime": runtime_identity(), "query_sha256": QUERY_SHA,
            "output_schema": OUTPUT_SCHEMA}
    if any(request[key] != value for key, value in pins.items()):
        raise ValueError("native graph request drifted from original inputs, source or query")
    tasks = original_tasks()
    common.require_fields(request["tasks"], set(tasks), "original native graph cohort")
    upstream_row, upstream_sha = request["colgrep_row"], request["colgrep_result_sha256"]
    official = admit_upstream(assets / "colgrep", upstream_row, upstream_sha, tasks)
    if task_id not in tasks:
        raise ValueError("capture task is outside the original cohort")
    task, binding = tasks[task_id], request["tasks"][task_id]
    common.require_fields(binding, {"base", "seed_paths", "index_receipt_sha256"}, "native task binding")
    base, seeds, upstream_attempt_sha = official[task_id]
    if binding["base"] != base or binding["seed_paths"] != seeds:
        raise ValueError("graph query base or seed order differs from the admitted ColGREP attempt")
    index = assets / "indexes" / task["language"]
    receipt = assets / "index-builds" / f"{task['language']}.json"
    staged_worker = assets / WORKER.name
    mounts = [(index, "/dcp10/index"), (staged_worker, "/dcp10/worker.mjs"), (NODE, "/dcp10/node")]
    mounts.extend((LADYBUG / name, f"/dcp10/ladybug/{name}") for name in LADYBUG_FILES)

    def verify_snapshot():
        root = graph.bind_task(WORK, task, base)
        for path, _ in mounts:
            check_custody(path)
        check_custody(receipt)
        inputs = index_identity(index, receipt, binding["index_receipt_sha256"], task_id=task_id, base=base, writer=writer)
        for name in inputs:
            check_custody(index / name)
        inputs[str(NODE)] = seal_file(NODE, NODE_SHA)
        inputs[str(staged_worker)] = seal_file(staged_worker, producer[WORKER.name])
        for name, digest in LADYBUG_FILES.items():
            inputs[name] = seal_file(LADYBUG / name, digest)
        return root, inputs

    root, snapshot = verify_snapshot()
    tracked = tracked_files(root)
    for seed in seeds:
        graph.check_path(seed, root, tracked)
    record = {"schema": OUTPUT_SCHEMA, "request_sha256": request_sha, "task_id": task_id, "base": base,
              "index_receipt_sha256": binding["index_receipt_sha256"], "colgrep_row": upstream_row,
              "colgrep_result_sha256": upstream_sha,
              "colgrep_attempt_sha256": upstream_attempt_sha, "query_sha256": QUERY_SHA, "seed_paths": seeds,
              "raw_stdout_sha256": None, "edges": [], "error": None}
    timeout = remaining(TIMEOUT)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0.001 <= timeout <= TIMEOUT:
        raise ValueError("invalid or exhausted native graph launch budget")
    if not seeds:
        return {**record, "status": "no_seeds"}, None
    try:
        raw = launch(mounts, seeds, timeout)
    except QueryError as exc:
        return {**record, "status": "error", "error": str(exc)}, None
    finally:
        if verify_snapshot() != (root, snapshot) or producer_identity() != producer or writer_identity() != writer:
            raise IsolationError("sealed GitNexus checkout, index or source changed during the query")
        remaining(TIMEOUT)
    try:
        edges = validate_edges(raw, seeds, root, tracked)
    except QueryError as exc:
        return {**record, "status": "error", "error": str(exc)}, None
    return {**record, "status": "ok" if edges else "empty", "edges": edges,
            "raw_stdout_sha256": sha256(raw).hexdigest()}, raw
