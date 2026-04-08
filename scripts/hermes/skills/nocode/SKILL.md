---
name: nocode
description: Disable REPL code execution for this conversation. Forces direct text responses only — no Python/shell execution.
version: 1.0.0
metadata:
  hermes:
    tags: [routing, orchestrator, safety]
---

# /nocode — Disable REPL Execution

Skip REPL code execution and force direct text responses only.

## Usage

- `/nocode` — Disable code execution for this conversation
- `/nocode off` — Re-enable code execution (default behavior)

## API Mapping

| Command | API Parameter | Value |
|---------|--------------|-------|
| `/nocode` | `x_disable_repl` | `"true"` |
| `/nocode off` | `x_disable_repl` | `"false"` |

## When to Use

- Discussing sensitive topics where code execution is unnecessary
- When the orchestrator's REPL loop is wasting turns on a non-code task
- For pure reasoning/analysis where direct answers are preferred
- When latency matters and you want to skip the code execution overhead

## Notes

- Override parameter must be passed as a string (`"true"` not `true`)
- When REPL is disabled, the model generates a direct text answer instead of writing Python
- This does not affect the model's reasoning ability, only its tool-use behavior
