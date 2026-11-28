#!/usr/bin/env python3
"""Bind completed replay streams to their pinned input and check interpretability."""

import argparse
import json
from pathlib import Path

from review_inputs import MANIFEST, check_hash, pinned_body, sha256


def review_stream(receipt_path, pins, bodies):
    receipt = json.loads(receipt_path.read_bytes())
    label, name = receipt["label"], receipt["name"]
    expected = pins[label]
    body = bodies[label]
    if "-preserved-" in name:
        body = {**body, "chat_template_kwargs": {
            **body["chat_template_kwargs"], "preserve_thinking": True,
        }}
    wire_body = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    if sha256(wire_body) != receipt["request_body_sha256"]:
        raise ValueError(f"unrecognized target payload for {name}")
    if (receipt["source_body_sha256"] != expected["decoded_sha256"]
            or receipt["slot"] != int(expected["slot"])
            or receipt["http_status"] != 200):
        raise ValueError(f"target source, slot, or status differs for {name}")

    transport = receipt_path.parent / "private"
    message_path = transport / f"{name}.message.json"
    raw_message = message_path.read_bytes()
    check_hash(raw_message, receipt["private_message_sha256"], "parsed message")
    check_hash((transport / f"{name}.sse.jsonl").read_bytes(), receipt["private_sse_sha256"], "SSE")
    response = json.loads(raw_message)
    for key in ("name", "label", "finish_reason", "source_body_sha256", "request_body_sha256"):
        if response[key] != receipt[key]:
            raise ValueError(f"parsed message {key} differs from receipt for {name}")
    message = response["message"]
    definitions = {tool["function"]["name"]: tool["function"]["parameters"] for tool in body["tools"]}
    actions = []
    for call in message["tool_calls"]:
        function = call["function"]
        schema = definitions.get(function["name"])
        arguments = None
        try:
            arguments = json.loads(function["arguments"])
        except json.JSONDecodeError:
            pass
        well_formed_fields = (
            schema is not None
            and isinstance(arguments, dict)
            and set(schema.get("required", ())) <= arguments.keys()
            and arguments.keys() <= schema["properties"].keys()
        )
        actions.append({
            "name": function["name"],
            "arguments_sha256": sha256(function["arguments"].encode()),
            "advertised_tool_and_fields": well_formed_fields,
        })
    evidence = {
        "name": name,
        "label": label,
        "finish_reason": receipt["finish_reason"],
        "output_tokens": receipt["native"]["predicted_n"],
        "source_body_sha256": receipt["source_body_sha256"],
        "request_body_sha256": receipt["request_body_sha256"],
        "parsed_message_sha256": receipt["private_message_sha256"],
        "private_sse_sha256": receipt["private_sse_sha256"],
        "visible_content_sha256": sha256(message["content"].encode()),
        "visible_characters": len(message["content"]),
        "actions": actions,
    }
    if label == "OFF56" and any(tag in message["content"] for tag in ("<template>", "</template>")):
        evidence["strictformat_compliant"] = False
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    pins = {
        ("ON" if "-on-" in row["id"] else "OFF") + row["seq"]: row
        for row in json.loads(MANIFEST.read_bytes())["requests"]
    }
    bodies = {label: pinned_body(row) for label, row in pins.items()}
    reviews = [
        review_stream(path, pins, bodies)
        for path in sorted(args.run_directory.glob("*-target.receipt.json"))
        if "-fixed" not in path.name
    ]
    print(json.dumps(reviews, indent=2))


if __name__ == "__main__":
    main()
