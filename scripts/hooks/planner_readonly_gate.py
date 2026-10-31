#!/usr/bin/env python3
"""Opt-in Claude PreToolUse spike; host installs with a fixed actor-seat argument.

This is an action approval boundary, not a sandbox or a filesystem isolation
mechanism. Never derive the seat from the tool payload or the command's env.
"""
import json
import re
import sys

# Absolute executable path: never use PATH or an actor-provided program name.
EXTERNAL_VERBS = frozenset({'/usr/bin/cat'})
MAX_INPUT_BYTES = 65536
_LITERAL = re.compile(r'^[A-Za-z0-9_./:+,@%=-]+$')


def allowed(seat, payload):
    if seat not in ('planner', 'critic') or not isinstance(payload, dict):
        return False
    if payload.get('hook_event_name') != 'PreToolUse':
        return False
    tool, args = payload.get('tool_name'), payload.get('tool_input')
    if not isinstance(args, dict):
        return False
    # Deliberately narrow: no tool options, no hidden behavior from future fields.
    if tool == 'Read':
        return set(args) == {'file_path'} and isinstance(args['file_path'], str) and bool(args['file_path'])
    if tool == 'Glob':
        return set(args) == {'pattern'} and isinstance(args['pattern'], str) and bool(args['pattern'])
    if tool == 'Grep':
        return set(args) == {'pattern'} and isinstance(args['pattern'], str) and bool(args['pattern'])
    if tool != 'Bash' or set(args) != {'command'} or not isinstance(args['command'], str):
        return False
    # No quoting, substitutions, shell metacharacters, options or wrappers.
    command = args['command']
    if not re.fullmatch(r'[A-Za-z0-9_./:+,@%= -]+', command):
        return False
    parts = command.split(' ')
    return (len(parts) >= 2 and parts[0] in EXTERNAL_VERBS
            and all(_LITERAL.fullmatch(p) and not p.startswith('-') for p in parts[1:]))


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError('hook payload too large')
        payload = json.loads(raw)
        seat = sys.argv[1] if len(sys.argv) == 2 else None
        decision = 'allow' if allowed(seat, payload) else 'ask'
    except Exception:  # malformed or unexpected parser/inspection failures ask
        decision = 'ask'
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
          'permissionDecision': decision,
          'permissionDecisionReason': 'Read-only actor gate: human approval required' if decision == 'ask' else 'Read-only actor gate: allowlisted inspection'}}))


if __name__ == '__main__':
    main()
