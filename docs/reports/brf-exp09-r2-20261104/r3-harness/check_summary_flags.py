#!/usr/bin/env python3
"""Offline regression check; fake persisted rows only, no model or compute."""
from summary_flags import (
    completion_flags, completion_record, duplicate_cell_keys, exact_failed_id_recall, validate_completion,
)

rows = {
    ("item-01", "control"): {"view": "", "answer_raw": "{}", "evidence": {}},
    ("item-01", "verified_quote"): {
        "view": "pointer", "answer_raw": "{}",
        "evidence": {"planted_mismatch_rejected": True},
    },
}
assert completion_flags(rows) == (True, True)
rows[("item-01", "verified_quote")]["evidence"]["planted_mismatch_rejected"] = False
assert completion_flags(rows) == (False, True)
rows[("item-01", "control")]["answer_raw"] = None
assert completion_flags(rows) == (False, False)

items = [f"item-{i:02d}" for i in range(1, 25)]
arms = ["control", "verified_quote", "shape_header", "pointer_only"]
full = {}
for item in items:
    for arm in arms:
        full[(item, arm)] = {
            "view": "fake", "answer_raw": "{}", "parsed": True,
            "answer_meta": {"usage": {"completion_tokens": 30}},
            "evidence": {"planted_mismatch_rejected": arm == "verified_quote"},
        }
assert validate_completion(full, items, arms) == (True, [])
kind, summary = completion_record(full, items, arms)
assert kind == "pass_complete" and summary["validation_reasons"] == []

missing = dict(full)
missing.pop(("item-24", "pointer_only"))
ok, reasons = validate_completion(missing, items, arms)
assert not ok and any(reason.startswith("grid-mismatch") for reason in reasons)
kind, summary = completion_record(missing, items, arms)
assert kind == "validation_incomplete" and summary["validation_reasons"]

extra = dict(full)
extra[("item-25", "control")] = {
    "view": "fake", "answer_raw": "{}", "parsed": True,
    "answer_meta": {"usage": {"completion_tokens": 30}},
    "evidence": {},
}
ok, reasons = validate_completion(extra, items, arms)
assert not ok and any(reason.startswith("grid-mismatch") for reason in reasons)

bad = {key: dict(value) for key, value in full.items()}
bad[("item-04", "verified_quote")] = dict(bad[("item-04", "verified_quote")])
bad[("item-04", "verified_quote")]["evidence"] = {"planted_mismatch_rejected": False}
ok, reasons = validate_completion(bad, items, arms)
assert not ok and "mechanism-not-fired" in reasons

bad = {key: dict(value) for key, value in full.items()}
bad[("item-03", "shape_header")]["answer_raw"] = None
ok, reasons = validate_completion(bad, items, arms)
assert not ok and "capture-incomplete" in reasons

bad = {key: dict(value) for key, value in full.items()}
bad[("item-02", "control")]["answer_meta"] = {"usage": {"completion_tokens": 1024}}
ok, reasons = validate_completion(bad, items, arms)
assert not ok and "answer-cap-hit-or-unknown:item-02:control" in reasons

native = [{"kind": "cell", "item": "item-01", "arm": "control"}]
assert duplicate_cell_keys(native + native) == [("item-01", "control")]

gold_ids = [" tests/unit/test_alpha ", "tests/unit/test_beta"]
exact = exact_failed_id_recall(
    {"failed_ids": ["tests/unit/test_alpha", "tests/unit/test_beta"]}, gold_ids
)
assert exact == {
    "exact_failed_id_reference_count": 2,
    "exact_failed_id_hits": 2,
    "exact_failed_id_recall": 1.0,
    "exact_failed_id_reference_cap": 10,
}
near = exact_failed_id_recall({"failed_ids": ["tests/unit/test_alph", "unit/test_beta"]}, gold_ids)
assert near["exact_failed_id_hits"] == 0 and near["exact_failed_id_recall"] == 0.0
assert exact_failed_id_recall({"failed_ids": "tests/unit/test_alpha"}, gold_ids)["exact_failed_id_hits"] == 0
assert exact_failed_id_recall(None, gold_ids)["exact_failed_id_hits"] == 0
assert exact_failed_id_recall({"failed_ids": ["x"]}, [f"id-{i}" for i in range(12)]) == {
    "exact_failed_id_reference_count": 10,
    "exact_failed_id_hits": 0,
    "exact_failed_id_recall": 0.0,
    "exact_failed_id_reference_cap": 10,
}
print("summary flag tests passed")
