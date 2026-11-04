#!/usr/bin/env python3
"""Freeze or verify an outcome-independent candidate; never call a model/scorer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DATASET_SHA256 = "b087b5dad72b3e765a6cf93a9e7d516d8796698a0fd358abb73c6627df19f66e"
NAMESPACE = "epyc-p5-candidate-swe-verified-40-v1"
COUNT = 40


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def canonical_sha(value: object) -> str:
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def test_names(value: object) -> list[str]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError("invalid test identity list")
    if len(set(value)) != len(value):
        raise ValueError("duplicate test identity")
    return value


def artifacts(dataset: Path) -> dict[str, bytes]:
    raw = dataset.read_bytes()
    if sha(raw) != DATASET_SHA256:
        raise ValueError("original dataset bytes differ from pinned source")
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) != 500:
        raise ValueError("expected 500 source rows")
    ids = [r["instance_id"] for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != 500:
        raise ValueError("invalid or duplicate source IDs")

    def rank(row: dict) -> tuple[str, str]:
        iid = row["instance_id"]
        return sha((NAMESPACE + "\0" + iid).encode()), iid

    selected = sorted(rows, key=rank)[:COUNT]
    questions, cases = [], []
    for row in selected:
        for key in ("repo", "base_commit", "problem_statement", "patch", "test_patch"):
            if not isinstance(row[key], str) or not row[key]:
                raise ValueError(f"missing {key}")
        # This explicit allowlist is the only model-facing artifact. No hints,
        # solution/test patches, expected tests, or grading metadata enter it.
        question = {"id": row["instance_id"], "repo": row["repo"],
                    "base_commit": row["base_commit"], "prompt": row["problem_statement"]}
        questions.append(question)
        fail, passing = test_names(row["FAIL_TO_PASS"]), test_names(row["PASS_TO_PASS"])
        if not fail:
            raise ValueError("empty FAIL_TO_PASS")
        cases.append({"instance_id": row["instance_id"], "selection_sha256": rank(row)[0],
                      "source_row_sha256": canonical_sha(row), "question_sha256": canonical_sha(question),
                      "repo": row["repo"], "base_commit": row["base_commit"],
                      "gold_patch_sha256": sha(row["patch"].encode()),
                      "test_patch_sha256": sha(row["test_patch"].encode()),
                      "FAIL_TO_PASS": fail, "PASS_TO_PASS": passing,
                      "fail_to_pass_sha256": canonical_sha(fail),
                      "pass_to_pass_sha256": canonical_sha(passing)})
    qraw = encoded(questions)
    manifest = {"schema": "p5.candidate-question-manifest.v1", "status": "CANDIDATE_NOT_APPROVED",
                "source_dataset_sha256": DATASET_SHA256, "source_count": 500,
                "selection": {"namespace": NAMESPACE, "count": COUNT,
                              "rule": "sort ascending by SHA256(UTF8(namespace + NUL + instance_id)), then instance_id; first 40",
                              "rationale": "Bounded 40-case review candidate; identity-only hash ranking avoids outcome, difficulty, repository, and scorer-success selection. Not a powered experiment or approved final sample."},
                "questions_sha256": sha(qraw), "cases": cases,
                "limitations": ["No model exposure, inference, or scorer execution performed by this tool.",
                                "Existing one-case scorer control does not establish selected-case coverage.",
                                "Evaluation-only manifest contains test identities; never supply it to a model.",
                                "A byte pin and exclusive creation prevent silent tool overwrite; file permissions are not a tamper-proof storage boundary."]}
    out = {"questions.json": qraw, "manifest.eval-only.json": encoded(manifest)}
    out["SHA256SUMS"] = "".join(f"{sha(data)}  {name}\n" for name, data in sorted(out.items())).encode()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "verify"))
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    expected = artifacts(args.dataset)
    if args.command == "freeze":
        # Never partially replace or silently repin an existing candidate.
        args.directory.mkdir(parents=True, exist_ok=False)
        for name, raw in expected.items():
            path = args.directory / name
            with path.open("xb") as stream:
                stream.write(raw)
            path.chmod(0o444)
    else:
        for name, raw in expected.items():
            if (args.directory / name).read_bytes() != raw:
                raise ValueError(f"candidate/source mismatch: {name}")
    print(json.dumps({"status": "CANDIDATE_SOURCE_MATCH", "command": args.command,
                      "cases": COUNT, "source_dataset_sha256": DATASET_SHA256,
                      "artifact_sha256": {name: sha(raw) for name, raw in expected.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
