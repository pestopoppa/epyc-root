from hashlib import sha256
import json
from math import isclose
from pathlib import Path
from statistics import mean
import sys

work = Path(sys.argv[1])
packet, pilot = work / "packet", work / "pilot"

def load(path):
    return json.loads(path.read_bytes())

def rows(path, key):
    records = list(map(json.loads, path.read_bytes().splitlines()))
    result = {record[key]: record for record in records}
    assert len(result) == len(records)
    return result

def lines(spans):
    return {(p, i) for p, start, end in spans for i in range(start, end + 1)}

def triples(spans):
    return ((s["file"], s["start_line"], s["end_line"]) for s in spans)

def metrics(count):
    tp, fp, fn = (count[k] for k in ("tp", "fp", "fn"))
    return {
        "precision": tp / (tp + fp) if tp + fp else 0,
        "recall": tp / (tp + fn) if tp + fn else 0,
        "f1": 2 * tp / (2 * tp + fp + fn) if tp else 0,
    }

run = load(pilot / "run.json")
assert sha256((packet / "request.json").read_bytes()).hexdigest() == run["request_sha256"]
request = load(packet / "request.json")
for filename, sha in request["packet_hashes"].items():
    assert sha256((packet / filename).read_bytes()).hexdigest() == sha
for filename, sha in run["output_sha256"].items():
    assert sha256((pilot / filename).read_bytes()).hexdigest() == sha
scores = load(pilot / "scored-output.json")
gold = rows(packet / "tasks.jsonl", "instance_id")
predictions = rows(pilot / "predictions.jsonl", "task_id")
discovery = rows(pilot / "discovery.jsonl", "task_id")
decisions = load(packet / "dispositions.json")["tasks"]
assert len(gold) == len(decisions) == len(request["selected"]) == 3
assert set(gold) == {r["task_id"] for r in request["selected"]} == {r["task_id"] for r in decisions}
eligible = {r["task_id"] for r in decisions if r["disposition"] == "include"}
excluded = {r["task_id"]: r["disposition"] for r in decisions if r["task_id"] not in eligible}
assert len(scores["eligible_task_ids"]) == scores["eligible_task_count"] == len(eligible)
assert set(predictions) == set(discovery) == set(scores["eligible_task_ids"]) == eligible
assert len(scores["excluded"]) == len(excluded)
assert {r["task_id"]: r["reason"] for r in scores["excluded"]} == excluded
assert len(load(packet / "dataset-audit.json")["empty_gold_ids"]) == 3
assert len(load(packet / "dataset-audit.json")["workspace_bare_paths_by_id"]) == 42
arm, = scores["arms"]
assert arm["arm"] == request["arm"]
scopes = arm["scopes"]
assert [scope["budget_tokens"] for scope in scopes] == [None, *request["budgets"]]
for scope in scopes:
    budget = scope["budget_tokens"]
    assert len(scope["per_task"]) == len(eligible)
    assert {r["task_id"] for r in scope["per_task"]} == eligible
    for result in scope["per_task"]:
        task = result["task_id"]
        pred = predictions[task]
        status = pred["status"]
        assert result["status"] == status
        assert status in {"ok", "error", "no_context_extracted", "checkout_failed"}
        spans = gold[task]["gold_context"]
        gold_files = {s["file"] for s in spans}
        gold_lines = lines(triples(spans))
        if budget is None:
            pred_files = set(pred["pred_files"])
            pred_lines = lines(triples(pred["pred_spans"]))
        elif status in {"error", "checkout_failed"}:
            assert discovery[task]["error"]
            pred_files, pred_lines = set(), set()
        else:
            plans = discovery[task]["pack_plans"]
            assert [p["budget_tokens"] for p in plans] == request["budgets"]
            plan = next(p for p in plans if p["budget_tokens"] == budget)
            entries = plan["entries"]
            assert len({e["path"] for e in entries}) == len(entries)
            assert plan["estimated_packed_tokens"] == sum(e["estimated_tokens"] for e in entries) <= budget
            assert all(e["packer_mode"] == e["rendered_mode"] for e in entries)
            pred_files = {e["path"] for e in entries if e["packer_mode"] != "excluded"}
            assert pred_files == set(plan["pred_files"])
            pred_lines = lines((e["path"], a, b) for e in entries for a, b in e["pred_spans"])
        if status != "ok":
            assert not pred_files and not pred_lines and not pred["pack_candidates"]
        for key, g, p in (("file", gold_files, pred_files), ("line", gold_lines, pred_lines)):
            count = {"tp": len(p & g), "fp": len(p - g), "fn": len(g - p)}
            assert result["counts"][key] == count
            for metric, value in metrics(count).items():
                assert result["metrics"][f"{key}_{metric}"] == value
    assert set(scope["metrics"]) == {f"{kind}_{metric}" for kind in ("file", "line")
                                    for metric in ("precision", "recall", "f1")}
    for k, v in scope["metrics"].items():
        assert isclose(v["value"], mean(r["metrics"][k] for r in scope["per_task"]), rel_tol=1e-15)
print(f"Verified {len(eligible) * len(scopes)} task-scope counts, six macro metrics per scope, "
      "all three actual pack budgets and rendered modes.")
