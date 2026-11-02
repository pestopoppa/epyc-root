#!/usr/bin/env python3
"""Freeze P5 scorer inputs and check native report coverage; never run a scorer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: str) -> tuple[bytes, object]:
    raw = Path(path).read_bytes()
    return raw, json.loads(raw)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def unique_rows(rows: object, key: str) -> dict[str, dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{key}: expected a nonempty row list")
    out = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(key), str) or not row[key]:
            raise ValueError(f"missing {key}")
        if row[key] in out:
            raise ValueError(f"duplicate {key}: {row[key]}")
        out[row[key]] = row
    return out


def tests(value: object) -> list[str]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x for x in value):
        raise ValueError("FAIL_TO_PASS must be a nonempty test-name list")
    if len(set(value)) != len(value):
        raise ValueError("duplicate FAIL_TO_PASS test")
    return value


def freeze(args: argparse.Namespace) -> dict:
    qraw, qdoc = read(args.questions)
    draw, ddoc = read(args.dataset)
    questions = unique_rows(qdoc, "id")
    dataset = unique_rows(ddoc, "instance_id")
    scorer = Path(args.scorer).read_bytes()
    cases = []
    for iid, question in questions.items():
        row = dataset.get(iid)
        if row is None:
            raise ValueError(f"question absent from dataset: {iid}")
        patch, base, repo = row.get("patch"), row.get("base_commit"), row.get("repo")
        if not all(isinstance(x, str) and x for x in (patch, base, repo)):
            raise ValueError(f"{iid}: missing gold patch/base/repo")
        fail = tests(row.get("FAIL_TO_PASS"))
        cases.append({"instance_id": iid, "question_sha256": digest(canonical(question)),
                      "gold_patch_sha256": digest(patch.encode()), "repo": repo,
                      "base_commit": base, "fail_to_pass_sha256": digest(canonical(fail))})
    return {"schema": "p5.gold-binding.v1", "questions_sha256": digest(qraw),
            "dataset_sha256": digest(draw), "scorer_sha256": digest(scorer), "cases": cases}


def id_list(report: dict, key: str) -> set[str]:
    value = report.get(key)
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError(f"invalid {key}")
    if len(value) != len(set(value)):
        raise ValueError(f"duplicate {key}")
    return set(value)


def check(args: argparse.Namespace) -> dict:
    _, expected = read(args.binding)
    if not isinstance(expected, dict) or expected != freeze(args):
        raise ValueError("binding differs from current question, dataset, scorer or cases")
    _, report = read(args.report)
    if not isinstance(report, dict):
        raise ValueError("report is not an object")
    ids = {x["instance_id"] for x in expected["cases"]}
    completed, resolved = id_list(report, "completed_ids"), id_list(report, "resolved_ids")
    unresolved, errors = id_list(report, "unresolved_ids"), id_list(report, "error_ids")
    if completed != ids or resolved != ids or unresolved or errors:
        raise ValueError("gold report must complete and resolve exactly every bound case, without errors")
    if report.get("total_instances") != len(ids) or report.get("completed_instances") != len(ids) or report.get("resolved_instances") != len(ids) or report.get("error_instances") != 0 or report.get("unresolved_instances") != 0:
        raise ValueError("gold report counters disagree with cases")
    return {"status": "REPORT_COVERAGE_MATCH", "cases": len(ids),
            "binding_sha256": digest(Path(args.binding).read_bytes()),
            "report_sha256": digest(Path(args.report).read_bytes()),
            "limitation": "report consistency only; does not prove fresh execution, negative controls, or scorer validity"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("freeze", "check"):
        p = sub.add_parser(name)
        p.add_argument("--questions", required=True)
        p.add_argument("--dataset", required=True)
        p.add_argument("--scorer", required=True, help="exact scorer entrypoint file")
        if name == "freeze":
            p.add_argument("--output", required=True)
        else:
            p.add_argument("--binding", required=True)
            p.add_argument("--report", required=True)
    args = parser.parse_args()
    if args.cmd == "freeze":
        result = freeze(args)
        with Path(args.output).open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    else:
        print(json.dumps(check(args), sort_keys=True))


if __name__ == "__main__":
    main()
