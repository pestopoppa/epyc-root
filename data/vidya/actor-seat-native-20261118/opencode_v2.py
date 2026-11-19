"""Project our read-only OpenCode v2 session export into the research metrics parser.

The source file remains the CLI's untouched bytes. Only the input to the existing
parser is translated. An unsupported event or part stops this instrument.
"""
import json


def metrics_export(path, parse_export_data):
    native = json.loads(path.read_bytes())
    session_id = native["info"]["id"]
    messages = []
    for event in native["messages"]:
        role = event["type"]
        if role == "idle":
            continue
        if role not in ("user", "assistant"):
            raise ValueError(f"unsupported OpenCode v2 message type: {role}")
        info = {"id": event["id"], "sessionID": session_id, "role": role, "time": event["time"]}
        if role == "assistant":
            # The old parser defaults absent usage to zero. Refuse incomplete v2 usage
            # here so each count projected by this instrument is producer-observed.
            tokens = event["tokens"]
            cache = tokens["cache"]
            counts = [tokens[key] for key in ("input", "output", "reasoning")]
            counts.extend(cache[key] for key in ("read", "write"))
            if any(type(count) is not int or count < 0 for count in counts):
                raise ValueError("OpenCode v2 usage is missing or invalid")
            info.update(finish=event["finish"], tokens=tokens)
            parts = event["content"]
            if any(part["type"] not in ("text", "reasoning") for part in parts):
                raise ValueError("unsupported OpenCode v2 content in the tool-denied native control")
        else:
            parts = [{"type": "text", "text": event["text"]}]
        messages.append({"info": info, "parts": parts})
    return parse_export_data({"messages": messages})
