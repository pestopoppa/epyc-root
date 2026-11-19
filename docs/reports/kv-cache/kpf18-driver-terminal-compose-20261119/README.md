# KPF-18 full-driver terminal-refusal composition

The disabled successor now composes the source-bound terminal-refusal patch
with the previously sealed full-driver transport. STOP, deadline, missing
rowflow fields and underlying guard refusal reach the actual gate's Abort
path (rc3), skip publication, call fake server cleanup and finalize a partial
run. A latched refusal survives an exception from the actual controller's
attempt finalizer, including simultaneous refusal-ledger failure. Ordinary
seed errors retain all three construction attempts and the existing diagnostic
publication behavior.

Installed successor: `/mnt/raid0/llm/tmp/kvu/driver-terminal-successor-20261119`.
The installer changes only the driver and import binder, and writes a disabled
launcher and manifest. All other inputs remain at their existing paths, bound
by SHA-256. The sealed patch is applied with zero fuzz; its context line for
the already-composed output root is adapted from `guard.attempt_root()` to
`output_root()`. The preceding transport overlay is unchanged. Explicit module
binding refuses a preloaded terminal adapter or boundary helper. Both direct
entries still return 78.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-driver-terminal-compose-20261119 \
  -p test_composition.py -v
```

Four harness checks and eleven child-process checks pass. The persistent
installation also passes all eleven checks. The child imports the entire
installed driver and actual controller/gate, invokes actual `item3` to create
its cell, and executes it through actual `gate.main` and `controller.run`.
No AST extraction or replacement cell is used. Native seed peers, server,
identity setup, ledger and publication are fakes. Cases cover STOP, deadline,
guard refusal, missing contract, attempt-finalizer failure, refusal-ledger
failure, both ledger failures, ordinary-error retry, callable identity,
repeated binding and source drift. Harness checks cover disabled entries,
destination refusal, incomplete installation and foreign preloaded helpers.
The qualification record binds installed driver/manifest and test by SHA-256.

This is model-free software qualification. It does not qualify native
cancellation/release, actual owned server/descendant drain, the diagnostic
publication pipeline, native execution custody or current rowflow admission.
The retained boundary adapter checks exported fields; it is not admission
authority. Historical native inventory drift (including `/usr/bin/flock`)
still requires current execution dependency binding. No model or GPU ran;
KPF-18.0d remains open and no layout verdict follows.

Next: prepare the owned-native lifecycle qualification from this successor,
bind current execution dependencies and current official admission, then make
the scheduled lifecycle row ready before GPU diagnostic publication.
GitNexus status/impact report no indexed repository in this lane; graph blast
radius is unavailable. Repository edits are confined to this package and the
owning handoff/progress entry.
