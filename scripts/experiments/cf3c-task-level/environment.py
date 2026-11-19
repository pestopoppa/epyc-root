"""An isolated finite order service with stateful tool execution and its task oracle."""

import json
from dataclasses import dataclass


def _tool(name, description, properties):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    key: {"type": "string", "description": value}
                    for key, value in properties.items()
                },
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    _tool(
        "inspect_order",
        "Get the archive desk and release challenge for an order.",
        {"order": "The order ID from the user's request."},
    ),
    _tool(
        "release_order",
        "Release the inspected order and return its confirmation.",
        {
            "receipt": "Receipt for the archive desk returned by inspect_order.",
            "challenge": "Exact challenge from inspect_order.",
        },
    ),
]


@dataclass
class OrderService:
    order: str
    desk: int
    receipt: str
    challenge: str
    confirmation: str
    inspected: bool = False
    released: bool = False

    def execute(self, calls):
        observations, events = [], []
        for call in calls:
            name = call["function"]["name"]
            try:
                arguments = json.loads(call["function"]["arguments"])
            except (TypeError, ValueError):
                arguments = None
            if len(calls) == 1:
                outcome, result = self._execute_one(name, arguments)
            else:
                outcome, result = (
                    "rejected",
                    {"message": "Call only one tool at a time."},
                )
            events.append({"tool": name, "call_id": call["id"], "outcome": outcome})
            observations.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, sort_keys=True),
                }
            )
        return observations, events

    def _execute_one(self, name, arguments):
        if not isinstance(arguments, dict):
            return "rejected", {
                "message": "Supply a JSON object with the documented arguments."
            }
        if name == "inspect_order" and arguments == {"order": self.order}:
            self.inspected = True
            return "inspected", {"desk": self.desk, "challenge": self.challenge}
        if (
            name == "release_order"
            and self.inspected
            and arguments
            == {
                "receipt": self.receipt,
                "challenge": self.challenge,
            }
        ):
            self.released = True
            return "released", {"confirmation": self.confirmation}
        return "rejected", {
            "message": "Action denied. Check the order, archive desk receipt and challenge."
        }

    def score(self, content):
        if not isinstance(content, str):
            raise TypeError("native stopped choice has no textual content")
        answer = content.strip()
        if answer == "BLOCKED":
            status = "abstained"
        elif not answer:
            status = "NA"
        else:
            status = "graded"
        return {
            "status": status,
            "answer": answer or None,
            "correct": self.released and answer == f"RELEASED {self.confirmation}",
            "non_termination": int(status == "NA"),
            "finish_reason": "empty_answer" if status == "NA" else "stop",
        }
