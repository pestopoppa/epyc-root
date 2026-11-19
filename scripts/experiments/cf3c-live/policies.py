"""Deterministic structured-history policies and fixed continuation fixtures."""
from copy import deepcopy
import json

from src.context_compression import CompressorConfig, ContextCompressor, sanitize_tool_pairs

ARMS = ("A0", "A1-k4", "A1-k8", "A1-k12", "A2", "A3")
CASES = (
    {"id": "old-deep", "steps": 6, "target": 2, "early": False},
    {"id": "old-head", "steps": 8, "target": 2, "early": True},
    {"id": "recent", "steps": 10, "target": 9, "early": False},
)
LATEST = 3
MASK_CHARS = 180
FILL = (
    "The archive imported this journal segment from the reconciliation ledger. "
    "The receiving office indexed the journal under its daily reconciliation batch. "
    "The checkpoint confirms transfer dates and excludes temporary routing assignments. "
    "The records custodian issued a routine retention note with no action required. "
)
TOOLS = [{"type": "function", "function": {
    "name": "archive_read", "description": "Read an archive record by desk number.",
    "parameters": {"type": "object", "properties": {"desk": {"type": "integer"}},
                   "required": ["desk"]},
}}]


def make_messages(case):
    messages = [
        {"role": "system", "content": "Read the supplied archive transcript carefully."},
        {"role": "user", "content": "Review the desk records from the audit."},
    ]
    for index in range(1, case["steps"] + 1):
        call_id = f"archive-{index:02}"
        receipt = case["answer"] if index == case["target"] else case["decoys"][index - 1]
        field = f"receipt={receipt}\n"
        head = f"ObservationHead{index:02} -- Desk {index} archived record\n"
        observation = head + (field if case["early"] else "") + FILL * 8
        if not case["early"]:
            observation += "\n" + field
        observation += f"ObservationTail{index:02}"
        thoughts = (
            f"ReasoningTrace{index:02}. I should check the next desk ledger. "
            "The desk number identifies the relevant record. I should rely on the archived field "
            "and avoid substituting a routing ID or a label from another record. "
        )
        messages += [
            {"role": "assistant", "content": "", "reasoning_content": thoughts + FILL * 3,
             "tool_calls": [{"id": call_id, "type": "function", "function": {
                 "name": "archive_read", "arguments": json.dumps({"desk": index}),
             }}]},
            {"role": "tool", "tool_call_id": call_id, "content": observation},
        ]
    messages.append({
        "role": "user",
        "content": f"What is the exact receipt for desk {case['target']}? "
                   "Reply with only the 16 lowercase hexadecimal characters, or UNKNOWN if missing.",
    })
    return messages


def apply_policy(messages, arm):
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm}")
    history = deepcopy(messages[:-1])
    observations = [index for index, msg in enumerate(history) if msg["role"] == "tool"]
    reasoning = [index for index, msg in enumerate(history)
                 if msg["role"] == "assistant"
                 and any(str(msg.get(key) or "").strip() for key in ("reasoning_content", "content"))]
    receipt = {"arm": arm, "pairs_fixed": 0, "compaction_model_calls": 0}
    if arm.startswith("A1-"):
        threshold = int(arm.split("-k")[1])
        # This is the v1 history length guard. The production class owns all
        # protected-zone alignment, threshold counting, typing and sanitization.
        if len(history) > 8:
            result = ContextCompressor(CompressorConfig(tool_output_age_threshold=threshold)).compress(history)
            history = result.messages
            receipt.update(pairs_fixed=result.tool_pairs_fixed,
                           production_stubbed=result.tool_outputs_summarized)
        receipt["production_threshold"] = threshold
    elif arm == "A2":
        for index in observations[:-LATEST]:
            original = history[index]["content"]
            if len(original) > MASK_CHARS:
                history[index]["content"] = original[:MASK_CHARS] + "\n[Older observation truncated]"
    elif arm == "A3":
        for index in reasoning[:-LATEST]:
            for key in ("reasoning_content", "content"):
                if str(history[index].get(key) or "").strip():
                    history[index][key] = "omitted"
    if sanitize_tool_pairs(history)[1] or receipt["pairs_fixed"] or len(history) != len(messages) - 1:
        raise ValueError("tool pair custody failed for the fixture")
    selected = [*history, deepcopy(messages[-1])]
    receipt["changed_observations"] = [index for index in observations if selected[index] != messages[index]]
    receipt["changed_assistant_entries"] = [index for index in reasoning if selected[index] != messages[index]]
    return selected, receipt


def verify_render(case, selected, rendered):
    """Prove each retained or removed field actually reached the template."""
    tool_messages = [msg for msg in selected if msg["role"] == "tool"]
    assistants = [msg for msg in selected if msg["role"] == "assistant"]
    for index, (tool, assistant) in enumerate(zip(tool_messages, assistants, strict=True), 1):
        for marker, visible in (
            (f"ObservationHead{index:02}", f"ObservationHead{index:02}" in tool["content"]),
            (f"ObservationTail{index:02}", f"ObservationTail{index:02}" in tool["content"]),
            (f"ReasoningTrace{index:02}", f"ReasoningTrace{index:02}" in assistant["reasoning_content"]),
        ):
            if (marker in rendered) != visible:
                raise ValueError(f"rendered prompt visibility mismatch for {marker}")
    if (case["answer"] in rendered) != any(case["answer"] in msg["content"] for msg in tool_messages):
        raise ValueError("rendered answer exposure disagrees with served observation")
