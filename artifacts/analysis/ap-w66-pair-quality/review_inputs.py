#!/usr/bin/env python3
"""Reconstruct pinned W66 fixture states from recorded direct edits as data."""

import argparse
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE.parent / "ap-w66-replay-inputs" / "requests.json"
BASELINE = Path(
    "/mnt/raid0/llm/tmp/ws58-a3b-revalidate-20261126/coverage/"
    "w66-light-brief-v2/cases/DS41-W-66/baseline"
)
SOURCE = "scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py"
BASELINE_HASH = "ec49d2f0607335d2a68c2522a9eee81fa379eb2e9d1d3f522af4e30c35096d83"
LEGACY_RECEIPT_ASSERTION = ast.unparse(
    ast.parse(
        'assert continuation["runtime_recipe_reference"] == {'
        '"locator": "fixture-runtime-selection", "sha256": "b" * 64, "verified": True}'
    ).body[0]
)


def sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def canonical_hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def check_hash(blob, expected, name):
    if sha256(blob) != expected:
        raise ValueError(f"{name} SHA-256 mismatch")


def pinned_body(row):
    receipts = Path(row["wire_receipt_path"])
    matching_receipts = [
        record for record in map(json.loads, receipts.read_bytes().splitlines())
        if canonical_hash(record) == row["receipt_sha256"]
    ]
    if len(matching_receipts) != 1:
        raise ValueError(f"expected one receipt for sequence {row['seq']}")
    receipt = matching_receipts[0]
    for key in ("seq", "slot", "body_ref"):
        if str(receipt[key]) != row[key]:
            raise ValueError(f"receipt {key} differs from manifest")
    zipped = (receipts.parent / row["body_ref"]).read_bytes()
    check_hash(zipped, row["gzip_sha256"], "compressed body")
    decoded = gzip.decompress(zipped)
    check_hash(decoded, row["decoded_sha256"], "decoded body")
    return json.loads(decoded)


def project_edit(source, arguments):
    """Use only literal string replacement and Python syntax parsing."""
    if arguments["path"] not in (SOURCE, f"/case/{SOURCE}"):
        raise ValueError("path is outside the fixture scope")
    old, new = arguments["oldString"], arguments["newString"]
    replace_all = arguments.get("replaceAll", False)
    matches = source.count(old)
    if not old or old == new or not matches or (matches != 1 and not replace_all):
        raise ValueError("edit has no unique applicable replacement")
    return source.replace(old, new, -1 if replace_all else 1)


def reconstruct(body, baseline):
    messages = body["messages"]
    tool_results = {
        message["tool_call_id"]: message.get("content")
        for message in messages if message["role"] == "tool"
    }
    source = baseline
    edit_indices = []
    for index, message in enumerate(messages):
        for call in message.get("tool_calls") or []:
            function = call["function"]
            result = tool_results.get(call["id"])
            if function["name"] == "edit" and str(result).startswith(f"Edited {SOURCE} ("):
                source = project_edit(source, json.loads(function["arguments"]))
                edit_indices.append(index)
    ast.parse(source)
    return source, edit_indices


def assertions(source):
    return Counter(
        ast.unparse(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Assert)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", type=int, choices=(28, 29, 52, 56))
    parser.add_argument("--edit-arguments", type=Path, help="inspect a proposed edit JSON file as data")
    args = parser.parse_args()
    if args.edit_arguments and args.sequence is None:
        parser.error("--edit-arguments requires --sequence")

    raw_baseline = (BASELINE / SOURCE).read_bytes()
    check_hash(raw_baseline, BASELINE_HASH, "pinned baseline")
    baseline = raw_baseline.decode()
    nonreceipt_assertions = assertions(baseline)
    if nonreceipt_assertions.pop(LEGACY_RECEIPT_ASSERTION) != 1:
        raise ValueError("baseline does not have exactly one legacy receipt assertion")
    evidence = {
        "fixture_path": SOURCE,
        "baseline_sha256": BASELINE_HASH,
        "manifest_sha256": sha256(MANIFEST.read_bytes()),
        "rubric_sha256": sha256((HERE / "rubric.md").read_bytes()),
        "targets": [],
    }
    for row in json.loads(MANIFEST.read_bytes())["requests"]:
        if args.sequence is not None and int(row["seq"]) != args.sequence:
            continue
        body = pinned_body(row)
        source, edits = reconstruct(body, baseline)
        last_message = body["messages"][-1]
        target = {
            "sequence": int(row["seq"]),
            "slot": int(row["slot"]),
            "unit": row["id"],
            "wire_receipt_sha256": row["receipt_sha256"],
            "decoded_body_sha256": row["decoded_sha256"],
            "last_message_sha256": canonical_hash(last_message),
            "last_message_role": last_message["role"],
            "fixture_state_sha256": sha256(source.encode()),
            "successful_edit_message_indices": edits,
        }
        if args.edit_arguments:
            arguments = args.edit_arguments.read_bytes()
            target["edit_arguments_sha256"] = sha256(arguments)
            try:
                projected = project_edit(source, json.loads(arguments))
                target["nonreceipt_assertions_missing_verbatim"] = list(
                    (nonreceipt_assertions - assertions(projected)).elements()
                )
                target["projected_state_sha256"] = sha256(projected.encode())
            except (KeyError, TypeError, ValueError, SyntaxError) as error:
                target["projection_error"] = str(error)
        evidence["targets"].append(target)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
