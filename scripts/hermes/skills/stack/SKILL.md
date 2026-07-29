---
name: stack
description: Control the orchestrator stack lifecycle from Hermes via a thin wrapper over the existing stack launcher.
version: 1.0.0
metadata:
  hermes:
    tags: [orchestrator, stack, launcher]
---

# /stack — Orchestrator Stack Control

Use `/stack` when you want Hermes to forward stack lifecycle actions directly to
the existing orchestrator launcher without inventing routing logic or runtime
glue. This command is a no-inference wrapper around
`/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` and
exposes the launcher’s `status`, `start`, `stop`, and `reload` commands as-is.

## Usage

- `/stack status` - Show stack state and running components
- `/stack start` - Start the stack with the launcher defaults
- `/stack start --hot-only` - Start only HOT models
- `/stack start --include-warm ROLE...` - Include specific WARM roles
- `/stack start --only ROLE...` - Start only the listed roles
- `/stack start --dev` - Start the launcher’s dev configuration
- `/stack stop --all` - Stop all managed components
- `/stack stop COMPONENT...` - Stop specific components
- `/stack reload COMPONENT...` - Reload specific components in place

## Runtime Surface

| Field | Value |
|---|---|
| Type | Local Hermes command wrapper |
| Launcher | `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` |
| Invocation | `python3 /mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py <command> [args...]` |
| Commands | `status`, `start`, `stop`, `reload` |
| Scope | Orchestrator API, model servers, and other managed stack components |

## Command Mapping

| Hermes command | Launcher command | Notes |
|---|---|---|
| `/stack status` | `status` | Read-only status inspection |
| `/stack start ...` | `start ...` | Forwards launcher flags verbatim |
| `/stack stop ...` | `stop ...` | Use `--all` or explicit component names |
| `/stack reload ...` | `reload ...` | Requires one or more component names |

## Gotchas

- This skill does not add new launcher behavior; it only documents and exposes
  the existing Python entrypoint.
- Pass launcher flags exactly as supported by
  `orchestrator_stack.py`; do not infer or rename components.
- The launcher’s command surface is the source of truth for valid arguments.
  Re-check the file before adding new examples or aliases.
