from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
import sys

work = Path(sys.argv[1])
packet, pilot = work / "packet", work / "pilot"

def load(path):
    return json.loads(path.read_bytes())

def rows(path, key):
    return {r[key]: r for r in map(json.loads, path.read_bytes().splitlines())}

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
for filename, sha in run["output_sha256"].items():
    assert sha256((pilot / filename).read_bytes()).hexdigest() == sha
scores = load(pilot / "scored-output.json")
gold = rows(packet / "tasks.jsonl", "instance_id")
predictions = rows(pilot / "predictions.jsonl", "task_id")
discovery = rows(pilot / "discovery.jsonl", "task_id")
assert len(gold) == len(predictions) == len(discovery) == scores["eligible_task_count"] == 3
assert scores["excluded"] == []
assert len(load(packet / "dataset-audit.json")["empty_gold_ids"]) == 3
assert len(load(packet / "dataset-audit.json")["workspace_bare_paths_by_id"]) == 42
for scope in scores["arms"][0]["scopes"]:
    budget = scope["budget_tokens"]
    for result in scope["per_task"]:
        task = result["task_id"]
        pred = predictions[task]
        assert result["status"] == pred["status"] == "ok"
        spans = gold[task]["gold_context"]
        gold_files = {s["file"] for s in spans}
        gold_lines = lines(triples(spans))
        if budget is None:
            pred_files = set(pred["pred_files"])
            pred_lines = lines(triples(pred["pred_spans"]))
        else:
            plan = next(p for p in discovery[task]["pack_plans"] if p["budget_tokens"] == budget)
            entries = plan["entries"]
            assert len({e["path"] for e in entries}) == len(entries)
            assert plan["estimated_packed_tokens"] == sum(e["estimated_tokens"] for e in entries) <= budget
            assert all(e["packer_mode"] == e["rendered_mode"] for e in entries)
            pred_files = {e["path"] for e in entries if e["packer_mode"] != "excluded"}
            assert pred_files == set(plan["pred_files"])
            pred_lines = lines((e["path"], a, b) for e in entries for a, b in e["pred_spans"])
        for key, g, p in (("file", gold_files, pred_files), ("line", gold_lines, pred_lines)):
            count = {"tp": len(p & g), "fp": len(p - g), "fn": len(g - p)}
            assert result["counts"][key] == count
            for metric, value in metrics(count).items():
                assert result["metrics"][f"{key}_{metric}"] == value
    for k, v in scope["metrics"].items():
        assert v["value"] == mean(r["metrics"][k] for r in scope["per_task"])
print("Verified 12 task-scope counts, six macro metrics per scope, all three actual pack budgets and rendered modes.")
