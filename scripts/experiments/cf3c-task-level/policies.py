"""Build the archived prefix and apply its source-pinned history interventions."""

import hashlib
import json
from copy import deepcopy

from src.context_compression import (
    CompressorConfig,
    ContextCompressor,
    sanitize_tool_pairs,
)

ARMS = ("A0", "A1-k4", "A1-k8", "A1-k12", "A2", "A3")
LOCATIONS = ("tool-tail", "tool-head", "assistant-reasoning")
EXPOSED = {
    "tool-tail": (True, False, False, False, False, True),
    "tool-head": (True, False, False, False, True, True),
    "assistant-reasoning": (True, True, True, True, True, False),
}
LATEST = 3
MASK_CHARS = 180
FILL = (
    "The records office indexed this entry under the current reconciliation batch. "
    "The transfer date is provisional pending routine review by the archive custodian. "
    "This entry excludes temporary routing instructions and lists no outstanding action. "
    "The sealed original is held by the audit desk."
)
SYSTEM = (
    "You are finishing an order reconciliation in a local simulator. The earlier archive readings "
    "provide receipts by desk. Those readings are closed and cannot be run again. "
    "Inspect the requested order with inspect_order. It returns the archive desk and a challenge. "
    "Find that desk's receipt in the historical context, then call release_order with the receipt "
    "and challenge. After a successful release, reply exactly RELEASED followed by a space and "
    "the confirmation from the tool. If you cannot release the order, reply exactly BLOCKED."
)


def archive(case):
    history = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Read the ten desk records for the current audit."},
    ]
    for desk in range(1, 11):
        target = desk == case["desk"]
        location = case["location"] if target else "tool-tail"
        decoy = hashlib.sha256(f"{case['id']}/decoy/{desk}".encode()).hexdigest()[:12]
        receipt = case["receipt"] if target else decoy
        field = f"Receipt for desk {desk}: {receipt}"
        note = f"ArchiveThinking{desk:02}: Desk {desk} reviewed for the transfer audit."
        if location == "assistant-reasoning":
            note += f" {field}"
        observation = f"ArchiveHead{desk:02}: desk {desk} reconciliation record.\n"
        if location == "tool-head":
            observation += field + "\n"
        observation += FILL
        if location == "tool-tail":
            observation += "\n" + field
        observation += f"\nArchiveTail{desk:02}"
        call_id = f"archived-{desk:02}"
        history.extend(
            (
                {
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": note,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": "archive_read",
                                "arguments": json.dumps({"desk": desk}),
                            },
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": call_id, "content": observation},
            )
        )
    history.append(
        {
            "role": "user",
            "content": f"Please reconcile and release order {case['order']}.",
        }
    )
    return history


def select(history, arm):
    if arm not in ARMS:
        raise ValueError(f"unknown policy {arm}")
    messages = deepcopy(history)
    receipt = {
        "arm": arm,
        "production_stubbed": 0,
        "pairs_fixed": 0,
        "compaction_model_calls": 0,
    }
    if arm.startswith("A1-"):
        k = int(arm.split("-k")[1])
        # Match the pilot convention at task entry: the pending user request is
        # outside the compressor. On continuation, the current tool tail is protected.
        separate_user = messages[-1]["role"] == "user"
        archived = messages[:-1] if separate_user else messages
        result = ContextCompressor(
            CompressorConfig(tool_output_age_threshold=k)
        ).compress(archived)
        messages = result.messages + (messages[-1:] if separate_user else [])
        receipt.update(
            production_threshold=k,
            production_stubbed=result.tool_outputs_summarized,
            pairs_fixed=result.tool_pairs_fixed,
        )
    elif arm == "A2":
        observations = [m for m in messages if m["role"] == "tool"]
        for message in observations[:-LATEST]:
            content = message["content"]
            if len(content) > MASK_CHARS:
                message["content"] = (
                    content[:MASK_CHARS] + "\n[Older observation truncated]"
                )
    elif arm == "A3":
        assistants = [
            m
            for m in messages
            if m["role"] == "assistant"
            and any(
                str(m.get(field) or "").strip()
                for field in ("reasoning_content", "content")
            )
        ]
        for message in assistants[:-LATEST]:
            for field in ("reasoning_content", "content"):
                if str(message.get(field) or "").strip():
                    message[field] = "omitted"

    if (
        sanitize_tool_pairs(messages)[1]
        or receipt["pairs_fixed"]
        or len(messages) != len(history)
    ):
        raise ValueError("history intervention changed tool pair custody")
    receipt["changed_observations"] = []
    receipt["changed_assistant_entries"] = []
    for index, (before, after) in enumerate(zip(history, messages, strict=True)):
        if before == after:
            continue
        if (
            before["role"] == "tool"
            and {**before, "content": after["content"]} == after
        ):
            receipt["changed_observations"].append(index)
        elif (
            before["role"] == "assistant"
            and {
                **before,
                **{
                    key: after[key]
                    for key in ("content", "reasoning_content")
                    if key in after
                },
            }
            == after
        ):
            receipt["changed_assistant_entries"].append(index)
        else:
            raise ValueError("history intervention changed an invariant message field")
    receipt["active"] = bool(
        receipt["changed_observations"] or receipt["changed_assistant_entries"]
    )
    return messages, receipt


def occurrences(messages, value):
    return [
        {"message": index, "field": key, "count": count}
        for index, message in enumerate(messages)
        for key, data in message.items()
        if (count := json.dumps(data, ensure_ascii=False).count(value))
    ]


def verify_structured(case, original, selected, arm, policy):
    desk = case["desk"]
    location = case["location"]
    first = 2 * desk
    index, field = (
        (first, "reasoning_content")
        if location == "assistant-reasoning"
        else (first + 1, "content")
    )
    witness = [{"message": index, "field": field, "count": 1}]
    expected = EXPOSED[location][ARMS.index(arm)]
    entries = occurrences(selected, case["receipt"])
    if occurrences(original[:23], case["receipt"]) != witness:
        raise ValueError("archived receipt escaped its registered carrier")
    if [entry for entry in entries if entry["message"] < 23] != (
        witness if expected else []
    ):
        raise ValueError("selected archive disagrees with the registered exposure")
    if arm.startswith("A1-") and (
        policy["production_stubbed"] < 6
        or (len(original) == 23 and policy["production_stubbed"] != 6)
    ):
        raise ValueError("registered A1 threshold did not activate")
    if policy["active"] != (arm != "A0"):
        raise ValueError("unexpected policy activation")
    return {"archive_receipt_exposed": expected, "receipt_occurrences": entries}


def verify_render(case, messages, rendered, custody):
    for desk in range(1, 11):
        for marker, index, field in (
            (f"ArchiveHead{desk:02}", 2 * desk + 1, "content"),
            (f"ArchiveTail{desk:02}", 2 * desk + 1, "content"),
            (f"ArchiveThinking{desk:02}", 2 * desk, "reasoning_content"),
        ):
            entries = occurrences(messages, marker)
            archived = [entry for entry in entries if entry["message"] < 23]
            expected = (
                [{"message": index, "field": field, "count": 1}]
                if marker in messages[index][field]
                else []
            )
            if archived != expected or rendered.count(marker) != sum(
                entry["count"] for entry in entries
            ):
                raise ValueError(
                    f"native render/archive visibility mismatch for {marker}"
                )
    if rendered.count(case["receipt"]) != sum(
        entry["count"] for entry in custody["receipt_occurrences"]
    ):
        raise ValueError("native receipt exposure disagrees with structured history")
