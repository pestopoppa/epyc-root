# KPF-18 checkpoint restore witness

`restore_witness.attest` parses the native `SLT_TRC` checkpoint restore event from the P1 server. It requires independently obtained task and slot IDs and an expected checkpoint position, and refuses missing, ambiguous or inconsistent events. The parser alone does not bind an HTTP request, verify the mapped binary, prove physical placement or establish a correctness verdict.

The historical `a1f0c8cf9` server emits the event immediately after checkpoint state is loaded. With fork mode enabled its response timings expose `id_task` and `id_slot`; a caller must preserve and cross-check those values, capture the relevant native log at trace verbosity, and verify the running mapped server library against the intended build. The historical `libllama-server-impl.so` inspected for this format had SHA-256 `58e8905f269b9e6f6f38354f826ea83cbaf9b7f9a9d76e502ec54840394f9269`.

Run the isolated parser tests with `python3 -m unittest discover -s docs/reports/kv-cache/kpf18-restore-witness-20261105 -p 'test_*.py'`. These model-free tests do not qualify a live inference run.
