#!/usr/bin/env python3
"""Completion predicate for the full 24-prompt source-validation arm."""
import json
import sys

PROMPTS = "/mnt/raid0/llm/epyc-root/scripts/inf70/harness1/prompts.json"
with open(PROMPTS) as f:
    expected = json.load(f)
with open(sys.argv[1]) as f:
    rows = [json.loads(line) for line in f if line.strip()]
if len(rows) != len(expected):
    raise SystemExit(f"incomplete: {len(rows)} rows, expected {len(expected)}")
for i, row in enumerate(rows):
    if row.get("seq") != i or row.get("id") != expected[i]["id"]:
        raise SystemExit(f"row identity mismatch at index {i}")
    if row.get("verdict") == "HTTP-ERROR":
        raise SystemExit(f"HTTP-ERROR at index {i}")
first = rows[0]
if first.get("token_source") != "response" or not isinstance(first.get("token_ids"), list) or not first["token_ids"]:
    raise SystemExit("first generated IDs were not a non-empty response token list")
if first.get("classifier") != "inf70-classify.v1.1":
    raise SystemExit(f"unexpected classifier {first.get('classifier')!r}")
print(f"complete: {len(rows)} ordered rows; first token_source=response with {len(first['token_ids'])} IDs")
