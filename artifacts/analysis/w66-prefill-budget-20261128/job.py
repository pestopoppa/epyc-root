"""Compare the stock C22 prefill controller on two pinned W66 streams."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import statistics
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
ARCHIVE = Path("/mnt/raid0/llm/archive/compute-evidence/ap-w66-pair-20261127-r2")
ARCHIVED_RUN = ARCHIVE / "r2/out/run"
ARM_FLAGS = {"control": ("--prefill-budget-decoding", "0", "--prefill-budget-target-ms", "0"),
             "budget": ("--prefill-budget-decoding", "256", "--prefill-budget-target-ms", "900")}
TARGET_COUNT = {"ON28": (38, 75077), "OFF56": (107912, 4334)}
PREFIX_SHA = "d387b46340e2f82c23008681facbf83b9cc15698aad65e790c11fa4fb03fcb0d"
REPLAY_SHA = "de726115ef8ef36a6791e07855413389a1be2cce14f63031892cf617732d8cd2"
CAP = 256
PEER_CEILING = 1.30
P99_TARGET_MS = 900
ITERATION = re.compile(r"prefill-budget: iter (\d+): decode_rows = (\d+) \(slots (\d+)\), "
                       r"prompt = (\d+) \(slots (\d+)\), budget = (\d+), "
                       r"t_iter = ([\d.]+) ms, kv_pos = (\d+), ms/tok = ([\d.]+)")


def load_endpoint():
    source = HERE / "replay_endpoint.py"
    spec = importlib.util.spec_from_file_location("replay_endpoint", source)
    endpoint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(endpoint)
    if endpoint.digest_file(source) != REPLAY_SHA:
        raise RuntimeError("reused endpoint source does not match its sealed replay")
    return endpoint


def load_states(replay):
    manifest = ARCHIVE / "SHA256SUMS"
    pins = {}
    for line in manifest.read_text().splitlines():
        digest, path = line.split("  ", 1)
        pins[path] = digest
    prefixes = ARCHIVE / "r2/prefixes.json"
    if replay.digest_file(prefixes) != pins["r2/prefixes.json"] or pins["r2/prefixes.json"] != PREFIX_SHA:
        raise RuntimeError("archived guarded token arrays failed verification")
    prefixes = json.loads(prefixes.read_text())
    states = {}
    for label, (fresh, cached) in TARGET_COUNT.items():
        path = ARCHIVED_RUN / f"{label}.state.json"
        if replay.digest_file(path) != pins[str(path.relative_to(ARCHIVE))]:
            raise RuntimeError(f"archive state receipt mismatch for {label}")
        state = json.loads(path.read_text())
        prefix = prefixes[label]
        check = state["prefix_check"]
        if (check["prefix_sha256"] != prefix["prefix_ids_sha256"]
                or check["prompt_sha256"] != prefix["prompt_ids_sha256"]
                or (prefix["prompt_count"], prefix["prefix_count"]) != (fresh + cached, cached)
                or state["save"]["n_saved"] != cached or state["slot"] != prefix["slot"]):
            raise RuntimeError(f"archived state has wrong prompt or cache for {label}")
        for file in state["files"]:
            relative = f'r2/out/run/private/slots/{file["name"]}'
            if pins[relative] != file["sha256"] or (ARCHIVE / relative).stat().st_size != file["bytes"]:
                raise RuntimeError(f"archived snapshot identity differs for {label}")
        states[label] = state
    return states, replay.digest_file(manifest)


def restore_visits(endpoint, states):
    slots = endpoint.raw / "slots"
    for state in states.values():
        for file in state["files"]:
            source = ARCHIVED_RUN / "private/slots" / file["name"]
            (slots / file["name"]).symlink_to(source)
    # C22's restore action opens the state and its trailers for reading. The runner
    # only sends restore and erase for these paths. Each erase affects RAM.
    return {label: endpoint.restore(state) for label, state in states.items()}


def run_streams(endpoint, name):
    first = threading.Event()
    payloads = {label: endpoint.inputs.payload(label, limit=CAP, fixed=True) for label in TARGET_COUNT}
    with ThreadPoolExecutor(max_workers=2) as pool:
        on_run = pool.submit(endpoint.stream, f"{name}-on28", "ON28", payloads["ON28"], first)
        while not first.wait(.025) and not on_run.done():
            endpoint.check()
        if not first.is_set() or on_run.done():
            raise RuntimeError("ON28 did not reach peer launch trigger during its decode")
        off_run = pool.submit(endpoint.stream, f"{name}-off56", "OFF56", payloads["OFF56"])
        rows = {"ON28": on_run.result(), "OFF56": off_run.result()}
    for label, (fresh, cached) in TARGET_COUNT.items():
        row = rows[label]
        n = row["native"]
        if (n["prompt_n"], n["cache_n"], n["predicted_n"], row["finish_reason"]) != (
                fresh, cached, CAP, "length"):
            raise RuntimeError(f"target framing, cache, or fixed cap differs for {label}: {n}")
    return rows


def native_iterations(log, visit_start, arm):
    iterations = []
    with log.open() as handle:
        for line_no, line in enumerate(handle, 1):
            if line_no <= visit_start:
                continue
            found = ITERATION.search(line)
            if not found:
                continue
            iteration, decode, decoding_slots, prompt, prefill_slots, budget, elapsed, kv, cost = found.groups()
            mixed = bool(int(decode) and int(decoding_slots) and int(prompt) and int(prefill_slots))
            if mixed:
                if arm == "budget" and not 64 <= int(budget) <= 256:
                    raise RuntimeError(f"unexpected native treatment budget at iteration {iteration}")
                if arm == "budget" and int(prompt) > min(int(budget), 2048 - int(decode)):
                    raise RuntimeError(f"native treatment exceeded its budget at iteration {iteration}")
                if arm == "control" and int(budget):
                    raise RuntimeError(f"unexpected applied budget in control at iteration {iteration}")
            iterations.append({"log_line": line_no, "iteration": int(iteration),
                               "decode_rows": int(decode), "decoding_slots": int(decoding_slots),
                               "prompt_tokens": int(prompt), "prefilling_slots": int(prefill_slots),
                               "budget_tokens": int(budget), "iteration_ms": float(elapsed),
                               "kv_positions": int(kv), "ema_ms_per_prompt_token": float(cost),
                               "mixed": mixed})
    result = [row for row in iterations if row["mixed"]]
    if not result:
        raise RuntimeError(f"no genuinely mixed iterations in {arm}")
    if arm == "control" and max(row["prompt_tokens"] for row in result) <= 256:
        raise RuntimeError("control never demonstrated a larger prefill chunk")
    if arm == "budget" and result[0]["budget_tokens"] != 256:
        raise RuntimeError("first mixed iteration does not match unseeded treatment")
    pre_mixed = [row for row in iterations if row["iteration"] < result[0]["iteration"]]
    if (sum(row["prompt_tokens"] for row in pre_mixed) != TARGET_COUNT["ON28"][0]
            or any(row["ema_ms_per_prompt_token"] for row in pre_mixed)):
        raise RuntimeError("controller was seeded before the first mixed iteration")
    native_prompt_total = sum(row["prompt_tokens"] for row in iterations)
    if native_prompt_total != sum(fresh for fresh, _ in TARGET_COUNT.values()):
        raise RuntimeError(f"native iterations account for {native_prompt_total} prompt tokens")
    times = sorted(row["iteration_ms"] for row in result)
    mixed_prompt = sum(row["prompt_tokens"] for row in result)
    return {"count": len(times), "nearest_rank_p99_ms": times[math.ceil(.99 * len(times)) - 1],
            "worst_ms": times[-1], "mean_ms": statistics.mean(times),
            "prefill_tokens": mixed_prompt,
            "ordinary_peer_prefill_tokens": TARGET_COUNT["OFF56"][0] - mixed_prompt,
            "first_mixed_iteration": result[0],
            "pre_mixed_iterations": pre_mixed,
            "decode_rows": sum(row["decode_rows"] for row in result), "rows": iterations}


def core_metrics(replay, rows, mixed):
    target, peer = rows["ON28"], rows["OFF56"]
    native = replay.reductions([target, peer])
    phase = native["monotonic_s"]
    on_decode = phase[target["name"]]["decode"]
    off_prefill = phase[peer["name"]]["prefill"]
    both_end = max(target["end_ns"], peer["end_ns"])
    return {"on28_decode_s": target["native"]["predicted_ms"] / 1000,
            "on28_wall_s": target["wall_s"], "on28_ttft_s": target["ttft_s"],
            "off56_ttft_s": peer["ttft_s"], "off56_wall_s": peer["wall_s"],
            "off56_prefill_s": peer["native"]["prompt_ms"] / 1000,
            "both_finish_s_since_on28_forward": (both_end - target["forward_ns"]) / 1e9,
            "peer_forward_offset_s": (peer["forward_ns"] - target["forward_ns"]) / 1e9,
            "peer_prefill_during_on28_decode_approx_s": replay.overlap(on_decode, off_prefill),
            "mixed_iteration_p99_ms": mixed["nearest_rank_p99_ms"],
            "mixed_iteration_worst_ms": mixed["worst_ms"],
            "phase_reduction": native}


def one_visit(replay, inputs, states, all_out, pair, arm, interrupted, smoke=False):
    name = f"p{pair}-{arm}"
    out = all_out / name
    out.mkdir()
    endpoint = replay.Endpoint(out, inputs)
    interrupted["endpoint"] = endpoint
    archived_argv = inputs.trace["historical_runtime"]["argv"]
    inputs.trace["historical_runtime"]["argv"] = archived_argv + list(ARM_FLAGS[arm])
    begin = time.monotonic()
    try:
        endpoint.start()
        loads = time.monotonic() - begin
        if smoke:
            outcome = replay.smoke(endpoint)
            restores = restore_visits(endpoint, states)
            return {"name": name, "loads_s": loads, "probe": outcome, "restores": restores}
        restores = restore_visits(endpoint, states)
        # C22's startup warm-up is the same in every visit. The first user-facing
        # request here has 38 fresh tokens, below the EMA update threshold of 64.
        log = endpoint.raw / "server.log"
        with log.open() as handle:
            line_before = sum(1 for _ in handle)
        rows = run_streams(endpoint, name)
        mixed = native_iterations(log, line_before, arm)
        receipt = {"name": name, "arm": arm, "controller_argv": ARM_FLAGS[arm],
                   "loads_s": loads, "snapshot_restores": restores, "streams": rows,
                   "mixed": mixed, "metrics": core_metrics(replay, rows, mixed)}
        replay.save_json(out / "visit.json", receipt)
        return receipt
    finally:
        inputs.trace["historical_runtime"]["argv"] = archived_argv
        try:
            endpoint.close()
        finally:
            interrupted["endpoint"] = None


def interpret(pairs):
    keys = ("on28_decode_s", "off56_ttft_s", "both_finish_s_since_on28_forward", "mixed_iteration_p99_ms")
    result = {}
    for key in keys:
        control = [pair["control"]["metrics"][key] for pair in pairs]
        budget = [pair["budget"]["metrics"][key] for pair in pairs]
        noise = max(max(control) - min(control), max(budget) - min(budget))
        change = [b - a for a, b in zip(control, budget)]
        result[key] = {"control": control, "budget": budget, "budget_minus_control": change,
                       "same_arm_max_range": noise,
                       "all_lower_beyond_range": all(x < -noise for x in change),
                       "all_higher_beyond_range": all(x > noise for x in change),
                       "all_inside_range": all(abs(x) <= noise for x in change)}
    ratios = [pair["budget"]["metrics"]["off56_ttft_s"] / pair["control"]["metrics"]["off56_ttft_s"]
              for pair in pairs]
    on = result["on28_decode_s"]
    ttft = result["off56_ttft_s"]
    joint = result["both_finish_s_since_on28_forward"]
    p99 = result["mixed_iteration_p99_ms"]
    joint_answered = any(joint[key] for key in
                         ("all_lower_beyond_range", "all_higher_beyond_range", "all_inside_range"))
    return {"effects": result, "off56_ttft_ratio": ratios, "off56_ttft_ratio_limit": PEER_CEILING,
            "mixed_iteration_p99_target_ms": P99_TARGET_MS,
            "off56_ttft_ceiling_pass": all(ratio <= PEER_CEILING for ratio in ratios),
            "budget_p99_target_pass": all(value <= P99_TARGET_MS for value in p99["budget"]),
            "stop_futility": len(pairs) >= 2 and all(ratio > PEER_CEILING for ratio in ratios)
                           and ttft["all_higher_beyond_range"],
            "stop_on_answer": len(pairs) >= 2 and on["all_lower_beyond_range"] and joint_answered
                           and (all(ratio <= PEER_CEILING for ratio in ratios)
                                or all(ratio > PEER_CEILING for ratio in ratios))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--validate", action="store_true")
    cli = parser.parse_args()
    replay = load_endpoint()
    replay.ROOT = cli.root
    inputs = replay.Inputs()
    states, archive_sha = load_states(replay)
    if cli.validate:
        print(json.dumps({"archive_manifest_sha256": archive_sha,
                          "cache": {key: state["save"]["n_saved"] for key, state in states.items()}}))
        return
    os.umask(0o077)
    os.environ.pop("LLAMA_ARG_PREFILL_BUDGET_DECODING", None)
    os.environ.pop("LLAMA_ARG_PREFILL_BUDGET_TARGET_MS", None)
    smoke_mode = os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1"
    out = HERE / "out" / ("smoke" if smoke_mode else "run")
    out.mkdir(parents=True)
    interrupted = {"endpoint": None, "signaled": False}

    def stop(*_):
        interrupted["signaled"] = True
        if interrupted["endpoint"]:
            interrupted["endpoint"].stop.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if smoke_mode:
        sys.path.insert(0, replay.ROWFLOW_SUPPORT)
        import ak_row_harness
        try:
            receipt = one_visit(replay, inputs, states, out, 0, "budget", interrupted, smoke=True)
            replay.save_json(out / "receipt.json", receipt)
            unit_s = receipt["probe"]["first"]["wall_s"]
            ak_row_harness.write_smoke_measure("out/smoke", unit_s, 1, receipt["loads_s"],
                                               "stream and restore qualification probe")
            ak_row_harness.end_smoke("PASS", 0, "C22 controller argument load, streaming and sealed slot restores",
                                     str(out.parent))
        except Exception as error:
            ak_row_harness.end_smoke("FAIL", 1, str(error), str(out.parent))
            raise
        return
    result = {"schema": "epyc.w66-prefill-budget.v1", "complete": False, "pairs": [],
              "started_unix": time.time(), "private_prefix_sha256": PREFIX_SHA,
              "prior_archive_manifest_sha256": archive_sha, "endpoint_source_sha256": REPLAY_SHA,
              "fixed_generated_tokens_each_stream": CAP, "frozen_cap_on_peer_is_new_control": True,
              "accepted_work_claim": False}
    stop_reason = "at most three pairs"
    try:
        for pair, order in enumerate((("control", "budget"), ("budget", "control"),
                                      ("control", "budget")), 1):
            block = {"pair": pair, "order": order}
            for arm in order:
                if interrupted["signaled"]:
                    raise RuntimeError("stopped before next arm")
                block[arm] = one_visit(replay, inputs, states, out, pair, arm, interrupted)
            result["pairs"].append(block)
            verdict = result["decision"] = interpret(result["pairs"])
            replay.save_json(out / "RESULT.json", result)
            if verdict["stop_futility"] or verdict["stop_on_answer"]:
                stop_reason = "paired peer TTFT futility" if verdict["stop_futility"] else "paired timing answered"
                break
        result.update(complete=True, stop_reason=stop_reason)
    except Exception as error:
        result.update(error=str(error), error_type=type(error).__name__)
        raise
    finally:
        result["ended_unix"] = time.time()
        replay.save_json(out / "RESULT.json", result)


if __name__ == "__main__":
    main()
