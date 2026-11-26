"""Reconcile native Taskflow request counters with the retained attempt ledgers."""

from collections import defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path


TMP = Path("/mnt/raid0/llm/tmp")
PILOT = TMP / "ws58-a3b-pilot-20261126/runtime"
CANARY = TMP / "taskflow-finish-20261126"
R2 = TMP / "taskflow-stage1-gpu-r2-20261126/out"
R8G = TMP / "taskflow-stage1-cpu-r8g-20261123/out"
CANARY_FINDINGS = TMP / "ws58-a3b-finish-20261126/docs/design/taskflow-stage1-canary-findings.md"
OUT = Path(__file__).resolve().parent
SOURCES = {}
COUNTERS = {
    "cached": "cache_n",
    "uncached": "prompt_n",
    "generated": "predicted_n",
}


def read_record(path):
    data = path.read_bytes()
    SOURCES[str(path)] = sha256(data).hexdigest()
    return data.decode()


def read_json(path):
    return json.loads(read_record(path))


def read_requests(path):
    return [json.loads(line) for line in read_record(path).splitlines()]


def role(request):
    digest = request["digest"]
    if request["arm"] == "smoke":
        return "wire control ON" if digest["thinking"] else "wire control OFF"
    if digest.get("is_title") and not digest.get("tools"):
        assert digest["thinking"] is False
        return "reviewer OFF"
    assert digest.get("tools") and isinstance(digest.get("thinking"), bool)
    return "worker ON" if digest["thinking"] else "worker OFF"


def number(value):
    return type(value) is int and value >= 0


def counters(requests):
    observed = defaultdict(list)
    complete = 0
    for request in requests:
        values = {field: request.get(key) for field, key in COUNTERS.items()}
        cached, uncached, generated = values.values()
        usage = request.get("usage")
        if usage:
            expected_cache = usage["prompt_tokens_details"]["cached_tokens"]
            assert cached == expected_cache
            assert number(uncached) and cached + uncached == usage["prompt_tokens"]
            assert generated == usage["completion_tokens"]
            assert "reasoning_tokens" not in (usage.get("completion_tokens_details") or {})
        if number(cached) and number(uncached):
            observed["prompt"].append(cached + uncached)
        for field, value in values.items():
            if number(value):
                observed[field].append(value)
        complete += all(number(value) for value in values.values())
    return {
        "requests": len(requests),
        "complete_counters": complete,
        **{field: sum(observed[field]) for field in ("prompt", *COUNTERS)},
        **{f"valid_{field}": len(observed[field]) for field in ("prompt", *COUNTERS)},
    }


def by_role(requests):
    groups = defaultdict(list)
    for request in requests:
        groups[role(request)].append(request)
    return {key: counters(rows) for key, rows in sorted(groups.items())}


def one_row(requests, prefix):
    return {**prefix, **counters(requests)}


def pilot_audit():
    report = read_json(PILOT / "PERFORMANCE.json")
    rows = []
    for backend, entry in report["actual_request_logs"].items():
        path = PILOT / f"out-{backend}/requests.jsonl"
        assert Path(entry["path"]) == path
        rows.extend(read_requests(path))
        assert SOURCES[str(path)] == entry["sha256"]
    identities = {(r["backend"], r["label"], r["t0"], r.get("body_ref")) for r in rows}
    assert len(identities) == len(rows)
    attempts = defaultdict(list)
    tasks = defaultdict(list)
    output = []
    for request in rows:
        if request["arm"] != "smoke":
            attempts[request["label"]].append(request)
    for record in report["attempts"]:
        raw = attempts.pop(record["label"], [])
        tasks[record["logical_key"]].extend(raw)
        assert len(raw) == record["telemetry"]["requests"]
        totals = counters(raw)
        for key, native in COUNTERS.items():
            assert totals[key] == record["telemetry"]["tokens"][native]
        raw_roles = by_role(raw)
        prefix = {
            "task": record["logical_key"],
            "attempt": record["label"],
            "device": record["backend"],
            "audit": (record["audit"] or {}).get("class") or "corrected test accepted",
            "harness_state": record["state"],
        }
        if raw_roles:
            output.extend({**prefix, "role": name, **totals} for name, totals in raw_roles.items())
        else:
            output.append({**prefix, "role": "no calls", **totals})
    assert not attempts
    for logical_key, task_rows in tasks.items():
        for backend, telemetry in report["logical_tasks"][logical_key].items():
            backend_rows = [r for r in task_rows if r["backend"] == backend]
            assert len(backend_rows) == telemetry["requests"]
            for role_key, native in COUNTERS.items():
                assert counters(backend_rows)[role_key] == telemetry["tokens"][native]
    return output, {task: by_role(task_rows) for task, task_rows in sorted(tasks.items())}, by_role(rows)


def canary_audit():
    perf = read_json(CANARY / "PERFORMANCE.json")
    verdict = read_json(CANARY / "FINAL-VERDICT.json")
    initial_matrix = read_json(CANARY / "MATRIX.json")
    followup_matrix = read_json(CANARY / "FOLLOWUP-MATRIX.json")
    read_record(CANARY / "audit-prior.md")
    read_record(CANARY_FINDINGS)
    original = verdict["original"]["units"]
    rows_by_attempt = {"cpu": read_requests(CANARY / "out-cpu/requests.jsonl"),
                       "gpu": read_requests(CANARY / "out-gpu/requests.jsonl"),
                       "previous-gpu-r2": read_requests(R2 / "requests.jsonl")}
    output = []
    for key, outcome in sorted(original.items()):
        arm, task = key.split(":", 1)
        source, = initial_matrix["units"][key]
        initial = [r for r in rows_by_attempt[source["source"]] if r["arm"] == arm and r["task"] == task]
        counts = by_role(initial) or {"no calls": counters([])}
        for name, totals in counts.items():
            output.append({"task": task, "arm": arm, "role": name, "phase": "original",
                           "device": source["source"], "outcome": outcome["verdict"],
                           "audit": outcome["classification"], **totals})
    for backend in ("cpu", "gpu"):
        assert perf["devices"][backend]["overall"]["requests"] == len(rows_by_attempt[backend])
    retained_gpu = [r for r in output if r["device"] == "previous-gpu-r2"]
    assert sum(r["requests"] for r in retained_gpu) == perf["retained_gpu_r2"]["overall"]["requests"]
    for case in sorted({v["case"] for v in followup_matrix["units"]}):
        entries = [v for v in followup_matrix["units"] if v["case"] == case]
        for backend in {v["backend"] for v in entries}:
            native = read_requests(CANARY / case / f"out-{backend}/requests.jsonl")
            assert perf["followups"][case][backend]["overall"]["requests"] == len(native)
            for entry in entries:
                arm, task = entry["unit"].split(":", 1)
                selected = [r for r in native if r["arm"] == arm and r["task"] == task]
                audit = entry["audit"]
                for name, totals in by_role(selected).items():
                    output.append({"task": task, "arm": arm, "role": name, "phase": case,
                                   "device": backend, "outcome": audit["verdict"],
                                   "audit": audit.get("classification"), **totals})
    for case in ("reviewer-replay", "reviewer-fullpatch-replay"):
        native = read_requests(CANARY / case / "requests.jsonl")
        assert perf["reviewer_replays"][case]["overall"]["requests"] == len(native)
        counts = defaultdict(list)
        for request in native:
            counts[(request["task"], request["arm"], role(request))].append(request)
        for (task, arm, name), selected in sorted(counts.items()):
            output.append(one_row(selected, {"task": task, "arm": arm, "role": name, "phase": case,
                                            "device": "gpu", "outcome": "reviewer replay", "audit": None}))
    return output


def r8g_audit():
    read_record(R8G / "verdict.json")
    selected = defaultdict(list)
    for request in read_requests(R8G / "requests.jsonl"):
        selected[(request["task"], request["arm"], role(request))].append(request)
    return [one_row(rows, {"task": task, "arm": arm, "role": name}) for (task, arm, name), rows
            in sorted(selected.items())]


def write_table(filename, rows):
    with (OUT / filename).open("w") as file:
        writer = csv.DictWriter(file, rows[0], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    attempts, logical, totals = pilot_audit()
    write_table("pilot-attempts.tsv", attempts)
    write_table("pilot-logical-tasks.tsv", [{"task": task, "role": name, **values}
                                           for task, roles in logical.items() for name, values in roles.items()])
    write_table("c22-canary-attempts.tsv", canary_audit())
    write_table("r8g-canary-attempts.tsv", r8g_audit())
    (OUT / "pilot-role-totals.json").write_text(json.dumps({
        "totals": totals, "reasoning_only_tokens": None,
    }, indent=2) + "\n")
    with (OUT / "SOURCES.sha256").open("w") as file:
        for path, digest in sorted(SOURCES.items()):
            file.write(f"{digest}  {path}\n")


if __name__ == "__main__":
    main()
