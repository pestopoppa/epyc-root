#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--run-dir", required=True)
p.add_argument("--launcher-log", required=True)
p.add_argument("--started-at", required=True)
p.add_argument("--launcher-sha", required=True)
p.add_argument("--job-sha", required=True)
a = p.parse_args()
run = Path(a.run_dir)
log_path = Path(a.launcher_log)
smoke = json.loads((run / "SMOKE.json").read_text())
state = json.loads((run / "STATE.json").read_text())
expected_tag = "Accurate_Retrieval__eventqa_65536__base"
assert smoke["run_id"] == run.name
assert smoke["started_at"] >= a.started_at
assert smoke["arm"] == "base" and smoke["record_index"] == 0
assert smoke["writer_ok"] is True
assert "one real first question" in smoke["scope"]
assert smoke["launcher_path"] == "/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261030-r13/launch.sh"
assert state["run_id"] == run.name and state["status"] == "complete"
assert state["rc"] == 0 and state["partial"] is False and state["work_started"] is True
assert state["direct_child_reaped"] is True
assert state["ended_at"] >= a.started_at
result_json = Path(smoke["result_json"])
result_jsonl = Path(smoke["result_jsonl"])
for result in (result_json, result_jsonl):
    assert result.is_file() and result.stat().st_size > 0
assert hashlib.sha256(result_json.read_bytes()).hexdigest() == smoke["result_json_sha256"]
assert hashlib.sha256(result_jsonl.read_bytes()).hexdigest() == smoke["result_jsonl_sha256"]
result = json.loads(result_json.read_text())
rows = [json.loads(line) for line in result_jsonl.read_text().splitlines() if line.strip()]
assert len(result.get("data", [])) == len(rows) == 1
assert rows[0].get("record_index") == 0
assert rows[0].get("resume_identity", {}).get("question_index") == 0
assert rows[0].get("resume_identity", {}).get("split") == "Accurate_Retrieval"
assert rows[0].get("resume_identity", {}).get("source") == "eventqa_65536"
assert str(rows[0].get("output", "")).strip()
samples = (run / "GPU-SAMPLES.tsv").read_text().splitlines()
assert any(len(row.split("\t")) == 7 and row.split("\t")[1] == expected_tag and row.split("\t")[4] == "after_generate" and row.split("\t")[5] == "1" for row in samples)
log = log_path.read_text(errors="replace")
job_log = (run / "job.log").read_text(errors="replace")
assert f"START {expected_tag} " in job_log
assert f"RESULT_OK {expected_tag} records 1" in job_log
assert f"END {expected_tag} rc=0" in job_log
assert "held gpu-quiet exclusive" in log
print(json.dumps({"ok": True, "run_id": run.name, "started_at": smoke["started_at"], "state": state["status"], "rc": state["rc"], "first_request": expected_tag, "records": 1, "result_json_sha256": smoke["result_json_sha256"], "result_jsonl_sha256": smoke["result_jsonl_sha256"], "launcher_sha256": a.launcher_sha, "job_sha256": a.job_sha}, sort_keys=True))
