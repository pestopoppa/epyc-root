#!/usr/bin/env python3
"""Acquire a scoped, observation-only contention pair under a live Rowflow claim."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import shutil
import signal
import socket
import sys
import threading
import time
import uuid

SOURCE = Path(__file__).resolve().parent
sys.path[:0] = [str(SOURCE), str(SOURCE / "m4_cpu_ownership")]
import kernel_promotion_hot_stack_runner as runner
from m4_cpu_producer.native import k35_stack_context_matrix_runner as k35

planner = runner.planner
require = planner.require
SCHEMA = "epyc.kernel_promotion_contention_observation.v1"
PAIR = ((8180, "frontdoor", 2, range(48, 96)), (8086, "worker_vision", 0, range(48)))
ROLE_ORDER = tuple(role for _, role, _, _ in PAIR)
N_PREDICT = 100
REQUEST = {
    "prompt": "Write a 100-word essay analyzing the philosophical implications of autonomous "
              "decision-making in artificial intelligence systems.",
    "n_predict": N_PREDICT,
    "temperature": 0,
    "cache_prompt": False,
}


def select_endpoints(plan):
    endpoints = []
    for port, role, index, cores in PAIR:
        matches = [item for item in plan["endpoints"] if item["canonical_port"] == port]
        require(len(matches) == 1, f"missing or duplicate configured instance on {port}")
        endpoint = matches[0]
        require(endpoint["roles"][0] == role and endpoint["backend"] == "cpu"
                and endpoint["numa_instance"] == index and endpoint["test"] == "chat"
                and endpoint["device"] == "none" and set(endpoint["physical_cpus"]) == set(cores),
                f"CPU instance geometry or recipe changed on {port}")
        endpoints.append(endpoint)
    left, right = endpoints
    require(left["port"] != right["port"], "isolated ports must be distinct")
    return endpoints


def scoped_plan(plan):
    endpoints = select_endpoints(plan)
    ports = {str(endpoint["canonical_port"]): endpoint["port"] for endpoint in endpoints}
    resources = plan["spec"]["resources"] | {"gpu_devices": []}
    return plan | {"endpoints": endpoints, "images": {"cpu": plan["images"]["cpu"]},
                   "spec": plan["spec"] | {"ports": ports, "resources": resources}}


def prepare(packet, directory):
    require(planner.main(["--spec", str(packet / "spec.json"), "--output-dir", str(directory)]) == 0,
            "pinned stack plan preparation failed")
    path = directory / "plan.json"
    plan = planner.read_json(path)
    require(plan["contention_matrix_status"] in ("ok", "stale"),
            "acquisition requires the pinned topology-matched source matrix")
    scoped_plan(plan)
    with (directory / "plan.sha256").open("x") as stream:
        print(planner.digest(path), file=stream)
    return path, plan


def load_prepared(packet):
    path = runner.canonical_file(packet / "prepared" / "plan.json")
    require((path.parent.stat().st_mode & 0o077) == 0, "prepared plan directory must be private")
    plan_sha = runner.canonical_file(path.with_name("plan.sha256")).read_text().strip()
    plan_bytes = path.read_bytes()
    require(hashlib.sha256(plan_bytes).hexdigest() == plan_sha, "prepared plan digest changed")
    plan = json.loads(plan_bytes, object_pairs_hook=planner.unique_keys)
    require(plan["schema"] == planner.PLAN_SCHEMA and plan["status"] == "prepared_only"
            and plan["contention_matrix_status"] in ("ok", "stale"),
            "acquisition requires a prepared, topology-matched source plan")
    return path, plan_sha, plan_bytes, plan


def verify_prepared_inputs(plan):
    spec = plan["spec"]
    root = planner.check_stack_inputs(spec)
    planner.check_pin(Path(planner.__file__), plan["planner_sha256"])
    for relative in planner.LAUNCHER_FILES:
        planner.check_pin(root / relative, plan["launcher_sha256"][relative])
    candidate = spec["candidate"]
    image = planner.verify_stage(candidate["cpu"], candidate, "cpu", planner.production_runtime_dirs())
    require(image == plan["images"]["cpu"], "prepared CPU image identity changed")


def check_workloads(runtime, path):
    # Exclude only live and still owned servers by captured PID, birth, executable and listener.
    owned = {}
    identity_errors = {}
    for server in runtime.servers:
        try:
            runtime.verify_identity(server)
            require(runner.owned.birth(server.pid) == server.birth, "captured PID birth changed")
        except (OSError, ValueError) as exc:
            identity_errors[server.pid] = str(exc)
        else:
            owned[server.pid] = server.birth
    observed = k35.collect_process_blockers()
    foreign = [row for row in observed if row.get("pid") not in owned]
    planner.write_new(path, {"verified": owned, "identity_errors": identity_errors,
                             "observed": observed, "foreign": foreign})
    require(not foreign and not identity_errors, "K35 workload or server identity refusal; see " + path.name)


def leg_timing(status, raw):
    require(status == 200, f"completion returned HTTP {status}")
    result = json.loads(raw, object_pairs_hook=planner.unique_keys)
    timings = result["timings"]
    require(type(timings["predicted_n"]) is int and timings["predicted_n"] == N_PREDICT,
            "completion did not produce the complete fixed-token leg")
    ms = timings["predicted_ms"]
    require(type(ms) in (int, float) and math.isfinite(ms) and ms > 0,
            "completion lacks a positive finite decode duration")
    return ms / 1000


def ratio(frontdoor_s, vision_s, pair_frontdoor_s, pair_vision_s):
    values = frontdoor_s, vision_s, pair_frontdoor_s, pair_vision_s
    require(all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in values),
            "contention ratio requires four complete positive decode durations")
    seq_s = frontdoor_s + vision_s
    parallel_s = max(pair_frontdoor_s, pair_vision_s)
    return {"seq_aggregate_tps": 2 * N_PREDICT / seq_s,
            "parallel_aggregate_tps": 2 * N_PREDICT / parallel_s, "ratio": seq_s / parallel_s}


def complete_scans(states, scans):
    if any("sent" not in state or "headers" not in state for state in states.values()):
        return []
    start = max(state["sent"] for state in states.values())
    end = min(state["headers"] for state in states.values())
    return [scan for scan in scans if start <= scan["start"] < scan["end"] <= end]


def capture_response(response, server, state, directory, sockets, remaining):
    state["headers"] = time.monotonic()
    state["status"] = response.status
    with (directory / f"{server.port}.response.json").open("xb") as stream:
        byte_count = 0
        while not response.isclosed():
            sockets[server.port].settimeout(remaining())
            chunk = response.read1(min(65536, runner.MAX_RESPONSE + 1 - byte_count))
            stream.write(chunk)
            byte_count += len(chunk)
            require(byte_count <= runner.MAX_RESPONSE, "completion exceeded response size limit")
            if not chunk:
                break


def capture_phase(runtime, directory, servers):
    directory.mkdir(mode=0o700)
    check_workloads(runtime, directory / "workloads.json")
    request = directory / "request.json"
    planner.write_new(request, REQUEST)
    request_bytes = request.read_bytes()
    states = {server.port: {} for server in servers}
    sockets = {}
    scans = []
    barrier = threading.Barrier(len(servers))
    abort = threading.Event()
    timeout = runtime.timeout(180)
    deadline = time.monotonic() + timeout

    def remaining():
        seconds = deadline - time.monotonic()
        require(seconds > 0 and not abort.is_set(), "request deadline ended")
        return seconds

    def request_leg(server):
        state = states[server.port]
        connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=min(5, timeout))
        try:
            runtime.verify_identity(server)
            connection.connect()
            sockets[server.port] = connection.sock
            runtime.verify_identity(server)
            barrier.wait(timeout=remaining())
            connection.sock.settimeout(remaining())
            connection.request("POST", "/completion", body=request_bytes,
                               headers={"Content-Type": "application/json"})
            state["sent"] = time.monotonic()
            response = connection.getresponse()
            try:
                capture_response(response, server, state, directory, sockets, remaining)
            finally:
                response.close()
            runtime.verify_identity(server)
            return leg_timing(response.status, (directory / f"{server.port}.response.json").read_bytes())
        except Exception as exc:
            state["failure"] = f"{type(exc).__name__}: {exc}"
            barrier.abort()
            raise
        finally:
            state["finished"] = time.monotonic()
            connection.close()

    try:
        with ThreadPoolExecutor(max_workers=len(servers)) as pool:
            futures = {server.endpoint["roles"][0]: pool.submit(request_leg, server) for server in servers}
            try:
                while not all(future.done() for future in futures.values()):
                    runtime.check()
                    remaining()
                    if (not scans and all("sent" in state and "headers" not in state
                                          for state in states.values())):
                        scan_start = time.monotonic()
                        witnesses = {server.port: runtime.sample(server) for server in servers}
                        scans.append({"start": scan_start, "end": time.monotonic(), "witnesses": witnesses})
                    time.sleep(0.025)
                durations = {role: future.result() for role, future in futures.items()}
            except BaseException:
                abort.set()
                barrier.abort()
                for conn in list(sockets.values()):
                    try:
                        conn.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                raise
    finally:
        scans = complete_scans(states, scans)
        planner.write_new(directory / "requests.json", {"legs": states, "overlap_scans": scans})
    require(scans, "no full custody scan fits inside the common request interval")
    return durations


def finish_cleanup(runtime, observation, result):
    try:
        cleanup = runtime.cleanup() if runtime is not None else {"servers": {}, "spawn_unproved": False}
    except Exception as exc:
        cleanup = {"servers": {}, "spawn_unproved": True, "failure": f"{type(exc).__name__}: {exc}"}
    planner.write_new(observation / "cleanup.json", cleanup)
    result["cleanup_proved"] = runner.cleanup_proved(cleanup)
    if not result["cleanup_proved"]:
        result.update(status="failed", cleanup_failure="captured-PID cleanup was not proved")


def require_live_grant(row_id, environ):
    require(environ.get("FILLER_ID") == row_id
            and not any(environ.get(key) == "1" for key in ("FILLER_SMOKE", "FILLER_DRYRUN", "FILLER_DIRECT")),
            "a real grant for the acquisition row is required")


def run(packet, directory, row_id):
    observation = directory / "observation"
    observation.mkdir(mode=0o700)
    result = {"schema": SCHEMA, "unit_id": row_id, "attempt_id": directory.name, "status": "failed",
              "authority": "observation_only"}
    runtime = None
    previous = {}
    try:
        require_live_grant(row_id, os.environ)
        plan_path, plan_sha, plan_bytes, plan = load_prepared(packet)
        selected = scoped_plan(plan)
        admission = runner.Admission(selected)
        planner.write_new(observation / "admission.json", admission.witness())
        (observation / "prepared-plan.json").write_bytes(plan_bytes)
        planner.write_new(observation / "inputs.json", {
            "plan_sha256": plan_sha, "producer_sha256": planner.digest(Path(__file__)),
            "linkage_sha256": planner.digest(runner.LINKAGE),
            "scope": {"ports": selected["spec"]["ports"], "resources": selected["spec"]["resources"]},
        })
        verify_prepared_inputs(plan)
        planner.write_new(observation / "host.json", runner.evidence.host_snapshot())
        source = planner.ORCHESTRATOR / runner.MATRIX_CONFIG
        source_digest = plan["spec"]["config_sha256"][runner.MATRIX_CONFIG]
        matrix_bytes = source.read_bytes()
        require(hashlib.sha256(matrix_bytes).hexdigest() == source_digest, "source matrix changed")
        with (observation / "source-matrix.yaml").open("xb") as stream:
            stream.write(matrix_bytes)
        runtime = runner.Runtime(selected, plan_path, observation, admission, 780, 180)
        previous = {sig: signal.signal(sig, lambda number, _: setattr(runtime, "interrupted", number))
                    for sig in runner.SIGNALS}
        check_workloads(runtime, observation / "preload-workloads.json")
        runtime.preflight()
        runtime.verify_model_inputs()
        servers = []
        for endpoint in selected["endpoints"]:
            check_workloads(runtime, observation / f'preload-{endpoint["port"]}-workloads.json')
            server = runtime.start(endpoint)
            servers.append(server)
            planner.write_new(observation / f"{server.port}.startup.json", runtime.ready(server))
        solo = {}
        for server in servers:
            role = server.endpoint["roles"][0]
            solo.update(capture_phase(runtime, observation / f"solo-{role}", [server]))
        parallel = capture_phase(runtime, observation / "parallel", servers)
        check_workloads(runtime, observation / "post-requests-workloads.json")
        runtime.check()
        planner.check_stack_inputs(plan["spec"])
        result.update({"status": "captured", "roles": list(ROLE_ORDER),
                       "scope": "isolated_cpu_instance_pair",
                       "instances": [{"role": endpoint["roles"][0], "port": endpoint["port"],
                                      "canonical_port": endpoint["canonical_port"],
                                      "instance_idx": endpoint["numa_instance"]}
                                     for endpoint in selected["endpoints"]],
                       "source_matrix_status_at_prepare": plan["contention_matrix_status"],
                       "source_matrix_sha256": source_digest, "topology_hash": plan["topology_hash"],
                       "plan_sha256": plan_sha, "samples": 1,
                       "decode_s": {"solo": solo, "parallel": parallel},
                       **ratio(*(solo[role] for role in ROLE_ORDER),
                               *(parallel[role] for role in ROLE_ORDER))})
    except Exception as exc:
        result.update(status="failed", failure=f"{type(exc).__name__}: {exc}")
    finally:
        try:
            finish_cleanup(runtime, observation, result)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    if runtime is not None:
        for server in runtime.servers:
            try:
                source = runner.canonical_file(Path(server.endpoint["log"]))
                shutil.copyfile(source, observation / f"{server.port}.server.log")
            except (OSError, ValueError) as exc:
                result.update(status="failed", artifact_failure=str(exc))
    planner.write_new(directory / "result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--acquire", action="store_true")
    mode.add_argument("--validate-inputs", action="store_true")
    mode.add_argument("--dry-run-result", type=Path)
    args = parser.parse_args(argv)
    packet = args.packet.resolve(strict=True)
    row_id = planner.read_json(packet / "row.spec.json")["id"]
    if args.acquire:
        require_live_grant(row_id, os.environ)
    if args.dry_run_result:
        require(os.environ.get("FILLER_DRYRUN") == "1", "dry-run result requires keeper dry-run mode")
        planner.write_new(args.dry_run_result, {"unit_id": row_id, "status": "plumbing_only"})
        return 0
    if args.validate_inputs:
        _, plan = prepare(packet, packet / "prepared")
        print(json.dumps({"source_matrix_status": plan["contention_matrix_status"],
                          "topology_hash": plan["topology_hash"],
                          "ports": scoped_plan(plan)["spec"]["ports"]}))
        return 0
    out = packet / "out"
    out.mkdir(exist_ok=True)
    require(not (out / "RESULT.json").exists(), "acquisition result already exists")
    directory = out / uuid.uuid4().hex
    directory.mkdir(mode=0o700)
    result = run(packet, directory, row_id)
    files = {str(path.relative_to(directory)): planner.digest(path)
             for path in sorted(directory.rglob("*")) if path.is_file()}
    planner.write_new(out / "RESULT.json", result | {"capture_dir": str(directory), "files": files})
    return 0 if result["status"] == "captured" else 2


if __name__ == "__main__":
    raise SystemExit(main())
