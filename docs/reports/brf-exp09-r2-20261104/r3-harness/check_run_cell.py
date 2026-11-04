#!/usr/bin/env python3
"""Exercise the actual job.run_cell with fake transport and output; no inference."""
import json
import os
import tempfile
from summary_flags import completion_flags, validate_completion

JOB = "/mnt/raid0/llm/tmp/brf-exp09-expand-r3/job.py"
with tempfile.TemporaryDirectory(prefix="exp09-r3-run-cell-") as td:
    os.makedirs(os.path.join(td, "corpus"))
    json.dump({"port": 18429}, open(os.path.join(td, "identity.json"), "w"))
    json.dump({"items": []}, open(os.path.join(td, "corpus", "MANIFEST.json"), "w"))
    src = open(JOB).read().replace(
        'B = "/mnt/raid0/llm/tmp/brf-exp09-expand-r3"', f'B = {td!r}', 1
    )
    ns = {"__name__": "exp09_r3_test_job", "__file__": JOB}
    exec(compile(src, JOB, "exec"), ns)
    result_path = os.path.join(td, "results.jsonl")
    ns["RES"] = result_path
    ns["vq_view"] = lambda text, item, gold: (
        "fake observation", {"planted_mismatch_rejected": True, "marker": "test-evidence"}
    )
    ns["chat"] = lambda prompt, n: (
        '{"exit_status":"fail","n_failed":1,"failed_ids":["test_x"],"first_exception":"AssertionError","need_fetch":null}',
        {"usage": {"completion_tokens": 20}},
    )
    item = {"id": "item-01", "sha256": "abc", "gold": {
        "exit_status": "fail", "n_failed": 1, "failed_ids": ["test_x"],
        "first_exception": "AssertionError",
    }}
    rec = ns["run_cell"](item, "verified_quote", "fake full log")
    emitted = json.loads(open(result_path).readline())
    assert rec["view"] == "fake observation"
    assert rec["answer_raw"].startswith("{")
    assert rec["evidence"]["marker"] == "test-evidence"
    assert rec["accuracy"] == 1.0
    assert rec["exact_failed_id_reference_count"] == 1
    assert rec["exact_failed_id_hits"] == 1
    assert rec["exact_failed_id_recall"] == 1.0
    assert rec["exact_failed_id_reference_cap"] == 10
    malformed_score = ns["score"]("not JSON", item["gold"], "fake observation")
    assert malformed_score["parsed"] is False
    malformed_exact = ns["exact_failed_id_recall"](malformed_score["answer"], item["gold"]["failed_ids"])
    assert malformed_exact["exact_failed_id_hits"] == 0
    for field in ("view", "answer_raw", "evidence", "accuracy"):
        assert emitted[field] == rec[field]
    loaded, duplicates, malformed = ns["done_cells"]()
    assert len(loaded) == 1 and not duplicates and not malformed
    with open(result_path, "a") as f:
        f.write(json.dumps(emitted) + "\n")
        f.write("{bad json\n")
        f.write("[]\n")
        f.write("null\n")
        f.write("42\n")
        f.write('"scalar"\n')
    loaded, duplicates, malformed = ns["done_cells"]()
    assert len(loaded) == 1 and duplicates == [("item-01", "verified_quote")]
    assert malformed == [3, 4, 5, 6, 7]
    assert completion_flags({("item-01", "verified_quote"): rec}) == (True, True)
    arms = ["control", "verified_quote", "shape_header", "pointer_only"]
    rows = {}
    for i in range(1, 25):
        for arm in arms:
            rows[(f"item-{i:02d}", arm)] = {
                "view": "fake", "answer_raw": "{}", "parsed": True,
                "answer_meta": {"usage": {"completion_tokens": 20}},
                "evidence": {"planted_mismatch_rejected": arm == "verified_quote"},
            }
    rows[("item-01", "verified_quote")] = rec
    assert validate_completion(rows, [f"item-{i:02d}" for i in range(1, 25)], arms) == (True, [])
print("actual job.run_cell regression test passed")
