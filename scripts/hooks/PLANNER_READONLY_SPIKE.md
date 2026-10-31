# Opt-in planner/critic action gate spike

The host must bind this hook to *all* PreToolUse calls for a dedicated actor seat, with an immutable seat argument selected by the host. This complete settings example has no matcher, so it covers all tools:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/python3 /ABSOLUTE/TRUSTED/PATH/planner_readonly_gate.py planner",
            "timeout": 5,
            "onFailure": "block"
          }
        ]
      }
    ]
  }
}
```

Use `critic` for a critic seat. Claude Code **2.1.295 or later** and a working native human permission flow are prerequisites. The host must verify that its actual installation supports and enforces this configuration before use. As the [official hooks reference](https://code.claude.com/docs/en/hooks#block-the-action-when-a-hook-fails) explains, failures and timeouts otherwise normally continue; `onFailure: "block"` blocks the action on those failures. Invalid JSON or schema output is also a hook failure; do not rely on a failed process to emit `ask`. This is an example only, not an installation. The host must protect the settings, hook and interpreter from that actor, and provide the normal interactive human approval flow. The hook returns native `allow` for a narrow set of inspection requests and `ask` otherwise. No actor-supplied role, flag, payload field or command environment can authorize an action. Unknown seat, malformed input, unknown tool, extra options, shell syntax and all non-allowlisted commands request approval. Approval belongs to the host's native permission mechanism, not this hook. An actor must not be able to change the hook registration or interpreter.

Only plain Read(file_path), Glob(pattern), Grep(pattern), and `/usr/bin/cat` with literal non-option operands are recognized; this intentionally sacrifices compatibility. It does not support shell quoting or compound commands. The absolute executable must be host-trusted. It does not restrict what a read can disclose, symlink traversal, device files, filesystem effects outside the hook, other unhooked channels, or provide an OS sandbox. This spike does not enable an actor, hook, or global setting. More tools and options require their own safe parsing and tests.

The tests simulate the host failure contract and are not a live Claude session. Run the test module with the project's bounded model-free prep protocol. It drives the native JSON boundary in a child process and executes only a fixed, allowlisted cat against its own test fixture; rejected input is never executed.
