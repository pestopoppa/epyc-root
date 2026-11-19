"""Bind request identity and retained sampled-placement evidence to a floor.

This is structural custody only. Procfs samples do not prove continuous
placement or lack of contention, and the separate native observer functional
qualification does not change that limit.
"""
import hashlib
import json


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _validate_observation(event, prompt_id, prompt_sha, launch_ordinal=None, phase=None, *, runtime_prepared):
    if event.get("prompt_id") != prompt_id or event.get("request_sha256") != prompt_sha:
        raise ValueError("request event does not match the pinned prompt identity")
    if event.get("status") != "observed-at-boundaries":
        raise ValueError("request boundary is incomplete")
    if (event.get("placement_observation") != "sampled-during-request"
            or event.get("placement_continuous") != "unproven"
            or event.get("contention_continuous") != "unproven"
            or event.get("no_inference_scope") != "sanctioned-claim-witness-only"):
        raise ValueError("request observation claim scope differs")
    target = event.get("target")
    if (not isinstance(target, dict) or type(target.get("pid")) is not int
            or target["pid"] <= 0 or type(target.get("start_ticks")) is not int
            or target["start_ticks"] < 0 or not isinstance(target.get("boot_id"), str)
            or not target["boot_id"]):
        raise ValueError("request target identity is incomplete")
    before, after = event.get("before"), event.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("request boundary snapshots are missing")
    for edge in (before, after):
        if edge.get("target") != target or not isinstance(edge.get("tasks"), dict):
            raise ValueError("request boundary target identity differs")
        if not isinstance(edge.get("global_holders"), dict) or not edge["global_holders"]:
            raise ValueError("request boundary claim-owner snapshot is missing")
        if (not isinstance(edge.get("preflight"), dict)
                or edge["preflight"].get("verdict") != "PASS"):
            raise ValueError("request boundary preflight is not PASS")
    from runtime_linkage import bind_prepared
    for edge in (before, after):
        runtime = edge.get("runtime_linkage")
        if (not isinstance(runtime, dict) or runtime.get("target") != target
                or runtime.get("status") != "matching-c5-mapped-inodes"
                or runtime.get("coverage") != "point-in-time-only"
                or runtime.get("measurement_admission") != "none"):
            raise ValueError("runtime map receipt scope or target mismatch")
        rebound = bind_prepared(runtime, runtime_prepared)
        if runtime.get("prepared_sha256") != rebound["prepared_sha256"]:
            raise ValueError("runtime map digests do not match prevalidated binaries")
    if before["runtime_linkage"] != after["runtime_linkage"]:
        raise ValueError("runtime map changed across request boundaries")
    if before["tasks"] != after["tasks"] or before["global_holders"] != after["global_holders"]:
        raise ValueError("request boundary task or claim-owner state changed")
    window = event.get("placement_window_ns")
    samples = event.get("placement_samples")
    if (not isinstance(window, list) or len(window) != 2
            or any(type(x) is not int for x in window) or window[0] <= 0 or window[0] >= window[1]
            or not isinstance(samples, list) or not 2 <= len(samples) <= 4096):
        raise ValueError("request placement sample window is invalid")
    previous = 0
    identity = (target["pid"], target["start_ticks"])
    topology = None
    for sample in samples:
        stamp = sample.get("monotonic_ns")
        if (type(stamp) is not int or not window[0] <= stamp <= window[1]
                or stamp <= previous or sample.get("pid") != identity[0]
                or sample.get("start_ticks") != identity[1]):
            raise ValueError("placement sample time or target identity differs")
        previous = stamp
        topo = sample.get("topology")
        tasks = sample.get("tasks")
        if not isinstance(topo, dict) or not topo or not isinstance(tasks, dict) or not tasks:
            raise ValueError("placement sample lacks topology or task census")
        if topology is None:
            topology = topo
        elif topo != topology:
            raise ValueError("placement topology changed within request")
        for tid, task in tasks.items():
            if (not str(tid).isdigit() or not isinstance(task, dict)
                    or type(task.get("cpu")) is not int
                    or str(task["cpu"]) not in topo
                    or type(task.get("node")) is not int
                    or task["node"] != topo[str(task["cpu"]) ]):
                raise ValueError("placement task sample does not bind to topology")
    from journal_writer import validate_writer_check
    validate_writer_check(event)
    from request_observer_join import validate_receipt
    ordinal = event.get("launch_ordinal", launch_ordinal)
    phase_name = event.get("phase", phase)
    context = {"launch_ordinal": ordinal, "phase": phase_name,
               "slot_index": event.get("slot_index", 0),
               "prompt_id": event["prompt_id"],
               "request_sha256": event["request_sha256"]}
    validate_receipt(event.get("native_observer"), request_context=context,
                     target=target, placement_window_ns=window)
    from census_receipt import read_event
    census_event = dict(event, **context)
    read_event(census_event)


def bind_request_boundaries(row, events, frozen_requests, *, runtime_prepared):
    """Attach per-launch request identity and phase records before floor sealing.

    CH-26b uses np=1. Each owned process must therefore emit exactly one warmup and
    one measurement boundary record. The calibration plan determines each process's
    pair and arm; event order alone never determines the scientific arm identity.
    """
    if row.get("schema") != "epyc.autokernel.serving_floor.v2":
        raise ValueError("unexpected floor schema")
    plan = row.get("calibration_plan") or {}
    orders = plan.get("orders")
    pairs = row.get("calibration_pairs")
    if not isinstance(orders, list) or len(orders) != pairs or pairs != 24:
        raise ValueError("floor plan does not declare the fixed 24-pair unit")
    if row.get("comparison_pairs") != 5 or row.get("np") != 1:
        raise ValueError("floor does not match the declared CH-26b comparison/slot count")
    if not isinstance(frozen_requests, (list, tuple)) or len(frozen_requests) != 1:
        raise ValueError("CH-26b requires the pinned single frozen request")
    prompt_id, body = frozen_requests[0]
    prompt_sha = hashlib.sha256(body).hexdigest()
    expected_launches = []
    for pair_index, order in enumerate(orders):
        if sorted(order) != ["anchor", "candidate"]:
            raise ValueError("matched calibration plan has invalid pair order")
        for arm in order:
            expected_launches.append({"launch_ordinal": len(expected_launches) + 1,
                                      "pair_index": pair_index, "arm": arm})
    if len(events) != len(expected_launches) * 2:
        raise ValueError("request-boundary count does not equal two phases per process")
    by_launch = {}
    observer_ids = set()
    for event in events:
        ordinal = event.get("launch_ordinal")
        if type(ordinal) is not int or not 1 <= ordinal <= len(expected_launches):
            raise ValueError("request event has invalid launch ordinal")
        phase = event.get("phase")
        if phase not in ("warmup", "measurement") or event.get("slot_index") != 0:
            raise ValueError("request event has unexpected phase or slot")
        _validate_observation(event, prompt_id, prompt_sha, ordinal, phase, runtime_prepared=runtime_prepared)
        observer_id = event["native_observer"]["observer_id"]
        if observer_id in observer_ids:
            raise ValueError("duplicate native observer receipt ID")
        observer_ids.add(observer_id)
        key = (ordinal, phase)
        if key in by_launch:
            raise ValueError("duplicate request boundary for launch and phase")
        by_launch[key] = event
    launches = []
    for expected in expected_launches:
        ordinal = expected["launch_ordinal"]
        phases = {}
        for phase in ("warmup", "measurement"):
            event = by_launch.get((ordinal, phase))
            if event is None:
                raise ValueError("missing request boundary for launch and phase")
            phases[phase] = {
                "status": event["status"],
                "prompt_id": event["prompt_id"],
                "request_sha256": event["request_sha256"],
                "target": event["target"],
                "before": event["before"],
                "after": event["after"],
                "placement_window_ns": event["placement_window_ns"],
                "placement_samples": event["placement_samples"],
                "native_observer": event["native_observer"],
                "writer_check": event["writer_check"],
                "host_census": event["host_census"],
                "measurement_admission": event["measurement_admission"],
                "placement_observation": event["placement_observation"],
                "placement_continuous": event["placement_continuous"],
                "contention_continuous": event["contention_continuous"],
                "no_inference_scope": event["no_inference_scope"],
            }
        launches.append({**expected, "phases": phases})
    binding = {"schema": "epyc.ch26b.request_floor_binding.v1",
               "request_digest": row.get("request_digest"),
               "launch_count": len(launches), "request_count": len(events),
               "runtime_prepared_sha256": _digest(runtime_prepared),
               "launches": launches}
    if not binding["request_digest"]:
        raise ValueError("floor lacks request digest")
    binding["content_sha256"] = _digest(binding)
    result = dict(row)
    result.pop("content_sha256", None)
    result["request_binding"] = binding
    result["content_sha256"] = _digest(result)
    return result


def verify_bound_receipt(row, *, runtime_prepared):
    binding = row.get("request_binding")
    if not isinstance(binding, dict):
        return False
    binding_copy = dict(binding)
    binding_digest = binding_copy.pop("content_sha256", None)
    row_copy = dict(row)
    row_digest = row_copy.pop("content_sha256", None)
    if not (binding_digest == _digest(binding_copy)
            and row_digest == _digest(row_copy)
            and binding.get("schema") == "epyc.ch26b.request_floor_binding.v1"
            and binding.get("launch_count") == 48
            and binding.get("request_count") == 96
            and binding.get("runtime_prepared_sha256") == _digest(runtime_prepared)
            and len(binding.get("launches", [])) == 48):
        return False
    seen = set()
    observer_ids = set()
    for launch in binding["launches"]:
        if (type(launch.get("launch_ordinal")) is not int
                or not 1 <= launch["launch_ordinal"] <= 48
                or launch.get("arm") not in ("anchor", "candidate")
                or not isinstance(launch.get("phases"), dict)
                or set(launch["phases"]) != {"warmup", "measurement"}):
            return False
        if launch["launch_ordinal"] in seen:
            return False
        seen.add(launch["launch_ordinal"])
        for phase_name, phase in launch["phases"].items():
            try:
                _validate_observation(phase, phase["prompt_id"], phase["request_sha256"],
                                      launch["launch_ordinal"], phase_name, runtime_prepared=runtime_prepared)
                observer_id = phase["native_observer"]["observer_id"]
                if observer_id in observer_ids:
                    return False
                observer_ids.add(observer_id)
            except (KeyError, TypeError, ValueError, OSError):
                return False
    return len(seen) == 48
