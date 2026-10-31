# DP-5 wake-character fixture acceptance

The actual `_press_key_with_wake` helper is already committed (introduced2054659d7) and the quarantined composer repair calls it. This patch adds the missing requested fixture behavior and regression controls; no live adapter, roster, transport, config, or service changes.

The disposable fixture supports `--mode wake --pending queued`: bare Enter/Ctrl-U do nothing until an ordinary character arrives. Exact SPACE is recorded. The helper tests import the real owner module; their sole mocked transport writes the requested byte to captured private PTY children. No tmux subprocess, real pane or external message occurs. Each child exits via Ctrl-D and its captured Popen is waited; R6 receipts prove empty childsets.

Final7 tests pass: both Claude/Codex glyphs with exact wake/send order and transcript trailing SPACE, clear with no transcript, honest bare-key noops, swallowed/failed Enter leaving the real wake SPACE queued, failed wake never sends key, and all4 original fixture modes preserving original behavior. Helper rc0 is only transport acceptance; the swallowed-key fixture explicitly remains pending rather than being claimed delivered.

Mutation removes only the actual helper wake-send AST assignment and executes the same positive PTY test: exactly1 assertion failure,0 errors. The final mutation runner returns0 only after proving that expected red result; its log preserves the failure. Green final7 source and mutation are both R6 family28 CPUs124-125, ~6.0s/50.9MB and1.22s/50.5MB; no model/GPU run or janitor operation. The integrated seven-test suite, mutation control and Ruff all passed after the final changes; see `integrated-controls-r2.log` and its resource receipt.

Tests are self-contained in a normal root checkout: `python3 scripts/coordination/tests/test_dp5_wake_pty.py`; the sibling `mutation_control.py` reruns the negative control against that checkout. Private review runs used DP5_OWNER_ROOT only to import the unchanged actual helper from the owner checkout. This is software conformance, no new live-UI calibration or deployment claim.
