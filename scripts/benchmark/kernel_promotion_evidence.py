#!/usr/bin/env python3
"""Capture, compare, and seal observation-only K35 lifecycle evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN_SCRIPTS = str(ROOT / ".claude/skills/kernel-promotion/scripts")
if PLAN_SCRIPTS not in sys.path:
    sys.path.insert(0, PLAN_SCRIPTS)
import resident_plan

ARMS = resident_plan.ARMS
HOT_LIBRARY = re.compile(r"lib(?:ggml|llama|mtmd)[^. /]*\.so(?:\..*)?(?: \(deleted\))?$")
REQUIRED_HOT_LIBRARIES = (
    "libggml-base.so", "libggml-cpu.so", "libggml.so", "libllama.so",
    "libllama-common.so", "libllama-server-impl.so", "libmtmd.so",
)
SCHEMA = "epyc.kernel_promotion_lifecycle_evidence.v1"
OBSERVATION_SCHEMA = "epyc.kernel_promotion_lifecycle_observation.v1"
CPU_LIST = "0-95"
REGIONS = ["q0", "q1", "q2", "q3"]
CALIBRATION_RATIO = (0.99, 1.01)
ORDER_EFFECT_LIMIT = 0.01
ABBA_QUARTET_SIZE = 4


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=resident_plan._unique_object)


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sha(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def observation_source(k35_sha256):
    return {
        "schema": OBSERVATION_SCHEMA,
        "runner_sha256": digest(Path(__file__).with_name("kernel_promotion_resident_runner.py")),
        "validator_sha256": digest(Path(__file__)),
        "planner_sha256": digest(Path(resident_plan.__file__)),
        "k35_sha256": k35_sha256,
    }


def check_observation_source(root, source, pins):
    require(sha(pins["k35_sha256"]) and source == observation_source(pins["k35_sha256"]),
            "lifecycle producer or validator source differs from the installed source")
    records = {}
    for line in (root / "SOURCE.sha256").read_text().splitlines():
        checksum, separator, path = line.partition("  ")
        require(separator and sha(checksum) and path and path not in records,
                "invalid or duplicate source manifest entry")
        records[path] = checksum
    for key, relative in (
        ("runner_sha256", "scripts/benchmark/kernel_promotion_resident_runner.py"),
        ("validator_sha256", "scripts/benchmark/kernel_promotion_evidence.py"),
        ("planner_sha256", ".claude/skills/kernel-promotion/scripts/resident_plan.py"),
        ("k35_sha256", "k35-research.py"),
    ):
        entries = [value for path, value in records.items() if path == relative or path.endswith(f"/{relative}")]
        require(entries == [source[key]], f"source manifest does not uniquely bind {relative}")
    require(pins["arms"].keys() == set(ARMS), "arm identities are incomplete")
    for arm in pins["arms"].values():
        binary = Path(arm["binary_path"])
        require(binary.is_absolute() and binary.name == "llama-server" and sha(arm["binary_sha256"])
                and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", arm["commit"]),
                "arm commit and executable pins are incomplete")
        check_hot_library_pins(arm["libraries"])


def stat_identity(stat):
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def valid_stat(identity):
    return (isinstance(identity, list) and len(identity) == 5
            and all(type(part) is int and part >= 0 for part in identity)
            and identity[1] > 0 and identity[2] > 0)


def valid_model_pin(path, pin):
    return Path(path).is_absolute() and sha(pin["sha256"]) and valid_stat(pin["stat"])


def verify_models(models):
    for path, pin in models.items():
        require(valid_model_pin(path, pin), f"invalid prepared model pin: {path}")
        require(stat_identity(Path(path).stat()) == pin["stat"], f"prepared model changed: {path}")


def check_hot_library_pins(names):
    require(all(any(name == prefix or name.startswith(f"{prefix}.") for name in names)
                for prefix in REQUIRED_HOT_LIBRARIES), "CPU hot-library pins are incomplete")
    require(all(Path(name).name == name and HOT_LIBRARY.fullmatch(name) and sha(expected)
                for name, expected in names.items()), "invalid CPU hot-library pins")


def verify_image_pins(pins, arm, binary):
    image = pins["arms"][arm]
    require(image["binary_path"] == str(binary) and sha(image["binary_sha256"]),
            f"{arm} binary pin differs")
    names = image["libraries"]
    check_hot_library_pins(names)
    for name, expected in names.items():
        path = binary.parent / name
        require(path.resolve(strict=True) == path and digest(path) == expected,
                f"{arm} invalid or changed library pin: {name}")


def map_identities(maps, select=lambda path: HOT_LIBRARY.fullmatch(path.name)):
    identities = {}
    for line in maps.splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) != 6:
            continue
        path = Path(fields[5])
        if not select(path):
            continue
        require(path.is_absolute() and not path.name.endswith(" (deleted)"),
                f"mapped hot library lacks a stable path: {path}")
        major, minor = (int(part, 16) for part in fields[3].split(":"))
        identity = [os.makedev(major, minor), int(fields[4])]
        previous = identities.setdefault(str(path), identity)
        require(previous == identity, f"multiple mapping identities for {path}")
    return identities


def model_mappings(maps, model_paths, pins, *, no_mmap):
    mapped = map_identities(maps, lambda path: str(path).removesuffix(" (deleted)") in model_paths)
    require(no_mmap or mapped.keys() == model_paths, "model mmap witness does not cover every launched model")
    for path, identity in mapped.items():
        require(identity == pins[path]["stat"][:2], f"mapped model differs from prepared inode: {path}")
    return mapped


def file_witness(path, expected, mapped=None):
    with path.open("rb") as stream:
        identity = stat_identity(os.fstat(stream.fileno()))
        require(mapped is None or identity[:2] == mapped, f"mapped inode differs from file: {path}")
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
        require(actual == expected and stat_identity(os.fstat(stream.fileno())) == identity,
                f"live image differs from pin or changed while hashing: {path}")
    return {"stat": identity, "sha256": actual}


def live_image(proc, binary, pin):
    exe = proc / "exe"
    require(exe.resolve(strict=True) == binary, "live executable path differs from pin")
    mappings = map_identities((proc / "maps").read_text())
    expected = {str(binary.parent / name): value for name, value in pin["libraries"].items()}
    require(mappings.keys() == expected.keys(), "live hot-library set differs from the pinned stage")
    return {
        "binary": file_witness(exe, pin["binary_sha256"]),
        "libraries": {path: file_witness(Path(path), expected[path], identity)
                      for path, identity in mappings.items()},
    }


def verify_live_image(proc, image):
    mappings = map_identities((proc / "maps").read_text())
    require(stat_identity((proc / "exe").stat()) == image["binary"]["stat"]
            and mappings == {path: witness["stat"][:2] for path, witness in image["libraries"].items()}
            and all(stat_identity(Path(path).stat()) == witness["stat"]
                    for path, witness in image["libraries"].items()),
            "live executable or hot-library identity changed")


def host_snapshot():
    node_root = Path("/sys/devices/system/node")
    nodes = {node.name: (node / "cpulist").read_text().strip()
             for node in sorted(node_root.glob("node[0-9]*"))}
    return {
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "uptime_s": float(Path("/proc/uptime").read_text().split()[0]),
        "numa_online": (node_root / "online").read_text().strip(),
        "numa_cpus": nodes,
        "cpu_online": Path("/sys/devices/system/cpu/online").read_text().strip(),
        "cpu_model": next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                          if line.startswith("model name")),
        "memory": {line.split(":")[0]: line.split(":", 1)[1].strip()
                   for line in Path("/proc/meminfo").read_text().splitlines()
                   if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:", "SwapFree:"))},
    }


def valid_affinity(affinity, pid, allowed):
    return (isinstance(affinity, dict) and str(pid) in affinity
            and all(tid.isdecimal() and mask and all(type(cpu) is int and cpu in allowed for cpu in mask)
                    for tid, mask in affinity.items()))


def check_server(directory, arm, server, cleanup, pins, host):
    pid = server["pid"]
    cpus = server["allowed_cpus"]
    allowed = set(cpus)
    require(type(pid) is int and pid > 0 and type(server["pgid"]) is int and server["pgid"] == pid
            and type(server["birth"]) is int and server["birth"] > 0 and allowed
            and isinstance(cpus, list) and all(type(cpu) is int and 0 <= cpu < 96 for cpu in cpus)
            and valid_affinity(server["affinity"], pid, allowed),
            "server has incomplete PID/affinity evidence")
    require(type(cleanup["pid"]) is int and cleanup["pid"] == pid
            and cleanup["dead"] is True and cleanup["port_closed"] is True,
            "captured server cleanup is unproved")
    pin = pins["arms"][arm]
    image = server["image"]
    expected = {str(Path(pin["binary_path"]).parent / name): value for name, value in pin["libraries"].items()}
    require(sha(pin["binary_sha256"]) and valid_stat(image["binary"].get("stat"))
            and image["binary"]["sha256"] == pin["binary_sha256"]
            and expected and all(sha(value) for value in expected.values())
            and all(valid_stat(info.get("stat")) for info in image["libraries"].values())
            and {path: info["sha256"] for path, info in image["libraries"].items()} == expected,
            "server image differs from the prepared pins")
    maps = (directory / f"{arm}-maps.txt").read_text()
    require(map_identities(maps) == {path: info["stat"][:2] for path, info in image["libraries"].items()},
            "live map device/inode evidence differs")
    numa = (directory / f"{arm}-numa-maps.txt").read_text()
    require(any(line.split()[1:2] == [f"interleave:{host['numa_online']}"] for line in numa.splitlines()),
            "no live NUMA map exhibits the declared interleave policy")
    argv = read(directory / f"{arm}-argv.json")
    env = read(directory / f"{arm}-env.json")
    require(pin["binary_path"] in argv and "--interleave=all" in argv
            and ("--kv-unified" if pins["kv_mode"] == "unified" else "--no-kv-unified") in argv
            and env["LD_LIBRARY_PATH"] == str(Path(pin["binary_path"]).parent)
            and env["ROCR_VISIBLE_DEVICES"] == env["HIP_VISIBLE_DEVICES"] == "-1",
            "captured argv/environment differs from bound CPU runtime")
    model_paths = {argv[argv.index(flag) + 1] for flag in ("-m", "-md") if flag in argv}
    require(model_paths and model_paths <= pins["models"].keys(), "captured model differs from prepared identity")
    require(server["models"] == model_mappings(maps, model_paths, pins["models"], no_mmap="--no-mmap" in argv),
            "model mapping evidence differs")
    require((directory / f"{arm}-server.log").stat().st_size > 0, "missing server log")


def collect_request(directory, cohort, scheduled, server, *, opened=None):
    row = read(directory / "row.json")
    request_path, response_path = directory / "request.json", directory / "response.json"
    body, response = read(request_path), read(response_path)
    expected = cohort["request_body"] | scheduled.get("request_overrides", {})
    require(resident_plan._canonical_json({key: row[key] for key in scheduled})
            == resident_plan._canonical_json(scheduled)
            and row["request_file_sha256"] == digest(request_path)
            and row["response_file_sha256"] == digest(response_path)
            and resident_plan._canonical_json(expected) == resident_plan._canonical_json(body),
            f"request artifacts differ from the plan: {directory}")
    limit = expected[resident_plan._body_token_limit(expected)]
    observed = row["summary"]
    elapsed = observed["elapsed_s"]
    count = (response.get("usage") or {}).get("completion_tokens") or (response.get("timings") or {}).get("predicted_n")
    require(type(count) is int and type(observed["completion_tokens"]) is int
            and count == observed["completion_tokens"] == limit
            and type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed > 0,
            f"short response or invalid timing: {directory}")
    witness = read(directory / "request-affinity.json")
    affinity_elapsed = witness["query_elapsed_s"]
    offsets = witness["sample_offsets_s"]
    require(type(affinity_elapsed) in (int, float) and math.isfinite(affinity_elapsed)
            and 0 < affinity_elapsed <= elapsed and offsets
            and all(type(sample) in (int, float) and 0 < sample <= affinity_elapsed for sample in offsets)
            and witness["failure"] is None
            and all(valid_affinity(affinity, server["pid"], set(server["allowed_cpus"]))
                    for affinity in (row["active_affinity_before"], row["active_affinity_after"],
                                     witness["first_sample_affinity"])),
            f"missing during-request affinity proof: {directory}")
    if opened is not None:
        require(witness["claim_id"] == opened["claim_id"] and type(witness["provider_pid_starttime"]) is int
                and witness["provider_pid_starttime"] == opened["provider_pid_starttime"]
                and type(witness["http_status"]) is int and 200 <= witness["http_status"] < 300,
                f"request is outside the bound HTTP/CPU claim: {directory}")
        hashes = witness["http_body_sha256"]
        require(hashes.keys() == {"request", "response"}, f"missing HTTP body digests: {directory}")
        for kind, value in (("request", body), ("response", response)):
            path = directory / f"{kind}.http.json"
            require(digest(path) == hashes[kind] and resident_plan._canonical_json(read(path))
                    == resident_plan._canonical_json(value),
                    f"retained HTTP bytes differ from their digest or parsed artifact: {path}")
    if "idle_peer_cpu_s" in row and not scheduled.get("excluded"):
        cpu_s = row["idle_peer_cpu_s"]
        require(type(cpu_s) in (int, float) and 0 <= cpu_s <= max(0.25, 0.01 * elapsed)
                and cpu_s == row["idle_peer_after"]["cpu_s"] - row["idle_peer_before"]["cpu_s"],
                f"invalid idle-peer witness: {directory}")
    return parity_values(body, response, limit)


def parity_values(body, response, limit):
    ids = response.get("tokens")
    if not (isinstance(ids, list) and len(ids) == limit and all(type(token) is int and token >= 0 for token in ids)):
        ids = None
    if "n_predict" in body:
        content = response.get("content")
    else:
        choices = response.get("choices")
        choice = choices[0] if isinstance(choices, list) and len(choices) == 1 else None
        message = choice.get("message") if isinstance(choice, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
    return body, content if isinstance(content, str) else None, ids


def compare(left, right):
    require(resident_plan._canonical_json(left[0]) == resident_plan._canonical_json(right[0]),
            "paired request bodies differ")
    return {
        "body": "exact",
        "content": equality(left[1], right[1]),
        "token_ids": equality(left[2], right[2]),
    }


def equality(left, right):
    if left is None or right is None:
        return "incomplete"
    return "exact" if left == right else "different"


def same_runtime_image(provenance):
    arms = (provenance or {}).get("arms", {})
    production, candidate = (arms.get(arm, {}) for arm in resident_plan.ARMS)
    if "binary_sha256" in production or "binary_sha256" in candidate:
        libraries = production.get("libraries")
        commit = production.get("commit")
        binary_sha = production.get("binary_sha256")
        return bool(
            sha(binary_sha) and binary_sha == candidate.get("binary_sha256")
            and isinstance(libraries, dict) and libraries and libraries == candidate.get("libraries")
            and all(sha(digest) for digest in libraries.values())
            and isinstance(commit, str) and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit)
            and commit == candidate.get("commit")
        )
    path, binary_sha = production.get("path"), production.get("sha256")
    return (isinstance(path, str) and Path(path).is_absolute() and path == candidate.get("path")
            and sha(binary_sha) and binary_sha == candidate.get("sha256"))


def positive_finite(value):
    return type(value) in (int, float) and 0 < value <= sys.float_info.max


def median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    # Adding half the difference keeps the midpoint within the input range.
    if len(ordered) % 2 == 0:
        lower = ordered[middle - 1]
        return lower + (ordered[middle] - lower) / 2
    return ordered[middle]


def median_and_mad(values):
    center = median(values)
    return center, median(abs(value - center) for value in values)


def validity_header(calibration, *, status):
    return {
        "status": status,
        "same_runtime_calibration": calibration,
        "calibration_ratio_bounds": list(CALIBRATION_RATIO),
        "order_effect_limit": ORDER_EFFECT_LIMIT,
        "order_effect_estimator": "per-arm quartet-position medians, abs(earlier-later)/min(earlier,later)",
    }


def summarize_resident_validity(cohort, directory, calibration):
    comparisons, invalid_timing_positions = [], []
    by_arm = {arm: {} for arm in resident_plan.ARMS}
    measured = cohort["requests"]
    for left, right in zip(measured[::2], measured[1::2], strict=True):
        parity_by_arm, tps_by_arm = {}, {}
        for row in (left, right):
            arm, position = row["arm"], row["schedule_position"]
            request_dir = directory / f"request-{position:03}"
            body = read(request_dir / "request.json")
            response = read(request_dir / "response.json")
            parity_by_arm[arm] = parity_values(body, response, body[resident_plan._body_token_limit(body)])
            timings = response.get("timings")
            tps = timings.get("predicted_per_second") if isinstance(timings, dict) else None
            if not positive_finite(tps):
                invalid_timing_positions.append(position)
                tps = None
            by_arm[arm].setdefault(position % ABBA_QUARTET_SIZE, []).append(tps)
            tps_by_arm[arm] = tps
        production_tps, candidate_tps = (tps_by_arm[arm] for arm in resident_plan.ARMS)
        ratio = candidate_tps / production_tps if production_tps is not None and candidate_tps is not None else None
        comparisons.append({
            "pair_index": left["pair_index"],
            "positions_by_arm": {row["arm"]: row["schedule_position"] for row in (left, right)},
            **compare(*(parity_by_arm[arm] for arm in resident_plan.ARMS)),
            "production_tps": production_tps, "candidate_tps": candidate_tps,
            "candidate_over_production": ratio if positive_finite(ratio) else None,
        })
    outcomes = {pair[field] for pair in comparisons for field in ("content", "token_ids")}
    parity = "different" if "different" in outcomes else "incomplete" if "incomplete" in outcomes else "exact"
    ratios = [pair["candidate_over_production"] for pair in comparisons]
    summary = {
        "parity": parity, "median_by_arm": {}, "mad_by_arm": {},
        "median_paired_ratio": None, "mad_paired_ratio": None, "arm_order_bias": {},
        "idle_peer_pass": True, "calibration_ratio_pass": None, "order_effect_pass": None,
        "invalid_timing_positions": invalid_timing_positions, "comparisons": comparisons,
        "violations": [],
    }
    violations = summary["violations"]
    if parity == "different":
        violations.append("exact parity mismatch")
    if None in ratios:
        violations.append("invalid decode timing or ratio")
        return summary
    median_ratio, mad_ratio = median_and_mad(ratios)
    summary["median_paired_ratio"], summary["mad_paired_ratio"] = median_ratio, mad_ratio
    if calibration:
        summary["calibration_ratio_pass"] = CALIBRATION_RATIO[0] <= median_ratio <= CALIBRATION_RATIO[1]
        if not summary["calibration_ratio_pass"]:
            violations.append("incumbent throughput drift")
    summary["order_effect_pass"] = True
    for arm, position_samples in by_arm.items():
        first, second = sorted(position_samples)
        earlier, later = (median(position_samples[position]) for position in (first, second))
        low, high = sorted((earlier, later))
        effect = (high - low) / low
        summary["arm_order_bias"][arm] = {
            "quartet_positions": [first, second],
            "median_tps": [earlier, later],
            "relative_effect": effect if effect <= sys.float_info.max else None,
        }
        if effect > ORDER_EFFECT_LIMIT:
            summary["order_effect_pass"] = False
        values = position_samples[first] + position_samples[second]
        summary["median_by_arm"][arm], summary["mad_by_arm"][arm] = median_and_mad(values)
    if not summary["order_effect_pass"]:
        violations.append("ABBA schedule-position bias")
    return summary


def replay_resident_validity(root, plan, pins, capture):
    calibration = same_runtime_image(pins)
    summaries = []
    cohorts = capture["cohorts"]
    require(len(cohorts) <= len(plan["cohorts"])
            and (not capture["complete"] or len(cohorts) == len(plan["cohorts"])),
            "resident cohort inventory differs from the plan")
    for index, info in enumerate(cohorts):
        cohort = plan["cohorts"][index]
        require(all(info[key] == cohort[key] for key in ("scenario", "nominal_context")),
                "resident cohort identity changed")
        if "validity" not in info:
            require(not capture["complete"] and index == len(cohorts) - 1,
                    "resident validity is missing from a completed cohort")
            break
        summary = summarize_resident_validity(cohort, root / f"cohort-{index:03}", calibration)
        require(resident_plan._canonical_json(info["validity"]) == resident_plan._canonical_json(summary),
                "resident validity does not rederive from the native responses")
        summaries.append(summary)
        require(not summary["violations"] or (not capture["complete"] and index == len(cohorts) - 1),
                "resident capture disposition conflicts with diagnostic violations")
    if summaries and summaries[-1]["violations"]:
        status = "failed"
    elif capture["complete"] and all(summary["parity"] == "exact" for summary in summaries):
        status = "pass"
    else:
        status = "incomplete"
    header = validity_header(calibration, status=status)
    require(resident_plan._canonical_json(header) == resident_plan._canonical_json(capture["resident_validity"]),
            "resident estimator, calibration identity or disposition does not rederive")
    return header


def capture_rows(root, plan, pins, opened, fresh, *, source=None, seen_processes=None):
    mode = "fresh" if fresh else "resident"
    lifecycle = "fresh_server" if fresh else "paired_resident"
    capture = read(root / "capture.json")
    require(capture["schema"] == f"epyc.kernel_promotion_{mode}_capture.v1"
            and capture["status"] == "observation_only" and capture["lifecycle_mode"] == lifecycle
            and capture["schedule_sha256"] == plan["schedule_sha256"]
            and capture["provenance"] == pins
            and resident_plan._canonical_json(read(root / "plan.json")) == resident_plan._canonical_json(plan),
            f"{mode} capture differs from pinned inputs")
    require(read(root / "claim.open.json") == opened and capture["cleanup_proved"] is True,
            f"{mode} capture lacks the bound CPU claim or cleanup")
    if source is not None:
        require(capture["observation_source"] == source and type(capture["complete"]) is bool,
                f"{mode} capture producer identity or completion disposition differs")
        require(("failure" not in capture if capture["complete"] else
                 isinstance(capture.get("failure"), str) and capture["failure"]),
                f"{mode} failure conflicts with the lifecycle disposition")
    options = {"opened": opened} if source is not None else {}
    if capture["complete"] is not True:
        return None
    host = read(root / "host.json")
    after = read(root / "host-after.json")
    stable = ("boot_id", "numa_online", "numa_cpus", "cpu_online", "cpu_model")
    require(all(host[k] and host[k] == after[k] for k in stable) and host["numa_cpus"]
            and after["uptime_s"] >= host["uptime_s"], "host topology changed across capture")
    matrix = (root / "contention-matrix.yaml").read_text()
    check = (root / "contention-matrix.txt").read_text()
    topology = re.search(r'^topology_hash: "?([0-9a-f]+)"?$', matrix, re.MULTILINE)
    require(topology and f"OK: contention matrix is fresh (topology_hash={topology[1][:8]})" in check,
            "missing matching topology freshness witness")
    for arm in ARMS:
        require((root / f"{arm}-linkage.txt").stat().st_size > 0, f"missing {arm} linkage report")
    values = {}
    if seen_processes is None:
        seen_processes = set()
    for index, (cohort, info) in enumerate(zip(plan["cohorts"], capture["cohorts"], strict=True)):
        directory = root / f"cohort-{index:03}"
        require(all(info[key] == cohort[key] for key in ("scenario", "nominal_context")), "cohort identity changed")
        warmups = {warmup["arm"]: warmup for warmup in cohort["warmups"]}
        if not fresh:
            for arm in ARMS:
                server = info["servers"][arm]
                identity = server["pid"], server["birth"]
                require(identity not in seen_processes, "unexpected resident process reuse")
                seen_processes.add(identity)
                check_server(directory, arm, server, info["cleanup"][arm], pins, host)
                collect_request(directory / f"warmup-{arm}", cohort, warmups[arm], server, **options)
        requests = info["requests"] if fresh else cohort["requests"]
        for observed, row in zip(requests, cohort["requests"], strict=True):
            position, arm = row["schedule_position"], row["arm"]
            request_dir = directory / f"request-{position:03}"
            if fresh:
                require(observed["complete"] is True and all(observed.get(k) == v for k, v in row.items()),
                        "fresh request has missing or changed schedule metadata")
                server = observed["server"]
                identity = server["pid"], server["birth"]
                require(identity not in seen_processes, "fresh capture reused a server")
                seen_processes.add(identity)
                check_server(request_dir, arm, server, observed["cleanup"], pins, host)
                collect_request(request_dir / "warmup", cohort, warmups[arm], server, **options)
            else:
                server = info["servers"][arm]
                require("idle_peer_cpu_s" in read(request_dir / "row.json"), "missing resident idle-peer witness")
            key = cohort["scenario"], cohort["nominal_context"], row["pair_index"], position
            values[key] = collect_request(request_dir, cohort, row, server, **options)
        expected_dirs = {f"request-{row['schedule_position']:03}" for row in cohort["requests"]}
        require({p.name for p in directory.glob("request-*")} == expected_dirs,
                "request directory set differs from the plan")
    require({p.name for p in root.glob("cohort-*")} == {f"cohort-{i:03}" for i in range(len(plan["cohorts"]))},
            "cohort directory set differs from the plan")
    return values


def parity_pack(plan, resident, fresh):
    comparisons = []
    captures = {"paired_resident": resident, "fresh_server": fresh}
    for cohort in plan["cohorts"]:
        keys = [(row["scenario"], row["nominal_context"], row["pair_index"], row["schedule_position"])
                for row in cohort["requests"]]
        for mode, values in captures.items():
            if values is None:
                continue
            for left, right in zip(keys[::2], keys[1::2], strict=True):
                comparisons.append({"comparison": mode, "left": left, "right": right,
                                    **compare(values[left], values[right])})
        if resident is not None and fresh is not None:
            for key in keys:
                comparisons.append({"comparison": "resident_vs_fresh", "left": key, "right": key,
                                    **compare(resident[key], fresh[key])})
    outcomes = {item[field] for item in comparisons for field in ("content", "token_ids")}
    verdict = "different" if "different" in outcomes else "incomplete"
    if outcomes == {"exact"} and resident is not None:
        verdict = "exact"
    return {"status": "observation_only", "verdict": verdict, "comparisons": comparisons,
            "resident_complete": resident is not None, "fresh_complete": fresh is not None}


def build_comparison(root):
    pins = read(root / "pins.json")
    plan_path = root / "input-plan.json"
    require(digest(plan_path) == pins["plan_sha256"]
            and digest(root / "SOURCE.sha256") == pins["source_manifest_sha256"],
            "plan or source manifest differs from prepared pins")
    plan = read(plan_path)
    resident_plan.validate_plan(plan)
    model_records = (root / "model.sha256").read_text().splitlines()
    require(pins["models"] and all(valid_model_pin(path, pin) for path, pin in pins["models"].items())
            and sorted(model_records) == sorted(f"{pin['sha256']}  {path}" for path, pin in pins["models"].items()),
            "prepared model digest record differs from pinned identity")
    opened, closed = read(root / "provider.open.json"), read(root / "provider.close.json")
    require(opened["schema"] == closed["schema"] == "region-lock-claim.v1"
            and opened["phase"] == "open" and closed["phase"] == "close"
            and opened["provider"] == "region-lock" and opened["cpu_list"] == CPU_LIST
            and opened["regions"] == REGIONS
            and {item["region"] for item in opened["flock_proof"]} == set(REGIONS)
            and digest(root / "provider.grant") == opened["grant_sha256"]
            and closed["open_sha256"] == digest(root / "provider.open.json")
            and all(opened[k] == closed[k] for k in ("claim_id", "provider_pid", "provider_pid_starttime"))
            and datetime.fromisoformat(opened["grant_start"]) <= datetime.fromisoformat(opened["opened_utc"])
            <= datetime.fromisoformat(closed["closed_utc"]) <= datetime.fromisoformat(opened["grant_end"])
            and closed["child_rc"] in (0, 78), "provider claim closure is unproved")
    resident_root = root / "resident"
    capture = read(resident_root / "capture.json")
    fresh_root = resident_root / "fresh-replay"
    fallback_path = resident_root / "fresh-fallback.json"
    failed = capture["complete"] is not True
    fallback = read(fallback_path) if failed and fallback_path.is_file() else {}
    if failed:
        require(fallback.get("fresh_complete") is True,
                f"resident capture is incomplete and has no complete fresh replay: "
                f"{capture.get('failure') or 'no runner failure recorded'}")
    if (fresh_root / "capture.json").is_file():
        fresh_capture = read(fresh_root / "capture.json")
        require(fresh_capture["complete"] is True,
                f"fresh capture is incomplete: {fresh_capture.get('failure') or 'no runner failure recorded'}")
    source = capture["observation_source"] if "observation_source" in capture else None
    if "observation_source" in capture:
        check_observation_source(root, source, pins)
        dates = [datetime.fromisoformat(receipt[key]) for receipt, key in (
            (opened, "grant_start"), (opened, "opened_utc"), (closed, "closed_utc"), (opened, "grant_end"),
        )]
        require(type(capture["fresh_comparison_requested"]) is bool
                and type(closed["child_rc"]) is int and all(value.utcoffset() is not None for value in dates)
                and isinstance(opened["claim_id"], str) and opened["claim_id"]
                and type(opened["provider_pid"]) is int and type(opened["provider_pid_starttime"]) is int
                and opened["provider_pid"] > 0 and opened["provider_pid_starttime"] > 0,
                "invalid native lifecycle intent, claim identity or exit disposition")
    seen_processes = set() if source is not None else None
    resident = capture_rows(
        resident_root, plan, pins, opened, fresh=False, source=source, seen_processes=seen_processes,
    )
    if failed:
        require(fallback["resident_rows_valid"] is False and fallback["cleanup_proved"] is True
                and fallback["plan"] == plan
                and fallback.get("fresh_capture") == "fresh-replay/capture.json"
                and closed["child_rc"] == 78,
                "fresh replay does not bind a clean resident failure")
        if source is not None:
            require(fallback["schema"] == "epyc.kernel_promotion_fresh_fallback.v1"
                    and fallback["status"] == "observation_only" and fallback["lifecycle_mode"] == "fresh_server"
                    and fallback["reason"] == capture["failure"] and fallback["fresh_attempted"] is True
                    and fallback["requires_fresh_execution"] is False,
                    "native fallback disposition differs from the resident failure")
    else:
        require(closed["child_rc"] == 0, "resident/fresh comparison did not finish")
        if source is not None:
            require(capture["fresh_comparison_requested"] == fresh_root.exists()
                    and not fallback_path.exists(),
                    "fresh replay does not match the resident run intent")
    fresh = None
    if fresh_root.exists():
        fresh = capture_rows(
            fresh_root, plan, pins, opened, fresh=True, source=source, seen_processes=seen_processes,
        )
    require(resident is not None or fresh is not None, "no complete lifecycle capture")
    require(not fresh_root.exists() or fresh is not None, "fresh capture is incomplete")
    report = parity_pack(plan, resident, fresh)
    if source is not None:
        if fresh is not None:
            require(read(fresh_root / "capture.json")["attempted"] is True,
                    "complete fresh capture lacks its attempted disposition")
        report["observation"] = {
            "source": source,
            "schedule_sha256": plan["schedule_sha256"],
            "plan_sha256": pins["plan_sha256"],
            "closed_utc": closed["closed_utc"],
            "model_sha256_by_path": {path: model["sha256"] for path, model in pins["models"].items()},
            "arm_images": pins["arms"],
            "disposition": ("fresh_fallback" if failed else
                            "resident_and_fresh" if fresh is not None else "resident_only"),
            "resident_validity": replay_resident_validity(resident_root, plan, pins, capture),
        }
    return report


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), "invalid evidence directory")
    hashes = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        require(not path.is_symlink() and (path.is_file() or path.is_dir()), f"unsupported evidence path: {path}")
        if path.is_file() and relative not in {"MANIFEST.json", "COMPLETE"}:
            hashes[relative] = digest(path)
    return hashes


def verify(root):
    require(not (root / "MANIFEST.json").is_symlink(), "invalid evidence manifest")
    manifest = read(root / "MANIFEST.json")
    require(not (root / "COMPLETE").is_symlink()
            and (root / "COMPLETE").read_text() == digest(root / "MANIFEST.json") + "\n"
            and manifest["schema"] == SCHEMA and manifest["status"] == "observation_only"
            and manifest["files"] == inventory(root), "evidence seal is incomplete or changed")
    comparisons = build_comparison(root)
    require(resident_plan._canonical_json(read(root / "comparison.json"))
            == resident_plan._canonical_json(comparisons), "sealed comparison does not reproduce")
    return comparisons


def seal(staging, destination):
    require(staging.resolve().parent == destination.resolve().parent and not destination.exists()
            and not destination.is_symlink(), "seal needs a new sibling directory")
    comparison = build_comparison(staging)
    write(staging / "comparison.json", comparison)
    write(staging / "MANIFEST.json", {"schema": SCHEMA, "status": "observation_only", "files": inventory(staging)})
    with (staging / "COMPLETE").open("x") as stream:
        stream.write(digest(staging / "MANIFEST.json") + "\n")
    verify(staging)
    staging.rename(destination)
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--seal-to", type=Path)
    args = parser.parse_args()
    try:
        report = seal(args.capture, args.seal_to) if args.seal_to else verify(args.capture)
        print(json.dumps(report, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
